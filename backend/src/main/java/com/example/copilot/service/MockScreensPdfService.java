package com.example.copilot.service;

import com.example.copilot.dto.ai.AiMockScreenComponent;
import com.example.copilot.dto.ai.AiMockScreenPlanItem;
import com.example.copilot.dto.ai.AiMockScreenSpecification;
import com.example.copilot.entity.MockScreensScreenOutput;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.common.PDRectangle;
import org.apache.pdfbox.pdmodel.font.PDFont;
import org.apache.pdfbox.pdmodel.font.PDType1Font;
import org.apache.pdfbox.pdmodel.font.Standard14Fonts;
import org.apache.pdfbox.util.Matrix;
import org.springframework.stereotype.Service;

import java.awt.Color;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

@Service
@RequiredArgsConstructor
public class MockScreensPdfService {

    private static final PDRectangle PAGE_SIZE = PDRectangle.A4;
    private static final float PAGE_WIDTH = PAGE_SIZE.getWidth();
    private static final float PAGE_HEIGHT = PAGE_SIZE.getHeight();
    private static final float FRAME_X = 36;
    private static final float FRAME_TOP = 139;
    private static final float FRAME_WIDTH = PAGE_WIDTH - 2 * FRAME_X;
    private static final float FRAME_HEIGHT = PAGE_HEIGHT - FRAME_TOP - 35;
    private static final float COMPONENT_ROW_HEIGHT = 55;
    private static final int COMPONENTS_PER_PAGE = 10;

    private static final Color TEXT = new Color(30, 41, 59);
    private static final Color MUTED = new Color(100, 116, 139);
    private static final Color BORDER = new Color(203, 213, 225);
    private static final Color SURFACE = new Color(248, 250, 252);
    private static final Color ACCENT = new Color(243, 111, 33);
    private static final Color ACCENT_LIGHT = new Color(255, 243, 235);

    private final ObjectMapper objectMapper;

    public byte[] generateConsolidatedPdf(
            List<MockScreensScreenOutput> outputs,
            List<AiMockScreenPlanItem> expectedPlan) {
        List<MockScreensScreenOutput> orderedOutputs = validateAndOrder(outputs, expectedPlan);
        List<AiMockScreenSpecification> screens = orderedOutputs.stream()
                .map(this::readScreenSpecification)
                .toList();

        try (PDDocument document = new PDDocument(); ByteArrayOutputStream pdfBytes = new ByteArrayOutputStream()) {
            for (int index = 0; index < screens.size(); index++) {
                renderScreen(document, screens.get(index), index + 1, screens.size());
            }
            document.save(pdfBytes);
            byte[] result = pdfBytes.toByteArray();
            if (result.length == 0) {
                throw new IllegalStateException("PDF rendering produced an empty file.");
            }
            return result;
        } catch (IOException exception) {
            throw new IllegalStateException("Could not render the consolidated Mock Screens PDF.", exception);
        }
    }

    private List<MockScreensScreenOutput> validateAndOrder(
            List<MockScreensScreenOutput> outputs,
            List<AiMockScreenPlanItem> expectedPlan) {
        if (outputs == null || expectedPlan == null || expectedPlan.isEmpty()
                || outputs.size() != expectedPlan.size()) {
            throw new IllegalStateException("The generated screen sequence is incomplete.");
        }

        List<MockScreensScreenOutput> ordered = outputs.stream()
                .sorted(Comparator.comparing(MockScreensScreenOutput::getSequence))
                .toList();
        for (int index = 0; index < ordered.size(); index++) {
            MockScreensScreenOutput output = ordered.get(index);
            AiMockScreenPlanItem planned = expectedPlan.get(index);
            if (planned.getSequence() != index + 1
                    || output.getSequence() == null
                    || !output.getSequence().equals(planned.getSequence())
                    || !planned.getScreenName().equals(output.getScreenName())) {
                throw new IllegalStateException("The generated screen sequence is incomplete.");
            }
        }
        return ordered;
    }

    private AiMockScreenSpecification readScreenSpecification(MockScreensScreenOutput output) {
        try {
            AiMockScreenSpecification screen = objectMapper.readValue(
                    output.getSpecificationJson(), AiMockScreenSpecification.class);
            if (screen.getSequence() != output.getSequence()
                    || !output.getScreenName().equals(screen.getScreenName())
                    || screen.getComponents() == null || screen.getComponents().isEmpty()) {
                throw new IllegalStateException("A stored screen specification is invalid.");
            }
            return screen;
        } catch (IOException exception) {
            throw new IllegalStateException("A stored screen specification could not be read.", exception);
        }
    }

    private void renderScreen(PDDocument document, AiMockScreenSpecification screen, int ordinal, int total)
            throws IOException {
        List<AiMockScreenComponent> components = screen.getComponents();
        int pageCount = Math.max(1, (components.size() + COMPONENTS_PER_PAGE - 1) / COMPONENTS_PER_PAGE);
        for (int pageIndex = 0; pageIndex < pageCount; pageIndex++) {
            PDPage page = new PDPage(PAGE_SIZE);
            document.addPage(page);
            try (PDPageContentStream stream = new PDPageContentStream(document, page)) {
                renderPageHeader(stream, screen, ordinal, total, pageIndex > 0);
                renderViewport(stream);

                float rowTop = FRAME_TOP + 66;
                int start = pageIndex * COMPONENTS_PER_PAGE;
                int end = Math.min(start + COMPONENTS_PER_PAGE, components.size());
                for (int index = start; index < end; index++) {
                    renderComponent(stream, components.get(index), rowTop);
                    rowTop += COMPONENT_ROW_HEIGHT;
                }
            }
        }
    }

    private void renderPageHeader(
            PDPageContentStream stream,
            AiMockScreenSpecification screen,
            int ordinal,
            int total,
            boolean continued) throws IOException {
        PDFont bold = new PDType1Font(Standard14Fonts.FontName.HELVETICA_BOLD);
        PDFont regular = new PDType1Font(Standard14Fonts.FontName.HELVETICA);
        drawText(stream, "Mock Screens | Screen " + ordinal + " of " + total
                        + (continued ? " (continued)" : ""),
            36, 33, PAGE_WIDTH - 72, bold, 16, TEXT, true);
        drawText(stream, screen.getScreenName(), 36, 58, PAGE_WIDTH - 72,
                bold, 12, MUTED, true);
        drawText(stream, screen.getPurpose(), 36, 77, PAGE_WIDTH - 72,
                regular, 10, MUTED, true);
        drawRule(stream, FRAME_X, 118, FRAME_WIDTH);
    }

    private void renderViewport(PDPageContentStream stream) throws IOException {
        drawBox(stream, FRAME_X, FRAME_TOP, FRAME_WIDTH, FRAME_HEIGHT, Color.WHITE, BORDER);
        drawBox(stream, FRAME_X + 1, FRAME_TOP + 1, FRAME_WIDTH - 2, 28, SURFACE, SURFACE);
        drawCircle(stream, FRAME_X + 17, FRAME_TOP + 15, 3, new Color(248, 113, 113));
        drawCircle(stream, FRAME_X + 29, FRAME_TOP + 15, 3, new Color(251, 191, 36));
        drawCircle(stream, FRAME_X + 41, FRAME_TOP + 15, 3, new Color(74, 222, 128));
        drawText(stream, "APPLICATION PREVIEW", FRAME_X + 54, FRAME_TOP + 9,
                FRAME_WIDTH - 70, new PDType1Font(Standard14Fonts.FontName.HELVETICA_BOLD),
                7, MUTED, false);
    }

    private void renderComponent(PDPageContentStream stream, AiMockScreenComponent component, float top)
            throws IOException {
        float x = FRAME_X + 14;
        float width = FRAME_WIDTH - 28;
        String type = component.getComponentType() != null ? component.getComponentType() : "component";
        String label = textOr(component.getLabel(), type);
        String description = textOr(component.getDescription(), "");
        drawBox(stream, x, top, width, COMPONENT_ROW_HEIGHT - 6, SURFACE, BORDER);

        PDFont regular = new PDType1Font(Standard14Fonts.FontName.HELVETICA);
        PDFont bold = new PDType1Font(Standard14Fonts.FontName.HELVETICA_BOLD);
        switch (type) {
            case "button" -> {
                float buttonWidth = Math.min(width - 22, Math.max(110, measureText(label, bold, 10) + 28));
                drawBox(stream, x + 12, top + 12, buttonWidth, 25, ACCENT, ACCENT);
                drawText(stream, label, x + 20, top + 19, buttonWidth - 16, bold, 10, Color.WHITE, true);
                drawOptionalDescription(stream, description, x + buttonWidth + 23, top + 17, width - buttonWidth - 35);
            }
            case "input", "select" -> {
                drawText(stream, label + (component.isRequired() ? " *" : ""),
                        x + 12, top + 4, width - 24, bold, 8, TEXT, true);
                drawBox(stream, x + 12, top + 20, width - 24, 22, Color.WHITE, BORDER);
                if ("select".equals(type)) {
                    drawText(stream, "v", x + width - 24, top + 27, 10, bold, 8, MUTED, false);
                }
                drawOptionalDescription(stream, description, x + 16, top + 25, width - 48);
            }
            case "checkbox", "radio" -> {
                if ("radio".equals(type)) {
                    drawCircle(stream, x + 25, top + 23, 6, Color.WHITE);
                    drawCircle(stream, x + 25, top + 23, 2.5f, ACCENT);
                } else {
                    drawBox(stream, x + 19, top + 17, 12, 12, Color.WHITE, BORDER);
                }
                drawText(stream, label, x + 42, top + 17, width - 55, bold, 9, TEXT, true);
                drawOptionalDescription(stream, description, x + 42, top + 30, width - 55);
            }
            case "table" -> renderTable(stream, component, x, top, width, bold, regular);
            case "card", "modal", "alert", "imagePlaceholder" -> {
                Color fill = "alert".equals(type) ? ACCENT_LIGHT : Color.WHITE;
                drawBox(stream, x + 10, top + 8, width - 20, 34, fill, BORDER);
                drawText(stream, label, x + 19, top + 13, width - 40, bold, 9, TEXT, true);
                drawOptionalDescription(stream, description, x + 19, top + 26, width - 40);
            }
            case "header" -> {
                drawBox(stream, x + 1, top + 1, width - 2, COMPONENT_ROW_HEIGHT - 8, ACCENT_LIGHT, ACCENT_LIGHT);
                drawText(stream, label, x + 15, top + 16, width - 30, bold, 12, TEXT, true);
                drawOptionalDescription(stream, description, x + 15, top + 31, width - 30);
            }
            case "navigation" -> {
                drawText(stream, label, x + 12, top + 9, width - 24, bold, 9, TEXT, true);
                drawOptionalDescription(stream, description, x + 12, top + 25, width - 24);
                drawRule(stream, x + 12, top + 42, width - 24);
            }
            default -> {
                drawText(stream, label, x + 12, top + 10, width - 24, bold, 9, TEXT, true);
                drawOptionalDescription(stream, description, x + 12, top + 25, width - 24);
            }
        }
    }

    private void renderTable(
            PDPageContentStream stream,
            AiMockScreenComponent component,
            float x,
            float top,
            float width,
            PDFont bold,
            PDFont regular) throws IOException {
        drawText(stream, textOr(component.getLabel(), "Table"), x + 12, top + 5,
                width - 24, bold, 8, TEXT, true);
        float tableTop = top + 20;
        float cellWidth = (width - 24) / 3;
        for (int row = 0; row < 2; row++) {
            for (int column = 0; column < 3; column++) {
                float cellX = x + 12 + column * cellWidth;
                float cellTop = tableTop + row * 13;
                drawBox(stream, cellX, cellTop, cellWidth, 13, row == 0 ? ACCENT_LIGHT : Color.WHITE, BORDER);
                if (row == 0 && column == 0) {
                    drawText(stream, "Column", cellX + 3, cellTop + 3, cellWidth - 6,
                            regular, 6, MUTED, true);
                }
            }
        }
    }

    private void drawOptionalDescription(
            PDPageContentStream stream,
            String description,
            float x,
            float top,
            float maxWidth) throws IOException {
        if (!description.isBlank() && maxWidth > 30) {
            drawText(stream, description, x, top, maxWidth,
                    new PDType1Font(Standard14Fonts.FontName.HELVETICA), 7, MUTED, true);
        }
    }

    private void drawText(
            PDPageContentStream stream,
            String value,
            float x,
            float top,
            float maxWidth,
            PDFont font,
            float fontSize,
            Color color,
            boolean centered) throws IOException {
        if (maxWidth <= 0) return;
        List<String> lines = wrap(value, font, fontSize, maxWidth);
        float lineY = PAGE_HEIGHT - top - fontSize;
        stream.beginText();
        stream.setFont(font, fontSize);
        stream.setNonStrokingColor(color);
        for (String line : lines) {
            float lineX = centered ? x + Math.max(0, (maxWidth - measureText(line, font, fontSize)) / 2) : x;
            stream.setTextMatrix(Matrix.getTranslateInstance(lineX, lineY));
            stream.showText(line);
            lineY -= fontSize + 2;
        }
        stream.endText();
    }

    private List<String> wrap(String value, PDFont font, float fontSize, float maxWidth) throws IOException {
        String safe = sanitize(textOr(value, ""));
        if (safe.isBlank()) return List.of("");
        List<String> lines = new ArrayList<>();
        StringBuilder line = new StringBuilder();
        boolean truncated = false;
        for (String word : safe.split("\\s+")) {
            String candidate = line.isEmpty() ? word : line + " " + word;
            if (measureText(candidate, font, fontSize) <= maxWidth) {
                line.setLength(0);
                line.append(candidate);
            } else {
                if (!line.isEmpty()) {
                    lines.add(line.toString());
                    if (lines.size() == 2) {
                        truncated = true;
                        break;
                    }
                }
                line.setLength(0);
                String fittingWord = truncateWord(word, font, fontSize, maxWidth);
                line.append(fittingWord);
                if (!fittingWord.equals(word)) {
                    truncated = true;
                    break;
                }
            }
        }
        if (!line.isEmpty()) {
            if (lines.size() < 2) lines.add(line.toString());
            else truncated = true;
        }
        if (truncated && !lines.isEmpty()) {
            int lastIndex = lines.size() - 1;
            lines.set(lastIndex, ellipsize(lines.get(lastIndex), font, fontSize, maxWidth));
        }
        return lines.isEmpty() ? List.of("") : lines;
    }

    private String ellipsize(String value, PDFont font, float fontSize, float maxWidth) throws IOException {
        String shortened = value;
        while (!shortened.isEmpty() && measureText(shortened + "...", font, fontSize) > maxWidth) {
            shortened = shortened.substring(0, shortened.length() - 1);
        }
        return shortened + "...";
    }

    private String truncateWord(String word, PDFont font, float fontSize, float maxWidth) throws IOException {
        StringBuilder fitting = new StringBuilder();
        for (char character : word.toCharArray()) {
            String candidate = fitting.toString() + character;
            if (measureText(candidate, font, fontSize) > maxWidth) break;
            fitting.append(character);
        }
        return fitting.isEmpty() ? "?" : fitting.toString();
    }

    private float measureText(String value, PDFont font, float fontSize) throws IOException {
        return font.getStringWidth(sanitize(value)) / 1000 * fontSize;
    }

    private String sanitize(String value) {
        return value.replaceAll("[^\\x20-\\x7E]", "?");
    }

    private String textOr(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private void drawBox(PDPageContentStream stream, float x, float top, float width, float height,
                         Color fill, Color stroke) throws IOException {
        float bottom = PAGE_HEIGHT - top - height;
        stream.setNonStrokingColor(fill);
        stream.addRect(x, bottom, width, height);
        stream.fill();
        stream.setStrokingColor(stroke);
        stream.setLineWidth(0.7f);
        stream.addRect(x, bottom, width, height);
        stream.stroke();
    }

    private void drawCircle(PDPageContentStream stream, float centerX, float top, float radius, Color color)
            throws IOException {
        float centerY = PAGE_HEIGHT - top;
        float control = radius * 0.55228475f;
        stream.setNonStrokingColor(color);
        stream.moveTo(centerX + radius, centerY);
        stream.curveTo(centerX + radius, centerY + control,
            centerX + control, centerY + radius, centerX, centerY + radius);
        stream.curveTo(centerX - control, centerY + radius,
            centerX - radius, centerY + control, centerX - radius, centerY);
        stream.curveTo(centerX - radius, centerY - control,
            centerX - control, centerY - radius, centerX, centerY - radius);
        stream.curveTo(centerX + control, centerY - radius,
            centerX + radius, centerY - control, centerX + radius, centerY);
        stream.closePath();
        stream.fill();
    }

    private void drawRule(PDPageContentStream stream, float x, float top, float width) throws IOException {
        stream.setStrokingColor(BORDER);
        stream.setLineWidth(0.7f);
        float y = PAGE_HEIGHT - top;
        stream.moveTo(x, y);
        stream.lineTo(x + width, y);
        stream.stroke();
    }
}