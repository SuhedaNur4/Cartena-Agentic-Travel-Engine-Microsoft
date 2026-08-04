"""API: FastAPI dependency resolvers."""

from __future__ import annotations

from fastapi import Request

from backend.application.use_cases.export_itinerary import ExportItineraryUseCase
from backend.application.use_cases.generate_itinerary import GenerateItineraryUseCase
from backend.application.use_cases.get_itinerary import GetItineraryUseCase
from backend.application.use_cases.list_itineraries import ListItinerariesUseCase
from backend.application.use_cases.list_destinations import ListDestinationsUseCase
from backend.application.use_cases.update_day import UpdateDayUseCase
from backend.application.use_cases.regenerate_day import RegenerateDayUseCase
from backend.application.use_cases.toggle_favorite import ToggleFavoriteUseCase
from backend.application.use_cases.resume_workflow import ResumeWorkflowUseCase
from backend.core.container import Container


def _get_container(request: Request) -> Container:
    return request.app.state.container


def get_generate_use_case(request: Request) -> GenerateItineraryUseCase:
    return _get_container(request).generate_itinerary


def get_get_use_case(request: Request) -> GetItineraryUseCase:
    return _get_container(request).get_itinerary


def get_list_use_case(request: Request) -> ListItinerariesUseCase:
    return _get_container(request).list_itineraries


def get_export_use_case(request: Request) -> ExportItineraryUseCase:
    return _get_container(request).export_itinerary


def get_list_destinations_use_case(request: Request) -> ListDestinationsUseCase:
    return _get_container(request).list_destinations


def get_update_day_use_case(request: Request) -> UpdateDayUseCase:
    return _get_container(request).update_day


def get_regenerate_day_use_case(request: Request) -> RegenerateDayUseCase:
    return _get_container(request).regenerate_day


def get_toggle_favorite_use_case(request: Request) -> ToggleFavoriteUseCase:
    return _get_container(request).toggle_favorite

def get_resume_workflow_use_case(request: Request) -> ResumeWorkflowUseCase:
    return _get_container(request).resume_workflow
