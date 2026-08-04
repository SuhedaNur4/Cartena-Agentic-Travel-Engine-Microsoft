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

    async def run(self, request: TripRequest) -> AsyncIterator[dict]:
        """
        Execute the full agentic workflow and yield SSE events.

        Each node may append events to state.sse_events; this method drains
        the queue after every node call so the client sees real-time progress.
        """
        state = WorkflowState(request=request)

        async def drain() -> AsyncIterator[dict]:
            """Flush all pending SSE events from state to the caller."""
            while state.sse_events:
                yield state.sse_events.pop(0)

        try:
            # ── Phase 1: Context Gathering ─────────────────────────────────────
            state = await planner_node(state, self._online_adapters)
            async for event in drain():
                yield event

            state = await constraint_node(state)
            async for event in drain():
                yield event

            state = await retriever_node(state, self._embeddings, self._vector_store)
            async for event in drain():
                yield event

            # ── Phase 2: Generation + Validation (with Repair Loop) ────────────
            while True:
                # Generator always runs at the start of each loop iteration.
                state = await generator_node(state, self._llm)
                async for event in drain():
                    yield event

                # Parse the raw LLM output into a typed Itinerary.
                state = await parser_node(state, self._llm)
                async for event in drain():
                    yield event

                next_after_parser = route_after_parser(state)
                if next_after_parser == "failed":
                    # Parser emitted an error event; nothing left to do.
                    return

                # Validate the parsed Itinerary against deterministic rules.
                state = await validator_node(state)
                async for event in drain():
                    yield event

                next_after_validator = route_after_validator(state)

                if next_after_validator == "finalize":
                    # Validation passed — persist and emit done.
                    state = await finalize_node(state, self._repo)
                    async for event in drain():
                        yield event
                    return

                if next_after_validator == "repair":
                    # Build repair prompt; loop back to Generator.
                    state = await repair_node(state)
                    async for event in drain():
                        yield event
                    # Continue the while loop → next iteration hits generator_node.
                    continue

                # next_after_validator == "failed": repair budget exhausted.
                logger.error(
                    "Repair loop exhausted after %d attempts for '%s'.",
                    state.repair_attempts,
                    request.destination,
                )
                yield {
                    "type": "error",
                    "message": (
                        f"Could not produce a valid itinerary for "
                        f"'{request.destination}' after "
                        f"{state.repair_attempts} repair attempt(s). "
                        f"Please try again."
                    ),
                }
                return

        except Exception as exc:  # noqa: BLE001
            logger.exception("Unhandled exception in StateGraphEngine: %s", exc)
            yield {"type": "error", "message": str(exc)}
