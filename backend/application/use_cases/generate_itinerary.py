"""
Use Case: GenerateItinerary

Entry point for the travel itinerary generation workflow.

This class is a thin orchestrator — its only responsibility is to:
  1. Instantiate the StateGraphEngine with the correct infrastructure adapters.
  2. Delegate execution entirely to the engine.
  3. Stream SSE-ready event dicts back to the FastAPI layer.

All business logic, routing decisions, and the Repair Loop live inside the
StateGraphEngine and its nodes. This separation keeps the Use Case ignorant of
the orchestration details, making it trivial to swap the engine implementation
(e.g., from a custom state machine to a different orchestration strategy)
without touching any external API contract.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, AsyncIterator

from backend.application.ports.embedding_port import IEmbeddingClient
from backend.application.ports.itinerary_repo_port import IItineraryRepository
from backend.application.ports.llm_port import ILLMClient
from backend.application.ports.online_adapter_port import IOnlineAdapter
from backend.application.ports.vector_store_port import IVectorStore
from backend.application.use_cases.state_graph import StateGraphEngine
from backend.domain.models.trip_request import TripRequest

if TYPE_CHECKING:
    from backend.application.ports.checkpoint_repo_port import ICheckpointRepository
    from backend.application.ports.trace_repo_port import ITraceRepository

logger = logging.getLogger(__name__)


class GenerateItineraryUseCase:
    """
    Drives the agentic travel planning workflow via StateGraphEngine.

    Lifecycle:
        1. Receives a TripRequest (fully validated value object).
        2. Delegates to StateGraphEngine.run() — an async generator.
        3. Yields each SSE event dict to the FastAPI streaming endpoint.

    The Use Case itself contains no pipeline logic; it is purely a composition
    root that wires infrastructure ports to the orchestration engine.
    """

    def __init__(
        self,
        llm_client: ILLMClient,
        embedding_client: IEmbeddingClient,
        vector_store: IVectorStore,
        itinerary_repo: IItineraryRepository,
        online_adapters: list[IOnlineAdapter] | None = None,
        # Optional observability ports — safe to omit in tests
        checkpoint_repo: "ICheckpointRepository | None" = None,
        trace_repo: "ITraceRepository | None" = None,
    ) -> None:
        self._engine = StateGraphEngine(
            llm_client=llm_client,
            embedding_client=embedding_client,
            vector_store=vector_store,
            itinerary_repo=itinerary_repo,
            online_adapters=online_adapters,
            checkpoint_repo=checkpoint_repo,
            trace_repo=trace_repo,
        )

    async def execute(self, request: TripRequest) -> AsyncIterator[dict]:
        """
        Async generator: yields SSE-ready event dicts.

        Event types (mirrors the previous linear pipeline contract):
          {"type": "stage",   "name": "<string>"}
          {"type": "chunk",   "content": "<token>"}
          {"type": "context", "kb_chunks": <int>, "kb_miss": <bool>}
          {"type": "done",    "id": "<uuid>", "day_count": <int>, ...}
          {"type": "error",   "message": "<string>"}
        """
        return self._run(request)

    async def _run(self, request: TripRequest) -> AsyncIterator[dict]:
        try:
            async for event in self._engine.run(request):
                yield event
        except Exception as exc:  # noqa: BLE001
            logger.exception("GenerateItineraryUseCase unhandled error: %s", exc)
            yield {"type": "error", "message": str(exc)}
