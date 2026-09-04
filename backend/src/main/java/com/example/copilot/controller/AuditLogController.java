package com.example.copilot.controller;

import com.example.copilot.dto.ApiResponse;
import com.example.copilot.entity.AuditLog;
import com.example.copilot.repository.AuditLogRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Sort;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.example.copilot.service.AuditService;
import com.example.copilot.util.UserContext;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping
@RequiredArgsConstructor
public class AuditLogController {

    private final AuditLogRepository auditLogRepository;
    private final AuditService auditService;

    @GetMapping({"/api/audit-logs", "/api/audit-history"})
    public ApiResponse<List<AuditLog>> getAuditLogs(
            @RequestParam(value = "user", required = false) String requestedUser,
            @RequestParam(value = "userId", required = false) String requestedUserId
    ) {
        String currentUser = UserContext.getCurrentUser();
        boolean isAdmin = UserContext.isAdmin();

        List<AuditLog> logs;

        if (isAdmin) {
            // ADMIN: Can view all logs, or filter by requestedUser if provided
            String targetUser = requestedUser != null ? requestedUser.trim() : (requestedUserId != null ? requestedUserId.trim() : null);
            if (targetUser != null && !targetUser.isEmpty() && !"All".equalsIgnoreCase(targetUser)) {
                logs = auditLogRepository.findByUserNameIgnoreCaseOrderByCreatedAtDesc(targetUser);
            } else {
                logs = auditLogRepository.findAllByOrderByCreatedAtDesc();
            }
        } else {
            // USER: Backend STRICT ENFORCEMENT — forcibly filter by authenticated currentUser only!
            // Ignores any requestedUser or requestedUserId parameter passed by non-admin users.
            logs = auditLogRepository.findByUserNameIgnoreCaseOrderByCreatedAtDesc(currentUser);
        }

        return ApiResponse.success(logs, "Audit logs retrieved successfully");
    }

    @PostMapping({"/api/audit-logs", "/api/audit-history"})
    public ApiResponse<String> recordAuditLog(@RequestBody Map<String, Object> body) {
        String feature = (String) body.getOrDefault("feature", "General");
        String action = (String) body.getOrDefault("action", "Execute");
        String input = (String) body.getOrDefault("input", "");
        String output = (String) body.getOrDefault("output", "");
        String status = (String) body.getOrDefault("status", "SUCCESS");
        String model = (String) body.getOrDefault("model", "System");
        String promptVersion = (String) body.getOrDefault("promptVersion", "v1.0");
        String projectName = (String) body.get("projectName");
        String documentName = (String) body.get("documentName");
        String documentVersion = (String) body.get("documentVersion");
        String inputType = (String) body.get("inputType");
        Long execTime = body.get("executionTimeMs") != null ? ((Number) body.get("executionTimeMs")).longValue() : 0L;

        String userName = body.get("userName") != null ? (String) body.get("userName") : UserContext.getCurrentUser();
        String userRole = body.get("userRole") != null ? (String) body.get("userRole") : UserContext.getCurrentRole();

        // Non-admins cannot log on behalf of another user
        if (!UserContext.isAdmin()) {
            userName = UserContext.getCurrentUser();
            userRole = UserContext.getCurrentRole();
        }

        auditService.logAuditFull(
                feature, action, userName, userRole, input, null, model, promptVersion,
                output, status, execTime, null, projectName, documentName, documentVersion, inputType
        );

        return ApiResponse.success("Audit log recorded", "Success");
    }
}
