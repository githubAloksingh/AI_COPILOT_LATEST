package com.example.copilot.service;

import com.example.copilot.entity.DocumentChunk;
import com.example.copilot.repository.DocumentChunkRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class MockScreenServiceTest {

    @Test
    void missingExtractedTextFailsWithoutReadingOriginalFileBytesOrUsingFilename() {
        DocumentChunkRepository chunkRepository = mock(DocumentChunkRepository.class);
        DocumentService documentService = mock(DocumentService.class);
        when(documentService.getDocumentContent(42L)).thenReturn("");
        when(chunkRepository.findByDocumentIdOrderByChunkIndexAsc(42L)).thenReturn(List.of());

        MockScreenService service = new MockScreenService(
                null,
                chunkRepository,
                null,
                null,
                null,
                documentService,
                null,
                null,
                new ObjectMapper()
        );

        IllegalStateException error = assertThrows(
                IllegalStateException.class,
                () -> service.retrieveCompleteBrdText(42L)
        );

        assertTrue(error.getMessage().contains("No usable extracted BRD text"));
        verify(documentService, never()).getOriginalFileBytes(42L);
    }

    @Test
    void fallsBackToPersistedExtractedChunksWhenAiContentIsUnavailable() {
        DocumentChunkRepository chunkRepository = mock(DocumentChunkRepository.class);
        DocumentService documentService = mock(DocumentService.class);
        when(documentService.getDocumentContent(42L)).thenReturn("");

        DocumentChunk first = new DocumentChunk();
        first.setChunkText("First extracted section");
        DocumentChunk second = new DocumentChunk();
        second.setChunkText("Second extracted section");
        when(chunkRepository.findByDocumentIdOrderByChunkIndexAsc(42L)).thenReturn(List.of(first, second));

        MockScreenService service = new MockScreenService(
                null,
                chunkRepository,
                null,
                null,
                null,
                documentService,
                null,
                null,
                new ObjectMapper()
        );

        String text = service.retrieveCompleteBrdText(42L);

        assertTrue(text.startsWith("First extracted section"));
        assertTrue(text.endsWith("Second extracted section"));
        verify(documentService, never()).getOriginalFileBytes(42L);
    }
}
