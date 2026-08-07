"""
Knowledge Service.
Orchestrates destination resolution and knowledge retrieval across multiple providers.
"""
import logging

from backend.infrastructure.knowledge_base.resolver import DestinationResolver
from backend.application.ports.knowledge_provider import IDestinationKnowledgeProvider
from backend.domain.models.destination import KnowledgeDocument

logger = logging.getLogger(__name__)


class DestinationResolutionError(Exception):
    """Raised when a destination cannot be resolved or found in any KB."""
    pass


class KnowledgeService:
    def __init__(self, resolver: DestinationResolver, providers: list[IDestinationKnowledgeProvider]):
        """
        providers should be ordered by priority (e.g. LocalProvider first, then WikipediaProvider).
        """
        self.resolver = resolver
        self.providers = providers

    async def get_context_for_destination(self, input_name: str, query_text: str) -> list[KnowledgeDocument]:
        """
        Resolves the destination and tries providers in order until one returns data.
        If all fail, raises DestinationResolutionError.
        """
        resolved_dest = self.resolver.resolve(input_name)
        
        for provider in self.providers:
            try:
                docs = await provider.get_destination_context(resolved_dest, query_text)
                if docs:
                    logger.info(f"Resolved {input_name} using provider {provider.__class__.__name__}")
                    return docs
            except Exception as e:
                logger.error(f"Error fetching from {provider.__class__.__name__}: {e}")
                
        # If we reach here, no provider could find the destination.
        # Epic 7 Guardrail: Controlled Failure over Hallucination
        logger.error(f"Failed to resolve destination '{input_name}' across all providers.")
        raise DestinationResolutionError(f"Destination '{input_name}' could not be resolved.")
