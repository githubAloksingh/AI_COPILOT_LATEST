package com.example.copilot.controller;

import com.example.copilot.dto.ApiResponse;
import com.example.copilot.dto.MockScreensJobResponse;
import com.example.copilot.dto.MockScreensStartRequest;
import com.example.copilot.exception.MockScreensJobException;
import com.example.copilot.entity.MockScreensPdfArtifact;
import com.example.copilot.service.MockScreensJobService;
import com.example.copilot.service.MockScreensPdfArtifactService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;

@RestController
@RequestMapping("/api/copilot/mock-screens/jobs")
@RequiredArgsConstructor
public class MockScreensJobController {

    private final MockScreensJobService jobService;
    private final MockScreensPdfArtifactService pdfArtifactService;

    @PostMapping
    public ResponseEntity<ApiResponse<MockScreensJobResponse>> createJob(
            @RequestBody MockScreensStartRequest request) {
        MockScreensJobResponse job = jobService.createJob(request);
        return ResponseEntity.status(HttpStatus.ACCEPTED)
            .location(URI.create(job.getStatusUrl()))
                .body(ApiResponse.success(job, "Mock Screens job queued."));
    }

    @GetMapping("/{jobId}")
    public ApiResponse<MockScreensJobResponse> getJobStatus(@PathVariable String jobId) {
        return ApiResponse.success(jobService.getJobStatus(jobId), "Mock Screens job status retrieved.");
    }

    @GetMapping(value = "/{jobId}/pdf", produces = MediaType.APPLICATION_PDF_VALUE)
    public ResponseEntity<byte[]> previewPdf(@PathVariable String jobId) {
        return pdfResponse(pdfArtifactService.getCompletedArtifact(jobId), false);
    }

    @GetMapping(value = "/{jobId}/pdf/download", produces = MediaType.APPLICATION_PDF_VALUE)
    public ResponseEntity<byte[]> downloadPdf(@PathVariable String jobId) {
        return pdfResponse(pdfArtifactService.getCompletedArtifact(jobId), true);
    }

    private ResponseEntity<byte[]> pdfResponse(MockScreensPdfArtifact artifact, boolean attachment) {
        String disposition = attachment ? "attachment" : "inline";
        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_PDF)
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        disposition + "; filename=\"" + artifact.getFileName().replace("\"", "") + "\"")
                .header(HttpHeaders.CONTENT_LENGTH, String.valueOf(artifact.getSizeBytes()))
                .body(artifact.getPdfData());
    }

    @ExceptionHandler(MockScreensJobException.class)
    public ResponseEntity<ApiResponse<Void>> handleMockScreensJobException(MockScreensJobException exception) {
        return ResponseEntity.status(exception.getHttpStatus())
                .body(ApiResponse.error(exception.getCode(), exception.getMessage()));
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ApiResponse<Void>> handleMalformedRequest(HttpMessageNotReadableException exception) {
        return ResponseEntity.badRequest()
                .body(ApiResponse.error("INVALID_REQUEST", "Request body must contain valid JSON."));
    }
}