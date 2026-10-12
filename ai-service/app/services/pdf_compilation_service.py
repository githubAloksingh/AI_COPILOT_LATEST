import base64
from datetime import datetime
import io
import logging
from typing import Any, Dict, List, Optional
import pymupdf  # PyMuPDF
from PIL import Image

logger = logging.getLogger(__name__)


class PdfCompilationService:
    """
    Section 17: Consolidated Mock Screens PDF Generator.
    Combines all generated screen mockup images in sequential order with
    an executive cover page, table of contents, and individual screen specification pages.
    """

    def compile_pdf(
        self,
        application_name: str,
        project_name: Optional[str],
        brd_name: Optional[str],
        summary: Optional[str],
        screens: List[Dict[str, Any]]
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
            image_bytes = self._extract_image_bytes(screen_data)
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
            ordered_screens.append(screen_data)

        doc = pymupdf.open()
        page_width = 842.0  # A4 Landscape width in points (approx 11.69 in)
        page_height = 595.0 # A4 Landscape height in points (approx 8.27 in)
        sorted_screens = sorted(ordered_screens, key=lambda screen: screen["sequence"])
        overflow_toc_page_size = 38
        overflow_toc_pages = [
            sorted_screens[start:start + overflow_toc_page_size]
            for start in range(14, len(sorted_screens), overflow_toc_page_size)
        ]
        total_pages = len(sorted_screens) + 1 + len(overflow_toc_pages)

        # -------------------------------------------------------------
        # PAGE 1: EXECUTIVE COVER PAGE
        # -------------------------------------------------------------
        cover = doc.new_page(width=page_width, height=page_height)
        # Deep enterprise navy banner
        cover.draw_rect(pymupdf.Rect(0, 0, page_width, 180), fill=(0.06, 0.12, 0.28), color=None)
        # Accent stripe
        cover.draw_rect(pymupdf.Rect(0, 180, page_width, 186), fill=(0.95, 0.43, 0.13), color=None)

        # Cover Titles
        cover.insert_text((50, 70), "NEWGEN AI WORK COPILOT", fontsize=14, color=(0.95, 0.43, 0.13), fontname="hebo")
        cover.insert_text((50, 115), "UI/UX Mock Screen Architecture Blueprint", fontsize=26, color=(1.0, 1.0, 1.0), fontname="hebo")
        cover.insert_text((50, 150), f"System: {application_name}", fontsize=16, color=(0.85, 0.90, 0.98), fontname="helv")

        # Cover Metadata Panel
        y_meta = 220.0
        cover.draw_rect(pymupdf.Rect(50, y_meta, page_width - 50, y_meta + 145), fill=(0.97, 0.98, 0.99), color=(0.85, 0.88, 0.92), radius=0.08, width=0.8)

        now_str = datetime.now().strftime("%B %d, %Y - %H:%M:%S UTC")
        cover.insert_text((70, y_meta + 30), "DOCUMENT INFORMATION", fontsize=10, color=(0.20, 0.40, 0.70), fontname="hebo")
        cover.insert_text((70, y_meta + 55), f"Source BRD Document:  {brd_name or 'Uploaded BRD'}", fontsize=11, color=(0.1, 0.15, 0.25), fontname="hebo")
        cover.insert_text((70, y_meta + 78), f"Project Association:   {project_name or 'General Enterprise'}", fontsize=10, color=(0.3, 0.35, 0.45), fontname="helv")
        cover.insert_text((70, y_meta + 100), f"Generated Date:       {now_str}", fontsize=10, color=(0.3, 0.35, 0.45), fontname="helv")

        cover.insert_text((520, y_meta + 55), f"Total Screens:      {len(screens)} screens", fontsize=11, color=(0.1, 0.15, 0.25), fontname="hebo")
        cover.insert_text((520, y_meta + 78), "Plan Status:         Schema validated", fontsize=10, color=(0.15, 0.65, 0.35), fontname="hebo")
        cover.insert_text((520, y_meta + 100), "Image Engine:       Local PyMuPDF renderer", fontsize=10, color=(0.3, 0.35, 0.45), fontname="helv")
        if summary and "This plan is based on a truncated BRD excerpt" in summary:
            cover.insert_text(
                (70, y_meta + 130),
                "Coverage: PARTIAL — the BRD exceeded the analysis limit; omitted content was not analyzed.",
                fontsize=9,
                color=(0.70, 0.28, 0.12),
                fontname="hebo",
            )

        # Table of Contents
        y_toc = 385.0
        cover.insert_text((50, y_toc), "TABLE OF CONTENTS / SCREEN SEQUENCE", fontsize=11, color=(0.1, 0.15, 0.25), fontname="hebo")
        cover.draw_line(pymupdf.Point(50, y_toc + 8), pymupdf.Point(page_width - 50, y_toc + 8), color=(0.85, 0.88, 0.92), width=0.8)

        col_w = (page_width - 100) / 2
        for idx, sc in enumerate(sorted_screens[:14]):
            col_idx = 0 if idx < 7 else 1
            row_idx = idx if idx < 7 else (idx - 7)
            tx = 50 + col_idx * col_w
            ty = y_toc + 30 + row_idx * 22
            seq = sc.get("sequence", idx + 1)
            name = sc.get("name") or sc.get("screenName") or f"Screen {seq}"
            stype = sc.get("screenType") or sc.get("screen_type") or "detail"
            cover.insert_text((tx, ty), f"[{seq:02d}]  {name[:32]}", fontsize=9, color=(0.15, 0.20, 0.30), fontname="hebo")
            cover.insert_text((tx + 240, ty), f"({stype})", fontsize=8, color=(0.45, 0.50, 0.60), fontname="helv")

        # Cover Footer
        cover.insert_text((50, page_height - 25), "Confidential • Enterprise Architecture Blueprint • AI Work Copilot", fontsize=9, color=(0.5, 0.55, 0.65), fontname="helv")
        cover.insert_text((page_width - 120, page_height - 25), "Page 1 of " + str(total_pages), fontsize=9, color=(0.5, 0.55, 0.65), fontname="helv")

        # -------------------------------------------------------------
        # ADDITIONAL TABLE OF CONTENTS PAGES
        # -------------------------------------------------------------
        for toc_page_index, toc_screens in enumerate(overflow_toc_pages, start=2):
            toc_page = doc.new_page(width=page_width, height=page_height)
            toc_page.draw_rect(
                pymupdf.Rect(0, 0, page_width, 50),
                fill=(0.97, 0.98, 0.99),
                color=(0.88, 0.90, 0.93),
                width=0.8,
            )
            toc_page.insert_text((40, 32), "TABLE OF CONTENTS / SCREEN SEQUENCE (CONTINUED)",
                                 fontsize=13, color=(0.1, 0.15, 0.25), fontname="hebo")
            for idx, sc in enumerate(toc_screens):
                col_idx = 0 if idx < 19 else 1
                row_idx = idx if idx < 19 else idx - 19
                tx = 40 + col_idx * ((page_width - 80) / 2)
                ty = 78 + row_idx * 24
                seq = sc.get("sequence", idx + 15)
                name = sc.get("name") or sc.get("screenName") or f"Screen {seq}"
                stype = sc.get("screenType") or sc.get("screen_type") or "detail"
                toc_page.insert_text((tx, ty), f"[{seq:02d}]  {name[:38]}", fontsize=9,
                                     color=(0.15, 0.20, 0.30), fontname="hebo")
                toc_page.insert_text((tx + 250, ty), f"({stype[:20]})", fontsize=8,
                                     color=(0.45, 0.50, 0.60), fontname="helv")
            toc_page.insert_text(
                (page_width - 120, page_height - 25),
                f"Page {toc_page_index} of {total_pages}",
                fontsize=9,
                color=(0.5, 0.55, 0.65),
                fontname="helv",
            )

        # -------------------------------------------------------------
        # SCREEN MOCKUP PAGES
        # -------------------------------------------------------------
        first_screen_page = 2 + len(overflow_toc_pages)

        for page_idx, sc in enumerate(sorted_screens, start=first_screen_page):
            sp = doc.new_page(width=page_width, height=page_height)
            
            seq = sc.get("sequence", page_idx - 1)
            name = sc.get("name") or sc.get("screenName") or f"Screen {seq}"
            stype = sc.get("screenType") or sc.get("screen_type") or "detail"
            purpose = sc.get("purpose") or "Operational screen interface"
            role = sc.get("userRole") or sc.get("user_role") or "Enterprise User"
            wf = sc.get("workflowState") or sc.get("workflow_state") or ""

            # Top Header Bar on Page
            sp.draw_rect(pymupdf.Rect(0, 0, page_width, 50), fill=(0.97, 0.98, 0.99), color=(0.88, 0.90, 0.93), width=0.8)
            # Sequence Badge
            sp.draw_rect(pymupdf.Rect(40, 14, 110, 36), fill=(0.12, 0.25, 0.69), radius=0.1, color=None)
            sp.insert_text((52, 29), f"SCREEN {seq:02d}", fontsize=10, color=(1.0, 1.0, 1.0), fontname="hebo")
            # Screen Name
            sp.insert_text((125, 30), name[:40], fontsize=14, color=(0.1, 0.15, 0.25), fontname="hebo")
            # Metadata pill in right header
            sp.insert_text((page_width - 320, 29), f"Role: {role[:18]}  |  Type: {stype}", fontsize=9, color=(0.4, 0.45, 0.55), fontname="helv")

            # Insert Image in Center of Page
            img_bytes = sc["_validated_image_bytes"]

            img_rect = pymupdf.Rect(40, 60, page_width - 40, page_height - 50)
            sp.insert_image(img_rect, stream=img_bytes, keep_proportion=True)

            # Footer
            sp.draw_line(pymupdf.Point(40, page_height - 35), pymupdf.Point(page_width - 40, page_height - 35), color=(0.88, 0.90, 0.93), width=0.6)
            sp.insert_text((40, page_height - 20), f"Purpose: {purpose[:120]}", fontsize=8, color=(0.4, 0.45, 0.55), fontname="helv")
            sp.insert_text((page_width - 120, page_height - 20), f"Page {page_idx} of {total_pages}", fontsize=9, color=(0.4, 0.45, 0.55), fontname="helv")

        pdf_bytes = doc.tobytes(deflate=True, garbage=4)
        doc.close()
        expected_page_count = total_pages
        actual_page_count = self.count_pages(pdf_bytes)
        if actual_page_count != expected_page_count:
            raise RuntimeError(
                f"Compiled PDF has {actual_page_count} pages; expected {expected_page_count}."
            )
        logger.info("Compiled %d-page consolidated mock screen PDF (%d bytes)", total_pages, len(pdf_bytes))
        return pdf_bytes

    def count_pages(self, pdf_bytes: bytes) -> int:
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
            return doc.page_count

    def _extract_image_bytes(self, sc: Dict[str, Any]) -> Optional[bytes]:
        for key in ("imageData", "image_base64"):
            raw = sc.get(key)
            if not raw:
                continue
            if isinstance(raw, bytes):
                return raw
            if isinstance(raw, str):
                try:
                    return base64.b64decode(raw, validate=True)
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"Generated image field '{key}' is not valid base64.") from exc
            raise ValueError(f"Generated image field '{key}' must be bytes or base64 text.")

        path = sc.get("imagePath") or sc.get("image_path")
        if path and isinstance(path, str):
            import os
            if not os.path.isfile(path):
                raise ValueError(f"Generated image file does not exist: {path}")
            try:
                with open(path, "rb") as image_file:
                    return image_file.read()
            except OSError as exc:
                raise ValueError(f"Could not read generated image file: {path}") from exc
        return None

    def _draw_image_fallback_card(self, page: pymupdf.Page, rect: pymupdf.Rect, name: str, purpose: str):
        page.draw_rect(rect, fill=(0.98, 0.99, 1.0), color=(0.85, 0.88, 0.92), radius=0.08, width=0.8)
        page.insert_text((rect.x0 + 40, rect.y0 + 100), f"Mock Screen: {name}", fontsize=18, color=(0.15, 0.25, 0.5), fontname="hebo")
        page.insert_text((rect.x0 + 40, rect.y0 + 140), purpose, fontsize=12, color=(0.35, 0.4, 0.5), fontname="helv")


pdf_compilation_service = PdfCompilationService()
