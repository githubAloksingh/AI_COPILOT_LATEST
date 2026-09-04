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
    
    // UPLOADING, PROCESSING, COMPLETED, FAILED
    private String status;
    private String errorMessage;
}
