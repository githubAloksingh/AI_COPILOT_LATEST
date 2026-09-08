package com.example.copilot.repository;

import com.example.copilot.entity.AuditLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AuditLogRepository extends JpaRepository<AuditLog, Long> {
    List<AuditLog> findByUserNameOrderByCreatedAtDesc(String userName);
    List<AuditLog> findByUserNameIgnoreCaseOrderByCreatedAtDesc(String userName);
    List<AuditLog> findAllByOrderByCreatedAtDesc();

    @org.springframework.data.jpa.repository.Query("SELECT a FROM AuditLog a WHERE (a.projectId = :projectId OR (a.projectId IS NULL AND a.projectName = :projectName)) AND LOWER(a.feature) IN :features ORDER BY a.createdAt DESC")
    List<AuditLog> findByProjectAndFeatures(
        @org.springframework.data.repository.query.Param("projectId") Long projectId,
        @org.springframework.data.repository.query.Param("projectName") String projectName,
        @org.springframework.data.repository.query.Param("features") List<String> features
    );
}
