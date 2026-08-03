"""
Infrastructure: ChromaAdapter

Implements IVectorStore using ChromaDB in embedded (local) persistent mode.
No separate ChromaDB server process required — the DB lives in a local directory.
"""

from __future__ import annotations

import asyncio
import logging
from functools import partial

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.application.ports.vector_store_port import IVectorStore
from backend.domain.models.knowledge_chunk import KnowledgeChunk

logger = logging.getLogger(__name__)


class ChromaAdapter(IVectorStore):
    """
    Vector store backed by ChromaDB in local persistent mode.

    Uses cosine similarity (configured at collection creation).
    City-level filtering uses ChromaDB's `where` metadata filter.

    Thread safety: ChromaDB's Python client is not async-native.
    Heavy operations (upsert during ingestion) run in a thread pool.
    Retrieval is fast enough to run synchronously within the executor
    without measurable impact on response latency.
    """

    def __init__(self, persist_dir: str, collection_name: str) -> None:
        self._persist_dir = persist_dir
        self._collection_name = collection_name
        self._client: chromadb.PersistentClient | None = None
        self._collection = None

    def _init_client(self) -> None:
        """Synchronous client + collection initialization."""
        if self._client is not None:
            return

        logger.info("Initializing ChromaDB at: %s", self._persist_dir)
        self._client = chromadb.PersistentClient(
            path=self._persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "ChromaDB ready. Collection '%s' has %d documents.",
            self._collection_name,
            self._collection.count(),
        )

    async def _ensure_ready(self) -> None:
        if self._client is None:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._init_client)

    async def upsert(
        self,
        chunks: list[KnowledgeChunk],
        embeddings: list[list[float]],
    ) -> None:
        await self._ensure_ready()

        def _do_upsert() -> None:
            self._collection.upsert(
                ids=[c.id for c in chunks],
                documents=[c.content for c in chunks],
                embeddings=embeddings,
                metadatas=[c.to_chroma_metadata() for c in chunks],
            )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _do_upsert)
        logger.info("Upserted %d chunks into ChromaDB.", len(chunks))

    async def retrieve(
        self,
        query_vector: list[float],
        city: str | None = None,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[tuple[KnowledgeChunk, float]]:
        await self._ensure_ready()

        # `city` buraya normalize edilmiş olarak gelir (bkz. GenerateItineraryUseCase).
        where = {"city_key": city} if city else None

        def _do_query() -> list[tuple[KnowledgeChunk, float]]:
            try:
                result = self._collection.query(
                    query_embeddings=[query_vector],
                    n_results=top_k,
                    where=where,
                    include=["documents", "distances", "metadatas"],
                )
                ids = result["ids"][0] if result["ids"] else []
                docs = result["documents"][0] if result["documents"] else []
                metas = result["metadatas"][0] if result["metadatas"] else []
                dists = result["distances"][0] if result["distances"] else []
                
                pairs = []
                for chunk_id, doc, meta, dist in zip(ids, docs, metas, dists):
                    score = round(1.0 - dist, 4)
                    if score >= min_score:
                        chunk = KnowledgeChunk.from_chroma_metadata(chunk_id, doc, meta)
                        pairs.append((chunk, score))
                return pairs
            except Exception as exc:
                # ChromaDB raises if where-filter matches 0 documents
                logger.warning("ChromaDB query failed (city=%s): %s", city, exc)
                return []

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _do_query)

    async def document_count(self, city: str | None = None) -> int:
        await self._ensure_ready()

        def _do_count() -> int:
            if city:
                result = self._collection.get(where={"city_key": city})
                return len(result["ids"])
            return self._collection.count()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _do_count)

    async def health_check(self) -> bool:
        try:
            await self._ensure_ready()
            return self._collection is not None
        except Exception:
            return False
