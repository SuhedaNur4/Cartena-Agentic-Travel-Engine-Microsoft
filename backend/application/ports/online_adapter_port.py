"""Port: IOnlineAdapter — abstract interface for optional online data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod


class IOnlineAdapter(ABC):
    """
    Defines the contract for optional online data augmentation.

    In the MVP, all concrete adapters are stubs that return empty lists.
    Future versions implement WeatherAdapter (Open-Meteo) and
    POIAdapter (Overpass/OSM) without changing the RAG pipeline.

    The use case checks `is_available()` before calling `fetch()`.
    A False return short-circuits gracefully — no errors, no retries.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable adapter identifier (e.g., 'weather', 'poi')."""
        ...  # pragma: no cover

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Returns True only if the adapter is enabled AND the upstream
        service is currently reachable.

        Stubs always return False.
        """
        ...  # pragma: no cover

    @abstractmethod
    async def fetch(self, query: str, context: dict) -> list[str]:
        """
        Retrieve supplementary context strings for the given query.

        Args:
            query:   The destination + trip summary string.
            context: Additional structured context (budget, interests, dates).

        Returns:
            A list of short context strings to inject into the prompt.
            Returns [] if data is unavailable or the adapter is a stub.
        """
        ...  # pragma: no cover
