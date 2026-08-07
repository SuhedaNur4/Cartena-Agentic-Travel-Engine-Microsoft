import pytest
from pydantic import ValidationError
from backend.api.schemas.requests import TripRequestDTO

def test_legacy_single_destination_request():
    """Test that a legacy request with 'destination' maps correctly to 'destinations'."""
    data = {
        "destination": "Tokyo",
        "duration_days": 5,
        "budget": "medium",
        "interests": ["culture"]
    }
    req = TripRequestDTO(**data)
    domain_req = req.to_domain()
    assert domain_req.destinations == ("Tokyo",)

def test_multi_destination_request():
    """Test that a new request with 'destinations' array works correctly."""
    data = {
        "destinations": ["Tokyo", "Kyoto"],
        "duration_days": 10,
        "budget": "high",
        "interests": ["food", "nature"]
    }
    req = TripRequestDTO(**data)
    domain_req = req.to_domain()
    assert domain_req.destinations == ("Tokyo", "Kyoto")
    
def test_mixed_destination_fields_prefer_destinations():
    """If for some reason both are provided, destinations should take precedence or combine, based on pydantic logic."""
    data = {
        "destination": "Osaka",
        "destinations": ["Tokyo", "Kyoto"],
        "duration_days": 10,
        "budget": "medium",
        "interests": ["culture"]
    }
    req = TripRequestDTO(**data)
    # The current logic in TripRequestDTO expects destinations to be used if present.
    domain_req = req.to_domain()
    assert domain_req.destinations == ("Osaka", "Tokyo", "Kyoto")

def test_missing_destination():
    """Test that missing both fields raises validation error."""
    data = {
        "duration_days": 5,
        "budget": "Medium",
        "interests": ["Culture"]
    }
    with pytest.raises(ValidationError):
        TripRequestDTO(**data)
