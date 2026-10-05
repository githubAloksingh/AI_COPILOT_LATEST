package com.example.copilot.service;

import com.example.copilot.dto.ai.AiMockScreenComponent;
import com.example.copilot.dto.ai.AiMockScreenPlanItem;
import com.example.copilot.dto.ai.AiMockScreenSpecification;
import com.example.copilot.entity.MockScreensScreenOutput;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class MockScreensPdfServiceTest {

    private final MockScreensPdfService pdfService = new MockScreensPdfService(new ObjectMapper());

    @Test
    void generatesOneConsolidatedPdfInPersistedSequenceOrder() throws Exception {
        byte[] pdf = pdfService.generateConsolidatedPdf(
            List.of(screen(2, "SECOND_SCREEN"), screen(1, "FIRST_SCREEN")),
            List.of(plannedScreen(1, "FIRST_SCREEN"), plannedScreen(2, "SECOND_SCREEN")));

        try (PDDocument document = Loader.loadPDF(pdf)) {
            assertEquals(2, document.getNumberOfPages());
            PDFTextStripper stripper = new PDFTextStripper();
            stripper.setStartPage(1);
            stripper.setEndPage(1);
            String firstPage = stripper.getText(document);
            stripper.setStartPage(2);
            stripper.setEndPage(2);
            String secondPage = stripper.getText(document);
            assertTrue(firstPage.contains("FIRST_SCREEN"));
            assertTrue(secondPage.contains("SECOND_SCREEN"));
        }
    }

    @Test
    void rejectsMissingSequenceBeforeCreatingPdf() {
        assertThrows(IllegalStateException.class,
            () -> pdfService.generateConsolidatedPdf(
                List.of(screen(1, "FIRST"), screen(3, "THIRD")),
                List.of(plannedScreen(1, "FIRST"), plannedScreen(2, "SECOND"))));
    }

    private MockScreensScreenOutput screen(int sequence, String name) throws Exception {
        AiMockScreenComponent header = new AiMockScreenComponent();
        header.setComponentType("header");
        header.setLabel(name);
        AiMockScreenComponent action = new AiMockScreenComponent();
        action.setComponentType("button");
        action.setLabel("Continue");

        AiMockScreenSpecification specification = new AiMockScreenSpecification();
        specification.setSequence(sequence);
        specification.setScreenName(name);
        specification.setPurpose("A readable purpose for " + name);
        specification.setLayoutDescription("A consistent page layout.");
        specification.setComponents(List.of(header, action));

        MockScreensScreenOutput output = new MockScreensScreenOutput();
        output.setSequence(sequence);
        output.setScreenName(name);
        output.setPurpose(specification.getPurpose());
        output.setSpecificationJson(new ObjectMapper().writeValueAsString(specification));
        return output;
    }

    private AiMockScreenPlanItem plannedScreen(int sequence, String name) {
        AiMockScreenPlanItem planned = new AiMockScreenPlanItem();
        planned.setSequence(sequence);
        planned.setScreenName(name);
        planned.setPurpose("Purpose for " + name);
        planned.setRelevantRequirements(List.of("Requirement for " + name));
        return planned;
    }
}