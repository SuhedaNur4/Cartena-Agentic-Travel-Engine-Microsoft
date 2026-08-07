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
        destinations=("Tokyo",),
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
    from backend.application.services.knowledge_service import KnowledgeService
    from backend.infrastructure.knowledge_base.resolver import DestinationResolver
    mock_ks = AsyncMock(spec=KnowledgeService)
    mock_ks.get_context_for_destination.return_value = []
    
    checkpoint_repo = AsyncMock()
    checkpoint_repo.get.return_value = None
    
    llm_client = AsyncMock()
    async def fake_stream(*args, **kwargs):
        yield "chunk"
    llm_client.stream = fake_stream
    
    return {
        "llm_client": llm_client,
        "embedding_client": AsyncMock(),
        "vector_store": AsyncMock(),
        "itinerary_repo": AsyncMock(),
        "online_adapters": [],
        "checkpoint_repo": checkpoint_repo,
        "trace_repo": AsyncMock(),
        "knowledge_service": mock_ks,
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
    
    # Execute
    async for _ in use_case.execute(mock_trip_request, workflow_id="test_wf"):
        pass

    save_calls = mock_dependencies["checkpoint_repo"].save.call_args_list
    assert len(save_calls) > 0, "State was never saved to checkpoint"
    final_state = save_calls[-1][0][1]

    assert final_state is not None
    assert final_state.visited_nodes == ["planner", "constraint_analysis", "retriever", "generator", "parser", "validator", "finalize"]
    assert final_state.violation_report.is_valid is True
    assert final_state.repair_attempts == 0


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
    
    async for _ in use_case.execute(mock_trip_request, workflow_id='test_wf'):

    
        pass

    
    

    
    save_calls = mock_dependencies['checkpoint_repo'].save.call_args_list

    
    assert len(save_calls) > 0, 'State was never saved to checkpoint'

    
    final_state = save_calls[-1][0][1]

    assert final_state is not None
    assert final_state.visited_nodes == [
        "planner", "constraint_analysis", "retriever", "generator", "parser", "validator",
        "repair", "generator", "parser", "validator",
        "finalize"
    ]
    assert final_state.repair_attempts == 1
    assert final_state.violation_report.is_valid is True


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
    
    events = []
    async for event in use_case.execute(mock_trip_request, workflow_id='test_wf'):
        events.append(event)
    
    error_events = [e for e in events if e["type"] == "error"]
    assert len(error_events) > 0
    assert "3 repair attempt" in error_events[0]["message"]
