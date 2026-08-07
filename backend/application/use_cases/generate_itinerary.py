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
from backend.application.use_cases.allocation.engine import AllocationEngine
from backend.application.services.knowledge_service import KnowledgeService
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
        checkpoint_repo: "ICheckpointRepository | None" = None,
        trace_repo: "ITraceRepository | None" = None,
        allocation_engine: AllocationEngine | None = None,
        knowledge_service: KnowledgeService | None = None,
    ) -> None:
        self._allocation_engine = allocation_engine
        self._knowledge_service = knowledge_service
        self._engine = StateGraphEngine(
            llm_client=llm_client,
            knowledge_service=knowledge_service,
            embedding_client=embedding_client,
            vector_store=vector_store,
            itinerary_repo=itinerary_repo,
            online_adapters=online_adapters,
            checkpoint_repo=checkpoint_repo,
            trace_repo=trace_repo,
        )

    async def execute(
        self,
        request: TripRequest | None = None,
        workflow_id: str | None = None,
        planning_mode: str = "full",
        original_itinerary=None,
        target_days: list[int] | None = None,
        user_replan_reason: str = ""
    ) -> AsyncIterator[dict]:
        """
        Async generator: yields SSE-ready event dicts.

        Declared with `yield` so it is a true async generator — the FastAPI
        router can safely do `async for event in use_case.execute(request)`.

        Event types (mirrors the previous linear pipeline contract):
          {"type": "stage",   "name": "<string>"}
          {"type": "chunk",   "content": "<token>"}
          {"type": "context", "kb_chunks": <int>, "kb_miss": <bool>}
          {"type": "done",    "id": "<uuid>", "day_count": <int>, ...}
          {"type": "error",   "message": "<string>"}
        """
        try:
            if request and self._allocation_engine and not workflow_id:
                yield {"type": "stage", "name": "Resolving destinations"}
                if self._knowledge_service:
                    normalized_dests = []
                    for dest_str in request.destinations:
                        resolved_dests = await self._knowledge_service.parse_and_resolve_destinations(dest_str)
                        for r_dest in resolved_dests:
                            normalized_dests.append(r_dest.input_name)
                            
                    import dataclasses
                    request = dataclasses.replace(request, destinations=tuple(normalized_dests))
                
                yield {"type": "stage", "name": "Analyzing route sequence"}
                from backend.application.use_cases.allocation.route_analyzer import RouteAnalyzer
                analyzer = RouteAnalyzer()
                route_seq = analyzer.analyze(request)
                
                # Combine start, stops, and end in order (deduplicate if needed, though they shouldn't overlap if coded right)
                # Wait, route_seq.stops actually contains ALL intermediate stops AND start and end depending on how we wrote it.
                # Actually, in RouteAnalyzer we appended start_city, intermediate, then end_city to stops.
                ordered_dests = tuple(route_seq.stops)
                request = dataclasses.replace(request, destinations=ordered_dests)
                
                yield {"type": "stage", "name": "Allocating trip days"}
                request = await self._allocation_engine.allocate(request)

            async for event in self._engine.run(
                request,
                workflow_id,
                planning_mode=planning_mode,
                original_itinerary=original_itinerary,
                target_days=target_days,
                user_replan_reason=user_replan_reason
            ):
                yield event
        except Exception as exc:  # noqa: BLE001
            logger.exception("GenerateItineraryUseCase unhandled error: %s", exc)
            yield {"type": "error", "message": str(exc)}
