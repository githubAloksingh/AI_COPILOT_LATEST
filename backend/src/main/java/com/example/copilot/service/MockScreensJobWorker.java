package com.example.copilot.service;

import com.example.copilot.client.AiServiceClient;
import com.example.copilot.dto.MockScreensJobClaim;
import com.example.copilot.dto.ai.AiMockScreenPlanItem;
import com.example.copilot.dto.ai.AiMockScreenGenerationResponse;
import com.example.copilot.dto.ai.AiMockScreenSpecification;
import com.example.copilot.dto.ai.AiMockScreensPlanResponse;
import com.example.copilot.entity.MockScreensJob;
import com.example.copilot.exception.MockScreensJobException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.example.copilot.entity.MockScreensScreenOutput;
import com.fasterxml.jackson.core.type.TypeReference;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.core.task.TaskExecutor;
import org.springframework.core.task.TaskRejectedException;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Optional;
import java.util.ArrayList;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

@Slf4j
@Component
public class MockScreensJobWorker {

    private static final int MAX_JOBS_PER_POLL = 4;
    private static final String GENERIC_FAILURE_MESSAGE =
            "We could not create a screen plan from the selected BRD. Please retry the job.";
        private static final String SCREEN_FAILURE_MESSAGE =
            "We could not generate screen %d from the selected BRD. Please retry the job.";
            private static final String PDF_FAILURE_MESSAGE =
                "We could not create the final Mock Screens PDF. Please retry the job.";

    private final MockScreensJobService jobService;
    private final AiServiceClient aiServiceClient;
    private final ObjectMapper objectMapper;
    private final TaskExecutor jobExecutor;
    private final MockScreensPdfService pdfService;
    private final MockScreensPdfArtifactService pdfArtifactService;
    private final ConcurrentMap<String, MockScreensJobClaim> activeClaims = new ConcurrentHashMap<>();

    public MockScreensJobWorker(
            MockScreensJobService jobService,
            AiServiceClient aiServiceClient,
            ObjectMapper objectMapper,
            @Qualifier("mockScreensJobExecutor") TaskExecutor jobExecutor,
            MockScreensPdfService pdfService,
            MockScreensPdfArtifactService pdfArtifactService) {
        this.jobService = jobService;
        this.aiServiceClient = aiServiceClient;
        this.objectMapper = objectMapper;
        this.jobExecutor = jobExecutor;
        this.pdfService = pdfService;
        this.pdfArtifactService = pdfArtifactService;
    }

    @Scheduled(fixedDelayString = "${copilot.mock-screens.poll-delay-ms:1000}")
    public void dispatchQueuedJobs() {
        for (int i = 0; i < MAX_JOBS_PER_POLL; i++) {
            Optional<MockScreensJobClaim> claimedJob = jobService.claimNextQueuedJob();
            if (claimedJob.isEmpty()) {
                return;
            }

            MockScreensJobClaim claim = claimedJob.get();
            submitClaim(claim, () -> planJob(claim), "WORKER_QUEUE_FULL",
                    "The Mock Screens service is busy. Please submit the request again later.");
        }
    }

    @Scheduled(fixedDelayString = "${copilot.mock-screens.poll-delay-ms:1000}")
    public void dispatchPdfReadyJobs() {
        for (int i = 0; i < MAX_JOBS_PER_POLL; i++) {
            Optional<MockScreensJobClaim> claimedJob = jobService.claimNextPdfReadyJob();
            if (claimedJob.isEmpty()) {
                return;
            }

            MockScreensJobClaim claim = claimedJob.get();
            submitClaim(claim, () -> generatePdf(claim), "PDF_WORKER_QUEUE_FULL",
                    "The Mock Screens PDF service is busy. Please retry the job later.");
        }
    }

    @Scheduled(fixedDelayString = "${copilot.mock-screens.heartbeat-delay-ms:30000}")
    public void renewActiveLeases() {
        for (MockScreensJobClaim claim : activeClaims.values()) {
            if (!jobService.renewLease(claim)) {
                activeClaims.remove(claim.leaseToken(), claim);
            }
        }
    }

    @Scheduled(fixedDelayString = "${copilot.mock-screens.recovery-delay-ms:30000}")
    public void recoverExpiredJobs() {
        jobService.recoverExpiredJobs();
    }

    void planJob(MockScreensJobClaim claim) {
        Long id = claim.id();
        try {
            MockScreensJob job = jobService.getClaimedJobForPlanning(id, claim.leaseToken());
            if (job.getScreenPlan() == null || job.getScreenPlan().isBlank()) {
                AiMockScreensPlanResponse response = aiServiceClient.planMockScreens(job.getBrdId());
                validatePlan(response);
                String planJson = objectMapper.writeValueAsString(response.getScreens());
                jobService.storeScreenPlan(id, claim.leaseToken(), planJson);
            }
            generateScreens(claim);
        } catch (MockScreensJobException exception) {
            log.warn("Mock Screens planning stopped for job {}: {}", id, exception.getMessage());
            jobService.failJob(id, claim.leaseToken(), exception.getCode(), exception.getMessage());
        } catch (Exception exception) {
            log.error("Mock Screens planning failed for job {}", id, exception);
            jobService.failJob(id, claim.leaseToken(), "SCREEN_PLANNING_FAILED", GENERIC_FAILURE_MESSAGE);
        }
    }

    void generateScreens(MockScreensJobClaim claim) {
        Long id = claim.id();
        Integer activeSequence = null;
        try {
            MockScreensJob job = jobService.getJobForScreenGeneration(id, claim.leaseToken());
            List<AiMockScreenPlanItem> plan = objectMapper.readValue(
                    job.getScreenPlan(), new TypeReference<List<AiMockScreenPlanItem>>() {});
            validatePlan(plan);

            List<MockScreensScreenOutput> storedOutputs =
                    jobService.getScreenOutputsForGeneration(id, claim.leaseToken());
            if (storedOutputs.size() > plan.size()) {
                throw new IllegalStateException("More screens are stored than the plan contains.");
            }
            List<AiMockScreenSpecification> completedScreens = new ArrayList<>();
            for (int index = 0; index < storedOutputs.size(); index++) {
                AiMockScreenSpecification storedScreen = objectMapper.readValue(
                        storedOutputs.get(index).getSpecificationJson(), AiMockScreenSpecification.class);
                validateGeneratedScreen(storedScreen, plan.get(index));
                if (!storedOutputs.get(index).getSequence().equals(index + 1)) {
                    throw new IllegalStateException("Stored screen sequence is incomplete.");
                }
                completedScreens.add(storedScreen);
            }

            for (int index = storedOutputs.size(); index < plan.size(); index++) {
                AiMockScreenPlanItem plannedScreen = plan.get(index);
                activeSequence = plannedScreen.getSequence();
                jobService.getJobForScreenGeneration(id, claim.leaseToken());
                AiMockScreenGenerationResponse response = aiServiceClient.generateMockScreen(
                    job.getBrdId(), plannedScreen, List.copyOf(completedScreens));
                validateGeneratedScreen(response, plannedScreen);

                String specificationJson = objectMapper.writeValueAsString(response.getScreen());
                jobService.storeGeneratedScreen(id, claim.leaseToken(), response.getScreen(), specificationJson);
                completedScreens.add(response.getScreen());
                activeSequence = null;
            }

            jobService.markReadyForPdf(id, claim.leaseToken(), plan.size());
        } catch (MockScreensJobException exception) {
            log.warn("Mock Screens generation stopped for job {} at sequence {}: {}",
                    id, activeSequence, exception.getMessage());
            jobService.failJob(id, claim.leaseToken(), activeSequence, exception.getCode(), exception.getMessage());
        } catch (Exception exception) {
            log.error("Mock Screens generation failed for job {} at sequence {}", id, activeSequence, exception);
            String failureMessage = activeSequence == null
                    ? "We could not prepare the generated screens for PDF generation. Please retry the job."
                    : String.format(SCREEN_FAILURE_MESSAGE, activeSequence);
            jobService.failJob(id, claim.leaseToken(), activeSequence, "SCREEN_GENERATION_FAILED", failureMessage);
        }
    }

    void generatePdf(MockScreensJobClaim claim) {
        Long id = claim.id();
        try {
            MockScreensJob job = jobService.getJobForPdfGeneration(id, claim.leaseToken());
            List<AiMockScreenPlanItem> plan = objectMapper.readValue(
                    job.getScreenPlan(), new TypeReference<List<AiMockScreenPlanItem>>() {});
            List<MockScreensScreenOutput> outputs = jobService.getScreenOutputsForPdf(id, claim.leaseToken());
            byte[] pdfBytes = pdfService.generateConsolidatedPdf(outputs, plan);
            pdfArtifactService.persistAndComplete(id, claim.leaseToken(), pdfBytes);
        } catch (MockScreensJobException exception) {
            log.warn("Mock Screens PDF generation stopped for job {}: {}", id, exception.getMessage());
            jobService.failJob(id, claim.leaseToken(), exception.getCode(), exception.getMessage());
        } catch (Exception exception) {
            log.error("Mock Screens PDF generation failed for job {}", id, exception);
            jobService.failJob(id, claim.leaseToken(), "PDF_GENERATION_FAILED", PDF_FAILURE_MESSAGE);
        }
    }

    private void submitClaim(MockScreensJobClaim claim, Runnable task, String errorCode, String message) {
        activeClaims.put(claim.leaseToken(), claim);
        try {
            jobExecutor.execute(() -> {
                try {
                    task.run();
                } finally {
                    activeClaims.remove(claim.leaseToken(), claim);
                }
            });
        } catch (TaskRejectedException exception) {
            activeClaims.remove(claim.leaseToken(), claim);
            log.warn("Mock Screens worker queue rejected job {}", claim.id(), exception);
            jobService.failJob(claim.id(), claim.leaseToken(), errorCode, message);
        }
    }

    private void validatePlan(AiMockScreensPlanResponse response) {
        validatePlan(response != null ? response.getScreens() : null);
    }

    private void validatePlan(List<AiMockScreenPlanItem> screens) {
        if (screens == null || screens.isEmpty()) {
            throw new IllegalStateException("AI service returned an empty screen plan.");
        }

        for (int index = 0; index < screens.size(); index++) {
            AiMockScreenPlanItem screen = screens.get(index);
            if (screen == null
                    || screen.getSequence() != index + 1
                    || screen.getScreenName() == null || screen.getScreenName().isBlank()
                    || screen.getPurpose() == null || screen.getPurpose().isBlank()
                    || screen.getRelevantRequirements() == null || screen.getRelevantRequirements().isEmpty()) {
                throw new IllegalStateException("AI service returned an invalid ordered screen plan.");
            }
        }
    }

    private void validateGeneratedScreen(
            AiMockScreenGenerationResponse response,
            AiMockScreenPlanItem plannedScreen) {
        AiMockScreenSpecification screen = response != null ? response.getScreen() : null;
        validateGeneratedScreen(screen, plannedScreen);
        }

        private void validateGeneratedScreen(
            AiMockScreenSpecification screen,
            AiMockScreenPlanItem plannedScreen) {
        if (screen == null
                || screen.getSequence() != plannedScreen.getSequence()
                || !plannedScreen.getScreenName().equals(screen.getScreenName())
                || screen.getPurpose() == null || screen.getPurpose().isBlank()
                || screen.getLayoutDescription() == null || screen.getLayoutDescription().isBlank()
                || screen.getComponents() == null || screen.getComponents().isEmpty()) {
            throw new IllegalStateException("AI service returned a screen that does not match its planned sequence.");
        }
    }
}