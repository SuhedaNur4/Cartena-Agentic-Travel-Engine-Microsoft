"""
API Router: World Geography
Provides static endpoints for the World Explorer feature.
"""

import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import Any

from backend.core.config import settings

router = APIRouter()

# Load geography data once into memory since it's small and static
world_data_path = Path("backend/data/world_geography.json")
world_data = {"countries": []}
if world_data_path.exists():
    with world_data_path.open(encoding="utf-8") as f:
        world_data = json.load(f)

@router.get("/countries", response_model=dict[str, list[dict[str, Any]]])
async def get_countries() -> dict[str, list[dict[str, Any]]]:
    """
    Returns the list of all countries with their major cities.
    """
    return world_data

@router.get("/countries/{code}/cities", response_model=list[str])
async def get_country_cities(code: str) -> list[str]:
    """
    Returns the major cities for a specific country code.
    """
    code = code.upper()
    for country in world_data.get("countries", []):
        if country["code"] == code:
            return country.get("cities", [])
    raise HTTPException(status_code=404, detail="Country not found")
