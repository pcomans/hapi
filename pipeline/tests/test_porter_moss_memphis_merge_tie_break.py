"""Unit tests for the Porter-Moss Memphis merge.py tie-break enforcement.

Mirrors the canonical pattern in PR #128 (Leprohon) / PR #146 (Beckerath) /
the Porter-Moss Theban tie-break tests. Issue #145.

Memphis has no overrides yet (chunk 1 merged cleanly with all ties resolved
by real 2/1 majorities), so this file omits the reconciled-pin section that
the Theban variant carries. The `test_overrides_json_keys_well_formed` is
kept as a forward-compatibility check that asserts the shape any future
override entry must satisfy.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

SOURCE_DIR = (
    Path(__file__).parent.parent
    / "pipeline" / "authority" / "sources" / "porter-moss-memphis"
)
MERGE_PY = SOURCE_DIR / "merge.py"


@pytest.fixture(scope="module")
def merge_module():
    spec = importlib.util.spec_from_file_location("pm_memphis_merge", MERGE_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# === _majority — unanimous and clear majority ============================

def test_majority_unanimous_returns_value(merge_module):
    values = ["Khufu", "Khufu", "Khufu"]
    chosen, count = merge_module._majority(values, tid="G1", field="occupant_name")
    assert chosen == "Khufu"
    assert count == 3


def test_majority_clear_majority_returns_majority_value(merge_module):
    values = ["Menkaureʿ", "Menkaureʿ", "Menkaure"]
    chosen, count = merge_module._majority(values, tid="G3", field="occupant_name")
    assert chosen == "Menkaureʿ"
    assert count == 2


def test_majority_two_agents_one_dropped_majority_resolves(merge_module):
    values = ["G1", "G1"]
    chosen, count = merge_module._majority(values, tid="G1", field="tomb_id")
    assert chosen == "G1"
    assert count == 2


# === _majority — tie with override =====================================

def test_majority_tie_with_override_uses_override(merge_module):
    key = ("test.99", "occupant_name")
    merge_module.TIE_BREAK_OVERRIDES[key] = {
        "value": "RESOLVED",
        "rationale": "test fixture",
    }
    try:
        values = ["alpha", "beta", "gamma"]
        chosen, _ = merge_module._majority(
            values, tid="test.99", field="occupant_name"
        )
        assert chosen == "RESOLVED"
    finally:
        del merge_module.TIE_BREAK_OVERRIDES[key]


def test_majority_one_one_partial_row_tie_with_override(merge_module):
    key = ("test.99", "discoverer")
    merge_module.TIE_BREAK_OVERRIDES[key] = {
        "value": "Reisner",
        "rationale": "test fixture",
    }
    try:
        values = ["Reisner", None]
        chosen, _ = merge_module._majority(
            values, tid="test.99", field="discoverer"
        )
        assert chosen == "Reisner"
    finally:
        del merge_module.TIE_BREAK_OVERRIDES[key]


# === _majority — tie raises ============================================

def test_majority_tie_uncovered_identifier_raises(merge_module):
    values = ["alpha", "beta", "gamma"]
    with pytest.raises(ValueError) as exc:
        merge_module._majority(values, tid="uncov.99", field="occupant_name")
    msg = str(exc.value)
    assert "Unresolved IDENTIFIER tie" in msg
    assert "uncov.99" in msg
    assert "occupant_name" in msg
    assert "tie-break-overrides.json" in msg


def test_majority_one_one_partial_row_tie_uncovered_raises(merge_module):
    values = ["Reisner", None]
    with pytest.raises(ValueError) as exc:
        merge_module._majority(values, tid="uncov.99", field="discoverer")
    msg = str(exc.value)
    assert "Unresolved IDENTIFIER tie" in msg


# === _majority — sentinel-null normalisation ===========================

def test_majority_sentinel_null_collapses_to_none(merge_module):
    values = ["-", None, None]
    chosen, count = merge_module._majority(
        values, tid="X.99", field="discoverer"
    )
    assert chosen is None
    assert count == 3


def test_sentinel_null_strings_includes_null_for_parity(merge_module):
    """Per PR #146 P1.3 — `null` is a recognised sentinel-null on Leprohon's
    side; PM merges across the same canonical surface so it must collapse
    `"null"` strings too."""
    assert "null" in merge_module.SENTINEL_NULL_STRINGS


# === _majority — keyword-only tid/field ================================

def test_majority_requires_tid_and_field(merge_module):
    """Constitutional rule 10: no silent first-seen fallback."""
    with pytest.raises(TypeError):
        merge_module._majority(["a", "b", "c"])
    with pytest.raises(TypeError):
        merge_module._majority(["a", "b", "c"], tid="x.01")
    with pytest.raises(TypeError):
        merge_module._majority(["a", "b", "c"], field="occupant_name")


# === overrides file — schema validation ================================

def test_load_overrides_rejects_keys_without_separator(merge_module, tmp_path):
    bad = tmp_path / "tie-break-overrides.json"
    bad.write_text(json.dumps({"badkey": {"value": 1, "rationale": "x"}}))
    orig = merge_module._OVERRIDES_PATH
    merge_module._OVERRIDES_PATH = bad
    try:
        with pytest.raises(ValueError, match="missing '|' separator"):
            merge_module._load_overrides()
    finally:
        merge_module._OVERRIDES_PATH = orig


def test_load_overrides_rejects_empty_tid(merge_module, tmp_path):
    bad = tmp_path / "tie-break-overrides.json"
    bad.write_text(json.dumps({"|occupant_name": {"value": "x", "rationale": "test fixture for empty tid"}}))
    orig = merge_module._OVERRIDES_PATH
    merge_module._OVERRIDES_PATH = bad
    try:
        with pytest.raises(ValueError, match="empty tomb_id or field"):
            merge_module._load_overrides()
    finally:
        merge_module._OVERRIDES_PATH = orig


def test_load_overrides_rejects_empty_field(merge_module, tmp_path):
    bad = tmp_path / "tie-break-overrides.json"
    bad.write_text(json.dumps({"G1|": {"value": "x", "rationale": "test fixture for empty field"}}))
    orig = merge_module._OVERRIDES_PATH
    merge_module._OVERRIDES_PATH = bad
    try:
        with pytest.raises(ValueError, match="empty tomb_id or field"):
            merge_module._load_overrides()
    finally:
        merge_module._OVERRIDES_PATH = orig


def test_override_value_passes_through_deep_normalise(merge_module):
    """Per Gemini PR #155 round-2 (parity from Kitchen)."""
    key = ("test.99", "discoverer")
    merge_module.TIE_BREAK_OVERRIDES[key] = {
        "value": "-",
        "rationale": "test fixture (sentinel-null override)",
    }
    try:
        values = ["alpha", "beta", "gamma"]
        chosen, _ = merge_module._majority(
            values, tid="test.99", field="discoverer"
        )
        assert chosen is None
    finally:
        del merge_module.TIE_BREAK_OVERRIDES[key]


def test_load_overrides_rejects_non_dict_root(merge_module, tmp_path):
    """Per Gemini PR #157 round-1 (parity from Ryholt)."""
    for bad_root in ([], "string-at-root", 42, None):
        bad = tmp_path / "tie-break-overrides.json"
        bad.write_text(json.dumps(bad_root))
        orig = merge_module._OVERRIDES_PATH
        merge_module._OVERRIDES_PATH = bad
        try:
            with pytest.raises(ValueError, match="top-level JSON must be a dict"):
                merge_module._load_overrides()
        finally:
            merge_module._OVERRIDES_PATH = orig


def test_load_overrides_rejects_non_dict_value(merge_module, tmp_path):
    """Per Gemini PR #155 round-1 (parity from Kitchen)."""
    bad = tmp_path / "tie-break-overrides.json"
    bad.write_text(json.dumps({"G1|occupant_name": "Khufu"}))
    orig = merge_module._OVERRIDES_PATH
    merge_module._OVERRIDES_PATH = bad
    try:
        with pytest.raises(ValueError, match="must be a dict"):
            merge_module._load_overrides()
    finally:
        merge_module._OVERRIDES_PATH = orig


def test_load_overrides_rejects_missing_value_key(merge_module, tmp_path):
    """Per Gemini PR #155 round-1 (parity from Kitchen)."""
    bad = tmp_path / "tie-break-overrides.json"
    bad.write_text(json.dumps({"G1|occupant_name": {"rationale": "missing value key"}}))
    orig = merge_module._OVERRIDES_PATH
    merge_module._OVERRIDES_PATH = bad
    try:
        with pytest.raises(ValueError, match="missing required key"):
            merge_module._load_overrides()
    finally:
        merge_module._OVERRIDES_PATH = orig


def test_load_overrides_rejects_missing_rationale_key(merge_module, tmp_path):
    """Per Gemini PR #155 round-1 (parity from Kitchen)."""
    bad = tmp_path / "tie-break-overrides.json"
    bad.write_text(json.dumps({"G1|occupant_name": {"value": "Khufu"}}))
    orig = merge_module._OVERRIDES_PATH
    merge_module._OVERRIDES_PATH = bad
    try:
        with pytest.raises(ValueError, match="missing required key"):
            merge_module._load_overrides()
    finally:
        merge_module._OVERRIDES_PATH = orig


# === current overrides set (chunk-2 G7000x notes_from_pm 1/1/1 tie) =====

def test_tie_break_overrides_contains_documented_chunks(merge_module):
    """Documented 1/1/1 ties with printed-source citations:

    - Chunk 2: `G7000x|notes_from_pm` (B. EAST FIELD opener; three
      agents truncated the headword block at three sentence boundaries).
    - Chunk 3: `LG84|occupant_alt_names` (PAKAP good name WEHEBREc-EMAKHET;
      three agents produced three raised-ayin variants).
    - Chunk 4: `SAQ-IputII|notes_from_pm`, `SAQ-Neit|notes_from_pm`,
      `SAQ-MerenreI|notes_from_pm` (three Saqqâra queen-enclosure /
      Dyn-VI-king rows where agents disagreed on period-before-PYRAMID
      and raised-ayin normalisation in the verbatim headword block).
    - Chunk 6: `G1151|notes_from_pm`, `G1201|notes_from_pm`,
      `G1221|notes_from_pm` (three West Field G 1000-1200 rows where
      agents disagreed on colon-vs-semicolon punctuation, underdot-Ḥ
      glyph normalisation for Meḥyt, and `(?)` hedge handling for SHAD).

    Constitutional rule 2: every tie-break has a documented printed-source
    citation; no first-seen-pick, no `Counter.most_common(1)[0]`-on-tie
    silent resolution. This test fails loud when a new chunk adds an
    override — forcing the author to document the addition here too.
    """
    overrides = merge_module.TIE_BREAK_OVERRIDES
    assert set(overrides.keys()) == {
        ("G7000x", "notes_from_pm"),
        ("LG84", "occupant_alt_names"),
        ("SAQ-IputII", "notes_from_pm"),
        ("SAQ-Neit", "notes_from_pm"),
        ("SAQ-MerenreI", "notes_from_pm"),
        ("G1151", "notes_from_pm"),
        ("G1201", "notes_from_pm"),
        ("G1221", "notes_from_pm"),
    }

    g7000x = overrides[("G7000x", "notes_from_pm")]
    assert "PM III.1" in g7000x["rationale"]
    assert "p.179" in g7000x["rationale"]
    assert g7000x["value"].startswith("TOMB OF HETEPHERES [I]")
    assert g7000x["value"].endswith("(1925-7).")

    lg84 = overrides[("LG84", "occupant_alt_names")]
    assert "PM III.1" in lg84["rationale"]
    assert "p.290" in lg84["rationale"]
    assert lg84["value"] == ["Wehebreʿ-emakhet"]

    for chunk4_key in [
        ("SAQ-IputII", "notes_from_pm"),
        ("SAQ-Neit", "notes_from_pm"),
        ("SAQ-MerenreI", "notes_from_pm"),
    ]:
        entry = overrides[chunk4_key]
        assert "PM III.2" in entry["rationale"], chunk4_key
        assert isinstance(entry["value"], str), chunk4_key


# === SENTINEL_NULL_STRINGS divergence tripwires ==========================
#
# Per Gemini PR #219 round-1 medium-priority finding (merge.py:153) and the
# scope-accountability-enforcer's follow-up: the deliberate divergence from
# the Theban-source `SENTINEL_NULL_STRINGS` (omitting `"unknown"`) creates a
# new latent foot-gun — if agents emit case-variant `"Unknown"` vs
# `"unknown"`, the merge no longer silently collapses them. These tests
# pin the contract that:
#   1. `_normalise_value` returns the literal string for ANY case-variant
#      of `Unknown` (no silent collapse to None).
#   2. A case-mixed `_majority` call raises (1/1/1) or picks the literal
#      majority (2/1) — both behaviours surface the issue at merge time
#      OR at schema-validation time, never silently drop the row.
# If a future edit re-adds `"unknown"` to `SENTINEL_NULL_STRINGS`, every
# assertion below flips, and the loud test failure points the future-author
# at the scope-accountability rationale documented in `merge.py:145-152`.


def test_unknown_literal_survives_normalisation(merge_module):
    """`merge._normalise_value` MUST return the literal string for any
    case-variant of "Unknown". Per the Memphis SENTINEL_NULL_STRINGS
    divergence, `"unknown"` is no longer a null sentinel — it survives
    as its literal string and is then either matched (majority vote) or
    rejected (downstream schema test `test_occupant_role_controlled_vocab`).
    """
    assert merge_module._normalise_value("Unknown") == "Unknown"
    assert merge_module._normalise_value("unknown") == "unknown"
    assert merge_module._normalise_value("UNKNOWN") == "UNKNOWN"
    # Sanity: actual null sentinels still collapse to None.
    assert merge_module._normalise_value("none") is None
    assert merge_module._normalise_value("—") is None
    assert merge_module._normalise_value("n/a") is None


def test_case_mixed_unknown_does_not_silently_collapse(merge_module):
    """A 1/1/1 case-mixed disagreement on `occupant_role` (each agent emits
    a different case-variant of "Unknown") MUST raise an unresolved-tie
    ValueError. This forces an explicit `tie-break-overrides.json` entry
    with a cited rationale — no silent first-seen pick.

    Without the SENTINEL_NULL_STRINGS divergence, this scenario would
    have silently collapsed all three values to None (the Theban
    behaviour); with the divergence, the literal strings survive and
    `_majority` does the right thing — fails loud.
    """
    with pytest.raises(ValueError, match="IDENTIFIER tie"):
        merge_module._majority(
            ["Unknown", "unknown", "UNKNOWN"],
            tid="TESTROW",
            field="occupant_role",
        )


def test_case_mixed_unknown_2_1_split_picks_literal_majority(merge_module):
    """A 2/1 case-mixed split picks the literal majority — `"Unknown"`
    wins over `"unknown"` because the two `"Unknown"` votes match
    exactly. The literal then either passes the downstream
    controlled-vocab schema test (if it's "Unknown") or fails loud
    (if a future scenario picks "unknown"). Either path is loud
    enough to surface case-mixing as a real issue.
    """
    chosen, count = merge_module._majority(
        ["Unknown", "Unknown", "unknown"],
        tid="TESTROW",
        field="occupant_role",
    )
    assert chosen == "Unknown"
    assert count == 2


def test_overrides_json_keys_well_formed(merge_module):
    """Forward-compatibility shape check: every key parses as `<tid>|<field>`
    and every rationale carries a structured printed-source citation. PM III
    citations match `PM III.<digit>` / `p. <digits>` / `page <digits>` /
    `book p<digits>` / `scan-NNN`. No-op while overrides is empty."""

    citation_pattern = re.compile(
        r"PM\s+III\.\d"                  # PM III.1 / PM III.2
        r"|p\.\s*\d+"                     # p. <digits>
        r"|page\s+\d+"                    # page <digits>
        r"|book\s+p\d+"                   # book p<digits>
        r"|scan-\d{3}",                   # scan-NNN
        re.IGNORECASE,
    )
    for (tid, field), entry in merge_module.TIE_BREAK_OVERRIDES.items():
        assert tid, f"empty tid in key ({tid!r}, {field!r})"
        assert field, f"empty field in key ({tid!r}, {field!r})"
        assert "rationale" in entry, f"override ({tid!r}, {field!r}) missing rationale"
        rationale = entry["rationale"]
        assert isinstance(rationale, str) and len(rationale) >= 20, (
            f"rationale for ({tid!r}, {field!r}) too short to carry a citation: {rationale!r}"
        )
        assert citation_pattern.search(rationale), (
            f"rationale for ({tid!r}, {field!r}) lacks a structured printed-"
            f"source citation matching `PM III.<digit>` / `p. <digits>` / "
            f"`page <digits>` / `book p<digits>` / `scan-NNN`. "
            f"Got: {rationale!r}"
        )
