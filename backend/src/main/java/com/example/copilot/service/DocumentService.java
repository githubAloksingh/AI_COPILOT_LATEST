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
     * Stores the exact original PDF/file binary directly into the MySQL document table (file_data LONGBLOB column)
     * AND writes a copy to the persistent uploads/ disk directory.
     */
    public void saveOriginalFile(Long documentId, byte[] bytes) {
        saveOriginalFile(documentId, bytes, null);
    }

    public void saveOriginalFile(Long documentId, Path sourcePath) throws IOException {
        byte[] bytes = null;
        if (sourcePath != null && Files.exists(sourcePath)) {
            try {
                bytes = Files.readAllBytes(sourcePath);
            } catch (Exception ignored) {
            }
        }
        saveOriginalFile(documentId, bytes, sourcePath);
    }

    public void saveOriginalFile(Long documentId, byte[] bytes, Path sourcePath) {
        Document doc = getDocumentById(documentId);
        String savedFilePath = null;

        try {
            Path uploadDirectory = getPrimaryUploadDirectory();
            Files.createDirectories(uploadDirectory);

            String fileName = doc.getFileName() != null ? doc.getFileName() : "document.bin";
            String suffix = fileName.contains(".") ? fileName.substring(fileName.lastIndexOf('.')) : ".bin";
            Path destination = uploadDirectory.resolve("document-" + documentId + suffix).normalize();

            if (sourcePath != null && Files.exists(sourcePath)) {
                Files.copy(sourcePath, destination, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
                savedFilePath = destination.toString();
            } else if (bytes != null && bytes.length > 0) {
                Files.write(destination, bytes);
                savedFilePath = destination.toString();
            }
        } catch (Exception e) {
            log.warn("Could not save original file to disk for document ID {}: {}", documentId, e.getMessage());
        }

        if (bytes != null && bytes.length > 0) {
            doc.setFileData(bytes);
        }
        if (savedFilePath != null) {
            doc.setOriginalFilePath(savedFilePath);
        }
        documentRepository.save(doc);
        log.info("Saved original file ({} bytes) in MySQL and on disk at '{}' for document ID {}",
                bytes != null ? bytes.length : 0, savedFilePath, documentId);
    }

    /**
     * Compatibility overload for callers passing filename.
     */
    public void saveOriginalFile(Long documentId, String originalFilename, byte[] bytes) {
        saveOriginalFile(documentId, bytes, null);
    }

    /**
     * Retrieves the exact original uploaded PDF/file bytes directly from MySQL or disk.
     */
    public byte[] getOriginalFileBytes(Long id) {
        Document doc = getDocumentById(id);
        byte[] bytes = documentRepository.findFileDataById(id);
        if (bytes == null || bytes.length == 0) {
            bytes = doc.getFileData();
        }

        if (bytes == null || bytes.length == 0) {
            bytes = readStoredOriginalFile(id, doc);
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
        for (Path directory : uploadDirectories()) {
            if (!Files.isDirectory(directory)) {
                continue;
            }
            try (java.util.stream.Stream<Path> files = Files.list(directory)) {
                Path legacyFile = files
                        .filter(path -> isOriginalFileName(path, id))
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
                log.warn("Could not migrate legacy original file for document {} from {}: {}", id, directory, e.getMessage());
            }
        }
        return null;
    }

    private byte[] readStoredOriginalFile(Long id, Document doc) {
        String storedPath = doc.getOriginalFilePath();
        if (storedPath == null || storedPath.isBlank()) {
            return null;
        }

        try {
            Path storedFile = Path.of(storedPath).toAbsolutePath().normalize();
            if (Files.isRegularFile(storedFile) && Files.isReadable(storedFile)) {
                return Files.readAllBytes(storedFile);
            }

            Path fileName = storedFile.getFileName();
            if (fileName != null) {
                for (Path directory : uploadDirectories()) {
                    Path candidate = directory.resolve(fileName).normalize();
                    if (candidate.startsWith(directory) && Files.isRegularFile(candidate)) {
                        return Files.readAllBytes(candidate);
                    }
                }
            }
        } catch (IOException | RuntimeException e) {
            log.warn("Could not read original file for document {}: {}", id, e.getMessage());
        }
        return null;
    }

    private Path getPrimaryUploadDirectory() {
        Path backendUploads = Path.of("backend", "uploads").toAbsolutePath().normalize();
        if (Files.isDirectory(backendUploads)) {
            return backendUploads;
        }
        Path rootUploads = Path.of("uploads").toAbsolutePath().normalize();
        if (Files.isDirectory(rootUploads)) {
            return rootUploads;
        }
        return backendUploads;
    }

    private List<Path> uploadDirectories() {
        return List.of(
                Path.of("uploads").toAbsolutePath().normalize(),
                Path.of("backend", "uploads").toAbsolutePath().normalize(),
                Path.of("..", "uploads").toAbsolutePath().normalize(),
                Path.of("..", "backend", "uploads").toAbsolutePath().normalize());
    }

    private boolean isOriginalFileName(Path path, Long documentId) {
        String name = path.getFileName().toString();
        return name.startsWith("document-" + documentId + "-")
                || name.startsWith("document-" + documentId + ".");
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
