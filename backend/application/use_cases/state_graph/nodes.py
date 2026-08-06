"""
State Graph: Node Implementations

Each node is a pure async function that receives the shared WorkflowState,
mutates it in-place, and returns it.  Nodes never call each other directly;
the Router decides which node executes next.

Node catalogue:
    planner_node           — Resolves online context stubs; emits stage event.
    constraint_node        — Derives the ConstraintMap from the TripRequest.
    retriever_node         — Embeds query and fetches RAG chunks from ChromaDB.
    generator_node         — Streams LLM output; stores full text in state.
    parser_node            — Parses raw LLM text into an Itinerary domain model.
    validator_node         — Runs deterministic ItineraryValidator; sets status.
    repair_node            — Formats violation report into a targeted repair prompt.
    finalize_node          — Persists the Itinerary to SQLite; emits done event.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime

from backend.application.ports.embedding_port import IEmbeddingClient
from backend.application.ports.itinerary_repo_port import IItineraryRepository
from backend.application.ports.llm_port import ILLMClient
from backend.application.ports.online_adapter_port import IOnlineAdapter
from backend.application.ports.vector_store_port import IVectorStore
from backend.application.use_cases.state_graph.state import TraceEvent, WorkflowState
from backend.domain.services import constraint_map as constraint_map_svc
from backend.domain.services import itinerary_parser, prompt_builder
from backend.domain.services.city import normalize_city
from backend.domain.services.validator import ItineraryValidator

logger = logging.getLogger(__name__)


# ── Node 1: Planner ───────────────────────────────────────────────────────────


async def planner_node(
    state: WorkflowState,
    online_adapters: list[IOnlineAdapter] | None = None,
) -> WorkflowState:
    """
    Resolves any available online context (weather, POI stubs).
    In the current MVP, all adapters are stubs and always return empty lists.
    Emits the first SSE stage event so the frontend shows progress immediately.
    """
    t0 = time.monotonic()
    state.enter_node("planner")
    state.emit({"type": "stage", "name": "Understanding request"})

    for adapter in online_adapters or []:
        try:
            if await adapter.is_available():
                extra = await adapter.fetch(state.request.query_text, {})
                state.online_context.extend(extra)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Online adapter failed (non-fatal): %s", exc)

    state.record_trace(
        TraceEvent(
            node="planner",
            timestamp=datetime.utcnow(),
            duration_ms=(time.monotonic() - t0) * 1000,
            metadata={"online_context_items": len(state.online_context)},
        )
    )
    return state


# ── Node 2: Constraint Analysis ───────────────────────────────────────────────


async def constraint_node(state: WorkflowState) -> WorkflowState:
    """
    Derives a structured ConstraintMap from the TripRequest.
    The map is a plain dict consumed by the Validator and Prompt Builder.
    Pure computation — no I/O.
    """
    t0 = time.monotonic()
    state.enter_node("constraint_analysis")

    state.constraints = constraint_map_svc.build(state.request)

    state.record_trace(
        TraceEvent(
            node="constraint_analysis",
            timestamp=datetime.utcnow(),
            duration_ms=(time.monotonic() - t0) * 1000,
            metadata={"budget_level": state.constraints.get("budget_level")},
        )
    )
    return state


# ── Node 3: Retriever ─────────────────────────────────────────────────────────


async def retriever_node(
    state: WorkflowState,
    embedding_client: IEmbeddingClient,
    vector_store: IVectorStore,
) -> WorkflowState:
    """
    Embeds the trip query and retrieves top-k semantically relevant KB chunks.
    Falls back to unfiltered retrieval if no city-specific chunks are found.
    Emits context metadata event so the frontend can show a KB-miss badge.
    """
    t0 = time.monotonic()
    state.enter_node("retriever")
    state.emit({"type": "stage", "name": "Retrieving local knowledge"})

    query_vector = await embedding_client.embed(state.request.query_text)
    city_key = normalize_city(state.request.destination)

    # IVectorStore.retrieve() returns list[tuple[KnowledgeChunk, float]].
    # We extract only the content strings — the float similarity scores are
    # not consumed downstream yet (reserved for EPIC 3 observability).
    raw_chunks = await vector_store.retrieve(
        query_vector=query_vector,
        city=city_key,
        top_k=5,
    )
    # Deduplicate by content while preserving order.
    unique_contents: list[str] = list(
        dict.fromkeys(chunk.content for chunk, _score in raw_chunks)
    )
    kb_miss = len(unique_contents) == 0

    if kb_miss:
        logger.warning(
            "No KB chunks found for '%s'. Falling back to unfiltered retrieval.",
            state.request.destination,
        )
        fallback_raw = await vector_store.retrieve(
            query_vector=query_vector,
            city=None,
            top_k=3,
        )
        unique_contents = list(
            dict.fromkeys(chunk.content for chunk, _score in fallback_raw)
        )

    state.rag_chunks = unique_contents
    state.kb_miss = kb_miss

    state.emit(
        {
            "type": "context",
            "kb_chunks": len(unique_contents),
            "kb_miss": kb_miss,
        }
    )

    state.record_trace(
        TraceEvent(
            node="retriever",
            timestamp=datetime.utcnow(),
            duration_ms=(time.monotonic() - t0) * 1000,
            metadata={"kb_chunks": len(unique_contents), "kb_miss": kb_miss},
        )
    )
    return state


# ── Node 4: Generator ─────────────────────────────────────────────────────────


async def generator_node(
    state: WorkflowState,
    llm_client: ILLMClient,
) -> WorkflowState:
    """
    Builds the RAG-augmented prompt and streams the LLM output token by token.
    On repair iterations the repair_prompt is injected as the user message,
    keeping the same system context but focusing the model on the violations.
    Streams each token as an SSE chunk event for real-time frontend updates.
    """
    t0 = time.monotonic()
    state.enter_node("generator")
    state.emit({"type": "stage", "name": "Generating itinerary"})

    # First pass: build a fresh prompt from the request + RAG context.
    # Repair pass: reuse system prompt but inject the targeted repair instruction.
    if state.repair_attempts == 0:
        state.emit({"type": "stage", "name": "Building AI prompt"})
        system_prompt, user_prompt = prompt_builder.build(
            request=state.request,
            rag_chunks=state.rag_chunks,
            online_context=state.online_context,
            chunks_are_off_topic=state.kb_miss,
        )
        state.system_prompt = system_prompt
        state.user_prompt = user_prompt
    else:
        # Repair pass: keep system context, swap user message to repair prompt.
        user_prompt = state.repair_prompt

    logger.info(
        "Generator streaming (%s, attempt %d).",
        state.request.destination,
        state.repair_attempts + 1,
    )

    full_response = ""
    async for token in llm_client.stream(
        state.system_prompt,
        user_prompt,
        expected_days=state.request.duration_days,
    ):
        full_response += token
        state.emit({"type": "chunk", "content": token})

    state.generated_text = full_response

    state.record_trace(
        TraceEvent(
            node="generator",
            timestamp=datetime.utcnow(),
            duration_ms=(time.monotonic() - t0) * 1000,
            metadata={
                "repair_attempt": state.repair_attempts,
                "response_chars": len(full_response),
            },
        )
    )
    return state


# ── Node 5: Parser ────────────────────────────────────────────────────────────


async def parser_node(
    state: WorkflowState,
    llm_client: ILLMClient,
) -> WorkflowState:
    """
    Converts the raw LLM text into a typed Itinerary domain model.
    Uses the JSONSanitizer + Pydantic pipeline from itinerary_parser service.
    If parsing itself fails, records the error and transitions to 'failed'.
    """
    t0 = time.monotonic()
    state.enter_node("parser")

    try:
        state.itinerary = itinerary_parser.parse(
            raw_response=state.generated_text,
            trip_request=state.request,
            model_used=llm_client.model_name,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Parser failed: %s", exc)
        state.status = "failed"
        state.error_message = f"Parsing error: {exc}"
        state.emit({"type": "error", "message": state.error_message})

    state.record_trace(
        TraceEvent(
            node="parser",
            timestamp=datetime.utcnow(),
            duration_ms=(time.monotonic() - t0) * 1000,
            metadata={
                "days_parsed": len(state.itinerary.days) if state.itinerary else 0,
                "parse_ok": state.itinerary is not None,
            },
        )
    )
    return state


# ── Node 6: Validator ─────────────────────────────────────────────────────────


async def validator_node(state: WorkflowState) -> WorkflowState:
    """
    Runs the deterministic ItineraryValidator against the parsed Itinerary.
    Hard violations → status = "repair" (triggers Repair Loop).
    Clean validation → status = "success".
    """
    t0 = time.monotonic()
    state.enter_node("validator")

    if state.itinerary is None:
        # Parser already set status = "failed"; nothing to validate.
        return state

    report = ItineraryValidator.validate(
        itinerary=state.itinerary,
        constraints=state.constraints,
    )
    state.violation_report = report

    if report.is_valid:
        state.status = "success"
        # Propagate quality scores into the Itinerary model for persistence.
        state.itinerary.constraint_score = report.constraint_score
        state.itinerary.quality_score = report.quality_score
    else:
        state.status = "repair"
        logger.warning(
            "Validation failed (attempt %d): %s",
            state.repair_attempts + 1,
            report.hard_violations,
        )

    state.record_trace(
        TraceEvent(
            node="validator",
            timestamp=datetime.utcnow(),
            duration_ms=(time.monotonic() - t0) * 1000,
            metadata={
                "is_valid": report.is_valid,
                "hard_violations": len(report.hard_violations),
                "constraint_score": report.constraint_score,
            },
        )
    )
    return state


# ── Node 7: Repair ────────────────────────────────────────────────────────────


async def repair_node(state: WorkflowState) -> WorkflowState:
    """
    Translates the ViolationReport into a targeted repair instruction for the LLM.
    Increments the repair counter so the Router can enforce the attempt limit.
    The actual LLM call happens in the next Generator invocation.
    """
    t0 = time.monotonic()
    state.enter_node("repair")
    state.emit({"type": "stage", "name": "Repairing itinerary"})

    state.repair_prompt = state.violation_report.to_repair_prompt(
        expected_days=state.request.duration_days
    )
    state.repair_attempts += 1

    logger.info("Repair loop iteration %d initiated.", state.repair_attempts)

    state.record_trace(
        TraceEvent(
            node="repair",
            timestamp=datetime.utcnow(),
            duration_ms=(time.monotonic() - t0) * 1000,
            metadata={"repair_attempt": state.repair_attempts},
        )
    )
    return state


# ── Node 8: Finalize ──────────────────────────────────────────────────────────


async def finalize_node(
    state: WorkflowState,
    itinerary_repo: IItineraryRepository,
) -> WorkflowState:
    """
    Persists the validated Itinerary to SQLite and emits the terminal 'done' event.
    This node is only reached when status == "success"; it is never called for
    failed or exhausted-repair-loop paths.
    """
    t0 = time.monotonic()
    state.enter_node("finalize")
    state.emit({"type": "stage", "name": "Saving itinerary"})

    state.itinerary.kb_miss = state.kb_miss
    if state.planning_mode == "PARTIAL" and state.original_itinerary:
        target = state.target_days[0] if state.target_days else 1
        new_day = next((d for d in state.itinerary.days if d.day_number == target), None)
        if not new_day and state.itinerary.days:
            new_day = state.itinerary.days[0]
            new_day.day_number = target
            
        if new_day:
            for i, d in enumerate(state.original_itinerary.days):
                if d.day_number == target:
                    state.original_itinerary.days[i] = new_day
                    break
            
            state.original_itinerary.id = state.original_itinerary.id or state.itinerary.id
            itinerary_id = await itinerary_repo.save(state.original_itinerary)
            
            import dataclasses
            state.emit(
                {
                    "type": "done",
                    "id": itinerary_id,
                    "day": dataclasses.asdict(new_day),
                    "kb_miss": state.kb_miss,
                    "is_complete": True,
                }
            )
        else:
            state.emit({"type": "error", "message": "Failed to extract regenerated day."})
    else:
        itinerary_id = await itinerary_repo.save(state.itinerary)
        state.itinerary.id = itinerary_id

        state.emit(
            {
                "type": "done",
                "id": itinerary_id,
                "kb_miss": state.kb_miss,
                "day_count": len(state.itinerary.days),
                "is_complete": True,
            }
        )

    state.record_trace(
        TraceEvent(
            node="finalize",
            timestamp=datetime.utcnow(),
            duration_ms=(time.monotonic() - t0) * 1000,
            metadata={"itinerary_id": itinerary_id},
        )
    )
    return state
