from typing import List
from app.config import settings


class ChunkingService:
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

    def chunk_text(self, text: str, chunk_size: int = None, chunk_overlap: int = None) -> List[str]:
        if not text:
            return []

        c_size = chunk_size or self.chunk_size
        c_overlap = chunk_overlap if chunk_overlap is not None else self.chunk_overlap

        chunks = []
        length = len(text)
        step = c_size - c_overlap

        if step <= 0:
            step = c_size

        for i in range(0, length, step):
            end = min(i + c_size, length)
            chunk = text[i:end]
            if chunk.strip():
                chunks.append(chunk)
            if end == length:
                break

        return chunks


chunking_service = ChunkingService()
