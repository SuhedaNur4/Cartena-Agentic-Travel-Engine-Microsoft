"""Unit tests for ItineraryParser — all three parsing strategies."""

import json
import pytest

from backend.domain.models.trip_request import BudgetLevel, Interest, TripRequest
from backend.domain.services.itinerary_parser import parse


@pytest.fixture
def trip_request() -> TripRequest:
    return TripRequest(
        destinations=("Paris",),
        duration_days=3,
        budget=BudgetLevel.MEDIUM,
        interests=(Interest.CULTURE,),
    )


def make_json_response(days: int) -> str:
    data = {
        "days": [
            {
                "day_number": i + 1,
                "title": f"Day {i + 1} in Paris",
                "morning": {"description": "Visit the Louvre", "location": "Louvre Museum"},
                "afternoon": {"description": "Walk along the Seine", "location": "Seine River"},
                "evening": {"description": "Dinner at a bistro", "location": "Le Marais"},
                "meals": {
                    "breakfast": "Croissant at a boulangerie",
                    "lunch": "Croque-monsieur",
                    "dinner": "Duck confit",
                },
                "budget_estimate": "medium",
                "tips": ["Book Louvre tickets online", "Arrive early"],
            }
            for i in range(days)
        ]
    }
    return json.dumps(data)


# ── Strategy 1: JSON parsing ────────────────────────────────────────────────────

class TestJSONParsing:
    def test_valid_json_produces_correct_day_count(self, trip_request):
        raw = make_json_response(3)
        itinerary = parse(raw, trip_request, "phi-4-mini")
        assert len(itinerary.days) == 3

    def test_day_fields_populated(self, trip_request):
        raw = make_json_response(1)
        itinerary = parse(raw, trip_request, "phi-4-mini")
        day = itinerary.days[0]
        assert day.morning.description == "Visit the Louvre"
        assert day.morning.location == "Louvre Museum"
        assert day.meals.breakfast == "Croissant at a boulangerie"
        assert day.budget_estimate == BudgetLevel.MEDIUM
        assert len(day.tips) == 2

    def test_json_wrapped_in_markdown_fence(self, trip_request):
        raw = f"```json\n{make_json_response(2)}\n```"
        itinerary = parse(raw, trip_request, "phi-4-mini")
        assert len(itinerary.days) == 2

    def test_invalid_budget_normalized_to_medium(self, trip_request):
        data = {"days": [{"day_number": 1, "title": "Day 1", "morning": {"description": "test", "location": ""},
                          "afternoon": {"description": "", "location": ""}, "evening": {"description": "", "location": ""},
                          "meals": {"breakfast": "", "lunch": "", "dinner": ""},
                          "budget_estimate": "unknown_value", "tips": []}]}
        itinerary = parse(json.dumps(data), trip_request, "phi-4-mini")
        assert itinerary.days[0].budget_estimate == BudgetLevel.MEDIUM

    def test_trip_request_preserved(self, trip_request):
        raw = make_json_response(3)
        itinerary = parse(raw, trip_request, "phi-4-mini")
        assert itinerary.trip_request is trip_request
        assert itinerary.model_used == "phi-4-mini"


# ── Strategy 2: Regex parsing ───────────────────────────────────────────────────

class TestRegexFallback:
    def test_regex_parses_section_markers(self, trip_request):
        raw = """
Day 1: Arrival in Paris
Morning: Visit the Eiffel Tower and enjoy the views.
Afternoon: Explore Le Marais neighborhood.
Evening: Dinner at a classic bistro in Saint-Germain.
Breakfast: Croissant at Café de Flore.
Lunch: Croque-monsieur.
Dinner: Duck confit.
Tips:
- Book timed entry tickets in advance
- Wear comfortable shoes

Day 2: Museums and Culture
Morning: The Louvre Museum.
Afternoon: Musée d'Orsay.
Evening: Seine River cruise.
"""
        itinerary = parse(raw, trip_request, "phi-4-mini")
        assert len(itinerary.days) >= 2


# ── Strategy 3: Fallback ────────────────────────────────────────────────────────

class TestLastResortFallback:
    def test_completely_unparseable_returns_single_day(self, trip_request):
        raw = "This is just some random text with no structure at all."
        itinerary = parse(raw, trip_request, "phi-4-mini")
        assert len(itinerary.days) == 1
        assert "Parsing encountered issues" in itinerary.days[0].tips[0]

    def test_raw_response_preserved(self, trip_request):
        raw = "Some raw response text."
        itinerary = parse(raw, trip_request, "phi-4-mini")
        assert itinerary.raw_response == raw
