"""
Use case for resolving human-in-the-loop workflows.
"""

from typing import AsyncIterator
from backend.application.use_cases.state_graph.core import StateGraphEngine
from backend.application.use_cases.state_graph.state import WorkflowState


class HumanReviewResolutionUseCase:
    """
    Resumes a workflow that was suspended for human review.
    Applies the human's resolution to the state, saves it, and resumes the graph.
    """

    def __init__(
        self,
        engine: StateGraphEngine,
        checkpoint_repo,
    ) -> None:
        self._engine = engine
        self._checkpoint_repo = checkpoint_repo

    async def execute(self, workflow_id: str, resolution_id: str) -> AsyncIterator[dict]:
        """
        Fetches the suspended state, applies the resolution, and resumes execution.
        """
        state: WorkflowState | None = await self._checkpoint_repo.get(workflow_id)
        if not state:
            yield {"type": "error", "message": f"Workflow {workflow_id} not found."}
            return

        if state.status != "WAITING_HUMAN":
            yield {"type": "error", "message": f"Workflow {workflow_id} is not waiting for human review. Status: {state.status}"}
            return

        # 1. Apply human resolution
        state.apply_human_resolution(resolution_id)

        # 2. Reset status so it can run again
        state.status = "running"
        
        # 3. Save checkpoint before resuming
        await self._checkpoint_repo.save(workflow_id, state)

        # 4. Resume the engine
        async for event in self._engine.run(workflow_id=workflow_id):
            yield event
