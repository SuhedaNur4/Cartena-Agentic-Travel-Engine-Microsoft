"""Port: IEmbeddingClient — abstract interface for text embedding."""

from __future__ import annotations

from abc import ABC, abstractmethod


class IEmbeddingClient(ABC):
    """
    Metni embedding vektörüne çeviren sözleşme.

    Aktif adapter: LocalEmbeddingAdapter (sentence-transformers,
    all-MiniLM-L6-v2). Foundry Local kataloğunda embedding modeli
    bulunmadığı için Foundry adapter'ı kullanılmıyor.
    """

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """
        Generate a dense vector embedding for the given text.

        Args:
            text: The input string to embed (query or document chunk).

        Returns:
            A list of floats representing the embedding vector.
        """
        ...  # pragma: no cover

    @abstractmethod
    async def health_check(self) -> bool:
        """Returns True if the embedding service is reachable."""
        ...  # pragma: no cover

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Fiilen yüklü olan embedding modelinin adı."""
        ...  # pragma: no cover
