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
        ("TT4", "notes_from_pm"):
            # Tie-break pinned a pre-fix-rows form; CHUNK9_CORRECTIONS then
            # restored Amūn macrons + Thonūfer macron + dropped the medial
            # underdot in `Ḥenutmehyt` (egyptologist printed-source review).
            "Chiseller of Amūn in the Place of Truth. Temp. Ramesses II. "
            "(L. D. Text, No. 106.) Parents, Thonūfer, Chiseller of Amūn in "
            "the Khenu, and Maʿetnefert. Wives, Nefertere and Ḥenutmehyt.",
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
        # Chunk 10 (PR — TT11–TT20) — 2 PDF-cited tie-break overrides on
        # cosmetic/typographic 1/1/1 ties (capitalisation + ayin presence).
        # Neither row has a CHUNK10_CORRECTIONS entry on notes_from_pm so
        # the override value is the final reconciled.jsonl value.
        ("TT12", "notes_from_pm"):
            "Overseer of the granary of the King's wife and King's mother "
            "ʿAḥḥotp. Temp. Amosis to Amenophis I (?). (CHAMPOLLION, No. 51, "
            "L. D. Text, No. 2.) Mother, ʿAḥmosi.",
        ("TT14", "notes_from_pm"):
            "wʿab-priest of 'Amenophis, the favourite of Amūn'. Ramesside.",
        # Chunk 11 (TT21–TT30) — 2 PDF-cited tie-break overrides on
        # cosmetic/typographic 1/1/1 ties (macron-drop / ayin-drop /
        # double-period). TT26's note also lands a CHUNK11_CORRECTIONS
        # entry restoring the wife `Meryēsi` macron-ē; the post-fix-rows
        # pin reflects that restored form. TT29's note is the override
        # value verbatim (no CHUNK11_CORRECTIONS on TT29 notes; the
        # CHUNK11_CORRECTIONS entry for TT29 targets occupant_name).
        ("TT26", "notes_from_pm"):
            "Overseer of the treasury in the Ramesseum in the estate of "
            "Amūn. Temp. Ramesses II. (L. D. Text, No. 29.) Wife, Meryēsi.",
        ("TT29", "notes_from_pm"):
            "Governor of the town, Vizier. Temp. Amenophis II. (HAY, "
            "No. 15.) Parents, [ʿAḥmosi] Ḥumay (tomb 224) and Nub. Wife, "
            "Wertmaʿetef.",
        # Chunk 12 (TT31–TT40) — 8 tie-break overrides all on cosmetic/
        # typographic 1/1/1 ties (citation-clause placement + double-period)
        # following the TT26 precedent. The TT32 occupant_name override pins
        # `Thutmosi` (agent A's PDF-closest stripped-diacritic form);
        # CHUNK12_CORRECTIONS layers the post-merge `Ḏhutmosi` (d-bar Ḏ)
        # restoration per the PR #151 precedent (egyptologist verified
        # the d-emphatic in `Ḏḥwty`/Thoth and its derived names is `Ḏ`
        # not `Ḍ` after direct PM PDF read of p.604 and p.755). All other
        # chunk-12 entries pass through fix_rows.py unchanged
        # (CHUNK12_CORRECTIONS otherwise covers only the macron-
        # restoration corrections on TT33/TT34/TT39 `occupant_name` and
        # the TT33 `source_citation.page` 49→50 fix).
        ("TT31", "notes_from_pm"):
            "First prophet of Menkheperreʿ (Tuthmosis III). Temp. Ramesses II. "
            "(L. D. Text, No. 51.) Parents, Neferḥotep, First prophet of "
            "Amenophis II, and Tausert, Songstress of Monthu. Wives, Ruia and "
            "Mutia or May.",
        ("TT32", "occupant_name"):
            "Ḏhutmosi",
        ("TT33", "notes_from_pm"):
            "Prophet, Chief lector. Saite. (L. D. Text, No. 20.) "
            "Mother, Namenkhesi, Sistrum-player of Amūn. Wife, Tedi.",
        ("TT35", "notes_from_pm"):
            "First prophet of Amūn. Temp. Ramesses II. "
            "(CHAMPOLLION, No. 45, L. D. Text, Nos. 10, 11.) "
            "Parents, Roma, First and second prophet of Amūn, and Roma, "
            "Singer of Amūn. Wife, Mertesger, Chief of the harim of Amūn.",
        ("TT36", "notes_from_pm"):
            "Chief steward of the divine adoratress. Temp. Psammetikhos I. "
            "(CHAMPOLLION, No. 56, L. D. Text, No. 25.) "
            "Parents, ʿAnkh-ḥor, Divine father, and De-ubasteiri, variant Teiri. "
            "Wife, Shepenernute (name in tomb 196).",
        ("TT37", "notes_from_pm"):
            "Chief steward of the god's wife Amenardais I. Saite. "
            "(CHAMPOLLION, No. 54, L. D. Text, No. 23.) "
            "Parents, Pedemut, Scribe, and Estawert "
            "(names from statues, in Berlin Mus. 8163, see infra, p. 69, "
            "and Cairo Mus. Ent. 36711).",
        ("TT39", "notes_from_pm"):
            "Second prophet of Amūn. Temp. Tuthmosis III. "
            "(L. D. Text, No. 18.) Parents, Puia and Neferi. "
            "Wives, Tanefert and Sensonb.",
        ("TT40", "notes_from_pm"):
            "Viceroy of Kush, Governor of the South Lands. "
            "Temp. Amenophis IV to Tutʿankhamūn. "
            "(CHAMPOLLION, A, L. D. Text, No. 110.) Mother, Wenḥo.",
        # Chunk 14 (TT51–TT60) — 5 tie-break overrides on cosmetic
        # `notes_from_pm` punctuation/diacritic 1/1/1 ties. Pinned values
        # are the post-fix_rows state — TT58 reflects the CHUNK14_CORRECTIONS
        # `Amenemonet` → `Amenemōnet` macron restoration applied after merge.
        ("TT53", "notes_from_pm"):
            "Agent of Amūn. Temp. Tuthmosis III. "
            "(CHAMPOLLION, No. 16 bis, L. D. Text, No. 78.) "
            "Parents, Yotefnūfer, Agent of Amūn, and Tetiemnūter. "
            "Wife, Sebknakht.",
        ("TT54", "notes_from_pm"):
            "Sculptor of Amūn, temp. Tuthmosis IV to Amenophis III(?). "
            "Usurped by Kenro, wab-priest, Head of the magazine of Khons, "
            "early Dyn. XIX. Wife (of Ḥuy), Taenheruensi, "
            "(of Kenro), Tarenenu, Chief of the harim of Amūn.",
        ("TT57", "notes_from_pm"):
            "Royal scribe, Overseer of the granaries of Upper and Lower Egypt. "
            "Temp. Amenophis III. (L. D. Text, No. 80.) Wife, Tiyi.",
        ("TT58", "notes_from_pm"):
            "Name unknown, temp. Amenophis III. Usurped by Amenḥotp, "
            "Overseer of the prophets of Amūn, and his son Amenemōnet, "
            "Temple-scribe of the Temple of Ramesses 'Beloved like Amūn', "
            "Dyn. XX. (L. D. Text, No. 43.) "
            "Wife (of Amenemōnet), Ḥenutʿanensu.",
        ("TT60", "notes_from_pm"):
            "Governor of the town and Vizier, and mother, Sent, "
            "Prophetess of Ḥatḥor. Temp. Sesostris I. "
            "(L. D. Text, No. 42.) Wife (of Antefoḳer), Sitsisobk. "
            "Mother (of Sent), Dui.",
        # Chunk 15 (TT61–TT70) — 2 tie-break overrides:
        # TT65 notes_from_pm: override pinned agent A's mid-sentence citation
        # form (per chunk-12 citation-clause precedent); CHUNK15_CORRECTIONS
        # layers two post-merge fixes: (a) `accounts(?)` → `accounts (?)`
        # spacing and (b) `'Alchesi'` → `'Aichesi'` (PDF-verified OCR
        # misread; PM prints `Ai` not `Al`).
        # TT68 notes_from_pm: override pinned agent A's `wʿab-priest` ayin
        # position (per TT14 precedent); no fix_rows correction — final form
        # matches the override verbatim.
        ("TT65", "notes_from_pm"):
            "Scribe of the royal accounts (?) in the Presence, Overseer of the "
            "granary, temp. Ḥatshepsut (?). Usurped by Imiseba, Head of the "
            "altar, Head of the temple-scribes of the estate of Amūn, temp. "
            "Ramesses IX. (CHAMPOLLION, No. 60, L. D. Text, No. 40, WILKINSON, "
            "No. 1, 'Aichesi' of Prisse.) Parents, Amenḥotp, Head of scribes "
            "of the Temple of Amen-reʿ in Karnak, and Mutemmeres. "
            "Wife, Te(n)tpapersetha.",
        ("TT68", "notes_from_pm"):
            "wʿab-priest of Amūn of Karnak, and of Mut of Asher, Dyn. XX. "
            "Usurped by Espaneferḥor, Head of the temple-scribes of the estate "
            "of Amūn, temp. Siamūn. Father (of Espaneferḥor), Iufenamūn. "
            "Wife (of Espaneferḥor), Tabekenmut, Singer of the ... of Mut.",
        # Chunk 16 (TT71–TT80) — 4 tie-break overrides, all on notes_from_pm.
        # All pinned to agent A at merge time: no headword-prefix,
        # mid-sentence citation (per chunk-12 citation-clause precedent).
        # CHUNK16_CORRECTIONS layers post-merge fixes on TT77/TT78/TT79
        # (egyptologist PDF-verified): TT77 ayin restoration on
        # `Raʿḥuy` (was `Raḥuy`); TT78 macron-Ē restoration on
        # `Ēsi` (was `Esi`); TT79 ayin restoration on `wʿab-priest`
        # (was `wab-priest`, per TT14/TT68 precedent). TT80
        # passes through fix_rows unchanged on this field.
        ("TT77", "notes_from_pm"):
            "Child of the nursery, Overseer of works in the Temple of Amūn, "
            "Standard-bearer of the Lord of the Two Lands. Usurped by Roy, "
            "Overseer of sculptors of the Lord of the Two Lands. Temp. "
            "Tuthmosis IV. (CHAMPOLLION, No. 8 bis, L. D. Text, No. 62.) "
            "Wife (of Ptaḥemḥet), Meryt. Wife (of Roy), Raʿḥuy.",
        ("TT78", "notes_from_pm"):
            "Royal scribe, Scribe of recruits. Temp. Tuthmosis III to "
            "Amenophis III. (CHAMPOLLION, No. 4, L. D. Text, No. 57, "
            "WILKINSON, No. 16, HAY, No. 23.) Mother, Ēsi. Wife, Ithuy.",
        ("TT79", "notes_from_pm"):
            "Overseer of the granary of the Lord of the Two Lands, wʿab-priest "
            "in the Mortuary Temple of Tuthmosis III. Temp. Tuthmosis III to "
            "Amenophis II (?). (CHAMPOLLION, No. 7, L. D. Text, No. 60.) "
            "Father, Minnakht (tomb 87).",
        ("TT80", "notes_from_pm"):
            "Overseer of the treasury, Royal scribe. Temp. Amenophis II. "
            "(CHAMPOLLION, No. 6, L. D. Text, No. 59, HAY, No. 21.) "
            "Wife, Takhaʿt.",
        # Chunk 17 (TT81–TT90) — 8 tie-break overrides, all on notes_from_pm.
        # All pinned to agent A at merge time: clean punctuation (no
        # double-period after close-paren), no headword-prefix duplication.
        # CHUNK17_CORRECTIONS layers post-merge fixes on TT81 (PM-faithful
        # bracket-prefix `[1st ed. Anena], ` + Queen-Ahhotep doubled-ḥ
        # `ʿAḥotp` → `ʿAḥḥotp`) and TT84 (small-caps→Title-case `MERY` →
        # `Mery` per TT51/TT57/TT58/TT60 chunk-12-and-14 precedent).
        # TT82/TT83/TT85/TT87/TT88/TT90 pass through fix_rows unchanged
        # on the notes_from_pm field (post-fix-rows value matches the
        # tie-break override's pinned merge-time value verbatim).
        ("TT81", "notes_from_pm"):
            "[1st ed. Anena], Overseer of the granary of Amūn. Temp. "
            "Amenophis I to Tuthmosis III. (CHAMPOLLION, No. 5, "
            "WILKINSON, No. 14, HAY, No. 8.) Parents, Ineni, Judge, and "
            "Sit-ḏhout. Wife, ʿAḥḥotp, called Thuiu.",
        ("TT82", "notes_from_pm"):
            "Scribe, Counter of the grain of Amūn, Steward of the Vizier. "
            "Temp. Tuthmosis III. (L. D. Text, No. 56, HAY, No. 16.) "
            "Parents, Ḏhutmosi, Overseer of lands, and Antef. "
            "Wife, Beketamūn.",
        ("TT83", "notes_from_pm"):
            "Governor of the town and Vizier. Early temp. Tuthmosis III. "
            "(L. D. Text, No. 41, WILKINSON, No. 64.) "
            "Wife, Taʿamethu (name in tomb 131).",
        ("TT84", "notes_from_pm"):
            "First royal herald, Overseer of the gate, temp. Tuthmosis "
            "III. Partly usurped by Mery (tomb 95), temp. Amenophis II. "
            "(CHAMPOLLION, No. 11, L. D. Text, No. 71, WILKINSON, No. "
            "31, HAY, No. 19.) Parents (of Amunezeḥ), Siḏhout, Judge, "
            "and Resi. Wife (of Amunezeḥ), Ḥenutnefert.",
        ("TT85", "notes_from_pm"):
            "Lieutenant-commander of soldiers. Temp. Tuthmosis III to "
            "Amenophis II. (CHAMPOLLION, No. 12, HAY, No. 20.) "
            "Mother, Tetires. Wife, Baki, Chief royal nurse.",
        ("TT87", "notes_from_pm"):
            "Overseer of the granaries of Upper and Lower Egypt, Overseer "
            "of horses of the Lord of the Two Lands, Royal scribe. Temp. "
            "Tuthmosis III. (HAY, No. 17.) Father, Sen-ḏhout.",
        ("TT88", "notes_from_pm"):
            "Lieutenant of the King, Standard-bearer of the Lord of the "
            "Two Lands. Temp. Tuthmosis III to Amenophis II. (CHAMPOLLION, "
            "No. 8, L. D. Text, No. 61.) Wife, Neit, Chief royal nurse, "
            "Governess of the god.",
        ("TT90", "notes_from_pm"):
            "Standard-bearer of (the sacred bark called) 'Beloved-of-Amūn', "
            "Captain of troops of the police on the west of Thebes. "
            "Temp. Tuthmosis IV to Amenophis III. (CHAMPOLLION, No. 9 bis, "
            "L. D. Text, No. 63, HAY, No. 22.) Wives, Sensenbut and Tiy.",
        # Chunk 18 (TT91–TT100) — 3 tie-break overrides on notes_from_pm.
        # All pinned to agent A: macron-Ū on `Amūn` per PM body-prose
        # verbatim policy + ayin-before-a `wʿab-priest` per the TT14 /
        # TT68 / TT79 precedent. TT95 also resolves the structural
        # decision to put TT84 in shared_with_tombs (A+B win 2/1 over C)
        # and drop the `(See also usurpation in tomb 84.)` parenthetical
        # from notes (prevents the Tier-3 `is_usurped` regex from
        # spuriously firing on TT95, which is Mery's primary tomb).
        # TT95/TT97/TT100 pass through fix_rows unchanged on this field
        # (post-fix-rows value matches the pinned merge-time value).
        ("TT95", "notes_from_pm"):
            "First prophet of Amūn. (See also usurpation in tomb 84.) "
            "Temp. Amenophis II. (CHAMPOLLION, No. 14, L. D. Text, "
            "No. 70, HAY, No. 14.) Parents, Nebpeḥtireʿ, First prophet "
            "of Min of Koptos, and Ḥunay(t), Chief nurse of the Lord of "
            "the Two Lands (name from tomb 84). Wife, Dey.",
        ("TT97", "notes_from_pm"):
            "First prophet of Amūn. Temp. Amenophis II (?). Father, "
            "Ḏḥutiḥotp, wʿab-priest, Overseer of sandal-makers of the "
            "Temple of Amūn.",
        ("TT100", "notes_from_pm"):
            "Governor of the town and Vizier. Temp. Tuthmosis III to "
            "Amenophis II. (CHAMPOLLION, No. 15, L. D. Text, No. 58, "
            "WILKINSON, No. 35.) Parents, Neferweben, [Vizier], "
            "wʿab-priest of Amūn, and Bet. Wife, Meryt.",
        # Chunk 19 (TT101-TT110) — 4 tie-break overrides, all on notes_from_pm.
        # TT104: cross-reference `(See tomb 80.)` precedes temporal clause per
        #   PM I.1 p.217 printed order (agent A matched; B reversed; C dropped).
        # TT106: mid-sentence citation before `Parents,` per PM I.1 p.219
        #   printed convention; `Merytreʿ` (not `Meytrerʿ` OCR typo of agent C;
        #   not end-sentence placement of agent B). Agent A pinned.
        # TT107: mid-sentence citation + `Ḥepu` (underdot-ḥ) per PM I.1 p.224;
        #   agent C form pinned (agent A had `Hepu` without diacritic; B had
        #   end-sentence citation).
        # TT110: `Baktḥ.` (with underdot-ḥ) per PM I.1 p.227; agent A pinned
        #   (B added spurious `[or]` from hieroglyphic determinative; C stripped ḥ).
        # All four pass through fix_rows unchanged on this field.
        ("TT104", "notes_from_pm"):
            "(See tomb 80.) Temp. Amenophis II.",
        ("TT106", "notes_from_pm"):
            "Governor of the town and Vizier. Temp. Sethos I to Ramesses II. "
            "(CHAMPOLLION, No. 32, L. D. Text, No. 39, HAY, No. 7.) Parents, "
            "Nebneteru called Theri, Chief prophet of Amūn, and Merytreʿ, "
            "Chief of the harim of Amūn. Wife, Tiy, Chief of the harim of Amūn.",
        ("TT107", "notes_from_pm"):
            "Royal scribe, Steward of the estate of Amenophis III "
            "'Reʿ is brilliant'. Temp. Amenophis III. "
            "(CHAMPOLLION, No. 33, L. D. Text, No. 37.) Parents, Neby, Judge, "
            "and Ḥepu.",
        ("TT110", "notes_from_pm"):
            "Royal butler, Royal herald. Temp. Ḥatshepsut to Tuthmosis III. "
            "Parents, Pesediri (?) and Keku. Wife, Baktḥ.",
        # Chunk 20 (TT111-TT120) — 4 tie-break overrides, all on notes_from_pm.
        # TT112: macron-Amūn + source-faithful `Wife of (ʿAshefytemweset)` order
        #   per PM I.1 p.229 printed text; agent A pinned.
        # TT113: ayin-before-a `wʿab` (TT14/TT68/TT97 precedent) + lowercase
        #   initial (body prose) + `Bekenamtūn` (consonant-complete + macron-Ū);
        #   assembled from correct elements across agents (no single agent perfect).
        # TT114: macron-Amūn + ayin-before-a `wʿab-priest` for father's title;
        #   agent A pinned. Egyptologist pending on role=None (PM prints a title).
        # TT120: `Amūn` macron-Ū + `Maḥu` underdot-ḥ per PM `MAI;IU` glyph;
        #   agent C pinned. All four pass through fix_rows unchanged on this field.
        ("TT112", "notes_from_pm"):
            "Temp. Tuthmosis III. Usurped by ʿAshefytemweset, Prophet of Amūn "
            "'Great of Majesty', Ramesside. (CHAMPOLLION, No. 59.) "
            "Father (of ʿAshefytemweset), Pentawer. "
            "Wife of (ʿAshefytemweset), Mutemwia.",
        ("TT113", "notes_from_pm"):
            "wʿab-priest over-the-secrets of the estate of Amūn, Prophet in the "
            "Temple of Tuthmosis IV. Temp. Ramesses VIII. "
            "(WILKINSON, No. 2, HAY, No. 10.) Father, Bekenamtūn, "
            "wʿab-priest of Amūn. Wife, Esi.",
        ("TT114", "notes_from_pm"):
            "Head of goldworkers of the estate of Amūn. Dyn. XX. "
            "Father, a wʿab-priest of Anubis.",
        ("TT120", "notes_from_pm"):
            "Second prophet of Amūn. Temp. Amenophis III. "
            "Parents, Yuia and Thuiu (tomb 46 in the Valley of the Kings). "
            "Called Maḥu in GARDINER and WEIGALL, Cat.",
        # Chunk 21 (TT121-TT130) — 1 tie-break override on notes_from_pm.
        # TT122: agent B's `with Chapels of Amenemḥet, both Overseers...` value
        #   pinned (includes shared-occupancy descriptor, no occupant_name dup,
        #   macron-Ū on Amūn). Passes through fix_rows unchanged.
        ("TT122", "notes_from_pm"):
            "with Chapels of Amenemḥet, both Overseers of the magazine of Amūn. "
            "Temp. Tuthmosis III. Parents (of [Amen]ḥotp), ʿAmethu (tomb 83) "
            "and Taʿamethu. Father (of Amenemḥet), Neferḥotep, Prophet. "
            "Wife (of Amenemḥet), Esnub.",
        # Chunk 22 (TT131-TT140) — 7 tie-break overrides.
        # TT134: agent C pinned ((1st ed. 135) + Amenaphis + mid-sentence citation;
        #   CHUNK22_CORRECTIONS would restore Amūn macron but tie-break value
        #   already has Amūn — passes through fix_rows unchanged on notes field.
        # TT135: agent C pinned (macron-Ū correct, no ayin skeleton). CHUNK22_CORRECTIONS
        #   restores `Wab-priest` → `wʿab-priest` — post-fix-rows value differs.
        # TT137: agent C pinned (Amūn macron + mid-sentence citation). Passes through
        #   fix_rows unchanged.
        # TT138: agent C pinned (Amūn macron + CHAMPOLLION uppercase + mid-sentence).
        #   CHUNK22_CORRECTIONS restores `Nesha.` → `Neshaʿ.` — post-fix-rows differs.
        # TT139: agent C pinned (Amūn macrons + Ptaḥ/Ḥatḥor/Ḥenutnefert underdots).
        #   CHUNK22_CORRECTIONS restores `Wab-priest` → `wʿab-priest` — post-fix-rows differs.
        # TT140|notes_from_pm: agent A pinned (lowercase `probably`, no headword prefix).
        #   CHUNK22_CORRECTIONS restores `Kefia` → `Ḥefia` — post-fix-rows differs.
        # TT140|occupant_alt_names: agent B pinned (`["Hefia"]`, ḥ-stripped per
        #   TT57/TT120 matchable-name precedent). Passes through fix_rows unchanged.
        ("TT134", "notes_from_pm"):
            "(1st ed. 135) Prophet of Amenaphis who navigates on the Sea of Amūn. "
            "Dyn. XIX. (L. D. Text, No. 79.) Father, Besuemopet, same title as "
            "deceased. Wife, Tabesi.",
        ("TT135", "notes_from_pm"):
            "wʿab-priest in front of Amūn. Dyn. XIX.",
        ("TT137", "notes_from_pm"):
            "Head of works of the Lord of the Two Lands in every monument of Amūn. "
            "Temp. Ramesses II. (L. D. Text, No. 91.) Parents, Bak, Head of works "
            "in the Place of Eternity, and Tekhu. Wife, Taikharu.",
        ("TT138", "notes_from_pm"):
            "Overseer of the garden in the Ramesseum in the estate of Amūn. "
            "Temp. Ramesses II. (CHAMPOLLION, No. 29.) Wife, Neshaʿ.",
        ("TT139", "notes_from_pm"):
            "wʿab-priest in front, First royal son in front of Amūn, Overseer "
            "of peasants of Amūn. Temp. Amenophis III. Father, Sheroy, Prophet "
            "of Ptaḥ and Ḥatḥor. Wife, Ḥenutnefert.",
        ("TT140", "notes_from_pm"):
            "probably called Ḥefia, Goldworker, Portrait sculptor. "
            "Temp. Tuthmosis III to Amenophis II. Wife, Tauy.",
        ("TT140", "occupant_alt_names"): ["Hefia"],
        # Chunk 23 (TT141-TT150) — 7 tie-break overrides (all notes_from_pm,
        # all 1/1/1 Amün/Amūn/Amun macron split; TT144 also has (?) spacing +
        # wife-name Ḥ; TT147 also has (?) spacing).
        # TT141: agent B pinned (Amūn macron + wife-name ayin). CHUNK23_CORRECTIONS
        #   restores `Wab-priest` → `wʿab-priest` — post-fix-rows value differs.
        # TT144/TT146/TT147/TT148/TT149/TT150: agent B pinned (Amūn macron).
        #   Pass through fix_rows unchanged on the notes field.
        ("TT141", "notes_from_pm"):
            "wʿab-priest of Amūn. Ramesside. Wife, Takhaʿ(t).",
        ("TT144", "notes_from_pm"):
            "Head of the field-labourers. Temp. Tuthmosis III (?). Wife, Henuttaui.",
        ("TT146", "notes_from_pm"):
            "Overseer of the granary of Amūn, Scribe, Counter of grain, tny of the "
            "god's wife (titles from cones). Temp. Tuthmosis III (?). (Inaccessible.) "
            "Wife, Suitnub (from cone).",
        ("TT147", "notes_from_pm"):
            "Head of the masters of ceremonies(?) of Amūn, &c. Temp. Tuthmosis IV(?). "
            "Wife, Nefert.",
        ("TT148", "notes_from_pm"):
            "Prophet of Amūn. Temp. Ramesses III to V. Parents, Thonnfer (tomb 158) "
            "and Nefertere. Wife, Tamert, Chief of the harim [of Amūn].",
        ("TT149", "notes_from_pm"):
            "Royal scribe of the table of the Lord of the Two Lands, Overseer of the "
            "huntsmen of Amūn. Ramesside. Wife, Sitmut.",
        ("TT150", "notes_from_pm"):
            "Overseer of cattle of Amūn. Late Dyn. XVIII. (Unfinished.) Wife, "
            "Iaet-ib, Royal concubine.",
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
