"""Test sahtesi: ILLMClient — gerçek LLM olmadan deterministik akış."""

from __future__ import annotations

from typing import AsyncIterator

from backend.application.ports.llm_port import ILLMClient


class FakeLLMClient(ILLMClient):
    """Verilen metni token token yayar. Çağrı argümanlarını kaydeder."""

    def __init__(self, response: str, model_name: str = "fake-model") -> None:
        self._response = response
        self._model_name = model_name
        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None
        self.last_expected_days: int | None = None
        self.call_count = 0

    @property
    def model_name(self) -> str:
        return self._model_name

    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        expected_days: int | None = None,
        json_schema: dict | None = None,
    ) -> AsyncIterator[str]:
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        self.last_expected_days = expected_days
        self.last_json_schema = json_schema
        self.call_count += 1
        # 40 karakterlik parçalar hâlinde yay — gerçek token akışını taklit eder
        for i in range(0, len(self._response), 40):
            yield self._response[i:i + 40]

    async def health_check(self) -> bool:
        return True
