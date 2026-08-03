"""
Infrastructure: SQLiteItineraryRepository

Implements IItineraryRepository using aiosqlite for fully async SQLite access.
Schema is created automatically on first use (no migration tool needed for MVP).
Itinerary days are stored as a JSON blob alongside structured metadata columns
for fast list queries without deserializing the full day data.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

import aiosqlite

from backend.application.ports.itinerary_repo_port import IItineraryRepository
from backend.domain.models.itinerary import (
    ActivityBlock,
    Day,
    Itinerary,
    ItinerarySummary,
    MealSuggestion,
)
from backend.domain.models.trip_request import BudgetLevel, Interest, TripRequest

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS itineraries (
    id              TEXT PRIMARY KEY,
    destination     TEXT NOT NULL,
    duration_days   INTEGER NOT NULL,
    budget          TEXT NOT NULL,
    interests       TEXT NOT NULL,       -- JSON array of strings
    notes           TEXT NOT NULL DEFAULT '',
    model_used      TEXT NOT NULL,
    created_at      TEXT NOT NULL,       -- ISO-8601 UTC
    day_count       INTEGER NOT NULL,
    days_json       TEXT NOT NULL,       -- Full day data as JSON blob
    raw_response    TEXT NOT NULL DEFAULT '',
    kb_miss         INTEGER NOT NULL DEFAULT 0  -- 1 if KB had no city-specific chunks
)
"""

# Mevcut DB'lere eksik sütunları eklemek için migration listesi.
# CREATE TABLE IF NOT EXISTS var olan tabloya sütun eklemez, bu yüzden
# ALTER TABLE ADD COLUMN ile ileriye dönük migration yapılır.
# Her eleman (sütun_adı, ALTER_TABLE_ifadesi) çiftidir.
_MIGRATIONS: list[tuple[str, str]] = [
    (
        "kb_miss",
        "ALTER TABLE itineraries ADD COLUMN kb_miss INTEGER NOT NULL DEFAULT 0",
    ),
    (
        "is_favorite",
        "ALTER TABLE itineraries ADD COLUMN is_favorite INTEGER NOT NULL DEFAULT 0",
    ),
]


class SQLiteItineraryRepository(IItineraryRepository):

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._initialized = False

    async def _ensure_schema(self, db: aiosqlite.Connection) -> None:
        if not self._initialized:
            await db.execute(_CREATE_TABLE)
            await db.commit()
            # İleriye dönük migration: var olan tabloya eksik sütunları ekle.
            # Her migration yalnızca bir kez çalışır: önce PRAGMA table_info ile
            # sütun varlığı kontrol edilir; varsa ALTER TABLE sessizce atlanır.
            async with db.execute("PRAGMA table_info(itineraries)") as cur:
                existing = {row[1] async for row in cur}  # row[1] = sütun adı
            for col_name, alter_sql in _MIGRATIONS:
                if col_name not in existing:
                    await db.execute(alter_sql)
                    logger.info("DB migration: added column '%s'", col_name)
            await db.commit()
            self._initialized = True

    async def save(self, itinerary: Itinerary) -> str:
        if not itinerary.id:
            itinerary.id = str(uuid.uuid4())

        days_data = [
            {
                "day_number": d.day_number,
                "title": d.title,
                "morning": {
                    "description": d.morning.description, 
                    "location": d.morning.location,
                    "why_recommended": d.morning.why_recommended,
                    "duration_estimate": d.morning.duration_estimate,
                    "cost_estimate": d.morning.cost_estimate,
                    "reservation_needed": d.morning.reservation_needed,
                    "transport_suggestion": d.morning.transport_suggestion,
                },
                "afternoon": {
                    "description": d.afternoon.description, 
                    "location": d.afternoon.location,
                    "why_recommended": d.afternoon.why_recommended,
                    "duration_estimate": d.afternoon.duration_estimate,
                    "cost_estimate": d.afternoon.cost_estimate,
                    "reservation_needed": d.afternoon.reservation_needed,
                    "transport_suggestion": d.afternoon.transport_suggestion,
                },
                "evening": {
                    "description": d.evening.description, 
                    "location": d.evening.location,
                    "why_recommended": d.evening.why_recommended,
                    "duration_estimate": d.evening.duration_estimate,
                    "cost_estimate": d.evening.cost_estimate,
                    "reservation_needed": d.evening.reservation_needed,
                    "transport_suggestion": d.evening.transport_suggestion,
                },
                "meals": {"breakfast": d.meals.breakfast, "lunch": d.meals.lunch, "dinner": d.meals.dinner},
                "budget_estimate": d.budget_estimate.value,
                "tips": d.tips,
            }
            for d in itinerary.days
        ]

        async with aiosqlite.connect(self._db_path) as db:
            await self._ensure_schema(db)
            await db.execute(
                """
                INSERT OR REPLACE INTO itineraries
                    (id, destination, duration_days, budget, interests, notes,
                     model_used, created_at, day_count, days_json, raw_response,
                     kb_miss)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    itinerary.id,
                    itinerary.destination,
                    itinerary.duration_days,
                    itinerary.trip_request.budget.value,
                    json.dumps([i.value for i in itinerary.trip_request.interests]),
                    itinerary.trip_request.notes or "",
                    itinerary.model_used,
                    itinerary.created_at.isoformat(),
                    len(itinerary.days),
                    json.dumps(days_data, ensure_ascii=False),
                    itinerary.raw_response or "",
                    int(itinerary.kb_miss),
                ),
            )
            await db.commit()

        logger.info("Saved itinerary %s (%s)", itinerary.id, itinerary.destination)
        return itinerary.id

    async def get(self, itinerary_id: str) -> Itinerary | None:
        async with aiosqlite.connect(self._db_path) as db:
            await self._ensure_schema(db)
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM itineraries WHERE id = ?", (itinerary_id,)
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_itinerary(row)

    async def list_all(self, limit: int = 50) -> list[ItinerarySummary]:
        async with aiosqlite.connect(self._db_path) as db:
            await self._ensure_schema(db)
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT id, destination, duration_days, budget, model_used, created_at, day_count
                FROM itineraries
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()

        return [
            ItinerarySummary(
                id=row["id"],
                destination=row["destination"],
                duration_days=row["duration_days"],
                budget=BudgetLevel(row["budget"]),
                model_used=row["model_used"],
                created_at=datetime.fromisoformat(row["created_at"]),
                day_count=row["day_count"],
                is_favorite=bool(row["is_favorite"]) if "is_favorite" in row.keys() else False,
            )
            for row in rows
        ]

    async def delete(self, itinerary_id: str) -> bool:
        async with aiosqlite.connect(self._db_path) as db:
            await self._ensure_schema(db)
            cursor = await db.execute(
                "DELETE FROM itineraries WHERE id = ?", (itinerary_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def toggle_favorite(self, itinerary_id: str, is_favorite: bool) -> bool:
        """Sets the is_favorite flag for an itinerary."""
        async with aiosqlite.connect(self._db_path) as db:
            await self._ensure_schema(db)
            cursor = await db.execute(
                "UPDATE itineraries SET is_favorite = ? WHERE id = ?",
                (int(is_favorite), itinerary_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def update_day(self, itinerary_id: str, day: Day) -> bool:
        """Update a specific day's JSON within an itinerary."""
        async with aiosqlite.connect(self._db_path) as db:
            await self._ensure_schema(db)
            db.row_factory = aiosqlite.Row
            
            async with db.execute("SELECT days_json FROM itineraries WHERE id = ?", (itinerary_id,)) as cur:
                row = await cur.fetchone()
                if not row:
                    return False
                
            days_data = json.loads(row["days_json"])
            
            day_idx = -1
            for i, d in enumerate(days_data):
                if d["day_number"] == day.day_number:
                    day_idx = i
                    break
                    
            if day_idx == -1:
                return False
                
            days_data[day_idx] = {
                "day_number": day.day_number,
                "title": day.title,
                "morning": {
                    "description": day.morning.description, 
                    "location": day.morning.location,
                    "why_recommended": day.morning.why_recommended,
                    "duration_estimate": day.morning.duration_estimate,
                    "cost_estimate": day.morning.cost_estimate,
                    "reservation_needed": day.morning.reservation_needed,
                    "transport_suggestion": day.morning.transport_suggestion,
                    "lat": getattr(day.morning, "lat", None),
                    "lon": getattr(day.morning, "lon", None),
                },
                "afternoon": {
                    "description": day.afternoon.description, 
                    "location": day.afternoon.location,
                    "why_recommended": day.afternoon.why_recommended,
                    "duration_estimate": day.afternoon.duration_estimate,
                    "cost_estimate": day.afternoon.cost_estimate,
                    "reservation_needed": day.afternoon.reservation_needed,
                    "transport_suggestion": day.afternoon.transport_suggestion,
                    "lat": getattr(day.afternoon, "lat", None),
                    "lon": getattr(day.afternoon, "lon", None),
                },
                "evening": {
                    "description": day.evening.description, 
                    "location": day.evening.location,
                    "why_recommended": day.evening.why_recommended,
                    "duration_estimate": day.evening.duration_estimate,
                    "cost_estimate": day.evening.cost_estimate,
                    "reservation_needed": day.evening.reservation_needed,
                    "transport_suggestion": day.evening.transport_suggestion,
                    "lat": getattr(day.evening, "lat", None),
                    "lon": getattr(day.evening, "lon", None),
                },
                "meals": {
                    "breakfast": day.meals.breakfast,
                    "lunch": day.meals.lunch,
                    "dinner": day.meals.dinner,
                },
                "budget_estimate": day.budget_estimate.value,
                "tips": day.tips,
            }
            
            cursor = await db.execute(
                "UPDATE itineraries SET days_json = ? WHERE id = ?",
                (json.dumps(days_data, ensure_ascii=False), itinerary_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_destinations(self) -> list[dict]:
        async with aiosqlite.connect(self._db_path) as db:
            await self._ensure_schema(db)
            query = """
                SELECT destination, COUNT(*) AS trips, MAX(created_at) AS last_planned
                FROM itineraries 
                GROUP BY destination 
                ORDER BY last_planned DESC
            """
            async with db.execute(query) as cursor:
                rows = await cursor.fetchall()
                
            return [
                {
                    "destination": row[0],
                    "trips": row[1],
                    "last_planned": row[2],
                }
                for row in rows
            ]

    @staticmethod
    def _row_to_itinerary(row: aiosqlite.Row) -> Itinerary:
        interests = tuple(Interest(i) for i in json.loads(row["interests"]))
        trip_request = TripRequest(
            destination=row["destination"],
            duration_days=row["duration_days"],
            budget=BudgetLevel(row["budget"]),
            interests=interests,
            notes=row["notes"],
        )

        days_data: list[dict] = json.loads(row["days_json"])
        days = [
            Day(
                day_number=d["day_number"],
                title=d.get("title", ""),
                morning=ActivityBlock(
                    d["morning"]["description"], 
                    d["morning"].get("location", ""),
                    d["morning"].get("why_recommended", ""),
                    d["morning"].get("duration_estimate", ""),
                    d["morning"].get("cost_estimate", ""),
                    d["morning"].get("reservation_needed", False),
                    d["morning"].get("transport_suggestion", ""),
                    lat=d["morning"].get("lat"),
                    lon=d["morning"].get("lon")
                ),
                afternoon=ActivityBlock(
                    d["afternoon"]["description"], 
                    d["afternoon"].get("location", ""),
                    d["afternoon"].get("why_recommended", ""),
                    d["afternoon"].get("duration_estimate", ""),
                    d["afternoon"].get("cost_estimate", ""),
                    d["afternoon"].get("reservation_needed", False),
                    d["afternoon"].get("transport_suggestion", ""),
                    lat=d["afternoon"].get("lat"),
                    lon=d["afternoon"].get("lon")
                ),
                evening=ActivityBlock(
                    d["evening"]["description"], 
                    d["evening"].get("location", ""),
                    d["evening"].get("why_recommended", ""),
                    d["evening"].get("duration_estimate", ""),
                    d["evening"].get("cost_estimate", ""),
                    d["evening"].get("reservation_needed", False),
                    d["evening"].get("transport_suggestion", ""),
                    lat=d["evening"].get("lat"),
                    lon=d["evening"].get("lon")
                ),
                meals=MealSuggestion(
                    d["meals"].get("breakfast", ""),
                    d["meals"].get("lunch", ""),
                    d["meals"].get("dinner", ""),
                ),
                budget_estimate=BudgetLevel(d.get("budget_estimate", "medium")),
                tips=d.get("tips", []),
            )
            for d in days_data
        ]

        keys = row.keys()
        itinerary = Itinerary(
            trip_request=trip_request,
            days=days,
            model_used=row["model_used"],
            created_at=datetime.fromisoformat(row["created_at"]),
            raw_response=row["raw_response"] if "raw_response" in keys else "",
            kb_miss=bool(row["kb_miss"]) if "kb_miss" in keys else False,
            is_favorite=bool(row["is_favorite"]) if "is_favorite" in keys else False,
            constraint_score=float(row["constraint_score"]) if "constraint_score" in keys else 1.0,
            quality_score=float(row["quality_score"]) if "quality_score" in keys else 1.0,
        )
        itinerary.id = row["id"]
        return itinerary
