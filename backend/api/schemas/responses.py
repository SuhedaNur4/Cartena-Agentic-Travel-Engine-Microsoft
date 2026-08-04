"""API: Pydantic response schemas (output DTOs)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from backend.domain.models.trip_request import BudgetLevel, Interest


class ActivityBlockDTO(BaseModel):
    description: str
    location: str = ""
    why_recommended: str = ""
    duration_estimate: str = ""
    cost_estimate: str = ""
    reservation_needed: bool = False
    transport_suggestion: str = ""


class MealSuggestionDTO(BaseModel):
    breakfast: str
    lunch: str
    dinner: str


class DayDTO(BaseModel):
    day_number: int
    title: str
    morning: ActivityBlockDTO
    afternoon: ActivityBlockDTO
    evening: ActivityBlockDTO
    meals: MealSuggestionDTO
    budget_estimate: BudgetLevel
    tips: list[str]


class ItineraryResponseDTO(BaseModel):
    """Full itinerary DTO for viewing/editing."""

    id: str
    destination: str
    duration_days: int
    budget: BudgetLevel
    interests: list[Interest]
    notes: str
    model_used: str
    created_at: datetime
    day_count: int
    is_complete: bool
    kb_miss: bool
    is_favorite: bool
    days: list[DayDTO]


class ItinerarySummaryDTO(BaseModel):
    """Lightweight DTO for the history list view."""

    id: str
    destination: str
    duration_days: int
    budget: BudgetLevel
    model_used: str
    created_at: datetime
    day_count: int
    is_favorite: bool


class HealthResponseDTO(BaseModel):
    status: str                         # "healthy" | "degraded" | "offline"
    llm: str                            # "online" | "offline"
    embedding: str                      # "online" | "offline"
    chroma: str                         # "ready" | "not_ready"
    kb_document_count: int
    llm_model: str
    embedding_model: str


class ErrorResponseDTO(BaseModel):
    error: str
    detail: str = ""
