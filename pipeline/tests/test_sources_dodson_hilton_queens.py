"""Structural value-assertion tests for Dodson & Hilton queens extract.

Per rule 5: every populated field on a sampled fixture row is asserted.
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


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    return tuple(json.loads(line) for line in JSONL.read_text().splitlines() if line.strip())


def _row(dh_id: str) -> dict:
    hits = [r for r in _rows() if r["dh_id"] == dh_id]
    if len(hits) != 1:
        raise AssertionError(f"expected 1 row for {dh_id!r}, got {len(hits)}")
    return hits[0]


def test_row_count() -> None:
    """Brief Lives (47) + Unplaced (12) = 59 entries across printed pp. 137–141."""
    assert len(_rows()) == 59, len(_rows())


def test_dh_id_is_unique() -> None:
    """No duplicate dh_id in the extract."""
    ids = [r["dh_id"] for r in _rows()]
    assert len(ids) == len(set(ids)), "duplicate dh_id detected"


def test_every_row_has_complete_citation() -> None:
    """Rule 1: every row traces to the source chunk."""
    for r in _rows():
        assert r["source_citation"] == {"pdf_pages": PDF_PAGES, "edition": EDITION}, r


def test_every_row_has_dyn18() -> None:
    """Scope of this PR: entirely 18th Dynasty pre-Amarna."""
    for r in _rows():
        assert r["dynasty"] == 18, r


def test_every_row_has_power_and_glory_sub_period() -> None:
    """All entries in this chunk sit under D&H's 'The Power and the Glory' section."""
    for r in _rows():
        assert r["sub_period"] == "The Power and the Glory", r


def test_unplaced_count_is_twelve() -> None:
    """D&H's 'Unplaced' sub-block on printed p. 141 has exactly 12 entries:
    Amenemhat Q, Henut Q, Henutiunu, Merybennu, Meryetptah A, Nebetnehat A,
    Sithori, Tatau, Thutmose Q, Ti, Wiay A, [...]pentepkau.
    """
    unplaced = [r for r in _rows() if r["unplaced"]]
    assert len(unplaced) == 12, f"expected 12 unplaced, got {len(unplaced)}"
    expected_ids = {
        "Amenemhat Q", "Henut Q", "Henutiunu", "Merybennu", "Meryetptah A",
        "Nebetnehat A", "Sithori", "Tatau", "Thutmose Q", "Ti", "Wiay A",
        "[...]pentepkau",
    }
    assert {r["dh_id"] for r in unplaced} == expected_ids


def test_mutemwia_full_row() -> None:
    """Mother of Amenhotep III — flagship Power-and-Glory queen row.
    Full-field assertion per rule 5.
    """
    r = _row("Mutemwia")
    assert r["dh_id"] == "Mutemwia"
    assert r["name"] == "Mutemwia"
    assert r["alt_names"] == []
    assert r["roles"] == ["KGW", "KM"]
    assert r["sex"] == "female"
    assert r["spouse_names"] == ["Thutmose IV"]
    assert r["father_name"] is None
    assert r["mother_name"] is None
    assert r["children_names"] == ["Amenhotep III"]
    assert r["dynasty"] == 18
    assert r["sub_period"] == "The Power and the Glory"
    assert r["unplaced"] is False
    assert r["notes"].startswith("Wife of Thutmose IV and mother of Amenhotep III")
    assert "TT226" in r["notes"]
    assert r["source_citation"] == {"pdf_pages": PDF_PAGES, "edition": EDITION}


def test_hatshepsut_d_five_role_codes() -> None:
    """D&H's Hatshepsut-as-queen-and-king carries five role codes on the
    same entry: GW, KGW, KD, KSis, UWC — tests that semicolon-parenthesis
    splitting preserves all five.
    """
    r = _row("Hatshepsut D")
    assert r["roles"] == ["GW", "KGW", "KD", "KSis", "UWC"]
    assert r["father_name"] == "Thutmose I"
    assert r["spouse_names"] == ["Thutmose II"]
    assert r["sex"] == "female"
    # The prose explicitly says she was "later king" — an inline disambiguator
    # we preserve verbatim in notes rather than promoting to a separate field.
    assert "later king" in r["notes"]


def test_lacuna_name_preserved() -> None:
    """`[...]pentepkau` is the last entry in the Unplaced block. The
    square-bracketed lacuna in the name is a genuine gap in the
    attestation and must survive transcription + extraction.
    """
    r = _row("[...]pentepkau")
    assert r["dh_id"] == "[...]pentepkau"
    assert r["roles"] == ["KSon"]
    assert r["sex"] == "male"
    assert r["unplaced"] is True
    assert r["dynasty"] == 18


def test_iset_a_and_iset_b_are_distinct() -> None:
    """Regression test: Iset A (mother of Thutmose III) and Iset B
    (daughter of Thutmose III + Meryetre-Hatshepsut) are two separate
    individuals. Any extraction that collapses them into one row is wrong.
    """
    a = _row("Iset A")
    b = _row("Iset B")
    assert a["roles"] == ["GW", "KM", "KW", "KGW"]
    assert b["roles"] == ["KD"]
    assert a["children_names"] == ["Thutmose III"]
    assert b["children_names"] == []
    assert a["sex"] == "female"
    assert b["sex"] == "female"


def test_three_syrian_wives_of_thutmose_iii_are_distinct() -> None:
    """Menhet, Menwi and Merti are three distinct wives of Thutmose III
    buried together in Wadi Gabbanet el-Qurud. D&H writes near-identical
    prose for all three; test that they are three rows.
    """
    for dh_id in ["Menhet", "Menwi", "Merti"]:
        r = _row(dh_id)
        assert r["roles"] == ["KW"]
        assert r["sex"] == "female"
        assert r["spouse_names"] == ["Thutmose III"]


def test_kings_cross_referenced_in_bold_caps_not_extracted_as_entries() -> None:
    """`**AMENHOTEP II**`, `**AMENHOTEP III**`, `**THUTMOSE IV**` appear in
    BOLD CAPS inside other entries' prose (Amenhotep B, Amenhotep D,
    Thutmose A) as D&H's king-cross-reference convention. They are NOT
    themselves Brief Lives entries in this chunk. No row in the extract
    should have one of those strings as dh_id.
    """
    king_refs = {"AMENHOTEP II", "AMENHOTEP III", "THUTMOSE IV"}
    for r in _rows():
        assert r["dh_id"] not in king_refs, r


def test_sex_inference_covers_every_row() -> None:
    """Every row has a non-null sex; value ∈ {male, female}."""
    for r in _rows():
        assert r["sex"] in ("male", "female"), r


def test_role_code_set_spans_the_known_codes() -> None:
    """Every known D&H code in this chunk appears on at least one row."""
    all_codes = set()
    for r in _rows():
        all_codes.update(r["roles"])
    for expected in ["KM", "KW", "KGW", "GW", "KSis", "KD", "KSon", "EKSon"]:
        assert expected in all_codes, f"expected code {expected!r} never extracted"


def test_reburial_prose_verbatim_on_reburied_princesses() -> None:
    """D&H uses the phrase 'One of the group of princesses reburied during
    the 21st Dynasty on Sheikh Abd el-Qurna' verbatim for several
    princesses. Test that the phrase survives unchanged in notes.
    """
    reburied = ["Pyihia", "Meryetptah A", "Sithori", "Tatau", "Wiay A"]
    phrase = "One of the group of princesses reburied"
    for dh_id in reburied:
        r = _row(dh_id)
        assert phrase in r["notes"], (dh_id, r["notes"])


def test_disambiguator_letters_preserved_on_homonyms() -> None:
    """D&H uses trailing single-letter disambiguators (A, B, C, D) on
    homonymous royals. Test that these survive in dh_id (and therefore in
    name, since name == dh_id for this source).
    """
    for dh_id in [
        "Ahmes B", "Ahmose B", "Amenemhat B", "Amenemhat C",
        "Amenemopet A", "Amenemopet B",
        "Amenhotep B", "Amenhotep C", "Amenhotep D",
        "Hatshepsut D", "Iset A", "Iset B",
        "Khaemwaset A", "Menkheperre A", "Mutneferet A",
        "Meryetamun C", "Meryetamun D",
        "Nebetiunet B", "Nefertiry B", "Nefertiry C", "Neferure A",
        "Siamun B", "Siatum A", "Thutmose A",
        "Tiaa A", "Tiaa B",
        "Meryetptah A", "Nebetnehat A", "Wiay A",
    ]:
        r = _row(dh_id)
        assert r["name"] == dh_id
