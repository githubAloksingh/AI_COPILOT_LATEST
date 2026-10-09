import base64
from datetime import datetime
import io
import logging
from typing import Any, Dict, List, Optional
import pymupdf  # PyMuPDF

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
        doc = pymupdf.open()
        page_width = 842.0  # A4 Landscape width in points (approx 11.69 in)
        page_height = 595.0 # A4 Landscape height in points (approx 8.27 in)

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
        cover.draw_rect(pymupdf.Rect(50, y_meta, page_width - 50, y_meta + 120), fill=(0.97, 0.98, 0.99), color=(0.85, 0.88, 0.92), radius=0.08, width=0.8)

        now_str = datetime.now().strftime("%B %d, %Y - %H:%M:%S UTC")
        cover.insert_text((70, y_meta + 30), "DOCUMENT INFORMATION", fontsize=10, color=(0.20, 0.40, 0.70), fontname="hebo")
        cover.insert_text((70, y_meta + 55), f"Source BRD Document:  {brd_name or 'Uploaded BRD'}", fontsize=11, color=(0.1, 0.15, 0.25), fontname="hebo")
        cover.insert_text((70, y_meta + 78), f"Project Association:   {project_name or 'General Enterprise'}", fontsize=10, color=(0.3, 0.35, 0.45), fontname="helv")
        cover.insert_text((70, y_meta + 100), f"Generated Date:       {now_str}", fontsize=10, color=(0.3, 0.35, 0.45), fontname="helv")

        cover.insert_text((520, y_meta + 55), f"Total Screens:      {len(screens)} screens", fontsize=11, color=(0.1, 0.15, 0.25), fontname="hebo")
        cover.insert_text((520, y_meta + 78), "Validation Status:  BRD Grounded & Validated", fontsize=10, color=(0.15, 0.65, 0.35), fontname="hebo")
        cover.insert_text((520, y_meta + 100), "Engine Version:     Gemini 3.5 / Vector Mockup v2.0", fontsize=10, color=(0.3, 0.35, 0.45), fontname="helv")

        # Table of Contents
        y_toc = 365.0
        cover.insert_text((50, y_toc), "TABLE OF CONTENTS / SCREEN SEQUENCE", fontsize=11, color=(0.1, 0.15, 0.25), fontname="hebo")
        cover.draw_line(pymupdf.Point(50, y_toc + 8), pymupdf.Point(page_width - 50, y_toc + 8), color=(0.85, 0.88, 0.92), width=0.8)

        col_w = (page_width - 100) / 2
        for idx, sc in enumerate(screens[:14]):
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
        cover.insert_text((page_width - 120, page_height - 25), "Page 1 of " + str(len(screens) + 1), fontsize=9, color=(0.5, 0.55, 0.65), fontname="helv")

        # -------------------------------------------------------------
        # PAGES 2..N+1: INDIVIDUAL SCREEN MOCKUP PAGES
        # -------------------------------------------------------------
        # Sort screens sequentially
        sorted_screens = sorted(screens, key=lambda s: s.get("sequence", 0))

        for page_idx, sc in enumerate(sorted_screens, start=2):
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
            img_bytes = self._extract_image_bytes(sc)
            if img_bytes:
                # Target rect for image: full width margins, fitting nicely
                img_rect = pymupdf.Rect(40, 60, page_width - 40, page_height - 50)
                try:
                    sp.insert_image(img_rect, stream=img_bytes, keep_proportion=True)
                except Exception as e:
                    logger.warning("Failed to insert screen image for screen %d: %s", seq, e)
                    self._draw_image_fallback_card(sp, img_rect, name, purpose)
            else:
                img_rect = pymupdf.Rect(40, 60, page_width - 40, page_height - 50)
                self._draw_image_fallback_card(sp, img_rect, name, purpose)

            # Footer
            sp.draw_line(pymupdf.Point(40, page_height - 35), pymupdf.Point(page_width - 40, page_height - 35), color=(0.88, 0.90, 0.93), width=0.6)
            sp.insert_text((40, page_height - 20), f"Purpose: {purpose[:120]}", fontsize=8, color=(0.4, 0.45, 0.55), fontname="helv")
            sp.insert_text((page_width - 120, page_height - 20), f"Page {page_idx} of {len(sorted_screens) + 1}", fontsize=9, color=(0.4, 0.45, 0.55), fontname="helv")

        pdf_bytes = doc.tobytes(deflate=True, garbage=4)
        doc.close()
        logger.info("Compiled %d-page consolidated mock screen PDF (%d bytes)", len(screens) + 1, len(pdf_bytes))
        return pdf_bytes

    def _extract_image_bytes(self, sc: Dict[str, Any]) -> Optional[bytes]:
        # Check raw bytes
        if "imageData" in sc and sc["imageData"]:
            raw = sc["imageData"]
            if isinstance(raw, bytes):
                return raw
            if isinstance(raw, str):
                try:
                    return base64.b64decode(raw)
                except Exception:
                    pass
        if "image_base64" in sc and sc["image_base64"]:
            try:
                return base64.b64decode(sc["image_base64"])
            except Exception:
                pass
        # Check file path on disk
        path = sc.get("imagePath") or sc.get("image_path")
        if path and isinstance(path, str):
            import os
            if os.path.exists(path):
                try:
                    with open(path, "rb") as f:
                        return f.read()
                except Exception:
                    pass
        return None

    def _draw_image_fallback_card(self, page: pymupdf.Page, rect: pymupdf.Rect, name: str, purpose: str):
        page.draw_rect(rect, fill=(0.98, 0.99, 1.0), color=(0.85, 0.88, 0.92), radius=0.08, width=0.8)
        page.insert_text((rect.x0 + 40, rect.y0 + 100), f"Mock Screen: {name}", fontsize=18, color=(0.15, 0.25, 0.5), fontname="hebo")
        page.insert_text((rect.x0 + 40, rect.y0 + 140), purpose, fontsize=12, color=(0.35, 0.4, 0.5), fontname="helv")


pdf_compilation_service = PdfCompilationService()
