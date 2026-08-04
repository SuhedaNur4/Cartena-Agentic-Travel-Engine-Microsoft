"""FoundryLLMAdapter üretim parametreleri."""

from backend.infrastructure.llm.foundry_llm_adapter import FoundryLLMAdapter


def make_adapter() -> FoundryLLMAdapter:
    return FoundryLLMAdapter(base_url="http://localhost:1/v1", model="phi-4-mini")


class TestGenerationParams:
    def test_temperature_is_low_for_structured_output(self):
        """0.7 katı JSON için yüksek: model şemadan sapıyor."""
        assert make_adapter().temperature <= 0.2

    def test_token_budget_scales_with_day_count(self):
        adapter = make_adapter()
        assert adapter.token_budget(13) > adapter.token_budget(3)

    def test_token_budget_has_a_floor_for_short_trips(self):
        adapter = make_adapter()
        assert adapter.token_budget(1) >= 2048

    def test_thirteen_day_trip_gets_more_than_the_old_fixed_budget(self):
        """Eski sabit 4096, 13 günlük planı kesiyordu."""
        assert make_adapter().token_budget(13) > 4096

    def test_unknown_day_count_falls_back_to_floor(self):
        assert make_adapter().token_budget(None) >= 2048
