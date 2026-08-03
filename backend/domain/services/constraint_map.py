"""
Domain service: ConstraintMap

Pure function — no I/O, no external dependencies.
Derives a structured constraint dictionary from a TripRequest so the
ItineraryValidator has full context about user's actual preferences
instead of hardcoded pipeline defaults.

Design principle:
  - If user has NOT specified a preference -> mark as "unspecified" (do not guess).
  - Physical mobility != interests. Nature lovers may still love long hikes.
  - Budget values are destination-aware, not global fixed mappings.
"""

from __future__ import annotations

from backend.domain.models.trip_request import BudgetLevel, TripRequest


def build(request: TripRequest) -> dict:
    """
    Build a structured constraint map from a TripRequest.

    Returns a dict consumed by ItineraryValidator.validate().

    Keys:
        walking_tolerance      : "low" | "high" | "unspecified"
        accessibility_required : bool
        group_nearby_required  : bool
        budget_level           : str  (BudgetLevel.value)
        daily_budget_limit_usd : float | None
        currency               : "USD"
    """
    constraints: dict = {}
    notes_lower = (request.notes or "").lower()

    # -- Walking Tolerance (from explicit notes only, NOT from interests) ------
    _LOW_WALK = {"no walking", "minimal walking", "limited walking",
                 "dont walk", "mobility", "wheelchair", "cant walk far",
                 "avoid walking", "prefer not to walk", "mobility issues"}
    _HIGH_WALK = {"love walking", "lots of walking", "walking tour",
                  "hike", "hiking", "trekking", "long walks", "active day"}

    if any(sig in notes_lower for sig in _LOW_WALK):
        constraints["walking_tolerance"] = "low"
    elif any(sig in notes_lower for sig in _HIGH_WALK):
        constraints["walking_tolerance"] = "high"
    else:
        constraints["walking_tolerance"] = "unspecified"

    # -- Accessibility ---------------------------------------------------------
    _ACCESS = {"wheelchair", "mobility", "disabled", "accessibility",
               "handicap", "mobility impaired"}
    accessibility = any(sig in notes_lower for sig in _ACCESS)
    constraints["accessibility_required"] = accessibility
    constraints["group_nearby_required"] = accessibility
    if accessibility and constraints["walking_tolerance"] != "high":
        constraints["walking_tolerance"] = "low"

    # -- Budget ----------------------------------------------------------------
    constraints["budget_level"] = request.budget.value
    constraints["daily_budget_limit_usd"] = _daily_budget_usd(request.budget, request.destination)
    constraints["currency"] = "USD"

    return constraints


def _daily_budget_usd(budget: BudgetLevel, destination: str) -> float | None:
    """
    Destination-region-aware daily budget ceiling (USD, activities + meals).
    Returns None for LUXURY (no meaningful upper bound).
    """
    d = destination.lower()

    def _match(*keywords: str) -> bool:
        return any(k in d for k in keywords)

    if _match("thailand", "vietnam", "cambodia", "bali", "indonesia",
              "sri lanka", "india", "nepal", "myanmar", "laos"):
        region = "cheap_asia"
    elif _match("tokyo", "japan", "singapore", "hong kong", "seoul", "korea"):
        region = "mid_asia"
    elif _match("paris", "london", "rome", "berlin", "amsterdam", "barcelona",
                "madrid", "vienna", "copenhagen", "iceland", "reykjavik",
                "prague", "budapest", "florence", "venice", "lisbon", "athens"):
        region = "europe"
    elif _match("dubai", "abu dhabi", "qatar", "doha"):
        region = "middle_east"
    elif _match("new york", "los angeles", "miami", "chicago", "toronto",
                "vancouver", "buenos aires", "rio", "mexico", "cusco"):
        region = "americas"
    elif _match("cairo", "marrakech", "cape town", "nairobi", "zanzibar", "morocco"):
        region = "africa"
    else:
        region = "default"

    _TABLE = {
        "cheap_asia":  {BudgetLevel.LOW: 30,  BudgetLevel.MEDIUM: 60,  BudgetLevel.HIGH: 120, BudgetLevel.LUXURY: None},
        "mid_asia":    {BudgetLevel.LOW: 50,  BudgetLevel.MEDIUM: 100, BudgetLevel.HIGH: 200, BudgetLevel.LUXURY: None},
        "europe":      {BudgetLevel.LOW: 60,  BudgetLevel.MEDIUM: 130, BudgetLevel.HIGH: 250, BudgetLevel.LUXURY: None},
        "middle_east": {BudgetLevel.LOW: 60,  BudgetLevel.MEDIUM: 140, BudgetLevel.HIGH: 280, BudgetLevel.LUXURY: None},
        "americas":    {BudgetLevel.LOW: 55,  BudgetLevel.MEDIUM: 120, BudgetLevel.HIGH: 230, BudgetLevel.LUXURY: None},
        "africa":      {BudgetLevel.LOW: 40,  BudgetLevel.MEDIUM: 80,  BudgetLevel.HIGH: 160, BudgetLevel.LUXURY: None},
        "default":     {BudgetLevel.LOW: 50,  BudgetLevel.MEDIUM: 100, BudgetLevel.HIGH: 200, BudgetLevel.LUXURY: None},
    }
    return _TABLE[region][budget]
