package com.example.copilot.entity;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Entity
@Table(name = "mock_screen")
@Getter
@Setter
public class MockScreen extends BaseEntity {

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "generation_id", nullable = false)
    @JsonIgnore
    private MockScreenGeneration generation;

    @Column(name = "sequence", nullable = false)
    private Integer sequence;

    @Column(name = "screen_name", nullable = false)
    private String screenName;

    @Column(name = "screen_type", nullable = false, length = 100)
    private String screenType;

    @Column(name = "purpose", columnDefinition = "TEXT")
    private String purpose;

    @Column(name = "user_role", length = 100)
    private String userRole;

    @Column(name = "workflow_state", length = 100)
    private String workflowState;

    @Column(name = "specification_json", columnDefinition = "LONGTEXT")
    private String specificationJson;

    @Column(name = "image_prompt", columnDefinition = "TEXT")
    private String imagePrompt;

    @Column(name = "image_path", length = 1024)
    private String imagePath;

    @Lob
    @Basic(fetch = FetchType.LAZY)
    @Column(name = "image_data", columnDefinition = "LONGBLOB")
    @JsonIgnore
    private byte[] imageData;

    @Column(name = "image_mime_type", length = 50)
    private String imageMimeType = "image/png";

    // PENDING, GENERATING, COMPLETED, FAILED
    @Column(name = "status", nullable = false, length = 50)
    private String status;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;
}
