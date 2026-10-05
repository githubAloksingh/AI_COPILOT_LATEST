package com.example.copilot.service;

import com.example.copilot.client.AiServiceClient;
import com.example.copilot.dto.MockScreensJobClaim;
import com.example.copilot.dto.MockScreensJobResponse;
import com.example.copilot.dto.ai.AiMockScreenComponent;
import com.example.copilot.dto.ai.AiMockScreenGenerationResponse;
import com.example.copilot.dto.ai.AiMockScreenPlanItem;
import com.example.copilot.dto.ai.AiMockScreenSpecification;
import com.example.copilot.dto.ai.AiMockScreensPlanResponse;
import com.example.copilot.entity.MockScreensJob;
import com.example.copilot.entity.MockScreensJobStatus;
import com.example.copilot.entity.MockScreensScreenOutput;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.InOrder;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class MockScreensJobWorkerTest {

    private static final MockScreensJobClaim CLAIM = new MockScreensJobClaim(51L, "lease-token");

    @Mock
    private MockScreensJobService jobService;

    @Mock
    private AiServiceClient aiServiceClient;

    @Mock
    private MockScreensPdfService pdfService;

    @Mock
    private MockScreensPdfArtifactService pdfArtifactService;

    private final ObjectMapper objectMapper = new ObjectMapper();
    private List<Runnable> submittedTasks;
    private MockScreensJobWorker worker;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
        submittedTasks = new ArrayList<>();
        worker = new MockScreensJobWorker(
            jobService, aiServiceClient, objectMapper, submittedTasks::add, pdfService, pdfArtifactService);
    }

    @Test
    void dispatcherPicksQueuedJobAndSubmitsBackgroundTask() {
        when(jobService.claimNextQueuedJob()).thenReturn(Optional.of(CLAIM), Optional.empty());

        worker.dispatchQueuedJobs();

        assertEquals(1, submittedTasks.size());
        verify(jobService, org.mockito.Mockito.times(2)).claimNextQueuedJob();
    }

    @Test
    void pdfDispatcherPicksReadyForPdfJobAndSubmitsBackgroundTask() {
        when(jobService.claimNextPdfReadyJob()).thenReturn(Optional.of(CLAIM), Optional.empty());

        worker.dispatchPdfReadyJobs();

        assertEquals(1, submittedTasks.size());
        verify(jobService, org.mockito.Mockito.times(2)).claimNextPdfReadyJob();
    }

    @Test
        void screensGenerateAndPersistStrictlyInPlannedSequence() throws Exception {
        MockScreensJob job = processingJob(List.of(
            plannedScreen(1, "Account Details"),
            plannedScreen(2, "Review Details")));
        when(jobService.getJobForScreenGeneration(51L, CLAIM.leaseToken())).thenReturn(job);
        when(jobService.getScreenOutputsForGeneration(51L, CLAIM.leaseToken())).thenReturn(List.of());
        List<Integer> startedSequences = new ArrayList<>();
        when(aiServiceClient.generateMockScreen(eq(9L), eq(job.getPrompt()), any(AiMockScreenPlanItem.class), anyList()))
            .thenAnswer(invocation -> {
                AiMockScreenPlanItem planned = invocation.getArgument(2);
                List<AiMockScreenSpecification> previous = invocation.getArgument(3);
                assertEquals(startedSequences.size(), previous.size());
                startedSequences.add(planned.getSequence());
                return generatedScreen(planned);
            });

        worker.generateScreens(CLAIM);

        assertEquals(List.of(1, 2), startedSequences);
        ArgumentCaptor<AiMockScreenSpecification> storedScreens = ArgumentCaptor.forClass(AiMockScreenSpecification.class);
        verify(jobService, org.mockito.Mockito.times(2))
            .storeGeneratedScreen(eq(51L), eq(CLAIM.leaseToken()), storedScreens.capture(), any());
        assertEquals(List.of(1, 2), storedScreens.getAllValues().stream()
            .map(AiMockScreenSpecification::getSequence).toList());
        InOrder order = inOrder(aiServiceClient, jobService);
        order.verify(aiServiceClient).generateMockScreen(eq(9L), eq(job.getPrompt()),
            argThat((AiMockScreenPlanItem screen) -> screen.getSequence() == 1), eq(List.of()));
        order.verify(jobService).storeGeneratedScreen(eq(51L), eq(CLAIM.leaseToken()),
            argThat(screen -> screen.getSequence() == 1), any());
        order.verify(aiServiceClient).generateMockScreen(eq(9L), eq(job.getPrompt()),
            argThat((AiMockScreenPlanItem screen) -> screen.getSequence() == 2),
            argThat((List<AiMockScreenSpecification> previous) -> previous.size() == 1));
        order.verify(jobService).storeGeneratedScreen(eq(51L), eq(CLAIM.leaseToken()),
            argThat(screen -> screen.getSequence() == 2), any());
        order.verify(jobService).markReadyForPdf(51L, CLAIM.leaseToken(), 2);
        }

    @Test
    void resumedGenerationSkipsAlreadyPersistedScreens() throws Exception {
        MockScreensJob job = processingJob(List.of(
            plannedScreen(1, "Account Details"), plannedScreen(2, "Review Details")));
        MockScreensScreenOutput existing = storedOutput(1, "Account Details");
        existing.setSpecificationJson(objectMapper.writeValueAsString(
            generatedScreen(plannedScreen(1, "Account Details")).getScreen()));
        when(jobService.getJobForScreenGeneration(51L, CLAIM.leaseToken())).thenReturn(job);
        when(jobService.getScreenOutputsForGeneration(51L, CLAIM.leaseToken())).thenReturn(List.of(existing));
        when(aiServiceClient.generateMockScreen(eq(9L), eq(job.getPrompt()), any(AiMockScreenPlanItem.class), anyList()))
            .thenAnswer(invocation -> generatedScreen(invocation.getArgument(2)));

        worker.generateScreens(CLAIM);

        verify(aiServiceClient).generateMockScreen(eq(9L), eq(job.getPrompt()),
            argThat((AiMockScreenPlanItem screen) -> screen.getSequence() == 2), anyList());
        verify(aiServiceClient, never()).generateMockScreen(eq(9L), eq(job.getPrompt()),
            argThat((AiMockScreenPlanItem screen) -> screen.getSequence() == 1), anyList());
        verify(jobService).storeGeneratedScreen(eq(51L), eq(CLAIM.leaseToken()),
            argThat((AiMockScreenSpecification screen) -> screen.getSequence() == 2), any());
        verify(jobService).markReadyForPdf(51L, CLAIM.leaseToken(), 2);
    }

        @Test
        void generationFailureStopsLaterScreensAndStoresFailedSequence() throws Exception {
        MockScreensJob job = processingJob(List.of(
            plannedScreen(1, "Account Details"),
            plannedScreen(2, "Review Details"),
            plannedScreen(3, "Confirmation")));
        when(jobService.getJobForScreenGeneration(51L, CLAIM.leaseToken())).thenReturn(job);
        when(jobService.getScreenOutputsForGeneration(51L, CLAIM.leaseToken())).thenReturn(List.of());
        List<Integer> startedSequences = new ArrayList<>();
        when(aiServiceClient.generateMockScreen(eq(9L), eq(job.getPrompt()), any(AiMockScreenPlanItem.class), anyList()))
            .thenAnswer(invocation -> {
                AiMockScreenPlanItem planned = invocation.getArgument(2);
                startedSequences.add(planned.getSequence());
                if (planned.getSequence() == 2) {
                throw new RuntimeException("provider internal response");
                }
                return generatedScreen(planned);
            });

        worker.generateScreens(CLAIM);

        assertEquals(List.of(1, 2), startedSequences);
        verify(jobService).storeGeneratedScreen(eq(51L), eq(CLAIM.leaseToken()),
            argThat(screen -> screen.getSequence() == 1), any());
        verify(jobService, never()).storeGeneratedScreen(eq(51L), eq(CLAIM.leaseToken()),
            argThat(screen -> screen.getSequence() == 2), any());
        verify(jobService, never()).markReadyForPdf(any(), any(), anyInt());
        verify(jobService).failJob(
            51L,
            CLAIM.leaseToken(),
            2,
            "SCREEN_GENERATION_FAILED",
            "We could not generate screen 2 from the selected BRD. Please retry the job.");
        }

        @Test
        void publicJobStatusResponseContainsNoScreenOutput() throws Exception {
        MockScreensJobResponse response = MockScreensJobResponse.builder()
            .jobId("e77c2dc5-e6bf-4d7c-9a8c-9053a9064438")
            .status(MockScreensJobStatus.PROCESSING)
            .build();

        String json = objectMapper.writeValueAsString(response);

        assertFalse(json.contains("screenPlan"));
        assertFalse(json.contains("specificationJson"));
        assertFalse(json.contains("components"));
    }

        @Test
        void successfulPdfGenerationPersistsOneFileFromAllOrderedOutputs() throws Exception {
        MockScreensJob job = processingJob(List.of(
            plannedScreen(1, "Account Details"),
            plannedScreen(2, "Review Details")));
        job.setStatus(MockScreensJobStatus.PDF_GENERATING);
        List<MockScreensScreenOutput> outputs = List.of(
            storedOutput(1, "Account Details"), storedOutput(2, "Review Details"));
        byte[] pdfBytes = new byte[]{37, 80, 68, 70};
        when(jobService.getJobForPdfGeneration(51L, CLAIM.leaseToken())).thenReturn(job);
        when(jobService.getScreenOutputsForPdf(51L, CLAIM.leaseToken())).thenReturn(outputs);
        when(pdfService.generateConsolidatedPdf(eq(outputs), anyList())).thenAnswer(invocation -> {
            List<AiMockScreenPlanItem> expectedPlan = invocation.getArgument(1);
            assertEquals(List.of(1, 2), expectedPlan.stream().map(AiMockScreenPlanItem::getSequence).toList());
            return pdfBytes;
        });

        worker.generatePdf(CLAIM);

        verify(pdfArtifactService).persistAndComplete(51L, CLAIM.leaseToken(), pdfBytes);
        verify(jobService, never()).failJob(any(), any(), any(), any());
        }

        @Test
        void pdfGenerationFailureDoesNotPersistArtifact() throws Exception {
        MockScreensJob job = processingJob(List.of(plannedScreen(1, "Account Details")));
        job.setStatus(MockScreensJobStatus.PDF_GENERATING);
        List<MockScreensScreenOutput> outputs = List.of(storedOutput(1, "Account Details"));
        when(jobService.getJobForPdfGeneration(51L, CLAIM.leaseToken())).thenReturn(job);
        when(jobService.getScreenOutputsForPdf(51L, CLAIM.leaseToken())).thenReturn(outputs);
        when(pdfService.generateConsolidatedPdf(eq(outputs), anyList()))
            .thenThrow(new IllegalStateException("sequence gap"));

        worker.generatePdf(CLAIM);

        verify(jobService).failJob(
            51L,
            CLAIM.leaseToken(),
            "PDF_GENERATION_FAILED",
            "We could not create the final Mock Screens PDF. Please retry the job.");
        verify(pdfArtifactService, never()).persistAndComplete(any(), any(), any());
        }

        @Test
        void pdfPersistenceFailureMarksJobFailedWithoutArtifactReference() throws Exception {
        MockScreensJob job = processingJob(List.of(plannedScreen(1, "Account Details")));
        job.setStatus(MockScreensJobStatus.PDF_GENERATING);
        List<MockScreensScreenOutput> outputs = List.of(storedOutput(1, "Account Details"));
        byte[] pdfBytes = new byte[]{37, 80, 68, 70};
        when(jobService.getJobForPdfGeneration(51L, CLAIM.leaseToken())).thenReturn(job);
        when(jobService.getScreenOutputsForPdf(51L, CLAIM.leaseToken())).thenReturn(outputs);
        when(pdfService.generateConsolidatedPdf(eq(outputs), anyList())).thenReturn(pdfBytes);
        org.mockito.Mockito.doThrow(new IllegalStateException("storage unavailable"))
            .when(pdfArtifactService).persistAndComplete(51L, CLAIM.leaseToken(), pdfBytes);

        worker.generatePdf(CLAIM);

        verify(jobService).failJob(
            51L,
            CLAIM.leaseToken(),
            "PDF_GENERATION_FAILED",
            "We could not create the final Mock Screens PDF. Please retry the job.");
        }

    @Test
    void planningFailureMarksJobFailedWithSafeMessage() {
        when(jobService.getClaimedJobForPlanning(51L, CLAIM.leaseToken())).thenReturn(processingJob());
        when(aiServiceClient.planMockScreens(9L, "Create the onboarding flow"))
                .thenThrow(new RuntimeException("provider response contains internal details"));

        worker.planJob(CLAIM);

        verify(jobService).failJob(
                51L,
                CLAIM.leaseToken(),
                "SCREEN_PLANNING_FAILED",
                "We could not create a screen plan from the selected BRD. Please retry the job.");
        verify(jobService, never()).storeScreenPlan(any(), any(), any());
        assertTrue(submittedTasks.isEmpty());
    }

    private MockScreensJob processingJob() {
        MockScreensJob job = new MockScreensJob();
        job.setId(51L);
        job.setJobId("e77c2dc5-e6bf-4d7c-9a8c-9053a9064438");
        job.setProjectId(5L);
        job.setBrdId(9L);
        job.setPrompt("Create the onboarding flow");
        job.setStatus(MockScreensJobStatus.PROCESSING);
        return job;
    }

    private MockScreensJob processingJob(List<AiMockScreenPlanItem> screens) throws Exception {
        MockScreensJob job = processingJob();
        job.setScreenPlan(objectMapper.writeValueAsString(screens));
        return job;
    }

    private AiMockScreenPlanItem plannedScreen(int sequence, String name) {
        AiMockScreenPlanItem screen = new AiMockScreenPlanItem();
        screen.setSequence(sequence);
        screen.setScreenName(name);
        screen.setPurpose("Support the onboarding flow");
        screen.setRelevantRequirements(List.of("Capture and review user details"));
        return screen;
    }

    private MockScreensScreenOutput storedOutput(int sequence, String name) {
        MockScreensScreenOutput output = new MockScreensScreenOutput();
        output.setMockScreensJobId(51L);
        output.setSequence(sequence);
        output.setScreenName(name);
        output.setPurpose("Support the onboarding flow");
        output.setSpecificationJson("{}");
        return output;
    }

    private AiMockScreenGenerationResponse generatedScreen(AiMockScreenPlanItem planned) {
        AiMockScreenSpecification specification = new AiMockScreenSpecification();
        specification.setSequence(planned.getSequence());
        specification.setScreenName(planned.getScreenName());
        specification.setPurpose(planned.getPurpose());
        specification.setLayoutDescription("Layout for " + planned.getScreenName());
        AiMockScreenComponent component = new AiMockScreenComponent();
        component.setComponentType("text");
        component.setLabel(planned.getScreenName());
        specification.setComponents(List.of(component));
        AiMockScreenGenerationResponse response = new AiMockScreenGenerationResponse();
        response.setScreen(specification);
        return response;
    }
}