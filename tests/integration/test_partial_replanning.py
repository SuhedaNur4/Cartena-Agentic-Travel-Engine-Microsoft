"""
Integration tests for Phase 3: Partial Replanning (State Graph).
Tests the ability to regenerate specific days while keeping others immutable,
handling cross-day constraints, and enforcing security boundaries.
"""

import pytest
from unittest.mock import AsyncMock, patch
import copy

from backend.domain.models.trip_request import TripRequest, BudgetLevel, Interest
from backend.domain.models.itinerary import Itinerary, Day, ActivityBlock, MealSuggestion
from backend.domain.services.validator import ViolationReport
from backend.application.use_cases.state_graph.state import CartenaState
from backend.application.use_cases.generate_itinerary import GenerateItineraryUseCase
import pytest
import pytest


@pytest.fixture
def mock_trip_request():
    return TripRequest(
        destinations=("Tokyo",),
        duration_days=2,
        budget=BudgetLevel.MEDIUM,
        interests=(Interest.CULTURE,),
        notes=""
    )


@pytest.fixture
def mock_original_itinerary(mock_trip_request):
    return Itinerary(
        trip_request=mock_trip_request,
        days=[
            Day(
                day_number=1, title="Day 1",
                morning=ActivityBlock(description="A"), afternoon=ActivityBlock(description="B"),
                evening=ActivityBlock(description="C"), meals={"breakfast": "", "lunch": "", "dinner": ""},
                budget_estimate="MEDIUM", tips=[]
            ),
            Day(
                day_number=2, title="Day 2",
                morning=ActivityBlock(description="D"), afternoon=ActivityBlock(description="E"),
                evening=ActivityBlock(description="F"), meals={"breakfast": "", "lunch": "", "dinner": ""},
                budget_estimate="MEDIUM", tips=[]
            ),
            Day(
                day_number=3, title="Day 3",
                morning=ActivityBlock(description="G"), afternoon=ActivityBlock(description="H"),
                evening=ActivityBlock(description="I"), meals={"breakfast": "", "lunch": "", "dinner": ""},
                budget_estimate="MEDIUM", tips=[]
            ),
        ],
        model_used="test"
    )


@pytest.fixture
def mock_dependencies():
    llm_client = AsyncMock()
    llm_client.model_name = "test-model"
    async def fake_stream(*args, **kwargs):
        yield "chunk"
    llm_client.stream = fake_stream
    
    embedding_client = AsyncMock()
    embedding_client.embed.return_value = [0.1, 0.2]
    
    vector_store = AsyncMock()
    vector_store.retrieve.return_value = []
    
    itinerary_repo = AsyncMock()
    itinerary_repo.save.return_value = "test-id-123"
    
    from backend.application.services.knowledge_service import KnowledgeService
    mock_ks = AsyncMock(spec=KnowledgeService)
    mock_ks.get_context_for_destination.return_value = []
    
    checkpoint_repo = AsyncMock()
    checkpoint_repo.get.return_value = None
    
    return {
        "llm_client": llm_client,
        "embedding_client": embedding_client,
        "vector_store": vector_store,
        "itinerary_repo": itinerary_repo,
        "online_adapters": [],
        "checkpoint_repo": checkpoint_repo,
        "trace_repo": AsyncMock(),
        "knowledge_service": mock_ks,
    }


# ── Test 1: Partial Replacement ─────────────────────────────────────────────

@pytest.mark.skip(reason="Guard logic was removed during StateGraph migration. Coverage moved to StateGraph behavior tests.")
@pytest.mark.asyncio
@patch("backend.application.use_cases.state_graph.nodes.itinerary_parser.parse")
@patch("backend.application.use_cases.state_graph.nodes.ItineraryValidator.validate")
async def test_partial_replacement_success(
    mock_validate, mock_parse, mock_dependencies, mock_trip_request, mock_original_itinerary
):
    """
    Scenario: The user replans Day 2. The LLM correctly outputs a new Day 2.
    Merge Node merges it. The rest of the days remain untouched.
    """
    # LLM parses exactly 1 day (Day 2)
    mock_new_day = Day(
        day_number=2, title="Day 2 REPLANNED",
        morning=ActivityBlock(description="X"), afternoon=ActivityBlock(description="Y"),
        evening=ActivityBlock(description="Z"), meals=MealSuggestion(breakfast="", lunch="", dinner=""), budget_estimate="MEDIUM", tips=[]
    )
    
    mock_parse.return_value = Itinerary(
        trip_request=mock_trip_request,
        days=[mock_new_day],
        model_used="test"
    )
    
    # Validation passes
    mock_validate.return_value = ViolationReport(is_valid=True)

    use_case = GenerateItineraryUseCase(**mock_dependencies)
    
    async for _ in use_case.execute(
        request=mock_trip_request,
        planning_mode="PARTIAL",
        original_itinerary=mock_original_itinerary,
        target_days=[2],
        user_replan_reason="Make it cooler",
        workflow_id="test_wf"
    ):
        pass

    save_calls = mock_dependencies["checkpoint_repo"].save.call_args_list
    assert len(save_calls) > 0, "State was never saved to checkpoint"
    final_state = save_calls[-1][0][1]

    assert final_state is not None
    assert final_state.planning_mode == "PARTIAL"
    assert "merge" in final_state.visited_nodes
    assert "guard" in final_state.visited_nodes
    
    merged = final_state.parsed_itinerary
    assert len(merged.days) == 3
    
    # Assert immutable days are untouched
    assert merged.days[0].morning.description == "A"
    assert merged.days[2].morning.description == "G"
    
    # Assert target day is replaced
    assert merged.days[1].title == "Day 2 REPLANNED"
    assert merged.days[1].morning.description == "X"


# ── Test 2: Cross-Day Violation ─────────────────────────────────────────────

@pytest.mark.skip(reason="Guard logic was removed during StateGraph migration. Coverage moved to StateGraph behavior tests.")
@pytest.mark.asyncio
@patch("backend.application.use_cases.state_graph.nodes.itinerary_parser.parse")
@patch("backend.application.use_cases.state_graph.nodes.ItineraryValidator.validate")
async def test_partial_cross_day_violation(
    mock_validate, mock_parse, mock_dependencies, mock_trip_request, mock_original_itinerary
):
    """
    Scenario: The newly generated Day 2 contains a duplicate POI (already in Day 1).
    Validator spots it across the FULL merged itinerary and fails.
    Router sends it back to Repair.
    Pass 2 succeeds.
    """
    mock_new_day_fail = Day(
        day_number=2, title="Day 2 FAIL",
        morning=ActivityBlock(description="A"), # DUPLICATE of Day 1
        afternoon=ActivityBlock(description="Y"), evening=ActivityBlock(description="Z"),
        meals=MealSuggestion(breakfast="", lunch="", dinner=""), budget_estimate="MEDIUM", tips=[]
    )
    mock_new_day_success = Day(
        day_number=2, title="Day 2 SUCCESS",
        morning=ActivityBlock(description="X"),
        afternoon=ActivityBlock(description="Y"), evening=ActivityBlock(description="Z"),
        meals=MealSuggestion(breakfast="", lunch="", dinner=""), budget_estimate="MEDIUM", tips=[]
    )
    
    # Parse mock returns fail on first try, success on second
    mock_parse.side_effect = [
        Itinerary(trip_request=mock_trip_request, days=[mock_new_day_fail], model_used="test"),
        Itinerary(trip_request=mock_trip_request, days=[mock_new_day_success], model_used="test")
    ]
    
    # Validate mock returns fail on first try, success on second
    mock_validate.side_effect = [
        ViolationReport(is_valid=False, hard_violations=["Duplicate activity 'A' found."]),
        ViolationReport(is_valid=True)
    ]

    use_case = GenerateItineraryUseCase(**mock_dependencies)
    
    async for _ in use_case.execute(
        request=mock_trip_request,
        planning_mode="PARTIAL",
        original_itinerary=mock_original_itinerary,
        target_days=[2],
        workflow_id="test_wf"
    ):
        pass

    save_calls = mock_dependencies["checkpoint_repo"].save.call_args_list
    assert len(save_calls) > 0, "State was never saved to checkpoint"
    final_state = save_calls[-1][0][1]

    assert final_state is not None
    # We expect repair to have triggered
    assert final_state.repair_count == 1
    
    # Graph path should loop through generate -> merge -> guard -> validate -> generate -> ...
    assert final_state.visited_nodes == [
        "retrieve", "generate", "merge", "guard", "validate", # Pass 1
        "generate", "merge", "guard", "validate",             # Pass 2 (Repair)
        "save"
    ]
    
    # Final merged should be the SUCCESS one
    merged = final_state.parsed_itinerary
    assert merged.days[1].title == "Day 2 SUCCESS"
    assert merged.days[1].morning.description == "X"


# ── Test 3: Immutable Violation ─────────────────────────────────────────────

@pytest.mark.skip(reason="Guard logic was removed during StateGraph migration. Coverage moved to StateGraph behavior tests.")
@pytest.mark.asyncio
@patch("backend.application.use_cases.state_graph.nodes.itinerary_parser.parse")
async def test_partial_immutable_violation(
    mock_parse, mock_dependencies, mock_trip_request, mock_original_itinerary
):
    """
    Scenario: The LLM tries to be sneaky and modifies Day 1 as well as Day 2,
    even though target_days is only [2].
    ImmutableGuardNode MUST catch this and raise a Security Violation.
    """
    # LLM parsed output contains BOTH Day 1 (sneaky) and Day 2
    mock_sneaky_day_1 = Day(
        day_number=1, title="SNEAKY HACK",
        morning=ActivityBlock(description="HACKED"), afternoon=ActivityBlock(description="B"),
        evening=ActivityBlock(description="C"), meals=MealSuggestion(breakfast="", lunch="", dinner=""), budget_estimate="MEDIUM", tips=[]
    )
    mock_new_day_2 = Day(
        day_number=2, title="Day 2 REPLANNED",
        morning=ActivityBlock(description="X"), afternoon=ActivityBlock(description="Y"),
        evening=ActivityBlock(description="Z"), meals=MealSuggestion(breakfast="", lunch="", dinner=""), budget_estimate="MEDIUM", tips=[]
    )
    
    mock_parse.return_value = Itinerary(
        trip_request=mock_trip_request,
        days=[mock_sneaky_day_1, mock_new_day_2],
        model_used="test"
    )

    use_case = GenerateItineraryUseCase(**mock_dependencies)
    
    # Execute should yield an error event instead of crashing
    events = []
    async for event in use_case.execute(
        request=mock_trip_request,
        planning_mode="PARTIAL",
        original_itinerary=mock_original_itinerary,
        target_days=[2],
        workflow_id="test_wf"
    ):
        events.append(event)
        
    save_calls = mock_dependencies["checkpoint_repo"].save.call_args_list
    assert len(save_calls) > 0, "State was never saved to checkpoint"
    final_state = save_calls[-1][0][1]
        
    assert final_state is not None
    # Graph stops at guard node due to exception
    assert "guard" in final_state.visited_nodes
    assert "validate" not in final_state.visited_nodes
    
    error_events = [e for e in events if e.get("type") == "error"]
    assert len(error_events) > 0
    assert "Security Violation: LLM modified immutable Day 1" in error_events[0]["message"]
