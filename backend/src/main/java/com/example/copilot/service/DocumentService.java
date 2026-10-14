package com.example.copilot.service;

import com.example.copilot.client.AiServiceClient;
import com.example.copilot.entity.Document;
import com.example.copilot.entity.DocumentChunk;
import com.example.copilot.repository.DocumentChunkRepository;
import com.example.copilot.repository.DocumentRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.core.io.Resource;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class DocumentService {

    private final DocumentRepository documentRepository;
    private final DocumentChunkRepository documentChunkRepository;
    private final AiServiceClient aiServiceClient;
    private final AuditService auditService;

    public List<Document> getAllDocuments() {
        return documentRepository.findAllByOrderByCreatedAtDesc();
    }

    public List<Document> getDocumentsByProjectId(Long projectId) {
        return documentRepository.findByProjectIdOrderByCreatedAtDesc(projectId);
    }

    public Document getDocumentById(Long id) {
        return documentRepository.findById(id)
                .orElseThrow(() -> new org.springframework.web.server.ResponseStatusException(
                        org.springframework.http.HttpStatus.NOT_FOUND, "Document not found with id " + id));
    }

    /** Stores the exact original file bytes in the document table's file_data LONGBLOB column. */
    public void saveOriginalFile(Long documentId, byte[] bytes) {
        if (bytes == null || bytes.length == 0) {
            throw new IllegalArgumentException("Original file content cannot be empty.");
        }
        Document doc = getDocumentById(documentId);
        doc.setFileData(bytes);
        doc.setOriginalFilePath(null);
        documentRepository.save(doc);
        log.info("Saved original file ({} bytes) in MySQL for document ID {}", bytes.length, documentId);
    }

    /**
     * Retrieves the exact original uploaded file bytes from MySQL.
     */
    public byte[] getOriginalFileBytes(Long id) {
        getDocumentById(id);
        byte[] bytes = documentRepository.findFileDataById(id);
        if (bytes == null || bytes.length == 0) {
            log.warn("Original file binary not found in MySQL for document ID {}", id);
            throw new org.springframework.web.server.ResponseStatusException(
                    org.springframework.http.HttpStatus.NOT_FOUND,
                    "Original file binary not found in database for document ID " + id);
        }
        return bytes;
    }

    public Resource getOriginalFileResource(Long id) {
        return new org.springframework.core.io.ByteArrayResource(getOriginalFileBytes(id));
    }

    public String getDocumentContent(Long id) {
        return aiServiceClient.getDocumentContent(id);
    }

    public List<DocumentChunk> getDocumentChunks(Long id) {
        return documentChunkRepository.findByDocumentIdOrderByChunkIndexAsc(id);
    }

    public void deleteDocument(Long id) {
        long startTime = System.currentTimeMillis();
        Document doc = documentRepository.findById(id).orElse(null);
        String name = doc != null ? doc.getFileName() : "Doc #" + id;

        documentRepository.deleteById(id);
        long duration = System.currentTimeMillis() - startTime;
        auditService.logAuditFull("Knowledge Base", "DELETE_DOCUMENT", "System", "SYSTEM",
                "Deleted document: " + name, null, "System", "v1.0", "COMPLETED", "COMPLETED", duration, null, null, name, doc != null ? doc.getVersion() : null, null);
    }
}
