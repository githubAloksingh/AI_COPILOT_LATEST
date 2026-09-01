from app.services.chunking_service import ChunkingService


def test_chunking_sliding_window():
    service = ChunkingService(chunk_size=10, chunk_overlap=2)
    text = "0123456789ABCDEF"  # length 16, step = 8 -> [0..10], [8..16]
    chunks = service.chunk_text(text, chunk_size=10, chunk_overlap=2)
    assert len(chunks) == 2
    assert chunks[0] == "0123456789"
    assert chunks[1] == "89ABCDEF"


def test_chunking_empty():
    service = ChunkingService(chunk_size=100, chunk_overlap=10)
    assert service.chunk_text("") == []
    assert service.chunk_text(None) == []


def test_chunking_single_small_text():
    service = ChunkingService(chunk_size=100, chunk_overlap=10)
    text = "Short text"
    chunks = service.chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0] == "Short text"
