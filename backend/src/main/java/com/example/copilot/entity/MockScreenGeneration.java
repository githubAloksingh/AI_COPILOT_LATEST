package com.example.copilot.entity;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "mock_screen_generation")
@Getter
@Setter
public class MockScreenGeneration extends BaseEntity {

    @Column(name = "document_id", nullable = false)
    private Long documentId;

    @Column(name = "job_id", nullable = false, unique = true, length = 100)
    private String jobId;

    @Column(name = "project_id")
    private Long projectId;

    // QUEUED, ANALYZING, PLANNING, GENERATING, COMBINING, COMPLETED, FAILED, PARTIAL_SUCCESS
    @Column(name = "status", nullable = false, length = 50)
    private String status;

    @Column(name = "total_screens")
    private Integer totalScreens = 0;

    @Column(name = "completed_screens")
    private Integer completedScreens = 0;

    @Column(name = "current_screen")
    private String currentScreen;

    @Column(name = "current_screen_sequence")
    private Integer currentScreenSequence;

    @Column(name = "application_name")
    private String applicationName;

    @Column(name = "application_summary", columnDefinition = "TEXT")
    private String applicationSummary;

    @Column(name = "design_system_json", columnDefinition = "LONGTEXT")
    private String designSystemJson;

    @Column(name = "screen_plan_json", columnDefinition = "LONGTEXT")
    private String screenPlanJson;

    @Column(name = "pdf_path", length = 1024)
    private String pdfPath;

    @Lob
    @Basic(fetch = FetchType.LAZY)
    @Column(name = "pdf_data", columnDefinition = "LONGBLOB")
    @JsonIgnore
    private byte[] pdfData;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "completed_at")
    private LocalDateTime completedAt;

    @OneToMany(mappedBy = "generation", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    @OrderBy("sequence ASC")
    private List<MockScreen> screens = new ArrayList<>();
}
