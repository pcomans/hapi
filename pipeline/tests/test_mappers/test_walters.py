"""Tests for the Walters Art Museum mapper and ingest using real fixture data.

Each fixture is one object as the ingest stores it: its `art.csv` row and its `media.csv` rows
(data commit f7531ed751ac2c138eeb6f923a3b4fd325d78adf). Each fixture's expected record lists
every populated canonical field; every other field must be None.
"""

import json
from pathlib import Path

import pytest

from pipeline.assets.ingest import walters as ingest
from pipeline.assets.normalize.walters import WaltersMapper, collection_codes, is_egyptian
from pipeline.types.canonical import CanonicalArtifact

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "walters"


def _load_fixture(name: str) -> dict:
    with open(FIXTURES_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _with_object(raw: dict, **fields) -> dict:
    return {**raw, "object": {**raw["object"], **fields}}


EXPECTED = {
    # Relief Fragment — a hyphenated pair of rulers stays as written.
    "hyphenated_reign.json": {
        "id": "walters-1605",
        "source_museum": "walters",
        "source_url": "https://purl.thewalters.org/art/22.216",
        "source_id": "1605",
        "title": "Relief Fragment Showing a Priest with an Incense Burner",
        "object_type": "reliefs",
        "materials": ["limestone"],
        "dimensions": "H: 13 3/16 x W: 14 in. (33.5 x 35.5 cm)",
        "dynasty": "26th Dynasty",
        "ruler_display_name": "Psametik I-Necho II",
        "date_start": -676,
        "date_end": -638,
        "date_display": "ca. 664-610 BCE (Late Period, 26th dynasty, reign of Psamtek I)",
        "provenance": "Dikran Kelekian, New York and Paris [date and mode of acquisition unknown]; Henry Walters, Baltimore, 1929, by purchase; Walters Art Museum, 1931, by bequest.",
        "accession_number": "22.216",
        "credit_line": "Walters Art Museum, 1931, by bequest.",
        "image_url": "https://art.thewalters.org/images/raw/PS1_22.216_Fnt_DD_T08.jpg",
        "thumbnail_url": "https://art.thewalters.org/images/raw/PS1_22.216_Fnt_DD_T08.jpg",
        "license": "cc0",
    },
    # Head of Hatshepsut (?) — dated modern (a forgery), filed in the Egyptian collection.
    "modern_object.json": {
        "id": "walters-24708",
        "source_museum": "walters",
        "source_url": "https://purl.thewalters.org/art/22.77",
        "source_id": "24708",
        "title": "Head of Hatshepsut (?)",
        "object_type": "figurines; statues",
        "materials": ["limestone, red and black paint"],
        "dimensions": "H: 5 5/8 × W: 4 1/8 × D: 3 3/8 in. (14.3 × 10.5 × 8.5 cm)Mount: H: 10 5/8 × W: 6 5/16 × D: 4 1/16 in. (27 × 16 × 10.3 cm)",
        "dynasty": "18th Dynasty",
        "date_start": 1900,
        "date_end": 1930,
        "date_display": "early 20th century (modern)",
        "provenance": "Dikran Kelekian, New York and Paris [date and mode of acquisition unknown] [said to be from Deir el-Bahri]; Henry Walters, Baltimore, 1931, by purchase; Walters Art Museum, 1931, by bequest.",
        "accession_number": "22.77",
        "credit_line": "Walters Art Museum, 1931, by bequest.",
        "image_url": "https://art.thewalters.org/images/raw/PS4_22.77_DD_AT23_44924-tms.jpg",
        "thumbnail_url": "https://art.thewalters.org/images/raw/PS4_22.77_DD_AT23_44924-tms.jpg",
        "license": "cc0",
    },
    # Kneeling King — in no collection, culture Egyptian; no dynasty.
    "no_collection_egyptian_culture.json": {
        "id": "walters-1200",
        "source_museum": "walters",
        "source_url": "https://purl.thewalters.org/art/54.2103",
        "source_id": "1200",
        "title": "Kneeling King",
        "object_type": "statuettes (statues)",
        "materials": ["bronze"],
        "dimensions": "Overall: 6 7/8 in. (17.5 cm)",
        "date_start": -760,
        "date_end": -343,
        "date_display": "mid 8th-mid 4th century BCE (Late Period)",
        "provenance": "Dikran Kelekian, Paris and New York [date and mode of acquisition unknown] [said to have been found at the pyramids]; Henry Walters, Baltimore, 1911, by purchase; Walters Art Museum, 1931, by bequest.",
        "accession_number": "54.2103",
        "credit_line": "Walters Art Museum, 1931, by bequest.",
        "image_url": "https://art.thewalters.org/images/raw/ARG_54.2103_3Qtr_BW.jpg",
        "thumbnail_url": "https://art.thewalters.org/images/raw/ARG_54.2103_3Qtr_BW.jpg",
        "license": "cc0",
    },
    # Crocodile with a Falcon Head — no image marked primary: the lowest rank.
    "no_primary_image.json": {
        "id": "walters-37893",
        "source_museum": "walters",
        "source_url": "https://purl.thewalters.org/art/22.347",
        "source_id": "37893",
        "title": "Statue of a Crocodile with the Head of a Falcon",
        "object_type": "statues ; sculpture",
        "materials": ["steatite"],
        "dimensions": "H: 3 1/4 x W: 3 1/2 x D: 10 9/16 in. (8.3 x 8.8 x 26.8 cm)",
        "dynasty": "30th-early Ptolemaic Dynasty",
        "date_start": -412,
        "date_end": -250,
        "date_display": "ca. 380-250 BCE (Late Period (30th dynasty)-early Ptolemaic Period)",
        "provenance": "Dikran Kelekian, New York and Paris [date and mode of acquisition unknown]; Henry Walters, Baltimore, 1924, by purchase; Walters Art Museum, 1931, by bequest.",
        "accession_number": "22.347",
        "credit_line": "Walters Art Museum, 1931, by bequest.",
        "image_url": "https://art.thewalters.org/images/raw/PS1_22.347_Rt_DD_T08.jpg",
        "thumbnail_url": "https://art.thewalters.org/images/raw/PS1_22.347_Rt_DD_T08.jpg",
        "license": "cc0",
    },
    # Fatimid plaque — Islamic collection, culture Egyptian-Islamic (out of scope, still mappable).
    "other_collection.json": {
        "id": "walters-74",
        "source_museum": "walters",
        "source_url": "https://purl.thewalters.org/art/71.562",
        "source_id": "74",
        "title": "Plaque with Figural Scene",
        "object_type": "reliefs; plaques; ivories",
        "materials": ["ivory (elephant tusk)"],
        "dimensions": "H: 2 7/8 x W: 3 1/4 x D: 3/8 in. (7.3 x 8.2 x 0.9 cm)",
        "dynasty": "Fatimid Dynasty",
        "date_start": 1001,
        "date_end": 1200,
        "date_display": "11th-12th century (Fatimid)",
        "provenance": "Dikran Kelekian, New York and Paris [date and mode of acquisition unknown];  Henry Walters, Baltimore [date of acquisition unknown], by purchase;  Walters Art Museum, 1931, by bequest.",
        "accession_number": "71.562",
        "credit_line": "Walters Art Museum, 1931, by bequest.",
        "image_url": "https://art.thewalters.org/images/raw/PL1_71.562_Fnt_TR_T97.jpg",
        "thumbnail_url": "https://art.thewalters.org/images/raw/PL1_71.562_Fnt_TR_T97.jpg",
        "license": "cc0",
    },
    # Scarab of Shepenwepet — a Reign listing two rulers keeps its inner dates; nine images.
    "reign_list.json": {
        "id": "walters-24458",
        "source_museum": "walters",
        "source_url": "https://purl.thewalters.org/art/42.48",
        "source_id": "24458",
        "title": "Scarab with Cat and Title of Shepenwepet",
        "object_type": "scarabs; amulets",
        "materials": ["light beige faience with green-blue glaze"],
        "dimensions": "H: 3/8 x W: 9/16 x L: 11/16 in. (0.9 x 1.4 x 1.8 cm)",
        "dynasty": "25th-26th Dynasty",
        "ruler_display_name": "Shabako (715-700 BC), Psammetichus I",
        "date_start": -712,
        "date_end": -656,
        "date_display": "ca. 700-656 BCE (Third Intermediate-Late Period)",
        "provenance": "Henry Walters, Baltimore [date and mode of acquisition unknown]; Walters Art Museum, 1931, by bequest.",
        "accession_number": "42.48",
        "credit_line": "Walters Art Museum, 1931, by bequest.",
        "image_url": "https://art.thewalters.org/images/raw/CUR_42.48_Back_DD_RS2009.jpg",
        "thumbnail_url": "https://art.thewalters.org/images/raw/CUR_42.48_Back_DD_RS2009.jpg",
        "license": "cc0",
    },
    # Vase with Names of Amenhotep III and Queen Tiye — reign, dynasty, CC0 primary image.
    "rich_object.json": {
        "id": "walters-481",
        "source_museum": "walters",
        "source_url": "https://purl.thewalters.org/art/48.403",
        "source_id": "481",
        "title": "Vase with Names of Amenhotep III and Queen Tiye",
        "object_type": "vases",
        "materials": ["Egyptian faience with dark blue glaze"],
        "dimensions": "H: 2 13/16 x Diam at base: 2 5/16 in. (7.2 x 5.8 cm); Diam at top: 1 7/8 in. (4.8 cm)",
        "dynasty": "18th Dynasty",
        "ruler_display_name": "Amenhotep III",
        "date_start": -1382,
        "date_end": -1358,
        "date_display": "ca. 1370 BCE (New Kingdom, 18th dynasty, reign of Amenhotep III)",
        "provenance": "Rev. William MacGregor, Tamworth, Staffordshire, by 1922; Sale, Sotheby, Wilkinson & Hodge, London, June 26-29 and July 4-6, 1922, no. 272; Dikran Kelekian, Paris and New York, 1922, by purchase; Henry Walters, Baltimore, 1923, by purchase; Walters Art Museum, 1931, by bequest.",
        "accession_number": "48.403",
        "credit_line": "Walters Art Museum, 1931, by bequest.",
        "image_url": "https://art.thewalters.org/images/raw/PS1_48.403_Fnt_DD_T08.jpg",
        "thumbnail_url": "https://art.thewalters.org/images/raw/PS1_48.403_Fnt_DD_T08.jpg",
        "license": "cc0",
    },
    # Amulet of Horus the Child — collection codes run together ("EGYJWL").
    "run_together_codes.json": {
        "id": "walters-24014",
        "source_museum": "walters",
        "source_url": "https://purl.thewalters.org/art/48.1596",
        "source_id": "24014",
        "title": "Amulet of Horus the Child",
        "object_type": "amulets; figurines",
        "materials": ["Egyptian faience with green-blue glaze"],
        "dimensions": "H: 1 3/16 x W: 1/4 x D: 7/16 in. (3.08 x 0.67 x 1.07 cm)",
        "date_start": -1550,
        "date_end": -1070,
        "date_display": "mid 16th-early 11th century BCE (New Kingdom (?))",
        "provenance": "Henry Walters, Baltimore [date and mode of acquisition unknown]; Walters Art Museum, 1931, by bequest.",
        "accession_number": "48.1596",
        "credit_line": "Walters Art Museum, 1931, by bequest.",
        "image_url": "https://art.thewalters.org/images/raw/CUR_48.1596_Fnt_DD_RS2009.jpg",
        "thumbnail_url": "https://art.thewalters.org/images/raw/CUR_48.1596_Fnt_DD_RS2009.jpg",
        "license": "cc0",
    },
    # Cylinder Seal — no media rows, so no image and no license.
    "sparse_no_image.json": {
        "id": "walters-1358",
        "source_museum": "walters",
        "source_url": "https://purl.thewalters.org/art/42.178",
        "source_id": "1358",
        "title": "Cylinder Seal with an Offering Scene and Hieroglyphs",
        "object_type": "cylinder seals (artifacts)",
        "materials": ["steatite"],
        "dimensions": "H: 9/16 x W: 1/2 in. (1.4 x 1.3 cm)",
        "date_start": -2960,
        "date_end": -2649,
        "date_display": "ca. 2960-2649 BCE (Early Dynastic)",
        "provenance": "Henry Walters, Baltimore, [date and mode of acquisition unknown]; Walters Art Museum, 1931, by bequest.",
        "accession_number": "42.178",
        "credit_line": "Walters Art Museum, 1931, by bequest.",
        "license": "none",
    },
    # Ostracon with a Royal Head — the final "(?)" holds no digit, so the dates before it stay.
    "uncertain_reign.json": {
        "id": "walters-5104",
        "source_museum": "walters",
        "source_url": "https://purl.thewalters.org/art/32.1",
        "source_id": "5104",
        "title": "Ostracon with a Royal Head",
        "object_type": "ostraka; sketches",
        "materials": ["limestone with ink"],
        "dimensions": "H: 7 5/16 x W: 5 3/4 x D: 1 1/8 in. (18.5 x 14.6 x 2.9 cm)",
        "dynasty": "19th Dynasty",
        "ruler_display_name": "Seti I (1290-1279/8) (?)",
        "date_start": -1292,
        "date_end": -1268,
        "date_display": "ca. 1280 BCE (New Kingdom, 19th dynasty)",
        "provenance": "Dikran Kelekian, Paris and New York [date and mode of acquisition unknown]; Henry Walters, Baltimore, 1923, by purchase; Walters Art Museum, 1931, by bequest.",
        "accession_number": "32.1",
        "credit_line": "Walters Art Museum, 1931, by bequest.",
        "image_url": "https://art.thewalters.org/images/raw/PS1_32.1_Fnt_DD_T07.jpg",
        "thumbnail_url": "https://art.thewalters.org/images/raw/PS1_32.1_Fnt_DD_T07.jpg",
        "license": "cc0",
    },
}

DESCRIPTIONS = {
    "hyphenated_reign.json": "<p>A mortuary priest, traditionally clothed in animal skin a",
    "modern_object.json": "<p>This head is the portrait of a king, perhaps Hatshepsut. ",
    "no_collection_egyptian_culture.json": "<p>The king kneels with his torso inclined forward and his a",
    "no_primary_image.json": "<p>This may represent the god Horus the Elder, who is occasi",
    "other_collection.json": "<p>This pentagonal plaque depicts a running man and his dog,",
    "reign_list.json": "<p>This scaraboid faience amulet is inscribed on the bottom ",
    "rich_object.json": "<p>Royalty of the 18th Dynasty commissioned luxury goods in ",
    "run_together_codes.json": "<p>Harpokrates (Horus the Child) is shown standing with his ",
    "sparse_no_image.json": "<p>This cylinder seal depicts a figure seated, arms extended",
    "uncertain_reign.json": "<p>This sketch depicts a king wearing the \"blue crown,\" a co",
}


def test_every_fixture_is_tested():
    assert sorted(EXPECTED) == sorted(DESCRIPTIONS) == sorted(p.name for p in FIXTURES_DIR.glob("*.json"))


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_every_field(name):
    raw = _load_fixture(name)
    result = WaltersMapper().map_to_canonical(raw).model_dump(mode="json")
    description = result.pop("description")
    assert description[:60] == DESCRIPTIONS[name]
    assert description == raw["object"]["Description"].strip()
    expected = {field: None for field in CanonicalArtifact.model_fields if field != "description"}
    expected.update(EXPECTED[name])
    assert result == expected


@pytest.mark.parametrize("name, egyptian", [
    ("rich_object.json", True),
    ("reign_list.json", True),
    ("uncertain_reign.json", True),
    ("hyphenated_reign.json", True),
    ("modern_object.json", True),               # dated modern, but the museum files it as Egyptian
    ("no_primary_image.json", True),
    ("sparse_no_image.json", True),
    ("run_together_codes.json", True),          # "EGYJWL"
    ("no_collection_egyptian_culture.json", True),
    ("other_collection.json", False),           # Islamic collection, culture "Egyptian-Islamic"
])
def test_is_egyptian(name, egyptian):
    assert is_egyptian(_load_fixture(name)) == egyptian


def test_run_together_codes_are_read_as_two():
    assert collection_codes(_load_fixture("run_together_codes.json")) == ("EGY", "JWL")
    assert collection_codes(_load_fixture("other_collection.json")) == ("ISL",)
    assert collection_codes(_load_fixture("no_collection_egyptian_culture.json")) == ()


def test_the_unlisted_prehistoric_code_is_known():
    raw = _with_object(_load_fixture("rich_object.json"), CollectionID="EGY|PRE")
    assert (collection_codes(raw), is_egyptian(raw)) == (("EGY", "PRE"), True)


def test_an_unknown_collection_code_raises():
    raw = _with_object(_load_fixture("rich_object.json"), CollectionID="EGY|XYZ")
    with pytest.raises(ValueError, match=r"walters-481: unknown collection codes \['XYZ'\]"):
        is_egyptian(raw)


def test_no_collection_and_another_culture_raises():
    raw = _with_object(_load_fixture("no_collection_egyptian_culture.json"), Culture="Egypto-Roman")
    with pytest.raises(ValueError, match="walters-1200: in no collection, with culture 'Egypto-Roman'"):
        is_egyptian(raw)


@pytest.mark.parametrize("reign, ruler", [
    ("Hatshepsut (1479-1457)", "Hatshepsut"),
    ("Thutmose III", "Thutmose III"),
    ("King Shabaqo (715-700 BC)", "King Shabaqo"),
    ("Amenophis IV/Akhenaten-Smenkhkare (1352-1336 BC)", "Amenophis IV/Akhenaten-Smenkhkare"),
    ("Tutankhamen or Ay", "Tutankhamen or Ay"),
    ("", None),
])
def test_ruler_display_name_is_the_reign_without_its_dates(reign, ruler):
    raw = _with_object(_load_fixture("rich_object.json"), Reign=reign)
    assert WaltersMapper().map_to_canonical(raw).ruler_display_name == ruler


def test_two_primary_images_raise():
    raw = _load_fixture("reign_list.json")
    raw = {**raw, "media": [{**m, "IsPrimary": "1"} for m in raw["media"]]}
    with pytest.raises(ValueError, match="walters-24458: 9 primary images"):
        WaltersMapper().map_to_canonical(raw)


def test_no_primary_image_and_a_tied_first_rank_raises():
    raw = _load_fixture("no_primary_image.json")
    raw = {**raw, "media": [{**m, "Rank": "1"} for m in raw["media"]]}
    with pytest.raises(ValueError, match="walters-37893: no primary image and a tied first rank"):
        WaltersMapper().map_to_canonical(raw)


def test_a_pdf_is_not_an_image():
    raw = _load_fixture("rich_object.json")
    pdf = {**raw["media"][0], "MediaType": "PDF", "ImageURL": "https://art.thewalters.org/files/pdf/", "Filename": ""}
    result = WaltersMapper().map_to_canonical({**raw, "media": [pdf]})
    assert (result.image_url, result.thumbnail_url, result.license.value) == (None, None, "none")


class _Response:
    def __init__(self, content: bytes = b"", payload=None):
        self.content = content
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


ART = ("ObjectID,Title,CollectionID,Culture\n"
       "1,Vase,EGY,Egyptian\n"
       "2,Bowl,ISL,Egyptian-Islamic\n"
       "3,Plate,REN,Italian\n"
       "4,Seal,,Egyptian\n"
       '5,"Amulet, with a comma",EGYJWL,\n')
MEDIA = ("ObjectID,ImageURL,IsPrimary\n"
         "4,https://example.org/4.jpg,1\n"
         "1,https://example.org/1b.jpg,0\n"
         "3,https://example.org/3.jpg,1\n"
         "1,https://example.org/1a.jpg,1\n")


def _files(monkeypatch, files: dict[str, str]):
    urls = []

    def get(url, timeout):
        urls.append(url)
        if url.startswith("https://api.github.com/"):
            return _Response(payload={"sha": "abc123"})
        return _Response(content=files[url.rsplit("/", 1)[1]].encode("utf-8"))

    monkeypatch.setattr(ingest.requests, "get", get)
    return urls


def test_the_ingest_reads_both_files_at_one_commit_and_keeps_the_candidates(monkeypatch):
    urls = _files(monkeypatch, {"art.csv": ART, "media.csv": MEDIA})
    commit = ingest.resolve_commit()
    art, _ = ingest.read_csv(commit, "art.csv")
    media, _ = ingest.read_csv(commit, "media.csv")
    records = ingest.candidate_records(art, media)
    assert urls == [
        "https://api.github.com/repos/WaltersArtMuseum/api-thewalters-org/commits/main",
        "https://raw.githubusercontent.com/WaltersArtMuseum/api-thewalters-org/abc123/art.csv",
        "https://raw.githubusercontent.com/WaltersArtMuseum/api-thewalters-org/abc123/media.csv",
    ]
    # The Egyptian collection's code (also run together), or a culture naming Egypt; media in file order.
    assert [(r["object"]["ObjectID"], [m["ImageURL"] for m in r["media"]]) for r in records] == [
        ("1", ["https://example.org/1b.jpg", "https://example.org/1a.jpg"]),
        ("2", []),
        ("4", ["https://example.org/4.jpg"]),
        ("5", []),
    ]
    assert records[3]["object"] == {"ObjectID": "5", "Title": "Amulet, with a comma", "CollectionID": "EGYJWL",
                                    "Culture": ""}


def test_a_repeated_object_raises():
    art = [{"ObjectID": "1", "CollectionID": "EGY", "Culture": ""}] * 2
    with pytest.raises(ValueError, match="art.csv repeats an ObjectID"):
        ingest.candidate_records(art, [])


@pytest.mark.parametrize("text", [
    "ObjectID,Title\n1,Vase,extra\n",   # more fields than the header
    "ObjectID,Title\n1\n",              # fewer
])
def test_a_row_that_does_not_fit_the_header_raises(monkeypatch, text):
    _files(monkeypatch, {"art.csv": text})
    with pytest.raises(ValueError, match="art.csv row 2 does not have the header's fields"):
        ingest.read_csv("abc123", "art.csv")
