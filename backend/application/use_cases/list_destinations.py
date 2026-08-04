"""Use Case: ListDestinations — return unique destinations from saved itinerary history."""

from __future__ import annotations

from backend.application.ports.itinerary_repo_port import IItineraryRepository


class ListDestinationsUseCase:
    def __init__(self, repo: IItineraryRepository) -> None:
        self._repo = repo

    async def execute(self) -> list[str]:
        """Return a sorted, deduplicated list of all destination names ever saved."""
        summaries = await self._repo.list_all(limit=500)
        seen: dict[str, None] = {}
        for s in summaries:
            seen[s.destination] = None
        return sorted(seen.keys())
