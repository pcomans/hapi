"""Tests for the Brooklyn Museum mapper using real fixture data."""

import json
from pathlib import Path

import pytest

from pipeline.assets.normalize.brooklyn import BrooklynMapper
from pipeline.types.sources import License

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "brooklyn"


def _load_fixture(name: str) -> dict:
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


@pytest.fixture
def mapper():
    return BrooklynMapper()


class TestRichObject:
    """Isis Nursing Horus — full metadata, dynasty, period, geography, multi-material medium."""

    @pytest.fixture(autouse=True)
    def setup(self, mapper):
        raw = _load_fixture("rich_object.json")
        self.result = mapper.map_to_canonical(raw)

    def test_id(self):
        assert self.result.id == "brooklyn-4035"

    def test_source_museum(self):
        assert self.result.source_museum == "brooklyn"

    def test_source_url(self):
        assert self.result.source_url == "https://www.brooklynmuseum.org/objects/4035"

    def test_source_id(self):
        assert self.result.source_id == "4035"

    def test_title(self):
        assert self.result.title == "Isis Nursing Horus"

    def test_description(self):
        assert self.result.description.startswith("Green calcite figure of Isis")

    def test_object_type(self):
        assert self.result.object_type == "Sculpture"

    def test_materials(self):
        assert self.result.materials == ["Egyptian alabaster (calcite)", "bronze"]

    def test_dimensions(self):
        assert self.result.dimensions == "7 3/8 x 2 1/4 x 5 5/16 in. (18.7 x 5.7 x 13.5 cm)"

    def test_period(self):
        assert self.result.period == "Third Intermediate Period to Late Period"

    def test_dynasty(self):
        assert self.result.dynasty == "second half of Dynasty 25 to Dynasty 26"

    def test_no_ruler(self):
        assert self.result.ruler_display_name is None

    def test_dates(self):
        assert self.result.date_start == -712
        assert self.result.date_end == -525

    def test_date_display(self):
        assert self.result.date_display == "ca. 712–525 B.C.E."

    def test_origin_site_raw(self):
        assert self.result.origin_site_raw == "Saqqara, Egypt"

    def test_origin_certainty(self):
        assert self.result.origin_certainty == "uncertain"

    def test_accession_number(self):
        assert self.result.accession_number == "37.400Ea-c"

    def test_credit_line(self):
        assert self.result.credit_line == "Charles Edwin Wilbour Fund"

    def test_image_url(self):
        assert self.result.image_url == "https://brooklynmuseum.b-cdn.net/collections/objects/37.400E_front_PS2.jpg"

    def test_thumbnail_url(self):
        assert self.result.thumbnail_url == "https://imgsrv.brooklynmuseum.org/collections/objects/37.400E_front_PS2.jpg?width=400&quality=75"

    def test_license(self):
        assert self.result.license == License.CC_BY_NC_ND


class TestDynastyTypo:
    """Head of Akhenaten — dynasty with typo, verbose period, modern forgery dates."""

    @pytest.fixture(autouse=True)
    def setup(self, mapper):
        raw = _load_fixture("dynasty_typo.json")
        self.result = mapper.map_to_canonical(raw)

    def test_id(self):
        assert self.result.id == "brooklyn-60260"

    def test_source_museum(self):
        assert self.result.source_museum == "brooklyn"

    def test_source_url(self):
        assert self.result.source_url == "https://www.brooklynmuseum.org/objects/60260"

    def test_source_id(self):
        assert self.result.source_id == "60260"

    def test_title(self):
        assert self.result.title == "Head of Akhenaten Made in Two Pieces"

    def test_description_is_none(self):
        assert self.result.description is None

    def test_object_type(self):
        assert self.result.object_type == "Sculpture"

    def test_materials(self):
        assert self.result.materials == ["Limestone"]

    def test_dimensions(self):
        assert self.result.dimensions == "4 1/16 × 3 5/8 in. (10.3 × 9.2 cm)"

    def test_dynasty_preserved_with_typo(self):
        assert self.result.dynasty == "in the style fo the late Dynasty 18"

    def test_period_verbose(self):
        assert self.result.period == "Modern, in the style of the New Kingdom, Amarna Period"

    def test_modern_dates(self):
        assert self.result.date_start == 1942
        assert self.result.date_end == 1943

    def test_date_display(self):
        assert self.result.date_display == "1942–1943 C.E."

    def test_no_geography(self):
        assert self.result.origin_site_raw is None
        assert self.result.origin_certainty is None

    def test_accession_number(self):
        assert self.result.accession_number == "47.88a-b"

    def test_credit_line(self):
        assert self.result.credit_line == "Gift of Jean Tano"

    def test_image_url(self):
        assert self.result.image_url == "https://brooklynmuseum.b-cdn.net/collections/objects/CUR.47.88a-b_NegA_print_bw.jpg"

    def test_thumbnail_url(self):
        assert self.result.thumbnail_url == "https://imgsrv.brooklynmuseum.org/collections/objects/CUR.47.88a-b_NegA_print_bw.jpg?width=400&quality=75"

    def test_license(self):
        assert self.result.license == License.CC_BY_NC_ND


class TestNonEgyptian:
    """Cypriot Juglet — non-Egyptian culture, Cyprus geography, provenance text."""

    @pytest.fixture(autouse=True)
    def setup(self, mapper):
        raw = _load_fixture("non_egyptian.json")
        self.result = mapper.map_to_canonical(raw)

    def test_id(self):
        assert self.result.id == "brooklyn-3198"

    def test_source_museum(self):
        assert self.result.source_museum == "brooklyn"

    def test_source_url(self):
        assert self.result.source_url == "https://www.brooklynmuseum.org/objects/3198"

    def test_source_id(self):
        assert self.result.source_id == "3198"

    def test_title(self):
        assert self.result.title == "Cypriot Base-Ring Juglet (Bilbil)"

    def test_description(self):
        assert "Undecorated jug" in self.result.description

    def test_object_type(self):
        assert self.result.object_type == "Vessel"

    def test_materials(self):
        assert self.result.materials == ["Clay", "slip"]

    def test_dimensions(self):
        assert self.result.dimensions == "5 13/16 x Diam. 2 13/16 in. (14.8 x 7.1 cm)"

    def test_period(self):
        assert self.result.period == "Late Cypriot IB Period"

    def test_dynasty_is_none(self):
        assert self.result.dynasty is None

    def test_bce_dates(self):
        assert self.result.date_start == -1577
        assert self.result.date_end == -1573

    def test_date_display(self):
        assert self.result.date_display == "ca. 1575–1475 B.C.E."

    def test_origin_site_raw(self):
        assert self.result.origin_site_raw == "Cyprus"

    def test_origin_certainty_place_made(self):
        assert self.result.origin_certainty == "made_in"

    def test_accession_number(self):
        assert self.result.accession_number == "00.164"

    def test_credit_line(self):
        assert self.result.credit_line == "Anonymous gift"

    def test_image_url(self):
        assert self.result.image_url == "https://brooklynmuseum.b-cdn.net/collections/objects/CUR.00.164_erg2.jpg"

    def test_thumbnail_url(self):
        assert self.result.thumbnail_url == "https://imgsrv.brooklynmuseum.org/collections/objects/CUR.00.164_erg2.jpg?width=400&quality=75"

    def test_license(self):
        assert self.result.license == License.CC_BY_NC_ND


class TestSparseNoImage:
    """Model of Hoe — sparse record, no image, no geography, no dynasty."""

    @pytest.fixture(autouse=True)
    def setup(self, mapper):
        raw = _load_fixture("sparse_no_image.json")
        self.result = mapper.map_to_canonical(raw)

    def test_id(self):
        assert self.result.id == "brooklyn-123351"

    def test_source_museum(self):
        assert self.result.source_museum == "brooklyn"

    def test_source_url(self):
        assert self.result.source_url == "https://www.brooklynmuseum.org/objects/123351"

    def test_source_id(self):
        assert self.result.source_id == "123351"

    def test_title(self):
        assert self.result.title == "Model of Hoe or Amulet"

    def test_description_is_none(self):
        assert self.result.description is None

    def test_object_type(self):
        assert self.result.object_type == "Model"

    def test_materials(self):
        assert self.result.materials == ["Limestone"]

    def test_dimensions(self):
        assert self.result.dimensions == "4 x 3/16 x 4 1/8 in. (10.2 x 0.5 x 10.5 cm)"

    def test_period(self):
        assert self.result.period == "Predynastic Period to Early Dynastic Period"

    def test_dynasty_is_none(self):
        assert self.result.dynasty is None

    def test_dates(self):
        assert self.result.date_start == -4400
        assert self.result.date_end == -2675

    def test_date_display(self):
        assert self.result.date_display == "ca. 4400–2675 B.C.E."

    def test_no_geography(self):
        assert self.result.origin_site_raw is None
        assert self.result.origin_certainty is None

    def test_accession_number(self):
        assert self.result.accession_number == "07.447.788"

    def test_credit_line(self):
        assert self.result.credit_line == "Charles Edwin Wilbour Fund"

    def test_no_image(self):
        assert self.result.image_url is None
        assert self.result.thumbnail_url is None

    def test_license_none_for_no_image(self):
        assert self.result.license == License.NONE


class TestReportedlyFrom:
    """Funerary Cone — Reportedly from Thebes, dynasty with qualifier, dimensions with \\r\\n."""

    @pytest.fixture(autouse=True)
    def setup(self, mapper):
        raw = _load_fixture("reportedly_from.json")
        self.result = mapper.map_to_canonical(raw)

    def test_id(self):
        assert self.result.id == "brooklyn-118436"

    def test_source_museum(self):
        assert self.result.source_museum == "brooklyn"

    def test_source_url(self):
        assert self.result.source_url == "https://www.brooklynmuseum.org/objects/118436"

    def test_source_id(self):
        assert self.result.source_id == "118436"

    def test_title(self):
        assert self.result.title == "Funerary Cone of King\u2019s Scribe, Ramose"

    def test_description(self):
        assert "Pottery funerary cone" in self.result.description

    def test_object_type(self):
        assert self.result.object_type == "Document"

    def test_materials(self):
        assert self.result.materials == ["Clay"]

    def test_dimensions_stripped(self):
        assert self.result.dimensions == "Diam. 3 15/16 x 7 1/16 in. (10 x 18 cm)"

    def test_period(self):
        assert self.result.period == "Late Period"

    def test_dynasty(self):
        assert self.result.dynasty == "Dynasty 25, or later"

    def test_dates(self):
        assert self.result.date_start == -664
        assert self.result.date_end == -332

    def test_date_display(self):
        assert self.result.date_display == "664–332 B.C.E."

    def test_origin_site_raw(self):
        assert self.result.origin_site_raw == "Thebes, Egypt"

    def test_origin_certainty_reportedly_from(self):
        assert self.result.origin_certainty == "uncertain"

    def test_accession_number(self):
        assert self.result.accession_number == "37.1931E"

    def test_credit_line(self):
        assert self.result.credit_line == "Charles Edwin Wilbour Fund"

    def test_image_url(self):
        assert self.result.image_url == "https://brooklynmuseum.b-cdn.net/collections/objects/CUR.37.1931E_37.1930E_GRPA_print_bw.JPG"

    def test_thumbnail_url(self):
        assert self.result.thumbnail_url == "https://imgsrv.brooklynmuseum.org/collections/objects/CUR.37.1931E_37.1930E_GRPA_print_bw.JPG?width=400&quality=75"

    def test_license(self):
        assert self.result.license == License.CC_BY_NC_ND
