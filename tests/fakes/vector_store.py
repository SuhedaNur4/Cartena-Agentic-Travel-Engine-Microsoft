"""Test sahtesi: IVectorStore — chromadb olmadan şehir filtreli retrieval."""

from __future__ import annotations

from backend.application.ports.vector_store_port import IVectorStore
from backend.domain.models.knowledge_chunk import KnowledgeChunk


# Sahtenin filtrelediği metadata anahtarı — ChromaAdapter ile aynı olmalı.
# `city_key` normalize edilmiş anahtardır (bkz. domain/services/city.py);
# sorgu tarafı da normalize_city()'den geçtiği için yazım farkları eşleşir.
_FILTER_KEY = "city_key"


class FakeVectorStore(IVectorStore):
    """
    In-memory vector store.

    Benzerlik hesaplamaz — `chunks` listesinin sırasını "alaka sırası" kabul eder.
    Bu, sıralamayı bozan hataları testte görünür kılar.

    Filtreleme ChromaAdapter ile aynı anahtar üzerinden yapılır (`_FILTER_KEY`):
    sahte gerçekten daha hoşgörülü olursa testler yalan söyler.
    """

    def __init__(self, chunks: list[KnowledgeChunk] | None = None) -> None:
        self._chunks: list[KnowledgeChunk] = list(chunks or [])
        self.last_city: str | None = None
        self.retrieve_calls: list[str | None] = []

    async def upsert(self, chunks: list[KnowledgeChunk], embeddings: list[list[float]]) -> None:
        by_id = {c.id: c for c in self._chunks}
        for c in chunks:
            by_id[c.id] = c
        self._chunks = list(by_id.values())

    def _matching(self, city: str | None) -> list[KnowledgeChunk]:
        if city is None:
            return self._chunks
        return [c for c in self._chunks if c.to_chroma_metadata().get(_FILTER_KEY) == city]

    async def retrieve(
        self,
        query_vector: list[float],
        city: str | None = None,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[tuple[KnowledgeChunk, float]]:
        self.last_city = city
        self.retrieve_calls.append(city)
        # Sabit 1.0 skor: testler içerik ve filtrelemeyi doğrular, skor mantığını değil.
        # min_score filtrelemesi de uygulanır (1.0 her zaman geçer, default 0.0 ile).
        return [
            (c, 1.0)
            for c in self._matching(city)[:top_k]
            if 1.0 >= min_score
        ]

    async def document_count(self, city: str | None = None) -> int:
        return len(self._matching(city))

    async def health_check(self) -> bool:
        return True
