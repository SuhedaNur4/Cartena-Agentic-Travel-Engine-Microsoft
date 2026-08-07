import pytest
import asyncio
from unittest.mock import AsyncMock
from backend.application.use_cases.allocation.engine import AllocationEngine
from backend.domain.models.trip_request import TripRequest, BudgetLevel, Interest

@pytest.fixture
def dummy_llm():
    llm = AsyncMock()
    return llm

@pytest.fixture
def engine(dummy_llm):
    return AllocationEngine(llm_client=dummy_llm)

@pytest.mark.asyncio
async def test_user_allocation_valid(engine):
    req = TripRequest(
        destinations=("Tokyo", "Kyoto", "Osaka"),
        duration_days=9,
        budget=BudgetLevel.MEDIUM,
        interests=(Interest.CULTURE,),
        allocation_mode="USER",
        allocations={"Tokyo": 4, "Kyoto": 3, "Osaka": 2}
    )
    result = await engine.allocate(req)
    assert result.allocations == {"Tokyo": 4, "Kyoto": 3, "Osaka": 2}

@pytest.mark.asyncio
async def test_user_allocation_invalid_total(engine):
    req = TripRequest(
        destinations=("Tokyo", "Kyoto"),
        duration_days=10,
        budget=BudgetLevel.MEDIUM,
        interests=(Interest.CULTURE,),
        allocation_mode="USER",
        allocations={"Tokyo": 5, "Kyoto": 6} # sum is 11
    )
    with pytest.raises(ValueError, match="Total allocated days.*does not match"):
        await engine.allocate(req)

@pytest.mark.asyncio
async def test_user_allocation_negative_or_zero(engine):
    req = TripRequest(
        destinations=("Tokyo", "Kyoto"),
        duration_days=10,
        budget=BudgetLevel.MEDIUM,
        interests=(Interest.CULTURE,),
        allocation_mode="USER",
        allocations={"Tokyo": 0, "Kyoto": 10}
    )
    with pytest.raises(ValueError, match="Must be > 0"):
        await engine.allocate(req)
        
@pytest.mark.asyncio
async def test_user_allocation_missing_destination(engine):
    req = TripRequest(
        destinations=("Tokyo", "Kyoto", "Osaka"),
        duration_days=10,
        budget=BudgetLevel.MEDIUM,
        interests=(Interest.CULTURE,),
        allocation_mode="USER",
        allocations={"Tokyo": 5, "Kyoto": 5}
    )
    with pytest.raises(ValueError, match="is missing from allocations"):
        await engine.allocate(req)

@pytest.mark.asyncio
async def test_ai_allocation_fallback_heuristic(engine, dummy_llm):
    # Setup LLM to fail
    async def mock_stream(*args, **kwargs):
        raise Exception("LLM Error")
        yield "" # to make it an async generator if needed
        
    dummy_llm.stream = mock_stream
    
    req = TripRequest(
        destinations=("Tokyo", "Kyoto", "Nara"),
        duration_days=10,
        budget=BudgetLevel.MEDIUM,
        interests=(Interest.CULTURE,),
        allocation_mode="AI"
    )
    
    result = await engine.allocate(req)
    # Even distribution for 10 days among 3 cities: 10 // 3 = 3, remainder 1 to the first city
    assert result.allocations == {"Tokyo": 4, "Kyoto": 3, "Nara": 3}
