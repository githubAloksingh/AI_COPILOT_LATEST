package com.example.copilot.controller;

import com.example.copilot.dto.ApiResponse;
import com.example.copilot.dto.HistoryItemDto;
import com.example.copilot.entity.AuditLog;
import com.example.copilot.entity.Document;
import com.example.copilot.entity.Project;
import com.example.copilot.repository.AuditLogRepository;
import com.example.copilot.repository.DocumentRepository;
import com.example.copilot.repository.ProjectRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;
import java.util.*;

@Slf4j
@RestController
@RequiredArgsConstructor
public class HistoryController {

    private final AuditLogRepository auditLogRepository;
    private final ProjectRepository projectRepository;
    private final DocumentRepository documentRepository;

    @GetMapping("/api/history")
    public ApiResponse<List<HistoryItemDto>> getFeatureHistory(
            @RequestParam(value = "projectId", required = false) Long projectId,
            @RequestParam(value = "documentId", required = false) Long documentId,
            @RequestParam(value = "feature", required = false) String feature
    ) {
        if (projectId == null || feature == null || feature.trim().isEmpty()) {
            return ApiResponse.success(Collections.emptyList(), "Project ID and feature required");
        }

        Project project = projectRepository.findById(projectId).orElse(null);
        if (project == null) {
            return ApiResponse.success(Collections.emptyList(), "Project not found");
        }

        List<String> featureAliases = mapFeatureToAliases(feature.trim());
        boolean isUserStory = featureAliases.contains("user story");

        // For User Story: If no BRD document is selected, return empty history
        if (isUserStory && documentId == null) {
            return ApiResponse.success(Collections.emptyList(), "No User Stories generated yet.");
        }

        // Preload documents for this project to resolve document linkages fast
        List<Document> projectDocs = documentRepository.findByProjectIdOrderByCreatedAtDesc(projectId);
        Map<String, Document> docByName = new HashMap<>();
        Map<Long, Document> docById = new HashMap<>();
        for (Document d : projectDocs) {
            if (d.getId() != null) {
                docById.put(d.getId(), d);
            }
            if (d.getFileName() != null) {
                docByName.putIfAbsent(d.getFileName().toLowerCase().trim(), d);
            }
        }

        Document selectedDoc = documentId != null ? docById.get(documentId) : null;
        String selectedDocName = selectedDoc != null ? selectedDoc.getFileName() : null;

        List<AuditLog> logs;
        if (documentId != null) {
            logs = auditLogRepository.findByProjectAndDocumentAndFeatures(
                    projectId, project.getProjectName(), documentId, selectedDocName, featureAliases
            );
        } else {
            logs = auditLogRepository.findByProjectAndFeatures(projectId, project.getProjectName(), featureAliases);
        }

        List<HistoryItemDto> result = new ArrayList<>();

        if (isUserStory) {
            // USER STORY SPECIFIC LOGIC:
            // Load only actual persisted User Story generations for the selected BRD
            int sNo = 1;
            for (AuditLog l : logs) {
                if (!"GENERATE".equalsIgnoreCase(l.getAction())) {
                    continue;
                }
                String docName = selectedDoc != null ? selectedDoc.getFileName() : l.getDocumentName();
                if (docName == null || docName.trim().isEmpty()) {
                    docName = "BRD";
                }

                String version = l.getDocumentVersion();
                if (version == null || version.trim().isEmpty() || "v1".equalsIgnoreCase(version.trim())) {
                    version = "1." + (sNo - 1);
                }

                result.add(HistoryItemDto.builder()
                        .id(l.getId())
                        .projectId(projectId)
                        .projectName(project.getProjectName())
                        .documentId(selectedDoc != null ? selectedDoc.getId() : l.getDocumentId())
                        .documentName(docName)
                        .version(version)
                        .feature("user_story")
                        .action(l.getAction())
                        .fileType("PDF")
                        .canView(true)
                        .viewUrl("/api/history/" + l.getId() + "/content")
                        .downloadUrl("/api/history/" + l.getId() + "/download")
                        .content(l.getOutput())
                        .createdAt(l.getCreatedAt())
                        .build());
                sNo++;
            }
            return ApiResponse.success(result, "History retrieved successfully");
        }

        // Generic logic for other features
        Set<String> seenKeys = new HashSet<>();
        for (AuditLog l : logs) {
            String docName = l.getDocumentName();
            if (docName == null || docName.trim().isEmpty()) {
                continue;
            }

            docName = docName.trim();
            Document matchingDoc = null;
            if (l.getDocumentId() != null) {
                matchingDoc = docById.get(l.getDocumentId());
            }
            if (matchingDoc == null) {
                matchingDoc = docByName.get(docName.toLowerCase());
            }

            String version = l.getDocumentVersion();
            if (version == null || version.trim().isEmpty()) {
                version = matchingDoc != null && matchingDoc.getVersion() != null ? matchingDoc.getVersion() : "1.0";
            }

            String dedupKey = (matchingDoc != null ? matchingDoc.getId() : docName) + "_" + version + "_" + l.getAction();
            if (!seenKeys.add(dedupKey)) {
                continue;
            }

            boolean isPdf = false;
            boolean isZip = false;
            if (matchingDoc != null) {
                String fn = matchingDoc.getFileName() != null ? matchingDoc.getFileName().toLowerCase() : "";
                isPdf = fn.endsWith(".pdf") || "BRD".equalsIgnoreCase(matchingDoc.getFileType()) || "application/pdf".equalsIgnoreCase(matchingDoc.getFileType());
                isZip = fn.endsWith(".zip") || "ZIP".equalsIgnoreCase(matchingDoc.getFileType()) || "CODEBASE".equalsIgnoreCase(matchingDoc.getFileType());
            } else {
                String fn = docName.toLowerCase();
                isPdf = fn.endsWith(".pdf") || fn.contains("brd");
                isZip = fn.endsWith(".zip");
            }

            boolean canView = isPdf && matchingDoc != null;
            String viewUrl = canView ? "/api/documents/" + matchingDoc.getId() + "/view" : null;
            String downloadUrl = matchingDoc != null
                    ? "/api/documents/" + matchingDoc.getId() + "/download"
                    : null;

            result.add(HistoryItemDto.builder()
                    .id(l.getId())
                    .projectId(projectId)
                    .projectName(project.getProjectName())
                    .documentId(matchingDoc != null ? matchingDoc.getId() : null)
                    .documentName(docName)
                    .version(version)
                    .feature(feature)
                    .action(l.getAction())
                    .fileType(isPdf ? "PDF" : (isZip ? "ZIP" : "OTHER"))
                    .canView(canView)
                    .viewUrl(viewUrl)
                    .downloadUrl(downloadUrl)
                    .content(l.getOutput())
                    .createdAt(l.getCreatedAt())
                    .build());
        }

        return ApiResponse.success(result, "History retrieved successfully");
    }

    @GetMapping("/api/history/{id}/content")
    public ApiResponse<String> getHistoryContent(@PathVariable("id") Long id) {
        AuditLog logItem = auditLogRepository.findById(id).orElse(null);
        if (logItem == null || logItem.getOutput() == null) {
            return ApiResponse.error("History content not found");
        }
        return ApiResponse.success(logItem.getOutput(), "History content retrieved");
    }

    @GetMapping("/api/history/{id}/download")
    public ResponseEntity<byte[]> downloadHistoryContent(@PathVariable("id") Long id) {
        AuditLog logItem = auditLogRepository.findById(id).orElse(null);
        if (logItem == null || logItem.getOutput() == null) {
            return ResponseEntity.notFound().build();
        }
        String content = logItem.getOutput();
        String version = logItem.getDocumentVersion() != null ? logItem.getDocumentVersion() : "1.0";
        String filename = "User_Stories_v" + version + ".json";
        byte[] bytes = content.getBytes(StandardCharsets.UTF_8);
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + filename + "\"")
                .contentType(MediaType.APPLICATION_JSON)
                .body(bytes);
    }

    private List<String> mapFeatureToAliases(String feature) {
        String f = feature.toUpperCase().replace("-", "_").replace(" ", "_");
        switch (f) {
            case "USER_STORY":
                return Arrays.asList("user story", "user_story");
            case "FUNCTIONAL_DESIGN":
                return Arrays.asList("functional design", "functional_design");
            case "TECHNICAL_DESIGN":
                return Arrays.asList("technical design", "technical_design");
            case "REQUIREMENT_ASSISTANT":
            case "REQUIREMENT":
            case "REQUIREMENTS":
                return Arrays.asList("requirement assistant", "requirement_assistant", "requirement", "requirements");
            case "TEST_GENERATOR":
            case "TEST_CASE":
            case "TESTCASE":
                return Arrays.asList("test generator", "test_generator", "test case", "testcase");
            case "DEFECT_TRIAGE":
            case "DEFECT":
                return Arrays.asList("defect triage", "defect_triage", "defect");
            case "RELEASE_NOTES":
            case "RELEASE_NOTE":
                return Arrays.asList("release notes", "release_notes", "release note", "release_note");
            default:
                return Arrays.asList(feature.toLowerCase(), f.toLowerCase());
        }
    }
}
