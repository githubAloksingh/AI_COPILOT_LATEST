package com.example.copilot.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.LocalDateTime;
import lombok.Getter;
import lombok.Setter;

@Entity
@Table(
        name = "mock_screens_job",
        uniqueConstraints = {
            @UniqueConstraint(name = "uk_mock_screens_job_job_id", columnNames = "job_id"),
            @UniqueConstraint(name = "uk_mock_screens_job_idempotency_key", columnNames = "idempotency_key")
        },
        indexes = {
            @Index(name = "idx_mock_screens_job_project_brd", columnList = "project_id, brd_id"),
            @Index(name = "idx_mock_screens_job_queue_status_created_id", columnList = "status, created_at, id")
        }
)
@Getter
@Setter
public class MockScreensJob extends BaseEntity {

    @Column(name = "job_id", nullable = false, length = 36)
    private String jobId;

    @Column(name = "project_id", nullable = false)
    private Long projectId;

    @Column(name = "brd_id", nullable = false)
    private Long brdId;

    @Column(name = "idempotency_key", length = 128)
    private String idempotencyKey;

    @Column(name = "lease_token", length = 36)
    private String leaseToken;

    @Column(name = "lease_until")
    private LocalDateTime leaseUntil;

    @Column(nullable = false, columnDefinition = "LONGTEXT")
    private String prompt;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private MockScreensJobStatus status;

    @Column(name = "error_code", length = 64)
    private String errorCode;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "screen_plan", columnDefinition = "LONGTEXT")
    private String screenPlan;

    @Column(name = "failed_sequence")
    private Integer failedSequence;

    @Column(name = "pdf_artifact_id")
    private Long pdfArtifactId;
}