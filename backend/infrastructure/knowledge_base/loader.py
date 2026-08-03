"""
Infrastructure: Knowledge Base Loader

Reads the destinations.json seed file and converts it to KnowledgeChunk domain models.
Pure I/O function — no business logic.
"""

from __future__ import annotations

import json
import logging
import hashlib
from pathlib import Path

from backend.domain.models.knowledge_chunk import KnowledgeChunk

logger = logging.getLogger(__name__)


def load(kb_path: str) -> list[KnowledgeChunk]:
    """
    Load and parse the knowledge base JSON file.

    Expected JSON format:
    [
      {
        "city": "Paris",
        "category": "landmarks",
        "content": "...",
        "tags": ["culture", "art"],
        "budget_tiers": ["medium", "high"]
      },
      ...
    ]

    Returns:
        List of KnowledgeChunk domain models with deterministic IDs.
    """
    path = Path(kb_path)
    if not path.exists():
        logger.warning("Knowledge base file not found: %s", kb_path)
        return []

    with path.open(encoding="utf-8") as f:
        raw: list[dict] = json.load(f)

    chunks: list[KnowledgeChunk] = []
    city_counters: dict[str, int] = {}

    for entry in raw:
        city = entry.get("city", "unknown").lower().replace(" ", "_")
        category = entry.get("category", "general")
        content = entry.get("content", "")
        
        # Ingestion idempotency: use content hash instead of counter
        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()[:12]

        chunk = KnowledgeChunk(
            id=f"{city}_{category}_{content_hash}",
            city=entry.get("city", "Unknown"),
            category=category,
            content=content,
            tags=tuple(entry.get("tags", [])),
            budget_tiers=tuple(entry.get("budget_tiers", [])),
            lat=entry.get("lat"),
            lon=entry.get("lon"),
        )
        chunks.append(chunk)

    logger.info("Loaded %d knowledge chunks from %s", len(chunks), kb_path)
    return chunks
