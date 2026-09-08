package com.example.copilot.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class HistoryItemDto {
    private Long id;
    private Long projectId;
    private String projectName;
    private Long documentId;
    private String documentName;
    private String version;
    private String feature;
    private String action;
    private String fileType;
    private boolean canView;
    private String viewUrl;
    private String downloadUrl;
    private LocalDateTime createdAt;
}
