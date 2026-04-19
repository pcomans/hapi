"""Structural value-assertion tests for Porter & Moss Vol I source extract.

Per CLAUDE.md rule 5: every populated field on every fixture-class row is
asserted, not just the field the test class is "themed" around.

Chunk 1 covers KV1–KV10 (PM I.2 § I.A "Tombs", printed p.495–518). Future
chunks (KV11–KV65, QV, TT...) extend `EXPECTED_TOMB_IDS` and add per-chunk
value-assertion tests; the structural tests below are forward-compatible.

Note on null `dynasty` and BCE-date fields: per CLAUDE.md rule 1 (every
authoritative fact must trace to a committed raw source) and rule 7
(authority lookup, not hard-coded), PM headwords don't print dynasty or
BCE dates — those fields stay null at this extraction stage and Phase A
king-authority enrichment (against pharaoh.se) fills them. The test suite
therefore asserts these fields are null on every chunk-1 row, not that
they carry expected dynasty values.
"""

from __future__ import annotations

import importlib.util
import json
import re
from functools import lru_cache
from pathlib import Path

SOURCE_DIR = (
    Path(__file__).parent.parent
    / "pipeline"
    / "authority"
    / "sources"
    / "porter-moss-theban-necropolis"
)
JSONL = SOURCE_DIR / "reconciled.jsonl"

EDITION_PM_I2 = "PM I.2 2nd ed. 1964"
EDITION_PM_I1 = "PM I.1 2nd ed. 1960"

# Chunk-1 (KV1–KV10), chunk-2 (KV11–KV20), chunk-3 (KV22–KV46 sparse) are
# the landed chunks. Extend as follow-up chunk PRs land. `EXPECTED_TOMB_IDS`
# is the union — row-count and ID-coverage tests reference it so they stay
# correct as the source grows.
#
# Absence patterns in PM I.2 § I.A:
# - KV21 is absent (jump from KV20 to KV22) — chunk-2 holds 10 rows.
# - KV24–KV33, KV37, KV40, KV41, KV44 are absent from chunk-3's range —
#   PM I.2 (1964) did not catalogue these as inscribed royal tombs. Chunk-3
#   holds 11 rows: KV22, 23, 34, 35, 36, 38, 39, 42, 43, 45, 46.
CHUNK1_TOMB_IDS: frozenset[str] = frozenset(
    {f"KV{n}" for n in range(1, 11)}
)
CHUNK2_TOMB_IDS: frozenset[str] = frozenset(
    {f"KV{n}" for n in range(11, 21)}
)
CHUNK3_TOMB_IDS: frozenset[str] = frozenset(
    {"KV22", "KV23", "KV34", "KV35", "KV36", "KV38", "KV39", "KV42",
     "KV43", "KV45", "KV46"}
)
# Chunk-4: KV47-KV57 sparse. KV49-KV54 and KV58-KV61 absent from PM I.2
# § I.A (PM jumps 48 → 55, 57 → 62). KV62 Tutankhamun is deferred to a
# dedicated chunk 5 because PM's KV62 entry spans 17 printed pages and
# warrants its own extraction PR.
CHUNK4_TOMB_IDS: frozenset[str] = frozenset(
    {"KV47", "KV48", "KV55", "KV56", "KV57"}
)
# Chunk-5: KV62 Tutʿankhamun as a standalone single-row chunk. User
# direction on chunk 5 scope: tomb-row granularity is sufficient for the
# museum-data-join use case; per-chamber sub-structure would inflate the
# schema past what downstream enrichment needs.
CHUNK5_TOMB_IDS: frozenset[str] = frozenset({"KV62"})
EXPECTED_TOMB_IDS: frozenset[str] = (
    CHUNK1_TOMB_IDS
    | CHUNK2_TOMB_IDS
    | CHUNK3_TOMB_IDS
    | CHUNK4_TOMB_IDS
    | CHUNK5_TOMB_IDS
)


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    return tuple(
        json.loads(line) for line in JSONL.read_text().splitlines() if line.strip()
    )


def _row(tomb_id: str) -> dict:
    hits = [r for r in _rows() if r["tomb_id"] == tomb_id]
    if len(hits) != 1:
        raise AssertionError(f"expected 1 row for {tomb_id}, got {len(hits)}")
    return hits[0]


# ---------------------------------------------------------------------------
# Structural tests (forward-compatible across chunks)
# ---------------------------------------------------------------------------


def test_row_count_matches_expected_set() -> None:
    """Exact-match row count to the union of all landed chunks' tomb IDs."""
    assert len(_rows()) == len(EXPECTED_TOMB_IDS), len(_rows())


def test_tomb_ids_match_expected_set() -> None:
    """Every expected tomb id is present, and no unexpected ids snuck in."""
    actual = {r["tomb_id"] for r in _rows()}
    assert actual == EXPECTED_TOMB_IDS, sorted(actual ^ EXPECTED_TOMB_IDS)


def test_tomb_id_is_unique() -> None:
    """No duplicate tomb_id in the committed extract."""
    ids = [r["tomb_id"] for r in _rows()]
    assert len(ids) == len(set(ids)), "duplicate tomb_id detected"


# Forward-compatible: extend the alternation as future chunks introduce
# non-KV/QV/TT prefixes (Dra' Abu el-Naga, Deir el-Medina, etc. may use
# their own scheme). Today the extract only uses KV.
_TOMB_ID_RE = re.compile(r"^(KV|QV|TT)\d+[a-z]?$")


def test_tomb_id_shape() -> None:
    """Every id matches `(KV|QV|TT)\\d+[a-z]?`. Extend the regex when a
    follow-up chunk lands a section with a different ID convention.
    """
    for r in _rows():
        assert _TOMB_ID_RE.match(r["tomb_id"]), r["tomb_id"]


def test_required_fields_present_on_every_row() -> None:
    """Schema discipline: every row carries every key, even when null/empty.

    Sparse rows are valid (CLAUDE.md rule 4), but the KEY must be present
    so downstream Phase A code can assume the schema without `.get()` calls.
    """
    required = {
        "tomb_id",
        "valley",
        "occupant_name",
        "occupant_alt_names",
        "occupant_role",
        "dynasty",
        "sub_period",
        "date_bce_approx_start",
        "date_bce_approx_end",
        "location_sub_area",
        "discovery_year",
        "discoverer",
        "is_unfinished",
        "shared_with_tombs",
        "notes_from_pm",
        "source_citation",
    }
    for r in _rows():
        missing = required - r.keys()
        assert not missing, (r["tomb_id"], sorted(missing))


def test_valley_constraint() -> None:
    """`valley` belongs to a known controlled vocabulary.

    Forward-compatible: extend the allowlist as future chunks add
    Dra' Abu el-Naga, Deir el-Bahri, Asasif, Sheikh Abd el-Qurna,
    Khokha, Qurnet Mura'i, Deir el-Medina, Ramesseum, Medinet Habu.
    """
    valid = {
        "Valley of the Kings",
        "Valley of the Queens",
        "Dra' Abu el-Naga",
        "Deir el-Bahri",
        "Asasif",
        "Sheikh Abd el-Qurna",
        "Khokha",
        "Qurnet Mura'i",
        "Deir el-Medina",
        "Ramesseum",
        "Medinet Habu",
    }
    for r in _rows():
        assert r["valley"] in valid, (r["tomb_id"], r["valley"])


def test_kv_rows_have_kv_tomb_id() -> None:
    """`tomb_id` prefix matches the `valley` value."""
    for r in _rows():
        if r["valley"] == "Valley of the Kings":
            assert r["tomb_id"].startswith("KV"), r
        if r["valley"] == "Valley of the Queens":
            assert r["tomb_id"].startswith("QV"), r


def test_dynasty_is_null_or_string() -> None:
    """`dynasty` is null at the extraction stage (Phase A enrichment fills
    it from the king authority). When populated by future enrichment, it
    must be the Arabic-numeral STRING form — Phase A relies on the string
    form for joining against the king authority; drift to int silently
    breaks that join.
    """
    for r in _rows():
        v = r["dynasty"]
        assert v is None or isinstance(v, str), (r["tomb_id"], v)


def test_dates_null_at_extraction_stage() -> None:
    """Per CLAUDE.md rule 1: PM headwords don't print BCE dates, so the
    dates fields stay null at extraction. Phase A king-authority enrichment
    against pharaoh.se populates them later. When populated, dates are
    negative ints.
    """
    for r in _rows():
        for field in ("date_bce_approx_start", "date_bce_approx_end"):
            v = r[field]
            if v is not None:
                assert isinstance(v, int) and v < 0, (r["tomb_id"], field, v)


def test_date_start_before_date_end() -> None:
    """For any row with both date_bce_approx_start and _end populated,
    start (more-negative, i.e. EARLIER BCE date) must be ≤ end. PM does
    not give regnal-end-then-start ordering anywhere; an inverted pair
    means a Phase A enrichment bug.
    """
    for r in _rows():
        s, e = r["date_bce_approx_start"], r["date_bce_approx_end"]
        if s is not None and e is not None:
            assert s <= e, (r["tomb_id"], s, e)


def test_source_citation_shape() -> None:
    """`source_citation` is a dict with `page` (int), `edition` (str), `section` (str)."""
    valid_editions = {EDITION_PM_I1, EDITION_PM_I2}
    for r in _rows():
        c = r["source_citation"]
        assert set(c.keys()) == {"page", "edition", "section"}, (r["tomb_id"], c.keys())
        assert isinstance(c["page"], int) and c["page"] > 0, (r["tomb_id"], c["page"])
        assert c["edition"] in valid_editions, (r["tomb_id"], c["edition"])
        assert isinstance(c["section"], str) and c["section"], (r["tomb_id"], c["section"])


def test_source_citation_page_in_chunk1_range() -> None:
    """Chunk 1 covers PM I.2 printed pages 495–518. Every chunk-1 row's
    page citation must fall within that range. Catches off-by-one bugs
    in extraction's running-header parsing.
    """
    for tid in CHUNK1_TOMB_IDS:
        r = _row(tid)
        page = r["source_citation"]["page"]
        assert 495 <= page <= 518, (tid, page)


def test_shared_with_tombs_are_valid_tomb_ids() -> None:
    """Every entry in `shared_with_tombs` matches the tomb-id regex."""
    for r in _rows():
        for tid in r["shared_with_tombs"]:
            assert _TOMB_ID_RE.match(tid), (r["tomb_id"], tid)


def test_shared_with_tombs_symmetry_within_chunk() -> None:
    """If KV5.shared_with_tombs lists KV7, then KV7.shared_with_tombs lists KV5.

    Symmetry is enforced only for tomb pairs where BOTH ends sit in the
    landed extract — across chunks, a one-sided cross-ref is legitimate
    (e.g. chunk 1 KV3 → KV11, but KV11 lands in chunk 2). The check uses
    the actual extract membership rather than the chunk plan so it stays
    correct as new chunks land.
    """
    by_id = {r["tomb_id"]: r for r in _rows()}
    for r in _rows():
        for partner in r["shared_with_tombs"]:
            if partner in by_id:
                back_refs = by_id[partner]["shared_with_tombs"]
                assert r["tomb_id"] in back_refs, (
                    f"{r['tomb_id']} → {partner} but {partner} → {back_refs}"
                )


def test_occupant_role_controlled_vocab() -> None:
    """Controlled vocabulary for `occupant_role`. Extend as new sections add roles."""
    valid = {"King", "Queen", "Royal Family", "Vizier", "Official",
             "High Priest", "Princess", "Prince", "Unknown"}
    for r in _rows():
        if r["occupant_role"] is not None:
            assert r["occupant_role"] in valid, (r["tomb_id"], r["occupant_role"])


# ---------------------------------------------------------------------------
# Chunk-1 specific value-assertion tests (KV1–KV10)
# ---------------------------------------------------------------------------


def test_chunk1_all_rows_kv_kings_no_dynasty_or_dates() -> None:
    """KV1–KV10 are all kings — `valley` and `occupant_role` are uniform.
    Dynasty + BCE dates are null at this stage (Phase A enrichment).
    """
    for tid in CHUNK1_TOMB_IDS:
        r = _row(tid)
        assert r["valley"] == "Valley of the Kings"
        assert r["occupant_role"] == "King"
        assert r["dynasty"] is None
        assert r["sub_period"] is None
        assert r["date_bce_approx_start"] is None
        assert r["date_bce_approx_end"] is None
        assert r["location_sub_area"] is None
        assert r["discovery_year"] is None
        assert r["discoverer"] is None
        assert r["source_citation"]["edition"] == EDITION_PM_I2
        assert r["source_citation"]["section"] == "I.A"


def test_chunk1_unfinished_flag() -> None:
    """KV3 (Ramesses III's first attempt) and KV5 (Ramesses II) are flagged
    `Unfinished` literally in PM. KV4 (Ramesses XI) was historically
    unfinished but PM doesn't use the literal word — `is_unfinished` stays
    false. This test pins the literal-text rule.
    """
    expected_unfinished = {"KV3", "KV5"}
    for tid in CHUNK1_TOMB_IDS:
        r = _row(tid)
        if tid in expected_unfinished:
            assert r["is_unfinished"] is True, tid
        else:
            assert r["is_unfinished"] is False, tid


def test_chunk1_shared_with_tombs() -> None:
    """KV3 → KV11 (chunk 2 — one-sided), KV5 ↔ KV7 (both chunk 1)."""
    assert _row("KV3")["shared_with_tombs"] == ["KV11"]
    assert _row("KV5")["shared_with_tombs"] == ["KV7"]
    assert _row("KV7")["shared_with_tombs"] == ["KV5"]
    # All other chunk-1 rows have empty shared_with_tombs.
    for tid in CHUNK1_TOMB_IDS - {"KV3", "KV5", "KV7"}:
        assert _row(tid)["shared_with_tombs"] == [], tid


def test_chunk1_kv1_minimal_row() -> None:
    """KV1 (Ramesses VII) is the minimal-shape KV chunk-1 row: no Unfinished
    flag, no cross-refs, no notes, no alt-names. Asserts every field.

    The KV3 flagship row (separate test below) exercises is_unfinished +
    shared_with_tombs; KV9 exercises notes_from_pm + occupant_alt_names.
    Together they cover every populated-field shape per rule 5.
    """
    r = _row("KV1")
    assert r["tomb_id"] == "KV1"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Ramesses VII"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 495,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk1_kv3_flagship_full_row() -> None:
    """KV3 (Ramesses III's unfinished tomb) is the flagship full-row test:
    exercises `is_unfinished=true` and `shared_with_tombs=["KV11"]` (a
    one-sided cross-chunk reference). Asserts every field per rule 5.
    """
    r = _row("KV3")
    assert r["tomb_id"] == "KV3"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Ramesses III"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is True
    assert r["shared_with_tombs"] == ["KV11"]
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 500,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk1_kv9_ramesses_vi_notes_and_alias() -> None:
    """KV9 exercises `notes_from_pm` (the cross-line clause about Ramesses V's
    doorway usurpation) and `occupant_alt_names` (the Memnon classical alias
    from PM's `'Tomb of Memnon'` parenthetical). Asserts every field per
    rule 5.
    """
    r = _row("KV9")
    assert r["tomb_id"] == "KV9"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Ramesses VI"
    assert r["occupant_alt_names"] == ["Memnon"]
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "doorways in outer part usurped from Ramesses V"
    assert r["source_citation"] == {
        "page": 511,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk1_kv4_ramesses_xi_notes_preserved() -> None:
    """KV4's headword: `RAMESSES XI (formerly XII)`. The parenthetical
    `(formerly XII)` is PM's regnal-number disambiguation — earlier
    scholarship counted this king as Ramesses XII. Preserved as a
    structured `notes_from_pm` rather than embedded in `occupant_name`,
    so downstream museum-data joins on the canonical `Ramesses XI` work.
    """
    r = _row("KV4")
    assert r["occupant_name"] == "Ramesses XI"
    assert r["notes_from_pm"] == "formerly XII"


def test_chunk1_two_ramesses_ii_tombs() -> None:
    """KV5 and KV7 are both attributed to Ramesses II (KV5 unfinished, KV7
    the actual completed tomb). Mutually-cross-referenced via shared_with_tombs.
    """
    kv5 = _row("KV5")
    kv7 = _row("KV7")
    for r in (kv5, kv7):
        assert r["occupant_name"] == "Ramesses II"
        assert r["valley"] == "Valley of the Kings"
        assert r["occupant_role"] == "King"
    assert kv5["is_unfinished"] is True
    assert kv7["is_unfinished"] is False
    assert kv5["shared_with_tombs"] == ["KV7"]
    assert kv7["shared_with_tombs"] == ["KV5"]
    assert kv5["source_citation"]["page"] == 501
    assert kv7["source_citation"]["page"] == 505


def test_chunk1_kv8_merneptah_page_507() -> None:
    """KV8 (Merneptah) headword opens at PM I.2 printed page 507, NOT 509.
    Egyptologist-reviewer caught the mis-citation in PR #66's first round;
    the field-rule-based prompt rewrite (with page extracted from chunk
    text running headers) produces the correct page. This test pins it.
    """
    r = _row("KV8")
    assert r["occupant_name"] == "Merneptah"
    assert r["source_citation"]["page"] == 507


# ---------------------------------------------------------------------------
# Chunk-2 specific value-assertion tests (KV11–KV20)
# ---------------------------------------------------------------------------


def test_chunk2_page_range() -> None:
    """Chunk 2 headwords sit on PM I.2 printed pages 518–546. Every chunk-2
    row's page citation must fall within that range. The chunk FILE
    extends two pages further (p.547–548) to give the extraction agents
    boundary context, but no KV headword in the chunk sits past p.546.
    """
    for tid in CHUNK2_TOMB_IDS:
        r = _row(tid)
        page = r["source_citation"]["page"]
        assert 518 <= page <= 546, (tid, page)
        assert r["source_citation"]["edition"] == EDITION_PM_I2
        assert r["source_citation"]["section"] == "I.A"


def test_chunk2_all_rows_valley_of_kings_no_dynasty_or_dates() -> None:
    """Every chunk-2 row has valley=VoK and null dynasty/dates/discoverer —
    same extraction-stage discipline as chunk 1.
    """
    for tid in CHUNK2_TOMB_IDS:
        r = _row(tid)
        assert r["valley"] == "Valley of the Kings"
        assert r["dynasty"] is None
        assert r["sub_period"] is None
        assert r["date_bce_approx_start"] is None
        assert r["date_bce_approx_end"] is None
        assert r["location_sub_area"] is None
        assert r["discovery_year"] is None
        assert r["discoverer"] is None


def test_chunk2_unfinished_flag() -> None:
    """KV18 (Ramesses X) is the only chunk-2 tomb flagged `Unfinished` in PM."""
    expected_unfinished = {"KV18"}
    for tid in CHUNK2_TOMB_IDS:
        r = _row(tid)
        if tid in expected_unfinished:
            assert r["is_unfinished"] is True, tid
        else:
            assert r["is_unfinished"] is False, tid


def test_chunk2_shared_with_tombs() -> None:
    """KV11 ↔ KV3 cross-chunk symmetry: both rows reference each other.
    KV20's informal `See also South Tomb` is NOT a numbered cross-ref — stays empty.
    """
    assert _row("KV11")["shared_with_tombs"] == ["KV3"]
    assert _row("KV3")["shared_with_tombs"] == ["KV11"]
    for tid in CHUNK2_TOMB_IDS - {"KV11"}:
        assert _row(tid)["shared_with_tombs"] == [], tid


def test_chunk2_kv11_ramesses_iii_full_row() -> None:
    """KV11 (Ramesses III) flagship row — exercises cross-chunk back-
    reference to KV3, classical aliases (`Bruce's tomb`, `the Harper's tomb`)
    from PM's headword parenthetical, and headword-at-page-tail extraction
    (KV11's headword sits at the bottom of physical p.60 / printed 518).
    Asserts every field per CLAUDE.md rule 5.
    """
    r = _row("KV11")
    assert r["tomb_id"] == "KV11"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Ramesses III"
    assert r["occupant_alt_names"] == ["Bruce's tomb", "the Harper's tomb"]
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == ["KV3"]
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 518,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv12_uninscribed() -> None:
    """KV12 (PM: `UNINSCRIBED`) — the tomb has no named occupant. Per the
    extraction prompt + fix_rows.py correction: `occupant_name=null` and
    `occupant_role='Unknown'`. Asserts every field per rule 5.
    """
    r = _row("KV12")
    assert r["tomb_id"] == "KV12"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] is None
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Unknown"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 527,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv13_bay_chancellor() -> None:
    """KV13 (Bay, Chancellor — non-royal). Exercises non-King
    `occupant_role` (`Official`) and the `notes_from_pm` regnal-dating
    fragment from PM's headword (`Temp. Merneptah-Siptah`), captured
    via fix_rows.py after the reviewer flagged that all three extraction
    agents dropped it. Asserts every field per rule 5.
    """
    r = _row("KV13")
    assert r["tomb_id"] == "KV13"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Bay"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Official"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "Temp. Merneptah-Siptah"
    assert r["source_citation"] == {
        "page": 527,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv14_tausert_usurpation_note() -> None:
    """KV14 (Tausert, usurped by Setnakht) — exercises the biographical-
    plus-usurpation `notes_from_pm` clause, distinct from `occupant_alt_names`
    (Setnakht is a later usurper, NOT a classical alias of Tausert).
    Asserts every field per rule 5.
    """
    r = _row("KV14")
    assert r["tomb_id"] == "KV14"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Tausert"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "wife of Sethos II. Usurped by Setnakht"
    assert r["source_citation"] == {
        "page": 527,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv17_sethos_i_belzoni_alias() -> None:
    """KV17 (Sethos I) — exercises the `Belzoni's tomb` classical alias
    from PM's headword single-quote parenthetical. PM's spelling
    `Sethos I` is preserved verbatim (the ruler authority bridges to
    the modern `Seti I` convention in Phase A; the extract stays
    faithful to PM). Asserts every field per rule 5.
    """
    r = _row("KV17")
    assert r["tomb_id"] == "KV17"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Sethos I"
    assert r["occupant_alt_names"] == ["Belzoni's tomb"]
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 535,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv18_ramesses_x_unfinished() -> None:
    """KV18 (Ramesses X) — exercises `is_unfinished=True` and the
    `formerly XI` regnal-number disambiguation note. PM's headword
    literally prints `RAMESSES X (formerly XI)` and `Unfinished.` after
    the bibliographic ribbon. Asserts every field per rule 5.
    """
    r = _row("KV18")
    assert r["tomb_id"] == "KV18"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Ramesses X"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is True
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "formerly XI"
    assert r["source_citation"] == {
        "page": 545,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv19_prince_ramesses_mentuherkhepshef() -> None:
    """KV19 (the Prince's tomb) — exercises the `Prince` role (royal son
    who never reigned, distinct from the rest of the chunk's ruling
    kings) and the `son of Ramesses IX` relational note from PM's
    headword. The `occupant_name` preserves PM's verbatim spelling
    `Raʿmeses-Mentuhirkhopshef` (with ayin, with PM's `e/i/u` choices)
    rather than over-modernising to `Ramesses-Mentuherkhepshef` —
    PM-verbatim policy, per egyptologist-reviewer on PR #68.
    Asserts every field per rule 5.
    """
    r = _row("KV19")
    assert r["tomb_id"] == "KV19"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Raʿmeses-Mentuhirkhopshef"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Prince"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "son of Ramesses IX"
    assert r["source_citation"] == {
        "page": 546,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv20_hatshepsut_king() -> None:
    """KV20 (Hatshepsut) — exercises Hatshepsut-as-ruling-King disposition
    (not Queen), and `shared_with_tombs=[]` (PM's `See also South Tomb`
    is informal, not a numbered KV cross-ref). Asserts every field per
    rule 5.
    """
    r = _row("KV20")
    assert r["tomb_id"] == "KV20"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Hatshepsut"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 546,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


# ---------------------------------------------------------------------------
# Chunk-3 specific value-assertion tests (KV22–KV46 sparse)
# ---------------------------------------------------------------------------


def test_chunk3_page_range() -> None:
    """Chunk 3 headwords sit on PM I.2 printed pages 547–562. Every chunk-3
    row's page citation must fall within that range.
    """
    for tid in CHUNK3_TOMB_IDS:
        r = _row(tid)
        page = r["source_citation"]["page"]
        assert 547 <= page <= 562, (tid, page)
        assert r["source_citation"]["edition"] == EDITION_PM_I2
        assert r["source_citation"]["section"] == "I.A"


def test_chunk3_all_rows_valley_of_kings_no_dynasty_or_dates() -> None:
    """Every chunk-3 row has valley=VoK and null dynasty/dates/discoverer —
    same extraction-stage discipline as chunks 1 and 2.

    `is_unfinished` and `shared_with_tombs` are pinned per-row in the
    themed tests below rather than here — asserting them as chunk-wide
    invariants would fail if a future reviewer-caught correction
    identifies an Unfinished tomb or cross-ref in this PM range, and
    the per-row tests already give full coverage.
    """
    for tid in CHUNK3_TOMB_IDS:
        r = _row(tid)
        assert r["valley"] == "Valley of the Kings"
        assert r["dynasty"] is None
        assert r["sub_period"] is None
        assert r["date_bce_approx_start"] is None
        assert r["date_bce_approx_end"] is None
        assert r["discovery_year"] is None
        assert r["discoverer"] is None


def test_chunk3_kv21_absent_from_expected_set() -> None:
    """KV21 is not part of chunk-2 (KV20 jumps to KV22 in PM). Defensive
    structural check — lives here because chunk-3's range-definition is
    what documents the absence formally.
    """
    assert "KV21" not in EXPECTED_TOMB_IDS


def test_chunk3_missing_kv_ids_absent_from_expected_set() -> None:
    """KV24–KV33, KV37, KV40, KV41, KV44 are not in PM I.2 § I.A — they
    jump out of PM's cataloguing. If a future chunk PR accidentally pulls
    one of these in, this test fails loudly.
    """
    must_be_absent = (
        [f"KV{n}" for n in range(24, 34)] + ["KV37", "KV40", "KV41", "KV44"]
    )
    for tid in must_be_absent:
        assert tid not in EXPECTED_TOMB_IDS, tid


def test_chunk3_kv22_amenophis_iii_west_valley() -> None:
    """KV22 (Amenophis III) — West Valley tomb. Exercises:
    - `location_sub_area = "West Valley"` (first row in the extract with
      a non-null sub-area);
    - PM-verbatim `"Amenophis III"` despite modern `Amenhotep III`
      convention (PM's 1964 form is Amenophis);
    - `notes_from_pm` captures headword `Excavated by ...` clause.
    Asserts every field per rule 5.
    """
    r = _row("KV22")
    assert r["tomb_id"] == "KV22"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Amenophis III"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] == "West Valley"
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "Excavated by Davis, and by Carnarvon and Carter"
    assert r["source_citation"] == {
        "page": 547,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv23_ay_classical_aliases() -> None:
    """KV23 (Ay) — two classical-traveller nicknames (`Eesa` by Wilkinson,
    `Schai` by Prisse / Nestor L'Hôte) captured in `occupant_alt_names`.
    Also in the West Valley. Asserts every field per rule 5.
    """
    r = _row("KV23")
    assert r["tomb_id"] == "KV23"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Ay"
    assert r["occupant_alt_names"] == ["Eesa", "Schai"]
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] == "West Valley"
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "Excavated by Belzoni"
    assert r["source_citation"] == {
        "page": 550,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv34_tuthmosis_iii_first_edition_note() -> None:
    """KV34 (Tuthmosis III) — `notes_from_pm` captures PM's `[Ist ed. 24]`
    cross-reference to the 1st-edition tomb numbering. Parallel in shape
    to chunk-1 KV4's `formerly XII` and chunk-2 KV18's `formerly XI`.
    Asserts every field per rule 5.
    """
    r = _row("KV34")
    assert r["tomb_id"] == "KV34"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Tuthmosis III"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "1st ed. 24"
    assert r["source_citation"] == {
        "page": 551,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv36_mahirper_official() -> None:
    """KV36 (Mahirper) — non-royal `Official` role (Standard-bearer, Child
    of the nursery, temp. Hatshepsut). PM's text layer prints `MAI;IIRPER`
    where `I;I` is the underdot-H glyph; applying the chunk-1/2 rule
    `I;I → h` yields `Mahirper` (not `Maihirper` — that leaves a
    spurious `i` before the `h`; egyptologist-reviewer second-pass on
    PR #69 confirmed no published Egyptological form reads `Maihirper`).
    Asserts every field per rule 5.
    """
    r = _row("KV36")
    assert r["tomb_id"] == "KV36"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Mahirper"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Official"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == (
        "Standard-bearer, Child of the nursery. Temp. Hatshepsut. "
        "Excavated by Loret"
    )
    assert r["source_citation"] == {
        "page": 556,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv39_uninscribed_unknown_with_attribution_note() -> None:
    """KV39 — PM prints `Uninscribed tomb, attributed to Amenophis I by
    Weigall...`. Exercises: null `occupant_name` + `Unknown` role
    (distinct from KV12 which is `UNINSCRIBED` without attribution),
    plus the attribution-descriptor captured as `notes_from_pm`. Asserts
    every field per rule 5.
    """
    r = _row("KV39")
    assert r["tomb_id"] == "KV39"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] is None
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Unknown"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == (
        "Uninscribed tomb, attributed to Amenophis I by Weigall in Ann. "
        "Serv. xi (1911)"
    )
    assert r["source_citation"] == {
        "page": 559,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv42_tuthmosis_ii_attribution_uncertain() -> None:
    """KV42 (Tuthmosis II) — PM prints the attribution with a `(?)`
    uncertainty marker (`TUTHMOSIS II (?)`). The structured `occupant_name`
    stays clean; the uncertainty is captured in `notes_from_pm` alongside
    the existing `Excavated by Loret` headword clause. Asserts every
    field per rule 5.
    """
    r = _row("KV42")
    assert r["tomb_id"] == "KV42"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Tuthmosis II"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "(?). Excavated by Loret"
    assert r["source_citation"] == {
        "page": 559,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv35_amenophis_ii() -> None:
    """KV35 (Amenophis II) — straightforward King row. PM's text layer
    renders `II` as `n` in this headword; the extract normalises to
    `Amenophis II`. Asserts every field per rule 5.
    """
    r = _row("KV35")
    assert r["tomb_id"] == "KV35"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Amenophis II"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 554,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv38_tuthmosis_i() -> None:
    """KV38 (Tuthmosis I) — King row with `Excavated by Loret` headword
    clause in notes. Asserts every field per rule 5.
    """
    r = _row("KV38")
    assert r["tomb_id"] == "KV38"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Tuthmosis I"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "Excavated by Loret"
    assert r["source_citation"] == {
        "page": 557,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv43_tuthmosis_iv() -> None:
    """KV43 (Tuthmosis IV) — King row with `Excavated by Davis` headword
    clause in notes. Asserts every field per rule 5.
    """
    r = _row("KV43")
    assert r["tomb_id"] == "KV43"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Tuthmosis IV"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "Excavated by Davis"
    assert r["source_citation"] == {
        "page": 559,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv45_userhet_re_used() -> None:
    """KV45 (Userhet) — re-used tomb pattern. Original Dyn XVIII occupant
    (Userhet) is the canonical `occupant_name`; the re-user (Merenkhons,
    Dyn XXII) goes in `notes_from_pm`. Asserts every field per rule 5.
    """
    r = _row("KV45")
    assert r["tomb_id"] == "KV45"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Userhet"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Official"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == (
        "Overseer of the Fields of Amun, Dyn. XVIII, re-used by Merenkhons, "
        "Doorkeeper of the House of Amun, Dyn. XXII (name from scarab). "
        "Excavated by Davis and Carter"
    )
    assert r["source_citation"] == {
        "page": 562,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv46_yuia_and_thuiu_multi_occupant() -> None:
    """KV46 — multi-occupant tomb (Yuia + Thuiu, parents of Queen Teye).
    Exercises the multi-occupant row pattern: `occupant_name` joined with
    `" and "`, `occupant_role = "Royal Family"` (they are royal in-laws),
    biographical+relational prose captured in `notes_from_pm`. Asserts
    every field per rule 5.
    """
    r = _row("KV46")
    assert r["tomb_id"] == "KV46"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Yuia and Thuiu"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Royal Family"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == (
        "Yuia, Divine father; Thuiu, Chief of the harim of Amun, parents "
        "of Queen Teye"
    )
    assert r["source_citation"] == {
        "page": 562,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


# ---------------------------------------------------------------------------
# Chunk-4 specific value-assertion tests (KV47, 48, 55, 56, 57)
# ---------------------------------------------------------------------------


def test_chunk4_page_range() -> None:
    """Chunk 4 headwords sit on PM I.2 printed pages 564–567."""
    for tid in CHUNK4_TOMB_IDS:
        r = _row(tid)
        page = r["source_citation"]["page"]
        assert 564 <= page <= 567, (tid, page)
        assert r["source_citation"]["edition"] == EDITION_PM_I2
        assert r["source_citation"]["section"] == "I.A"


def test_chunk4_all_rows_valley_of_kings_no_dynasty_or_dates() -> None:
    """Every chunk-4 row has valley=VoK and null dynasty/dates/discoverer."""
    for tid in CHUNK4_TOMB_IDS:
        r = _row(tid)
        assert r["valley"] == "Valley of the Kings"
        assert r["dynasty"] is None
        assert r["sub_period"] is None
        assert r["date_bce_approx_start"] is None
        assert r["date_bce_approx_end"] is None
        assert r["discovery_year"] is None
        assert r["discoverer"] is None


def test_chunk4_missing_kv_ids_absent_from_expected_set() -> None:
    """KV49–54 and KV58–61 are absent from PM I.2 § I.A (PM jumps 48 → 55
    and 57 → 62). KV62 (Tutʿankhamun) IS in the expected set as of chunk 5.
    """
    must_be_absent = (
        [f"KV{n}" for n in range(49, 55)]
        + [f"KV{n}" for n in range(58, 62)]
    )
    for tid in must_be_absent:
        assert tid not in EXPECTED_TOMB_IDS, tid


def test_chunk4_kv47_merneptah_siptah() -> None:
    """KV47 — Merneptah-Siptah, King, first Dyn-19 joint-name occupant.
    PM's `MERNEPTAḤ-SIPTAḤ` → `Merneptah-Siptah` (underdots stripped in
    occupant_name per the README's diacritic policy). Asserts every
    field per rule 5.
    """
    r = _row("KV47")
    assert r["tomb_id"] == "KV47"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Merneptah-Siptah"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 564,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk4_kv48_amenemopet_vizier() -> None:
    """KV48 — Amenemopet, Vizier, temp. Amenophis II. First `Vizier` role
    in the landed extract (vs `Official` for Bay in KV13). PM's notes
    clause preserves the title pair, regnal-dating, and TT29 cross-ref.
    Asserts every field per rule 5.
    """
    r = _row("KV48")
    assert r["tomb_id"] == "KV48"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Amenemopet"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Vizier"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == (
        "Governor of the town, Vizier. Temp. Amenophis II. "
        "(Also owner of Theb. tb. 29.)"
    )
    assert r["source_citation"] == {
        "page": 565,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk4_kv55_amenophis_iv_hedged_attribution() -> None:
    """KV55 — PM's headword: `Probably AMENOPHIS IV, formerly attributed
    to Queen Teye or to Smenkhkarēʿ.` The structured `occupant_name`
    strips PM's `Probably` hedge (clean matchable name); the full
    hedging clause is captured verbatim in `notes_from_pm` including
    PM's macron-e and trailing ayin on `Smenkhkarēʿ`. Asserts every
    field per rule 5.
    """
    r = _row("KV55")
    assert r["tomb_id"] == "KV55"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Amenophis IV"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == (
        "Probably Amenophis IV, formerly attributed to Queen Teye or to "
        "Smenkhkarēʿ."
    )
    assert r["source_citation"] == {
        "page": 565,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk4_kv56_gold_tomb_uninscribed() -> None:
    """KV56 — PM's `'Gold Tomb', uninscribed.` (the nickname stems from
    the rich Tausert / Sethos II jewelry finds in this tomb). Null name
    + `Unknown` role + PM's nickname captured verbatim in notes.
    Asserts every field per rule 5.
    """
    r = _row("KV56")
    assert r["tomb_id"] == "KV56"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] is None
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Unknown"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "'Gold Tomb', uninscribed."
    assert r["source_citation"] == {
        "page": 567,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk4_kv57_haremhab() -> None:
    """KV57 — Haremhab, King. PM's `ḤAREMḤAB` → `Haremhab` (underdots
    stripped in occupant_name). Asserts every field per rule 5.
    """
    r = _row("KV57")
    assert r["tomb_id"] == "KV57"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Haremhab"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 567,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


# ---------------------------------------------------------------------------
# Chunk-5 specific value-assertion tests (KV62 Tutʿankhamun, standalone)
# ---------------------------------------------------------------------------


def test_chunk5_kv62_tutankhamun_full_row() -> None:
    """KV62 — Tutʿankhamun, standalone single-row chunk. Exercises PM's
    ayin glyph preservation in `occupant_name` (matches chunk-2 KV19
    `Raʿmeses-Mentuhirkhopshef` precedent — ayin is a royal-name
    radical, not a styling diacritic, so preserved even though the
    `occupant_name` field otherwise strips diacritics).

    Also exercises the joint `notes_from_pm` capture:
    - PM's `[1st ed. 58]` cross-ref → `"1st ed. 58"` (same normalisation
      as chunk-3 KV34).
    - PM's `Excavated by Carnarvon and Carter.` ribbon clause.
    - Joined with `". "` per chunk-2 KV14 pattern.

    Asserts every field per CLAUDE.md rule 5.
    """
    r = _row("KV62")
    assert r["tomb_id"] == "KV62"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Tutʿankhamun"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == (
        "1st ed. 58. Excavated by Carnarvon and Carter."
    )
    assert r["source_citation"] == {
        "page": 569,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


# ---------------------------------------------------------------------------
# Audit-trail tests for fix_rows.py
# ---------------------------------------------------------------------------


def _import_fix_rows():
    """Load the source's fix_rows.py module by file path (the directory has a
    hyphen so `importlib.import_module` doesn't work directly).
    """
    spec = importlib.util.spec_from_file_location(
        "pm_theban_fix_rows", SOURCE_DIR / "fix_rows.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_all_corrections_includes_every_chunk_list() -> None:
    """fix_rows.py's `ALL_CORRECTIONS` aggregates every `CHUNK*_CORRECTIONS`
    list. Dropping a chunk's corrections list silently destroys its audit
    trail — this test fails loud if a chunk is added without being included.

    Uses natural-numeric sort on the chunk suffix (NOT lexicographic sort)
    so the test stays correct at chunk 10+. Gemini code-review on PR #71
    flagged that the prior lex-sort would mis-order `CHUNK10` before
    `CHUNK2`, invalidating the equality assertion against a numerically-
    ordered `ALL_CORRECTIONS`.
    """
    fix_rows = _import_fix_rows()
    chunk_re = re.compile(r"^CHUNK(\d+)_CORRECTIONS$")
    chunk_attrs = sorted(
        (attr for attr in dir(fix_rows) if chunk_re.match(attr)),
        key=lambda attr: int(chunk_re.match(attr).group(1)),
    )
    expected = [getattr(fix_rows, a) for a in chunk_attrs]
    assert fix_rows.ALL_CORRECTIONS == expected, (
        f"ALL_CORRECTIONS missing one of the per-chunk lists. "
        f"Found chunk attrs: {chunk_attrs}"
    )
