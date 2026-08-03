"""Port: IItineraryRepository — abstract interface for itinerary persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.domain.models.itinerary import Itinerary, ItinerarySummary


class IItineraryRepository(ABC):
    """
    Defines the contract for persisting and retrieving itineraries.

    The concrete adapter (SQLiteItineraryRepo) uses aiosqlite.
    Future adapters might target PostgreSQL or a cloud database.
    """

    @abstractmethod
    async def save(self, itinerary: Itinerary) -> str:
        """
        Persist a complete itinerary and return its assigned UUID.

        The `itinerary.id` field will be set by this method if empty.
        """
        ...  # pragma: no cover

    @abstractmethod
    async def get(self, itinerary_id: str) -> Itinerary | None:
        """Return the full itinerary for the given ID, or None if not found."""
        ...  # pragma: no cover

    @abstractmethod
    async def list_all(self, limit: int = 50) -> list[ItinerarySummary]:
        """
        Return lightweight summaries for all saved itineraries.

        Args:
            limit: Maximum number of results (most recent first).
        """
        ...  # pragma: no cover

    @abstractmethod
    async def delete(self, itinerary_id: str) -> bool:
        """Delete an itinerary by ID. Returns True if it existed."""
        ...  # pragma: no cover

    @abstractmethod
    async def get_destinations(self) -> list[dict]:
        """
        Return a list of unique destinations and their plan counts.
        Format: [{"destination": str, "trips": int, "last_planned": str}]
        """
        ...  # pragma: no cover

    @abstractmethod
    async def toggle_favorite(self, itinerary_id: str, is_favorite: bool) -> bool:
        """Sets the is_favorite flag for an itinerary."""
        ...  # pragma: no cover

    @abstractmethod
    async def update_day(self, itinerary_id: str, day: 'Day') -> bool:
        """Update a specific day's JSON within an itinerary."""
        ...  # pragma: no cover
