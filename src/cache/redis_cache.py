import logging
import time
from datetime import datetime, timezone

from redisvl.extensions.cache.llm import SemanticCache
from redisvl.utils.vectorize import HFTextVectorizer

from src.cache.base import CacheResult, CacheStoreBase

logger = logging.getLogger(__name__)

REDIS_URL = "redis://localhost:6379"

# Map our model names to the HF model names that RedisVL's vectorizer expects.
# This is only used to set the correct vector dimension in the index schema.
# We always pass pre-computed vectors — the vectorizer is never called for embedding.
_MODEL_TO_HF = {
    "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
    "all-mpnet-base-v2": "sentence-transformers/all-mpnet-base-v2",
    "BAAI/bge-large-en-v1.5": "BAAI/bge-large-en-v1.5",
}


def _index_name_for_model(model_name: str) -> str:
    safe_name = model_name.replace("/", "_").replace("-", "_")
    return f"semcache_{safe_name}"


class RedisCacheStore(CacheStoreBase):
    """Redis-backed semantic cache using RedisVL's SemanticCache.

    One index per embedding model. Uses cosine distance internally.
    """

    def __init__(self, model_name: str, redis_url: str = REDIS_URL, overwrite: bool = False) -> None:
        self._model_name = model_name
        self._index_name = _index_name_for_model(model_name)

        hf_model = _MODEL_TO_HF.get(model_name, model_name)
        vectorizer = HFTextVectorizer(model=hf_model)

        self._cache = SemanticCache(
            name=self._index_name,
            redis_url=redis_url,
            distance_threshold=0.15,  # default, overridden per query
            vectorizer=vectorizer,
            overwrite=overwrite,
        )

        logger.info(
            "Redis cache ready: index=%s (dim=%d)",
            self._index_name,
            vectorizer.dims,
        )

    def search(self, embedding: list[float], threshold: float) -> CacheResult:
        start = time.perf_counter()

        # Always fetch the nearest neighbor (broad search), then check
        # threshold in code. This avoids a double-query on misses and
        # matches ChromaDB's single-query approach.
        results = self._cache.check(
            vector=embedding,
            num_results=1,
            distance_threshold=2.0,  # accept anything
        )

        elapsed_ms = (time.perf_counter() - start) * 1000

        if not results:
            # Empty cache
            logger.info("Redis Cache MISS (empty cache, latency=%.1fms)", elapsed_ms)
            return CacheResult(
                hit=False, similarity_score=0.0,
                cached_prompt=None, cached_response=None,
                search_latency_ms=elapsed_ms,
            )

        entry = results[0]
        distance = float(entry.get("vector_distance", 2.0))
        similarity = 1.0 - distance

        if similarity >= threshold:
            logger.info(
                "Redis Cache HIT (score=%.4f, threshold=%.2f, latency=%.1fms)",
                similarity, threshold, elapsed_ms,
            )
            return CacheResult(
                hit=True,
                similarity_score=similarity,
                cached_prompt=entry.get("prompt", ""),
                cached_response=entry.get("response", ""),
                search_latency_ms=elapsed_ms,
            )

        logger.info(
            "Redis Cache MISS (best_score=%.4f, threshold=%.2f, latency=%.1fms)",
            similarity, threshold, elapsed_ms,
        )
        return CacheResult(
            hit=False,
            similarity_score=similarity,
            cached_prompt=None,
            cached_response=None,
            search_latency_ms=elapsed_ms,
        )

    def store(self, prompt: str, embedding: list[float], response: str, metadata: dict) -> None:
        store_metadata = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hit_count": 0,
            **{k: v for k, v in metadata.items() if k not in ("response", "timestamp")},
        }
        self._cache.store(
            prompt=prompt,
            response=response,
            vector=embedding,
            metadata=store_metadata,
        )
        logger.info("Stored Redis cache entry (index=%s)", self._index_name)

    def clear(self) -> None:
        self._cache.clear()
        logger.info("Cleared Redis cache: %s", self._index_name)

    def get_all_entries(self) -> list[dict]:
        try:
            r = self._cache._index.client
            from redis.commands.search.query import Query
            q = Query("*").paging(0, 10000)
            results = r.ft(self._index_name).search(q)
            entries = []
            for doc in results.docs:
                entries.append({
                    "id": doc.id,
                    "prompt": getattr(doc, "prompt", ""),
                    "metadata": {
                        "response": getattr(doc, "response", ""),
                        "timestamp": getattr(doc, "updated_at", ""),
                        "hit_count": 0,
                        "tokens_used": getattr(doc, "tokens_used", 0),
                    },
                })
            return entries
        except Exception as e:
            logger.warning("Failed to get all Redis entries: %s", e)
            return []

    def count(self) -> int:
        try:
            info = self._cache._index.info()
            return int(info.get("num_docs", 0))
        except Exception:
            return 0
