"""
State Graph: Core Engine

Custom agentic orchestration engine — built without third-party frameworks.

Design principles:
    - All control flow is deterministic Python, not LLM-driven.
    - The LLM is a single node in the graph, not the orchestrator.
    - Nodes are pure async functions; the engine sequences and routes them.
    - WorkflowState is the single source of truth; nodes never communicate
      directly with each other.

Graph topology:
    START
      ↓
    planner_node
      ↓
    constraint_node
      ↓
    retriever_node
      ↓
    generator_node
      ↓
    parser_node
      ↓
    validator_node
      ├─ success  ──→ finalize_node  ──→ END
      └─ repair   ──→ repair_node
                          ↓
                    generator_node   (loop back, up to MAX_REPAIR_ATTEMPTS)
      └─ failed   ──→ END  (error event already in state.sse_events)
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from backend.application.ports.embedding_port import IEmbeddingClient
from backend.application.ports.itinerary_repo_port import IItineraryRepository
from backend.application.ports.llm_port import ILLMClient
from backend.application.ports.online_adapter_port import IOnlineAdapter
from backend.application.ports.vector_store_port import IVectorStore
from backend.application.use_cases.state_graph.nodes import (
    constraint_node,
    finalize_node,
    generator_node,
    parser_node,
    planner_node,
    repair_node,
    retriever_node,
    validator_node,
)
from backend.application.use_cases.state_graph.router import (
    route_after_parser,
    route_after_validator,
)
from backend.application.use_cases.state_graph.state import WorkflowState
from backend.domain.models.trip_request import TripRequest

logger = logging.getLogger(__name__)


class StateGraphEngine:
    """
    Custom agentic orchestration engine for Cartena's travel planning workflow.

    The engine wires together all infrastructure adapters, executes nodes in
    the defined topological order, and handles conditional routing through the
    Repair Loop.  It yields SSE-ready event dicts as an async generator so that
    FastAPI can stream them to the client with zero buffering delay.

    Usage:
        engine = StateGraphEngine(llm, embeddings, vector_store, repo)
        async for event in engine.run(trip_request):
            yield event  # SSE dict
    """

    def __init__(
        self,
        llm_client: ILLMClient,
        embedding_client: IEmbeddingClient,
        vector_store: IVectorStore,
        itinerary_repo: IItineraryRepository,
        online_adapters: list[IOnlineAdapter] | None = None,
        checkpoint_repo: Any | None = None,
        trace_repo: Any | None = None,
    ) -> None:
        self._llm = llm_client
        self._embeddings = embedding_client
        self._vector_store = vector_store
        self._repo = itinerary_repo
        self._online_adapters = online_adapters or []
        self._checkpoint_repo = checkpoint_repo
        self._trace_repo = trace_repo

    async def run(self, request: TripRequest | None = None, workflow_id: str | None = None) -> AsyncIterator[dict]:
        """
        Execute the full agentic workflow and yield SSE events.

        Each node may append events to state.sse_events; this method drains
        the queue after every node call so the client sees real-time progress.
        """
        state = None
        if workflow_id and self._checkpoint_repo:
            state = await self._checkpoint_repo.get(workflow_id)
        if not state:
            if not request:
                yield {"type": "error", "message": "TripRequest is required for new workflows."}
                return
            state = WorkflowState(request=request)
            if workflow_id:
                state.workflow_id = workflow_id

        async def drain() -> AsyncIterator[dict]:
            """Flush all pending SSE events from state to the caller."""
            while state.sse_events:
                yield state.sse_events.pop(0)

        async def save_checkpoint(next_node: str) -> None:
            """Save the current state with the node to resume from on next run."""
            if self._checkpoint_repo:
                state.resume_from_node = next_node
                await self._checkpoint_repo.save(state.workflow_id, state)

        # Record if this run was resumed (for trace metadata)
        was_resumed = bool(state.resume_from_node)
        resume_target = state.resume_from_node

        async def _save_trace(final_status: str) -> None:
            """Converts state trace events into a WorkflowTrace and persists it."""
            if not self._trace_repo:
                return
            
            from backend.domain.models.trace import WorkflowTrace, TraceEvent as DomainTraceEvent
            from datetime import datetime
            
            domain_events = []
            for ev in state.trace_events:
                domain_ev = DomainTraceEvent(
                    timestamp=ev.timestamp,
                    node=ev.node,
                    duration_ms=ev.duration_ms,
                    planning_mode=state.planning_mode,
                    repair_count=state.repair_attempts,
                    workflow_status=state.workflow_status,
                    validation_result=state.violation_report.is_valid if state.violation_report else None,
                    model_name=self._llm.model_name if hasattr(self._llm, 'model_name') else None,
                    error_type=None,
                    metadata=dict(ev.metadata)
                )
                domain_events.append(domain_ev)
                
            if domain_events and was_resumed:
                domain_events[0].metadata["resumed"] = True
                domain_events[0].metadata["resume_from_node"] = resume_target

            total_duration = sum(e.duration_ms for e in domain_events)
            trace = WorkflowTrace(
                workflow_id=state.workflow_id,
                start_time=domain_events[0].timestamp if domain_events else datetime.utcnow(),
                end_time=datetime.utcnow(),
                events=domain_events,
                final_status=final_status,
                total_duration_ms=total_duration
            )
            try:
                await self._trace_repo.save(trace)
            except Exception as e:
                logger.error("Failed to save trace: %s", e)

        # If resuming, we skip all nodes until we hit the resume target
        skip = bool(state.resume_from_node)

        try:
            # ── Phase 1: Context Gathering ─────────────────────────────────────
            if skip and state.resume_from_node == "planner": skip = False
            if not skip:
                state = await planner_node(state, self._online_adapters)
                await save_checkpoint("constraint_analysis")
                async for event in drain():
                    yield event

            if skip and state.resume_from_node == "constraint_analysis": skip = False
            if not skip:
                state = await constraint_node(state)
                await save_checkpoint("retriever")
                async for event in drain():
                    yield event

            if skip and state.resume_from_node == "retriever": skip = False
            if not skip:
                state = await retriever_node(state, self._embeddings, self._vector_store)
                await save_checkpoint("generator")
                async for event in drain():
                    yield event

            # ── Phase 2: Generation + Validation (with Repair Loop) ────────────
            while True:
                if skip and state.resume_from_node == "generator": skip = False
                if not skip:
                    state = await generator_node(state, self._llm)
                    await save_checkpoint("parser")
                    async for event in drain():
                        yield event

                if skip and state.resume_from_node == "parser": skip = False
                if not skip:
                    state = await parser_node(state, self._llm)
                    async for event in drain():
                        yield event

                    next_after_parser = route_after_parser(state)
                    if next_after_parser == "failed":
                        await _save_trace("FAILED")
                        return
                    await save_checkpoint("validator")

                if skip and state.resume_from_node == "validator": skip = False
                if not skip:
                    state = await validator_node(state)
                    async for event in drain():
                        yield event

                # We are definitely past the resume point once we hit validation logic
                skip = False

                next_after_validator = route_after_validator(state)

                if next_after_validator == "finalize":
                    await save_checkpoint("finalize")
                    state = await finalize_node(state, self._repo)
                    # Clear resume node on completion so it doesn't resume again
                    await save_checkpoint("")
                    async for event in drain():
                        yield event
                    await _save_trace("SUCCESS")
                    return

                if next_after_validator == "repair":
                    await save_checkpoint("repair")
                    state = await repair_node(state)
                    await save_checkpoint("generator")
                    async for event in drain():
                        yield event
                    continue

                logger.error(
                    "Repair loop exhausted after %d attempts for '%s'.",
                    state.repair_attempts,
                    state.request.destination if state.request else "unknown",
                )
                yield {
                    "type": "error",
                    "message": (
                        f"Could not produce a valid itinerary after "
                        f"{state.repair_attempts} repair attempt(s). Please try again."
                    ),
                }
                await _save_trace("FAILED")
                return

        except Exception as exc:  # noqa: BLE001
            logger.exception("Unhandled exception in StateGraphEngine: %s", exc)
            yield {"type": "error", "message": str(exc)}
            await _save_trace("EXCEPTION")
