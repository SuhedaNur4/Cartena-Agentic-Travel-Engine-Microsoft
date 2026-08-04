"""Unit tests for PromptBuilder — pure function, no mocks needed."""

import pytest

from backend.domain.models.trip_request import BudgetLevel, Interest, TripRequest
from backend.domain.services.prompt_builder import build


@pytest.fixture
def basic_request() -> TripRequest:
    return TripRequest(
        destination="Tokyo",
        duration_days=5,
        budget=BudgetLevel.MEDIUM,
        interests=(Interest.CULTURE, Interest.FOOD),
        notes="Traveling alone",
    )


def test_build_returns_two_strings(basic_request):
    system_prompt, user_prompt = build(basic_request, rag_chunks=[], online_context=None)
    assert isinstance(system_prompt, str)
    assert isinstance(user_prompt, str)
    assert len(system_prompt) > 100
    assert len(user_prompt) > 50


def test_destination_in_user_prompt(basic_request):
    _, user_prompt = build(basic_request, rag_chunks=[])
    assert "Tokyo" in user_prompt


def test_duration_in_user_prompt(basic_request):
    _, user_prompt = build(basic_request, rag_chunks=[])
    assert "5" in user_prompt


def test_rag_chunks_injected(basic_request):
    chunks = ["Shinjuku is Tokyo's entertainment hub.", "Shibuya Crossing is iconic."]
    _, user_prompt = build(basic_request, rag_chunks=chunks)
    assert "Shinjuku" in user_prompt
    assert "Shibuya" in user_prompt


def test_no_rag_chunks_fallback_message(basic_request):
    _, user_prompt = build(basic_request, rag_chunks=[])
    assert "No specific local knowledge" in user_prompt


def test_online_context_injected(basic_request):
    online = ["Current weather: 22°C, partly cloudy"]
    _, user_prompt = build(basic_request, rag_chunks=[], online_context=online)
    assert "22°C" in user_prompt


def test_system_prompt_requests_json(basic_request):
    system_prompt, _ = build(basic_request, rag_chunks=[])
    assert "JSON" in system_prompt
    assert "days" in system_prompt


def test_notes_in_user_prompt(basic_request):
    _, user_prompt = build(basic_request, rag_chunks=[])
    assert "Traveling alone" in user_prompt


class TestOffTopicChunks:
    """
    KB miss'te başka şehirlerin chunk'ları çekiliyor. Prompt bunları
    hedef şehir hakkında GERÇEK diye sunmamalı.
    """

    def test_off_topic_chunks_are_not_claimed_as_destination_facts(self):
        from backend.domain.services.prompt_builder import build

        request = TripRequest(
            destination="Tokyo",
            duration_days=2,
            budget=BudgetLevel.MEDIUM,
            interests=(Interest.CULTURE,),
        )
        _, user_prompt = build(
            request=request,
            rag_chunks=["The Eiffel Tower is best at dusk."],
            chunks_are_off_topic=True,
        )

        # "Tokyo hakkında gerçekler" iddiası olmamalı
        assert "facts about Tokyo were retrieved" not in user_prompt
        # ve modele bunların hedef şehre ait OLMADIĞI söylenmeli
        assert "NOT about Tokyo" in user_prompt

    def test_on_topic_chunks_are_still_presented_as_destination_facts(self):
        from backend.domain.services.prompt_builder import build

        request = TripRequest(
            destination="Tokyo",
            duration_days=2,
            budget=BudgetLevel.MEDIUM,
            interests=(Interest.CULTURE,),
        )
        _, user_prompt = build(
            request=request,
            rag_chunks=["Senso-ji opens at dawn."],
            chunks_are_off_topic=False,
        )
        assert "facts about Tokyo were retrieved" in user_prompt
        assert "NOT about Tokyo" not in user_prompt

    def test_no_chunks_claims_neither_retrieval_nor_off_topic(self, basic_request):
        """
        Üçüncü durum: hiç chunk yok. Önceki hâl _ON_TOPIC_HEADER seçip
        "şu gerçekler getirildi" diyor, hemen ardından hiçbir şey koymuyordu.
        """
        from backend.domain.services.prompt_builder import build

        _, user_prompt = build(basic_request, rag_chunks=[])
        assert "facts about Tokyo were retrieved" not in user_prompt
        assert "NOT about Tokyo" not in user_prompt
        assert "No specific local knowledge" in user_prompt


class TestLiveContext:
    """
    `online_context` bugün kabul edilip sessizce yok sayılıyor —
    test_online_context_injected bu yüzden tabanda kırmızı.
    """

    def test_online_context_block_absent_when_empty(self, basic_request):
        from backend.domain.services.prompt_builder import build

        _, user_prompt = build(basic_request, rag_chunks=[], online_context=[])
        assert "[LIVE CONTEXT]" not in user_prompt

    def test_online_context_block_absent_when_none(self, basic_request):
        from backend.domain.services.prompt_builder import build

        _, user_prompt = build(basic_request, rag_chunks=[], online_context=None)
        assert "[LIVE CONTEXT]" not in user_prompt

    def test_multiple_online_items_all_appear(self, basic_request):
        from backend.domain.services.prompt_builder import build

        _, user_prompt = build(
            basic_request,
            rag_chunks=[],
            online_context=["Weather: 22°C", "Museum closed Mondays"],
        )
        assert "[LIVE CONTEXT]" in user_prompt
        assert "22°C" in user_prompt
        assert "Museum closed Mondays" in user_prompt
