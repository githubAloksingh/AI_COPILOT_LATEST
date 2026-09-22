package com.example.copilot.service;

import com.example.copilot.entity.AuditLog;
import com.example.copilot.repository.*;
import lombok.RequiredArgsConstructor;
import com.example.copilot.entity.Project;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class DashboardService {

    private final ProjectRepository projectRepository;
    private final DocumentRepository documentRepository;
    private final DocumentChunkRepository documentChunkRepository;
    private final RequirementRepository requirementRepository;
    private final TestCaseRepository testCaseRepository;
    private final DefectRepository defectRepository;
    private final ReleaseNoteRepository releaseNoteRepository;
    private final GenerationRepository generationRepository;
    private final AuditLogRepository auditLogRepository;

    public Map<String, Object> getDashboardStats() {
        Map<String, Object> stats = new HashMap<>();
        
        stats.put("projectsCreated", projectRepository.count());
        stats.put("documentsUploaded", documentRepository.count());
        stats.put("chunksStored", documentChunkRepository.count());
        stats.put("requirementsGenerated", requirementRepository.count());
        stats.put("testCasesGenerated", testCaseRepository.count());
        stats.put("defectsTriaged", defectRepository.count());
        stats.put("releaseNotesGenerated", releaseNoteRepository.count());
        stats.put("totalGenerations", generationRepository.count());

        return stats;
    }

    public List<AuditLog> getRecentActivity() {
        List<Project> activeProjects = projectRepository.findAll();
        Set<Long> activeProjectIds = activeProjects.stream()
                .map(Project::getId)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());
        Set<String> activeProjectNames = activeProjects.stream()
                .map(p -> p.getProjectName() != null ? p.getProjectName().trim().toLowerCase() : "")
                .filter(s -> !s.isEmpty())
                .collect(Collectors.toSet());

        return auditLogRepository.findAll(Sort.by(Sort.Direction.DESC, "createdAt")).stream()
                .filter(log -> !"DELETE_PROJECT".equalsIgnoreCase(log.getAction()))
                .filter(log -> {
                    boolean matchesId = log.getProjectId() != null && activeProjectIds.contains(log.getProjectId());
                    boolean matchesName = log.getProjectName() != null && activeProjectNames.contains(log.getProjectName().trim().toLowerCase());
                    return matchesId || matchesName;
                })
                .limit(20)
                .collect(Collectors.toList());
    }
}
