"""Use Case: ListItineraries — return lightweight summaries of saved itineraries."""

from __future__ import annotations

from backend.application.ports.itinerary_repo_port import IItineraryRepository
from backend.domain.models.itinerary import ItinerarySummary


class ListItinerariesUseCase:
    def __init__(self, repo: IItineraryRepository) -> None:
        self._repo = repo

    async def execute(self, limit: int = 50) -> list[ItinerarySummary]:
        return await self._repo.list_all(limit=limit)
