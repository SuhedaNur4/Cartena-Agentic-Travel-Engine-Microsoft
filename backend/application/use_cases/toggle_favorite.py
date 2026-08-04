"""Use Case: ToggleFavorite — flip the is_favorite flag on a saved itinerary."""

from __future__ import annotations

from backend.application.ports.itinerary_repo_port import IItineraryRepository


class ToggleFavoriteUseCase:
    def __init__(self, repo: IItineraryRepository) -> None:
        self._repo = repo

    async def execute(self, itinerary_id: str) -> bool | None:
        """
        Toggle the is_favorite flag on the given itinerary.

        Returns:
            The new is_favorite value after toggling, or None if not found.
        """
        itinerary = await self._repo.get(itinerary_id)
        if not itinerary:
            return None

        itinerary.is_favorite = not itinerary.is_favorite
        await self._repo.update(itinerary)
        return itinerary.is_favorite
