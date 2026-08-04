"""Test sahtesi: IEmbeddingClient — torch/sentence-transformers olmadan."""

from __future__ import annotations

from backend.application.ports.embedding_port import IEmbeddingClient


class FakeEmbeddingClient(IEmbeddingClient):
    """Deterministik sahte vektör. Benzerlik anlamı yok; sadece pipeline'ı besler."""

    def __init__(self, model_name: str = "fake-embedding") -> None:
        self._model_name = model_name
        self.embed_calls: list[str] = []

    @property
    def model_name(self) -> str:
        return self._model_name

    async def embed(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        return [float(len(text) % 7), 0.5, 0.25]

    async def health_check(self) -> bool:
        return True
