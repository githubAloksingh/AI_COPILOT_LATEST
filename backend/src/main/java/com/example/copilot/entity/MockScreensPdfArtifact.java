package com.example.copilot.entity;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.Basic;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Index;
import jakarta.persistence.Lob;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.Getter;
import lombok.Setter;

@Entity
@Table(
        name = "mock_screens_pdf_artifact",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_mock_screens_pdf_job", columnNames = "mock_screens_job_id"),
        indexes = @Index(name = "idx_mock_screens_pdf_project_brd", columnList = "project_id, brd_id")
)
@Getter
@Setter
public class MockScreensPdfArtifact extends BaseEntity {

    @Column(name = "mock_screens_job_id", nullable = false)
    private Long mockScreensJobId;

    @Column(name = "job_id", nullable = false, length = 36)
    private String jobId;

    @Column(name = "project_id", nullable = false)
    private Long projectId;

    @Column(name = "brd_id", nullable = false)
    private Long brdId;

    @Column(name = "file_name", nullable = false, length = 255)
    private String fileName;

    @Column(name = "content_type", nullable = false, length = 100)
    private String contentType;

    @Column(name = "size_bytes", nullable = false)
    private Long sizeBytes;

    @Lob
    @Basic(fetch = FetchType.LAZY)
    @Column(name = "pdf_data", columnDefinition = "LONGBLOB", nullable = false)
    @JsonIgnore
    private byte[] pdfData;
}