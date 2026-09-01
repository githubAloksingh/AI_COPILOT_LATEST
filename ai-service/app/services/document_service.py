import logging
import re
from typing import Optional
from app.parsers import ALL_PARSERS

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(self):
        self.parsers = ALL_PARSERS

    def extract_text(self, content_bytes: bytes, file_name: str = "", file_type: str = "") -> str:
        """Find appropriate parser and extract text."""
        effective_type = file_type or ""
        if not effective_type or effective_type == "unknown":
            if file_name and "." in file_name:
                effective_type = file_name.split(".")[-1].lower()

        matched_parser = None
        for parser in self.parsers:
            if parser.supports(effective_type, file_name):
                matched_parser = parser
                break

        if not matched_parser:
            raise ValueError(f"Unsupported file type: {effective_type or file_name}")

        raw_text = matched_parser.parse(content_bytes)
        return self.clean_text(raw_text)

    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""
        # Normalize carriage returns
        cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
        # Remove null characters
        cleaned = cleaned.replace("\x00", "")
        # Remove excessive whitespace runs (more than 3 newlines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()


document_service = DocumentService()
