import pytest
import asyncio
import os
from backend.core.config import Settings
from backend.core.container import build
from backend.domain.models.trip_request import TripRequest, BudgetLevel, Interest

@pytest.mark.external
@pytest.mark.asyncio
async def test_e2e_multi_dest_flow():
    # Only run this if we are actively opting into the full LLM E2E, 
    # but we can try it, it will fail on CI if Ollama is not running.
    # The user requested to run this, so we assume Ollama is active.
    
    settings = Settings()
    container = build(settings)
    
    req = TripRequest(
        destinations=("Tokyo", "Kyoto", "Eskişehir"),
        duration_days=10,
        budget=BudgetLevel.MEDIUM,
        interests=(Interest.CULTURE, Interest.FOOD),
        allocation_mode="USER",
        allocations={"Tokyo": 4, "Kyoto": 4, "Eskişehir": 2}
    )
    
    events = []
    
    try:
        async for event in container.generate_itinerary.execute(request=req):
            events.append(event)
            if event["type"] == "error":
                pytest.fail(f"Pipeline failed with error: {event['message']}")
    except Exception as e:
        # If Ollama is missing or no model is found, we can't fully run E2E on local without mocking
        # but the prompt specifically said "aktif Ollama/local LLM ile gerçek 10 günlük Tokyo + Kyoto + Eskişehir E2E".
        pytest.fail(f"Unhandled exception during execution: {e}")
        
    # Assertions based on the Validation Gate
    
    # 1. Check if generation completed successfully
    done_events = [e for e in events if e["type"] == "done"]
    assert len(done_events) > 0, "Generator did not complete successfully"

    assert "id" in done_events[0]
    assert done_events[0]["is_complete"] is True
    
    # Since we can't easily inspect internal state here without mocking, this E2E test proves that 
    # the orchestration and LLM integration works without crashing.

@pytest.mark.external
@pytest.mark.asyncio
async def test_e2e_unknown_destination_failure():
    settings = Settings()
    container = build(settings)
    
    req = TripRequest(
        destinations=("Tokyo", "Fakeland"),
        duration_days=5,
        budget=BudgetLevel.MEDIUM,
        interests=(Interest.CULTURE,),
        allocation_mode="USER",
        allocations={"Tokyo": 3, "Fakeland": 2}
    )
    
    events = []
    async for event in container.generate_itinerary.execute(request=req):
        events.append(event)
        
    # It should never reach done, it should emit an error
    error_events = [e for e in events if e["type"] == "error"]
    assert len(error_events) > 0, "Unknown destination did not produce an error"
    assert "Fakeland" in error_events[0]["message"]
    
    done_events = [e for e in events if e["type"] == "done"]
    assert len(done_events) == 0, "Unknown destination reached generation step (Hallucination risk)"
