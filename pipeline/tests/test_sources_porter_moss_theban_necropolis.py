"""Structural value-assertion tests for Porter & Moss Vol I source extract.

Per CLAUDE.md rule 5: every populated field on every fixture-class row is
asserted, not just the field the test class is "themed" around.

Chunk 1 covers KV1–KV10 (PM I.2 § I.A "Tombs", printed p.495–518). Future
chunks (KV11–KV65, QV, TT...) extend `EXPECTED_TOMB_IDS` and add per-chunk
value-assertion tests; the structural tests below are forward-compatible.
"""

from __future__ import annotations

import importlib
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

# Chunk-1 (KV1–KV10) is the only landed chunk so far. Extend this set in
# follow-up chunk PRs; the row-count and ID-coverage tests reference it
# rather than hard-coded numbers so the tests stay correct as the source grows.
CHUNK1_TOMB_IDS: frozenset[str] = frozenset(
    {f"KV{n}" for n in range(1, 11)}
)
EXPECTED_TOMB_IDS: frozenset[str] = CHUNK1_TOMB_IDS


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


_TOMB_ID_RE = re.compile(r"^(KV|QV|TT)\d+[a-z]?$")


def test_tomb_id_shape() -> None:
    """Every id matches `(KV|QV|TT)\\d+[a-z]?`."""
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


def test_dynasty_is_string() -> None:
    """`dynasty` is a string (Arabic-numeral form), not int. Phase A relies
    on the string form for joining against the king authority — drift to
    int silently breaks that join.
    """
    for r in _rows():
        if r["dynasty"] is not None:
            assert isinstance(r["dynasty"], str), (r["tomb_id"], r["dynasty"])


def test_dates_are_negative_ints() -> None:
    """BCE convention: every date_bce_approx_* field is a negative integer
    (or null). Positive ints would mean CE — out of scope for any Theban
    tomb in PM Vol I.
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
    means an extraction bug.
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


def test_chunk1_all_kv_kings_in_dyn_19_or_20() -> None:
    """KV1–KV10 are all Ramesside or near-Ramesside (Merneptah). Dyn 19/20 only."""
    for tid in CHUNK1_TOMB_IDS:
        r = _row(tid)
        assert r["dynasty"] in ("19", "20"), (tid, r["dynasty"])
        assert r["valley"] == "Valley of the Kings"
        assert r["occupant_role"] == "King"
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


def test_chunk1_kv1_ramesses_vii_full_row() -> None:
    """Flagship row: assert every populated field for KV1.

    Per rule 5: a fixture-class test asserts EVERY field, not just the
    fields the test name suggests.
    """
    r = _row("KV1")
    assert r["tomb_id"] == "KV1"
    assert r["valley"] == "Valley of the Kings"
    assert r["occupant_name"] == "Ramesses VII"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] == "20"
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] == -1136
    assert r["date_bce_approx_end"] == -1129
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


def test_chunk1_kv9_ramesses_vi_notes_preserved() -> None:
    """KV9's headword carries the verbatim phrase `doorways in outer part
    usurped from` (the sentence continues onto the next line into body
    prose; only the headword fragment is in scope). Per the prompt's
    headword-only rule, the short fragment is kept as-is — completion to
    `... from Ramesses V` requires reading body prose, which is out of scope.
    """
    r = _row("KV9")
    assert r["occupant_name"] == "Ramesses VI"
    assert r["dynasty"] == "20"
    assert r["date_bce_approx_start"] == -1145
    assert r["date_bce_approx_end"] == -1137
    assert r["notes_from_pm"] == "doorways in outer part usurped from"
    assert r["source_citation"]["page"] == 511


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
    the actual completed tomb). Both rows present, identical Dyn 19 dates,
    different is_unfinished flags, mutually-cross-referenced via
    shared_with_tombs.
    """
    kv5 = _row("KV5")
    kv7 = _row("KV7")
    for r in (kv5, kv7):
        assert r["occupant_name"] == "Ramesses II"
        assert r["dynasty"] == "19"
        assert r["date_bce_approx_start"] == -1279
        assert r["date_bce_approx_end"] == -1213
    assert kv5["is_unfinished"] is True
    assert kv7["is_unfinished"] is False
    assert kv5["shared_with_tombs"] == ["KV7"]
    assert kv7["shared_with_tombs"] == ["KV5"]
    assert kv5["source_citation"]["page"] == 501
    assert kv7["source_citation"]["page"] == 505


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
    """
    fix_rows = _import_fix_rows()
    chunk_attrs = sorted(
        attr for attr in dir(fix_rows)
        if attr.startswith("CHUNK") and attr.endswith("_CORRECTIONS")
    )
    expected = [getattr(fix_rows, a) for a in chunk_attrs]
    assert fix_rows.ALL_CORRECTIONS == expected, (
        f"ALL_CORRECTIONS missing one of the per-chunk lists. "
        f"Found chunk attrs: {chunk_attrs}"
    )
