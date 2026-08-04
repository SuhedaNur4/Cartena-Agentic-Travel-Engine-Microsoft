"""
Integration tests to verify the deterministic routing logic of the State Graph orchestration.
These tests mock the LLM and validation outputs to force specific state transitions,
ensuring the graph behaves correctly under valid, repairable, and exhausted conditions.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.domain.models.trip_request import TripRequest, BudgetLevel, Interest
from backend.domain.models.itinerary import Itinerary, Day, ActivityBlock
from backend.domain.services.validator import ViolationReport
from backend.application.use_cases.state_graph.state import CartenaState
from backend.application.use_cases.generate_itinerary import GenerateItineraryUseCase

# ── Fixtures & Mocks ────────────────────────────────────────────────────────

@pytest.fixture
def mock_trip_request():
    return TripRequest(
        destination="Tokyo",
        duration_days=1,
        budget=BudgetLevel.MEDIUM,
        interests=(Interest.CULTURE,),
        notes=""
    )

@pytest.fixture
def mock_valid_itinerary(mock_trip_request):
    return Itinerary(
        trip_request=mock_trip_request,
        days=[
            Day(
                day_number=1,
                title="Test Day",
                morning=ActivityBlock(description="Test"),
                afternoon=ActivityBlock(description="Test"),
                evening=ActivityBlock(description="Test"),
                meals={"breakfast": "Test", "lunch": "Test", "dinner": "Test"},
                budget_estimate="MEDIUM",
                tips=["Enjoy"]
            )
        ],
        model_used="test-model"
    )

@pytest.fixture
def mock_incomplete_itinerary(mock_trip_request):
    # An itinerary missing its days (simulating a parse failure)
    return Itinerary(trip_request=mock_trip_request, days=[], model_used="test-model")


@pytest.fixture
def mock_dependencies():
    llm_client = AsyncMock()
    llm_client.model_name = "test-model"
    # Stream needs to return an async iterator
    async def mock_stream(*args, **kwargs):
        yield "fake response"
    llm_client.stream = mock_stream
    
    embedding_client = AsyncMock()
    embedding_client.embed.return_value = [0.1, 0.2]
    
    vector_store = AsyncMock()
    # retrieve needs to return list of (Chunk, score)
    vector_store.retrieve.return_value = []
    
    itinerary_repo = AsyncMock()
    itinerary_repo.save.return_value = "test-id-123"
    
    return {
        "llm_client": llm_client,
        "embedding_client": embedding_client,
        "vector_store": vector_store,
        "itinerary_repo": itinerary_repo,
        "online_adapters": []
    }


# ── Tests ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("backend.application.use_cases.state_graph.nodes.itinerary_parser.parse")
@patch("backend.application.use_cases.state_graph.nodes.ItineraryValidator.validate")
async def test_graph_valid_path(
    mock_validate, mock_parse, mock_dependencies, mock_trip_request, mock_valid_itinerary
):
    """
    Scenario: The LLM produces a completely valid itinerary on the first try.
    Expected Path: retrieve -> generate -> validate -> save
    """
    # Setup mocks for a VALID outcome
    mock_parse.return_value = mock_valid_itinerary
    mock_validate.return_value = ViolationReport(is_valid=True)

    use_case = GenerateItineraryUseCase(**mock_dependencies)
    
    # We will intercept the state after execution
    final_state = None
    
    # We must actually capture the state. 
    # Let's monkeypatch the graph run to capture the state
    original_run = use_case._graph.run
    
    async def wrapped_run(state: CartenaState):
        nonlocal final_state
        final_state = state
        async for event in original_run(state):
            yield event
            
    use_case._graph.run = wrapped_run
    
    # Execute
    async for _ in use_case.execute(mock_trip_request):
        pass

    assert final_state is not None
    assert final_state.visited_nodes == ["retrieve", "generate", "validate", "save"]
    assert final_state.validation_report.is_valid is True
    assert final_state.repair_count == 0


@pytest.mark.asyncio
@patch("backend.application.use_cases.state_graph.nodes.itinerary_parser.parse")
@patch("backend.application.use_cases.state_graph.nodes.ItineraryValidator.validate")
async def test_graph_repair_path(
    mock_validate, mock_parse, mock_dependencies, mock_trip_request, mock_valid_itinerary
):
    """
    Scenario: The LLM fails validation on pass 1, but succeeds on pass 2 (repair).
    Expected Path: retrieve -> generate -> validate -> generate -> validate -> save
    """
    mock_parse.return_value = mock_valid_itinerary
    
    # Pass 1: Invalid. Pass 2: Valid
    mock_validate.side_effect = [
        ViolationReport(is_valid=False, hard_violations=["Budget exceeded"]),
        ViolationReport(is_valid=True)
    ]

    use_case = GenerateItineraryUseCase(**mock_dependencies)
    
    final_state = None
    original_run = use_case._graph.run
    async def wrapped_run(state: CartenaState):
        nonlocal final_state
        final_state = state
        async for event in original_run(state):
            yield event
    use_case._graph.run = wrapped_run
    
    async for _ in use_case.execute(mock_trip_request):
        pass

    assert final_state is not None
    assert final_state.visited_nodes == [
        "retrieve", "generate", "validate", "generate", "validate", "save"
    ]
    assert final_state.repair_count == 1
    assert final_state.validation_report.is_valid is True


@pytest.mark.asyncio
@patch("backend.application.use_cases.state_graph.nodes.itinerary_parser.parse")
@patch("backend.application.use_cases.state_graph.nodes.ItineraryValidator.validate")
async def test_graph_max_repairs_exhausted(
    mock_validate, mock_parse, mock_dependencies, mock_trip_request, mock_valid_itinerary
):
    """
    Scenario: The LLM continually fails validation and exhausts max_repairs.
    Expected Path: retrieve -> generate -> validate (fail) -> generate -> validate (fail) 
                   -> generate -> validate (fail) -> save (with warnings)
    Note: max_repairs=2 means 1 initial try + 2 repairs = 3 generate/validate cycles.
    """
    mock_parse.return_value = mock_valid_itinerary
    
    # Always invalid
    mock_validate.return_value = ViolationReport(
        is_valid=False, 
        hard_violations=["Stubborn constraint violation"]
    )

    use_case = GenerateItineraryUseCase(**mock_dependencies)
    
    final_state = None
    original_run = use_case._graph.run
    async def wrapped_run(state: CartenaState):
        nonlocal final_state
        final_state = state
        async for event in original_run(state):
            yield event
    use_case._graph.run = wrapped_run
    
    async for _ in use_case.execute(mock_trip_request):
        pass

    assert final_state is not None
    assert final_state.visited_nodes == [
        "retrieve", 
        "generate", "validate",  # initial
        "generate", "validate",  # repair 1
        "generate", "validate",  # repair 2
        "save"                   # exhausted fallback
    ]
    assert final_state.repair_count == 2
    
    # Crucial assertion: the failure was NOT masked as a success.
    # The report is still invalid, and violations are preserved in the state.
    assert final_state.validation_report.is_valid is False
    assert "Stubborn constraint violation" in final_state.validation_report.hard_violations
    
    # Ensure it was actually saved despite the fallback
    mock_dependencies["itinerary_repo"].save.assert_called_once()
