import io
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import pymupdf  # PyMuPDF for vector-quality UI layout & rendering
from PIL import Image
from app.api.schemas import (
    DesignContext,
    HeaderStat,
    ScreenAction,
    ScreenComponent,
    ScreenField,
    ScreenSpecification,
    ScreenTable
)
from app.prompts.mock_screen_prompts import build_mock_screen_render_brief

logger = logging.getLogger(__name__)


class ImageGenerationService:
    """
    Renders screen mockups locally as high-resolution PNGs with PyMuPDF.
    """

    def __init__(self):
        self.provider = os.getenv("IMAGE_GENERATOR_PROVIDER", "pymupdf").strip().lower()

    def build_screen_image_prompt(self, spec: ScreenSpecification, design: DesignContext) -> str:
        """Describe the local render for API compatibility; no remote image prompt is submitted."""
        fields = self._resolve_form_fields(spec)
        columns = self._resolve_table_columns(spec)
        actions = [action.label for action in spec.actions]
        navigation_context = spec.navigation_context if isinstance(spec.navigation_context, dict) else {}
        navigation_items = navigation_context.get("navigation_items", [])
        if not isinstance(navigation_items, list):
            navigation_items = []
        navigation_labels = [
            str(item.get("label") or item.get("name") or "")
            if isinstance(item, dict)
            else str(item)
            for item in navigation_items
        ]
        return build_mock_screen_render_brief(
            brand_name=design.brand_name,
            application_type=design.application_type,
            sequence=spec.sequence,
            screen_name=spec.name,
            purpose=spec.purpose,
            user_role=spec.user_role,
            layout=self._classify_layout(spec),
            navigation=", ".join(navigation_labels) or "not specified",
            fields=", ".join(field.label for field in fields) or "none specified",
            table_columns=", ".join(columns) or "none specified",
            actions=", ".join(actions) or "none specified",
        )

    def generate_screen_image(self, spec: ScreenSpecification, design: Optional[DesignContext] = None) -> bytes:
        """Render and validate a local PNG for one screen specification."""
        if self.provider != "pymupdf":
            raise RuntimeError(
                f"Unsupported IMAGE_GENERATOR_PROVIDER '{self.provider}'. "
                "Mock-screen images must use the local PyMuPDF renderer."
            )

        active_design = design or DesignContext()
        spec.image_prompt = self.build_screen_image_prompt(spec, active_design)
        image_bytes = self._render_enterprise_mockup(spec, active_design)
        try:
            with Image.open(io.BytesIO(image_bytes)) as image:
                if image.format != "PNG" or image.width < 1024 or image.height < 576:
                    raise RuntimeError("PyMuPDF renderer returned an invalid or low-resolution PNG.")
                image.verify()
        except (OSError, ValueError) as exc:
            raise RuntimeError("PyMuPDF renderer returned an invalid or unreadable PNG image.") from exc

        logger.info(
            "Rendered local mockup for screen %s (sequence=%d, bytes=%d)",
            spec.screen_id,
            spec.sequence,
            len(image_bytes),
        )
        return image_bytes

    # =========================================================================
    # HIGH-FIDELITY ENTERPRISE UI VECTOR MOCKUP RENDERER
    # =========================================================================
    def _render_enterprise_mockup(self, spec: ScreenSpecification, design: DesignContext) -> bytes:
        """
        Renders a razor-sharp, realistic, presentation-ready 1600x900 enterprise desktop UI mockup.
        Strictly enforces design system consistency across screens.
        """
        doc = pymupdf.open()
        width = 1600.0
        height = 920.0
        page = doc.new_page(width=width, height=height)

        # Color palette helpers
        c_primary = self._hex_to_rgb(design.primary_color, (0.12, 0.25, 0.69)) # #1E40AF
        c_secondary = self._hex_to_rgb(design.secondary_color, (0.05, 0.58, 0.53))
        c_accent = self._hex_to_rgb(design.accent_color, (0.96, 0.62, 0.07))
        c_bg = self._hex_to_rgb(design.neutral_light, (0.965, 0.975, 0.985))
        c_card = self._hex_to_rgb(design.surface_color, (1.0, 1.0, 1.0))
        c_border = (0.88, 0.90, 0.93)
        c_text_dark = self._hex_to_rgb(design.neutral_dark, (0.09, 0.12, 0.18))
        c_text_muted = (0.42, 0.48, 0.55)
        c_sidebar_bg = c_card
        layout = self._classify_layout(spec)
        navigation_context = spec.navigation_context if isinstance(spec.navigation_context, dict) else {}
        navigation_items = navigation_context.get("navigation_items", [])
        if not isinstance(navigation_items, list):
            navigation_items = []
        nav_labels = [
            str(item.get("label") or item.get("name") or "").strip()
            if isinstance(item, dict)
            else str(item).strip()
            for item in navigation_items
        ]
        nav_labels = [label for label in nav_labels if label]
        active_nav_item = str(navigation_context.get("active_nav_item") or spec.name).strip()
        navigation_pattern = design.navigation_pattern.lower()
        show_navigation = len(nav_labels) > 1 and spec.screen_type.lower() != "login"
        use_sidebar = show_navigation and "sidebar" in navigation_pattern
        use_top_navigation = show_navigation and not use_sidebar and "top" in navigation_pattern
        sidebar_width = 230.0 if use_sidebar else 0.0
        navigation_height = 48.0 if use_top_navigation else 0.0

        # 1. Background
        page.draw_rect(pymupdf.Rect(0, 0, width, height), fill=c_bg, color=None)

        # 2. Header Bar (Top 64px)
        header_height = 64.0
        page.draw_rect(pymupdf.Rect(0, 0, width, header_height), fill=(1.0, 1.0, 1.0), color=c_border, width=0.8)
        # Brand Accent bar on top edge
        page.draw_rect(pymupdf.Rect(0, 0, width, 4.0), fill=c_primary, color=None)

        # Use a supplied brand only; avoid implying a fixed product or environment.
        brand_title = design.brand_name if design.brand_name != "Enterprise Suite" else "Application"
        page.draw_rect(pymupdf.Rect(24, 16, 60, 36), fill=c_primary, radius=0.1, color=None)
        page.insert_text((96, 40), brand_title[:28], fontsize=16, color=c_text_dark, fontname="hebo")

        page.insert_text((width - 206, 36), spec.user_role[:24], fontsize=10, color=c_text_dark, fontname="hebo")

        if use_sidebar:
            sidebar_top = header_height
            page.draw_rect(pymupdf.Rect(0, sidebar_top, sidebar_width, height), fill=c_sidebar_bg, color=c_border, width=0.8)
            page.insert_text((24, sidebar_top + 30), "NAVIGATION", fontsize=9, color=c_text_muted, fontname="hebo")
            y_nav = sidebar_top + 50
            for item_name in nav_labels[:12]:
                is_active = item_name.casefold() == active_nav_item.casefold()
                nav_rect = pymupdf.Rect(16, y_nav, sidebar_width - 16, y_nav + 36)
                if is_active:
                    page.draw_rect(nav_rect, fill=(0.92, 0.95, 1.0), color=None, radius=0.1)
                    page.draw_rect(pymupdf.Rect(16, y_nav + 6, 20, y_nav + 30), fill=c_primary, radius=0.1, color=None)
                page.insert_text(
                    (32, y_nav + 23),
                    self._fit_navigation_label(item_name, sidebar_width - 56),
                    fontsize=11,
                    color=c_primary if is_active else c_text_dark,
                    fontname="hebo" if is_active else "helv",
                )
                y_nav += 42
        elif use_top_navigation:
            item_width = (width - 48) / min(len(nav_labels), 8)
            for index, item_name in enumerate(nav_labels[:8]):
                nav_x = 24 + index * item_width
                is_active = item_name.casefold() == active_nav_item.casefold()
                if is_active:
                    page.draw_rect(
                        pymupdf.Rect(nav_x, header_height, nav_x + item_width - 6, header_height + 36),
                        fill=(0.92, 0.95, 1.0),
                        color=None,
                        radius=0.1,
                    )
                page.insert_text(
                    (nav_x + 10, header_height + 23),
                    self._fit_navigation_label(item_name, item_width - 20),
                    fontsize=10,
                    color=c_primary if is_active else c_text_dark,
                    fontname="hebo" if is_active else "helv",
                )

        # 4. Main Workspace Content Area
        content_x = sidebar_width + (24 if use_sidebar else 30)
        content_w = width - content_x - 24
        content_y = header_height + navigation_height + 20

        # Breadcrumbs
        crumbs = navigation_context.get("breadcrumbs")
        if isinstance(crumbs, list) and crumbs:
            crumb_text = " > ".join(str(crumb) for crumb in crumbs)
            page.insert_text((content_x, content_y), crumb_text[:100], fontsize=10, color=c_text_muted, fontname="helv")

        # Screen Title & Primary Actions Banner
        content_y += 24
        # Sequence pill badge
        seq_text = f"SCREEN {spec.sequence:02d}"
        page.draw_rect(pymupdf.Rect(content_x, content_y - 14, content_x + 84, content_y + 8), fill=c_primary, radius=0.15, color=None)
        page.insert_text((content_x + 10, content_y), seq_text, fontsize=9, color=(1.0, 1.0, 1.0), fontname="hebo")

        # Main Screen Title
        page.insert_text((content_x + 96, content_y + 4), spec.name[:45], fontsize=20, color=c_text_dark, fontname="hebo")

        # Task-focused layouts render supplied actions in their content panel instead.
        action_x = width - 24
        header_actions = self._header_actions_for_screen(spec, layout)
        primary_actions = header_actions
        for act in reversed(primary_actions[:3]):
            btn_w = max(90.0, len(act.label) * 8.5 + 24)
            btn_rect = pymupdf.Rect(action_x - btn_w, content_y - 16, action_x, content_y + 16)
            if act.type == "primary":
                page.draw_rect(btn_rect, fill=c_primary, radius=0.15, color=None)
                page.insert_text((action_x - btn_w + 14, content_y + 5), act.label, fontsize=11, color=(1.0, 1.0, 1.0), fontname="hebo")
            elif act.type == "danger":
                page.draw_rect(btn_rect, fill=(0.94, 0.25, 0.25), radius=0.15, color=None)
                page.insert_text((action_x - btn_w + 14, content_y + 5), act.label, fontsize=11, color=(1.0, 1.0, 1.0), fontname="hebo")
            else:
                page.draw_rect(btn_rect, fill=(1.0, 1.0, 1.0), color=c_border, radius=0.15, width=0.8)
                page.insert_text((action_x - btn_w + 14, content_y + 5), act.label, fontsize=11, color=c_text_dark, fontname="hebo")
            action_x -= (btn_w + 12)

        # Purpose Subtitle
        content_y += 24
        page.insert_text((content_x, content_y), spec.purpose[:140], fontsize=11, color=c_text_muted, fontname="helv")

        # Workflow progress is shown in the task-specific stepper, not as a second
        # generic banner above the form.
        content_y += 18

        # KPI tiles belong on overview-style screens; other screens use space for their task.
        stats = spec.header_stats if self._classify_layout(spec) in {"overview", "work_queue"} else []
        if stats:
            kpi_count = min(len(stats), 4)
            card_w = (content_w - (kpi_count - 1) * 16) / kpi_count
            kpi_h = 76.0
            for idx, stat in enumerate(stats[:4]):
                k_x = content_x + idx * (card_w + 16)
                k_rect = pymupdf.Rect(k_x, content_y, k_x + card_w, content_y + kpi_h)
                page.draw_rect(k_rect, fill=c_card, color=c_border, radius=0.1, width=0.8)
                # Accent bar on left edge of KPI card
                page.draw_rect(pymupdf.Rect(k_x, content_y + 12, k_x + 4, content_y + kpi_h - 12), fill=c_primary if idx % 2 == 0 else c_secondary, radius=0.1, color=None)
                page.insert_text((k_x + 16, content_y + 24), stat.label[:28], fontsize=10, color=c_text_muted, fontname="helv")
                page.insert_text((k_x + 16, content_y + 54), stat.value[:18], fontsize=20, color=c_text_dark, fontname="hebo")
                if stat.change:
                    pill_color = (0.15, 0.65, 0.35) if "+" in stat.change else (0.85, 0.30, 0.20)
                    page.insert_text((k_x + card_w - 60, content_y + 50), stat.change, fontsize=10, color=pill_color, fontname="hebo")
            content_y += (kpi_h + 18)

        # 5. Dynamic Screen Layout Content (Tables, Forms, Work Queues)
        self._render_screen_body(page, spec, design, content_x, content_y, content_w, height - 35)

        # 6. Global Footer bar
        footer_y = height - 24
        page.draw_rect(pymupdf.Rect(0, footer_y - 6, width, height), fill=(1.0, 1.0, 1.0), color=c_border, width=0.8)
        page.insert_text((content_x, footer_y + 10), f"Screen Spec: {spec.screen_id} | Target Role: {spec.user_role}", fontsize=9, color=c_text_muted, fontname="helv")

        # Render to High-DPI PNG pixmap (120 dpi provides clean ~2000x1150 resolution)
        pix = page.get_pixmap(dpi=120)
        png_bytes = pix.tobytes("png")
        doc.close()
        return png_bytes

    def _fit_navigation_label(self, label, max_width):
        font = pymupdf.Font("hebo")
        if font.text_length(label, fontsize=11) <= max_width:
            return label
        words = label.split()
        fitted = ""
        for word in words:
            candidate = f"{fitted} {word}".strip()
            if font.text_length(candidate, fontsize=11) > max_width:
                break
            fitted = candidate
        return fitted or (label[:1] + "...")

    def _header_actions_for_screen(self, spec, layout):
        actions_in_body = (
            list(spec.actions)
            if layout in {"form", "workflow", "approval", "document_review"}
            else []
        )
        if layout in {"work_queue", "report"}:
            actions_in_body.extend(
                action for action in spec.actions if "export" in action.label.lower()
            )
        body_labels = {action.label.casefold() for action in actions_in_body}
        return [action for action in spec.actions if action.label.casefold() not in body_labels]

    def _render_screen_body(
        self,
        page: pymupdf.Page,
        spec: ScreenSpecification,
        design: DesignContext,
        x: float,
        y: float,
        w: float,
        max_y: float
    ) -> None:
        """Choose a task-specific composition from screen intent and supplied components."""
        layout = self._classify_layout(spec)
        if layout == "approval":
            self._render_approval_view(page, spec, design, x, y, w, max_y)
        elif layout == "document_review":
            self._render_document_review_view(page, spec, design, x, y, w, max_y)
        elif layout == "report":
            self._render_report_view(page, spec, design, x, y, w, max_y)
        elif layout == "detail":
            self._render_detail_view(page, spec, design, x, y, w, max_y)
        elif layout == "workflow":
            self._render_workflow_view(page, spec, design, x, y, w, max_y)
        elif layout == "work_queue":
            self._render_table_view(page, spec, design, x, y, w, max_y)
        elif layout == "form":
            self._render_form_view(page, spec, design, x, y, w, max_y)
        elif layout == "overview":
            self._render_dashboard_view(page, spec, design, x, y, w, max_y)
        else:
            self._render_detail_view(page, spec, design, x, y, w, max_y)

    def _classify_layout(self, spec: ScreenSpecification) -> str:
        """Map screen intent to a stable layout archetype without changing API models."""
        screen_type = re.sub(r"[^a-z0-9]+", "_", spec.screen_type.lower()).strip("_")
        explicit_layouts = {
            "create_form": "form",
            "edit_form": "form",
            "form": "form",
            "login": "form",
            "configuration": "form",
            "settings": "form",
            "dashboard": "overview",
            "overview": "overview",
            "work_queue": "work_queue",
            "search": "work_queue",
            "list": "work_queue",
            "tracker": "work_queue",
            "audit": "work_queue",
            "audit_trail": "work_queue",
            "report": "report",
            "adhoc_report": "report",
            "analytics": "report",
            "approval": "approval",
            "approval_checkpoint": "approval",
            "document_viewer": "document_review",
            "document_review": "document_review",
            "detail_view": "detail",
            "case_detail": "detail",
            "workflow_stepper": "workflow",
            "wizard": "workflow",
        }
        if screen_type in explicit_layouts:
            return explicit_layouts[screen_type]

        # An explicit form or record type must not be overridden by broad purpose words
        # such as "onboarding", "review", or "approval".
        if screen_type.endswith("_form"):
            return "form"
        if screen_type.endswith("_detail"):
            return "detail"

        identity = " ".join((spec.name, spec.purpose, screen_type)).lower()
        component_types = " ".join(component.type.lower() for component in spec.components)
        components = " ".join((identity, component_types))

        if any(word in components for word in ("document", "attachment", "file_viewer", "contract")):
            return "document_review"
        if any(word in components for word in ("approval", "approve", "decision", "adjudicat")):
            return "approval"
        if any(component.steps for component in spec.components) or any(
            word in components for word in ("workflow_stepper", "wizard", "guided_setup")
        ):
            return "workflow"
        if any(word in components for word in ("analytics", "report", "trend", "performance_metric")):
            return "report"
        if any(word in components for word in ("work_queue", "queue", "inbox", "tracker", "search", "list")):
            return "work_queue"
        if any(word in components for word in ("create_form", "edit_form", "form", "data_entry")):
            return "form"
        if any(word in components for word in ("login", "sign_in", "configuration", "settings")):
            return "form"
        if any(word in components for word in ("detail_view", "case", "record_detail", "profile", "casefile")):
            return "detail"
        if any(word in components for word in ("audit", "history", "activity_log")):
            return "work_queue"
        if any(word in components for word in ("dashboard", "overview", "home")):
            return "overview"

        component_types = {component.type.lower() for component in spec.components}
        if any("table" in component_type for component_type in component_types) or spec.tables:
            return "work_queue"
        if "form" in component_types or spec.fields:
            return "form"
        return "detail"

    def _render_approval_view(self, page, spec, design, x, y, w, max_y) -> None:
        primary = self._hex_to_rgb(design.primary_color, (0.12, 0.25, 0.69))
        border = (0.88, 0.90, 0.93)
        dark = (0.09, 0.12, 0.18)
        muted = (0.42, 0.48, 0.55)
        bottom = max_y - 10
        left_w = w * 0.68
        right_x = x + left_w + 16
        right_w = w - left_w - 16

        page.draw_rect(pymupdf.Rect(x, y, x + left_w, bottom), fill=(1, 1, 1), color=border, width=0.8)
        page.draw_rect(pymupdf.Rect(x, y, x + left_w, y + 42), fill=(0.95, 0.97, 1), color=border, width=0.8)
        page.insert_text((x + 18, y + 27), "REVIEW CONTEXT", fontsize=10, color=primary, fontname="hebo")
        if spec.workflow_state:
            self._draw_status_badge(page, x + left_w - 150, y + 11, spec.workflow_state)

        fields = self._resolve_form_fields(spec)
        if fields:
            field_y = y + 72
            for field in fields[:7]:
                page.insert_text((x + 20, field_y), field.label[:34].upper(), fontsize=8, color=muted, fontname="hebo")
                value = field.value or field.placeholder or "Not provided"
                page.insert_text((x + 20, field_y + 19), str(value)[:62], fontsize=11, color=dark, fontname="helv")
                page.draw_line((x + 20, field_y + 29), (x + left_w - 20, field_y + 29), color=border, width=0.5)
                field_y += 48
        else:
            page.insert_text((x + 20, y + 80), spec.purpose[:105], fontsize=12, color=dark, fontname="helv")
            if spec.tables:
                row = (spec.tables[0].rows or [{}])[0]
                field_y = y + 120
                for key, value in list(row.items())[:6]:
                    page.insert_text((x + 20, field_y), str(key).upper()[:30], fontsize=8, color=muted, fontname="hebo")
                    page.insert_text((x + 20, field_y + 18), str(value)[:62], fontsize=11, color=dark, fontname="helv")
                    field_y += 44

        page.draw_rect(pymupdf.Rect(right_x, y, right_x + right_w, bottom), fill=(1, 1, 1), color=border, width=0.8)
        page.draw_rect(pymupdf.Rect(right_x, y, right_x + right_w, y + 42), fill=(0.97, 0.98, 0.99), color=border, width=0.8)
        page.insert_text((right_x + 16, y + 27), "DECISION", fontsize=10, color=dark, fontname="hebo")
        cursor_y = y + 66
        for heading, items in (
            ("BUSINESS RULES", spec.business_rules),
            ("NOTES", spec.notifications),
        ):
            if not items:
                continue
            page.insert_text((right_x + 16, cursor_y), heading, fontsize=8, color=muted, fontname="hebo")
            cursor_y += 20
            for item in items[:3]:
                page.draw_circle(pymupdf.Point(right_x + 20, cursor_y - 3), 2, fill=primary, color=None)
                page.insert_text((right_x + 30, cursor_y), str(item)[:43], fontsize=9, color=dark, fontname="helv")
                cursor_y += 30
        for action in spec.actions[:3]:
            if cursor_y + 38 > bottom:
                break
            fill = primary if action.type == "primary" else (1, 1, 1)
            color = (1, 1, 1) if action.type == "primary" else dark
            page.draw_rect(pymupdf.Rect(right_x + 16, cursor_y, right_x + right_w - 16, cursor_y + 30),
                           fill=fill, color=primary if action.type == "primary" else border, width=0.8)
            page.insert_text((right_x + 28, cursor_y + 20), action.label[:32], fontsize=10, color=color, fontname="hebo")
            cursor_y += 38

    def _render_document_review_view(self, page, spec, design, x, y, w, max_y) -> None:
        primary = self._hex_to_rgb(design.primary_color, (0.12, 0.25, 0.69))
        border = (0.88, 0.90, 0.93)
        dark = (0.09, 0.12, 0.18)
        muted = (0.42, 0.48, 0.55)
        bottom = max_y - 10
        viewer_w = w * 0.64
        review_x = x + viewer_w + 16
        review_w = w - viewer_w - 16

        page.draw_rect(pymupdf.Rect(x, y, x + viewer_w, bottom), fill=(0.93, 0.94, 0.95), color=border, width=0.8)
        paper = pymupdf.Rect(x + 34, y + 22, x + viewer_w - 34, bottom - 22)
        page.draw_rect(paper, fill=(1, 1, 1), color=border, width=0.8)
        page.insert_text((paper.x0 + 24, paper.y0 + 32), (spec.components[0].title if spec.components and spec.components[0].title else spec.name)[:55],
                         fontsize=13, color=dark, fontname="hebo")
        page.insert_text((paper.x0 + 24, paper.y0 + 55), spec.purpose[:80], fontsize=9, color=muted, fontname="helv")
        fields = self._resolve_form_fields(spec)
        table_columns = self._resolve_table_columns(spec)
        rows = self._resolve_table_rows(spec, table_columns)
        component_notes = [
            component.description for component in spec.components if component.description
        ]
        content_lines = [(field.label, field.value or field.placeholder or "") for field in fields[:5]]
        if not content_lines:
            content_lines = [
                (str(key), str(value))
                for row in rows[:4]
                for key, value in list(row.items())[:3]
            ][:8]
        if not content_lines:
            content_lines = [(f"Review note {index + 1}", note) for index, note in enumerate(component_notes[:5])]
        for idx, (label, value) in enumerate(content_lines[:8]):
            line_y = paper.y0 + 96 + idx * 64
            page.insert_text((paper.x0 + 24, line_y), label[:44], fontsize=9, color=primary, fontname="hebo")
            page.insert_text((paper.x0 + 24, line_y + 20), value[:70] or "Value not provided",
                             fontsize=10, color=dark, fontname="helv")
            page.draw_line((paper.x0 + 24, line_y + 30), (paper.x1 - 24, line_y + 30), color=border, width=0.6)
        if not content_lines:
            page.draw_rect(pymupdf.Rect(paper.x0 + 24, paper.y0 + 96, paper.x1 - 24, paper.y0 + 180),
                           fill=(0.97, 0.98, 0.99), color=border, width=0.7)
            page.insert_text((paper.x0 + 40, paper.y0 + 130), "Document preview unavailable",
                             fontsize=11, color=dark, fontname="hebo")
            page.insert_text((paper.x0 + 40, paper.y0 + 152), "No document content was supplied for this screen.",
                             fontsize=9, color=muted, fontname="helv")

        page.draw_rect(pymupdf.Rect(review_x, y, review_x + review_w, bottom), fill=(1, 1, 1), color=border, width=0.8)
        page.draw_rect(pymupdf.Rect(review_x, y, review_x + review_w, y + 42), fill=(0.97, 0.98, 0.99), color=border, width=0.8)
        page.insert_text((review_x + 16, y + 27), "REVIEW PANEL", fontsize=10, color=dark, fontname="hebo")
        cursor_y = y + 68
        for heading, items in (("WORKFLOW", [spec.workflow_state] if spec.workflow_state else []),
                               ("REQUIREMENTS", spec.business_rules),
                               ("ANNOTATIONS", spec.notifications or component_notes)):
            if not items:
                continue
            page.insert_text((review_x + 16, cursor_y), heading, fontsize=8, color=muted, fontname="hebo")
            cursor_y += 19
            for item in items[:4]:
                page.draw_rect(pymupdf.Rect(review_x + 16, cursor_y - 12, review_x + 20, cursor_y + 10),
                               fill=primary, color=None)
                page.insert_text((review_x + 28, cursor_y), str(item)[:44], fontsize=9, color=dark, fontname="helv")
                cursor_y += 30
        if not any((spec.workflow_state, spec.business_rules, spec.notifications, component_notes, spec.actions)):
            page.insert_text((review_x + 16, cursor_y + 8), "No review notes or actions supplied.",
                             fontsize=9, color=muted, fontname="helv")
        elif spec.data_sources:
            page.insert_text((review_x + 16, cursor_y + 8), "SOURCE: " + ", ".join(spec.data_sources[:2])[:44],
                             fontsize=8, color=muted, fontname="helv")
        for action in spec.actions[:2]:
            if cursor_y + 38 > bottom:
                break
            page.draw_rect(pymupdf.Rect(review_x + 16, cursor_y, review_x + review_w - 16, cursor_y + 30),
                           fill=primary if action.type == "primary" else (1, 1, 1),
                           color=primary if action.type == "primary" else border, width=0.8)
            page.insert_text((review_x + 28, cursor_y + 20), action.label[:30], fontsize=9,
                             color=(1, 1, 1) if action.type == "primary" else dark, fontname="hebo")
            cursor_y += 38

    def _render_report_view(self, page, spec, design, x, y, w, max_y) -> None:
        primary = self._hex_to_rgb(design.primary_color, (0.12, 0.25, 0.69))
        border = (0.88, 0.90, 0.93)
        dark = (0.09, 0.12, 0.18)
        muted = (0.42, 0.48, 0.55)
        bottom = max_y - 10
        filters = [field.label for field in self._resolve_form_fields(spec)[:4]] if spec.fields or any(c.fields for c in spec.components) else []
        page.draw_rect(pymupdf.Rect(x, y, x + w, y + 42), fill=(1, 1, 1), color=border, width=0.8)
        page.insert_text((x + 16, y + 26), "REPORT PARAMETERS", fontsize=8, color=muted, fontname="hebo")
        filter_text = "   |   ".join(filters) if filters else spec.purpose
        page.insert_text((x + 175, y + 26), filter_text[:100], fontsize=9, color=dark, fontname="helv")

        metrics = spec.header_stats or [
            stat for component in spec.components for stat in component.stats
        ]
        columns = self._resolve_table_columns(spec)
        rows = self._resolve_table_rows(spec, columns)
        has_tabular_data = bool(rows)
        chart_top = y + 58
        metric_rows = max(1, (min(len(metrics), 8) + 1) // 2)
        metric_panel_height = 42 + metric_rows * 52
        chart_bottom = min(bottom - 176, chart_top + metric_panel_height) if metrics else chart_top
        chart_x = x + 24
        chart_w = w - 48
        if metrics:
            page.draw_rect(pymupdf.Rect(x, chart_top, x + w, chart_bottom), fill=(1, 1, 1), color=border, width=0.8)
            page.insert_text((chart_x, chart_top + 24), "PERFORMANCE INDICATORS", fontsize=9, color=muted, fontname="hebo")
            gap = 12.0
            card_w = (chart_w - gap) / 2
            for index, stat in enumerate(metrics[:8]):
                col = index % 2
                row = index // 2
                card_x = chart_x + col * (card_w + gap)
                card_y = chart_top + 34 + row * 52
                page.draw_rect(pymupdf.Rect(card_x, card_y, card_x + card_w, card_y + 46),
                               fill=(0.98, 0.99, 1.0), color=border, width=0.6)
                page.draw_rect(pymupdf.Rect(card_x, card_y, card_x + 3, card_y + 46), fill=primary, color=None)
                page.insert_text((card_x + 12, card_y + 16), stat.label[:32], fontsize=8, color=muted, fontname="helv")
                page.insert_text((card_x + 12, card_y + 36), stat.value[:18], fontsize=11, color=dark, fontname="hebo")
                if stat.change:
                    page.insert_text((card_x + card_w - 100, card_y + 36), stat.change[:15],
                                     fontsize=8, color=primary, fontname="hebo")
        content_y = chart_bottom + (14 if metrics else 0)
        distribution = self._report_distribution(columns, rows)
        if distribution:
            category_column, category_counts = distribution
            chart_height = 50 + len(category_counts) * 27
            chart_bottom = min(bottom - 180, content_y + chart_height)
            page.draw_rect(pymupdf.Rect(x, content_y, x + w, chart_bottom),
                           fill=(1, 1, 1), color=border, width=0.8)
            page.insert_text((x + 18, content_y + 23), f"RECORDS BY {category_column.upper()[:34]}",
                             fontsize=9, color=muted, fontname="hebo")
            max_count = max(count for _, count in category_counts)
            bar_x = x + 270
            bar_w = w - 360
            for index, (category, count) in enumerate(category_counts):
                row_y = content_y + 42 + index * 27
                page.insert_text((x + 18, row_y + 13), category[:32], fontsize=9, color=dark, fontname="helv")
                page.draw_rect(pymupdf.Rect(bar_x, row_y, bar_x + bar_w, row_y + 14),
                               fill=(0.94, 0.96, 0.98), color=None)
                page.draw_rect(pymupdf.Rect(bar_x, row_y, bar_x + bar_w * count / max_count, row_y + 14),
                               fill=primary, color=None)
                page.insert_text((bar_x + bar_w + 12, row_y + 12), str(count),
                                 fontsize=9, color=dark, fontname="hebo")
            content_y = chart_bottom + 14

        table_y = content_y
        if has_tabular_data:
            table_bottom = min(bottom, table_y + 160 + len(rows) * 36)
            self._render_table_view(page, spec, design, x, table_y, w, table_bottom)
        else:
            supporting_content = spec.business_rules or [
                component.description for component in spec.components if component.description
            ]
            if supporting_content:
                panel_bottom = min(bottom, table_y + 54 + min(len(supporting_content), 3) * 24)
                page.draw_rect(pymupdf.Rect(x, table_y, x + w, panel_bottom),
                               fill=(1, 1, 1), color=border, width=0.8)
                page.insert_text((x + 18, table_y + 26), "REPORT CONTEXT", fontsize=9, color=muted, fontname="hebo")
                for idx, detail in enumerate(supporting_content[:3]):
                    page.insert_text((x + 18, table_y + 54 + idx * 24), str(detail)[:120],
                                     fontsize=9, color=dark, fontname="helv")
            else:
                page.draw_rect(pymupdf.Rect(x, table_y, x + w, min(bottom, table_y + 82)),
                               fill=(0.97, 0.98, 0.99), color=border, width=0.7)
                page.insert_text((x + 18, table_y + 34), "Report data not supplied",
                                 fontsize=11, color=dark, fontname="hebo")
                page.insert_text((x + 18, table_y + 58), "Add metrics or a result table to populate this analysis.",
                                 fontsize=9, color=muted, fontname="helv")

    def _report_distribution(self, columns, rows):
        if not rows:
            return []
        preferred = ("status", "region", "category", "type", "department", "group")
        column = next(
            (name for token in preferred for name in columns if token in name.lower()),
            next((name for name in columns if not any(token in name.lower() for token in ("id", "date", "time"))), None),
        )
        if not column:
            return []
        counts = {}
        for row in rows:
            value = str(row.get(column, "")).strip()
            if value:
                counts[value] = counts.get(value, 0) + 1
        return column, sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:5]

    def _render_detail_view(self, page, spec, design, x, y, w, max_y) -> None:
        primary = self._hex_to_rgb(design.primary_color, (0.12, 0.25, 0.69))
        border = (0.88, 0.90, 0.93)
        dark = (0.09, 0.12, 0.18)
        muted = (0.42, 0.48, 0.55)
        bottom = max_y - 10
        main_w = w * 0.7
        rail_x = x + main_w + 16
        rail_w = w - main_w - 16
        page.draw_rect(pymupdf.Rect(x, y, x + main_w, bottom), fill=(1, 1, 1), color=border, width=0.8)
        page.draw_rect(pymupdf.Rect(x, y, x + main_w, y + 42), fill=(0.96, 0.97, 0.99), color=border, width=0.8)
        page.insert_text((x + 18, y + 27), "RECORD SUMMARY", fontsize=10, color=dark, fontname="hebo")
        fields = self._resolve_form_fields(spec)
        if spec.fields or any(component.fields for component in spec.components):
            fields = [field for field in fields if field.label not in {"Primary Identifier", "Business Category"}]
        if fields:
            col_w = (main_w - 54) / 2
            for index, field in enumerate(fields[:10]):
                col = index % 2
                row = index // 2
                fx = x + 20 + col * (col_w + 14)
                fy = y + 76 + row * 72
                page.insert_text((fx, fy), field.label[:32], fontsize=9, color=muted, fontname="helv")
                page.insert_text((fx, fy + 22), (field.value or field.placeholder or "Not provided")[:38],
                                 fontsize=11, color=dark, fontname="hebo")
                page.draw_line((fx, fy + 33), (fx + col_w, fy + 33), color=border, width=0.6)
        elif spec.tables and spec.tables[0].rows:
            row = spec.tables[0].rows[0]
            for index, (label, value) in enumerate(list(row.items())[:10]):
                fy = y + 76 + index * 42
                page.insert_text((x + 20, fy), str(label)[:28], fontsize=9, color=muted, fontname="helv")
                page.insert_text((x + 230, fy), str(value)[:55], fontsize=10, color=dark, fontname="hebo")
        else:
            page.insert_text((x + 20, y + 78), spec.purpose[:110], fontsize=11, color=dark, fontname="helv")

        page.draw_rect(pymupdf.Rect(rail_x, y, rail_x + rail_w, bottom), fill=(1, 1, 1), color=border, width=0.8)
        page.insert_text((rail_x + 16, y + 27), "ACTIVITY & RULES", fontsize=9, color=primary, fontname="hebo")
        cursor_y = y + 60
        for heading, items in (("STATUS", [spec.workflow_state] if spec.workflow_state else []),
                               ("BUSINESS RULES", spec.business_rules),
                               ("UPDATES", spec.notifications)):
            if not items:
                continue
            page.insert_text((rail_x + 16, cursor_y), heading, fontsize=8, color=muted, fontname="hebo")
            cursor_y += 18
            for item in items[:3]:
                if cursor_y > bottom - 20:
                    break
                page.insert_text((rail_x + 16, cursor_y), str(item)[:45], fontsize=9, color=dark, fontname="helv")
                cursor_y += 29

    def _render_workflow_view(self, page, spec, design, x, y, w, max_y) -> None:
        primary = self._hex_to_rgb(design.primary_color, (0.12, 0.25, 0.69))
        border = (0.88, 0.90, 0.93)
        muted = (0.42, 0.48, 0.55)
        steps = next((component.steps for component in spec.components if component.steps), [])
        step_rect = pymupdf.Rect(x, y, x + w, y + 62)
        page.draw_rect(step_rect, fill=(1, 1, 1), color=border, width=0.8)
        if steps:
            step_w = (w - 32) / len(steps)
            for idx, step in enumerate(steps[:6]):
                sx = x + 16 + idx * step_w
                page.draw_circle(pymupdf.Point(sx + 12, y + 22), 10,
                                 fill=primary if idx == 0 else (0.92, 0.94, 0.97), color=None)
                page.insert_text((sx + 9, y + 25), str(idx + 1), fontsize=8,
                                 color=(1, 1, 1) if idx == 0 else muted, fontname="hebo")
                page.insert_text((sx + 28, y + 25), str(step)[:22], fontsize=9, color=muted, fontname="helv")
                if idx < len(steps) - 1:
                    page.draw_line((sx + step_w - 12, y + 22), (sx + step_w + 4, y + 22), color=border, width=1)
        else:
            page.insert_text((x + 18, y + 26), "Workflow steps were not provided for this screen.",
                             fontsize=10, color=muted, fontname="helv")
        self._render_form_view(page, spec, design, x, y + 76, w, max_y)

    def _render_table_view(
        self,
        page: pymupdf.Page,
        spec: ScreenSpecification,
        design: DesignContext,
        x: float,
        y: float,
        w: float,
        max_y: float
    ) -> None:
        c_primary = self._hex_to_rgb(design.primary_color, (0.12, 0.25, 0.69))
        c_border = (0.88, 0.90, 0.93)
        c_card = (1.0, 1.0, 1.0)
        c_text_dark = (0.09, 0.12, 0.18)
        c_text_muted = (0.42, 0.48, 0.55)

        # Filter and Search bar above table
        filter_bar_h = 42.0
        page.draw_rect(pymupdf.Rect(x, y, x + w, y + filter_bar_h), fill=c_card, color=c_border, radius=0.1, width=0.8)
        has_fields = bool(spec.fields or any(component.fields for component in spec.components))
        filters = [field.label for field in self._resolve_form_fields(spec)[:3]] if has_fields else []
        filter_x = x + 12
        filter_width = min(260.0, max(150.0, (w - 48) / max(1, min(len(filters), 3))))
        for label in filters:
            page.draw_rect(pymupdf.Rect(filter_x, y + 7, filter_x + filter_width, y + 35),
                           fill=(0.96, 0.97, 0.98), color=c_border, radius=0.1, width=0.8)
            page.insert_text((filter_x + 12, y + 23), label[:26], fontsize=9, color=c_text_dark, fontname="helv")
            filter_x += filter_width + 10
        export_action = next((action for action in spec.actions if "export" in action.label.lower()), None)
        if export_action:
            page.draw_rect(pymupdf.Rect(x + w - 130, y + 7, x + w - 12, y + 35),
                           fill=(0.95, 0.97, 1.0), color=c_border, radius=0.1, width=0.8)
            page.insert_text((x + w - 118, y + 23), export_action.label[:18], fontsize=9, color=c_primary, fontname="hebo")

        table_y = y + filter_bar_h + 16
        table_title = next((table.title for table in spec.tables if table.title), "")
        if not table_title:
            table_title = next(
                (
                    component.title
                    for component in spec.components
                    if component.title and (component.columns or component.rows)
                ),
                "",
            )
        if table_title:
            page.insert_text((x + 4, table_y + 20), table_title[:64], fontsize=12,
                             color=c_text_dark, fontname="hebo")
            table_y += 34
        table_h = max_y - table_y - 20
        page.draw_rect(pymupdf.Rect(x, table_y, x + w, table_y + table_h), fill=c_card, color=c_border, radius=0.08, width=0.8)

        columns = self._resolve_table_columns(spec)
        th_h = 38.0
        rows = self._resolve_table_rows(spec, columns)
        row_y = table_y
        if columns:
            page.draw_rect(pymupdf.Rect(x, table_y, x + w, table_y + th_h), fill=(0.95, 0.96, 0.98), color=c_border, width=0.8)
            col_w = w / len(columns)
            for i, col in enumerate(columns):
                cx = x + i * col_w
                page.insert_text((cx + 14, table_y + 24), col[:20].upper(), fontsize=9, color=(0.28, 0.32, 0.38), fontname="hebo")
            row_y += th_h

        row_h = 36.0
        max_rows = int((table_h - th_h - 44) / row_h)

        if not columns or not rows:
            empty_message = (
                "No table columns or rows were supplied for this screen."
                if not columns
                else "No example rows were supplied."
            )
            page.insert_text((x + 18, row_y + 34), empty_message,
                             fontsize=10, color=c_text_muted, fontname="helv")
        for r_idx, r_data in enumerate(rows[:max_rows]):
            bg = (1.0, 1.0, 1.0) if r_idx % 2 == 0 else (0.985, 0.99, 0.995)
            page.draw_rect(pymupdf.Rect(x, row_y, x + w, row_y + row_h), fill=bg, color=c_border, width=0.4)
            for c_idx, col_name in enumerate(columns):
                cx = x + c_idx * col_w
                val = str(r_data.get(col_name, "-"))
                if "status" in col_name.lower():
                    # Status Badge
                    self._draw_status_badge(page, cx + 12, row_y + 8, val)
                elif "action" in col_name.lower():
                    page.insert_text((cx + 14, row_y + 22), val[:24], fontsize=9, color=c_primary, fontname="hebo")
                else:
                    page.insert_text((cx + 14, row_y + 22), val[:24], fontsize=10, color=c_text_dark, fontname="helv")
            row_y += row_h

        # Pagination Footer
        pag_y = table_y + table_h - 38
        page.draw_rect(pymupdf.Rect(x, pag_y, x + w, table_y + table_h), fill=(0.98, 0.99, 1.0), color=c_border, width=0.6)
        pagination = next((table.pagination_info for table in spec.tables if table.pagination_info), "")
        if pagination:
            page.insert_text((x + 16, pag_y + 23), pagination[:70], fontsize=9, color=c_text_muted, fontname="helv")

    def _render_form_view(
        self,
        page: pymupdf.Page,
        spec: ScreenSpecification,
        design: DesignContext,
        x: float,
        y: float,
        w: float,
        max_y: float
    ) -> None:
        c_primary = self._hex_to_rgb(design.primary_color, (0.12, 0.25, 0.69))
        c_border = (0.88, 0.90, 0.93)
        c_card = (1.0, 1.0, 1.0)
        c_text_dark = (0.09, 0.12, 0.18)
        c_text_muted = (0.42, 0.48, 0.55)

        form_h = max_y - y - 10
        card_rect = pymupdf.Rect(x, y, x + w, y + form_h)
        page.draw_rect(card_rect, fill=c_card, color=c_border, radius=0.08, width=0.8)

        # Form Header Bar
        fh_h = 44.0
        page.draw_rect(pymupdf.Rect(x, y, x + w, y + fh_h), fill=(0.97, 0.98, 0.99), color=c_border, width=0.8)
        page.insert_text((x + 20, y + 27), f"{spec.name} - Input Specifications", fontsize=12, color=c_text_dark, fontname="hebo")

        # Resolve fields
        fields = self._resolve_form_fields(spec)
        f_y = y + fh_h + 20
        col_count = 2
        col_w = (w - 60) / col_count

        for i in range(0, len(fields), 2):
            if f_y > max_y - 80:
                break
            for c_idx in range(2):
                if i + c_idx < len(fields):
                    f = fields[i + c_idx]
                    fx = x + 24 + c_idx * (col_w + 24)
                    # Label
                    req_star = " *" if f.required else ""
                    page.insert_text((fx, f_y), f.label[:32] + req_star, fontsize=10, color=c_text_dark if not f.required else (0.8, 0.2, 0.2), fontname="hebo")
                    # Input Field Box
                    input_h = 36.0
                    input_rect = pymupdf.Rect(fx, f_y + 8, fx + col_w, f_y + 8 + input_h)
                    page.draw_rect(input_rect, fill=(0.985, 0.99, 1.0), color=c_border, radius=0.1, width=0.8)
                    val_text = f.value or f.placeholder or f"Enter {f.label}..."
                    if f.type == "select":
                        val_text += "  [v]"
                    page.insert_text((fx + 12, f_y + 30), val_text[:40], fontsize=10, color=c_text_dark if f.value else c_text_muted, fontname="helv")
            f_y += 68
        if not fields:
            page.insert_text((x + 24, f_y + 10), spec.purpose[:110], fontsize=11, color=c_text_muted, fontname="helv")

        # Form Action Bar at Bottom of Card
        action_y = y + form_h - 52
        page.draw_rect(pymupdf.Rect(x, action_y, x + w, y + form_h), fill=(0.98, 0.99, 1.0), color=c_border, width=0.8)
        button_x = x + w - 20
        for action in reversed(spec.actions[:3]):
            button_w = min(190.0, max(92.0, len(action.label) * 7.0 + 24))
            button_x -= button_w
            button_fill = (0.84, 0.18, 0.18) if action.type == "danger" else (
                c_primary if action.type == "primary" else (1, 1, 1)
            )
            button_text = (1, 1, 1) if action.type in {"primary", "danger"} else c_text_dark
            page.draw_rect(pymupdf.Rect(button_x, action_y + 10, button_x + button_w, action_y + 42),
                           fill=button_fill,
                           color=button_fill if action.type in {"primary", "danger"} else c_border,
                           radius=0.1, width=0.8)
            page.insert_text((button_x + 12, action_y + 30), action.label[:22], fontsize=9,
                             color=button_text, fontname="hebo")
            button_x -= 10

    def _render_dashboard_view(
        self,
        page: pymupdf.Page,
        spec: ScreenSpecification,
        design: DesignContext,
        x: float,
        y: float,
        w: float,
        max_y: float
    ) -> None:
        c_border = (0.88, 0.90, 0.93)
        c_card = (1.0, 1.0, 1.0)
        c_text_dark = (0.09, 0.12, 0.18)
        c_text_muted = (0.42, 0.48, 0.55)

        components = spec.components[:3]
        if not components:
            page.draw_rect(pymupdf.Rect(x, y, x + w, max_y - 10), fill=c_card, color=c_border, width=0.8)
            page.insert_text((x + 22, y + 38), spec.purpose[:120], fontsize=12, color=c_text_dark, fontname="helv")
            return

        gap = 16.0
        main_w = w * 0.64
        rail_x = x + main_w + gap
        rail_w = w - main_w - gap
        main_h = max_y - y - 10
        for index, component in enumerate(components):
            if index == 0:
                cx, cy, cw, ch = x, y, main_w, main_h * 0.56
            elif index == 1:
                cx, cy, cw, ch = rail_x, y, rail_w, main_h * 0.56
            else:
                cx, cy, cw, ch = x, y + main_h * 0.56 + 14, w, main_h * 0.44 - 14
            page.draw_rect(pymupdf.Rect(cx, cy, cx + cw, cy + ch), fill=c_card, color=c_border, width=0.8)
            heading = component.title or component.type.replace("_", " ").title()
            page.insert_text((cx + 16, cy + 24), heading[:48], fontsize=11, color=c_text_dark, fontname="hebo")
            if component.description:
                page.insert_text((cx + 16, cy + 42), component.description[:105], fontsize=9, color=c_text_muted, fontname="helv")
            if component.stats:
                stat_y = cy + 70
                for stat in component.stats[:4]:
                    page.insert_text((cx + 18, stat_y), stat.label[:28], fontsize=9, color=c_text_muted, fontname="helv")
                    page.insert_text((cx + cw - 100, stat_y), stat.value[:16], fontsize=12, color=c_text_dark, fontname="hebo")
                    stat_y += 34
            elif component.rows:
                row_y = cy + 60
                for row in component.rows[:max(1, min(5, int((ch - 72) / 28)))]:
                    row_text = "  |  ".join(f"{key}: {value}" for key, value in list(row.items())[:3])
                    page.insert_text((cx + 16, row_y), row_text[:115], fontsize=9, color=c_text_dark, fontname="helv")
                    row_y += 26
            elif component.steps:
                page.insert_text((cx + 16, cy + 72), "  >  ".join(component.steps[:5])[:110],
                                 fontsize=10, color=c_text_dark, fontname="helv")
            elif component.fields:
                details = "  |  ".join(field.label for field in component.fields[:5])
                page.insert_text((cx + 16, cy + 72), details[:100], fontsize=9, color=c_text_muted, fontname="helv")
            else:
                page.insert_text((cx + 16, cy + 70), component.description or spec.purpose[:90],
                                 fontsize=9, color=c_text_muted, fontname="helv")

    def _render_mixed_view(self, page, spec, design, x, y, w, max_y):
        # Default mixed detail view
        self._render_table_view(page, spec, design, x, y, w, max_y)

    def _render_card_header(self, page: pymupdf.Page, x: float, y: float, w: float, title: str):
        c_border = (0.88, 0.90, 0.93)
        page.draw_rect(pymupdf.Rect(x, y, x + w, y + 36), fill=(0.96, 0.97, 0.98), color=c_border, radius=0.1, width=0.8)
        page.insert_text((x + 16, y + 23), title.upper(), fontsize=10, color=(0.15, 0.18, 0.25), fontname="hebo")

    def _draw_status_badge(self, page: pymupdf.Page, x: float, y: float, text: str) -> None:
        lower = text.lower()
        if any(w in lower for w in ["active", "approved", "completed", "resolved", "success"]):
            fill = (0.90, 0.97, 0.92)
            border = (0.70, 0.88, 0.74)
            color = (0.12, 0.52, 0.24)
        elif any(w in lower for w in ["pending", "review", "draft", "in progress"]):
            fill = (1.0, 0.96, 0.88)
            border = (0.98, 0.86, 0.65)
            color = (0.75, 0.45, 0.05)
        elif any(w in lower for w in ["reject", "fail", "high", "error", "closed"]):
            fill = (0.99, 0.91, 0.91)
            border = (0.96, 0.72, 0.72)
            color = (0.78, 0.18, 0.18)
        else:
            fill = (0.94, 0.95, 0.97)
            border = (0.82, 0.85, 0.90)
            color = (0.32, 0.36, 0.42)

        badge_w = max(68.0, len(text) * 7.0 + 16)
        rect = pymupdf.Rect(x, y, x + badge_w, y + 20)
        page.draw_rect(rect, fill=fill, color=border, radius=0.3, width=0.6)
        page.insert_text((x + 8, y + 14), text[:16], fontsize=8, color=color, fontname="hebo")

    def _resolve_table_columns(self, spec: ScreenSpecification) -> List[str]:
        for c in spec.components:
            if c.columns:
                return c.columns[:6]
        for table in spec.tables:
            if table.columns:
                return table.columns[:6]
        for component in spec.components:
            if component.rows:
                row_columns = list(component.rows[0].keys())
                if row_columns:
                    return row_columns[:6]
        for table in spec.tables:
            if table.rows:
                row_columns = list(table.rows[0].keys())
                if row_columns:
                    return row_columns[:6]
        return []

    def _resolve_table_rows(self, spec: ScreenSpecification, columns: List[str]) -> List[Dict[str, Any]]:
        for c in spec.components:
            if c.rows and len(c.rows) > 0:
                return c.rows
        if spec.tables and len(spec.tables) > 0 and spec.tables[0].rows:
            return spec.tables[0].rows
        return []

    def _resolve_form_fields(self, spec: ScreenSpecification) -> List[ScreenField]:
        fields: List[ScreenField] = []
        seen_labels = set()
        for c in spec.components:
            for field in c.fields:
                label = field.label.casefold()
                if label not in seen_labels:
                    fields.append(field)
                    seen_labels.add(label)
        for field in spec.fields:
            label = field.label.casefold()
            if label not in seen_labels:
                fields.append(field)
                seen_labels.add(label)
        return fields

    def _hex_to_rgb(self, hex_code: Optional[str], fallback: Tuple[float, float, float]) -> Tuple[float, float, float]:
        if not hex_code or not isinstance(hex_code, str):
            return fallback
        clean = hex_code.strip().lstrip("#")
        if len(clean) == 3:
            clean = "".join(c * 2 for c in clean)
        if len(clean) == 6:
            try:
                r = int(clean[0:2], 16) / 255.0
                g = int(clean[2:4], 16) / 255.0
                b = int(clean[4:6], 16) / 255.0
                return (r, g, b)
            except ValueError:
                pass
        return fallback


image_generation_service = ImageGenerationService()
