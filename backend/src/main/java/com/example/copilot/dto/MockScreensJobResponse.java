package com.example.copilot.dto;

import com.example.copilot.entity.MockScreensJobStatus;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MockScreensJobResponse {
    private String jobId;
    private Long projectId;
    private Long brdId;
    private MockScreensJobStatus status;
    private String errorCode;
    private String errorMessage;
    private Integer failedSequence;
    private Long pdfArtifactId;
    private String pdfFileName;
    private String pdfContentType;
    private Long pdfSizeBytes;
    private java.time.LocalDateTime pdfCreatedAt;
    private String pdfPreviewUrl;
    private String pdfDownloadUrl;
    private String statusUrl;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}