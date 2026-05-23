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
        # Chunk 24 (TT151-TT160) — 3 tie-break overrides (all notes_from_pm).
        # TT151: agent C pinned (no OCR garbage, has Parents clause). CHUNK24_CORRECTIONS
        #   restores `Amun` → `Amūn` — post-fix-rows value differs from pinned C value.
        # TT157: agent A pinned (Amūn×2, CHAMPOLLION uppercase). Pass through unchanged.
        # TT158: agent A pinned (Amūn×2, CHAMPOLLION uppercase). Pass through unchanged.
        ("TT151", "notes_from_pm"):
            "Scribe, Counter of cattle of the god's wife of Amūn, Steward of the "
            "god's wife. Temp. Tuthmosis IV. (Unfinished.) Wife, Nefertere. "
            "Parents, Nebnufer.",
        ("TT157", "notes_from_pm"):
            "First prophet of Amūn. Temp. Ramesses II. (CHAMPOLLION, No. 42, "
            "L. D. Text, No. 7.) Wife, Takhaʿt, Chief of the harim of Amūn, "
            "Songstress of Isis.",
        ("TT158", "notes_from_pm"):
            "Third prophet of Amūn. Probably temp. Ramesses III. (CHAMPOLLION, "
            "No. 44, L. D. Text, No. 9.) Wife, Nefertere, Chief of the harim "
            "of Amūn.",
        ("TT181", "notes_from_pm"):
            "Head sculptor of the Lord of the Two Lands, and Ipuky, Sculptor of "
            "the Lord of the Two Lands. Temp. Amenophis III to IV. Parents (of "
            "Nebamūn), Neferḥet and Thepu; (of Ipuky), Senennūter and Netermosi. "
            "Wife of Ipuky (and probably of Nebamūn), Ḥenutnefert.",
        ("TT189", "occupant_name"): "Nekht-Ḏhout",
        ("TT189", "notes_from_pm"):
            "Overseer of carpenters of the northern lake of Amūn, Head of "
            "goldworkers in the estate of Amūn. Temp. Ramesses II. Wives, "
            "Netemḥab and Tentpa...",
        ("TT190", "notes_from_pm"):
            "Divine father, Prophet of the head of the King. Saite (usurped "
            "from a Ramesside tomb). Parents, Pakharkhons, Divine father, and "
            "Meramūniotes, Sistrum-player of Amen-rēʿ. Wife, Tanub.",
        # Chunk-28 overrides (TT192/TT193/TT194/TT196 — all notes_from_pm).
        # No CHUNK28_CORRECTIONS touch these fields; post-fix-rows values
        # match the pinned tie-break values verbatim.
        ("TT192", "notes_from_pm"):
            "Steward of the Great Royal Wife Teye, called Senaʿa. Temp. "
            "Amenophis III to IV. Parents, Silḥed and Ruiu.",
        ("TT193", "notes_from_pm"):
            "Magnate of the seal in the treasury of the estate of Amūn. "
            "Dyn. XIX. Wife, Tadetawert. Stela only, but numbered as a tomb.",
        ("TT194", "notes_from_pm"):
            "Overseer of marshland-dwellers of the estate of Amūn, Scribe of "
            "the temple of Amūn. Dyn. XIX. Father, a wʿab-priest in front of "
            "Amūn, Scribe of divine offerings of Amūn. Wife, Nezemtmut.",
        ("TT196", "notes_from_pm"):
            "Chief steward of Amūn. Saite. Parents, Ibi (tomb 36) and "
            "Shepenernōte.",
        # Chunk-29 overrides (TT202/TT207/TT209/TT210 — all notes_from_pm).
        # TT202 and TT207 have CHUNK29_CORRECTIONS applied post-merge that
        # add macron-Ū to Amūn; TT209 and TT210 match the pinned value verbatim.
        ("TT202", "notes_from_pm"):
            "Prophet of Ptaḥ Lord of Thebes, Priest in front of Amūn. Dyn. XIX(?).",
        ("TT207", "notes_from_pm"):
            "Scribe of divine offerings of Amūn. Ramesside. Parents, Ḥemawen and Nebuy.",
        ("TT209", "notes_from_pm"):
            "(?) Hereditary prince, Sole beloved friend. Saite. (formerly read Ḥatashemro)",
        ("TT210", "notes_from_pm"):
            "Servant in the Place of Truth. Dyn. XIX. (L. D. Text, No. 104.) "
            "Parents(?), Piay, Sculptor in the Place of Truth, and Nefertkhaʿ. "
            "Wife, Nebtyunu.",
        # Chunk-30 overrides (TT211/TT213/TT215/TT217/TT218 notes_from_pm
        # + TT217 source_citation).
        # TT211: CHUNK30_CORRECTIONS restores ayin Wa'be(t)→Waʿbe(t).
        # TT213: pinned value matches final (Bald, commas, no L.D. bleed).
        # TT215: CHUNK30_CORRECTIONS restores Ḥatḥor/Ḥunuro underdots + L.D. cite.
        # TT217 notes: CHUNK30_CORRECTIONS restores ayin Nefertkha→Nefertkhaʿ.
        # TT217 source_citation: pinned value is the final page dict.
        # TT218: CHUNK30_CORRECTIONS rewrites to commas/no Co-occupants/Ḥetepti/Amūn.
        ("TT211", "notes_from_pm"):
            "Servant of the Lord of the Two Lands in the Place of Truth. Dyn. XIX. "
            "Parents, Nefersenut, same title as deceased, and Iuy. Wife, Waʿbe(t).",
        ("TT213", "notes_from_pm"):
            "Servant of the Lord of the Two Lands, Servant in the Place of Truth. "
            "Dyn. XX. Parents, Bald (tomb 298) and Taysen. Wife, Nebtnuhet.",
        ("TT215", "notes_from_pm"):
            "Royal scribe in the Place of Truth. (Burial Chamber is tomb 265.) "
            "Dyn. XIX. Parents, Minmosi and Esi (names in tomb 335). Wife, "
            "Ḥatḥor, called Ḥunuro. (L. D. Text, No. 100.)",
        ("TT217", "notes_from_pm"):
            "Sculptor. Temp. Ramesses II. Parents, Piay and Nefertkhaʿ "
            "(names in tomb 210). Wife, Duammeres.",
        ("TT217", "source_citation"):
            {"edition": "PM I.1 2nd ed. 1960", "page": 315, "section": "I"},
        ("TT218", "notes_from_pm"):
            "Servant in the Place of Truth on the west of Thebes. Ramesside. "
            "Parents, Nebenmaʿet, Hr-mnw of Amūn, and Ḥetepti. Wife, Iymway.",
        # Chunk-31 overrides (TT221/TT222 occupant_name, TT223/TT224 notes_from_pm).
        ("TT221", "occupant_name"): "Horimin",
        ("TT222", "occupant_name"): "Hekmaʿetreʿ-Nakht",
        ("TT223", "notes_from_pm"):
            "First ḳk-priest. Saite. (CHAMPOLLION, No. 17, L. D. Text, No. 93.)",
        ("TT224", "notes_from_pm"):
            "Overseer of the estate of the god's wife, Overseer of the two "
            "granaries of the god's wife ʿAḥmosi Nefertere. Temp. Tuthmosis "
            "III or Hatshepsut. Parents, Senusert and Taidy. Wife, Nub, "
            "Royal concubine (in tombs 29 and 96).",
        # Chunk-32 (TT231-TT240) — 3 tie-break overrides:
        # TT232|notes_from_pm: agent A's `Weshebamunheref` pinned at merge;
        #   CHUNK32_CORRECTIONS restores the underdot-ḥ → `Weshebamunḥeref`.
        #   Post-fix-rows value differs from the pinned merge-time value.
        # TT235|occupant_name: agent B's `Userhet` pinned; no CHUNK32_CORRECTIONS
        #   on this field — final value matches the override verbatim.
        # TT239|attribution_certainty: tie-break pinned `uncertain` (3-way split:
        #   A=uncertain, B=probable, C=attested), the deriver also fires
        #   `uncertain` from the `(?)`. BUT a DERIVER_OVERRIDE (added PR #276
        #   round-1 per Gemini correction) overrides to `attested` because the
        #   `(?)` qualifies the REGNAL DATE RANGE (Temp. Tuthmosis IV to
        #   Amenophis II), not Penhet's identification. Per chunk-10 TT12 +
        #   chunk-31 TT225 orthogonality precedent.
        ("TT232", "notes_from_pm"):
            "Scribe of the divine seal of the treasury of Amun. Ramesside. "
            "Father, Weshebamunḥeref.",
        ("TT235", "occupant_name"): "Userhet",
        ("TT239", "attribution_certainty"): "attested",
        # Chunk-33 (TT241-TT250) — 6 tie-break overrides:
        # TT241|notes_from_pm: agent C's value pinned (wife `<Alimosi` — ayin
        #   preserved). Post-fix-rows: unchanged (no CHUNK33_CORRECTIONS on this
        #   field beyond what the tie-break already set).
        # TT241|occupant_name: tie-break pinned agent A's `Kahmosi` (anchor;
        #   all agents wrong). CHUNK33_CORRECTIONS overwrites to `ʿAhmosi`.
        #   Post-fix-rows value differs from the pinned merge-time value.
        # TT242|notes_from_pm: agent C's value pinned (best adoratress name +
        #   Pedeamonnai). CHUNK33_CORRECTIONS appends `(L. D. Text, No. 22.)`.
        #   Post-fix-rows value differs from the pinned merge-time value.
        # TT242|occupant_name: agent B's `Wehebreconi` pinned. CHUNK33_CORRECTIONS
        #   strips phantom `i` → `Wehebrecon`. Post-fix-rows differs.
        # TT243|notes_from_pm: agent B's `called Ragi` pinned; no CHUNK33_CORRECTIONS
        #   on this field — final value matches the override verbatim.
        #   (Flag for egyptologist: nickname unresolvable from OCR hieroglyphs.)
        # TT246|notes_from_pm: agent A's `Sitmenḥit` pinned (source OCR `l).` = ḥ);
        #   no CHUNK33_CORRECTIONS — final value matches the override verbatim.
        ("TT241", "notes_from_pm"):
            "Scribe of the divine writings, Child of the nursery, Head of "
            "mysteries in the House of the morning. Temp. Tuthmosis III(?). "
            "Wife, ʿAlimosi.",
        ("TT241", "occupant_name"): "ʿAhmosi",
        ("TT242", "notes_from_pm"):
            "Chamberlain of the divine adoratress ʿAnkhnesneferebreʿ. Saite. "
            "Wife, Tadepanehep. Father, Pedeamonnai; mother, Mutardais. "
            "(L. D. Text, No. 22.)",
        ("TT242", "occupant_name"): "Wehebrecon",
        ("TT243", "notes_from_pm"):
            "Mayor of the Southern City, called Ragi, Royal scribe. Saite. "
            "Father, a prophet and Izeneku-priest in Southern On.",
        ("TT246", "notes_from_pm"): "Scribe. Dyn. XVIII. Wife, Sitmenḥit.",
        # Chunk-34 (TT251-TT260) — 10 tie-break overrides (all notes_from_pm):
        # Agent C systematically truncated notes (dropped parents/wife clauses)
        # creating 1/1/1 splits. No CHUNK34_CORRECTIONS touch these fields, so
        # final values equal the tie-break-pinned values verbatim.
        ("TT251", "notes_from_pm"):
            "Royal scribe, Overseer of the cattle of Amun, Overseer of the "
            "magazine of Amun. Temp. early Tuthmosis III. Father, Nesu-t, "
            "Head of the magazine of Amun.",
        ("TT252", "notes_from_pm"):
            "Steward, Nurse of the god's wife. Temp. Hatshepsut. Parents, "
            "see tomb 71 (brother Senenmut). Wife, Senemiʿoḥ (name in tomb 71).",
        ("TT253", "notes_from_pm"):
            "Scribe, Counter of the grain (a) in the granary of Amun, (b) of "
            "the granary of divine offerings. Temp. Amenophis III (?). "
            "Wife, Tannfer.",
        ("TT254", "notes_from_pm"):
            "Scribe of the treasury, Custodian of the estate of Teye in the "
            "estate of Amun. Late Dyn. XVIII. Wife, Tamert.",
        ("TT255", "notes_from_pm"):
            "Royal scribe, Steward in the estates of Haremhab, and of Amun. "
            "Temp. Haremhab (?). Wife, Nebttaui, nickname Towey. "
            "(CHAMPOLLION, No. 52, HAY, No. 2.)",
        ("TT256", "notes_from_pm"):
            "Overseer of the cabinet, Fanbearer, Child of the nursery. "
            "Temp. Amenophis II. Wife, Ryu. (L. D. Text, No. 31.)",
        # TT257 notes_from_pm: tie-break value unchanged by fix_rows.
        # TT257 attribution_certainty: DERIVER_OVERRIDE → attested
        #   (deriver fires on `perhaps Piay` = secondary figure's parentage hedge,
        #   not occupant-identity hedge; same class as TT253/TT255/TT258/TT260).
        # NOTE: tie-break-overrides.json only covers notes_from_pm for TT257;
        # the attribution_certainty DERIVER_OVERRIDE is NOT a tie-break entry,
        # so no separate pin is needed here beyond the notes_from_pm pin.
        ("TT257", "notes_from_pm"):
            "Scribe, Counter of the grain of Amun, temp. Tuthmosis IV to "
            "Amenophis III. Usurped by Maḥu, Deputy in the mansion of "
            "Usimare-setepenre (= Ramesseum) in the estate of Amun, temp. "
            "Ramesses II. Father (of Maḥu), perhaps Piay. Wife (of Maḥu), "
            "Tawert. (L. D. Text, No. 32.)",
        ("TT258", "notes_from_pm"):
            "Child of the nursery, Royal scribe of the house of the royal "
            "children. Temp. Tuthmosis IV (?). Mother, Nay.",
        ("TT259", "notes_from_pm"):
            "Warb-priest, Scribe in all the monuments of the estate of Amun, "
            "Head of the outline-draughtsmen in the House of Gold of the "
            "estate of Amun. Ramesside. Parents, Ḥuy, warb-priest of Amun, "
            "and Beketptaḥ. Wife, Mutemwia.",
        ("TT260", "notes_from_pm"):
            "Scribe, Weigher of [Amun], Overseer of the ploughed lands of "
            "[Amun]. Temp. Tuthmosis III (?). Wife, Nubemweset (name from cone).",
        # Chunk-35 (TT261-TT270) — 4 tie-break overrides:
        # TT266|occupant_name: B's `Amennakht` pinned (PDF-verbatim AMENNAKHT).
        #   No CHUNK35_CORRECTIONS on this field — final value equals pinned.
        # TT266|notes_from_pm: PDF-verbatim `Buḳentef` + `Ḥenutrayunu` pinned.
        #   No CHUNK35_CORRECTIONS on this field — final value equals pinned.
        # TT267|notes_from_pm: PDF-verbatim `Tārekhʿan` + `Ḥenutmet` pinned.
        #   No CHUNK35_CORRECTIONS on this field — final value equals pinned.
        # TT268|notes_from_pm: `Family tomb of Nebnakht.` + `ʿAuti` pinned.
        #   No CHUNK35_CORRECTIONS on this field — final value equals pinned.
        ("TT266", "occupant_name"): "Amennakht",
        ("TT266", "notes_from_pm"):
            "Chief craftsman of the Lord of the Two Lands in the Place of "
            "Truth on the west of Thebes. Dyn. XIX. Parents, Buḳentef and Iy "
            "(names in tomb 219). Wife, Ḥenutrayunu.",
        ("TT267", "notes_from_pm"):
            "Officer of the workmen in the Place of Truth on the west of "
            "Thebes, Fashioner of the images of all the gods in the House of "
            "Gold. Dyn. XX. (L. D. Text, Nos. 102-3.) Parents, Amennakht and "
            "Tārekhʿan. Wife, Ḥenutmet.",
        ("TT268", "notes_from_pm"):
            "Family tomb of Nebnakht. Servant in the Place of Truth. Dyn. XIX. "
            "Parents, Ipy and ʿAuti (names from stela in Turin Mus. Sup. 6044). "
            "Wife, Thay.",
        # Chunk-36 (TT271-TT280) — 7 tie-break overrides:
        # TT273|occupant_name: source-verbatim Sayemiotf (no CHUNK36_CORRECTIONS).
        # TT274|co_occupants: PM-verbatim ...y name; role null→Official by
        #   CHUNK36_CORRECTIONS (SENTINEL_NULL_STRINGS collapses Unknown→null).
        # TT274|notes_from_pm: Amun→Amūn macron by CHUNK36_CORRECTIONS.
        # TT276|notes_from_pm: ʿAḥḥotp + Ḥenutyunu by CHUNK36_CORRECTIONS.
        # TT278|occupant_name: Amenemhab (no CHUNK36_CORRECTIONS on this field).
        # TT279|notes_from_pm: Tasentenḥor underdot by CHUNK36_CORRECTIONS.
        # TT280|notes_from_pm: Mentuḥotp + (Formerly read Meḥenkwetreʿ.) by
        #   CHUNK36_CORRECTIONS.
        # TT283|co_occupants: [] (tie-break pinned empty list; Tamut is wife in notes).
        # TT283|notes_from_pm: Amun→Amūn macron by CHUNK37_CORRECTIONS.
        # TT289|notes_from_pm: harin + comma punctuation (tie-break; no CHUNK37 change).
        # TT290|notes_from_pm: Tausert Meḥytkhacti + wife placeholder by CHUNK37_CORRECTIONS.
        ("TT273", "occupant_name"): "Sayemiotf",
        ("TT274", "co_occupants"): [
            {"alt_names": [], "name": "...y", "role": "Official"}
        ],
        ("TT274", "notes_from_pm"):
            "First prophet of Monthu of Tod, and of Thebes, sem-priest in the "
            "Ramesseum in the estate of Amūn. Ramesside. (Inaccessible.) Wife, ...y.",
        ("TT276", "notes_from_pm"):
            "Overseer of the treasury of gold and silver, Judge, Overseer of "
            "the cabinet. Temp. Tuthmosis IV (?). Parents, Nekhu (?) and "
            "ʿAḥḥotp. Wife, Ḥenutyunu.",
        ("TT278", "occupant_name"): "Amenemhab",
        ("TT279", "notes_from_pm"):
            "Chief steward of the god's wife. Temp. Psammetikhos I. Parents, "
            "Pedubaste, Divine father beloved of the god, and Tasentenḥor.",
        ("TT280", "notes_from_pm"):
            "Chief steward in ..., Chancellor. Temp. Mentuḥotp (Sʿankhkareʿ). "
            "(Formerly read Meḥenkwetreʿ.) Son Antef, Hereditary Prince.",
        ("TT283", "co_occupants"): [],
        ("TT283", "notes_from_pm"):
            "First prophet of Amūn. Temp. Ramesses II to Sethos II. Wife, Tamut. "
            "(name in niche in Court).",
        ("TT289", "notes_from_pm"):
            "Viceroy of Kush, Overseer of the South Lands. Temp. Ramesses II. "
            "Father, Siwazyt. Wife, Nefertmut, Chief of the harin of Nekhbet.",
        ("TT290", "notes_from_pm"):
            "Servant in the Place of Truth on the West. Ramesside. Parents, "
            "Siwazyt, Head of the bark of Amūn, and Tausert Meḥytkhacti. "
            "Wife, [name unclear in source].",
        # Chunk-38 (TT291-TT300) — 10 tie-break overrides:
        # TT291|co_occupants: Nekhtmin with name key (only A was schema-valid).
        # TT291|notes_from_pm: full co-occupant clause + Min-hotep (A form).
        # TT292|notes_from_pm: He-nekhu → Ḥenekhu by CHUNK38_CORRECTIONS.
        # TT293|occupant_name: Raʿmessenakht (B; source RA<MESSENAKHT ayin).
        # TT294|notes_from_pm: Hathor (B clean form; no spurious trailing e).
        # TT295|occupant_name: Dhutmosi → Ḏhutmosi by CHUNK38_CORRECTIONS.
        # TT295|notes_from_pm: B+C majority form; no Called Paroy prefix.
        # TT298|co_occupants: Unnufer with name key (only A was schema-valid).
        # TT299|occupant_name: Iniherkhac (A; source INI;IERKHAC]).
        # TT300|occupant_name: ʿAnhotp (B; source cANI;IOTP ayin+strip-Ḥ).
        ("TT291", "co_occupants"): [
            {"alt_names": [], "name": "Nekhtmin", "role": "Official"}
        ],
        ("TT291", "notes_from_pm"):
            "Servant in the Great Place, and Nekhtmin, Servant in the Place "
            "of Truth. Late Dyn. XVIII. Parents (of Nu), Pia and Mutnefert, "
            "and wife, Khatnesut. Parents (of Nekhtmin), Min-hotep and "
            "Nefertere, and wife, Sekhmet.",
        ("TT292", "notes_from_pm"):
            "Servant in the Place of Truth. Temp. Sethos I to Ramesses II. "
            "Father, Ḥenekhu (from stela in Brit. Mus. 262). Wife, Makhay.",
        ("TT293", "occupant_name"): "Raʿmessenakht",
        ("TT294", "notes_from_pm"):
            "Overseer of the granary of Amun, temp. Amenophis III. Usurped by "
            "Roma, wab-priest of Amun, early Ramesside. Wife (of Roma), Hathor.",
        ("TT295", "occupant_name"): "Ḏhutmosi",
        ("TT295", "notes_from_pm"):
            "Head of the secrets in the Chest of Anubis, sem-priest in the "
            "Good House, Embalmer. Temp. Tuthmosis IV to Amenophis III (?). "
            "Parents, Sennuter, sem-priest in the Good House, &c., and Senemiʿoḥ. "
            "Wives, Nefertere and Rennutet.",
        ("TT298", "co_occupants"): [
            {"alt_names": [], "name": "Unnufer", "role": "Official"}
        ],
        ("TT299", "occupant_name"): "Iniherkhac",
        ("TT300", "occupant_name"): "ʿAnhotp",
        # Chunk 39 (TT301–TT310) — 8 tie-break overrides.
        # TT301/TT302/TT304/TT307 notes: CHUNK39_CORRECTIONS further mutates.
        # TT305/TT306/TT308 notes + co_occupants: CHUNK39_CORRECTIONS mutates.
        # TT306 occupant_name: pinned directly, no further mutation.
        ("TT301", "notes_from_pm"):
            "Scribe of the table of the Lord of the Two Lands in the estate of "
            "Amun. Ramesside. Wife, (name in cartouche). (Name and titles copied "
            "by GREENLEES, in Philadelphia Univ. Mus.)",
        ("TT302", "notes_from_pm"):
            "Overseer of the magazine. Ramesside. Father, Userḥat, Head of the "
            "magazine of Amun. (Description by GREENLEES, in Philadelphia Univ. Mus.)",
        ("TT304", "notes_from_pm"):
            "Scribe of the table of Amun, Scribe of the Lord of the Two Lands. "
            "Ramesside. For position, see p. 356.",
        ("TT305", "co_occupants"):
            [{"alt_names": [], "name": "Tamelhit", "role": "Unknown"}],
        ("TT305", "notes_from_pm"):
            "Wʿab-priest in front of Amun, Scribe of the divine offerings of Amun. "
            "Dyn. XIX-XXI. Wife, Tamelḥit.",
        ("TT306", "occupant_name"): "Irzanen",
        ("TT306", "notes_from_pm"):
            "Door-opener of the estate of Amun. Dyn. XIX-XXI. Wife, Mutenopet. "
            "(Copies of texts by GREENLEES, in Philadelphia Univ. Mus.)",
        ("TT307", "notes_from_pm"):
            "(name from ushabti). Dyn. XX-XXI. (Unfinished.) "
            "(Description by GREENLEES, in Philadelphia Univ. Mus.)",
        ("TT308", "notes_from_pm"):
            "Unique royal concubine, Prophetess of Ḥatḥor. Temp. Mentuḥotp "
            "(Nebḥepetreʿ). Deir el-Bahari, in the Temple of Mentuḥotp. "
            "(NAVILLE, No. 10.)",
        # Chunk 40 (TT311–TT320) — 8 tie-break overrides.
        # TT311/TT313/TT315/TT317/TT318/TT319/TT320 notes: CHUNK40_CORRECTIONS
        # further mutates (diacritic restores, mother name fix, d-bar restore).
        # TT312/TT316/TT320 occupant_name: CHUNK40_CORRECTIONS mutates TT317
        # (d-bar) and TT320 (ayin restore). TT312/TT316 pinned directly.
        ("TT312", "occupant_name"): "Espel(a)shuti",
        ("TT313", "notes_from_pm"):
            "Great steward. Temp. Mentuḥotp-Nebḥepetreʿ and Mentuḥotp-Sʿankhkareʿ.",
        ("TT316", "occupant_name"): "Neferhotep",
        ("TT317", "notes_from_pm"):
            "Scribe of the counting of corn in the granary of divine offerings of "
            "Amun. Temp. Tuthmosis III(?). (CHAMPOLLION, No. 25.) Parents, Senires, "
            "Mayor, and Taiy. Wife, Titau.",
        ("TT318", "notes_from_pm"):
            "Necropolis-stonemason of Amun. Temp. Tuthmosis III to Hatshepsut(?). "
            "(CHAMPOLLION, No. 26.) Wife, Henut.",
        ("TT319", "notes_from_pm"):
            "Daughter of Mentuḥotp-Sʿankhibtaui and Iʿob, wife of "
            "Mentuḥotp-Nebḥepetreʿ.",
        ("TT320", "notes_from_pm"):
            "Perhaps wife of Amosis. (Royal Cache, Dyn. XXI, see DEIR EL-BAHARI, "
            "Bibl. i 2, Pt. 2, in the Press.)",
        ("TT320", "occupant_name"): "Inhaʿpi",
        # Chunk 41 (TT321–TT330) — 4 tie-break overrides.
        # TT322 occupant_name: pinned B `Penshenʿabu` (source `PENSHEN<ABU`).
        # TT323 notes_from_pm: pinned A's form as base; CHUNK41_CORRECTIONS
        #   restores parent name `Amenemḥet` (OCR `Ameneml_tet`).
        # TT329 notes_from_pm: pinned C's headword form; CHUNK41_CORRECTIONS
        #   restores Ḥenutwact, Icoḥnufer, Patet.
        # TT330 notes_from_pm: pinned C's form; CHUNK41_CORRECTIONS restores
        #   ayin `Takhac` → `Takhaʿ`.
        ("TT322", "occupant_name"): "Penshenʿabu",
        ("TT323", "notes_from_pm"):
            "Outline-draughtsman of Amun in the Place of Truth, and in the Temple"
            " of Sokari. Temp. Sethos I. Parents, Amenemḥet, Outline-draughtsman"
            " in the Temple of Sokari, and Mutnefert. Wife, Nefertere.",
        ("TT329", "notes_from_pm"):
            "Mosi and Annexed tomb of Mosi probably his grandson, and Ipy, perhaps"
            " his son, all Servants in the Place of Truth. Ramesside. Wife (of"
            " Mosi, tomb 329), Ḥenutwact. Father (of Mosi, Annexed tomb),"
            " Icoḥnufer. Wife (of Mosi, Annexed tomb), Patet (name on stela,"
            " Louvre, C. 280, see infra). Wife (of Ipy), Bakt.",
        ("TT330", "notes_from_pm"):
            "Servant in the Place of Truth. Dyn. XIX. Parents, Simut and Peshedu."
            " Wife, Takhaʿ.",
        # Chunk 42 (TT331–TT340) — 5 tie-break overrides.
        # TT331 notes_from_pm: pinned C-shape with Ḥatiay restored (CHUNK42_CORRECTIONS
        #   restores diacritic from `Hatiay`; A/B hallucinated L.D.Text 105 from TT335).
        # TT333 source_citation: 3-way tie 400/401/399; C=399 correct per page-break marker.
        # TT335 notes_from_pm: pinned C-shape (Warb-priest, (I) parens, 105 decoded, correct
        #   placement of L.D.Text before Parents).
        # TT339 notes_from_pm: pinned B-style with [t] bracket restored (includes Peshedu
        #   full role per TT181/TT291 joint-burial precedent).
        # TT340 notes_from_pm: pinned A's form (Macenhmut closest to source `Macenl;mt`).
        ("TT331", "notes_from_pm"):
            "Chief prophet of Monthu. Ramesside. Father, Ḥatiay (tomb 324). Wife, Maiay."
            " Chief of the harim of Monthu.",
        ("TT333", "source_citation"):
            {"edition": "PM I.1 2nd ed. 1960", "page": 399, "section": "I"},
        ("TT335", "notes_from_pm"):
            "Warb-priest of Amenophis (I) Lord of the Two Lands, Chiseller of Amun,"
            " Servant in the Place of Truth. Dyn. XIX. (L. D. Text, No. 105.) Parents,"
            " Piay and Nefertkha. Wife, Nubemsheset.",
        ("TT339", "notes_from_pm"):
            "Servant in the Place of Truth, and Peshedu, Servant in the Place of Truth,"
            " Necropolis-stonemason of Amun in Karnak. Temp. Ramesses II. Parents (of"
            " Huy), Seba and Nefer[t]iyti (names from stelae in Brit. Mus. 446 and"
            " Louvre, C. 86). Father (of Peshedu), Harmosi. Wife (of both), Takharu.",
        ("TT340", "notes_from_pm"):
            "Servant in the Place of Truth (perhaps also owner of tomb 354). Early"
            " Dyn. XVIII. Parents, Macenhmut(?) and Hut. Wives, Reditico and Nubnefert.",
        # Chunk 43 (TT341–TT350) — 3 tie-break overrides.
        # TT343 notes_from_pm: 1/1/1 split on `called Paḥeḳmen,` prefix presence +
        #   mid-sentence citation punctuation. Agent B pinned (correct prefix, clean `.)
        #   Parents,`). PDF p.428 / chunk-43 source line 119 confirms `called PAḤEKMEN`.
        # TT345 notes_from_pm: 1/1/1 split on three axes: ayin in wʿb-priest, parent
        #   name (Senidhout vs Senigḥout vs Senighout), punctuation. Constructed value:
        #   ayin from B, `Senidhout` from A (PDF p.431 plain `d`), clean punctuation.
        # TT346 notes_from_pm: 1/1/1 split on macron-ō in Tentōpet and macron-ē + case
        #   in Penrēʿ. Constructed: `Tentōpet` from A (macron-ō confirmed PDF p.432),
        #   `Penrēʿ` from direct PDF read (small-caps with macron-ē → title-case).
        #   DERIVER_OVERRIDE needed: `Probably` qualifies usurpation event, not primary
        #   attribution; attribution_certainty pinned back to `attested`.
        # TT343 notes EXPECTED reflects the post-CHUNK43_CORRECTIONS form: plain k
        # (egyptologist P1.2 PDF verification — PM p.428 prints `PAḤEKMEN` with
        # Ḥ-underdot + plain K, not Ḳ-underdot). The merge-time tie-break value
        # had Ḳ-underdot (`Paḥeḳmen`), which is then overridden in fix_rows.py.
        ("TT343", "notes_from_pm"):
            "called Paḥekmen, Overseer of works, Child of the nursery. Early Dyn."
            " XVIII. (CHAMPOLLION, No. 37, L. D. Text, No. 74.) Parents, Irtonena"
            " and Tirukak.",
        ("TT345", "notes_from_pm"):
            "wʿb-priest, Eldest king's son of Tuthmosis I. Temp. Tuthmosis I."
            " (CHAMPOLLION, No. 30, L. D. Text, No. 75.) Parents, Senidhout and"
            " Takhrod. Wife, Renay.",
        ("TT346", "notes_from_pm"):
            "Overseer of the women of the royal harim of the divine adoratress"
            " Tentōpet, temp. Ramesses IV. Probably usurped from Penrēʿ, Chief of"
            " Mezay, Overseer of the Lands of Syria (name on cones in Pit in Court),"
            " [temp. Ramesses II].",
        # Chunk 44 (TT351–TT360) — 1 tie-break override.
        # TT354 notes_from_pm: 1/1/1 split on all-caps vs title-case for inline
        #   `Perhaps AMENEMḤET` name + C truncated `(tomb 340, ...)` parenthetical.
        #   Pin B's mixed-case form with full parenthetical; PDF p.418 confirms full
        #   text. No DERIVER_OVERRIDE: `Perhaps` correctly fires uncertain on primary
        #   attribution. TT354 shared_with_tombs=["TT340"] is correct (B+C majority,
        #   accepted as-is): PM phrases the cross-tomb relationship in TT354 via
        #   `Perhaps AMENEMḤET (tomb 340, ...)` and reciprocally in TT340 via
        #   `(perhaps also owner of tomb 354)` — same person proposed for both tombs,
        #   bidirectional cross-tomb-identity reference. Symmetry with TT340.shared_with_tombs=["TT354"]
        #   (landed chunk-42).
        ("TT354", "notes_from_pm"):
            "No texts. Perhaps Amenemḥet (tomb 340, cf. box-lid in Finds of this"
            " tomb). Early Dyn. XVIII.",
        # Chunk 45 (TT361–TT370) — 2 tie-break overrides.
        # TT362 notes_from_pm: 1/1/1 split on wab-priest romanisation:
        #   A=`Wab-priest` (capitalised W, ayin dropped); B=`waʿb-priest`
        #   (ayin after a); C=`wʿb-priest` (ayin present, medial-a dropped).
        #   Pin `wʿab-priest` per the bar-a-as-ayin-before-a convention from
        #   TT14/TT97/TT100 overrides. CHUNK45_CORRECTIONS then restores
        #   PM diacritics on TT366+TT369; no CHUNK45_CORRECTIONS on TT362
        #   (the wʿab form is the merge-time final form, no post-merge diacritic).
        ("TT362", "notes_from_pm"):
            "wʿab-priest of Amūn. Late Dyn. XIX. Wife, Ḥatḥor.",
        # TT368 notes_from_pm: 1/1/1 split on `called Ḥuy` prefix:
        #   A=`Called Ḥuy,...` (capitalised C — wrong, mid-sentence position);
        #   B=`called Ḥuy,...` (lowercase c — verbatim PM p.431);
        #   C dropped `called Ḥuy,` entirely (substantive omission).
        #   Pin agent B; lowercase per PM printed page.
        ("TT368", "notes_from_pm"):
            "called Ḥuy, Overseer of sculptors of Amūn in the Southern City."
            " Late Dyn. XVIII. Parents, Ḥati, Overseer of sculptors of the"
            " Lord of the Two Lands, and Ipy. Wife, Mery[mut].",
        # TT381 notes_from_pm: 1/1/1 split on statue-sentence inclusion and
        #   CAPS on AMENEMONET. A=complete with statue sentence + CAPS;
        #   B=truncated + lowercase; C=truncated + CAPS. Pin A's complete form
        #   (verbatim-preserve: statue sentence is PM body content, not a
        #   citation ribbon). Macron stripped per OCR source (no macron visible).
        ("TT381", "notes_from_pm"):
            "Uninscribed. Perhaps AMENEMONET, Messenger of the King to every"
            " land. Ramesside. Headless statue of Amenemonet.",
        # TT386 notes_from_pm: 1/1/1 split on parenthetical inclusion and
        #   Wilkinson site-name spelling. A=Mináfed (accent); B=dropped
        #   parenthetical; C=Mimifed (matches OCR source). Pin C's Mimifed
        #   form + A+C's parenthetical inclusion.
        ("TT386", "notes_from_pm"):
            "Chancellor of the King of Lower Egypt, Overseer of soldiers."
            " Middle Kingdom. (WILKINSON, 'Bab om el Mimifed',"
            " Bibl. i, 1st ed. p. 190, bb.)",
        # TT389 notes_from_pm: 1/1/1 split on OCR-garbled priest-title cluster.
        #   A=smtj/ḥsk+Amenemōnet (PDF-faithful); B=snwḥ/ḥrk+Amenemonet;
        #   C=sm/ḥrk+Amenemonet. Merge picked B+C 2/1 majority, but PDF p.440
        #   confirms agent A was correct. Pinned post-CHUNK47_CORRECTIONS:
        #   `smtj-priest, ..., ḥsk-priest, ..., Amenemōnet, ...` per PDF
        #   p.440 direct read (post-reconciliation-agent SUBSTANTIVE FLAG).
        ("TT389", "notes_from_pm"):
            "smtj-priest, Chamberlain of Min, ḥsk-priest, Mayor of the"
            " Southern City. Saite. (CHAMPOLLION, No. 57, L. D. Text, No. 28,"
            " Bibl. i, 1st ed. p. 190, cc.) Parents, Amenemōnet, Prophet of"
            " Min, and Neferuneit. Wives, Tahert and Beteb.",
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


# === Chunk-37 per-row pins (TT281-TT290) ============================
# Rule 5: every row asserts all key fields. All values are post-fix-rows
# final state (after CHUNK37_CORRECTIONS and DERIVER_OVERRIDES applied).


def test_chunk47_row_count(reconciled):
    """Merged total should be 465 after chunk 47 (+10 from chunk-46's 455)."""
    assert len(reconciled) == 465


def test_tt281_unfinished_temple(reconciled):
    """TT281: Unfinished Temple of Mentuḥotp-Sʿankhkareʿ (King).
    Special row — not a private tomb; is_unfinished=True; no theban_area."""
    r = _row(reconciled, "TT281")
    assert r["occupant_name"] == "Mentuhotp-Sʿankhkareʿ"
    assert r["occupant_role"] == "King"
    assert r["is_unfinished"] is True
    assert r["is_usurped"] is False
    assert r["theban_area"] is None
    assert r["notes_from_pm"] == (
        "Unfinished Temple of Mentuḥotp-Sʿankhkareʿ. See Bibl. ii, p. 135."
    )
    assert r["source_citation"]["page"] == 364
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []


def test_tt282_nakht(reconciled):
    """TT282: Nakht, Head of bowmen, Overseer of the South Lands. Ramesside.
    Dra' Abu el-Naga'."""
    r = _row(reconciled, "TT282")
    assert r["occupant_name"] == "Nakht"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["is_usurped"] is False
    assert r["is_unfinished"] is False
    assert r["notes_from_pm"] == "Head of bowmen, Overseer of the South Lands. Ramesside."
    assert r["source_citation"]["page"] == 364
    assert r["occupant_alt_names"] == []


def test_tt283_roma(reconciled):
    """TT283: Roma (Roy), First prophet of Amūn. Alt-name Roy; wife Tamut
    named in niche in Court. Tie-breaks on co_occupants and notes_from_pm."""
    r = _row(reconciled, "TT283")
    assert r["occupant_name"] == "Roma"
    assert r["occupant_alt_names"] == ["Roy"]
    assert r["occupant_role"] == "High Priest"
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["is_usurped"] is False
    assert r["co_occupants"] == []
    assert r["notes_from_pm"] == (
        "First prophet of Amūn. Temp. Ramesses II to Sethos II. "
        "Wife, Tamut. (name in niche in Court)."
    )
    assert r["source_citation"]["page"] == 365


def test_tt284_paiemneter_reused(reconciled):
    """TT284: Paijemneter. PM marks (Reused.) — is_usurped=True via
    DERIVER_OVERRIDE (deriver regex misses 'Reused' lexical form)."""
    r = _row(reconciled, "TT284")
    assert r["occupant_name"] == "Paijemneter"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["is_usurped"] is True
    assert r["notes_from_pm"] == (
        "Scribe of the offerings of all the gods. Ramesside. (Reused.) "
        "Father, Raʿy. Wife, Bek(et)werner."
    )
    assert r["source_citation"]["page"] == 366


def test_tt285_iny(reconciled):
    """TT285: Iny, Head of the magazine of Mut. Ramesside."""
    r = _row(reconciled, "TT285")
    assert r["occupant_name"] == "Iny"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["is_usurped"] is False
    assert r["co_occupants"] == []
    assert r["notes_from_pm"] == (
        "Head of the magazine of Mut. Ramesside. Wife, Tentonet, Songstress of Mut."
    )
    assert r["source_citation"]["page"] == 367


def test_tt286_niay(reconciled):
    """TT286: Niay, Scribe of the table. Ramesside."""
    r = _row(reconciled, "TT286")
    assert r["occupant_name"] == "Niay"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["is_usurped"] is False
    assert r["notes_from_pm"] == (
        "Scribe of the table. Ramesside. Parents, Roro and Esi. Wife, Tabes."
    )
    assert r["source_citation"]["page"] == 368


def test_tt287_pendu(reconciled):
    """TT287: Pendu, Wab-priest of Amūn (macron restored). Ramesside."""
    r = _row(reconciled, "TT287")
    assert r["occupant_name"] == "Pendu"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["is_usurped"] is False
    assert r["notes_from_pm"] == "Wab-priest of Amūn. Ramesside."
    assert r["source_citation"]["page"] == 369


def test_tt288_bekenkhons_reused(reconciled):
    """TT288: Bekenkhons, re-used by Setau (TT289). is_usurped=True via
    DERIVER_OVERRIDE; shared_with_tombs=[TT289] from B+C majority."""
    r = _row(reconciled, "TT288")
    assert r["occupant_name"] == "Bekenkhons"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["is_usurped"] is True
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == (
        "Scribe of the divine book of Khons. Ramesside. Re-used by Setau (tomb 289)."
    )
    assert r["source_citation"]["page"] == 369


def test_tt289_setau(reconciled):
    """TT289: Setau, Viceroy of Kush. Tie-break on notes_from_pm for
    harin/harem and punctuation."""
    r = _row(reconciled, "TT289")
    assert r["occupant_name"] == "Setau"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["is_usurped"] is False
    assert r["notes_from_pm"] == (
        "Viceroy of Kush, Overseer of the South Lands. Temp. Ramesses II. "
        "Father, Siwazyt. Wife, Nefertmut, Chief of the harin of Nekhbet."
    )
    assert r["source_citation"]["page"] == 369


def test_tt290_irinufer(reconciled):
    """TT290: Irinufer (not 'Irinofer' — OCR !RINUFER corrected by
    CHUNK37_CORRECTIONS). Deir el-Medina. Wife name unclear in OCR;
    EGYPTOLOGIST REVIEW REQUIRED."""
    r = _row(reconciled, "TT290")
    assert r["occupant_name"] == "Irinufer"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "Deir el-Medina"
    assert r["is_usurped"] is False
    assert "Tausert Meḥytkhacti" in r["notes_from_pm"]
    assert "Amūn" in r["notes_from_pm"]
    assert "[name unclear in source]" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 372


# === Chunk-38 per-row pins (TT291-TT300) ====================================
# Rule 5: every row asserts all key fields. All values are post-fix-rows
# final state (after CHUNK38_CORRECTIONS and DERIVER_OVERRIDES applied).


def test_tt291_nu_nekhtmin_joint(reconciled):
    """TT291: Nu + Nekhtmin, joint burial. Third joint burial in source.
    DERIVER_OVERRIDE: is_joint_burial=True (no auto-deriver for this field)."""
    r = _row(reconciled, "TT291")
    assert r["occupant_name"] == "Nu"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "Deir el-Medina"
    assert r["is_joint_burial"] is True
    assert r["is_usurped"] is False
    assert r["is_unfinished"] is False
    assert len(r["co_occupants"]) == 1
    assert r["co_occupants"][0]["name"] == "Nekhtmin"
    assert r["shared_with_tombs"] == []
    assert "Nekhtmin" in r["notes_from_pm"]
    assert "Min-hotep" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 374


def test_tt292_peshedu(reconciled):
    """TT292: Peshedu, Servant in the Place of Truth. Father Ḥenekhu.
    CHUNK38_CORRECTIONS: He-nekhu → Ḥenekhu (underdot-Ḥ restored).
    EGYPTOLOGIST REVIEW REQUIRED for exact printed form."""
    r = _row(reconciled, "TT292")
    assert r["occupant_name"] == "Peshedu"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "Deir el-Medina"
    assert r["is_usurped"] is False
    assert "Ḥenekhu" in r["notes_from_pm"]
    assert "Brit. Mus. 262" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 375


def test_tt293_ramessesnakht(reconciled):
    """TT293: Raʿmessenakht, First Prophet of Amun. Ayin retained in name.
    Tie-break: B's `Raʿmessenakht` (source `RA<MESSENAKHT`, `<`=ayin)."""
    r = _row(reconciled, "TT293")
    assert r["occupant_name"] == "Raʿmessenakht"
    assert r["occupant_role"] == "High Priest"
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["is_usurped"] is False
    assert "Merubaste" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 376


def test_tt294_amenhotep_usurped(reconciled):
    """TT294: Amenhotep (original), usurped by Roma. Unfinished. Khokha.
    is_usurped=True: auto-detected by deriver (`\\busurped\\b` in notes).
    co_occupants=[]: Roma captured in notes_from_pm only (usurper, not co-owner).
    Usurpation direction: Amenhotep is the original occupant."""
    r = _row(reconciled, "TT294")
    assert r["occupant_name"] == "Amenhotep"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "Khokha"
    assert r["is_usurped"] is True
    assert r["is_unfinished"] is True
    assert r["co_occupants"] == []
    assert "Usurped by Roma" in r["notes_from_pm"]
    assert "Hathor" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 376


def test_tt295_dhutmosi_paroy(reconciled):
    """TT295: Ḏhutmosi called Paroy. D-bar via CHUNK38_CORRECTIONS.
    DERIVER_OVERRIDE: attribution_certainty=attested (regnal-date `(?)`)."""
    r = _row(reconciled, "TT295")
    assert r["occupant_name"] == "Ḏhutmosi"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "Khokha"
    assert r["occupant_alt_names"] == ["Paroy"]
    assert r["tomb_aliases"] == []
    assert r["attribution_certainty"] == "attested"
    assert r["is_usurped"] is False
    assert "Senemiʿoḥ" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 377


def test_tt296_nefersekheru(reconciled):
    """TT296: Nefersekheru, Scribe. Wife Maʿetmut (ayin via CHUNK38_CORRECTIONS).
    Source `Ma<etmut`, `<`=ayin; majority had `Maetmut`."""
    r = _row(reconciled, "TT296")
    assert r["occupant_name"] == "Nefersekheru"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "Khokha"
    assert r["is_usurped"] is False
    assert "Maʿetmut" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 378


def test_tt297_amenemopet_thonufer(reconciled):
    """TT297: Amenemopet called Thonufer. Alt name Thonufer in occupant_alt_names."""
    r = _row(reconciled, "TT297")
    assert r["occupant_name"] == "Amenemopet"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "ʿAsâsîf"
    assert r["occupant_alt_names"] == ["Thonufer"]
    assert r["is_usurped"] is False
    assert "Counter of grain of Amun" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 379


def test_tt298_baki_unnufer(reconciled):
    """TT298: Baki + father (probably) Unnufer. NOT a joint burial.
    DERIVER_OVERRIDE: attribution_certainty=attested (`(probably)` qualifies
    father, not Baki's identity)."""
    r = _row(reconciled, "TT298")
    assert r["occupant_name"] == "Baki"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "Deir el-Medina"
    assert r["is_joint_burial"] is False
    assert r["attribution_certainty"] == "attested"
    assert len(r["co_occupants"]) == 1
    assert r["co_occupants"][0]["name"] == "Unnufer"
    assert "Taysen" in r["notes_from_pm"]
    assert "tomb 213" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 379


def test_tt299_iniherkhac(reconciled):
    """TT299: Iniherkhac (A's form; source `INI;IERKHAC]`, I;I=Ḥ stripped).
    Also owner of TT359 → shared_with_tombs=["TT359"]."""
    r = _row(reconciled, "TT299")
    assert r["occupant_name"] == "Iniherkhac"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "Deir el-Medina"
    assert r["shared_with_tombs"] == ["TT359"]
    assert r["is_usurped"] is False
    assert "Hay" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 380


def test_tt300_anhotp(reconciled):
    """TT300: ʿAnhotp (B's form; source `cANI;IOTP`: c=ayin, I;I=Ḥ stripped).
    A had `Amenhotep` (wrong name); C had `Canihotep` (OCR-literal)."""
    r = _row(reconciled, "TT300")
    assert r["occupant_name"] == "ʿAnhotp"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["is_usurped"] is False
    assert "Viceroy of Kush" in r["notes_from_pm"]
    assert "Hunuro" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 381


# ===== Chunk 39 (TT301–TT310) ============================================


def test_tt301_hori(reconciled):
    """TT301 — Hori, Scribe. Dra' Abu el-Naga. p.381.

    Name: source `I;IORI` = Ḥori; strip-ḥ → `Hori` (tie-break + CHUNK39
    correction from majority `Khori`). GREENLEES note in notes_from_pm.
    Wife cartouche-named (name illegible per PM).
    EGYPTOLOGIST REVIEW REQUIRED: confirm Hori vs Khori.
    """
    r = _row(reconciled, "TT301")
    assert r["occupant_name"] == "Hori"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Scribe of the table of the Lord of the Two Lands" in r["notes_from_pm"]
    assert "Ramesside" in r["notes_from_pm"]
    assert "GREENLEES" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 381


def test_tt302_paraemhab(reconciled):
    """TT302 — Paraʿemhab, Overseer of the magazine. Dra' Abu el-Naga. p.381.

    Name: source `PARA<EMI;IAB` → `Paraʿemhab` (ayin retained, ḥ stripped via
    CHUNK39_CORRECTIONS). Father: `Userḥat` (underdot-ḥ restored in
    notes_from_pm per verbatim-preserve).
    EGYPTOLOGIST REVIEW REQUIRED: confirm father-name diacritics.
    """
    r = _row(reconciled, "TT302")
    assert r["occupant_name"] == "Paraʿemhab"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Overseer of the magazine" in r["notes_from_pm"]
    assert "Ramesside" in r["notes_from_pm"]
    assert "Userḥat" in r["notes_from_pm"]
    assert "GREENLEES" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 381


def test_tt303_paser_third_prophet(reconciled):
    """TT303 — Paser, Third prophet + Head of magazine of Amun. Dra' Abu el-Naga. p.381.

    Role: `Official` (NOT `High Priest`). High Priest reserved for First prophet
    of Amūn only (TT35/TT67/TT86/TT95 precedent). Third prophet → Official.
    Majority A+C incorrectly voted `High Priest`; corrected by CHUNK39_CORRECTIONS.
    """
    r = _row(reconciled, "TT303")
    assert r["occupant_name"] == "Paser"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Third prophet of Amun" in r["notes_from_pm"]
    assert "magazine" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 381


def test_tt304_piay(reconciled):
    """TT304 — Piay, Scribe of the table. Dra' Abu el-Naga. p.383.

    Tie-break pinned B's form (no parentheses on cross-reference clause).
    Source line 183: `For position, see p. 356.` — verbatim, no parens.
    """
    r = _row(reconciled, "TT304")
    assert r["occupant_name"] == "Piay"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Scribe of the table of Amun" in r["notes_from_pm"]
    assert "Ramesside" in r["notes_from_pm"]
    assert "p. 356" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 383


def test_tt305_paser_waab(reconciled):
    """TT305 — Paser, Wʿab-priest. Wife Tamelḥit. Dra' Abu el-Naga. p.383.

    ayin restored in priest title (source `warb-priest` = wʿab-priest).
    Wife: `Tamelḥit` in notes; `Tamelhit` in co_occupants.name (strip-ḥ).
    EGYPTOLOGIST REVIEW REQUIRED: wife-name diacritics.
    """
    r = _row(reconciled, "TT305")
    assert r["occupant_name"] == "Paser"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert len(r["co_occupants"]) == 1
    co = r["co_occupants"][0]
    assert co["name"] == "Tamelhit"
    assert co["role"] == "Unknown"
    assert co["alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Wʿab-priest" in r["notes_from_pm"]
    assert "Tamelḥit" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 383


def test_tt306_irzanen(reconciled):
    """TT306 — Irzanen, Door-opener. Wife Mutenopet. Dra' Abu el-Naga. p.384.

    Name: source `lRZANEN` (l=OCR for I) → `Irzanen` (tie-break pinned A; C had
    Cyrillic contamination). GREENLEES note from headword preserved.
    EGYPTOLOGIST REVIEW REQUIRED: confirm Irzanen vs Irzana.
    """
    r = _row(reconciled, "TT306")
    assert r["occupant_name"] == "Irzanen"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert len(r["co_occupants"]) == 1
    co = r["co_occupants"][0]
    assert co["name"] == "Mutenopet"
    assert co["role"] == "Unknown"
    assert co["alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Door-opener of the estate of Amun" in r["notes_from_pm"]
    assert "Mutenopet" in r["notes_from_pm"]
    assert "GREENLEES" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 384


def test_tt307_thonufer_unfinished(reconciled):
    """TT307 — Thonufer. Dra' Abu el-Naga. p.385. Unfinished.

    is_unfinished=True (PM literal `(Unfinished.)`). Name from ushabti.
    GREENLEES note from headword. Parenthesised `(Unfinished.)` per source.
    """
    r = _row(reconciled, "TT307")
    assert r["occupant_name"] == "Thonufer"
    assert r["occupant_role"] is None
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is True
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "name from ushabti" in r["notes_from_pm"]
    assert "(Unfinished.)" in r["notes_from_pm"]
    assert "GREENLEES" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 385


def test_tt308_kemsit_royal_concubine(reconciled):
    """TT308 — Kemsit, Unique royal concubine + Prophetess of Ḥatḥor. Deir el-Bahari. p.385.

    First Deir el-Bahari primary theban_area row. Temp. Mentuḥotp (Nebḥepetreʿ).
    location_sub_area = `In the Temple of Mentuḥotp`. Notes include NAVILLE ref
    and temple location. Diacritics: Ḥatḥor, Mentuḥotp, Nebḥepetreʿ.
    EGYPTOLOGIST REVIEW REQUIRED: confirm all diacritics.
    """
    r = _row(reconciled, "TT308")
    assert r["occupant_name"] == "Kemsit"
    assert r["occupant_role"] == "Royal Family"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] == "In the Temple of Mentuḥotp"
    assert "royal concubine" in r["notes_from_pm"]
    assert "Ḥatḥor" in r["notes_from_pm"]
    assert "Mentuḥotp" in r["notes_from_pm"]
    assert "Nebḥepetreʿ" in r["notes_from_pm"]
    assert "NAVILLE" in r["notes_from_pm"]
    assert "Deir el-Bahari" in r["notes_from_pm"]
    assert r["theban_area"] == "Deir el-Bahari"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 385


def test_tt309_anonymous_blocked(reconciled):
    """TT309 — Name unknown. Sh. ʿAbd el-Qurna. p.386. Blocked.

    Anonymous occupant: occupant_name=None, occupant_role=None (sentinel-null).
    (Blocked.) in notes_from_pm per PM.
    """
    r = _row(reconciled, "TT309")
    assert r["occupant_name"] is None
    assert r["occupant_role"] is None
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Name unknown" in r["notes_from_pm"]
    assert "(Blocked.)" in r["notes_from_pm"]
    assert r["theban_area"] == "Sh. ʿAbd el-Qurna"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 386


def test_tt310_anonymous_chancellor(reconciled):
    """TT310 — A Chancellor of the King of Lower Egypt. Deir el-Bahari. p.386.

    Second Deir el-Bahari primary theban_area row. Anonymous chancellor: Dyn. XI.
    occupant_name=None, occupant_role=None (sentinel-null normalization from `Unknown`).
    """
    r = _row(reconciled, "TT310")
    assert r["occupant_name"] is None
    assert r["occupant_role"] is None
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Chancellor" in r["notes_from_pm"]
    assert r["theban_area"] == "Deir el-Bahari"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 386


# ===== Chunk 40 (TT311–TT320) ============================================


def test_tt311_khety_deir_el_bahari(reconciled):
    """TT311 — Khety, Seal-bearer. Deir el-Bahari. p.386. Temp. Mentuḥotp-Nebḥepetreʿ.

    First Dyn. XI Mentuhotep-era cluster row. Diacritic restore by CHUNK40.
    EGYPTOLOGIST REVIEW REQUIRED: confirm Mentuhotep diacritics.
    """
    r = _row(reconciled, "TT311")
    assert r["occupant_name"] == "Khety"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Seal-bearer" in r["notes_from_pm"]
    assert "Mentuḥotp-Nebḥepetreʿ" in r["notes_from_pm"]
    assert r["theban_area"] == "Deir el-Bahari"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 386


def test_tt312_espelaashuti_vizier(reconciled):
    """TT312 — Espel(a)shuti, Vizier. Deir el-Bahari. p.387. Saite.

    Parenthetical-preserve in occupant_name per reconciled precedents.
    In court of a Dyn. XI tomb. Mother, Irterau (tomb 390).
    """
    r = _row(reconciled, "TT312")
    assert r["occupant_name"] == "Espel(a)shuti"
    assert r["occupant_role"] == "Vizier"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Vizier" in r["notes_from_pm"]
    assert "Saite" in r["notes_from_pm"]
    assert "Irterau" in r["notes_from_pm"]
    assert r["theban_area"] == "Deir el-Bahari"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 387


def test_tt313_henenu_great_steward(reconciled):
    """TT313 — Henenu, Great steward. Deir el-Bahari. p.388. Dyn. XI two-king tenure.

    Diacritic restore by CHUNK40: Mentuḥotp-Nebḥepetreʿ and Mentuḥotp-Sʿankhkareʿ.
    EGYPTOLOGIST REVIEW REQUIRED: confirm all diacritics.
    """
    r = _row(reconciled, "TT313")
    assert r["occupant_name"] == "Henenu"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Great steward" in r["notes_from_pm"]
    assert "Mentuḥotp-Nebḥepetreʿ" in r["notes_from_pm"]
    assert "Sʿankhkareʿ" in r["notes_from_pm"]
    assert r["theban_area"] == "Deir el-Bahari"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 388


def test_tt314_harhotep_dyn_xi(reconciled):
    """TT314 — Harhotep, Seal-bearer. Deir el-Bahari. p.389. Dyn. XI.

    dynasty=XI restored by CHUNK40 (merge majority B+C=null miss; source explicit).
    Mother, Sentshe.
    """
    r = _row(reconciled, "TT314")
    assert r["occupant_name"] == "Harhotep"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Seal-bearer" in r["notes_from_pm"]
    assert "Dyn. XI" in r["notes_from_pm"]
    assert "Sentshe" in r["notes_from_pm"]
    assert r["theban_area"] == "Deir el-Bahari"
    assert r["dynasty"] == "XI"
    assert r["source_citation"]["page"] == 389


def test_tt315_ipi_vizier(reconciled):
    """TT315 — Ipi, Vizier. Deir el-Bahari. p.389. Temp. Mentuḥotp-Nebḥepetreʿ.

    Second Vizier of the Mentuhotep cluster (TT312 Espel(a)shuti is Saite).
    Diacritic restore by CHUNK40.
    EGYPTOLOGIST REVIEW REQUIRED: confirm diacritics.
    """
    r = _row(reconciled, "TT315")
    assert r["occupant_name"] == "Ipi"
    assert r["occupant_role"] == "Vizier"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Vizier" in r["notes_from_pm"]
    assert "Mentuḥotp-Nebḥepetreʿ" in r["notes_from_pm"]
    assert r["theban_area"] == "Deir el-Bahari"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 389


def test_tt316_neferhotep_custodian_dyn_xi(reconciled):
    """TT316 — Neferhotep, Custodian of the bow. Deir el-Bahari. p.390. Dyn. XI.

    dynasty=XI restored by CHUNK40 (merge majority null miss; source explicit).
    Wife(?), Mery(t) — DERIVER_OVERRIDE: (?) qualifies wife relationship, not
    primary occupant attribution. attribution_certainty=attested.
    """
    r = _row(reconciled, "TT316")
    assert r["occupant_name"] == "Neferhotep"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Custodian of the bow" in r["notes_from_pm"]
    assert "Dyn. XI" in r["notes_from_pm"]
    assert "Nebtiotef" in r["notes_from_pm"]
    assert "Mery(t)" in r["notes_from_pm"]
    assert r["theban_area"] == "Deir el-Bahari"
    assert r["dynasty"] == "XI"
    assert r["source_citation"]["page"] == 390


def test_tt317_dhutnufer_sh_abd_el_qurna(reconciled):
    """TT317 — Ḏhutnufer, Scribe. Sh. ʿAbd el-Qurna. p.390.

    d-bar Ḏ restored by CHUNK40. CHAMPOLLION No. 25 before Parents per PM order.
    DERIVER_OVERRIDE: (?) qualifies regnal date (Tuthmosis III), not occupant identity.
    attribution_certainty=attested.
    EGYPTOLOGIST REVIEW REQUIRED: confirm d-bar from PM I.1 p.390 printed source.
    """
    r = _row(reconciled, "TT317")
    assert r["occupant_name"] == "Ḏhutnufer"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Scribe of the counting of corn" in r["notes_from_pm"]
    assert "(CHAMPOLLION, No. 25.)" in r["notes_from_pm"]
    assert "Parents, Senires" in r["notes_from_pm"]
    assert "Titau" in r["notes_from_pm"]
    assert r["theban_area"] == "Sh. ʿAbd el-Qurna"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 390


def test_tt318_amenmosi_sh_abd_el_qurna(reconciled):
    """TT318 — Amenmosi, Necropolis-stonemason of Amun. Sh. ʿAbd el-Qurna. p.391.

    CHAMPOLLION No. 26 before Wife per PM source order.
    DERIVER_OVERRIDE: (?) qualifies regnal-range tail (Hatshepsut), not occupant identity.
    attribution_certainty=attested.
    """
    r = _row(reconciled, "TT318")
    assert r["occupant_name"] == "Amenmosi"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Necropolis-stonemason" in r["notes_from_pm"]
    assert "(CHAMPOLLION, No. 26.)" in r["notes_from_pm"]
    assert "Henut" in r["notes_from_pm"]
    assert r["theban_area"] == "Sh. ʿAbd el-Qurna"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 391


def test_tt319_nofru_royal_family(reconciled):
    """TT319 — Nofru, daughter of Mentuḥotp-Sʿankhibtaui, wife of Mentuḥotp-Nebḥepetreʿ.

    King's daughter (Royal Family). Deir el-Bahari in Temple of Ḥatshepsut. p.391.
    Mother Iʿob restored by CHUNK40. Father epithet Sʿankhibtaui restored (ayin+i).
    EGYPTOLOGIST REVIEW REQUIRED: confirm all diacritics.
    """
    r = _row(reconciled, "TT319")
    assert r["occupant_name"] == "Nofru"
    assert r["occupant_role"] == "Royal Family"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Sʿankhibtaui" in r["notes_from_pm"]
    assert "Iʿob" in r["notes_from_pm"]
    assert "Nebḥepetreʿ" in r["notes_from_pm"]
    assert r["theban_area"] == "Deir el-Bahari"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 391


def test_tt320_inhapi_royal_cache(reconciled):
    """TT320 — Inhaʿpi, perhaps wife of Amosis. Royal Cache, Dyn. XXI. Deir el-Bahari. p.392.

    Royal Family; dynasty=XXI restored by CHUNK40 (merge majority null miss).
    occupant_name ayin restored to Inhaʿpi by CHUNK40.
    DERIVER_OVERRIDE: `perhaps` qualifies spousal relationship, not primary occupant identity.
    attribution_certainty=attested.
    EGYPTOLOGIST REVIEW REQUIRED: confirm occupant_name form from PM I.1 p.392.
    """
    r = _row(reconciled, "TT320")
    assert r["occupant_name"] == "Inhaʿpi"
    assert r["occupant_role"] == "Royal Family"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Perhaps wife of Amosis" in r["notes_from_pm"]
    assert "Royal Cache" in r["notes_from_pm"]
    assert "Dyn. XXI" in r["notes_from_pm"]
    assert "i 2" in r["notes_from_pm"]
    assert r["theban_area"] == "Deir el-Bahari"
    assert r["dynasty"] == "XXI"
    assert r["source_citation"]["page"] == 392


# === Chunk-42 per-row pins (TT331-TT340) =====================================
# Rule 5: every row asserts all key fields. All values are post-fix-rows
# final state (after CHUNK42_CORRECTIONS and DERIVER_OVERRIDES applied).


def test_tt331_penne_chief_prophet_monthu(reconciled):
    """TT331: Penne, Chief prophet of Monthu. Sh. 'Abd el-Qurna. p.399.

    Tie-break: notes_from_pm (3-way split; A/B hallucinated L.D.Text 105 from TT335).
    CHUNK42_CORRECTIONS: Hatiay → Ḥatiay (underdot-Ḥ restored from source I:Iatiay);
    shared_with_tombs=[TT324] (symmetry with TT324.shared_with_tombs=[TT331]).
    EGYPTOLOGIST REVIEW REQUIRED: confirm Ḥatiay from PM I.1 p.399.
    """
    r = _row(reconciled, "TT331")
    assert r["occupant_name"] == "Penne"
    assert r["occupant_role"] == "High Priest"
    assert r["attribution_certainty"] == "attested"
    assert r["theban_area"] == "Sh. ʿAbd el-Qurna"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == ["TT324"]
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Ḥatiay" in r["notes_from_pm"]
    assert "Chief of the harim of Monthu" in r["notes_from_pm"]
    assert "Ramesside" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 399


def test_tt332_penernutet_granary_watchman(reconciled):
    """TT332: Penernutet, Chief watchman granary estate of Amun. Dra' Abu el-Naga. p.399.

    CHUNK42_CORRECTIONS: majority-wrong page 400 → 399 (source line 34 in printed-399 block).
    """
    r = _row(reconciled, "TT332")
    assert r["occupant_name"] == "Penernutet"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Chief watchman" in r["notes_from_pm"]
    assert "Ramesside" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 399


def test_tt333_anonymous_amenophis_iii(reconciled):
    """TT333: Anonymous, name lost. Dra' Abu el-Naga. p.399.

    Tie-break: source_citation 3-way 400/401/399 → 399 (C correct, per page-break).
    attribution_certainty=uncertain (name lost, temp date hedged with (?)).
    """
    r = _row(reconciled, "TT333")
    assert r["occupant_name"] is None
    assert r["occupant_role"] == "Unknown"
    assert r["attribution_certainty"] == "uncertain"
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Name lost" in r["notes_from_pm"]
    assert "Amenophis III" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 399


def test_tt334_anonymous_chief_husbandmen(reconciled):
    """TT334: Anonymous, A Chief of husbandmen. Dra' Abu el-Naga. p.401.

    attribution_certainty=uncertain ((?)-hedged temp date).
    """
    r = _row(reconciled, "TT334")
    assert r["occupant_name"] is None
    assert r["occupant_role"] == "Unknown"
    assert r["attribution_certainty"] == "uncertain"
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Chief of husbandmen" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 401


def test_tt335_nekhtamun_warb_priest(reconciled):
    """TT335: Nekhtamun, warb-priest of Amenophis I. Deir el-Medina. p.401.

    Tie-break: notes_from_pm (3-way split on capitalization, (I) parens, L.D.Text placement).
    CHUNK42_CORRECTIONS: majority-wrong page 402 → 401; spurious co_occupant [] removed;
    shared_with_tombs=[TT336] (symmetry with TT336.shared_with_tombs=[TT335]).
    is_unfinished=True (A+C majority, from source items (1)-(2) unfinished).
    """
    r = _row(reconciled, "TT335")
    assert r["occupant_name"] == "Nekhtamun"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["theban_area"] == "Deir el-Medina"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == ["TT336"]
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is True
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Warb-priest" in r["notes_from_pm"]
    assert "Amenophis (I)" in r["notes_from_pm"]
    assert "L. D. Text, No. 105." in r["notes_from_pm"]
    assert "Nefertkha" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 401


def test_tt336_neferronpet_brother_tt335(reconciled):
    """TT336: Neferronpet, Servant in the Place of Truth. Brother of TT335 Nekhtamun.
    Deir el-Medina. p.404."""
    r = _row(reconciled, "TT336")
    assert r["occupant_name"] == "Neferronpet"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["theban_area"] == "Deir el-Medina"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == ["TT335"]
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Huynefert" in r["notes_from_pm"]
    assert "tomb 335" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 404


def test_tt337_ken_usurped_by_eskhons(reconciled):
    """TT337: Ken, Chiseller in Place of Truth. Usurped BY Eskhons (victim direction).
    Deir el-Medina. p.405. is_usurped=True via deriver.
    CHUNK42_CORRECTIONS: shared_with_tombs=[TT4] (symmetry with TT4.shared_with_tombs=[TT337]).
    """
    r = _row(reconciled, "TT337")
    assert r["occupant_name"] == "Ken"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["theban_area"] == "Deir el-Medina"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == ["TT4"]
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is True
    assert r["location_sub_area"] is None
    assert "Eskhons" in r["notes_from_pm"]
    assert "Usurped by" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 405


def test_tt338_may_outline_draughtsman(reconciled):
    """TT338: May, Outline-draughtsman of Amun. Deir el-Medina. p.406.
    Short notes (majority A+C correctly omit bibliography appendage from B)."""
    r = _row(reconciled, "TT338")
    assert r["occupant_name"] == "May"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["theban_area"] == "Deir el-Medina"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Outline-draughtsman" in r["notes_from_pm"]
    assert "Tamyt" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 406


def test_tt339_huy_peshedu_joint_burial(reconciled):
    """TT339: Huy + Peshedu, FIFTH joint burial in PM I.1. Deir el-Medina. p.406.

    Tie-break: notes_from_pm (3-way: A omits Peshedu title, B includes it, C uses name prefixes).
    CHUNK42_CORRECTIONS: page 407 → 406 (unanimous-wrong); co_occupant name Peshedu restored.
    is_joint_burial=True (all 3 agents agreed).
    """
    r = _row(reconciled, "TT339")
    assert r["occupant_name"] == "Huy"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["theban_area"] == "Deir el-Medina"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["is_joint_burial"] is True
    assert len(r["co_occupants"]) == 1
    assert r["co_occupants"][0]["name"] == "Peshedu"
    assert r["co_occupants"][0]["role"] == "Official"
    assert r["shared_with_tombs"] == []
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "Peshedu" in r["notes_from_pm"]
    assert "Servant in the Place of Truth" in r["notes_from_pm"]
    assert "Necropolis-stonemason" in r["notes_from_pm"]
    assert "Nefer[t]iyti" in r["notes_from_pm"]
    assert "Harmosi" in r["notes_from_pm"]
    assert "Takharu" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 406


def test_tt340_amenemhet_perhaps_tt354(reconciled):
    """TT340: Amenemhet, Servant in Place of Truth. Deir el-Medina. p.407.

    Tie-break: notes_from_pm (3-way on parent name Macenhmut/Macenhumt/Macenhmy).
    DERIVER_OVERRIDE: `perhaps` qualifies TT354 secondary ownership, not primary identity
    → attribution_certainty=attested (majority A+B=probable was wrong).
    is_unfinished=True (A+C majority; source items (2)-(3) explicitly marked unfinished).
    EGYPTOLOGIST REVIEW REQUIRED: confirm parent name Macenhmut from PM I.1 p.408.
    """
    r = _row(reconciled, "TT340")
    assert r["occupant_name"] == "Amenemhet"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["theban_area"] == "Deir el-Medina"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == ["TT354"]
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is True
    assert r["is_usurped"] is False
    assert r["location_sub_area"] is None
    assert "perhaps also owner of tomb 354" in r["notes_from_pm"]
    assert "Macenhmut" in r["notes_from_pm"]
    assert "Reditico" in r["notes_from_pm"]
    assert "Nubnefert" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 407


# === Chunk-46 per-row pins (TT371–TT380) ====================================
# Rule 5: every row asserts all key fields. All values are post-fix-rows
# final state (after CHUNK46_CORRECTIONS applied).


def test_tt371_anonymous_khokha(reconciled):
    """TT371: Anonymous, Ramesside. Khokha. occupant_role restored to Unknown
    (sentinel-null collapse fixed by CHUNK46_CORRECTIONS)."""
    r = _row(reconciled, "TT371")
    assert r["occupant_name"] is None
    assert r["occupant_role"] == "Unknown"
    assert r["theban_area"] == "Khokha"
    assert r["notes_from_pm"] == "Name unknown. Ramesside."
    assert r["source_citation"]["page"] == 432
    assert r["attribution_certainty"] == "attested"
    assert r["is_uninscribed"] is False
    assert r["is_usurped"] is False
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []


def test_tt372_amenkhau(reconciled):
    """TT372: Amenkhaʿu, Overseer of carpenters of Temple of Medinet Habu.
    Temp. Ramesses III. Khokha. Mother Maʿetnefert, wife Nefertere-emḥab.
    Cosmetic: agent B had Medînet (circumflex); A+C majority correct."""
    r = _row(reconciled, "TT372")
    assert r["occupant_name"] == "Amenkhaʿu"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "Khokha"
    assert r["notes_from_pm"] == (
        "Overseer of carpenters of the Temple of Medinet Habu."
        " Temp. Ramesses III. Mother, Maʿetnefert. Wife, Nefertere-emḥab."
    )
    assert r["source_citation"]["page"] == 432
    assert r["attribution_certainty"] == "attested"
    assert r["is_uninscribed"] is False
    assert r["is_usurped"] is False
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []


def test_tt373_amenmessu(reconciled):
    """TT373: Amenmessu, Scribe of the altar. Ramesside. Khokha. Father Iny."""
    r = _row(reconciled, "TT373")
    assert r["occupant_name"] == "Amenmessu"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "Khokha"
    assert r["notes_from_pm"] == (
        "Scribe of the altar of the Lord of the Two Lands. Ramesside. Father, Iny."
    )
    assert r["source_citation"]["page"] == 433
    assert r["attribution_certainty"] == "attested"
    assert r["is_uninscribed"] is False
    assert r["is_usurped"] is False
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []


def test_tt374_amenemopet_cross_reference(reconciled):
    """TT374: Amenemopet, Scribe of treasury. Dyn. XIX. Khokha.
    CHUNK46_CORRECTIONS restored `For position, see p. 292.` (agent C had it;
    A+B majority dropped it; verbatim-preserve policy requires restoration).
    Matchable-name policy: PM AMENEMŌPET macron-Ō stripped → Amenemopet."""
    r = _row(reconciled, "TT374")
    assert r["occupant_name"] == "Amenemopet"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "Khokha"
    assert r["notes_from_pm"] == (
        "Scribe of the treasury in the Ramesseum. Dyn. XIX. For position, see p. 292."
    )
    assert r["source_citation"]["page"] == 434
    assert r["attribution_certainty"] == "attested"
    assert r["is_uninscribed"] is False
    assert r["is_usurped"] is False
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []


def test_tt375_anonymous_dra_abu_el_naga(reconciled):
    """TT375: Anonymous, Ramesside. Dra' Abu el-Naga. occupant_role=Unknown
    (sentinel-null collapse fixed by CHUNK46_CORRECTIONS)."""
    r = _row(reconciled, "TT375")
    assert r["occupant_name"] is None
    assert r["occupant_role"] == "Unknown"
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["notes_from_pm"] == "Name unknown. Ramesside."
    assert r["source_citation"]["page"] == 434
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []


def test_tt376_anonymous_dra_abu_el_naga(reconciled):
    """TT376: Anonymous, Dyn. XVIII. Dra' Abu el-Naga. occupant_role=Unknown."""
    r = _row(reconciled, "TT376")
    assert r["occupant_name"] is None
    assert r["occupant_role"] == "Unknown"
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["notes_from_pm"] == "Name lost. Dyn. XVIII."
    assert r["source_citation"]["page"] == 434
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []


def test_tt377_anonymous_dra_abu_el_naga(reconciled):
    """TT377: Anonymous, Ramesside. Dra' Abu el-Naga. occupant_role=Unknown."""
    r = _row(reconciled, "TT377")
    assert r["occupant_name"] is None
    assert r["occupant_role"] == "Unknown"
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["notes_from_pm"] == "Name lost. Ramesside."
    assert r["source_citation"]["page"] == 434
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []


def test_tt378_anonymous_dra_abu_el_naga(reconciled):
    """TT378: Anonymous, Dyn. XIX. Dra' Abu el-Naga. occupant_role=Unknown."""
    r = _row(reconciled, "TT378")
    assert r["occupant_name"] is None
    assert r["occupant_role"] == "Unknown"
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["notes_from_pm"] == "Name unknown. Dyn. XIX."
    assert r["source_citation"]["page"] == 435
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []


def test_tt379_anonymous_dra_abu_el_naga(reconciled):
    """TT379: Anonymous, Ramesside. Dra' Abu el-Naga. occupant_role=Unknown."""
    r = _row(reconciled, "TT379")
    assert r["occupant_name"] is None
    assert r["occupant_role"] == "Unknown"
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["notes_from_pm"] == "Name lost. Ramesside."
    assert r["source_citation"]["page"] == 435
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []


def test_tt380_ankhefen_re_harakhti(reconciled):
    """TT380: ʿAnkhef(en)-Reʿ-Harakhti, Chief in Thebes. Ptolemaic. Qurnet Muraʿi.
    occupant_name: B+C majority `Reʿ` wins over A's `Rʿ` (PDF p.435 line 140 =
    `R:Ec` OCR = Reʿ). Parents: CHUNK46_CORRECTIONS post-fix-rows restores both
    parent names from PM p.435 direct PDF read (egyptologist + code-reviewer
    P2 PR #293 round 1): `Dḥout` (PLAIN D, NOT d-bar Ḏ — agents over-applied
    the Thoth-family convention) and `Esnūter` (macron-ū restored from agent
    B; A+C majority OCR-misread as `Esntiter`)."""
    r = _row(reconciled, "TT380")
    assert r["occupant_name"] == "ʿAnkhef(en)-Reʿ-Harakhti"
    assert r["occupant_role"] == "Official"
    assert r["theban_area"] == "Qurnet Muraʿi"
    assert r["notes_from_pm"] == (
        "Chief in Thebes. Ptolemaic. Parents, Dḥout and Esnūter."
    )
    assert r["source_citation"]["page"] == 435
    assert r["attribution_certainty"] == "attested"
    assert r["is_uninscribed"] is False
    assert r["is_usurped"] is False
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
