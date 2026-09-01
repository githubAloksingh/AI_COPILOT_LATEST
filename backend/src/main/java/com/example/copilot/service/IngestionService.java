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

    public Document uploadDocument(MultipartFile file) {
        Document doc = new Document();
        doc.setFileName(file.getOriginalFilename());
        doc.setFileType(file.getContentType() != null ? file.getContentType() : "unknown");
        doc.setFileSize(file.getSize());
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
            log.info("Successfully completed ingestion for document ID: {} ({} chunks)", document.getId(), response.getChunk_count());

        } catch (Exception e) {
            log.error("Failed to process document ID {}: {}", documentId, e.getMessage(), e);
            document.setStatus("FAILED");
            String err = e.getMessage() != null ? e.getMessage() : "Unknown error during ingestion";
            if (err.length() > 500) {
                err = err.substring(0, 500) + "...";
            }
            document.setErrorMessage(err);
            documentRepository.save(document);
        }
    }
}
