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
public class ReleaseNote extends BaseEntity {

    @Column(name = "project_id")
    private Long projectId;

    @Column(name = "document_id")
    private Long documentId;

    private String version;
    
    @Column(columnDefinition = "TEXT")
    private String sprintInformation;
    
    @Column(columnDefinition = "TEXT")
    private String summary;
    
    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> newFeatures;
    
    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> improvements;
    
    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> bugFixes;
    
    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> breakingChanges;
    
    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> knownIssues;
    
    @Column(columnDefinition = "TEXT")
    private String technicalNotes;
}
