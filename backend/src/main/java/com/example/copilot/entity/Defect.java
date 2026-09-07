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
public class Defect extends BaseEntity {

    @Column(name = "project_id")
    private Long projectId;

    @Column(name = "document_id")
    private Long documentId;

    private String title;
    
    @Column(columnDefinition = "TEXT")
    private String description;
    
    @Column(columnDefinition = "TEXT")
    private String logs;
    
    private String environment;
    
    @Column(columnDefinition = "TEXT")
    private String stepsToReproduce;
    
    @Column(columnDefinition = "TEXT")
    private String expectedBehavior;
    
    @Column(columnDefinition = "TEXT")
    private String actualBehavior;
    
    private String severity;
    private String priority;
    
    @Column(columnDefinition = "TEXT")
    private String probableRootCause;
    
    @Column(columnDefinition = "TEXT")
    private String evidence;
    
    @Column(columnDefinition = "TEXT")
    private String suggestedInvestigation;
    
    @Column(columnDefinition = "TEXT")
    private String suggestedFix;
    
    private String confidence;
    
    @JdbcTypeCode(SqlTypes.JSON)
    private List<Map<String, Object>> relatedDefects;
    
    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> sources;
}
