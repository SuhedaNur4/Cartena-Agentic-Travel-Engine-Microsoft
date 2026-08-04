"""API: Pydantic request schemas (input DTOs)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator

from backend.domain.models.trip_request import BudgetLevel, Interest


class TripRequestDTO(BaseModel):
    """Input DTO for the /generate endpoint. Validated before reaching the use case."""

    destination: str = Field(..., min_length=2, max_length=100, examples=["Paris"])
    duration_days: int = Field(..., ge=1, le=30, examples=[5])
    budget: BudgetLevel = Field(..., examples=[BudgetLevel.MEDIUM])
    interests: list[Interest] = Field(..., min_length=1, examples=[[Interest.CULTURE, Interest.FOOD]])
    notes: str = Field(default="", max_length=500, examples=["Traveling with kids, vegetarian"])
    title: str | None = None
    start_date: date | None = Field(
        default=None,
        examples=["2025-08-15"],
        description="Optional trip start date (ISO 8601). Used to fetch weather forecast.",
    )

    @field_validator("destination")
    @classmethod
    def strip_destination(cls, v: str) -> str:
        return v.strip()

    def to_domain(self):
        """Convert DTO → domain TripRequest."""
        from backend.domain.models.trip_request import TripRequest
        return TripRequest(
            destination=self.destination,
            duration_days=self.duration_days,
            budget=self.budget,
            interests=tuple(self.interests),
            notes=self.notes,
            start_date=self.start_date,
        )

class ToggleFavoriteRequestDTO(BaseModel):
    is_favorite: bool

class ReplanRequestDTO(BaseModel):
    reason: str | None = None

class ResumeRequestDTO(BaseModel):
    resolution_id: str
