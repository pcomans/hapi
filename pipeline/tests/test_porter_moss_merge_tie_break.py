"""Unit tests for Porter-Moss merge.py's tie-break enforcement.

Mirrors the canonical pattern in PR #128 (Leprohon) / PR #146 (Beckerath).
Issue #145.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

SOURCE_DIR = (
    Path(__file__).parent.parent
    / "pipeline" / "authority" / "sources" / "porter-moss-theban-necropolis"
)
MERGE_PY = SOURCE_DIR / "merge.py"


@pytest.fixture(scope="module")
def merge_module():
    spec = importlib.util.spec_from_file_location("pm_merge", MERGE_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# === _majority — unanimous and clear majority ============================

def test_majority_unanimous_returns_value(merge_module):
    values = ["Ramesses VII", "Ramesses VII", "Ramesses VII"]
    chosen, count = merge_module._majority(values, tid="KV1", field="occupant_name")
    assert chosen == "Ramesses VII"
    assert count == 3


def test_majority_clear_majority_returns_majority_value(merge_module):
    values = ["Hatshepsut", "Hatshepsut", "Hatshepsout"]
    chosen, count = merge_module._majority(values, tid="KV20", field="occupant_name")
    assert chosen == "Hatshepsut"
    assert count == 2


def test_majority_two_agents_one_dropped_majority_resolves(merge_module):
    values = ["KV1", "KV1"]
    chosen, count = merge_module._majority(values, tid="KV1", field="tomb_id")
    assert chosen == "KV1"
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
        "value": "Loret",
        "rationale": "test fixture",
    }
    try:
        values = ["Loret", None]
        chosen, _ = merge_module._majority(
            values, tid="test.99", field="discoverer"
        )
        assert chosen == "Loret"
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
    values = ["Loret", None]
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


def test_sentinel_null_strings_includes_null_for_leprohon_parity(merge_module):
    """Per PR #146 P1.3 — `null` is a recognised sentinel-null on
    Leprohon's side; PM merges across the same canonical surface so it
    must collapse `"null"` strings too."""
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
    bad.write_text(json.dumps({"KV1|": {"value": "x", "rationale": "test fixture for empty field"}}))
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
    bad.write_text(json.dumps({"KV1|occupant_name": "Ramesses VII"}))
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
    bad.write_text(json.dumps({"KV1|occupant_name": {"rationale": "missing value key"}}))
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
    bad.write_text(json.dumps({"KV1|occupant_name": {"value": "Ramesses VII"}}))
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


def _row(reconciled: list, tid: str) -> dict:
    hits = [r for r in reconciled if r["tomb_id"] == tid]
    assert len(hits) == 1, f"expected 1 row for {tid}, got {len(hits)}"
    return hits[0]


def test_dan_aqhor_occupant_name_pinned(reconciled):
    """DAN-Aqhor 1/1/1 tie on `occupant_name`. Override pins agent A's
    `ʿAq-hor` (pre-fix-rows merge value); fix_rows.py DAN-Aqhor entry
    then layers the underdot ḳ correction matching PM headword `ʿAḲ-ḤOR`."""
    r = _row(reconciled, "DAN-Aqhor")
    # Post-fix-rows state — fix_rows applies the underdot.
    assert r["occupant_name"] == "ʿAḳ-hor"


def test_dan_antef_sekhemre_occupant_name_pinned(reconciled):
    """DAN-AntefSekhemreHeruhirmaet 1/1/1 tie on `occupant_name`. Override
    pins agent A's value `Antef (Sekhemreʿ-Heruhirmaʿet)` (preserving the
    parenthetical disambiguator one agent had dropped); fix_rows.py then
    strips the parenthetical to bare `Antef` per the DAN-Antef* canonical
    bare-lemma convention (parenthetical is preserved in occupant_alt_names).
    Test pins the post-fix-rows state."""
    r = _row(reconciled, "DAN-AntefSekhemreHeruhirmaet")
    assert r["occupant_name"] == "Antef"


def test_post_fix_rows_pipeline_determinism(merge_module, reconciled):
    """Issue #152 (egyptologist PR #151 review methodology recommendation):
    every tie-break override row × field gets a curated post-fix_rows.py
    final-form pin. Catches drift in EITHER file (overrides or fix_rows.py)
    silently changing the result.

    The dependency between `tie-break-overrides.json` and `fix_rows.py` is
    a multi-file convention — the override pins a pre-fix-rows merge value;
    fix_rows.py may then layer underdot diacritics, restore Bibl. ribbons,
    or strip parenthetical disambiguators. This test pins the FINAL state
    of every override-touched row × field per the printed Beckerath /
    PM extraction prompt + scholarly conventions.

    Maintenance: when adding a new tie-break override OR a new fix_rows
    correction touching an override-pinned row × field, update the
    `EXPECTED` dict here to match the new final form. The test FAILS LOUDLY
    rather than silently regressing.

    Constitutional rule 3 (deterministic enforcement over convention) —
    converts the documented override→fix_rows convention into a CI gate.
    """
    EXPECTED: dict[tuple[str, str], object] = {
        # 9 overrides where fix_rows.py mutates post-merge:
        ("KV36", "notes_from_pm"):
            "Standard-bearer, Child of the nursery. Temp. Ḥatshepsut. Excavated by Loret.",
        ("KV42", "notes_from_pm"):
            "(?). Excavated by Loret",
        ("QV47", "notes_from_pm"):
            "daughter of Seḳenenreʿ-Taʿa and Sit-ḏḥout. Dyn. XVII. (Bibl. i, 1st ed. p. 49.)",
        ("SWV-HatshepsutSouth", "notes_from_pm"):
            "See also Tomb 20, supra, p. 546. Sarcophagus as Queen-Consort, quartzite, in Cairo Mus. Ent. 47032.",
        ("DAN-AhmosiHenutempet", "notes_from_pm"):
            "Daughter of ʿAḥḥotp (wife of King Seḳenenreʿ-Taʿa).",
        ("DAN-AhmosiNefertere", "notes_from_pm"):
            "Tomb of Queen ʿAḥmosi Nefertere (probably). Attributed to Amenophis I by "
            "Carter, later equated by Černý with 'House of Amenophis of the Garden'.",
        ("DAN-AntefSekhemreHeruhirmaet", "occupant_name"):
            "Antef",
        ("DAN-Aqhor", "occupant_name"):
            "ʿAḳ-hor",
        ("DAN-MentuhotpIWifeOfDjhuti", "notes_from_pm"):
            "Wife of King Ḏḥuti. Found in tomb by Passalacqua.",
        # 2 overrides where reconciled.jsonl == override value verbatim
        # (fix_rows.py does NOT mutate):
        ("KV39", "notes_from_pm"):
            "Uninscribed tomb, attributed to Amenophis I by Weigall in Ann. Serv. xi "
            "(1911), pp. 174-5 [12], and id. A Guide to the Antiquities of Upper "
            "Egypt, pp. 163-4, but this is not supported by any inscriptional "
            "evidence, and does not correspond with the position given in the Abbott "
            "Papyrus (cf. Peet, The Great Tomb-Robberies of the Twentieth Egyptian "
            "Dynasty, pp. 37-8). See also the tomb of Queen ʿAhmosi Nefertere, "
            "infra, p. 599.",
        ("QV74", "notes_from_pm"):
            "Great King's mother and King's wife. "
            "(CHAMPOLLION, No. 15, L. D. Text, No. 2, HAY, No. 7.)",
    }
    # Sanity: EXPECTED covers every override.
    override_keys = set(merge_module.TIE_BREAK_OVERRIDES.keys())
    expected_keys = set(EXPECTED.keys())
    missing = override_keys - expected_keys
    stale = expected_keys - override_keys
    assert not missing, (
        f"EXPECTED is missing post-fix-rows pins for these tie-break "
        f"overrides: {sorted(missing)}. When adding a new override entry, "
        f"add a matching final-state pin here."
    )
    assert not stale, (
        f"EXPECTED has stale pins for tie-break overrides that no longer "
        f"exist: {sorted(stale)}. When removing an override entry, drop "
        f"the matching pin here."
    )
    # Per-row final-state assertion.
    for (tid, field), expected_value in EXPECTED.items():
        row = _row(reconciled, tid)
        actual = row.get(field)
        assert actual == expected_value, (
            f"Override-touched row × field ({tid!r}, {field!r}) has post-"
            f"fix_rows.py value {actual!r} but EXPECTED {expected_value!r}. "
            f"Either tie-break-overrides.json or fix_rows.py changed the "
            f"resolution path; update EXPECTED to match the new final form "
            f"(after verifying against the printed PM source)."
        )


def test_overrides_json_keys_well_formed(merge_module):
    """Every key parses as `<tid>|<field>` and every rationale carries a
    structured printed-source citation. Same regex pattern as Beckerath
    PR #146 (PM I.2 page references match the Beckerath book p<digits>
    convention; PM also uses scan-style references in fix_rows.py
    rationale prose)."""

    citation_pattern = re.compile(
        r"PM\s+I\.\d"                    # PM I.2 / PM I.1
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
            f"source citation matching `PM I.<digit>` / `p. <digits>` / "
            f"`page <digits>` / `book p<digits>` / `scan-NNN`. "
            f"Got: {rationale!r}"
        )
