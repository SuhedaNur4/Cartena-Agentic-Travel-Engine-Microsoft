"""Use Case: UpdateDay — patch a single day's content in a saved itinerary."""

from __future__ import annotations

import dataclasses

from backend.application.ports.itinerary_repo_port import IItineraryRepository
from backend.domain.models.itinerary import Day


class UpdateDayUseCase:
    def __init__(self, repo: IItineraryRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        itinerary_id: str,
        day_number: int,
        updates: dict,
    ) -> bool:
        """
        Apply partial updates to a single day of a saved itinerary.

        Args:
            itinerary_id: UUID of the saved itinerary.
            day_number:   1-indexed day to update.
            updates:      Dict with optional keys: title, morning, afternoon,
                          evening, meals, tips, budget_estimate.

        Returns:
            True if the day was found and updated, False if not found.
        """
        itinerary = await self._repo.get(itinerary_id)
        if not itinerary:
            return False

        target_day: Day | None = next(
            (d for d in itinerary.days if d.day_number == day_number), None
        )
        if not target_day is None:
            day_idx = itinerary.days.index(target_day)

            # Apply supported scalar updates
            for field in ("title",):
                if field in updates:
                    setattr(itinerary.days[day_idx], field, updates[field])

            if "tips" in updates:
                itinerary.days[day_idx].tips = updates["tips"]

        await self._repo.update(itinerary)
        return True
