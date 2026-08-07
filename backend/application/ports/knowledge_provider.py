"""
Port for destination knowledge providers.
"""

from abc import ABC, abstractmethod
from backend.domain.models.destination import ResolvedDestination, KnowledgeDocument


class IDestinationKnowledgeProvider(ABC):
    """Abstract interface for fetching knowledge about a destination."""

    @abstractmethod
    async def get_destination_context(self, destination: ResolvedDestination, query_text: str) -> list[KnowledgeDocument]:
        """
        Retrieve knowledge documents for the given destination.
        Returns an empty list if the provider has no information.
        """
        pass
