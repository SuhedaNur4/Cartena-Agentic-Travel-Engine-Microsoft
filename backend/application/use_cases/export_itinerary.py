"""
Use Case: ExportItinerary — convert a saved itinerary to Markdown or JSON.

Pure formatting logic — no I/O beyond the repository read.
"""

from __future__ import annotations

import json

from backend.application.ports.itinerary_repo_port import IItineraryRepository
from backend.domain.models.itinerary import ActivityBlock, Itinerary


def _block_dict(block: ActivityBlock) -> dict:
    """ActivityBlock -> export sözlüğü. Yedi alanın tamamı."""
    return {
        "description": block.description,
        "location": block.location,
        "why_recommended": block.why_recommended,
        "duration_estimate": block.duration_estimate,
        "cost_estimate": block.cost_estimate,
        "reservation_needed": block.reservation_needed,
        "transport_suggestion": block.transport_suggestion,
    }


class ExportItineraryUseCase:
    def __init__(self, repo: IItineraryRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        itinerary_id: str,
        fmt: str = "json",
    ) -> tuple[str, str] | None:
        """
        Returns (content_string, mime_type) or None if not found.

        Args:
            itinerary_id: UUID of the saved itinerary.
            fmt:          "json" or "md"
        """
        itinerary = await self._repo.get(itinerary_id)
        if not itinerary:
            return None

        if fmt == "md":
            return self._to_markdown(itinerary), "text/markdown"
        return self._to_json(itinerary), "application/json"

    # ── Formatters ─────────────────────────────────────────────────────────────

    @staticmethod
    def _to_json(itinerary: Itinerary) -> str:
        data = {
            "id": itinerary.id,
            "destination": itinerary.destination,
            "duration_days": itinerary.duration_days,
            "budget": itinerary.trip_request.budget.value,
            "interests": [i.value for i in itinerary.trip_request.interests],
            "model_used": itinerary.model_used,
            "created_at": itinerary.created_at.isoformat(),
            "days": [
                {
                    "day_number": day.day_number,
                    "title": day.title,
                    "morning": _block_dict(day.morning),
                    "afternoon": _block_dict(day.afternoon),
                    "evening": _block_dict(day.evening),
                    "meals": {
                        "breakfast": day.meals.breakfast,
                        "lunch": day.meals.lunch,
                        "dinner": day.meals.dinner,
                    },
                    "budget_estimate": day.budget_estimate.value,
                    "tips": day.tips,
                }
                for day in itinerary.days
            ],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def _to_markdown(itinerary: Itinerary) -> str:
        lines: list[str] = [
            f"# {itinerary.destination} — {itinerary.duration_days}-Day Itinerary",
            f"",
            f"**Budget:** {itinerary.trip_request.budget.value.capitalize()}  ",
            f"**Interests:** {', '.join(i.value for i in itinerary.trip_request.interests)}  ",
            f"**Generated:** {itinerary.created_at.strftime('%Y-%m-%d')}  ",
            f"**Model:** {itinerary.model_used}",
            f"",
            "---",
            "",
        ]

        for day in itinerary.days:
            lines += [
                f"## Day {day.day_number}: {day.title}",
                "",
                f"### 🌅 Morning",
                f"{day.morning.description}",
                f"📍 *{day.morning.location}*" if day.morning.location else "",
                "",
                f"### ☀️ Afternoon",
                f"{day.afternoon.description}",
                f"📍 *{day.afternoon.location}*" if day.afternoon.location else "",
                "",
                f"### 🌙 Evening",
                f"{day.evening.description}",
                f"📍 *{day.evening.location}*" if day.evening.location else "",
                "",
                f"### 🍽️ Meals",
                f"- **Breakfast:** {day.meals.breakfast}",
                f"- **Lunch:** {day.meals.lunch}",
                f"- **Dinner:** {day.meals.dinner}",
                "",
                f"### 💡 Tips",
            ]
            for tip in day.tips:
                if tip:
                    lines.append(f"- {tip}")
            lines += [
                f"",
                f"**Daily budget:** {day.budget_estimate.value.capitalize()}",
                "",
                "---",
                "",
            ]

        return "\n".join(lines)
