"""
Domain value object for flight context.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class FlightContext:
    arrival_city: str | None = None
    departure_city: str | None = None
