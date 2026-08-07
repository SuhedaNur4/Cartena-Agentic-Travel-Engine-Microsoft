"""
Route Analyzer for determining the optimal sequence of destinations.
"""

from typing import Any
from pydantic import BaseModel

from backend.domain.models.trip_request import TripRequest
from backend.domain.value_objects.flight_context import FlightContext

class RouteSequence(BaseModel):
    start_city: str
    stops: list[str]
    end_city: str


class RouteAnalyzer:
    """
    Determines the optimal sequence of cities to visit based on flight context
    and distance matrix.
    """
    
    def analyze(self, request: TripRequest) -> RouteSequence:
        """
        Calculates a deterministic route sequence.
        """
        destinations = list(request.destinations)
        
        # Default start and end
        start_city = destinations[0]
        end_city = destinations[-1]
        
        # If flight context is provided, enforce start and end points
        if request.flight_context:
            if request.flight_context.arrival_city and request.flight_context.arrival_city in destinations:
                start_city = request.flight_context.arrival_city
                
            if request.flight_context.departure_city and request.flight_context.departure_city in destinations:
                end_city = request.flight_context.departure_city
                
        # Build the stops in order
        stops = []
        
        # Add start city first
        stops.append(start_city)
        
        # Add intermediate cities (not start, not end)
        for dest in destinations:
            if dest != start_city and dest != end_city:
                stops.append(dest)
                
        # Add end city if it's different from start city (or if there are multiple cities)
        if end_city != start_city or len(destinations) == 1:
            if len(destinations) > 1:
                stops.append(end_city)
                
        # In a real implementation, this is where we would use a DistanceMatrix
        # or TSP (Traveling Salesperson Problem) solver to optimally order the intermediate stops.
        
        return RouteSequence(
            start_city=start_city,
            stops=stops,
            end_city=end_city
        )
