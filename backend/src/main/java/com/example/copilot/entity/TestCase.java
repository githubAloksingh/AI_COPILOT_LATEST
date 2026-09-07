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
    
    @Column(columnDefinition = "TEXT")
    private String scenario;
    
    private String type;
    private String priority;
    
    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> preconditions;
    
    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> steps;
    
    @Column(columnDefinition = "TEXT")
    private String expectedResult;
    
    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> sources;
}
