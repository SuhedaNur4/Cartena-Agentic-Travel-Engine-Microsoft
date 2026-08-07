"""
Use Case: RegenerateDay

Re-runs the LLM pipeline to regenerate a single day of a saved itinerary,
leaving all other days untouched.

The regeneration uses the same RAG + Prompt Builder pipeline as the full
generation workflow, but scopes the request to a single day and merges
the result back into the existing itinerary.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from backend.application.ports.itinerary_repo_port import IItineraryRepository
from backend.application.ports.llm_port import ILLMClient
from backend.application.services.knowledge_service import KnowledgeService
from backend.domain.services import itinerary_parser, prompt_builder
from backend.domain.services.city import normalize_city
from backend.domain.services.validator import ItineraryValidator

logger = logging.getLogger(__name__)


class RegenerateDayUseCase:
    """
    Regenerates a single day of an existing itinerary.

    Yields SSE events compatible with the frontend streaming protocol.
    """

    def __init__(
        self,
        llm_client: ILLMClient,
        knowledge_service: KnowledgeService,
        itinerary_repo: IItineraryRepository,
    ) -> None:
        self._llm = llm_client
        self._knowledge_service = knowledge_service
        self._repo = itinerary_repo

    async def execute(
        self,
        itinerary_id: str,
        day_number: int,
        reason: str = "",
    ) -> AsyncIterator[dict]:
        async for event in self._run(itinerary_id, day_number, reason):
            yield event

    async def _run(
        self,
        itinerary_id: str,
        day_number: int,
        reason: str,
    ) -> AsyncIterator[dict]:
        try:
            itinerary = await self._repo.get(itinerary_id)
            if not itinerary:
                yield {"type": "error", "message": f"Itinerary {itinerary_id} not found."}
                return

            yield {"type": "stage", "name": "Preparing regeneration"}

            # Build a focused trip request for just this day
            request = itinerary.trip_request

            # RAG retrieval via KnowledgeService
            all_chunks = []
            has_kb_miss = False
            for dest in request.destinations:
                try:
                    docs = await self._knowledge_service.get_context_for_destination(dest, request.query_text)
                    for doc in docs:
                        chunk_str = f"Source: {doc.source.upper()} | Title: {doc.title}\n{doc.content}"
                        all_chunks.append(chunk_str)
                except Exception as e:
                    logger.error(f"Failed to fetch knowledge for {dest}: {e}")
                    has_kb_miss = True
            
            unique_chunks = list(dict.fromkeys(all_chunks))
            kb_miss = has_kb_miss

            yield {"type": "stage", "name": f"Regenerating Day {day_number}"}

            # Build prompt scoped to 1 day
            system_prompt, user_prompt = prompt_builder.build(
                request=request,
                rag_chunks=unique_chunks,
                online_context=[],
                chunks_are_off_topic=kb_miss,
                target_day=day_number,
                user_replan_reason=reason,
            )

            full_response = ""
            async for token in self._llm.stream(
                system_prompt, user_prompt, expected_days=1
            ):
                full_response += token
                yield {"type": "chunk", "content": token}

            # Parse the new day
            parsed_itinerary = itinerary_parser.parse(
                raw_response=full_response,
                trip_request=request,
                model_used=self._llm.model_name,
            )

            if not parsed_itinerary or not parsed_itinerary.days:
                yield {"type": "error", "message": "Could not parse regenerated day."}
                return

            new_day = parsed_itinerary.days[0]
            new_day.day_number = day_number

            import copy
            from backend.domain.services import constraint_map
            
            # Deep copy the original itinerary to preserve properties
            merged_itinerary = copy.deepcopy(itinerary)
            
            # Replace only the target day
            for idx, day in enumerate(merged_itinerary.days):
                if day.day_number == day_number:
                    merged_itinerary.days[idx] = new_day
                    break

            # Validate the FULL merged itinerary against constraints
            constraints = constraint_map.build(request)
            report = ItineraryValidator.validate(
                itinerary=merged_itinerary,
                constraints=constraints,
            )
            
            if not report.is_valid:
                logger.error("Partial regeneration validation failed: %s", report.hard_violations)
                yield {
                    "type": "error", 
                    "message": f"Validation failed for regenerated day: {report.hard_violations[0]}"
                }
                return

            # Inherit quality scores and save
            merged_itinerary.constraint_score = report.constraint_score
            merged_itinerary.quality_score = report.quality_score
            merged_itinerary.kb_miss = kb_miss
            
            await self._repo.save(merged_itinerary)
            yield {"type": "done", "id": itinerary_id, "day_number": day_number}

        except Exception as exc:  # noqa: BLE001
            logger.exception("RegenerateDayUseCase error: %s", exc)
            yield {"type": "error", "message": str(exc)}
