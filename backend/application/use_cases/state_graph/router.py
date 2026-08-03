"""
State Graph: Routing Logic

The Router determines which node executes next based on the current
WorkflowState.  It contains no business logic — only structural decisions
about workflow flow control.

Routing table:
    after_parser     → "validator"  (always — move to validation)
    after_validator  → "finalize"   (status == "success")
                     → "repair"     (status == "repair", attempts < MAX)
                     → "failed"     (repair attempts exhausted)
"""

from __future__ import annotations

from backend.application.use_cases.state_graph.state import MAX_REPAIR_ATTEMPTS, WorkflowState


def route_after_parser(state: WorkflowState) -> str:
    """
    After the Parser node:
      - If parsing failed (status == "failed"), terminate immediately.
      - Otherwise, always proceed to the Validator.
    """
    if state.status == "failed":
        return "failed"
    return "validator"


def route_after_validator(state: WorkflowState) -> str:
    """
    After the Validator node:
      - "success"  → Finalize (persist + emit done)
      - "repair"   → Repair Node (if repair budget remains)
      - exhausted  → "failed" (emit error, stop)
    """
    if state.status == "success":
        return "finalize"

    if state.status == "repair":
        if state.repair_attempts < MAX_REPAIR_ATTEMPTS:
            return "repair"
        # Repair budget exhausted; fail gracefully.
        return "failed"

    # Catch-all for unexpected states.
    return "failed"
