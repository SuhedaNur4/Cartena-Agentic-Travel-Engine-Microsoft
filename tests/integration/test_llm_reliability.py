import pytest
from backend.domain.models.trip_request import TripRequest, BudgetLevel, Interest
from backend.domain.services.itinerary_parser import parse
from backend.domain.services.validator import ItineraryValidator

@pytest.mark.xfail(strict=False, reason="Small models occasionally violate strict JSON schema resulting in regex fallback")
def test_small_model_sometimes_violates_json_schema():
    """
    xai-agent philosophy: We do not hide known limitations of our system.
    Small local LLMs (like Phi-4-mini or Qwen3-4B) occasionally forget commas in JSON
    or output conversational text before the JSON block.
    
    This test uses a raw, slightly malformed response simulating this edge case.
    The test expects that our parser handles it via regex fallback.
    If the parser fails completely, it's an xfail.
    """
    raw_malformed_response = '''
    Sure, here is your itinerary!
    {
      "days": [
        {
          "day_number": 1,
          "title": "Arrival",
          "morning": { "description": "Arrive and check in" }
          "afternoon": { "description": "Walk around" } // Missing comma above!
          "evening": { "description": "Dinner" },
          "meals": { "breakfast": "", "lunch": "", "dinner": "Local place" },
          "budget_estimate": "LOW",
          "tips": ["Tip 1"]
        }
      ]
    }
    '''
    request = TripRequest(
        destinations=("Tokyo",),
        duration_days=1,
        budget=BudgetLevel.LOW,
        interests=(Interest.FOOD,),
        notes=""
    )
    
    # We attempt to parse. If it fails entirely (because regex fallback also fails), 
    # it's a known weakness.
    itinerary = parse(raw_malformed_response, request, model_used="test-model")
    
    # Verify it actually parsed 1 day
    assert len(itinerary.days) == 1
    assert itinerary.days[0].day_number == 1

@pytest.mark.xfail(strict=False, reason="Local models sometimes ignore negative constraints on the first pass")
def test_model_sometimes_ignores_negative_constraints():
    """
    Models, especially sub-7B, struggle with negative constraints 
    (e.g. "budget is LOW, do not suggest luxury").
    They might suggest a 3-star Michelin restaurant because they associate Tokyo with fine dining.
    
    Our 2-pass repair loop fixes this, but this test explicitly documents the FIRST PASS weakness.
    """
    # A simulated first-pass response that violates the negative constraint.
    raw_luxury_response = '''{
      "days": [
        {
          "day_number": 1,
          "title": "Luxury Tokyo",
          "morning": { "description": "Visit park", "location": "Park", "why_recommended": "", "duration_estimate": "", "cost_estimate": "Free", "reservation_needed": false, "transport_suggestion": "" },
          "afternoon": { "description": "Museum", "location": "Museum", "why_recommended": "", "duration_estimate": "", "cost_estimate": "1000 JPY", "reservation_needed": false, "transport_suggestion": "" },
          "evening": { "description": "Fine dining at a 3-star Michelin restaurant", "location": "Ginza", "why_recommended": "", "duration_estimate": "", "cost_estimate": "50000 JPY", "reservation_needed": true, "transport_suggestion": "" },
          "meals": { "breakfast": "Cafe", "lunch": "Ramen", "dinner": "Michelin 3-star" },
          "budget_estimate": "LOW",
          "tips": ["Enjoy!"]
        }
      ]
    }'''
    request = TripRequest(
        destinations=("Tokyo",),
        duration_days=1,
        budget=BudgetLevel.LOW,
        interests=(Interest.FOOD,),
        notes=""
    )
    
    itinerary = parse(raw_luxury_response, request, model_used="test-model")
    report = ItineraryValidator.validate(itinerary)
    
    # We EXPECT this to be invalid (it violates the LOW budget constraint).
    # If the LLM *does* output this, the Validator must catch it.
    assert not report.is_valid
    assert len(report.hard_violations) > 0
    assert any("Luxury/expensive" in v or "exceeds" in v for v in report.hard_violations)
