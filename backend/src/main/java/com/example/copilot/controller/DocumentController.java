package com.example.copilot.controller;

import com.example.copilot.dto.ApiResponse;
import com.example.copilot.entity.Document;
import com.example.copilot.service.DocumentService;
import com.example.copilot.service.IngestionService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@RestController
@RequiredArgsConstructor
public class DocumentController {

    private final DocumentService documentService;
    private final IngestionService ingestionService;

    @GetMapping("/api/documents")
    public ApiResponse<List<Document>> getAllDocuments() {
        return ApiResponse.success(documentService.getAllDocuments(), "Documents retrieved");
    }

    @GetMapping("/api/projects/{projectId}/documents")
    public ApiResponse<List<Document>> getDocumentsByProjectId(@PathVariable Long projectId) {
        return ApiResponse.success(documentService.getDocumentsByProjectId(projectId), "Project documents retrieved");
    }

    @PostMapping("/api/documents")
    public ApiResponse<Document> uploadDocument(@RequestParam("file") MultipartFile file) {
        return uploadProjectDocument(null, file, null, null, "System", "v1");
    }

    @PostMapping("/api/projects/{projectId}/documents")
    public ApiResponse<Document> uploadProjectDocument(
            @PathVariable Long projectId,
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "title", required = false) String title,
            @RequestParam(value = "customType", required = false) String customType,
            @RequestParam(value = "uploadedBy", required = false, defaultValue = "System") String uploadedBy,
            @RequestParam(value = "version", required = false, defaultValue = "v1") String version
    ) {
        if (file == null || file.isEmpty()) {
            throw new RuntimeException("Uploaded file cannot be empty");
        }
        Document doc = ingestionService.uploadDocument(projectId, file, title, customType, uploadedBy, version);
        try {
            byte[] fileBytes = file.getBytes();
            ingestionService.processDocumentAsync(doc.getId(), fileBytes, file.getOriginalFilename(), file.getContentType());
        } catch (Exception e) {
            throw new RuntimeException("Failed to start document processing: " + e.getMessage(), e);
        }
        return ApiResponse.success(doc, "Document uploaded successfully. Ingestion in progress.");
    }

    @GetMapping("/api/documents/{id}/content")
    public ApiResponse<String> getDocumentContent(@PathVariable Long id) {
        String content = documentService.getDocumentContent(id);
        return ApiResponse.success(content, "Document content retrieved");
    }

    @DeleteMapping("/api/documents/{id}")
    public ApiResponse<Void> deleteDocument(@PathVariable Long id) {
        documentService.deleteDocument(id);
        return ApiResponse.success(null, "Document deleted");
    }
}
