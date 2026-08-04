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

from backend.application.ports.embedding_port import IEmbeddingClient
from backend.application.ports.itinerary_repo_port import IItineraryRepository
from backend.application.ports.llm_port import ILLMClient
from backend.application.ports.vector_store_port import IVectorStore
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
        embedding_client: IEmbeddingClient,
        vector_store: IVectorStore,
        itinerary_repo: IItineraryRepository,
    ) -> None:
        self._llm = llm_client
        self._embeddings = embedding_client
        self._vector_store = vector_store
        self._repo = itinerary_repo

    async def execute(
        self,
        itinerary_id: str,
        day_number: int,
        reason: str = "",
    ) -> AsyncIterator[dict]:
        return self._run(itinerary_id, day_number, reason)

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

            # RAG retrieval
            query_vector = await self._embeddings.embed(request.query_text)
            city_key = normalize_city(request.destination)
            chunks = await self._vector_store.retrieve(
                query_vector=query_vector,
                city=city_key,
                top_k=5,
            )
            unique_chunks = list(dict.fromkeys(chunks))
            kb_miss = len(unique_chunks) == 0
            if kb_miss:
                fallback = await self._vector_store.retrieve(
                    query_vector=query_vector, city=None, top_k=3
                )
                unique_chunks = list(dict.fromkeys(fallback))

            yield {"type": "stage", "name": f"Regenerating Day {day_number}"}

            # Build prompt scoped to 1 day
            system_prompt, user_prompt = prompt_builder.build(
                request=request,
                rag_chunks=unique_chunks,
                online_context=[],
                chunks_are_off_topic=kb_miss,
            )
            # Append user's reason if provided
            if reason:
                user_prompt += f"\n\nUser note for this day: {reason}"
            user_prompt += f"\n\nGenerate ONLY Day {day_number}. Output a single day object."

            full_response = ""
            async for token in self._llm.stream(
                system_prompt, user_prompt, expected_days=1
            ):
                full_response += token
                yield {"type": "chunk", "content": token}

            # Parse and validate the new day
            new_itinerary = itinerary_parser.parse(
                raw_response=full_response,
                trip_request=request,
                model_used=self._llm.model_name,
            )

            if not new_itinerary.days:
                yield {"type": "error", "message": "Could not parse regenerated day."}
                return

            new_day = new_itinerary.days[0]
            new_day.day_number = day_number

            # Merge back into the original itinerary
            for idx, day in enumerate(itinerary.days):
                if day.day_number == day_number:
                    itinerary.days[idx] = new_day
                    break

            await self._repo.update(itinerary)
            yield {"type": "done", "id": itinerary_id, "day_number": day_number}

        except Exception as exc:  # noqa: BLE001
            logger.exception("RegenerateDayUseCase error: %s", exc)
            yield {"type": "error", "message": str(exc)}
