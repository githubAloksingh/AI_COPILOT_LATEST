import logging
import time
from typing import List
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.candidate_models = settings.gemini_embedding_candidate_models
        self.timeout = httpx.Timeout(45.0, connect=15.0)

    def embed_text(self, text: str) -> List[float]:
        results = self.embed_texts([text])
        if not results:
            raise RuntimeError("Failed to generate embedding for single text.")
        return results[0]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        api_key = settings.gemini_api_key or self.api_key
        if not api_key or not api_key.strip():
            raise RuntimeError("GEMINI_API_KEY is missing. Cannot generate embeddings.")

        all_embeddings: List[List[float]] = []
        batch_size = 50

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_result = self._embed_batch_with_fallback(batch, api_key.strip())
            all_embeddings.extend(batch_result)

            # Subtle pacing to prevent aggressive rate limiting
            if i + batch_size < len(texts):
                time.sleep(0.1)

        return all_embeddings

    def _embed_batch_with_fallback(self, batch: List[str], api_key: str) -> List[List[float]]:
        with httpx.Client(timeout=self.timeout) as client:
            for model in self.candidate_models:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents"
                    f"?key={api_key}"
                )
                requests_payload = [
                    {
                        "model": f"models/{model}",
                        "content": {"parts": [{"text": text}]},
                    }
                    for text in batch
                ]
                body = {"requests": requests_payload}

                try:
                    resp = client.post(url, json=body)
                    if resp.status_code == 200:
                        data = resp.json()
                        if "embeddings" in data:
                            results = [
                                [float(v) for v in emb["values"]]
                                for emb in data["embeddings"]
                                if "values" in emb
                            ]
                            if len(results) == len(batch):
                                return results
                    else:
                        logger.debug("Batch embed model %s returned status %s: %s", model, resp.status_code, resp.text)
                except Exception as e:
                    logger.debug("Batch embedding with %s failed: %s", model, e)

            # Fallback to individual embeddings
            logger.warning("batchEmbedContents failed on candidate models. Falling back to individual calls.")
            fallback_list: List[List[float]] = []
            for text in batch:
                fallback_list.append(self._embed_single_text(text, api_key, client))
            return fallback_list

    def _embed_single_text(self, text: str, api_key: str, client: httpx.Client) -> List[float]:
        body = {"content": {"parts": [{"text": text}]}}
        for model in self.candidate_models:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"
                f"?key={api_key}"
            )
            try:
                resp = client.post(url, json=body)
                if resp.status_code == 200:
                    data = resp.json()
                    if "embedding" in data and "values" in data["embedding"]:
                        return [float(v) for v in data["embedding"]["values"]]
            except Exception as e:
                logger.debug("Single embedding with %s failed: %s", model, e)

        raise RuntimeError("Failed to generate embedding with Gemini models. Check GEMINI_API_KEY.")


embedding_service = EmbeddingService()
