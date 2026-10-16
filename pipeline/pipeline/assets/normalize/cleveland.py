"""Cleveland Museum of Art mapper — transforms raw Open Access API records to CanonicalArtifact.

Field mapping notes (docs/museum-sources/cleveland.md):
- `culture` is a list (one entry in practice) of comma-separated segments, e.g.
  "Egypt, Thebes(?), New Kingdom (1540–1069 BCE), Dynasty 18, reign of Tuthmosis III (1479–1425 BCE)".
  The mapper takes the dynasty segments and the reign segment out as raw text; places in it
  are left to enrichment.
- `collection` is the museum's grouping: "Egypt - <period>", "Egyptian", "Near Eastern Art" or
  "Egypt - Modern Forgery". It decides inclusion (`is_egyptian`) and gives the period.
- `find_spot` is the explicit find place, present on a few records.
- `share_license_status` is per record ("CC0" or "Copyrighted"); images exist only when
  `images` is set.
"""

import re

from pipeline.enrich.mentions import cleveland_reign_components, cleveland_reign_text, component_spans
from pipeline.types.canonical import CanonicalArtifact
from pipeline.types.protocol import MapperProtocol
from pipeline.types.sources import License, MuseumSource

# The museum's own `collection` groupings for this department (docs/museum-sources/cleveland.md).
EGYPT_COLLECTION_PREFIX = "Egypt - "
EGYPTIAN_COLLECTION = "Egyptian"
# Out of scope: the department's Near Eastern holdings, and objects the museum itself
# classifies as modern forgeries (not ancient Egyptian artifacts).
EXCLUDED_COLLECTIONS = frozenset({"Near Eastern Art", "Egypt - Modern Forgery"})

LICENSE_STATUS = {"CC0": License.CC0, "Copyrighted": License.RESTRICTED}

_PLAIN_REIGN = re.compile(r"^reign\s+of\s+", re.IGNORECASE)
_DYNASTY = re.compile(r"^Dynasty\s+\S")


def is_egyptian(raw: dict) -> bool:
    """Whether the museum's `collection` puts the record in Hapi's Egyptian scope. Raises on a
    collection this rule has not seen, so a new grouping is decided, not guessed."""
    collection = raw["collection"]
    if collection in EXCLUDED_COLLECTIONS:
        return False
    if collection == EGYPTIAN_COLLECTION or collection.startswith(EGYPT_COLLECTION_PREFIX):
        return True
    raise ValueError(f"cleveland-{raw['id']}: unknown collection {collection!r}")


class ClevelandMapper(MapperProtocol):
    source = MuseumSource.CLEVELAND

    def map_to_canonical(self, raw: dict) -> CanonicalArtifact:
        object_id = str(raw["id"])
        segments = _culture_segments(raw.get("culture"))
        license_ = _determine_license(raw)
        image_url = raw["images"]["web"]["url"] if license_ == License.CC0 else None

        return CanonicalArtifact(
            id=f"cleveland-{object_id}",
            source_museum=self.source.value,
            source_url=raw["url"],
            source_id=object_id,
            title=raw.get("title") or None,
            description=raw.get("description") or None,
            object_type=raw.get("type") or None,
            materials=[raw["technique"]] if raw.get("technique") else None,
            dimensions=raw.get("measurements") or None,
            period=_period(raw["collection"]),
            dynasty=_dynasty(segments),
            ruler_display_name=_ruler(raw),
            date_start=raw.get("creation_date_earliest"),
            date_end=raw.get("creation_date_latest"),
            date_display=raw.get("creation_date") or None,
            origin_site_raw=raw.get("find_spot") or None,
            origin_certainty=None,  # Cleveland marks doubt inline ("Thebes(?)"), not as a field
            provenance=_provenance(raw.get("provenance")),
            current_location=raw.get("current_location") or None,
            accession_number=raw.get("accession_number") or None,
            credit_line=raw.get("creditline") or None,
            image_url=image_url,
            thumbnail_url=image_url,  # the API's smallest rendition is `web`
            license=license_,
            wikidata_id=_wikidata_id(raw.get("external_resources"), object_id),
        )


def _culture_segments(culture: list[str] | None) -> list[str]:
    """Top-level comma components of each entry, split as the mention reader splits them (a comma
    inside parentheses does not split)."""
    return [segment for entry in culture or [] for segment, _, _ in component_spans(entry)]


def _dynasty(segments: list[str]) -> str | None:
    """The culture's "Dynasty N" segments as raw text. A composite object can name more than
    one ("Dynasty 12 (barrel beads) and New Kingdom", "Dynasty 19 (eye beads)"); all are kept,
    joined in the museum's order, so none is picked over another."""
    return ", ".join(seg for seg in segments if _DYNASTY.match(seg)) or None


def _ruler(raw: dict) -> str | None:
    """The culture's reign component as raw text (`cleveland_reign_components`, the mention
    reader's own), without its trailing dates and without a plain leading "reign of". Qualifiers,
    doubt marks and ranges stay as written ("probably reign of Senusret I", "Ramesses II(?)",
    "Tuthmosis III (1479–1425 BCE)–reign of Amenhotep III"). More than one raises."""
    found = [cleveland_reign_text(c) for entry in raw.get("culture") or [] for c, _ in cleveland_reign_components(entry)]
    if len(found) > 1:
        raise ValueError(f"cleveland-{raw['id']}: {len(found)} reign components in culture: {found}")
    return _PLAIN_REIGN.sub("", found[0]) if found else None


def _period(collection: str) -> str | None:
    if collection.startswith(EGYPT_COLLECTION_PREFIX):
        return collection[len(EGYPT_COLLECTION_PREFIX):]
    return None


def _provenance(entries: list[dict] | None) -> str | None:
    """The provenance entries' descriptions, in the order the API lists them. An entry without a
    description raises rather than vanish (none in the department on 2026-10-16)."""
    parts = []
    for entry in entries or []:
        if not entry.get("description"):
            raise ValueError(f"provenance entry without a description: {entry}")
        parts.append(entry["description"])
    return "; ".join(parts) or None


def _wikidata_id(resources: dict | None, object_id: str) -> str | None:
    urls = (resources or {}).get("wikidata") or []
    if len(urls) > 1:
        raise ValueError(f"cleveland-{object_id}: several Wikidata items: {urls}")
    if not urls:
        return None
    match = re.search(r"/(Q\d+)$", urls[0])
    if not match:
        raise ValueError(f"cleveland-{object_id}: not a Wikidata item URL: {urls[0]}")
    return match.group(1)


def _determine_license(raw: dict) -> License:
    """Per record: no image → NONE; otherwise the record's `share_license_status`. Raises on a
    status the mapping does not know."""
    if not raw.get("images"):
        return License.NONE
    status = raw["share_license_status"]
    if status not in LICENSE_STATUS:
        raise ValueError(f"cleveland-{raw['id']}: unknown share_license_status {status!r}")
    return LICENSE_STATUS[status]
