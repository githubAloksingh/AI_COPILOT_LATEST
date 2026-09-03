import io
import logging
import zipfile
from typing import Dict, List, Tuple

from .base import DocumentParser

logger = logging.getLogger(__name__)

# Extensions to treat as readable code/text files
ALLOWED_EXTENSIONS = {
    ".java", ".py", ".ts", ".js", ".jsx", ".tsx",
    ".json", ".sql", ".html", ".css", ".scss",
    ".yml", ".yaml", ".properties", ".xml",
    ".go", ".cs", ".cpp", ".c", ".h", ".rs", ".kt",
    ".php", ".rb", ".sh", ".md", ".env.example"
}

# Directories and patterns to ignore
IGNORED_DIRS = {
    ".git", ".idea", ".vscode", "__pycache__", "node_modules",
    "target", "build", "dist", ".next", ".gradle", "bin", "obj",
    "out", ".mvn", "coverage", ".pytest_cache"
}

IGNORED_EXTENSIONS = {
    ".class", ".jar", ".war", ".pyc", ".exe", ".dll", ".so",
    ".zip", ".tar", ".gz", ".7z", ".pdf", ".png", ".jpg", ".jpeg",
    ".gif", ".ico", ".svg", ".mp4", ".mov", ".woff", ".woff2",
    ".ttf", ".eot", ".map"
}

MAX_TOTAL_CHARS = 70000
MAX_PER_FILE_CHARS = 10000


class ZipParser(DocumentParser):
    """Extracts project structure and readable source code from a ZIP archive."""

    def supports(self, file_type: str, file_name: str = "") -> bool:
        ext = file_name.lower().endswith(".zip") if file_name else False
        mime = "zip" in file_type.lower() if file_type else False
        return ext or mime

    def parse(self, content_bytes: bytes) -> str:
        _, summary = ZipParser.extract_zip(content_bytes)
        return summary

    @staticmethod
    def extract_zip(zip_bytes: bytes) -> Tuple[List[str], str]:
        """
        Parses a zip archive and returns:
        1. List of key source file paths found.
        2. Formatted summary containing project structure and key source code contents.
        """
        if not zip_bytes:
            return [], "Empty zip archive."

        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                all_names = z.namelist()

                # Filter valid source code files
                valid_files = []
                for name in all_names:
                    # Skip directories
                    if name.endswith("/") or name.endswith("\\"):
                        continue

                    # Split path parts to check against ignored directories
                    parts = name.replace("\\", "/").split("/")
                    if any(part in IGNORED_DIRS or part.startswith(".") for part in parts[:-1]):
                        continue

                    filename = parts[-1]
                    if filename.startswith("."):
                        continue

                    # Check extension
                    ext = ""
                    if "." in filename:
                        ext = "." + filename.rsplit(".", 1)[-1].lower()

                    if ext in IGNORED_EXTENSIONS:
                        continue

                    if ext in ALLOWED_EXTENSIONS or filename in {"Dockerfile", "Makefile", "Jenkinsfile"}:
                        valid_files.append(name)

                if not valid_files:
                    return [], "No supported source code files found in the ZIP archive."

                # Prioritize key architectural files: controllers, services, routes, models, entities, handlers
                def file_priority(path: str) -> int:
                    lower = path.lower()
                    if any(k in lower for k in ["controller", "route", "endpoint", "api", "resource"]):
                        return 0
                    if any(k in lower for k in ["service", "handler", "manager", "business", "logic"]):
                        return 1
                    if any(k in lower for k in ["model", "entity", "schema", "dto", "domain", "repository"]):
                        return 2
                    if any(k in lower for k in ["app", "main", "server", "index"]):
                        return 3
                    return 4

                valid_files.sort(key=file_priority)

                extracted_sources: List[str] = []
                code_sections: List[str] = []
                total_chars = 0

                # Include project structure overview (first 80 files)
                structure_overview = "Project Structure (sampled):\n" + "\n".join(f"- {f}" for f in valid_files[:80])
                code_sections.append(structure_overview)
                total_chars += len(structure_overview)

                for file_path in valid_files:
                    if total_chars >= MAX_TOTAL_CHARS:
                        code_sections.append(f"\n... [Remaining {len(valid_files) - len(extracted_sources)} source files omitted to stay within token limits]")
                        break

                    try:
                        with z.open(file_path) as f:
                            raw = f.read()
                            # Decode safely
                            try:
                                text = raw.decode("utf-8")
                            except UnicodeDecodeError:
                                text = raw.decode("latin-1", errors="ignore")

                            # Limit per-file length
                            if len(text) > MAX_PER_FILE_CHARS:
                                text = text[:MAX_PER_FILE_CHARS] + "\n... [truncated file content]"

                            section = f"\n\n--- FILE: {file_path} ---\n{text}"
                            code_sections.append(section)
                            total_chars += len(section)
                            extracted_sources.append(file_path)

                    except Exception as e:
                        logger.warning("Could not read %s from zip: %s", file_path, e)

                return extracted_sources, "".join(code_sections)

        except zipfile.BadZipFile:
            logger.error("Uploaded file is not a valid zip archive.")
            return [], "Invalid or corrupted zip archive."
        except Exception as e:
            logger.error("Error reading zip archive: %s", e)
            return [], f"Failed to extract zip contents: {str(e)}"
