"""
Port for Checkpoint Repository
"""

from typing import Protocol
from backend.application.use_cases.state_graph.state import CartenaState

class ICheckpointRepository(Protocol):
    async def save(self, workflow_id: str, state: CartenaState) -> None:
        """Saves a checkpoint of the current workflow state."""
        ...

    async def get(self, workflow_id: str) -> CartenaState | None:
        """Retrieves a checkpointed workflow state by ID."""
        ...
