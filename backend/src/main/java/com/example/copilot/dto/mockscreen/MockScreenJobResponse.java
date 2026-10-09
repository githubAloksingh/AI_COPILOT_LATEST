package com.example.copilot.dto.mockscreen;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MockScreenJobResponse {
    private String jobId;
    private Long documentId;
    private String documentName;
    private String projectName;
    private String status;
    private Integer totalScreens;
    private Integer completedScreens;
    private String currentScreen;
    private Integer currentScreenSequence;
    private String applicationName;
    private String applicationSummary;
    @Builder.Default
    private List<ScreenDto> screens = new ArrayList<>();
    private String pdfUrl;
    private String error;
    private LocalDateTime createdAt;
    private LocalDateTime completedAt;
}
