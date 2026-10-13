package com.example.copilot.service;

import com.example.copilot.entity.MockScreensJob;
import com.example.copilot.entity.MockScreensJobStatus;
import com.example.copilot.entity.MockScreensPdfArtifact;
import com.example.copilot.exception.MockScreensJobException;
import com.example.copilot.repository.MockScreensJobRepository;
import com.example.copilot.repository.MockScreensPdfArtifactRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

@Service
@RequiredArgsConstructor
public class MockScreensPdfArtifactService {

    private static final String PDF_CONTENT_TYPE = "application/pdf";

    private final MockScreensJobRepository jobRepository;
    private final MockScreensPdfArtifactRepository artifactRepository;

    @Transactional
    public MockScreensPdfArtifact persistAndComplete(Long jobId, String leaseToken, byte[] pdfBytes) {
        if (pdfBytes == null || pdfBytes.length == 0) {
            throw new IllegalArgumentException("A non-empty PDF is required.");
        }

        MockScreensJob job = jobRepository.findByIdForUpdate(jobId)
                .orElseThrow(() -> new MockScreensJobException(
                        HttpStatus.NOT_FOUND, "JOB_NOT_FOUND", "Mock Screens job was not found."));
        if (job.getStatus() != MockScreensJobStatus.PDF_GENERATING
            || !java.util.Objects.equals(job.getLeaseToken(), leaseToken)
            || job.getPdfArtifactId() != null) {
            throw new MockScreensJobException(
                    HttpStatus.CONFLICT, "JOB_NOT_GENERATING_PDF", "Mock Screens job is not ready to store a PDF.");
        }

        MockScreensPdfArtifact artifact = new MockScreensPdfArtifact();
        artifact.setMockScreensJobId(job.getId());
        artifact.setJobId(job.getJobId());
        artifact.setProjectId(job.getProjectId());
        artifact.setBrdId(job.getBrdId());
        artifact.setFileName("Mock_Screens_" + job.getJobId() + ".pdf");
        artifact.setContentType(PDF_CONTENT_TYPE);
        artifact.setSizeBytes((long) pdfBytes.length);
        artifact.setPdfData(pdfBytes);

        MockScreensPdfArtifact savedArtifact = artifactRepository.saveAndFlush(artifact);
        job.setPdfArtifactId(savedArtifact.getId());
        job.setStatus(MockScreensJobStatus.COMPLETED);
        job.setErrorCode(null);
        job.setErrorMessage(null);
        job.setFailedSequence(null);
        job.setLeaseToken(null);
        job.setLeaseUntil(null);
        jobRepository.save(job);
        return savedArtifact;
    }

    @Transactional(readOnly = true)
    public MockScreensPdfArtifact getCompletedArtifact(String jobId) {
        String normalizedJobId;
        try {
            normalizedJobId = UUID.fromString(jobId).toString();
        } catch (IllegalArgumentException | NullPointerException exception) {
            throw new MockScreensJobException(HttpStatus.BAD_REQUEST, "INVALID_JOB_ID", "Job ID must be a valid UUID.");
        }

        MockScreensJob job = jobRepository.findByJobId(normalizedJobId)
                .orElseThrow(() -> new MockScreensJobException(
                        HttpStatus.NOT_FOUND, "JOB_NOT_FOUND", "Mock Screens job was not found."));
        if (job.getStatus() != MockScreensJobStatus.COMPLETED || job.getPdfArtifactId() == null) {
            throw new MockScreensJobException(
                    HttpStatus.CONFLICT, "PDF_NOT_READY", "The final Mock Screens PDF is not available yet.");
        }

        return artifactRepository.findById(job.getPdfArtifactId())
                .orElseThrow(() -> new MockScreensJobException(
                        HttpStatus.NOT_FOUND, "PDF_NOT_FOUND", "The final Mock Screens PDF was not found."));
    }
}