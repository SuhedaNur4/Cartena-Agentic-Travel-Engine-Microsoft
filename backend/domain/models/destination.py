"""
Domain models for destinations and knowledge.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResolvedDestination:
    """Canonical representation of a destination."""
    input_name: str
    canonical_name: str
    country: str | None = None
    region: str | None = None
    destination_type: str = "city"  # e.g., 'city', 'country', 'region'


@dataclass
class KnowledgeDocument:
    """A unit of knowledge retrieved from any knowledge provider."""
    source: str           # e.g., "local", "wikipedia"
    title: str            # Document title or destination name
    content: str          # The actual text content
    destination: str      # Canonical name of the destination this document belongs to
    metadata: dict[str, Any] = field(default_factory=dict)
