from abc import ABC, abstractmethod
import numpy as np


class EmbedderBase(ABC):
    @abstractmethod
    def embed(self, text: str) -> np.ndarray:
        """Generate embedding vector for a text string."""
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings for a batch of texts."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass
