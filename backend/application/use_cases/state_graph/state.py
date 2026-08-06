"""
State Graph: WorkflowState / CartenaState

Defines the shared mutable state object that is threaded through every node
in the Cartena agentic pipeline.  All nodes read from and write back to this
single dataclass — no node stores private state between invocations.

Design note:
    WorkflowState intentionally contains observability fields (trace_events,
    visited_nodes, current_node) so that the Observability layer can be wired
    in without any changes to the node implementations themselves.

    CartenaState is provided as a backward-compatible alias used by the
    checkpoint and trace repository layers.
"""

from __future__ import annotations

import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from backend.domain.models.trip_request import BudgetLevel

if TYPE_CHECKING:
    from backend.domain.models.itinerary import Itinerary
    from backend.domain.models.trip_request import TripRequest
    from backend.domain.services.validator import ViolationReport
    from backend.domain.models.resolution import ResolutionOption

logger = logging.getLogger(__name__)

MAX_REPAIR_ATTEMPTS: int = 3


@dataclass
class TraceEvent:
    """Lightweight event record emitted by each node as it executes."""

    node: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowState:
    """
    Central state object shared across all pipeline nodes.

    Lifecycle:
        1. Created by GenerateItineraryUseCase before graph execution.
        2. Passed into StateGraphEngine.run(), which threads it through nodes.
        3. Returned to the UseCase after graph completion for result extraction.
    """

    # ── Input ──────────────────────────────────────────────────────────────────
    request: "TripRequest | None" = None

    # ── Context gathered during pipeline ──────────────────────────────────────
    online_context: list[str] = field(default_factory=list)
    rag_chunks: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    kb_miss: bool = False

    # ── LLM generation ─────────────────────────────────────────────────────────
    system_prompt: str = ""
    user_prompt: str = ""
    generated_text: str = ""
    raw_response: str = ""  # Alias kept for checkpoint deserialization

    # ── Parsed & validated output ──────────────────────────────────────────────
    itinerary: "Itinerary | None" = None          # Current working itinerary
    original_itinerary: "Itinerary | None" = None  # Preserved for partial repair
    parsed_itinerary: "Itinerary | None" = None    # After parser node
    merged_itinerary: "Itinerary | None" = None    # After partial-repair merge
    violation_report: "ViolationReport | None" = None
    validation_report: "ViolationReport | None" = None  # Alias for checkpoint compat
    resolutions: list[Any] = field(default_factory=list)  # HITL resolution options

    # ── Repair loop control ────────────────────────────────────────────────────
    repair_attempts: int = 0
    repair_count: int = 0          # Alias kept for checkpoint deserialization
    max_repairs: int = MAX_REPAIR_ATTEMPTS
    repair_prompt: str = ""

    # ── Workflow control (HITL / resume support) ───────────────────────────────
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_status: str = "RUNNING"   # RUNNING | SUCCESS | FAILED | WAITING_FOR_HUMAN
    planning_mode: str = "full"        # full | partial | regenerate
    resume_from_node: str = ""         # Node to resume from on checkpoint restore
    user_decision: str = ""            # Human-in-the-loop decision string
    target_days: list[int] = field(default_factory=list)  # Days targeted for partial replan
    user_replan_reason: str = ""       # Reason provided by user for partial replan
    itinerary_id: str = ""             # ID assigned after persistence

    # ── Final status ───────────────────────────────────────────────────────────
    # "running" | "success" | "failed" | "repair"
    status: str = "running"
    error_message: str = ""

    # ── Observability ──────────────────────────────────────────────────────────
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    current_node: str = ""
    visited_nodes: list[str] = field(default_factory=list)
    trace_events: list[TraceEvent] = field(default_factory=list)

    # ── SSE event stream (yielded to FastAPI) ──────────────────────────────────
    sse_events: list[dict] = field(default_factory=list)

    def enter_node(self, name: str) -> None:
        """Called by each node on entry to keep observability fields up-to-date."""
        self.current_node = name
        self.visited_nodes.append(name)
        self.workflow_status = "RUNNING"

    def emit(self, event: dict) -> None:
        """Queue an SSE event to be streamed to the client."""
        self.sse_events.append(event)

    def apply_human_resolution(self, resolution_id: str) -> None:
        """
        Applies the human's chosen resolution to the workflow state.
        This mutates the underlying domain properties (like Budget) so that
        the next node (e.g. constraint_analysis) correctly rebuilds the world context.
        """
        import dataclasses
        if resolution_id == "increase_budget" and self.request:
            # We explicitly update the domain request parameter
            self.request = dataclasses.replace(self.request, budget=BudgetLevel.HIGH)
        elif resolution_id == "relax_constraints" and self.request:
            new_notes = f"{self.request.notes} (User override: relax constraints and allow cheaper/flexible alternatives.)"
            self.request = dataclasses.replace(self.request, notes=new_notes)
        elif resolution_id == "retry":
            pass # Just retry with same constraints
        else:
            logger.warning("Unknown human resolution ID: %s", resolution_id)

    def record_trace(self, event: TraceEvent) -> None:
        """Append a trace event for the Observability layer."""
        self.trace_events.append(event)


# ── Backward-compatible alias ──────────────────────────────────────────────────
# The checkpoint repository and port layer were written using CartenaState.
# This alias ensures zero import breakage without renaming the class.
CartenaState = WorkflowState
