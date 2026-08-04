"""GenerateItineraryUseCase testleri — pipeline'ın kalbi, şu ana dek testsizdi."""

import pathlib

import pytest

from backend.application.use_cases.generate_itinerary import GenerateItineraryUseCase
from backend.domain.models.knowledge_chunk import KnowledgeChunk
from backend.domain.models.trip_request import BudgetLevel, Interest, TripRequest
from tests.fakes.embedding import FakeEmbeddingClient
from tests.fakes.llm import FakeLLMClient
from tests.fakes.vector_store import FakeVectorStore

FIXTURE = pathlib.Path(__file__).parents[2] / "fixtures" / "qwen3_schema_echo.txt"


class RecordingRepo:
    """IItineraryRepository sahtesi — neyin kaydedildiğini görmek için."""

    def __init__(self) -> None:
        self.saved: list = []

    async def save(self, itinerary) -> str:
        self.saved.append(itinerary)
        return "test-id-1"

    async def get(self, itinerary_id: str):
        return None

    async def list_all(self, limit: int = 50):
        return []

    async def delete(self, itinerary_id: str) -> bool:
        return False


def make_request(destination="Tokyo", days=3) -> TripRequest:
    return TripRequest(
        destination=destination,
        duration_days=days,
        budget=BudgetLevel.MEDIUM,
        interests=(Interest.CULTURE,),
    )


async def collect(use_case, request) -> list[dict]:
    return [event async for event in await use_case.execute(request)]


@pytest.fixture
def qwen3_broken_response() -> str:
    """Gerçek qwen3-0.6b çıktısı: şema üretmek yerine şemayı geri kopyalamış."""
    return FIXTURE.read_text(encoding="utf-8")


class TestParseFailureIsNotSaved:
    """
    Task 0'daki karakterizasyon testinin yerini alır.
    Eski davranış: bozuk çıktı 1 günlük 'plan' olarak kaydediliyordu.
    """

    async def test_broken_llm_output_is_not_saved(self, qwen3_broken_response):
        repo = RecordingRepo()
        use_case = GenerateItineraryUseCase(
            llm_client=FakeLLMClient(qwen3_broken_response),
            embedding_client=FakeEmbeddingClient(),
            vector_store=FakeVectorStore([]),
            itinerary_repo=repo,
        )
        events = await collect(use_case, make_request(days=13))

        assert repo.saved == [], "ayrıştırılamayan çıktı kaydedilmemeli"
        assert [e for e in events if e["type"] == "done"] == []

        errors = [e for e in events if e["type"] == "error"]
        assert len(errors) == 1
        assert "13" in errors[0]["message"]

    async def test_partial_but_well_formed_regex_parse_is_not_saved(self):
        """
        Deliberate trade-off, not an oversight: `is_complete()` demands exact
        day-count equality, so a partial-but-well-formed parse is discarded
        just like garbage is — even though the regex fallback strategy
        (`_try_regex_parse`) can legitimately extract real, well-formed days
        (real titles, real Morning/Afternoon/Evening sections) when only a
        later day's markup is malformed.

        The product decision (kept as-is on review): saving a partial
        itinerary is only honest if the UI can tell the user "incomplete —
        regenerate day N", and that "regenerate a single day" UI does not
        exist yet (separate, not-yet-built work). Until it does, a 2-of-5-day
        result must be rejected exactly like unparseable noise — anything
        else would let a partial plan masquerade as a completed trip in
        history.

        This text has no JSON braces at all, so `_try_json_parse` returns
        None outright and parsing falls through to `_try_regex_parse`, which
        extracts 2 real days from "Day 1:"/"Day 2:" markers — confirmed by
        running `itinerary_parser.parse()` directly on this exact input
        before writing this assertion.
        """
        partial_text = (
            "Day 1: Arrival and Exploration\n"
            "Morning: Arrive at the airport and check into the hotel.\n"
            "Afternoon: Walk around the old town and visit the main square.\n"
            "Evening: Enjoy a welcome dinner at a local restaurant.\n"
            "\n"
            "Day 2: Museums and Culture\n"
            "Morning: Visit the national museum.\n"
            "Afternoon: Explore the art gallery district.\n"
            "Evening: Attend a local music performance.\n"
        )
        repo = RecordingRepo()
        use_case = GenerateItineraryUseCase(
            llm_client=FakeLLMClient(partial_text),
            embedding_client=FakeEmbeddingClient(),
            vector_store=FakeVectorStore([]),
            itinerary_repo=repo,
        )
        events = await collect(use_case, make_request(days=5))

        assert repo.saved == [], (
            "2 well-formed days out of 5 requested must not be saved — "
            "saving partials requires the not-yet-built 'regenerate a "
            "single day' UI"
        )
        assert [e for e in events if e["type"] == "done"] == []

        errors = [e for e in events if e["type"] == "error"]
        assert len(errors) == 1
        assert "2" in errors[0]["message"]
        assert "5" in errors[0]["message"]

    async def test_valid_output_is_saved(self):
        import json

        valid = json.dumps({
            "days": [
                {
                    "day_number": i + 1,
                    "title": f"Day {i + 1}",
                    "morning": {"description": "A", "location": "L"},
                    "afternoon": {"description": "B", "location": "L"},
                    "evening": {"description": "C", "location": "L"},
                    "meals": {"breakfast": "x", "lunch": "y", "dinner": "z"},
                    "budget_estimate": "medium",
                    "tips": ["t1", "t2"],
                }
                for i in range(3)
            ]
        })
        repo = RecordingRepo()
        use_case = GenerateItineraryUseCase(
            llm_client=FakeLLMClient(valid),
            embedding_client=FakeEmbeddingClient(),
            vector_store=FakeVectorStore([]),
            itinerary_repo=repo,
        )
        events = await collect(use_case, make_request(days=3))

        assert len(repo.saved) == 1
        done = [e for e in events if e["type"] == "done"]
        assert len(done) == 1
        assert done[0]["day_count"] == 3
        assert done[0]["is_complete"] is True

    async def test_kb_miss_is_propagated_to_saved_itinerary(self):
        """KB boşsa itinerary.kb_miss=True olarak kaydedilmeli."""
        import json

        valid = json.dumps({
            "days": [{
                "day_number": 1, "title": "Day 1",
                "morning": {"description": "A", "location": "L"},
                "afternoon": {"description": "B", "location": "L"},
                "evening": {"description": "C", "location": "L"},
                "meals": {"breakfast": "x", "lunch": "y", "dinner": "z"},
                "budget_estimate": "medium", "tips": [],
            }]
        })
        repo = RecordingRepo()
        # FakeVectorStore([]) → KB boş → kb_miss=True
        use_case = GenerateItineraryUseCase(
            llm_client=FakeLLMClient(valid),
            embedding_client=FakeEmbeddingClient(),
            vector_store=FakeVectorStore([]),
            itinerary_repo=repo,
        )
        await collect(use_case, make_request(days=1))

        assert len(repo.saved) == 1
        assert repo.saved[0].kb_miss is True, (
            "KB boşken üretilen plan kb_miss=True ile kaydedilmeli"
        )

    async def test_kb_hit_sets_kb_miss_false(self):
        """KB chunk bulunursa itinerary.kb_miss=False olarak kaydedilmeli."""
        import json

        valid = json.dumps({
            "days": [{
                "day_number": 1, "title": "Day 1",
                "morning": {"description": "A", "location": "L"},
                "afternoon": {"description": "B", "location": "L"},
                "evening": {"description": "C", "location": "L"},
                "meals": {"breakfast": "x", "lunch": "y", "dinner": "z"},
                "budget_estimate": "medium", "tips": [],
            }]
        })
        repo = RecordingRepo()
        store = FakeVectorStore([kb_chunk("Tokyo", "Senso-ji opens at dawn.")])
        use_case = GenerateItineraryUseCase(
            llm_client=FakeLLMClient(valid),
            embedding_client=FakeEmbeddingClient(),
            vector_store=store,
            itinerary_repo=repo,
        )
        await collect(use_case, make_request(destination="Tokyo", days=1))

        assert len(repo.saved) == 1
        assert repo.saved[0].kb_miss is False, (
            "KB chunk varken üretilen plan kb_miss=False ile kaydedilmeli"
        )


def kb_chunk(city: str, content: str, idx: int = 0) -> KnowledgeChunk:
    return KnowledgeChunk(
        id=f"{city.lower()}_landmarks_{idx}",
        city=city,
        category="landmarks",
        content=content,
    )


class TestCityNormalization:
    @pytest.mark.parametrize("typed", ["Tokyo", "tokyo", "TOKYO", "  tokyo  "])
    async def test_kb_found_regardless_of_casing(self, typed):
        store = FakeVectorStore([kb_chunk("Tokyo", "Senso-ji opens at dawn.")])
        use_case = GenerateItineraryUseCase(
            llm_client=FakeLLMClient("{}"),
            embedding_client=FakeEmbeddingClient(),
            vector_store=store,
            itinerary_repo=RecordingRepo(),
        )
        events = await collect(use_case, make_request(destination=typed))

        context = [e for e in events if e["type"] == "context"][0]
        assert context["kb_miss"] is False
        assert context["kb_chunks"] == 1
        assert store.last_city == "tokyo"

    async def test_turkish_dotted_i_finds_istanbul(self):
        store = FakeVectorStore([kb_chunk("Istanbul", "Hagia Sophia is free on Mondays.")])
        use_case = GenerateItineraryUseCase(
            llm_client=FakeLLMClient("{}"),
            embedding_client=FakeEmbeddingClient(),
            vector_store=store,
            itinerary_repo=RecordingRepo(),
        )
        events = await collect(use_case, make_request(destination="İstanbul"))

        assert [e for e in events if e["type"] == "context"][0]["kb_miss"] is False


class TestPoisonedFallback:
    async def test_other_city_chunks_are_flagged_off_topic_in_prompt(self):
        """Tokyo yok; Paris chunk'ı geliyor. Prompt onu Tokyo gerçeği sanmamalı."""
        store = FakeVectorStore([kb_chunk("Paris", "The Eiffel Tower is best at dusk.")])
        llm = FakeLLMClient("{}")
        use_case = GenerateItineraryUseCase(
            llm_client=llm,
            embedding_client=FakeEmbeddingClient(),
            vector_store=store,
            itinerary_repo=RecordingRepo(),
        )
        events = await collect(use_case, make_request(destination="Tokyo"))

        assert [e for e in events if e["type"] == "context"][0]["kb_miss"] is True
        assert "facts about Tokyo were retrieved" not in llm.last_user_prompt
        assert "NOT about Tokyo" in llm.last_user_prompt


class TestRetrievalOrder:
    async def test_chunk_order_is_preserved_in_prompt(self):
        """Alaka sırası tek sinyal; set() onu bozuyordu."""
        ordered = [
            kb_chunk("Tokyo", "RANK1 most relevant", 0),
            kb_chunk("Tokyo", "RANK2", 1),
            kb_chunk("Tokyo", "RANK3", 2),
            kb_chunk("Tokyo", "RANK4", 3),
            kb_chunk("Tokyo", "RANK5 least relevant", 4),
        ]
        llm = FakeLLMClient("{}")
        use_case = GenerateItineraryUseCase(
            llm_client=llm,
            embedding_client=FakeEmbeddingClient(),
            vector_store=FakeVectorStore(ordered),
            itinerary_repo=RecordingRepo(),
        )
        await collect(use_case, make_request(destination="Tokyo"))

        prompt = llm.last_user_prompt
        positions = [prompt.index(f"RANK{i}") for i in range(1, 6)]
        assert positions == sorted(positions), "chunk sırası bozuldu"

    async def test_duplicate_chunks_are_removed_keeping_first_occurrence(self):
        dupes = [
            kb_chunk("Tokyo", "FIRST", 0),
            kb_chunk("Tokyo", "SECOND", 1),
            kb_chunk("Tokyo", "FIRST", 2),
        ]
        llm = FakeLLMClient("{}")
        use_case = GenerateItineraryUseCase(
            llm_client=llm,
            embedding_client=FakeEmbeddingClient(),
            vector_store=FakeVectorStore(dupes),
            itinerary_repo=RecordingRepo(),
        )
        events = await collect(use_case, make_request(destination="Tokyo"))

        assert [e for e in events if e["type"] == "context"][0]["kb_chunks"] == 2
        assert llm.last_user_prompt.count("FIRST") == 1
        assert llm.last_user_prompt.index("FIRST") < llm.last_user_prompt.index("SECOND")
