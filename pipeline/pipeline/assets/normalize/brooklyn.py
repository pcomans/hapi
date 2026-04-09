"""Brooklyn Museum mapper — transforms raw Brooklyn data to CanonicalArtifact.

Field mapping notes:
- Raw data is a merged JSON blob: search API fields (sourceId, title, dates,
  startYear, endYear, imageUrl, geographicalLocations, constituents, classification)
  plus RSC detail fields (medium, dimensions, dynasty, period, creditLine,
  provenance, rightsType, inscribed, objectDate).
- `geographicalLocations` is an array from the search API with flat objects
  containing `continent`, `country`, `city`, `name`, `type`.
- `constituents` is an array with `role` and `name` — culture is indicated
  by role="Culture". Non-Egyptian cultures (Cypriot, Roman, Greek, etc.) are
  in the same department but should not be filtered here (ingest or normalize
  asset handles filtering).
- `dynasty` is free-text with typos (e.g., "in the style fo the late Dynasty 18").
- `period` can be verbose (e.g., "Modern, in the style of the New Kingdom, Amarna Period").
- `startYear`/`endYear` use negative integers for BCE.
- `dimensions` may contain trailing `\r\n` whitespace.
- Brooklyn images are noncommercial use with attribution.
"""

import re

from pipeline.types.canonical import CanonicalArtifact
from pipeline.types.protocol import MapperProtocol
from pipeline.types.sources import MUSEUM_LICENSE, License, MuseumSource


EGYPTIAN_CULTURES = frozenset({
    "Egyptian",
    "Coptic",
    "Demotic",
    "Graeco-Egyptian",
    "Egypto-Roman",
    "Nubian",
})


def is_egyptian(raw: dict) -> bool:
    """Return True if the record should be included in the Egyptian artifacts index.

    Includes objects with no culture tag (most of the Egyptian department) and
    objects tagged with Egyptian-adjacent cultures. Excludes objects explicitly
    tagged as non-Egyptian (Greek, Roman, Etruscan, etc.).
    """
    constituents = raw.get("constituents") or []
    cultures = [c["name"] for c in constituents if c.get("role") == "Culture"]
    if not cultures:
        return True
    return any(c in EGYPTIAN_CULTURES for c in cultures)


class BrooklynMapper(MapperProtocol):
    source = MuseumSource.BROOKLYN

    def map_to_canonical(self, raw: dict) -> CanonicalArtifact:
        source_id = str(raw["sourceId"])

        return CanonicalArtifact(
            id=f"brooklyn-{source_id}",
            source_museum=self.source.value,
            source_url=raw.get("url") or f"https://www.brooklynmuseum.org/objects/{source_id}",
            source_id=source_id,
            title=raw.get("title") or None,
            description=raw.get("description") or None,
            object_type=raw.get("classification") or None,
            materials=_parse_medium(raw.get("medium")),
            dimensions=_parse_dimensions(raw.get("dimensions")),
            period=raw.get("period") or None,
            dynasty=raw.get("dynasty") or None,
            ruler_display_name=None,  # Brooklyn has no ruler field; enrichment resolves this
            date_start=_to_int(raw.get("startYear")),
            date_end=_to_int(raw.get("endYear")),
            date_display=raw.get("dates") or None,
            origin_site_raw=_extract_origin_site(raw.get("geographicalLocations")),
            origin_certainty=_map_geography_type(raw.get("geographicalLocations")),
            provenance=raw.get("provenance") or None,
            accession_number=raw.get("accessionNumber") or None,
            credit_line=raw.get("creditLine") or None,
            image_url=raw.get("imageUrl") or None,
            thumbnail_url=_build_thumbnail_url(raw.get("imageUrl")),
            license=_determine_license(raw),
        )


def _parse_medium(medium: str | None) -> list[str] | None:
    """Split medium string into individual materials.

    Brooklyn's medium field uses commas as delimiters
    (e.g., "Egyptian alabaster (calcite), bronze" or "Clay, slip").
    """
    if not medium:
        return None
    parts = [m.strip() for m in re.split(r",\s*", medium) if m.strip()]
    return parts or None


def _parse_dimensions(dimensions: str | None) -> str | None:
    """Clean up dimensions string, stripping trailing whitespace/newlines."""
    if not dimensions:
        return None
    cleaned = dimensions.strip()
    return cleaned or None


def _to_int(value: object) -> int | None:
    """Convert a value to int. None means absent."""
    if value is None:
        return None
    return int(value)


def _extract_origin_site(geo_locations: list[dict] | None) -> str | None:
    """Extract origin site from geographical locations.

    Returns the `name` field from the first geographical location that has one.
    The `name` field is the most complete (e.g., "Saqqara, Egypt").
    """
    if not geo_locations:
        return None
    for geo in geo_locations:
        if geo is None:
            continue
        name = geo.get("name")
        if name:
            return name
    return None


def _map_geography_type(geo_locations: list[dict] | None) -> str | None:
    """Map Brooklyn's geography type to origin certainty.

    Uses the first non-null geographical location's `type` field.
    """
    if not geo_locations:
        return None
    geo_type = None
    for geo in geo_locations:
        if geo is None:
            continue
        geo_type = geo.get("type")
        if geo_type:
            break
    if not geo_type:
        return None
    mapping = {
        "Place made": "made_in",
        "Place excavated": "excavated",
        "Place found": "excavated",
        "Place collected": "collected",
        "Place used": "used",
        "Place modified": "made_in",
        "Reportedly from": "uncertain",
        "Possible place made": "uncertain",
        "Possible place collected": "uncertain",
        "Possible place purchased": "uncertain",
        "Possible place manufactured": "uncertain",
    }
    if geo_type not in mapping:
        raise ValueError(f"Unknown Brooklyn geography type: {geo_type!r}")
    return mapping[geo_type]


def _build_thumbnail_url(image_url: str | None) -> str | None:
    """Build thumbnail URL from full image URL.

    Brooklyn uses a separate thumbnail server at imgsrv.brooklynmuseum.org.
    """
    if not image_url:
        return None
    # Extract filename from CDN URL
    # e.g., "https://brooklynmuseum.b-cdn.net/collections/objects/37.400E_front_PS2.jpg"
    # → "https://imgsrv.brooklynmuseum.org/collections/objects/37.400E_front_PS2.jpg?width=400&quality=75"
    filename = image_url.rsplit("/", 1)[-1] if "/" in image_url else None
    if not filename:
        return None
    return f"https://imgsrv.brooklynmuseum.org/collections/objects/{filename}?width=400&quality=75"


def _determine_license(raw: dict) -> License:
    """Determine license based on image availability."""
    if not raw.get("imageUrl"):
        return License.NONE
    return MUSEUM_LICENSE[MuseumSource.BROOKLYN]
