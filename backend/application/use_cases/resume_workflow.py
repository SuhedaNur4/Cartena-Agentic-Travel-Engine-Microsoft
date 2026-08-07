"""
Use Case: ResumeWorkflow

Restores a paused workflow from a checkpoint and resumes generation
from the last saved node.  Used by the HITL (Human-In-The-Loop) flow
when a user approves a resolution option.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from backend.application.ports.checkpoint_repo_port import ICheckpointRepository

logger = logging.getLogger(__name__)


class ResumeWorkflowUseCase:
    """
    Loads a persisted CartenaState from the checkpoint repository and
    hands it back to the GenerateItineraryUseCase to continue execution
    from the resume_from_node field.
    """

    def __init__(
        self,
        checkpoint_repo: ICheckpointRepository,
        generate_itinerary_use_case: object,  # GenerateItineraryUseCase (avoid circular import)
    ) -> None:
        self._checkpoint_repo = checkpoint_repo
        self._generate_uc = generate_itinerary_use_case

    async def execute(
        self,
        workflow_id: str,
        user_decision: str = "",
    ) -> AsyncIterator[dict]:
        async for event in self._run(workflow_id, user_decision):
            yield event

    async def _run(
        self,
        workflow_id: str,
        user_decision: str,
    ) -> AsyncIterator[dict]:
        try:
            state = await self._checkpoint_repo.get(workflow_id)
            if not state:
                yield {
                    "type": "error",
                    "message": f"No checkpoint found for workflow '{workflow_id}'.",
                }
                return

            if state.workflow_status == "WAITING_HUMAN" and user_decision:
                resolutions = state.violation_report.resolutions if state.violation_report else []
                action = next((r.action for r in resolutions if r.id == user_decision), None)
                if not action:
                    yield {"type": "error", "message": f"Invalid resolution ID: {user_decision}"}
                    return
                if action.type == "update_budget":
                    from backend.domain.models.trip_request import BudgetLevel
                    import dataclasses
                    state.request = dataclasses.replace(state.request, budget=BudgetLevel(action.value))
                elif action.type == "append_reason":
                    state.user_replan_reason = action.value

            state.user_decision = user_decision
            state.workflow_status = "RUNNING"

            yield {"type": "stage", "name": "Resuming workflow"}

            await self._checkpoint_repo.save(workflow_id, state)
            
            # Delegate back to the engine via the generate use case
            async for event in self._generate_uc._engine.run(
                workflow_id=workflow_id
            ):
                yield event

        except Exception as exc:  # noqa: BLE001
            logger.exception("ResumeWorkflowUseCase error: %s", exc)
            yield {"type": "error", "message": str(exc)}
