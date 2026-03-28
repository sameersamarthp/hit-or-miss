import hashlib
import logging
import time
from datetime import datetime, timezone

import chromadb

from src.cache.base import CacheResult, CacheStoreBase
from src.config import CHROMA_PERSIST_DIR, collection_name_for_model

logger = logging.getLogger(__name__)

# Singleton ChromaDB client — shared across all cache instances
_chroma_client: chromadb.ClientAPI | None = None


def _get_chroma_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        logger.info("ChromaDB client initialised (persist_dir=%s)", CHROMA_PERSIST_DIR)
    return _chroma_client


def _hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()


class ChromaCacheStore(CacheStoreBase):
    """ChromaDB-backed semantic cache. One collection per embedding model."""

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        client = _get_chroma_client()
        col_name = collection_name_for_model(model_name)
        self._collection = client.get_or_create_collection(
            name=col_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "Cache collection ready: %s (%d entries)",
            col_name,
            self._collection.count(),
        )

    def search(self, embedding: list[float], threshold: float) -> CacheResult:
        start = time.perf_counter()

        if self._collection.count() == 0:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return CacheResult(
                hit=False,
                similarity_score=0.0,
                cached_prompt=None,
                cached_response=None,
                search_latency_ms=elapsed_ms,
            )

        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=1,
            include=["documents", "metadatas", "distances"],
        )

        elapsed_ms = (time.perf_counter() - start) * 1000

        # ChromaDB cosine distance = 1 - cosine_similarity
        distance = results["distances"][0][0]  # type: ignore[index]
        similarity = 1.0 - distance

        if similarity >= threshold:
            metadata = results["metadatas"][0][0]  # type: ignore[index]
            cached_prompt = results["documents"][0][0]  # type: ignore[index]
            logger.info(
                "Cache HIT (score=%.4f, threshold=%.2f, latency=%.1fms)",
                similarity,
                threshold,
                elapsed_ms,
            )
            return CacheResult(
                hit=True,
                similarity_score=similarity,
                cached_prompt=cached_prompt,
                cached_response=metadata.get("response", ""),
                search_latency_ms=elapsed_ms,
            )

        logger.info(
            "Cache MISS (best_score=%.4f, threshold=%.2f, latency=%.1fms)",
            similarity,
            threshold,
            elapsed_ms,
        )
        return CacheResult(
            hit=False,
            similarity_score=similarity,
            cached_prompt=None,
            cached_response=None,
            search_latency_ms=elapsed_ms,
        )

    def store(self, prompt: str, embedding: list[float], response: str, metadata: dict) -> None:
        doc_id = _hash_prompt(prompt)
        store_metadata = {
            "response": response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hit_count": 0,
            **{k: v for k, v in metadata.items() if k != "response"},
        }
        self._collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[prompt],
            metadatas=[store_metadata],
        )
        logger.info("Stored cache entry (id=%s…, collection=%s)", doc_id[:12], self._collection.name)

    def clear(self) -> None:
        client = _get_chroma_client()
        col_name = self._collection.name
        client.delete_collection(col_name)
        self._collection = client.get_or_create_collection(
            name=col_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Cleared cache collection: %s", col_name)

    def get_all_entries(self) -> list[dict]:
        if self._collection.count() == 0:
            return []
        results = self._collection.get(include=["documents", "metadatas"])
        entries = []
        for i, doc_id in enumerate(results["ids"]):
            entries.append({
                "id": doc_id,
                "prompt": results["documents"][i],  # type: ignore[index]
                "metadata": results["metadatas"][i],  # type: ignore[index]
            })
        return entries

    def count(self) -> int:
        return self._collection.count()
