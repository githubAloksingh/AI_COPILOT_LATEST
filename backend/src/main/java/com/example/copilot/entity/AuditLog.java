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
public class AuditLog extends BaseEntity {

    private String requestId;
    private String feature;
    
    @Column(columnDefinition = "TEXT")
    private String input;
    
    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> retrievedSources;
    
    private String model;
    private String promptVersion;
    
    @Column(columnDefinition = "LONGTEXT")
    private String output;
    
    private String status; // SUCCESS, FAILED
    private Long executionTimeMs;
    
    @Column(columnDefinition = "TEXT")
    private String errorMessage;

    public java.time.LocalDateTime getTimestamp() {
        return getCreatedAt();
    }
}
