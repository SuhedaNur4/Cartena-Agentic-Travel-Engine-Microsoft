"""
API Router: POST /api/v1/generate

Streams itinerary generation as Server-Sent Events (SSE).
This router is intentionally thin — validation only, then delegates to use case.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.api.dependencies import get_generate_use_case
from backend.api.schemas.requests import TripRequestDTO
from backend.application.use_cases.generate_itinerary import GenerateItineraryUseCase

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/generate",
    summary="Generate a travel itinerary (streaming SSE)",
    response_description="Server-Sent Events stream of itinerary chunks",
)
async def generate_itinerary(
    body: TripRequestDTO,
    use_case: GenerateItineraryUseCase = Depends(get_generate_use_case),
) -> StreamingResponse:
    """
    Accepts trip parameters and streams the AI-generated itinerary via SSE.

    SSE Event types:
    - `context`  — RAG metadata (kb_chunks count, kb_miss flag)
    - `chunk`    — Raw LLM token
    - `done`     — Generation complete (includes itinerary id)
    - `error`    — Pipeline error (generation continues with fallback where possible)
    """
    trip_request = body.to_domain()

    async def event_stream():
        try:
            async for event in use_case.execute(trip_request):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:
            logger.exception("Unhandled error in event stream: %s", exc)
            error_event = {"type": "error", "message": "Internal server error."}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",     # Disable Nginx buffering if proxied
            "Connection": "keep-alive",
        },
    )
