"""Tests for the Met mapper using real fixture data."""

import json
from pathlib import Path

import pytest

from pipeline.assets.normalize.met import MetMapper
from pipeline.types.sources import License

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "met"


def _load_fixture(name: str) -> dict:
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


@pytest.fixture
def mapper():
    return MetMapper()


class TestRichObject:
    """Thutmose III statuette — full metadata, reign, dates, image, gallery."""

    @pytest.fixture(autouse=True)
    def setup(self, mapper):
        raw = _load_fixture("rich_object.json")
        self.result = mapper.map_to_canonical(raw)

    def test_id(self):
        assert self.result.id == "met-547772"

    def test_source_museum(self):
        assert self.result.source_museum == "met"

    def test_source_url(self):
        assert self.result.source_url == "https://www.metmuseum.org/art/collection/search/547772"

    def test_title(self):
        assert self.result.title == "Ritual Statuette of Thutmose III"

    def test_object_type(self):
        assert self.result.object_type == "Statuette"

    def test_materials(self):
        assert self.result.materials == ["Black bronze", "gold inlay"]

    def test_period(self):
        assert self.result.period == "New Kingdom"

    def test_dynasty(self):
        assert self.result.dynasty == "Dynasty 18"

    def test_ruler_extracted_from_reign(self):
        assert self.result.ruler_display_name == "Thutmose III"

    def test_dates(self):
        assert self.result.date_start == -1479
        assert self.result.date_end == -1425

    def test_date_display(self):
        assert self.result.date_display == "ca. 1479–1425 B.C."

    def test_origin_site_raw(self):
        assert self.result.origin_site_raw == "Egypt"

    def test_origin_certainty(self):
        assert self.result.origin_certainty == "confirmed"

    def test_image(self):
        assert "DT537.jpg" in self.result.image_url

    def test_thumbnail(self):
        assert self.result.thumbnail_url == "https://images.metmuseum.org/CRDImages/eg/web-large/DT537.jpg"

    def test_license(self):
        assert self.result.license == License.CC0

    def test_gallery(self):
        assert self.result.current_location == "Gallery 118"

    def test_wikidata_id(self):
        assert self.result.wikidata_id == "Q29385916"

    def test_accession_number(self):
        assert self.result.accession_number == "1995.21"


class TestSparseObject:
    """Fishtail Knife — minimal fields."""

    @pytest.fixture(autouse=True)
    def setup(self, mapper):
        raw = _load_fixture("sparse_object.json")
        self.result = mapper.map_to_canonical(raw)

    def test_id(self):
        assert self.result.id == "met-548235"

    def test_title(self):
        assert self.result.title == "Fishtail Knife"

    def test_no_dynasty(self):
        assert self.result.dynasty is None

    def test_period(self):
        assert self.result.period == "Predynastic, Naqada II"

    def test_no_ruler(self):
        assert self.result.ruler_display_name is None

    def test_image_present(self):
        assert self.result.image_url == "https://images.metmuseum.org/CRDImages/eg/original/DP112575.jpg"


class TestAmbiguousProvenance:
    """Bottle — 'Said to be from' geography type, not public domain."""

    @pytest.fixture(autouse=True)
    def setup(self, mapper):
        raw = _load_fixture("ambiguous_provenance.json")
        self.result = mapper.map_to_canonical(raw)

    def test_origin_certainty_uncertain(self):
        assert self.result.origin_certainty == "uncertain"

    def test_origin_site_raw_includes_subregion(self):
        assert "Girga" in self.result.origin_site_raw

    def test_license_restricted_for_non_public_domain(self):
        assert self.result.license == License.RESTRICTED


class TestCoregencyReign:
    """Queen Tiye ring — reign spans two rulers."""

    @pytest.fixture(autouse=True)
    def setup(self, mapper):
        raw = _load_fixture("coregency_reign.json")
        self.result = mapper.map_to_canonical(raw)

    def test_ruler_preserves_full_span(self):
        assert self.result.ruler_display_name == "Amenhotep III to Akhenaten"

    def test_excavation_id(self):
        assert self.result.excavation_id == "Petrie excavations, 1891–92"

    def test_origin_site_raw(self):
        assert "Amarna" in self.result.origin_site_raw

    def test_dates(self):
        assert self.result.date_start == -1395
        assert self.result.date_end == -1331


class TestNoImage:
    """Wedge — no image available."""

    @pytest.fixture(autouse=True)
    def setup(self, mapper):
        raw = _load_fixture("no_image.json")
        self.result = mapper.map_to_canonical(raw)

    def test_no_image(self):
        assert self.result.image_url is None

    def test_no_thumbnail(self):
        assert self.result.thumbnail_url is None

    def test_still_has_required_fields(self):
        assert self.result.id == "met-545782"
        assert self.result.source_url == "https://www.metmuseum.org/art/collection/search/545782"
        assert self.result.source_museum == "met"

    def test_excavation(self):
        assert self.result.excavation_id == "MMA excavations"

    def test_license_restricted_for_non_public_domain(self):
        assert self.result.license == License.RESTRICTED


class TestMultilineMedium:
    """Oblique Lyre — medium field contains \\r\\n delimiters."""

    @pytest.fixture(autouse=True)
    def setup(self, mapper):
        raw = _load_fixture("multiline_medium.json")
        self.result = mapper.map_to_canonical(raw)

    def test_id(self):
        assert self.result.id == "met-546960"

    def test_materials_split_on_newlines(self):
        assert self.result.materials == [
            "Wood (frame)",
            "bronze or copper alloy",
            "(staple)",
            "Bronze",
        ]

    def test_title(self):
        assert self.result.title == "Partially Restored Oblique Lyre"

    def test_object_type(self):
        assert self.result.object_type == "Music"
