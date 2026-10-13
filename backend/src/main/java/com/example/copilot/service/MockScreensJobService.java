package com.example.copilot.service;

import com.example.copilot.dto.MockScreensJobResponse;
import com.example.copilot.dto.MockScreensJobClaim;
import com.example.copilot.dto.MockScreensStartRequest;
import com.example.copilot.dto.ai.AiMockScreenSpecification;
import com.example.copilot.entity.Document;
import com.example.copilot.entity.MockScreensJob;
import com.example.copilot.entity.MockScreensJobStatus;
import com.example.copilot.entity.MockScreensPdfArtifact;
import com.example.copilot.entity.MockScreensScreenOutput;
import com.example.copilot.exception.MockScreensJobException;
import com.example.copilot.repository.DocumentRepository;
import com.example.copilot.repository.MockScreensJobRepository;
import com.example.copilot.repository.MockScreensPdfArtifactRepository;
import com.example.copilot.repository.MockScreensScreenOutputRepository;
import com.example.copilot.repository.ProjectRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Locale;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class MockScreensJobService {

    private final ProjectRepository projectRepository;
    private final DocumentRepository documentRepository;
    private final MockScreensJobRepository jobRepository;
    private final MockScreensScreenOutputRepository screenOutputRepository;
    private final MockScreensPdfArtifactRepository pdfArtifactRepository;

    public MockScreensJobResponse createJob(MockScreensStartRequest request) {
        validateRequest(request);

        if (!projectRepository.existsById(request.getProjectId())) {
            throw new MockScreensJobException(HttpStatus.NOT_FOUND, "PROJECT_NOT_FOUND", "Project was not found.");
        }

        Document brd = documentRepository.findById(request.getBrdId())
                .orElseThrow(() -> new MockScreensJobException(
                        HttpStatus.NOT_FOUND, "BRD_NOT_FOUND", "BRD document was not found."));
        validateBrd(request.getProjectId(), brd);

        MockScreensJob job = new MockScreensJob();
        job.setJobId(UUID.randomUUID().toString());
        job.setProjectId(request.getProjectId());
        job.setBrdId(request.getBrdId());
        job.setIdempotencyKey(UUID.randomUUID().toString());
        job.setPrompt("");
        job.setStatus(MockScreensJobStatus.QUEUED);

        try {
            return toResponse(jobRepository.saveAndFlush(job));
        } catch (DataIntegrityViolationException exception) {
            throw exception;
        }
    }

    @Transactional(readOnly = true)
    public MockScreensJobResponse getJobStatus(String jobId) {
        String normalizedJobId;
        try {
            normalizedJobId = UUID.fromString(jobId).toString();
        } catch (IllegalArgumentException | NullPointerException ex) {
            throw new MockScreensJobException(HttpStatus.BAD_REQUEST, "INVALID_JOB_ID", "Job ID must be a valid UUID.");
        }

        MockScreensJob job = jobRepository.findByJobId(normalizedJobId)
                .orElseThrow(() -> new MockScreensJobException(
                        HttpStatus.NOT_FOUND, "JOB_NOT_FOUND", "Mock Screens job was not found."));
        return toResponse(job);
    }

    @Transactional
    public Optional<MockScreensJobClaim> claimNextQueuedJob() {
        return jobRepository.findFirstByStatusOrderByCreatedAtAscIdAsc(MockScreensJobStatus.QUEUED)
                .map(job -> {
                    return claim(job, MockScreensJobStatus.PROCESSING);
                });
    }

    @Transactional
    public Optional<MockScreensJobClaim> claimNextPdfReadyJob() {
        return jobRepository.findFirstByStatusOrderByCreatedAtAscIdAsc(MockScreensJobStatus.READY_FOR_PDF)
                .map(job -> claim(job, MockScreensJobStatus.PDF_GENERATING));
    }

    @Transactional
    public MockScreensJob getClaimedJobForPlanning(Long id, String leaseToken) {
        MockScreensJob job = requireClaimedJob(id, leaseToken, MockScreensJobStatus.PROCESSING);

        Document brd = documentRepository.findById(job.getBrdId())
                .orElseThrow(() -> new MockScreensJobException(
                        HttpStatus.NOT_FOUND, "BRD_NOT_FOUND", "The selected BRD is no longer available."));
        validateBrd(job.getProjectId(), brd);
        return job;
    }

    @Transactional
    public MockScreensJob getJobForScreenGeneration(Long id, String leaseToken) {
        MockScreensJob job = requireClaimedJob(id, leaseToken, MockScreensJobStatus.PROCESSING);
        if (job.getScreenPlan() == null || job.getScreenPlan().isBlank()) {
            throw new MockScreensJobException(
                    HttpStatus.CONFLICT, "SCREEN_PLAN_NOT_READY", "The screen plan is not ready for generation.");
        }
        return job;
    }

    @Transactional
    public MockScreensJob getJobForPdfGeneration(Long id, String leaseToken) {
        return requireClaimedJob(id, leaseToken, MockScreensJobStatus.PDF_GENERATING);
    }

    @Transactional
    public List<MockScreensScreenOutput> getScreenOutputsForPdf(Long id, String leaseToken) {
        requireClaimedJob(id, leaseToken, MockScreensJobStatus.PDF_GENERATING);
        return screenOutputRepository.findByMockScreensJobIdOrderBySequenceAsc(id);
    }

    @Transactional
    public List<MockScreensScreenOutput> getScreenOutputsForGeneration(Long id, String leaseToken) {
        requireClaimedJob(id, leaseToken, MockScreensJobStatus.PROCESSING);
        return screenOutputRepository.findByMockScreensJobIdOrderBySequenceAsc(id);
    }

    @Transactional
    public void storeGeneratedScreen(
            Long id, String leaseToken, AiMockScreenSpecification screen, String specificationJson) {
        requireClaimedJob(id, leaseToken, MockScreensJobStatus.PROCESSING);
        if (screen == null || specificationJson == null || specificationJson.isBlank()) {
            throw new IllegalArgumentException("A valid generated screen is required.");
        }

        long completedCount = screenOutputRepository.countByMockScreensJobId(id);
        if (screen.getSequence() != completedCount + 1) {
            throw new IllegalStateException("Generated screens must be saved in sequence.");
        }

        MockScreensScreenOutput output = new MockScreensScreenOutput();
        output.setMockScreensJobId(id);
        output.setSequence(screen.getSequence());
        output.setScreenName(screen.getScreenName());
        output.setPurpose(screen.getPurpose());
        output.setSpecificationJson(specificationJson);
        screenOutputRepository.save(output);
    }

    @Transactional
    public void markReadyForPdf(Long id, String leaseToken, int plannedScreenCount) {
        MockScreensJob job = requireClaimedJob(id, leaseToken, MockScreensJobStatus.PROCESSING);

        List<MockScreensScreenOutput> outputs = screenOutputRepository
                .findByMockScreensJobIdOrderBySequenceAsc(id);
        if (outputs.size() != plannedScreenCount) {
            throw new IllegalStateException("Not all planned screens have been generated.");
        }
        for (int index = 0; index < outputs.size(); index++) {
            if (outputs.get(index).getSequence() != index + 1) {
                throw new IllegalStateException("Generated screen sequence is incomplete.");
            }
        }

        job.setStatus(MockScreensJobStatus.READY_FOR_PDF);
        job.setErrorCode(null);
        job.setErrorMessage(null);
        job.setFailedSequence(null);
        clearLease(job);
        jobRepository.save(job);
    }

    @Transactional
    public void storeScreenPlan(Long id, String leaseToken, String screenPlan) {
        if (screenPlan == null || screenPlan.isBlank()) {
            throw new IllegalArgumentException("A non-empty screen plan is required.");
        }
        MockScreensJob job = requireClaimedJob(id, leaseToken, MockScreensJobStatus.PROCESSING);
        job.setScreenPlan(screenPlan);
        jobRepository.save(job);
    }

    @Transactional
    public void failJob(Long id, String leaseToken, String errorCode, String userSafeMessage) {
        failJobRecord(id, leaseToken, null, errorCode, userSafeMessage);
    }

    @Transactional
    public void failJob(Long id, String leaseToken, Integer failedSequence, String errorCode, String userSafeMessage) {
        failJobRecord(id, leaseToken, failedSequence, errorCode, userSafeMessage);
    }

    @Transactional
    public boolean renewLease(MockScreensJobClaim claim) {
        java.time.LocalDateTime databaseNow = jobRepository.databaseNow();
        return jobRepository.extendLease(
                claim.id(), claim.leaseToken(),
                List.of(MockScreensJobStatus.PROCESSING, MockScreensJobStatus.PDF_GENERATING),
            databaseNow.plusMinutes(2)) == 1;
    }

    @Transactional
    public int recoverExpiredJobs() {
        List<MockScreensJob> staleJobs = jobRepository.findExpiredLeases(
                List.of(MockScreensJobStatus.PROCESSING, MockScreensJobStatus.PDF_GENERATING),
                jobRepository.databaseNow(), PageRequest.of(0, 50));
        for (MockScreensJob job : staleJobs) {
            job.setStatus(job.getStatus() == MockScreensJobStatus.PROCESSING
                    ? MockScreensJobStatus.QUEUED : MockScreensJobStatus.READY_FOR_PDF);
            clearLease(job);
        }
        return staleJobs.size();
    }

    private MockScreensJobClaim claim(MockScreensJob job, MockScreensJobStatus status) {
        java.time.LocalDateTime databaseNow = jobRepository.databaseNow();
        job.setStatus(status);
        job.setLeaseToken(UUID.randomUUID().toString());
        job.setLeaseUntil(databaseNow.plusMinutes(2));
        job.setErrorCode(null);
        job.setErrorMessage(null);
        job.setFailedSequence(null);
        MockScreensJob saved = jobRepository.saveAndFlush(job);
        return new MockScreensJobClaim(saved.getId(), saved.getLeaseToken());
    }

    private MockScreensJob requireClaimedJob(Long id, String leaseToken, MockScreensJobStatus expectedStatus) {
        MockScreensJob job = jobRepository.findByIdForUpdate(id)
                .orElseThrow(() -> new MockScreensJobException(
                        HttpStatus.NOT_FOUND, "JOB_NOT_FOUND", "Mock Screens job was not found."));
        if (job.getStatus() != expectedStatus || !Objects.equals(job.getLeaseToken(), leaseToken)) {
            throw new MockScreensJobException(
                    HttpStatus.CONFLICT, "JOB_LEASE_LOST", "Mock Screens job lease is no longer active.");
        }
        return job;
    }

    private void failJobRecord(Long id, String leaseToken, Integer failedSequence,
                               String errorCode, String userSafeMessage) {
        jobRepository.findByIdForUpdate(id).ifPresent(job -> {
            boolean validLease = Objects.equals(job.getLeaseToken(), leaseToken)
                    && (job.getStatus() == MockScreensJobStatus.PROCESSING
                    || job.getStatus() == MockScreensJobStatus.PDF_GENERATING);
            if (validLease) {
                job.setStatus(MockScreensJobStatus.FAILED);
                job.setErrorCode(errorCode);
                job.setErrorMessage(userSafeMessage);
                job.setFailedSequence(failedSequence);
                clearLease(job);
                jobRepository.save(job);
            }
        });
    }

    private void clearLease(MockScreensJob job) {
        job.setLeaseToken(null);
        job.setLeaseUntil(null);
    }

    private void validateRequest(MockScreensStartRequest request) {
        if (request == null) {
            throw new MockScreensJobException(HttpStatus.BAD_REQUEST, "INVALID_REQUEST", "Request body is required.");
        }
        if (request.getProjectId() == null || request.getProjectId() <= 0) {
            throw new MockScreensJobException(HttpStatus.BAD_REQUEST, "INVALID_PROJECT_ID", "A valid projectId is required.");
        }
        if (request.getBrdId() == null || request.getBrdId() <= 0) {
            throw new MockScreensJobException(HttpStatus.BAD_REQUEST, "INVALID_BRD_ID", "A valid brdId is required.");
        }
    }

    private void validateBrd(Long projectId, Document brd) {
        if (!Objects.equals(brd.getProjectId(), projectId)) {
            throw new MockScreensJobException(
                    HttpStatus.CONFLICT, "BRD_PROJECT_MISMATCH", "The BRD does not belong to the selected project.");
        }
        if (!isBrdDocument(brd)) {
            throw new MockScreensJobException(
                    HttpStatus.BAD_REQUEST, "INVALID_BRD", "The selected document is not a BRD or PDF.");
        }
        if (!"COMPLETED".equalsIgnoreCase(brd.getStatus())) {
            throw new MockScreensJobException(
                    HttpStatus.CONFLICT, "BRD_NOT_COMPLETED", "The BRD must finish ingestion before planning.");
        }
    }

    private boolean isBrdDocument(Document document) {
        String fileType = document.getFileType() == null
                ? ""
                : document.getFileType().trim().toUpperCase(Locale.ROOT);
        String fileName = document.getFileName() == null
                ? ""
                : document.getFileName().trim().toLowerCase(Locale.ROOT);
        return "BRD".equals(fileType)
            || "APPLICATION/PDF".equals(fileType)
            || fileName.endsWith(".pdf");
    }

    private MockScreensJobResponse toResponse(MockScreensJob job) {
        String statusUrl = "/api/copilot/mock-screens/jobs/" + job.getJobId();
        MockScreensJobResponse.MockScreensJobResponseBuilder response = MockScreensJobResponse.builder()
                .jobId(job.getJobId())
                .projectId(job.getProjectId())
                .brdId(job.getBrdId())
                .status(job.getStatus())
                .errorCode(job.getErrorCode())
                .errorMessage(job.getErrorMessage())
                .failedSequence(job.getFailedSequence())
                .statusUrl(statusUrl)
                .createdAt(job.getCreatedAt())
            .updatedAt(job.getUpdatedAt());
        if (job.getStatus() == MockScreensJobStatus.COMPLETED && job.getPdfArtifactId() != null) {
            pdfArtifactRepository.findById(job.getPdfArtifactId()).ifPresent(artifact -> response
                .pdfArtifactId(artifact.getId())
                .pdfFileName(artifact.getFileName())
                .pdfContentType(artifact.getContentType())
                .pdfSizeBytes(artifact.getSizeBytes())
                .pdfCreatedAt(artifact.getCreatedAt())
                .pdfPreviewUrl(statusUrl + "/pdf")
                .pdfDownloadUrl(statusUrl + "/pdf/download"));
        }
        return response.build();
    }
}