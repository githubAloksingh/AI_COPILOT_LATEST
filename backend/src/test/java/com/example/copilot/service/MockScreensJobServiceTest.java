package com.example.copilot.service;

import com.example.copilot.dto.MockScreensJobResponse;
import com.example.copilot.dto.MockScreensJobClaim;
import com.example.copilot.dto.MockScreensStartRequest;
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
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import org.springframework.dao.DataIntegrityViolationException;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class MockScreensJobServiceTest {

    @Mock
    private ProjectRepository projectRepository;

    @Mock
    private DocumentRepository documentRepository;

    @Mock
    private MockScreensJobRepository jobRepository;

    @Mock
    private MockScreensScreenOutputRepository screenOutputRepository;

    @Mock
    private MockScreensPdfArtifactRepository pdfArtifactRepository;

    private MockScreensJobService service;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
        service = new MockScreensJobService(
            projectRepository, documentRepository, jobRepository, screenOutputRepository, pdfArtifactRepository);
    }

    @Test
    void createJobPersistsQueuedJobForCompletedBrdInProject() {
        when(projectRepository.existsById(5L)).thenReturn(true);
        when(documentRepository.findById(9L)).thenReturn(Optional.of(completedBrd(5L)));
        when(jobRepository.saveAndFlush(any(MockScreensJob.class))).thenAnswer(invocation -> invocation.getArgument(0));

        MockScreensJobResponse response = service.createJob(
            new MockScreensStartRequest(5L, 9L, "  Design the main flow  ", "key-001"));

        assertEquals(MockScreensJobStatus.QUEUED, response.getStatus());
        assertEquals(5L, response.getProjectId());
        assertEquals(9L, response.getBrdId());
        assertTrue(response.getJobId().matches("[0-9a-f-]{36}"));
        ArgumentCaptor<MockScreensJob> jobCaptor = ArgumentCaptor.forClass(MockScreensJob.class);
        verify(jobRepository).saveAndFlush(jobCaptor.capture());
        assertEquals("Design the main flow", jobCaptor.getValue().getPrompt());
        assertEquals(response.getJobId(), jobCaptor.getValue().getJobId());
        assertEquals("key-001", jobCaptor.getValue().getIdempotencyKey());
        }

        @Test
        void createJobReturnsExistingJobForSameIdempotentRequest() {
        MockScreensJob existing = queuedJob("key-001");
        when(jobRepository.findByIdempotencyKey("key-001")).thenReturn(Optional.of(existing));

        MockScreensJobResponse response = service.createJob(
            new MockScreensStartRequest(5L, 9L, "Design the main flow", "key-001"));

        assertEquals(existing.getJobId(), response.getJobId());
        verify(jobRepository, org.mockito.Mockito.never()).saveAndFlush(any());
        }

        @Test
        void createJobRejectsReusingKeyForDifferentRequest() {
        when(jobRepository.findByIdempotencyKey("key-001"))
            .thenReturn(Optional.of(queuedJob("key-001")));

        MockScreensJobException exception = assertThrows(
            MockScreensJobException.class,
            () -> service.createJob(new MockScreensStartRequest(5L, 9L, "Different prompt", "key-001")));

        assertEquals("IDEMPOTENCY_KEY_REUSED", exception.getCode());
        }

        @Test
        void concurrentIdempotencyInsertReturnsTheWinningJob() {
        MockScreensJob winner = queuedJob("key-001");
        when(projectRepository.existsById(5L)).thenReturn(true);
        when(documentRepository.findById(9L)).thenReturn(Optional.of(completedBrd(5L)));
        when(jobRepository.saveAndFlush(any(MockScreensJob.class)))
            .thenThrow(new DataIntegrityViolationException("unique idempotency key"));
        when(jobRepository.findByIdempotencyKey("key-001"))
            .thenReturn(Optional.empty(), Optional.of(winner));

        MockScreensJobResponse response = service.createJob(
            new MockScreensStartRequest(5L, 9L, "Design the main flow", "key-001"));

        assertEquals(winner.getJobId(), response.getJobId());
    }

    @Test
    void createJobRejectsBrdFromAnotherProject() {
        when(projectRepository.existsById(5L)).thenReturn(true);
        when(documentRepository.findById(9L)).thenReturn(Optional.of(completedBrd(6L)));

        MockScreensJobException exception = assertThrows(
                MockScreensJobException.class,
                () -> service.createJob(new MockScreensStartRequest(5L, 9L, "Create screens", "key-002")));

        assertEquals("BRD_PROJECT_MISMATCH", exception.getCode());
    }

    @Test
    void createJobRejectsBrdThatHasNotCompletedIngestion() {
        Document document = completedBrd(5L);
        document.setStatus("PROCESSING");
        when(projectRepository.existsById(5L)).thenReturn(true);
        when(documentRepository.findById(9L)).thenReturn(Optional.of(document));

        MockScreensJobException exception = assertThrows(
                MockScreensJobException.class,
                () -> service.createJob(new MockScreensStartRequest(5L, 9L, "Create screens", "key-003")));

        assertEquals("BRD_NOT_COMPLETED", exception.getCode());
    }

    @Test
    void createJobRejectsBlankPromptBeforeDatabaseAccess() {
        MockScreensJobException exception = assertThrows(
                MockScreensJobException.class,
                () -> service.createJob(new MockScreensStartRequest(5L, 9L, "  ", "key-004")));

        assertEquals("PROMPT_REQUIRED", exception.getCode());
    }

    @Test
    void getJobStatusReturnsStoredStatusAndErrorDetails() {
        MockScreensJob job = new MockScreensJob();
        job.setJobId("e77c2dc5-e6bf-4d7c-9a8c-9053a9064438");
        job.setProjectId(5L);
        job.setBrdId(9L);
        job.setStatus(MockScreensJobStatus.FAILED);
        job.setErrorCode("GENERATION_FAILED");
        job.setErrorMessage("A later worker reported failure.");
        when(jobRepository.findByJobId(job.getJobId())).thenReturn(Optional.of(job));

        MockScreensJobResponse response = service.getJobStatus(job.getJobId());

        assertEquals(MockScreensJobStatus.FAILED, response.getStatus());
        assertEquals("GENERATION_FAILED", response.getErrorCode());
        assertEquals("A later worker reported failure.", response.getErrorMessage());
        verify(jobRepository).findByJobId(job.getJobId());
    }

    @Test
    void completedJobStatusIncludesOnlyFinalPdfMetadata() {
        MockScreensJob job = new MockScreensJob();
        job.setJobId("e77c2dc5-e6bf-4d7c-9a8c-9053a9064438");
        job.setProjectId(5L);
        job.setBrdId(9L);
        job.setStatus(MockScreensJobStatus.COMPLETED);
        job.setPdfArtifactId(84L);
        MockScreensPdfArtifact artifact = new MockScreensPdfArtifact();
        artifact.setId(84L);
        artifact.setFileName("Mock_Screens_final.pdf");
        artifact.setContentType("application/pdf");
        artifact.setSizeBytes(512L);
        artifact.setCreatedAt(java.time.LocalDateTime.of(2026, 9, 30, 12, 0));
        when(jobRepository.findByJobId(job.getJobId())).thenReturn(Optional.of(job));
        when(pdfArtifactRepository.findById(84L)).thenReturn(Optional.of(artifact));

        MockScreensJobResponse response = service.getJobStatus(job.getJobId());

        assertEquals(MockScreensJobStatus.COMPLETED, response.getStatus());
        assertEquals(84L, response.getPdfArtifactId());
        assertEquals("Mock_Screens_final.pdf", response.getPdfFileName());
        assertEquals("application/pdf", response.getPdfContentType());
        assertEquals(512L, response.getPdfSizeBytes());
        assertEquals("/api/copilot/mock-screens/jobs/" + job.getJobId() + "/pdf", response.getPdfPreviewUrl());
        assertEquals("/api/copilot/mock-screens/jobs/" + job.getJobId() + "/pdf/download", response.getPdfDownloadUrl());
    }

    @Test
    void claimNextQueuedJobMovesJobToProcessing() {
        MockScreensJob job = new MockScreensJob();
        job.setId(73L);
        job.setStatus(MockScreensJobStatus.QUEUED);
        when(jobRepository.findFirstByStatusOrderByCreatedAtAscIdAsc(MockScreensJobStatus.QUEUED))
                .thenReturn(Optional.of(job));
        when(jobRepository.databaseNow()).thenReturn(java.time.LocalDateTime.now());
        when(jobRepository.saveAndFlush(job)).thenReturn(job);

        Optional<MockScreensJobClaim> claimed = service.claimNextQueuedJob();

        assertEquals(73L, claimed.orElseThrow().id());
        assertEquals(job.getLeaseToken(), claimed.orElseThrow().leaseToken());
        assertEquals(MockScreensJobStatus.PROCESSING, job.getStatus());
        assertTrue(job.getLeaseUntil().isAfter(java.time.LocalDateTime.now()));
        verify(jobRepository).saveAndFlush(job);
    }

    @Test
    void markReadyForPdfRequiresAndPreservesEveryOrderedScreen() {
        MockScreensJob job = new MockScreensJob();
        job.setId(73L);
        job.setStatus(MockScreensJobStatus.PROCESSING);
        MockScreensScreenOutput first = output(1);
        MockScreensScreenOutput second = output(2);
        job.setLeaseToken("active-lease");
        when(jobRepository.findByIdForUpdate(73L)).thenReturn(Optional.of(job));
        when(screenOutputRepository.findByMockScreensJobIdOrderBySequenceAsc(73L))
                .thenReturn(List.of(first, second));
        when(jobRepository.save(job)).thenReturn(job);

        service.markReadyForPdf(73L, "active-lease", 2);

        assertEquals(MockScreensJobStatus.READY_FOR_PDF, job.getStatus());
        verify(screenOutputRepository).findByMockScreensJobIdOrderBySequenceAsc(73L);
        verify(jobRepository).save(job);
    }

    @Test
    void markReadyForPdfRejectsMissingScreenOutput() {
        MockScreensJob job = new MockScreensJob();
        job.setId(73L);
        job.setStatus(MockScreensJobStatus.PROCESSING);
        job.setLeaseToken("active-lease");
        when(jobRepository.findByIdForUpdate(73L)).thenReturn(Optional.of(job));
        when(screenOutputRepository.findByMockScreensJobIdOrderBySequenceAsc(73L))
                .thenReturn(List.of(output(1)));

        assertThrows(IllegalStateException.class, () -> service.markReadyForPdf(73L, "active-lease", 2));
        assertEquals(MockScreensJobStatus.PROCESSING, job.getStatus());
        verify(jobRepository, never()).save(job);
    }

    @Test
    void failJobStoresFailedScreenSequence() {
        MockScreensJob job = new MockScreensJob();
        job.setId(73L);
        job.setStatus(MockScreensJobStatus.PROCESSING);
        job.setLeaseToken("active-lease");
        when(jobRepository.findByIdForUpdate(73L)).thenReturn(Optional.of(job));
        when(jobRepository.save(job)).thenReturn(job);

        service.failJob(73L, "active-lease", 2, "SCREEN_GENERATION_FAILED", "Screen 2 could not be generated.");

        assertEquals(MockScreensJobStatus.FAILED, job.getStatus());
        assertEquals(2, job.getFailedSequence());
        assertEquals("Screen 2 could not be generated.", job.getErrorMessage());
    }

    @Test
    void expiredProcessingAndPdfLeasesReturnToTheirSafeQueues() {
        MockScreensJob processing = leasedJob(MockScreensJobStatus.PROCESSING, "processing-token");
        MockScreensJob pdfGenerating = leasedJob(MockScreensJobStatus.PDF_GENERATING, "pdf-token");
        when(jobRepository.findExpiredLeases(any(), any(), any())).thenReturn(List.of(processing, pdfGenerating));
        when(jobRepository.databaseNow()).thenReturn(java.time.LocalDateTime.now());

        assertEquals(2, service.recoverExpiredJobs());

        assertEquals(MockScreensJobStatus.QUEUED, processing.getStatus());
        assertEquals(MockScreensJobStatus.READY_FOR_PDF, pdfGenerating.getStatus());
        assertEquals(null, processing.getLeaseToken());
        assertEquals(null, pdfGenerating.getLeaseToken());
    }

    @Test
    void staleLeaseCannotFailAJobAfterItHasBeenReclaimed() {
        MockScreensJob job = leasedJob(MockScreensJobStatus.PROCESSING, "new-token");
        when(jobRepository.findByIdForUpdate(73L)).thenReturn(Optional.of(job));

        service.failJob(73L, "old-token", "SCREEN_GENERATION_FAILED", "Failed");

        assertEquals(MockScreensJobStatus.PROCESSING, job.getStatus());
        verify(jobRepository, never()).save(job);
    }

    private Document completedBrd(Long projectId) {
        Document document = new Document();
        document.setProjectId(projectId);
        document.setFileName("Requirements.pdf");
        document.setFileType("BRD");
        document.setStatus("COMPLETED");
        return document;
    }

    private MockScreensJob queuedJob(String idempotencyKey) {
        MockScreensJob job = new MockScreensJob();
        job.setJobId("e77c2dc5-e6bf-4d7c-9a8c-9053a9064438");
        job.setProjectId(5L);
        job.setBrdId(9L);
        job.setPrompt("Design the main flow");
        job.setIdempotencyKey(idempotencyKey);
        job.setStatus(MockScreensJobStatus.QUEUED);
        return job;
    }

    private MockScreensJob leasedJob(MockScreensJobStatus status, String leaseToken) {
        MockScreensJob job = new MockScreensJob();
        job.setId(73L);
        job.setStatus(status);
        job.setLeaseToken(leaseToken);
        job.setLeaseUntil(java.time.LocalDateTime.now().minusMinutes(5));
        return job;
    }

    private MockScreensScreenOutput output(int sequence) {
        MockScreensScreenOutput output = new MockScreensScreenOutput();
        output.setMockScreensJobId(73L);
        output.setSequence(sequence);
        output.setScreenName("Screen " + sequence);
        output.setPurpose("Purpose " + sequence);
        output.setSpecificationJson("{\"sequence\":" + sequence + "}");
        return output;
    }
}