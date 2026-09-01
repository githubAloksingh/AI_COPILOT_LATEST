import csv
import io
from .base import DocumentParser


class CsvParser(DocumentParser):
    def supports(self, file_type: str, file_name: str = "") -> bool:
        if file_type and ("csv" in file_type.lower() or "comma-separated" in file_type.lower()):
            return True
        if file_name and file_name.lower().endswith(".csv"):
            return True
        return False

    def parse(self, content_bytes: bytes) -> str:
        text_content = content_bytes.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text_content))
        
        try:
            headers = next(reader)
        except StopIteration:
            return ""

        if not headers:
            return ""

        lines = []
        row_index = 1
        for row in reader:
            if not row or not any(cell.strip() for cell in row):
                continue
            
            parts = []
            for j, cell in enumerate(row):
                header = headers[j].strip() if j < len(headers) and headers[j] and headers[j].strip() else f"Col{j}"
                val = cell.strip() if cell else ""
                parts.append(f"{header}={val}")
            
            lines.append(f"Row {row_index}: {', '.join(parts)}")
            row_index += 1

        return "\n".join(lines).strip()
