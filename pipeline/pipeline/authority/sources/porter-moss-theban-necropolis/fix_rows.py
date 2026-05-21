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

import copy
import json
import re
from pathlib import Path
from typing import Callable

SOURCE_DIR = Path(__file__).parent
RECONCILED = SOURCE_DIR / "reconciled.jsonl"
DIFF = SOURCE_DIR / "merge-disagreements.txt"


# Chunk-1 corrections from the egyptologist-reviewer pass on PR #66, plus
# one verbatim-preserve trailing-period restoration after the post-
# postprocessor rerun on PR #140.
# Each entry: (tomb_id, field, new_value, rationale).
CHUNK1_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "KV10",
        "notes_from_pm",
        "Inaccessible after Corridor B.",
        "PM p.517 headword prints `Inaccessible after Corridor B.` with a "
        "trailing period (chunk-1 line 870). Post-postprocessor agents "
        "dropped the period; restore via override per the README's "
        "notes_from_pm verbatim-preserve policy and to match the "
        "punctuation handling on KV14/KV19/KV22/KV23/KV43/KV45 etc. "
        "Gemini round-4 review (PR #140) flagged the punctuation "
        "inconsistency.",
    ),
    # KV9 occupant_alt_names correction superseded by AUDIT_FIX_CORRECTIONS
    # (PR A, 2026-05-02): the two strings 'Tomb of Metempsychosis' /
    # 'Tomb of Memnon' are TOMB-nicknames, not alternate-names of the
    # occupant Ramesses VI. Migrated to the new `tomb_aliases` field; this
    # row's `occupant_alt_names` is now `[]`.
]


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
        "Temp. Merneptaḥ-Siptaḥ.",
        "Strip 'Chancellor.' prefix (already encoded as "
        "occupant_role=Official). Preserve PM's underdot-Ḥ in the "
        "verbatim-preserve `notes_from_pm` field — earlier override "
        "incorrectly applied the strip-ḥ rule (which is for "
        "occupant_name only, the matchable-name field) to notes. "
        "Egyptologist-reviewer printed-source pass on PM I.2 PDF "
        "(2026-04-29 KV1-14 sweep) flagged as R2: PM p.527 prints "
        "`Temp. Merneptaḥ-Siptaḥ` with both ḥ underdots; this aligns "
        "with the chunk-7 sibling overrides for DAN-Ahhotep / "
        "DAN-AhmosiHenutempet / DAN-AhmosiSonOfSeqenenre that already "
        "preserve underdots in notes_from_pm.",
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
    (
        "KV20",
        "occupant_name",
        "Hatshepsut",
        "Strip underdot-H (Ḥ → H) per README's matchable-name-field "
        "diacritic-stripping convention. Pre-postprocessor (PR #140), the "
        "publisher OCR's variant cap-Ḥ glyphs (`I:I` in `I:Iatshepsut`) "
        "led the agents to emit plain `Hatshepsut` after their own "
        "case-aware normalisation; post-postprocessor the agents see "
        "canonical Unicode `Ḥ` and one or more carry the diacritic into "
        "occupant_name despite the README rule. Align here.",
    ),
]


# Chunk-3 (KV22, 23, 34, 35, 36, 38, 39, 42, 43, 45, 46 — 11 rows after
# skipping absent KV24–33/37/40/41/44). Corrections after the field-rule-
# based prompt + 3-agent merge + egyptologist-reviewer second pass:
#
# 1. KV34 — `notes_from_pm`: PM p.551 prints `34. [1st ed. 24] TUTHMOSIS
#    III`; the bracketed cross-ref is structurally parallel to chunk-1
#    KV4 `"formerly XII"` and chunk-2 KV18 `"formerly XI"`. All three
#    agents silently dropped it.
# 2. KV39 — `occupant_role`: prompt rule 1 says role="Unknown" when
#    occupant_name is null. PM p.559 prints `39· Uninscribed tomb,
#    attributed to Amenophis I by Weigall...`; agents emitted null despite
#    the rule.
# 3. KV42 — `notes_from_pm`: PM p.559 prints `42. TUTHMOSIS II (?)` with
#    attribution-uncertainty marker. Keep `occupant_name` structured and
#    absorb the (?) into notes alongside the existing `Excavated by Loret`
#    headword clause (period-space separator, chunk-2 KV14 precedent).
#
# Previously also corrected KV22 and KV36 occupant_name. The postprocessor
# (PR #140 / #132) now handles both at chunk-text level: KV36's
# `MAI;IIRPER` → `MAḤIRPER` is a direct Phase-1 substring substitution
# (`I;I` → `Ḥ`); KV22's `AMENOPHIS I Il` → `AMENOPHIS III` is the king-
# name-anchored Roman-numeral fix's all-caps multi-token branch (matches
# under `re.IGNORECASE` with the `I\s+Il` alternative). Both overrides
# became no-ops in the post-merge audit because the 3 agents now read the
# canonical form unanimously. Dropped.
CHUNK3_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "KV22",
        "notes_from_pm",
        "Excavated by Davis, and by Carnarvon and Carter.",
        "PM p.547 headword excavator clause `Excavated by Davis, and by "
        "Carnarvon and Carter, see CARTER and MACE...` — same shape as "
        "KV23/KV43/KV45 excavator clauses. (KV35/KV47/KV48 do NOT print "
        "explicit `Excavated by` clauses — Loret/Davis/Carter are cited "
        "via publication titles only — so no override is needed there.) "
        "The post-postprocessor rerun's three agents all dropped this "
        "`Excavated by ...` tail from notes_from_pm even though the "
        "postprocessor surfaced it cleanly. Restore via override "
        "(egyptologist-reviewer flagged as R1 in PR #140 review).",
    ),
    (
        "KV23",
        "notes_from_pm",
        "Excavated by Belzoni.",
        "PM p.550 headword excavator clause `Excavated by Belzoni, see "
        "id. Narrative of the Researches ... in Egypt and Nubia, "
        "pp. 123-4.` — same systemic dropout as KV22. Egyptologist-"
        "reviewer flagged as R2 in PR #140 review.",
    ),
    (
        "KV38",
        "notes_from_pm",
        "Excavated by Loret.",
        "PM p.557 headword excavator clause `Excavated by Loret, see "
        "DAVIS, &c., The Tomb of Hatshopsttu, p. xiv...` (chunk-3 line "
        "393) — same R1/R2 systemic loss as KV22/KV23/KV43/KV45. The "
        "egyptologist-reviewer's spot-check missed this one but the "
        "shape is identical: headword bibliographic-ribbon excavator "
        "clause that the post-postprocessor agents stripped.",
    ),
    (
        "KV34",
        "notes_from_pm",
        "1st ed. 24",
        "PM p.551 headword prints `34. [1st ed. 24] TUTHMOSIS III`. The "
        "postprocessor normalises `[Ist|rst|xst ed.` → `[1st ed.` at "
        "chunk-text level, so the agents now see the canonical form, but "
        "all three still drop the bracketed cross-ref entirely from "
        "notes_from_pm — they treat it as a section reference rather "
        "than headword content. Restore the PM-verbatim `1st ed. 24` "
        "string. Parallel in shape to chunk-1 KV4 'formerly XII' and "
        "chunk-2 KV18 'formerly XI'.",
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
    (
        "KV36",
        "notes_from_pm",
        "Standard-bearer, Child of the nursery. Temp. Ḥatshepsut. "
        "Excavated by Loret.",
        "PM p.556 prints `Temp. Ḥatshepsut.` with underdot-Ḥ in body "
        "text (the strip-ḥ rule applies to occupant_name only — the "
        "matchable-name field — NOT to notes_from_pm, which is "
        "verbatim-preserve). The post-postprocessor merge produced "
        "plain `Hatshepsut` in this notes field; restore the underdot. "
        "Direct R7 parallel to the DAN-Ahhotep / DAN-AhmosiHenutempet / "
        "DAN-AhmosiSonOfSeqenenre fix_rows entries that already restore "
        "ḥ/ḳ in their notes fields. Egyptologist-reviewer printed-source "
        "pass on PM I.2 PDF (post-merge, 2026-04-29) flagged this as "
        "R-NEW-1.",
    ),
    (
        "KV43",
        "notes_from_pm",
        "Excavated by Davis.",
        "PM p.559 headword excavator clause for KV43 (Tuthmosis IV) — "
        "same systemic R1/R2 dropout: post-postprocessor agents lost "
        "the `Excavated by ...` tail. Egyptologist-reviewer flagged as "
        "R1/R2/R4 sibling.",
    ),
    (
        "KV46",
        "notes_from_pm",
        "Divine father, and Chief of the harîm of Amūn, parents of Queen Teye.",
        "PM p.562 prints a single declarative sentence: `YUIA ..., Divine "
        "father, and THUIU ..., Chief of the harîm of Amūn, parents of "
        "Queen Teye.` — circumflex-î in `harîm`, macron-ū in `Amūn`. The "
        "post-postprocessor merge restructured it into a `Yuia: ... ; "
        "Thuiu: ... ;` agent-list with prefixes AND dropped both "
        "diacritics. Restore PM-verbatim by dropping the `Yuia:` / "
        "`Thuiu:` prefixes (those duplicate occupant_name='Yuia and "
        "Thuiu') and keeping only the role-clauses joined by `, and`. "
        "Egyptologist-reviewer printed-source pass flagged as R-NEW-3.",
    ),
    (
        "KV45",
        "notes_from_pm",
        "Overseer of the Fields of Amūn, Dyn. XVIII, re-used by Merenkhons, "
        "Doorkeeper of the House of Amūn, Dyn. XXII (name from scarab). "
        "Excavated by Davis and Carter.",
        "PM p.562 headword reads `Overseer of the Fields of Amūn, Dyn. "
        "XVIII, re-used by MERENKHONS, Doorkeeper of the House of Amūn, "
        "Dyn. XXII (name from scarab). Excavated by Davis and Carter.` "
        "Two regressions to address: (1) the `Excavated by Davis and "
        "Carter.` tail was dropped by post-postprocessor agents (R1/R2 "
        "systemic loss); (2) PM prints `Amūn` (twice) with macron-ū AND "
        "uses `,` (not `;`) after `Dyn. XVIII`. The merged-value body had "
        "stripped both macrons and substituted `;` for `,`. Egyptologist-"
        "reviewer printed-source pass on PM I.2 PDF (post-merge, "
        "2026-04-29) flagged macron-loss as R-NEW-2 and self-acknowledged "
        "the `;`-vs-`,` paraphrase; restoring all three at once for full "
        "PM-verbatim alignment.",
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
        "Wife of King Ḏḥuti. Found in tomb by Passalacqua.",
        "PM p.604 prints sentence-form `QUEEN MENTUḤOTP¹, wife of King Ḏḥuti` "
        "where `Ḏ` is d with bar/macron — the standard Egyptological "
        "transliteration of the d-emphatic, same character as in `Ḏḥwty`/Thoth "
        "(NOT `Ḍ` d-with-underdot, which is a different consonant in "
        "Semitic transliteration). The earlier P1 finding on PR #100 caught "
        "the OCR `Ql_J.uti` → `Djhuti` diacritic loss but installed the "
        "WRONG underdot consonant `Ḍ`; egyptologist printed-source review "
        "on PR #151 corrected `Ḍ` → `Ḏ` after direct PDF read of p.604. "
        "Wrong-consonant risk: `Ḍḥuti` would never match against TLA / "
        "Trismegistos / museum data using `Ḏḥuti`. tomb_id "
        "`DAN-MentuhotpIWifeOfDjhuti` (descriptor) intentionally retains "
        "ASCII `Djhuti` for filename safety; the PM-verbatim consonant `Ḏ` "
        "lives in `notes_from_pm`.",
    ),
    (
        "DAN-AhmosiNefertere",
        "notes_from_pm",
        "Tomb of Queen ʿAḥmosi Nefertere (probably). Attributed to Amenophis I "
        "by Carter, later equated by Černý with 'House of Amenophis of the Garden'.",
        "Egyptologist-reviewer P2 finding on PR #100 (reviewer-notes-chunk7.md): "
        "PM p.599-600 §III.C headword spells out the Carter attribution "
        "history in detail ('attributed to Amenophis I by Carter; Černý equates "
        "with House of Amenophis of the Garden'); the pre-review note dropped "
        "the Černý follow-up. Restore verbatim per the reviewer's citation of "
        "the full attribution-history clause. tomb_id renamed via CHUNK7_RENAMES.",
    ),
    # Chunk-7 `ḥ` sweep (Gemini round-3 on PR #101): the chunk-7 prompt
    # allowed `ḥ` in `occupant_name`, contradicting the README's project-wide
    # strip-ḥ policy. Most of these overrides became no-ops once the chunk-text
    # postprocessor (PR #140 / #132) started normalising the publisher OCR's
    # variant ḥ glyphs (`J:I`/`I:I`/`I;I`/`l:I`/`I:J`) to canonical Unicode `Ḥ`
    # at the chunk-text level: agents now see the same ḥ in every position and
    # apply the README's strip-ḥ rule consistently in occupant_name. Seven
    # `occupant_name` overrides (SWV-HatshepsutSouth, DAN-Ahhotep,
    # DAN-AhmosiHenutempet, DAN-AhmosiNefertere, DAN-AhmosiSonOfSeqenenre,
    # DAN-MentuhotpSankhibtaui, DAN-Neferhotep) are dropped as empirically
    # redundant — verified by comparing merge-only reconciled.jsonl to the
    # desired values during PR #140's post-merge audit. Two entries remain:
    # DAN-MentuhotpIWifeOfDjhuti (the agents preserve PM's "Queen" prefix in
    # occupant_name; the override strips it to match the role-encoded canonical
    # form) and DAN-Aqhor's occupant_name (handled in the earlier
    # P1-rename block above; underdot-K `ḳ` is a distinguishing radical that
    # the postprocessor does not touch).
    (
        "DAN-MentuhotpIWifeOfDjhuti",
        "occupant_name",
        "Mentuhotp I",
        "Agents preserve PM's `Queen` prefix from the headword (`QUEEN "
        "MENTUHOTP I, wife of King Ḍḥuti`); the project-wide convention is "
        "to encode the title in `occupant_role` and keep `occupant_name` "
        "as the bare regnal name. Strip the prefix here.",
    ),
    # Post-postprocessor rerun: the seven Dyn-17 royal rows below carried
    # their parenthetical prenomen INTO `occupant_name` (`Antef (Sehertaui)`,
    # `Kamosi (Wazkheperreʿ)`, etc.). The README defines `occupant_name` as
    # the matchable name field for Phase-A king-authority joining; pharaoh.se
    # and Beckerath key the multiple Antef kings on the bare prenomen list
    # (in `occupant_alt_names`), not on a parenthetical-string-in-name.
    # Strip the parenthetical so the joinable form matches the pharaoh.se
    # `Antef` entries. The prenomen survives in `occupant_alt_names`.
    # Egyptologist-reviewer flagged as R6 in PR #140 review.
    (
        "DAN-AntefSehertaui",
        "occupant_name",
        "Antef",
        "Strip parenthetical prenomen `(Sehertaui)`; alt_names retains it. "
        "R6 in egyptologist-reviewer PR #140 review.",
    ),
    (
        "DAN-AntefWahankh",
        "occupant_name",
        "Antef",
        "Strip parenthetical prenomen `(Wahankh)`; alt_names retains it.",
    ),
    (
        "DAN-AntefNubkheperre",
        "occupant_name",
        "Antef",
        "Strip parenthetical prenomen `(Nubkheperreʿ)`; alt_names retains it.",
    ),
    (
        "DAN-AntefSekhemreHeruhirmaet",
        "occupant_name",
        "Antef",
        "Strip parenthetical prenomen `(Sekhemreʿ-Heruhirmaʿet)`; alt_names "
        "retains it.",
    ),
    (
        "DAN-AntefSekhemreWepmaet",
        "occupant_name",
        "Antef",
        "Strip parenthetical prenomen `(Sekhemreʿ-Wepmaʿet)`; alt_names "
        "retains it.",
    ),
    (
        "DAN-KamosiWazkheperre",
        "occupant_name",
        "Kamosi",
        "Strip parenthetical prenomen `(Wazkheperreʿ)`; alt_names retains it.",
    ),
    (
        "DAN-SebkemsafSekhemreShedtaui",
        "occupant_name",
        "Sebkemsaf II",
        "Strip parenthetical prenomen `(Sekhemreʿ-Shedtaui)`; alt_names "
        "retains it.",
    ),
    # Post-postprocessor rerun: three rows had their `notes_from_pm` ḥ/ḳ
    # diacritics stripped despite the README's verbatim-preserve policy
    # for that field. The agents now correctly strip ḥ in `occupant_name`
    # (per the postprocessor's canonical Unicode handoff) but extended the
    # strip to `notes_from_pm`, which the README forbids. Restore the PM-
    # printed underdots. Egyptologist-reviewer flagged as R7 in PR #140.
    (
        "DAN-Ahhotep",
        "notes_from_pm",
        "Wife of King Seḳenenreʿ-Taʿa. Found by Mariette in 1859.",
        "Restore underdot-K (ḳ) in `Seḳenenreʿ-Taʿa` per README's "
        "notes_from_pm verbatim-preserve policy. PM p.600 prints "
        "Seḳenenreʿ-Taʿa with the underdot.",
    ),
    (
        "DAN-AhmosiHenutempet",
        "notes_from_pm",
        "Daughter of ʿAḥḥotp (wife of King Seḳenenreʿ-Taʿa).",
        "Restore underdot-H (ḥ) in `ʿAḥḥotp` and underdot-K (ḳ) in "
        "`Seḳenenreʿ-Taʿa` per README's notes_from_pm verbatim-preserve "
        "policy. PM p.605 prints both underdots in headword. Drop the "
        "`Coffin possibly from here.` tail the post-postprocessor agents "
        "added — that comes from the find-list line below the headword "
        "(`Coffin, possibly from here, formerly in possession of "
        "Castellari`) which is body content, not headword.",
    ),
    (
        "DAN-AhmosiSonOfSeqenenre",
        "notes_from_pm",
        "Eldest son of King Seḳenenreʿ-Taʿa and ʿAḥḥotp.",
        "Restore underdot-K and underdot-H per README's notes_from_pm "
        "verbatim-preserve policy.",
    ),
    # DAN-AhmosiHenutempet is the well-known Dyn-17 princess (daughter of
    # Ahhotep, sister of Ahmose I); the OLD test expected `Princess` and
    # the post-postprocessor merge downgraded to the more generic
    # `Royal Family`. Restore the more specific egyptological vocab.
    (
        "DAN-AhmosiHenutempet",
        "occupant_role",
        "Princess",
        "Daughter of a queen-consort; standard Egyptological convention "
        "is `Princess` for daughters of kings. The OLD merged value was "
        "`Princess`; post-postprocessor agents picked `Royal Family` "
        "(more generic). Egyptologist-reviewer R8 in PR #140 review.",
    ),
    # Post-postprocessor rerun lost two pyramid cross-refs from headword
    # tails. Same systemic R1/R2/R4 clause-loss pattern but on chunk-7
    # rows. Restore.
    (
        "DAN-KamosiWazkheperre",
        "notes_from_pm",
        "Found by Mariette in 1857. For pyramid, possibly of Kamosi, see infra, p. 620.",
        "Restore the dropped pyramid cross-ref `For pyramid, possibly "
        "of Kamosi, see infra, p. 620.` from PM p.600 headword tail. "
        "Egyptologist-reviewer R9 in PR #140 review.",
    ),
    (
        "DAN-AntefNubkheperre",
        "notes_from_pm",
        "Found by Mariette in 1860. Pyramid, see Hay MSS. 29816.",
        "Restore the dropped pyramid cross-ref `Pyramid, see HAY MSS. "
        "29816.` from PM p.602 headword tail. Egyptologist-reviewer R10 "
        "in PR #140 review.",
    ),
    (
        "DAN-Neferhotep",
        "notes_from_pm",
        "Scribe of the Great Harîm, probably temp. Antef (Nubkheperrēʿ). "
        "Rock-tomb, uninscribed. Found by Mariette in 1860, probably "
        "near Theb. tb. 13.",
        "PM p.604 prints `Scribe of the Great Harîm, probably temp. "
        "Antef (Nubkheperrēʿ). Rock-tomb, uninscribed. Found by Mariette "
        "in 1860, probably near Theb. tb. 13.` — circumflex-î in "
        "`Harîm`, macron-ē in `Nubkheperrēʿ`. The post-postprocessor "
        "merge stripped both diacritics. Restore per the verbatim-"
        "preserve policy on notes_from_pm. Egyptologist-reviewer "
        "printed-source pass flagged as R-NEW-4.",
    ),
    (
        "DAN-SebkemsafSekhemreShedtaui",
        "notes_from_pm",
        "Pyramid behind Theb. tb. 24, perhaps belonging to this tomb.",
        "Same R9/R10 systemic clause-loss: post-postprocessor agents "
        "dropped the pyramid cross-ref from PM p.604 headword tail. "
        "Restore.",
    ),
    # Post-postprocessor rerun dropped the `, quartzite, in Cairo Mus.
    # Ent. 47032` object-cite tail from SWV-HatshepsutSouth. The Cairo
    # Mus. Ent. 47032 reference (sarcophagus of Hatshepsut as Queen-
    # Consort, quartzite — confirmed by HAYES, Royal Sarcophagi, and the
    # standard sarcophagus literature) is exactly the catalogable fact
    # the schema is meant to retain. Egyptologist-reviewer R5 in PR #140.
    (
        "SWV-HatshepsutSouth",
        "notes_from_pm",
        "See also Tomb 20, supra, p. 546. Sarcophagus as Queen-Consort, quartzite, in Cairo Mus. Ent. 47032.",
        "Restore the `, quartzite, in Cairo Mus. Ent. 47032` object-cite "
        "tail from PM p.591 headword. Egyptologist-reviewer R5 in PR "
        "#140 review.",
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
        "daughter of Seḳenenreʿ-Taʿa and Sit-ḏḥout. Dyn. XVII. (Bibl. i, 1st ed. p. 49.)",
        "PM p.755 prints the mother's name as 'Sit-ḏḥout' with `ḏ` (d with "
        "bar/macron — the standard Egyptological transliteration of the "
        "d-emphatic, same character used for the deity Ḏḥuti/Thoth `Ḏḥwty`). "
        "Egyptologist printed-source review on PR #151 corrected this from "
        "the previous `ḍ` (d with underdot) — different consonants representing "
        "different sounds in standard Erman/Grapow/Hannig transliteration. "
        "The text-layer OCR renders the ḏḥ digraph as 'gQ.' (drops the bar-D "
        "entirely and renders the ḥ as `Q` + period) — this exact source token "
        "`Sit-gQ.out` is the one place this bigram appears in any chunk, and "
        "the postprocessor's substring substitution normalises it. The "
        "override here is the egyptologist-reviewer's PM-verbatim sentence-"
        "restoration (complete clause + bibliographic ribbon tail).",
    ),
    (
        "QV74",
        "notes_from_pm",
        "Great King's mother and King's wife. (CHAMPOLLION, No. 15, L. D. Text, No. 2, HAY, No. 7.)",
        "PM p.767 main text prints `74. QUEEN TENTŌPET [cartouche], Great "
        "King's mother and King's wife.¹ (CHAMPOLLION, No. 15, L. D. Text, "
        "No. 2, HAY, No. 7.) Plan, p. 760.` (verbatim). The earlier override "
        "synthesized main-text + footnote 1 (Gauthier/Černý/Seele Ramesses-IV/V "
        "genealogy) into a prose blob that did not appear verbatim in PM — a "
        "rule-1 (provenance) violation. Egyptologist printed-source review "
        "on PR #151 corrected this to PM-main-text-verbatim only. The "
        "footnote 1 genealogy + per-citation chain is dropped from "
        "`notes_from_pm` here; the schema currently has no `notes_footnote` / "
        "`notes_genealogy` field, so the genealogy is tracked for restoration "
        "via follow-up issue (schema split).",
    ),
    # Gemini round-3 finding on PR #101 originally added 5 occupant_name
    # ḥ-strip overrides here (QV42, QV43, QV46, QV47, QV55) to align chunk 8
    # back to the project-wide README convention ("strip ḥ in occupant_name;
    # keep ayin"). All 5 became no-ops once the chunk-text postprocessor
    # (PR #140 / #132) began normalising the publisher OCR's variant cap-Ḥ
    # glyphs (`I;I` in `PARAʿḤIRWENEMEF`, `J:I` in `SET-ḤIRKHOPSHEF`,
    # `I;I` in `IMḤOTEP` / `CAḤMOSI` / `AMEN(ḤIR)KHOPSHEF`) to canonical
    # Unicode `Ḥ` at chunk-text level: agents now see the same ḥ in every
    # position and apply the README strip-ḥ rule consistently. Dropped here
    # as empirically redundant — verified by PR #140's post-merge audit.
]


CHUNK8_RENAMES: dict[str, str] = {}


# Chunk-9 (PM I.1 § I — TT1-TT10 Deir el-Medina core). FIRST chunk drawn
# from PM I.1; previous chunks 1-8 came from PM I.2. Merge picked the
# `.).` redundant-double-period form on TT2/TT6/TT7/TT8/TT10 because two of
# three agents stitched the bibliographic close-paren `(L. D. Text, No. N.)`
# onto the next sentence's leading word with a paragraph-separator period in
# between — but PM I.1 prints `(L. D. Text, No. N.) <Next sentence>` with no
# period after the close-paren (verified at physical pp.19, 24, 32, 34, 37 of
# `proprietary/books/Porter & Moss - PM I Theban Necropolis.pdf`). Strip the
# redundant period to match PM's printed punctuation. TT4 already lands
# clean via `tie-break-overrides.json` so no entry needed for that row.
CHUNK9_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT1",
        "notes_from_pm",
        "Servant in the Place of Truth. Dyn. XIX. Father, Khaʿbekhnet (name on fragment, BRUYÈRE, Rapport (1927), fig. 34 [4]). Wife, Iyneferti.",
        "Restore the dropped object-cite parenthetical `(name on fragment, "
        "BRUYÈRE, Rapport (1927), fig. 34 [4])` that PM I.1 p.1 prints "
        "between the Father / Wife clauses. Same systemic R5/R9/R10 "
        "clause-loss pattern as TT10's Turin Mus. 1559 restoration and "
        "the chunk-7 SWV-HatshepsutSouth `Cairo Mus. Ent. 47032` "
        "restoration: object-level provenance cross-references are "
        "exactly the catalogable facts the schema is meant to retain. "
        "Egyptologist printed-source review on PR #196 third pass "
        "flagged the omission (see reviewer-notes-chunk9.md).",
    ),
    (
        "TT2",
        "notes_from_pm",
        "Servant in the Place of Truth. Temp. Ramesses II. (L. D. Text, No. 107.) Parents, Sennezem (tomb 1) and Iyneferti. Wives, Saḥte and (probably) Esi.",
        "Strip redundant `.).` double-period to PM-faithful `.)` form. PM "
        "I.1 p.6 (TT2) prints `(L. D. Text, No. 107.) Parents, …` with no "
        "period after the bibliographic close-paren; merge majority "
        "stitched the paragraph break with an extra period.",
    ),
    (
        "TT3",
        "notes_from_pm",
        "Servant in the Place of Truth on the west of Thebes. Ramesside. Parents, Menna and Huy. Wife, Nezemtbehdet.",
        "Drop false underdots inserted by extraction agents. PM I.1 p.9 (TT3 "
        "Peshedu) prints `Huy` (plain h, no underdot) and `Nezemtbehdet` "
        "(plain h, no underdot). Egyptologist printed-source review (chunk-9 "
        "PR) verified directly against the PDF. The README's notes_from_pm "
        "verbatim-preserve policy applies in both directions: drop the "
        "underdot when PM does not print one, preserve when it does.",
    ),
    (
        "TT4",
        "notes_from_pm",
        "Chiseller of Amūn in the Place of Truth. Temp. Ramesses II. (L. D. Text, No. 106.) Parents, Thonūfer, Chiseller of Amūn in the Khenu, and Maʿetnefert. Wives, Nefertere and Ḥenutmehyt.",
        "Three corrections applied per egyptologist printed-source review "
        "(chunk-9 PR): (a) drop medial false underdot in `Ḥenutmeḥyt` → "
        "`Ḥenutmehyt`. PM I.1 p.11 prints the queen's name in multiple body "
        "positions ((2), (5), (7)) where the medial `h` appears plain; "
        "comparison with clearly-underdotted instances on the same page "
        "(`Ḥaremḥab`, `Amenemḥab`) supports reading the medial as plain `h` "
        "in PM's typesetting of this entry. The standard scholarly form is "
        "`Ḥnwt-mḥyt` (TLA / Ranke PN) so this is a verbatim-vs-canonical "
        "diacritic-distribution call; we follow the verbatim-preserve rule "
        "and pin to PM's printed form, accepting that PM's typesetting may "
        "be locally inconsistent with PM's own conventions elsewhere in the "
        "volume. Egyptologist printed-source review on PR #196 second-pass "
        "verified the body-text positions and flagged this as a defensible "
        "P2 to soften the rationale (no data change). "
        "(b) Restore macrons on `Amūn` (both occurrences) — PM prints `Amūn` "
        "with macron-u; matches the chunk-3/7 macron-preserve precedent "
        "(KV45/KV46/DAN-Neferhotep all preserve macrons in notes). "
        "(c) Restore macron on `Thonūfer` — same rationale. The earlier "
        "tie-break-overrides.json TT4 entry's claim that 'macrons dropped "
        "per project-wide convention' was empirically wrong vs the chunk-3/7 "
        "precedent; superseded by this CHUNK9_CORRECTIONS entry.",
    ),
    (
        "TT5",
        "notes_from_pm",
        "Servant in the Place of Truth on the west of Thebes. Ramesside. Parents, Neferronpet and Mahi (name on stela in Brit. Mus. 150, see infra, p. 14). Wife, Taēsi.",
        "Three corrections per egyptologist printed-source review (chunk-9 "
        "PR): (a) drop false underdot on `Maḥi` → `Mahi`; PM I.1 p.12 "
        "prints `Mahi` (plain h, no underdot). (b) Restore macron on "
        "`Taēsi` — PM prints `Taēsi` with macron-e per the chunk-3/7 "
        "macron-preserve precedent. (c) Restore the dropped object-cite "
        "parenthetical `(name on stela in Brit. Mus. 150, see infra, "
        "p. 14)` that PM I.1 p.12 prints between the Parents and Wife "
        "clauses. Brit. Mus. 150 is a major British Museum object — "
        "exactly the catalog-level cross-reference Hapi needs for "
        "cross-museum reunification of Deir el-Medina material. Same "
        "systemic R5/R9/R10 pattern as TT1's BRUYÈRE 1927 fragment cite "
        "and TT10's Turin Mus. 1559 cite. Egyptologist printed-source "
        "review on PR #196 third pass flagged the omission "
        "(see reviewer-notes-chunk9.md).",
    ),
    (
        "TT6",
        "notes_from_pm",
        "Foremen in the Place of Truth. Temp. Ḥaremḥab to Ramesses II. (L. D. Text, No. 101.) Wife (of Neferḥōtep), Iymau; (of Nebnūfer), Iy.",
        "Two corrections: (a) Strip redundant `.).` double-period to PM-faithful "
        "`.)` form; PM I.1 p.14 prints `(L. D. Text, No. 101.) Wife …` with "
        "single period inside parens. (b) Restore macrons on `Neferḥōtep` and "
        "`Nebnūfer` per chunk-3/7 macron-preserve precedent — PM prints both "
        "with macron-ō / macron-ū respectively. The strip-Ḥ rule applies to "
        "`occupant_name` (matchable field) only; `notes_from_pm` is verbatim-"
        "preserve, so both the Ḥ underdot and the macron stay.",
    ),
    (
        "TT7",
        "notes_from_pm",
        "Scribe in the Place of Truth. Temp. Ramesses II. (L. D. Text, No. 99.) Parents, Amenemḥab and Kakaia. Wife, Mutemwia.",
        "Strip redundant `.).` double-period to PM-faithful `.)` form. "
        "Same pattern as TT2 fix; PM I.1 p.15 prints `(L. D. Text, No. 99.) "
        "Parents …` with single period inside parens.",
    ),
    (
        "TT8",
        "notes_from_pm",
        "Chief in the Great Place. Temp. Amenophis II, Tuthmosis IV, and Amenophis III. (L. D. Text, No. 96.) Wife, Meryt.",
        "Strip redundant `.).` double-period to PM-faithful `.)` form. "
        "Same pattern as TT2 fix; PM I.1 p.16 prints `(L. D. Text, No. 96.) "
        "Wife …` with single period inside parens.",
    ),
    (
        "TT7",
        "occupant_name",
        "Raʿmosi",
        "PM I.1 p.15 prints `7. RAʿMOSI [cartouche]` — titlecase form "
        "is `Raʿmosi`. The merge-output `Raʿmose` silently anglicized "
        "PM's `-osi` ending to `-ose`, a rule-1 (work-like-a-scholar) "
        "provenance violation in the matchable-name field. Compounded "
        "by wrong-person collision risk: `Raʿmose` is the name of the "
        "famous Vizier of Amenhotep IV in TT55 — a different historical "
        "person from this Deir el-Medina scribe. PM's `RAʿMOSI` (TT7 "
        "scribe) vs `RAʿMOSE` (TT55 vizier) distinction is the volume's "
        "deliberate disambiguation; preserving it in `occupant_name` is "
        "exactly what the matchable-field convention is for. Cross-"
        "volume corroboration: chunk-7's `DAN-AhmosiHenutempet` / "
        "`DAN-AhmosiSonOfSeqenenre` rows preserve PM's `-osi` ending "
        "verbatim — it is PM's editorial convention, not a typesetting "
        "accident. Egyptologist printed-source review on PR #196 third "
        "pass flagged as P1 merge-blocker.",
    ),
    (
        "TT9",
        "occupant_name",
        "Amenmosi",
        "PM I.1 p.18 prints `9. AMENMOSI [cartouche]` — titlecase form "
        "is `Amenmosi`. Same rule-1 violation as TT7's `Raʿmose` → "
        "`Raʿmosi` correction; same `-osi` → `-ose` Anglicization axis. "
        "PM consistently uses the Greek-style `-osi` transcription for "
        "the whole `iʿḥ-msi.w` / `Jmn-msi.w` name family across the "
        "volume — chunk-7's `Ahmosi`-family rows preserve the convention. "
        "Egyptologist printed-source review on PR #196 third pass "
        "flagged as P1 merge-blocker.",
    ),
    (
        "TT9",
        "notes_from_pm",
        "Servant in the Place of Truth, Charmer of scorpions. Ramesside. Wife, Tent-hōm.",
        "Drop false underdot on `Tent-ḥōm` → `Tent-hōm`. PM I.1 p.18 (TT9 "
        "Amenmose) prints `Tent-hōm` with plain h + macron-o (egyptologist "
        "verified directly against the PDF). The macron is correct; the "
        "underdot was inserted by extraction agents over-applying the "
        "strip-Ḥ-restore rule. Macron-o preserved per chunk-3/7 precedent.",
    ),
    (
        "TT10",
        "notes_from_pm",
        "Servants in the Place of Truth. Temp. Ramesses II. (L. D. Text, No. 97.) Father (of Penbuy), Iri (name from offering-table of Penbuy, in Turin Mus. 1559). Wives (of Penbuy), Amentetusert and Irnūfer; (of Kasa), Bukhaʿnef.",
        "Three corrections: (a) Strip redundant `.).` double-period to PM-"
        "faithful `.)` form; PM I.1 p.19 prints `(L. D. Text, No. 97.) "
        "Father …` with single period inside parens. (b) Restore macron on "
        "`Irnūfer` per chunk-3/7 macron-preserve precedent — PM prints "
        "`Irnūfer` with macron-u. (c) Restore the dropped Turin Mus. 1559 "
        "object-cite parenthetical `(name from offering-table of Penbuy, "
        "in Turin Mus. 1559)` — PM I.1 p.19 prints this between the "
        "Father / Wives clauses. The Turin Mus. catalog cross-reference is "
        "the kind of catalogable fact the schema is meant to retain "
        "(parallel to the chunk-7 SWV-HatshepsutSouth `Cairo Mus. Ent. "
        "47032` restoration). Egyptologist printed-source review on PR #196 "
        "second-pass flagged the omission as the same R5/R9/R10 systemic-"
        "clause-loss pattern.",
    ),
]


CHUNK9_RENAMES: dict[str, str] = {}


# Chunk-10 corrections — egyptologist-reviewer pass (this PR), all PDF-cited
# against `proprietary/books/Porter & Moss - PM I Theban Necropolis.pdf`.
# PM I.1 offset: physical = printed + 18.
CHUNK10_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT15",
        "notes_from_pm",
        "King's son, Mayor in the Southern City. Early Dyn. XVIII. Parents, Raḥotp, Overseer of the harim of the Lake (i.e. Fayûm), and Sensonb. Wife, Senbi.",
        "PM I.1 p.26 (physical p.44) prints `Fayûm` (circumflex û). "
        "Verbatim-preserve per README notes_from_pm policy. Text-layer "
        "extraction dropped the circumflex; egyptologist printed-source "
        "review (this PR) restored.",
    ),
    (
        "TT16",
        "notes_from_pm",
        "Prophet of 'Amenophis of the Forecourt'. Temp. Ramesses II. Wife, Ternūte.",
        "PM I.1 p.28 (physical p.46) prints `Wife, Ternūte` (n + macron-ū). "
        "Text-layer OCR misread as `Termite` (rn → rm ligature error + "
        "macron drop), fabricating a non-Egyptian woman's name. "
        "Verbatim-preserve per README notes_from_pm policy; same wrong-"
        "person-class risk as the chunk-9 TT3 false-underdot fixes. "
        "Egyptologist printed-source review (this PR).",
    ),
    (
        "TT17",
        "notes_from_pm",
        "Scribe and physician of the King. Temp. Amenophis II (?). Parents, Nebseny, Judge, and Amenḥotp (?). Wife, Ta...nūfer.",
        "PM I.1 p.29 (physical p.47) prints `Wife, Ta . . . nūfer` (n + "
        "macron-ū, with a printed lacuna `. . .` between `Ta` and `nūfer`). "
        "Text-layer OCR misread the `n` as `m` (same OCR class as TT16's "
        "Ternūte/Termite). Verbatim-preserve per README notes_from_pm "
        "policy. Egyptologist printed-source review (this PR).",
    ),
    (
        "TT17",
        "occupant_name",
        "Nebamūn",
        "PM I.1 p.29 (physical p.47) prints the headword `17. NEBAMŪN` "
        "with capital macron-ū. README's occupant_name policy preserves "
        "vowel macrons (ū, ō, ē, ā); only underdot-Ḥ is stripped. "
        "Chunk-7 `Wahʿankh` / `Sekhemreʿ-Wepmaʿet` set the macron-"
        "preserve precedent for occupant_name. Egyptologist printed-"
        "source review (this PR).",
    ),
]


CHUNK10_RENAMES: dict[str, str] = {}


# Chunk-11 corrections — egyptologist-reviewer pass (this PR), all PDF-cited
# against `proprietary/books/Porter & Moss - PM I Theban Necropolis.pdf`.
# PM I.1 offset: physical = printed + 18.
CHUNK11_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT26",
        "notes_from_pm",
        "Overseer of the treasury in the Ramesseum in the estate of Amūn. Temp. Ramesses II. (L. D. Text, No. 29.) Wife, Meryēsi.",
        "PM I.1 p.43 (physical p.61) prints `Wife, Meryēsi` (macron-ē). "
        "Text-layer OCR dropped the macron-ē. Verbatim-preserve per README "
        "notes_from_pm policy. Same chunk-9 KV55 / chunk-10 TT16 macron-"
        "preserve precedent for wife / family-clause name fragments. "
        "Egyptologist printed-source review (this PR). Per Gemini Code "
        "Assist PR #199 round 1, the rationale was originally `(n + macron-"
        "ē)` — the `n +` was a copy-paste leftover from chunk-10 TT16's "
        "`Termite → Ternūte` rn→rm OCR fix; TT26's only OCR issue is the "
        "macron drop, no n→m involved.",
    ),
    (
        "TT27",
        "notes_from_pm",
        "Chief steward of the divine adoratress ʿAnkhnesneferebreʿ. Temp. Apries and Amasis. (Inaccessible.) Parents, Ḥarsiēsi, Chamberlain of the divine adoratress, and Tahibet (from cone).",
        "PM I.1 p.43 (physical p.61) prints `Parents, Ḥarsiēsi` (macron-ē). "
        "Text-layer OCR dropped the macron-ē. Verbatim-preserve per README "
        "notes_from_pm policy. Same macron-ē class as TT26 above. Per "
        "Gemini Code Assist PR #199 round 1, also dropped a redundant "
        "`ʿAsâsîf.` sub-site token that this CHUNK11_CORRECTIONS entry "
        "previously included (the sub-site is captured in `theban_area`; "
        "sibling chunk-11 rows TT25 and TT26 do not repeat the sub-site "
        "in notes). The redundant token was authored into the correction "
        "value here, not emitted by the merge — per merge-disagreements "
        "TT27 line 118 none of agents a/b/c produced the token; the "
        "merge majority value is `(Inaccessible.) Parents,` directly. "
        "Egyptologist printed-source review (this PR).",
    ),
    (
        "TT29",
        "notes_from_pm",
        "Governor of the town, Vizier. Temp. Amenophis II. (HAY, No. 15.) Parents, [ʿAḥmosi] Ḥumay (tomb 224) and Nub. Wife, Wertmaʿetef.",
        "PM I.1 p.45 (physical p.63) prints `Parents, [ʿAḥmosi] Ḥumay (tomb "
        "224) and Nub.` — the character after the opening bracket is the "
        "ayin ʿ, not a `C`. The tie-break override pins agent B's bracket-"
        "and-name-root form `[Aḥmosi]` (best candidate; minority — agents "
        "A and C both produced `[Caḥmosi]`, mis-reading the ayin as a "
        "leading C; agent B alone got the bracket + name-root + "
        "punctuation right, only the leading ayin missing) at merge time "
        "per the KV36 principle (ties at merge, diacritics at fix_rows). "
        "This CHUNK11_CORRECTIONS entry layers the PM-faithful ayin "
        "restoration post-merge. Per Gemini Code Assist PR #199 round 1 "
        "(separation-of-concerns refactor) and round 2 (majority/minority "
        "wording correction); egyptologist printed-source review (this "
        "PR) verified PM p.45.",
    ),
    (
        "TT29",
        "occupant_name",
        "Amenemōpet",
        "PM I.1 p.45 (physical p.63) prints the headword `29. AMENEMŌPET` "
        "with capital macron-Ō. README's occupant_name policy preserves "
        "vowel macrons (ū, ō, ē, ā); only underdot-Ḥ is stripped. "
        "Same chunk-7 `Wahʿankh` / chunk-10 TT17 `Nebamūn` macron-preserve "
        "precedent. Sibling row TT24 `Nebamūn` (chunk 11) restored the "
        "macron correctly; TT29 was a parallel agent miss. Egyptologist "
        "printed-source review (this PR).",
    ),
]


CHUNK11_RENAMES: dict[str, str] = {}


CHUNK12_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT32",
        "occupant_name",
        "Ḏhutmosi",
        "PM I.1 p.49 / physical PDF p.67. The d-emphatic in this name "
        "family (`Thutmose` < Egyptian `Ḏḥwty-msj` < `Ḏḥwty`/Thoth) is "
        "the standard Egyptological d-bar `Ḏ` (U+1E0E), NOT d-underdot "
        "`Ḍ` (U+1E0C, a different consonant used in some Semitic "
        "transliteration systems). PR #151 (egyptologist printed-source "
        "review) explicitly verified this on PM I.2 p.604 (`Ḏḥuti` for "
        "DAN-MentuhotpIWifeOfDjhuti) and PM I.2 p.755 (`Sit-ḏḥout` for "
        "QV47), correcting earlier `Ḍ` extractions to `Ḏ` after direct "
        "PDF read. Agent B's `Ḏhutmosi` (d-bar) was the egyptologically "
        "correct form; agents A (`Thutmosi`, no diacritic) and C "
        "(`Hutmosi`, dropped consonant) were both wrong. Tie-break pins "
        "agent A's PDF-closest stripped-diacritic form for merge "
        "auditability; this CHUNK12_CORRECTIONS entry layers the post-"
        "merge diacritic restoration to the egyptologically-canonical "
        "`Ḏhutmosi`. Wrong-consonant risk: a row keyed on `Ḍhutmosi` "
        "would never match against TLA / Trismegistos / museum data "
        "using the d-bar form.",
    ),
    (
        "TT33",
        "occupant_name",
        "Pedamenōpet",
        "PM I.1 p.50 / physical PDF p.68. Direct PDF visual check of "
        "headword: PM prints `PEDAMENŌPET` (capital macron-Ō). pypdf "
        "text-layer drops capital macrons (same class as chunk-11 TT29 "
        "`Amenemōpet` restoration). The macron is visible in the PDF "
        "page image but not in the extracted text layer.",
    ),
    (
        "TT33",
        "source_citation",
        {"edition": "PM I.1 2nd ed. 1960", "section": "I", "page": 50},
        "PM I.1 p.50 / physical PDF p.68. Direct PDF visual check (parent "
        "agent, this PR) confirms TT33's headword `33. PEDAMENŌPET` is on "
        "printed p.50 (the page-number `50` is visible at the top-left of "
        "physical p.68), NOT p.49 (where TT32's body text continues). "
        "Agents A and C both gave page=49 (likely conflated with TT32's "
        "spillover); agent B gave 50 (correct). The merge majority vote "
        "(2-1) chose the wrong page; the egyptologist subagent missed it "
        "because the named PDF was not at the path it was given. This "
        "CHUNK12_CORRECTIONS entry layers the post-merge page fix.",
    ),
    (
        "TT34",
        "occupant_name",
        "Mentuemhēt",
        "PM I.1 p.56 / physical PDF p.74. Direct PDF visual check of "
        "headword: PM prints `MENTUEMḤĒT` (capital underdot-Ḥ + capital "
        "macron-Ē). pypdf text-layer captures the Ḥ residual but drops "
        "the Ē macron (same class as TT33). Per PM-faithful diacritic "
        "policy (strip underdot-Ḥ from occupant_name; preserve macrons), "
        "the canonical form is `Mentuemhēt`.",
    ),
    (
        "TT39",
        "occupant_name",
        "Puimrēʿ",
        "PM I.1 p.71 / physical PDF p.89. Direct PDF visual check of "
        "headword: PM prints `PUIMRĒʿ` (capital macron-Ē + ayin). "
        "pypdf text-layer drops the capital macron-Ē (same class as "
        "TT33/TT34). The ayin (U+02BF) was correctly extracted by the "
        "agents.",
    ),
]


CHUNK12_RENAMES: dict[str, str] = {}


CHUNK13_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT41",
        "occupant_name",
        "Amenemōpet",
        "PM I.1 p.78 / physical PDF p.96. Direct PDF visual check (parent "
        "agent, this PR) confirms PM prints headword `AMENEMŌPET` with "
        "capital macron-Ō on the second O (visible in the rendered "
        "headword; `Amūn` body prose on the same page confirms PM's "
        "diacritic-preservation policy). pypdf text-layer drops capital "
        "macrons in CAPS headwords (same OCR class as chunk-11 TT29 "
        "`AMENEMŌPET`, chunk-12 TT33 `PEDAMENŌPET`, chunk-12 TT34 "
        "`MENTUEMḤĒT`, chunk-12 TT39 `PUIMRĒʿ`). Restore Ō macron per "
        "the PM-faithful diacritic policy (preserve vowel macrons in "
        "occupant_name).",
    ),
    (
        "TT41",
        "notes_from_pm",
        "Chief steward of Amūn in the Southern City. Temp. Ramesses I to Sethos I(?). (CHAMPOLLION, No. 35.) Parents, Nefertiu, Judge, and Iny, Songstress of the Theban Triad. Wife, Nezem(t).",
        "PM I.1 p.78 / physical PDF p.96. Direct PDF visual check confirms "
        "PM prints `(CHAMPOLLION, No. 35.)` with a single period inside "
        "the close-paren only; the next field `Parents,` begins fresh on "
        "the next line. Reconciled value carried a spurious double period "
        "`(CHAMPOLLION, No. 35.).` from a 2/1 reconciliation (agents A "
        "and C both made the same OCR-introduced error; agent B was "
        "correct). Same class as chunk-12 TT26/TT31/TT33/TT35/TT36/TT37/"
        "TT39/TT40 double-period strip; this chunk-13 case differs only "
        "in that the wrong form went 2/1 (instead of 1/1/1) at "
        "reconciliation, requiring a CHUNK13_CORRECTIONS entry rather "
        "than a tie-break override.",
    ),
    (
        "TT47",
        "notes_from_pm",
        "Overseer of the royal harim. Temp. Amenophis III. (Inaccessible.) Parents, Neḥ, Judge, and Senenu. Wife, Maiay.",
        "PM I.1 p.87 / physical PDF p.105. Direct PDF visual check "
        "confirms PM prints `(Inaccessible.)` with a single period inside "
        "the close-paren only — a tomb-state-marker parenthetical on its "
        "own line, with the next field starting fresh. Reconciled value "
        "carried spurious double period `(Inaccessible.).` from a 2/1 "
        "reconciliation (same OCR-introduced class as TT41 / TT49 in "
        "this chunk). Strip the spurious period.",
    ),
    (
        "TT49",
        "notes_from_pm",
        "Chief scribe of Amūn. Probably temp. Ay. (CHAMPOLLION, No. 53, HAY, No. 11.) Parents, Neby, Servant of Amūn, and Iuy. Wife, Merytreʿ.",
        "PM I.1 p.91 / physical PDF p.109. Direct PDF visual check "
        "confirms PM prints `(CHAMPOLLION, No. 53, HAY, No. 11.)` with "
        "a single period inside the close-paren only. Reconciled value "
        "carried spurious double period (same class as TT41, TT47). "
        "Strip the spurious period.",
    ),
]


CHUNK13_RENAMES: dict[str, str] = {}


# Chunk-14 (TT51–TT60, Sh. ʿAbd el-Qurna). Reviewer-identified corrections
# for this chunk: 4 capital-macron restorations on `occupant_name`
# (TT51/TT53/TT56/TT57 — same `-emḤĒt` OCR class as chunk-12 TT34
# `MENTUEMḤĒT`), 1 macron restoration in TT58 `notes_from_pm`
# (`Amenemonet` → `Amenemōnet`), and 1 controlled-vocab pairing fix on
# TT58 `occupant_role` (`null` → `"Unknown"` per the chunk-8 KV12/QV36/
# QV40 null-name pairing invariant). ALL_CORRECTIONS aggregation is
# enforced by `test_all_corrections_includes_every_chunk_list`.
CHUNK14_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT51",
        "occupant_name",
        "Userhēt",
        "PM I.1 p.97 / physical PDF p.115. Direct PDF visual check (parent "
        "agent, this PR) confirms PM prints headword `USERḤĒT` with capital "
        "underdot-Ḥ + capital macron-Ē. pypdf text-layer drops capital "
        "macrons in CAPS headwords (same OCR class as chunk-11 TT29 "
        "`AMENEMŌPET`, chunk-12 TT34 `MENTUEMḤĒT`/TT39 `PUIMRĒʿ`, chunk-13 "
        "TT41 `AMENEMŌPET`). Strip Ḥ-underdot per PM-faithful policy; "
        "preserve macron-Ē → `Userhēt`. Note: chunk-13 TT47 has the same "
        "name and is likely also affected (egyptologist sweep flag — "
        "tracked separately, out of scope this PR).",
    ),
    (
        "TT53",
        "occupant_name",
        "Amenemhēt",
        "PM I.1 p.102 / physical PDF p.120. Direct PDF visual check "
        "confirms PM prints headword `AMENEMḤĒT` with capital underdot-Ḥ "
        "+ capital macron-Ē — same OCR class as TT51, parallel to "
        "chunk-12 TT34 `MENTUEMḤĒT` → `Mentuemhēt`. Strip Ḥ-underdot, "
        "preserve macron-Ē → `Amenemhēt`.",
    ),
    (
        "TT56",
        "occupant_name",
        "Userhēt",
        "PM I.1 p.111 / physical PDF p.129. Direct PDF visual check "
        "confirms PM prints headword `USERḤĒT` (same name as TT51, "
        "different individual — within-source NAME collision: "
        "different sub-period, different role-detail). Same "
        "macron-restoration class.",
    ),
    (
        "TT57",
        "occupant_name",
        "Khaʿemhēt",
        "PM I.1 p.113 / physical PDF p.131. Direct PDF visual check "
        "confirms PM prints headword `KHAʿEMḤĒT` with ayin (`ʿ`) + "
        "capital underdot-Ḥ + capital macron-Ē. Strip Ḥ-underdot, "
        "preserve ayin and macron-Ē → `Khaʿemhēt`. Same OCR class as "
        "TT51/TT53/TT56.",
    ),
    (
        "TT58",
        "occupant_role",
        "Unknown",
        "PM I.1 p.119 / physical PDF p.137. Headword `58. Name unknown, "
        "temp. Amenophis III. Usurped by AMENḤOTP ...` — anonymous "
        "original occupant. Per the chunk-8 KV12/KV39/KV56/QV36/QV40/"
        "QV73/QV75 precedent, null `occupant_name` MUST co-occur with "
        "`occupant_role=\"Unknown\"` (controlled-vocab pairing invariant). "
        "All 3 agents emitted `null` for occupant_role — agent reports "
        "claimed `Unknown` but the JSONL output had `null`. This "
        "correction enforces the pairing invariant.",
    ),
    (
        "TT58",
        "notes_from_pm",
        "Name unknown, temp. Amenophis III. Usurped by Amenḥotp, Overseer of the prophets of Amūn, and his son Amenemōnet, Temple-scribe of the Temple of Ramesses 'Beloved like Amūn', Dyn. XX. (L. D. Text, No. 43.) Wife (of Amenemōnet), Ḥenutʿanensu.",
        "PM I.1 p.119 / physical PDF p.137. Direct PDF visual check "
        "confirms PM prints `Amenemōnet` with macron-Ō (visible in body "
        "prose where lowercase macrons are preserved by pypdf). Reconciled "
        "value carried `Amenemonet` (no macron) — same `pet`/`net` "
        "macron-restoration class as chunk-11 TT29 `Amenemōpet`, chunk-12 "
        "TT33 `Pedamenōpet`. Restore macron-Ō at both occurrences in "
        "notes_from_pm (the usurper-son name + the wife-disambiguation "
        "parenthetical) per the verbatim-preserve policy.",
    ),
]


CHUNK14_RENAMES: dict[str, str] = {}


# Chunk-15 (TT61–TT70) corrections. Reviewer-identified: 5 corrections
# layered post-merge — TT65 occupant_name macron restoration (`Nebamun` →
# `Nebamūn`, PDF-verified capital macron-Ū drop, same OCR class as chunk-12
# TT34); TT65 notes_from_pm (spacing fix `accounts (?)` + PDF-corrected
# OCR misread `'Aichesi'` for the Prisse d'Avennes 19th-c. nickname);
# TT65 tomb_aliases (`["Aichesi"]` per the chunk-7/14 'Stuart's Tomb'
# precedent); TT68 occupant_name macron restoration (`[Per?]enkhmun` →
# `[Per?]enkhmūn`, same OCR class); TT70 controlled-vocab pairing fix
# (anonymous occupant_role `null` → `"Unknown"` per the chunk-8 + chunk-14
# TT58 invariant). ALL_CORRECTIONS aggregation enforced by
# `test_all_corrections_includes_every_chunk_list`.
CHUNK15_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT65",
        "occupant_name",
        "Nebamūn",
        "PM I.1 p.129 / physical PDF p.147. Direct PDF visual check (parent "
        "agent, this PR) confirms PM prints headword `NEBAMŪN` with capital "
        "macron-Ū. pypdf text-layer drops capital macrons in CAPS headwords "
        "(same OCR class as chunk-11 TT29 `AMENEMŌPET`, chunk-12 TT34 "
        "`MENTUEMḤĒT`/TT39 `PUIMRĒʿ`, chunk-13 TT41 `AMENEMŌPET`, chunk-14 "
        "TT51 `USERḤĒT`). Restore macron-Ū per PM-faithful policy. Within-"
        "source NAME collision with chunk-10 TT17 `Nebamūn` (already on "
        "disk with macron) — same name, different individual; both rows "
        "now consistent on the macron.",
    ),
    (
        "TT65",
        "notes_from_pm",
        (
            "Scribe of the royal accounts (?) in the Presence, Overseer "
            "of the granary, temp. Ḥatshepsut (?). Usurped by Imiseba, "
            "Head of the altar, Head of the temple-scribes of the estate "
            "of Amūn, temp. Ramesses IX. (CHAMPOLLION, No. 60, L. D. "
            "Text, No. 40, WILKINSON, No. 1, 'Aichesi' of Prisse.) "
            "Parents, Amenḥotp, Head of scribes of the Temple of "
            "Amen-reʿ in Karnak, and Mutemmeres. Wife, Te(n)tpapersetha."
        ),
        "PM I.1 p.129 / physical PDF p.147 (TT65 Nebamūn). Two corrections "
        "layered onto the tie-break-pinned form: (1) restore space before "
        "`(?)` in `accounts (?)` matching the parallel `temp. Ḥatshepsut "
        "(?)` form in the same entry and the broader PM printing standard "
        "(also TT62 `Tuthmosis III (?)`, TT69 `Tuthmosis IV (?)`); (2) "
        "correct OCR misread `'Alchesi'` → `'Aichesi'` (PM prints `Ai`, "
        "not `Al` — direct PDF visual check this PR; all 3 agents read "
        "the OCR `Al` cluster as `Al` but PDF clearly shows `Ai`).",
    ),
    (
        "TT65",
        "tomb_aliases",
        ["Aichesi"],
        "PM I.1 p.129 / physical PDF p.147. PM's headword body "
        "parenthetical `'Aichesi' of Prisse` is a 19th-c. tomb-nickname "
        "(Prisse d'Avennes' designation), structurally analogous to TT55 "
        "`'Stuart's Tomb'` (chunk-14 precedent) and the chunk-7 traveller-"
        "designation pattern. Promote to tomb_aliases per the established "
        "convention; the verbatim parenthetical stays in notes_from_pm "
        "for verbatim-preserve compliance.",
    ),
    (
        "TT68",
        "occupant_name",
        "[Per?]enkhmūn",
        "PM I.1 p.133 / physical PDF p.151. Direct PDF visual check (parent "
        "agent, this PR) confirms PM prints headword `[PER?]ENKHMŪN` with "
        "capital macron-Ū. Same OCR macron-drop class as TT65 / chunk-12 "
        "TT34 etc. Preserve editorial brackets `[Per?]` per the bracketed-"
        "name-fragment rule; restore macron-Ū on the surviving tail.",
    ),
    (
        "TT70",
        "occupant_role",
        "Unknown",
        "PM I.1 p.139 / physical PDF p.157. Headword `70. Usurped by "
        "AMENMOSI ...` — anonymous original occupant (the headword opens "
        "directly with `Usurped by` with no primary name). Per the "
        "controlled-vocab pairing invariant established by chunk-8 KV12/"
        "KV39/KV56/QV36/QV40/QV73/QV75 and re-affirmed by chunk-14 TT58: "
        "null `occupant_name` MUST co-occur with `occupant_role=\"Unknown\"`. "
        "All 3 agents emitted `null` for occupant_role despite the "
        "prompt's explicit pairing rule (same agent-emission gap as "
        "chunk-14 TT58). This correction enforces the invariant.",
    ),
]


CHUNK15_RENAMES: dict[str, str] = {}


# Chunk-16 (TT71–TT80) corrections. Egyptologist-reviewer pass applied
# 6 PDF-verified corrections: 3 capital-macron restorations on
# `occupant_name` (TT72 `Reʿ` → `Rēʿ`, TT77 `Ptahemhet` → `Ptahemhēt`,
# TT80 `Ḏhutnufer` → `Ḏhutnūfer`), 1 macron restoration in
# `notes_from_pm` (TT78 `Esi` → `Ēsi`), and 2 ayin restorations in
# `notes_from_pm` (TT77 `Raḥuy` → `Raʿḥuy`, TT79 `wab-priest` →
# `wʿab-priest` per TT14/TT68 precedent). All cite direct PM PDF
# visual checks. ALL_CORRECTIONS aggregation is enforced by
# `test_all_corrections_includes_every_chunk_list`.
CHUNK16_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT72",
        "occupant_name",
        "Rēʿ",
        "PM I.1 p.142 / physical PDF p.160. Egyptologist printed-source "
        "review (this PR) confirms PM prints headword `RĒʿ` with capital "
        "macron-Ē + ayin. Same OCR macron-drop class as chunk-11 TT29 "
        "`AMENEMŌPET`, chunk-12 TT34 `MENTUEMḤĒT`, chunk-14 TT51 "
        "`USERḤĒT`, chunk-15 TT65 `NEBAMŪN`. Restore macron-Ē; preserve "
        "ayin (U+02BF). The deity name `Reʿ` (sun god) takes capital "
        "macron in PM-faithful transliteration.",
    ),
    (
        "TT77",
        "occupant_name",
        "Ptahemhēt",
        "PM I.1 p.150 / physical PDF p.168. Egyptologist confirms PM "
        "prints headword `PTAḤEMḤĒT` with multi-Ḥ + capital macron-Ē "
        "(same `-emḤĒT` cluster as chunk-12 TT34 `MENTUEMḤĒT` / chunk-14 "
        "TT51 `USERḤĒT` / chunk-14 TT53 `AMENEMḤĒT`). Strip both Ḥ-"
        "underdots per policy; preserve macron-Ē → `Ptahemhēt`.",
    ),
    (
        "TT78",
        "notes_from_pm",
        (
            "Royal scribe, Scribe of recruits. Temp. Tuthmosis III to "
            "Amenophis III. (CHAMPOLLION, No. 4, L. D. Text, No. 57, "
            "WILKINSON, No. 16, HAY, No. 23.) Mother, Ēsi. Wife, Ithuy."
        ),
        "PM I.1 p.152 / physical PDF p.170. Egyptologist confirms PM "
        "prints mother's name `Ēsi` with capital macron-Ē in body prose "
        "(lowercase macrons preserved by pypdf — but the OCR for this "
        "page also dropped it). Restore macron-Ē in notes_from_pm per "
        "the verbatim-preserve policy and the same OCR class as "
        "chunk-9 TT5 `Taēsi`.",
    ),
    (
        "TT77",
        "notes_from_pm",
        (
            "Child of the nursery, Overseer of works in the Temple of "
            "Amūn, Standard-bearer of the Lord of the Two Lands. Usurped "
            "by Roy, Overseer of sculptors of the Lord of the Two Lands. "
            "Temp. Tuthmosis IV. (CHAMPOLLION, No. 8 bis, L. D. Text, "
            "No. 62.) Wife (of Ptaḥemḥet), Meryt. Wife (of Roy), Raʿḥuy."
        ),
        "PM I.1 p.150 / physical PDF p.168. Egyptologist confirms PM "
        "prints Roy's wife's name `Raʿḥuy` with ayin (U+02BF) — same "
        "OCR drop class as chunk-9 / chunk-10 ayin restorations. The "
        "OCR text-layer rendered `Raḥuy` (no ayin); restore per the "
        "verbatim-preserve policy.",
    ),
    (
        "TT79",
        "notes_from_pm",
        (
            "Overseer of the granary of the Lord of the Two Lands, "
            "wʿab-priest in the Mortuary Temple of Tuthmosis III. "
            "Temp. Tuthmosis III to Amenophis II (?). (CHAMPOLLION, "
            "No. 7, L. D. Text, No. 60.) Father, Minnakht (tomb 87)."
        ),
        "PM I.1 p.156 / physical PDF p.174. Egyptologist confirms PM "
        "prints `wʿab-priest` with ayin (U+02BF) before the `a` — same "
        "TT14 (PM I.1 p.26) / TT68 (PM I.1 p.133) `wʿab-priest` "
        "precedent already established in tie-break-overrides.json. "
        "The chunk-16 merge pinned agent A's stripped form (no ayin); "
        "fix_rows layers the ayin restoration post-merge per the "
        "merge/fix_rows separation-of-concerns convention.",
    ),
    (
        "TT80",
        "occupant_name",
        "Ḏhutnūfer",
        "PM I.1 p.157 / physical PDF p.175. Direct PDF visual check "
        "(parent agent, this PR) confirms PM prints headword `ḎḤUTNŪFER` "
        "with capital d-bar Ḏ (Thoth/Djehuty name family) + capital "
        "underdot-Ḥ + capital macron-Ū. All 3 agents converged on the "
        "d-bar Ḏ + Ḥ-stripped form `Ḏhutnufer` (correct per the "
        "PR #200 / #151 d-bar precedent for the Ḏḥwty-family); the "
        "macron-Ū drop is the same OCR class as chunk-12 TT34 "
        "`MENTUEMḤĒT` / chunk-14 TT51 `USERḤĒT` / chunk-15 TT65 "
        "`NEBAMŪN` / chunk-15 TT68 `[PER?]ENKHMŪN`. Restore macron-Ū "
        "→ `Ḏhutnūfer`.",
    ),
]


CHUNK16_RENAMES: dict[str, str] = {}


CHUNK17_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT81",
        "notes_from_pm",
        (
            "[1st ed. Anena], Overseer of the granary of Amūn. Temp. "
            "Amenophis I to Tuthmosis III. (CHAMPOLLION, No. 5, "
            "WILKINSON, No. 14, HAY, No. 8.) Parents, Ineni, Judge, and "
            "Sit-ḏhout. Wife, ʿAḥḥotp, called Thuiu."
        ),
        "PM I.1 p.159 / physical PDF p.177 (TT81 Ineni). Direct PDF "
        "visual check (parent agent, this PR, after egyptologist-"
        "reviewer flag re: ḥ-underdot drop) confirms PM p.159 prints: "
        "`Parents, Ineni ⟨hg⟩, Judge, and Sit-ḏhout ⟨hg⟩. Wife, "
        "ʿAḥḥotp ⟨hg⟩, called Thuiu ⟨hg⟩.` Two PM-faithful details that "
        "the merge tie-break VALUE itself now reflects (after the "
        "egyptologist flag): (1) `[1st ed. Anena], ` belongs at the "
        "start of notes_from_pm — PM prints `81. INENI ⟨hieroglyphs⟩ "
        "[1st ed. Anena], Overseer of the granary of Amūn` with the "
        "bracket inline with the headword BEFORE the role. (2) `ʿAḥotp` "
        "(single ḥ — agent A's form) → `ʿAḥḥotp` (doubled ḥ — direct "
        "PDF visual: both ḥ-underdots present on PM p.159 for Queen "
        "Ahhotep, also matches the chunk-12 TT12 override precedent for "
        "the same queen). The parent name `Sit-ḏhout` (d-bar Ḏ + plain "
        "h, no ḥ-underdot) is now pinned in the tie-break override "
        "value itself per per-row PDF observation; fix_rows only layers "
        "the bracket-prefix + Queen-Ahhotep doubled-ḥ.",
    ),
    (
        "TT82",
        "occupant_name",
        "Amenemhēt",
        "PM I.1 p.163 / physical PDF p.181 (TT82). Direct PDF visual "
        "check confirms PM prints headword `82. AMENEMḤĒT` with capital "
        "macron-Ē (and underdot-Ḥ which we strip per occupant_name "
        "policy). Same macron-Ē OCR drop class as chunk-12 TT34 "
        "`MENTUEMḤĒT` / chunk-14 TT51 `USERḤĒT` / chunk-14 TT53 + "
        "chunk-16 TT77 `AMENEMḤĒT` / `PTAḤEMḤĒT`. Restore macron-Ē → "
        "`Amenemhēt` (Ḥ underdot stripped per occupant_name policy).",
    ),
    (
        "TT84",
        "notes_from_pm",
        (
            "First royal herald, Overseer of the gate, temp. Tuthmosis "
            "III. Partly usurped by Mery (tomb 95), temp. Amenophis II. "
            "(CHAMPOLLION, No. 11, L. D. Text, No. 71, WILKINSON, No. "
            "31, HAY, No. 19.) Parents (of Amunezeḥ), Siḏhout, Judge, "
            "and Resi. Wife (of Amunezeḥ), Ḥenutnefert."
        ),
        "PM I.1 p.167 / physical PDF p.185 (TT84 Amunezeḥ). The merge "
        "tie-break (post-egyptologist-flag rewrite) now pins the "
        "PDF-correct `Siḏhout` (d-bar Ḏ + plain h, no ḥ-underdot — "
        "direct PDF visual at p.167). This fix_rows entry layers a "
        "single prose-style normalisation: PM body prose prints "
        "`Partly usurped by MERY (tomb 95)` in small caps; per the "
        "TT51/TT57/TT58/TT60 chunk-12-and-14 precedent, body-prose "
        "small-caps are text-layer artefacts of PM's typographic "
        "convention and are normalised to Title-case `Mery` in "
        "notes_from_pm. Same pattern as TT58 (`AMENḤOTP`/`AMENEMONET` "
        "→ `Amenḥotp`/`Amenemonet`) and TT60 (`ANTEFOḲER`/`SENT` → "
        "`Antefoḳer`/`Sent`). Fix_rows applies the prose-style "
        "normalisation post-merge per the merge/fix_rows separation-"
        "of-concerns convention.",
    ),
    (
        "TT86",
        "notes_from_pm",
        (
            "First prophet of Amūn. Temp. Tuthmosis III. Parents, "
            "Amenemḥēt and Taōnet, King's nurse."
        ),
        "PM I.1 p.175 / physical PDF p.193 (TT86 Menkheperraʿsonb). "
        "Direct PDF visual check confirms PM prints `Parents, "
        "Amenemḥēt and Taōnet ⟨hieroglyphs⟩, King's nurse.` with two "
        "macrons in body prose: capital macron-Ē on `Amenemḥēt` (same "
        "OCR drop class as the TT82 occupant_name correction in this "
        "chunk + the chunk-12-onward `-emḤĒT` cluster) and capital "
        "macron-Ō on `Taōnet` (same class as chunk-15 TT74 `TENTŌPET`-"
        "family macron-Ō restorations). The body-prose `Amenemḥēt` "
        "RETAINS the underdot-Ḥ per the verbatim-preserve policy for "
        "notes_from_pm (different from the occupant_name policy which "
        "strips Ḥ underdot — TT82 in this chunk strips, TT86 notes "
        "preserves; both are correct per their respective policies).",
    ),
    (
        "TT90",
        "occupant_name",
        "Nebamūn",
        "PM I.1 p.183 / physical PDF p.201 (TT90 Nebamun). Direct PDF "
        "visual check confirms PM prints headword `90. NEBAMŪN` with "
        "capital macron-Ū. Same OCR macron-drop class as chunk-15 TT65 "
        "`NEBAMŪN` (the within-source NAME collision precedent — "
        "Nebamūn appears at least 3× in PM I.1: TT17, TT65, TT90). "
        "Agents A+C kept the prompt-rule-compliant stripped form "
        "`Nebamun` (per the no-pre-derive-macrons-from-outside-"
        "knowledge rule); agent B violated the rule by pre-deriving "
        "`Nebamūn`. Merge resolved 2/1 to `Nebamun` per the prompt-"
        "rule-compliant majority; fix_rows layers the macron "
        "restoration post-merge per the egyptologist-cited PM "
        "headword form.",
    ),
]


CHUNK17_RENAMES: dict[str, str] = {}


CHUNK18_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT91",
        "occupant_role",
        "Unknown",
        "PM I.1 p.185 / physical PDF p.203 (TT91 anonymous occupant). PM "
        "headword reads `91. Captain of the troops ..., Overseer of "
        "horses. Temp. Tuthmosis IV to Amenophis III.` — no NAME-IN-CAPS "
        "token. All 3 agents emitted `occupant_name=null` + "
        "`occupant_role=\"Unknown\"`. Merge.py sentinel-null normalisation "
        "(SENTINEL_NULL_STRINGS at merge.py:159) coerced the literal "
        "string `\"Unknown\"` to JSON `null` because it is in the "
        "sentinel set. Pin `\"Unknown\"` post-merge per the chunk-8 + "
        "chunk-14 TT58 + chunk-15 TT70 anonymous-occupant pairing "
        "invariant: when occupant_name is null, occupant_role must be "
        "\"Unknown\" (controlled-vocab pairing rule).",
    ),
    (
        "TT93",
        "occupant_name",
        "Ḳenamūn",
        "PM I.1 p.190 / physical PDF p.208 (TT93). Direct PDF visual "
        "check (parent agent, this PR) confirms PM prints headword "
        "`93. ḲENAMŪN` with capital underdot-Ḳ + capital macron-Ū. "
        "Agents A+B converged on `Ḳenamun` (Ḳ correct, macron-Ū "
        "stripped per the no-pre-derive-macrons rule); agent C "
        "extracted the wrong name `Hen-Amūn` (mis-decoded the OCR `~` "
        "cluster as `H` instead of `Ḳ`). Merge resolved 2/1 to "
        "`Ḳenamun` per the prompt-rule-compliant majority; fix_rows "
        "layers the macron-Ū restoration post-merge per the OCR "
        "capital-macron-drop precedent (chunk-11 TT29 `AMENEMŌPET` / "
        "chunk-12 TT34 `MENTUEMḤĒT` / chunk-15 TT65 `NEBAMŪN` / "
        "chunk-16 TT72 `RĒʿ` / chunk-17 TT90 `NEBAMŪN`).",
    ),
    (
        "TT95",
        "shared_with_tombs",
        [],
        "PM I.1 p.195 / physical PDF p.213 (TT95 Mery — USURPER of "
        "TT84). Agents A+B (2/1 majority) emitted "
        "`shared_with_tombs=[\"TT84\"]` reading PM's `(See also "
        "usurpation in tomb 84.)` parenthetical as a chunk-9 `See "
        "also Tomb N` ownership cross-ref. This is structurally wrong: "
        "PM's phrasing is `See also usurpation in tomb N` (an EVENT "
        "cross-reference), NOT `See also Tomb N` (an ownership cross-"
        "reference). The chunk-9-onward `shared_with_tombs` rule "
        "documents only ownership-flavoured patterns (`See also Tomb "
        "N`, `Also owner of tomb N`). Override the merge majority to "
        "[] post-merge: the cross-ref is structurally captured by the "
        "verbatim parenthetical preserved in `notes_from_pm` (see "
        "tie-break-overrides.json TT95|notes_from_pm). Without this "
        "override, the within-section symmetry test "
        "`test_shared_with_tombs_symmetry_within_chunk` fails because "
        "TT84 has no back-ref to TT95 (and shouldn't — TT84's headword "
        "doesn't print a `See also Tomb 95` ownership reference, only "
        "the `Partly usurped by MERY (tomb 95)` event reference).",
    ),
    (
        "TT97",
        "occupant_name",
        "Amenemhēt",
        "PM I.1 p.203 / physical PDF p.221 (TT97). Direct PDF visual "
        "check (parent agent, this PR — flagged by Gemini Code Assist "
        "round 1) confirms PM prints headword `97. AMENEMḤĒT` with "
        "capital macron-Ē. All 3 agents converged on `Amenemhet` "
        "(stripped Ḥ-underdot per occupant_name policy + macron-Ē "
        "stripped per the no-pre-derive-macrons rule). Same OCR "
        "capital-macron-drop class as chunk-11 TT29 `AMENEMŌPET`, "
        "chunk-12 TT34 `MENTUEMḤĒT`, chunk-14 TT51 `USERḤĒT`, "
        "chunk-14 TT53 + chunk-16 TT77 `AMENEMḤĒT`/`PTAḤEMḤĒT`, "
        "chunk-17 TT82 `AMENEMḤĒT`. Restore macron-Ē → `Amenemhēt` "
        "(Ḥ underdot stripped per occupant_name policy).",
    ),
    (
        "TT93",
        "notes_from_pm",
        (
            "Chief steward of the King. Temp. Amenophis II. (CHAMPOLLION, "
            "No. 8 quater, L. D. Text, No. 68, WILKINSON, No. 33, HAY, "
            "No. 18.) Mother, Amenemōpet, Royal nurse. Wife, Tadedetes."
        ),
        "PM I.1 p.190 / physical PDF p.208 (TT93 Ḳenamūn body prose). "
        "Direct PDF visual check (parent agent, this PR — flagged by "
        "Gemini Code Assist round 1) confirms PM prints `Mother, "
        "Amenemōpet ⟨hg⟩, Royal nurse.` with capital macron-Ō on the "
        "mother's name. All 3 agents converged on `Amenemopet` "
        "(macron-Ō stripped). Same OCR capital-macron-drop class as "
        "chunk-11 TT29 occupant_name `AMENEMŌPET` (the same name "
        "family) and chunk-15 TT74 `TENTŌPET`. Restore body-prose "
        "macron-Ō per the verbatim-preserve policy for notes_from_pm "
        "(different from occupant_name policy which strips Ḥ-underdot "
        "but preserves macrons; here the macron-Ō is restored as "
        "PM-verbatim).",
    ),
    (
        "TT100",
        "occupant_name",
        "Rekhmirēʿ",
        "PM I.1 p.206 / physical PDF p.224 (TT100, Governor of the "
        "town and Vizier — major Theban tomb spanning 9 printed "
        "pages). Direct PDF visual check (parent agent, this PR) "
        "confirms PM prints headword `100. REKHMIRĒʿ` with capital "
        "macron-Ē + ayin (U+02BF). All 3 agents converged on "
        "`Rekhmireʿ` (ayin correct, macron-Ē stripped per the no-pre-"
        "derive-macrons rule). Fix_rows layers the macron-Ē "
        "restoration post-merge per the OCR capital-macron-drop "
        "precedent (chunk-11 TT29 `AMENEMŌPET` etc., chunk-16 TT72 "
        "`RĒʿ` for the same Reʿ-name family).",
    ),
]


CHUNK18_RENAMES: dict[str, str] = {}


# Chunk-19: PM I.1 § I Numbered Tombs TT101-TT110 (Sh. ʿAbd el-Qurna).
# No field-value corrections at merge time; 4 tie-break-overrides.json entries
# resolved all 1/1/1 ties (TT104|notes_from_pm, TT106|notes_from_pm,
# TT107|notes_from_pm, TT110|notes_from_pm).  DERIVER_OVERRIDES below handle
# TT108 + TT110 attribution_certainty over-fires (regnal-date and
# family-name hedge classes respectively).
# Egyptologist review pending for potential capital-macron restorations:
#   TT101 THANURO → THANŪRO?  TT105 KHAʿEMOPET → KHAʿEMŌPET?
#   TT107 NEFERSEKHERU → NEFERSEKHĒRU?
# These are NOT applied here until PDF visual confirmation is obtained.
CHUNK19_CORRECTIONS: list[tuple[str, str, object, str]] = []
# DECLINE — PR #263 round-1 egyptologist P1 (TT102 Imhotep → Imḥotep) was
# considered and DECLINED. The project's `occupant_name` field is a
# matchable-name field that STRIPS underdot-Ḥ (`ḥ` → `h`, `Ḥ` → `H`) per
# the README convention enforced by `test_occupant_name_has_no_underdot_h`
# (line 391). Egyptologically `Imḥotep` is correct, but the project's
# project-wide policy is plain `Imhotep` in occupant_name (matching the
# tomb_id strip-Ḥ rule). The underdot-bearing PM-source form lives in
# notes_from_pm if it appears there. Per
# `feedback_reviewer_vs_deterministic_output.md`: reviewer corrections
# that contradict deterministic project tests are declined.

CHUNK19_RENAMES: dict[str, str] = {}


# Chunk-20: PM I.1 § I Numbered Tombs TT111-TT120 (Sh. ʿAbd el-Qurna).
# No field-value corrections at merge time; 4 tie-break-overrides.json entries
# resolved all 1/1/1 ties (TT112|notes_from_pm, TT113|notes_from_pm,
# TT114|notes_from_pm, TT120|notes_from_pm). DERIVER_OVERRIDES below handle
# TT116 + TT118 attribution_certainty over-fires (both regnal-date hedges).
# Egyptologist review pending:
#   TT114 occupant_role="Unknown" may be wrong — PM's headword prints a title
#   (`Head of goldworkers of the estate of Amūn`) without a personal name.
#   If PM convention marks this row as Official-with-lost-name (not Unknown),
#   the role should be "Official". All 3 agents agreed on "Unknown" (transcribed
#   the absence of a personal name as Unknown), but the title presence suggests
#   the agents applied the Unknown rule too broadly. Pending egyptologist
#   printed-source review before applying any correction.
#   TT120 occupant_alt_names=["Mahu"] — "Mahu" is an external-catalogue name
#   (Gardiner & Weigall), not a verified ancient alias. The alt_names field is
#   designed for alternate ancient readings; whether a modern-catalogue label
#   belongs here is an egyptologist judgment call.
CHUNK20_CORRECTIONS: list[tuple[str, str, object, str]] = []
# TT115 is_uninscribed=True moved to DERIVER_OVERRIDES below (the issue-#182
# deriver pass runs after SPOT_CORRECTIONS and would over-write a True
# value here back to False since `No texts` doesn't match the deriver's
# `\buninscribed\b` regex). DERIVER_OVERRIDES wins over deriver output.

CHUNK20_RENAMES: dict[str, str] = {}


# Chunk-21 (PM I.1 § I — TT121-TT130, Sh. ʿAbd el-Qurna).
# One tie-break override (TT122 notes_from_pm). No reviewer-identified
# corrections after 3-agent merge. The empty list is retained so
# `test_all_corrections_includes_every_chunk_list` continues to enforce
# ALL_CORRECTIONS aggregation.
CHUNK21_CORRECTIONS: list[tuple[str, str, object, str]] = []

CHUNK21_RENAMES: dict[str, str] = {}


# Chunk-22 (PM I.1 § I — TT131-TT140, Sh. ʿAbd el-Qurna + Dra' Abu el-Naga).
# Seven tie-break-overrides.json entries (TT134|notes_from_pm, TT135|notes_from_pm,
# TT137|notes_from_pm, TT138|notes_from_pm, TT139|notes_from_pm,
# TT140|notes_from_pm, TT140|occupant_alt_names). 2/1-majority resolutions:
# TT131 notes (A+C drop headword parenthetical), TT132 occupant_name (A+C
# Raʿmosi), TT133 notes (B+C Amūn + Hunuro), TT137 occupant_name (B+C Mose).
# Post-merge corrections applied here:
#   TT131 — all 3 agents mis-decoded OCR `6z` as `62` (TT62) rather than `61`
#     (TT61). Semantic and symmetry evidence confirms `61`: (a) TT61 (Governor
#     and Vizier, Temp. Tuthmosis III) is the known companion tomb of Amenuser,
#     the same official; TT62 (Overseer of Cabinet, Temp. Tuthmosis III (?)) is
#     a different person. (b) The within-section symmetry test requires TT131 to
#     back-ref TT61 because TT61 already carries `shared_with_tombs: ["TT131"]`
#     from an earlier chunk. Fix: `shared_with_tombs: ["TT61"]` and
#     `notes_from_pm: "(See tomb 61.) ..."` (replacing both the cross-ref value
#     and the parenthetical text). The `z`→`1` OCR misread is a known hazard for
#     this scan's numeral rendering (compare `z`→`2` majority class).
#   TT133 — restore `Ḥunuro` underdot-ḥ (B+C majority stripped it; source OCR
#     `l:lunuro` = `Ḥunuro`; verbatim-preserve policy for notes_from_pm).
#   TT135 — `Wab-priest` → `wʿab-priest` (ayin before a, lowercase per PM
#     body-prose convention; same class as TT113/TT114 ayin-before-a).
#   TT136 — occupant_role: None → "Unknown" (sentinel-null coercion by merge.py;
#     same precedent as TT58/TT70/TT91; all 3 agents correctly emitted
#     occupant_role="Unknown" but the SENTINEL_NULL_STRINGS pass coerced it).
#   TT138 — `Wife, Nesha.` → `Wife, Neshaʿ.` (ayin restoration; source OCR
#     `Nesha(` = `Neshaʿ`; A+B emitted ayin, C dropped it; C won tie-break
#     on other axes, so ayin must be restored here).
#   TT139 — `Wab-priest` → `wʿab-priest` (same ayin-before-a class as TT135).
#   TT140 — `Kefia` → `Ḥefia` in notes_from_pm (OCR `~EFIA` / `l):.efia`
#     confirms underdot-Ḥ; `Hefia` in occupant_alt_names is ḥ-stripped per
#     TT57/TT120 matchable-name precedent and resolves correctly via tie-break
#     override; verbatim-preserve notes_from_pm restores `Ḥefia` with underdot).
#     DERIVER_OVERRIDES below handle TT140 attribution_certainty over-fire
#     (`probably called` hedges the alt-name only, not the primary attribution).
# Egyptologist review pending for potential capital-macron restorations in
# occupant_name fields (all 3 agents agree on the stripped forms; PDF visual
# confirmation needed before applying macron restorations per chunk-11 precedent).
CHUNK22_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT131",
        "shared_with_tombs",
        ["TT61"],
        "PM I.1 p.245 / physical PDF p.263 (TT131 Amenuser). Source OCR "
        "`(See tomb 6z.)` — all 3 agents decoded `6z` → `62` (TT62). Correct "
        "reading is `61` (TT61): (1) TT61 (Governor and Vizier, Temp. Tuthmosis "
        "III) is the documented companion tomb of Amenuser / User — same official, "
        "same period; TT62 (Overseer of Cabinet, Temp. Tuthmosis III (?)) is a "
        "different person with no known connection to TT131. (2) Within-section "
        "symmetry: TT61 already carries `shared_with_tombs: [\"TT131\"]` from "
        "chunk-9 processing, establishing the expected bidirectional pair. PM's "
        "cross-ref convention requires the pair to be symmetric within § I. "
        "The `z`→`1` OCR misread is plausible for this scan's numeral rendering "
        "(compare the `6z` → `62` majority-class decoding pattern, where `z` "
        "normally represents `2`, but occasionally represents `1` when the "
        "numeral `1` has a serifed or ambiguous glyph form).",
    ),
    (
        "TT131",
        "notes_from_pm",
        "(See tomb 61.) Temp. Tuthmosis III. (L. D. Text, No. 87.)",
        "PM I.1 p.245 / physical PDF p.263 (TT131 Amenuser). Source OCR "
        "`(See tomb 6z.) Temp. Tuthmosis III.` — all 3 agents decoded "
        "`6z` → `62`, placing the parenthetical as `(See tomb 62.)`. Correct "
        "reading is `61` (see shared_with_tombs correction above — same OCR "
        "mis-decode rationale). Additionally: majority A+C dropped the cross-ref "
        "parenthetical from notes_from_pm entirely; agent B retained it with "
        "the incorrect `62`. Per the chunk-9-onward shared_with_tombs "
        "ownership-cross-ref convention, the verbatim parenthetical is preserved "
        "in notes_from_pm even when the structured field already carries the "
        "reference (same policy as TT104 `(See tomb 80.)`). Cross-ref precedes "
        "the temporal clause per PM's printed order (TT104 tie-break precedent).",
    ),
    (
        "TT133",
        "notes_from_pm",
        "Chief of the weavers in the Ramesseum in the estate of Amūn on the "
        "west of Thebes. Temp. Ramesses II. Wife, Ḥunuro.",
        "PM I.1 p.249 / physical PDF p.267 (TT133 Neferronpet). Source OCR "
        "`l:lunuro` = `Ḥunuro` (underdot-Ḥ confirmed by `l:` OCR pattern "
        "for underdot-ḥ, same class as `l:Iatl:lor` = `Ḥatḥor` in TT139). "
        "Majority B+C emitted `Hunuro` (underdot stripped); agent A correctly "
        "emitted `Ḥunuro`. B+C won the notes tie on the `Amūn` macron axis; "
        "the underdot-ḥ on the wife's name must be restored per the "
        "verbatim-preserve policy for notes_from_pm.",
    ),
    (
        "TT135",
        "notes_from_pm",
        "wʿab-priest in front of Amūn. Dyn. XIX.",
        "PM I.1 p.250 / physical PDF p.268 (TT135 Bekenamun). Source OCR "
        "`warb-priest` = `wʿab-priest` (ayin-hook before `a`, same OCR "
        "rendering class as TT113/TT114 where `wʿab` was established by "
        "TT14/TT68/TT97 precedent). Tie-break pinned agent C `Wab-priest` "
        "(best non-ayin skeleton with macron-Ū). Restore: (1) ayin before `a` "
        "→ `wʿab`; (2) sentence-initial lowercase `w` per PM body-prose "
        "convention (contrast heading small-caps `W`). Full correction: "
        "`Wab-priest` → `wʿab-priest`.",
    ),
    (
        "TT136",
        "occupant_role",
        "Unknown",
        "PM I.1 p.251 / physical PDF p.269 (TT136, anonymous royal scribe). "
        "All 3 agents correctly emitted occupant_role=\"Unknown\" (controlled-"
        "vocab sentinel for rows with no identified occupant; paired with "
        "occupant_name=null per schema invariant). merge.py SENTINEL_NULL_STRINGS "
        "pass coerces the literal string \"Unknown\" to JSON null — same class "
        "as TT58 (chunk-14), TT70 (chunk-15), TT91 (chunk-18). Restore "
        "\"Unknown\" here. Note: `occupant_name` is correctly null (all 3 "
        "agents agreed) — no correction needed there.",
    ),
    (
        "TT138",
        "notes_from_pm",
        "Overseer of the garden in the Ramesseum in the estate of Amūn. "
        "Temp. Ramesses II. (CHAMPOLLION, No. 29.) Wife, Neshaʿ.",
        "PM I.1 p.251 / physical PDF p.269 (TT138 Nezemger). Source OCR "
        "`Wife, Nesha(` — the `(` is OCR rendering of ayin-hook `ʿ`, giving "
        "`Neshaʿ`. Agents A+B emitted `Neshaʿ` (ayin correct); agent C "
        "emitted `Nesha` (ayin dropped). Agent C won the tie on macron-Ū "
        "+ CHAMPOLLION uppercase + mid-sentence citation axes; the ayin on "
        "the wife's name must be restored per verbatim-preserve policy for "
        "notes_from_pm.",
    ),
    (
        "TT139",
        "notes_from_pm",
        "wʿab-priest in front, First royal son in front of Amūn, Overseer "
        "of peasants of Amūn. Temp. Amenophis III. Father, Sheroy, Prophet "
        "of Ptaḥ and Ḥatḥor. Wife, Ḥenutnefert.",
        "PM I.1 p.252 / physical PDF p.270 (TT139 Pairi). Source OCR "
        "`warb-priest` = `wʿab-priest` (same OCR-ayin rendering class as "
        "TT113/TT114/TT135). Tie-break pinned agent C `Wab-priest` (correct "
        "Amūn macrons + Ptaḥ/Ḥatḥor/Ḥenutnefert underdots). Restore: "
        "(1) ayin before `a` → `wʿab`; (2) sentence-initial lowercase `w` "
        "per PM body-prose convention. Full correction: `Wab-priest` → "
        "`wʿab-priest`.",
    ),
    (
        "TT140",
        "notes_from_pm",
        "probably called Ḥefia, Goldworker, Portrait sculptor. "
        "Temp. Tuthmosis III to Amenophis II. Wife, Tauy.",
        "PM I.1 p.254 / physical PDF p.272 (TT140 Neferronpet). Source OCR "
        "p.272 `H7, probably called ~EFIA` and scene caption "
        "`[Deceased as l):.efia and wife.]` — `l):` is the OCR rendering of "
        "underdot-Ḥ (same class as `l:Iatl:lor` = `Ḥatḥor` in TT139). "
        "Confirms PM-faithful alt-name is `Ḥefia` with underdot-ḥ. "
        "Tie-break pinned agent A `probably called Kefia` (correct lowercase + "
        "no headword-prefix convention); `Kefia` is an OCR misread (K for Ḥ). "
        "Restore `Kefia` → `Ḥefia` in notes_from_pm per verbatim-preserve "
        "policy. Note: occupant_alt_names uses ḥ-stripped `Hefia` per the "
        "TT57/TT120 matchable-name strip-ḥ rule — no correction needed there.",
    ),
]

CHUNK22_RENAMES: dict[str, str] = {}


# Chunk-23 corrections (TT141–TT150): egyptologist-cited merge-output fixes.
#
# Three entries needed after the chunk-23 merge:
#
# 1. TT141 notes_from_pm — tie-break pinned agent B's `Wab-priest` (best
#    macron+ayin skeleton). Restore ayin + lowercase initial per the
#    TT14/TT68/TT97/TT113/TT114/TT135/TT139 ayin-before-a precedent.
#    PM I.1 p.254 source OCR `warb-priest` = `wʿab-priest` (same OCR
#    rendering class).
#
# 2. TT143 occupant_role — all 3 agents correctly emitted
#    occupant_role="Unknown" (PM headword: `Name lost. Temp. Tuthmosis III
#    to Amenophis II (?).`, no personal name given). merge.py
#    SENTINEL_NULL_STRINGS coerces the literal string "Unknown" to JSON
#    null. Restore "Unknown" per the TT136 (chunk-22), TT116 (chunk-20),
#    TT70 (chunk-15), TT58 (chunk-14) precedent.
#
# 3. TT147 occupant_role — same class as TT143: PM headword has no personal
#    name for this tomb. All 3 agents correctly emitted "Unknown", then
#    SENTINEL_NULL coercion dropped it. Restore.
CHUNK23_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT141",
        "notes_from_pm",
        "wʿab-priest of Amūn. Ramesside. Wife, Takhaʿ(t).",
        "PM I.1 p.254 / physical PDF p.272 (TT141 Bekenkhons). Source OCR "
        "`warb-priest` = `wʿab-priest` (ayin-hook before `a`, same OCR "
        "rendering class as TT113/TT114/TT135/TT139 where `wʿab` was "
        "established by TT14/TT68/TT97 precedent). Tie-break pinned agent B "
        "`Wab-priest of Amūn` (best macron-Ū + ayin-on-wife skeleton). "
        "Restore: (1) ayin before `a` → `wʿab`; (2) sentence-initial lowercase "
        "`w` per PM body-prose convention. Full correction: `Wab-priest` → "
        "`wʿab-priest`.",
    ),
    (
        "TT143",
        "occupant_role",
        "Unknown",
        "PM I.1 p.255 / physical PDF p.273 (TT143, anonymous tomb). PM headword "
        "carries no personal name (`Name lost.`); all 3 agents correctly emitted "
        "occupant_role=\"Unknown\" (controlled-vocab sentinel for rows with no "
        "identified occupant, paired with occupant_name=null per schema invariant). "
        "merge.py SENTINEL_NULL_STRINGS coerces the literal string \"Unknown\" to "
        "JSON null. Restore \"Unknown\" per the TT136 (chunk-22), TT116 (chunk-20), "
        "TT70 (chunk-15), TT58 (chunk-14) class precedent.",
    ),
    (
        "TT147",
        "occupant_role",
        "Unknown",
        "PM I.1 p.258 / physical PDF p.276 (TT147, anonymous tomb). PM headword "
        "has no personal name; all 3 agents correctly emitted occupant_role=\"Unknown\" "
        "(controlled-vocab sentinel paired with occupant_name=null). merge.py "
        "SENTINEL_NULL_STRINGS coerces \"Unknown\" to null. Restore per the same "
        "TT143/TT136/TT116/TT70/TT58 class precedent.",
    ),
]

CHUNK23_RENAMES: dict[str, str] = {}


# Chunk-24 corrections (TT151–TT160): egyptologist-cited merge-output fixes.
#
# Three entries needed after the chunk-24 merge:
#
# 1. TT151 notes_from_pm — tie-break pinned agent C's skeleton (no OCR garbage,
#    has Parents clause per source text line 31 `Paren~Nebnufer`). Agent C had
#    `Amun` (no macron). Restore `Amun` → `Amūn` per PM verbatim policy for the
#    Amūn deity name. Same macron-restore class as TT141-TT150 cluster (chunk-23).
#
# 2. TT152 occupant_role — all 3 agents correctly emitted occupant_role="Unknown"
#    (controlled-vocab sentinel for anonymous tombs paired with occupant_name=null).
#    merge.py SENTINEL_NULL_STRINGS coerces the literal string "Unknown" to null.
#    Restore per TT143/TT147 (chunk-23), TT136 (chunk-22), TT116 (chunk-20),
#    TT70 (chunk-15), TT58 (chunk-14) class precedent.
#
# 3. TT153 occupant_role — same class as TT152: PM headword has no personal
#    name; all agents emitted occupant_role="Unknown"; SENTINEL_NULL_STRINGS
#    coerces to null. Restore per same precedent chain.
CHUNK24_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT151",
        "notes_from_pm",
        "Scribe, Counter of cattle of the god's wife of Amūn, Steward of the god's wife. Temp. Tuthmosis IV. (Unfinished.) Wife, Nefertere. Parents, Nebnufer.",
        "PM I.1 p.261 / physical PDF p.279 (TT151 Hety, Scribe). Tie-break pinned "
        "agent C as best skeleton (no OCR garbage `Men:;;:`, has Parents clause "
        "confirmed by source OCR line 31 `Paren~Nebnufer`). Agent C had `Amun` "
        "(no macron). Restore `Amun` → `Amūn` for the deity name per PM verbatim "
        "policy (macron-ū retained in body prose, same class as TT141/TT142/TT146/"
        "TT147/TT148/TT149/TT150 in chunk-23 and TT22/TT23 cluster in earlier chunks).",
    ),
    (
        "TT152",
        "occupant_role",
        "Unknown",
        "PM I.1 p.262 / physical PDF p.280 (TT152, anonymous tomb). PM headword "
        "carries no personal name (`Name lost.`); all 3 agents correctly emitted "
        "occupant_role=\"Unknown\" (controlled-vocab sentinel for rows with no "
        "identified occupant, paired with occupant_name=null per schema invariant). "
        "merge.py SENTINEL_NULL_STRINGS coerces the literal string \"Unknown\" to "
        "JSON null. Restore \"Unknown\" per TT143/TT147 (chunk-23), TT136 (chunk-22), "
        "TT116 (chunk-20), TT70 (chunk-15), TT58 (chunk-14) class precedent.",
    ),
    (
        "TT153",
        "occupant_role",
        "Unknown",
        "PM I.1 p.262 / physical PDF p.280 (TT153, anonymous tomb). PM headword "
        "has no personal name; all 3 agents correctly emitted occupant_role=\"Unknown\" "
        "(controlled-vocab sentinel paired with occupant_name=null). merge.py "
        "SENTINEL_NULL_STRINGS coerces \"Unknown\" to null. Restore per the same "
        "TT152/TT143/TT147/TT136/TT116/TT70/TT58 class precedent.",
    ),
]

CHUNK24_RENAMES: dict[str, str] = {}


# Chunk-25 corrections (TT161–TT170): merge-output fixes.
#
# 1. TT167 occupant_role — all 3 agents correctly emitted occupant_role="Unknown"
#    (controlled-vocab sentinel for rows with no identified occupant, paired with
#    occupant_name=null per schema invariant). merge.py SENTINEL_NULL_STRINGS
#    coerces the literal string "Unknown" to JSON null. Restore "Unknown" per
#    TT152/TT153 (chunk-24), TT143/TT147 (chunk-23), TT136 (chunk-22),
#    TT116 (chunk-20), TT70 (chunk-15), TT58 (chunk-14) class precedent.
CHUNK25_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT167",
        "occupant_role",
        "Unknown",
        "PM I.1 p.278 (TT167, anonymous unfinished tomb). PM headword carries no "
        "personal name (`Name lost.`); all 3 agents correctly emitted "
        "occupant_role=\"Unknown\" (controlled-vocab sentinel paired with "
        "occupant_name=null per schema invariant). merge.py SENTINEL_NULL_STRINGS "
        "coerces \"Unknown\" to null. Restore per TT152/TT153 (chunk-24), "
        "TT143/TT147 (chunk-23), TT136 (chunk-22), TT116 (chunk-20), TT70 "
        "(chunk-15), TT58 (chunk-14) class precedent.",
    ),
]

CHUNK25_RENAMES: dict[str, str] = {}

CHUNK26_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT171",
        "occupant_role",
        "Unknown",
        "PM I.1 p.279 (TT171, anonymous Dyn. XVIII tomb, Sh. ʿAbd el-Qurna). "
        "PM headword carries no personal name (`Name lost.`); all 3 agents "
        "correctly emitted occupant_role=\"Unknown\" (controlled-vocab sentinel "
        "paired with occupant_name=null per schema invariant). merge.py "
        "SENTINEL_NULL_STRINGS coerces \"Unknown\" to null. Restore per TT167 "
        "(chunk-25), TT152/TT153 (chunk-24), TT143/TT147 (chunk-23), TT136 "
        "(chunk-22), TT116 (chunk-20), TT70 (chunk-15), TT58 (chunk-14) "
        "class precedent.",
    ),
    (
        "TT175",
        "occupant_role",
        "Unknown",
        "PM I.1 p.281 (TT175, anonymous tomb, Khokha). PM headword carries no "
        "personal name (`No name.`); all 3 agents correctly emitted "
        "occupant_role=\"Unknown\" (controlled-vocab sentinel paired with "
        "occupant_name=null per schema invariant). merge.py SENTINEL_NULL_STRINGS "
        "coerces \"Unknown\" to null. Restore per TT171 (this chunk), TT167 "
        "(chunk-25), TT152/TT153 (chunk-24) class precedent.",
    ),
    (
        "TT180",
        "occupant_role",
        "Unknown",
        "PM I.1 p.286 (TT180, anonymous unfinished tomb, Khokha). PM headword "
        "carries no personal name (`No name.`); all 3 agents correctly emitted "
        "occupant_role=\"Unknown\" (controlled-vocab sentinel paired with "
        "occupant_name=null per schema invariant). merge.py SENTINEL_NULL_STRINGS "
        "coerces \"Unknown\" to null. Restore per TT171/TT175 (this chunk), "
        "TT167 (chunk-25), TT152/TT153 (chunk-24) class precedent.",
    ),
]

CHUNK26_RENAMES: dict[str, str] = {}


# Chunk-27 (TT181–TT190, Khôkha + ʿAsâsîf). Five PDF-verified corrections
# applied post-merge, all verbatim-preserve restorations against PM I.1:
#
# 1. TT181 — `occupant_name`: PM p.286 headword prints `NEBAMŪN` with
#    capital macron-Ū. Same pypdf capital-macron-drop OCR class as TT65
#    `NEBAMŪN` (chunk-15) and TT17 `NEBAMŪN` (chunk-10). All 3 agents
#    emitted `Nebamun`; restore macron-Ū.
# 2. TT181 — `notes_from_pm`: tie-break pinned agent A's form which carries
#    two errors the PDF resolves: (a) `Nebamon` → `Nebamūn` (macron +
#    correct `un` ending — PM p.286 prints `NEBAMŪN` headword); (b)
#    `Senennoter` → `Senennūter` (macron-Ū — PM p.286 prints `Senennūter`
#    with macron-Ū; the `no`→`ū` is a clear OCR misread of the macron
#    over the `ū`).
# 3. TT187 — `notes_from_pm`: tie-break pinned agent A's `Wab-priest`
#    (PM-faithful for the role-token but capitalized). PM p.293 prints
#    `wʿab-priest of Amūn. Dyn. XIX.` (OCR text-layer renders the printed
#    `wʿab-priest` as `warb-priest`). Three restorations: (a) `Wab-priest`
#    → `wʿab-priest` (insert U+02BF ayin + lowercase sentence-initial per
#    chunk-22 TT113 ayin-before-a precedent); (b) `Amun` → `Amūn`
#    (macron-Ū per chunk-12-onward verbatim-preserve); (c) `<Ashakhet`
#    → `ʿAshakhet` (ayin whitelist).
# 4. TT189 — `notes_from_pm`: tie-break pinned agent A's `Neteḥab` (closest
#    to PM-faithful). PM p.295 prints `Netemḥab` (underdot-H, with `m`).
#    Restore the missing `m` + add macron-Ū to `Amūn` ×2 per the
#    verbatim-preserve policy (same chunk-12-onward macron-retain class).
# 5. TT190 — `notes_from_pm`: tie-break pinned agent C's `Meramuniotes` and
#    `Amen-Re`. PM p.297 prints `Meramūniotes` (macron-Ū) and `Amen-rēʿ`
#    (macron-ē + ayin). Restore both diacritics.
CHUNK27_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT181",
        "occupant_name",
        "Nebamūn",
        "PM I.1 p.286 / physical PDF p.304 headword prints `NEBAMŪN` with "
        "capital macron-Ū. Same pypdf capital-macron-drop OCR class as "
        "chunk-10 TT17 `NEBAMŪN`, chunk-15 TT65 `NEBAMŪN` — all 3 agents "
        "emitted `Nebamun` (macron stripped). Restore macron-Ū per "
        "PM-faithful diacritic policy (preserve vowel macrons in "
        "occupant_name; only underdot-Ḥ is stripped).",
    ),
    (
        "TT181",
        "notes_from_pm",
        "Head sculptor of the Lord of the Two Lands, and Ipuky, Sculptor "
        "of the Lord of the Two Lands. Temp. Amenophis III to IV. Parents "
        "(of Nebamūn), Neferḥet and Thepu; (of Ipuky), Senennūter and "
        "Netermosi. Wife of Ipuky (and probably of Nebamūn), Ḥenutnefert.",
        "PM I.1 p.286 / physical PDF p.304. Two diacritic restorations on "
        "the tie-break-pinned agent-A form: (a) `Nebamon` → `Nebamūn` "
        "×2 — PM headword prints `NEBAMŪN` with macron-Ū (same OCR-drop "
        "class as occupant_name fix above); PM's parenthetical form of "
        "the name also carries the macron. (b) `Senennoter` → `Senennūter` "
        "— PM p.286 prints `Senennūter` with macron-Ū on the ū; the OCR "
        "text-layer rendered the macron-ū cluster as `no` (standard "
        "macron-drop within a consonant cluster). Verbatim-preserve "
        "policy on notes_from_pm per the chunk-9 KV55 / chunk-10 TT16 "
        "macron-preserve precedent.",
    ),
    (
        "TT187",
        "notes_from_pm",
        "wʿab-priest of Amūn. Dyn. XIX. Parents, ʿAshakhet (tomb 174) "
        "and Tazabu. Wife, Mutemonet.",
        "PM I.1 p.293 / physical PDF p.311 (TT187 PAKHIḤET) prints "
        "`wʿab-priest of Amūn. Dyn. XIX.` (the printed-book form). "
        "The OCR text-layer renders this as `warb-priest of Amlin.` "
        "All 3 agents emitted `Wab-priest` (capital-W, no ayin). "
        "Three restorations: (a) `Wab-priest` → `wʿab-priest` — "
        "insert U+02BF ayin + lowercase sentence-initial per "
        "chunk-22 TT113 + chunk-23 TT141 + chunk-26 ayin-before-a "
        "precedent (PM body-prose sentence-initial lowercase preserved "
        "per source verbatim, not auto-capitalized). (b) `Amun` → "
        "`Amūn` — PM body-prose macron-Ū per chunk-12-onward "
        "macron-retain class (same as TT184, TT189). (c) `<Ashakhet` "
        "→ `ʿAshakhet` — PM OCR raised-ayin glyph `<` → U+02BF per "
        "postprocess whitelist. Verbatim-preserve policy on "
        "notes_from_pm. Gemini PR #271 round 1 finding 3279424043.",
    ),
    (
        "TT189",
        "notes_from_pm",
        "Overseer of carpenters of the northern lake of Amūn, Head of "
        "goldworkers in the estate of Amūn. Temp. Ramesses II. Wives, "
        "Netemḥab and Tentpa...",
        "PM I.1 p.295 / physical PDF p.313 (TT189 Nekht-Ḏhout). Two "
        "restorations on the tie-break-pinned agent-A form: (a) `Neteḥab` "
        "→ `Netemḥab` — PM p.295 prints `Netemḥab` (underdot-H with "
        "`m`); agent A's OCR shortening dropped the `m`. (b) `Amun` × 2 "
        "→ `Amūn` × 2 — PM prints `Amūn` with macron-Ū in body prose "
        "(same chunk-12-onward macron-retain class as TT184, TT187 etc.). "
        "Verbatim-preserve policy on notes_from_pm.",
    ),
    (
        "TT190",
        "notes_from_pm",
        "Divine father, Prophet of the head of the King. Saite (usurped "
        "from a Ramesside tomb). Parents, Pakharkhons, Divine father, and "
        "Meramūniotes, Sistrum-player of Amen-rēʿ. Wife, Tanub.",
        "PM I.1 p.297 / physical PDF p.315 (TT190 Esbanebded). Two "
        "diacritic restorations on the tie-break-pinned agent-C form: "
        "(a) `Meramuniotes` → `Meramūniotes` — PM p.297 prints "
        "`Meramūniotes` with macron-Ū; agent C stripped the macron. "
        "(b) `Amen-Re` → `Amen-rēʿ` — PM p.297 prints `Amen-rēʿ` with "
        "macron-ē + ayin (standard PM rendering of the Amen-Re solar form "
        "in body prose); agents A+B have lowercase `Amen-re`, agent C "
        "has `Amen-Re` (capital R — heading artefact). Verbatim-preserve "
        "policy on notes_from_pm per the chunk-3/7 macron-preserve "
        "precedent (KV45/KV46/DAN-Neferhotep all preserve macrons in "
        "notes fields).",
    ),
]


CHUNK27_RENAMES: dict[str, str] = {}


# === Audit-fix migration (issue: occupant_alt_names misuse) ==================
#
# Pre-PR-A audit (2026-05-02) found two distinct schema misuses in PM rows:
#
# Shape A — tomb nicknames stuffed in `occupant_alt_names` (which is meant
# for alternate name forms of the SAME PERSON, e.g. throne-name vs personal-
# name). Affected rows (4): KV9, KV11, KV17, KV23. The strings are aliases
# of the TOMB (Belzoni's tomb, Bruce's tomb, local Arabic surveyor names),
# not of its occupant.
#
# Shape B — joint occupants compounded into a single `occupant_name` string
# with `" and "` / `", and "` (KV46 Yuia+Thuiu, SWV Three Princesses Menhet
# +Merti+Menwi). The compound string is unjoinable against any king/person
# authority and the per-occupant role is lost in the aggregate "Royal
# Family" label.
#
# Fix:
#   - Add `tomb_aliases: list[str]` field for tomb nicknames.
#   - Add `co_occupants: list[{name, role, alt_names}]` field for additional
#     people buried in the same tomb. Headword stays as the row-level
#     `occupant_name` / `occupant_role` / `occupant_alt_names` triplet.
#   - Migrate existing rows via SCHEMA_FIELD_DEFAULTS (adds the missing
#     fields with `[]` defaults) + AUDIT_FIX_CORRECTIONS (moves values from
#     `occupant_alt_names`/`occupant_name` to the correct fields).
#
# `occupant_alt_names` retains its honest meaning post-fix: ONLY alternate
# readings of the SAME person's name (prenomens like the chunk-7 DAN-Antef
# rows; transliteration variants; throne-name vs birth-name pairs).
# `valley` → `theban_area` field rename (PR #170, 2026-05-02). The rename
# was a pure key change applied to `reconciled.jsonl` directly + every
# prompt + every test, but the per-chunk agent JSONLs were NOT updated
# (they remain the stable record of each round of agent extraction).
# Re-running `merge.py` therefore regenerates rows with the OLD `valley`
# key — restoring the old field name. This migration runs in `main()`
# before `SPOT_CORRECTIONS` to rename the key on every row that still
# carries it. Idempotent: a row that already has `theban_area` is
# untouched. Per CLAUDE.md rule 3 (deterministic-enforcement-over-
# convention), the rename's "convention" of "always edit reconciled.jsonl
# directly when renaming a key" needs a code-level enforcement so re-
# merge doesn't silently regress.
LEGACY_FIELD_RENAMES: dict[str, str] = {
    "valley": "theban_area",
}


SCHEMA_FIELD_DEFAULTS: dict[str, object] = {
    "tomb_aliases": [],
    "co_occupants": [],
    # PR A round-2 (egyptologist P1): explicit flag for joint coordinate
    # burials where PM does NOT mark a principal occupant. Default False
    # — the ordinary case is one tomb, one occupant (or one headword +
    # subordinate co-occupants). When True, downstream consumers MUST
    # treat `occupant_name` and `co_occupants[*].name` as a coordinate
    # union for join purposes — the headword is a serialisation artifact,
    # not a primacy claim. SWV-ThreePrincesses is the canonical case
    # (PM lists Menhet/Merti/Menwi coordinately at p.591); KV46 is NOT
    # (PM's syntactic-coordinate construction at p.562 marks Yuia as the
    # subject — `YUIA ..., Divine father, AND THUIU ...`).
    "is_joint_burial": False,
    # === Issue #182 schema-audit additions (Tier 3, all P2) ============
    # Shape J P2: typed flags that PM marks via prose annotations on
    # `notes_from_pm` rather than as structured fields. Each flag is
    # mechanically derivable from a stable PM convention.
    #
    # `is_uninscribed`: PM literally writes "uninscribed" on the row.
    # Pinned canonical set in the migration code below.
    "is_uninscribed": False,
    # `is_usurped`: PM literally writes "usurped" / "usurpation" on the
    # row. Pinned canonical set: KV9 (doorways usurped from Ramesses V)
    # + KV14 (usurped by Setnakht).
    "is_usurped": False,
    # `attribution_certainty`: enum {"attested", "probable", "uncertain"}
    # — derived from PM's hedge tokens ("Probably", "(probably)",
    # "tentatively", "uncertain", "perhaps", "attributed to") in
    # `notes_from_pm`. Default "attested".
    "attribution_certainty": "attested",
}


AUDIT_FIX_CORRECTIONS: list[tuple[str, str, object, str]] = [
    # ---- Shape A: tomb nicknames moved from occupant_alt_names → tomb_aliases.
    (
        "KV9",
        "tomb_aliases",
        ["Tomb of Metempsychosis", "Tomb of Memnon"],
        "Audit-fix (PR A): the strings 'Tomb of Metempsychosis' and 'Tomb "
        "of Memnon' are 19th-c. classical-traveller nicknames for the TOMB "
        "(Ramesses VI's KV9 was misidentified as Memnon's by early "
        "European travellers), not alternate names of the occupant. "
        "Migrated from occupant_alt_names to the new tomb_aliases field. "
        "PM I.2 p.511 prints these in the headword parenthetical "
        "`('Tomb of Metempsychosis', or 'Tomb of Memnon'. ...)`.",
    ),
    (
        "KV9",
        "occupant_alt_names",
        [],
        "Audit-fix (PR A): cleared after migrating tomb-nicknames to "
        "tomb_aliases. Ramesses VI's prenomen `Nebmaatre-Meryamun` "
        "(printed in PM as a hieroglyphic cartouche only, not as a "
        "transcribed English variant) lives in pharaoh.se's authority "
        "record, not in this row's `occupant_alt_names`. PR A round-2 "
        "egyptologist clarification: empty list is correct here for "
        "what PM prints in transcribed form.",
    ),
    (
        "KV9",
        "notes_from_pm",
        "doorways in outer part usurped from Ramesses V.",
        "PR A round-2 (egyptologist P2): restore the trailing period to "
        "match PM I.2 p.511's sentence-final punctuation and the fix_rows "
        "policy already applied to KV10 (`Inaccessible after Corridor B.`). "
        "Pre-PR-A this row read without the period; one-character "
        "punctuation drift relative to PM's printed text.",
    ),
    (
        "KV11",
        "tomb_aliases",
        ["Bruce's tomb", "the Harper's tomb"],
        "Audit-fix (PR A): 'Bruce's tomb' (after James Bruce, who entered "
        "it 1768) and 'the Harper's tomb' (after the famous painted "
        "harpist scene) are 19th-c. nicknames for the TOMB, not for "
        "Ramesses III. Migrated to tomb_aliases. PM I.2 p.518 headword.",
    ),
    (
        "KV11",
        "occupant_alt_names",
        [],
        "Audit-fix (PR A): cleared after migrating tomb-nicknames to "
        "tomb_aliases.",
    ),
    (
        "KV17",
        "tomb_aliases",
        ["Belzoni's tomb"],
        "Audit-fix (PR A): 'Belzoni's tomb' refers to Giovanni Battista "
        "Belzoni, the tomb's 1817 discoverer — a TOMB-name, not an "
        "alternate name of Sethos I. Migrated to tomb_aliases. PM I.2 "
        "p.535 headword.",
    ),
    (
        "KV17",
        "occupant_alt_names",
        [],
        "Audit-fix (PR A): cleared after migrating tomb-nicknames to "
        "tomb_aliases.",
    ),
    (
        "KV23",
        "tomb_aliases",
        ["Eesa", "Schai"],
        "Audit-fix (PR A): 'Eesa' is the local Arabic name for Ay's "
        "tomb cited by Wilkinson in his West-Valley topography ('W. -2 "
        "(\"Eesa\")'); 'Schai' is the Prisse / Nestor L'Hôte surveyor "
        "designation for the same tomb. Both are TOMB-names from "
        "19th-c. survey traditions, not alternate names of the king Ay. "
        "Migrated to tomb_aliases. PM I.2 p.550 headword bibliographic "
        "ribbon.",
    ),
    (
        "KV23",
        "occupant_alt_names",
        [],
        "Audit-fix (PR A): cleared after migrating tomb-nicknames to "
        "tomb_aliases.",
    ),
    # ---- Shape B: joint occupants split into headword + co_occupants.
    (
        "KV46",
        "occupant_name",
        "Yuia",
        "Audit-fix (PR A): split compound 'Yuia and Thuiu' into headword + "
        "co_occupants. PM I.2 p.562 lists Yuia first ('YUIA ..., Divine "
        "father, and THUIU ...'), so Yuia is the headword. Thuiu moves "
        "to co_occupants below.",
    ),
    (
        "KV46",
        "occupant_role",
        "Official",
        "Audit-fix (PR A): per-person role replaces the aggregate 'Royal "
        "Family' label. Yuia's title in PM is 'Divine father' (it-ntr) — "
        "the standard Egyptian honorific given to the non-royal father "
        "of a king's wife (here Queen Teye, wife of Amenhotep III). This "
        "is a court title for a non-royal in-law, not a royal-family "
        "designation. Role = 'Official'.",
    ),
    (
        "KV46",
        "co_occupants",
        [
            {
                "name": "Thuiu",
                "role": "Official",
                "alt_names": [],
            }
        ],
        "Audit-fix (PR A): Thuiu is the second occupant (wife of Yuia, "
        "mother of Queen Teye). PM I.2 p.562 gives her title as 'Chief of "
        "the harîm of Amūn', a religious-administrative court office for "
        "a non-royal. Role = 'Official' (parallel to Yuia). No alternate "
        "names attested in PM headword.",
    ),
    (
        "KV46",
        "is_joint_burial",
        False,
        "PR A round-2 (egyptologist P1): NOT a joint coordinate burial. "
        "PM I.2 p.562 prints `YUIA ..., Divine father, AND THUIU ..., "
        "Chief of the harîm of Amūn, parents of Queen Teye.` The "
        "syntactic-coordinate construction marks Yuia as the subject + "
        "principal occupant; museum jewellery from this tomb is "
        "conventionally catalogued as 'from the tomb of Yuya and Thuyu' "
        "with Yuya leading. Headword Yuia + co_occupant Thuiu correctly "
        "reflects the asymmetry; no joint-burial flag needed.",
    ),
    (
        "SWV-ThreePrincesses",
        "occupant_name",
        "Menhet",
        "Audit-fix (PR A): split compound 'Menhet, Merti, and Menwi' into "
        "headword + co_occupants. PM I.2 p.591 lists Menhet first; she "
        "becomes the headword, the other two move to co_occupants.",
    ),
    (
        "SWV-ThreePrincesses",
        "co_occupants",
        [
            {
                "name": "Merti",
                "role": "Royal Family",
                "alt_names": [],
            },
            {
                "name": "Menwi",
                "role": "Royal Family",
                "alt_names": [],
            },
        ],
        "Audit-fix (PR A): Merti and Menwi are the second and third "
        "occupants. The conventional scholarly identification is that all "
        "three were minor wives of Tuthmosis III (the Wadi Qubbanet "
        "el-Qirud burial); whether 'wife' / 'queen' / 'princess' is the "
        "correct per-person role is a scholarly call beyond this audit-"
        "fix's scope. Preserved the existing 'Royal Family' aggregate "
        "label across all three; refining per-person roles is a follow-"
        "up for the egyptologist-reviewer once chunk 7 is re-extracted "
        "with the new schema.",
    ),
    (
        "SWV-ThreePrincesses",
        "is_joint_burial",
        True,
        "PR A round-2 (egyptologist P1): TRUE — joint coordinate burial. "
        "PM I.2 p.591 prints `TOMB OF THREE PRINCESSES, MENHET ..., "
        "MERTI ..., AND MENWI ...` — three names listed coordinately on "
        "a single line, with no syntactic primacy marker (compare KV46's "
        "subject-coordinate construction). The choice of Menhet as "
        "headword is a serialisation convention (PM lists her first, "
        "Met catalogues canopic jars 26.8.41a-c first), NOT a primacy "
        "claim. Setting `is_joint_burial=True` signals to downstream "
        "Phase-A that `occupant_name` and `co_occupants[*].name` form a "
        "coordinate union for join purposes — Met canopic jars "
        "26.8.42a-c (Merti) and 26.8.43a-c (Menwi) must NOT be silently "
        "merged onto Menhet's authority record because the row-level "
        "headword is Menhet. Per Lilyquist 2003, *The Tomb of Three "
        "Foreign Wives of Thutmose III*, all three were minor Syrian / "
        "Levantine wives of Tuthmosis III; their non-Egyptian names + "
        "individual canopic-jar sets confirm no hierarchical primacy.",
    ),
]


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
    CHUNK9_CORRECTIONS,
    CHUNK10_CORRECTIONS,
    CHUNK11_CORRECTIONS,
    CHUNK12_CORRECTIONS,
    CHUNK13_CORRECTIONS,
    CHUNK14_CORRECTIONS,
    CHUNK15_CORRECTIONS,
    CHUNK16_CORRECTIONS,
    CHUNK17_CORRECTIONS,
    CHUNK18_CORRECTIONS,
    CHUNK19_CORRECTIONS,
    CHUNK20_CORRECTIONS,
    CHUNK21_CORRECTIONS,
    CHUNK22_CORRECTIONS,
    CHUNK23_CORRECTIONS,
    CHUNK24_CORRECTIONS,
    CHUNK25_CORRECTIONS,
    CHUNK26_CORRECTIONS,
    CHUNK27_CORRECTIONS,
    AUDIT_FIX_CORRECTIONS,
]

# `ALL_RENAMES` aggregates per-chunk `CHUNK<N>_RENAMES` dicts (only chunk 7
# has renames so far; future chunks can define their own `CHUNK<N>_RENAMES`
# and merge it in here). Kept as a separate `main`-function input so the
# rename path stays symmetric to the field-correction path.
ALL_RENAMES: dict[str, str] = {
    **CHUNK7_RENAMES,
    **CHUNK8_RENAMES,
    **CHUNK9_RENAMES,
    **CHUNK10_RENAMES,
    **CHUNK11_RENAMES,
    **CHUNK12_RENAMES,
    **CHUNK13_RENAMES,
    **CHUNK14_RENAMES,
    **CHUNK15_RENAMES,
    **CHUNK16_RENAMES,
    **CHUNK17_RENAMES,
    **CHUNK18_RENAMES,
    **CHUNK19_RENAMES,
    **CHUNK20_RENAMES,
    **CHUNK21_RENAMES,
    **CHUNK22_RENAMES,
    **CHUNK23_RENAMES,
    **CHUNK24_RENAMES,
    **CHUNK25_RENAMES,
    **CHUNK26_RENAMES,
    **CHUNK27_RENAMES,
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


# === Issue #182 schema-audit derivation (Tier 3 P2) ==========================
# Mechanically detect typed flags from PM's prose markers in
# `notes_from_pm`. Pure derivation — no asserted facts beyond what PM
# verbatim records. Idempotent.

_UNINSCRIBED_RE = re.compile(r"\buninscribed\b", re.IGNORECASE)
_USURPED_RE = re.compile(r"\busurp(?:ed|ation)\b", re.IGNORECASE)

# Hedge tokens for `attribution_certainty`. Order matters: more-uncertain
# enums win on compound markers ("perhaps Probably" → "uncertain"). One
# combined regex per enum keeps `_detect_attribution_certainty` to two
# `search` calls instead of six.
# `(?)` is PM's standard attribution-uncertainty glyph (KV42 notes start
# with `(?). Excavated by Loret`, QV60 notes start with `(?). daughter
# of Ramesses II.`). Per Gemini round-2 finding.
_ATTRIBUTION_HEDGE_PATTERNS = [
    ("uncertain", re.compile(
        r"\b(?:uncertain|perhaps|possibly|tentatively)\b|\(\?\)", re.IGNORECASE
    )),
    ("probable", re.compile(
        r"\bprobably\b|\(probably\)|\battributed to\b", re.IGNORECASE
    )),
]


def _detect_attribution_certainty(notes: str | None) -> str:
    """Return enum value derived from PM's hedge tokens.

    Default is `attested`. Stronger uncertainty wins over weaker — if
    both `uncertain` and `probable` markers appear, `uncertain` wins.
    """
    if not notes:
        return "attested"
    for enum_val, pat in _ATTRIBUTION_HEDGE_PATTERNS:
        if pat.search(notes):
            return enum_val
    return "attested"


# Data-driven migration table: (field_name, deriver). Each deriver
# takes `notes` (str | None) and returns the derived value. Adding a
# new typed flag is a one-tuple change. Per Gemini round-3.
_Deriver = Callable[[str | None], bool | str]
_ISSUE_182_DERIVATIONS: list[tuple[str, _Deriver]] = [
    ("is_uninscribed", lambda notes: bool(notes and _UNINSCRIBED_RE.search(notes))),
    ("is_usurped", lambda notes: bool(notes and _USURPED_RE.search(notes))),
    ("attribution_certainty", _detect_attribution_certainty),
]


# Per-row deriver overrides for cases where the regex-based deriver fires
# on a hedge token that PM applies to a SECONDARY clause (a wife / parent /
# child / sibling identification) rather than to the PRIMARY occupant
# attribution. The deriver scans `notes_from_pm` with a context-free regex,
# so it cannot distinguish `(probably) Esi` (qualifying the second wife
# in TT2's headword) from `Probably Hatshepsut II` (qualifying the
# headword's primary attribution).
#
# Each entry (tomb_id, field, value, rationale) overrides the deriver's
# output AFTER the regex pass runs; the rationale must cite the PM page
# and the structural reason the deriver's regex output is incorrect for
# that row. Idempotent: a second run finds the field already at the
# pinned value.
#
# Format mirrors `SPOT_CORRECTIONS` so a future schema/audit pass can
# treat the same shape uniformly. Apply only to rows whose primary
# attribution is fully attested per PM but whose `notes_from_pm`
# contains a hedge in a clearly-secondary clause; do NOT use this to
# soften an attribution PM genuinely hedges.
DERIVER_OVERRIDES: list[tuple[str, str, object, str]] = [
    (
        "TT2",
        "attribution_certainty",
        "attested",
        "PM I.1 p.6 prints `2. KHAʿBEKHNET ..., Servant in the Place of Truth. "
        "Temp. Ramesses II.` — the primary attribution to Khaʿbekhnet is fully "
        "attested. The `(probably)` token in `notes_from_pm` qualifies the "
        "identification of his SECOND WIFE Esi (`Wives, Saḥte ... and (probably) "
        "Esi`), not the headword. The `_detect_attribution_certainty` regex is "
        "context-free and fires on any `(probably)` in notes — which is correct "
        "for primary-attribution hedges (e.g. KV55 `Probably Amenophis IV...`) "
        "but wrong for intra-note secondary-clause hedges. Egyptologist printed-"
        "source review on PR (chunk 9) flagged.",
    ),
    # Chunk-10 attribution_certainty overrides — egyptologist-reviewer pass
    # (this PR). Same TT2-precedent rationale: PM's `(?)` glyph in notes_from_pm
    # qualifies the regnal-date (or in TT17 also a parent's identification),
    # NOT the primary occupant identification. The deriver fires context-free
    # on any `(?)` in notes; per the chunk-9 TT2 precedent, attribution_certainty
    # encodes occupant-identity certainty, not regnal-date certainty. All four
    # PM headwords name the occupant unhedged with the occupational title
    # unhedged.
    (
        "TT12",
        "attribution_certainty",
        "attested",
        "PM I.1 p.24 prints `12. ḤRAY ..., Overseer of the granary of the "
        "King's wife and King's mother ʿAḥḥotp. Temp. Amosis to Amenophis I "
        "(?).` The `(?)` qualifies the regnal-range tail (Amenophis I), not "
        "Hray's identification. Per chunk-9 TT2 precedent.",
    ),
    (
        "TT17",
        "attribution_certainty",
        "attested",
        "PM I.1 p.29 prints `17. NEBAMŪN ..., Scribe and physician of the "
        "King. Temp. Amenophis II (?). ... Parents, Nebseny, Judge, and "
        "Amenḥotp (?).` Both `(?)` qualify (a) the regnal date and (b) the "
        "second parent's identification (Amenḥotp; per PM's `Parents, "
        "<Father>, <Title>, and <Mother>` convention this is the mother). "
        "Neither hedge qualifies Nebamun's identification. Per chunk-9 TT2 "
        "precedent.",
    ),
    (
        "TT19",
        "attribution_certainty",
        "attested",
        "PM I.1 p.32 prints `19. AMENMOSI ..., First prophet of 'Amenophis "
        "of the Forecourt'. Temp. Ramesses I to Sethos I (?).` The `(?)` "
        "qualifies the regnal-range tail (Sethos I), not Amenmosi's "
        "identification. Per chunk-9 TT2 precedent.",
    ),
    (
        "TT20",
        "attribution_certainty",
        "attested",
        "PM I.1 p.34 prints `20. MENTUḤIRKHOPSHEF ..., Fan-bearer, Mayor "
        "of Aphroditopolis. Temp. Tuthmosis III (?).` The `(?)` qualifies "
        "the regnal date, not Mentuhirkhopshef's identification. Per "
        "chunk-9 TT2 precedent.",
    ),
    # Chunk-11 attribution_certainty override — egyptologist-reviewer pass
    # (this PR). Same rationale as the chunk-10 cluster: PM's `(?)` glyph
    # qualifies the regnal date of the USURPER (Mery[amūn]), not Wah's
    # primary occupant identification. The original occupant Wah is fully
    # attested; only the usurpation timing under Tuthmosis III carries
    # the hedge.
    (
        "TT22",
        "attribution_certainty",
        "attested",
        "PM I.1 p.37 prints `22. WAḤ ..., Royal butler. Partly usurped by "
        "Mery[amūn], Eldest son of the King. Temp. Tuthmosis III(?).` The "
        "`(?)` qualifies the regnal date of the USURPER (Mery[amūn]), not "
        "Wah's identification as the original occupant. Wah's primary "
        "attribution is unhedged. Per chunk-9 TT2 + chunk-10 TT12/TT17/"
        "TT19/TT20 precedent that attribution_certainty encodes occupant-"
        "identity certainty, not regnal-date certainty.",
    ),
    # Chunk-13 attribution_certainty overrides — egyptologist + code-reviewer
    # pass (this PR). Same chunk-9-TT2 / chunk-10-cluster / chunk-11-TT22
    # precedent: PM's `(?)` glyph qualifies a regnal-date or a usurper-
    # title token, NOT the primary occupant's identification. The deriver
    # fires context-free on any `(?)` in notes; per the established
    # precedent, attribution_certainty encodes occupant-identity certainty,
    # not regnal-date certainty. The five chunk-13 overrides below all flip
    # the deriver's `uncertain` (or `probable` for TT49's `Probably temp.
    # Ay`) back to the egyptologist-confirmed `attested` for the primary
    # occupant.
    (
        "TT41",
        "attribution_certainty",
        "attested",
        "PM I.1 p.78 prints `41. AMENEMŌPET ..., Chief steward of Amūn "
        "in the Southern City. Temp. Ramesses I to Sethos I(?).` The "
        "`(?)` qualifies the regnal-range tail (Sethos I), not "
        "Amenemōpet's identification. Per chunk-9 TT2 + chunk-10 TT19 "
        "precedent (regnal-range tail hedge).",
    ),
    (
        "TT43",
        "attribution_certainty",
        "attested",
        "PM I.1 p.83 prints `43. NEFERRONPET ..., Overseer of the "
        "kitchen of the Lord of the Two Lands. Temp. Amenophis II(?).` "
        "The `(?)` qualifies the regnal date (Amenophis II), not "
        "Neferronpet's identification. Per chunk-9 TT2 + chunk-10 TT12/"
        "TT19 precedent.",
    ),
    (
        "TT45",
        "attribution_certainty",
        "attested",
        "PM I.1 p.85 prints `45. ḎḤOUT ..., Steward of the First "
        "prophet of Amūn, Mery (tomb 95), temp. Amenophis II. Usurped "
        "by Ḏḥutemḥab, Head of the makers of fine linen(?) of the "
        "estate of Amūn, temp. Ramesses II (?).` Two `(?)` hedges, "
        "BOTH on the usurper's clause: `fine linen(?)` qualifies the "
        "USURPER's title (Ḏḥutemḥab), `Ramesses II (?)` qualifies the "
        "USURPER's regnal date. Neither qualifies Ḏhout's primary "
        "attribution as the original occupant — Ḏhout is unhedged "
        "with the title `Steward of the First prophet of Amūn, Mery, "
        "temp. Amenophis II`. Same usurper-clause structure as "
        "chunk-11 TT22 (Wah usurped by Mery[amūn]); same override "
        "rationale.",
    ),
    (
        "TT46",
        "attribution_certainty",
        "attested",
        "PM I.1 p.86 prints `46. RAʿMOSI ..., Steward, Overseer of "
        "the granaries of Upper and Lower Egypt. Temp. Amenophis III "
        "(?).` The `(?)` qualifies the regnal date (Amenophis III), "
        "not Raʿmosi's identification. Per chunk-9 TT2 + chunk-10 "
        "TT20 precedent (regnal-date hedge).",
    ),
    (
        "TT49",
        "attribution_certainty",
        "attested",
        "PM I.1 p.91 prints `49. NEFERḤOTEP ..., Chief scribe of Amūn. "
        "Probably temp. Ay.` The `Probably` adverb qualifies the regnal "
        "date (temp. Ay), not Neferhotep's identification — Neferhotep "
        "is unhedged with the title `Chief scribe of Amūn`. The deriver "
        "fires `attribution_certainty=\"probable\"` on any `\\bprobably\\b` "
        "match in notes (context-free); this override flips back to "
        "`attested` per the chunk-9 TT2 + chunk-10 TT12/TT17/TT19/TT20 + "
        "chunk-11 TT22 + chunk-13 TT41/TT43/TT45/TT46 precedent that "
        "attribution_certainty encodes occupant-identity certainty, "
        "not regnal-date certainty.",
    ),
    # Chunk-14 attribution_certainty overrides. Same TT2-precedent chain:
    # PM's `(?)` qualifies the regnal-date claim, NOT the primary occupant's
    # identification. Both TT52 and TT54 have unhedged headword attributions;
    # only the temporal qualifier carries the hedge.
    (
        "TT52",
        "attribution_certainty",
        "attested",
        "PM I.1 p.99 prints `52. NAKHT ..., Scribe, Astronomer of Amūn. "
        "Temp. Tuthmosis IV(?).` The `(?)` qualifies the regnal date "
        "(Tuthmosis IV), not Nakht's identification as Scribe/Astronomer "
        "of Amūn. Same regnal-date hedge class as chunk-10 TT12/TT19/TT20 "
        "and chunk-13 TT41/TT43/TT46. Per chunk-9 TT2 precedent.",
    ),
    (
        "TT54",
        "attribution_certainty",
        "attested",
        "PM I.1 p.104 prints `54. ḤUY ..., Sculptor of Amun, temp. "
        "Tuthmosis IV to Amenophis III(?).` The `(?)` qualifies the "
        "regnal-range tail (Amenophis III), not Huy's identification as "
        "Sculptor of Amun. Same regnal-range tail pattern as chunk-10 "
        "TT12/TT19/TT20 and chunk-13 TT41/TT43/TT46. Per chunk-9 TT2 "
        "precedent.",
    ),
    # Chunk-15 attribution_certainty overrides. Same TT2-precedent chain:
    # PM's `(?)` qualifies the regnal-date claim, NOT the primary occupant's
    # identification. TT62, TT65, and TT69 all have unhedged headword
    # attributions; only the temporal qualifier carries the hedge.
    (
        "TT62",
        "attribution_certainty",
        "attested",
        "PM I.1 p.125 prints `62. AMENEMWASKHET ..., Overseer of the "
        "Cabinet. Temp. Tuthmosis III(?).` The `(?)` qualifies the regnal "
        "date (Tuthmosis III), not Amenemwaskhet's identification as "
        "Overseer of the Cabinet. Same regnal-date hedge class as chunk-10 "
        "TT12/TT19/TT20, chunk-13 TT43, chunk-14 TT52. Per chunk-9 TT2 "
        "precedent that attribution_certainty encodes occupant-identity "
        "certainty, not regnal-date certainty.",
    ),
    (
        "TT65",
        "attribution_certainty",
        "attested",
        "PM I.1 p.129 prints `65. NEBAMŪN ..., Scribe of the royal "
        "accounts(?), Overseer of the granary, temp. Ḥatshepsut (?). "
        "Usurped by Imiseba ...` The `(?)` qualifies the regnal date "
        "(Ḥatshepsut), not Nebamun's identification as Scribe/Overseer. "
        "The usurpation by Imiseba (temp. Ramesses IX) is fully attested. "
        "Same regnal-date hedge class as chunk-10 TT12/TT19/TT20, chunk-13 "
        "TT41/TT43, chunk-14 TT52. Per chunk-9 TT2 precedent.",
    ),
    (
        "TT69",
        "attribution_certainty",
        "attested",
        "PM I.1 p.134 prints `69. MENNA ..., Scribe of the fields of the "
        "Lord of the Two Lands of Upper and Lower Egypt. Temp. Tuthmosis "
        "IV(?).` The `(?)` qualifies the regnal date (Tuthmosis IV), not "
        "Menna's identification as Scribe of the fields. Same regnal-date "
        "hedge class as chunk-10 TT12/TT20, chunk-14 TT52. Per chunk-9 TT2 "
        "precedent that attribution_certainty encodes occupant-identity "
        "certainty, not regnal-date certainty.",
    ),
    (
        "TT70",
        "attribution_certainty",
        "attested",
        "PM I.1 p.139 prints `70. Usurped by AMENMOSI ..., Overseer of "
        "sandal-makers(?) of the estate of Amūn ...`. The `(?)` qualifies "
        "the USURPER's title (`sandal-makers(?)` — Amenmosi's title is "
        "uncertain), NOT the primary occupant's identification. The "
        "primary occupant is intentionally null (anonymous original "
        "occupant; see CHUNK15_CORRECTIONS pairing fix). The "
        "attribution_certainty field encodes occupant-identity certainty "
        "per the chunk-9 TT2 precedent — and there is no occupant "
        "identity to hedge. Flip from deriver-fired `uncertain` back to "
        "`attested`. Same usurper-clause hedge class as chunk-11 TT22 "
        "(Wah usurped by Mery[amūn], regnal hedge on usurper's date).",
    ),
    # Chunk-16 attribution_certainty override. Same TT2-precedent chain:
    # PM's `(?)` qualifies the regnal-date range, NOT the primary occupant's
    # identification. TT79's headword names Menkheper unhedged with his
    # occupational titles; only the temporal qualifier `Amenophis II (?)`
    # carries the hedge.
    (
        "TT79",
        "attribution_certainty",
        "attested",
        "PM I.1 p.156 prints `79. MENKHEPER (or MENKHEPERRAʿSONB) ..., "
        "Overseer of the granary of the Lord of the Two Lands, wʿab-"
        "priest in the Mortuary Temple of Tuthmosis III. Temp. Tuthmosis "
        "III to Amenophis II (?).` The `(?)` qualifies the regnal-range "
        "tail (Amenophis II), not Menkheper's identification as Overseer "
        "of the granary / wʿab-priest. Same regnal-range tail hedge class "
        "as chunk-10 TT12/TT19/TT20, chunk-13 TT41/TT43/TT46, chunk-14 "
        "TT52/TT54, chunk-15 TT62/TT65/TT69. Per chunk-9 TT2 precedent "
        "that attribution_certainty encodes occupant-identity certainty, "
        "not regnal-date certainty.",
    ),
    # Chunk-18 is_usurped override (TT95 Mery). Mery is the USURPER of
    # TT84 (PM `(See also usurpation in tomb 84.)` in TT95's headword);
    # he is NOT the usurped party of TT95, which is his own primary
    # tomb. The Tier-3 deriver fires `is_usurped=true` on the `usurp`
    # regex match in `notes_from_pm` (the parenthetical is preserved
    # verbatim per the chunk-9-onward rule). Override post-merge per
    # the same merge-resolves-ties / fix_rows-applies-corrections
    # boundary used for chunk-9 TT2 attribution_certainty.
    (
        "TT95",
        "is_usurped",
        False,
        "PM I.1 p.195 prints `95. MERY ..., First prophet of Amūn. "
        "(See also usurpation in tomb 84.)` Mery is the USURPER of "
        "TT84 (Amunezeḥ — chunk-17 TT84 row carries `Partly usurped by "
        "MERY`), NOT the usurped party at TT95. The `is_usurped` "
        "regex `\\busurp(?:ed|ation)\\b` fires on the `usurpation` "
        "token in TT95's preserved parenthetical. Override to "
        "`is_usurped=false` per the structural distinction: TT95 is "
        "Mery's primary tomb, the cross-reference points to his "
        "later usurpation of TT84 (a different tomb). Same chunk-9 "
        "TT2 precedent class — Tier-3 regex fires context-free; "
        "egyptologist-cited override pins the correct value.",
    ),
    # Chunk-18 attribution_certainty overrides. Same regnal-range hedge class
    # as chunks 10, 13, 14, 15, 16 above. PM's `Temp. <King> (?)` qualifies
    # the dating, not the occupant's identification — all three rows have
    # unhedged primary attribution to a named occupant with named title.
    (
        "TT94",
        "attribution_certainty",
        "attested",
        "PM I.1 p.194 prints `94. RAʿMOSI ..., called ʿAMY ..., First "
        "royal herald, Fan-bearer on the right of the King. Temp. "
        "Amenophis II (?).` The `(?)` qualifies the regnal-date "
        "(Amenophis II), not the occupant identification. Per chunk-9 "
        "TT2 precedent.",
    ),
    (
        "TT97",
        "attribution_certainty",
        "attested",
        "PM I.1 p.203 prints `97. AMENEMḤET ..., First prophet of "
        "Amūn. Temp. Amenophis II (?).` The `(?)` qualifies the "
        "regnal-date (Amenophis II), not the occupant identification. "
        "Per chunk-9 TT2 precedent.",
    ),
    (
        "TT98",
        "attribution_certainty",
        "attested",
        "PM I.1 p.204 prints `98. KAEMḤERIBSEN ..., Third prophet of "
        "Amūn. Temp. Tuthmosis III to Amenophis II (?).` The `(?)` "
        "qualifies the regnal-range tail (Amenophis II), not the "
        "occupant identification. Per chunk-9 TT2 precedent. Note: "
        "the `(Inaccessible.)` parenthetical on the sub-site line is "
        "preserved verbatim in `notes_from_pm` per the chunk-12 TT47 "
        "tomb-state-marker precedent — does not affect this override.",
    ),
    # Chunk-19 attribution_certainty overrides. TT108 is a regnal-date hedge
    # (same class as TT52/TT69 etc.); TT110 is a parent-identification hedge
    # in a secondary clause (same class as TT17 Amenḥotp (?)). Both occupants
    # are named and titled without hedge in the PM headword itself.
    (
        "TT108",
        "attribution_certainty",
        "attested",
        "PM I.1 p.225 prints `108. NEBSENY ..., First prophet of Onuris. "
        "Temp. Tuthmosis IV(?).` The `(?)` qualifies the regnal date "
        "(Tuthmosis IV), not Nebseny's identification as First prophet of "
        "Onuris. Same regnal-date hedge class as chunk-10 TT12/TT19/TT20, "
        "chunk-13 TT43, chunk-14 TT52, chunk-15 TT69. Per chunk-9 TT2 "
        "precedent that attribution_certainty encodes occupant-identity "
        "certainty, not regnal-date certainty.",
    ),
    (
        "TT110",
        "attribution_certainty",
        "attested",
        "PM I.1 p.227 prints `110. ḎHOUT ..., Royal butler, Royal herald. "
        "Temp. Ḥatshepsut to Tuthmosis III. Parents, Pesediri (?) and Keku.` "
        "The `(?)` qualifies the identification of the PARENT Pesediri — a "
        "secondary-clause family hedge, not the primary occupant attribution. "
        "Ḏhout's identification as Royal butler / Royal herald temp. Ḥatshepsut "
        "to Tuthmosis III is fully attested. Same family-name identification "
        "hedge class as chunk-10 TT17 (`Amenḥotp (?)`). Per chunk-9 TT2 "
        "precedent that attribution_certainty encodes occupant-identity "
        "certainty, not secondary-clause family-name certainty.",
    ),
    # Chunk-20 attribution_certainty overrides. TT116 is an anonymous row
    # where (?) qualifies the regnal-date range (Amenophis III), not the
    # occupant identity (there is none to hedge — the occupant is unnamed).
    # TT118 is a named occupant where (?) qualifies the regnal date only.
    # Both follow the regnal-date-hedge class established by chunk-10 cluster
    # (TT12/TT19/TT20) and extended through chunks 13–19.
    (
        "TT116",
        "attribution_certainty",
        "attested",
        "PM I.1 p.233 prints `116. Hereditary prince. Temp. Tuthmosis IV to "
        "Amenophis III (?).` The `(?)` qualifies the regnal-range tail "
        "(Amenophis III), not the occupant's identity — which is fully "
        "attested as an unnamed hereditary prince of the stated period. "
        "Same regnal-date hedge class as chunk-10 TT12/TT19/TT20, chunk-13 "
        "TT41/TT43, chunk-14 TT52, chunk-15 TT69, chunk-17 TT94, chunk-18 "
        "TT97/TT98. Per chunk-9 TT2 precedent that attribution_certainty "
        "encodes occupant-identity certainty, not regnal-date certainty.",
    ),
    (
        "TT118",
        "attribution_certainty",
        "attested",
        "PM I.1 p.233 prints `118. AMENMOSI ..., Fan-bearer on the right of "
        "the King. Temp. Amenophis III (?).` The `(?)` qualifies the regnal "
        "date (Amenophis III), not Amenmosi's identification as Fan-bearer. "
        "Same regnal-date hedge class as chunk-10 TT12/TT19/TT20 and the "
        "TT116 same-chunk override above. Per chunk-9 TT2 precedent.",
    ),
    (
        "TT115",
        "is_uninscribed",
        True,
        "PR #264 round-3 Gemini finding 3277852207: TT115 notes_from_pm "
        "begins `No texts. Dyn. XIX.` — PM's `No texts` is the semantic "
        "equivalent of `uninscribed` for chunk-20-class tombs (a Dyn. XIX "
        "tomb where PM found no inscriptions). The is_uninscribed deriver "
        "regex fires only on the literal word `uninscribed`; this DERIVER_"
        "OVERRIDE extends the typed-flag to PM's `No texts` phrasing per "
        "the chunk-12 TT47 `(Uninscribed.)` precedent (note: TT47 used the "
        "explicit `Uninscribed` token; TT115 uses the synonymous `No texts` "
        "form). Egyptologically equivalent: both flag a tomb where PM "
        "found no inscriptional layer.",
    ),
    # Chunk-21 attribution_certainty overrides. TT121, TT126, TT127, and TT130
    # each carry `(?)` qualifying a regnal date (e.g. `Tuthmosis III (?)` or
    # `Saite (?)`) — a temporal-range hedge, not a primary occupant-identity
    # hedge. All four occupants are named (or in TT126 titled without name) with
    # unhedged attribution in the PM headword proper. Same regnal-date-hedge
    # class as chunk-10 TT12/TT19/TT20, extended through chunks 13–20.
    # Per chunk-9 TT2 precedent: attribution_certainty encodes occupant-identity
    # certainty, not regnal-date certainty.
    (
        "TT121",
        "attribution_certainty",
        "attested",
        "PM I.1 p.235 prints `121. ʿAI;IMOSI ..., First lector of Amūn. "
        "Temp. Tuthmosis III (?).` The `(?)` qualifies the regnal date "
        "(Tuthmosis III), not the identification of ʿAhmosi as First lector "
        "of Amūn. Per chunk-9 TT2 precedent.",
    ),
    (
        "TT126",
        "attribution_certainty",
        "attested",
        "PM I.1 p.241 prints `126. I:IARMOSI ..., Great commander of soldiers "
        "of the estate of Amūn. Saite (?).` The `(?)` qualifies the period "
        "attribution (Saite), not Harmosi's identification. Per chunk-9 TT2 "
        "precedent.",
    ),
    (
        "TT127",
        "attribution_certainty",
        "attested",
        "PM I.1 p.241 prints `127. SENEMI<OI;I ..., Royal scribe, Overseer "
        "of all that grows. Temp. Tuthmosis III (?), usurped in Ramesside "
        "times.` The `(?)` qualifies the regnal date (Tuthmosis III), not "
        "Senemiʿoh's identification. The `usurped in Ramesside times` clause "
        "correctly sets is_usurped=True via the deriver (Senemiʿoh IS the "
        "usurped party, no override needed — contrast TT95 Mery). Per chunk-9 "
        "TT2 precedent.",
    ),
    (
        "TT130",
        "attribution_certainty",
        "attested",
        "PM I.1 p.244 prints `130. MAY ..., Harbour-master in the Southern "
        "City. Temp. Tuthmosis III (?).` The `(?)` qualifies the regnal date "
        "(Tuthmosis III), not May's identification as Harbour-master. Per "
        "chunk-9 TT2 precedent.",
    ),
    # Chunk-22 attribution_certainty override. TT140 Neferronpet: the
    # `probably called Ḥefia` token qualifies the ALT-NAME identification
    # only (PM says the occupant is *probably* also known as Ḥefia — a
    # naming hedge, not an occupant-identity hedge). The headword proper
    # `140. NEFERRONPET H7, ...` attributes the tomb to Neferronpet without
    # any qualification. The _detect_attribution_certainty regex fires
    # context-free on `\bprobably\b` and returns `probable` — incorrect for
    # this row. Per chunk-9 TT2 precedent: attribution_certainty encodes
    # occupant-identity certainty, not alt-name certainty.
    (
        "TT140",
        "attribution_certainty",
        "attested",
        "PM I.1 p.254 prints `140. NEFERRONPET H7, probably called ~EFIA...` "
        "The `probably called` token qualifies the ALT-NAME identification "
        "(`Ḥefia`) only — PM attributes the tomb to Neferronpet without "
        "qualification. The `_detect_attribution_certainty` regex fires "
        "context-free on `\\bprobably\\b` and returns `probable` — incorrect "
        "here. Per chunk-9 TT2 precedent: attribution_certainty encodes "
        "occupant-identity certainty, not alt-name certainty. Same class as "
        "TT49 (`Chief scribe of Amūn. Probably temp. Ay.` — regnal-date hedge "
        "only), TT2 (`(probably) Esi` — second-wife hedge). Override → "
        "`attested`.",
    ),
    # Chunk-23 attribution_certainty overrides. TT142, TT143, TT144, TT146,
    # and TT147 all carry `(?)` qualifying a regnal-date claim in notes_from_pm.
    # The deriver fires context-free on `\(\?\)` → `uncertain`; the correct
    # value is `attested` in all five cases because the `(?)` hedges the
    # temporal qualifier, not the primary occupant attribution (or for the two
    # anonymous tombs TT143/TT147, there is no occupant identity to hedge).
    # Per chunk-9 TT2 precedent extended through chunks 10–22.
    (
        "TT142",
        "attribution_certainty",
        "attested",
        "PM I.1 p.255 prints `142. SIMUT ..., Overseer of works of Amen-reʿ "
        "in Karnak. Temp. Tuthmosis III to Amenophis II (?).` The `(?)` "
        "qualifies the regnal-range tail (Amenophis II), not Simut's "
        "identification as Overseer of works. Same regnal-range tail hedge "
        "class as chunk-10 TT12/TT19/TT20, chunk-13 TT41/TT43/TT46, chunk-14 "
        "TT52/TT54, chunk-15 TT79. Per chunk-9 TT2 precedent that "
        "attribution_certainty encodes occupant-identity certainty, not "
        "regnal-date certainty.",
    ),
    (
        "TT143",
        "attribution_certainty",
        "attested",
        "PM I.1 p.255 (TT143, anonymous tomb). Notes: `Name lost. Temp. "
        "Tuthmosis III to Amenophis II (?).` The `(?)` qualifies the "
        "regnal-range tail (Amenophis II). There is no identified occupant "
        "whose identity could be hedged — the tomb owner is unknown. The "
        "deriver fires `uncertain` on the `(?)` token; correct value is "
        "`attested` (the anonymous assignment to the stated period is the "
        "best-attested reading of the source). Same class as chunk-20 TT116 "
        "(anonymous hereditary prince with regnal-range hedge). Per chunk-9 "
        "TT2 precedent.",
    ),
    (
        "TT144",
        "attribution_certainty",
        "attested",
        "PM I.1 p.257 prints `144. NU ..., Head of the field-labourers. "
        "Temp. Tuthmosis III (?).` The `(?)` qualifies the regnal date "
        "(Tuthmosis III), not Nu's identification as Head of field-labourers. "
        "Same regnal-date hedge class as chunk-10 TT12/TT19/TT20, chunk-13 "
        "TT43/TT46. Per chunk-9 TT2 precedent that attribution_certainty "
        "encodes occupant-identity certainty, not regnal-date certainty.",
    ),
    (
        "TT146",
        "attribution_certainty",
        "attested",
        "PM I.1 p.258 prints `146. NEBAMŪN ..., Overseer of the granary of "
        "Amūn. Temp. Tuthmosis III (?). (Inaccessible.)` The `(?)` qualifies "
        "the regnal date (Tuthmosis III), not Nebamun's identification as "
        "Overseer of the granary. Same regnal-date hedge class as chunk-10 "
        "TT12/TT19/TT20, chunk-13 TT43, chunk-14 TT52. Per chunk-9 TT2 "
        "precedent that attribution_certainty encodes occupant-identity "
        "certainty, not regnal-date certainty.",
    ),
    (
        "TT147",
        "attribution_certainty",
        "attested",
        "PM I.1 p.258 (TT147, anonymous tomb). Notes: `Head of the masters "
        "of ceremonies(?) of Amūn, &c. Temp. Tuthmosis IV(?).` Two `(?)` "
        "hedges: (1) `ceremonies(?)` qualifies the TITLE of the anonymous "
        "occupant (the role label is uncertain); (2) `IV(?)` qualifies the "
        "regnal date (Tuthmosis IV). Neither hedge qualifies an occupant "
        "identity — the occupant is unnamed. The deriver fires `uncertain` "
        "on the `(?)` token(s); correct value is `attested` (the anonymous "
        "assignment with uncertain title is the PM-source reading). Same "
        "anonymous-with-hedge class as TT143 (this chunk) and TT116 "
        "(chunk-20). Per chunk-9 TT2 precedent.",
    ),
    # Chunk-24 attribution_certainty overrides. TT152, TT153, TT154, and TT158
    # all carry hedge tokens in notes_from_pm that qualify temporal/regnal claims,
    # not the primary occupant attribution. The deriver fires context-free on
    # `\(\?\)` and `probably` tokens; per the chunk-9 TT2 precedent extended
    # through chunks 10–23, attribution_certainty encodes occupant-identity
    # certainty, not regnal-date or event-timing certainty.
    (
        "TT152",
        "attribution_certainty",
        "attested",
        "PM I.1 p.262 (TT152, anonymous tomb). Notes: `Name lost, late Dyn. XVIII. "
        "Usurped in Ramesside times(?).` The `(?)` qualifies the temporal claim "
        "about the usurpation timing (`in Ramesside times`), not a primary occupant "
        "identity — the occupant is unnamed. The deriver fires `uncertain` on `(?)`; "
        "correct value is `attested` (PM's best reading of the source for this "
        "anonymous tomb). Same anonymous-tomb-with-event-hedge class as TT143/TT147 "
        "(chunk-23), TT116 (chunk-20). Per chunk-9 TT2 precedent that "
        "attribution_certainty encodes occupant-identity certainty.",
    ),
    (
        "TT153",
        "attribution_certainty",
        "attested",
        "PM I.1 p.262 (TT153, anonymous tomb). Notes: `Name lost. Temp. Sethos I (?).` "
        "The `(?)` qualifies the regnal date (Sethos I), not a primary occupant "
        "identity — the occupant is unnamed. The deriver fires `uncertain` on `(?)`; "
        "correct value is `attested`. Same anonymous-tomb-regnal-hedge class as "
        "TT143/TT147 (chunk-23), TT116 (chunk-20). Per chunk-9 TT2 precedent.",
    ),
    (
        "TT154",
        "attribution_certainty",
        "attested",
        "PM I.1 p.262 prints `154. TATI ..., Butler. Temp. Tuthmosis III(?).` "
        "The `(?)` qualifies the regnal date (Tuthmosis III), not Tati's "
        "identification as Butler. Same regnal-date hedge class as chunk-10 "
        "TT12/TT19/TT20, chunk-13 TT41/TT43/TT46, chunk-14 TT52/TT54, chunk-15 "
        "TT79, chunk-23 TT142/TT144/TT146. Per chunk-9 TT2 precedent that "
        "attribution_certainty encodes occupant-identity certainty, not "
        "regnal-date certainty.",
    ),
    (
        "TT158",
        "attribution_certainty",
        "attested",
        "PM I.1 p.268 prints `158. THONUFER ..., Third prophet of Amūn. Probably "
        "temp. Ramesses III.` The `Probably` token qualifies the regnal date "
        "(Ramesses III), not Thonufer's identification as Third prophet of Amūn. "
        "PM headword names Thonufer unhedged with the title unhedged; the temporal "
        "qualifier alone carries the `Probably` hedge. Same regnal-date hedge class "
        "as chunk-18 TT107/TT108, chunk-21 TT123, chunk-22 TT138 (all `Probably` "
        "tokens on regnal claims). Per chunk-9 TT2 precedent that attribution_certainty "
        "encodes occupant-identity certainty, not regnal-date certainty.",
    ),
    # Chunk-25 attribution_certainty overrides. TT161 and TT165 carry `(?)`
    # tokens in notes_from_pm that qualify regnal-date claims, not the primary
    # occupant attribution. The deriver fires context-free on any `(?)` in
    # notes; per the chunk-9 TT2 precedent extended through chunks 10–24,
    # attribution_certainty encodes occupant-identity certainty, not
    # regnal-date certainty. Both PM headwords name the occupant unhedged
    # with the title unhedged.
    (
        "TT161",
        "attribution_certainty",
        "attested",
        "PM I.1 p.274 prints `161. NAKHT ..., Bearer of the floral offerings of "
        "Amūn. Temp. Amenophis III(?).` The `(?)` qualifies the regnal date "
        "(Amenophis III), not Nakht's identification as Bearer of the floral "
        "offerings of Amūn. PM headword names Nakht unhedged with the title "
        "unhedged. Per chunk-9 TT2 precedent that attribution_certainty encodes "
        "occupant-identity certainty, not regnal-date certainty.",
    ),
    (
        "TT163",
        "attribution_certainty",
        "attested",
        "PM I.1 p.276 prints `163. AMENEMḤET ..., Mayor of the Southern City, "
        "Royal scribe. Dyn. XIX. (Inaccessible.) Father(?), Ḥuy, Judge, Mayor.` "
        "The `(?)` qualifies the identification of the FATHER (Ḥuy), not "
        "Amenemhet's identification as Mayor/Royal scribe. Same parentage-hedge "
        "class as chunk-10 TT17 (`Amenḥotp (?)` = second parent). PM headword "
        "names Amenemhet unhedged with the title unhedged. Per chunk-9 TT2 "
        "precedent that attribution_certainty encodes occupant-identity certainty, "
        "not parentage or regnal-date certainty.",
    ),
    (
        "TT165",
        "attribution_certainty",
        "attested",
        "PM I.1 p.277 prints `165. NEḤEMCAWAY ..., Goldworker and portrait-"
        "sculptor. Temp. Tuthmosis IV(?).` The `(?)` qualifies the regnal date "
        "(Tuthmosis IV), not Nehemʿaway's identification as Goldworker and "
        "portrait-sculptor. PM headword names Nehemʿaway unhedged with the title "
        "unhedged. Per chunk-9 TT2 precedent that attribution_certainty encodes "
        "occupant-identity certainty, not regnal-date certainty.",
    ),
    # Chunk-26 attribution_certainty overrides. TT172, TT175, and TT177 each
    # carry a `(?)` token in notes_from_pm that qualifies a regnal-date claim,
    # NOT the primary occupant attribution. The deriver fires context-free on
    # any `(?)` in notes; per the chunk-9 TT2 precedent extended through
    # chunks 10–25, attribution_certainty encodes occupant-identity certainty,
    # not regnal-date certainty. TT175 is anonymous (occupant_name=null) but
    # the `(?)` still qualifies the temporal clause, not an identity claim;
    # `attested` here means "this tomb is unambiguously identified as TT175,
    # the occupant identity is unknown rather than uncertain."
    (
        "TT172",
        "attribution_certainty",
        "attested",
        "PM I.1 p.279 prints `172. MENTIYWY ..., Royal butler, Child of the "
        "nursery. Temp. Tuthmosis III to Amenophis II (?). Mother, Ḥepu.` "
        "The `(?)` qualifies the regnal-range tail (Amenophis II), not "
        "Mentiywy's identification as Royal butler / Child of the nursery. "
        "PM headword names Mentiywy unhedged with the title unhedged. Same "
        "regnal-range tail hedge class as chunk-10 TT12/TT19/TT20, chunk-13 "
        "TT41/TT43/TT46, chunk-14 TT52/TT54, chunk-16 TT79. Per chunk-9 "
        "TT2 precedent that attribution_certainty encodes occupant-identity "
        "certainty, not regnal-date certainty.",
    ),
    (
        "TT175",
        "attribution_certainty",
        "attested",
        "PM I.1 p.281 prints `175. No name. Temp. Tuthmosis IV (?).` "
        "The `(?)` qualifies the regnal date (Tuthmosis IV), not any "
        "occupant-identity claim — there is no identity claim; the occupant "
        "is anonymous. `attested` here means the tomb record is "
        "unambiguously TT175 (the identity is unknown, not uncertain). "
        "Same regnal-date hedge class as chunk-10 TT12/TT20, chunk-14 "
        "TT52, chunk-15 TT69, chunk-25 TT165. Per chunk-9 TT2 precedent "
        "that attribution_certainty encodes occupant-identity certainty, "
        "not regnal-date certainty.",
    ),
    (
        "TT177",
        "attribution_certainty",
        "attested",
        "PM I.1 p.283 prints `177. AMENEMOPET ..., Scribe of truth in the "
        "Ramesseum in the estate of Amūn. Temp. Ramesses II (?). "
        "(Unfinished.)` The `(?)` qualifies the regnal date (Ramesses II), "
        "not Amenemopet's identification as Scribe of truth. PM headword "
        "names Amenemopet unhedged with the title unhedged. Same "
        "regnal-date hedge class as chunk-10 TT12/TT19/TT20, chunk-13 "
        "TT41/TT43, chunk-14 TT52, chunk-25 TT165. Per chunk-9 TT2 "
        "precedent that attribution_certainty encodes occupant-identity "
        "certainty, not regnal-date certainty.",
    ),
    # Chunk-27 deriver overrides.
    # TT181 Nebamūn: notes_from_pm contains `(and probably of Nebamūn)` —
    # this `probably` qualifies the identification of Ḥenutnefert as a
    # PROBABLE WIFE OF NEBAMŪN (a secondary-clause parenthetical hedging
    # the wife's association, not the headword occupant's identity).
    # PM headword `181. NEBAMŪN ..., Head sculptor ... and IPUKY ...,
    # Sculptor` attributes both men to the tomb without qualification.
    # The `_detect_attribution_certainty` regex fires context-free on
    # `\bprobably\b` and returns `probable` — incorrect for this row.
    # Same structural class as TT2 (chunk-9 DERIVER_OVERRIDE: `(probably)
    # Esi` qualifies the second wife, not the headword occupant). Per
    # chunk-9 TT2 precedent that attribution_certainty encodes occupant-
    # identity certainty, not secondary-association certainty.
    (
        "TT181",
        "attribution_certainty",
        "attested",
        "PM I.1 p.286 prints `181. NEBAMŪN ..., Head sculptor of the Lord "
        "of the Two Lands, and IPUKY ..., Sculptor ...` — both occupants "
        "attributed to the joint tomb without qualification. The `probably` "
        "in notes_from_pm (`Wife of Ipuky (and probably of Nebamūn)`) "
        "qualifies Ḥenutnefert's identification as Nebamūn's wife, not "
        "the identity of either headword occupant. Same secondary-clause "
        "hedge class as TT2 (`(probably) Esi` — second wife). Per "
        "chunk-9 TT2 precedent that attribution_certainty encodes "
        "occupant-identity certainty, not secondary-association certainty.",
    ),
    # TT190 Esbanebded: notes_from_pm reads
    # `Saite (usurped from a Ramesside tomb)` — the `usurped` token means
    # Esbanebded IS THE USURPER of an earlier Ramesside tomb, not the
    # usurped party. The `_USURPED_RE` regex fires context-free on any
    # `usurp` token and would set `is_usurped=True`, which is wrong for
    # the headword occupant (PM's `is_usurped` flag is intended to mark
    # the primary occupant as a VICTIM of usurpation, not as the agent).
    # Exact structural parallel to TT95 Mery (chunk-18 DERIVER_OVERRIDE):
    # Mery usurped TT84 but is the headword occupant of TT95 — is_usurped
    # correctly False for TT95. Same logic applies here.
    (
        "TT190",
        "is_usurped",
        False,
        "PM I.1 p.297 prints `190. ESBANEBDED ..., Divine father, Prophet "
        "of the head of the King. Saite (usurped from a Ramesside tomb).` "
        "Esbanebded IS THE USURPER (Saite-period occupant who took over a "
        "Ramesside tomb); the `is_usurped` flag marks the PRIMARY OCCUPANT "
        "as a victim of usurpation, not as the agent. Same structural "
        "parallel as TT95 Mery (chunk-18 DERIVER_OVERRIDE). The deriver "
        "regex fires on `usurped` context-free; override to False.",
    ),
]


def _apply_issue_182_migrations(rows: list[dict]) -> list[str]:
    """Per-row schema-audit migrations for issue #182. Idempotent.

    Runs the regex-based derivers first, then applies `DERIVER_OVERRIDES`
    for rows where the deriver's context-free regex fires on a
    secondary-clause hedge that PM does not apply to the primary occupant
    attribution. The override pass is logged distinctly from the deriver
    pass so the audit trail makes the override-vs-derivation distinction
    explicit.

    Design note (per code-reviewer P2-3 on PR #196): the deriver pass
    runs unconditionally on every row, including those in
    `DERIVER_OVERRIDES`. We could short-circuit (skip the regex when an
    override exists) and avoid the temporary "deriver wrote X / override
    wrote Y" two-line log entry per override row. Trade-off chosen: keep
    the deriver visible in the log so adding a new override is auditable
    against what the regex would have produced — the future maintainer
    inspecting `merge-disagreements.txt` sees the exact regex output the
    override is countermanding. The on-disk file is byte-stable across
    runs (the deriver result is deterministic, the override is
    deterministic, both fire the same way every run), so idempotence is
    preserved. If `DERIVER_OVERRIDES` grows past ~10 entries this
    trade-off should be revisited.
    """
    log: list[str] = []
    for row in rows:
        tid = row["tomb_id"]
        notes = row.get("notes_from_pm")
        for field, deriver in _ISSUE_182_DERIVATIONS:
            new_val = deriver(notes)
            if row[field] != new_val:
                row[field] = new_val
                # Use json.dumps for log-line consistency with the
                # rest of the file (booleans render as `true` not
                # `True`, strings as `"x"` not `'x'`). Per Gemini round-5.
                log.append(
                    f"- {tid}: {field} → {json.dumps(new_val, ensure_ascii=False)} "
                    f"(issue #182 derivation from notes_from_pm)"
                )
    # Per-row deriver overrides (apply AFTER the regex pass so the
    # override wins). Logged as "deriver override" so the audit trail
    # distinguishes context-free derivation from per-row overrides.
    by_id = {r["tomb_id"]: r for r in rows}
    for tomb_id, field, new_val, rationale in DERIVER_OVERRIDES:
        row = by_id.get(tomb_id)
        if row is None:
            raise KeyError(
                f"DERIVER_OVERRIDES references unknown tomb_id {tomb_id!r}"
            )
        if row[field] != new_val:
            row[field] = new_val
            log.append(
                f"- {tomb_id}: {field} → {json.dumps(new_val, ensure_ascii=False)} "
                f"(deriver override; {rationale[:80]}...)"
            )
        else:
            log.append(
                f"- {tomb_id}: {field} already matches deriver override "
                f"(no-op this run; {rationale[:80]}...)"
            )
    return log


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

    # Legacy field-key migration: PR #170 renamed `valley` → `theban_area`
    # by editing reconciled.jsonl directly (the per-chunk agent JSONLs
    # were not touched — they remain the stable record of each round of
    # agent extraction). Re-running `merge.py` therefore regenerates rows
    # with the OLD `valley` key. This migration enforces the rename on
    # every load so the convention can no longer silently regress on a
    # re-merge. Idempotent: a row that already has `theban_area` and no
    # `valley` is unchanged. Logged distinctly from the typed-flag
    # derivation pass and the SPOT_CORRECTIONS pass.
    legacy_rename_log: list[str] = []
    legacy_renamed_count = 0
    for old_key, new_key in LEGACY_FIELD_RENAMES.items():
        per_key_renamed: list[str] = []  # rows where this run actually moved value
        per_key_collision_dropped: list[str] = []  # rows where both keys present, equal values
        for row in rows:
            if old_key in row:
                if new_key in row:
                    # Both keys present — old PR #170 row + a stray
                    # legacy `valley` re-introduced by re-merge. Prefer
                    # the new key's value (the canonical post-#170
                    # state) and drop the legacy key.
                    if row[old_key] != row[new_key]:
                        raise ValueError(
                            f"row {row.get('tomb_id')!r} carries both "
                            f"{old_key!r}={row[old_key]!r} and "
                            f"{new_key!r}={row[new_key]!r} with different "
                            f"values; resolve before merging."
                        )
                    # Equal values: drop the legacy key. Logged distinctly
                    # from the canonical rename path so the audit trail
                    # records the collision (per code-reviewer P3-2 on
                    # PR #196: a silently-dropped key is a rule-2 mini-
                    # violation; loud no-op log preserves the trail).
                    del row[old_key]
                    per_key_collision_dropped.append(row["tomb_id"])
                else:
                    row[new_key] = row.pop(old_key)
                    per_key_renamed.append(row["tomb_id"])
        legacy_renamed_count += len(per_key_renamed) + len(per_key_collision_dropped)
        if per_key_renamed:
            legacy_rename_log.append(
                f"- {old_key} → {new_key}: renamed on {len(per_key_renamed)} "
                f"row(s) (first/last: {per_key_renamed[0]}, "
                f"{per_key_renamed[-1]})"
            )
        if per_key_collision_dropped:
            legacy_rename_log.append(
                f"- {old_key} → {new_key}: dropped legacy {old_key!r} key "
                f"on {len(per_key_collision_dropped)} row(s) where both "
                f"keys carried equal values "
                f"(first/last: {per_key_collision_dropped[0]}, "
                f"{per_key_collision_dropped[-1]})"
            )
        if not per_key_renamed and not per_key_collision_dropped:
            legacy_rename_log.append(
                f"- {old_key} → {new_key}: no-op this run "
                f"(every row already uses {new_key!r})"
            )

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

    # Schema field-add pass.
    #
    # Existing rows lack the `tomb_aliases` and `co_occupants` fields
    # introduced by PR A — the agent prompts were written before those
    # fields existed, so the 3-agent merge never emitted them. Add the
    # fields with their default values (empty lists) before SPOT_CORRECTIONS
    # runs, so the audit-fix corrections can populate them on the affected
    # rows without KeyError.
    #
    # Idempotent: rows already carrying the field are not overwritten.
    # `copy.deepcopy` defends against any future default that is a mutable
    # nested structure being aliased across rows.
    field_add_log: list[str] = []
    for field, default in SCHEMA_FIELD_DEFAULTS.items():
        added_for_rows: list[str] = []
        for r in rows:
            if field not in r:
                r[field] = copy.deepcopy(default)
                added_for_rows.append(r["tomb_id"])
        if added_for_rows:
            field_add_log.append(
                f"- {field}: added with default {json.dumps(default, ensure_ascii=False)} "
                f"to {len(added_for_rows)} row(s) "
                f"(first/last: {added_for_rows[0]}, {added_for_rows[-1]})"
            )
        else:
            field_add_log.append(
                f"- {field}: present on every row already (no-op this run)"
            )

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

    # Issue #182 schema-audit pass: derive typed flags from
    # `notes_from_pm`. Pure derivation — no asserted facts beyond
    # what PM verbatim records. Idempotent.
    schema_182_log = _apply_issue_182_migrations(rows)
    if schema_182_log:
        override_log.extend(schema_182_log)
    else:
        # Always log the no-op line so the audit trail across runs is
        # consistent (mirrors the field_add_log / rename_log pattern).
        # Per Gemini round-2 finding.
        override_log.append(
            "- issue #182 schema-audit pass: 0 changes this run "
            "(reconciled.jsonl already reflects all derived typed flags)"
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
    if legacy_rename_log:
        body_sections.append(
            "Legacy field-key renames (post-#170 reconcile):\n"
            + "\n".join(legacy_rename_log)
        )
    if rename_log:
        body_sections.append("Tomb-id renames:\n" + "\n".join(rename_log))
    if field_add_log:
        body_sections.append("Schema field additions:\n" + "\n".join(field_add_log))
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
