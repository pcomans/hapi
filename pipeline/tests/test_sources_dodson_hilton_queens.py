"""Structural value-assertion tests for Dodson & Hilton queens extract.

Per rule 5: every populated field on a fixture row is asserted.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

SOURCE_DIR = (
    Path(__file__).parent.parent
    / "pipeline"
    / "authority"
    / "sources"
    / "dodson-hilton-queens"
)
JSONL = SOURCE_DIR / "reconciled.jsonl"

EDITION = "Thames & Hudson 2004 hardback"
PDF_PAGES = "126-130"
SUB_PERIOD = "The Power and the Glory"
CITATION = {"pdf_pages": PDF_PAGES, "edition": EDITION}


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    return tuple(json.loads(line) for line in JSONL.read_text().splitlines() if line.strip())


def _row(dh_id: str) -> dict:
    hits = [r for r in _rows() if r["dh_id"] == dh_id]
    if len(hits) != 1:
        raise AssertionError(f"expected 1 row for {dh_id!r}, got {len(hits)}")
    return hits[0]


def _assert_full_row(dh_id: str, expected: dict) -> None:
    """Assert full-row equality per rule 5. Every schema field must be
    present in `expected`; the row must match key-for-key, value-for-value.
    """
    row = _row(dh_id)
    schema_fields = {
        "dh_id", "name", "alt_names", "roles", "sex",
        "spouse_names", "father_name", "mother_name", "children_names",
        "dynasty", "sub_period", "unplaced",
        "notes", "source_citation",
    }
    missing = schema_fields - expected.keys()
    assert not missing, f"{dh_id}: test fixture missing schema field(s) {missing}"
    extra = expected.keys() - schema_fields
    assert not extra, f"{dh_id}: test fixture has non-schema field(s) {extra}"
    for k in schema_fields:
        assert row[k] == expected[k], (
            f"{dh_id}.{k}: stored {row[k]!r} != expected {expected[k]!r}"
        )


# ---------------------------------------------------------------------------
# Cross-file invariants
# ---------------------------------------------------------------------------


def test_row_count() -> None:
    """Brief Lives (47) + Unplaced (12) = 59 entries across printed pp. 137–141."""
    assert len(_rows()) == 59, len(_rows())


def test_dh_id_is_unique() -> None:
    """No duplicate dh_id in the extract."""
    ids = [r["dh_id"] for r in _rows()]
    assert len(ids) == len(set(ids)), "duplicate dh_id detected"


def test_every_row_has_complete_citation() -> None:
    for r in _rows():
        assert r["source_citation"] == CITATION, r


def test_every_row_has_dyn18_and_sub_period() -> None:
    for r in _rows():
        assert r["dynasty"] == 18, r
        assert r["sub_period"] == SUB_PERIOD, r


def test_unplaced_set_is_the_twelve_expected_ids() -> None:
    """D&H's 'Unplaced' sub-block on printed p. 141 has exactly 12 entries."""
    unplaced = [r for r in _rows() if r["unplaced"]]
    assert len(unplaced) == 12, f"expected 12 unplaced, got {len(unplaced)}"
    assert {r["dh_id"] for r in unplaced} == {
        "Amenemhat Q", "Henut Q", "Henutiunu", "Merybennu", "Meryetptah A",
        "Nebetnehat A", "Sithori", "Tatau", "Thutmose Q", "Ti", "Wiay A",
        "[...]pentepkau",
    }


def test_unplaced_rows_sort_last_in_reconciled_jsonl() -> None:
    """The 12 unplaced rows must occupy the trailing 12 positions of
    `reconciled.jsonl` — merge.py's sort groups them into a final bin so
    the file reads as placed-alphabetical, then unplaced-alphabetical.
    This is a regression on the issue code-reviewer flagged on the first
    sort key implementation (which pushed only `Q`-suffix and `[`-prefix
    ids, leaving `Henutiunu`, `Sithori`, etc. interleaved in the main
    alphabetical block).
    """
    rows = _rows()
    for r in rows[:-12]:
        assert r["unplaced"] is False, r["dh_id"]
    for r in rows[-12:]:
        assert r["unplaced"] is True, r["dh_id"]


def test_sex_inference_covers_every_row() -> None:
    for r in _rows():
        assert r["sex"] in ("male", "female"), r


def test_role_code_set_spans_the_known_codes() -> None:
    """Every known D&H code in this chunk appears on at least one row."""
    all_codes: set[str] = set()
    for r in _rows():
        all_codes.update(r["roles"])
    for expected in ["KM", "KW", "KGW", "GW", "KSis", "KD", "KSon", "EKSon"]:
        assert expected in all_codes, f"expected code {expected!r} never extracted"


def test_kings_cross_referenced_in_bold_caps_not_extracted_as_entries() -> None:
    """`AMENHOTEP II`, `AMENHOTEP III`, `THUTMOSE IV` are cross-references
    inside other rows' prose, not Brief Lives entries of their own.
    """
    king_refs = {"AMENHOTEP II", "AMENHOTEP III", "THUTMOSE IV"}
    for r in _rows():
        assert r["dh_id"] not in king_refs, r


# ---------------------------------------------------------------------------
# Full-row fixture assertions (per rule 5)
# ---------------------------------------------------------------------------


def test_ahmes_b_full_row() -> None:
    """Wife of Thutmose I / mother of Hatshepsut — KM, KGW, KSis."""
    _assert_full_row("Ahmes B", {
        "dh_id": "Ahmes B",
        "name": "Ahmes B",
        "alt_names": [],
        "roles": ["KM", "KGW", "KSis"],
        "sex": "female",
        "spouse_names": ["Thutmose I"],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Hatshepsut"],
        "dynasty": 18,
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Wife of Thutmose I; known from a range of monuments, principally "
            "those of her daughter, Hatshepsut, but also from other material, "
            "including a statue of her mortuary priest, Nakht, from Karnak."
        ),
        "source_citation": CITATION,
    })


def test_hatshepsut_d_full_row() -> None:
    """D&H's Hatshepsut-as-queen-and-later-king carries five role codes."""
    _assert_full_row("Hatshepsut D", {
        "dh_id": "Hatshepsut D",
        "name": "Hatshepsut D",
        "alt_names": [],
        "roles": ["GW", "KGW", "KD", "KSis", "UWC"],
        "sex": "female",
        "spouse_names": ["Thutmose II"],
        "father_name": "Thutmose I",
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Daughter of Thutmose I, wife of Thutmose II and later king. A "
            "range of monuments date to her period as queen, and also as "
            "regent for Thutmose III. These include inscriptions from Karnak, "
            "Nubia and Sinai, and an (unused) tomb and sarcophagus in the "
            "Wadi Siqqat Taqa el-Zeide at Thebes."
        ),
        "source_citation": CITATION,
    })


def test_iset_a_full_row() -> None:
    """Mother of Thutmose III. Note: Iset A and Iset B are distinct; see test below."""
    _assert_full_row("Iset A", {
        "dh_id": "Iset A",
        "name": "Iset A",
        "alt_names": [],
        "roles": ["GW", "KM", "KW", "KGW"],
        "sex": "female",
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Thutmose III"],
        "dynasty": 18,
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Mother of Thutmose III; she was given the title of KGW during "
            "his reign, as well as GW after her death. Possessor of a statue "
            "from Karnak, and mentioned a number of times on her son's "
            "funerary monuments and equipment."
        ),
        "source_citation": CITATION,
    })


def test_iset_b_full_row() -> None:
    """Daughter of Thutmose III + Meryetre-Hatshepsut — distinct from Iset A."""
    _assert_full_row("Iset B", {
        "dh_id": "Iset B",
        "name": "Iset B",
        "alt_names": [],
        "roles": ["KD"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Thutmose III",
        "mother_name": "Meryetre-Hatshepsut",
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Daughter of Thutmose III and Meryetre-Hatshepsut. Represented on "
            "the statue of her grandmother, Huy, in the British Museum."
        ),
        "source_citation": CITATION,
    })


def test_mutemwia_full_row() -> None:
    """Wife of Thutmose IV, mother of Amenhotep III — flagship Power-and-Glory queen."""
    _assert_full_row("Mutemwia", {
        "dh_id": "Mutemwia",
        "name": "Mutemwia",
        "alt_names": [],
        "roles": ["KGW", "KM"],
        "sex": "female",
        "spouse_names": ["Thutmose IV"],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Amenhotep III"],
        "dynasty": 18,
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Wife of Thutmose IV and mother of Amenhotep III; shown in the "
            "'divine birth' scenes of her son in Luxor temple. A statue of her "
            "probably came from his mortuary temple, with a figure of her in "
            "a boat found adjacent to the granite sanctuary of the Karnak "
            "temple (British Museum); she is also represented with her son on "
            "the Colossi of Memnon and in the tomb of Heqareshu (TT226, now "
            "in the Luxor Museum)."
        ),
        "source_citation": CITATION,
    })


def test_mutneferet_a_full_row() -> None:
    """Wife of Thutmose I / mother of Thutmose II. Hedged father_name
    ("probable daughter of Ahmose I") preserved verbatim.
    """
    _assert_full_row("Mutneferet A", {
        "dh_id": "Mutneferet A",
        "name": "Mutneferet A",
        "alt_names": [],
        "roles": ["KM", "KW", "KSis", "KD"],
        "sex": "female",
        "spouse_names": ["Thutmose I"],
        "father_name": "Ahmose I (probable)",
        "mother_name": None,
        "children_names": ["Thutmose II"],
        "dynasty": 18,
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Wife of Thutmose I, mother of Thutmose II and probable daughter "
            "of Ahmose I. Represented by the leg of her son on a colossus in "
            "front of the south face of the Eighth Pylon, in the temple of "
            "Thutmose III at Deir el-Bahari and on a stela found near the "
            "Ramesseum. She was also the owner of a statue found in the "
            "chapel of Wadjmose."
        ),
        "source_citation": CITATION,
    })


def test_tiaa_a_full_row_with_egyptologist_override_applied() -> None:
    """Tiaa A's `notes` was corrected by fix_rows.py to restore the article
    "a" in "including a number of usurpations" (Gemini OCR had dropped it
    and left a stray colon). This test locks in the corrected verbatim-
    prose and would break if fix_rows.py stopped running.
    """
    _assert_full_row("Tiaa A", {
        "dh_id": "Tiaa A",
        "name": "Tiaa A",
        "alt_names": [],
        "roles": ["KGW", "KM", "GW"],
        "sex": "female",
        "spouse_names": ["Amenhotep II"],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Thutmose IV"],
        "dynasty": 18,
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Wife of Amenhotep II and mother of Thutmose IV. A number of "
            "monuments were created for her by the latter at Giza, Thebes and "
            "the Fayoum, including a number of usurpations of material "
            "belonging to Meryetre-Hatshepsut. She was buried in tomb KV32, "
            "where many fragments of her funerary equipment have been found; "
            "some material was washed by floodwater into the adjacent tomb "
            "KV47, where it was for a long time thought to belong to a "
            "like-named mother of Siptah."
        ),
        "source_citation": CITATION,
    })


def test_menhet_full_row() -> None:
    """One of the three Syrian wives of Thutmose III buried together."""
    _assert_full_row("Menhet", {
        "dh_id": "Menhet",
        "name": "Menhet",
        "alt_names": [],
        "roles": ["KW"],
        "sex": "female",
        "spouse_names": ["Thutmose III"],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Wife of Thutmose III, probably of Syrian extraction. Buried in "
            "a tomb in Wadi Gabbanet el-Qurud together with Menwi and Merti; "
            "much of the funerary equipment is now in the Metropolitan "
            "Museum of Art."
        ),
        "source_citation": CITATION,
    })


def test_menwi_full_row() -> None:
    _assert_full_row("Menwi", {
        "dh_id": "Menwi",
        "name": "Menwi",
        "alt_names": [],
        "roles": ["KW"],
        "sex": "female",
        "spouse_names": ["Thutmose III"],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Wife of Thutmose III, probably of Syrian extraction. Buried with "
            "Menhet and Merti."
        ),
        "source_citation": CITATION,
    })


def test_merti_full_row() -> None:
    _assert_full_row("Merti", {
        "dh_id": "Merti",
        "name": "Merti",
        "alt_names": [],
        "roles": ["KW"],
        "sex": "female",
        "spouse_names": ["Thutmose III"],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Wife of Thutmose III, probably of Syrian extraction. Buried with "
            "Menhet and Menwi."
        ),
        "source_citation": CITATION,
    })


def test_pyihia_full_row() -> None:
    """Regular placed KD reburied during the 21st Dynasty — tests that the
    repeated reburial-prose stencil doesn't collapse to `unplaced: true`.
    (Pyihia is a placed daughter of Thutmose IV; Wiay A et al. are unplaced.)
    """
    _assert_full_row("Pyihia", {
        "dh_id": "Pyihia",
        "name": "Pyihia",
        "alt_names": [],
        "roles": ["KD"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Thutmose IV",
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Daughter of Thutmose IV. One of the group of princesses reburied "
            "during the 21st Dynasty on Sheikh Abd el-Qurna."
        ),
        "source_citation": CITATION,
    })


def test_lacuna_name_full_row() -> None:
    """`[...]pentepkau` — the square-bracketed lacuna in the name must
    survive transcription + extraction + sort order (it now sits in the
    trailing unplaced bin, not at the very end of the whole file).
    """
    _assert_full_row("[...]pentepkau", {
        "dh_id": "[...]pentepkau",
        "name": "[...]pentepkau",
        "alt_names": [],
        "roles": ["KSon"],
        "sex": "male",
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD,
        "unplaced": True,
        "notes": (
            "Unplaced, probably mid-18th Dynasty. Known only from a fragment "
            "of sphinx-stela from near the Second Pyramid of Giza."
        ),
        "source_citation": CITATION,
    })


def test_siamun_b_full_row() -> None:
    """KSon placed by D&H — tests the male-inference branch + father-from-prose
    extraction (`Son of Thutmose III` → father_name).
    """
    _assert_full_row("Siamun B", {
        "dh_id": "Siamun B",
        "name": "Siamun B",
        "alt_names": [],
        "roles": ["KSon"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Thutmose III",
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Son of Thutmose III. Named upon the statuette of the Chancellor, "
            "Sennefer, in the Cairo Museum."
        ),
        "source_citation": CITATION,
    })
