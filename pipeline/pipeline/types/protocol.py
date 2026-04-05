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

    Error handling philosophy (dev phase):
        FAIL FAST. If a record can't be mapped, raise an exception with
        a clear message identifying the record and the problem. Do not
        silently skip records, return partial results, or add defensive
        try/except blocks. A failing mapper means a fixture is missing
        or the mapping logic has a bug — both must be fixed immediately.

        Once mappers are validated against real data and stable, this
        policy will be relaxed to handle incoming data quality issues
        gracefully. Until then: loud failures, no defensive programming.
    """

    source: MuseumSource

    def map_to_canonical(self, raw: dict) -> CanonicalArtifact:
        """Map a single raw museum record to the canonical schema.

        Returns a CanonicalArtifact with None for unmappable optional fields.
        Raises ValueError or KeyError if the record is malformed or missing
        data required for a valid mapping (id, source_url).
        """
        ...
