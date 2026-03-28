from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CacheResult:
    hit: bool
    similarity_score: float
    cached_prompt: str | None
    cached_response: str | None
    search_latency_ms: float


class CacheStoreBase(ABC):
    @abstractmethod
    def search(self, embedding: list[float], threshold: float) -> CacheResult:
        """Search for a similar prompt. Return CacheResult."""
        pass

    @abstractmethod
    def store(self, prompt: str, embedding: list[float], response: str, metadata: dict) -> None:
        """Store a prompt-response pair with its embedding."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all entries in this cache."""
        pass

    @abstractmethod
    def get_all_entries(self) -> list[dict]:
        """Return all cached entries (for the inspector UI)."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Return number of entries in cache."""
        pass
