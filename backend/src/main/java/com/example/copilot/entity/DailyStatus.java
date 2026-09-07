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
public class DailyStatus extends BaseEntity {

    @Column(name = "project_id")
    private Long projectId;

    @Column(name = "document_id")
    private Long documentId;

    @Column(columnDefinition = "TEXT")
    private String sprintInformation;
    
    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> completed;
    
    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> inProgress;
    
    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> blockers;
    
    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> risks;
    
    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> nextSteps;
    
    @Column(columnDefinition = "TEXT")
    private String importantUpdates;
}
