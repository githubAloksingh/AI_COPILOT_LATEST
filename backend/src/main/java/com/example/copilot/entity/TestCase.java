package com.example.copilot.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import java.util.List;

@Entity
@Getter
@Setter
public class TestCase extends BaseEntity {

    @Column(name = "project_id")
    private Long projectId;

    @Column(name = "document_id")
    private Long documentId;

    private String tcId;
    private Long requirementId;

    @Column(nullable = false)
    private String type = "FUNCTIONAL";

    @Column(nullable = false)
    private String priority = "MEDIUM";
    
    @Column(columnDefinition = "TEXT")
    private String scenario;
    
    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> preconditions;
    
    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> steps;
    
    @Column(columnDefinition = "TEXT")
    private String expectedResult;
    
    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> sources;
}
