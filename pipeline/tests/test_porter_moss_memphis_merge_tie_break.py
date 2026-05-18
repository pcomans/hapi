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
    - Chunk 7: `G2100a|notes_from_pm`, `G2156b|notes_from_pm` (Merib's
      G 2100 annexe with raised-ayin normalisation in `Menkaureʿ`, and
      the second G 2156 = Redenes mastaba with cross-reference clause
      preservation).
    - Chunk 8: `G2347a|notes_from_pm`, `G2381|notes_from_pm`,
      `G2381|occupant_name`, `G2387|occupant_name`,
      `G2415|notes_from_pm`, `G2423|notes_from_pm` (six Cemetery en
      Echelon rows: G 2347a bare-suffix Shape-2 null-notes normalisation;
      G 2381 + G 2387 underdot-Ḥ + post-hyphen capitalisation on the
      compound theophoric `Meryptaḥʿankh`; G 2415 lowercase-`and`
      conjunction preservation on Weri/Meti joint-burial headword;
      G 2423 raised-`a` → ayin in `Maʿet` + wife-clause preservation
      for Meḥu/Khenit).
    - Chunk 9: `G3008|notes_from_pm`, `G3008|co_occupant_roles`,
      `G3050|notes_from_pm`, `G3050|co_occupant_roles`,
      `G3093|notes_from_pm`, `G3093|co_occupant_roles`,
      `G3098|notes_from_pm`, `G3098|co_occupant_roles` (Fisher Minor
      Cemetery wife-clause structure: each of four named occupants has
      a wife/co-occupant whose role string and notes triggered 1/1/1
      ties across the agents, mostly on Ḥathor underdot + `etc.`
      trailer + body-mastaba-line inclusion. G 3098 is the chunk-9
      annexe-pair compound carrying both Iymerery and Neferḥetpes-Wer
      in one row).
    - Chunk 12: `SAQ-Shepseskaf|tomb_aliases` (PM's `Mastabet Faraʿun`
      typographic variant normalised to the canonical `Mastabat el-
      Faraʿun` transliteration form used in museum catalogs).
    - Chunk 10: `JKR-Ankh|co_occupant_roles`,
      `JKR-Irty|co_occupant_roles`,
      `JKR-Ithu|co_occupant_roles`, `JKR-Ithu|notes_from_pm`,
      `JKR-Iiu|co_occupant_roles`, `JKR-Iiu|notes_from_pm`,
      `JKR-MeniII|co_occupant_roles`, `JKR-Inpuhotp|notes_from_pm`,
      `JKR-Sinekhen|notes_from_pm`, `JKR-SonbI|notes_from_pm` (Junker
      West named-tomb cluster — wife-clause `mitrt`/`mjtrt` typography
      normalisation, ʾtw-aleph + `@` OCR drift, Saḥurēʿ/Neuserrēʿ/Rēʿ
      macron-Ē + ayin compounding, Sentiotes I bracketed Roman regnal,
      and the three-co-occupant Ithu parent-pair-plus-wife block).
    - Chunk 11 (halves 11a+11b): `D1|notes_from_pm`, `D4|notes_from_pm`,
      `D15|notes_from_pm`, `D32|notes_from_pm`, `D37|occupant_name`,
      `STN-Ibir|notes_from_pm`, `STN-Wemtetka|notes_from_pm`,
      `D117|co_occupants`, `D117|co_occupant_roles`,
      `D203|co_occupant_roles`, `D207|notes_from_pm`,
      `D215|notes_from_pm`, `STN-Iri|co_occupant_roles`,
      `STN-Nu|notes_from_pm` (Steindorff Cemetery D-numbered + STN-
      interstitials — Shape-2 bare-numeric null normalisation,
      ellipsis-truncation ID notes, Shape-4 joint-twin notes,
      Re-deity-compound + ḥ-root `Rēʿḥerka` triple-diacritic,
      three-co-occupant parent-pair-plus-wife block, `mitrt`
      typography, controlled-vocab fallback for unknown joint-twin
      role, and PM cross-reference preservation).
    - Chunk 15 (halves 15a+15b): `G4911|notes_from_pm`,
      `G4940|notes_from_pm`, `G4970|co_occupant_roles`,
      `G5110|notes_from_pm`, `G5150|notes_from_pm`,
      `G5170|co_occupants`, `G5170|co_occupant_roles`,
      `G5170|notes_from_pm`, `G5210|notes_from_pm`,
      `G5221|notes_from_pm`, `G5232|notes_from_pm`,
      `G5350|notes_from_pm`, `G5480|notes_from_pm`,
      `G5482|notes_from_pm`, `G5550|notes_from_pm` (Cemetery en
      Echelon South — wife-clause Ḥathor + Ḥeket underdot,
      Re-deity macron normalisation, bracketed-Roman drop, alt-name
      idiom handling, Shape-2 bare-numeric null normalisation,
      Schiaparelli excavator-history drop).

    - Chunk 17 (halves 17a+17b): `G7152|notes_from_pm`,
      `G7210|co_occupant_roles`, `G7220|notes_from_pm`,
      `G7244|co_occupants`, `G7244|notes_from_pm`,
      `G7248|notes_from_pm`, `G7249|notes_from_pm`,
      `G7350|co_occupant_roles`, `G7350|notes_from_pm`,
      `G7391|notes_from_pm`, `G7410|co_occupant_roles`,
      `G7410|co_occupants`, `G7410|notes_from_pm`,
      `G7420|notes_from_pm`, `G7430|co_occupant_roles`,
      `G7430|notes_from_pm`, `G7510|co_occupant_roles`,
      `G7510|notes_from_pm`, `G7530|notes_from_pm`,
      `G7540|notes_from_pm`, `G7550|co_occupant_roles`,
      `G7550|notes_from_pm`, `G7650|notes_from_pm`,
      `G7660|notes_from_pm`, `G7690|notes_from_pm`,
      `G7760|co_occupant_roles`, `G7760|co_occupants`,
      `G7760|notes_from_pm`, `G7809|notes_from_pm`,
      `G7810|co_occupant_roles`, `G7815|notes_from_pm`,
      `G7820|notes_from_pm`, `G7836|notes_from_pm`,
      `G7948|notes_from_pm` (G 7000 East Field remainder — G 7152
      dating-spillover drop, Ḥarzedef joint-twin parent hedges,
      G 7220/G 7420/G 7540 body-prose-only sub-entry null convention,
      composite-entry chapel sub-feature drops, G 7350 Ḥetepḥeres II
      two-husband roles with `King (later)` parenthetical, G 7391
      `wad` → `waʿb` OCR correction, G 7410+7420 Meresʿankh II
      parent-pair vs twin-occupant co-occupant split, `(possibly)` and
      `(probably)` parenthetical hedge forms on multiple entries,
      G 7510 `No burial place for wife.` structural note retention,
      G 7530+7540 joint-twin headword + null sub-entry, G 7550/G 7660
      Ḥetepḥeres diacritics + Menkaurēʿ Re-compound, G 7650 Mertiotes
      name normalisation + Ḥathor underdot, G 7690 bare artifact entry
      OCR-faithful no-comma form, G 7760 three-co-occupant with
      `Khufuʿankh` ayin no-hyphen, G 7809 `Dyn V` period restore,
      G 7815/G 7836 Rock-cut-tomb retention + Ḥathor underdot,
      G 7820 joint headword `Meresʿankh` ayin + body-trailer drop,
      G 7948 `waab` → `waʿb` + LG code drop + `Ḥathor` underdot).

    - Chunk 19 (east-trailing + Cemetery G I S + Quarry Cemetery):
      `LG10|notes_from_pm`, `LG10|occupant_alt_names`,
      `LG10|occupant_name`, `LG10|occupant_role` — LG 10 SENEZEMIB INTI
      row dropped by Agent B (9 rows); agents A+C (11 rows each) carried
      it, requiring four-field tie-break with Vizier role per the
      `G 2370` cross-reference in PM body prose.

    - Chunk 14 (halves 14a+14b): `G4351|co_occupant_roles`,
      `G4520|occupant_name`, `G4561|co_occupant_roles`,
      `G4561|notes_from_pm`, `G4630|co_occupant_roles`,
      `G4630|notes_from_pm`, `G4651|co_occupant_roles`,
      `G4651|notes_from_pm`, `G4710|co_occupant_roles`,
      `G4710|notes_from_pm`, `G4761|co_occupants`,
      `G4761|co_occupant_roles` (Cemetery G 4000 — Imisetkai
      Ḥathor-titled wife, Khufu-ʿAnkh hyphenated theophoric, four
      Wife-<Hathor/Neith>-clause rows in the second half, G 4761
      Nufer [I] three-co-occupant Probably-parent-pair-plus-wife).

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
        ("G2100a", "notes_from_pm"),
        ("G2156b", "notes_from_pm"),
        ("G2347a", "notes_from_pm"),
        ("G2381", "notes_from_pm"),
        ("G2381", "occupant_name"),
        ("G2387", "occupant_name"),
        ("G2415", "notes_from_pm"),
        ("G2423", "notes_from_pm"),
        ("G3008", "notes_from_pm"),
        ("G3008", "co_occupant_roles"),
        ("G3050", "notes_from_pm"),
        ("G3050", "co_occupant_roles"),
        ("G3093", "notes_from_pm"),
        ("G3093", "co_occupant_roles"),
        ("G3098", "notes_from_pm"),
        ("G3098", "co_occupant_roles"),
        ("SAQ-Shepseskaf", "tomb_aliases"),
        ("JKR-Ankh", "co_occupant_roles"),
        ("JKR-Irty", "co_occupant_roles"),
        ("JKR-Ithu", "co_occupant_roles"),
        ("JKR-Ithu", "notes_from_pm"),
        ("JKR-Iiu", "co_occupant_roles"),
        ("JKR-Iiu", "notes_from_pm"),
        ("JKR-MeniII", "co_occupant_roles"),
        ("JKR-Inpuhotp", "notes_from_pm"),
        ("JKR-Sinekhen", "notes_from_pm"),
        ("JKR-SonbI", "notes_from_pm"),
        # Chunk 11 (halves 11a + 11b): Steindorff Cemetery D-numbered + STN-
        # interstitial tombs. 14 ties resolved across the two halves. Shape-2
        # bare-numeric D.I + ellipsis truncation D.15/STN-Ibir, Shape-4 joint
        # twins D.4/D.32/D.203 dropping primary occupant name from notes,
        # Re-deity-compound + ḥ-root name D.37 (`Rēʿḥerka` with macron-Ē +
        # ayin + underdot-Ḥ), D.117 three-co-occupant parent-pair-plus-wife
        # block with gendered Father/Mother roles, D.215 wife clause `mitrt`
        # typography normalisation, STN-Iri unknown-role joint twin
        # (controlled-vocab fallback), STN-Nu cross-reference preservation.
        ("D1", "notes_from_pm"),
        ("D4", "notes_from_pm"),
        ("D15", "notes_from_pm"),
        ("D32", "notes_from_pm"),
        ("D37", "occupant_name"),
        ("STN-Ibir", "notes_from_pm"),
        ("STN-Wemtetka", "notes_from_pm"),
        ("D117", "co_occupants"),
        ("D117", "co_occupant_roles"),
        ("D203", "co_occupant_roles"),
        ("D207", "notes_from_pm"),
        ("D215", "notes_from_pm"),
        ("STN-Iri", "co_occupant_roles"),
        ("STN-Nu", "notes_from_pm"),
        # Chunk 14 (halves 14a + 14b): Cemetery G 4000 (Hemiunu cluster
        # — Reisner Excavation). 12 ties resolved: G4351 + G4520 in 14a
        # (Imisetkai wife title cluster preservation, Khufu-ʿAnkh
        # hyphenation convention), G4561 / G4630 / G4651 / G4710 wife-
        # clause roles + notes pattern (Wife, <title> form + Ḥathor
        # underdot + waʿb normalisation + drop mastaba trailer), G4761
        # Nufer [I] three-co-occupant block (Probably-parent-pair + wife
        # parallel to chunk-11 D117).
        ("G4351", "co_occupant_roles"),
        ("G4520", "occupant_name"),
        ("G4561", "co_occupant_roles"),
        ("G4561", "notes_from_pm"),
        ("G4630", "co_occupant_roles"),
        ("G4630", "notes_from_pm"),
        ("G4651", "co_occupant_roles"),
        ("G4651", "notes_from_pm"),
        ("G4710", "co_occupant_roles"),
        ("G4710", "notes_from_pm"),
        ("G4761", "co_occupants"),
        ("G4761", "co_occupant_roles"),
        # Chunk 15 (halves 15a + 15b): Cemetery en Echelon South Part
        # (Reisner + Junker Excavations). 16 ties resolved across
        # the two halves: wife-clause Ḥathor + Ḥeket underdot
        # (G4940/G4970/G5170), Re-deity-compound macron (Saḥurēʿ /
        # Neferirkarēʿ / Menkaureʿ / Meresʿankh / Kawaʿab /
        # Ḥetepḥeres II), bracketed-Roman drop (G5110 / G5170 / G5210
        # per chunks-7 convention), `called <ALT>` alt-name drop from
        # notes (G5150 chunk-14 G4651 precedent), three-co-occupant
        # parent-pair-plus-wife block (G5170 parallel to chunk-11
        # D117), bare-numeric pseudo-headword null normalisation
        # (G5221/G5232/G5350 per chunk-11 D1 convention) + body-
        # attested Shape-2 keep (G5482), and Schiaparelli excavator-
        # history drop (G4911/G5550).
        ("G4911", "notes_from_pm"),
        ("G4940", "notes_from_pm"),
        ("G4970", "co_occupant_roles"),
        ("G5110", "notes_from_pm"),
        ("G5150", "notes_from_pm"),
        ("G5170", "co_occupants"),
        ("G5170", "co_occupant_roles"),
        ("G5170", "notes_from_pm"),
        ("G5210", "notes_from_pm"),
        ("G5221", "notes_from_pm"),
        ("G5232", "notes_from_pm"),
        ("G5350", "notes_from_pm"),
        ("G5480", "notes_from_pm"),
        ("G5482", "notes_from_pm"),
        ("G5550", "notes_from_pm"),
        # Chunk 17 (halves 17a + 17b): G 7000 East Field remainder.
        # 34 ties resolved: G7152 dating-spillover drop (dynasty null),
        # Ḥarzedef joint-twin parent hedges, G7220/G7420/G7540 body-prose
        # sub-entry null convention, composite-entry chapel sub-feature
        # drops, G7350 two-husband `King (later)` role, G7391 wad→waʿb,
        # G7410 parent-pair co-occupant split, `(possibly)`/`(probably)`
        # hedge parentheticals, G7510 structural note retention,
        # G7530+7540 joint-twin, diacritics (Ḥetepḥeres/Menkaurēʿ/Ḥathor),
        # G7760 three-co-occupant + Khufuʿankh ayin, G7809 period restore,
        # Rock-cut-tomb retention, G7948 waab→waʿb + LG drop.
        ("G7152", "notes_from_pm"),
        ("G7210", "co_occupant_roles"),
        ("G7220", "notes_from_pm"),
        ("G7244", "co_occupants"),
        ("G7244", "notes_from_pm"),
        ("G7248", "notes_from_pm"),
        ("G7249", "notes_from_pm"),
        ("G7350", "co_occupant_roles"),
        ("G7350", "notes_from_pm"),
        ("G7391", "notes_from_pm"),
        ("G7410", "co_occupant_roles"),
        ("G7410", "co_occupants"),
        ("G7410", "notes_from_pm"),
        ("G7420", "notes_from_pm"),
        ("G7430", "co_occupant_roles"),
        ("G7430", "notes_from_pm"),
        ("G7510", "co_occupant_roles"),
        ("G7510", "notes_from_pm"),
        ("G7530", "notes_from_pm"),
        ("G7540", "notes_from_pm"),
        ("G7550", "co_occupant_roles"),
        ("G7550", "notes_from_pm"),
        ("G7650", "notes_from_pm"),
        ("G7660", "notes_from_pm"),
        ("G7690", "notes_from_pm"),
        ("G7760", "co_occupant_roles"),
        ("G7760", "co_occupants"),
        ("G7760", "notes_from_pm"),
        ("G7809", "notes_from_pm"),
        ("G7810", "co_occupant_roles"),
        ("G7815", "notes_from_pm"),
        ("G7820", "notes_from_pm"),
        ("G7836", "notes_from_pm"),
        ("G7948", "notes_from_pm"),
        # Chunk 19 (east-trailing + Cemetery G I S + Quarry Cemetery):
        # LG 10 SENEZEMIB INTI four-field tie-break — Agent B (9 rows) missed
        # the LG 10 SENEZEMIB row that agents A+C (11 rows each) caught.
        # Required overrides on `notes_from_pm`, `occupant_alt_names` ["Inti"],
        # `occupant_name` "Senezemib", and `occupant_role` "Vizier" (same
        # person as G 2370 cross-reference per PM body prose).
        ("LG10", "notes_from_pm"),
        ("LG10", "occupant_alt_names"),
        ("LG10", "occupant_name"),
        ("LG10", "occupant_role"),
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
