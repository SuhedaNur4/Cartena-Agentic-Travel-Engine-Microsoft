"""API sözleşme testleri — domain'deki veri gerçekten dışarı çıkıyor mu?"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from backend.api.v1.routers import itineraries as itineraries_router
from backend.application.use_cases.export_itinerary import ExportItineraryUseCase
from backend.application.use_cases.get_itinerary import GetItineraryUseCase
from backend.application.use_cases.list_itineraries import ListItinerariesUseCase
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


def make_itinerary() -> Itinerary:
    return Itinerary(
        trip_request=TripRequest(
            destinations=("Tokyo",),
            duration_days=1,
            budget=BudgetLevel.MEDIUM,
            interests=(Interest.CULTURE,),
        ),
        days=[
            Day(
                day_number=1,
                title="Arrival",
                morning=ActivityBlock(
                    description="Visit Senso-ji",
                    location="Asakusa",
                    why_recommended="Quietest at dawn",
                    duration_estimate="2 hours",
                    cost_estimate="$0",
                    reservation_needed=True,
                    transport_suggestion="10 min walk",
                ),
                afternoon=ActivityBlock("Ueno Park", "Ueno"),
                evening=ActivityBlock("Izakaya", "Shinjuku"),
                meals=MealSuggestion("Onigiri", "Ramen", "Yakitori"),
                budget_estimate=BudgetLevel.MEDIUM,
                tips=["Suica card", "Carry cash"],
            )
        ],
        model_used="fake-model",
    )


@pytest.fixture
async def client(tmp_path):
    repo = SQLiteItineraryRepository(db_path=str(tmp_path / "api.db"))
    itinerary_id = await repo.save(make_itinerary())

    app = FastAPI()
    app.include_router(itineraries_router.router, prefix="/api/v1")
    app.dependency_overrides[itineraries_router.get_get_use_case] = (
        lambda: GetItineraryUseCase(repo)
    )
    app.dependency_overrides[itineraries_router.get_list_use_case] = (
        lambda: ListItinerariesUseCase(repo)
    )
    app.dependency_overrides[itineraries_router.get_export_use_case] = (
        lambda: ExportItineraryUseCase(repo)
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.itinerary_id = itinerary_id
        yield c


class TestItineraryDetail:
    async def test_get_returns_200(self, client):
        """B1 düzeltilmeden bu 500 dönüyordu."""
        res = await client.get(f"/api/v1/itineraries/{client.itinerary_id}")
        assert res.status_code == 200

    async def test_response_carries_all_seven_activity_fields(self, client):
        """Veri SQLite'ta var; API sınırını geçmiyordu."""
        res = await client.get(f"/api/v1/itineraries/{client.itinerary_id}")
        morning = res.json()["days"][0]["morning"]

        assert morning["description"] == "Visit Senso-ji"
        assert morning["location"] == "Asakusa"
        assert morning["why_recommended"] == "Quietest at dawn"
        assert morning["duration_estimate"] == "2 hours"
        assert morning["cost_estimate"] == "$0"
        assert morning["reservation_needed"] is True
        assert morning["transport_suggestion"] == "10 min walk"

    async def test_export_json_carries_all_seven_fields(self, client):
        res = await client.get(
            f"/api/v1/itineraries/{client.itinerary_id}/export", params={"fmt": "json"}
        )
        assert res.status_code == 200
        morning = res.json()["days"][0]["morning"]
        assert morning["why_recommended"] == "Quietest at dawn"
        assert morning["cost_estimate"] == "$0"
        assert morning["transport_suggestion"] == "10 min walk"
        assert morning["reservation_needed"] is True

    async def test_missing_itinerary_returns_404(self, client):
        res = await client.get("/api/v1/itineraries/yok-boyle")
        assert res.status_code == 404
