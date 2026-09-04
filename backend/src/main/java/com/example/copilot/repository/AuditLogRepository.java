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
}
