from __future__ import annotations

import asyncio
import logging

from backend.application.ports.embedding_port import IEmbeddingClient

logger = logging.getLogger(__name__)


class LocalEmbeddingAdapter(IEmbeddingClient):
    """
    Embedding adapter that uses sentence-transformers running locally.
    Used as a fallback because Foundry Local currently does not package
    a native embedding model via the OpenAI compatible endpoint.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model = None
        self._lock = asyncio.Lock()

    @property
    def model_name(self) -> str:
        return self._model_name

    async def _get_model(self):
        if self._model is not None:
            return self._model

        async with self._lock:
            if self._model is not None:
                return self._model

            logger.info("Loading sentence-transformers model: %s", self._model_name)
            loop = asyncio.get_event_loop()
            
            def _load():
                from sentence_transformers import SentenceTransformer
                return SentenceTransformer(self._model_name)
                
            self._model = await loop.run_in_executor(None, _load)
            logger.info("Sentence-transformers model loaded.")
            return self._model

    async def embed(self, text: str) -> list[float]:
        """Generate a vector embedding for the given text."""
        model = await self._get_model()
        loop = asyncio.get_event_loop()

        def _embed_sync() -> list[float]:
            # encode returns a numpy array, convert to list of floats
            embedding = model.encode(text)
            return embedding.tolist()

        return await loop.run_in_executor(None, _embed_sync)

    async def health_check(self) -> bool:
        try:
            await self._get_model()
            return True
        except Exception:
            return False
