"""
Infrastructure: IngestionService

Ingests the knowledge base into ChromaDB at application startup.
Always re-embeds and upserts every chunk (idempotent by ID via ChromaDB's
upsert) — there is no count-based skip, so metadata schema changes (e.g.
adding `city_key`) and KB content edits always take effect on restart.
"""

from __future__ import annotations

import logging

from backend.application.ports.embedding_port import IEmbeddingClient
from backend.application.ports.vector_store_port import IVectorStore
from backend.domain.models.knowledge_chunk import KnowledgeChunk

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Runs once during application startup via the FastAPI lifespan event.
    Rebuilds the ChromaDB index from the seed knowledge base every startup.
    """

    def __init__(
        self,
        vector_store: IVectorStore,
        embedding_client: IEmbeddingClient,
    ) -> None:
        self._vector_store = vector_store
        self._embedding_client = embedding_client

    async def ingest(self, chunks: list[KnowledgeChunk]) -> int:
        """
        Embed and upsert all knowledge chunks into the vector store.

        Every chunk is re-embedded and re-upserted on each call — there is
        no count-based skip. ChromaDB's upsert is idempotent by ID, so this
        is safe; it also guarantees metadata schema changes and KB content
        edits are always reflected after a restart.

        Returns the number of chunks ingested.
        """
        if not chunks:
            logger.info("No chunks to ingest.")
            return 0

        # Sayı tabanlı atlama yok: upsert ID'ye göre idempotent, ve her açılışta
        # yeniden gömmek KB metni değiştiğinde bayat vektör kalmasını önler.
        # 33 chunk ~ birkaç saniye. KB binlere çıkarsa içerik hash'i ile revize et.
        logger.info("Ingesting %d KB chunks into vector store...", len(chunks))

        embeddings: list[list[float]] = []
        for i, chunk in enumerate(chunks):
            vector = await self._embedding_client.embed(chunk.content)
            embeddings.append(vector)
            if (i + 1) % 10 == 0:
                logger.info("  Embedded %d / %d chunks...", i + 1, len(chunks))

        await self._vector_store.upsert(chunks, embeddings)
        logger.info("Ingestion complete. %d chunks indexed.", len(chunks))
        return len(chunks)
