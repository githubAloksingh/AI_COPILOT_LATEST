from importlib import import_module

__all__ = [
    "DocumentService",
    "document_service",
    "ChunkingService",
    "chunking_service",
    "EmbeddingService",
    "embedding_service",
    "RetrievalService",
    "retrieval_service",
    "GeminiService",
    "gemini_service",
    "RagService",
    "rag_service",
]


def __getattr__(name):
    module_map = {
        "DocumentService": (".document_service", "DocumentService"),
        "document_service": (".document_service", "document_service"),
        "ChunkingService": (".chunking_service", "ChunkingService"),
        "chunking_service": (".chunking_service", "chunking_service"),
        "EmbeddingService": (".embedding_service", "EmbeddingService"),
        "embedding_service": (".embedding_service", "embedding_service"),
        "RetrievalService": (".retrieval_service", "RetrievalService"),
        "retrieval_service": (".retrieval_service", "retrieval_service"),
        "GeminiService": (".gemini_service", "GeminiService"),
        "gemini_service": (".gemini_service", "gemini_service"),
        "RagService": (".rag_service", "RagService"),
        "rag_service": (".rag_service", "rag_service"),
    }
    if name in module_map:
        module_name, attribute_name = module_map[name]
        module = import_module(module_name, __name__)
        value = getattr(module, attribute_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
