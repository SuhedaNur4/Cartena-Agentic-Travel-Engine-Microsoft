"""
Infrastructure: OllamaLLMAdapter

Implements ILLMClient using the OpenAI-compatible client pointed at
the local Ollama API endpoint. Uses streaming completion for token-by-token
response delivery via SSE.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from openai import AsyncOpenAI

from backend.application.ports.llm_port import ILLMClient

logger = logging.getLogger(__name__)


class OllamaLLMAdapter(ILLMClient):
    """
    Ollama's OpenAI-compatible API wrapper.
    
    Configuration:
        base_url: Ollama API URL (e.g., http://localhost:11434/v1)
        model:    e.g., "phi4-mini:latest"
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        temperature: float = 0.2,
        max_tokens_per_day: int = 350,
        max_tokens_floor: int = 1024,
    ) -> None:
        self._model = model
        self.temperature = temperature
        self._max_tokens_per_day = max_tokens_per_day
        self._max_tokens_floor = max_tokens_floor
        
        # Ollama's OpenAI compatibility layer uses /v1
        if not base_url.endswith("/v1") and not base_url.endswith("/v1/"):
            base_url = f"{base_url.rstrip('/')}/v1"
            
        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key="ollama", # dummy key required by openai client
            timeout=300.0,
            max_retries=1,
        )

    @property
    def model_name(self) -> str:
        return self._model

    def token_budget(self, expected_days: int | None) -> int:
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
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ]

        max_tokens = self.token_budget(expected_days)
        logger.debug(
            "Starting Ollama LLM stream: model=%s temp=%s max_tokens=%d",
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
            logger.warning("Ollama closed connection unexpectedly (%s).", e)

    async def health_check(self) -> bool:
        """Verify Ollama is running by listing available models."""
        try:
            models = await self._client.models.list()
            return len(models.data) > 0
        except Exception:
            return False
