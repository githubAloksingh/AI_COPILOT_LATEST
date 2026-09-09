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

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
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

    /**
     * Stores the exact original PDF/file binary directly into the MySQL document table (file_data LONGBLOB column).
     * No filesystem or disk storage is used.
     */
    public void saveOriginalFile(Long documentId, byte[] bytes) {
        Document doc = getDocumentById(documentId);
        doc.setFileData(bytes);
        documentRepository.save(doc);
        log.info("Saved original file binary ({} bytes) directly into MySQL for document ID {}",
                bytes != null ? bytes.length : 0, documentId);
    }

    /**
     * Compatibility overload for callers passing filename.
     */
    public void saveOriginalFile(Long documentId, String originalFilename, byte[] bytes) {
        saveOriginalFile(documentId, bytes);
    }

    /**
     * Retrieves the exact original uploaded PDF/file bytes directly from MySQL.
     * Does NOT touch Render Disk, ChromaDB, or extracted text.
     */
    public byte[] getOriginalFileBytes(Long id) {
        Document doc = getDocumentById(id);
        byte[] bytes = documentRepository.findFileDataById(id);
        if (bytes == null || bytes.length == 0) {
            bytes = doc.getFileData();
        }

        if (bytes == null || bytes.length == 0) {
            bytes = migrateLegacyFileToDatabase(id, doc);
        }

        if (bytes == null || bytes.length == 0) {
            log.warn("Original file binary not found in MySQL for document ID {}: {}", id, doc.getFileName());
            throw new org.springframework.web.server.ResponseStatusException(
                    org.springframework.http.HttpStatus.NOT_FOUND,
                    "Original file binary not found in database for document: " + doc.getFileName());
        }

        return bytes;
    }

    private byte[] migrateLegacyFileToDatabase(Long id, Document doc) {
        Path directory = Path.of("uploads").toAbsolutePath().normalize();
        try (java.util.stream.Stream<Path> files = Files.list(directory)) {
            Path legacyFile = files
                    .filter(path -> path.getFileName().toString().startsWith("document-" + id + "-"))
                    .filter(path -> Files.isRegularFile(path) && Files.isReadable(path))
                    .findFirst()
                    .orElse(null);
            if (legacyFile != null) {
                byte[] bytes = Files.readAllBytes(legacyFile);
                doc.setFileData(bytes);
                doc.setOriginalFilePath(null);
                documentRepository.save(doc);
                log.info("Migrated legacy original file to MySQL for document ID {} ({} bytes)", id, bytes.length);
                return bytes;
            }
        } catch (IOException e) {
            log.warn("Could not migrate legacy original file for document {}: {}", id, e.getMessage());
        }
        return null;
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
