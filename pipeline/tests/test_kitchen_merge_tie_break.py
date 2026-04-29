"""Unit tests for Kitchen-TIPE merge.py's tie-break enforcement.

Mirrors the canonical pattern in PR #128 (Leprohon) / PR #146 (Beckerath) /
PR #151 (Porter-Moss). Issue #136.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

SOURCE_DIR = (
    Path(__file__).parent.parent
    / "pipeline" / "authority" / "sources" / "kitchen-tipe"
)
MERGE_PY = SOURCE_DIR / "merge.py"


@pytest.fixture(scope="module")
def merge_module():
    spec = importlib.util.spec_from_file_location("kitchen_merge", MERGE_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# === _majority — unanimous and clear majority ============================

def test_majority_unanimous_returns_value(merge_module):
    values = ["Ramesses XI", "Ramesses XI", "Ramesses XI"]
    chosen, count = merge_module._majority(values, kid="20.01", field="name")
    assert chosen == "Ramesses XI"
    assert count == 3


def test_majority_clear_majority_returns_majority_value(merge_module):
    values = [-1098, -1098, -1099]
    chosen, count = merge_module._majority(values, kid="20.01", field="start_bce")
    assert chosen == -1098
    assert count == 2


# === _majority — tie with override =====================================

def test_majority_tie_with_override_uses_override(merge_module):
    key = ("test.99", "name")
    merge_module.TIE_BREAK_OVERRIDES[key] = {
        "value": "RESOLVED",
        "rationale": "test fixture",
    }
    try:
        values = ["alpha", "beta", "gamma"]
        chosen, _ = merge_module._majority(
            values, kid="test.99", field="name"
        )
        assert chosen == "RESOLVED"
    finally:
        del merge_module.TIE_BREAK_OVERRIDES[key]


def test_majority_one_one_partial_row_tie_with_override(merge_module):
    key = ("test.99", "prenomen")
    merge_module.TIE_BREAK_OVERRIDES[key] = {
        "value": "Aakheperre",
        "rationale": "test fixture",
    }
    try:
        values = ["Aakheperre", None]
        chosen, _ = merge_module._majority(
            values, kid="test.99", field="prenomen"
        )
        assert chosen == "Aakheperre"
    finally:
        del merge_module.TIE_BREAK_OVERRIDES[key]


# === _majority — tie raises ============================================

def test_majority_tie_uncovered_identifier_raises(merge_module):
    values = ["alpha", "beta", "gamma"]
    with pytest.raises(ValueError) as exc:
        merge_module._majority(values, kid="uncov.99", field="name")
    msg = str(exc.value)
    assert "Unresolved IDENTIFIER tie" in msg
    assert "uncov.99" in msg
    assert "name" in msg
    assert "tie-break-overrides.json" in msg


def test_majority_one_one_partial_row_tie_uncovered_raises(merge_module):
    values = [-1098, None]
    with pytest.raises(ValueError) as exc:
        merge_module._majority(values, kid="uncov.99", field="start_bce")
    msg = str(exc.value)
    assert "Unresolved IDENTIFIER tie" in msg


# === sentinel-null + null parity =======================================

def test_majority_sentinel_null_collapses_to_none(merge_module):
    values = ["-", None, None]
    chosen, count = merge_module._majority(
        values, kid="X.99", field="prenomen"
    )
    assert chosen is None
    assert count == 3


def test_sentinel_null_strings_includes_null_for_leprohon_parity(merge_module):
    """Per PR #146 P1.3 — `null` is a recognised sentinel-null on
    Leprohon's side; Kitchen merges across the same canonical surface."""
    assert "null" in merge_module.SENTINEL_NULL_STRINGS


# === _majority — keyword-only kid/field ================================

def test_majority_requires_kid_and_field(merge_module):
    """Constitutional rule 10: no silent first-seen fallback."""
    with pytest.raises(TypeError):
        merge_module._majority(["a", "b", "c"])
    with pytest.raises(TypeError):
        merge_module._majority(["a", "b", "c"], kid="x.01")
    with pytest.raises(TypeError):
        merge_module._majority(["a", "b", "c"], field="name")


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


def test_load_overrides_rejects_empty_kid(merge_module, tmp_path):
    bad = tmp_path / "tie-break-overrides.json"
    bad.write_text(json.dumps({"|name": {"value": "x", "rationale": "test fixture for empty kid"}}))
    orig = merge_module._OVERRIDES_PATH
    merge_module._OVERRIDES_PATH = bad
    try:
        with pytest.raises(ValueError, match="empty kitchen_id or field"):
            merge_module._load_overrides()
    finally:
        merge_module._OVERRIDES_PATH = orig


def test_load_overrides_rejects_empty_field(merge_module, tmp_path):
    bad = tmp_path / "tie-break-overrides.json"
    bad.write_text(json.dumps({"20.01|": {"value": "x", "rationale": "test fixture for empty field"}}))
    orig = merge_module._OVERRIDES_PATH
    merge_module._OVERRIDES_PATH = bad
    try:
        with pytest.raises(ValueError, match="empty kitchen_id or field"):
            merge_module._load_overrides()
    finally:
        merge_module._OVERRIDES_PATH = orig


def test_load_overrides_rejects_non_dict_value(merge_module, tmp_path):
    """Per Gemini PR #155 round-1 — every override value MUST be a dict
    (not a bare string). A malformed entry would silently break the
    `override['value']` lookup at merge time."""
    bad = tmp_path / "tie-break-overrides.json"
    bad.write_text(json.dumps({"20.01|name": "Ramesses XI"}))
    orig = merge_module._OVERRIDES_PATH
    merge_module._OVERRIDES_PATH = bad
    try:
        with pytest.raises(ValueError, match="must be a dict"):
            merge_module._load_overrides()
    finally:
        merge_module._OVERRIDES_PATH = orig


def test_override_value_passes_through_deep_normalise(merge_module):
    """Per Gemini PR #155 round-2 — override values are passed through
    `_deep_normalise` for parity with majority-vote values. If a future
    override `value` encodes a sentinel-null string (`-`, `none`, etc.),
    it collapses to None just like an agent emission would.
    """
    key = ("test.99", "prenomen")
    merge_module.TIE_BREAK_OVERRIDES[key] = {
        "value": "-",
        "rationale": "test fixture (sentinel-null override)",
    }
    try:
        values = ["alpha", "beta", "gamma"]
        chosen, _ = merge_module._majority(
            values, kid="test.99", field="prenomen"
        )
        assert chosen is None, f"expected sentinel-null override to collapse to None, got {chosen!r}"
    finally:
        del merge_module.TIE_BREAK_OVERRIDES[key]


def test_load_overrides_rejects_missing_value_key(merge_module, tmp_path):
    """Per Gemini PR #155 round-1 — every override dict MUST carry the
    `value` key. Missing key would KeyError opaquely at merge time."""
    bad = tmp_path / "tie-break-overrides.json"
    bad.write_text(json.dumps({"20.01|name": {"rationale": "missing value key"}}))
    orig = merge_module._OVERRIDES_PATH
    merge_module._OVERRIDES_PATH = bad
    try:
        with pytest.raises(ValueError, match="missing required key"):
            merge_module._load_overrides()
    finally:
        merge_module._OVERRIDES_PATH = orig


def test_load_overrides_rejects_missing_rationale_key(merge_module, tmp_path):
    """Per Gemini PR #155 round-1 — every override dict MUST carry the
    `rationale` key. Citation is load-bearing per constitutional rule 6
    (reconciled values must trace to a documented basis)."""
    bad = tmp_path / "tie-break-overrides.json"
    bad.write_text(json.dumps({"20.01|name": {"value": "Ramesses XI"}}))
    orig = merge_module._OVERRIDES_PATH
    merge_module._OVERRIDES_PATH = bad
    try:
        with pytest.raises(ValueError, match="missing required key"):
            merge_module._load_overrides()
    finally:
        merge_module._OVERRIDES_PATH = orig


# === reconciled.jsonl pins for current overrides =======================

@pytest.fixture(scope="module")
def reconciled():
    path = SOURCE_DIR / "reconciled.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _row(reconciled: list, kid: str) -> dict:
    hits = [r for r in reconciled if r["kitchen_id"] == kid]
    assert len(hits) == 1, f"expected 1 row for {kid}, got {len(hits)}"
    return hits[0]


def test_21H_01_notes_from_kitchen_post_fix_rows_null(reconciled):
    """21H.01 Herihor 1/1/1 tie on `notes_from_kitchen`. Override pins
    agent A's `hp`; fix_rows.py SPOT_CORRECTIONS sets to None per
    egyptologist finding (the `hp` marker is reserved for Pinudjem I,
    NOT Herihor)."""
    r = _row(reconciled, "21H.01")
    assert r["notes_from_kitchen"] is None


def test_dyn21_concurrent_with_kings_recomputed_deterministically(reconciled):
    """All four override-resolved Dyn-21 ties on `concurrent_with_kings`
    are functional no-ops because fix_rows.py `_compute_concurrency`
    deterministically recomputes the list from start_bce/end_bce
    interval overlap. Verify the post-fix-rows lists are non-empty
    where expected."""
    psusennes_i = _row(reconciled, "21.03")
    assert isinstance(psusennes_i["concurrent_with_kings"], list)
    assert len(psusennes_i["concurrent_with_kings"]) >= 1
    djed = _row(reconciled, "21H.06")
    assert isinstance(djed["concurrent_with_kings"], list)
    smendes_ii = _row(reconciled, "21H.08")
    assert isinstance(smendes_ii["concurrent_with_kings"], list)


def test_overrides_json_keys_well_formed(merge_module):
    """Every key parses as `<kid>|<field>` and every rationale carries a
    structured printed-source citation."""
    citation_pattern = re.compile(
        r"Kitchen\s+TIPE"                  # Kitchen TIPE
        r"|TIPE"                            # TIPE
        r"|Table\s+\d"                      # Table N
        r"|p\.\s*\d+"                       # p. <digits>
        r"|page\s+\d+"                      # page <digits>
        r"|PDF\s+pp\s*\d+"                  # PDF pp <digits>
        r"|pp\s*\d+",                       # pp <digits>
        re.IGNORECASE,
    )
    for (kid, field), entry in merge_module.TIE_BREAK_OVERRIDES.items():
        assert kid, f"empty kid in key ({kid!r}, {field!r})"
        assert field, f"empty field in key ({kid!r}, {field!r})"
        assert "rationale" in entry, f"override ({kid!r}, {field!r}) missing rationale"
        rationale = entry["rationale"]
        assert isinstance(rationale, str) and len(rationale) >= 20, (
            f"rationale for ({kid!r}, {field!r}) too short to carry a citation: {rationale!r}"
        )
        assert citation_pattern.search(rationale), (
            f"rationale for ({kid!r}, {field!r}) lacks a structured printed-"
            f"source citation matching `Kitchen TIPE` / `TIPE` / `Table N` / "
            f"`p. <digits>` / `page <digits>` / `PDF pp <digits>` / `pp <digits>`. "
            f"Got: {rationale!r}"
        )
