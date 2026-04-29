"""Unit tests for Beckerath merge.py's tie-break enforcement.

Covers (issue #144, mirrors Leprohon PR #128):
  * `_majority` raises on unresolved IDENTIFIER ties (no override,
    no clear majority) — option (a) enforcement, "data is sacred,
    fail loudly".
  * `TIE_BREAK_OVERRIDES` lookup resolves IDENTIFIER ties when an
    explicit override exists.
  * 1/1 partial-row ties (one agent missed the row, the other two
    disagree on a field) raise too — these are the dominant tie
    shape on Beckerath's current data.
  * `_majority` requires keyword-only `bid` and `field` (no silent
    first-seen fallback).
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SOURCE_DIR = (
    Path(__file__).parent.parent
    / "pipeline" / "authority" / "sources" / "beckerath-1997-chronologie"
)
MERGE_PY = SOURCE_DIR / "merge.py"


@pytest.fixture(scope="module")
def merge_module():
    spec = importlib.util.spec_from_file_location("beckerath_merge", MERGE_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# === _majority — unanimous and clear majority ============================

def test_majority_unanimous_returns_value(merge_module):
    """All three agents agree → value, count = 3."""
    values = ["Hor Aha", "Hor Aha", "Hor Aha"]
    chosen, count = merge_module._majority(values, bid="01.01", field="egyptian_titulary")
    assert chosen == "Hor Aha"
    assert count == 3


def test_majority_clear_majority_returns_majority_value(merge_module):
    """Two agree, one differs → majority value, count = 2."""
    values = ["Cheops", "Cheops", "Cheops (Chufu)"]
    chosen, count = merge_module._majority(values, bid="04.02", field="name")
    assert chosen == "Cheops"
    assert count == 2


def test_majority_two_agents_one_dropped_majority_resolves(merge_module):
    """When `present` already filtered out the missing agent and two
    remaining agents agree → majority value, count = 2."""
    values = ["Apophis", "Apophis"]
    chosen, count = merge_module._majority(values, bid="15.05", field="name")
    assert chosen == "Apophis"
    assert count == 2


# === _majority — tie with explicit override ==============================

def test_majority_tie_with_override_uses_override(merge_module):
    """1/1/1 tie with a TIE_BREAK_OVERRIDES entry → override value."""
    key = ("test.99", "name")
    merge_module.TIE_BREAK_OVERRIDES[key] = {
        "value": "RESOLVED",
        "rationale": "test fixture",
    }
    try:
        values = ["alpha", "beta", "gamma"]
        chosen, _ = merge_module._majority(
            values, bid="test.99", field="name"
        )
        assert chosen == "RESOLVED"
    finally:
        del merge_module.TIE_BREAK_OVERRIDES[key]


def test_majority_one_one_tie_with_override_uses_override(merge_module):
    """1/1 partial-row tie (one agent missed the row) with an override
    → override value. This is the dominant tie shape on Beckerath's
    current data — see the 03.06 cohort in tie-break-overrides.json."""
    key = ("test.99", "start_bce_high")
    merge_module.TIE_BREAK_OVERRIDES[key] = {
        "value": -2663,
        "rationale": "test fixture (1/1 partial-row tie)",
    }
    try:
        # Only two agents present; they disagree.
        values = [-2663, None]
        chosen, _ = merge_module._majority(
            values, bid="test.99", field="start_bce_high"
        )
        assert chosen == -2663
    finally:
        del merge_module.TIE_BREAK_OVERRIDES[key]


# === _majority — tie raises on uncovered IDENTIFIER ======================

def test_majority_tie_uncovered_identifier_raises(merge_module):
    """1/1/1 IDENTIFIER tie with NO override → ValueError naming
    candidates and pointing at tie-break-overrides.json."""
    values = ["alpha", "beta", "gamma"]
    with pytest.raises(ValueError) as exc:
        merge_module._majority(values, bid="uncov.99", field="name")
    msg = str(exc.value)
    assert "Unresolved IDENTIFIER tie" in msg
    assert "uncov.99" in msg
    assert "name" in msg
    assert "tie-break-overrides.json" in msg
    # Diagnostic must enumerate every candidate so the next agent
    # adding the override has the values in front of it.
    assert '"alpha"' in msg
    assert '"beta"' in msg
    assert '"gamma"' in msg


def test_majority_one_one_partial_row_tie_uncovered_raises(merge_module):
    """1/1 tie (only 2 agents present, they disagree) with no override
    → raise. Pre-#144, this case was silently first-seen-picked by
    `Counter.most_common(1)[0]`."""
    values = [-2663, None]
    with pytest.raises(ValueError) as exc:
        merge_module._majority(
            values, bid="uncov.99", field="start_bce_high"
        )
    msg = str(exc.value)
    assert "Unresolved IDENTIFIER tie" in msg
    assert "-2663" in msg
    assert "null" in msg


# === _majority — sentinel-null deep normalisation =========================

def test_majority_sentinel_null_collapses_to_none(merge_module):
    """`-` and other sentinel strings normalise to None, so an agent
    emitting `"-"` and another emitting `null` for the same cell is
    NOT a tie — both mean "no value" per Beckerath's typography."""
    values = ["-", None, None]
    chosen, count = merge_module._majority(
        values, bid="X.99", field="egyptian_titulary"
    )
    assert chosen is None
    assert count == 3


# === _majority — keyword-only bid/field ====================================

def test_majority_requires_bid_and_field(merge_module):
    """Constitutional rule 10: no silent first-seen fallback for
    'legacy callers'. `bid` and `field` are keyword-only required.
    Mirrors the Leprohon `_majority` signature in PR #128."""
    with pytest.raises(TypeError):
        merge_module._majority(["a", "b", "c"])
    with pytest.raises(TypeError):
        merge_module._majority(["a", "b", "c"], bid="x.01")
    with pytest.raises(TypeError):
        merge_module._majority(["a", "b", "c"], field="name")


# === overrides file — schema validation =================================

def test_load_overrides_rejects_keys_without_separator(merge_module, tmp_path):
    """`tie-break-overrides.json` keys must be `<bid>|<field>`. A key
    without `|` is a malformed entry — raise loudly per rule 2."""
    bad = tmp_path / "tie-break-overrides.json"
    bad.write_text(json.dumps({"badkey": {"value": 1, "rationale": "x"}}))
    # Patch the module-level path; restore after.
    orig = merge_module._OVERRIDES_PATH
    merge_module._OVERRIDES_PATH = bad
    try:
        with pytest.raises(ValueError, match="missing '|' separator"):
            merge_module._load_overrides()
    finally:
        merge_module._OVERRIDES_PATH = orig


# === reconciled.jsonl pins for current overrides ========================
#
# Lock specific resolved values on disk so a future re-run of merge.py
# without the override table can't drift back to a silent first-seen
# pick. Each test names a row × field that the current
# `tie-break-overrides.json` resolves and asserts the value in the
# committed reconciled.jsonl matches.

@pytest.fixture(scope="module")
def reconciled():
    path = SOURCE_DIR / "reconciled.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _row(reconciled: list, bid: str) -> dict:
    hits = [r for r in reconciled if r["beckerath_id"] == bid]
    assert len(hits) == 1, f"expected 1 row for {bid}, got {len(hits)}"
    return hits[0]


def test_03_06_brace_bracket_dates_pinned(reconciled):
    """03.06 Ahu (Huni, Aches) — brace bracket on book p187 (scan-105-
    right). Agent C dropped this row; A and B split 1/1 on every date.
    Override pins agent A's bracket-shared dates matching 03.04 / 03.05.
    Pre-#144 the silent first-seen happened to land on these values
    too; this test makes that traceable to the override + citation."""
    r = _row(reconciled, "03.06")
    assert r["start_bce_high"] == -2663
    assert r["start_bce_low"] == -2613
    assert r["end_bce_high"] == -2639
    assert r["end_bce_low"] == -2589
    assert r["name"] == "Ahu (Huni, Aches)"
    assert r["egyptian_titulary"] is None
    assert r["egyptian_titulary_kind"] is None


def test_15_04_chajan_name_pinned(reconciled):
    """15.04 Chajan — 1/1/1 tie on `name`. Override pins agent B's
    bare `Chajan` form per the Greek-alias + Egyptian-prenomen pair
    discriminator (compound moves to egyptian_titulary via fix_rows)."""
    r = _row(reconciled, "15.04")
    assert r["name"] == "Chajan"


def test_19_08_te_wosret_name_pinned(reconciled):
    """19.08 Kgin.Te-wosret — 1/1/1 tie on `name`. Override pins agent
    C's no-space + no-parens form per the Kgin spacing standardisation
    + Co-regent queen rule."""
    r = _row(reconciled, "19.08")
    assert r["name"] == "Kgin.Te-wosret"


def test_dyn29_dyn30_name_post_fix_rows_split(reconciled):
    """Dyn 29-30 Late Period rows — 1/1/1 ties on `name` resolved by the
    tie-break override (pinning agent A's full compound to match
    Beckerath's verbatim print) AND THEN by the fix_rows.py 15.04-style
    split (issue #147) which realigns to the canonical kind=`mixed`
    pattern: name=bare Greek lemma, titulary=full inner compound.

    This test pins the post-fix_rows (final reconciled.jsonl) state.
    See `test_sources_beckerath_1997_chronologie.py::
    test_dyn29_dyn30_greek_egyptian_pair_split` for the full split-
    pattern assertion (name + titulary + kind together).
    """
    assert _row(reconciled, "29.03")["name"] == "Psamuthis"
    assert _row(reconciled, "30.01")["name"] == "Nektanebês"
    assert _row(reconciled, "30.02")["name"] == "Teôs"
    assert _row(reconciled, "30.03")["name"] == "Nektanebôs"


def test_overrides_json_keys_well_formed(merge_module):
    """Every key in tie-break-overrides.json parses as `<bid>|<field>`
    and every value carries a non-empty rationale with a strict citation.

    Tightened from a substring check ("page", "printed") to anchored
    regex on the actual citation conventions: `scan-NNN-(left|right)`,
    `book p<digits>`, `Anhang [AB]`, `PDF p<digits>`, or the canonical
    edition string. A future loose rationale ("the page was printed")
    no longer slips past — only structured printed-source references
    pass. (Code-reviewer P2-1 on PR #146.)
    """
    import re

    citation_pattern = re.compile(
        r"scan-\d{3}-(?:left|right)"           # scan-NNN-{left,right}
        r"|book\s+p\d+"                          # book p<digits>
        r"|PDF\s+p\d+"                           # PDF p<digits>
        r"|Anhang\s+[AB]"                        # Anhang A | Anhang B
        r"|Supplement\s+zu\s+A"                  # Supplement zu A
        r"|MÄS\s+46",                            # canonical edition
        re.IGNORECASE,
    )
    for (bid, field), entry in merge_module.TIE_BREAK_OVERRIDES.items():
        assert bid, f"empty bid in key ({bid!r}, {field!r})"
        assert field, f"empty field in key ({bid!r}, {field!r})"
        assert "rationale" in entry, f"override ({bid!r}, {field!r}) missing rationale"
        rationale = entry["rationale"]
        assert isinstance(rationale, str) and len(rationale) >= 20, (
            f"rationale for ({bid!r}, {field!r}) too short to carry a "
            f"citation: {rationale!r}"
        )
        assert citation_pattern.search(rationale), (
            f"rationale for ({bid!r}, {field!r}) lacks a structured printed-"
            f"source citation matching scan-NNN-{{left,right}} / book p<digits> "
            f"/ PDF p<digits> / Anhang [AB] / Supplement zu A / MÄS 46. "
            f"Got: {rationale!r}"
        )


def test_load_overrides_rejects_empty_bid(merge_module, tmp_path):
    """`<empty>|name` must raise — silent dead overrides hide bugs.
    (Code-reviewer P1.1 on PR #146.)"""
    bad = tmp_path / "tie-break-overrides.json"
    bad.write_text(json.dumps({"|name": {"value": "x", "rationale": "test fixture for empty bid"}}))
    orig = merge_module._OVERRIDES_PATH
    merge_module._OVERRIDES_PATH = bad
    try:
        with pytest.raises(ValueError, match="empty bid or field"):
            merge_module._load_overrides()
    finally:
        merge_module._OVERRIDES_PATH = orig


def test_load_overrides_rejects_empty_field(merge_module, tmp_path):
    """`03.06|<empty>` must raise — silent dead overrides hide bugs.
    (Code-reviewer P1.1 on PR #146.)"""
    bad = tmp_path / "tie-break-overrides.json"
    bad.write_text(json.dumps({"03.06|": {"value": "x", "rationale": "test fixture for empty field"}}))
    orig = merge_module._OVERRIDES_PATH
    merge_module._OVERRIDES_PATH = bad
    try:
        with pytest.raises(ValueError, match="empty bid or field"):
            merge_module._load_overrides()
    finally:
        merge_module._OVERRIDES_PATH = orig


def test_override_value_passes_through_deep_normalise(merge_module):
    """Per Gemini PR #155 round-2 (parity from Kitchen). A sentinel-null
    encoded in an override `value` collapses to None at merge time."""
    key = ("test.99", "egyptian_titulary")
    merge_module.TIE_BREAK_OVERRIDES[key] = {
        "value": "-",
        "rationale": "test fixture (sentinel-null override)",
    }
    try:
        values = ["alpha", "beta", "gamma"]
        chosen, _ = merge_module._majority(
            values, bid="test.99", field="egyptian_titulary"
        )
        assert chosen is None
    finally:
        del merge_module.TIE_BREAK_OVERRIDES[key]


def test_load_overrides_rejects_non_dict_root(merge_module, tmp_path):
    """Per Gemini PR #157 round-1 (parity from Ryholt). Top-level JSON
    must be a dict — list/null/string at root would otherwise raise
    AttributeError at `.items()`."""
    for bad_root in ([], "string-at-root", 42):
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
    """Per Gemini PR #155 round-1 (parity from Kitchen). Bare-string
    value would silently fail at merge-time `override['value']` lookup."""
    bad = tmp_path / "tie-break-overrides.json"
    bad.write_text(json.dumps({"03.06|name": "Ahu (Huni, Aches)"}))
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
    bad.write_text(json.dumps({"03.06|name": {"rationale": "missing value key"}}))
    orig = merge_module._OVERRIDES_PATH
    merge_module._OVERRIDES_PATH = bad
    try:
        with pytest.raises(ValueError, match="missing required key"):
            merge_module._load_overrides()
    finally:
        merge_module._OVERRIDES_PATH = orig


def test_load_overrides_rejects_missing_rationale_key(merge_module, tmp_path):
    """Per Gemini PR #155 round-1 (parity from Kitchen). Citation is
    load-bearing per constitutional rule 6."""
    bad = tmp_path / "tie-break-overrides.json"
    bad.write_text(json.dumps({"03.06|name": {"value": "Ahu (Huni, Aches)"}}))
    orig = merge_module._OVERRIDES_PATH
    merge_module._OVERRIDES_PATH = bad
    try:
        with pytest.raises(ValueError, match="missing required key"):
            merge_module._load_overrides()
    finally:
        merge_module._OVERRIDES_PATH = orig


def test_sentinel_null_strings_includes_null_for_leprohon_parity(merge_module):
    """`"null"` is a recognised sentinel-null on Leprohon's side.
    Beckerath agents transcribing the literal string `"null"` for an
    absent cell must collapse to None too — otherwise a `(None, "null")`
    pair registers as a tie. (Code-reviewer P1.3 on PR #146.)
    """
    assert "null" in merge_module.SENTINEL_NULL_STRINGS
