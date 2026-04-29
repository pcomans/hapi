"""Unit tests for Ryholt-1997-SIP merge.py's tie-break enforcement.

Mirrors the canonical pattern in PR #128 (Leprohon) / PR #146 (Beckerath) /
PR #151 (Porter-Moss) / PR #155 (Kitchen). Issue #133.

NB: Ryholt's `raw/agent-{a,b,c}.jsonl` are gitignored AND not on local disk
in this session — the existing reconciled.jsonl was committed from a
prior pipeline run. So these tests verify the NEW enforcer machinery
without re-running merge against agent files. A future Dagster re-run
(once agent JSONLs are regenerated) will surface any current ties via
the enforcer; the override file ships empty and populates on demand.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

SOURCE_DIR = (
    Path(__file__).parent.parent
    / "pipeline" / "authority" / "sources" / "ryholt-1997-sip"
)
MERGE_PY = SOURCE_DIR / "merge.py"


@pytest.fixture(scope="module")
def merge_module():
    spec = importlib.util.spec_from_file_location("ryholt_merge", MERGE_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# === _majority — unanimous and clear majority ============================

def test_majority_unanimous_returns_value(merge_module):
    values = ["Sobekhotep", "Sobekhotep", "Sobekhotep"]
    chosen, count = merge_module._majority(values, rid="13.16", field="nomen")
    assert chosen == "Sobekhotep"
    assert count == 3


def test_majority_clear_majority_returns_majority_value(merge_module):
    values = [-1700, -1700, -1701]
    chosen, count = merge_module._majority(values, rid="13.16", field="date_bce_start")
    assert chosen == -1700
    assert count == 2


# === _majority — tie with override =====================================

def test_majority_tie_with_override_uses_override(merge_module):
    key = ("test.99", "nomen")
    merge_module.TIE_BREAK_OVERRIDES[key] = {
        "value": "RESOLVED",
        "rationale": "test fixture",
    }
    try:
        values = ["alpha", "beta", "gamma"]
        chosen, _ = merge_module._majority(values, rid="test.99", field="nomen")
        assert chosen == "RESOLVED"
    finally:
        del merge_module.TIE_BREAK_OVERRIDES[key]


def test_majority_one_one_partial_row_tie_with_override(merge_module):
    key = ("test.99", "prenomen")
    merge_module.TIE_BREAK_OVERRIDES[key] = {
        "value": "Sekhemre",
        "rationale": "test fixture",
    }
    try:
        values = ["Sekhemre", None]
        chosen, _ = merge_module._majority(values, rid="test.99", field="prenomen")
        assert chosen == "Sekhemre"
    finally:
        del merge_module.TIE_BREAK_OVERRIDES[key]


def test_override_value_passes_through_deep_normalise(merge_module):
    """Per Gemini PR #155 round-2 — override values pass through
    `_deep_normalise` for parity with majority-vote values."""
    key = ("test.99", "prenomen")
    merge_module.TIE_BREAK_OVERRIDES[key] = {
        "value": "-",
        "rationale": "test fixture (sentinel-null override)",
    }
    try:
        values = ["alpha", "beta", "gamma"]
        chosen, _ = merge_module._majority(values, rid="test.99", field="prenomen")
        assert chosen is None
    finally:
        del merge_module.TIE_BREAK_OVERRIDES[key]


# === _majority — tie raises ============================================

def test_majority_tie_uncovered_identifier_raises(merge_module):
    values = ["alpha", "beta", "gamma"]
    with pytest.raises(ValueError) as exc:
        merge_module._majority(values, rid="uncov.99", field="nomen")
    msg = str(exc.value)
    assert "Unresolved IDENTIFIER tie" in msg
    assert "uncov.99" in msg
    assert "nomen" in msg
    assert "tie-break-overrides.json" in msg


def test_majority_one_one_partial_row_tie_uncovered_raises(merge_module):
    values = ["Sekhemre", None]
    with pytest.raises(ValueError) as exc:
        merge_module._majority(values, rid="uncov.99", field="prenomen")
    assert "Unresolved IDENTIFIER tie" in str(exc.value)


# === sentinel-null + null parity =======================================

def test_majority_sentinel_null_collapses_to_none(merge_module):
    values = ["-", None, None]
    chosen, count = merge_module._majority(values, rid="X.99", field="prenomen")
    assert chosen is None
    assert count == 3


def test_sentinel_null_strings_includes_null_for_leprohon_parity(merge_module):
    """Per PR #146 P1.3 + parity with sibling sources."""
    assert "null" in merge_module.SENTINEL_NULL_STRINGS


# === _majority — keyword-only rid/field ================================

def test_majority_requires_rid_and_field(merge_module):
    """Constitutional rule 10: no silent first-seen fallback."""
    with pytest.raises(TypeError):
        merge_module._majority(["a", "b", "c"])
    with pytest.raises(TypeError):
        merge_module._majority(["a", "b", "c"], rid="x.01")
    with pytest.raises(TypeError):
        merge_module._majority(["a", "b", "c"], field="nomen")


# === overrides file — schema validation ================================

def test_load_overrides_rejects_keys_without_separator(merge_module, tmp_path):
    bad = tmp_path / "tie-break-overrides.json"
    bad.write_text(json.dumps({"badkey": {"value": 1, "rationale": "test"}}))
    orig = merge_module._OVERRIDES_PATH
    merge_module._OVERRIDES_PATH = bad
    try:
        with pytest.raises(ValueError, match="missing '|' separator"):
            merge_module._load_overrides()
    finally:
        merge_module._OVERRIDES_PATH = orig


def test_load_overrides_rejects_empty_rid(merge_module, tmp_path):
    bad = tmp_path / "tie-break-overrides.json"
    bad.write_text(json.dumps({"|nomen": {"value": "x", "rationale": "test fixture for empty rid"}}))
    orig = merge_module._OVERRIDES_PATH
    merge_module._OVERRIDES_PATH = bad
    try:
        with pytest.raises(ValueError, match="empty ryholt_id or field"):
            merge_module._load_overrides()
    finally:
        merge_module._OVERRIDES_PATH = orig


def test_load_overrides_rejects_empty_field(merge_module, tmp_path):
    bad = tmp_path / "tie-break-overrides.json"
    bad.write_text(json.dumps({"13.16|": {"value": "x", "rationale": "test fixture for empty field"}}))
    orig = merge_module._OVERRIDES_PATH
    merge_module._OVERRIDES_PATH = bad
    try:
        with pytest.raises(ValueError, match="empty ryholt_id or field"):
            merge_module._load_overrides()
    finally:
        merge_module._OVERRIDES_PATH = orig


def test_load_overrides_rejects_non_dict_value(merge_module, tmp_path):
    bad = tmp_path / "tie-break-overrides.json"
    bad.write_text(json.dumps({"13.16|nomen": "Sobekhotep"}))
    orig = merge_module._OVERRIDES_PATH
    merge_module._OVERRIDES_PATH = bad
    try:
        with pytest.raises(ValueError, match="must be a dict"):
            merge_module._load_overrides()
    finally:
        merge_module._OVERRIDES_PATH = orig


def test_load_overrides_rejects_missing_value_or_rationale(merge_module, tmp_path):
    for incomplete in [{"rationale": "no value"}, {"value": "no rationale"}]:
        bad = tmp_path / "tie-break-overrides.json"
        bad.write_text(json.dumps({"13.16|nomen": incomplete}))
        orig = merge_module._OVERRIDES_PATH
        merge_module._OVERRIDES_PATH = bad
        try:
            with pytest.raises(ValueError, match="missing required key"):
                merge_module._load_overrides()
        finally:
            merge_module._OVERRIDES_PATH = orig


def test_load_overrides_rejects_non_dict_root(merge_module, tmp_path):
    """Per Gemini PR #157 round-1 — top-level JSON must be a dict.
    A list / null / string at the root previously raised AttributeError
    at `.items()`; now raises ValueError with the file path."""
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


def test_overrides_file_starts_empty(merge_module):
    """Ryholt ships with NO overrides because raw/agent-*.jsonl files
    aren't on this disk — re-running merge would raise on uncovered ties.
    Locked here so a future override drift adds an entry without
    documenting the resolution path."""
    assert len(merge_module.TIE_BREAK_OVERRIDES) == 0
