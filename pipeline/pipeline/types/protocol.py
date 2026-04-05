"""Mapper protocol that all museum mappers must implement."""

from typing import Protocol

from .canonical import CanonicalArtifact
from .sources import MuseumSource


class MapperProtocol(Protocol):
    """Interface for museum-to-canonical mappers.

    Each museum gets its own mapper that implements this protocol.
    Mappers are pure transforms: dict in, CanonicalArtifact out.
    No network calls, no database writes, no side effects.

    Ruler/site resolution happens in the enrich stage, NOT in mappers.
    Mappers extract raw text values; enrichment resolves to authority IDs.
    """

    source: MuseumSource

    def map_to_canonical(self, raw: dict) -> CanonicalArtifact:
        """Map a single raw museum record to the canonical schema.

        Must never raise on missing data — return None for unmappable fields.
        """
        ...
