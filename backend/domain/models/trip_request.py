"""
Domain model: TripRequest and its value types.

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class BudgetLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    LUXURY = "luxury"

    @classmethod
    def from_label(cls, label: str) -> "BudgetLevel":
        return cls(label.lower())


class Interest(str, Enum):
    CULTURE = "culture"
    FOOD = "food"
    ADVENTURE = "adventure"
    RELAXATION = "relaxation"
    SHOPPING = "shopping"
    NATURE = "nature"
    NIGHTLIFE = "nightlife"


@dataclass(frozen=True)
class TripRequest:
    """Immutable value object representing a user's travel planning request."""

    destinations: tuple[str, ...]
    duration_days: int
    budget: BudgetLevel
    interests: tuple[Interest, ...]
    notes: str = ""
    start_date: date | None = None   # Optional trip start date; used for weather forecast
    allocation_mode: str = "AI"      # "USER" or "AI"
    allocations: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.destinations:
            raise ValueError("At least one destination must be provided.")
        if not (1 <= self.duration_days <= 30):
            raise ValueError("Trip duration must be between 1 and 30 days.")
        if not self.interests:
            raise ValueError("At least one interest must be selected.")

    @property
    def query_text(self) -> str:
        """Human-readable summary used as embedding input."""
        interests_str = ", ".join(i.value for i in self.interests)
        dest_str = " and ".join(self.destinations)
        return (
            f"{dest_str} {self.duration_days} day trip "
            f"{self.budget.value} budget {interests_str}"
        )
