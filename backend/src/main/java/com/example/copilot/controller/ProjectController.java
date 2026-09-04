package com.example.copilot.controller;

import com.example.copilot.dto.ApiResponse;
import com.example.copilot.dto.CreateProjectRequest;
import com.example.copilot.entity.Project;
import com.example.copilot.service.ProjectService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/projects")
@RequiredArgsConstructor
public class ProjectController {

    private final ProjectService projectService;

    @GetMapping
    public ApiResponse<List<Project>> getAllProjects() {
        return ApiResponse.success(projectService.getAllProjects(), "Projects retrieved");
    }

    @GetMapping("/{id}")
    public ApiResponse<Project> getProjectById(@PathVariable Long id) {
        return ApiResponse.success(projectService.getProjectById(id), "Project retrieved");
    }

    @PostMapping
    public ApiResponse<Project> createProject(@RequestBody CreateProjectRequest request) {
        Project project = projectService.createProject(request);
        return ApiResponse.success(project, "Project created successfully");
    }

    @DeleteMapping("/{id}")
    public ApiResponse<Void> deleteProject(@PathVariable Long id) {
        projectService.deleteProject(id);
        return ApiResponse.success(null, "Project deleted successfully");
    }
}
