from fastapi import APIRouter, Depends
from backend.application.use_cases.list_destinations import ListDestinationsUseCase
from backend.api.dependencies import get_list_destinations_use_case

router = APIRouter(
    prefix="/destinations",
    tags=["Destinations"],
)

@router.get("/")
async def list_destinations(
    use_case: ListDestinationsUseCase = Depends(get_list_destinations_use_case),
):
    """
    Return a list of all unique destinations with their trip count.
    """
    return await use_case.execute()
