"""API: Pydantic request schemas (input DTOs)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.domain.models.trip_request import BudgetLevel, Interest


class FlightContextDTO(BaseModel):
    arrival_city: str | None = Field(default=None, description="City where the user arrives")
    departure_city: str | None = Field(default=None, description="City from where the user departs")

class TripRequestDTO(BaseModel):
    """Input DTO for the /generate endpoint. Validated before reaching the use case."""

    destination: str = Field(..., max_length=100, examples=["Paris"])
    destinations: list[str] | None = Field(default=None, examples=[["Tokyo", "Kyoto"]])
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

    allocation_mode: str = Field(default="AI", examples=["USER", "AI"])
    allocations: dict[str, int] = Field(default_factory=dict, examples=[{"Tokyo": 2, "Kyoto": 3}])
    flight_context: FlightContextDTO | None = None

    @model_validator(mode='after')
    def check_destinations(self):
        dest_list = self.destinations or []
        if self.destination:
            dest = self.destination.strip()
            if dest and dest not in dest_list:
                dest_list.insert(0, dest)
        if not dest_list:
            raise ValueError("Either 'destination' or 'destinations' must be provided and not empty.")
        self.destinations = dest_list
        return self

    def to_domain(self):
        """Convert DTO → domain TripRequest."""
        from backend.domain.models.trip_request import TripRequest
        from backend.domain.value_objects.flight_context import FlightContext
        
        fc = None
        if self.flight_context:
            fc = FlightContext(
                arrival_city=self.flight_context.arrival_city,
                departure_city=self.flight_context.departure_city
            )
            
        return TripRequest(
            destinations=tuple(self.destinations),
            duration_days=self.duration_days,
            budget=self.budget,
            interests=tuple(self.interests),
            notes=self.notes,
            start_date=self.start_date,
            allocation_mode=self.allocation_mode,
            allocations=self.allocations,
            flight_context=fc
        )

class ToggleFavoriteRequestDTO(BaseModel):
    is_favorite: bool

class ReplanRequestDTO(BaseModel):
    reason: str | None = None

class ResumeRequestDTO(BaseModel):
    resolution_id: str
