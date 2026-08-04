"""
Infrastructure: OllamaEmbeddingAdapter

IEmbeddingClient implementation that delegates embedding generation
to a locally running Ollama instance via its REST API.

Target model  : nomic-embed-text  (768-dim, nomic-bert architecture)
Target endpoint: http://localhost:11434/api/embeddings

Design decisions
----------------
- Uses httpx.AsyncClient for async-native HTTP — no blocking calls.
- Stateless: no connection pooling state is kept between requests.
  Each `embed()` call opens a short-lived connection (fine for a local
  Ollama which is always on the same host).
- Falls back to an empty list and logs on any network error, so the
  caller (ingestion pipeline) can decide how to handle the failure.
- `health_check()` uses the lighter /api/tags endpoint rather than
  sending a full embedding request.
"""

from __future__ import annotations

import logging

import httpx

from backend.application.ports.embedding_port import IEmbeddingClient

logger = logging.getLogger(__name__)


class OllamaEmbeddingAdapter(IEmbeddingClient):
    """
    Sends embedding requests to a local Ollama instance.

    Args:
        base_url:   Root URL of the Ollama server.
                    Default: http://localhost:11434
        model:      Ollama model tag to use for embeddings.
                    Default: nomic-embed-text
        timeout:    HTTP request timeout in seconds.
                    Default: 30.0
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    # ── IEmbeddingClient protocol ─────────────────────────────────────────────

    @property
    def model_name(self) -> str:
        return self._model

    async def embed(self, text: str) -> list[float]:
        """
        Generate a dense embedding vector for the given text.

        Calls POST /api/embeddings with {"model": ..., "prompt": ...}
        and returns the "embedding" field from the response.

        Returns [] on network / API errors (caller must handle gracefully).
        """
        url = f"{self._base_url}/api/embeddings"
        payload = {"model": self._model, "prompt": text}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                embedding: list[float] = data.get("embedding", [])
                if not embedding:
                    logger.warning(
                        "OllamaEmbeddingAdapter: empty embedding returned for "
                        "model=%s, text_preview='%s'",
                        self._model,
                        text[:60],
                    )
                return embedding

        except httpx.TimeoutException:
            logger.error(
                "OllamaEmbeddingAdapter: timeout after %.1fs — is Ollama running at %s?",
                self._timeout,
                self._base_url,
            )
            return []
        except httpx.HTTPStatusError as exc:
            logger.error(
                "OllamaEmbeddingAdapter: HTTP %s from %s — %s",
                exc.response.status_code,
                url,
                exc.response.text[:200],
            )
            return []
        except Exception as exc:  # noqa: BLE001
            logger.error("OllamaEmbeddingAdapter: unexpected error: %s", exc)
            return []

    async def health_check(self) -> bool:
        """
        Returns True if the Ollama server is reachable and the target
        model is listed in /api/tags.
        """
        url = f"{self._base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                models: list[dict] = data.get("models", [])
                available = [m.get("name", "") for m in models]
                # nomic-embed-text may appear as "nomic-embed-text:latest"
                is_available = any(
                    self._model in name for name in available
                )
                if not is_available:
                    logger.warning(
                        "OllamaEmbeddingAdapter.health_check: model '%s' not found in "
                        "available models: %s",
                        self._model,
                        available,
                    )
                return is_available
        except Exception as exc:  # noqa: BLE001
            logger.warning("OllamaEmbeddingAdapter.health_check failed: %s", exc)
            return False
