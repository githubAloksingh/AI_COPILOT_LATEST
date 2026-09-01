from .base import DocumentParser


class TextParser(DocumentParser):
    def supports(self, file_type: str, file_name: str = "") -> bool:
        if file_type and (
            "text" in file_type.lower()
            or "txt" in file_type.lower()
            or "markdown" in file_type.lower()
            or "json" in file_type.lower()
        ):
            return True
        if file_name:
            lower = file_name.lower()
            return lower.endswith(".txt") or lower.endswith(".md") or lower.endswith(".json")
        return False

    def parse(self, content_bytes: bytes) -> str:
        return content_bytes.decode("utf-8", errors="replace").strip()
