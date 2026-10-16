"""Tests for the Cleveland Museum of Art mapper using real fixture data.

Each fixture's expected record lists every populated canonical field; every other field must
be None (or License.NONE for `license`).
"""

import json
from pathlib import Path

import pytest

from pipeline.assets.ingest import cleveland as ingest
from pipeline.assets.normalize.cleveland import ClevelandMapper, is_egyptian
from pipeline.types.canonical import CanonicalArtifact

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "cleveland"


def _load_fixture(name: str) -> dict:
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


EXPECTED = {
    # Head of Amenhotep III — reign, dynasty, gallery, provenance, CC0 image, Wikidata.
    "rich_object.json": {
        "id": "cleveland-130133",
        "source_museum": "cleveland",
        "source_url": "https://clevelandart.org/art/1952.513",
        "source_id": "130133",
        "title": "Head of Amenhotep III Wearing the Blue Crown",
        "object_type": "Sculpture",
        "materials": ["granodiorite"],
        "dimensions": "Overall: 39.1 x 30.3 x 27.7 cm (15 3/8 x 11 15/16 x 10 7/8 in.)",
        "period": "New Kingdom",
        "dynasty": "Dynasty 18",
        "ruler_display_name": "Amenhotep III",
        "date_start": -1391,
        "date_end": -1353,
        "date_display": "c. 1391–1353 BCE",
        "provenance": "Milton Girod, Chahaignes, France, sold to the Cleveland Museum of Art; "
                      "The Cleveland Museum of Art, Cleveland, Oh",
        "current_location": "107 Egyptian",
        "accession_number": "1952.513",
        "credit_line": "Gift of the Hanna Fund",
        "image_url": "https://openaccess-cdn.clevelandart.org/1952.513/1952.513_web.jpg",
        "thumbnail_url": "https://openaccess-cdn.clevelandart.org/1952.513/1952.513_web.jpg",
        "license": "cc0",
        "wikidata_id": "Q60751152",
    },
    # Caryatid Mirror — no image, no description, dynasty without a reign.
    "sparse_no_image.json": {
        "id": "cleveland-306809",
        "source_museum": "cleveland",
        "source_url": "https://clevelandart.org/art/1983.195",
        "source_id": "306809",
        "title": "Caryatid Mirror",
        "object_type": "Cosmetic Objects",
        "materials": ["bronze"],
        "dimensions": "32.4 cm (12 3/4 in.)",
        "period": "New Kingdom",
        "dynasty": "Dynasty 18",
        "date_start": -1484,
        "date_end": -1420,
        "date_display": "c. 1479–1425 BCE",
        "accession_number": "1983.195",
        "credit_line": "Leonard C. Hanna Jr. Fund",
        "license": "none",
        "wikidata_id": "Q60740239",
    },
    # Boomerang — the "Egyptian" collection (no period), Copyrighted, no image.
    "copyrighted_no_image.json": {
        "id": "cleveland-101400",
        "source_museum": "cleveland",
        "source_url": "https://clevelandart.org/art/1920.2011",
        "source_id": "101400",
        "title": "Boomerang",
        "object_type": "Wood",
        "materials": ["wood"],
        "date_start": 1920,
        "date_end": 1920,
        "date_display": "1920",
        "accession_number": "1920.2011",
        "credit_line": "Gift of Mrs. Gordon N. Morrill",
        "license": "none",
        "wikidata_id": "Q79496645",
    },
    # Domestic Shrine — "Thebes(?)" in culture, the "Tuthmosis III" spelling, provenance
    # entry without a sortorder.
    "uncertain_place.json": {
        "id": "cleveland-101390",
        "source_museum": "cleveland",
        "source_url": "https://clevelandart.org/art/1920.2002",
        "source_id": "101390",
        "title": "Domestic Shrine",
        "object_type": "Sculpture",
        "materials": ["limestone, originally painted"],
        "dimensions": "Overall: 42.4 x 27.4 x 9 cm (16 11/16 x 10 13/16 x 3 9/16 in.)",
        "period": "New Kingdom",
        "dynasty": "Dynasty 18",
        "ruler_display_name": "Tuthmosis III",
        "date_start": -1479,
        "date_end": -1425,
        "date_display": "c. 1479–1425 BCE",
        "provenance": "Probably Theban area. Purchased from Jusef Hasan, Luxor, through Howard Carter",
        "current_location": "107 Egyptian",
        "accession_number": "1920.2002",
        "credit_line": "Gift of the John Huntington Art and Polytechnic Trust",
        "image_url": "https://openaccess-cdn.clevelandart.org/1920.2002/1920.2002_web.jpg",
        "thumbnail_url": "https://openaccess-cdn.clevelandart.org/1920.2002/1920.2002_web.jpg",
        "license": "cc0",
        "wikidata_id": "Q60741668",
    },
    # Ripple-Flaked Knife — explicit find_spot from an excavation.
    "find_spot_excavated.json": {
        "id": "cleveland-94656",
        "source_museum": "cleveland",
        "source_url": "https://clevelandart.org/art/1915.30",
        "source_id": "94656",
        "title": "Ripple-Flaked Knife",
        "object_type": "Tools and Equipment",
        "materials": ["flint"],
        "dimensions": "Overall: 5 x 14.3 cm (1 15/16 x 5 5/8 in.)",
        "period": "Predynastic",
        "date_start": -4000,
        "date_end": -3000,
        "date_display": "4000–3000 BCE",
        "origin_site_raw": "El-Haraga, cemetery G, grave 413",
        "provenance": "British School of Archaeology in Egypt, gifted to the Cleveland Museum of Art; "
                      "Cleveland Museum of Art, Cleveland, OH",
        "accession_number": "1915.30",
        "credit_line": "Gift of the British School of Archaeology in Egypt",
        "image_url": "https://openaccess-cdn.clevelandart.org/1915.30/1915.30_web.jpg",
        "thumbnail_url": "https://openaccess-cdn.clevelandart.org/1915.30/1915.30_web.jpg",
        "license": "cc0",
        "wikidata_id": "Q79475132",
    },
    # Necklace — a composite object with two dynasty segments, kept together in order.
    "two_dynasties.json": {
        "id": "cleveland-94373",
        "source_museum": "cleveland",
        "source_url": "https://clevelandart.org/art/1914.752",
        "source_id": "94373",
        "title": "Necklace",
        "object_type": "Jewelry",
        "materials": ["glass and carnelian"],
        "dimensions": "Overall: 23.8 cm (9 3/8 in.)",
        "period": "Middle Kingdom",
        "dynasty": "Dynasty 12 (barrel beads) and New Kingdom, Dynasty 19 (eye beads)",
        "date_start": -1980,
        "date_end": -1186,
        "date_display": "barrel beads: 1980–1801 BCE; eye beads: 1295–1186",
        "provenance": "Purchased from Mohammed Mohasseb and Son, Luxor, by Lucy Olcott Perkins "
                      "through Henry W. Kent",
        "accession_number": "1914.752",
        "credit_line": "Gift of the John Huntington Art and Polytechnic Trust",
        "image_url": "https://openaccess-cdn.clevelandart.org/1914.752/1914.752_web.jpg",
        "thumbnail_url": "https://openaccess-cdn.clevelandart.org/1914.752/1914.752_web.jpg",
        "license": "cc0",
        "wikidata_id": "Q79474666",
    },
    # Head of a King or Osiris — out of scope (a modern forgery, `is_egyptian`), but mapped as
    # any record is.
    "modern_forgery.json": {
        "id": "cleveland-95006",
        "source_museum": "cleveland",
        "source_url": "https://clevelandart.org/art/1915.557",
        "source_id": "95006",
        "title": "Head of a King or Osiris",
        "object_type": "Sculpture",
        "materials": ["graywacke"],
        "dimensions": "Overall: 9.8 x 4.2 x 8.4 cm (3 7/8 x 1 5/8 x 3 5/16 in.)",
        "period": "Modern Forgery",
        "date_start": 1900,
        "date_end": 1915,
        "date_display": "1900–1915",
        "accession_number": "1915.557",
        "credit_line": "Gift of the John Huntington Art and Polytechnic Trust",
        "image_url": "https://openaccess-cdn.clevelandart.org/1915.557/1915.557_web.jpg",
        "thumbnail_url": "https://openaccess-cdn.clevelandart.org/1915.557/1915.557_web.jpg",
        "license": "cc0",
        "wikidata_id": "Q79475945",
    },
    # Statuette of a Bull — out of scope (Near Eastern Art collection), no period.
    "near_eastern_collection.json": {
        "id": "cleveland-135568",
        "source_museum": "cleveland",
        "source_url": "https://clevelandart.org/art/1958.95",
        "source_id": "135568",
        "title": "Statuette of a Bull with Curved Horns",
        "object_type": "Sculpture",
        "materials": ["bronze"],
        "dimensions": "Overall: 6.1 x 2.9 x 6.4 cm (2 3/8 x 1 1/8 x 2 1/2 in.); "
                      "with base: 7.4 x 2.9 x 6.4 cm (2 15/16 x 1 1/8 x 2 1/2 in.)",
        "date_start": -2000,
        "date_end": -1000,
        "date_display": "late 2000s BCE",
        "accession_number": "1958.95",
        "credit_line": "Bequest of Leonard C. Hanna Jr.",
        "image_url": "https://openaccess-cdn.clevelandart.org/1958.95/1958.95_web.jpg",
        "thumbnail_url": "https://openaccess-cdn.clevelandart.org/1958.95/1958.95_web.jpg",
        "license": "cc0",
        "wikidata_id": "Q80028939",
    },
}

DESCRIPTIONS = {
    "rich_object.json": "During the long, peaceful reign of Amenhotep III, Egypt reac",
    "uncertain_place.json": "Used in the home like an icon, this shrine was originally pr",
}


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_every_field(name):
    raw = _load_fixture(name)
    result = ClevelandMapper().map_to_canonical(raw).model_dump(mode="json")
    description = result.pop("description")
    if name in DESCRIPTIONS:
        assert description[:60] == DESCRIPTIONS[name]
        assert description == raw["description"]
    else:
        assert description is None
    expected = {field: None for field in CanonicalArtifact.model_fields if field != "description"}
    expected.update(EXPECTED[name])
    assert result == expected


@pytest.mark.parametrize("name, egyptian", [
    ("rich_object.json", True),
    ("sparse_no_image.json", True),
    ("copyrighted_no_image.json", True),
    ("uncertain_place.json", True),
    ("find_spot_excavated.json", True),
    ("two_dynasties.json", True),
    ("modern_forgery.json", False),          # collection "Egypt - Modern Forgery"
    ("near_eastern_collection.json", False),  # collection "Near Eastern Art", culture "Egypt(?)"
])
def test_is_egyptian(name, egyptian):
    assert is_egyptian(_load_fixture(name)) == egyptian


def test_unknown_collection_raises():
    raw = _load_fixture("rich_object.json") | {"collection": "Egypt"}
    with pytest.raises(ValueError, match="unknown collection 'Egypt'"):
        is_egyptian(raw)


def test_unknown_license_status_raises():
    raw = _load_fixture("rich_object.json") | {"share_license_status": "CC BY"}
    with pytest.raises(ValueError, match="unknown share_license_status 'CC BY'"):
        ClevelandMapper().map_to_canonical(raw)


def test_copyrighted_image_is_restricted_and_not_shown():
    raw = _load_fixture("rich_object.json") | {"share_license_status": "Copyrighted"}
    result = ClevelandMapper().map_to_canonical(raw)
    assert (result.license.value, result.image_url, result.thumbnail_url) == ("restricted", None, None)


def test_two_reign_segments_raise():
    raw = _load_fixture("rich_object.json")
    raw = raw | {"culture": [raw["culture"][0] + ", reign of Akhenaten (1351–1334 BCE)"]}
    with pytest.raises(ValueError, match="2 reign components"):
        ClevelandMapper().map_to_canonical(raw)


@pytest.mark.parametrize("culture, ruler", [
    # A plain "reign of" is dropped; qualifiers, doubt marks and ranges stay as written.
    ("Egypt, Dynasty 12, probably reign of Senusret I", "probably reign of Senusret I"),
    ("Egypt, Dynasty 19, reign of Ramesses II(?)", "Ramesses II(?)"),
    ("Egypt, Dynasty 18, joint reign of Hatshepsut and Tuthmosis III", "joint reign of Hatshepsut and Tuthmosis III"),
    ("Egypt, New Kingdom (1540–1069 BCE), Dynasty 18, reign of Tuthmosis III (1479–1425 BCE)–reign of Amenhotep III "
     "(1390–1352 BCE)", "Tuthmosis III (1479–1425 BCE)–reign of Amenhotep III"),
    ("Egypt, Old Kingdom (2647–2124 BCE), Dynasty 5, reign of Nyuserre (2445–2422 BCE) or later",
     "Nyuserre (2445–2422 BCE) or later"),
    # A comma inside the dates does not split the component.
    ("Egypt, Dynasty 26, reign of Psamtik I (664–610 BCE, approximately)", "Psamtik I"),
])
def test_ruler_display_name_is_the_reign_component_as_written(culture, ruler):
    raw = _load_fixture("rich_object.json") | {"culture": [culture]}
    assert ClevelandMapper().map_to_canonical(raw).ruler_display_name == ruler


@pytest.mark.parametrize("resources, message", [
    ({"wikidata": ["https://www.wikidata.org/wiki/Q1", "https://www.wikidata.org/wiki/Q2"]},
     r"cleveland-130133: several Wikidata items"),
    ({"wikidata": ["https://example.org/Q1/x"]}, r"cleveland-130133: not a Wikidata item URL"),
])
def test_a_wikidata_value_that_is_not_one_item_raises(resources, message):
    raw = _load_fixture("rich_object.json") | {"external_resources": resources}
    with pytest.raises(ValueError, match=message):
        ClevelandMapper().map_to_canonical(raw)


def test_a_provenance_entry_without_a_description_raises():
    raw = _load_fixture("rich_object.json")
    raw = raw | {"provenance": raw["provenance"] + [{"description": None, "date": "1960"}]}
    with pytest.raises(ValueError, match="provenance entry without a description"):
        ClevelandMapper().map_to_canonical(raw)


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def _pages(monkeypatch, pages):
    calls = []

    def get(url, params, timeout):
        calls.append(params["skip"])
        return _Response(pages[params["skip"]])

    monkeypatch.setattr(ingest, "PAGE_SIZE", 2)
    monkeypatch.setattr(ingest.requests, "get", get)
    return calls


def test_fetch_department_reads_every_page(monkeypatch):
    a, b, c = (_load_fixture(n) for n in ("rich_object.json", "sparse_no_image.json", "modern_forgery.json"))
    calls = _pages(monkeypatch, {0: {"info": {"total": 3}, "data": [a, b]}, 2: {"info": {"total": 3}, "data": [c]}})
    assert [r["id"] for r in ingest.fetch_department()] == [130133, 306809, 95006]
    assert calls == [0, 2]


def test_fetch_department_stops_at_an_empty_page_and_checks_the_total(monkeypatch):
    a, b = (_load_fixture(n) for n in ("rich_object.json", "sparse_no_image.json"))
    calls = _pages(monkeypatch, {0: {"info": {"total": 3}, "data": [a, b]}, 2: {"info": {"total": 3}, "data": []}})
    with pytest.raises(ValueError, match=r"read 2 records \(2 distinct\); the API reports 3"):
        ingest.fetch_department()
    assert calls == [0, 2]


def test_fetch_department_raises_on_a_repeated_record(monkeypatch):
    a, b = (_load_fixture(n) for n in ("rich_object.json", "sparse_no_image.json"))
    _pages(monkeypatch, {0: {"info": {"total": 3}, "data": [a, b]}, 2: {"info": {"total": 3}, "data": [b]}})
    with pytest.raises(ValueError, match=r"read 3 records \(2 distinct\); the API reports 3"):
        ingest.fetch_department()


def test_fetch_department_raises_when_the_total_changes(monkeypatch):
    a, b, c = (_load_fixture(n) for n in ("rich_object.json", "sparse_no_image.json", "modern_forgery.json"))
    _pages(monkeypatch, {0: {"info": {"total": 3}, "data": [a, b]}, 2: {"info": {"total": 4}, "data": [c]}})
    with pytest.raises(ValueError, match="department total changed during ingest: 3 -> 4"):
        ingest.fetch_department()
