"""
Integration tests for Human-in-the-Loop (HITL) scenarios.
"""
import asyncio
import pytest

from backend.application.use_cases.state_graph.core import StateGraphEngine
from backend.application.use_cases.human_review_resolution import HumanReviewResolutionUseCase
from backend.domain.models.trip_request import TripRequest, BudgetLevel, Interest
from backend.application.ports.checkpoint_repo_port import ICheckpointRepository
from backend.application.ports.itinerary_repo_port import IItineraryRepository
from tests.fakes.vector_store import FakeVectorStore
from tests.fakes.embedding import FakeEmbeddingClient

# A fake LLM client that intentionally fails the budget check by proposing a luxury restaurant.
class HITLFakeLLMClient:
    def __init__(self):
        self.model_name = "hitl-fake-gpt-4o"
        self.call_count = 0

    async def stream(self, system_prompt: str, user_prompt: str, expected_days: int = 1):
        self.call_count += 1
        
        # On the first call, produce a luxury response that violates a BUDGET constraint.
        if self.call_count == 1:
            yield '{\n'
            yield '  "days": [\n'
            yield '    {\n'
            yield '      "day_number": 1,\n'
            yield '      "title": "A Day in Tokyo",\n'
            yield '      "morning": {\n'
            yield '        "description": "Visit Senso-ji",\n'
            yield '        "cost_estimate": "Free"\n'
            yield '      },\n'
            yield '      "afternoon": {\n'
            yield '        "description": "Walk around Asakusa",\n'
            yield '        "cost_estimate": "Free"\n'
            yield '      },\n'
            yield '      "evening": {\n'
            yield '        "description": "Dinner at a 3-star michelin luxury fine dining restaurant",\n'
            yield '        "cost_estimate": "35,000 JPY"\n'
            yield '      },\n'
            yield '      "meals": {\n'
            yield '        "breakfast": "Street food",\n'
            yield '        "lunch": "Ramen",\n'
            yield '        "dinner": "Luxury Sushi"\n'
            yield '      },\n'
            yield '      "tips": ["Book in advance"]\n'
            yield '    }\n'
            yield '  ]\n'
            yield '}'
        else:
            # On the second call (after HITL changes budget to HIGH), produce a normal response 
            # Note: The same text is fine because now the constraint map allows luxury!
            yield '{\n'
            yield '  "days": [\n'
            yield '    {\n'
            yield '      "day_number": 1,\n'
            yield '      "title": "A Day in Tokyo",\n'
            yield '      "morning": {\n'
            yield '        "description": "Visit Senso-ji",\n'
            yield '        "cost_estimate": "Free"\n'
            yield '      },\n'
            yield '      "afternoon": {\n'
            yield '        "description": "Walk around Asakusa",\n'
            yield '        "cost_estimate": "Free"\n'
            yield '      },\n'
            yield '      "evening": {\n'
            yield '        "description": "Dinner at a 3-star michelin luxury fine dining restaurant",\n'
            yield '        "cost_estimate": "35,000 JPY"\n'
            yield '      },\n'
            yield '      "meals": {\n'
            yield '        "breakfast": "Street food",\n'
            yield '        "lunch": "Ramen",\n'
            yield '        "dinner": "Luxury Sushi"\n'
            yield '      },\n'
            yield '      "tips": ["Book in advance"]\n'
            yield '    }\n'
            yield '  ]\n'
            yield '}'


class InMemoryCheckpointRepo(ICheckpointRepository):
    def __init__(self):
        self._store = {}
    
    async def save(self, workflow_id: str, state) -> None:
        self._store[workflow_id] = state
        
    async def get(self, workflow_id: str):
        return self._store.get(workflow_id)


class InMemoryItineraryRepo(IItineraryRepository):
    def __init__(self):
        self._store = {}
        self._counter = 1
    
    async def save(self, itinerary) -> str:
        new_id = f"itin-{self._counter}"
        self._counter += 1
        itinerary.id = new_id
        self._store[new_id] = itinerary
        return new_id
        
    async def get(self, id: str):
        return self._store.get(id)
        
    async def update(self, itinerary) -> None:
        if itinerary.id in self._store:
            self._store[itinerary.id] = itinerary
            
    async def list_all(self, dest=None): return []
    async def delete(self, id): pass
    async def toggle_favorite(self, id, fav): pass
    async def get_destinations(self): return []
    async def update_day(self, id, d): pass


@pytest.mark.asyncio
async def test_human_in_the_loop_budget_violation():
    """
    Proves the 4 phases of HITL:
    1. HITL Trigger (LLM violates budget -> Validator marks CRITICAL -> Event emitted).
    2. Checkpoint (Workflow suspends with WAITING_HUMAN).
    3. Human Decision (User updates budget to HIGH).
    4. Resume (Workflow continues and succeeds without infinite repair loop).
    """
    llm = HITLFakeLLMClient()
    checkpoint_repo = InMemoryCheckpointRepo()
    itinerary_repo = InMemoryItineraryRepo()
    
    engine = StateGraphEngine(
        llm_client=llm,
        embedding_client=FakeEmbeddingClient(),
        vector_store=FakeVectorStore(),
        itinerary_repo=itinerary_repo,
        checkpoint_repo=checkpoint_repo
    )
    
    request = TripRequest(
        destination="Tokyo",
        duration_days=1,
        budget=BudgetLevel.LOW, # explicitly LOW
        interests=[Interest.CULTURE],
        notes="First time in Japan"
    )
    
    workflow_id = "test-hitl-123"
    hitl_event = None
    
    # ── CASE 1: HITL Trigger ─────────────────────────────────────────────────────────────
    print("\\n==================================================")
    print("CASE 1 & 2: HITL Trigger & Checkpoint")
    print("==================================================")
    
    async for event in engine.run(request=request, workflow_id=workflow_id):
        if event.get("type") == "human_review_required":
            hitl_event = event
    
    assert hitl_event is not None, "Expected human_review_required event to be emitted."
    assert "Critical violation detected" in hitl_event["message"]
    print(f"[PASS] Case 1 Passed: HITL triggered. Resolutions: {hitl_event['resolutions']}")
    
    # ── CASE 2: Checkpoint ───────────────────────────────────────────────────────────────
    state = await checkpoint_repo.get(workflow_id)
    assert state is not None
    assert state.status == "WAITING_HUMAN"
    assert state.resume_from_node == "constraint_analysis"
    assert state.repair_attempts == 0, "Repair loop should NOT have been triggered."
    print(f"[PASS] Case 2 Passed: Checkpoint status is WAITING_HUMAN and resume_from_node is constraint_analysis.")
    
    # ── CASE 3: Human Decision ───────────────────────────────────────────────────────────
    print("\\n==================================================")
    print("CASE 3 & 4: Human Decision & Resume")
    print("==================================================")
    
    hitl_use_case = HumanReviewResolutionUseCase(engine, checkpoint_repo)
    
    # We apply "increase_budget" resolution
    events = []
    async for event in hitl_use_case.execute(workflow_id=workflow_id, resolution_id="increase_budget"):
        events.append(event)
        
    state_after = await checkpoint_repo.get(workflow_id)
    assert state_after.request.budget == BudgetLevel.HIGH, "Budget should have been updated to HIGH."
    print("[PASS] Case 3 Passed: Human resolution applied (Budget is now HIGH).")
    
    # ── CASE 4: Resume & Success ─────────────────────────────────────────────────────────
    done_event = next((e for e in events if e.get("type") == "done"), None)
    assert done_event is not None, "Expected 'done' event after resuming workflow."
    
    # Verify the workflow succeeded
    assert state_after.status == "success"
    assert state_after.repair_attempts == 0, "Repair loop was completely bypassed via HITL."
    print("[PASS] Case 4 Passed: Workflow resumed successfully and repair loop was correctly bypassed.")

if __name__ == "__main__":
    asyncio.run(test_human_in_the_loop_budget_violation())
