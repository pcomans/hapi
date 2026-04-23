"""Apply LLM-reviewer-identified corrections to reconciled.jsonl.

Run AFTER merge.py. Mirrors Kitchen / Baud / Dodson-Hilton patterns —
idempotent re-runs, append-only LLM-APPLIED OVERRIDES section in
merge-disagreements.txt, every override recorded with rationale.

For chunk 1 (KV1–KV10): the field-rule-based prompt rewrite (post code-
reviewer feedback on PR #66) means agents now extract `source_citation.page`
from the chunk text running header, capture the complete `notes_from_pm`
clause across two-line headword wraps, and populate `occupant_alt_names`
from headword classical-alias parentheticals. The egyptologist-reviewer's
chunk-1 findings are therefore handled at extraction time; CHUNK1_CORRECTIONS
is empty pending any further reviewer-identified fixes.

Run:
    cd pipeline && uv run python pipeline/authority/sources/porter-moss-theban-necropolis/fix_rows.py

Idempotent: re-running replaces (not duplicates) the LLM-APPLIED OVERRIDES
section in merge-disagreements.txt.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
RECONCILED = SOURCE_DIR / "reconciled.jsonl"
DIFF = SOURCE_DIR / "merge-disagreements.txt"


# Chunk-1 corrections from the egyptologist-reviewer pass on PR #66.
# Each entry: (tomb_id, field, new_value, rationale).
CHUNK1_CORRECTIONS: list[tuple[str, str, object, str]] = []


# Chunk-2 (KV11–KV20) corrections. The prompt was rewritten post-PR-#68
# code-review (original prompt was flagged as an answer-table — rule 1/7
# regression) and the three agents were re-run under the field-rule prompt.
# Four residual corrections remain after the re-merge:
#
# 1. KV12 — `occupant_role`: prompt rule 1 says role="Unknown" when
#    occupant_name is null (UNINSCRIBED tombs), but all three agents
#    still emit null (transcribing the empty cell alongside empty name).
# 2. KV13 — `notes_from_pm`: agents captured PM's full headword suffix
#    `"Chancellor. Temp. Merneptaḥ-Siptaḥ"`. The `Chancellor` title is
#    already encoded via `occupant_role="Official"` per prompt rule 2
#    — duplicating it in notes violates single-source-of-truth. Strip
#    the prefix and normalise `ḥ` → `h` to match chunk-1's convention
#    (Merneptah without underdot).
# 3. KV18 — `notes_from_pm`: agents captured `"(formerly XI)"` including
#    the parentheses. Chunk 1's KV4 note for the same pattern is
#    `"formerly XII"` without parens. Strip parens for consistency.
# 4. KV19 — `occupant_name`: the `MENTUHIRKHOPSHEF` glyph in PM's text
#    layer has no underdot-H marker (it's `UH`, not the `I:I` form seen
#    elsewhere), but two of three agents over-normalised to `Mentuḥir...`.
#    Align with chunk-1's no-underdot convention (Hatshepsut, Merneptah).
#    Egyptologist-reviewer on PR #68 confirmed PM prints no underdot here.
CHUNK2_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "KV12",
        "occupant_role",
        "Unknown",
        "prompt rule 1 says role='Unknown' when occupant_name is null; "
        "PM p.527 headword is 'UNINSCRIBED' and all three agents still "
        "emit null despite the rule.",
    ),
    (
        "KV13",
        "notes_from_pm",
        "Temp. Merneptah-Siptah",
        "strip 'Chancellor.' (already encoded as occupant_role=Official) "
        "and normalise 'ḥ' → 'h' to match chunk-1's no-underdot "
        "convention (Merneptah in KV8 is rendered without underdot).",
    ),
    (
        "KV18",
        "notes_from_pm",
        "formerly XI",
        "strip parentheses to match chunk-1's KV4 pattern "
        "('formerly XII' without parens).",
    ),
    (
        "KV19",
        "occupant_name",
        "Raʿmeses-Mentuhirkhopshef",
        "PM p.546 headword prints MENTUHIRKHOPSHEF with plain H (no "
        "underdot glyph in the text layer); agents over-normalised to "
        "Mentuḥirkhopshef. Align with chunk-1's no-underdot convention.",
    ),
]


# Chunk-3 (KV22, 23, 34, 35, 36, 38, 39, 42, 43, 45, 46 — 11 rows after
# skipping absent KV24–33/37/40/41/44). Corrections after the field-rule-
# based prompt + 3-agent merge + egyptologist-reviewer second pass:
#
# 1. KV22 — `occupant_name`: PM text layer `AMENOPHIS I Il` = I + Il(=II)
#    = III; majority vote fell to "Amenophis II" because the chunk-3 prompt
#    had a mistaken example (`AMENOPHIS Il → Amenophis II`). Agent A
#    counted glyphs correctly. Egyptologist-reviewer confirmed KV22 is
#    Amenhotep III's West Valley tomb.
# 2. KV34 — `notes_from_pm`: PM p.551 prints `34. [1st ed. 24] TUTHMOSIS
#    III`; the raw OCR for KV34 renders `[rst ed. 24]` (the text layer's
#    Arabic `1` got mangled to `rst` for this specific line). `1st ed.`
#    is the Arabic form PM actually prints: across chunks 1-3 the OCR
#    produces 52 `[1st ed.` tokens vs 60 mangled variants (`Ist` 23,
#    `rst` 17, `xst` 20) — all OCR misreads of the same Arabic-1 glyph.
#    The bracketed 1st-edition cross-ref is structurally parallel to
#    chunk-1 KV4 `"formerly XII"` and chunk-2 KV18 `"formerly XI"`.
#    All three agents silently dropped it.
# 3. KV39 — `occupant_role`: prompt rule 1 says role="Unknown" when
#    occupant_name is null. PM p.559 prints `39· Uninscribed tomb,
#    attributed to Amenophis I by Weigall...`; agents emitted null despite
#    the rule.
# 4. KV42 — `notes_from_pm`: PM p.559 prints `42. TUTHMOSIS II (?)` with
#    attribution-uncertainty marker. Keep `occupant_name` structured and
#    absorb the (?) into notes alongside the existing `Excavated by Loret`
#    headword clause (period-space separator, chunk-2 KV14 precedent).
CHUNK3_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "KV22",
        "occupant_name",
        "Amenophis III",
        "PM p.547 text layer 'AMENOPHIS I Il' = I + Il(=II) = III. "
        "Majority vote was misled by a mistaken prompt example; agent A "
        "counted glyphs and got III. Egyptologist-reviewer confirmed KV22 "
        "is Amenhotep III's West Valley tomb.",
    ),
    (
        "KV34",
        "notes_from_pm",
        "1st ed. 24",
        "PM p.551 headword prints `34. [1st ed. 24] TUTHMOSIS III`. The "
        "chunk-3 text-layer OCR for this specific line renders the "
        "bracketed Arabic `1` as `rst`; across chunks 1-3 the same "
        "printed `[1st ed. N]` token OCRs to `1st` 52 times and to "
        "mangled variants (`Ist`/`rst`/`xst`) 60 times. Store the "
        "PM-verbatim `1st ed. 24` in notes_from_pm rather than "
        "transcribing any one OCR variant. Parallel in shape to "
        "chunk-1 KV4 'formerly XII' / chunk-2 KV18 'formerly XI'.",
    ),
    (
        "KV36",
        "occupant_name",
        "Mahirper",
        "PM p.556 headword prints `36. MAI;IIRPER` — the `I;I` glyph is "
        "the underdot-H (ḥ). Applying the chunk-1/2 rule `I;I → h` "
        "yields `MA` + `h` + `IRPER` = `MAHIRPER` → `Mahirper`. "
        "Agent B got this right; agents A and C kept a spurious `i` "
        "before the `h`. Egyptologist-reviewer second-pass confirmed no "
        "published Egyptological form reads 'Maihirper'.",
    ),
    (
        "KV39",
        "occupant_role",
        "Unknown",
        "prompt rule 1: role='Unknown' when occupant_name is null. PM "
        "p.559 prints 'Uninscribed tomb, attributed to Amenophis I by "
        "Weigall...'; agents emitted null despite the rule.",
    ),
    (
        "KV42",
        "notes_from_pm",
        "(?). Excavated by Loret",
        "PM p.559 prints 'TUTHMOSIS II (?)' — the `(?)` is PM's own "
        "attribution-uncertainty marker. Keep occupant_name structured "
        "as 'Tuthmosis II'; record PM's `(?)` glyph verbatim in notes "
        "(no paraphrase, per rule 1 PM-verbatim policy). Preserve the "
        "existing 'Excavated by Loret' headword clause; join with '. ' "
        "per chunk-2 KV14.",
    ),
]


# Chunk-4 (KV47, 48, 55, 56, 57 — 5 rows after skipping absent KV49-54
# and KV58-61; KV62 Tutankhamun deferred to its own chunk). Two residual
# corrections after the field-rule-based prompt + 3-agent merge +
# egyptologist-reviewer pass:
#
# 1. KV55 — `notes_from_pm`: agents stripped PM's `Smenkhkarēʿ` (macron-e
#    + trailing ayin `ʿ`) down to plain `Smenkhkare`, and dropped the
#    sentence-ending period. PM p.565 prints `Smenkhkarēʿ.` with both
#    diacritics and the period as part of the sentence. `notes_from_pm`
#    is the verbatim-preserve field, so both the macron and the ayin
#    must be restored.
# 2. KV56 — `occupant_role`: prompt rule 1 says role="Unknown" when
#    occupant_name is null. PM p.567 headword is the bare `'Gold Tomb',
#    uninscribed.` with no attribution clause; agents emitted null for
#    role. Same fix pattern as chunk-2 KV12 and chunk-3 KV39.
CHUNK4_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "KV55",
        "notes_from_pm",
        "Probably Amenophis IV, formerly attributed to Queen Teye or to Smenkhkarēʿ.",
        "The text-layer OCR for chunk 4 drops PM's macron-e and renders "
        "the ayin as `c` (`Smenkhkarec`); agents carried that through to "
        "the reconciled notes. Egyptologist-reviewer pre-merge pass on "
        "PR #70 verified PM p.565 itself prints `Smenkhkarēʿ` with both "
        "the macron and the trailing ayin, and confirmed the sentence-"
        "final period closes PM's sentence. notes_from_pm is verbatim-"
        "preserve against PM's printed text (not against the OCR text "
        "layer) — restore both diacritics.",
    ),
    (
        "KV56",
        "occupant_role",
        "Unknown",
        "prompt rule 1: role='Unknown' when occupant_name is null. PM "
        "p.567 headword is the bare `'Gold Tomb', uninscribed.` with no "
        "attribution; same fix pattern as chunk-2 KV12 and chunk-3 KV39.",
    ),
]


# Chunk-5 (KV62 Tutʿankhamun, single-row, headword-only per user direction
# that tomb-row granularity is sufficient for the museum-data-join use case).
# The 3 extraction subagents were unanimous on every field under the field-
# rule-based prompt. Egyptologist-reviewer pre-merge pass on PR #71 verified
# PM p.569 prints `TUT'ANKHAMŪN` with apostrophe-for-ayin + macron-u, and
# the bracketed `[1st ed. 58]` cross-reference in the headword; the chunk-5
# row's `Tutʿankhamun` (apostrophe normalised to Unicode ayin per chunk-2
# KV19 precedent; macron-u dropped per the occupant_name diacritic-stripping
# policy, which applies in royal-name English forms across chunks 1-4) and
# `notes_from_pm` value `"1st ed. 58. Excavated by Carnarvon and Carter."`
# (with `[1st ed. N]` normalised to `1st ed. N` per chunk-3 KV34 precedent
# and joined per chunk-2 KV14 `". "` pattern) both match PM's printed text.
# No reviewer-identified corrections needed. The empty list is retained
# (rather than dropped) so `test_all_corrections_includes_every_chunk_list`
# continues to enforce ALL_CORRECTIONS aggregation.
CHUNK5_CORRECTIONS: list[tuple[str, str, object, str]] = []


# Chunk-7 (PM I.2 §§ II + III.A/C/D — 18 descriptor-id rows) corrections
# from the egyptologist-reviewer pass on this PR (reviewer notes at
# `reviewer-notes-chunk7.md`).
#
# P1 corrections:
# 1. DAN-Aqhor (renamed from DAN-Ahhor) — PM p.605 prints headword `ʿAḲ-ḤOR`
#    (*rḫ-nswt* "king's acquaintance"), not `ʿAḥḥor`. This is a courtier,
#    not a royal-family member. `occupant_name` → "ʿAḳ-ḥor",
#    `occupant_role` → "Official" (was "Royal Family").
# 2. DAN-MentuhotpIWifeOfDjhuti (renamed from DAN-MentuhotpIWifeOfDjehuti)
#    — PM p.604 prints "Ḍḥuti" (underdot-D, underdot-H). The text-layer
#    OCR lost both diacritics. `notes_from_pm` restores "Ḍḥuti" verbatim.
# 3. DAN-AhmosiNefertari → renamed to DAN-AhmosiNefertere (PM prints
#    "Nefertere" not "Nefertari"). `notes_from_pm` expanded to capture
#    PM's Carter/Amenophis-I attribution history.
# 4. DAN-KamosiWazkheperre (renamed from DAN-KamoseWadjkheperre) — PM
#    p.600 headword is "KAMOSI (WAZKHEPERREʿ)"; descriptor uses PM-faithful
#    forms per the Ahmosi/Mentuhotp convention.
#
# CHUNK7_RENAMES below runs before CHUNK7_CORRECTIONS — the corrections
# reference the NEW tomb_ids.
CHUNK7_RENAMES: dict[str, str] = {
    "DAN-Ahhor": "DAN-Aqhor",
    "DAN-AhmosiNefertari": "DAN-AhmosiNefertere",
    "DAN-KamoseWadjkheperre": "DAN-KamosiWazkheperre",
    "DAN-MentuhotpIWifeOfDjehuti": "DAN-MentuhotpIWifeOfDjhuti",
}

CHUNK7_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "DAN-Aqhor",
        "occupant_name",
        "ʿAḳ-hor",
        "PM p.605 headword is `ʿAḲ-ḤOR` (*rḫ-nswt* 'king's acquaintance' "
        "compound), not `ʿAḥḥor`. Egyptologist-reviewer flagged agents' "
        "misread; tomb_id renamed to `DAN-Aqhor` via CHUNK7_RENAMES. "
        "Underdot-H stripped to plain `h` per README's matchable-name-field "
        "convention (Gemini round-3 sweep on PR #101). ḳ (underdot-K) "
        "preserved as a distinguishing radical.",
    ),
    (
        "DAN-Aqhor",
        "occupant_role",
        "Official",
        "`Royal acquaintance` (*rḫ-nsw*) is a minor courtier title, not a "
        "royal-family affiliation. Downgrade role from 'Royal Family' to "
        "'Official' per egyptologist-reviewer P1 finding.",
    ),
    (
        "DAN-MentuhotpIWifeOfDjhuti",
        "notes_from_pm",
        "Wife of King Ḍḥuti. Found in tomb by Passalacqua.",
        "PM p.604 prints `wife of King Ḍḥuti` with both underdot-D and "
        "underdot-H. The text-layer OCR rendered `Ql_J.uti` as `Djhuti` "
        "(no diacritics) and the agents carried that through. Restore the "
        "PM-verbatim diacritics per the `notes_from_pm` verbatim-preserve "
        "policy (chunk-1..6 convention). tomb_id renamed to "
        "`DAN-MentuhotpIWifeOfDjhuti` via CHUNK7_RENAMES for descriptor "
        "consistency with the PM-faithful spelling convention.",
    ),
    (
        "DAN-AhmosiNefertere",
        "notes_from_pm",
        "Tomb of Queen ʿAḥmosi Nefertere (probably). Attributed to Amenophis I "
        "by Carter, later equated by Černý with 'House of Amenophis of the Garden'.",
        "PM p.599-600 §III.C headword spells out the Carter attribution "
        "history in detail; the pre-review note dropped the Černý follow-up. "
        "Restore per egyptologist-reviewer P2 finding (verbatim preserve of "
        "the attribution-history clause). tomb_id renamed via CHUNK7_RENAMES.",
    ),
    # Chunk-7 `ḥ` sweep (Gemini round-3 on PR #101): the chunk-7 prompt
    # allowed `ḥ` in `occupant_name`, contradicting the README's project-wide
    # strip-ḥ policy (KV8 Merneptah, KV36 Mahirper, etc.). Retroactive
    # alignment: 8 additional chunk-7 rows have `ḥ` stripped here. DAN-Aqhor
    # `occupant_name` is handled in the earlier entry above (ʿAḳ-hor instead
    # of ʿAḳ-ḥor). Ayin `ʿ` and underdot-K `ḳ` are preserved as distinguishing
    # radicals per README; only underdot-H is stripped in the matchable name.
    (
        "SWV-HatshepsutSouth",
        "occupant_name",
        "Hatshepsut",
        "Strip underdot-H (ḥ → h) per README's matchable-name-field convention. "
        "Gemini round-3 sweep on PR #101.",
    ),
    (
        "DAN-Ahhotep",
        "occupant_name",
        "ʿAhhotp",
        "Strip underdot-H (ḥ → h) per README's convention. Ayin ʿ retained. "
        "Gemini round-3 sweep on PR #101.",
    ),
    (
        "DAN-AhmosiHenutempet",
        "occupant_name",
        "ʿAhmosi Henutempet",
        "Strip underdot-H (ḥ → h) per README's convention; both the `Aḥmosi` "
        "and `Ḥenutempet` underdot-Hs are stripped to plain h. Ayin ʿ retained. "
        "Gemini round-3 sweep on PR #101.",
    ),
    (
        "DAN-AhmosiNefertere",
        "occupant_name",
        "ʿAhmosi Nefertere",
        "Strip underdot-H (ḥ → h) per README's convention. Ayin ʿ retained. "
        "Gemini round-3 sweep on PR #101.",
    ),
    (
        "DAN-AhmosiSonOfSeqenenre",
        "occupant_name",
        "ʿAhmosi",
        "Strip underdot-H (ḥ → h) per README's convention. Ayin ʿ retained. "
        "Gemini round-3 sweep on PR #101.",
    ),
    (
        "DAN-MentuhotpIWifeOfDjhuti",
        "occupant_name",
        "Mentuhotp I",
        "Strip underdot-H (ḥ → h) per README's convention. Gemini round-3 "
        "sweep on PR #101.",
    ),
    (
        "DAN-MentuhotpSankhibtaui",
        "occupant_name",
        "Mentuhotp-Sʿankhibtaui",
        "Strip underdot-H (ḥ → h) per README's convention. Ayin ʿ retained. "
        "Gemini round-3 sweep on PR #101.",
    ),
    (
        "DAN-Neferhotep",
        "occupant_name",
        "Neferhotep",
        "Strip underdot-H (ḥ → h) per README's convention. Gemini round-3 "
        "sweep on PR #101.",
    ),
]


# Chunk-8 (PM I.2 § X.A Valley of the Queens — 20 numbered tombs).
# Four null-name rows (QV36, QV40, QV73, QV75) emit role=null despite the
# prompt's rule that role='Unknown' when occupant_name is null. Same fix
# pattern as chunk-2 KV12, chunk-3 KV39, chunk-4 KV56: agents transcribe
# the empty-cell shape literally instead of applying the rule.
CHUNK8_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "QV36",
        "occupant_role",
        "Unknown",
        "prompt rule 1: role='Unknown' when occupant_name is null. PM p.751 "
        "headword is 'A PRINCESS, no name.'",
    ),
    (
        "QV40",
        "occupant_role",
        "Unknown",
        "prompt rule 1: role='Unknown' when occupant_name is null. PM p.751 "
        "headword is 'A QUEEN, cartouche blank.'",
    ),
    (
        "QV73",
        "occupant_role",
        "Unknown",
        "prompt rule 1: role='Unknown' when occupant_name is null. PM p.767 "
        "headword is 'A PRINCESS, no name. Dyn. XX.'",
    ),
    (
        "QV75",
        "occupant_role",
        "Unknown",
        "prompt rule 1: role='Unknown' when occupant_name is null. PM p.768 "
        "headword is 'A QUEEN, no name.'",
    ),
    (
        "QV47",
        "notes_from_pm",
        "daughter of Seḳenenreʿ-Taʿa and Sit-ḍḥout. Dyn. XVII. (Bibl. i, 1st ed. p. 49.)",
        "PM p.755 prints the mother's name as 'Sit-ḍḥout' (ḍ = d with "
        "underdot, not plain d and not g). The text-layer OCR renders 'ḍḥ' "
        "as 'gḥ' — a character-level misread. Egyptologist-reviewer P2 "
        "finding: restore PM-verbatim Unicode spelling with `ḍ` (U+1E0D, "
        "Latin small letter d with dot below) to match PM's typography.",
    ),
    (
        "QV74",
        "notes_from_pm",
        "Great King's mother and King's wife. Wife(?) of Ramesses IV; mother of Ramesses V; "
        "daughter of Ramesses IV (per PM p.767 footnote 1). (CHAMPOLLION, No. 15, L. D. Text, "
        "No. 2, HAY, No. 7.)",
        "PM p.767 footnote 1 carries three hedged filiation facts (Gauthier, "
        "Černý, Seele) that the headword-only extraction dropped. Egyptologist-"
        "reviewer P2: restore the footnote kinship hedges since they are the "
        "only filiation info PM gives for Tentopet.",
    ),
    # Gemini round-3 finding on PR #101: the chunk-8 prompt drifted from the
    # project-wide README convention ("strip ḥ in occupant_name; keep ayin").
    # Chunk 7's `occupant_name` values drifted in the same direction — chunk-7
    # cleanup is a separate followup PR (those values are already merged). The
    # 5 corrections below align chunk 8 back to the README convention; QV44
    # `Khaʿemweset` already uses plain h so no correction is needed there.
    (
        "QV42",
        "occupant_name",
        "Paraʿhirwenemef",
        "Strip underdot-H (ḥ → h) in occupant_name per README's "
        "matchable-name-field diacritic-stripping convention (KV8 Merneptah "
        "precedent). Ayin ʿ retained.",
    ),
    (
        "QV43",
        "occupant_name",
        "Set-hirkhopshef",
        "Strip underdot-H (ḥ → h) in occupant_name per README convention.",
    ),
    (
        "QV46",
        "occupant_name",
        "Imhotep",
        "Strip underdot-H (ḥ → h) in occupant_name per README convention.",
    ),
    (
        "QV47",
        "occupant_name",
        "ʿAhmosi",
        "Strip underdot-H (ḥ → h) in occupant_name per README convention. "
        "Ayin ʿ retained.",
    ),
    (
        "QV55",
        "occupant_name",
        "Amen(hir)khopshef",
        "Strip underdot-H (ḥ → h) in occupant_name per README convention. "
        "Parenthetical infix `(hir)` preserved verbatim from PM.",
    ),
]


CHUNK8_RENAMES: dict[str, str] = {}


# Aggregation: every chunk's corrections list must appear here.
# `test_all_corrections_includes_every_chunk_list` asserts module-level
# `CHUNK*_CORRECTIONS` attributes are all present so dropping one silently
# destroys its audit trail.
ALL_CORRECTIONS: list[list[tuple[str, str, object, str]]] = [
    CHUNK1_CORRECTIONS,
    CHUNK2_CORRECTIONS,
    CHUNK3_CORRECTIONS,
    CHUNK4_CORRECTIONS,
    CHUNK5_CORRECTIONS,
    CHUNK7_CORRECTIONS,
    CHUNK8_CORRECTIONS,
]

# `ALL_RENAMES` aggregates per-chunk `CHUNK<N>_RENAMES` dicts (only chunk 7
# has renames so far; future chunks can define their own `CHUNK<N>_RENAMES`
# and merge it in here). Kept as a separate `main`-function input so the
# rename path stays symmetric to the field-correction path.
ALL_RENAMES: dict[str, str] = {
    **CHUNK7_RENAMES,
    **CHUNK8_RENAMES,
}

SPOT_CORRECTIONS: list[tuple[str, str, object, str]] = [
    correction for chunk in ALL_CORRECTIONS for correction in chunk
]

# Duplicate-detection: a `(tomb_id, field)` pair appearing twice across the
# CHUNK_*_CORRECTIONS lists silently stomps the earlier value based on list
# order. Raise loud on any duplicate. (No allowlist needed yet — add one only
# when a legitimate intentional duplicate appears.)
_seen: set[tuple[str, str]] = set()
for _tomb_id, _field, _, _ in SPOT_CORRECTIONS:
    _key = (_tomb_id, _field)
    if _key in _seen:
        raise ValueError(
            f"Duplicate SPOT_CORRECTIONS entry for {_key!r}; later value "
            f"silently overrides. Merge the two entries, or refactor."
        )
    _seen.add(_key)
del _seen


def _import_merge_sort_key():
    """Import `_sort_key` from sibling `merge.py` to re-order rows after renames.

    The merge's sort key understands both numbered (`KV5`) and descriptor
    (`DAN-Aqhor`) tomb_id shapes, so renamed rows land back in their correct
    sort position instead of at the tail of the JSONL — preventing the
    reordering drift Gemini code review (PR #100) flagged.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "pm_theban_merge", SOURCE_DIR / "merge.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._sort_key


def main() -> None:
    rows = [json.loads(line) for line in RECONCILED.read_text().splitlines() if line.strip()]

    # Renames first: some reviewer-flagged corrections involve renaming a
    # descriptor tomb_id to match PM's printed name (e.g. `DAN-Ahhor` →
    # `DAN-Aqhor` because PM actually prints `ʿAḲ-ḤOR`, not `ʿAḥḥor`).
    # Renames MUST run before SPOT_CORRECTIONS because the corrections
    # reference the NEW tomb_id. Idempotent: re-running finds no rename
    # matches on already-renamed rows.
    #
    # Logging convention mirrors field corrections (per Gemini code-review on
    # PR #100): every declared rename logs EVERY run — distinguishing between
    # "renamed this run" and "already renamed (no-op)" — so the diff file
    # never silently loses the audit trail on idempotent re-runs.
    rename_log: list[str] = []
    applied_renames = 0
    by_id = {r["tomb_id"]: r for r in rows}
    for old_id, new_id in ALL_RENAMES.items():
        if old_id in by_id and new_id in by_id:
            raise ValueError(
                f"Rename target {new_id!r} already exists; cannot rename "
                f"{old_id!r} → {new_id!r} without merging."
            )
        if old_id in by_id:
            applied_renames += 1
            by_id[old_id]["tomb_id"] = new_id
            by_id[new_id] = by_id.pop(old_id)
            rename_log.append(
                f"- {old_id} → {new_id} (renamed this run)"
            )
        elif new_id in by_id:
            rename_log.append(
                f"- {old_id} → {new_id} (already renamed; no-op this run)"
            )
        else:
            raise KeyError(
                f"Neither {old_id!r} nor {new_id!r} found in reconciled.jsonl "
                f"— declared rename has no target row to act on."
            )

    # Re-sort rows by the merge's `_sort_key` so renamed rows land back in
    # their correct lexicographic position (not at the dict-insertion-order
    # tail). Required for reconciled.jsonl to stay sorted across fix_rows runs.
    sort_key = _import_merge_sort_key()
    rows = sorted(by_id.values(), key=lambda r: sort_key(r["tomb_id"]))

    # Spot corrections.
    #
    # The log must describe the *state* of reconciled.jsonl, not the *delta*
    # from the previous run. On a second run every `old_val == new_val`, so a
    # delta-style log would incorrectly report "no overrides applied" while
    # the file on disk reflects all the applied overrides. Instead: always
    # log every SPOT_CORRECTION entry, distinguishing between this-run-changed
    # and already-in-state-on-disk so the log doesn't lie about what happened.
    override_log: list[str] = []
    applied_count = 0
    for tomb_id, field, new_val, rationale in SPOT_CORRECTIONS:
        row = by_id.get(tomb_id)
        if row is None:
            raise KeyError(f"No row with tomb_id={tomb_id!r}")
        old_val = row.get(field)
        if old_val != new_val:
            applied_count += 1
            override_log.append(
                f"- {tomb_id}: {field} corrected this run ({rationale})\n"
                f"    was: {json.dumps(old_val, ensure_ascii=False)}\n"
                f"    now: {json.dumps(new_val, ensure_ascii=False)}"
            )
            row[field] = new_val
        else:
            override_log.append(
                f"- {tomb_id}: {field} already matches override (no-op this run; {rationale})\n"
                f"    value: {json.dumps(new_val, ensure_ascii=False)}"
            )

    RECONCILED.write_text(
        "\n".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows
        )
        + "\n"
    )

    existing_diff = DIFF.read_text()
    marker = "LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED"
    idx = existing_diff.find(marker)
    if idx != -1:
        existing_diff = existing_diff[:idx].rstrip()
    body_sections: list[str] = []
    if rename_log:
        body_sections.append("Tomb-id renames:\n" + "\n".join(rename_log))
    if override_log:
        body_sections.append("Field corrections:\n" + "\n".join(override_log))
    body = "\n\n".join(body_sections) if body_sections else (
        "- No overrides applied. The reviewer pass produced no "
        "actionable corrections on `reconciled.jsonl` for this chunk."
    )
    # Per-chunk summary header — distinguishes "chunk has 0 corrections"
    # from "chunk was never processed". Flagged by the PR #71 code-reviewer
    # as an audit-trail gap when a chunk's CHUNK*_CORRECTIONS list is empty
    # (no log lines get emitted, so the chunk's absence looks identical to
    # a skipped run).
    #
    # Label each chunk by its numeric suffix read from the attribute name
    # (NOT by list-position). Gemini code-review on PR #71 flagged that
    # labelling by enumerate index breaks at chunk 10+ because the sibling
    # `test_all_corrections_includes_every_chunk_list` uses lexicographic
    # sort (which reorders chunks at 10+). Numeric sort here decouples the
    # summary's correctness from ALL_CORRECTIONS's iteration order.
    chunk_pattern = re.compile(r"^CHUNK(\d+)_CORRECTIONS$")
    module_globals = dict(globals())
    chunks = [
        (int(match.group(1)), attr, module_globals[attr])
        for attr, value in module_globals.items()
        if (match := chunk_pattern.match(attr))
    ]
    chunks.sort(key=lambda entry: entry[0])
    chunk_summary_lines = [
        f"- Chunk {number}: {len(corrections)} correction(s) defined in {attr}."
        for number, attr, corrections in chunks
    ]
    chunk_summary = "Per-chunk correction counts:\n" + "\n".join(chunk_summary_lines)

    appended = (
        f"{existing_diff.rstrip()}\n\n"
        f"{marker}\n"
        + "=" * len(marker) + "\n"
        "Corrections applied by fix_rows.py AFTER the 3-subagent majority-vote\n"
        "merge. Source of each correction: the egyptologist-reviewer Claude\n"
        "Code subagent pass against the source PDF. No human scholar has\n"
        "signed off on this extract yet — per ADR-017 step 6, the extract is\n"
        "provisional until that happens.\n\n"
        f"{chunk_summary}\n\n"
        f"{body}\n"
    )
    DIFF.write_text(appended)

    print(
        f"Applied {applied_renames} rename(s) and {applied_count} override(s) this run "
        f"({len(rename_log)} renames + {len(override_log)} corrections total in log)."
    )
    print(f"Updated {RECONCILED.relative_to(RECONCILED.parents[4])}")
    print(f"Updated {DIFF.relative_to(DIFF.parents[4])}")


if __name__ == "__main__":
    main()
