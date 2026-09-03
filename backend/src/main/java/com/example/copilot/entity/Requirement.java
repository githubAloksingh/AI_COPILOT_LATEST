package com.example.copilot.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import java.util.List;
import java.util.Map;

@Entity
@Getter
@Setter
public class Requirement extends BaseEntity {

    /** BRD / document name this requirement was generated from */
    @Column(name = "brd_name")
    private String brdName;

    /** AI-assigned requirement ID e.g. REQ-001 */
    @Column(name = "requirement_id")
    private String requirementId;

    private String title;

    @Column(columnDefinition = "TEXT")
    private String description;

    private String priority;

    @Column(columnDefinition = "TEXT")
    private String summary;

    @Column(columnDefinition = "TEXT")
    private String userStory;

    /** Full grounded items: [{text, grounding, source[]}] */
    @JdbcTypeCode(SqlTypes.JSON)
    private List<Map<String, Object>> acceptanceCriteria;

    @JdbcTypeCode(SqlTypes.JSON)
    private List<Map<String, Object>> assumptions;

    @JdbcTypeCode(SqlTypes.JSON)
    private List<Map<String, Object>> dependencies;

    @JdbcTypeCode(SqlTypes.JSON)
    private List<Map<String, Object>> edgeCases;

    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> sources;

    /** AI model used e.g. gemini-3.7-flash */
    private String model;

    /** Prompt version e.g. requirement-v2 */
    @Column(name = "prompt_version")
    private String promptVersion;
}

