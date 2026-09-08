package com.example.copilot.service;

import com.example.copilot.client.AiServiceClient;
import com.example.copilot.entity.Document;
import com.example.copilot.entity.DocumentChunk;
import com.example.copilot.repository.DocumentChunkRepository;
import com.example.copilot.repository.DocumentRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.Resource;
import org.springframework.core.io.UrlResource;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.Optional;
import java.util.stream.Stream;

@Slf4j
@Service
@RequiredArgsConstructor
public class DocumentService {

    private static final Path UPLOADS_DIR = Paths.get("uploads");

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
                .orElseThrow(() -> new RuntimeException("Document not found with id " + id));
    }

    public void saveOriginalFile(Long documentId, String originalFilename, byte[] bytes) {
        try {
            if (!Files.exists(UPLOADS_DIR)) {
                Files.createDirectories(UPLOADS_DIR);
            }
            String safeName = (originalFilename != null) ? originalFilename.replaceAll("[^a-zA-Z0-9._-]", "_") : "doc";
            Path target = UPLOADS_DIR.resolve(documentId + "_" + safeName);
            Files.write(target, bytes);
        } catch (IOException e) {
            log.warn("Failed to save original file for document {}: {}", documentId, e.getMessage());
        }
    }

    public Resource loadOriginalFileAsResource(Long id) {
        Document doc = getDocumentById(id);
        try {
            if (Files.exists(UPLOADS_DIR)) {
                try (Stream<Path> stream = Files.list(UPLOADS_DIR)) {
                    Optional<Path> match = stream
                            .filter(p -> p.getFileName().toString().startsWith(id + "_"))
                            .findFirst();
                    if (match.isPresent() && Files.exists(match.get())) {
                        return new UrlResource(match.get().toUri());
                    }
                }
            }
        } catch (IOException e) {
            log.error("Error reading file for document {}: {}", id, e.getMessage());
        }
        throw new RuntimeException("Original file not found for document: " + doc.getFileName());
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

        // Clean up physical file if exists
        try {
            if (Files.exists(UPLOADS_DIR)) {
                try (Stream<Path> stream = Files.list(UPLOADS_DIR)) {
                    stream.filter(p -> p.getFileName().toString().startsWith(id + "_"))
                          .forEach(p -> {
                              try { Files.deleteIfExists(p); } catch (IOException ignored) {}
                          });
                }
            }
        } catch (Exception ignored) {}

        documentRepository.deleteById(id);
        long duration = System.currentTimeMillis() - startTime;
        auditService.logAuditFull("Knowledge Base", "DELETE_DOCUMENT", "System", "SYSTEM",
                "Deleted document: " + name, null, "System", "v1.0", "COMPLETED", "COMPLETED", duration, null, null, name, doc != null ? doc.getVersion() : null, null);
    }
}
