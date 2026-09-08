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
            documentService.saveOriginalFile(doc.getId(), file.getOriginalFilename(), fileBytes);
            ingestionService.processDocumentAsync(doc.getId(), fileBytes, file.getOriginalFilename(), file.getContentType());
        } catch (Exception e) {
            throw new RuntimeException("Failed to start document processing: " + e.getMessage(), e);
        }
        return ApiResponse.success(doc, "Document uploaded successfully. Ingestion in progress.");
    }

    @GetMapping("/api/documents/{id}/download")
    public org.springframework.http.ResponseEntity<org.springframework.core.io.Resource> downloadDocument(@PathVariable Long id) {
        Document doc = documentService.getDocumentById(id);
        org.springframework.core.io.Resource resource = documentService.loadOriginalFileAsResource(id);
        String contentType = doc.getFileType();
        if (doc.getFileName() != null && doc.getFileName().toLowerCase().endsWith(".pdf")) {
            contentType = "application/pdf";
        } else if (contentType == null || contentType.isEmpty() || "unknown".equalsIgnoreCase(contentType)) {
            contentType = org.springframework.http.MediaType.APPLICATION_OCTET_STREAM_VALUE;
        }
        return org.springframework.http.ResponseEntity.ok()
                .contentType(org.springframework.http.MediaType.parseMediaType(contentType))
                .header(org.springframework.http.HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + doc.getFileName() + "\"")
                .body(resource);
    }

    @GetMapping("/api/documents/{id}/view")
    public org.springframework.http.ResponseEntity<org.springframework.core.io.Resource> viewDocument(@PathVariable Long id) {
        Document doc = documentService.getDocumentById(id);
        org.springframework.core.io.Resource resource = documentService.loadOriginalFileAsResource(id);
        String contentType = doc.getFileType();
        if (doc.getFileName() != null && doc.getFileName().toLowerCase().endsWith(".pdf")) {
            contentType = "application/pdf";
        } else if (contentType == null || contentType.isEmpty() || "unknown".equalsIgnoreCase(contentType)) {
            contentType = org.springframework.http.MediaType.APPLICATION_OCTET_STREAM_VALUE;
        }
        return org.springframework.http.ResponseEntity.ok()
                .contentType(org.springframework.http.MediaType.parseMediaType(contentType))
                .header(org.springframework.http.HttpHeaders.CONTENT_DISPOSITION, "inline; filename=\"" + doc.getFileName() + "\"")
                .body(resource);
    }

    @GetMapping("/api/documents/{id}/content")
    public ApiResponse<String> getDocumentContent(@PathVariable Long id) {
        String content = documentService.getDocumentContent(id);
        return ApiResponse.success(content, "Document content retrieved");
    }

    @GetMapping("/api/documents/{id}/chunks")
    public ApiResponse<List<com.example.copilot.entity.DocumentChunk>> getDocumentChunks(@PathVariable Long id) {
        return ApiResponse.success(documentService.getDocumentChunks(id), "Document chunks retrieved");
    }

    @DeleteMapping("/api/documents/{id}")
    public ApiResponse<Void> deleteDocument(@PathVariable Long id) {
        documentService.deleteDocument(id);
        return ApiResponse.success(null, "Document deleted");
    }
}
