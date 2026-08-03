"""
State Graph: WorkflowState

Defines the shared mutable state object that is threaded through every node
in the Cartena agentic pipeline.  All nodes read from and write back to this
single dataclass — no node stores private state between invocations.

Design note:
    WorkflowState intentionally contains observability fields (trace_events,
    visited_nodes, current_node) so that the Observability layer can be wired
    in without any changes to the node implementations themselves.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.domain.models.itinerary import Itinerary
    from backend.domain.models.trip_request import TripRequest
    from backend.domain.services.validator import ViolationReport

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

    # ── Parsed & validated output ──────────────────────────────────────────────
    itinerary: "Itinerary | None" = None
    violation_report: "ViolationReport | None" = None

    # ── Repair loop control ────────────────────────────────────────────────────
    repair_attempts: int = 0
    repair_prompt: str = ""

    # ── Final status ───────────────────────────────────────────────────────────
    # "running" | "success" | "failed" | "repair"
    status: str = "running"
    error_message: str = ""

    # ── Observability (consumed by future WorkflowTrace layer) ─────────────────
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    current_node: str = ""
    visited_nodes: list[str] = field(default_factory=list)
    trace_events: list[TraceEvent] = field(default_factory=list)

    # ── SSE event stream (yielded to FastAPI) ──────────────────────────────────
    # Nodes append dicts here; the UseCase drains them incrementally.
    sse_events: list[dict] = field(default_factory=list)

    def enter_node(self, name: str) -> None:
        """Called by each node on entry to keep observability fields up-to-date."""
        self.current_node = name
        self.visited_nodes.append(name)

    def emit(self, event: dict) -> None:
        """Append an SSE-ready event dict for the FastAPI layer to stream."""
        self.sse_events.append(event)

    def record_trace(self, event: TraceEvent) -> None:
        """Append a trace event for the Observability layer."""
        self.trace_events.append(event)
