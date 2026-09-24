"""Resilient Resolver Router with Fallback.
Implements Open/Closed Principle and Liskov Substitution Principle:
Accepts a sequence of StreamResolverPort implementations and degrades gracefully.
Cyclomatic Complexity target: M <= 6.
"""
import logging
from typing import List
from domain.exceptions import ResolutionError
from domain.models import VideoMetadata
from ports.out_bound import StreamResolverPort

logger = logging.getLogger(__name__)


class ResilientStreamResolver:
    """Dispatches resolution across primary and secondary adapters."""

    def __init__(self, resolvers: List[StreamResolverPort]) -> None:
        if not resolvers:
            raise ValueError("At least one StreamResolverPort must be supplied.")
        self._resolvers = resolvers

    def resolve(self, url_or_id: str) -> VideoMetadata:
        """Attempt resolution sequentially until one succeeds."""
        errors: List[str] = []

        for resolver in self._resolvers:
            if not resolver.can_handle(url_or_id):
                continue

            resolver_name = resolver.__class__.__name__
            try:
                logger.info(f"Attempting resolution with {resolver_name}...")
                metadata = resolver.resolve(url_or_id)
                logger.info(f"Successfully resolved with {resolver_name}")
                return metadata
            except Exception as err:
                logger.warning(f"Resolver {resolver_name} failed: {err}")
                errors.append(f"{resolver_name}: {str(err)}")

        joined_errors = "; ".join(errors) if errors else "No compatible resolver found."
        raise ResolutionError(f"All stream resolvers exhausted. Errors: {joined_errors}")
