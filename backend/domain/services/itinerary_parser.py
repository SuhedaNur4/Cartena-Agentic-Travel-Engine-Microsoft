"""
Domain service: ItineraryParser.

Pure function — no I/O, no external dependencies (only stdlib + pydantic for validation).

Parsing strategy (approved in architecture review):
  1. PRIMARY:  Parse raw LLM text as JSON → validate with Pydantic schema.
  2. FALLBACK: If JSON extraction fails, apply regex section-marker parsing.
  3. LAST RESORT: Return a single-day itinerary with the raw text in the description.

This layered approach gives JSON reliability while degrading gracefully on
smaller models that occasionally produce malformed JSON.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from backend.domain.models.itinerary import (
    ActivityBlock,
    Day,
    Itinerary,
    MealSuggestion,
)
from backend.domain.models.trip_request import BudgetLevel, TripRequest

logger = logging.getLogger(__name__)


# ── Pydantic validation schemas (internal — not exposed as API DTOs) ────────────

class _ActivitySchema(BaseModel):
    description: str = ""
    location: str = ""
    why_recommended: str = ""
    duration_estimate: str = ""
    cost_estimate: str = ""
    reservation_needed: bool = False
    transport_suggestion: str = ""


class _MealsSchema(BaseModel):
    breakfast: str = ""
    lunch: str = ""
    dinner: str = ""


class _DaySchema(BaseModel):
    day_number: int
    title: str = ""
    morning: _ActivitySchema = Field(default_factory=_ActivitySchema)
    afternoon: _ActivitySchema = Field(default_factory=_ActivitySchema)
    evening: _ActivitySchema = Field(default_factory=_ActivitySchema)
    meals: _MealsSchema = Field(default_factory=_MealsSchema)
    budget_estimate: str = "medium"
    tips: list[str] = Field(default_factory=list)

    @field_validator("budget_estimate")
    @classmethod
    def normalize_budget(cls, v: str) -> str:
        valid = {"low", "medium", "high", "luxury"}
        normalized = v.lower().strip()
        return normalized if normalized in valid else "medium"

    @field_validator("tips")
    @classmethod
    def ensure_two_tips(cls, v: list[str]) -> list[str]:
        # Pad or trim to ensure exactly 2 tips
        while len(v) < 2:
            v.append("")
        return v[:2]


class _ItinerarySchema(BaseModel):
    days: list[_DaySchema]


# ── Public parse function ───────────────────────────────────────────────────────

def get_json_schema() -> dict[str, Any]:
    """Return the JSON schema for the itinerary structure, to be used in LLM tools."""
    activity_schema = {
        "type": "object",
        "properties": {
            "description": {"type": "string", "default": ""},
            "location": {"type": "string", "default": ""},
            "why_recommended": {"type": "string", "default": ""},
            "duration_estimate": {"type": "string", "default": ""},
            "cost_estimate": {"type": "string", "default": ""},
            "reservation_needed": {"type": "boolean", "default": False},
            "transport_suggestion": {"type": "string", "default": ""}
        }
    }
    
    return {
        "type": "object",
        "properties": {
            "days": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "day_number": {"type": "integer"},
                        "title": {"type": "string", "default": ""},
                        "morning": activity_schema,
                        "afternoon": activity_schema,
                        "evening": activity_schema,
                        "meals": {
                            "type": "object",
                            "properties": {
                                "breakfast": {"type": "string", "default": ""},
                                "lunch": {"type": "string", "default": ""},
                                "dinner": {"type": "string", "default": ""}
                            }
                        },
                        "budget_estimate": {"type": "string", "default": "medium"},
                        "tips": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["day_number"]
                }
            }
        },
        "required": ["days"]
    }

def parse(
    raw_response: str,
    trip_request: TripRequest,
    model_used: str,
) -> Itinerary:
    """
    Parse the LLM's raw text output into an Itinerary domain model.

    Attempts JSON parsing first, falls back to regex, then returns a
    best-effort single-day itinerary if all else fails.
    """
    days = (
        _try_json_parse(raw_response)
        or _try_regex_parse(raw_response, trip_request.duration_days)
        or _fallback_parse(raw_response)
    )

    return Itinerary(
        trip_request=trip_request,
        days=days,
        model_used=model_used,
        raw_response=raw_response,
    )


# ── Strategy 1: JSON parse + Pydantic validation ───────────────────────────────

def _try_json_parse(raw: str) -> list[Day] | None:
    """Extract JSON from the response and validate against the schema."""
    json_str = _extract_json_block(raw)
    if not json_str:
        return None

    try:
        data: dict[str, Any] = json.loads(json_str)
        schema = _ItinerarySchema.model_validate(data)
        return [_schema_day_to_domain(d) for d in schema.days]
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning("JSON parse failed: %s", exc)
        return None


def _extract_json_block(text: str) -> str | None:
    """
    Locate the JSON object in the response.
    Handles cases where the LLM wraps JSON in markdown code fences.
    """
    # Strip markdown fences if present
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1)

    # Find raw JSON object (greedy from first { to last })
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        return brace_match.group(0)

    return None


def _schema_day_to_domain(d: _DaySchema) -> Day:
    return Day(
        day_number=d.day_number,
        title=d.title,
        morning=ActivityBlock(
            d.morning.description, d.morning.location,
            d.morning.why_recommended, d.morning.duration_estimate,
            d.morning.cost_estimate, d.morning.reservation_needed,
            d.morning.transport_suggestion
        ),
        afternoon=ActivityBlock(
            d.afternoon.description, d.afternoon.location,
            d.afternoon.why_recommended, d.afternoon.duration_estimate,
            d.afternoon.cost_estimate, d.afternoon.reservation_needed,
            d.afternoon.transport_suggestion
        ),
        evening=ActivityBlock(
            d.evening.description, d.evening.location,
            d.evening.why_recommended, d.evening.duration_estimate,
            d.evening.cost_estimate, d.evening.reservation_needed,
            d.evening.transport_suggestion
        ),
        meals=MealSuggestion(d.meals.breakfast, d.meals.lunch, d.meals.dinner),
        budget_estimate=BudgetLevel(d.budget_estimate),
        tips=d.tips,
    )


# ── Strategy 2: Regex section-marker parsing ────────────────────────────────────

_DAY_PATTERN = re.compile(
    r"Day\s+(\d+)[:\-–]\s*(.+?)(?=Day\s+\d+[:\-–]|\Z)",
    re.DOTALL | re.IGNORECASE,
)
_SECTION_PATTERN = re.compile(
    r"(Morning|Afternoon|Evening|Breakfast|Lunch|Dinner|Tips?)[:\-–]\s*(.+?)(?=Morning|Afternoon|Evening|Breakfast|Lunch|Dinner|Tips?|\Z)",
    re.DOTALL | re.IGNORECASE,
)


def _try_regex_parse(raw: str, expected_days: int) -> list[Day] | None:
    """Parse structured text using section markers as anchors."""
    day_matches = _DAY_PATTERN.findall(raw)
    if not day_matches:
        return None

    days: list[Day] = []
    for day_num_str, day_body in day_matches:
        sections = {
            m.group(1).lower(): m.group(2).strip()
            for m in _SECTION_PATTERN.finditer(day_body)
        }
        day = Day(
            day_number=int(day_num_str),
            title=day_body.split("\n")[0].strip()[:120],
            morning=ActivityBlock(sections.get("morning", "")),
            afternoon=ActivityBlock(sections.get("afternoon", "")),
            evening=ActivityBlock(sections.get("evening", "")),
            meals=MealSuggestion(
                sections.get("breakfast", ""),
                sections.get("lunch", ""),
                sections.get("dinner", ""),
            ),
            budget_estimate=BudgetLevel.MEDIUM,
            tips=_extract_tips(sections.get("tips", sections.get("tip", ""))),
        )
        days.append(day)

    logger.info("Regex parser extracted %d days (expected %d)", len(days), expected_days)
    return days if days else None


def _extract_tips(raw_tips: str) -> list[str]:
    lines = [line.strip("•- ").strip() for line in raw_tips.split("\n") if line.strip()]
    return (lines + ["", ""])[:2]


# ── Strategy 3: Last-resort fallback ───────────────────────────────────────────

def _fallback_parse(raw: str) -> list[Day]:
    """Return the full raw response as a single day's morning description."""
    logger.warning("All parsing strategies failed; using raw fallback.")
    return [
        Day(
            day_number=1,
            title="Itinerary (unstructured)",
            morning=ActivityBlock(raw[:2000], ""),
            afternoon=ActivityBlock("", ""),
            evening=ActivityBlock("", ""),
            meals=MealSuggestion(),
            budget_estimate=BudgetLevel.MEDIUM,
            tips=["Parsing encountered issues — please regenerate.", ""],
        )
    ]
