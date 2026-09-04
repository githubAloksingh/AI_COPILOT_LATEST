package com.example.copilot.service;

import com.example.copilot.client.AiServiceClient;
import com.example.copilot.dto.ai.AiIngestionResponse;
import com.example.copilot.entity.Document;
import com.example.copilot.repository.DocumentRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

@Slf4j
@Service
@RequiredArgsConstructor
public class IngestionService {

    private final DocumentRepository documentRepository;
    private final AiServiceClient aiServiceClient;
    private final AuditService auditService;

    public Document uploadDocument(MultipartFile file) {
        return uploadDocument(null, file, null, null, "System", "v1");
    }

    public Document uploadDocument(Long projectId, MultipartFile file, String uploadedBy, String version) {
        return uploadDocument(projectId, file, null, null, uploadedBy, version);
    }

    public Document uploadDocument(Long projectId, MultipartFile file, String title, String customType, String uploadedBy, String version) {
        String originalFileName = file.getOriginalFilename();
        String finalName = (title != null && !title.trim().isEmpty()) ? title.trim() : originalFileName;
        String calculatedVersion = version;

        if (projectId != null && (version == null || version.isEmpty() || "v1".equalsIgnoreCase(version))) {
            java.util.List<Document> existing = documentRepository.findByProjectIdAndFileNameOrderByCreatedAtDesc(projectId, finalName);
            if (existing != null && !existing.isEmpty()) {
                int maxVersion = 1;
                for (Document d : existing) {
                    String v = d.getVersion();
                    if (v != null && v.toLowerCase().startsWith("v")) {
                        try {
                            int num = Integer.parseInt(v.substring(1));
                            if (num > maxVersion) {
                                maxVersion = num;
                            }
                        } catch (NumberFormatException ignored) {}
                    }
                }
                calculatedVersion = "v" + (maxVersion + 1);
            } else {
                calculatedVersion = "v1";
            }
        }

        Document doc = new Document();
        doc.setProjectId(projectId);
        doc.setFileName(finalName);
        doc.setFileType(customType != null && !customType.trim().isEmpty() ? customType.trim() : (file.getContentType() != null ? file.getContentType() : "unknown"));
        doc.setFileSize(file.getSize());
        doc.setUploadedBy(uploadedBy != null && !uploadedBy.trim().isEmpty() ? uploadedBy.trim() : "System");
        doc.setVersion(calculatedVersion != null && !calculatedVersion.trim().isEmpty() ? calculatedVersion.trim() : "v1");
        doc.setStatus("PROCESSING");
        return documentRepository.save(doc);
    }

    @Async("documentTaskExecutor")
    public void processDocumentAsync(Long documentId, byte[] fileBytes, String originalFileName, String fileType) {
        log.info("Starting async document ingestion for document ID: {} ({}) via AI Service", documentId, originalFileName);

        Document document = documentRepository.findById(documentId).orElse(null);
        if (document == null) {
            log.error("Document with ID {} not found for processing", documentId);
            return;
        }

        long startTime = System.currentTimeMillis();
        try {
            AiIngestionResponse response = aiServiceClient.ingestDocument(
                    documentId,
                    originalFileName,
                    fileType,
                    fileBytes
            );

            document.setStatus("COMPLETED");
            document.setErrorMessage(null);
            documentRepository.save(document);
            long duration = System.currentTimeMillis() - startTime;
            auditService.logAuditFull("Knowledge Base", "UPLOAD_DOCUMENT", document.getUploadedBy(), "USER",
                    "Uploaded document: " + document.getFileName() + " (" + response.getChunk_count() + " chunks)", null, "Parser", "v1.0", "COMPLETED", "COMPLETED", duration, null, null, document.getFileName(), document.getVersion(), document.getFileType());
            log.info("Successfully completed ingestion for document ID: {} ({} chunks)", document.getId(), response.getChunk_count());

        } catch (Exception e) {
            long duration = System.currentTimeMillis() - startTime;
            log.error("Failed to process document ID {}: {}", documentId, e.getMessage(), e);
            document.setStatus("FAILED");
            String err = e.getMessage() != null ? e.getMessage() : "Unknown error during ingestion";
            if (err.length() > 500) {
                err = err.substring(0, 500) + "...";
            }
            document.setErrorMessage(err);
            documentRepository.save(document);

            auditService.logAuditFull("Knowledge Base", "UPLOAD_DOCUMENT", document.getUploadedBy(), "USER",
                    "Uploaded document: " + document.getFileName(), null, "Parser", "v1.0", null, "FAILED", duration, err, null, document.getFileName(), document.getVersion(), document.getFileType());
        }
    }
}
