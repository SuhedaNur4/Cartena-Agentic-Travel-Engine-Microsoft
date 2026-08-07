"""
Destination Resolver Service.
Normalizes user inputs into canonical destination identities.
"""

from backend.domain.models.destination import ResolvedDestination

class DestinationResolver:
    """Resolves raw input strings into canonical ResolvedDestination objects."""

    def resolve(self, input_name: str) -> ResolvedDestination:
        """
        Takes an input like "İstanbul, Turkey" or "kyoto" and returns a canonical identity.
        For P0, we do basic string cleaning.
        """
        # Basic cleanup: split by comma, take the first part as city name
        parts = [p.strip() for p in input_name.split(",")]
        
        canonical_name = parts[0].title()
        
        # Simple normalization for common Turkish characters (if needed) or just rely on title()
        # "İstanbul" -> "Istanbul" mapping can be added here if desired.
        
        country = parts[1].title() if len(parts) > 1 else None
        
        return ResolvedDestination(
            input_name=input_name,
            canonical_name=canonical_name,
            country=country,
            destination_type="city"
        )
