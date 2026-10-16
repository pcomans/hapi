"""Walters Art Museum mapper — transforms raw Walters records to CanonicalArtifact.

A raw record is one object's `art.csv` row (`object`) and its `media.csv` rows (`media`), as the
ingest stores them. Field mapping notes (docs/museum-sources/walters.md):
- `CollectionID` lists the museum's collection codes, "|"-separated ("EGY", "EGY|JWL"). It decides
  inclusion (`is_egyptian`), with `Culture` for objects in no collection.
- `Reign` names the ruler(s) with dates ("Ramesses II (1279-1213 BC)"); `Dynasty` the dynasty
  ("18th Dynasty"). Both are raw text; enrichment resolves them.
- `Period` is empty for every object, and there is no find place: `GeographyID` is empty and no
  geography file is published.
- Images and their rights: every image is CC0 (the museum's rights policy); the record's image
  is its primary `media.csv` row.
"""

from pipeline.enrich.mentions import without_trailing_dates
from pipeline.types.canonical import CanonicalArtifact
from pipeline.types.protocol import MapperProtocol
from pipeline.types.sources import MUSEUM_LICENSE, License, MuseumSource

# The museum's collection codes (collections.csv), and its code for "Ancient Egypt and Nubia".
# "PRE" is not in collections.csv but art.csv uses it, beside another code, on 12 objects that
# are all prehistoric (Neolithic, Predynastic); its name is not published.
COLLECTION_CODES = frozenset({
    "AME", "ANE", "ARM", "BAR", "BYZ", "CHN", "EAN", "EGY", "ETH", "GRC", "INT", "ISL", "JMA", "JPK",
    "JWL", "MED", "MIS", "MSS", "PRE", "REN", "ROM", "SAY", "SEA", "TAF",
})
EGYPT_COLLECTION = "EGY"
# Codes written together without their "|" separator, as the file gives them (object 24014,
# "Amulet of Horus the Child": "EGYJWL").
RUN_TOGETHER_CODES = {"EGYJWL": ("EGY", "JWL")}
# Objects in no collection are kept when the museum's culture is this (all 192 such candidates
# on 2026-09-11 are ancient Egyptian objects).
UNASSIGNED_EGYPTIAN_CULTURE = "Egyptian"


def collection_codes(raw: dict) -> tuple[str, ...]:
    """The object's collection codes. Raises on a code the museum does not list."""
    value = raw["object"]["CollectionID"]
    if not value:
        return ()
    codes = tuple(code for token in value.split("|") for code in RUN_TOGETHER_CODES.get(token, (token,)))
    unknown = set(codes) - COLLECTION_CODES
    if unknown:
        raise ValueError(f"walters-{raw['object']['ObjectID']}: unknown collection codes {sorted(unknown)}")
    return codes


def is_egyptian(raw: dict) -> bool:
    """Whether the museum puts the object in Hapi's Egyptian scope: its collections include
    Ancient Egypt and Nubia, or it is in no collection and its culture is Egyptian. An object the
    museum files only in other collections (Islamic, Roman, Greek, Near Eastern) is out, whatever
    its culture says. Raises on an object in no collection whose culture this rule has not seen,
    so a new case is decided, not guessed."""
    codes = collection_codes(raw)
    if EGYPT_COLLECTION in codes:
        return True
    if codes:
        return False
    culture = raw["object"]["Culture"]
    if culture == UNASSIGNED_EGYPTIAN_CULTURE:
        return True
    raise ValueError(f"walters-{raw['object']['ObjectID']}: in no collection, with culture {culture!r}")


class WaltersMapper(MapperProtocol):
    source = MuseumSource.WALTERS

    def map_to_canonical(self, raw: dict) -> CanonicalArtifact:
        obj = raw["object"]
        object_id = obj["ObjectID"]
        if not object_id:
            raise ValueError("Walters record without an ObjectID")
        image_url = _primary_image(raw)
        license_ = MUSEUM_LICENSE[self.source] if image_url else License.NONE

        return CanonicalArtifact(
            id=f"walters-{object_id}",
            source_museum=self.source.value,
            source_url=obj["ResourceURL"],
            source_id=object_id,
            title=_text(obj["Title"]),
            description=_text(obj["Description"]),
            object_type=_text(obj["ObjectName"]),
            materials=[obj["Medium"].strip()] if obj["Medium"].strip() else None,
            dimensions=_text(obj["Dimensions"]),
            period=_text(obj["Period"]),
            dynasty=_text(obj["Dynasty"]),
            ruler_display_name=_ruler(obj["Reign"]),
            date_start=_year(obj["DateBeginYear"]),
            date_end=_year(obj["DateEndYear"]),
            date_display=_text(obj["DateText"]),
            origin_site_raw=None,  # the Walters publishes no find place
            origin_certainty=None,
            provenance=_text(obj["Provenance"]),
            current_location=None,  # `MuseumLocation` is a pointer to the website, not a location
            accession_number=_text(obj["AccessionNumber"]),
            credit_line=_text(obj["CreditLine"]),
            image_url=image_url,
            thumbnail_url=image_url,  # media.csv gives one URL per image
            license=license_,
            wikidata_id=None,
        )


def _text(value: str) -> str | None:
    """A CSV field without its surrounding whitespace; an empty field is None."""
    return value.strip() or None


def _year(value: str) -> int | None:
    return int(value) if value.strip() else None


def _ruler(value: str) -> str | None:
    """`Reign` as raw text without its trailing dates (`without_trailing_dates`, which the mention
    reader also uses). Lists, ranges and doubt marks stay as written ("Psametik I-Necho II",
    "Seti I (1290-1279/8) (?)")."""
    return without_trailing_dates(value.strip()) or None


def _primary_image(raw: dict) -> str | None:
    """The URL of the object's primary image: its one `media.csv` image row marked `IsPrimary`.
    With none marked, the image the museum ranks first (lowest `Rank`), which must be unique.
    More than one marked raises. No image row: None."""
    images = [m for m in raw["media"] if m["MediaType"] == "Image"]
    if not images:
        return None
    primary = [m for m in images if m["IsPrimary"] == "1"]
    if len(primary) > 1:
        raise ValueError(f"walters-{raw['object']['ObjectID']}: {len(primary)} primary images")
    if not primary:
        lowest = min(int(m["Rank"]) for m in images)
        primary = [m for m in images if int(m["Rank"]) == lowest]
        if len(primary) > 1:
            raise ValueError(f"walters-{raw['object']['ObjectID']}: no primary image and a tied first rank")
    return primary[0]["ImageURL"]
