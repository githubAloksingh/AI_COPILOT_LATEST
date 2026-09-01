import logging
from typing import List, Dict, Any, Tuple, Optional
import httpx
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import settings
from app.api.schemas import SourceDto
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(self):
        self.chroma_url = settings.chroma_url
        self.collection_name = settings.chroma_collection
        self.top_k = settings.top_k
        self.collection_id: Optional[str] = None
        self.base_collection_url: Optional[str] = None
        self._local_client: Optional[chromadb.ClientAPI] = None
        self._local_collection = None
        self.timeout = httpx.Timeout(45.0, connect=15.0)

    def _get_local_collection(self):
        """Fallback to in-memory/persistent ChromaDB client if remote server is unreachable."""
        if self._local_collection is None:
            try:
                self._local_client = chromadb.PersistentClient(
                    path=settings.chroma_persist_directory,
                    settings=ChromaSettings(anonymized_telemetry=False)
                )
                self._local_collection = self._local_client.get_or_create_collection(
                    name=self.collection_name
                )
                logger.info("Initialized local persistent ChromaDB collection: %s", self.collection_name)
            except Exception as e:
                logger.warning("Could not initialize local ChromaDB client: %s", e)
        return self._local_collection

    def ensure_collection(self):
        if self.collection_id and self.base_collection_url:
            return

        candidate_urls = []
        if settings.chroma_url and settings.chroma_url.strip():
            candidate_urls.append(settings.chroma_url.strip())
        candidate_urls.extend([
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://[::1]:8000"
        ])

        with httpx.Client(timeout=self.timeout) as client:
            for target_url in candidate_urls:
                # 1. Try v2 Chroma collections API
                try:
                    v2_url = f"{target_url}/api/v2/tenants/default_tenant/databases/default_database/collections"
                    resp = client.post(v2_url, json={"name": self.collection_name, "get_or_create": True})
                    if resp.status_code in (200, 201):
                        data = resp.json()
                        if "id" in data:
                            self.collection_id = data["id"]
                            self.base_collection_url = f"{v2_url}/{self.collection_id}"
                            logger.info("Chroma collection initialized via v2 at %s with ID %s", target_url, self.collection_id)
                            return
                except Exception:
                    pass

                # 2. Try v1 Chroma collections API
                try:
                    v1_url = f"{target_url}/api/v1/collections"
                    resp = client.post(v1_url, json={"name": self.collection_name, "get_or_create": True})
                    if resp.status_code in (200, 201):
                        data = resp.json()
                        if "id" in data:
                            self.collection_id = data["id"]
                            self.base_collection_url = f"{v1_url}/{self.collection_id}"
                            logger.info("Chroma collection initialized via v1 at %s with ID %s", target_url, self.collection_id)
                            return
                except Exception:
                    pass

        # If remote Chroma is not responding, fallback to local embedded Chroma
        logger.info("Remote Chroma unavailable. Using embedded persistent ChromaDB.")
        self._get_local_collection()

    def store_chunks(self, document_id: str, file_name: str, chunks: List[str]) -> int:
        if not chunks:
            return 0

        self.ensure_collection()
        batch_size = 50
        total_stored = 0

        for start_idx in range(0, len(chunks), batch_size):
            end_idx = min(start_idx + batch_size, len(chunks))
            chunk_batch = chunks[start_idx:end_idx]

            batch_embeddings = embedding_service.embed_texts(chunk_batch)

            ids = []
            metadatas = []
            for i, _ in enumerate(chunk_batch):
                global_index = start_idx + i
                ids.append(f"doc_{document_id}_chunk_{global_index}")
                metadatas.append({
                    "documentId": str(document_id),
                    "fileName": str(file_name or ""),
                    "chunkIndex": int(global_index)
                })

            if self.base_collection_url:
                url = f"{self.base_collection_url}/add"
                payload = {
                    "ids": ids,
                    "embeddings": batch_embeddings,
                    "metadatas": metadatas,
                    "documents": chunk_batch
                }
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code not in (200, 201):
                        logger.error("Chroma store error: %s - %s", resp.status_code, resp.text)
                        raise RuntimeError(f"Chroma storage failed with status {resp.status_code}")
                total_stored += len(chunk_batch)
            else:
                local_col = self._get_local_collection()
                if local_col:
                    local_col.upsert(
                        ids=ids,
                        embeddings=batch_embeddings,
                        metadatas=metadatas,
                        documents=chunk_batch
                    )
                    total_stored += len(chunk_batch)
                else:
                    raise RuntimeError("No available ChromaDB instance to store chunks.")

        return total_stored

    def retrieve_relevant_context(
        self, query: str, top_k: Optional[int] = None, document_id: Optional[str] = None
    ) -> Tuple[List[str], List[SourceDto]]:
        if not query or not query.strip():
            return [], []

        self.ensure_collection()
        k = top_k or self.top_k
        query_embedding = embedding_service.embed_text(query)

        chunks: List[str] = []
        sources: List[SourceDto] = []

        if self.base_collection_url:
            url = f"{self.base_collection_url}/query"
            payload: Dict[str, Any] = {
                "query_embeddings": [query_embedding],
                "n_results": k
            }
            if document_id:
                payload["where"] = {"documentId": str(document_id)}

            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    docs_list = data.get("documents", [[]])
                    metas_list = data.get("metadatas", [[]])

                    if docs_list and docs_list[0]:
                        chunks = docs_list[0]
                        metas = metas_list[0] if metas_list and metas_list[0] else []
                        for idx, chunk in enumerate(chunks):
                            meta = metas[idx] if idx < len(metas) and metas[idx] else {}
                            sources.append(SourceDto(
                                document_id=str(meta.get("documentId", "")),
                                file_name=str(meta.get("fileName", "")),
                                chunk_index=int(meta.get("chunkIndex", idx)) if meta.get("chunkIndex") is not None else idx,
                                snippet=chunk[:150] + "..." if len(chunk) > 150 else chunk
                            ))
                        return chunks, sources
        else:
            local_col = self._get_local_collection()
            if local_col:
                where_clause = {"documentId": str(document_id)} if document_id else None
                res = local_col.query(
                    query_embeddings=[query_embedding],
                    n_results=k,
                    where=where_clause
                )
                docs = res.get("documents", [[]])
                metas = res.get("metadatas", [[]])
                if docs and docs[0]:
                    chunks = docs[0]
                    for idx, chunk in enumerate(chunks):
                        meta = metas[0][idx] if metas and metas[0] and idx < len(metas[0]) else {}
                        sources.append(SourceDto(
                            document_id=str(meta.get("documentId", "")),
                            file_name=str(meta.get("fileName", "")),
                            chunk_index=int(meta.get("chunkIndex", idx)) if meta.get("chunkIndex") is not None else idx,
                            snippet=chunk[:150] + "..." if len(chunk) > 150 else chunk
                        ))
                    return chunks, sources

        return [], []


retrieval_service = RetrievalService()
