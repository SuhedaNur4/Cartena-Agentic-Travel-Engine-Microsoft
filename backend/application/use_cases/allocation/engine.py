"""
Trip Allocation Engine.
Distributes total trip days across multiple destinations.
"""
import logging
import json
import dataclasses
from backend.domain.models.trip_request import TripRequest
from backend.application.ports.llm_port import ILLMClient

logger = logging.getLogger(__name__)


class AllocationEngine:
    def __init__(self, llm_client: ILLMClient):
        self.llm_client = llm_client

    async def allocate(self, request: TripRequest) -> TripRequest:
        """
        Determines day allocation for multiple destinations.
        Returns a new TripRequest with allocations filled.
        """
        if len(request.destinations) == 1:
            # Trivial case
            allocations = {request.destinations[0]: request.duration_days}
            return dataclasses.replace(request, allocations=allocations)

        if request.allocation_mode == "USER":
            allocations = request.allocations
            self._validate_deterministic(allocations, request.destinations, request.duration_days)
            return dataclasses.replace(request, allocations=allocations)

        # AI Mode (AI-assisted optimization)
        try:
            allocations = await self._ai_allocation(request)
            self._validate_deterministic(allocations, request.destinations, request.duration_days)
        except Exception as e:
            logger.warning(f"AI allocation failed: {e}. Falling back to even distribution.")
            allocations = self._even_distribution(request.destinations, request.duration_days)

        return dataclasses.replace(request, allocations=allocations)

    def _validate_deterministic(self, allocations: dict[str, int], destinations: tuple[str, ...], total_days: int):
        if not allocations:
            raise ValueError("Allocations dictionary is empty.")
            
        sum_days = 0
        for dest in destinations:
            if dest not in allocations:
                raise ValueError(f"Destination {dest} is missing from allocations.")
            days = allocations[dest]
            if not isinstance(days, int) or days <= 0:
                raise ValueError(f"Destination {dest} has invalid days {days}. Must be > 0.")
            sum_days += days
            
        if sum_days != total_days:
            raise ValueError(f"Total allocated days ({sum_days}) does not match trip duration ({total_days}).")

    def _even_distribution(self, destinations: tuple[str, ...], total_days: int) -> dict[str, int]:
        n = len(destinations)
        base = total_days // n
        remainder = total_days % n
        
        allocations = {}
        for i, dest in enumerate(destinations):
            allocations[dest] = base + (1 if i < remainder else 0)
        return allocations

    async def _ai_allocation(self, request: TripRequest) -> dict[str, int]:
        """Ask LLM for a reasonable distribution, falling back to heuristic if needed."""
        system_prompt = (
            "You are a master travel planner. Distribute total days across the given destinations "
            "based on their relative size, POI density, and travel importance. "
            "Return ONLY a JSON object where keys are destination names and values are integer days. "
            f"The sum of days MUST exactly equal {request.duration_days}."
        )
        dest_str = ", ".join(request.destinations)
        user_prompt = f"Destinations: {dest_str}\nTotal days: {request.duration_days}"
        
        schema = {
            "type": "object",
            "properties": {d: {"type": "integer"} for d in request.destinations},
            "required": list(request.destinations)
        }
        
        result_text = ""
        try:
            async for chunk in self.llm_client.stream(system_prompt, user_prompt, json_schema=schema):
                result_text += chunk
                
            return json.loads(result_text)
        except Exception as e:
            logger.error(f"LLM allocation failed: {e}")
            raise
