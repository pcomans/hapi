"""Tests for the Harvard Art Museums mapper using real fixture data."""

import json
from pathlib import Path

import pytest

from pipeline.assets.normalize.harvard import HarvardMapper
from pipeline.types.sources import License

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "harvard"


def _load_fixture(name: str) -> dict:
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


@pytest.fixture
def mapper():
    return HarvardMapper()


class TestRichObject:
    """Horus Falcon — full metadata, period with dynasty, provenance, places, images."""

    @pytest.fixture(autouse=True)
    def setup(self, mapper):
        raw = _load_fixture("rich_object.json")
        self.result = mapper.map_to_canonical(raw)

    def test_id(self):
        assert self.result.id == "harvard-303839"

    def test_source_museum(self):
        assert self.result.source_museum == "harvard"

    def test_source_url(self):
        assert self.result.source_url == "https://www.harvardartmuseums.org/collections/object/303839"

    def test_source_id(self):
        assert self.result.source_id == "303839"

    def test_title(self):
        assert self.result.title == "Horus Falcon Wearing Crown of Upper and Lower Egypt with Uraeus"

    def test_description_is_none(self):
        assert self.result.description is None

    def test_object_type(self):
        assert self.result.object_type == "sculpture"

    def test_materials(self):
        assert self.result.materials == ["Leaded bronze, gold-alloy inlay around eye"]

    def test_dimensions(self):
        assert self.result.dimensions == "37.5 x 9.5 x 24.1 cm (14 3/4 x 3 3/4 x 9 1/2 in.)"

    def test_period_split_from_dynasty(self):
        assert self.result.period == "Late Period"

    def test_dynasty_split_from_period(self):
        assert self.result.dynasty == "Dynasty 26"

    def test_no_ruler(self):
        assert self.result.ruler_display_name is None

    def test_dates(self):
        assert self.result.date_start == -664
        assert self.result.date_end == -525

    def test_date_display(self):
        assert self.result.date_display == "mid 7th-late 6th century BCE"

    def test_origin_site_raw(self):
        assert self.result.origin_site_raw == "Ancient & Byzantine World, Africa, Egypt (Ancient)"

    def test_origin_certainty_is_none(self):
        assert self.result.origin_certainty is None

    def test_accession_number(self):
        assert self.result.accession_number == "1943.1118"

    def test_credit_line(self):
        assert self.result.credit_line == "Harvard Art Museums/Arthur M. Sackler Museum, Bequest of Grenville L. Winthrop"

    def test_image_url(self):
        assert "HUAM:DDC251071_dynmc" in self.result.image_url

    def test_thumbnail_url(self):
        assert "HUAM:DDC251071_dynmc" in self.result.thumbnail_url
        assert "width=400" in self.result.thumbnail_url

    def test_license(self):
        assert self.result.license == License.NON_COMMERCIAL_EDUCATIONAL


class TestSparseNoImage:
    """Relief fragment with Baboon — no image, no dates, no provenance, no places."""

    @pytest.fixture(autouse=True)
    def setup(self, mapper):
        raw = _load_fixture("sparse_no_image.json")
        self.result = mapper.map_to_canonical(raw)

    def test_id(self):
        assert self.result.id == "harvard-288555"

    def test_source_museum(self):
        assert self.result.source_museum == "harvard"

    def test_source_url(self):
        assert self.result.source_url == "https://www.harvardartmuseums.org/collections/object/288555"

    def test_title(self):
        assert self.result.title == "Relief fragment with Baboon"

    def test_description(self):
        assert "Baboon God Thoth" in self.result.description

    def test_object_type(self):
        assert self.result.object_type == "sculpture"

    def test_materials(self):
        assert self.result.materials == ["Light gray stone with black accretions on surface"]

    def test_dimensions(self):
        assert self.result.dimensions == "47 x 63.5 cm (18 1/2 x 25 in.)"

    def test_period(self):
        assert self.result.period == "New Kingdom"

    def test_no_dynasty(self):
        assert self.result.dynasty is None

    def test_no_dates(self):
        assert self.result.date_start is None
        assert self.result.date_end is None

    def test_date_display(self):
        assert self.result.date_display == "16th-11th century BCE"

    def test_no_origin_site(self):
        assert self.result.origin_site_raw is None

    def test_no_image(self):
        assert self.result.image_url is None

    def test_no_thumbnail(self):
        assert self.result.thumbnail_url is None

    def test_accession_number(self):
        assert self.result.accession_number == "1991.644.A"

    def test_credit_line(self):
        assert self.result.credit_line == "Harvard Art Museums/Arthur M. Sackler Museum, Bequest of Gerhardt Liebmann"

    def test_license_none_when_no_image(self):
        assert self.result.license == License.NONE


class TestMultilineMedium:
    """Fayum portrait — medium with \\r\\n delimiters, places with specific site, CE dates."""

    @pytest.fixture(autouse=True)
    def setup(self, mapper):
        raw = _load_fixture("multiline_medium.json")
        self.result = mapper.map_to_canonical(raw)

    def test_id(self):
        assert self.result.id == "harvard-219609"

    def test_source_museum(self):
        assert self.result.source_museum == "harvard"

    def test_source_url(self):
        assert self.result.source_url == "https://www.harvardartmuseums.org/collections/object/219609"

    def test_title(self):
        assert self.result.title == "Portrait of a woman"

    def test_description(self):
        assert "mummy portrait" in self.result.description

    def test_object_type(self):
        assert self.result.object_type == "painting"

    def test_materials_split_on_newlines(self):
        assert self.result.materials == [
            "Binder: Beeswax",
            "Pigments: Lead white, red and yellow ochres, carbon black, indigo, madder lake, green earth (celadonite), natrojarosite",
            "Support: Native Egyptian sycomore fig (Ficus sycomorus)",
        ]

    def test_dimensions(self):
        assert self.result.dimensions == "35.3 × 22.5 × 2 cm (13 7/8 × 8 7/8 × 13/16 in.)"

    def test_period(self):
        assert self.result.period == "Roman Imperial period, Middle"

    def test_no_dynasty(self):
        assert self.result.dynasty is None

    def test_dates_ce(self):
        assert self.result.date_start == 125
        assert self.result.date_end == 155

    def test_date_display(self):
        assert self.result.date_display == "c. 130-150 CE"

    def test_origin_site_raw(self):
        assert self.result.origin_site_raw == "Ancient & Byzantine World, Africa, Antinoopolis (Egypt)"

    def test_accession_number(self):
        assert self.result.accession_number == "1923.60"

    def test_credit_line(self):
        assert self.result.credit_line == "Harvard Art Museums/Arthur M. Sackler Museum, Gift of Dr. Denman W. Ross"

    def test_image_url(self):
        assert "HUAM:70813_dynmc" in self.result.image_url

    def test_thumbnail_url(self):
        assert "HUAM:70813_dynmc" in self.result.thumbnail_url

    def test_license(self):
        assert self.result.license == License.NON_COMMERCIAL_EDUCATIONAL


class TestPlacesAndDates:
    """Temple Relief of Queen Arsinoe II — places, BCE dates, provenance."""

    @pytest.fixture(autouse=True)
    def setup(self, mapper):
        raw = _load_fixture("places_and_dates.json")
        self.result = mapper.map_to_canonical(raw)

    def test_id(self):
        assert self.result.id == "harvard-289668"

    def test_source_museum(self):
        assert self.result.source_museum == "harvard"

    def test_source_url(self):
        assert self.result.source_url == "https://www.harvardartmuseums.org/collections/object/289668"

    def test_title(self):
        assert self.result.title == "Temple Relief of Queen Arsinoe II"

    def test_object_type(self):
        assert self.result.object_type == "architectural element"

    def test_materials(self):
        assert self.result.materials == ["Limestone, with red ocher, charcoal black, and Egyptian blue on chalk"]

    def test_dimensions(self):
        assert self.result.dimensions == "42.5 cm h x 57.7 cm w x 7.5 cm d (16 3/4 x 22 11/16 x 2 15/16 in.)"

    def test_period(self):
        assert self.result.period == "Ptolemaic period"

    def test_no_dynasty(self):
        assert self.result.dynasty is None

    def test_dates(self):
        assert self.result.date_start == -269
        assert self.result.date_end == -260

    def test_date_display(self):
        assert self.result.date_display == "after 270 BCE"

    def test_origin_site_raw(self):
        assert self.result.origin_site_raw == "Ancient & Byzantine World, Africa, Egypt (Ancient)"

    def test_accession_number(self):
        assert self.result.accession_number == "1983.96"

    def test_credit_line(self):
        assert "Samuel H. Lin" in self.result.credit_line

    def test_image_url(self):
        assert "HUAM:DDC103438_dynmc" in self.result.image_url

    def test_thumbnail_url(self):
        assert "HUAM:DDC103438_dynmc" in self.result.thumbnail_url

    def test_license(self):
        assert self.result.license == License.NON_COMMERCIAL_EDUCATIONAL
