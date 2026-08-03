"""
Infrastructure: FoundryEmbeddingAdapter

IEmbeddingClient'ı Foundry Local'in OpenAI-uyumlu /embeddings ucuyla uygular.
(Foundry Local SDK'sını KULLANMAZ — standart openai istemcisiyle konuşur.)

DURUM: Kullanılmıyor. Foundry Local kataloğunda embedding modeli yok;
container LocalEmbeddingAdapter'ı bağlıyor. Foundry ileride embedding
sunarsa diye duruyor.
"""

from __future__ import annotations

import logging

from openai import AsyncOpenAI

from backend.application.ports.embedding_port import IEmbeddingClient

logger = logging.getLogger(__name__)


class FoundryEmbeddingAdapter(IEmbeddingClient):
    """
    Embedding adapter that calls the Foundry Local OpenAI-compatible API.
    """

    def __init__(
        self,
        base_url: str,
        model_id: str = "qwen3-embedding-0.6b",
        api_key: str = "foundry"
    ) -> None:
        self._model_id = model_id
        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=60.0,
            max_retries=1,
        )

    @property
    def model_name(self) -> str:
        return self._model_id

    async def embed(self, text: str) -> list[float]:
        """Generate a vector embedding for the given text."""
        response = await self._client.embeddings.create(
            input=text,
            model=self._model_id,
        )
        return response.data[0].embedding

    async def health_check(self) -> bool:
        try:
            # A simple call to verify it's up
            await self._client.models.list()
            return True
        except Exception:
            return False
