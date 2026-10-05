package com.example.copilot.service;

import com.example.copilot.entity.MockScreensJob;
import com.example.copilot.entity.MockScreensJobStatus;
import com.example.copilot.entity.MockScreensPdfArtifact;
import com.example.copilot.repository.MockScreensJobRepository;
import com.example.copilot.repository.MockScreensPdfArtifactRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import java.time.LocalDateTime;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class MockScreensPdfArtifactServiceTest {

    @Mock
    private MockScreensJobRepository jobRepository;

    @Mock
    private MockScreensPdfArtifactRepository artifactRepository;

    private MockScreensPdfArtifactService service;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
        service = new MockScreensPdfArtifactService(jobRepository, artifactRepository);
    }

    @Test
    void persistsFinalPdfMetadataAndCompletesJobWithReference() {
        MockScreensJob job = pdfGeneratingJob();
        byte[] bytes = new byte[]{37, 80, 68, 70, 45, 49};
        LocalDateTime createdAt = LocalDateTime.of(2026, 9, 30, 12, 0);
        job.setLeaseToken("pdf-lease");
        when(jobRepository.findByIdForUpdate(73L)).thenReturn(Optional.of(job));
        when(artifactRepository.saveAndFlush(any(MockScreensPdfArtifact.class))).thenAnswer(invocation -> {
            MockScreensPdfArtifact artifact = invocation.getArgument(0);
            artifact.setId(84L);
            artifact.setCreatedAt(createdAt);
            return artifact;
        });
        when(jobRepository.save(job)).thenReturn(job);

        MockScreensPdfArtifact artifact = service.persistAndComplete(73L, "pdf-lease", bytes);

        assertEquals(84L, artifact.getId());
        assertEquals(job.getJobId(), artifact.getJobId());
        assertEquals(5L, artifact.getProjectId());
        assertEquals(9L, artifact.getBrdId());
        assertEquals("Mock_Screens_" + job.getJobId() + ".pdf", artifact.getFileName());
        assertEquals("application/pdf", artifact.getContentType());
        assertEquals((long) bytes.length, artifact.getSizeBytes());
        assertEquals(createdAt, artifact.getCreatedAt());
        assertArrayEquals(bytes, artifact.getPdfData());
        assertEquals(84L, job.getPdfArtifactId());
        assertEquals(MockScreensJobStatus.COMPLETED, job.getStatus());

        ArgumentCaptor<MockScreensPdfArtifact> artifactCaptor = ArgumentCaptor.forClass(MockScreensPdfArtifact.class);
        verify(artifactRepository).saveAndFlush(artifactCaptor.capture());
        assertArrayEquals(bytes, artifactCaptor.getValue().getPdfData());
        verify(jobRepository).save(job);
    }

    @Test
    void emptyPdfIsNotPersistedAndJobIsNotCompleted() {
        MockScreensJob job = pdfGeneratingJob();
        job.setLeaseToken("pdf-lease");
        when(jobRepository.findByIdForUpdate(73L)).thenReturn(Optional.of(job));

        assertThrows(IllegalArgumentException.class,
            () -> service.persistAndComplete(73L, "pdf-lease", new byte[0]));

        verify(artifactRepository, never()).saveAndFlush(any());
        verify(jobRepository, never()).save(any());
    }

    @Test
    void artifactCannotBeReadBeforeJobCompletes() {
        MockScreensJob job = pdfGeneratingJob();
        job.setPdfArtifactId(84L);
        when(jobRepository.findByJobId(job.getJobId())).thenReturn(Optional.of(job));

        assertThrows(RuntimeException.class, () -> service.getCompletedArtifact(job.getJobId()));
        verify(artifactRepository, never()).findById(84L);
    }

    private MockScreensJob pdfGeneratingJob() {
        MockScreensJob job = new MockScreensJob();
        job.setId(73L);
        job.setJobId("e77c2dc5-e6bf-4d7c-9a8c-9053a9064438");
        job.setProjectId(5L);
        job.setBrdId(9L);
        job.setStatus(MockScreensJobStatus.PDF_GENERATING);
        job.setLeaseToken("pdf-lease");
        return job;
    }
}
