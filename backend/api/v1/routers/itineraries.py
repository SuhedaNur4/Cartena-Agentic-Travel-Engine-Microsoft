"""API Router: Itinerary CRUD and export endpoints."""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from backend.api.dependencies import (
    get_export_use_case,
    get_get_use_case,
    get_list_use_case,
    get_update_day_use_case,
    get_generate_use_case,
    get_toggle_favorite_use_case,
    get_resume_workflow_use_case,
)
from backend.api.schemas.requests import ToggleFavoriteRequestDTO, ReplanRequestDTO, ResumeRequestDTO
from backend.api.schemas.responses import (
    ActivityBlockDTO,
    DayDTO,
    ItineraryResponseDTO,
    ItinerarySummaryDTO,
    MealSuggestionDTO,
)
from backend.application.use_cases.export_itinerary import ExportItineraryUseCase
from backend.application.use_cases.get_itinerary import GetItineraryUseCase
from backend.application.use_cases.list_itineraries import ListItinerariesUseCase
from backend.application.use_cases.update_day import UpdateDayUseCase
from backend.application.use_cases.generate_itinerary import GenerateItineraryUseCase
from backend.application.use_cases.toggle_favorite import ToggleFavoriteUseCase
from backend.application.use_cases.resume_workflow import ResumeWorkflowUseCase
from backend.domain.models.itinerary import ActivityBlock, Day, Itinerary, MealSuggestion
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def _block_to_dto(block: ActivityBlock) -> ActivityBlockDTO:
    """Domain ActivityBlock -> DTO. Yedi alanın tamamı."""
    return ActivityBlockDTO(
        description=block.description,
        location=block.location,
        why_recommended=block.why_recommended,
        duration_estimate=block.duration_estimate,
        cost_estimate=block.cost_estimate,
        reservation_needed=block.reservation_needed,
        transport_suggestion=block.transport_suggestion,
    )

def _dto_to_block(dto: ActivityBlockDTO) -> ActivityBlock:
    """DTO -> Domain ActivityBlock."""
    return ActivityBlock(
        description=dto.description,
        location=dto.location,
        why_recommended=dto.why_recommended,
        duration_estimate=dto.duration_estimate,
        cost_estimate=dto.cost_estimate,
        reservation_needed=dto.reservation_needed,
        transport_suggestion=dto.transport_suggestion,
    )

def _dto_to_day(dto: DayDTO) -> Day:
    """DTO -> Domain Day."""
    return Day(
        day_number=dto.day_number,
        title=dto.title,
        morning=_dto_to_block(dto.morning),
        afternoon=_dto_to_block(dto.afternoon),
        evening=_dto_to_block(dto.evening),
        meals=MealSuggestion(breakfast=dto.meals.breakfast, lunch=dto.meals.lunch, dinner=dto.meals.dinner),
        budget_estimate=dto.budget_estimate,
        tips=dto.tips,
    )
def _to_dto(itinerary: Itinerary) -> ItineraryResponseDTO:
    return ItineraryResponseDTO(
        id=itinerary.id,
        destination=itinerary.destination,
        duration_days=itinerary.duration_days,
        budget=itinerary.trip_request.budget,
        interests=list(itinerary.trip_request.interests),
        notes=itinerary.trip_request.notes,
        model_used=itinerary.model_used,
        created_at=itinerary.created_at,
        day_count=len(itinerary.days),
        is_complete=itinerary.is_complete(),
        kb_miss=itinerary.kb_miss,
        is_favorite=itinerary.is_favorite,
        days=[
            DayDTO(
                day_number=d.day_number,
                title=d.title,
                morning=_block_to_dto(d.morning),
                afternoon=_block_to_dto(d.afternoon),
                evening=_block_to_dto(d.evening),
                meals=MealSuggestionDTO(breakfast=d.meals.breakfast, lunch=d.meals.lunch, dinner=d.meals.dinner),
                budget_estimate=d.budget_estimate,
                tips=d.tips,
            )
            for d in itinerary.days
        ],
    )


@router.get(
    "/itineraries",
    response_model=list[ItinerarySummaryDTO],
    summary="List saved itineraries",
)
async def list_itineraries(
    limit: int = Query(default=50, ge=1, le=200),
    use_case: ListItinerariesUseCase = Depends(get_list_use_case),
) -> list[ItinerarySummaryDTO]:
    summaries = await use_case.execute(limit=limit)
    return [
        ItinerarySummaryDTO(
            id=s.id,
            destination=s.destination,
            duration_days=s.duration_days,
            budget=s.budget,
            model_used=s.model_used,
            created_at=s.created_at,
            day_count=s.day_count,
            is_favorite=s.is_favorite,
        )
        for s in summaries
    ]


@router.get(
    "/itineraries/{itinerary_id}",
    response_model=ItineraryResponseDTO,
    summary="Get a saved itinerary by ID",
)
async def get_itinerary(
    itinerary_id: str,
    use_case: GetItineraryUseCase = Depends(get_get_use_case),
) -> ItineraryResponseDTO:
    itinerary = await use_case.execute(itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail=f"Itinerary '{itinerary_id}' not found.")
    return _to_dto(itinerary)


@router.get(
    "/itineraries/{itinerary_id}/export",
    summary="Export itinerary as Markdown, JSON, or print-ready HTML (PDF)",
)
async def export_itinerary(
    itinerary_id: str,
    fmt: Literal["json", "md", "html"] = Query(default="json"),
    use_case: ExportItineraryUseCase = Depends(get_export_use_case),
) -> Response:
    result = await use_case.execute(itinerary_id=itinerary_id, fmt=fmt)
    if not result:
        raise HTTPException(status_code=404, detail=f"Itinerary '{itinerary_id}' not found.")

    content, mime_type = result

    if fmt == "html":
        # Open inline so the browser renders it; user can File → Print → Save as PDF
        return Response(
            content=content.encode("utf-8"),
            media_type=mime_type,
            headers={"Content-Disposition": f'inline; filename="itinerary_{itinerary_id[:8]}.html"'},
        )

    ext = {"json": "json", "md": "md"}.get(fmt, fmt)
    filename = f"itinerary_{itinerary_id[:8]}.{ext}"
    return Response(
        content=content.encode("utf-8"),
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/itineraries/{itinerary_id}/toggle-favorite",
    summary="Toggle favorite status of an itinerary",
)
async def toggle_favorite(
    itinerary_id: str,
    request: ToggleFavoriteRequestDTO,
    use_case: ToggleFavoriteUseCase = Depends(get_toggle_favorite_use_case),
):
    success = await use_case.execute(itinerary_id, request.is_favorite)
    if not success:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    return Response(status_code=204)


@router.post(
    "/workflows/{workflow_id}/resume",
    summary="Resume a paused workflow with user decision (HITL)",
)
async def resume_workflow(
    workflow_id: str,
    request: ResumeRequestDTO,
    resume_use_case: ResumeWorkflowUseCase = Depends(get_resume_workflow_use_case),
) -> StreamingResponse:
    import json
    
    async def sse_generator():
        try:
            async for event in resume_use_case.execute(workflow_id, request.resolution_id):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.exception("Error during resume workflow stream")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Internal Server Error'})}\n\n"
            
    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@router.put(
    "/itineraries/{itinerary_id}/days/{day_number}",
    summary="Update a specific day in an itinerary",
)
async def update_day(
    itinerary_id: str,
    day_number: int,
    day_dto: DayDTO,
    use_case: UpdateDayUseCase = Depends(get_update_day_use_case),
):
    if day_dto.day_number != day_number:
        raise HTTPException(status_code=400, detail="Day number in path does not match body.")
    
    domain_day = _dto_to_day(day_dto)
    success = await use_case.execute(itinerary_id, domain_day)
    if not success:
        raise HTTPException(status_code=404, detail="Itinerary or day not found.")
    return {"success": True}


@router.post(
    "/itineraries/{itinerary_id}/days/{day_number}/regenerate",
    summary="Regenerate a specific day in an itinerary using State Graph",
)
async def regenerate_day(
    itinerary_id: str,
    day_number: int,
    request: ReplanRequestDTO,
    generate_use_case: GenerateItineraryUseCase = Depends(get_generate_use_case),
    get_itinerary_use_case: GetItineraryUseCase = Depends(get_get_use_case),
) -> StreamingResponse:
    import json
    
    # We must fetch the original itinerary first
    original_itinerary = await get_itinerary_use_case.execute(itinerary_id)
    if not original_itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
        
    async def sse_generator():
        try:
            async for event in generate_use_case.execute(
                request=original_itinerary.trip_request,
                planning_mode="PARTIAL",
                original_itinerary=original_itinerary,
                target_days=[day_number],
                user_replan_reason=request.reason
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.exception("Error during regenerate day stream")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Internal Server Error'})}\n\n"
    
    return StreamingResponse(sse_generator(), media_type="text/event-stream")

