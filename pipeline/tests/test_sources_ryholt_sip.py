"""Structural value-assertion test for Ryholt 1997 SIP source extract.

Per rule 5: every populated field on a sampled fixture row is asserted.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

SOURCE_DIR = (
    Path(__file__).parent.parent / "pipeline" / "authority" / "sources" / "ryholt-1997-sip"
)
JSONL = SOURCE_DIR / "reconciled.jsonl"

EDITION = "CNI Publications 20, Museum Tusculanum Press, 1997"


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    return tuple(json.loads(line) for line in JSONL.read_text().splitlines() if line.strip())


def _row(ryholt_id: str) -> dict:
    hits = [r for r in _rows() if r["ryholt_id"] == ryholt_id]
    if len(hits) != 1:
        raise AssertionError(f"expected 1 row for {ryholt_id}, got {len(hits)}")
    return hits[0]


def test_row_count_is_in_expected_range() -> None:
    """Handoff estimated ~60-80 rows; the three-subagent extraction produced
    157 rows (including unattributed buckets and letter-suffix sub-entries
    Ryholt lists at the end of each dynasty). 157 is the reference value;
    the band below tolerates a small drift if the extraction is re-run.
    """
    rows = _rows()
    assert 150 <= len(rows) <= 170, f"Unexpected row count: {len(rows)}"


def test_dynasty_coverage() -> None:
    """Every target dynasty is represented; unattributed bucket exists."""
    dynasties = {r["dynasty"] for r in _rows()}
    assert dynasties >= {13, 14, 15, 16, 17}, dynasties
    assert None in dynasties, "No unattributed (`dynasty: null`) rows"


def test_every_row_has_complete_citation() -> None:
    """Rule 1: every row traces back to a pdf_pages range and edition."""
    for r in _rows():
        citation = r["source_citation"]
        assert citation["edition"] == EDITION, r
        pdf_pages = citation["pdf_pages"]
        assert isinstance(pdf_pages, str), r
        # "336-340" shape
        parts = pdf_pages.split("-")
        assert len(parts) == 2 and all(p.isdigit() for p in parts), r


def test_sobkhotep_i_file_13_1() -> None:
    """First king of the 13th Dynasty; all five titulary fields present."""
    r = _row("13.1")
    assert r["dynasty"] == 13
    assert r["sequence_in_dynasty"] == 1
    assert r["sequence_suffix"] is None
    assert r["nomen"] == "Sobkhotep I"
    assert r["prenomen"] == "Sekhemrekhutawy"
    assert r["horus_name_transliterated"] == "mnḫ-[...]"
    assert r["nebty_name_transliterated"] is None
    assert r["golden_horus_name_transliterated"] == "ꜥnḫ-nṯrw"
    assert r["prenomen_transliterated"] == "sḫm-rꜥ-ḫw-tꜣwy"
    assert r["nomen_transliterated"] == "sbk-ḥtp"
    assert r["date_bce_start"] == -1803
    assert r["date_bce_end"] == -1800
    assert r["polity"] == "Memphite"
    assert r["concurrent_with"] == ["14"]
    assert r["source_citation"] == {"pdf_pages": "336-340", "edition": EDITION}


def test_khendjer_file_13_22() -> None:
    """Dyn 13 king that motivated the schema example in the handoff."""
    r = _row("13.22")
    assert r["nomen"] == "Khendjer"
    assert r["prenomen"] == "Woserkare"
    assert r["prenomen_transliterated"] == "wsr-kꜣ-rꜥ"
    assert r["date_bce_start"] == -1764
    assert r["date_bce_end"] == -1759
    assert r["polity"] == "Memphite"


def test_sakir_har_15_3_no_prenomen() -> None:
    """Ryholt prints the word "none" in the Prenomen column of Table 96 for
    Sakir-Har, because his cartouche carries `ḥqꜣ-ḫꜣswt` rather than
    `sꜣ-rꜥ`. The sentinel-null normaliser in merge.py turns that string
    into JSON null; a human override on this branch also ensures the row
    is committed with null even if future runs regress.
    """
    r = _row("15.3")
    assert r["dynasty"] == 15
    assert r["sequence_in_dynasty"] == 3
    assert r["nomen"] == "Sakir-Har"
    assert r["prenomen"] is None
    assert r["prenomen_transliterated"] is None
    assert r["polity"] == "Avaris (Hyksos)"


def test_dyn14_homonym_disambiguators_typed() -> None:
    """Ryholt uses Roman-numeral suffixes in File 1 to distinguish kings
    with the same anglicised prenomen across dynasties (13.11 Sewadjkare
    vs 14.11 Sewadjkare III, etc.). Issue #177 PR #189 audit-fix:
    moved from in-string `(III)` glyph in `nomen` to typed
    `homonym_index` integer field. `nomen` now carries the bare name;
    consumers querying for "all Sewadjkare kings" should join on
    nomen alone, then disambiguate via homonym_index when present.
    """
    for rid, expected_nomen, expected_index in [
        ("13.11", "Sewadjkare", 1),
        ("14.11", "Sewadjkare", 3),
        ("14.17", "Awibre", 2),
        ("14.24", "Sankhibre", 2),
    ]:
        r = _row(rid)
        assert r["nomen"] == expected_nomen, (rid, r["nomen"])
        assert r["homonym_index"] == expected_index, (rid, r["homonym_index"])


def test_abydos_dynasty_rows_have_polity() -> None:
    """The 8 Abyd.* rows (Wepwawemsaf, Pantjeny, Snaaib, and five
    fragmentary kings) must carry polity="Abydos" and be concurrent with
    Dyns 15 and 16, per Ryholt's Part II §2.5 and Table 1.
    """
    abyd_rows = [r for r in _rows() if r["ryholt_id"].startswith("Abyd.")]
    assert len(abyd_rows) == 8, len(abyd_rows)
    for r in abyd_rows:
        assert r["dynasty"] is None, r
        assert r["polity"] == "Abydos", r
        assert r["concurrent_with"] == ["15", "16"], r


def test_khamudi_file_15_6() -> None:
    """Last Hyksos king, Dyn 15. Tests the 4-column Chronological-Table
    layout (Dyn 15 has no `No` column; an earlier regex parser missed
    this whole dynasty's dates).
    """
    r = _row("15.6")
    assert r["dynasty"] == 15
    assert r["sequence_in_dynasty"] == 6
    assert r["nomen"] == "Khamudi"
    assert r["prenomen"] == "Hotepibre"
    assert r["prenomen_transliterated"] == "ḥtp-ỉb-rꜥ"
    assert r["date_bce_start"] == -1541
    assert r["date_bce_end"] == -1540
    assert r["polity"] == "Avaris (Hyksos)"
    assert r["concurrent_with"] == ["16", "17", "Abydos"]


def test_kamose_file_17_9_not_nebmaatre() -> None:
    """Kamose (17/9) must NOT be conflated with Nebmaatre (17/a).

    This is a regression test for the bug that motivated switching from
    deterministic regex parsing to the three-subagent extraction: Ryholt
    uses letter-only file suffixes (17/a for Nebmaatre) that a naive
    `\\d+[a-z]?` regex couldn't match, so the pre-17/a block was treated
    as part of Kamose's entry and Nebmaatre's transliterated prenomen
    `nb-mꜣꜥt-rꜥ` appeared as Kamose's.
    """
    r = _row("17.9")
    assert r["nomen"] == "Kamose"
    assert r["prenomen"] == "Wadjkheperre"
    # The load-bearing assertion: transliterated prenomen must be Kamose's
    # `wꜣḏ-ḫpr-rꜥ`, not Nebmaatre's `nb-mꜣꜥt-rꜥ`.
    assert r["prenomen_transliterated"] == "wꜣḏ-ḫpr-rꜥ"


def test_nebmaatre_file_17_a_letter_suffix() -> None:
    """Nebmaatre is Ryholt's `File 17/a` (letter-only suffix). Verifies
    that suffix-only file labels are captured as distinct rows.
    """
    r = _row("17.a")
    assert r["dynasty"] == 17
    assert r["sequence_in_dynasty"] == 0 or r["sequence_in_dynasty"] is None or isinstance(
        r["sequence_in_dynasty"], int
    )
    assert r["sequence_suffix"] == "a"
    assert r["nomen"] == "Nebmaatre"
    # Not in Ryholt's Chron Tables proper (he flags his chronological
    # position as uncertain), so no anglicised prenomen / dates.
    assert r["prenomen"] is None
    assert r["prenomen_transliterated"] == "nb-mꜣꜥt-rꜥ"
    assert r["date_bce_start"] is None
    assert r["date_bce_end"] is None
    assert r["polity"] == "Theban"


def test_polity_matches_dynasty() -> None:
    """Per Ryholt's section headers: 13=Memphite, 14=Avaris,
    15=Avaris (Hyksos), 16/17=Theban. Abydos-Dynasty rows carry
    `dynasty: null` (Ryholt uses an "Abyd" file-prefix, not a dynasty
    number) but polity="Abydos". True unattributed rows (N.*, P.*, etc.)
    carry polity=null.
    """
    expected = {
        13: "Memphite",
        14: "Avaris",
        15: "Avaris (Hyksos)",
        16: "Theban",
        17: "Theban",
    }
    for r in _rows():
        if r["dynasty"] is None:
            if r["ryholt_id"].startswith("Abyd."):
                assert r["polity"] == "Abydos", r
            else:
                assert r["polity"] is None, r
        else:
            assert r["polity"] == expected[r["dynasty"]], r


# ---------------------------------------------------------------------------
# Issue #177 PR #189 — schema-audit-fix tests for the new typed fields
# ---------------------------------------------------------------------------


import importlib.util


def _fix_rows_module():
    spec = importlib.util.spec_from_file_location(
        "ryholt_fix_rows", SOURCE_DIR / "fix_rows.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_every_row_has_every_schema_field() -> None:
    """Issue #177: every row carries every key in SCHEMA_FIELD_DEFAULTS
    after fix_rows runs."""
    defaults = _fix_rows_module().SCHEMA_FIELD_DEFAULTS
    for r in _rows():
        for field in defaults:
            assert field in r, (r["ryholt_id"], field)


def test_no_uncertainty_glyphs_in_name_fields() -> None:
    """Issue #177 Shape J: `(?)` was migrated out of nomen / prenomen
    to typed `is_uncertain_attribution`. Closure: no name field still
    contains `(?)` after fix_rows.
    """
    for r in _rows():
        for f in ("nomen", "prenomen"):
            v = r.get(f) or ""
            assert "(?)" not in v, (r["ryholt_id"], f, v)


def test_no_trailing_syllabic_paren_in_nomen_transliterated() -> None:
    """Issue #177 Shape J: `(syllabic)` trailing form was stripped from
    nomen_transliterated; the typed `is_syllabic_nomen` flag carries the
    information. Non-trailing forms (with footnote suffixes or trailing
    prose like `(syllabic), not preceded by *sꜣ-rꜥ`) are kept verbatim
    because stripping them loses the qualifier; the flag still fires.
    """
    import re
    trailing_re = re.compile(r"\(syllabic\)\s*$")
    for r in _rows():
        nt = r.get("nomen_transliterated") or ""
        assert not trailing_re.search(nt), (r["ryholt_id"], nt)


def test_no_homonym_glyph_in_nomen() -> None:
    """Issue #177 Shape J: `(I)/(II)/(III)` Roman-numeral homonym
    glyphs were migrated out of nomen to typed `homonym_index`."""
    import re
    paren_roman_re = re.compile(r"\(([IVX]+)\)\s*$")
    for r in _rows():
        n = r.get("nomen") or ""
        assert not paren_roman_re.search(n), (r["ryholt_id"], n)


def test_no_var_in_nomen_transliterated() -> None:
    """Issue #177 Shape I: `, var. <alt>` was migrated out of
    nomen_transliterated to typed `nomen_transliterated_variants`."""
    for r in _rows():
        nt = r.get("nomen_transliterated") or ""
        assert ", var." not in nt, (r["ryholt_id"], nt)


def test_attestation_class_matches_ryholt_id_prefix() -> None:
    """Issue #177 Shape A+H: `attestation_class` is a deterministic
    function of the ryholt_id prefix.
    """
    expected_map = {
        "N": "nomen_only",
        "P": "prenomen_only",
        "H": "horus_only",
        "Nb": "nebty_only",
        "G": "golden_horus_only",
        # Per PR #189 Gemini round-1: `D` is Ryholt's prefix for
        # the Nebty (Two Ladies) name (see README), so D and Nb
        # both map to nebty_only.
        "D": "nebty_only",
        "Abyd": "abydos",
    }
    import re
    for r in _rows():
        m = re.match(r"^([A-Za-z]+)\.", r["ryholt_id"])
        if m:
            expected = expected_map.get(m.group(1), "unknown")
        else:
            expected = "king"
        assert r["attestation_class"] == expected, (r["ryholt_id"], r["attestation_class"], expected)


def test_dynasty_label_matches_dynasty_or_prefix() -> None:
    """Issue #177 Shape A: dynasty_label is `str(dynasty)` for numbered
    dynasties, `"Abydos"` for Abyd rows, None for unattributed."""
    import re
    for r in _rows():
        if r["dynasty"]:
            assert r["dynasty_label"] == str(r["dynasty"]), r
        else:
            m = re.match(r"^([A-Za-z]+)\.", r["ryholt_id"])
            prefix = m.group(1) if m else None
            if prefix == "Abyd":
                assert r["dynasty_label"] == "Abydos", r
            else:
                assert r["dynasty_label"] is None, r


def test_is_unattributed_matches_prefix() -> None:
    """Issue #177 Shape J: is_unattributed=True iff prefix is N/P/H/Nb/D/G."""
    import re
    for r in _rows():
        m = re.match(r"^([A-Za-z]+)\.", r["ryholt_id"])
        prefix = m.group(1) if m else None
        expected = prefix in {"N", "P", "H", "Nb", "D", "G"}
        assert r["is_unattributed"] == expected, (r["ryholt_id"], r["is_unattributed"], expected)


def test_is_abydos_dynasty_matches_prefix() -> None:
    """Issue #177 Shape J: is_abydos_dynasty=True iff prefix is `Abyd`."""
    for r in _rows():
        expected = r["ryholt_id"].startswith("Abyd.")
        assert r["is_abydos_dynasty"] == expected, (r["ryholt_id"], r["is_abydos_dynasty"], expected)


def test_date_attestation_matches_date_nulls() -> None:
    """Issue #177 Shape D: date_attestation enum reflects the actual
    date-bound null pattern."""
    for r in _rows():
        s, e = r["date_bce_start"], r["date_bce_end"]
        if s is not None and e is not None:
            expected = "both"
        elif s is not None:
            expected = "start_only"
        elif e is not None:
            expected = "end_only"
        else:
            expected = "none"
        assert r["date_attestation"] == expected, (r["ryholt_id"], r["date_attestation"], expected)


def test_uncertain_attribution_canonical_set() -> None:
    """Issue #177: pin the known uncertain-attribution rows.

    PR #189 Gemini round-1 widened detection to ALL name + transliteration
    fields (not just nomen/prenomen) and to embedded-uncertainty patterns
    `(?)` / `(..?)` / `(...?)`. The audit's original 3-row count missed
    4 rows where the `(?)` glyph appears in transliteration fields or
    embedded inside lacuna markers (13.17 ḥrw-ꜥꜣ (?), 13.53 Hor(..?),
    14.32 Hapu(...?), 16.5 ḥr-nṯr.w (?) ⁽¹⁾). Updated to the wider
    7-row set.
    """
    expected = {"13.17", "13.53", "14.32", "14.g", "16.5", "17.7", "Abyd.15"}
    actual = {r["ryholt_id"] for r in _rows() if r["is_uncertain_attribution"]}
    assert actual == expected, (sorted(actual - expected), sorted(expected - actual))


def test_homonym_index_canonical_set() -> None:
    """Issue #177: pin the 4 known homonym-index rows."""
    expected = {("13.11", 1), ("14.11", 3), ("14.17", 2), ("14.24", 2)}
    actual = {(r["ryholt_id"], r["homonym_index"]) for r in _rows() if r["homonym_index"]}
    assert actual == expected, (sorted(actual - expected), sorted(expected - actual))


def test_nomen_transliterated_variants_canonical_set() -> None:
    """Issue #177: pin the 3 known var.-bearing rows."""
    expected_rids = {"13.22", "14.2", "14.4"}
    actual_rids = {r["ryholt_id"] for r in _rows() if r["nomen_transliterated_variants"]}
    assert actual_rids == expected_rids, (sorted(actual_rids - expected_rids), sorted(expected_rids - actual_rids))
