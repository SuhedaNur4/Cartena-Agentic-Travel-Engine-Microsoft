"""Use Case: GetItinerary — fetch a single saved itinerary by ID."""

from __future__ import annotations

from backend.application.ports.itinerary_repo_port import IItineraryRepository
from backend.domain.models.itinerary import Itinerary


class GetItineraryUseCase:
    def __init__(self, repo: IItineraryRepository) -> None:
        self._repo = repo

    async def execute(self, itinerary_id: str) -> Itinerary | None:
        return await self._repo.get(itinerary_id)
