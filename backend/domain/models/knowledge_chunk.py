"""
Domain model: KnowledgeChunk — a unit of the destination knowledge base.

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.domain.services.city import normalize_city


@dataclass(frozen=True)
class KnowledgeChunk:
    """
    A single semantically coherent piece of destination knowledge.

    Each chunk is independently embeddable and retrievable from ChromaDB.
    The `id` field is derived deterministically as `{city}_{category}_{index}`
    to make ingestion idempotent.
    """

    id: str
    city: str
    category: str           # landmarks | cuisine | budget | culture | safety
    content: str
    tags: tuple[str, ...] = field(default_factory=tuple)
    budget_tiers: tuple[str, ...] = field(default_factory=tuple)
    lat: float | None = None
    lon: float | None = None

    def to_chroma_metadata(self) -> dict:
        """
        ChromaDB metadata sözlüğü (yalnızca string değerler).

        `city` gösterim içindir ("New York").
        `city_key` filtreleme içindir ("new york") — sorgu tarafı da
        normalize_city()'den geçtiği için yazım farkları eşleşmeyi bozmaz.
        """
        metadata = {
            "city": self.city,
            "city_key": normalize_city(self.city),
            "category": self.category,
            "tags": ",".join(self.tags),
            "budget_tiers": ",".join(self.budget_tiers),
        }
        if self.lat is not None:
            metadata["lat"] = self.lat
        if self.lon is not None:
            metadata["lon"] = self.lon
        return metadata

    @classmethod
    def from_chroma_metadata(cls, id_: str, content: str, metadata: dict) -> KnowledgeChunk:
        return cls(
            id=id_,
            city=metadata.get("city", ""),
            category=metadata.get("category", ""),
            content=content,
            tags=tuple(t.strip() for t in metadata.get("tags", "").split(",") if t.strip()),
            budget_tiers=tuple(t.strip() for t in metadata.get("budget_tiers", "").split(",") if t.strip()),
            lat=metadata.get("lat"),
            lon=metadata.get("lon"),
        )
