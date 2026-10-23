import io
import logging
from typing import Any, Dict, List, Optional
import pymupdf  # PyMuPDF for vector-quality UI layout & rendering
from PIL import Image
from app.api.schemas import (
    DesignContext,
    ScreenComponent,
    ScreenField,
    ScreenSpecification,
    ScreenTable,
)
from app.services.image_generation_service import image_generation_service

logger = logging.getLogger(__name__)


class WireframeService:
    """
    Renders structural, low-fidelity, greyscale wireframe PNGs with PyMuPDF.
    Includes architectural zone annotations (red dotted outlines and badges)
    and a semi-transparent WIREFRAME watermark.
    """

    def render_wireframe(self, spec: ScreenSpecification, design: Optional[DesignContext] = None) -> bytes:
        doc = pymupdf.open()
        width = 1600.0
        height = 920.0
        page = doc.new_page(width=width, height=height)

        # Greyscale Palette
        c_bg = (0.96, 0.965, 0.97)          # #F5F6F8
        c_card = (1.0, 1.0, 1.0)             # #FFFFFF
        c_card_alt = (0.93, 0.94, 0.95)     # #EDEFF2
        c_border = (0.65, 0.68, 0.72)       # #A6AEB8
        c_border_light = (0.80, 0.82, 0.85) # #CCD1D9
        c_text_dark = (0.15, 0.17, 0.20)    # #262B33
        c_text_muted = (0.45, 0.48, 0.52)   # #737A85
        c_annot = (0.85, 0.20, 0.20)        # Dotted Red Zone Annotation

        layout = image_generation_service._classify_layout(spec)
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

        show_navigation = len(nav_labels) > 1 and spec.screen_type.lower() != "login"
        sidebar_width = 240.0 if show_navigation else 0.0

        # 1. Background
        page.draw_rect(pymupdf.Rect(0, 0, width, height), fill=c_bg, color=None)

        # 2. Header Bar
        header_height = 64.0
        header_rect = pymupdf.Rect(0, 0, width, header_height)
        page.draw_rect(header_rect, fill=c_card, color=c_border, width=0.8)
        # Structural header elements
        app_title = design.brand_name if (design and design.brand_name) else "APPLICATION SYSTEM"
        page.draw_rect(pymupdf.Rect(24, 16, 50, 48), fill=c_card_alt, color=c_border, width=0.8)
        page.insert_text((34, 38), "[LOGO]", fontsize=9, color=c_text_muted, fontname="hebo")
        page.insert_text((86, 38), f"[APP: {app_title[:28].upper()}]", fontsize=14, color=c_text_dark, fontname="hebo")

        # Right header elements (User role, actions)
        page.draw_rect(pymupdf.Rect(width - 240, 16, width - 24, 48), fill=c_card_alt, color=c_border, width=0.8)
        page.insert_text((width - 228, 36), f"[ROLE: {spec.user_role[:20].upper()}]", fontsize=10, color=c_text_dark, fontname="helv")

        # Zone annotation: HEADER
        self._draw_zone_annotation(page, header_rect, "HEADER")

        # 3. Sidebar Navigation (if applicable)
        if show_navigation:
            sidebar_rect = pymupdf.Rect(0, header_height, sidebar_width, height)
            page.draw_rect(sidebar_rect, fill=c_card, color=c_border, width=0.8)
            page.insert_text((24, header_height + 28), "[NAVIGATION MENU]", fontsize=9, color=c_text_muted, fontname="hebo")
            y_nav = header_height + 44
            for item in nav_labels[:11]:
                is_active = item.casefold() == active_nav_item.casefold()
                item_rect = pymupdf.Rect(16, y_nav, sidebar_width - 16, y_nav + 34)
                if is_active:
                    page.draw_rect(item_rect, fill=c_card_alt, color=c_border, width=1.0)
                    page.insert_text((28, y_nav + 22), f"> [ {item[:20]} ]", fontsize=11, color=c_text_dark, fontname="hebo")
                else:
                    page.draw_rect(item_rect, fill=None, color=c_border_light, width=0.5)
                    page.insert_text((28, y_nav + 22), f"  [ {item[:20]} ]", fontsize=10, color=c_text_muted, fontname="helv")
                y_nav += 40

            self._draw_zone_annotation(page, sidebar_rect, "NAVIGATION")

        # 4. Main Canvas Area
        content_x = sidebar_width + 24
        content_w = width - content_x - 24
        content_y = header_height + 18

        # 5. Screen Title & Breadcrumbs / Actions Row
        title_box_rect = pymupdf.Rect(content_x, content_y, content_x + content_w, content_y + 60)
        page.draw_rect(title_box_rect, fill=c_card, color=c_border, width=0.8)
        page.insert_text(
            (content_x + 16, content_y + 26),
            f"SCREEN {spec.sequence:02d}: {spec.name.upper()}  [TYPE: {spec.screen_type.upper()}]",
            fontsize=13,
            color=c_text_dark,
            fontname="hebo",
        )
        page.insert_text(
            (content_x + 16, content_y + 46),
            f"Purpose: {spec.purpose[:115]}",
            fontsize=9,
            color=c_text_muted,
            fontname="helv",
        )

        # Page-level actions in title bar
        if spec.actions:
            act_x = content_x + content_w - 16
            for act in reversed(spec.actions[:3]):
                act_len = max(len(act.label) * 8 + 24, 90)
                act_rect = pymupdf.Rect(act_x - act_len, content_y + 14, act_x, content_y + 46)
                page.draw_rect(act_rect, fill=c_card_alt, color=c_border, width=1.0)
                page.insert_text((act_x - act_len + 10, content_y + 34), f"[ {act.label[:16]} ]", fontsize=9, color=c_text_dark, fontname="hebo")
                act_x -= (act_len + 10)

        self._draw_zone_annotation(page, title_box_rect, "PAGE TITLE & ACTIONS")

        # 6. Render Body by Layout Archetype
        body_y = content_y + 74
        body_h = height - body_y - 36
        self._render_wireframe_body(page, spec, layout, content_x, body_y, content_w, body_h)

        # 7. Watermark "WIREFRAME" across page
        self._draw_watermark(page, width, height)

        # 8. Footer bar
        footer_rect = pymupdf.Rect(content_x, height - 28, content_x + content_w, height - 6)
        page.draw_rect(footer_rect, fill=c_card, color=c_border_light, width=0.5)
        page.insert_text(
            (content_x + 12, height - 14),
            f"WIREFRAME BLUEPRINT — Architectural Layout & Zone Placement Validation — Screen {spec.sequence} ({spec.name})",
            fontsize=8,
            color=c_text_muted,
            fontname="helv",
        )
        self._draw_zone_annotation(page, footer_rect, "FOOTER")

        # Generate PNG bytes
        pix = page.get_pixmap(dpi=120)
        png_bytes = pix.tobytes("png")
        doc.close()

        # Validate with PIL
        with Image.open(io.BytesIO(png_bytes)) as img:
            if img.format != "PNG" or img.width < 1024 or img.height < 576:
                raise RuntimeError("Wireframe renderer returned an invalid or low-resolution PNG.")
            img.verify()

        logger.info("Rendered wireframe for screen %s (sequence=%d, bytes=%d)", spec.screen_id, spec.sequence, len(png_bytes))
        return png_bytes

    def _render_wireframe_body(self, page, spec: ScreenSpecification, layout: str, x: float, y: float, w: float, h: float):
        c_card = (1.0, 1.0, 1.0)
        c_card_alt = (0.93, 0.94, 0.95)
        c_border = (0.65, 0.68, 0.72)
        c_border_light = (0.80, 0.82, 0.85)
        c_text_dark = (0.15, 0.17, 0.20)
        c_text_muted = (0.45, 0.48, 0.52)

        if layout == "overview":
            # KPI Tiles on top (height: 100), then 2 split panels below
            kpi_h = 100.0
            kpi_rect = pymupdf.Rect(x, y, x + w, y + kpi_h)
            page.draw_rect(kpi_rect, fill=c_card, color=c_border, width=0.8)
            stats = spec.header_stats if spec.header_stats else [
                {"label": "TOTAL RECORDS", "value": "1,248"},
                {"label": "PENDING REVIEW", "value": "42"},
                {"label": "PROCESSING RATE", "value": "98.4%"},
                {"label": "EXCEPTIONS", "value": "3"}
            ]
            tile_w = (w - 32) / max(len(stats[:4]), 1)
            for idx, stat in enumerate(stats[:4]):
                lbl = stat.label if hasattr(stat, "label") else stat.get("label", "METRIC")
                val = stat.value if hasattr(stat, "value") else stat.get("value", "0")
                tx = x + 16 + idx * tile_w
                tile_rect = pymupdf.Rect(tx, y + 12, tx + tile_w - 12, y + kpi_h - 12)
                page.draw_rect(tile_rect, fill=c_card_alt, color=c_border_light, width=0.8)
                page.insert_text((tx + 12, y + 36), f"[ KPI: {lbl[:24].upper()} ]", fontsize=9, color=c_text_muted, fontname="hebo")
                page.insert_text((tx + 12, y + 68), f"{val}", fontsize=18, color=c_text_dark, fontname="hebo")

            self._draw_zone_annotation(page, kpi_rect, "KPI TILES")

            # Lower split panels
            lower_y = y + kpi_h + 16
            lower_h = h - kpi_h - 16
            left_w = w * 0.58
            left_rect = pymupdf.Rect(x, lower_y, x + left_w, lower_y + lower_h)
            right_rect = pymupdf.Rect(x + left_w + 16, lower_y, x + w, lower_y + lower_h)

            self._draw_wireframe_table(page, spec, left_rect, "WORK QUEUE / RECENT ACTIVITY")
            self._draw_zone_annotation(page, left_rect, "DATA TABLE")

            self._draw_wireframe_details_panel(page, spec, right_rect, "SUMMARY & METRICS")
            self._draw_zone_annotation(page, right_rect, "DETAIL PANEL")

        elif layout in ("work_queue", "report"):
            # Full table view with top filter bar
            filter_h = 56.0
            filter_rect = pymupdf.Rect(x, y, x + w, y + filter_h)
            page.draw_rect(filter_rect, fill=c_card, color=c_border, width=0.8)
            page.insert_text((x + 16, y + 34), "[ FILTERS & SEARCH: Search Keyword | Status Dropdown | Date Range | (Filter Actions) ]", fontsize=10, color=c_text_muted, fontname="hebo")
            self._draw_zone_annotation(page, filter_rect, "FILTERS")

            table_y = y + filter_h + 14
            table_rect = pymupdf.Rect(x, table_y, x + w, y + h)
            self._draw_wireframe_table(page, spec, table_rect, "DATA GRID")
            self._draw_zone_annotation(page, table_rect, "DATA TABLE")

        elif layout == "form":
            # Form entry layout: Left wide form panel, right sidebar with rules/tips
            left_w = w * 0.68
            form_rect = pymupdf.Rect(x, y, x + left_w, y + h)
            side_rect = pymupdf.Rect(x + left_w + 16, y, x + w, y + h)

            self._draw_wireframe_form(page, spec, form_rect)
            self._draw_zone_annotation(page, form_rect, "FORM")

            self._draw_wireframe_sidebar_rules(page, spec, side_rect)
            self._draw_zone_annotation(page, side_rect, "BUSINESS RULES PANEL")

        elif layout == "approval":
            # Split review & decision panel
            left_w = w * 0.65
            review_rect = pymupdf.Rect(x, y, x + left_w, y + h)
            decision_rect = pymupdf.Rect(x + left_w + 16, y, x + w, y + h)

            self._draw_wireframe_form(page, spec, review_rect, title="CASE & APPLICATION RECORD")
            self._draw_zone_annotation(page, review_rect, "CASE DATA")

            self._draw_wireframe_decision_panel(page, spec, decision_rect)
            self._draw_zone_annotation(page, decision_rect, "DECISION CHECKPOINT")

        elif layout == "document_review":
            # Document review: left viewer mock, right form checklist
            left_w = w * 0.55
            doc_rect = pymupdf.Rect(x, y, x + left_w, y + h)
            chk_rect = pymupdf.Rect(x + left_w + 16, y, x + w, y + h)

            page.draw_rect(doc_rect, fill=c_card, color=c_border, width=0.8)
            page.draw_rect(pymupdf.Rect(x, y, x + left_w, y + 40), fill=c_card_alt, color=c_border, width=0.8)
            page.insert_text((x + 16, y + 26), "[ DOCUMENT VIEWER CANVAS ]", fontsize=11, color=c_text_dark, fontname="hebo")
            # Document mock placeholder lines
            page.insert_text((x + 30, y + 80), "[ ATTACHMENT PREVIEW / SCANNED PDF RENDERING ZONE ]", fontsize=11, color=c_text_muted, fontname="hebo")
            page.draw_rect(pymupdf.Rect(x + 24, y + 100, x + left_w - 24, y + h - 24), fill=c_card_alt, color=c_border_light, width=0.8)
            page.insert_text((x + 40, y + 130), "[ Page 1 of Document — OCR Text & Structural Preview ]", fontsize=10, color=c_text_muted, fontname="helv")
            self._draw_zone_annotation(page, doc_rect, "DOCUMENT VIEWER")

            self._draw_wireframe_form(page, spec, chk_rect, title="VERIFICATION CHECKLIST")
            self._draw_zone_annotation(page, chk_rect, "CHECKLIST")

        elif layout == "workflow":
            # Stepper bar on top, step content below
            step_h = 70.0
            step_rect = pymupdf.Rect(x, y, x + w, y + step_h)
            page.draw_rect(step_rect, fill=c_card, color=c_border, width=0.8)
            steps = ["1. Initiation", "2. Data Verification", "3. Document Upload", "4. Review & Submit"]
            comp_steps = [s for comp in spec.components if comp.steps for s in comp.steps]
            if comp_steps:
                steps = comp_steps[:4]
            step_w = (w - 32) / len(steps)
            for idx, stp in enumerate(steps):
                sx = x + 16 + idx * step_w
                page.draw_circle(pymupdf.Point(sx + 20, y + 36), 14, fill=c_card_alt, color=c_border, width=1.0)
                page.insert_text((sx + 15, y + 41), str(idx + 1), fontsize=10, color=c_text_dark, fontname="hebo")
                page.insert_text((sx + 42, y + 40), f"[ {stp[:22]} ]", fontsize=10, color=c_text_dark, fontname="hebo")
            self._draw_zone_annotation(page, step_rect, "WORKFLOW STEPPER")

            body_rect = pymupdf.Rect(x, y + step_h + 16, x + w, y + h)
            self._draw_wireframe_form(page, spec, body_rect, title="STEPPER FORM WORKSPACE")
            self._draw_zone_annotation(page, body_rect, "FORM")

        else:  # detail
            left_w = w * 0.62
            d_rect = pymupdf.Rect(x, y, x + left_w, y + h)
            r_rect = pymupdf.Rect(x + left_w + 16, y, x + w, y + h)

            self._draw_wireframe_form(page, spec, d_rect, title="RECORD ATTRIBUTES")
            self._draw_zone_annotation(page, d_rect, "DETAIL VIEW")

            self._draw_wireframe_details_panel(page, spec, r_rect, "ASSOCIATED ACTIVITY & LOGS")
            self._draw_zone_annotation(page, r_rect, "DETAIL PANEL")

    def _draw_wireframe_table(self, page, spec: ScreenSpecification, rect: pymupdf.Rect, title: str):
        c_card = (1.0, 1.0, 1.0)
        c_card_alt = (0.93, 0.94, 0.95)
        c_border = (0.65, 0.68, 0.72)
        c_border_light = (0.80, 0.82, 0.85)
        c_text_dark = (0.15, 0.17, 0.20)
        c_text_muted = (0.45, 0.48, 0.52)

        page.draw_rect(rect, fill=c_card, color=c_border, width=0.8)
        # Table Title Bar
        page.draw_rect(pymupdf.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + 38), fill=c_card_alt, color=c_border, width=0.8)
        page.insert_text((rect.x0 + 16, rect.y0 + 24), f"[ {title} ]", fontsize=11, color=c_text_dark, fontname="hebo")

        # Resolve columns
        columns = image_generation_service._resolve_table_columns(spec)
        if not columns or len(columns) < 2:
            columns = ["RECORD ID", "IDENTIFIER / NAME", "TYPE", "STATUS", "LAST UPDATED", "ACTIONS"]

        # Table Header Row
        th_y = rect.y0 + 38
        th_h = 32.0
        page.draw_rect(pymupdf.Rect(rect.x0, th_y, rect.x1, th_y + th_h), fill=(0.88, 0.90, 0.92), color=c_border, width=0.8)
        col_w = (rect.width - 24) / max(len(columns[:6]), 1)
        for idx, col in enumerate(columns[:6]):
            cx = rect.x0 + 12 + idx * col_w
            page.insert_text((cx, th_y + 20), f"[ {col[:18].upper()} ]", fontsize=9, color=c_text_dark, fontname="hebo")

        # Table Data Rows
        row_y = th_y + th_h
        row_h = 36.0
        sample_rows = [
            ("REC-00142", "Active", "2026-10-12"),
            ("REC-00143", "Pending Approval", "2026-10-14"),
            ("REC-00144", "In Review", "2026-10-15"),
            ("REC-00145", "Approved", "2026-10-18"),
            ("REC-00146", "Draft", "2026-10-20"),
            ("REC-00147", "Processing", "2026-10-21"),
            ("REC-00148", "Active", "2026-10-22"),
        ]
        for r_idx in range(7):
            if row_y + row_h > rect.y1 - 40:
                break
            bg = c_card if (r_idx % 2 == 0) else c_card_alt
            row_rect = pymupdf.Rect(rect.x0, row_y, rect.x1, row_y + row_h)
            page.draw_rect(row_rect, fill=bg, color=c_border_light, width=0.4)
            s_rec = sample_rows[r_idx % len(sample_rows)]
            for c_idx, col in enumerate(columns[:6]):
                cx = rect.x0 + 12 + c_idx * col_w
                if c_idx == 0:
                    val = f"{s_rec[0]}_{r_idx+1:02d}"
                elif c_idx == len(columns[:6]) - 1:
                    val = "[ View | Edit ]"
                elif "status" in col.lower():
                    val = f"[ {s_rec[1]} ]"
                else:
                    val = f"Data Val {r_idx+1}.{c_idx+1}"
                page.insert_text((cx, row_y + 22), val[:20], fontsize=9, color=c_text_dark, fontname="helv")
            row_y += row_h

        # Pagination row
        page.draw_line((rect.x0, rect.y1 - 32), (rect.x1, rect.y1 - 32), color=c_border, width=0.6)
        page.insert_text((rect.x0 + 16, rect.y1 - 12), "[ Showing 1–7 of 142 records | < Prev | 1 | 2 | 3 | Next > ]", fontsize=9, color=c_text_muted, fontname="helv")

    def _draw_wireframe_form(self, page, spec: ScreenSpecification, rect: pymupdf.Rect, title: str = "DATA INPUT FORM"):
        c_card = (1.0, 1.0, 1.0)
        c_card_alt = (0.93, 0.94, 0.95)
        c_border = (0.65, 0.68, 0.72)
        c_border_light = (0.80, 0.82, 0.85)
        c_text_dark = (0.15, 0.17, 0.20)
        c_text_muted = (0.45, 0.48, 0.52)

        page.draw_rect(rect, fill=c_card, color=c_border, width=0.8)
        # Header
        page.draw_rect(pymupdf.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + 38), fill=c_card_alt, color=c_border, width=0.8)
        page.insert_text((rect.x0 + 16, rect.y0 + 24), f"[ {title} ]", fontsize=11, color=c_text_dark, fontname="hebo")

        fields = image_generation_service._resolve_form_fields(spec)
        if not fields:
            fields = [
                ScreenField(label="Applicant / Entity Name", type="text", placeholder="Enter full legal name"),
                ScreenField(label="Registration / ID Number", type="text", placeholder="e.g. REG-109283"),
                ScreenField(label="Category / Classification", type="select", placeholder="Select category"),
                ScreenField(label="Transaction / Allocation Amount", type="number", placeholder="0.00"),
                ScreenField(label="Effective Date", type="date", placeholder="YYYY-MM-DD"),
                ScreenField(label="Operational Notes", type="textarea", placeholder="Enter summary notes"),
            ]

        # 2-column form grid
        grid_w = (rect.width - 48) / 2
        f_y = rect.y0 + 56
        for idx, field in enumerate(fields[:10]):
            col_idx = idx % 2
            row_idx = idx // 2
            fx = rect.x0 + 16 + col_idx * (grid_w + 16)
            fy = f_y + row_idx * 68
            if fy + 60 > rect.y1 - 50:
                break

            # Label
            req_mark = " *" if field.required else ""
            page.insert_text((fx, fy + 12), f"[ FIELD: {field.label[:26].upper()}{req_mark} ]", fontsize=9, color=c_text_muted, fontname="hebo")
            # Field Box Outline
            input_rect = pymupdf.Rect(fx, fy + 18, fx + grid_w, fy + 52)
            page.draw_rect(input_rect, fill=c_card_alt, color=c_border, width=0.8)
            ph = field.placeholder or f"[ enter {field.type} ]"
            page.insert_text((fx + 10, fy + 38), ph[:32], fontsize=9, color=c_text_muted, fontname="helv")

        # Action Buttons row inside form
        act_y = rect.y1 - 42
        page.draw_line((rect.x0, act_y - 8), (rect.x1, act_y - 8), color=c_border_light, width=0.6)
        bx = rect.x0 + 16
        actions = spec.actions if spec.actions else [
            ScreenField(label="Submit Form", type="primary"),
            ScreenField(label="Save Draft", type="secondary"),
            ScreenField(label="Cancel", type="secondary")
        ]
        for act in actions[:3]:
            lbl = act.label if hasattr(act, "label") else str(act)
            b_w = max(len(lbl) * 8 + 24, 100)
            b_rect = pymupdf.Rect(bx, act_y, bx + b_w, act_y + 30)
            page.draw_rect(b_rect, fill=c_card_alt, color=c_border, width=1.0)
            page.insert_text((bx + 12, act_y + 19), f"[ {lbl[:18]} ]", fontsize=9, color=c_text_dark, fontname="hebo")
            bx += (b_w + 12)

    def _draw_wireframe_details_panel(self, page, spec: ScreenSpecification, rect: pymupdf.Rect, title: str):
        c_card = (1.0, 1.0, 1.0)
        c_card_alt = (0.93, 0.94, 0.95)
        c_border = (0.65, 0.68, 0.72)
        c_border_light = (0.80, 0.82, 0.85)
        c_text_dark = (0.15, 0.17, 0.20)
        c_text_muted = (0.45, 0.48, 0.52)

        page.draw_rect(rect, fill=c_card, color=c_border, width=0.8)
        page.draw_rect(pymupdf.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + 38), fill=c_card_alt, color=c_border, width=0.8)
        page.insert_text((rect.x0 + 16, rect.y0 + 24), f"[ {title} ]", fontsize=11, color=c_text_dark, fontname="hebo")

        items = [
            ("STATUS / STATE", spec.workflow_state or "Active"),
            ("PRIMARY ROLE", spec.user_role),
            ("SCREEN SEQUENCE", f"Screen #{spec.sequence}"),
            ("ASSOCIATED ENTITY", spec.data_sources[0] if spec.data_sources else "Core Record"),
        ]
        curr_y = rect.y0 + 56
        for lbl, val in items:
            page.insert_text((rect.x0 + 16, curr_y), f"[ {lbl} ]", fontsize=9, color=c_text_muted, fontname="hebo")
            page.insert_text((rect.x0 + 16, curr_y + 18), str(val)[:36], fontsize=10, color=c_text_dark, fontname="helv")
            page.draw_line((rect.x0 + 16, curr_y + 26), (rect.x1 - 16, curr_y + 26), color=c_border_light, width=0.4)
            curr_y += 42

        # Rules / References summary box
        if spec.business_rules:
            curr_y += 10
            page.insert_text((rect.x0 + 16, curr_y), "[ APPLICABLE BUSINESS RULES ]", fontsize=9, color=c_text_muted, fontname="hebo")
            curr_y += 18
            for r in spec.business_rules[:3]:
                page.insert_text((rect.x0 + 16, curr_y), f"- {r[:40]}", fontsize=9, color=c_text_dark, fontname="helv")
                curr_y += 20

    def _draw_wireframe_sidebar_rules(self, page, spec: ScreenSpecification, rect: pymupdf.Rect):
        self._draw_wireframe_details_panel(page, spec, rect, "GUIDELINES & BUSINESS RULES")

    def _draw_wireframe_decision_panel(self, page, spec: ScreenSpecification, rect: pymupdf.Rect):
        c_card = (1.0, 1.0, 1.0)
        c_card_alt = (0.93, 0.94, 0.95)
        c_border = (0.65, 0.68, 0.72)
        c_text_dark = (0.15, 0.17, 0.20)
        c_text_muted = (0.45, 0.48, 0.52)

        page.draw_rect(rect, fill=c_card, color=c_border, width=0.8)
        page.draw_rect(pymupdf.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + 38), fill=c_card_alt, color=c_border, width=0.8)
        page.insert_text((rect.x0 + 16, rect.y0 + 24), "[ DECISION & APPROVAL CHECKPOINT ]", fontsize=11, color=c_text_dark, fontname="hebo")

        curr_y = rect.y0 + 56
        page.insert_text((rect.x0 + 16, curr_y), "[ APPROVAL COMMENTS ]", fontsize=9, color=c_text_muted, fontname="hebo")
        curr_y += 12
        comment_rect = pymupdf.Rect(rect.x0 + 16, curr_y, rect.x1 - 16, curr_y + 80)
        page.draw_rect(comment_rect, fill=c_card_alt, color=c_border, width=0.8)
        page.insert_text((rect.x0 + 24, curr_y + 24), "[ Enter justification or rejection reasons... ]", fontsize=9, color=c_text_muted, fontname="helv")
        curr_y += 96

        page.insert_text((rect.x0 + 16, curr_y), "[ ACTIONS ]", fontsize=9, color=c_text_muted, fontname="hebo")
        curr_y += 14

        decisions = [
            ("[ APPROVE ]", "Primary action — mark approved"),
            ("[ REJECT ]", "Return to applicant with feedback"),
            ("[ REQUEST CLARIFICATION ]", "Hold in pending status")
        ]
        for btn_lbl, desc in decisions:
            b_rect = pymupdf.Rect(rect.x0 + 16, curr_y, rect.x1 - 16, curr_y + 34)
            page.draw_rect(b_rect, fill=c_card_alt, color=c_border, width=1.0)
            page.insert_text((rect.x0 + 26, curr_y + 22), btn_lbl, fontsize=10, color=c_text_dark, fontname="hebo")
            page.insert_text((rect.x0 + 26, curr_y + 44), desc, fontsize=8, color=c_text_muted, fontname="helv")
            curr_y += 56

    def _draw_zone_annotation(self, page, rect: pymupdf.Rect, label: str):
        """Draws red dotted boundary and a small red tag identifying the architectural zone."""
        c_red = (0.85, 0.20, 0.20)
        # Draw dotted red bounding outline
        page.draw_rect(rect, color=c_red, width=0.6, dashes="2 2")
        # Draw red label badge in top right corner of the zone
        tag_w = max(len(label) * 6 + 14, 52)
        tag_h = 15.0
        tag_x = rect.x1 - tag_w - 4
        tag_y = rect.y0 + 3
        if tag_x > rect.x0:
            tag_rect = pymupdf.Rect(tag_x, tag_y, tag_x + tag_w, tag_y + tag_h)
            page.draw_rect(tag_rect, fill=(1.0, 0.94, 0.94), color=c_red, width=0.5)
            page.insert_text((tag_x + 4, tag_y + 11), f"[{label}]", fontsize=7, color=c_red, fontname="hebo")

    def _draw_watermark(self, page, width: float, height: float):
        """Draws subtle 'WIREFRAME' watermark across the canvas."""
        c_wm = (0.88, 0.89, 0.91)
        page.insert_text(
            (width * 0.32, height * 0.52),
            "W I R E F R A M E",
            fontsize=68,
            color=c_wm,
            fontname="hebo",
            rotate=0,
        )


wireframe_service = WireframeService()
