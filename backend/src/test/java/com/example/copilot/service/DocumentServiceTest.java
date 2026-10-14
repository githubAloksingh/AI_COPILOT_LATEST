package com.example.copilot.service;

import com.example.copilot.client.AiServiceClient;
import com.example.copilot.entity.Document;
import com.example.copilot.repository.DocumentChunkRepository;
import com.example.copilot.repository.DocumentRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class DocumentServiceTest {

    @Mock
    private DocumentRepository documentRepository;

    @Mock
    private DocumentChunkRepository documentChunkRepository;

    @Mock
    private AiServiceClient aiServiceClient;

    @Mock
    private AuditService auditService;

    private DocumentService documentService;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
        documentService = new DocumentService(
                documentRepository,
                documentChunkRepository,
                aiServiceClient,
                auditService
        );
    }

    @Test
    void storesOriginalFileBytesInDatabase() {
        Document document = new Document();
        document.setId(42L);
        document.setOriginalFilePath("legacy/path/document.pdf");
        byte[] fileBytes = new byte[]{1, 2, 3};
        when(documentRepository.findById(42L)).thenReturn(Optional.of(document));
        when(documentRepository.save(any(Document.class))).thenAnswer(invocation -> invocation.getArgument(0));

        documentService.saveOriginalFile(42L, fileBytes);

        assertArrayEquals(fileBytes, document.getFileData());
        assertNull(document.getOriginalFilePath());
        verify(documentRepository).save(document);
    }

    @Test
    void retrievesOriginalFileBytesOnlyFromDatabase() {
        Document document = new Document();
        document.setId(42L);
        when(documentRepository.findById(42L)).thenReturn(Optional.of(document));
        byte[] fileBytes = new byte[]{4, 5, 6};
        when(documentRepository.findFileDataById(42L)).thenReturn(fileBytes);

        assertArrayEquals(fileBytes, documentService.getOriginalFileBytes(42L));
    }

    @Test
    void reportsMissingDatabaseFileInsteadOfFallingBackToDisk() {
        Document document = new Document();
        document.setId(42L);
        document.setOriginalFilePath("legacy/path/document.pdf");
        when(documentRepository.findById(42L)).thenReturn(Optional.of(document));
        when(documentRepository.findFileDataById(42L)).thenReturn(null);

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> documentService.getOriginalFileBytes(42L)
        );

        assertEquals(HttpStatus.NOT_FOUND, error.getStatusCode());
    }
}
