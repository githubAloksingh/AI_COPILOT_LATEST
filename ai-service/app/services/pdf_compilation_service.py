import base64
from datetime import datetime
import io
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pymupdf
from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)


class PdfCompilationService:
    PAGE_WIDTH = 842.0
    PAGE_HEIGHT = 595.0
    MARGIN = 40.0
    CONTENT_TOP = 68.0
    CONTENT_BOTTOM = PAGE_HEIGHT - 43.0
    ORANGE = (0.92, 0.36, 0.10)
    DARK = (0.12, 0.16, 0.23)
    MUTED = (0.39, 0.44, 0.52)
    BORDER = (0.87, 0.89, 0.92)
    PANEL = (0.98, 0.985, 0.99)
    WHITE = (1.0, 1.0, 1.0)

    def compile_pdf(
        self,
        application_name: str,
        project_name: Optional[str],
        brd_name: Optional[str],
        summary: Optional[str],
        screens: List[Dict[str, Any]],
    ) -> bytes:
        if not isinstance(screens, list) or not screens:
            raise ValueError("At least one generated screen is required to compile the PDF.")

        prepared = self._prepare_screens(screens)
        ordered = sorted(prepared, key=lambda screen: screen["sequence"])
        doc = pymupdf.open()
        renderer_name, visual_asset_name = self._provider_metadata()
        doc.set_metadata({
            "title": f"{application_name} Mock Screens",
            "author": "AI Work Copilot",
            "subject": f"BRD-derived UI screens rendered with {renderer_name}; visual assets: {visual_asset_name}",
            "creator": renderer_name,
            "producer": "PyMuPDF PDF composition",
        })

        self._render_cover(
            doc,
            application_name,
            project_name,
            brd_name,
            summary,
            ordered,
            renderer_name,
            visual_asset_name,
        )
        self._render_toc_continuations(doc, ordered[12:])

        for screen in ordered:
            self._render_mockup_page(doc, screen)
            self._render_specification_pages(doc, screen)

        self._stamp_footers(doc)
        pdf_bytes = doc.tobytes(deflate=True, garbage=4)
        page_count = doc.page_count
        doc.close()

        actual_page_count = self.count_pages(pdf_bytes)
        if actual_page_count != page_count:
            raise RuntimeError(
                f"Compiled PDF has {actual_page_count} pages; expected {page_count}."
            )
        logger.info(
            "Compiled %d-page consolidated mock screen PDF (%d bytes)",
            page_count,
            len(pdf_bytes),
        )
        return pdf_bytes

    def _prepare_screens(self, screens: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        prepared = []
        seen_sequences = set()
        for index, screen in enumerate(screens, start=1):
            if not isinstance(screen, dict):
                raise ValueError(f"Screen {index} must be an object.")
            raw_sequence = screen.get("sequence")
            if isinstance(raw_sequence, bool):
                raise ValueError(f"Screen {index} has an invalid sequence.")
            try:
                sequence = int(raw_sequence)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Screen {index} has an invalid sequence.") from exc
            if isinstance(raw_sequence, float) and not raw_sequence.is_integer():
                raise ValueError(f"Screen {index} has an invalid sequence.")
            if sequence < 1:
                raise ValueError(f"Screen {index} sequence must be a positive integer.")
            if sequence in seen_sequences:
                raise ValueError(f"Duplicate screen sequence {sequence} in PDF request.")
            seen_sequences.add(sequence)

            screen_data = dict(screen)
            screen_data["sequence"] = sequence
            image_bytes = self._extract_image_bytes(
                screen_data,
                ("imageData", "image_base64", "imagePath", "image_path"),
            )
            if not image_bytes:
                name = screen_data.get("name") or screen_data.get("screenName") or f"Screen {sequence}"
                raise ValueError(f"Generated image missing for screen {sequence} ({name}).")
            try:
                with Image.open(io.BytesIO(image_bytes)) as image:
                    image_format = image.format
                    image.verify()
            except (OSError, ValueError) as exc:
                raise ValueError(f"Generated image is invalid for screen {sequence}.") from exc
            if image_format != "PNG":
                raise ValueError(f"Generated image for screen {sequence} is not a PNG.")
            screen_data["_validated_image_bytes"] = image_bytes

            explanation = (
                screen_data.get("explanation")
                or screen_data.get("explanation_json")
                or screen_data.get("explanationJson")
            )
            if isinstance(explanation, str):
                try:
                    explanation = json.loads(explanation)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Explanation JSON is invalid for screen {sequence}."
                    ) from exc
            if explanation is not None and not isinstance(explanation, dict):
                raise ValueError(f"Explanation must be an object for screen {sequence}.")
            screen_data["_parsed_explanation"] = explanation or {}
            prepared.append(screen_data)
        return prepared

    @staticmethod
    def _provider_metadata() -> Tuple[str, str]:
        provider = settings.image_generator_provider.strip().lower()
        if provider == "stability":
            return "Chromium HTML/CSS renderer", "Stability AI decorative assets"
        if provider == "pymupdf":
            return "PyMuPDF Native Engine", "Not used"
        return f"Unconfigured renderer ({provider})", "Not used"

    def _render_cover(
        self,
        doc: pymupdf.Document,
        application_name: str,
        project_name: Optional[str],
        brd_name: Optional[str],
        summary: Optional[str],
        screens: Sequence[Dict[str, Any]],
        renderer_name: str,
        visual_asset_name: str,
    ) -> None:
        page = doc.new_page(width=self.PAGE_WIDTH, height=self.PAGE_HEIGHT)
        self._register_fonts(page)
        page.draw_rect(
            pymupdf.Rect(0, 0, self.PAGE_WIDTH, 190),
            color=None,
            fill=(0.10, 0.15, 0.24),
        )
        page.draw_rect(
            pymupdf.Rect(0, 186, self.PAGE_WIDTH, 191),
            color=None,
            fill=self.ORANGE,
        )
        page.insert_text(
            (self.MARGIN, 55),
            "AI WORK COPILOT  /  MOCK SCREEN BLUEPRINT",
            fontsize=10,
            color=(1.0, 0.69, 0.47),
            fontname=self._font_name(True),
        )
        title_rect = pymupdf.Rect(self.MARGIN, 73, self.PAGE_WIDTH - self.MARGIN, 123)
        page.insert_textbox(
            title_rect,
            application_name,
            fontsize=27,
            fontname=self._font_name(True),
            color=self.WHITE,
            lineheight=1.1,
        )
        page.insert_textbox(
            pymupdf.Rect(self.MARGIN, 128, self.PAGE_WIDTH - self.MARGIN, 170),
            "BRD-derived interface designs and screen specifications",
            fontsize=14,
            fontname=self._font_name(),
            color=(0.85, 0.89, 0.94),
        )

        card = pymupdf.Rect(self.MARGIN, 216, self.PAGE_WIDTH - self.MARGIN, 333)
        page.draw_rect(card, color=self.BORDER, fill=self.PANEL, radius=0.12, width=0.8)
        left_values = [
            ("SOURCE DOCUMENT", brd_name or "Not specified"),
            ("PROJECT", project_name or "Not specified"),
            ("GENERATED", datetime.now().astimezone().strftime("%d %b %Y, %H:%M %Z")),
        ]
        for index, (label, value) in enumerate(left_values):
            y = 243 + index * 27
            page.insert_text((self.MARGIN + 18, y), label, fontsize=8, fontname=self._font_name(True), color=self.MUTED)
            page.insert_textbox(
                pymupdf.Rect(self.MARGIN + 120, y - 11, 445, y + 7),
                str(value),
                fontsize=10,
                fontname=self._font_name(),
                color=self.DARK,
            )

        right_x = 470
        page.insert_text((right_x, 243), "SCREENS", fontsize=8, fontname=self._font_name(True), color=self.MUTED)
        page.insert_text(
            (right_x, 273),
            str(len(screens)),
            fontsize=21,
            fontname=self._font_name(True),
            color=self.ORANGE,
        )
        page.insert_text((right_x + 84, 243), "RENDERER", fontsize=8, fontname=self._font_name(True), color=self.MUTED)
        page.insert_textbox(
            pymupdf.Rect(right_x + 84, 251, self.PAGE_WIDTH - self.MARGIN - 12, 274),
            renderer_name,
            fontsize=9,
            fontname=self._font_name(),
            color=self.DARK,
        )
        page.insert_text((right_x, 303), "VISUAL ASSETS", fontsize=8, fontname=self._font_name(True), color=self.MUTED)
        page.insert_textbox(
            pymupdf.Rect(right_x + 84, 291, self.PAGE_WIDTH - self.MARGIN - 12, 313),
            visual_asset_name,
            fontsize=9,
            fontname=self._font_name(),
            color=self.DARK,
        )

        summary_lines: List[str] = []
        if summary:
            summary_lines = self._wrap_to_width(
                str(summary),
                self._font_object(),
                10,
                self.PAGE_WIDTH - 2 * self.MARGIN,
            )
        if summary and len(summary_lines) <= 3:
            self._draw_section_title(page, self.MARGIN, 363, "DOCUMENT OVERVIEW")
            self._draw_text_lines(
                page,
                self.MARGIN,
                384,
                self.PAGE_WIDTH - 2 * self.MARGIN,
                str(summary),
                10,
                self.DARK,
                max_bottom=435,
            )
        elif summary:
            self._draw_section_title(page, self.MARGIN, 363, "DOCUMENT OVERVIEW")
            page.insert_text(
                (self.MARGIN, 384),
                "Full business summary continues on the following page.",
                fontsize=10,
                fontname=self._font_name(),
                color=self.MUTED,
            )

        toc_y = 463 if summary else 399
        self._draw_section_title(page, self.MARGIN, toc_y, "SCREEN SEQUENCE")
        toc_y += 21
        for index, screen in enumerate(screens[:12]):
            column = index // 6
            row = index % 6
            x = self.MARGIN + column * 390
            y = toc_y + row * 17
            page.insert_text(
                (x, y),
                f"{screen['sequence']:02d}",
                fontsize=8.5,
                fontname=self._font_name(True),
                color=self.ORANGE,
            )
            page.insert_textbox(
                pymupdf.Rect(x + 25, y - 10, x + 370, y + 4),
                self._screen_name(screen),
                fontsize=9,
                fontname=self._font_name(),
                color=self.DARK,
            )
        if len(screens) > 12:
            page.insert_text(
                (self.MARGIN, min(toc_y + 6 * 17 + 3, 574)),
                f"+ {len(screens) - 12} screens listed on the contents page",
                fontsize=8,
                fontname=self._font_name(),
                color=self.MUTED,
            )
        if summary and len(summary_lines) > 3:
            self._render_summary_page(doc, str(summary))

    def _render_summary_page(self, doc: pymupdf.Document, summary: str) -> None:
        page = doc.new_page(width=self.PAGE_WIDTH, height=self.PAGE_HEIGHT)
        self._page_header(page, "APPLICATION OVERVIEW", "Business summary")
        self._draw_list_section(
            page,
            self.CONTENT_TOP,
            "APPLICATION SUMMARY",
            [summary],
            lambda continued=False: self._new_content_page(doc, continued),
        )

    def _new_content_page(self, doc: pymupdf.Document, continued: bool = False) -> pymupdf.Page:
        page = doc.new_page(width=self.PAGE_WIDTH, height=self.PAGE_HEIGHT)
        self._page_header(
            page,
            "APPLICATION OVERVIEW",
            "Business summary  /  continued" if continued else "Business summary",
        )
        return page

    def _render_toc_continuations(
        self,
        doc: pymupdf.Document,
        screens: Sequence[Dict[str, Any]],
    ) -> None:
        for offset in range(0, len(screens), 32):
            page = doc.new_page(width=self.PAGE_WIDTH, height=self.PAGE_HEIGHT)
            self._page_header(page, "CONTENTS", "Screen sequence")
            for index, screen in enumerate(screens[offset:offset + 32]):
                column = index // 16
                row = index % 16
                x = self.MARGIN + column * 390
                y = self.CONTENT_TOP + 17 + row * 28
                page.insert_text(
                    (x, y),
                    f"{screen['sequence']:02d}",
                    fontsize=9,
                    fontname=self._font_name(True),
                    color=self.ORANGE,
                )
                page.insert_textbox(
                    pymupdf.Rect(x + 28, y - 11, x + 360, y + 7),
                    self._screen_name(screen),
                    fontsize=10,
                    fontname=self._font_name(),
                    color=self.DARK,
                )

    def _render_mockup_page(self, doc: pymupdf.Document, screen: Dict[str, Any]) -> None:
        page = doc.new_page(width=self.PAGE_WIDTH, height=self.PAGE_HEIGHT)
        sequence = screen["sequence"]
        name = self._screen_name(screen)
        role = str(screen.get("userRole") or screen.get("user_role") or "")
        screen_type = str(screen.get("screenType") or screen.get("screen_type") or "")
        self._page_header(page, f"SCREEN {sequence:02d}  /  UI MOCKUP", name, role, screen_type)
        page.draw_rect(
            pymupdf.Rect(self.MARGIN, self.CONTENT_TOP - 5, self.PAGE_WIDTH - self.MARGIN, self.PAGE_HEIGHT - 39),
            color=self.BORDER,
            fill=(0.995, 0.996, 0.998),
            radius=0.1,
            width=0.7,
        )
        page.insert_image(
            pymupdf.Rect(self.MARGIN + 8, self.CONTENT_TOP + 3, self.PAGE_WIDTH - self.MARGIN - 8, self.PAGE_HEIGHT - 47),
            stream=screen["_validated_image_bytes"],
            keep_proportion=True,
            overlay=True,
        )
    def _render_specification_pages(
        self,
        doc: pymupdf.Document,
        screen: Dict[str, Any],
    ) -> None:
        sections = self._specification_sections(screen)
        page: Optional[pymupdf.Page] = None
        cursor = self.CONTENT_TOP

        def new_page(continued: bool = False) -> pymupdf.Page:
            nonlocal cursor
            result = doc.new_page(width=self.PAGE_WIDTH, height=self.PAGE_HEIGHT)
            title = self._screen_name(screen)
            if continued:
                title = f"{title}  /  continued"
            self._page_header(
                result,
                f"SCREEN {screen['sequence']:02d}  /  SPECIFICATION",
                title,
                str(screen.get("userRole") or screen.get("user_role") or ""),
                str(screen.get("screenType") or screen.get("screen_type") or ""),
            )
            cursor = self.CONTENT_TOP
            return result

        page = new_page()
        for title, kind, value in sections:
            if kind == "table":
                page, cursor = self._draw_table_section(
                    doc,
                    page,
                    cursor,
                    screen,
                    title,
                    value,
                    new_page,
                )
            else:
                page, cursor = self._draw_list_section(
                    page,
                    cursor,
                    title,
                    value,
                    new_page,
                )

    def _specification_sections(self, screen: Dict[str, Any]) -> List[Tuple[str, str, Any]]:
        explanation = screen.get("_parsed_explanation") or {}
        purpose = explanation.get("purpose_summary") or screen.get("purpose") or ""

        fields = self._collect_fields(screen, explanation)
        actions = self._collect_actions(screen, explanation)
        rules = self._unique_strings(
            self._as_list(screen.get("business_rules"))
            + self._as_list(
                self._mapping(screen.get("interaction")).get("validation_rules")
            )
            + self._as_list(explanation.get("validation_rules"))
        )
        navigation = self._collect_navigation(screen, explanation)
        references = self._unique_strings(
            self._as_list(screen.get("related_requirements"))
            + self._as_list(explanation.get("brd_references"))
        )

        components = []
        for component in self._as_list(screen.get("components")):
            if not isinstance(component, dict):
                continue
            title = component.get("title") or component.get("type") or "Component"
            details = [str(component.get("type") or "")]
            if component.get("description"):
                details.append(str(component["description"]))
            if component.get("columns"):
                details.append("Columns: " + ", ".join(map(str, component["columns"])))
            if component.get("steps"):
                details.append("Steps: " + " -> ".join(map(str, component["steps"])))
            if component.get("stats"):
                details.extend(
                    f"{stat.get('label')}: {stat.get('value')}"
                    for stat in component["stats"]
                    if isinstance(stat, dict)
                )
            if component.get("badges"):
                details.extend(
                    ", ".join(f"{key}: {value}" for key, value in badge.items())
                    for badge in component["badges"]
                    if isinstance(badge, dict)
                )
            if component.get("chart_type"):
                details.append(f"Chart: {component['chart_type']}")
                if component.get("chart_data_source"):
                    details.append(f"Data source: {component['chart_data_source']}")
                chart_values = []
                for point in self._as_list(component.get("chart_data")):
                    if not isinstance(point, dict):
                        continue
                    value = point.get("value", "")
                    prefix = component.get("chart_value_prefix") or ""
                    suffix = component.get("chart_value_suffix") or ""
                    if prefix and isinstance(value, (int, float)) and value < 0:
                        formatted_value = f"-{prefix}{abs(value):g}{suffix}"
                    else:
                        formatted_value = f"{prefix}{value}{suffix}"
                    chart_values.append(f"{point.get('label', '')}: {formatted_value}")
                if chart_values:
                    details.append("Chart values: " + ", ".join(chart_values))
                if component.get("chart_note"):
                    details.append(str(component["chart_note"]))
            components.append(f"{title}: " + " | ".join(item for item in details if item))
        for stat in self._as_list(screen.get("header_stats")):
            if isinstance(stat, dict):
                detail = f"{stat.get('label', '')}: {stat.get('value', '')}"
                if stat.get("change"):
                    detail += f" | {stat['change']}"
                if stat.get("status"):
                    detail += f" | {stat['status']}"
                components.append(detail)
        for table in self._as_list(screen.get("tables")):
            if isinstance(table, dict):
                title = table.get("title") or "Table"
                columns = self._as_list(table.get("columns"))
                details = [f"columns {', '.join(map(str, columns))}"] if columns else []
                for row_index, row in enumerate(self._as_list(table.get("rows")), start=1):
                    if isinstance(row, dict):
                        details.append(f"row {row_index}: {json.dumps(row, ensure_ascii=False, default=str)}")
                components.append(f"{title}: " + " | ".join(details) if details else str(title))
        for section in self._as_list(explanation.get("sections")):
            if not isinstance(section, dict):
                continue
            title = section.get("title") or "Section"
            content = [str(section.get(key)) for key in ("description", "notes") if section.get(key)]
            if section.get("columns"):
                content.append("Columns: " + ", ".join(map(str, section["columns"])))
            if content:
                components.append(f"{title}: " + " | ".join(content))

        interaction = self._mapping(screen.get("interaction"))
        event_lines = []
        for event in self._as_list(interaction.get("events")):
            if isinstance(event, dict) and event.get("label"):
                event_lines.append(
                    "Event: " + str(event["label"])
                    + (f" ({event['type']})" if event.get("type") else "")
                    + (f" - {event['trigger_component']}" if event.get("trigger_component") else "")
                )
        actions.extend(event_lines)

        nav_context = self._mapping(screen.get("navigation_context") or screen.get("navigationContext"))
        for key, label in (
            ("breadcrumbs", "Breadcrumbs"),
            ("navigation_items", "Navigation items"),
            ("active_nav_item", "Active navigation item"),
        ):
            value = nav_context.get(key)
            if value:
                rendered = " > ".join(map(str, value)) if isinstance(value, list) else str(value)
                navigation.append(f"{label}: {rendered}")
        navigation = self._unique_strings(navigation)

        data_bindings = []
        for binding in self._as_list(interaction.get("data_bindings")):
            if not isinstance(binding, dict):
                continue
            text = f"{binding.get('field', '')} -> {binding.get('entity', '')}"
            if binding.get("attribute"):
                text += f".{binding['attribute']}"
            if binding.get("binding_type"):
                text += f" | {binding['binding_type']}"
            data_bindings.append(text)

        state = screen.get("workflow_state") or screen.get("workflowState")
        notifications = self._unique_strings(
            self._as_list(screen.get("notifications"))
            + self._as_list(screen.get("data_sources"))
        )

        sections = [
            ("Business Purpose", "text", [purpose] if purpose else []),
            ("Field Inventory", "table", fields),
            ("Page Actions", "list", actions),
            ("Business Rules", "list", rules),
            ("Navigation Flow", "list", navigation),
            ("BRD Traceability", "list", references),
        ]
        if components:
            sections.insert(2, ("Screen Components", "list", components))
        if data_bindings:
            sections.insert(-1, ("Data Bindings", "list", self._unique_strings(data_bindings)))
        if state:
            sections.insert(-1, ("Workflow State", "list", [str(state)]))
        if notifications:
            sections.insert(-1, ("Notifications and Data Sources", "list", notifications))
        return sections

    def _collect_fields(self, screen: Dict[str, Any], explanation: Dict[str, Any]) -> List[Dict[str, Any]]:
        fields = []

        def add(field: Any) -> None:
            if not isinstance(field, dict):
                return
            label = field.get("label") or field.get("name")
            if not label:
                return
            key = re.sub(r"\s+", " ", str(label)).strip().casefold()
            if any(existing["_key"] == key for existing in fields):
                return
            fields.append({
                "_key": key,
                "name": str(label),
                "type": str(field.get("type") or "text"),
                "required": "Yes" if field.get("required") else "No",
                "details": " | ".join(
                    item
                    for item in (
                        str(field.get("rule") or field.get("placeholder") or ""),
                        f"Options: {', '.join(map(str, field['options']))}" if field.get("options") else "",
                        f"Value: {field['value']}" if field.get("value") not in (None, "") else "",
                    )
                    if item
                ),
            })

        for field in self._as_list(screen.get("fields")):
            add(field)
        for component in self._as_list(screen.get("components")):
            if isinstance(component, dict):
                for field in self._as_list(component.get("fields")):
                    add(field)
        for section in self._as_list(explanation.get("sections")):
            if isinstance(section, dict):
                for field in self._as_list(section.get("fields")):
                    add(field)
        return fields

    def _collect_actions(self, screen: Dict[str, Any], explanation: Dict[str, Any]) -> List[str]:
        actions = []
        for action in self._as_list(screen.get("actions")):
            if isinstance(action, dict) and action.get("label"):
                details = [str(action.get("label"))]
                if action.get("type"):
                    details.append(str(action["type"]))
                if action.get("target"):
                    details.append(f"Target: {action['target']}")
                actions.append(" | ".join(details))
        for component in self._as_list(screen.get("components")):
            if isinstance(component, dict):
                for action in self._as_list(component.get("actions")):
                    if isinstance(action, dict) and action.get("label"):
                        actions.append(
                            str(action["label"])
                            + (f" | {action['type']}" if action.get("type") else "")
                        )
        for action in self._as_list(explanation.get("actions")):
            if isinstance(action, dict) and action.get("label"):
                outcome = action.get("outcome")
                actions.append(
                    str(action["label"])
                    + (f" | {action['type']}" if action.get("type") else "")
                    + (f" - {outcome}" if outcome else "")
                )
        return self._unique_strings(actions)

    def _collect_navigation(self, screen: Dict[str, Any], explanation: Dict[str, Any]) -> List[str]:
        interaction = self._mapping(screen.get("interaction"))
        flows = []
        for flow in self._as_list(interaction.get("navigation_flows")):
            if not isinstance(flow, dict):
                continue
            text = str(flow.get("label") or flow.get("from_event") or "")
            if flow.get("to_screen_id"):
                text += f" -> {flow['to_screen_id']}"
            if flow.get("condition"):
                text += f" when {flow['condition']}"
            if text:
                flows.append(text)
        if explanation.get("navigation_flow"):
            flows.append(str(explanation["navigation_flow"]))
        return self._unique_strings(flows)

    def _draw_table_section(
        self,
        doc: pymupdf.Document,
        page: pymupdf.Page,
        cursor: float,
        screen: Dict[str, Any],
        title: str,
        rows: Sequence[Dict[str, Any]],
        new_page,
    ) -> Tuple[pymupdf.Page, float]:
        x = self.MARGIN
        width = self.PAGE_WIDTH - 2 * self.MARGIN
        columns = [250.0, 105.0, 68.0, width - 423.0]
        header_height = 22.0
        body_size = 9.0
        line_height = 12.0

        def heading(target: pymupdf.Page, y: float) -> float:
            target.insert_text((x + 2, y + 13), title.upper(), fontsize=9, fontname=self._font_name(True), color=self.ORANGE)
            table_top = y + 20
            target.draw_rect(
                pymupdf.Rect(x, table_top, x + width, table_top + header_height),
                color=self.BORDER,
                fill=(0.92, 0.94, 0.96),
                width=0.5,
            )
            labels = ("FIELD", "TYPE", "REQUIRED", "RULE / GUIDANCE")
            left = x
            for label, column_width in zip(labels, columns):
                target.insert_text(
                    (left + 7, table_top + 15),
                    label,
                    fontsize=8.5,
                    fontname=self._font_name(True),
                    color=self.DARK,
                )
                left += column_width
            return table_top + header_height

        if not rows:
            page, cursor = self._draw_list_section(page, cursor, title, [], new_page)
            return page, cursor

        if cursor + header_height + 40 > self.CONTENT_BOTTOM:
            page = new_page(True)
            cursor = self.CONTENT_TOP
        row_y = heading(page, cursor)

        font = self._font_object()
        for index, row in enumerate(rows):
            values = (
                str(row.get("name") or ""),
                str(row.get("type") or ""),
                str(row.get("required") or ""),
                str(row.get("details") or ""),
            )
            wrapped = [
                self._wrap_to_width(value, font, body_size, col_width - 14)
                for value, col_width in zip(values, columns)
            ]
            line_count = max(1, *(len(lines) for lines in wrapped))
            row_height = max(22.0, line_count * line_height + 10)
            if row_y + row_height > self.CONTENT_BOTTOM:
                page = new_page(True)
                cursor = self.CONTENT_TOP
                row_y = heading(page, cursor)

            fill = self.WHITE if index % 2 == 0 else (0.975, 0.98, 0.985)
            page.draw_rect(
                pymupdf.Rect(x, row_y, x + width, row_y + row_height),
                color=self.BORDER,
                fill=fill,
                width=0.35,
            )
            left = x
            for column_index, (text_lines, col_width) in enumerate(zip(wrapped, columns)):
                for line_index, line in enumerate(text_lines):
                    page.insert_text(
                        (left + 7, row_y + 14 + line_index * line_height),
                        line,
                        fontsize=body_size,
                        fontname=self._font_name(),
                        color=self.MUTED if column_index == 1 else self.DARK,
                    )
                left += col_width
            row_y += row_height
        return page, row_y + 12

    def _draw_list_section(
        self,
        page: pymupdf.Page,
        cursor: float,
        title: str,
        items: Sequence[str],
        new_page,
    ) -> Tuple[pymupdf.Page, float]:
        x = self.MARGIN
        width = self.PAGE_WIDTH - 2 * self.MARGIN
        title_height = 24.0
        if cursor + title_height + 22 > self.CONTENT_BOTTOM:
            page = new_page(True)
            cursor = self.CONTENT_TOP
        page.insert_text(
            (x + 2, cursor + 14),
            title.upper(),
            fontsize=9,
            fontname=self._font_name(True),
            color=self.ORANGE,
        )
        cursor += title_height
        if not items:
            items = ["Not specified in the screen plan."]
        font = self._font_object()
        for item in items:
            text = str(item)
            lines = self._wrap_to_width(text, font, 9.2, width - 34)
            line_height = 13.0
            first_chunk = True
            while lines:
                if cursor + line_height + 6 > self.CONTENT_BOTTOM:
                    page = new_page(True)
                    cursor = self.CONTENT_TOP
                    page.insert_text(
                        (x + 2, cursor + 14),
                        f"{title.upper()}  /  CONTINUED",
                        fontsize=9,
                        fontname=self._font_name(True),
                        color=self.ORANGE,
                    )
                    cursor += title_height
                available_lines = max(
                    1,
                    int((self.CONTENT_BOTTOM - cursor - 7) // line_height),
                )
                chunk, lines = lines[:available_lines], lines[available_lines:]
                if first_chunk:
                    page.draw_circle(
                        pymupdf.Point(x + 8, cursor + 9),
                        2.2,
                        color=None,
                        fill=self.ORANGE,
                    )
                    first_chunk = False
                for line_index, line in enumerate(chunk):
                    page.insert_text(
                        (x + 18, cursor + 12 + line_index * line_height),
                        line,
                        fontsize=9.2,
                        fontname=self._font_name(),
                        color=self.DARK,
                    )
                cursor += len(chunk) * line_height + 6
                if lines:
                    page = new_page(True)
                    cursor = self.CONTENT_TOP
                    page.insert_text(
                        (x + 2, cursor + 14),
                        f"{title.upper()}  /  CONTINUED",
                        fontsize=9,
                        fontname=self._font_name(True),
                        color=self.ORANGE,
                    )
                    cursor += title_height
        return page, cursor + 8

    def _page_header(
        self,
        page: pymupdf.Page,
        section: str,
        title: str,
        role: str = "",
        screen_type: str = "",
    ) -> None:
        self._register_fonts(page)
        page.draw_rect(
            pymupdf.Rect(0, 0, self.PAGE_WIDTH, 52),
            color=None,
            fill=(0.97, 0.98, 0.99),
        )
        page.draw_rect(pymupdf.Rect(0, 50, self.PAGE_WIDTH, 52), color=None, fill=self.ORANGE)
        page.insert_text(
            (self.MARGIN, 20),
            section,
            fontsize=8,
            fontname=self._font_name(True),
            color=self.ORANGE,
        )
        page.insert_textbox(
            pymupdf.Rect(self.MARGIN, 24, 490, 47),
            title,
            fontsize=13,
            fontname=self._font_name(True),
            color=self.DARK,
            lineheight=1.0,
        )
        details = "  |  ".join(value for value in (role, screen_type) if value)
        if details:
            page.insert_textbox(
                pymupdf.Rect(500, 20, self.PAGE_WIDTH - self.MARGIN, 43),
                details,
                fontsize=8,
                fontname=self._font_name(),
                color=self.MUTED,
                align=pymupdf.TEXT_ALIGN_RIGHT,
            )

    def _stamp_footers(self, doc: pymupdf.Document) -> None:
        total = doc.page_count
        for index, page in enumerate(doc, start=1):
            y = self.PAGE_HEIGHT - 25
            page.draw_line(
                pymupdf.Point(self.MARGIN, y - 7),
                pymupdf.Point(self.PAGE_WIDTH - self.MARGIN, y - 7),
                color=self.BORDER,
                width=0.6,
            )
            page.insert_text(
                (self.MARGIN, y + 5),
                "AI WORK COPILOT  -  SCREEN BLUEPRINT",
                fontsize=8,
                fontname=self._font_name(),
                color=self.MUTED,
            )
            page.insert_text(
                (self.PAGE_WIDTH - self.MARGIN - 95, y + 5),
                f"PAGE {index} OF {total}",
                fontsize=8,
                fontname=self._font_name(True),
                color=self.MUTED,
            )

    def _draw_section_title(self, page: pymupdf.Page, x: float, y: float, title: str) -> None:
        page.insert_text((x, y), title, fontsize=9, fontname=self._font_name(True), color=self.ORANGE)

    def _draw_text_lines(
        self,
        page: pymupdf.Page,
        x: float,
        top: float,
        width: float,
        text: str,
        font_size: float,
        color: Tuple[float, float, float],
        max_bottom: float,
    ) -> float:
        font = self._font_object()
        lines = self._wrap_to_width(str(text), font, font_size, width)
        line_height = font_size * 1.45
        for index, line in enumerate(lines):
            baseline = top + font_size + index * line_height
            if baseline > max_bottom:
                break
            page.insert_text((x, baseline), line, fontsize=font_size, fontname=self._font_name(), color=color)
        return top + len(lines) * line_height

    @staticmethod
    def _wrap_to_width(text: str, font: pymupdf.Font, size: float, width: float) -> List[str]:
        lines = []
        for paragraph in str(text).splitlines() or [""]:
            words = paragraph.split()
            if not words:
                lines.append("")
                continue
            current = ""
            for word in words:
                if font.text_length(word, fontsize=size) > width:
                    if current:
                        lines.append(current)
                        current = ""
                    piece = ""
                    for character in word:
                        if piece and font.text_length(piece + character, fontsize=size) > width:
                            lines.append(piece)
                            piece = character
                        else:
                            piece += character
                    current = piece
                    continue
                candidate = f"{current} {word}".strip()
                if current and font.text_length(candidate, fontsize=size) > width:
                    lines.append(current)
                    current = word
                else:
                    current = candidate
            if current:
                lines.append(current)
        return lines

    @classmethod
    def _font_file(cls, bold: bool = False) -> Optional[Path]:
        windows_name = "arialbd.ttf" if bold else "arial.ttf"
        linux_names = (
            ("DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf")
            if bold
            else ("DejaVuSans.ttf", "LiberationSans-Regular.ttf")
        )
        candidates = [Path("C:/Windows/Fonts") / windows_name]
        candidates.extend(
            Path("/usr/share/fonts/truetype/dejavu") / name
            for name in linux_names
            if name.startswith("DejaVu")
        )
        candidates.extend(
            Path("/usr/share/fonts/truetype/liberation2") / name
            for name in linux_names
            if name.startswith("Liberation")
        )
        return next((candidate for candidate in candidates if candidate.is_file()), None)

    @classmethod
    def _font_name(cls, bold: bool = False) -> str:
        return "BlueprintBold" if bold and cls._font_file(True) else (
            "BlueprintRegular" if not bold and cls._font_file(False) else (
                "hebo" if bold else "helv"
            )
        )

    @classmethod
    def _font_object(cls) -> pymupdf.Font:
        path = cls._font_file()
        return pymupdf.Font(fontfile=str(path)) if path else pymupdf.Font("helv")

    @classmethod
    def _register_fonts(cls, page: pymupdf.Page) -> None:
        for font_name, is_bold in (("BlueprintRegular", False), ("BlueprintBold", True)):
            path = cls._font_file(is_bold)
            if path:
                page.insert_font(fontname=font_name, fontfile=str(path))

    @staticmethod
    def _as_list(value: Any) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    @staticmethod
    def _mapping(value: Any) -> Dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _unique_strings(values: Iterable[Any]) -> List[str]:
        result = []
        seen = set()
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            key = re.sub(r"\s+", " ", text).casefold()
            if text and key not in seen:
                seen.add(key)
                result.append(text)
        return result

    @staticmethod
    def _screen_name(screen: Dict[str, Any]) -> str:
        return str(screen.get("name") or screen.get("screenName") or f"Screen {screen['sequence']}")

    def count_pages(self, pdf_bytes: bytes) -> int:
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
            return doc.page_count

    def _extract_image_bytes(
        self,
        screen: Dict[str, Any],
        candidate_keys: Tuple[str, ...],
    ) -> Optional[bytes]:
        for key in candidate_keys:
            raw = screen.get(key)
            if not raw:
                continue
            if isinstance(raw, bytes):
                return raw
            if isinstance(raw, str):
                try:
                    return base64.b64decode(raw, validate=True)
                except (ValueError, TypeError):
                    if os.path.isfile(raw):
                        try:
                            with open(raw, "rb") as image_file:
                                return image_file.read()
                        except OSError as exc:
                            raise ValueError(f"Could not read generated screen image at '{raw}'.") from exc
        return None


pdf_compilation_service = PdfCompilationService()


def compile_pdf(
    application_name: str,
    project_name: Optional[str] = None,
    brd_name: Optional[str] = None,
    summary: Optional[str] = None,
    screens: Optional[List[Dict[str, Any]]] = None,
) -> bytes:
    return pdf_compilation_service.compile_pdf(
        application_name=application_name,
        project_name=project_name,
        brd_name=brd_name,
        summary=summary,
        screens=screens or [],
    )


def count_pages(pdf_bytes: bytes) -> int:
    return pdf_compilation_service.count_pages(pdf_bytes)
