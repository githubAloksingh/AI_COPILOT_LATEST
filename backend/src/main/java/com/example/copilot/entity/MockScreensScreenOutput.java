package com.example.copilot.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.Getter;
import lombok.Setter;

@Entity
@Table(
        name = "mock_screens_screen_output",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_mock_screens_output_job_sequence",
                columnNames = {"mock_screens_job_id", "sequence_number"})
)
@Getter
@Setter
public class MockScreensScreenOutput extends BaseEntity {

    @Column(name = "mock_screens_job_id", nullable = false)
    private Long mockScreensJobId;

    @Column(name = "sequence_number", nullable = false)
    private Integer sequence;

    @Column(name = "screen_name", nullable = false, length = 200)
    private String screenName;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String purpose;

    @Column(name = "specification_json", nullable = false, columnDefinition = "LONGTEXT")
    private String specificationJson;
}