"""SQLiteItineraryRepository round-trip testleri."""

import aiosqlite
import pytest

from backend.domain.models.itinerary import (
    ActivityBlock,
    Day,
    Itinerary,
    MealSuggestion,
)
from backend.domain.models.trip_request import BudgetLevel, Interest, TripRequest
from backend.infrastructure.persistence.sqlite_itinerary_repo import (
    SQLiteItineraryRepository,
)


@pytest.fixture
def repo(tmp_path) -> SQLiteItineraryRepository:
    return SQLiteItineraryRepository(db_path=str(tmp_path / "test.db"))


def make_itinerary(kb_miss: bool = False) -> Itinerary:
    it = Itinerary(
        trip_request=TripRequest(
            destinations=("Tokyo",),
            duration_days=1,
            budget=BudgetLevel.MEDIUM,
            interests=(Interest.CULTURE, Interest.FOOD),
            notes="vegan",
            allocation_mode="USER",
            allocations={"Tokyo": 1},
        ),
        days=[
            Day(
                day_number=1,
                title="Arrival",
                morning=ActivityBlock(
                    "Visit Senso-ji", "Asakusa", "Quietest at dawn",
                    "2 hours", "$0", False, "10 min walk",
                ),
                afternoon=ActivityBlock("Ueno Park", "Ueno"),
                evening=ActivityBlock("Izakaya crawl", "Shinjuku"),
                meals=MealSuggestion("Onigiri", "Ramen", "Yakitori"),
                budget_estimate=BudgetLevel.MEDIUM,
                tips=["Get a Suica card", "Carry cash"],
            )
        ],
        model_used="fake-model",
        raw_response="RAW-RESPONSE-MARKER",
        kb_miss=kb_miss,
    )
    return it


class TestRoundTrip:
    async def test_save_then_get_returns_itinerary(self, repo):
        """Bugün AttributeError atıyor: sqlite3.Row'un .get() metodu yok."""
        saved_id = await repo.save(make_itinerary())
        loaded = await repo.get(saved_id)

        assert loaded is not None
        assert loaded.id == saved_id
        assert loaded.destinations == ("Tokyo",)
        assert loaded.raw_response == "RAW-RESPONSE-MARKER"

    async def test_get_missing_returns_none(self, repo):
        assert await repo.get("yok-boyle-bir-id") is None

    async def test_list_all_returns_summary(self, repo):
        await repo.save(make_itinerary())
        summaries = await repo.list_all()
        assert len(summaries) == 1
        assert summaries[0].destination == "Tokyo"
        assert summaries[0].day_count == 1

    async def test_kb_miss_false_persists_and_loads(self, repo):
        """kb_miss=False kaydedilip doğru okunmalı."""
        saved_id = await repo.save(make_itinerary(kb_miss=False))
        loaded = await repo.get(saved_id)
        assert loaded is not None
        assert loaded.kb_miss is False

    async def test_kb_miss_true_persists_and_loads(self, repo):
        """kb_miss=True (genel LLM bilgisi kullanıldı) doğru okunmalı."""
        saved_id = await repo.save(make_itinerary(kb_miss=True))
        loaded = await repo.get(saved_id)
        assert loaded is not None
        assert loaded.kb_miss is True


class TestMigration:
    async def test_migration_adds_kb_miss_to_old_db(self, tmp_path):
        """
        Eski DB'de (kb_miss sütunu olmadan) _ensure_schema çağrıldığında
        sütunun eklenmesi gerekir. CREATE TABLE IF NOT EXISTS bunu yapmaz;
        migration mekanizması yapar.
        """
        db_path = str(tmp_path / "old.db")

        # Eski şemayı (kb_miss sütunu yok) oluştur
        async with aiosqlite.connect(db_path) as db:
            await db.execute("""
                CREATE TABLE itineraries (
                    id TEXT PRIMARY KEY,
                    destination TEXT NOT NULL,
                    duration_days INTEGER NOT NULL,
                    budget TEXT NOT NULL,
                    interests TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    model_used TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    day_count INTEGER NOT NULL,
                    days_json TEXT NOT NULL,
                    raw_response TEXT NOT NULL DEFAULT ''
                )
            """)
            await db.commit()

        # Yeni repo bu DB'yi açmalı ve migration yapmalı
        repo = SQLiteItineraryRepository(db_path=db_path)
        saved_id = await repo.save(make_itinerary(kb_miss=True))
        loaded = await repo.get(saved_id)

        assert loaded is not None
        assert loaded.kb_miss is True
        assert loaded.trip_request.allocation_mode == "USER"
        assert loaded.trip_request.allocations == {"Tokyo": 1}
        assert loaded.destinations == ("Tokyo",)

