package com.example.copilot.service;

import com.example.copilot.dto.CreateProjectRequest;
import com.example.copilot.entity.Document;
import com.example.copilot.entity.Project;
import com.example.copilot.exception.ResourceNotFoundException;
import com.example.copilot.repository.DocumentRepository;
import com.example.copilot.repository.ProjectRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;


@Service
@RequiredArgsConstructor
public class ProjectService {

    private final ProjectRepository projectRepository;
    private final DocumentRepository documentRepository;
    private final AuditService auditService;

    public List<Project> getAllProjects() {
        return projectRepository.findAllByOrderByCreatedAtDesc();
    }

    public Project getProjectById(Long id) {
        return projectRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Project not found with id: " + id));
    }

    public Project createProject(CreateProjectRequest request) {
        long startTime = System.currentTimeMillis();
        if (request.getProjectName() == null || request.getProjectName().trim().isEmpty()) {
            throw new IllegalArgumentException("Project name is required");
        }
        if (request.getDepartment() == null || request.getDepartment().trim().isEmpty()) {
            throw new IllegalArgumentException("Department is required");
        }
        if (request.getProjectOwner() == null || request.getProjectOwner().trim().isEmpty()) {
            throw new IllegalArgumentException("Project owner is required");
        }

        Project project = new Project();
        project.setProjectName(request.getProjectName().trim());
        project.setDepartment(request.getDepartment().trim());
        project.setProjectOwner(request.getProjectOwner().trim());
        project.setCreatedBy("System");
        if (request.getStatus() != null && !request.getStatus().trim().isEmpty()) {
            project.setStatus(request.getStatus().trim());
        } else {
            project.setStatus("ACTIVE");
        }

        Project saved = projectRepository.save(project);
        long duration = System.currentTimeMillis() - startTime;
        auditService.logAuditFull("Knowledge Base", "CREATE_PROJECT", "System", "SYSTEM",
                "Created project: " + saved.getProjectName(), null, "System", "v1.0", "COMPLETED", "COMPLETED", duration, null, saved.getProjectName(), null, null, null);

        return saved;
    }

    @Transactional
    public void deleteProject(Long id) {
        long startTime = System.currentTimeMillis();
        Project project = getProjectById(id);
        String name = project.getProjectName();
        List<Document> docs = documentRepository.findByProjectIdOrderByCreatedAtDesc(id);
        if (docs != null && !docs.isEmpty()) {
            documentRepository.deleteAll(docs);
        }
        projectRepository.delete(project);
        long duration = System.currentTimeMillis() - startTime;
        auditService.logAuditFull("Knowledge Base", "DELETE_PROJECT", "System", "SYSTEM",
                "Deleted project: " + name, null, "System", "v1.0", "COMPLETED", "COMPLETED", duration, null, name, null, null, null);
    }
}
