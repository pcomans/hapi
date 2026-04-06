"""Harvard Art Museums mapper — transforms raw Harvard API responses to CanonicalArtifact.

Field mapping notes:
- Harvard's `period` field sometimes includes dynasty (e.g., "Late Period, Dynasty 26")
- `places` is an array of objects with `displayname` and `type` — "Creation Place" is the origin
- `places.displayname` uses hierarchical format: "Ancient & Byzantine World, Africa, Egypt (Ancient)"
- `medium` field can contain \r\n delimiters with labeled sections (e.g., "Binder: Beeswax\r\nPigments: ...")
- `worktypes` is an array of objects with `worktype` field — use first entry as object_type
- `datebegin`/`dateend` are negative for BCE, positive for CE; 0 means unknown
- `imagepermissionlevel`: 0 = ok to display, 1 = restricted, 2 = no display
- Harvard images are non-commercial educational use only
"""

import re

from pipeline.types.canonical import CanonicalArtifact
from pipeline.types.protocol import MapperProtocol
from pipeline.types.sources import MUSEUM_LICENSE, License, MuseumSource

HARVARD_BASE_URL = "https://www.harvardartmuseums.org/collections/object/"


class HarvardMapper(MapperProtocol):
    source = MuseumSource.HARVARD

    def map_to_canonical(self, raw: dict) -> CanonicalArtifact:
        object_id = str(raw["id"])
        period, dynasty = _parse_period_dynasty(raw.get("period"))

        return CanonicalArtifact(
            id=f"harvard-{object_id}",
            source_museum=self.source.value,
            source_url=raw.get("url") or f"{HARVARD_BASE_URL}{object_id}",
            source_id=object_id,
            title=raw.get("title") or None,
            description=raw.get("description") or None,
            object_type=_extract_object_type(raw.get("worktypes")),
            materials=_parse_medium(raw.get("medium")),
            dimensions=raw.get("dimensions") or None,
            period=period,
            dynasty=dynasty,
            ruler_display_name=None,  # Harvard has no ruler field; enrichment resolves this
            date_start=_parse_date(raw.get("datebegin")),
            date_end=_parse_date(raw.get("dateend")),
            date_display=raw.get("dated") or None,
            origin_site_raw=_extract_origin_site(raw.get("places")),
            origin_certainty=None,  # Harvard places don't carry confidence info
            accession_number=raw.get("objectnumber") or None,
            credit_line=raw.get("creditline") or None,
            image_url=_extract_image_url(raw),
            thumbnail_url=_extract_thumbnail_url(raw),
            license=_determine_license(raw),
        )


def _parse_period_dynasty(period_str: str | None) -> tuple[str | None, str | None]:
    """Split Harvard's period field into period and dynasty.

    Harvard sometimes combines them: "Late Period, Dynasty 26".
    """
    if not period_str:
        return None, None

    match = re.match(r"^(.+?),\s*(Dynasty\s+\d+.*)$", period_str)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    return period_str.strip(), None


def _parse_medium(medium: str | None) -> list[str] | None:
    """Split medium string into individual materials.

    Harvard's medium field can use commas, semicolons, and \r\n as delimiters.
    Some entries have labeled sections (e.g., "Binder: Beeswax\r\nPigments: ...").
    """
    if not medium:
        return None
    parts = [m.strip() for m in re.split(r"[\r\n]+", medium) if m.strip()]
    return parts or None


def _extract_object_type(worktypes: list[dict] | None) -> str | None:
    """Extract object type from worktypes array."""
    if not worktypes:
        return None
    return worktypes[0].get("worktype") or None


def _extract_origin_site(places: list[dict] | None) -> str | None:
    """Extract origin site from places array.

    Looks for entries with type "Creation Place". The displayname uses
    a hierarchical format like "Ancient & Byzantine World, Africa, Egypt (Ancient)".
    """
    if not places:
        return None
    for place in places:
        if place.get("type") == "Creation Place":
            return place.get("displayname") or None
    return None


def _parse_date(value: int | None) -> int | None:
    """Convert Harvard date to int, treating 0 as unknown."""
    if value is None or value == 0:
        return None
    return value


def _extract_image_url(raw: dict) -> str | None:
    """Extract primary image URL."""
    if raw.get("imagepermissionlevel", 1) != 0:
        return None
    return raw.get("primaryimageurl") or None


def _extract_thumbnail_url(raw: dict) -> str | None:
    """Extract thumbnail URL from images array."""
    if raw.get("imagepermissionlevel", 1) != 0:
        return None
    images = raw.get("images")
    if not images:
        return None
    base = images[0].get("baseimageurl")
    if base:
        return f"{base}?width=400"
    return None


def _determine_license(raw: dict) -> License:
    """Determine license based on image permission level and image availability."""
    if not raw.get("primaryimageurl"):
        return License.NONE
    if raw.get("imagepermissionlevel", 1) != 0:
        return License.RESTRICTED
    return MUSEUM_LICENSE[MuseumSource.HARVARD]
