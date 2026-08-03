"""Port: IVectorStore — abstract interface for semantic vector retrieval."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.domain.models.knowledge_chunk import KnowledgeChunk


class IVectorStore(ABC):
    """
    Defines the contract for storing and retrieving knowledge chunks
    by semantic similarity.

    The concrete adapter (ChromaAdapter) uses ChromaDB with cosine similarity.
    A future adapter might use Pinecone, Qdrant, or pgvector.
    """

    @abstractmethod
    async def upsert(
        self,
        chunks: list[KnowledgeChunk],
        embeddings: list[list[float]],
    ) -> None:
        """
        Insert or update knowledge chunks and their pre-computed embeddings.

        Args:
            chunks:     The knowledge chunks to store.
            embeddings: Pre-computed embedding vectors aligned with `chunks`.
        """
        ...  # pragma: no cover

    @abstractmethod
    async def retrieve(
        self,
        query_vector: list[float],
        city: str | None = None,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[tuple[KnowledgeChunk, float]]:
        """
        Find the top-k chunks most semantically similar to `query_vector`.

        Args:
            query_vector: Embedding of the user's query.
            city:         Optional filter — restrict results to a specific city.
            top_k:        Number of results to return.
            min_score:    Minimum cosine similarity (0–1). Chunks below this
                          threshold are excluded from the result. Default 0.0
                          (no filtering) keeps behaviour backward-compatible.

        Returns:
            List of (chunk, similarity_score) tuples, ordered by relevance descending.
        """
        ...  # pragma: no cover

    @abstractmethod
    async def document_count(self, city: str | None = None) -> int:
        """Returns the total number of indexed chunks, optionally filtered by city."""
        ...  # pragma: no cover

    @abstractmethod
    async def health_check(self) -> bool:
        """Returns True if the vector store is ready."""
        ...  # pragma: no cover
