package com.example.copilot.controller;

import com.example.copilot.dto.ApiResponse;
import com.example.copilot.dto.mockscreen.BrdDocumentDto;
import com.example.copilot.dto.mockscreen.MockScreenGenerateRequest;
import com.example.copilot.dto.mockscreen.MockScreenJobResponse;
import com.example.copilot.dto.mockscreen.ScreenDto;
import com.example.copilot.service.MockScreenService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/mock-screens")
@RequiredArgsConstructor
public class MockScreenController {

    private final MockScreenService mockScreenService;

    /**
     * Section 2 & 19: Get only BRD documents from Knowledge Base.
     */
    @GetMapping("/documents")
    public ApiResponse<List<BrdDocumentDto>> getBrdDocuments() {
        return ApiResponse.success(mockScreenService.getBrdDocuments(), "BRD documents retrieved");
    }

    /**
     * Section 15 & 26: Start asynchronous mock screens generation job.
     */
    @PostMapping("/generate")
    public ApiResponse<Map<String, Object>> generateMockScreens(
            @RequestBody MockScreenGenerateRequest request,
            @RequestHeader(value = "X-User-Name", required = false, defaultValue = "User A") String userName
    ) {
        if (request == null || request.getDocumentId() == null) {
            throw new IllegalArgumentException("documentId is required in request body");
        }

        MockScreenJobResponse initialJob = mockScreenService.createGenerationJob(request.getDocumentId(), userName);

        // Launch asynchronous processing
        mockScreenService.processGenerationJobAsync(initialJob.getJobId(), request.getDocumentId(), userName);

        Map<String, Object> responseData = Map.of(
                "jobId", initialJob.getJobId(),
                "status", initialJob.getStatus(),
                "documentId", request.getDocumentId()
        );

        return ApiResponse.success(responseData, "Mock screens generation job queued successfully");
    }

    /**
     * Section 15 & 26: Get generation job progress and status.
     */
    @GetMapping("/jobs/{jobId}")
    public ApiResponse<MockScreenJobResponse> getJobStatus(@PathVariable String jobId) {
        return ApiResponse.success(mockScreenService.getJobStatus(jobId), "Job status retrieved");
    }

    /**
     * Section 26: Get screens for a specific generation job.
     */
    @GetMapping("/jobs/{jobId}/screens")
    public ApiResponse<List<ScreenDto>> getJobScreens(@PathVariable String jobId) {
        return ApiResponse.success(mockScreenService.getJobScreens(jobId), "Job screens retrieved");
    }

    /**
     * Section 17 & 26: Download consolidated mock screens PDF.
     */
    @GetMapping("/jobs/{jobId}/pdf")
    public ResponseEntity<byte[]> downloadJobPdf(@PathVariable String jobId) {
        byte[] pdfBytes = mockScreenService.getPdfBytes(jobId);

        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_PDF)
                .header(HttpHeaders.CONTENT_DISPOSITION, "inline; filename=\"mock-screens-" + jobId + ".pdf\"")
                .header(HttpHeaders.CACHE_CONTROL, "no-cache, no-store, must-revalidate")
                .body(pdfBytes);
    }

    /**
     * Section 26: Stream individual screen image.
     */
    @GetMapping("/{screenId}/image")
    public ResponseEntity<byte[]> getScreenImage(@PathVariable Long screenId) {
        byte[] imgBytes = mockScreenService.getScreenImageBytes(screenId);

        return ResponseEntity.ok()
                .contentType(MediaType.IMAGE_PNG)
                .header(HttpHeaders.CONTENT_DISPOSITION, "inline; filename=\"screen-" + screenId + ".png\"")
                .header(HttpHeaders.CACHE_CONTROL, "public, max-age=86400")
                .body(imgBytes);
    }

    /**
     * Section 16 & 26: Retry generation for a failed screen.
     */
    @PostMapping("/{screenId}/retry")
    public ApiResponse<ScreenDto> retryScreen(@PathVariable Long screenId) {
        ScreenDto retriedScreen = mockScreenService.retryScreen(screenId);
        return ApiResponse.success(retriedScreen, "Screen generation retried successfully");
    }

    /**
     * View past generations history.
     */
    @GetMapping("/history")
    public ApiResponse<List<MockScreenJobResponse>> getGenerationHistory() {
        return ApiResponse.success(mockScreenService.getGenerationHistory(), "Generation history retrieved");
    }
}
