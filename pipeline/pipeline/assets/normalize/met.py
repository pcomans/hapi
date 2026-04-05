"""Met Museum mapper — transforms raw Met API responses to CanonicalArtifact."""

import re

from pipeline.types.canonical import CanonicalArtifact
from pipeline.types.sources import MUSEUM_LICENSE, MuseumSource

MET_BASE_URL = "https://www.metmuseum.org/art/collection/search/"


class MetMapper:
    """Maps Met API JSON to CanonicalArtifact.

    Field mapping notes:
    - geographyType indicates provenance confidence: "From" = confirmed,
      "Probably from" = likely, "Said to be from" = uncertain
    - reign field sometimes contains period info instead of ruler names
    - objectBeginDate/objectEndDate are negative integers for BCE dates
    - Met is CC0, so all images are unrestricted
    """

    source = MuseumSource.MET

    def map_to_canonical(self, raw: dict) -> CanonicalArtifact:
        object_id = str(raw["objectID"])

        return CanonicalArtifact(
            id=f"met-{object_id}",
            source_museum=self.source.value,
            source_url=raw.get("objectURL") or f"{MET_BASE_URL}{object_id}",
            source_id=object_id,
            title=raw.get("title") or None,
            description=None,  # Met API has no description field
            object_type=raw.get("objectName") or None,
            materials=_parse_medium(raw.get("medium")),
            dimensions=raw.get("dimensions") or None,
            period=raw.get("period") or None,
            dynasty=raw.get("dynasty") or None,
            ruler_display_name=_extract_ruler(raw.get("reign")),
            date_start=_to_int(raw.get("objectBeginDate")),
            date_end=_to_int(raw.get("objectEndDate")),
            date_display=raw.get("objectDate") or None,
            origin_site_raw=_build_origin_site_raw(raw),
            origin_certainty=_map_geography_type(raw.get("geographyType")),
            excavation_id=raw.get("excavation") or None,
            current_location=_build_current_location(raw),
            accession_number=raw.get("accessionNumber") or None,
            credit_line=raw.get("creditLine") or None,
            image_url=raw.get("primaryImage") or None,
            thumbnail_url=raw.get("primaryImageSmall") or None,
            license=MUSEUM_LICENSE[MuseumSource.MET],
            wikidata_id=_extract_wikidata_id(raw.get("objectWikidata_URL")),
        )


def _parse_medium(medium: str | None) -> list[str] | None:
    """Split medium string into individual materials."""
    if not medium:
        return None
    parts = [m.strip() for m in re.split(r"[,;]", medium) if m.strip()]
    return parts or None


def _extract_ruler(reign: str | None) -> str | None:
    """Extract ruler name from Met's reign field.

    Met formats this as "reign of X" or "joint reign of X and Y".
    """
    if not reign:
        return None
    match = re.match(r"(?:joint\s+)?reign\s+of\s+(.+)", reign, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return reign.strip() or None


def _to_int(value: object) -> int | None:
    """Convert a value to int, returning None for non-numeric."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _build_origin_site_raw(raw: dict) -> str | None:
    """Build origin site string from Met's structured geography fields.

    Concatenates non-empty fields in order: country, region, subregion, locale, locus.
    """
    parts = []
    for field in ("country", "region", "subregion", "locale", "locus"):
        val = raw.get(field, "")
        if val:
            parts.append(val)
    return ", ".join(parts) or None


def _map_geography_type(geo_type: str | None) -> str | None:
    """Map Met's geographyType to origin certainty."""
    if not geo_type:
        return None
    mapping = {
        "From": "confirmed",
        "Probably from": "probable",
        "Said to be from": "uncertain",
        "Possibly from": "uncertain",
        "Made in": "made_in",
    }
    return mapping.get(geo_type, geo_type.lower())


def _build_current_location(raw: dict) -> str | None:
    """Build current location from gallery number."""
    gallery = raw.get("GalleryNumber", "")
    if gallery:
        return f"Gallery {gallery}"
    return None


def _extract_wikidata_id(url: str | None) -> str | None:
    """Extract Wikidata Q-ID from URL."""
    if not url:
        return None
    match = re.search(r"(Q\d+)", url)
    return match.group(1) if match else None
