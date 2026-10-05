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
    private static final float SIDEBAR_WIDTH = 143;
    private static final float MAIN_X = 164;
    private static final float MAIN_WIDTH = PAGE_WIDTH - MAIN_X - 27;
    private static final float PANEL_TOP = 111;
    private static final float PANEL_HEIGHT = PAGE_HEIGHT - PANEL_TOP - 68;
    private static final int COMPONENTS_PER_PAGE = 12;

    private static final Color BACKGROUND = new Color(8, 23, 37);
    private static final Color SIDEBAR = new Color(11, 27, 42);
    private static final Color PANEL = new Color(16, 36, 56);
    private static final Color SURFACE = new Color(23, 47, 67);
    private static final Color FIELD = new Color(10, 27, 42);
    private static final Color TEXT = new Color(242, 246, 250);
    private static final Color MUTED = new Color(154, 175, 192);
    private static final Color BORDER = new Color(41, 68, 90);
    private static final Color ACCENT = new Color(243, 111, 33);
    private static final Color ALERT = new Color(67, 47, 33);

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
                renderApplicationChrome(stream, screen, ordinal, total, pageIndex > 0);
                drawRoundedBox(stream, MAIN_X, PANEL_TOP, MAIN_WIDTH, PANEL_HEIGHT, 8, PANEL, BORDER);
                drawText(stream, screen.getPurpose(), MAIN_X + 16, PANEL_TOP + 13,
                        MAIN_WIDTH - 32, regularFont(), 8, MUTED, false);

                int start = pageIndex * COMPONENTS_PER_PAGE;
                int end = Math.min(start + COMPONENTS_PER_PAGE, components.size());
                int count = end - start;
                float availableHeight = PANEL_HEIGHT - 57;
                float gap = count > 1 ? 6 : 0;
                float rowHeight = Math.min(62, (availableHeight - gap * (count - 1)) / count);
                float rowTop = PANEL_TOP + 39;
                for (int index = start; index < end; index++) {
                    renderComponent(stream, components.get(index), MAIN_X + 12, rowTop,
                            MAIN_WIDTH - 24, rowHeight);
                    rowTop += rowHeight + gap;
                }
            }
        }
    }

    private void renderApplicationChrome(
            PDPageContentStream stream,
            AiMockScreenSpecification screen,
            int ordinal,
            int total,
            boolean continued) throws IOException {
        PDFont bold = boldFont();
        PDFont regular = regularFont();
        drawBox(stream, 0, 0, PAGE_WIDTH, PAGE_HEIGHT, BACKGROUND, BACKGROUND);
        drawBox(stream, 0, 0, SIDEBAR_WIDTH, PAGE_HEIGHT, SIDEBAR, SIDEBAR);

        drawText(stream, "PCP", 19, 23, SIDEBAR_WIDTH - 34, bold, 22, ACCENT, false);
        drawText(stream, "PREFERRED CUSTODY PLATFORM", 20, 51, SIDEBAR_WIDTH - 32,
                bold, 5.8f, TEXT, false);
        drawRule(stream, 16, 76, SIDEBAR_WIDTH - 32, BORDER, 0.7f);

        String[] navigation = {"Dashboard", "Overdraft", "Un-Invested Cash", "Approvals",
                "Notifications", "Reports", "Audit Trail", "DMS"};
        String active = activeNavigation(screen.getScreenName());
        float navTop = 101;
        for (String item : navigation) {
            boolean selected = item.equals(active);
            if (selected) {
                drawRoundedBox(stream, 10, navTop, SIDEBAR_WIDTH - 20, 27, 5, ACCENT, ACCENT);
            }
            drawText(stream, item, 20, navTop + 8, SIDEBAR_WIDTH - 38, bold,
                    item.length() > 13 ? 7 : 8, selected ? Color.WHITE : MUTED, false);
            navTop += 36;
        }

        drawText(stream, fitOneLine(screen.getScreenName(), bold, 15, MAIN_WIDTH), MAIN_X, 24,
                MAIN_WIDTH, bold, 15, TEXT, false);
        drawText(stream, "Mock Screen " + String.format("%02d", ordinal) + " / " + total
                        + (continued ? "  |  continued" : ""),
                MAIN_X, 53, MAIN_WIDTH, regular, 8, MUTED, false);
        drawBox(stream, MAIN_X, 78, MAIN_WIDTH, 2.5f, ACCENT, ACCENT);
        drawText(stream, "Illustrative mock screen | Fictional data | Based on PCP BRD requirements",
                MAIN_X, PAGE_HEIGHT - 34, MAIN_WIDTH, regular, 6.1f, MUTED, false);
    }

    private String activeNavigation(String screenName) {
        String name = textOr(screenName, "").toLowerCase();
        if (name.contains("approval")) return "Approvals";
        if (name.contains("notification")) return "Notifications";
        if (name.contains("report")) return "Reports";
        if (name.contains("audit")) return "Audit Trail";
        if (name.contains("dms") || name.contains("document")) return "DMS";
        if (name.contains("un-invested") || name.contains("cash")) return "Un-Invested Cash";
        if (name.contains("overdraft")) return "Overdraft";
        return "Dashboard";
    }

    private void renderComponent(
            PDPageContentStream stream,
            AiMockScreenComponent component,
            float x,
            float top,
            float width,
            float height)
            throws IOException {
        String type = component.getComponentType() != null ? component.getComponentType() : "component";
        String label = textOr(component.getLabel(), type);
        String description = textOr(component.getDescription(), "");
        PDFont regular = regularFont();
        PDFont bold = boldFont();
        Color fill = "alert".equals(type) ? ALERT : SURFACE;
        drawRoundedBox(stream, x, top, width, height, 5, fill, BORDER);

        if (label.toLowerCase().contains("filter") || label.toLowerCase().contains("context")) {
            drawBox(stream, x + 1, top + 1, width - 2, 2, ACCENT, ACCENT);
        }
        switch (type) {
            case "button" -> {
                float buttonWidth = Math.min(width - 18, Math.max(74, measureText(label, bold, 8) + 22));
                float buttonHeight = Math.min(24, height - 12);
                drawRoundedBox(stream, x + 9, top + (height - buttonHeight) / 2,
                        buttonWidth, buttonHeight, 4, ACCENT, ACCENT);
                drawText(stream, label, x + 14, top + (height - 8) / 2,
                        buttonWidth - 10, bold, 8, Color.WHITE, true);
                drawOptionalDescription(stream, description, x + buttonWidth + 18,
                        top + (height - 7) / 2, width - buttonWidth - 28);
            }
            case "input", "select" -> {
                drawText(stream, label + (component.isRequired() ? " *" : ""), x + 10, top + 4,
                        width - 20, bold, 7, TEXT, false);
                float fieldTop = top + 17;
                float fieldHeight = Math.max(13, height - 21);
                drawRoundedBox(stream, x + 9, fieldTop, width - 18, fieldHeight, 3, FIELD, BORDER);
                String value = !description.isBlank() ? description
                        : "select".equals(type) ? "Select..." : "Enter value";
                if (component.getOptions() != null && !component.getOptions().isEmpty()) {
                    value = String.join(" / ", component.getOptions());
                }
                drawText(stream, value, x + 15, fieldTop + 3, width - 38,
                        regular, 6.5f, MUTED, false);
            }
            case "checkbox", "radio" -> {
                if ("radio".equals(type)) {
                    drawCircle(stream, x + 20, top + height / 2, 5, FIELD);
                    drawCircle(stream, x + 20, top + height / 2, 2, ACCENT);
                } else {
                    drawRoundedBox(stream, x + 14, top + height / 2 - 5, 10, 10, 2, FIELD, BORDER);
                }
                drawText(stream, label, x + 32, top + Math.max(6, (height - 8) / 2),
                        width - 44, bold, 8, TEXT, false);
                drawOptionalDescription(stream, description, x + 32, top + height - 14, width - 44);
            }
            case "table" -> renderTable(stream, component, x, top, width, height, bold, regular);
            case "header" -> {
                drawText(stream, label, x + 11, top + 8, width - 22, bold, 10, ACCENT, false);
                drawOptionalDescription(stream, description, x + 11, top + height - 15, width - 22);
            }
            case "navigation" -> drawText(stream, label, x + 11, top + 8,
                    width - 22, bold, 8, TEXT, false);
            default -> {
                boolean alert = "alert".equals(type);
                drawText(stream, label, x + 11, top + 7, width - 22, bold, 8,
                        alert ? ACCENT : TEXT, false);
                drawOptionalDescription(stream, description, x + 11, top + 20, width - 22);
            }
        }
    }

    private void renderTable(
            PDPageContentStream stream,
            AiMockScreenComponent component,
            float x,
            float top,
            float width,
            float height,
            PDFont bold,
            PDFont regular) throws IOException {
        drawText(stream, textOr(component.getLabel(), "Records"), x + 10, top + 4,
                width - 20, bold, 7.5f, TEXT, false);
        List<String> options = component.getOptions() == null ? List.of() : component.getOptions();
        String[] headings = options.isEmpty() ? new String[]{"Account", "Amount", "Status"}
                : splitTableRow(options.get(0));
        String[] values = options.size() < 2 ? new String[]{"Illustrative", "-", "Pending"}
                : splitTableRow(options.get(1));
        int columns = Math.max(1, Math.min(5, headings.length));
        float cellWidth = (width - 20) / columns;
        float tableTop = top + Math.max(17, (height - 22) / 2);
        for (int column = 0; column < columns; column++) {
            float cellX = x + 10 + column * cellWidth;
            drawRoundedBox(stream, cellX, tableTop, cellWidth - 2, 10, 2, FIELD, BORDER);
            drawText(stream, headings[column], cellX + 3, tableTop + 2,
                    cellWidth - 8, bold, 5.5f, ACCENT, false);
            String value = column < values.length ? values[column] : "-";
            drawText(stream, value, cellX + 3, tableTop + 11,
                    cellWidth - 8, regular, 5.7f, TEXT, false);
        }
    }

    private String[] splitTableRow(String value) {
        return value.split("\\s*[|]\\s*");
    }

    private PDFont regularFont() {
        return new PDType1Font(Standard14Fonts.FontName.HELVETICA);
    }

    private PDFont boldFont() {
        return new PDType1Font(Standard14Fonts.FontName.HELVETICA_BOLD);
    }

    private void drawOptionalDescription(
            PDPageContentStream stream,
            String description,
            float x,
            float top,
            float maxWidth) throws IOException {
        if (!description.isBlank() && maxWidth > 30) {
            drawText(stream, description, x, top, maxWidth,
                    regularFont(), 7, MUTED, false);
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

    private String fitOneLine(String value, PDFont font, float fontSize, float maxWidth) throws IOException {
        String safe = sanitize(textOr(value, "PCP Workspace"));
        if (measureText(safe, font, fontSize) <= maxWidth) return safe;
        String shortened = safe;
        while (!shortened.isEmpty() && measureText(shortened + "...", font, fontSize) > maxWidth) {
            shortened = shortened.substring(0, shortened.length() - 1);
        }
        return shortened + "...";
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

        private void drawRoundedBox(PDPageContentStream stream, float x, float top, float width, float height,
                    float radius, Color fill, Color stroke) throws IOException {
        float bottom = PAGE_HEIGHT - top - height;
        float rounded = Math.min(radius, Math.min(width, height) / 2);
        stream.setNonStrokingColor(fill);
        addRoundedPath(stream, x, bottom, width, height, rounded);
        stream.fill();
        stream.setStrokingColor(stroke);
        stream.setLineWidth(0.7f);
        addRoundedPath(stream, x, bottom, width, height, rounded);
        stream.stroke();
        }

        private void addRoundedPath(PDPageContentStream stream, float x, float bottom,
                    float width, float height, float radius) throws IOException {
        float right = x + width;
        float top = bottom + height;
        float control = radius * 0.55228475f;
        stream.moveTo(x + radius, bottom);
        stream.lineTo(right - radius, bottom);
        stream.curveTo(right - radius + control, bottom, right, bottom + radius - control,
            right, bottom + radius);
        stream.lineTo(right, top - radius);
        stream.curveTo(right, top - radius + control, right - radius + control, top,
            right - radius, top);
        stream.lineTo(x + radius, top);
        stream.curveTo(x + radius - control, top, x, top - radius + control, x, top - radius);
        stream.lineTo(x, bottom + radius);
        stream.curveTo(x, bottom + radius - control, x + radius - control, bottom,
            x + radius, bottom);
        stream.closePath();
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

    private void drawRule(PDPageContentStream stream, float x, float top, float width,
                          Color color, float lineWidth) throws IOException {
        stream.setStrokingColor(color);
        stream.setLineWidth(lineWidth);
        float y = PAGE_HEIGHT - top;
        stream.moveTo(x, y);
        stream.lineTo(x + width, y);
        stream.stroke();
    }
}