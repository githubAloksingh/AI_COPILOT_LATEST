from abc import ABC, abstractmethod


class DocumentParser(ABC):
    @abstractmethod
    def supports(self, file_type: str, file_name: str = "") -> bool:
        """Check if parser supports the given MIME type or file extension."""
        pass

    @abstractmethod
    def parse(self, content_bytes: bytes) -> str:
        """Extract text from the document byte content."""
        pass
