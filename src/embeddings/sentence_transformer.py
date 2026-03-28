import logging
import time

import numpy as np
from sentence_transformers import SentenceTransformer

from src.embeddings.base import EmbedderBase

logger = logging.getLogger(__name__)

# Models that need a query prefix for retrieval tasks
_BGE_MODELS = {"BAAI/bge-large-en-v1.5", "BAAI/bge-base-en-v1.5", "BAAI/bge-small-en-v1.5"}


class SentenceTransformerEmbedder(EmbedderBase):
    """Embedder backed by sentence-transformers. Lazy-loads the model on first use."""

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model: SentenceTransformer | None = None
        self._dimension: int | None = None

    def _load_model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info("Loading embedding model: %s", self._model_name)
            start = time.perf_counter()
            self._model = SentenceTransformer(self._model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
            elapsed = time.perf_counter() - start
            logger.info(
                "Model %s loaded in %.2fs (dim=%d)",
                self._model_name,
                elapsed,
                self._dimension,
            )
        return self._model

    def _prepare_text(self, text: str) -> str:
        """Add model-specific prefixes for query-time embedding."""
        if self._model_name in _BGE_MODELS:
            return f"Represent this sentence: {text}"
        return text

    def embed(self, text: str) -> np.ndarray:
        model = self._load_model()
        prepared = self._prepare_text(text)
        embedding: np.ndarray = model.encode(prepared, convert_to_numpy=True)
        return embedding

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        model = self._load_model()
        prepared = [self._prepare_text(t) for t in texts]
        embeddings: np.ndarray = model.encode(prepared, convert_to_numpy=True, batch_size=32)
        return [embeddings[i] for i in range(len(texts))]

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            self._load_model()
        return self._dimension  # type: ignore[return-value]
