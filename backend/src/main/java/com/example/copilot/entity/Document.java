package com.example.copilot.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import lombok.Getter;
import lombok.Setter;

@Entity
@Getter
@Setter
public class Document extends BaseEntity {

    @Column(name = "project_id")
    private Long projectId;

    private String fileName;
    private String fileType;
    private Long fileSize;

    @Column(name = "uploaded_by")
    private String uploadedBy = "System";

    @Column(name = "version")
    private String version = "v1";

    @Column(name = "chunk_count")
    private Integer chunkCount = 0;
    
    // UPLOADING, PROCESSING, COMPLETED, FAILED
    private String status;
    private String errorMessage;

    @jakarta.persistence.Lob
    @jakarta.persistence.Basic(fetch = jakarta.persistence.FetchType.LAZY)
    @Column(name = "file_data", columnDefinition = "LONGBLOB")
    @com.fasterxml.jackson.annotation.JsonIgnore
    private byte[] fileData;

    @Column(name = "original_file_path", length = 1024)
    @com.fasterxml.jackson.annotation.JsonIgnore
    private String originalFilePath;
}
