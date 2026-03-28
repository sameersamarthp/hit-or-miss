import collections
import json
import logging
import time
from dataclasses import dataclass, field

from src.cache.chroma_cache import ChromaCacheStore
from src.config import DEFAULT_EMBEDDING_MODEL, DEFAULT_SIMILARITY_THRESHOLD, EMBEDDING_MODELS
from src.embeddings.sentence_transformer import SentenceTransformerEmbedder
from src.proxy.llm_proxy import LLMProxy

logger = logging.getLogger(__name__)

MAX_RECENT_QUERIES = 20


def _extract_prompt_text(body: dict) -> str:
    """Extract the user prompt text from an Anthropic messages-format request body.

    Concatenates all user message content blocks into a single string for embedding.
    """
    messages = body.get("messages", [])
    parts: list[str] = []

    # Include system prompt if present
    system = body.get("system")
    if system:
        if isinstance(system, str):
            parts.append(system)
        elif isinstance(system, list):
            for block in system:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block["text"])

    for msg in messages:
        if msg.get("role") != "user":
            continue
        content = msg.get("content", "")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block["text"])
    return "\n".join(parts)


def _extract_response_text(response: dict) -> str:
    """Extract the assistant text from an Anthropic response."""
    content = response.get("content", [])
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block["text"])
    return "\n".join(parts)


class CacheMiddleware:
    """Orchestrates the embed → search → hit/miss → forward → store flow."""

    def __init__(self) -> None:
        self._embedders: dict[str, SentenceTransformerEmbedder] = {}
        self._caches: dict[str, ChromaCacheStore] = {}
        self._llm_proxy = LLMProxy()
        self._active_model: str = DEFAULT_EMBEDDING_MODEL
        self._threshold: float = DEFAULT_SIMILARITY_THRESHOLD
        self._total_requests: int = 0
        self._total_hits: int = 0
        self._total_latency_ms: float = 0.0
        self._recent_queries: collections.deque[dict] = collections.deque(maxlen=MAX_RECENT_QUERIES)

    @property
    def active_model(self) -> str:
        return self._active_model

    @active_model.setter
    def active_model(self, model_name: str) -> None:
        if model_name not in EMBEDDING_MODELS:
            raise ValueError(f"Unknown model: {model_name}. Available: {list(EMBEDDING_MODELS)}")
        self._active_model = model_name
        logger.info("Switched active embedding model to: %s", model_name)

    @property
    def threshold(self) -> float:
        return self._threshold

    @threshold.setter
    def threshold(self, value: float) -> None:
        self._threshold = value

    def _get_embedder(self, model_name: str) -> SentenceTransformerEmbedder:
        if model_name not in self._embedders:
            self._embedders[model_name] = SentenceTransformerEmbedder(model_name)
        return self._embedders[model_name]

    def _get_cache(self, model_name: str) -> ChromaCacheStore:
        if model_name not in self._caches:
            self._caches[model_name] = ChromaCacheStore(model_name)
        return self._caches[model_name]

    async def process_request(
        self,
        body: dict,
        model_override: str | None = None,
        threshold_override: float | None = None,
    ) -> dict:
        """Process an incoming LLM request through the semantic cache.

        Returns a dict with:
        - response: the Anthropic-format response dict
        - cache_hit: bool
        - similarity_score: float
        - timings: dict with embed_ms, search_ms, llm_ms, total_ms
        """
        total_start = time.perf_counter()

        model_name = model_override or self._active_model
        threshold = threshold_override or self._threshold

        prompt_text = _extract_prompt_text(body)
        if not prompt_text.strip():
            raise ValueError("Could not extract prompt text from request body")

        embedder = self._get_embedder(model_name)
        cache = self._get_cache(model_name)

        # --- Embed ---
        embed_start = time.perf_counter()
        embedding = embedder.embed(prompt_text)
        embed_ms = (time.perf_counter() - embed_start) * 1000
        embedding_list = embedding.tolist()

        # --- Search ---
        cache_result = cache.search(embedding_list, threshold)

        if cache_result.hit:
            # Reconstruct an Anthropic-style response from cached data
            cached_response = {
                "id": "cache-hit",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": cache_result.cached_response}],
                "model": body.get("model", "cached"),
                "stop_reason": "end_turn",
            }
            total_ms = (time.perf_counter() - total_start) * 1000
            result = {
                "response": cached_response,
                "cache_hit": True,
                "similarity_score": cache_result.similarity_score,
                "matched_prompt": cache_result.cached_prompt,
                "timings": {
                    "embed_ms": round(embed_ms, 2),
                    "search_ms": round(cache_result.search_latency_ms, 2),
                    "llm_ms": 0,
                    "total_ms": round(total_ms, 2),
                },
            }
            self._track(prompt_text, result)
            return result

        # --- Cache MISS: forward to LLM ---
        llm_start = time.perf_counter()
        llm_response = await self._llm_proxy.send(body)
        llm_ms = (time.perf_counter() - llm_start) * 1000

        # --- Store in cache ---
        response_text = _extract_response_text(llm_response)
        usage = llm_response.get("usage", {})
        tokens_used = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        cache.store(
            prompt=prompt_text,
            embedding=embedding_list,
            response=response_text,
            metadata={"tokens_used": tokens_used},
        )

        total_ms = (time.perf_counter() - total_start) * 1000
        result = {
            "response": llm_response,
            "cache_hit": False,
            "similarity_score": cache_result.similarity_score,
            "matched_prompt": None,
            "timings": {
                "embed_ms": round(embed_ms, 2),
                "search_ms": round(cache_result.search_latency_ms, 2),
                "llm_ms": round(llm_ms, 2),
                "total_ms": round(total_ms, 2),
            },
        }
        self._track(prompt_text, result)
        return result

    def _track(self, prompt_text: str, result: dict) -> None:
        """Update stats and recent queries log."""
        self._total_requests += 1
        if result["cache_hit"]:
            self._total_hits += 1
        self._total_latency_ms += result["timings"]["total_ms"]
        self._recent_queries.appendleft({
            "prompt": prompt_text[:120],
            "cache_hit": result["cache_hit"],
            "similarity_score": result["similarity_score"],
            "timings": result["timings"],
            "model": self._active_model,
        })

    def get_stats(self) -> dict:
        """Return aggregate cache statistics."""
        cache = self._get_cache(self._active_model)
        return {
            "active_model": self._active_model,
            "threshold": self._threshold,
            "total_requests": self._total_requests,
            "total_hits": self._total_hits,
            "hit_rate": round(self._total_hits / self._total_requests, 4) if self._total_requests else 0,
            "avg_latency_ms": round(self._total_latency_ms / self._total_requests, 2) if self._total_requests else 0,
            "cache_entries": cache.count(),
        }

    def get_recent_queries(self) -> list[dict]:
        return list(self._recent_queries)

    def get_cache_for_model(self, model_name: str) -> ChromaCacheStore:
        return self._get_cache(model_name)

    async def close(self) -> None:
        await self._llm_proxy.close()
