"""
Integration tests for Phase 4: Human-in-the-Loop (HITL) workflow.
Tests the pause -> checkpoint -> resume -> complete lifecycle.
"""

import pytest
import os
import json
from unittest.mock import AsyncMock, patch
from typing import AsyncIterator

from backend.domain.models.trip_request import TripRequest, BudgetLevel, Interest
from backend.domain.models.itinerary import Itinerary, Day, ActivityBlock
from backend.domain.services.validator import ViolationReport
from backend.domain.models.resolution import ResolutionOption, ResolutionAction
from backend.application.use_cases.state_graph.state import CartenaState
from backend.application.use_cases.generate_itinerary import GenerateItineraryUseCase
from backend.application.use_cases.resume_workflow import ResumeWorkflowUseCase
from backend.infrastructure.repositories.json_checkpoint_repo import JSONFileCheckpointRepository


@pytest.fixture
def mock_trip_request():
    return TripRequest(
        destination="Kyoto",
        duration_days=1,
        budget=BudgetLevel.MEDIUM,
        interests=(Interest.CULTURE,),
        notes=""
    )

@pytest.fixture
def checkpoint_repo(tmp_path):
    repo_dir = tmp_path / ".checkpoints"
    return JSONFileCheckpointRepository(directory=str(repo_dir))

@pytest.fixture
def mock_dependencies(checkpoint_repo):
    llm_client = AsyncMock()
    llm_client.model_name = "test-model"
    async def mock_stream(*args, **kwargs):
        yield "fake response"
    llm_client.stream = mock_stream
    
    embedding_client = AsyncMock()
    embedding_client.embed.return_value = [0.1, 0.2]
    
    vector_store = AsyncMock()
    vector_store.retrieve.return_value = []
    
    itinerary_repo = AsyncMock()
    itinerary_repo.save.return_value = "test-id-123"
    
    return {
        "llm_client": llm_client,
        "embedding_client": embedding_client,
        "vector_store": vector_store,
        "itinerary_repo": itinerary_repo,
        "checkpoint_repo": checkpoint_repo,
        "online_adapters": []
    }


# ── Test 1: Pause and Checkpoint ─────────────────────────────────────────────

@pytest.mark.asyncio
@patch("backend.application.use_cases.state_graph.nodes.itinerary_parser.parse")
@patch("backend.application.use_cases.state_graph.nodes.ItineraryValidator.validate")
async def test_hitl_pause_and_checkpoint(
    mock_validate, mock_parse, mock_dependencies, mock_trip_request
):
    """
    Scenario: The itinerary keeps failing validation. max_repairs is reached.
    The router must output 'HITL'. The workflow must pause, emit a hitl_required
    event, and save the state to the checkpoint repository.
    """
    mock_day = Day(
        day_number=1, title="Day 1",
        morning=ActivityBlock(description="A"), afternoon=ActivityBlock(description="B"),
        evening=ActivityBlock(description="C"), meals={}, budget_estimate="MEDIUM", tips=[]
    )
    
    # Always parse successfully
    mock_parse.return_value = Itinerary(
        trip_request=mock_trip_request,
        days=[mock_day],
        model_used="test"
    )
    
    # Always fail validation (Budget error)
    violation = ViolationReport(
        is_valid=False,
        hard_violations=["Budget exceeded"],
        resolutions=[
            ResolutionOption(
                id="increase_budget",
                label="Increase budget to high",
                action=ResolutionAction(type="update_budget", value="high")
            )
        ]
    )
    mock_validate.return_value = violation

    use_case = GenerateItineraryUseCase(**mock_dependencies)
    
    events = []
    async for event in use_case.execute(request=mock_trip_request, workflow_id="wf-1"):
        events.append(event)
        
    # Find the HITL event
    hitl_event = next((e for e in events if e.get("type") == "hitl_required"), None)
    assert hitl_event is not None
    assert hitl_event["workflow_id"] == "wf-1"
    assert len(hitl_event["resolutions"]) == 1
    assert hitl_event["resolutions"][0]["id"] == "increase_budget"

    # Verify Checkpoint exists
    repo = mock_dependencies["checkpoint_repo"]
    saved_state = await repo.get("wf-1")
    assert saved_state is not None
    assert saved_state.workflow_status == "WAITING_FOR_HUMAN"
    assert saved_state.repair_count == 2  # default max_repairs is 2
    assert saved_state.resolutions[0].id == "increase_budget"


# ── Test 2 & 4: Resume Integration & Normal Recovery ─────────────────────────

@pytest.mark.asyncio
@patch("backend.application.use_cases.state_graph.nodes.itinerary_parser.parse")
@patch("backend.application.use_cases.state_graph.nodes.ItineraryValidator.validate")
async def test_hitl_resume_and_normal_recovery(
    mock_validate, mock_parse, mock_dependencies, mock_trip_request
):
    """
    Scenario: 
    1. Workflow hits HITL and pauses.
    2. We resume it with "increase_budget".
    3. The state budget is modified to 'high'.
    4. Graph resumes from 'generate'.
    5. Next generation still fails ONCE (repair loop works after resume!).
    6. Next generation passes.
    7. Workflow ENDS and saves.
    """
    mock_day = Day(
        day_number=1, title="Day 1",
        morning=ActivityBlock(description="A"), afternoon=ActivityBlock(description="B"),
        evening=ActivityBlock(description="C"), meals={}, budget_estimate="MEDIUM", tips=[]
    )
    def mock_parse_func(*args, **kwargs):
        req = kwargs.get("trip_request")
        if req is None and len(args) > 1:
            req = args[1]
        return Itinerary(trip_request=req, days=[mock_day], model_used="test")
        
    mock_parse.side_effect = mock_parse_func
    
    violation_with_resolution = ViolationReport(
        is_valid=False, hard_violations=["Budget exceeded"],
        resolutions=[ResolutionOption(id="increase_budget", label="Inc", action=ResolutionAction(type="update_budget", value="high"))]
    )
    
    # 1. Fail twice for initial run
    # 2. After resume, fail once (triggering repair)
    # 3. Then succeed.
    mock_validate.side_effect = [
        violation_with_resolution,  # Try 1
        violation_with_resolution,  # Try 2 -> repair_count = 1
        violation_with_resolution,  # Try 3 -> repair_count = 2 (HITL triggered)
        ViolationReport(is_valid=False, hard_violations=["Some other error"]), # Post-resume Try 1 -> repair_count = 1
        ViolationReport(is_valid=True) # Post-resume Try 2 -> Save
    ]

    use_case = GenerateItineraryUseCase(**mock_dependencies)
    
    # Run initially until HITL
    async for _ in use_case.execute(request=mock_trip_request, workflow_id="wf-2"):
        pass

    repo = mock_dependencies["checkpoint_repo"]
    paused_state = await repo.get("wf-2")
    assert paused_state.workflow_status == "WAITING_FOR_HUMAN"
    assert paused_state.request.budget.value == "medium"
    
    # Now Resume
    resume_use_case = ResumeWorkflowUseCase(
        checkpoint_repo=repo,
        generate_itinerary_use_case=use_case
    )
    
    resume_events = []
    async for event in resume_use_case.execute("wf-2", "increase_budget"):
        resume_events.append(event)
        
    # Check that the state was updated internally
    final_state = await repo.get("wf-2") # The state might not be saved at END unless we explicitly save it, but we can check the graph state
    # We can inspect what happened by checking if the workflow finished
    done_event = next((e for e in resume_events if e.get("type") == "done"), None)
    assert done_event is not None
        
    # Check that the itinerary repo was called with the mutated budget
    itinerary_repo = mock_dependencies["itinerary_repo"]
    assert itinerary_repo.save.called
    saved_itinerary = itinerary_repo.save.call_args[0][0]
    assert saved_itinerary.trip_request.budget.value == "high"
    

# ── Test 3: Invalid Resolution ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hitl_invalid_resolution(mock_dependencies, mock_trip_request):
    """
    Scenario: Frontend sends a resolution_id that does not exist in the state's options.
    Must yield an error and not resume the workflow.
    """
    repo = mock_dependencies["checkpoint_repo"]
    state = CartenaState(request=mock_trip_request)
    state.workflow_status = "WAITING_FOR_HUMAN"
    state.resolutions = [
        ResolutionOption(id="valid_action", label="V", action=ResolutionAction(type="retry", value=""))
    ]
    await repo.save("wf-3", state)
    
    resume_use_case = ResumeWorkflowUseCase(
        checkpoint_repo=repo,
        generate_itinerary_use_case=GenerateItineraryUseCase(**mock_dependencies)
    )
    
    events = []
    async for event in resume_use_case.execute("wf-3", "fake_action"):
        events.append(event)
        
    error_event = next((e for e in events if e.get("type") == "error"), None)
    assert error_event is not None
    assert "Invalid resolution ID" in error_event["message"]
    
    # Checkpoint must remain untouched
    unchanged_state = await repo.get("wf-3")
    assert unchanged_state.workflow_status == "WAITING_FOR_HUMAN"
