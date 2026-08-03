"""
Infrastructure: FoundryLLMAdapter

Implements ILLMClient using the OpenAI-compatible client pointed at
the Foundry Local API endpoint. Uses streaming completion for token-by-token
response delivery via SSE.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from openai import AsyncOpenAI

from backend.application.ports.llm_port import ILLMClient

logger = logging.getLogger(__name__)


class FoundryLLMAdapter(ILLMClient):
    """
    Foundry Local'in OpenAI-uyumlu API'sini kullanan LLM adapter'ı.

    Yapılandırma:
        base_url: Foundry Local servis URL'i (port DİNAMİKTİR —
                  `foundry service status` ile öğrenilir)
        api_key:  Foundry Local geleneği gereği "foundry"
        model:    örn. "phi-4-mini" (chat+tools destekli)

    Model notu: `tools` yeteneği olmayan modeller (örn. mistral-7b-v0.2)
    structured output yapamaz ve bu şemayı güvenilir üretemez.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "foundry",
        temperature: float = 0.2,
        max_tokens_per_day: int = 350,
        max_tokens_floor: int = 1024,
    ) -> None:
        self._model = model
        self.temperature = temperature
        self._max_tokens_per_day = max_tokens_per_day
        self._max_tokens_floor = max_tokens_floor
        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=300.0,   # yerel çıkarım yavaştır; uzun planlar dakikalar sürer
            max_retries=1,
        )

    @property
    def model_name(self) -> str:
        return self._model

    def token_budget(self, expected_days: int | None) -> int:
        """
        Gün sayısına göre token bütçesi.

        Sabit 4096 uzun planları kesiyordu: her gün 3 aktivite x 7 alan +
        3 öğün + 2 ipucu üretiyor. Kesik JSON parse edilemez.
        """
        if not expected_days:
            return self._max_tokens_floor
        return max(self._max_tokens_floor, expected_days * self._max_tokens_per_day)

    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        expected_days: int | None = None,
        json_schema: dict | None = None,
    ) -> AsyncIterator[str]:
        """Foundry Local'den token akışı."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ]

        max_tokens = self.token_budget(expected_days)
        logger.debug(
            "Starting LLM stream: model=%s temp=%s max_tokens=%d",
            self._model, self.temperature, max_tokens,
        )

        kwargs = {
            "model": self._model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        import httpx

        try:
            response = await self._client.chat.completions.create(**kwargs)
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except (httpx.RemoteProtocolError, httpx.ReadError) as e:
            logger.warning("Foundry Local closed connection unexpectedly (%s).", e)

    async def health_check(self) -> bool:
        """Verify Foundry Local is running by listing available models."""
        try:
            models = await self._client.models.list()
            return len(models.data) > 0
        except Exception:
            return False
