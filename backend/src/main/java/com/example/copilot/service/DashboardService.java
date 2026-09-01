package com.example.copilot.service;

import com.example.copilot.entity.AuditLog;
import com.example.copilot.repository.*;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class DashboardService {

    private final DocumentRepository documentRepository;
    private final RequirementRepository requirementRepository;
    private final TestCaseRepository testCaseRepository;
    private final DefectRepository defectRepository;
    private final ReleaseNoteRepository releaseNoteRepository;
    private final GenerationRepository generationRepository;
    private final AuditLogRepository auditLogRepository;

    public Map<String, Object> getDashboardStats() {
        Map<String, Object> stats = new HashMap<>();
        
        stats.put("documentsUploaded", documentRepository.count());
        stats.put("requirementsGenerated", requirementRepository.count());
        stats.put("testCasesGenerated", testCaseRepository.count());
        stats.put("defectsTriaged", defectRepository.count());
        stats.put("releaseNotesGenerated", releaseNoteRepository.count());
        stats.put("totalGenerations", generationRepository.count());

        return stats;
    }

    public List<AuditLog> getRecentActivity() {
        return auditLogRepository.findAll(PageRequest.of(0, 10, Sort.by(Sort.Direction.DESC, "createdAt"))).getContent();
    }
}
