import base64
from datetime import datetime
import io
import json
import logging
from typing import Any, Dict, List, Optional
import pymupdf  # PyMuPDF
from PIL import Image

logger = logging.getLogger(__name__)


class PdfCompilationService:
    """
    Section 17: Consolidated Mock Screens PDF Generator.
    Combines all generated screens in sequential order with:
    - Executive cover page
    - Table of contents
    - Per screen: Mockup page + Specification/Explanation page
    """

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

        ordered_screens = []
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

            # 1. Mockup Image (mandatory)
            image_bytes = self._extract_image_bytes(screen_data, ("imageData", "image_base64", "imagePath", "image_path"))
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

            # 2. Explanation payload
            explanation = screen_data.get("explanation") or screen_data.get("explanation_json") or screen_data.get("explanationJson")
            if isinstance(explanation, str):
                try:
                    screen_data["_parsed_explanation"] = json.loads(explanation)
                except Exception:
                    screen_data["_parsed_explanation"] = None
            elif isinstance(explanation, dict):
                screen_data["_parsed_explanation"] = explanation
            else:
                screen_data["_parsed_explanation"] = None

            ordered_screens.append(screen_data)

        sorted_screens = sorted(ordered_screens, key=lambda screen: screen["sequence"])

        # Page counting
        page_width = 842.0   # A4 Landscape width in points
        page_height = 595.0  # A4 Landscape height in points

        overflow_toc_page_size = 38
        overflow_toc_pages = [
            sorted_screens[start:start + overflow_toc_page_size]
            for start in range(14, len(sorted_screens), overflow_toc_page_size)
        ]
        toc_page_count = 1 + len(overflow_toc_pages)

        # Count total pages: 2 pages per screen (Mockup page + Explanation page)
        total_content_pages = len(sorted_screens) * 2

        total_pages = 1 + len(overflow_toc_pages) + total_content_pages

        doc = pymupdf.open()

        # -------------------------------------------------------------
        # PAGE 1: EXECUTIVE COVER PAGE
        # -------------------------------------------------------------
        cover = doc.new_page(width=page_width, height=page_height)
        cover.draw_rect(pymupdf.Rect(0, 0, page_width, 180), fill=(0.06, 0.12, 0.28), color=None)
        cover.draw_rect(pymupdf.Rect(0, 180, page_width, 186), fill=(0.95, 0.43, 0.13), color=None)

        cover.insert_text((50, 70), "NEWGEN AI WORK COPILOT", fontsize=14, color=(0.95, 0.43, 0.13), fontname="hebo")
        cover.insert_text((50, 115), "UI/UX Architecture Specification & Blueprint", fontsize=26, color=(1.0, 1.0, 1.0), fontname="hebo")
        cover.insert_text((50, 150), f"System: {application_name}", fontsize=16, color=(0.85, 0.90, 0.98), fontname="helv")

        y_meta = 215.0
        cover.draw_rect(pymupdf.Rect(50, y_meta, page_width - 50, y_meta + 150), fill=(0.97, 0.98, 0.99), color=(0.85, 0.88, 0.92), radius=0.08, width=0.8)

        now_str = datetime.now().strftime("%B %d, %Y - %H:%M:%S UTC")
        cover.insert_text((70, y_meta + 28), "DOCUMENT METADATA & ARCHITECTURAL SUMMARY", fontsize=10, color=(0.20, 0.40, 0.70), fontname="hebo")
        cover.insert_text((70, y_meta + 52), f"Source BRD Document:  {brd_name or 'Uploaded BRD'}", fontsize=11, color=(0.1, 0.15, 0.25), fontname="hebo")
        cover.insert_text((70, y_meta + 74), f"Project Association:   {project_name or 'General Enterprise'}", fontsize=10, color=(0.3, 0.35, 0.45), fontname="helv")
        cover.insert_text((70, y_meta + 96), f"Generated Date:       {now_str}", fontsize=10, color=(0.3, 0.35, 0.45), fontname="helv")
        cover.insert_text((70, y_meta + 118), f"Document Scope:       Complete Architecture (High-Fidelity Mockups & Explanations)", fontsize=10, color=(0.3, 0.35, 0.45), fontname="helv")

        cover.insert_text((520, y_meta + 52), f"Total Screens:      {len(screens)} screens", fontsize=11, color=(0.1, 0.15, 0.25), fontname="hebo")
        cover.insert_text((520, y_meta + 74), "Interaction Model:  IFML-aligned state & events", fontsize=10, color=(0.15, 0.65, 0.35), fontname="hebo")
        cover.insert_text((520, y_meta + 96), "Blueprint Stages:   Mockup · Specifications", fontsize=10, color=(0.15, 0.65, 0.35), fontname="hebo")
        cover.insert_text((520, y_meta + 118), "Vector Engine:      PyMuPDF Native Engine", fontsize=10, color=(0.3, 0.35, 0.45), fontname="helv")

        # Table of Contents Preview on Cover
        y_toc = 385.0
        cover.insert_text((50, y_toc), "TABLE OF CONTENTS / SCREEN SEQUENCE", fontsize=11, color=(0.1, 0.15, 0.25), fontname="hebo")
        cover.draw_line(pymupdf.Point(50, y_toc + 8), pymupdf.Point(page_width - 50, y_toc + 8), color=(0.85, 0.88, 0.92), width=0.8)

        col_w = (page_width - 100) / 2
        for idx, sc in enumerate(sorted_screens[:14]):
            col_idx = 0 if idx < 7 else 1
            row_idx = idx if idx < 7 else (idx - 7)
            tx = 50 + col_idx * col_w
            ty = y_toc + 28 + row_idx * 21
            seq = sc.get("sequence", idx + 1)
            name = sc.get("name") or sc.get("screenName") or f"Screen {seq}"
            stype = sc.get("screenType") or sc.get("screen_type") or "detail"
            cover.insert_text((tx, ty), f"[{seq:02d}]  {name[:30]}", fontsize=9, color=(0.15, 0.20, 0.30), fontname="hebo")
            cover.insert_text((tx + 240, ty), f"({stype})", fontsize=8, color=(0.45, 0.50, 0.60), fontname="helv")

        cover.insert_text((50, page_height - 25), "Confidential • Enterprise Architecture Blueprint • AI Work Copilot", fontsize=9, color=(0.5, 0.55, 0.65), fontname="helv")
        cover.insert_text((page_width - 120, page_height - 25), f"Page 1 of {total_pages}", fontsize=9, color=(0.5, 0.55, 0.65), fontname="helv")

        # Additional TOC pages
        for toc_page_index, toc_screens in enumerate(overflow_toc_pages, start=2):
            toc_page = doc.new_page(width=page_width, height=page_height)
            toc_page.draw_rect(pymupdf.Rect(0, 0, page_width, 50), fill=(0.97, 0.98, 0.99), color=(0.88, 0.90, 0.93), width=0.8)
            toc_page.insert_text((40, 32), "TABLE OF CONTENTS / SCREEN SEQUENCE (CONTINUED)", fontsize=13, color=(0.1, 0.15, 0.25), fontname="hebo")
            for idx, sc in enumerate(toc_screens):
                col_idx = 0 if idx < 19 else 1
                row_idx = idx if idx < 19 else idx - 19
                tx = 40 + col_idx * ((page_width - 80) / 2)
                ty = 78 + row_idx * 24
                seq = sc.get("sequence", idx + 15)
                name = sc.get("name") or sc.get("screenName") or f"Screen {seq}"
                stype = sc.get("screenType") or sc.get("screen_type") or "detail"
                toc_page.insert_text((tx, ty), f"[{seq:02d}]  {name[:38]}", fontsize=9, color=(0.15, 0.20, 0.30), fontname="hebo")
                toc_page.insert_text((tx + 250, ty), f"({stype[:20]})", fontsize=8, color=(0.45, 0.50, 0.60), fontname="helv")
            toc_page.insert_text((page_width - 120, page_height - 25), f"Page {toc_page_index} of {total_pages}", fontsize=9, color=(0.5, 0.55, 0.65), fontname="helv")

        # -------------------------------------------------------------
        # PER-SCREEN PAGES: [MOCKUP] -> [EXPLANATION]
        # -------------------------------------------------------------
        current_page_num = toc_page_count + 1

        for sc in sorted_screens:
            seq = sc.get("sequence", 1)
            name = sc.get("name") or sc.get("screenName") or f"Screen {seq}"
            stype = sc.get("screenType") or sc.get("screen_type") or "detail"
            purpose = sc.get("purpose") or "Operational interface"
            role = sc.get("userRole") or sc.get("user_role") or "Enterprise User"

            # ---------------------------------------------------------
            # 1. MOCKUP PAGE
            # ---------------------------------------------------------
            mp = doc.new_page(width=page_width, height=page_height)
            mp.draw_rect(pymupdf.Rect(0, 0, page_width, 50), fill=(0.97, 0.98, 0.99), color=(0.88, 0.90, 0.93), width=0.8)
            # Badge
            mp.draw_rect(pymupdf.Rect(40, 14, 170, 36), fill=(0.12, 0.25, 0.69), radius=0.1, color=None)
            mp.insert_text((50, 29), f"SCREEN {seq:02d} — UI MOCKUP", fontsize=9, color=(1.0, 1.0, 1.0), fontname="hebo")
            mp.insert_text((180, 30), name[:38], fontsize=13, color=(0.10, 0.15, 0.25), fontname="hebo")
            mp.insert_text((page_width - 340, 29), f"Role: {role[:18]}  |  Type: {stype}", fontsize=9, color=(0.4, 0.45, 0.55), fontname="helv")

            img_rect = pymupdf.Rect(40, 60, page_width - 40, page_height - 50)
            mp.insert_image(img_rect, stream=sc["_validated_image_bytes"], keep_proportion=True)

            mp.draw_line(pymupdf.Point(40, page_height - 35), pymupdf.Point(page_width - 40, page_height - 35), color=(0.88, 0.90, 0.93), width=0.6)
            mp.insert_text((40, page_height - 20), f"Purpose: {purpose[:120]}", fontsize=8, color=(0.4, 0.45, 0.55), fontname="helv")
            mp.insert_text((page_width - 120, page_height - 20), f"Page {current_page_num} of {total_pages}", fontsize=9, color=(0.4, 0.45, 0.55), fontname="helv")
            current_page_num += 1

            # ---------------------------------------------------------
            # 2. EXPLANATION & ARCHITECTURAL SPECIFICATION PAGE
            # ---------------------------------------------------------
            ep = doc.new_page(width=page_width, height=page_height)
            self._render_explanation_page(ep, sc, page_width, page_height, total_pages, current_page_num)
            current_page_num += 1

        pdf_bytes = doc.tobytes(deflate=True, garbage=4)
        doc.close()

        actual_page_count = self.count_pages(pdf_bytes)
        if actual_page_count != total_pages:
            raise RuntimeError(f"Compiled PDF has {actual_page_count} pages; expected {total_pages}.")

        logger.info("Compiled %d-page consolidated mock screen PDF (%d bytes)", total_pages, len(pdf_bytes))
        return pdf_bytes

    def _render_explanation_page(
        self,
        page: pymupdf.Page,
        sc: Dict[str, Any],
        width: float,
        height: float,
        total_pages: int,
        page_num: int,
    ):
        seq = sc.get("sequence", 1)
        name = sc.get("name") or sc.get("screenName") or f"Screen {seq}"
        stype = sc.get("screenType") or sc.get("screen_type") or "detail"
        purpose = sc.get("purpose") or "Operational interface"
        role = sc.get("userRole") or sc.get("user_role") or "Enterprise User"
        exp = sc.get("_parsed_explanation") or {}

        # Colors
        c_primary = (0.12, 0.25, 0.69)
        c_border = (0.85, 0.88, 0.92)
        c_card = (0.98, 0.985, 0.99)
        c_text_dark = (0.10, 0.14, 0.20)
        c_text_muted = (0.40, 0.45, 0.52)

        # Header bar
        page.draw_rect(pymupdf.Rect(0, 0, width, 50), fill=(0.97, 0.98, 0.99), color=c_border, width=0.8)
        page.draw_rect(pymupdf.Rect(40, 14, 220, 36), fill=(0.15, 0.55, 0.45), radius=0.1, color=None)
        page.insert_text((50, 29), f"SCREEN {seq:02d} — SPECIFICATION & RULES", fontsize=9, color=(1.0, 1.0, 1.0), fontname="hebo")
        page.insert_text((228, 30), name[:38], fontsize=13, color=c_text_dark, fontname="hebo")
        page.insert_text((width - 340, 29), f"Role: {role[:18]}  |  Type: {stype}", fontsize=9, color=c_text_muted, fontname="helv")

        # 2-column layout for explanation content
        left_x = 40.0
        left_w = 420.0
        right_x = left_x + left_w + 20.0
        right_w = width - right_x - 40.0

        # LEFT COLUMN - BOX 1: PURPOSE SUMMARY
        y_cursor_l = 65.0
        purp_box_h = 95.0
        page.draw_rect(pymupdf.Rect(left_x, y_cursor_l, left_x + left_w, y_cursor_l + purp_box_h), fill=c_card, color=c_border, radius=0.04, width=0.8)
        page.insert_text((left_x + 14, y_cursor_l + 20), "1. BUSINESS PURPOSE & OPERATIONAL ROLE", fontsize=9, color=c_primary, fontname="hebo")
        purp_text = exp.get("purpose_summary") or purpose
        lines = self._wrap_text(purp_text, 68)[:4]
        for l_idx, line in enumerate(lines):
            page.insert_text((left_x + 14, y_cursor_l + 38 + l_idx * 14), line, fontsize=8.5, color=c_text_dark, fontname="helv")

        # LEFT COLUMN - BOX 2: SECTIONS & DATA FIELDS INVENTORY
        y_cursor_l += purp_box_h + 12.0
        box2_h = height - y_cursor_l - 45.0
        page.draw_rect(pymupdf.Rect(left_x, y_cursor_l, left_x + left_w, y_cursor_l + box2_h), fill=c_card, color=c_border, radius=0.04, width=0.8)
        page.insert_text((left_x + 14, y_cursor_l + 20), "2. SECTIONS & DATA FIELD INVENTORY", fontsize=9, color=c_primary, fontname="hebo")

        # Fields table
        sec_y = y_cursor_l + 32.0
        sections = exp.get("sections") or []
        fields = [f for s in sections for f in s.get("fields", [])] if sections else []
        if not fields:
            # Fall back to spec fields
            spec_fields = sc.get("fields") or []
            fields = [{"name": f.get("label", "Field"), "type": f.get("type", "text"), "required": f.get("required", False), "rule": f.get("placeholder", "")} for f in spec_fields]

        page.draw_rect(pymupdf.Rect(left_x + 14, sec_y, left_x + left_w - 14, sec_y + 18), fill=(0.91, 0.93, 0.96), color=c_border, width=0.5)
        page.insert_text((left_x + 20, sec_y + 12), "FIELD NAME", fontsize=8, color=c_text_dark, fontname="hebo")
        page.insert_text((left_x + 170, sec_y + 12), "TYPE", fontsize=8, color=c_text_dark, fontname="hebo")
        page.insert_text((left_x + 225, sec_y + 12), "REQ", fontsize=8, color=c_text_dark, fontname="hebo")
        page.insert_text((left_x + 260, sec_y + 12), "VALIDATION / APPLIED RULE", fontsize=8, color=c_text_dark, fontname="hebo")

        row_y = sec_y + 18.0
        for f_idx, field in enumerate(fields[:11]):
            bg = (1.0, 1.0, 1.0) if f_idx % 2 == 0 else (0.96, 0.97, 0.98)
            page.draw_rect(pymupdf.Rect(left_x + 14, row_y, left_x + left_w - 14, row_y + 18), fill=bg, color=c_border, width=0.3)
            fname = str(field.get("name") or field.get("label") or "Field")[:24]
            ftype = str(field.get("type", "text"))[:10]
            freq = "YES" if field.get("required") else "NO"
            frule = str(field.get("rule") or "Standard system constraint")[:32]
            page.insert_text((left_x + 20, row_y + 12), fname, fontsize=8, color=c_text_dark, fontname="helv")
            page.insert_text((left_x + 170, row_y + 12), ftype, fontsize=8, color=c_text_muted, fontname="helv")
            page.insert_text((left_x + 225, row_y + 12), freq, fontsize=7.5, color=c_text_dark, fontname="hebo")
            page.insert_text((left_x + 260, row_y + 12), frule, fontsize=8, color=c_text_dark, fontname="helv")
            row_y += 18.0

        # RIGHT COLUMN - BOX 3: ACTIONS & OUTCOMES
        y_cursor_r = 65.0
        box3_h = 120.0
        page.draw_rect(pymupdf.Rect(right_x, y_cursor_r, right_x + right_w, y_cursor_r + box3_h), fill=c_card, color=c_border, radius=0.04, width=0.8)
        page.insert_text((right_x + 14, y_cursor_r + 20), "3. PAGE ACTIONS & EVENT OUTCOMES", fontsize=9, color=c_primary, fontname="hebo")
        actions = exp.get("actions") or []
        if not actions and sc.get("actions"):
            actions = [{"label": a.get("label", "Action"), "type": a.get("type", "primary"), "outcome": f"Triggers {a.get('label')} processing"} for a in sc.get("actions")]
        act_y = y_cursor_r + 34.0
        for act in actions[:3]:
            albl = act.get("label", "Action")
            aout = act.get("outcome") or f"Submits data for validation and state transition."
            page.insert_text((right_x + 14, act_y), f"• [{albl.upper()}]: {aout[:60]}", fontsize=8, color=c_text_dark, fontname="helv")
            act_y += 24.0

        # RIGHT COLUMN - BOX 4: BUSINESS RULES & CONSTRAINTS
        y_cursor_r += box3_h + 12.0
        box4_h = 135.0
        page.draw_rect(pymupdf.Rect(right_x, y_cursor_r, right_x + right_w, y_cursor_r + box4_h), fill=c_card, color=c_border, radius=0.04, width=0.8)
        page.insert_text((right_x + 14, y_cursor_r + 20), "4. BUSINESS RULES & CONSTRAINTS", fontsize=9, color=c_primary, fontname="hebo")
        rules = exp.get("validation_rules") or sc.get("business_rules") or ["Field validation mandatory prior to state update."]
        rule_y = y_cursor_r + 34.0
        for r_idx, rule in enumerate(rules[:4]):
            page.insert_text((right_x + 14, rule_y), f"BR-{r_idx+1:02d}: {str(rule)[:65]}", fontsize=8, color=c_text_dark, fontname="helv")
            rule_y += 22.0

        # RIGHT COLUMN - BOX 5: NAVIGATION FLOW & TRACEABILITY
        y_cursor_r += box4_h + 12.0
        box5_h = height - y_cursor_r - 45.0
        page.draw_rect(pymupdf.Rect(right_x, y_cursor_r, right_x + right_w, y_cursor_r + box5_h), fill=c_card, color=c_border, radius=0.04, width=0.8)
        page.insert_text((right_x + 14, y_cursor_r + 20), "5. NAVIGATION & BRD TRACEABILITY", fontsize=9, color=c_primary, fontname="hebo")
        nav_text = exp.get("navigation_flow") or f"Inbound from entry workflow, outbound transitions to adjacent operational screens upon event completion."
        nav_lines = self._wrap_text(nav_text, 56)[:3]
        for nl_idx, nline in enumerate(nav_lines):
            page.insert_text((right_x + 14, y_cursor_r + 36 + nl_idx * 14), nline, fontsize=8, color=c_text_dark, fontname="helv")

        refs = exp.get("brd_references") or sc.get("related_requirements") or ["BRD Requirement Baseline"]
        refs_str = ", ".join(str(r) for r in refs[:5])
        page.insert_text((right_x + 14, y_cursor_r + 85), f"BRD Traceability: {refs_str[:55]}", fontsize=8, color=c_primary, fontname="hebo")

        # Page Footer
        page.draw_line(pymupdf.Point(40, height - 35), pymupdf.Point(width - 40, height - 35), color=c_border, width=0.6)
        page.insert_text((40, height - 20), "Detailed Screen Specification, Field Dictionary & Interaction Model", fontsize=8, color=c_text_muted, fontname="helv")
        page.insert_text((width - 120, height - 20), f"Page {page_num} of {total_pages}", fontsize=9, color=c_text_muted, fontname="helv")

    def _wrap_text(self, text: str, max_chars: int) -> List[str]:
        words = text.split()
        lines = []
        curr = []
        curr_len = 0
        for w in words:
            if curr_len + len(w) + 1 <= max_chars:
                curr.append(w)
                curr_len += len(w) + 1
            else:
                lines.append(" ".join(curr))
                curr = [w]
                curr_len = len(w)
        if curr:
            lines.append(" ".join(curr))
        return lines

    def count_pages(self, pdf_bytes: bytes) -> int:
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
            return doc.page_count

    def _extract_image_bytes(self, sc: Dict[str, Any], candidate_keys: tuple) -> Optional[bytes]:
        for key in candidate_keys:
            raw = sc.get(key)
            if not raw:
                continue
            if isinstance(raw, bytes):
                return raw
            if isinstance(raw, str):
                try:
                    return base64.b64decode(raw, validate=True)
                except (ValueError, TypeError):
                    pass
                import os
                if os.path.isfile(raw):
                    try:
                        with open(raw, "rb") as f:
                            return f.read()
                    except OSError:
                        pass
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
