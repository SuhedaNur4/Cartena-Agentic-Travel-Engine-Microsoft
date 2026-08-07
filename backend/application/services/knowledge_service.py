"""
Knowledge Service.
Orchestrates destination resolution and knowledge retrieval across multiple providers.
"""
import logging

from backend.infrastructure.knowledge_base.resolver import DestinationResolver
from backend.application.ports.knowledge_provider import IDestinationKnowledgeProvider
from backend.domain.models.destination import KnowledgeDocument, ResolvedDestination

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

    async def check_destination_exists(self, resolved_dest: ResolvedDestination) -> bool:
        """Returns True if the destination can be found in any provider without fetching full context."""
        for provider in self.providers:
            try:
                docs = await provider.get_destination_context(resolved_dest, "city overview")
                if docs:
                    return True
            except Exception:
                pass
        return False

    async def parse_and_resolve_destinations(self, raw_input: str) -> tuple[ResolvedDestination, ...]:
        """
        Resolver-aware parsing:
        1. Try to resolve the entire string. If it exists in KB, return it.
        2. If not, split by comma, and try resolving the parts.
        """
        full_resolved = self.resolver.resolve(raw_input)
        exists = await self.check_destination_exists(full_resolved)
        if exists:
            return (full_resolved,)
            
        parts = [p.strip() for p in raw_input.split(",") if p.strip()]
        if len(parts) > 1:
            results = []
            for part in parts:
                part_resolved = self.resolver.resolve(part)
                results.append(part_resolved)
            return tuple(results)
            
        return (full_resolved,)
