package com.example.copilot.controller;

import com.example.copilot.dto.ApiResponse;
import com.example.copilot.entity.Document;
import com.example.copilot.service.DocumentService;
import com.example.copilot.service.IngestionService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.nio.file.Files;
import java.nio.file.Path;
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
        Path temporaryFile = null;
        try {
            String originalFilename = file.getOriginalFilename();
            String suffix = originalFilename != null && originalFilename.contains(".")
                    ? originalFilename.substring(originalFilename.lastIndexOf('.'))
                    : ".bin";
            temporaryFile = Files.createTempFile("document-upload-", suffix);
            file.transferTo(temporaryFile);
            ingestionService.processDocumentAsync(doc.getId(), temporaryFile, originalFilename, file.getContentType());
        } catch (Exception e) {
            if (temporaryFile != null) {
                try {
                    Files.deleteIfExists(temporaryFile);
                } catch (Exception cleanupError) {
                    e.addSuppressed(cleanupError);
                }
            }
            throw new RuntimeException("Failed to start document processing: " + e.getMessage(), e);
        }
        return ApiResponse.success(doc, "Document uploaded successfully. Ingestion in progress.");
    }

    @GetMapping({"/api/documents/{id}/file", "/api/documents/{id}/view"})
    public org.springframework.http.ResponseEntity<org.springframework.core.io.Resource> getDocumentFile(@PathVariable Long id) {
        Document doc = documentService.getDocumentById(id);
        org.springframework.core.io.Resource fileResource = documentService.getOriginalFileResource(id);

        String fileName = (doc.getFileName() != null && !doc.getFileName().trim().isEmpty())
                ? doc.getFileName()
                : "document.pdf";
        String contentType = determineContentType(fileName, doc.getFileType());

        return org.springframework.http.ResponseEntity.ok()
                .contentType(org.springframework.http.MediaType.parseMediaType(contentType))
                .header(org.springframework.http.HttpHeaders.CONTENT_DISPOSITION, "inline; filename=\"" + sanitizeFilename(fileName) + "\"")
                .header(org.springframework.http.HttpHeaders.CACHE_CONTROL, "no-cache, no-store, must-revalidate")
                .body(fileResource);
    }

    @GetMapping("/api/documents/{id}/download")
    public org.springframework.http.ResponseEntity<org.springframework.core.io.Resource> downloadDocument(@PathVariable Long id) {
        Document doc = documentService.getDocumentById(id);
        org.springframework.core.io.Resource fileResource = documentService.getOriginalFileResource(id);

        String fileName = (doc.getFileName() != null && !doc.getFileName().trim().isEmpty())
                ? doc.getFileName()
                : "document.pdf";
        String contentType = determineContentType(fileName, doc.getFileType());

        return org.springframework.http.ResponseEntity.ok()
                .contentType(org.springframework.http.MediaType.parseMediaType(contentType))
                .header(org.springframework.http.HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + sanitizeFilename(fileName) + "\"")
                .header(org.springframework.http.HttpHeaders.CACHE_CONTROL, "no-cache, no-store, must-revalidate")
                .body(fileResource);
    }

    private String determineContentType(String fileName, String fileType) {
        if (fileName != null) {
            String lower = fileName.toLowerCase();
            if (lower.endsWith(".pdf")) return "application/pdf";
            if (lower.endsWith(".zip")) return "application/zip";
            if (lower.endsWith(".json")) return "application/json";
            if (lower.endsWith(".txt")) return "text/plain";
            if (lower.endsWith(".csv")) return "text/csv";
            if (lower.endsWith(".docx")) return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
        }
        if (fileType != null && !fileType.isEmpty() && !"unknown".equalsIgnoreCase(fileType)) {
            if ("BRD".equalsIgnoreCase(fileType) || fileType.toLowerCase().contains("pdf")) return "application/pdf";
            if ("ZIP".equalsIgnoreCase(fileType) || "CODEBASE".equalsIgnoreCase(fileType) || fileType.toLowerCase().contains("zip")) return "application/zip";
            return fileType;
        }
        return org.springframework.http.MediaType.APPLICATION_OCTET_STREAM_VALUE;
    }

    private String sanitizeFilename(String fileName) {
        if (fileName == null || fileName.trim().isEmpty()) {
            return "document.pdf";
        }
        return fileName.replace("\"", "\\\"");
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
