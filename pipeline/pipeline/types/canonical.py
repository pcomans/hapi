"""Canonical artifact model.

Must stay in sync with the SQLAlchemy table in models.py.
A structural test (tests/test_structure.py) verifies column names match.
"""

from pydantic import BaseModel

from .sources import License


class CanonicalArtifact(BaseModel):
    """A normalized Egyptian artifact record.

    All fields are optional except id, source_museum, and source_url.
    Sparse records are valid — the UI omits missing fields gracefully.
    """

    # Required fields
    id: str
    source_museum: str
    source_url: str

    # Optional identification
    source_id: str | None = None
    title: str | None = None
    description: str | None = None
    object_type: str | None = None
    materials: list[str] | None = None
    dimensions: str | None = None

    # Chronology
    period: str | None = None
    dynasty: str | None = None
    ruler_id: str | None = None
    ruler_display_name: str | None = None
    date_start: int | None = None
    date_end: int | None = None
    date_display: str | None = None

    # Provenance / origin
    origin_site_id: str | None = None
    origin_site_display_name: str | None = None
    origin_site_raw: str | None = None
    origin_certainty: str | None = None
    excavation_id: str | None = None
    tomb_temple_id: str | None = None

    # Provenance / ownership history
    provenance: str | None = None

    # Current location
    current_location: str | None = None
    accession_number: str | None = None
    credit_line: str | None = None

    # Images + license
    image_url: str | None = None
    thumbnail_url: str | None = None
    license: License = License.UNKNOWN

    # External identifiers
    wikidata_id: str | None = None
