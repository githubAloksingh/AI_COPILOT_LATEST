package com.example.copilot.dto.mockscreen;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BrdDocumentDto {
    private Long id;
    private String fileName;
    private String projectName;
    private Long projectId;
    private String uploadedBy;
    private LocalDateTime createdAt;
    private String status;
    private Integer chunkCount;
    private Long fileSize;
    private String fileType;
}
