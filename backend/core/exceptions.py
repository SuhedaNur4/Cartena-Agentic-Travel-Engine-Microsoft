"""Core: Application exception hierarchy."""

from __future__ import annotations


class CartenaError(Exception):
    """Base class for all application-level errors."""


class LLMUnavailableError(CartenaError):
    """Raised when the Foundry Local LLM service is not reachable."""


class EmbeddingError(CartenaError):
    """Raised when the embedding model fails to generate a vector."""


class RAGError(CartenaError):
    """Raised when ChromaDB retrieval fails."""


class ItineraryNotFoundError(CartenaError):
    """Raised when a requested itinerary ID does not exist in the database."""


class ValidationError(CartenaError):
    """Raised when user input fails domain-level validation."""


class ParsingError(CartenaError):
    """Raised when the LLM response cannot be parsed into a structured itinerary."""
