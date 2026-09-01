import fitz  # PyMuPDF
from .base import DocumentParser


class PdfParser(DocumentParser):
    def supports(self, file_type: str, file_name: str = "") -> bool:
        if file_type and ("application/pdf" in file_type.lower() or file_type.lower().endswith("pdf")):
            return True
        if file_name and file_name.lower().endswith(".pdf"):
            return True
        return False

    def parse(self, content_bytes: bytes) -> str:
        doc = fitz.open(stream=content_bytes, filetype="pdf")
        text_parts = []
        for page in doc:
            page_text = page.get_text()
            if page_text:
                text_parts.append(page_text)
        doc.close()
        return "\n".join(text_parts).strip()
