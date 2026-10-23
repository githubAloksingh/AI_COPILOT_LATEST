package com.example.copilot.service;

import com.example.copilot.entity.DocumentChunk;
import com.example.copilot.entity.MockScreen;
import com.example.copilot.entity.MockScreenGeneration;
import com.example.copilot.repository.DocumentChunkRepository;
import com.example.copilot.repository.MockScreenGenerationRepository;
import com.example.copilot.repository.MockScreenRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
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

    @Test
    void servesGeneratedPdfAndScreenImageFromDatabase() {
        MockScreenGenerationRepository generationRepository = mock(MockScreenGenerationRepository.class);
        MockScreenRepository screenRepository = mock(MockScreenRepository.class);
        MockScreenGeneration generation = new MockScreenGeneration();
        generation.setJobId("job-42");
        when(generationRepository.findByJobId("job-42")).thenReturn(Optional.of(generation));

        MockScreen screen = new MockScreen();
        screen.setId(84L);
        when(screenRepository.findById(84L)).thenReturn(Optional.of(screen));

        byte[] pdfBytes = new byte[]{37, 80, 68, 70};
        byte[] imageBytes = new byte[]{1, 2, 3};
        byte[] wireframeBytes = new byte[]{4, 5, 6};
        when(generationRepository.findPdfDataByJobId("job-42")).thenReturn(pdfBytes);
        when(screenRepository.findImageDataById(84L)).thenReturn(imageBytes);
        when(screenRepository.findWireframeDataById(84L)).thenReturn(wireframeBytes);

        MockScreenService service = new MockScreenService(
                null,
                null,
                null,
                generationRepository,
                screenRepository,
                null,
                null,
                null,
                new ObjectMapper()
        );

        assertArrayEquals(pdfBytes, service.getPdfBytes("job-42"));
        assertArrayEquals(imageBytes, service.getScreenImageBytes(84L));
        assertArrayEquals(wireframeBytes, service.getScreenWireframeBytes(84L));
    }
}
