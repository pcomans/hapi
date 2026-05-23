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


# Chunk-22 (PM I.1 § I — TT131-TT140, Sh. ʿAbd el-Qurna + Draʿ Abû el-Nagaʿ).
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
        "PM I.1 p.281 (TT175, anonymous tomb, Khôkha). PM headword carries no "
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
        "PM I.1 p.286 (TT180, anonymous unfinished tomb, Khôkha). PM headword "
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
        "Agents A+B emitted `Wab-priest` (capital-W); agent C emitted "
        "`wab-priest` (lowercase, still no ayin). Two restorations: "
        "(a) `Wab-priest` / `wab-priest` → `wʿab-priest` — insert "
        "U+02BF ayin + lowercase sentence-initial per chunk-22 TT113 "
        "+ chunk-23 TT141 + chunk-26 ayin-before-a precedent (PM "
        "body-prose sentence-initial lowercase preserved per source "
        "verbatim, not auto-capitalized). (b) `Amun` → `Amūn` — PM "
        "body-prose macron-Ū per chunk-12-onward macron-retain class "
        "(same as TT181, TT189 in this same chunk). The `ʿAshakhet` "
        "raised-ayin glyph `<` → U+02BF is already applied by the "
        "postprocess whitelist on the tie-break-pinned agent-A form "
        "(no separate restoration needed here). Verbatim-preserve "
        "policy on notes_from_pm. Gemini PR #271 round 1 finding "
        "3279424043 + round 3 rationale-accuracy finding 3279927029.",
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


# === Chunk 28 — TT191-TT200 (ʿAsâsîf + Khôkha, LP + XVIII + XIX) ============
#
# All 4 substantive divergences (TT192/TT193/TT194/TT196 notes_from_pm) were
# resolved via tie-break-overrides.json. One additional post-merge correction
# is applied to TT194 (Amūn macron consistency across all 4 occurrences in
# notes_from_pm, per Gemini PR #272 round-1 finding 3280621504).
CHUNK28_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT194",
        "notes_from_pm",
        "Overseer of marshland-dwellers of the estate of Amūn, Scribe of "
        "the temple of Amūn. Dyn. XIX. Father, a wʿab-priest in front of "
        "Amūn, Scribe of divine offerings of Amūn. Wife, Nezemtmut.",
        "PR #272 round 1 Gemini finding 3280621504: TT194 notes_from_pm "
        "had `Amūn` with macron-Ū in the first 2 occurrences (Overseer + "
        "Scribe of the temple) but `Amun` without macron in the 2 Father-"
        "clause occurrences (in front of Amun, Scribe of divine offerings "
        "of Amun). Per Constitutional Rule 6 verbatim-preserve + "
        "chunk-12-onward macron-retain class (same as TT181/TT187/TT189 "
        "in chunks 27/28), all 4 occurrences should carry macron-Ū. "
        "Tie-break-pinned agent merge introduced the inconsistency. "
        "Restoration applies macron-Ū to all 4 occurrences (no semantic "
        "change; pure diacritic consistency)."
    ),
]

CHUNK28_RENAMES: dict[str, str] = {}


# === Chunk 29 — TT201-TT210 (Khôkha ×8 + ʿAsâsîf ×1 + Deir el-Medina ×1) ===
#
# Tie-break overrides (tie-break-overrides.json) resolved 4 substantive
# 1/1/1 splits: TT202 notes_from_pm (Ptaḥ underdot + no-comma), TT207
# notes_from_pm (Ḥemawen underdot), TT209 notes_from_pm (formerly-read
# parenthetical + (?) uncertainty), TT210 notes_from_pm (L.D. citation
# mid-sentence + Nefertkhaʿ ayin).
#
# Post-merge CHUNK29_CORRECTIONS apply:
#   1. TT201 occupant_name: 2/1 majority chose `Re`; PM headword `RE<` =
#      `Reʿ` (ayin). Restore ayin per README ayin-preserve policy. Same axis
#      as TT204 and TT210 below.
#   2. TT202 occupant_role: 2/1 majority chose `High Priest`; PM says
#      `Prophet of Ptaḥ Lord of Thebes` — a lower-order priestly title, not
#      the First Prophet of Amun. `Official` is the correct role per the
#      pipeline's role-vocabulary precedent (TT197 `Chief steward of the
#      god's wife...` = Official, TT193 `Magnate of the seal...` = Official).
#   3. TT202 notes_from_pm: `Amun` → `Amūn` macron-Ū per chunk-12-onward
#      verbatim-preserve policy (PM body prose prints Amūn with macron).
#   4. TT204 occupant_name: 2/1 majority chose `Nebanensu`; PM `NEB<ANENSU`
#      = `Nebʿanensu`. Ayin-preserve.
#   5. TT207 notes_from_pm: `Amun` → `Amūn` macron-Ū (merge-pinned value
#      from agent C had `Amun` without macron; verbatim-preserve applies).
#   6. TT208 notes_from_pm: 2/1 majority chose `Amen-Re`; PM `Amen-rec` =
#      `Amen-reʿ` (ayin, lowercase `r`). Restore per verbatim-preserve.
#   7. TT210 occupant_name: 2/1 majority chose `Raweben`; PM `RA<WEBEN` =
#      `Raʿweben`. Ayin-preserve.
CHUNK29_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT201",
        "occupant_name",
        "Reʿ",
        "PM I.1 p.304 headword `RE< =~·` — the `<` is the PM text-layer "
        "rendering of the ayin (ʿ). Agents A+B (2/1 majority) chose `Re`; "
        "agent C's `Reʿ` matches the PM headword. Ayin-preserve convention "
        "per README and Constitutional Rule 1 (PM-faithful provenance). "
        "Same OCR-ayin axis as TT204 `Nebʿanensu` and TT210 `Raʿweben`.",
    ),
    (
        "TT202",
        "occupant_role",
        "Official",
        "PM I.1 p.305 headword `Prophet of Ptaḥ Lord of Thebes, Priest in "
        "front of Amun` — `Prophet of Ptaḥ` is a lower-order priestly "
        "title, NOT the First Prophet of Amun (High Priest rank). The "
        "project role-vocabulary uses `Official` for temple priests below "
        "the First-Prophet level (TT197 Chief steward = Official; TT193 "
        "Magnate of the seal = Official). Agents A+B (2/1 majority) chose "
        "`High Priest`; agent C's `Official` is correct. Flagged for "
        "egyptologist confirmation.",
    ),
    (
        "TT202",
        "notes_from_pm",
        "Prophet of Ptaḥ Lord of Thebes, Priest in front of Amūn. Dyn. XIX(?).",
        "Macron-Ū on `Amūn` per chunk-12-onward verbatim-preserve policy "
        "(PM body prose prints Amūn with macron throughout). Tie-break "
        "pinned agent C's form which had `Amun` without macron; correcting "
        "here per the verbatim-preserve rule. Underdot-Ḥ on `Ptaḥ` is "
        "already correct from the tie-break pin.",
    ),
    (
        "TT204",
        "occupant_name",
        "Nebʿanensu",
        "PM I.1 p.305 headword `NEB<ANENSU` — the `<` is the PM text-layer "
        "rendering of the ayin (ʿ). Agents A+B (2/1 majority) chose "
        "`Nebanensu`; agent C's `Nebʿanensu` matches PM. Ayin-preserve "
        "convention per README and Constitutional Rule 1. Same axis as "
        "TT201 `Reʿ` and TT210 `Raʿweben`.",
    ),
    (
        "TT204",
        "notes_from_pm",
        "Sailor of the first prophet of Amūn (title from cone). Dyn. XVIII.",
        "PR #273 round 2 Gemini finding 3282425875: TT204 notes_from_pm "
        "had `Amun` without macron-Ū. Per chunk-12-onward macron-retain "
        "class (same precedent as TT202 / TT207 / TT208 in this chunk + "
        "TT181/TT187/TT189 in chunks 27/28), PM body-prose always renders "
        "`Amūn` with macron-Ū. Restore macron-Ū to verbatim-preserve.",
    ),
    (
        "TT207",
        "notes_from_pm",
        "Scribe of divine offerings of Amūn. Ramesside. Parents, Ḥemawen and Nebuy.",
        "Macron-Ū on `Amūn` per chunk-12-onward verbatim-preserve policy. "
        "Tie-break pinned agent C's form which had `Amun` without macron. "
        "`Ḥemawen` with underdot-Ḥ is already correct from the tie-break "
        "pin (PM `~emawen` → `Ḥemawen`).",
    ),
    (
        "TT208",
        "notes_from_pm",
        "Divine father of Amen-reʿ. Ramesside.",
        "PM I.1 p.306 headword `RoMA ~~·.Divine father of Amen-rec.` — "
        "`Amen-rec` is the PM text-layer rendering of `Amen-reʿ` (lowercase "
        "`r`, ayin ʿ). Agents A+B (2/1 majority) chose `Amen-Re` (capital "
        "R, no ayin) — both elements wrong. Verbatim-preserve policy: "
        "restore lowercase `r` per PM's body-prose convention and the ayin "
        "per the README ayin-preserve rule. Compare TT65 tie-break rationale "
        "`Amen-reʿ` in `notes_from_pm` (same divine-name form).",
    ),
    (
        "TT210",
        "occupant_name",
        "Raʿweben",
        "PM I.1 p.307 headword `RA<WEBEN` — the `<` is the PM text-layer "
        "rendering of the ayin (ʿ). Agents A+B (2/1 majority) chose "
        "`Raweben`; agent C's `Raʿweben` matches PM. Ayin-preserve "
        "convention per README and Constitutional Rule 1. Same axis as "
        "TT201 `Reʿ` and TT204 `Nebʿanensu`.",
    ),
]

CHUNK29_RENAMES: dict[str, str] = {}


# === Chunk 30 — TT211-TT220 (Deir el-Medina) =================================
#
# Tie-break-overrides.json resolved 6 substantive 1/1/1 splits:
#   TT211|notes_from_pm — pin C (commas, Wa'be(t) bracket)
#   TT213|notes_from_pm — pin C (Bald not Baldi, no L.D. bleed)
#   TT215|notes_from_pm — pin C (correct order, tomb 335)
#   TT217|notes_from_pm — pin B (commas, no title expansion)
#   TT217|source_citation — pin 315 (source-confirmed headword page)
#   TT218|notes_from_pm — pin A (Hr-mnw abbreviation, ayins)
#
# Post-merge CHUNK30_CORRECTIONS apply:
#
#   1. TT211 source_citation.page: 308 → 307 (2/1 majority wrong; headword
#      `211. PANEB` appears at source line 25 under PRINTED PAGE 307).
#   2. TT211 notes_from_pm: `Wa'be(t)` → `Waʿbe(t)` — straight apostrophe `'`
#      restored to proper ayin U+02BF. Source `Wa<be(t)` where `<` = ayin ʿ
#      (same OCR-ayin rendering class as TT210 `Nefertkhaʿ` in CHUNK29).
#   3. TT214 notes_from_pm: `Amun` → `Amūn` — macron-Ū per chunk-12-onward
#      verbatim-preserve policy (PM body prose prints `Amūn` throughout).
#   4. TT215 source_citation.page: 312 → 311 (2/1 majority wrong; headword
#      `215. AMENEMOPET` appears at source line 332 under PRINTED PAGE 311).
#   5. TT215 shared_with_tombs: [] → ["TT265"] — 2/1 majority (B+C) wrong;
#      source line 332-333 explicitly states `(Burial Chamber is tomb 265.)`.
#      Same shared-burial-chamber precedent as TT215/TT265 bidirectional pair.
#   6. TT215 notes_from_pm: restore underdot-Ḥ on `Ḥatḥor` and `Ḥunuro` +
#      append `(L. D. Text, No. 100.)` — source line 395 `(L. D. Text, No. Ioo.)`
#      appears on TT216's locator line; TT215's locator also has a cite but
#      the TT215 agents' OCR extracted it from the Amenemopet body-cite line 344.
#      Actually the L.D. cite for TT215 appears in Agent A's form only and was
#      dropped by the tie-break — restoring here. PM `l:Iati}.or` = `Ḥatḥor`
#      (underdot-Ḥ); `I:Iunuro` = `Ḥunuro` (underdot-Ḥ); both verbatim-preserve.
#   7. TT216 source_citation.page: 313 → 312 (unanimous-wrong; headword
#      `216. NEFERḤOTEP` appears at source line 391 under PRINTED PAGE 312).
#   8. TT216 notes_from_pm: append `(L. D. Text, No. 100.)` — source line 395
#      `Deir el-Medina. (L. D. Text, No. Ioo.)` is a locator-line cite for TT216.
#      All 3 agents omitted it (2/1 majority pinned no-cite form). Per TT212
#      locator-line-cite precedent (same cite format, same Deir el-Medina area
#      line), the L.D. text citation belongs in notes_from_pm.
#   9. TT217 notes_from_pm: `Nefertkha` → `Nefertkhaʿ` — ayin restore; PM
#      source `Nefertkha<` where `<` = ayin ʿ (same OCR-ayin class as TT210
#      `Nefertkhaʿ` in CHUNK29, TT217 is Ipuy, son of Piay + Nefertkhaʿ).
#  10. TT218 source_citation.page: 318 → 317 (unanimous-wrong; headword
#      `218. AMENNAKHT` at source line 649 under PRINTED PAGE 317).
#  11. TT218 notes_from_pm: (a) colons → commas, (b) remove Co-occupants
#      clause (spurious agent annotation not in PM headword), (c) parenthetical
#      → comma form for parent title, (d) `Hetepti` → `Ḥetepti` (underdot-Ḥ;
#      source `I;Ietepti`), (e) `Amon` → `Amūn` (macron-Ū).
#  12. TT219 source_citation.page: 321 → 320 (unanimous-wrong; headword
#      `219. NEBENMACET` at source line 847 under PRINTED PAGE 320).
#  13. TT219 occupant_name: `Nebenmaet` → `Nebenmaʿet` — ayin restore;
#      PM headword `NEBENMA<ET` where `<` = ayin ʿ (2/1 majority stripped it).
#  14. TT220 occupant_name: `Khaemteri` → `Khaʿemteri` — ayin restore;
#      PM headword `KHA<EMTERI` where `<` = ayin ʿ (2/1 majority stripped it).
CHUNK30_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT211",
        "source_citation",
        {"edition": "PM I.1 2nd ed. 1960", "page": 307, "section": "I"},
        "PM I.1 p.307 / physical PDF source chunk-30-tt211-tt220.txt line 25: "
        "headword `211. PANEB` appears at source line 25 under "
        "`===== PHYSICAL PAGE 325 (PRINTED PAGE 307) =====` (source line 1). "
        "2/1 majority (agents A+B) reported page 308 — the next physical page "
        "where the tomb body continues. Correct printed page is 307.",
    ),
    (
        "TT211",
        "notes_from_pm",
        "Servant of the Lord of the Two Lands in the Place of Truth. Dyn. XIX. "
        "Parents, Nefersenut, same title as deceased, and Iuy. Wife, Waʿbe(t).",
        "PM I.1 p.307 / chunk-30-tt211-tt220.txt line 38: source OCR `Wa<be(t)` "
        "where `<` is the PM text-layer rendering of ayin ʿ (U+02BF). The `(t)` "
        "is PM's editorial bracket on the feminine ending. Tie-break pinned agent C "
        "`Wa'be(t)` (correct bracket) but with straight apostrophe `'` instead of "
        "proper ayin U+02BF. Restore: `Wa'be(t)` → `Waʿbe(t)` (same OCR-ayin "
        "class as TT210 `Nefertkhaʿ` in CHUNK29_CORRECTIONS).",
    ),
    (
        "TT214",
        "notes_from_pm",
        "Custodian in the Place of Truth, Servant of Amūn in Luxor. Ramesside. "
        "Wife, Tawert.",
        "PM I.1 p.310 / chunk-30-tt211-tt220.txt line 265: source OCR `Amlin` = "
        "`Amūn` (macron-Ū on ū). 2/1 majority (agents B+C) emitted `Amun` without "
        "macron; agent A used colon (lost at merge). Restore macron-Ū per "
        "chunk-12-onward verbatim-preserve policy (PM body prose consistently "
        "prints `Amūn` with macron throughout PM I.1 Deir el-Medina section).",
    ),
    (
        "TT215",
        "source_citation",
        {"edition": "PM I.1 2nd ed. 1960", "page": 311, "section": "I"},
        "PM I.1 p.311 / chunk-30-tt211-tt220.txt line 332: headword `215. AMENEMOPET` "
        "appears at source line 332 under `===== PHYSICAL PAGE 329 (PRINTED PAGE 311) =====` "
        "(source line 292). 2/1 majority (agents B+C) reported page 312 — the next "
        "physical page where the tomb body continues. Correct printed page is 311.",
    ),
    (
        "TT215",
        "shared_with_tombs",
        ["TT265"],
        "PM I.1 p.311 / chunk-30-tt211-tt220.txt line 332-333: PM explicitly states "
        "`(Burial Chamber is tomb 265.)` in TT215's headword. This is a direct "
        "physical-sharing relationship (same structural class as TT215/TT265 burial-"
        "chamber sharing). 2/1 majority (agents B+C) emitted [] (dropped the cross-ref); "
        "agent A correctly emitted [\"TT265\"]. Per the TT131/TT61 bidirectional-pair "
        "symmetry convention, TT265 must carry a reciprocal shared_with_tombs entry "
        "for TT215 — flag for egyptologist to verify chunk covering TT265.",
    ),
    (
        "TT215",
        "notes_from_pm",
        "Royal scribe in the Place of Truth. (Burial Chamber is tomb 265.) Dyn. XIX. "
        "Parents, Minmosi and Esi (names in tomb 335). Wife, Ḥatḥor, called Ḥunuro. "
        "(L. D. Text, No. 100.)",
        "PM I.1 p.311 / chunk-30-tt211-tt220.txt line 335: source OCR `l:Iati}.or` = "
        "`Ḥatḥor` (underdot-Ḥ on both H's); `I:Iunuro` = `Ḥunuro` (underdot-Ḥ). "
        "Tie-break pinned agent C `Hathor, called Hunuro` (correct order + tomb 335) "
        "but missing underdot-Ḥ on both names. Restore per verbatim-preserve policy "
        "for notes_from_pm. Additionally: source locator line prints `Deir el-Medina.` "
        "with L.D. cite annotation (agent A had `(L. D. Text, No. 100.)` but lost at "
        "tie-break; same locator-line-cite class as TT212 `(L. D. Text, No. 98.)` and "
        "TT216 `(L. D. Text, No. 100.)` per TT216's source line 395). Appended here.",
    ),
    (
        "TT216",
        "source_citation",
        {"edition": "PM I.1 2nd ed. 1960", "page": 312, "section": "I"},
        "PM I.1 p.312 / chunk-30-tt211-tt220.txt line 391: headword `216. NEFERḤOTEP` "
        "appears at source line 391 under `===== PHYSICAL PAGE 330 (PRINTED PAGE 312) =====` "
        "(source line 355). All 3 agents reported page 313 — the next physical page where "
        "the tomb body continues. Unanimous-wrong; correct printed page is 312.",
    ),
    (
        "TT216",
        "notes_from_pm",
        "Foreman. Temp. Ramesses II to Sethos II. Parents, Nebnufer (tomb 6) and Iy. "
        "Wife, Webekht. (L. D. Text, No. 100.)",
        "PM I.1 p.312 / chunk-30-tt211-tt220.txt line 395: source locator line "
        "`Deir el-Medina. (L. D. Text, No. Ioo.)` contains the L.D. Text citation. "
        "All 3 agents omitted it (2/1 majority pinned no-cite form via tie-break). "
        "Per TT212 locator-line-cite precedent (`(L. D. Text, No. 98.)` in TT212 "
        "notes_from_pm) and same-L.D.-number shared by TT215 and TT216, the citation "
        "belongs in notes_from_pm. Same L.D. cite `No. 100` covers TT215+TT216 "
        "(PM printed them together in the L.D. reference).",
    ),
    (
        "TT217",
        "notes_from_pm",
        "Sculptor. Temp. Ramesses II. Parents, Piay and Nefertkhaʿ (names in tomb 210). "
        "Wife, Duammeres.",
        "PM I.1 p.315 / chunk-30-tt211-tt220.txt line 534: source OCR `Nefertkha< ~~~~` "
        "where `<` = ayin ʿ (U+02BF). Tie-break pinned agent B `Nefertkha` (correct "
        "comma structure, no title expansion) but missing the ayin on `Nefertkhaʿ`. "
        "Restore ayin per the same OCR-ayin class as TT210 `Nefertkhaʿ` (CHUNK29) and "
        "TT132/TT138/TT201/TT204 ayin-preserve precedents. Note: TT217 Ipuy is the son "
        "of Piay + Nefertkhaʿ from TT210 — the bidirectional family link confirms ayin "
        "(TT210 CHUNK29_CORRECTIONS already carries `Nefertkhaʿ` with ayin).",
    ),
    (
        "TT218",
        "source_citation",
        {"edition": "PM I.1 2nd ed. 1960", "page": 317, "section": "I"},
        "PM I.1 p.317 / chunk-30-tt211-tt220.txt line 649: headword `218. AMENNAKHT` "
        "appears at source line 649 under `===== PHYSICAL PAGE 335 (PRINTED PAGE 317) =====` "
        "(source line 624). All 3 agents reported page 318 — the next physical page. "
        "Unanimous-wrong; correct printed page is 317.",
    ),
    (
        "TT218",
        "notes_from_pm",
        "Servant in the Place of Truth on the west of Thebes. Ramesside. Parents, "
        "Nebenmaʿet, Hr-mnw of Amūn, and Ḥetepti. Wife, Iymway.",
        "PM I.1 p.317 / chunk-30-tt211-tt220.txt line 651: source OCR "
        "`Nebenma<et :=::~ .:_~, r!-mnw of Amon, and I;Ietepti. Wife, lymway`. "
        "Tie-break pinned agent A's form. Four corrections on that form: "
        "(a) colons → commas (PM body-prose punctuation per all preceding chunks); "
        "(b) remove `Co-occupants: Son Khaʿemteri (tomb 220) and son Nebenmaʿet "
        "(tomb 219).` (spurious agent annotation — not in PM headword text; sons' "
        "tombs are captured in `shared_with_tombs: [\"TT219\", \"TT220\"]`); "
        "(c) `Hetepti` → `Ḥetepti` (underdot-Ḥ; source `I;Ietepti` = Ḥetepti, "
        "same `I;I` OCR pattern for capital underdot-Ḥ as seen throughout chunks 1-29); "
        "(d) `Amon` → `Amūn` (macron-Ū; chunk-12-onward verbatim-preserve policy). "
        "Parenthetical → comma form: `(Hr-mnw of Amūn)` → `, Hr-mnw of Amūn,` per "
        "PM's comma-separated title clause convention (source comma before `r!-mnw`).",
    ),
    (
        "TT219",
        "source_citation",
        {"edition": "PM I.1 2nd ed. 1960", "page": 320, "section": "I"},
        "PM I.1 p.320 / chunk-30-tt211-tt220.txt line 847: headword `219. NEBENMACET` "
        "appears at source line 847 under `===== PHYSICAL PAGE 338 (PRINTED PAGE 320) =====` "
        "(source line 814). All 3 agents reported page 321 — the next physical page. "
        "Unanimous-wrong; correct printed page is 320.",
    ),
    (
        "TT219",
        "occupant_name",
        "Nebenmaʿet",
        "PM I.1 p.320 headword `219. NEBENMA<ET` (source line 847: `NEBENMACET` "
        "where `C` = OCR rendering of `<ET` = ayin + ET, giving `Nebenmaʿet`). "
        "2/1 majority (agents B+C) emitted `Nebenmaet` (ayin dropped). Agent A's "
        "`Nebenmaʿet` matches PM headword. Ayin-preserve convention per README and "
        "Constitutional Rule 1. Same OCR-ayin class as TT201 `Reʿ`, TT204 `Nebʿanensu`, "
        "TT210 `Raʿweben` (CHUNK29) and TT220 `Khaʿemteri` (same chunk).",
    ),
    (
        "TT220",
        "occupant_name",
        "Khaʿemteri",
        "PM I.1 p.322 headword `220. KHA<EMTERI` (source line 956: `KHA<EMTERl` "
        "where `<` = ayin ʿ U+02BF, final `l` = OCR for `i`). 2/1 majority (agents B+C) "
        "emitted `Khaemteri` (ayin dropped). Agent A's `Khaʿemteri` matches PM headword. "
        "Ayin-preserve convention per README and Constitutional Rule 1. Same OCR-ayin "
        "class as TT219 `Nebenmaʿet` (same chunk) and TT201/TT204/TT210 (CHUNK29).",
    ),
    (
        "TT219",
        "shared_with_tombs",
        ["TT218"],
        "PM I.1 p.317-320 — TT218, TT219, TT220 form a family tomb complex: Amennakht "
        "(TT218) is the father; his sons Nebenmaʿet (TT219) and Khaʿemteri (TT220) each "
        "have adjacent tombs. TT218 already carries `shared_with_tombs: [\"TT219\", \"TT220\"]` "
        "(unanimous agent agreement from body-text cross-references at source lines 804-805). "
        "`test_shared_with_tombs_symmetry_within_chunk` requires bidirectional symmetry for "
        "within-section pairs. Agent A correctly emitted `[\"TT218\"]` for TT219; 2/1 "
        "majority (B+C) dropped the back-reference to []. Restoring symmetry here.",
    ),
    (
        "TT220",
        "shared_with_tombs",
        ["TT218"],
        "PM I.1 p.317-322 — same TT218/TT219/TT220 family tomb complex rationale as "
        "TT219 CHUNK30 correction above. TT218 carries `shared_with_tombs: [\"TT219\", \"TT220\"]`; "
        "symmetry requires TT220 to carry `[\"TT218\"]`. Agent A emitted `[\"TT218\"]`; "
        "2/1 majority (B+C) dropped it. Restoring to satisfy "
        "`test_shared_with_tombs_symmetry_within_chunk`.",
    ),
]

CHUNK30_RENAMES: dict[str, str] = {}


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


# Sub-site (theban_area) value migration to PM-faithful canonical forms (issues
# #288 + #291). Decided 2026-05-23: migrate `theban_area` values to match PM's
# printed diacritics, consistent with how `Sh. ʿAbd el-Qurna` / `ʿAsâsîf` /
# `Qurnet Muraʿi` already preserve PM's diacritics. The agent prompts and the
# per-chunk agent JSONLs landed BEFORE this decision used the project-stripped
# forms (`Dra' Abu el-Naga` / `Khokha` / `Deir el-Bahari`). Re-running merge.py
# regenerates rows with the OLD stripped values from the stable agent JSONLs;
# this migration runs in main() before SPOT_CORRECTIONS so downstream per-row
# corrections operate on the canonical PM-faithful form. Idempotent: a row
# already carrying the new form is unchanged. Character-precision verified by
# egyptologist-reviewer (issues #288/#291 PR): PM uses U+02BF MODIFIER LETTER
# LEFT HALF RING (ʿayin) in BOTH the leading and terminal positions of
# `Draʿ Abû el-Nagaʿ` — NOT ASCII apostrophe.
# `Deir el-Medina` is NOT migrated — PM prints it plain (no diacritics) per
# direct PDF verification (PM I.1 p.311 TT215 headword).
SUBSITE_PM_FAITHFUL_MIGRATION: dict[str, str] = {
    "Dra' Abu el-Naga": "Draʿ Abû el-Nagaʿ",
    "Khokha": "Khôkha",
    "Deir el-Bahari": "Deir el-Baḥri",
}


SCHEMA_FIELD_DEFAULTS: dict[str, object] = {
    "tomb_aliases": [],
    "co_occupants": [],
    # `sub_period`: not yet populated by PM I.1 extraction (all agents return
    # None; added here so rows from extraction prompts that omit the field still
    # satisfy the required-fields schema test. When a later pass assigns
    # sub-period values (e.g. Dyn. XVIII Early/Mid/Late), update here.
    "sub_period": None,
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


CHUNK31_RENAMES: dict[str, str] = {}


# Chunk-31 (TT221–TT230, Qurnet Muraʿi + ʿAsâsîf + Sh. ʿAbd el-Qurna).
# 5 anonymous rows (TT225/226/227/229/230) — same null-name/null-role
# pairing invariant issue as chunk-8 KV12/chunk-14 TT58/chunk-15 TT70.
# TT224 occupant_name: all three agents misread the leading ayin (ʿ) in
# PM's `ʿAHMOSI` headword as `C` (same OCR class as chunk-11 TT29
# `[Caḥmosi]`). TT224 notes_from_pm: the god's-wife epithet includes
# `ʿAḥmosi Nefertere` (PDF-verified ayin+Ḥ; the tie-break value carries
# `Ahmosi Nefertere` without diacritics — restore post-merge here).
# ALL_CORRECTIONS aggregation enforced by
# `test_all_corrections_includes_every_chunk_list`.
CHUNK31_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT224",
        "occupant_name",
        "ʿAhmosi",
        "PM I.1 p.325 / physical PDF p.343 (TT224). Direct PDF visual check "
        "confirms headword `224. 'AHMOSI [hieroglyph], called HUMAY` — the "
        "apostrophe is PM's convention for ayin (ʿ). Titlecase: `ʿAhmosi`. "
        "All three agents misread the leading ayin as `C` (OCR glyph collision "
        "where ʿ resembles a capital C in the text-layer), emitting `Cahmosi`. "
        "Same OCR-ayin-as-C class as chunk-11 TT29 `[Caḥmosi]` → `[ʿAḥmosi]` "
        "correction (which cross-references this same individual: PM I.1 p.45 "
        "prints `Parents, [ʿAḥmosi] Ḥumay (tomb 224)`). The strip-Ḥ policy "
        "applies only to underdot-Ḥ in occupant_name; the ayin is preserved. "
        "Note: the alt-name `Humay` (= `Ḥumay` with underdot stripped) is "
        "correctly captured in `occupant_alt_names` by the 2/1 majority.",
    ),
    (
        "TT224",
        "notes_from_pm",
        "Overseer of the estate of the god's wife, Overseer of the two granaries "
        "of the god's wife ʿAḥmosi Nefertere. Temp. Tuthmosis III or Hatshepsut. "
        "Parents, Senusert and Taidy. Wife, Nub, Royal concubine (in tombs 29 and 96).",
        "PM I.1 p.325 / physical PDF p.343 (TT224 ʿAhmosi, called Ḥumay). "
        "Two post-merge restorations: (1) restore ayin+Ḥ on `ʿAḥmosi Nefertere` "
        "in the god's-wife epithet — PM prints the queen's name `ʿAḥmosi Nefertere` "
        "with both diacritics in the body of the headword; the tie-break value "
        "carries plain `Ahmosi Nefertere` (ayin and Ḥ both dropped). "
        "notes_from_pm is the verbatim-preserve field; both diacritics must be "
        "restored. (2) the wife's name is `Nub` (bare short form) per direct PDF "
        "visual check; the tie-break value already pins `Nub` correctly (all three "
        "agents' forms Nuby/Nubek/Nuba were wrong; the override value used B/C "
        "structure with Nub restored). This correction entry solely layers the "
        "diacritic restoration on the god's-wife clause.",
    ),
    (
        "TT225",
        "occupant_role",
        "Unknown",
        "PM I.1 p.325 / physical PDF p.343 (TT225). Headword `225. A First prophet "
        "of Ḥathor. Temp. Tuthmosis III (?).` — anonymous occupant (no personal "
        "name). Per the controlled-vocab pairing invariant established by chunk-8 "
        "KV12/KV39/KV56/QV36/QV40/QV73/QV75 and chunk-14 TT58 / chunk-15 TT70: "
        "null `occupant_name` MUST co-occur with `occupant_role=\"Unknown\"`. "
        "Agents A and C emitted `Unknown` (`Unknown` collapses to null at merge per SENTINEL_NULL_STRINGS; CHUNK31_CORRECTIONS restores it post-merge), B emitted "
        "`High Priest`; majority chose null. Fix enforces the pairing invariant.",
    ),
    (
        "TT226",
        "occupant_role",
        "Unknown",
        "PM I.1 p.327 / physical PDF p.345 (TT226). Headword `226. A Royal scribe, "
        "Overseer of the royal nurses. Temp. Amenophis III.` — anonymous occupant. "
        "Per the null-name/null-role pairing invariant (chunk-8 KV12 / chunk-14 TT58 "
        "/ chunk-15 TT70 precedent). Agents A and C emitted `Unknown` "
        "(`Unknown` collapses to null at merge per SENTINEL_NULL_STRINGS; CHUNK31_CORRECTIONS restores it post-merge), B emitted `Official`; majority chose null. "
        "Fix enforces the pairing invariant.",
    ),
    (
        "TT227",
        "occupant_role",
        "Unknown",
        "PM I.1 p.327 / physical PDF p.345 (TT227). Headword `227. Name lost. "
        "Temp. Tuthmosis III.` — anonymous (name lost). Per the null-name/null-role "
        "pairing invariant (chunk-8 KV12 / chunk-14 TT58 / chunk-15 TT70 precedent). "
        "All three agents emitted `Unknown` (`Unknown` collapses to null at merge per SENTINEL_NULL_STRINGS; CHUNK31_CORRECTIONS restores it post-merge); majority chose "
        "null. Fix enforces the pairing invariant.",
    ),
    (
        "TT229",
        "occupant_role",
        "Unknown",
        "PM I.1 p.328 / physical PDF p.346 (TT229). Headword `229. Name lost. "
        "Dyn. XVIII. (Unfinished.)` — anonymous (name lost). Per the "
        "null-name/null-role pairing invariant. All three agents emitted `Unknown` "
        "(`Unknown` collapses to null at merge per SENTINEL_NULL_STRINGS; CHUNK31_CORRECTIONS restores it post-merge). Fix enforces the pairing invariant.",
    ),
    (
        "TT230",
        "occupant_role",
        "Unknown",
        "PM I.1 p.328 / physical PDF p.346 (TT230). Headword `230. Perhaps MEN~, "
        "Scribe of soldiers of the Lord of the Two Lands (from cones). Dyn. XVIII. "
        "(Unfinished.)` — anonymous (name lost; `Perhaps` attribution is to an "
        "identification via cone evidence, not a personal attestation). Per the "
        "null-name/null-role pairing invariant. All three agents emitted `Unknown` "
        "(`Unknown` collapses to null at merge per SENTINEL_NULL_STRINGS; CHUNK31_CORRECTIONS restores it post-merge). Fix enforces the pairing invariant.",
    ),
]


# Chunk-32 (TT231–TT240, Draʿ Abû el-Nagaʿ + Qurnet Muraʿi + Khôkha + ʿAsâsîf).
# 3 tie-break overrides: TT232|notes_from_pm (OCR garble of father's name),
# TT235|occupant_name (3 agents disagree on OCR `USERI;IET`), and
# TT239|attribution_certainty (3-way split on PM's `(?)` hedge).
# Post-merge corrections:
# 1. TT232 notes_from_pm: restore underdot-ḥ in father's name `Weshebamunḥeref`
#    (tie-break pinned agent A's plain `Weshebamunheref`; source OCR `l}.` = ḥ).
# 2. TT232 source_citation.page: 329 → 328 (headword at source line 41, under
#    physical p.346 / printed p.328; majority 2/1 landed on p.329 off-by-one).
# 3. TT236 source_citation.page: 330 → 329 (headword at source line 103, before
#    the p.330 page-break at source line 110; 2/1 majority landed on p.330).
# 4. TT239 notes_from_pm: restore underdot-ḥ in wife's name `Ḥetepti`
#    (source OCR `l:letepti`; all three agents stripped the underdot).
# 5. TT240 notes_from_pm: restore PM-faithful diacritics on the royal name —
#    `Mentuḥotp-Nebḥepetreʿ` (source OCR `Mentul;totp-Nebl;tepetre<`; the
#    `l;t` pattern decodes to `ḥt` here because the `;` ligature glyph
#    represents `ḥ` and the following `t` is the next consonant of `otp` /
#    `epetre`, so the `t` after the ligature is not part of the same
#    grapheme — the OCR cluster `l;t` consumes `ḥ` and the `t` is the next
#    letter; `<` = ayin; PM uses the older
#    PM-style `Mentuḥotp` without medial e, matching the chunk-7
#    `DAN-MentuhotpIWifeOfDjhuti` descriptor convention).
# ALL_CORRECTIONS aggregation enforced by
# `test_all_corrections_includes_every_chunk_list`.
CHUNK32_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT232",
        "notes_from_pm",
        "Scribe of the divine seal of the treasury of Amun. Ramesside. "
        "Father, Weshebamunḥeref.",
        "PM I.1 p.328 / chunk-32 source text line 44 (TT232 Tharwas). "
        "Source OCR reads `Weshebamunl}.eref` where `l}.` is the standard "
        "underdot-Ḥ artifact in this text layer (same class as `I;I` / "
        "`l:I` / `l;I` seen in other chunks). The merge tie-break pinned "
        "agent A's `Weshebamunheref` (cleanest OCR form — preserved the h "
        "consonant, stripped only the underdot). Restore the underdot per "
        "the notes_from_pm verbatim-preserve policy: `Weshebamunheref` → "
        "`Weshebamunḥeref`. Parallel to chunk-8 QV47 `Sit-ḏḥout` and "
        "chunk-9 TT6 `Neferḥōtep` restorations in notes_from_pm.",
    ),
    (
        "TT232",
        "source_citation",
        {"edition": "PM I.1 2nd ed. 1960", "page": 328, "section": "I"},
        "PM I.1 p.328 / chunk-32 source text. TT232 headword `THARWAS` "
        "appears at source line 41, which is under the physical page 346 / "
        "printed page 328 header (source line 1 / page marker). The printed "
        "page 329 header does not appear until source line 54. Agents A+B "
        "both cited page 329 (off-by-one — reading the body continuation "
        "page rather than the headword page); agent C correctly cited 328. "
        "Majority 2/1 picked 329. Correct the off-by-one per the chunk-30 "
        "TT211/TT215/TT216/TT218/TT219 source_citation.page correction "
        "precedent (CHUNK30_CORRECTIONS).",
    ),
    (
        "TT236",
        "source_citation",
        {"edition": "PM I.1 2nd ed. 1960", "page": 329, "section": "I"},
        "PM I.1 p.329 / chunk-32 source text. TT236 headword `HARNAKHT` "
        "appears at source line 103, which is before the physical page 348 / "
        "printed page 330 header at source line 110. The headword is on "
        "printed page 329. Agents A+C both cited page 330 (off-by-one — "
        "reading the body continuation page); agent B correctly cited 329. "
        "Majority 2/1 picked 330. Correct the off-by-one per the chunk-30 "
        "source_citation.page correction precedent.",
    ),
    (
        "TT239",
        "notes_from_pm",
        "Governor of all Northern Lands. Temp. Tuthmosis IV to "
        "Amenophis II (?). Wife, Ḥetepti.",
        "PM I.1 p.330 / chunk-32 source text line 129 (TT239 Penhet). "
        "Source OCR reads `Wife, l:letepti` where `l:l` is the standard "
        "underdot-Ḥ artifact (`l:I` class). PM prints `Ḥetepti` with "
        "underdot-Ḥ. All three agents stripped the underdot, emitting "
        "`Hetepti`. Restore per the notes_from_pm verbatim-preserve policy. "
        "Parallel to chunk-9 TT6 `Neferḥōtep` / `Nebnūfer` underdot "
        "restorations in notes_from_pm.",
    ),
    (
        "TT240",
        "notes_from_pm",
        "Overseer of sealers. Temp. Mentuḥotp-Nebḥepetreʿ. "
        "(L. D. Text, No. 14, New York, M.M.A. Excav. No. 517.) "
        "Parents, Iku and Nebti.",
        "PM I.1 p.330 / chunk-32 source text line 149 (TT240 Meru). "
        "Source OCR reads `Mentul;totp-Nebl;tepetre<` where `l;t` = `ḥt` "
        "(underdot-Ḥ followed by t) and trailing `<` = ayin (ʿ). "
        "PM prints the royal name `Mentuḥotp-Nebḥepetreʿ` — the older "
        "PM spelling of Mentuhotep-Nebhepetre (Nebhepetre Montuhotep II, "
        "XI Dynasty) without medial e, matching the `Mentuhotp` convention "
        "established by the chunk-7 `DAN-MentuhotpIWifeOfDjhuti` descriptor. "
        "The 2/1 majority merge picked agents A+C's `Mentuhotep-Nebhepetre` "
        "(stripped both ḥ underdots, used the modern -hotep spelling, and "
        "dropped the ayin). Restore PM-verbatim form: `Mentuḥotp-Nebḥepetreʿ`.",
    ),
]

CHUNK32_RENAMES: dict[str, str] = {}


# Chunk-33 (TT241–TT250, Khôkha + ʿAsâsîf + Sh. ʿAbd el-Qurna + Deir el-Medina).
# 6 tie-break overrides: TT241|notes_from_pm, TT241|occupant_name,
# TT242|notes_from_pm, TT242|occupant_name, TT243|notes_from_pm,
# TT246|notes_from_pm.
# Post-merge corrections:
# 1. TT241 occupant_name: `Kahmosi` → `ʿAhmosi` (PM headword `<AI;IMOSI` =
#    `ʿAḥmosi`; `<` = ayin, `I;I` = underdot-Ḥ artifact; strip-Ḥ rule → `ʿAhmosi`).
# 2. TT242 occupant_name: `Wehebreconi` → `Wehebrecon` (PM headword
#    `WEI;IEBREC 0!\'` = `Weḥebrecon`; strip-Ḥ, drop phantom terminal `i`).
# 3. TT242 notes_from_pm: add `(L. D. Text, No. 22.)` — tie-break pinned agent C's
#    value which lacked the bibliographic reference present in source and agent B.
# 4. TT248 occupant_name: `Djeḥutmosi` → `Ḏjehutmosi` (PM headword `I>~;~uTMOSI`
#    — `I>~` is OCR for d-bar `Ḏ`; `~;~` is OCR for underdot-Ḥ; 2/1 majority
#    A+C merged to `Djeḥutmosi`, dropping the d-bar; restore d-bar and strip
#    underdot-ḥ per matchable-name-field convention: `Ḏjehutmosi`).
# 5. TT250 occupant_name: `Amenemosi` → `Raʿmosi` (catastrophic misextraction —
#    all 3 agents extracted TT251 content; PM p.336 headword is `RA<MOSI` = `Raʿmosi`).
# 6. TT250 notes_from_pm: full rewrite to `(See tomb 7.) Temp. Ramesses II.`
#    (source text; agents extracted TT251's `Royal scribe, Overseer of the cattle...`).
# 7. TT250 theban_area: `Sh. ʿAbd el-Qurna` → `Deir el-Medina` (source text).
# 8. TT250 shared_with_tombs: `[]` → `["TT7"]` (PM `(See tomb 7.)` cross-ref;
#    parallel to chunk-30 TT212 shared_with_tombs=[\"TT7\"] precedent — same Raʿmosi).
# ALL_CORRECTIONS aggregation enforced by
# `test_all_corrections_includes_every_chunk_list`.
CHUNK33_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT241",
        "occupant_name",
        "ʿAhmosi",
        "PM I.1 p.331 / chunk-33 source text (TT241). Source headword OCR "
        "reads `<AI;IMOSI` where `<` is the standard ayin marker and `I;I` "
        "is the standard underdot-Ḥ artifact in this text layer. PM headword "
        "is `ʿAḥmosi`. The tie-break pinned agent A's `Kahmosi` (closest "
        "phonetically of three wrong reads). Apply strip-Ḥ rule to the "
        "matchable occupant_name field: `ʿAḥmosi` → `ʿAhmosi`. Parallel "
        "to chunk-31 TT224 `ʿAḥmosi-called-Ḥumay` and many prior chunks.",
    ),
    (
        "TT242",
        "occupant_name",
        "Wehebrecon",
        "PM I.1 p.332 / chunk-33 source text (TT242). Source headword OCR "
        "reads `WEI;IEBREC 0!\\'` where `I;I` is underdot-Ḥ and `0!\\'` "
        "decodes to terminal `ON`. PM headword is `WEḤEBRECON`. Strip-Ḥ "
        "rule on the matchable occupant_name field gives `Wehebrecon`. "
        "The tie-break pinned agent B's `Wehebreconi` (best candidate — "
        "correct Ḥ stripping + `on`, but added phantom terminal `i`). "
        "Remove phantom `i`: `Wehebreconi` → `Wehebrecon`.",
    ),
    (
        "TT242",
        "notes_from_pm",
        "Chamberlain of the divine adoratress ʿAnkhnesneferebreʿ. Saite. "
        "Wife, Tadepanehep. Father, Pedeamonnai; mother, Mutardais. "
        "(L. D. Text, No. 22.)",
        "PM I.1 p.332 / chunk-33 source text (TT242 Wehebrecon). Source "
        "confirms: (1) parents `PedeamQnnai` + `Mutardais` (where `Q` = "
        "hieroglyphic `on` → `Pedeamonnai`); (2) wife `Tadepanehep`; "
        "(3) bibliographic ref `(L. D. Text, No. 22.)`. The tie-break "
        "pinned agent C's value which had the best adoratress name spelling "
        "(`<Ankhnesneferebrec` with ayin OCR) and `Pedeamonnai`, but "
        "omitted the L.D. cite. Append the missing bibliographic reference + "
        "restore both ayin glyphs (leading `<` and trailing `c`) to U+02BF "
        "per source-wide diacritic policy (Gemini PR #277 round-1 finding "
        "3283267567/581).",
    ),
    (
        "TT241",
        "notes_from_pm",
        "Scribe of the divine writings, Child of the nursery, Head of "
        "mysteries in the House of the morning. Temp. Tuthmosis III(?). "
        "Wife, ʿAlimosi.",
        "PM I.1 p.331 / chunk-33 source text (TT241 ʿAhmosi). Tie-break "
        "pinned agent C's `<Alimosi` for the wife's name. The leading `<` "
        "is the OCR ayin glyph; restore to U+02BF (`ʿAlimosi`). Stays "
        "agent-C-faithful on the body (`Alimosi`) rather than speculatively "
        "Egyptologically normalizing to `ʿAḥmosi`: PM source OCR `<Al_lmosi` "
        "has `_l` mid-word noise that doesn't unambiguously decode to `Ḥ` "
        "(no `I;I` Ḥ-residual cluster present); per Constitutional Rule 1, "
        "keep the OCR-decoded form and let egyptologist review decide if "
        "the wife's name is the same as the occupant's. Gemini PR #277 "
        "round-1 finding 3283267541.",
    ),
    (
        "TT248",
        "occupant_name",
        "Ḏjehutmosi",
        "PM I.1 p.335 / chunk-33 source text (TT248). Source headword OCR "
        "reads `I>~;~uTMOSI` where `I>~` is the OCR rendering of d-bar `Ḏ` "
        "and `~;~` / `;~` encodes the underdot-Ḥ cluster. PM headword is "
        "`Ḏjeḥutmosi` (d-bar + underdot-Ḥ). The 2/1 majority (agents A+C) "
        "merged to `Djeḥutmosi`, dropping the d-bar. Restore the d-bar per "
        "the PM headword AND apply the strip-Ḥ rule for the matchable "
        "occupant_name field: `Djeḥutmosi` → `Ḏjehutmosi` (d-bar preserved "
        "as a distinguishing radical; underdot-ḥ stripped per README convention).",
    ),
    (
        "TT250",
        "occupant_name",
        "Raʿmosi",
        "PM I.1 p.336 / chunk-33 source text (TT250). Source headword "
        "clearly reads `250. RA<MOSI.` where `<` is the standard ayin "
        "marker → `Raʿmosi`. All three agents extracted TT251's content "
        "(`AMENMOSI / Amenemosi — Royal scribe, Overseer of the cattle of "
        "Amun, Sh. ʿAbd el-Qurna`) instead. TT250 is the same Raʿmosi as "
        "TT7 (PM `See tomb 7.`); the cross-ref aligns with chunk-30 TT212 "
        "which also references TT7. Catastrophic misextraction corrected "
        "from source text.",
    ),
    (
        "TT250",
        "notes_from_pm",
        "(See tomb 7.) Temp. Ramesses II.",
        "PM I.1 p.336 / chunk-33 source text (TT250 Raʿmosi). Source text "
        "for TT250 reads: `250. RA<MOSI. (See tomb 7.) Temp. Ramesses II. "
        "Deir el-Medina.` — this is the complete PM entry body. All three "
        "agents instead extracted TT251's note text (`Royal scribe, "
        "Overseer of the cattle of Amun, Overseer of the magazine of Amun. "
        "Temp. early Tuthmosis III. Father, Nesu, Head of the magazine of "
        "Amun.`). Full rewrite to PM source text.",
    ),
    (
        "TT250",
        "theban_area",
        "Deir el-Medina",
        "PM I.1 p.336 / chunk-33 source text (TT250 Raʿmosi). Source "
        "explicitly states `Deir el-Medina.` as the location. All three "
        "agents extracted `Sh. ʿAbd el-Qurna` from TT251's content. "
        "Corrected from source text.",
    ),
    (
        "TT250",
        "shared_with_tombs",
        ["TT7"],
        "PM I.1 p.336 / chunk-33 source text (TT250 Raʿmosi). Source "
        "reads `(See tomb 7.)` — explicit PM cross-reference to TT7, "
        "which is the same Raʿmosi scribe. Parallel to chunk-30 TT212 "
        "which also references TT7 via shared_with_tombs=[\"TT7\"]. "
        "TT7 shared_with_tombs already includes TT250 as a back-reference "
        "(established in chunk-1 corrections per symmetry convention).",
    ),
]

CHUNK33_RENAMES: dict[str, str] = {}


# Chunk 34: TT251–TT260. Corrections beyond what tie-break-overrides resolved.
# TT71 back-reference: TT252 PM says `Parents, see tomb 71 (brother Senenmut)`,
# establishing a within-section (§ I) shared_with_tombs relationship. By the
# pairing-invariant convention (enforced by test_shared_with_tombs_symmetry_
# within_chunk), TT71 must list TT252. TT71 already has TT353 (see-also
# inscription, also a within-section cross-ref); add TT252 alongside.
# DERIVER_OVERRIDES below handle TT253/TT255/TT257/TT258/TT260
# attribution_certainty over-fire on regnal-date/secondary-figure hedges.
CHUNK34_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT71",
        "shared_with_tombs",
        ["TT252", "TT353"],
        "PM I.1 p.337 / chunk-34 source text (TT252 Senimen). TT252 reads "
        "`Parents, see tomb 71 (brother Senenmut)` — an explicit within-"
        "section (§ I) PM cross-reference from TT252 to TT71. By the "
        "pairing-invariant convention (back-reference symmetry), TT71 "
        "must list TT252 in shared_with_tombs. TT71 already has TT353; "
        "append TT252 and sort lexicographically per existing convention "
        "(earlier TT-number first within the list). Parallel to TT250 "
        "shared_with_tombs=[\"TT7\"] back-ref (CHUNK33_CORRECTIONS).",
    ),
]

CHUNK34_RENAMES: dict[str, str] = {}


# Chunk-35: TT261–TT270. Corrections beyond what tie-break-overrides resolved.
#
# 1. TT261 — `occupant_name`: PM p.344 prints `KHA<EMWĒSET` where `<` is PM's
#    ayin glyph. All three agents dropped the ayin, producing `Khaemweset`.
#    The project-wide convention preserves ayin in `occupant_name` (matchable-
#    name field). Restore to `Khaʿemweset`. Macron-ē stripped per matchable-
#    name diacritic policy.
# 2. TT262 — `occupant_role`: prompt rule says role='Unknown' when
#    occupant_name is null. PM p.344 headword is bare `An Overseer of the
#    fields.` with no name; all agents emitted null despite the rule. Same
#    fix pattern as chunk-2 KV12, chunk-3 KV39, chunk-4 KV56, chunk-8 QV36.
# 3. TT269 — `occupant_role`: same null-name → Unknown rule. PM p.349 prints
#    `269. Name lost. Ramesside.` — no occupant named; agents emitted null.
# 4. TT270 — `notes_from_pm`: PM p.350 / physical PDF p.368 prints
#    `Ptaḥ-Sokari` with underdot-ḥ (verbatim-preserve field). Majority-
#    merged value `Ptah-Sokari` dropped the diacritic. Restore per README's
#    notes_from_pm verbatim-preserve policy.
CHUNK35_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT261",
        "occupant_name",
        "Khaʿemweset",
        "PM I.1 p.344 / physical PDF p.362 prints `KHA<EMWĒSET` where `<` "
        "is PM's ayin glyph and `Ē` is macron-e. All three agents dropped "
        "the ayin; merged value is `Khaemweset`. Project-wide convention "
        "preserves ayin (ʿ) in `occupant_name` per the DAN-Ahhotep / "
        "DAN-AhmosiHenutempet / chunk-7 ayin-family precedent. Macron-ē "
        "stripped per matchable-name diacritic policy (same as "
        "Khaʿemwaset/Tutʿankhamun etc.).",
    ),
    (
        "TT262",
        "occupant_role",
        "Unknown",
        "PM I.1 p.344 / physical PDF p.362. Headword is bare `An Overseer "
        "of the fields. Temp. Tuthmosis III (?).` — no occupant name given. "
        "Prompt rule: role='Unknown' when occupant_name is null. All three "
        "agents emitted null despite the rule. Same fix pattern as "
        "chunk-2 KV12, chunk-3 KV39, chunk-4 KV56, chunk-8 QV36/QV40/"
        "QV73/QV75.",
    ),
    (
        "TT269",
        "occupant_role",
        "Unknown",
        "PM I.1 p.349 / physical PDF p.367. Headword is bare `269. Name "
        "lost. Ramesside.` — no occupant name. Prompt rule: role='Unknown' "
        "when occupant_name is null. All three agents emitted null. Same "
        "fix pattern as TT262 above and the KV12/KV39/KV56/QV36 cluster.",
    ),
    (
        "TT266",
        "source_citation",
        {"edition": "PM I.1 2nd ed. 1960", "page": 346, "section": "I"},
        "PM I.1 p.346 / physical PDF p.364. TT266 headword begins on "
        "printed page 346 (physical page 364); all three agents cited "
        "page 347 (the continuation page). The `source_citation.page` "
        "should record where the headword starts per the project-wide "
        "convention (matching TT265 page=346 on the same physical page). "
        "Same off-by-one class as chunk-34 TT258/TT260 (agent C).",
    ),
    (
        "TT266",
        "shared_with_tombs",
        [],
        "PM I.1 p.346 / physical PDF p.364 (TT266 Amennakht). The phrase "
        "`names in tomb 219` in notes_from_pm records that the occupant's "
        "parents' names are attested in a text within TT219 — a one-way "
        "genealogical name-record reference, NOT a physical sharing or "
        "chapel/burial-chamber split of the same tomb. Majority (A+C) "
        "emitted `[\"TT219\"]`; fix_rows zeroes this out. Contrast with "
        "TT252 `Parents, see tomb 71 (brother Senenmut)` — which is an "
        "explicit PM `see tomb N` cross-reference between brothers' tombs "
        "— and TT265 `(See tomb 215, which is the Chapel.)` — where two "
        "tomb numbers reference the same physical structure. TT219 is a "
        "separate person and tomb (Amennakht, son of TT218's Amennakht); "
        "TT266's occupant is an unrelated person whose parents are merely "
        "named in TT219's inscriptions. The symmetry test "
        "(`test_shared_with_tombs_symmetry_within_chunk`) rightly rejects "
        "the asymmetric one-way reference.",
    ),
    (
        "TT270",
        "notes_from_pm",
        "Warb-priest, Lector of Ptaḥ-Sokari. Dyn. XIX. Destroyed.",
        "PM I.1 p.350 / physical PDF p.368 prints `Ptaḥ-Sokari` with "
        "underdot-ḥ in the compound divine name. The majority-merged value "
        "`Ptah-Sokari` dropped the underdot. `notes_from_pm` is verbatim-"
        "preserve per README policy — restore the underdot.",
    ),
]

CHUNK35_RENAMES: dict[str, str] = {}


# Chunk-36 (TT271-TT280 — 10 rows: TT271-TT278 Qurnet Muraʿi, TT279 ʿAsâsîf,
# TT280 Draʿ Abû el-Nagaʿ). Corrections after 3-agent merge + tie-break pass:
#
# Page citations:
#   TT274: A+B majority=352, correct=351 (physical 369 = printed 351; headword
#          on physical 369, agents cited the continuation page).
#   TT276: A+B majority=353, correct=352 (physical 370 = printed 352).
#   TT277: A+B majority=354, correct=353 (physical 371 = printed 353).
#   TT278: A+B+C all say 356, correct=355 (physical 373 = printed 355; all three
#          agents cited the plan page rather than the headword page).
#   TT280: B+C majority=360, correct=359 (physical 377 = printed 359).
#
# Diacritic and verbatim-preserve restorations:
#   TT272: merged `Amun` → `Amūn` (macron-u; source line 32 `Amlin` = `Amūn`
#          OCR; chunk-12-onward macron-retain policy).
#   TT274: merged `Amun` → `Amūn` (same macron-retain policy).
#   TT276: `Amenhotp` (tie-break intermediate) → `ʿAḥḥotp` (source `<Al_ll_lotp`
#          = ayin + Amenhotp with double-underdot-ḥ; standard Ramesside form;
#          parallel to DAN-AhmosiHenutempet's `ʿAḥḥotp`). Wife `Henutyunu` →
#          `Ḥenutyunu` (source `l:Ienutyunu`, I:I = underdot-Ḥ).
#   TT278: merged `Amen-Re` → `Amen-Reʿ` (source line 286 `Amen-re<` where `<`
#          is PM's ayin glyph; notes_from_pm verbatim-preserve policy).
#   TT279: `Tasentenhor` → `Tasentenḥor` (source line 423 `Tasentenl,>.or`
#          where `l,>.` = underdot-ḥ artifact; verbatim-preserve policy).
#   TT280: merged notes include `Mentuhotp`; restore `(formerly read Meḥenkwetreʿ)`
#          PM-verbatim parenthetical (source line 547 `(formerly read Mel.tenkwetrec)`
#          where `Mel.` = `Meḥ` and trailing `<` = ayin ʿ).
#
# Other:
#   TT279: occupant_alt_names add `Pbes` (source line 421 headword `PABA SA (PBES)`;
#          (PBES) is PM's alternate-name parenthetical, parallel to KV5
#          occupant_alt_names convention).
#   TT280: location_sub_area: majority null; source line 549 prints
#          `In valley south of Deir el-Bal].ri Temples` — set to canonical form.
#
# DERIVER_OVERRIDES: TT276 has `Tuthmosis IV (?)` in notes_from_pm — the `(?)`
# qualifies the REGNAL DATE, not Amenemopet's identification. Same class as
# chunk-10 TT12/TT17/TT19/TT20 etc. Added below.
CHUNK36_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT272",
        "notes_from_pm",
        "Divine father of Amūn in the West, Lector in the Temple of Sokari. Ramesside.",
        "PM I.1 p.351 / chunk-36 source line 32 prints `Amlin` = `Amūn` with "
        "macron-u (OCR artifacts `Aml` misread as `Ami`; the macron-u is the "
        "standard PM Amūn form in body prose). Majority-merged value dropped "
        "the macron. Restore per chunk-12-onward macron-retain policy "
        "(notes_from_pm verbatim-preserve field).",
    ),
    (
        "TT274",
        "source_citation",
        {"edition": "PM I.1 2nd ed. 1960", "page": 351, "section": "I"},
        "PM I.1: TT274 headword starts on physical p.369 = printed p.351 "
        "(chunk-36 source `PHYSICAL PAGE 369 (PRINTED PAGE 351)`, headword "
        "at source line 97). A+B majority cited p.352 (the continuation "
        "page). Per project-wide convention, source_citation.page records "
        "where the headword starts. Same off-by-one class as chunk-35 "
        "TT266 and chunk-34 TT258/TT260.",
    ),
    (
        "TT274",
        "notes_from_pm",
        "First prophet of Monthu of Tod, and of Thebes, sem-priest in the Ramesseum in the estate of Amūn. Ramesside. (Inaccessible.) Wife, ...y.",
        "Restore macron-ū on `Amūn` per chunk-12-onward macron-retain policy "
        "(source line 98 `Amiin` = `Amūn` OCR). The tie-break-overrides.json "
        "TT274|notes_from_pm entry used `Amun` as a stable merge-time "
        "intermediate; this correction layers the macron post-merge per the "
        "verbatim-preserve policy. `Tod` and `(Inaccessible.)` placement "
        "already pinned by the tie-break.",
    ),
    (
        "TT276",
        "source_citation",
        {"edition": "PM I.1 2nd ed. 1960", "page": 352, "section": "I"},
        "PM I.1: TT276 headword starts on physical p.370 = printed p.352 "
        "(chunk-36 source `PHYSICAL PAGE 370 (PRINTED PAGE 352)`, headword "
        "at source line 139). A+B majority cited p.353 (the continuation "
        "page). Per project-wide convention, source_citation.page records "
        "where the headword starts.",
    ),
    (
        "TT276",
        "notes_from_pm",
        "Overseer of the treasury of gold and silver, Judge, Overseer of the cabinet. Temp. Tuthmosis IV (?). Parents, Nekhu (?) and ʿAḥḥotp. Wife, Ḥenutyunu.",
        "Two restorations: (1) `Amenhotp` (tie-break intermediate) → `ʿAḥḥotp`: "
        "source line 142 prints `<Al_ll_lotp` where `<` is PM's ayin glyph and "
        "`Al_ll_lotp` is the OCR rendering of the Ramesside theophoric compound; "
        "PM's printed form is `ʿAḥḥotp` (ayin + double-underdot-ḥ), the standard "
        "Ramesside writing of Amenhotp/Amenhotep — parallel to "
        "DAN-AhmosiHenutempet `Daughter of ʿAḥḥotp` (fix_rows CHUNK7_CORRECTIONS). "
        "(2) `Henutyunu` → `Ḥenutyunu`: source line 142 prints `l:Ienutyunu` where "
        "`l:I` is PM's underdot-Ḥ glyph; notes_from_pm is verbatim-preserve "
        "so the Ḥ underdot is retained.",
    ),
    (
        "TT277",
        "source_citation",
        {"edition": "PM I.1 2nd ed. 1960", "page": 353, "section": "I"},
        "PM I.1: TT277 headword starts on physical p.371 = printed p.353 "
        "(chunk-36 source `PHYSICAL PAGE 371 (PRINTED PAGE 353)`, headword "
        "at source line 205). A+B majority cited p.354 (the continuation "
        "page). Per project-wide convention, source_citation.page records "
        "where the headword starts.",
    ),
    (
        "TT278",
        "source_citation",
        {"edition": "PM I.1 2nd ed. 1960", "page": 355, "section": "I"},
        "PM I.1: TT278 headword starts on physical p.373 = printed p.355 "
        "(chunk-36 source `PHYSICAL PAGE 373 (PRINTED PAGE 355)`, headword "
        "at source line 286). All three agents cited p.356 (the plan/map page). "
        "Per project-wide convention, source_citation.page records where the "
        "headword starts.",
    ),
    (
        "TT278",
        "notes_from_pm",
        "Herdsman of Amen-Reʿ. Ramesside. Wife, Tay, Songstress of Mut.",
        "Restore ayin on `Amen-Reʿ`: source line 286 prints `Amen-re<` where "
        "`<` is PM's ayin glyph. All three agents unanimously dropped the "
        "ayin. notes_from_pm is verbatim-preserve per README policy; the ayin "
        "is a meaningful consonant (distinguishes the solar epithet `Reʿ` from "
        "plain `Re`). Parallel to the DAN-Ahhotep / chunk-7 ayin-preservation "
        "precedents.",
    ),
    (
        "TT279",
        "occupant_alt_names",
        ["Pbes"],
        "PM I.1 p.357 / source line 421 headword prints `PABA SA (PBES)` — the "
        "parenthetical `PBES` is PM's alternate-name marker, parallel to the "
        "convention used for KV5 (`RAMESSES II`) and chunk-8 QV royal-name "
        "alt-names. Majority-merged value left occupant_alt_names=[] because "
        "A+C both omitted the parenthetical; agent B included the alternate in "
        "occupant_name. Add `Pbes` to occupant_alt_names per the schema's "
        "alt-name field purpose.",
    ),
    (
        "TT279",
        "notes_from_pm",
        "Chief steward of the god's wife. Temp. Psammetikhos I. Parents, Pedubaste, Divine father beloved of the god, and Tasentenḥor.",
        "Restore underdot-ḥ on `Tasentenḥor`: source line 423 prints "
        "`Tasentenl,>.or` where `l,>.` is PM's underdot-ḥ OCR glyph. "
        "Tie-break-overrides.json TT279|notes_from_pm used `Tasentenhor` "
        "(no underdot) as the stable merge-time form; this correction layers "
        "the verbatim-preserve underdot per README policy. The PM variant form "
        "in parentheses after the mother's name (source `(or}. f~~)`) is "
        "OCR-damaged and cannot be reliably resolved from the text layer alone; "
        "flagged for egyptologist printed-source review.",
    ),
    (
        "TT280",
        "occupant_name",
        "Meketreʿ",
        "PM I.1 p.359 / source line 547 prints headword `280. MEKETREC` "
        "where `C` is PM's OCR rendering of ayin (ʿ). Tie-break pinned "
        "`Meketrec` verbatim; restore ayin to U+02BF per project-wide "
        "ayin policy (consistent with `notes_from_pm` which uses "
        "`Meḥenkwetreʿ` in the same row). Per Gemini PR #280 round-1 "
        "finding 3283948489.",
    ),
    (
        "TT280",
        "source_citation",
        {"edition": "PM I.1 2nd ed. 1960", "page": 359, "section": "I"},
        "PM I.1: TT280 headword starts on physical p.377 = printed p.359 "
        "(chunk-36 source `PHYSICAL PAGE 377 (PRINTED PAGE 359)`, headword "
        "at source line 547). B+C majority cited p.360 (the continuation "
        "page). Per project-wide convention, source_citation.page records "
        "where the headword starts.",
    ),
    (
        "TT280",
        "location_sub_area",
        "In valley south of Deir el-Baḥri Temples",
        "PM I.1 p.359 / source line 549 prints `In valley south of Deir "
        "el-Bal].ri Temples` where `Bal].ri` = `Baḥri` (OCR artifact; the "
        "PM-faithful canonical form post-issue #291 migration is "
        "`Deir el-Baḥri` with Ḥ-underdot). "
        "Majority (A+C) emitted null; agent B correctly captured this PM "
        "location qualifier but was minority. PM explicitly marks this tomb "
        "outside the standard theban_area grid (`D-3, i, 3` map reference "
        "only). Restore the location_sub_area from the source per the "
        "verbatim-preserve policy. `Deir el-Baḥri` restored from OCR "
        "`Deir el-Bal].ri`.",
    ),
    (
        "TT280",
        "notes_from_pm",
        "Chief steward in ..., Chancellor. Temp. Mentuḥotp (Sʿankhkareʿ). "
        "(Formerly read Meḥenkwetreʿ.) Son Antef, Hereditary Prince.",
        "Three restorations from source line 547-548: (1) `Mentuhotp` → "
        "`Mentuḥotp`: source `Mentul.totp` where `l.` = PM's underdot-ḥ glyph; "
        "notes_from_pm is verbatim-preserve — restore the underdot. (2) Add "
        "`(Formerly read Meḥenkwetreʿ.)`: source line 547 prints `(formerly "
        "read Mel.tenkwetrec)` where `Mel.` = `Meḥ` (underdot-ḥ) and trailing "
        "`c` = ayin ʿ. This is PM's own editorial note about a superseded "
        "reading and belongs verbatim in notes_from_pm (parallel to chunk-3 "
        "KV34 `1st ed. 24` and chunk-2 KV18 `formerly XI` PM-editorial notes). "
        "(3) `Scankhkarec` → `Sʿankhkareʿ`: the prenomen S-ʿnkh-kꜣ-Rʿ "
        "(Sʿankhkareʿ) carries TWO ayins; both leading `c` and trailing `c` "
        "in the OCR represent ayin glyphs (per Gemini PR #280 round-1 "
        "finding 3283948494). `(formerly ...)` capitalised to `(Formerly ...)` "
        "per sentence-opening convention — PM prints the parenthetical "
        "standalone.",
    ),
    (
        "TT274",
        "co_occupants",
        [{"alt_names": [], "name": "...y", "role": "Official"}],
        "The tie-break-overrides.json TT274|co_occupants entry pinned "
        "`role: 'Unknown'`; merge.py's SENTINEL_NULL_STRINGS mechanism "
        "collapsed `Unknown` to null during structured-field deep-normalise. "
        "Restore to `Official` — the wife of a Ramesside sem-priest "
        "(`Amenwahsu`, First prophet of Monthu) is a non-royal woman of the "
        "official class. Consistent with TT6/TT10/TT60/TT122 co_occupant "
        "wives who all carry `Official` role.",
    ),
    (
        "TT280",
        "co_occupants",
        [{"alt_names": [], "name": "Antef", "role": "Official"}],
        "The B+C majority-merged co_occupants had `role: null` because agents "
        "did not assign a role to son Antef. PM source line 783 prints `son "
        "ANTEF ... Hereditary Prince` — Hereditary Prince is a high bureaucratic "
        "title (not a royal-blood designation) in Middle Kingdom Egypt. `Official` "
        "is the appropriate schema-level role per the project-wide convention "
        "that non-royal-blood hereditary titles map to `Official`. Consistent "
        "with TT279's Thalḥorpakhepesh role convention (son of a Late Period "
        "steward).",
    ),
]

CHUNK36_RENAMES: dict[str, str] = {}


CHUNK37_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT281",
        "occupant_name",
        "Mentuhotp-Sʿankhkareʿ",
        "PM I.1 p.364 / chunk-37 source line prints headword "
        "`MENTUI;IOTP-S<ANKHKARE<` where `I;I` = underdot-Ḥ glyph and `<` "
        "= ayin. Agent C dropped the ayins, giving `Mentuhotp-Sankhkare`. "
        "Majority (A+B) correctly has `Mentuhotp-Sʿankhkareʿ` with ayins. "
        "The `occupant_name` field is the matchable-name field — strip-ḥ "
        "policy applies (test_occupant_name_has_no_underdot_h). Underdot-Ḥ "
        "is preserved in `notes_from_pm` per the verbatim-preserve policy. "
        "The majority form `Mentuhotp-Sʿankhkareʿ` (no underdot) is correct "
        "for this field. This entry ensures the post-merge value is stable "
        "and documents the ayin-restoration.",
    ),
    (
        "TT281",
        "notes_from_pm",
        "Unfinished Temple of Mentuḥotp-Sʿankhkareʿ. See Bibl. ii, p. 135.",
        "PM I.1 p.364 / chunk-37 source headword reads `281. Unfinished Temple "
        "of MENTUI;IOTP-S<ANKHKARE<. See Bibl. ii, p. 135.` Agent B correctly "
        "preserved the occupant name in the notes text; A+C majority abbreviated "
        "to `Unfinished Temple. See Bibl. ii, p. 135.` dropping the occupant "
        "qualifier. Restore full PM headword text (verbatim-preserve policy). "
        "`MENTUI;IOTP` decoded to `Mentuḥotp` (I;I = underdot-Ḥ OCR glyph); "
        "`S<ANKHKARE<` decoded to `Sʿankhkareʿ` (< = ayin) per TT280 precedent.",
    ),
    (
        "TT283",
        "notes_from_pm",
        "First prophet of Amūn. Temp. Ramesses II to Sethos II. Wife, Tamut. (name in niche in Court).",
        "Restore macron-ū on `Amūn` per chunk-12-onward macron-retain policy. "
        "Tie-break pinned `Amun` as a stable merge-time intermediate (agent A "
        "had OCR garble `Amin`; B+C had `Amun` without macron). Source prints "
        "`Amiin` (OCR) = `Amūn` with macron-u. Consistent with TT272/TT274 "
        "and all prior chunk `Amūn` restorations.",
    ),
    (
        "TT283",
        "occupant_alt_names",
        ["Roy"],
        "PM I.1 p.365 / chunk-37 source line 34 prints headword `283. ROMA "
        "(RoY)` where `(RoY)` is PM's alternate-name parenthetical. All three "
        "agents emitted `occupant_alt_names: []` missing the `Roy` variant. "
        "Parallel to TT279 `(PBES)` → `occupant_alt_names: [\"Pbes\"]` in "
        "CHUNK36_CORRECTIONS. The parenthetical form without the PM-capitalisation "
        "renders as `Roy` in titlecase.",
    ),
    (
        "TT287",
        "notes_from_pm",
        "Wab-priest of Amūn. Ramesside.",
        "Restore macron-ū on `Amūn` per chunk-12-onward macron-retain policy. "
        "All three agents emitted `Amun` without macron. Source prints `Amlin` "
        "or `Amiin` (OCR artifacts) = `Amūn`. Consistent with TT283/TT272/TT274 "
        "restorations in this and prior chunks.",
    ),
    (
        "TT288",
        "shared_with_tombs",
        [],
        "PM I.1 p.369 / chunk-37 source prints `Re-used by Setau (tomb 289).` "
        "Agents B+C set `shared_with_tombs=[\"TT289\"]`. But `shared_with_tombs` "
        "encodes JOINT BURIAL / SHARED OWNERSHIP (cf. TT181/TT222 joint-burial "
        "pairs where both owners hold the space). TT288 is a RE-USE case: "
        "Setau (TT289 primary occupant) took over Bekenkhons's tomb. The "
        "re-use is already captured by `is_usurped=True` + `notes_from_pm`. "
        "Setting `shared_with_tombs=[\"TT289\"]` creates an asymmetry (TT289 "
        "does NOT reference TT288 in shared_with_tombs) that violates the "
        "`test_shared_with_tombs_symmetry_within_chunk` invariant. Correct to [].",
    ),
    (
        "TT290",
        "occupant_name",
        "Irinufer",
        "PM I.1 p.372 / chunk-37 source line prints headword `2<)0. !RINUFER` "
        "where `2<)0` is the OCR rendering of `290` and `!RINUFER` is the "
        "headword with OCR `!` for `I` (the capital I was garbled to an "
        "exclamation mark). Correct reading is `IRINUFER` → titlecase "
        "`Irinufer`. All three agents emitted `Irinofer` (substituting `o` "
        "for `u`, likely from misreading the OCR). Source-verbatim reading "
        "is `Irinufer`. Parallel pattern to TT278 `Amenemhab` where all agents "
        "garbled the OCR headword and CHUNK36_CORRECTIONS restored the correct "
        "form.",
    ),
    (
        "TT290",
        "notes_from_pm",
        "Servant in the Place of Truth on the West. Ramesside. "
        "Parents, Siwazyt, Head of the bark of Amūn, and Tausert Meḥytkhacti. "
        "Wife, [name unclear in source].",
        "Three restorations: (1) `Amon` → `Amūn` per macron-retain policy "
        "(OCR `Amon` = `Amūn` with macron-u dropped). (2) Mother's compound "
        "name: source line prints `Tausert Mel).ytkhacti` where `l).` = "
        "underdot-ḥ, giving `Meḥytkhacti`. Agent A truncated to `Tausert` "
        "alone; agents B/C either misread (B appended wife name to mother, C "
        "truncated). Tie-break pinned B's expanded form `Tausert Mehytkhacti`; "
        "restore underdot-ḥ to give `Meḥytkhacti`. (3) Wife's name: the OCR "
        "source renders the wife name as a hieroglyphic glyph string "
        "(`\\ l4o 4~ ~ ~.`) that cannot be resolved from the OCR alone. "
        "Agent B incorrectly used the occupant's own name `Irinofer`; agent C "
        "bracketed it with uncertainty. Replace with `[name unclear in source]` "
        "to be corrected after egyptologist printed-source review of PM p.372. "
        "EGYPTOLOGIST REVIEW REQUIRED: wife name of TT290 Irinufer.",
    ),
]


CHUNK37_RENAMES: dict[str, str] = {}


# Chunk-38 (TT291–TT300) corrections after the field-rule-based prompt +
# 3-agent merge + source-text review:
#
# 1. TT292 — `notes_from_pm`: tie-break pinned A's `He-nekhu` (spurious
#    hyphen) for the father name. Source `l:Ie}.nekhu` decodes to
#    `Ḥenekhu` (l:I = underdot-Ḥ, }.= OCR noise). Restore underdot-Ḥ;
#    remove spurious hyphen to give `Ḥenekhu`. EGYPTOLOGIST REVIEW REQUIRED
#    to confirm the exact father-name form from the printed source.
# 2. TT295 — `occupant_name`: tie-break pinned `Dhutmosi` (C's form).
#    Source headword `l)l;IUTMOSI` decodes to `Ḏhutmosi` (l) = d-bar Ḏ,
#    I;I = underdot-Ḥ stripped per matchable-name rule). Add d-bar per
#    TT32/TT205/TT248 precedent.
# 3. TT296 — `notes_from_pm`: majority pinned `Maetmut` (A+C). Source
#    line 204 prints `Ma<etmut` where `<` = PM's ayin glyph → `Maʿetmut`.
#    Only agent B captured the ayin. Restore ayin per verbatim-preserve
#    policy.
# 4. TT292 — EGYPTOLOGIST REVIEW FLAG: father name `He-nekhu` is an OCR
#    intermediate; the exact printed form of the father name in PM I.1 p.375
#    should be confirmed from the printed source.
CHUNK38_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT292",
        "notes_from_pm",
        "Servant in the Place of Truth. Temp. Sethos I to Ramesses II. "
        "Father, Ḥenekhu (from stela in Brit. Mus. 262). Wife, Makhay.",
        "Tie-break pinned A's `He-nekhu` (spurious hyphen, ḥ stripped). "
        "Source line 52 of chunk-38-tt291-tt300.txt prints `l:Ie}.nekhu` "
        "where `l:I` = underdot-Ḥ OCR glyph and `}.` = underdot/OCR noise "
        "cluster. Decoded: `Ḥenekhu` (underdot-Ḥ, no hyphen). Remove "
        "spurious hyphen, restore underdot-Ḥ. `notes_from_pm` is verbatim-"
        "preserve, so underdot-Ḥ is retained here (strip-ḥ rule applies only "
        "to `occupant_name`). EGYPTOLOGIST REVIEW REQUIRED: confirm exact "
        "father-name form from PM I.1 p.375 printed source.",
    ),
    (
        "TT295",
        "occupant_name",
        "Ḏhutmosi",
        "Tie-break pinned C's `Dhutmosi` as intermediate. Source line 153 "
        "of chunk-38-tt291-tt300.txt prints `295· l)l;IUTMOSI` where `l)` "
        "= OCR for d-bar Ḏ and `l;I`/`I;I` = underdot-Ḥ. Full decode: "
        "`ḎḤUTMOSI`. Apply strip-ḥ (underdot-H) for matchable `occupant_name` "
        "field → `Ḏhutmosi`. D-bar `Ḏ` is NOT stripped (only underdot-Ḥ is "
        "stripped per project convention). Consistent with TT32 `Ḏhutmosi`, "
        "TT205 `Ḏhutmosi` in reconciled.jsonl. Task brief names this occupant "
        "`ḎḤUTMOSI` with d-bar explicitly.",
    ),
    (
        "TT295",
        "notes_from_pm",
        "Head of the secrets in the Chest of Anubis, sem-priest in the "
        "Good House, Embalmer. Temp. Tuthmosis IV to Amenophis III (?). "
        "Parents, Sennuter, sem-priest in the Good House, &c., and "
        "Senemiʿoḥ. Wives, Nefertere and Rennutet.",
        "PR #282 round 1 Gemini findings 3284269377/391/406. The tie-break "
        "pinned agent B's form which was the MINORITY on `&c.`: source "
        "merge-disagreements.txt confirms A+C had `&c.` after Sennuter's "
        "title (PM verbatim); B dropped it. Per Constitutional Rule 6 + "
        "majority-rule, restore `&c.` (PM source line 157: "
        "`Sennuter t,` decodes to `Sennuter, sem-priest in the Good House, "
        "&c.`). Two diacritic restorations on mother's name: source "
        "`Senemi<ol,l` decodes as `Senemiʿoḥ` — `<` = ayin (U+02BF), "
        "`ol,l` = OCR for `oḥ` (underdot-Ḥ). notes_from_pm is verbatim-"
        "preserve; restore both ayin + underdot-ḥ. The tie-break "
        "rationale's claim that `C drops &c.` was incorrect — C kept "
        "`&c.`; only B dropped it.",
    ),
    (
        "TT296",
        "notes_from_pm",
        "Scribe of the divine offerings of all the gods, Officer of the treasury "
        "... in the Southern City. Ramesside. Wives, Maʿetmut, Sekhemui, and Nefertere.",
        "Majority (A+C) pinned `Maetmut` (ayin dropped). Source line 204 of "
        "chunk-38-tt291-tt300.txt prints `Ma<etmut` where `<` = PM's ayin "
        "glyph → `Maʿetmut`. Agent B correctly captured the ayin; A+C dropped "
        "it (OCR noise). `notes_from_pm` is verbatim-preserve — restore ayin "
        "per the established `<` = ʿ OCR-diacritic policy. Parallel to "
        "TT94/TT95/TT192 wife-name ayin restorations in prior chunks.",
    ),
]


CHUNK38_RENAMES: dict[str, str] = {}


# === Chunk-39 (TT301–TT310, Draʿ Abû el-Nagaʿ + Deir el-Baḥri + Sh. ʿAbd el-Qurna) =====
# First chunk to introduce `Deir el-Baḥri` as a primary `theban_area` value
# (TT308 Kemsit in the Temple of Mentuḥotp; TT310 anonymous Chancellor).
# The TT280 precedent used `Deir el-Baḥri` only as a `location_sub_area`
# qualifier because TT280's grid (D-3) pointed to Draʿ Abû el-Nagaʿ proper.
# TT308/TT310 are structurally different: PM I.1 p.385-386 lists them under
# the Deir el-Baḥri grid (Map III, C-4) and explicitly names the site in the
# headword. `Deir el-Baḥri` is admitted as a valid `theban_area` value.
#
# Corrections in this chunk:
# 1. TT301 occupant_name: `Khori` → `Hori` (source `I;IORI` where `I;I`=Ḥ;
#    strip-ḥ rule for matchable `occupant_name` field: Ḥori → `Hori`).
# 2. TT302 occupant_name: `Paraemhab` → `Paraʿemhab` (source `PARA<EMI;IAB`
#    where `<`=ayin, `I;I`=Ḥ; strip-ḥ retains ayin: `Paraʿemhab`).
# 3. TT302 notes_from_pm: `Userhat` → `Userḥat` (underdot-ḥ restore in
#    verbatim-preserve notes field; `Userl}~t` OCR → `Userḥat`).
# 4. TT303 occupant_role: `High Priest` → `Official` (Third prophet ≠ First
#    prophet; see CHUNK39_CORRECTIONS note 4 below; not a DERIVER_OVERRIDE
#    as the majority vote was factually wrong on the role mapping).
# 5. TT305 notes_from_pm: restore ayin in `Wab-priest` → `Wʿab-priest`
#    (source `warb-priest` = OCR for wʿab-priest where `<`=ayin rendered as `r`).
# 6. TT305 co_occupants: name `Tamelkhit` → `Tamelhit` (strip-ḥ: source
#    `Tamel;lit` = `Tamelḥit`; strip-ḥ applied → `Tamelhit`).
# 7. TT307 notes_from_pm: parenthesise `(Unfinished.)` per PM source
#    (source line 275: `(Unfinished.)` with parentheses).
# 8. TT308 notes_from_pm: add temple location qualifier and restore diacritics
#    (source line 289: `Deir el-Baḥri, in the Temple of Mentuḥotp.` +
#    ayin on Nebḥepetreʿ + ḥ-underdot on Mentuḥotp and Ḥatḥor).
CHUNK39_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT301",
        "occupant_name",
        "Hori",
        "Source line 8 of chunk-39-tt301-tt310.txt: `301. I;IORI` where `I;I` "
        "= underdot-Ḥ OCR glyph. Full decode: `ḤORI`. Apply strip-ḥ rule for "
        "matchable `occupant_name` field: Ḥori → `Hori`. Tie-break (majority "
        "A+B) pinned `Khori` — the `Kh` is an OCR misread of the `I;I` cluster "
        "rather than the correct strip-ḥ mapping. Correct form is `Hori` (cf. "
        "TT12 `Hori`, TT51 `Userhēt` — strip-ḥ convention applied throughout). "
        "EGYPTOLOGIST REVIEW REQUIRED: confirm Hori vs Khori from PM I.1 p.381 "
        "printed source.",
    ),
    (
        "TT302",
        "occupant_name",
        "Paraʿemhab",
        "Source line 24 of chunk-39-tt301-tt310.txt: `302. PARA<EMI;IAB` where "
        "`<` = PM ayin glyph (→ ʿ) and `I;I` = underdot-Ḥ OCR glyph. Full "
        "decode: `PARAʿEMḤAB`. Apply strip-ḥ for matchable `occupant_name` "
        "field (underdot-Ḥ stripped) but RETAIN ayin ʿ (per TT293 `Raʿmessenakht`, "
        "TT300 `ʿAnhotp` ayin-retain precedent). Correct form: `Paraʿemhab`. "
        "Tie-break majority (B+C) pinned plain `Paraemhab` (dropped ayin).",
    ),
    (
        "TT302",
        "notes_from_pm",
        "Overseer of the magazine. Ramesside. Father, Userḥat, Head of the "
        "magazine of Amun. (Description by GREENLEES, in Philadelphia Univ. Mus.)",
        "Tie-break pinned A's `Userhat` (drops underdot-ḥ). Source line 29 of "
        "chunk-39-tt301-tt310.txt prints `Userl}~t` where `l}` = OCR cluster "
        "for underdot-Ḥ → `Userḥat`. `notes_from_pm` is verbatim-preserve — "
        "restore underdot-ḥ. Cf. TT292 `Ḥenekhu` and TT295 `Senemiʿoḥ` "
        "precedents for underdot-ḥ restoration in notes_from_pm. "
        "EGYPTOLOGIST REVIEW REQUIRED: confirm exact father-name form from "
        "PM I.1 p.381 printed source.",
    ),
    (
        "TT303",
        "occupant_role",
        "Official",
        "PM I.1 p.381 / chunk-39 source. TT303 Paser holds `Third prophet of "
        "Amun` — NOT `First prophet`. `High Priest` / role=`High Priest` is "
        "reserved exclusively for First prophet of Amūn entries throughout "
        "PM I.1 § Numbered Tombs (TT35, TT67, TT72, TT86, TT95, TT97, TT157, "
        "TT222 in reconciled.jsonl). Second through Fourth prophets (cf. TT34 "
        "Fourth prophet, TT39 Second prophet — both `Official`) are `Official`. "
        "Merge majority A+C incorrectly voted `High Priest` on this row. Correct "
        "to `Official` per project role-mapping convention.",
    ),
    (
        "TT305",
        "notes_from_pm",
        "Wʿab-priest in front of Amun, Scribe of the divine offerings of Amun. "
        "Dyn. XIX-XXI. Wife, Tamelḥit.",
        "Two restorations from chunk-39-tt301-tt310.txt source line 191-194. "
        "(1) `Wab-priest` → `Wʿab-priest`: source prints `warb-priest` where "
        "`r` = OCR artifact for ayin `<` glyph (rendered as `r` before `a`). "
        "Full decode `w<ab-priest` = `wʿab-priest`. notes_from_pm is verbatim-"
        "preserve; restore ayin. Cf. TT97 `wʿab-priest` ayin-retain precedent. "
        "(2) `Tamelkhit` → `Tamelḥit`: source line 194 `Tamel;lit` where `;l` "
        "= underdot-Ḥ OCR cluster. notes_from_pm retains underdot-ḥ (verbatim-"
        "preserve). EGYPTOLOGIST REVIEW REQUIRED: confirm wife-name diacritics "
        "from PM I.1 p.383 printed source.",
    ),
    (
        "TT305",
        "co_occupants",
        [{"alt_names": [], "name": "Tamelhit", "role": "Unknown"}],
        "Strip-ḥ for co_occupants.name (matchable-name field): source "
        "`Tamel;lit` = `Tamelḥit` → strip-ḥ → `Tamelhit`. Tie-break pinned "
        "`Tamelkhit` (kh-substitution for ḥ); correct strip-ḥ removes the "
        "underdot-H entirely → `Tamelhit`. Role set to `Unknown` (sentinel-null "
        "normalized from `Unknown` by merge.py; explicit schema value restored). "
        "EGYPTOLOGIST REVIEW REQUIRED: confirm exact wife-name form from PM I.1 "
        "p.383 printed source.",
    ),
    (
        "TT306",
        "co_occupants",
        [{"alt_names": [], "name": "Mutenopet", "role": "Unknown"}],
        "Majority A+B+C agreed on Mutenopet as wife. Role field was "
        "sentinel-null normalized from `Unknown` to null by merge.py. Restore "
        "`Unknown` as explicit role value per schema convention (cf. other "
        "wife co_occupant entries in TT305 + chunk-31 TT225/TT226 sentinel-null restoration precedents).",
    ),
    (
        "TT307",
        "notes_from_pm",
        "(name from ushabti). Dyn. XX-XXI. (Unfinished.) "
        "(Description by GREENLEES, in Philadelphia Univ. Mus.)",
        "Source line 275 of chunk-39-tt301-tt310.txt prints `(Unfinished.)` "
        "WITH parentheses. Tie-break pinned A's form `Unfinished.` (no parens). "
        "Per verbatim-preserve policy, restore PM's parentheses: `(Unfinished.)` "
        "— consistent with how `(Blocked.)` at TT309 is parenthesised in PM.",
    ),
    (
        "TT308",
        "notes_from_pm",
        "Unique royal concubine, Prophetess of Ḥatḥor. Temp. Mentuḥotp "
        "(Nebḥepetreʿ). Deir el-Baḥri, in the Temple of Mentuḥotp. "
        "(NAVILLE, No. 10.)",
        "Three diacritic restorations + temple location addition from source "
        "lines 287-289 of chunk-39-tt301-tt310.txt. (1) `Hathor` → `Ḥatḥor`: "
        "source `l:latl:lor` where `l:l` = underdot-Ḥ OCR glyph × 2. "
        "notes_from_pm verbatim-preserve retains underdot-ḥ. (2) `Mentuhotep` "
        "→ `Mentuḥotp`: source `Mentul;10tp` where `l;10` = underdot-Ḥ cluster. "
        "Cf. TT280 `Mentuḥotp` precedent. (3) `Nebhepetre` → `Nebḥepetreʿ`: "
        "source `Neb}:lepetre<` where `}:l` = underdot-Ḥ and `<` = ayin glyph. "
        "notes_from_pm is verbatim-preserve — restore both underdot-ḥ AND ayin. "
        "Cf. TT280 `Sʿankhkareʿ` dual-ayin precedent. (4) Add temple location "
        "qualifier: source line 289 `Deir el-Bal).ri, in the Temple of "
        "Mentul).otp.` is part of the PM headword (site identification clause). "
        "All three agents omitted this clause; verbatim-preserve policy requires "
        "inclusion. EGYPTOLOGIST REVIEW REQUIRED: confirm all diacritics from "
        "PM I.1 p.385 printed source.",
    ),
    (
        "TT308",
        "location_sub_area",
        "In the Temple of Mentuḥotp",
        "Source line 289: `Deir el-Bal).ri, in the Temple of Mentul).otp.` — "
        "PM places the tomb specifically within the Mentuhotep temple complex "
        "at Deir el-Baḥri. The theban_area captures `Deir el-Baḥri`; the "
        "`location_sub_area` encodes the more precise location. Parallel to "
        "TT280 `In valley south of Deir el-Baḥri Temples` pattern (chunk-36 "
        "CHUNK36_CORRECTIONS). Decode: `Bal).ri` = `Bahari`, `Mentul).otp` = "
        "`Mentuḥotp` (underdot-ḥ restored per notes_from_pm verbatim-preserve). "
        "EGYPTOLOGIST REVIEW REQUIRED: confirm location sub-area form from "
        "PM I.1 p.385 printed source.",
    ),
]


CHUNK39_RENAMES: dict[str, str] = {}


# === Chunk 40: TT311–TT320 (PM I.1 Deir el-Baḥri / Sh. ʿAbd el-Qurna) ========
#
# Pre-merge agents: a=395, b=395, c=394 (394 = c missing 1 row from an earlier
# chunk, not this chunk). Merged: 395 rows. Chunk-40 added 10 rows (TT311-TT320).
#
# Tie-breaks applied (8 entries in tie-break-overrides.json):
#   TT312|occupant_name — Espel(a)shuti (parenthetical-preserve per reconciled
#       precedents Tanezem(t), Amen(hir)khopshef, Nebmehy(t))
#   TT313|notes_from_pm — A's form (OCR-literal `c` ayin; correct Sankhkare
#       vs B's Soankhkare OCR misread)
#   TT316|occupant_name — Neferhotep (strip-h: NEFERH_OTEP → Neferhotep; A correct)
#   TT317|notes_from_pm — C's form (CHAMPOLLION before Parents per PM source order)
#   TT318|notes_from_pm — C's form (CHAMPOLLION before Wife per PM source order)
#   TT319|notes_from_pm — A's form (majority father Sankhbtaui; CHUNK40 fixes mother)
#   TT320|notes_from_pm — C's form (space in `i 2` per PM superscript rendering)
#   TT320|occupant_name — A's Inhapi (ayin restore to Inhaʿpi by CHUNK40 below)
#
# CHUNK40_CORRECTIONS:
# 1. TT311 notes_from_pm: restore `Nebhepetreʿ` (OCR-literal `c` ayin → ʿ)
# 2. TT313 notes_from_pm: restore `Nebḥepetreʿ` and `Sʿankhkareʿ` diacritics
# 3. TT314 dynasty: null → "XI" (source line 160 explicit `Dyn. XI`; majority
#    B+C null is a miss — agent A alone had XI; CHUNK_CORRECTIONS fixes)
# 4. TT315 notes_from_pm: restore `Nebhepetreʿ` (OCR-literal `c` ayin → ʿ)
# 5. TT316 dynasty: null → "XI" (source line 205 explicit `Dyn. XI`; same
#    majority-null-misses pattern as TT314)
# 6. TT317 occupant_name: `Dhutnufer` → `Ḏhutnufer` (d-bar restore per TT32,
#    TT205, TT295 Ḏhutmosi precedents)
# 7. TT319 notes_from_pm: fix mother `Khob` → `Iʿob`, restore father ayin+i
#    to `Sʿankhibtaui`, restore `Nebhepetreʿ`
# 8. TT320 dynasty: null → "XXI" (source line 374 explicit `Dyn. XXI` in
#    Royal Cache clause; majority B+C null is a miss)
# 9. TT320 occupant_name: `Inhapi` → `Inhaʿpi` (ayin restore per TT293/TT300
#    ayin-retain precedent)
#
# DERIVER_OVERRIDES (added below):
#   TT316: `(?)` in `Wife(?), Mery(t).` qualifies the wife-relationship
#     certainty, not the primary occupant Neferhotep's identity.
#   TT317: `(?)` in `Temp. Tuthmosis III(?)` qualifies the regnal date,
#     not the primary occupant Ḏhutnufer's identity.
#   TT318: `(?)` in `Temp. Tuthmosis III to Hatshepsut(?)` qualifies the
#     regnal-range tail (Hatshepsut), not Amenmosi's identity.
#   TT320: `perhaps` in `perhaps wife of Amosis` qualifies the Amosis
#     genealogical relationship, NOT the primary occupant identification.
#     Inḥaʿpi's name is attested on the Royal Cache mummy-cloths (source
#     line 374); only the spousal relationship carries the hedge. Same
#     secondary-clause hedge pattern as TT2 `(probably) Esi` (second wife).
CHUNK40_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT311",
        "notes_from_pm",
        "Seal-bearer of the King of Lower Egypt. Temp. Mentuḥotp-Nebḥepetreʿ.",
        "Source line 40 of chunk-40-tt311-tt320.txt: `311. KHETY..., Seal-bearer "
        "of the King of Lower Egypt. Temp. Mentul:_lotpNebl:_lepetrec.` where "
        "`l:_l` = underdot-Ḥ OCR cluster and `c` = OCR-literal for ayin `<`. "
        "Two restorations: (1) `Mentuhotep-Nebhepetrec` → `Mentuḥotp-Nebḥepetreʿ`: "
        "restore underdot-Ḥ × 2 AND drop the anglicising vowel `e` in `-hotep` → `-ḥotp` (`Mentuhotep` → `Mentuḥotp` per chunk-36/39/40 "
        "TT280/TT308/TT313 Mentuhotep-era precedents) and OCR-literal `c` → ayin ʿ. "
        "notes_from_pm verbatim-preserve retains both diacritics. "
        "EGYPTOLOGIST REVIEW REQUIRED: confirm exact Mentuhotep epithet diacritics "
        "from PM I.1 p.386 printed source.",
    ),
    (
        "TT313",
        "notes_from_pm",
        "Great steward. Temp. Mentuḥotp-Nebḥepetreʿ and Mentuḥotp-Sʿankhkareʿ.",
        "Source line 132 of chunk-40-tt311-tt320.txt: `313. HENENU..., Great "
        "steward. Temp. MentuQ.otp-NebQ.epetre< and MentuQ.otp-S<ankhkare<.` "
        "where `Q.` = underdot-Ḥ and `<` = ayin. Four diacritic restorations: "
        "(1) `Mentuhotep-Nebhepetrec` → `Mentuḥotp-Nebḥepetreʿ` (underdot-Ḥ × 2 "
        "+ ayin); (2) `Mentuhotep-Sankhkare` → `Mentuḥotp-Sʿankhkareʿ` (underdot-Ḥ "
        "+ leading ayin on `Sʿankh` + trailing ayin). notes_from_pm verbatim-preserve "
        "retains all diacritics. Cf. TT280 chunk-36 `Mentuḥotp-Sʿankhkareʿ` "
        "precedent. EGYPTOLOGIST REVIEW REQUIRED: confirm all diacritics from "
        "PM I.1 p.388 printed source.",
    ),
    (
        "TT314",
        "dynasty",
        "XI",
        "Source line 160 of chunk-40-tt311-tt320.txt: `314. HARHQTP..., "
        "Seal-bearer of the King of Lower Egypt, Henchman. Dyn. XI.` — PM "
        "prints explicit `Dyn. XI` in the headword. Merge majority B+C=null "
        "missed this; agent A alone had `XI`. CHUNK40_CORRECTIONS restores "
        "the source-stated dynasty. notes_from_pm `Dyn. XI.` clause already "
        "correct in merged output. Parallel to chunk-19 TT108/TT110 dynasty "
        "null-miss pattern.",
    ),
    (
        "TT315",
        "notes_from_pm",
        "Governor of the town and Vizier, Judge. Temp. Mentuḥotp-Nebḥepetreʿ.",
        "Source line 180 of chunk-40-tt311-tt320.txt: `315. IPI..., Governor "
        "of the town and Vizier, Judge. Temp. Mentul.10tp-NebQ.epetrec.` where "
        "`l.10` / `Q.` = underdot-Ḥ OCR cluster and `c` = OCR-literal ayin. "
        "Two restorations: `Mentuhotep-Nebhepetrec` → `Mentuḥotp-Nebḥepetreʿ` "
        "(underdot-Ḥ × 2 + OCR-literal `c` → ayin ʿ). Same pattern as "
        "TT311/TT313. EGYPTOLOGIST REVIEW REQUIRED: confirm diacritics from "
        "PM I.1 p.389 printed source.",
    ),
    (
        "TT316",
        "dynasty",
        "XI",
        "Source line 205 of chunk-40-tt311-tt320.txt: `316. NEFERH_OTEP..., "
        "Custodian of the bow. Dyn. XI.` — PM prints explicit `Dyn. XI` in "
        "the headword. Merge majority B+C=null missed this; agent A alone had "
        "`XI`. Same majority-null-miss pattern as TT314 in this chunk. "
        "notes_from_pm `Dyn. XI.` clause already correct in merged output.",
    ),
    (
        "TT317",
        "occupant_name",
        "Ḏhutnufer",
        "Source line 229 of chunk-40-tt311-tt320.txt: `317. :>I;IUTNUFER` where "
        "`:>` = d-bar Ḏ OCR sequence and `I;I` = underdot-Ḥ OCR cluster. Full "
        "decode: `ḎḤUTNUFER`. Apply strip-ḥ for `occupant_name` (underdot-Ḥ "
        "stripped) but RETAIN d-bar Ḏ (not a strip-ḥ target; cf. TT32 `Ḏhutmosi`, "
        "TT205 `Ḏhutmosi`, TT295 `Ḏhutmosi` reconciled.jsonl precedents). "
        "Tie-break majority A+B pinned `Dhutnufer` (drops d-bar). Correct form: "
        "`Ḏhutnufer`. EGYPTOLOGIST REVIEW REQUIRED: confirm d-bar form from "
        "PM I.1 p.390 printed source.",
    ),
    (
        "TT319",
        "notes_from_pm",
        "Daughter of Mentuḥotp-Sʿankhibtaui and Iʿob, wife of Mentuḥotp-Nebḥepetreʿ.",
        "Source line 295 of chunk-40-tt311-tt320.txt: `319. NOFRU, daughter of "
        "Mentul.10tp-S<ankhibtaui and I<ob, wife of Mentul.10tp-Nebhepetre<.` "
        "where `l.10` = underdot-Ḥ, `<` = ayin, `I<ob` = mother's name. "
        "Three restorations from tie-break base (A's form with `Sankhbtaui`/`Khob`): "
        "(1) Mother `Khob` → `Iʿob`: source `I<ob` = I + ayin + ob; A's `Khob` "
        "misread initial `I` as `K`. B's `Iob` (drops ayin) and C's `Ikh` (wrong) "
        "are both wrong; decode gives `Iʿob`. "
        "(2) Father `Sankhbtaui` → `Sʿankhibtaui`: source `S<ankhibtaui` adds "
        "ayin after S plus the `i` between `ankh` and `btaui`. "
        "(3) `Nebhepetrec` → `Nebḥepetreʿ` (underdot-Ḥ + ayin per TT311/TT313/TT315). "
        "Also `Mentuhotep` → `Mentuḥotp` (underdot-Ḥ restore × 2). "
        "EGYPTOLOGIST REVIEW REQUIRED: confirm all diacritics from PM I.1 p.391 "
        "printed source.",
    ),
    (
        "TT320",
        "dynasty",
        "XXI",
        "Source line 374 of chunk-40-tt311-tt320.txt: `320. INI;IA<PI, perhaps "
        "wife of Amosis. (Royal Cache, Dyn. XXI, ...)` — PM explicitly states "
        "`Dyn. XXI` in the Royal Cache parenthetical. Merge majority B+C=null "
        "missed this; agent A alone had `XXI`. Same majority-null-miss pattern "
        "as TT314/TT316 in this chunk. The Royal Cache context places the tomb "
        "use squarely in Dyn. XXI.",
    ),
    (
        "TT320",
        "occupant_name",
        "Inhaʿpi",
        "Source line 374 of chunk-40-tt311-tt320.txt: `INI;IA<PI` where `I;I` "
        "= underdot-Ḥ OCR cluster and `<` = ayin glyph. Full decode: `INḤAʿPI`. "
        "Apply strip-ḥ for `occupant_name` matchable field (underdot-Ḥ stripped "
        "to h) but RETAIN ayin ʿ (per TT293 `Raʿmessenakht`, TT300 `ʿAnhotp` "
        "ayin-retain precedent): `INḤAʿPI` → strip-ḥ → `INHAʿPI` → `Inhaʿpi`. "
        "Tie-break pinned A's `Inhapi` (strips ayin too). Restore ayin to give "
        "`Inhaʿpi`. EGYPTOLOGIST REVIEW REQUIRED: confirm exact form from "
        "PM I.1 p.392 printed source.",
    ),
]


CHUNK40_RENAMES: dict[str, str] = {}


# Chunk-41 (TT321–TT330) merge analysis:
#
# Majority-resolved cleanly:
#   TT321|occupant_name — B+C `Khaʿemopet` (ayin restore; A dropped ayin)
#   TT325|occupant_name — A+B null (correct; C spuriously wrote `Smen` from
#     the PM "Possibly SMEN" attribution hedge — primary occupant anonymous)
#   TT326|shared_with_tombs — A+C `["TT3"]` (B missed the cross-ref)
#   TT329|co_occupants — B+C correct named list; A malformed (missing `name`)
#   TT329|is_joint_burial — A+C false (correct; B=true was wrong — this is a
#     hierarchical annexed-tomb structure, NOT a coordinate co-burial)
#   TT329|occupant_name — A+C `Mosi` (primary occupant; B=null wrong)
#
# Majority-WRONG (corrected below):
#   TT322|source_citation.page — A+B=394 but TT322 headword (source line 54)
#     falls on printed page 393 (page break to 394 at source line 62). C=393.
#   TT323|source_citation.page — B+C=395 but TT323 headword (source line 91)
#     falls on printed page 394 (page break to 395 at source line 115). A=394.
#   TT326|source_citation.page — B+C=397 but TT326 headword (source line 203)
#     falls on printed page 396 (page break to 397 at source line 217). A=396.
#   TT328|notes_from_pm — A+C majority drops diacritic from wife Tatemenet vs
#     B's `Tatemeḥet`. Source line 250: `Tatemel].et` where `l].` = underdot-ḥ
#     OCR cluster → `Tatemeḥet`. Restore diacritic in notes_from_pm.
#
# CHUNK41_CORRECTIONS:
# 1. TT321 notes_from_pm: restore Parents clause (majority A+B dropped it;
#    C alone retained "Parents (perhaps), Busentef and Iy (names in tomb
#    219 (5))"). Source line 46 unambiguous. Also: OCR `Bu~entef` —
#    `~` likely underdot-ṣ/ẓ; flag for egyptologist.
# 2. TT322 source_citation.page: majority-wrong 394 → 393.
# 3. TT323 source_citation.page: majority-wrong 395 → 394.
# 4. TT323 notes_from_pm: fix parent name `Ameneminet` → `Amenemḥet` (source
#    line 94 `Ameneml_tet` where `l_t` = underdot-Ḥ OCR cluster → `ḥet`).
#    EGYPTOLOGIST REVIEW REQUIRED.
# 5. TT324 occupant_role: majority A+B=Official override → High Priest.
#    PM headword "Chief prophet of Sobk" — `Chief prophet` = FIRST prophet
#    in Egyptological title convention, same as "High Priest" classification
#    (per chunk-39 TT303 Third prophet → Official; First/Chief prophet →
#    High Priest).
# 6. TT326 source_citation.page: majority-wrong 397 → 396.
# 7. TT328 notes_from_pm: restore diacritic `Tatemenet` → `Tatemeḥet` per
#    source line 250 OCR `Tatemel].et`.
# 8. TT329 notes_from_pm: fix names in pinned tie-break value (C's form):
#    `Icolnufer` → `Icoḥnufer` (source line 266 `Icol].nufer` where `l].` =
#    underdot-ḥ OCR cluster); `Aqatet` → `Patet` (source line 266 `J>.atet`
#    where `J>.` = `P` OCR artifact — PM name is `Pꜣtet`/Patet);
#    `Henutwact` → `Ḥenutwact` (source line 265 `l:Ienutwact` where `l:I` =
#    underdot-Ḥ OCR cluster; strip-ḥ for notes? No — notes_from_pm verbatim-
#    preserve retains diacritics).
# 9. TT330 notes_from_pm: fix OCR-literal ayin `c` in tie-break pin:
#    `Takhac` → `Takhaʿ` (source line 306 `Takha<` where `<` = ayin).
CHUNK41_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT321",
        "notes_from_pm",
        "Servant in the Place of Truth. Ramesside. Parents (perhaps), Busentef and Iy"
        " (names in tomb 219 (5)). Wife, Maani.",
        "Source line 46 of chunk-41-tt321-tt330.txt: `Parents (perhaps), Bu~entef and"
        " ly (names in tomb 2I9 (5)). Wife, Maani`. Merge majority A+B dropped the"
        " Parents clause entirely; C alone retained it. Restore per PM source."
        " `Bu~entef` OCR `~` is ambiguous (likely underdot-ṣ/ẓ); the base form"
        " `Busentef` is used here pending egyptologist printed-source confirmation."
        " EGYPTOLOGIST REVIEW REQUIRED: confirm exact parent name from PM I.1 p.393.",
    ),
    (
        "TT322",
        "source_citation",
        {"edition": "PM I.1 2nd ed. 1960", "page": 393, "section": "I"},
        "TT322 headword appears at source line 54 of chunk-41-tt321-tt330.txt, which"
        " is BEFORE the page break `===== PHYSICAL PAGE 412 (PRINTED PAGE 394) =====`"
        " at source line 62. Printed page = 393. Merge majority A+B=394 was wrong;"
        " C=393 is correct. Corrected per page-break marker.",
    ),
    (
        "TT323",
        "source_citation",
        {"edition": "PM I.1 2nd ed. 1960", "page": 394, "section": "I"},
        "TT323 headword appears at source line 91 of chunk-41-tt321-tt330.txt, which"
        " is AFTER the page break to printed 394 (line 62) but BEFORE the page break"
        " to printed 395 (line 115 `===== PHYSICAL PAGE 413 (PRINTED PAGE 395) =====`)."
        " Printed page = 394. Merge majority B+C=395 was wrong; A=394 is correct.",
    ),
    (
        "TT323",
        "notes_from_pm",
        "Outline-draughtsman of Amun in the Place of Truth, and in the Temple of"
        " Sokari. Temp. Sethos I. Parents, Amenemḥet, Outline-draughtsman in the"
        " Temple of Sokari, and Mutnefert. Wife, Nefertere.",
        "Source line 94 of chunk-41-tt321-tt330.txt: `Parents, Ameneml_tet,`"
        " where `l_t` = underdot-Ḥ OCR cluster → `ḥt` → parent name `Amenemḥet`."
        " Tie-break pinned A's form `Ameneminet` (OCR misread of `l_t` as `in`)."
        " Restore `Amenemḥet` per standard underdot-Ḥ OCR decode (cf. TT123"
        " Amenemḥet precedent in chunk-21 reconciled.jsonl). notes_from_pm"
        " verbatim-preserve retains the diacritic."
        " EGYPTOLOGIST REVIEW REQUIRED: confirm from PM I.1 p.394 printed source.",
    ),
    (
        "TT324",
        "occupant_role",
        "High Priest",
        "PM I.1 p.395 / chunk-41 source line 129-130: `324. ḤATIAY..., Overseer of"
        " the prophets of all the gods, Chief prophet of Sobk, Scribe of the Temple"
        " of Monthu.` `Chief prophet` in Egyptological title taxonomy = First prophet"
        " = High Priest class (the same senior cultic office). Merge majority A+B="
        "`Official` was wrong; C=`High Priest` is correct. Per chunk-39 TT303"
        " precedent: `Third prophet of Amun` → `Official`; `Chief/First prophet` →"
        " `High Priest`. `Chief prophet of Sobk` is the local Sobek cult's first"
        " prophet — highest priestly rank in that temple hierarchy.",
    ),
    (
        "TT325",
        "occupant_role",
        "Unknown",
        "All three agents correctly emitted `Unknown` for the anonymous TT325"
        " occupant. The merge sentinel-null logic collapses the string `Unknown`"
        " to null (SENTINEL_NULL_STRINGS includes 'unknown'), making the merged"
        " row emit null instead of the intended `Unknown`. Restore per prompt"
        " rule 1: `occupant_role='Unknown'` when `occupant_name` is null."
        " Parallel to KV12/KV39/TT58/TT70/TT91 sentinel-null restoration pattern.",
    ),
    (
        "TT326",
        "source_citation",
        {"edition": "PM I.1 2nd ed. 1960", "page": 396, "section": "I"},
        "TT326 headword appears at source line 203 of chunk-41-tt321-tt330.txt, which"
        " is AFTER the page break to printed 396 (line 167"
        " `===== PHYSICAL PAGE 414 (PRINTED PAGE 396) =====`) but BEFORE the page"
        " break to printed 397 (line 217"
        " `===== PHYSICAL PAGE 415 (PRINTED PAGE 397) =====`)."
        " Printed page = 396. Merge majority B+C=397 was wrong; A=396 is correct.",
    ),
    (
        "TT328",
        "notes_from_pm",
        "Servant in the Place of Truth. Dyn. XX. Wife, Tatemeḥet.",
        "Source line 250 of chunk-41-tt321-tt330.txt: `Wife, Tatemel].et` where"
        " `l].` = underdot-ḥ OCR cluster → `ḥ` → `Tatemeḥet`. Merge majority A+C"
        " dropped the diacritic to `Tatemenet`; B=`Tatemeḥet` is correct."
        " notes_from_pm verbatim-preserve retains the underdot-ḥ.",
    ),
    (
        "TT329",
        "notes_from_pm",
        "Mosi and Annexed tomb of Mosi probably his grandson, and Ipy, perhaps"
        " his son, all Servants in the Place of Truth. Ramesside. Wife (of Mosi,"
        " tomb 329), Ḥenutwact. Father (of Mosi, Annexed tomb), Icoḥnufer."
        " Wife (of Mosi, Annexed tomb), Patet (name on stela, Louvre, C. 280,"
        " see infra). Wife (of Ipy), Bakt.",
        "Corrections to tie-break-pinned value (C's form of chunk-41 source lines"
        " 262-268): (0) `Ipy, all Servants` → `Ipy, perhaps his son, all Servants`"
        " — source line 262-263 prints `... and Ipy ..., perhaps his son, all"
        " Servants in the Place of Truth.` The `perhaps his son` qualifying"
        " phrase for Ipy was dropped by all three agents; restore per PM"
        " verbatim-preserve (PR #285 round-1 Gemini finding 3284937977)."
        " (1) `Henutwact` → `Ḥenutwact`: source line 265 `l:Ienutwact`"
        " where `l:I` = underdot-Ḥ OCR cluster; notes_from_pm verbatim-preserve"
        " retains diacritic. (2) `Icolnufer` → `Icoḥnufer`: source line 266"
        " `Icol].nufer` where `l].` = underdot-ḥ OCR cluster. (3) `Aqatet` → `Patet`:"
        " source line 266 `J>.atet` where `J>.` is OCR artifact for `P` (descender"
        " of capital P misread as J-period); PM name is `Pꜣtet`/Patet. Agent A also"
        " had `Patet`; agent B had `Atatef` (OCR-scrambled). `Patet` is correct."
        " EGYPTOLOGIST REVIEW REQUIRED: confirm `Ḥenutwact`, `Icoḥnufer`, and"
        " `Patet` from PM I.1 p.397 printed source.",
    ),
    (
        "TT330",
        "notes_from_pm",
        "Servant in the Place of Truth. Dyn. XIX. Parents, Simut and Peshedu."
        " Wife, Takhaʿ.",
        "Source line 306 of chunk-41-tt321-tt330.txt: `Wife, Takha< i~~` where"
        " `<` = OCR-literal ayin `ʿ`. Tie-break pinned C's form `Takhac` (raw OCR)."
        " Restore ayin: `Takhac` → `Takhaʿ` per TT293/TT300 ayin-retain precedent."
        " Also: tie-break dropped B's `Takhaʿ` (correct) over C's `Takhac` because"
        " C retained the Parents clause. Final form: Parents retained + ayin restored.",
    ),
]


CHUNK41_RENAMES: dict[str, str] = {}


# Pre-merge disagreement map for chunk 42 (TT331–TT340):
#   TT331|notes_from_pm — 3-way tie: A=Hatay+L.D.Text xos, B=Hatiay+L.D.Text 105+Davies bib,
#     C=Hatiay, no bib. Tie-break pinned C-shape with Ḥatiay restored (source line 9
#     `I:Iatiay` where `I:I`=Ḥ). No L.D.Text marker for TT331; that marker belongs to TT335
#     (source line 188). CHUNK42_CORRECTIONS restores Hatiay→Ḥatiay diacritic.
#     EGYPTOLOGIST REVIEW REQUIRED: confirm Ḥatiay from PM I.1 p.399.
#   TT332|source_citation — majority A+B=400; source line 34 is inside PHYSICAL PAGE 417
#     (PRINTED PAGE 399) block (lines 1-52), before page break at line 53. Correct=399.
#   TT333|source_citation — 3-way tie 400/401/399; tie-break → 399 (source line 48 in
#     PRINTED PAGE 399 block). Correct. No further correction needed.
#   TT335|source_citation — majority A+B=402; source line 186 is inside PHYSICAL PAGE 419
#     (PRINTED PAGE 401) block (lines 152-206), before page break to 402 at line 207.
#     Correct=401.
#   TT335|co_occupants — majority A+B=[{role:Official, no name}]; C=[]. TT335 is Nekhtamun
#     solo; no co_occupant. The empty-name entry is a spurious extraction artifact.
#     Correct=[] (C is right).
#   TT339|source_citation — unanimous A+B+C=407; source line 460 is inside PHYSICAL PAGE 424
#     (PRINTED PAGE 406) block (lines 414-468), before page break to 407 at line 469.
#     Correct=406.
#   TT339|co_occupants — majority A+B=[{role:Official, no name}]; C=[{name:Peshedu,...}].
#     This IS joint burial (Huy + Peshedu); co_occupant name Peshedu must be present.
#     Restore name from C's extraction. is_joint_burial already True via majority.
#   TT340|attribution_certainty — majority A+B=probable; C=attested. `perhaps` in notes
#     applies to secondary ownership of tomb 354 (`perhaps also owner of tomb 354`), NOT
#     to Amenemḥet's primary occupancy. DERIVER_OVERRIDE → attested.
#
# CHUNK42_CORRECTIONS:
# 1. TT331 notes_from_pm: restore Ḥatiay diacritic (tie-break value pinned `Hatiay`
#    from C; source `I:Iatiay` where `I:I`=Ḥ OCR cluster → `Ḥatiay`).
#    EGYPTOLOGIST REVIEW REQUIRED: confirm Ḥatiay from PM I.1 p.399.
# 2. TT332 source_citation.page: majority-wrong 400 → 399.
# 3. TT335 source_citation.page: majority-wrong 402 → 401.
# 4. TT335 co_occupants: remove spurious empty-name entry → [].
# 5. TT339 source_citation.page: unanimous-wrong 407 → 406.
# 6. TT339 co_occupants: restore Peshedu name stripped by majority vote.
CHUNK42_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT333",
        "occupant_role",
        "Unknown",
        "TT333 is anonymous (occupant_name=None). merge.py sentinel-null normalization"
        " collapses the string `Unknown` to null. Restore `Unknown` per schema convention"
        " (prompt rule 1: `occupant_role=Unknown` when occupant_name is null)."
        " Same sentinel-null restoration pattern as TT325, KV12, KV39, TT58, TT70, TT91.",
    ),
    (
        "TT334",
        "occupant_role",
        "Unknown",
        "TT334 is anonymous (occupant_name=None). merge.py sentinel-null normalization"
        " collapses the string `Unknown` to null. Restore `Unknown` per schema convention"
        " (prompt rule 1: `occupant_role=Unknown` when occupant_name is null)."
        " Same sentinel-null restoration pattern as TT333, TT325, KV12, KV39.",
    ),
    (
        "TT331",
        "shared_with_tombs",
        ["TT324"],
        "TT331 (Penne) notes: `Father, Ḥatiay (tomb 324)`. TT324 (Ḥatiay, father)"
        " already has shared_with_tombs=[`TT331`] (from chunk-41 reconciliation)."
        " Symmetry invariant requires TT331.shared_with_tombs=[`TT324`] in return."
        " Majority B+C=[] missed the cross-reference; A=[`TT324`] was correct."
        " Restore per `test_shared_with_tombs_symmetry_within_chunk` enforcement.",
    ),
    # TT331|notes_from_pm: tie-break-overrides.json TT331|notes_from_pm value
    # at line 670 already contains the corrected form with Ḥatiay diacritic
    # restored; no separate CHUNK42_CORRECTIONS entry needed since the override
    # value is used directly at merge time (per Gemini PR #286 round-1 finding
    # 3289800344). Symmetry-invariant TT331|shared_with_tombs=["TT324"] is
    # still required via the entry above.
    (
        "TT332",
        "source_citation",
        {"edition": "PM I.1 2nd ed. 1960", "page": 399, "section": "I"},
        "TT332 headword appears at source line 34 of chunk-42-tt331-tt340.txt, inside"
        " the block `===== PHYSICAL PAGE 417 (PRINTED PAGE 399) =====` (lines 1-52),"
        " BEFORE the page break to printed 400 at line 53."
        " Printed page = 399. Merge majority A+B=400 was wrong; C=399 is correct."
        " Same majority-wrong page pattern as chunk-41 TT322/TT323/TT326.",
    ),
    (
        "TT335",
        "source_citation",
        {"edition": "PM I.1 2nd ed. 1960", "page": 401, "section": "I"},
        "TT335 headword appears at source line 186 of chunk-42-tt331-tt340.txt, inside"
        " the block `===== PHYSICAL PAGE 419 (PRINTED PAGE 401) =====` (lines 152-206),"
        " BEFORE the page break to printed 402 at line 207."
        " Printed page = 401. Merge majority A+B=402 was wrong; C=401 is correct."
        " Same majority-wrong page pattern as chunk-41 TT322/TT323/TT326.",
    ),
    (
        "TT335",
        "shared_with_tombs",
        ["TT336"],
        "TT336 (Neferronpet, brother of TT335 Nekhtamun) has shared_with_tombs=[`TT335`]."
        " Symmetry invariant requires TT335.shared_with_tombs=[`TT336`] in return."
        " Source lines 238-239 of chunk-42-tt331-tt340.txt reference Neferronpet (tomb 336)"
        " in TT335 Chamber B scene (13). Majority A+C=[] missed this; only B captured [TT336]"
        " (B also spuriously added TT217/TT292 — the TT336 entry alone is correct)."
        " Agent B's TT217/TT292 additions are spurious scene-based cross-references not"
        " qualifying as shared_with_tombs ownership links. Restore only [TT336] per"
        " `test_shared_with_tombs_symmetry_within_chunk` enforcement.",
    ),
    (
        "TT335",
        "co_occupants",
        [],
        "TT335 (Nekhtamun) is a sole-occupant tomb. Source lines 186-189 of"
        " chunk-42-tt331-tt340.txt name only Nekhtamun as headword owner; Nubemsheset"
        " is his wife (in notes). No co_occupant exists. Majority A+B=[{role:'Official',"
        " no name}] is a spurious extraction artifact (agents invented an unnamed"
        " co_occupant). C=[] is correct. is_joint_burial=False (majority). Reset to [].",
    ),
    (
        "TT337",
        "shared_with_tombs",
        ["TT4"],
        "TT337 (Ken) notes: `Chiseller in the Place of Truth (see tomb 4)`. TT4's"
        " notes (chunk-9, reconciled) read `Perhaps also owner of tomb 337` which"
        " generated TT4.shared_with_tombs=[`TT337`]. Symmetry invariant requires"
        " TT337.shared_with_tombs=[`TT4`] in return. Majority A+C=[] missed the"
        " cross-reference; B=[`TT4`] was correct. Restore per"
        " `test_shared_with_tombs_symmetry_within_chunk` enforcement.",
    ),
    (
        "TT339",
        "source_citation",
        {"edition": "PM I.1 2nd ed. 1960", "page": 406, "section": "I"},
        "TT339 headword appears at source line 460 of chunk-42-tt331-tt340.txt, inside"
        " the block `===== PHYSICAL PAGE 424 (PRINTED PAGE 406) =====` (lines 414-468),"
        " BEFORE the page break to printed 407 at line 469."
        " Printed page = 406. All three agents (unanimous) gave 407 — wrong."
        " Correct = 406. Unanimous-wrong page citation, not resolvable by majority vote;"
        " fixed here per chunk-12/chunk-41 page-citation correction precedent.",
    ),
    (
        "TT339",
        "co_occupants",
        [{"alt_names": [], "name": "Peshedu", "role": "Official"}],
        "TT339 is joint burial of Huy + Peshedu (is_joint_burial=True, all 3 agents"
        " agreed). Source line 460: `339. HUY ..., Servant in the Place of Truth, and"
        " PESHEDU ..., Servant in the Place of Truth, Necropolis-stonemason of Amun in"
        " Karnak.` Only agent C extracted co_occupant name Peshedu; A+B extracted an"
        " unnamed {role:'Official'} stub. Majority vote stripped the name. Restore"
        " Peshedu as co_occupant name from C's extraction, which is source-accurate."
        " Consistent with TT10 (Kasa), TT122 (Amenemḥet), TT181 (Ipuky), TT291"
        " (Nekhtmin) co_occupant name retention precedents.",
    ),
]


CHUNK42_RENAMES: dict[str, str] = {}


# Chunk-43 (TT341–TT350):
# Three tie-break disagreements (TT343|notes_from_pm, TT345|notes_from_pm,
# TT346|notes_from_pm) were resolved via tie-break-overrides.json with PDF
# verification at merge time. DERIVER_OVERRIDE for TT346 attribution_certainty
# is handled below.
#
# Egyptologist printed-source review (PR #287 round 1) flagged 4 P1
# diacritic regressions; 3 accepted as in-scope per-row corrections below
# (TT342 Tepiḥu, TT343 Paḥekmen, TT349 Amenhotp wife). The 4th (TT344
# theban_area `Dra' Abu el-Naga` → PM's printed `Draʿ Abû el-Nagaʿ`) was
# declined as out-of-scope: the canonical sub-site form is project-wide
# convention used by ~30+ rows across 11+ shipped chunks, so a per-row fix
# would break theban_area grouping; tracked as a follow-up cross-chunk
# canonical-form migration issue.
CHUNK43_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT342",
        "notes_from_pm",
        "Hereditary prince, Royal herald. Temp. Tuthmosis III. (CHAMPOLLION, No. 19,"
        " HAY, No. 6.) Mother, Tabenert. Wife, Tepiḥu.",
        "PM I.1 p.409 / physical PDF p.427 prints `Wife, Tepiḥu` with Ḥ-underdot"
        " (egyptologist-reviewer P1.1, PR #287 round 1). Agents split 1/2 on the"
        " diacritic; majority picked the wrong plain-h reading. Restore Ḥ-underdot"
        " per PM's printed page (notes_from_pm verbatim-preserve policy preserves"
        " Ḥ; the strip-Ḥ rule applies only to occupant_name).",
    ),
    (
        "TT343",
        "notes_from_pm",
        "called Paḥekmen, Overseer of works, Child of the nursery. Early Dyn. XVIII."
        " (CHAMPOLLION, No. 37, L. D. Text, No. 74.) Parents, Irtonena and Tirukak.",
        "PM I.1 p.410 / physical PDF p.428 prints `called PAḤEKMEN` with Ḥ-underdot"
        " on the h but PLAIN k (no Ḳ-underdot) — egyptologist-reviewer P1.2 PDF"
        " verification, PR #287 round 1. The chunk-43 OCR cluster `J5:` was decoded"
        " as Ḳ by the 3 agents based on the prompt's general Ḳ-pattern recognition;"
        " PDF reading is authoritative. Compare to same-page `Ḳurna` where Ḳ-underdot"
        " IS unmistakably printed. Restore plain k in the verbatim notes_from_pm.",
    ),
    (
        "TT343",
        "occupant_alt_names",
        ["Pahekmen"],
        "Companion correction to the TT343 notes_from_pm fix above (egyptologist"
        " P1.2). PM prints `Paḥekmen` with Ḥ-underdot + plain k. Per the matchable-name"
        " policy that governs occupant_alt_names (same rules as occupant_name: strip"
        " Ḥ-underdot → plain h, preserve Ḳ but here there is no Ḳ), the alt_names"
        " form is `Pahekmen` (plain h, plain k). The prior reconciled value"
        " `Paheḳmen` had a spurious Ḳ-underdot that was not in PM's printed page.",
    ),
    (
        "TT349",
        "notes_from_pm",
        "Overseer of fowl-houses. Early Dyn. XVIII. Mother, Ipu. Wife, Amenhotp.",
        "PM I.1 p.415 / physical PDF p.433 prints `Wife, Amenhotp` with PLAIN h"
        " (no Ḥ-underdot) — egyptologist-reviewer P1.4 PDF verification, PR #287"
        " round 1. Reconciled value spuriously inserted Ḥ-underdot. Within this"
        " same chunk TT345 + TT346 occupants `Amenhotp` correctly use plain h;"
        " TT349 wife was the outlier. Restore plain h per PM.",
    ),
]

CHUNK43_RENAMES: dict[str, str] = {}


# Chunk-44 (TT351–TT360) corrections.
#
# One substantive correction after merge:
#
# TT358 location_sub_area: majority B+C emitted null; agent A correctly
#   extracted "In Court of Temple of Ḥatshepsut" from PM I.1 p.421. PM
#   prints this as an explicit sub-area descriptor after the main headword
#   clause. Structural parallel: TT308 Kemsit has location_sub_area="In the
#   Temple of Mentuḥotp" (PDF p.403). Restore A's reading per PM verbatim.
#
# Note on TT354 shared_with_tombs: majority B+C emitted ["TT340"]. This is
#   CORRECT — TT340's landed reconciled entry (chunk-42) has
#   shared_with_tombs=["TT354"] based on PM's `(perhaps also owner of tomb 354)`
#   phrasing (explicit ownership formulation). TT354's `Perhaps AMENEMḤET
#   (tomb 340, cf. box-lid)` describes the same relationship from the other
#   side; the symmetry invariant (test_shared_with_tombs_symmetry_within_chunk)
#   requires both sides to reference each other. No correction needed.
CHUNK44_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT358",
        "location_sub_area",
        "In Court of Temple of Ḥatshepsut",
        "PM I.1 p.421 / physical PDF p.439: TT358 (ʿAḥmosi Merytamun)"
        " headword prints `In Court of Temple of Ḥatshepsut` as an explicit"
        " sub-area descriptor, paralleling TT308 Kemsit's"
        " location_sub_area='In the Temple of Mentuḥotp' (PDF p.403)."
        " Agent A correctly extracted this value; majority B+C emitted null."
        " Restore agent A's reading per PM verbatim.",
    ),
    (
        "TT358",
        "occupant_alt_names",
        ["Meryet-Amun"],
        "PM I.1 p.421 / physical PDF p.439 cites Winlock's monograph"
        " `The Tomb of Queen Meryet-Amūn at Thebes` in the headword's"
        " bibliographic reference, giving PM's textual alternative"
        " Romanization (`Meryet-Amūn`) of the same person who is named"
        " `ʿAḤMOSI MERYTAMŪN` in the headword's NAME-token. Per the"
        " matchable-name policy (strip macron-ū → plain u), the alt-name"
        " form is `Meryet-Amun`. This is the form the Met catalog uses"
        " for her own burial finds (M.M.A. Pit 65 sarcophagi + coffins,"
        " cited verbatim in this PM entry). The 3 agents extracted []"
        " (no alt-names) — egyptologist-reviewer P1 PR #290 round 1"
        " identified the missing alias; this restoration adds the single"
        " PM-cited form. Same `external-catalogue label as alt_name`"
        " pattern as chunk-21 TT120 ʿAnen → ['Mahu'] from Gardiner &"
        " Weigall Cat.",
    ),
    (
        "TT353",
        "notes_from_pm",
        "(See tomb 71.) Temp. Ḥatshepsut.",
        "PM I.1 p.417 / physical PDF p.435: TT353 SENENMUT headword prints"
        " `353. SENENMUT. (See tomb 71.) Temp. Ḥatshepsut.` The agents"
        " correctly populated shared_with_tombs=['TT71'] from the"
        " `(See tomb 71.)` cross-ref, but dropped the parenthetical from"
        " notes_from_pm. Per the established 6-row cross-chunk precedent"
        " (TT104, TT131, TT212, TT250, TT265, TT326 all preserve"
        " `(See tomb N.)` in notes_from_pm even when shared_with_tombs"
        " captures the structural relation), the `(See tomb N.)` parenthetical"
        " is preserved in notes_from_pm verbatim. The drop-rule applies only"
        " to `(Also owner of tomb N.)` / `(Perhaps also owner of tomb N.)`"
        " cross-ownership parentheticals (not `See tomb`). Restore per"
        " egyptologist-reviewer P1 PR #290 round 1.",
    ),
    (
        "TT359",
        "notes_from_pm",
        "(See tomb 299 with footnote.) Temp. Ramesses III and IV."
        " (L. D. Text, No. 108, WILKINSON, No. 10.)",
        "PM I.1 p.421 / physical PDF p.439: TT359 INḤERKHAʿ headword prints"
        " `359. INḤERKHAʿ. (See tomb 299 with footnote.) Temp. Ramesses III"
        " and IV.` followed by `(L. D. Text, No. 108, WILKINSON, No. 10.)`"
        " The agents correctly populated shared_with_tombs=['TT299'] +"
        " preserved the bibliographic cross-numbering paren, but dropped the"
        " `(See tomb 299 with footnote.)` cross-ref from notes_from_pm."
        " Restore per the same 6-row prior-chunk precedent cited in the"
        " TT353 entry above. Symmetric fix to TT353; both are PM-faithfulness"
        " regressions vs the established `See tomb N` retention pattern.",
    ),
]

CHUNK44_RENAMES: dict[str, str] = {}


CHUNK45_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT366",
        "notes_from_pm",
        "Custodian of the King's harîm. Temp. Mentuḥotp-Nebḥepetrēʿ."
        " (New York, M.M.A. Excav. No. 820.)",
        "PM I.1 p.429 / physical PDF p.447 (TT366 ZAR). Diacritic restoration"
        " in notes_from_pm verified by reconciliation-agent direct PDF read"
        " during the chunk-45 merge: PM p.429 prints `harîm` with circumflex"
        " î and `Nebḥepetrēʿ` with macron ē + trailing ayin in the"
        " Mentuhotep-II prenomen (one of the canonical Egyptological"
        " transliteration forms of `Nb-ḥpt-Rʿ`). Agent B correctly rendered"
        " both diacritics; A+C majority dropped both (`harim` plain i,"
        " `Nebḥepetreʿ` no macron on ē). Restore PM-faithful diacritics per"
        " the verbatim-preserve policy for notes_from_pm (macrons preserved"
        " in this field per chunk-15-onward convention). Matching the same"
        " fix_rows.py-direct-PDF-cite pattern as TT346 Penrēʿ (chunk-43) and"
        " TT354 (chunk-44) — both subsequently confirmed by"
        " egyptologist-reviewer pass on those PRs. egyptologist-reviewer on"
        " chunk-45 did not specifically re-verify these two macrons but did"
        " not contest them either; the direct PDF read stands as the"
        " source-trace.",
    ),
    (
        "TT369",
        "notes_from_pm",
        "First prophet of Ptaḥ, Third prophet of Amūn. Dyn. XIX."
        " Wife, Taōne(t).",
        "PM I.1 p.432 / physical PDF p.450 (TT369 KAEMWESET). Diacritic"
        " restoration in notes_from_pm verified by reconciliation-agent"
        " direct PDF read during the chunk-45 merge: PM p.432 prints `Taōne(t)`"
        " with macron ō on the vowel. Agent B correctly rendered"
        " `Taōne(t)`; A+C majority dropped the macron to `Taone(t)`."
        " Restore macron ō per the verbatim-preserve policy for"
        " notes_from_pm. The majority `occupant_role=High Priest` (A+B) is"
        " correct and requires no correction (agent C's `Official` was wrong"
        " — `First prophet of Ptaḥ` maps to High Priest under prompt rule 2"
        " per the major-state-cult extension covering Ptaḥ alongside"
        " Amun/Amen-Re). Same fix_rows.py-direct-PDF-cite pattern as the"
        " TT366 entry above.",
    ),
]

CHUNK45_RENAMES: dict[str, str] = {}


# Chunk-46 (TT371–TT380) corrections.
#
# 1. TT371, TT375, TT376, TT377, TT378, TT379 — `occupant_role`: sentinel-
#    null normalisation in merge.py collapses all three agents' `"Unknown"`
#    to null (because "unknown" is in SENTINEL_NULL_STRINGS). Restore per
#    the null-name/null-role pairing invariant established at KV12 (chunk-2),
#    QV36/40/73/75 (chunk-8), TT58 (chunk-14), TT225–TT230 (chunk-26), etc.
#
# 2. TT374 — `notes_from_pm`: agent C correctly included PM's cross-reference
#    sentence `"For position, see p. 292."` (chunk-46 source text line 92,
#    physical PDF p.452 / printed p.434). Agents A+B majority dropped it.
#    Per the verbatim-preserve policy for notes_from_pm and the established
#    precedent of TT304 (`"For position, see p. 356."`) and TT365
#    (`"For position, see p. ..."`) both preserved in reconciled.jsonl,
#    the dropped cross-reference must be restored.
CHUNK46_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT371",
        "occupant_role",
        "Unknown",
        "PM I.1 p.432 / physical PDF p.450 (TT371 anonymous). All three agents"
        " emitted `occupant_role='Unknown'`; merge.py sentinel-null normalisation"
        " collapsed it to null because `'unknown'` is in SENTINEL_NULL_STRINGS."
        " Restore per the null-name/null-role pairing invariant (KV12 chunk-2"
        " precedent; also TT225–TT230 chunk-26, TT375–TT379 same chunk-46).",
    ),
    (
        "TT374",
        "notes_from_pm",
        "Scribe of the treasury in the Ramesseum. Dyn. XIX. For position, see p. 292.",
        "PM I.1 p.434 / physical PDF p.452 (TT374 AMENEMOPET). Chunk-46 source"
        " text line 92 prints `For position, seep. 292.` (OCR artefact of"
        " `see p.`); the actual PM text is `For position, see p. 292.` Agent C"
        " captured this cross-reference; A+B majority dropped it. Verbatim-"
        "preserve policy for notes_from_pm requires restoration. Precedent:"
        " TT304 `For position, see p. 356.` and TT365 `For position, see p. ...`"
        " both preserved in reconciled.jsonl. Direct PDF read during chunk-46"
        " merge confirms the sentence is present on PM p.434.",
    ),
    (
        "TT375",
        "occupant_role",
        "Unknown",
        "PM I.1 p.434 / physical PDF p.452 (TT375 anonymous). Same sentinel-null"
        " collapse as TT371. Restore per null-name/null-role pairing invariant.",
    ),
    (
        "TT376",
        "occupant_role",
        "Unknown",
        "PM I.1 p.434 / physical PDF p.452 (TT376 anonymous). Same sentinel-null"
        " collapse as TT371. Restore per null-name/null-role pairing invariant.",
    ),
    (
        "TT377",
        "occupant_role",
        "Unknown",
        "PM I.1 p.434 / physical PDF p.452 (TT377 anonymous). Same sentinel-null"
        " collapse as TT371. Restore per null-name/null-role pairing invariant.",
    ),
    (
        "TT378",
        "occupant_role",
        "Unknown",
        "PM I.1 p.435 / physical PDF p.453 (TT378 anonymous). Same sentinel-null"
        " collapse as TT371. Restore per null-name/null-role pairing invariant.",
    ),
    (
        "TT379",
        "occupant_role",
        "Unknown",
        "PM I.1 p.435 / physical PDF p.453 (TT379 anonymous). Same sentinel-null"
        " collapse as TT371. Restore per null-name/null-role pairing invariant.",
    ),
    (
        "TT380",
        "notes_from_pm",
        "Chief in Thebes. Ptolemaic. Parents, Dḥout and Esnūter.",
        "PM I.1 p.435 / physical PDF p.453 (TT380 ʿANKHEF(EN)-RĒʿ-ḤARAKHTI)."
        " Two PM-faithfulness regressions in the parents-clause names,"
        " corrected from direct PDF read after egyptologist-reviewer P2 +"
        " code-reviewer P2 surfaced the issues in PR #293 round 1:"
        " (1) Parent name `Dḥout` — PM p.435 prints PLAIN D + ḥ-underdot"
        " (D-ḥ-o-u-t), NOT d-bar Ḏ + ḥ-underdot. Agent C decoded the OCR"
        " cluster `!)!;lout` as d-bar `Ḏḥout` per the Thoth/Djehuty"
        " family convention, but the PDF clearly shows the unbarred D-letter"
        " on p.435. This is the first PM-I.1 instance of `Dḥout` with plain D"
        " (not Ḏ) — possibly a PM-specific Romanization variant or simply not"
        " the Thoth name root despite the surface similarity. (2) Parent name"
        " `Esnūter` with macron-ū — PM p.435 clearly shows macron-ū on the u"
        " vowel. Agents A+C OCR-misread as `Esntiter` (extra t, no macron);"
        " agent B's `Esnūter` was correct but lost in majority vote. Restore"
        " both per PM verbatim under notes_from_pm preserve policy.",
    ),
]

CHUNK46_RENAMES: dict[str, str] = {}


# Chunk-47 corrections (TT381–TT390):
#
# 1. TT388 — `occupant_role`: all three agents emitted `occupant_role='Unknown'`
#    but merge.py sentinel-null normalisation collapsed it to null because
#    `'unknown'` is in SENTINEL_NULL_STRINGS. Restore per the null-name/null-role
#    pairing invariant (KV12 chunk-2 precedent; TT371–TT379 same chunk-46).
#
# 2. TT390 — `notes_from_pm`: B+C 2/1 majority chose `Amon` (no macron) for
#    the divine father's title `Divine father of Amūn`. PM I.1 p.440 / physical
#    PDF p.458 prints `Amūn` with macron-Ū throughout the Saite-period entries.
#    Agent A's `Amūn` (macron) is PM-faithful; B+C dropped the macron.
#    Per the verbatim-preserve policy for `notes_from_pm` and the macron-retention
#    precedent established in chunk-12-onward (TT26, TT53, etc.), restore `Amūn`.
CHUNK47_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT388",
        "occupant_role",
        "Unknown",
        "PM I.1 p.439 / physical PDF p.457 (TT388 anonymous, 'No texts. Saite.')."
        " All three agents emitted `occupant_role='Unknown'`; merge.py sentinel-null"
        " normalisation collapsed it to null because `'unknown'` is in"
        " SENTINEL_NULL_STRINGS. Restore per the null-name/null-role pairing"
        " invariant (KV12 chunk-2 precedent; also TT371–TT379 chunk-46).",
    ),
    (
        "TT390",
        "notes_from_pm",
        "Female scribe, Chief attendant of the divine adoratress Nitocris."
        " Temp. Psammetikhos I. (CHAMPOLLION, No. 16, L. D. Text, No. 94,"
        " Bibl. i, 1st ed. pp. 193-4, ss.) Parents, Ipwer, Divine father of"
        " Amūn, and Tashaiu.",
        "PM I.1 p.440 / physical PDF p.458 (TT390 IRTERAU). B+C 2/1 majority"
        " chose `Amon` (no macron) for `Divine father of Amūn`. PM prints"
        " `Amūn` with macron-Ū throughout the Saite-period entries (physical"
        " PDF p.458 confirmed). Agent A's `Amūn` is PM-faithful; B+C dropped"
        " the macron. Verbatim-preserve policy for notes_from_pm + macron-"
        "retention precedent (TT26/TT53/chunk-12-onward series) requires"
        " restoration.",
    ),
    # Note on TT389: PDF-confirmed priest-title cluster (`smtj-priest` +
    # `ḥsk-priest`) + macron-bearing parent (`Amenemōnet`) now pinned
    # DIRECTLY in tie-break-overrides.json TT389|notes_from_pm value (per
    # Gemini-PR-#294-round-1 architectural simplification: single source of
    # truth for the value, with PDF-verification cite in the tie-break
    # rationale, rather than wrong-merge-value + post-merge correction).
    # No CHUNK47_CORRECTIONS entry needed.
    (
        "TT382",
        "notes_from_pm",
        "Overseer of cattle, Overseer of the treasury, First prophet of"
        " Monthu. Ramesside. Wife, Tiy, Chief of the harîm of Monthu.",
        "PM I.1 p.435 / physical PDF p.453 (TT382 USERMONTU). egyptologist-"
        "reviewer P1 F3 PR #294 round-1 PDF verification: PM p.435 prints"
        " `Chief of the harîm of Monthu` with circumflex î (same character"
        " as 12+ earlier rows preserving `harîm` per chunk-45 TT366 +"
        " chunk-15+ convention). Agent A's `harîm` was PM-faithful; B+C 2/1"
        " majority dropped the circumflex to plain `harim`. No tie-break"
        " entry because the 2/1 was not flagged as 1/1/1 at merge time;"
        " restore via CHUNK47_CORRECTIONS post-merge per the verbatim-"
        "preserve policy for notes_from_pm.",
    ),
]

CHUNK47_RENAMES: dict[str, str] = {}


# ---------------------------------------------------------------------------
# CHUNK 48 — TT391–TT400
# ---------------------------------------------------------------------------
# Sentinel-null restoration: 7 anonymous rows (TT392–TT396, TT399, TT400)
#   extracted occupant_role="Unknown" but merge.py normalises sentinel-null
#   strings to null. Restore per the null-name/null-role pairing invariant
#   (KV12 chunk-2 precedent; chunk-46 TT371–TT379 pattern).
# Cosmetic corrections:
#   TT391 notes_from_pm: B+C 2/1 majority dropped macron-ē from
#     `Khonsemwēset` (→ `Khonsemweset`) and macron-ō from `Neferḥōtep`
#     (→ `Neferḥotep`). PDF p.441 / physical PDF p.459 confirms PM prints
#     `Khonsemwēset-Neferḥōtep` with both macrons. Verbatim-preserve policy
#     for notes_from_pm + macron-retention precedent (TT26/TT53/chunk-12-
#     onward series) requires restoration of agent A's macron-ē AND the
#     macron-ō which all three agents dropped from `Neferḥōtep`.
#   TT397 notes_from_pm: B+C 2/1 majority dropped the space in `Dyn. XVIII (?)`
#     → `Dyn. XVIII(?)`. PDF p.443 / physical PDF p.461 prints `Dyn. XVIII (?)`
#     with space. Verbatim-preserve policy requires restoration.
CHUNK48_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT392",
        "occupant_role",
        "Unknown",
        "PM I.1 p.442 / physical PDF p.460 (TT392 anonymous, 'Name unknown."
        " Saite (?).').  All three agents emitted `occupant_role='Unknown'`;"
        " merge.py sentinel-null normalisation collapsed it to null because"
        " `'unknown'` is in SENTINEL_NULL_STRINGS. Restore per the"
        " null-name/null-role pairing invariant (KV12 chunk-2 precedent;"
        " also TT371–TT379 chunk-46).",
    ),
    (
        "TT393",
        "occupant_role",
        "Unknown",
        "PM I.1 p.442 / physical PDF p.460 (TT393 anonymous, 'Name unknown."
        " Early Dyn. XVIII.'). Same sentinel-null restoration as TT392."
        " KV12 / chunk-46 TT371–TT379 precedent.",
    ),
    (
        "TT394",
        "occupant_role",
        "Unknown",
        "PM I.1 p.442 / physical PDF p.460 (TT394 anonymous, 'No texts."
        " Ramesside.'). Same sentinel-null restoration as TT392.",
    ),
    (
        "TT395",
        "occupant_role",
        "Unknown",
        "PM I.1 p.442 / physical PDF p.460 (TT395 anonymous, 'Name lost."
        " Ramesside.'). Same sentinel-null restoration as TT392.",
    ),
    (
        "TT396",
        "occupant_role",
        "Unknown",
        "PM I.1 p.442 / physical PDF p.460 (TT396 anonymous, 'Name unknown."
        " Dyn. XVIII.'). Same sentinel-null restoration as TT392.",
    ),
    (
        "TT399",
        "occupant_role",
        "Unknown",
        "PM I.1 p.443 / physical PDF p.461 (TT399 anonymous, 'No name."
        " Ramesside.'). Same sentinel-null restoration as TT392.",
    ),
    (
        "TT400",
        "occupant_role",
        "Unknown",
        "PM I.1 p.444 / physical PDF p.462 (TT400 anonymous, 'No texts.')."
        " Same sentinel-null restoration as TT392.",
    ),
    (
        "TT391",
        "notes_from_pm",
        "Prophet of Khonsemwēset-Neferḥōtep, Fourth prophet of Amūn,"
        " Mayor of the City. Probably Dyn. XXV. (CHAMPOLLION, No. 18,"
        " L. D. Text, No. 95, Bibl. i, 1st ed. p. 194, tt.)",
        "PM I.1 p.441 / physical PDF p.459 (TT391 KARABASAKEN). PDF p.459"
        " confirms PM prints `Khonsemwēset-Neferḥōtep` with macron-ē on"
        " `wēset` and macron-ō on `hōtep`. B+C 2/1 majority dropped macron-ē"
        " → `Khonsemweset`; all three agents dropped macron-ō → `Neferḥotep`."
        " Verbatim-preserve policy for notes_from_pm + macron-retention"
        " precedent (TT26/TT53/chunk-12-onward series) requires restoration"
        " of both macrons. egyptologist-reviewer PR #295 round-1 PDF p.441"
        " verification covered the row's full diacritic set (`ḥ/ē/ō` in"
        " `Khonsemwēset-Neferḥōtep` + `ū` in `Amūn`) and confirmed all four"
        " against the printed page. No tie-break entry because neither axis"
        " was flagged as 1/1/1 at merge time; restore via CHUNK48_CORRECTIONS"
        " post-merge per the same fix_rows.py-direct-PDF-cite-with-reviewer-"
        "attribution pattern as TT346 (chunk-43), TT366 + TT369 (chunk-45),"
        " TT380 (chunk-46), TT382 + TT386 + TT389 (chunk-47).",
    ),
    (
        "TT397",
        "notes_from_pm",
        "wʿb-priest of Amūn, Overseer of the magazine of Amūn, First King's"
        " son of Amūn. Dyn. XVIII (?). Wife, Senḥotp, Royal concubine.",
        "PM I.1 p.443 / physical PDF p.461 (TT397 NAKHT). PDF p.461 prints"
        " `Dyn. XVIII (?)` with a space before the parenthetical. B+C 2/1"
        " majority printed `Dyn. XVIII(?)` (no space). Verbatim-preserve"
        " policy for notes_from_pm requires retention of the PM space."
        " egyptologist-reviewer PR #295 round-1 confirmed all 10 chunk-48"
        " rows are PM-faithful against PDF pp.441-444 (no P1/P2/P3"
        " corrections required); this entry restores the PM-faithful space"
        " that the merge majority dropped. No tie-break entry (not a 1/1/1"
        " tie); restore post-merge per the same fix_rows.py-direct-PDF-cite-"
        "with-reviewer-attribution pattern as the TT391 entry above.",
    ),
]

CHUNK48_RENAMES: dict[str, str] = {}


# Chunk-49 (TT401–TT409) corrections.
#
# Sentinel-null restorations:
#   TT402 — `occupant_role`: all three agents emitted `role='Unknown'`; merge.py
#     sentinel-null normalisation collapsed it to null because 'unknown' is in
#     SENTINEL_NULL_STRINGS. Restore per null-name/null-role pairing invariant
#     (KV12 chunk-2 precedent; also TT371–TT379 chunk-46, TT392–TT396/TT399/TT400
#     chunk-48).
#   TT409 — stub entry (`See Addendum, p. 461.`), occupant_name=null. Same
#     sentinel-null collapse as TT402. Restore Unknown per same invariant.
#
# Macron restorations (verbatim-preserve policy):
#   TT401 notes_from_pm: A+B dropped macron-ū from `Amūn`; C preserved it.
#     Merge 2/1 majority chose `Amun`. PM p.444 / physical PDF p.462 prints
#     `goldsmiths of Amūn` with macron-ū — same PM printing convention confirmed
#     on same physical page range as chunk-48 TT391/TT397 restorations.
#   TT403 notes_from_pm: A+B printed `Dyn. XVIII(?)` (no space); C printed
#     `Dyn. XVIII (?)` (with space). Merge 2/1 chose no-space. PM p.445 /
#     physical PDF p.463 prints `Dyn. XVIII (?)` with space before parenthetical.
#     Verbatim-preserve policy requires restoration (same pattern as TT397
#     chunk-48 CHUNK48_CORRECTIONS entry).
#   TT404 notes_from_pm: A+B dropped macron-ū from `Amūn`; C preserved it.
#     Merge 2/1 chose `Amun`. PM p.445 / physical PDF p.463 prints `Prophet of
#     Amūn` with macron-ū. Same macron-retention precedent as TT391/TT401.
CHUNK49_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "TT402",
        "occupant_role",
        "Unknown",
        "PM I.1 p.444 / physical PDF p.462 (TT402 anonymous, 'Name unknown."
        " Temp. Tuthmosis IV to Amenophis III.'). All three agents emitted"
        " `occupant_role='Unknown'`; merge.py sentinel-null normalisation"
        " collapsed it to null because 'unknown' is in SENTINEL_NULL_STRINGS."
        " Restore per null-name/null-role pairing invariant (KV12 chunk-2"
        " precedent; TT371–TT379 chunk-46; TT392–TT400 chunk-48).",
    ),
    (
        "TT409",
        "occupant_role",
        "Unknown",
        "PM I.1 p.446 / physical PDF p.464 (TT409 stub, 'See Addendum, p."
        " 461.'). All three agents emitted `occupant_role='Unknown'`; merge.py"
        " sentinel-null normalisation collapsed it to null. Restore per"
        " null-name/null-role pairing invariant (KV12 chunk-2 precedent;"
        " TT392–TT400 chunk-48). TT409 is a genuine stub — occupant is unknown,"
        " details deferred to the Addendum.",
    ),
    (
        "TT401",
        "notes_from_pm",
        "Overseer of goldsmiths of Amūn (from cone). Temp. Tuthmosis III to"
        " Amenophis II (?). (Inaccessible.)",
        "PM I.1 p.444 / physical PDF p.462 (TT401 NEBSENY). PDF p.462 prints"
        " `goldsmiths of Amūn` with macron-ū. A+B dropped the macron → `Amun`;"
        " merge 2/1 chose `Amun`. Verbatim-preserve policy for notes_from_pm +"
        " macron-retention precedent (TT26/TT53/chunk-12-onward series) requires"
        " restoration. Same printing convention confirmed on same physical page"
        " range as chunk-48 TT391/TT397 restorations (printed pp.441-444).",
    ),
    (
        "TT403",
        "notes_from_pm",
        "(name from ushabti), Temple-scribe, Steward. Dyn. XVIII (?). (CHAMPOLLION,"
        " No. 21, Bibl. i, 1st ed. p. 192, mm.)",
        "PM I.1 p.445 / physical PDF p.463 (TT403 MERYMACET). PDF p.463 prints"
        " `Dyn. XVIII (?)` with a space before the parenthetical. A+B chose"
        " `Dyn. XVIII(?)` (no space); merge 2/1 dropped the space. Verbatim-"
        "preserve policy for notes_from_pm requires retention of the PM space."
        " Same pattern as TT397 chunk-48 CHUNK48_CORRECTIONS entry (`Dyn."
        " XVIII (?)` with space per printed p.443).",
    ),
    (
        "TT404",
        "notes_from_pm",
        "Chief steward of the divine adoratress. Temp. Amenardais I and"
        " Shepenwept II, Dyn. XXV. Parents, Pekiry, Prophet of Amūn, and"
        " Mereskhons.",
        "PM I.1 p.445 / physical PDF p.463 (TT404 AKHAMENERAU). PDF p.463"
        " prints `Prophet of Amūn` with macron-ū. A+B dropped the macron →"
        " `Amun`; merge 2/1 chose `Amun`. Verbatim-preserve policy for"
        " notes_from_pm + macron-retention precedent requires restoration."
        " Same PM macron-ū printing convention as TT401 (chunk-49) and"
        " TT391 (chunk-48).",
    ),
]

CHUNK49_RENAMES: dict[str, str] = {}


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
    CHUNK28_CORRECTIONS,
    CHUNK29_CORRECTIONS,
    CHUNK30_CORRECTIONS,
    CHUNK31_CORRECTIONS,
    CHUNK32_CORRECTIONS,
    CHUNK33_CORRECTIONS,
    CHUNK34_CORRECTIONS,
    CHUNK35_CORRECTIONS,
    CHUNK36_CORRECTIONS,
    CHUNK37_CORRECTIONS,
    CHUNK38_CORRECTIONS,
    CHUNK39_CORRECTIONS,
    CHUNK40_CORRECTIONS,
    CHUNK41_CORRECTIONS,
    CHUNK42_CORRECTIONS,
    CHUNK43_CORRECTIONS,
    CHUNK44_CORRECTIONS,
    CHUNK45_CORRECTIONS,
    CHUNK46_CORRECTIONS,
    CHUNK47_CORRECTIONS,
    CHUNK48_CORRECTIONS,
    CHUNK49_CORRECTIONS,
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
    **CHUNK28_RENAMES,
    **CHUNK29_RENAMES,
    **CHUNK30_RENAMES,
    **CHUNK31_RENAMES,
    **CHUNK32_RENAMES,
    **CHUNK33_RENAMES,
    **CHUNK34_RENAMES,
    **CHUNK35_RENAMES,
    **CHUNK36_RENAMES,
    **CHUNK37_RENAMES,
    **CHUNK38_RENAMES,
    **CHUNK39_RENAMES,
    **CHUNK40_RENAMES,
    **CHUNK41_RENAMES,
    **CHUNK42_RENAMES,
    **CHUNK43_RENAMES,
    **CHUNK44_RENAMES,
    **CHUNK45_RENAMES,
    **CHUNK46_RENAMES,
    **CHUNK47_RENAMES,
    **CHUNK48_RENAMES,
    **CHUNK49_RENAMES,
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
    # Chunk-29 deriver overrides.
    # TT202 Nekhtamun: notes_from_pm contains `Dyn. XIX(?)` — the `(?)` qualifies
    # the dynastic-date assignment, not Nekhtamun's identity as the tomb occupant.
    # PM headword `202. NEKHTAMUN ..., Prophet of Ptaḥ Lord of Thebes, Priest in
    # front of Amun` identifies the person unhedged. Same regnal-date hedge class
    # as chunk-10 TT12/TT17/TT19/TT20, chunk-11 TT22, chunk-13 TT41/TT43/TT45/
    # TT46/TT49. Per chunk-9 TT2 precedent.
    (
        "TT202",
        "attribution_certainty",
        "attested",
        "PM I.1 p.305 prints `202. NEKHTAMUN ..., Prophet of Ptaḥ Lord of "
        "Thebes, Priest in front of Amun. Dyn. XIX(?).` — the `(?)` "
        "qualifies the dynastic-date assignment (Dyn. XIX), not "
        "Nekhtamun's identification as the tomb occupant. The headword "
        "names the person unhedged. Deriver fires context-free on any "
        "`(?)` in notes. Same regnal-date hedge class as chunk-10 TT12/"
        "TT17/TT19/TT20, chunk-13 TT41/TT43/TT45/TT46/TT49, chunk-14 "
        "TT52, chunk-25 TT165. Per chunk-9 TT2 precedent that "
        "attribution_certainty encodes occupant-identity certainty, not "
        "dynastic-date certainty.",
    ),
    # TT205 Ḏhutmosi: notes_from_pm contains `Tuthmosis III(?) to Amenophis II(?)`
    # — both `(?)` qualify the regnal-period endpoints, not Ḏhutmosi's identity.
    # PM headword `205. ḎHUTMOSI ..., Royal butler. Temp. Tuthmosis III(?) to
    # Amenophis II(?).` names Ḏhutmosi unhedged. Same regnal-date class.
    (
        "TT205",
        "attribution_certainty",
        "attested",
        "PM I.1 p.305 prints `205. ḎHUTMOSI ..., Royal butler. Temp. "
        "Tuthmosis III(?) to Amenophis II(?).` — both `(?)` qualify the "
        "regnal-date range endpoints (Tuthmosis III, Amenophis II), not "
        "Ḏhutmosi's identification as the tomb occupant. Same regnal-date "
        "hedge class as TT202 (this chunk) and the chunk-10-to-25 cluster. "
        "Per chunk-9 TT2 precedent.",
    ),
    # TT210 Raʿweben: notes_from_pm contains `Parents(?)` — the `(?)` qualifies
    # the PARENTAGE identification (i.e., PM is uncertain who Raʿweben's parents
    # were), not Raʿweben's identity as the tomb occupant. PM headword `RA<WEBEN
    # ..., Servant in the Place of Truth. Dyn. XIX.` names the occupant unhedged.
    # Structural parallel to TT2 (chunk-9 DERIVER_OVERRIDE): `(probably) Esi`
    # qualifies the second wife, not the headword occupant.
    (
        "TT210",
        "attribution_certainty",
        "attested",
        "PM I.1 p.307 prints `210. RA<WEBEN ..., Servant in the Place of "
        "Truth. Dyn. XIX. ... Parents(?), Piay, Sculptor in the Place of "
        "Truth, and Nefertkhaʿ.` — the `(?)` qualifies the PARENTAGE "
        "identification (PM is uncertain about Raʿweben's parents), not "
        "Raʿweben's identity as the tomb occupant. The headword names "
        "the person and title unhedged. Same secondary-clause hedge class "
        "as TT2 `(probably) Esi` (wife identification). Per chunk-9 TT2 "
        "precedent that attribution_certainty encodes occupant-identity "
        "certainty, not secondary-clause certainty.",
    ),
    # Chunk-31: TT228 Amenmosi, Scribe of the treasury of Amun. The
    # `(probably)` in notes_from_pm (`Father (probably), Camethu (tomb 83)`)
    # qualifies the PATERNAL IDENTIFICATION (PM is uncertain whether Camethu
    # of tomb 83 is Amenmosi's father), NOT the primary occupant attribution.
    # PM headword `228. AMENMOSI ..., Scribe of the treasury of Amun. Dyn. XVIII.`
    # names Amenmosi unhedged. Same secondary-clause hedge class as TT2
    # (chunk-9 DERIVER_OVERRIDE where `(probably) Esi` qualifies the second wife).
    (
        "TT228",
        "attribution_certainty",
        "attested",
        "PM I.1 p.327 / physical PDF p.345 prints `228. AMENMOSI ..., "
        "Scribe of the treasury of Amun. Dyn. XVIII. Father (probably), "
        "Camethu (tomb 83).` — the `(probably)` qualifies the PATERNAL "
        "IDENTIFICATION (PM is uncertain whether Camethu of tomb 83 is "
        "Amenmosi's father), not Amenmosi's identification as the tomb "
        "occupant. The headword names Amenmosi and his title unhedged. "
        "Same secondary-clause hedge class as TT2 `(probably) Esi` "
        "(chunk-9 DERIVER_OVERRIDE). Per chunk-9 TT2 precedent that "
        "attribution_certainty encodes occupant-identity certainty, not "
        "secondary-clause certainty.",
    ),
    # Chunk-31: TT225 anonymous First prophet of Ḥathor. The `(?)` in
    # notes_from_pm qualifies the REGNAL DATE (`Temp. Tuthmosis III (?)`),
    # not the occupant's role attribution. The role `First prophet of Ḥathor`
    # is fully attested by PM's headword; only the dating is hedged.
    # Same regnal-date class as chunk-10 TT12/TT17/TT19/TT20 overrides.
    # (TT230's `Perhaps Menes` is a PRIMARY attribution hedge — different
    # structural class — so TT230 gets no override; `uncertain` from the
    # deriver is correct there.)
    (
        "TT225",
        "attribution_certainty",
        "attested",
        "PM I.1 p.325 / physical PDF p.343 prints `225. A First prophet of "
        "Ḥathor. Temp. Tuthmosis III (?).` — the `(?)` qualifies the "
        "regnal-date (`Tuthmosis III`), not the occupant's role-as-attribution. "
        "The role `First prophet of Ḥathor` is itself unhedged (PM states it "
        "as a definite known fact, not `probably` or `perhaps`). The occupant "
        "is anonymous (no personal name), but the tomb's ownership by SOME "
        "first prophet of Ḥathor is fully attested. Same regnal-date-hedge "
        "class as chunk-10 TT12/TT17/TT19/TT20 and the chunk-10-to-30 cluster "
        "(attribution_certainty encodes occupant-identity certainty, not "
        "regnal-date certainty). Per chunk-9 TT2 precedent.",
    ),
    # Chunk-32: TT239 Penḥet, Governor of all Northern Lands. The `(?)` in
    # notes_from_pm qualifies the REGNAL DATE RANGE (`Temp. Tuthmosis IV to
    # Amenophis II (?)`), not Penḥet's identification. PM headword `239.
    # PENḤET ..., Governor of all Northern Lands. Temp. Tuthmosis IV to
    # Amenophis II (?). Wife, Ḥetepti.` names Penḥet and his title unhedged.
    # Same regnal-range-hedge class as chunk-10 TT12/TT19/TT20 + chunk-31 TT225
    # + many others. Per Gemini PR #276 round-1 finding 3283048776/782/807.
    (
        "TT239",
        "attribution_certainty",
        "attested",
        "PM I.1 p.330 / physical PDF p.348 prints `239. PENḤET ..., "
        "Governor of all Northern Lands. Temp. Tuthmosis IV to Amenophis "
        "II (?). Wife, Ḥetepti.` — the `(?)` qualifies the REGNAL DATE "
        "RANGE (`Temp. Tuthmosis IV to Amenophis II`), not Penḥet's "
        "identification. Penḥet is unambiguously named + role-clustered "
        "as Governor of all Northern Lands. Same regnal-range-hedge "
        "orthogonality class as chunk-10 TT12/TT17/TT19/TT20 + chunk-13 "
        "TT43 + chunk-31 TT225 + many others. Per chunk-9 TT2 precedent "
        "that attribution_certainty encodes occupant-identity certainty, "
        "not regnal-date certainty. Gemini PR #276 round-1 finding "
        "3283048776/782/807. The tie-break-overrides.json TT239|"
        "attribution_certainty entry (pinned `uncertain`) was wrong; "
        "this DERIVER_OVERRIDE overrides the tie-break value post-merge.",
    ),
    # Chunk-33: TT241 ʿAḥmosi, Scribe of divine writings. The `(?)` in
    # notes_from_pm qualifies the REGNAL DATE (`Temp. Tuthmosis III(?)`),
    # not ʿAḥmosi's identification. PM headword `241. <AI;IMOSI ... Temp.
    # Tuthmosis III(?).` names ʿAḥmosi and his titles unambiguously; the
    # SHORTER 1930 JEA article citation confirms the occupant. Same
    # regnal-date-hedge class as chunk-10 TT12/TT17/TT19/TT20 + chunk-13
    # TT43 + chunk-31 TT225 + chunk-32 TT239 + chunk-33 TT249.
    (
        "TT241",
        "attribution_certainty",
        "attested",
        "PM I.1 p.331 / chunk-33 source text (TT241 ʿAḥmosi). Source "
        "reads `241. <AI;IMOSI ... Temp. Tuthmosis III(?).` — the `(?)` "
        "qualifies the REGNAL DATE (`Temp. Tuthmosis III`), not the "
        "occupant's identity. ʿAḥmosi is unambiguously named as headword "
        "and the Shorter 1930 JEA xvi article (cited in source) confirms "
        "the tomb attribution. Same regnal-date-hedge orthogonality class "
        "as chunk-10 TT12/TT17/TT19/TT20, chunk-31 TT225, chunk-32 TT239, "
        "chunk-33 TT249. Per chunk-9 TT2 precedent: attribution_certainty "
        "encodes occupant-identity certainty, not regnal-date certainty.",
    ),
    # Chunk-33: TT249 Neferronpet, Purveyor(?) of date-wine. The `(?)` in
    # notes_from_pm qualifies the ROLE/TITLE (`Purveyor(?)`) and the REGNAL
    # DATE (`Temp. Tuthmosis IV(?)`), not Neferronpet's identification. PM
    # headword `249. NEFERRONPET H7. Purveyor(?) of date-wine. Temp.
    # Tuthmosis IV(?).` names Neferronpet unambiguously (H7 = tomb H.7 in
    # the plan) — there is no uncertainty about who the tomb belongs to.
    # Same role-hedge orthogonality class as chunk-9 TT2 (Amenemḥet, `called
    # Suroy(?)`) + chunk-10 TT12/TT17/TT19/TT20 + chunk-13 TT43 + chunk-31
    # TT225 + chunk-32 TT239. Per chunk-9 TT2 precedent that
    # attribution_certainty encodes occupant-identity certainty, not
    # role/title or regnal-date certainty.
    (
        "TT249",
        "attribution_certainty",
        "attested",
        "PM I.1 p.335 / chunk-33 source text (TT249 Neferronpet). Source "
        "reads `249. NEFERRONPET H7. Purveyor(?) of date-wine. Temp. "
        "Tuthmosis IV(?).` — both `(?)` markers qualify the role/title "
        "(`Purveyor`) and the regnal date (`Tuthmosis IV`), not the "
        "occupant's identity. Neferronpet is unambiguously named and "
        "located (H7 plan reference). The deriver fires on `Purveyor(?)` "
        "as an attribution hedge, but this hedge is on the title, not the "
        "person. Same orthogonality class as chunk-9 TT2, chunk-10 "
        "TT12/TT17/TT19/TT20, chunk-13 TT43, chunk-31 TT225, chunk-32 "
        "TT239 — attribution_certainty encodes occupant-identity certainty, "
        "not role or regnal-date certainty.",
    ),
    # Chunk-34: TT257 Neferhotep. The `perhaps` in notes_from_pm qualifies the
    # identity of MAḤU'S FATHER (`Father (of Maḥu), perhaps Piay`), not
    # Neferhotep's identification. Neferhotep is unambiguously named as PM
    # headword. The usurper Maḥu is certain; only the paternity of Maḥu is
    # hedged with `perhaps`. Same secondary-clause-hedge class as chunk-9 TT2
    # (`called Suroy(?)`), chunk-10 TT12/TT17/TT19/TT20, chunk-31 TT225,
    # chunk-32 TT239, chunk-33 TT241/TT249, chunk-34 TT253/TT255/TT258/TT260.
    (
        "TT257",
        "attribution_certainty",
        "attested",
        "PM I.1 p.342 / chunk-34 source text (TT257 Neferhotep). Source "
        "reads `257. NEFERḤOTEP ... Usurped by MAḤU ... Father (of Maḥu), "
        "perhaps Piay.` — the `perhaps` qualifies the identity of MAḤU'S "
        "FATHER, not Neferhotep's identification. Neferhotep is "
        "unambiguously named as PM headword and the usurpation is certain "
        "(MAḤU's name also appears as a PM headword entry in the same "
        "tomb record). The deriver fires on `perhaps` as an attribution "
        "hedge, but this hedge applies only to a secondary figure's "
        "parentage — not to the primary occupant's identity. Same "
        "secondary-clause-hedge orthogonality class as chunk-9 TT2 "
        "(`called Suroy(?)`), chunk-10 TT12/TT17/TT19/TT20, chunk-31 "
        "TT225, chunk-32 TT239, chunk-33 TT241/TT249, chunk-34 "
        "TT253/TT255/TT258/TT260 — attribution_certainty encodes "
        "occupant-identity certainty, not secondary-figure paternity.",
    ),
    # Chunk-34: TT253 Khnemmosi. The `(?)` in notes_from_pm qualifies the
    # REGNAL DATE (`Temp. Amenophis III (?)`), not Khnemmosi's identification.
    # PM headword `253. KHNEMMOSI` names Khnemmosi unambiguously. Same
    # regnal-date-hedge orthogonality class as chunk-10 TT12/TT17/TT19/TT20,
    # chunk-31 TT225, chunk-32 TT239, chunk-33 TT241/TT249.
    (
        "TT253",
        "attribution_certainty",
        "attested",
        "PM I.1 p.338 / chunk-34 source text (TT253 Khnemmosi). Source "
        "reads `253. KHNEMMOSI ... Temp. Amenophis III (?).` — the `(?)` "
        "qualifies the REGNAL DATE (`Temp. Amenophis III`), not the "
        "occupant's identity. Khnemmosi is unambiguously named as headword "
        "with no identity uncertainty in PM. The deriver fires on the "
        "regnal-date `(?)` as an attribution hedge. Same regnal-date-hedge "
        "orthogonality class as chunk-10 TT12/TT17/TT19/TT20, chunk-31 "
        "TT225, chunk-32 TT239, chunk-33 TT241/TT249 — attribution_certainty "
        "encodes occupant-identity certainty, not regnal-date certainty.",
    ),
    # Chunk-34: TT255 Roy. The `(?)` in notes_from_pm qualifies the
    # REGNAL DATE (`Temp. Haremhab (?)`), not Roy's identification.
    # PM headword `255. ROY` names Roy unambiguously.
    (
        "TT255",
        "attribution_certainty",
        "attested",
        "PM I.1 p.340 / chunk-34 source text (TT255 Roy). Source reads "
        "`255. ROY ... Temp. Haremhab (?).` — the `(?)` qualifies the "
        "REGNAL DATE (`Temp. Haremhab`), not Roy's identity. Roy is "
        "unambiguously named as headword with no identity uncertainty. "
        "Same regnal-date-hedge orthogonality class as chunk-10 "
        "TT12/TT17/TT19/TT20, chunk-31 TT225, chunk-32 TT239, chunk-33 "
        "TT241/TT249, chunk-34 TT253 — attribution_certainty encodes "
        "occupant-identity certainty, not regnal-date certainty.",
    ),
    # Chunk-34: TT258 Menkheper. The `(?)` in notes_from_pm qualifies the
    # REGNAL DATE (`Temp. Tuthmosis IV (?)`), not Menkheper's identification.
    # PM headword `258. MENKHEPER` names Menkheper unambiguously.
    (
        "TT258",
        "attribution_certainty",
        "attested",
        "PM I.1 p.342 / chunk-34 source text (TT258 Menkheper). Source "
        "reads `258. MENKHEPER ... Temp. Tuthmosis IV (?).` — the `(?)` "
        "qualifies the REGNAL DATE (`Temp. Tuthmosis IV`), not Menkheper's "
        "identity. Menkheper is unambiguously named as headword. Same "
        "regnal-date-hedge orthogonality class as chunk-10 "
        "TT12/TT17/TT19/TT20, chunk-31 TT225, chunk-32 TT239, chunk-33 "
        "TT241/TT249, chunk-34 TT253/TT255 — attribution_certainty encodes "
        "occupant-identity certainty, not regnal-date certainty.",
    ),
    # Chunk-34: TT260 User. The `(?)` in notes_from_pm qualifies the
    # REGNAL DATE (`Temp. Tuthmosis III (?)`), not User's identification.
    # PM headword `260. USER` names User unambiguously.
    (
        "TT260",
        "attribution_certainty",
        "attested",
        "PM I.1 p.344 / chunk-34 source text (TT260 User). Source reads "
        "`260. USER ... Temp. Tuthmosis III (?).` — the `(?)` qualifies "
        "the REGNAL DATE (`Temp. Tuthmosis III`), not User's identity. "
        "User is unambiguously named as headword. Same regnal-date-hedge "
        "orthogonality class as chunk-10 TT12/TT17/TT19/TT20, chunk-31 "
        "TT225, chunk-32 TT239, chunk-33 TT241/TT249, chunk-34 "
        "TT253/TT255/TT258 — attribution_certainty encodes occupant-identity "
        "certainty, not regnal-date certainty.",
    ),
    # Chunk-35: TT262 (anonymous Overseer of fields). The `(?)` in
    # notes_from_pm qualifies the REGNAL DATE (`Temp. Tuthmosis III (?)`),
    # not the occupant's identification. PM p.344 headword is the bare
    # description `An Overseer of the fields.` — the occupant is anonymous
    # (no name), so occupant_name=null and occupant_role='Unknown'. The
    # deriver fires on the regnal-date `(?)` hedge. Attribution_certainty
    # encodes identity certainty (can we identify the occupant?), not
    # regnal-date certainty — same orthogonality class as chunk-10
    # TT12/TT17/TT19/TT20, chunk-31 TT225, chunk-32 TT239, chunk-33
    # TT241/TT249, chunk-34 TT253/TT255/TT258/TT260.
    (
        "TT262",
        "attribution_certainty",
        "attested",
        "PM I.1 p.344 / physical PDF p.362 (TT262, anonymous). Headword "
        "is bare `An Overseer of the fields. Temp. Tuthmosis III (?).` — "
        "the `(?)` qualifies the REGNAL DATE, not occupant identity. The "
        "occupant is anonymous (no name); `attested` reflects that PM "
        "records this tomb as definitively belonging to this person (even "
        "unnamed), not that the attribution is uncertain. Same regnal-date-"
        "hedge orthogonality class as chunk-10 TT12/TT17/TT19/TT20, chunk-"
        "31 TT225, chunk-32 TT239, chunk-33 TT241/TT249, chunk-34 "
        "TT253/TT255/TT258/TT260 — attribution_certainty encodes occupant-"
        "identity certainty, not regnal-date certainty.",
    ),
    # Chunk-36: TT276 Amenemopet. The `(?)` in notes_from_pm qualifies the
    # REGNAL DATE (`Temp. Tuthmosis IV (?)`), not Amenemopet's identification.
    # PM headword `276. AMENEMOPET ... Overseer of the treasury of gold and
    # silver, Judge, Overseer of the cabinet. Temp. Tuthmosis IV (?).` names
    # Amenemopet and his titles unambiguously; the `(?)` only qualifies the
    # regnal period. Same regnal-date-hedge orthogonality class as chunk-10
    # TT12/TT17/TT19/TT20, chunk-31 TT225, chunk-32 TT239, chunk-33
    # TT241/TT249, chunk-34 TT253/TT255/TT258/TT260, chunk-35 TT262.
    (
        "TT276",
        "attribution_certainty",
        "attested",
        "PM I.1 p.352 / chunk-36 source lines 139-140 (TT276 Amenemopet). "
        "Source reads `276. AMENEMOPET ... Overseer of the treasury of gold "
        "and silver, Judge, Overseer of the cabinet. Temp. Tuthmosis IV (?).` "
        "— the `(?)` qualifies the REGNAL DATE (`Temp. Tuthmosis IV`), not "
        "Amenemopet's identity. Amenemopet is unambiguously named as headword "
        "with no identity uncertainty in PM. The deriver fires on the regnal-"
        "date `(?)` as an attribution hedge. Same regnal-date-hedge "
        "orthogonality class as chunk-10 TT12/TT17/TT19/TT20, chunk-31 "
        "TT225, chunk-32 TT239, chunk-33 TT241/TT249, chunk-34 "
        "TT253/TT255/TT258/TT260, chunk-35 TT262 — attribution_certainty "
        "encodes occupant-identity certainty, not regnal-date certainty.",
    ),
    # Chunk-37 DERIVER_OVERRIDES: TT284 and TT288 use PM's `(Reused.)` /
    # `Re-used by Setau` language for secondary use of a tomb. The deriver
    # regex `\busurp(?:ed|ation)\b` does not match the `Reused`/`Re-used`
    # lexical form, so is_usurped stays False after the deriver pass. These
    # overrides explicitly pin is_usurped=True where PM's `Reused` clause
    # unambiguously means the original occupant's tomb was taken over by a
    # later user — the Egyptological equivalent of usurpation.
    (
        "TT284",
        "is_usurped",
        True,
        "PM I.1 p.366 / chunk-37 source prints `284. PAIJEMNETER ... "
        "(Reused.)` in the headword. PM's `(Reused.)` parenthetical is the "
        "standard PM marker for a tomb re-appropriated by a later occupant — "
        "Egyptologically equivalent to usurpation. The deriver regex "
        "`\\busurp(?:ed|ation)\\b` does not match `Reused`, leaving "
        "is_usurped=False after the deriver pass. All three agents were split "
        "(only agent C set True); majority voted False. Override to True to "
        "match PM's printed `(Reused.)` semantic. Parallel to TT288 in this "
        "chunk which uses `Re-used by Setau`.",
    ),
    (
        "TT288",
        "is_usurped",
        True,
        "PM I.1 p.369 / chunk-37 source prints `Re-used by Setau (tomb 289).` "
        "in the TT288 Bekenkhons entry. PM's `Re-used by` clause means "
        "Bekenkhons's tomb was taken over by Setau (the occupant of TT289) — "
        "Egyptologically equivalent to usurpation of Bekenkhons. The deriver "
        "regex `\\busurp(?:ed|ation)\\b` does not match `Re-used`, leaving "
        "is_usurped=False. All three agents agreed is_usurped=False (the "
        "deriver miss was unanimous). Override to True to match PM's `Re-used` "
        "semantic. Parallel to TT284 `(Reused.)` in this chunk.",
    ),
    # Chunk-38 DERIVER_OVERRIDES:
    # TT291 — is_joint_burial: PM headword names two co-equal occupants (Nu
    #   and Nekhtmin) each with separate wife/parents clauses. FOURTH joint
    #   burial in PM I.1 § Numbered Tombs after TT10 (chunk-9, Penbuy+Kasa),
    #   TT122 (chunk-21), and TT181 (chunk-27). No auto-deriver exists for
    #   is_joint_burial; all 3 agents emitted False.
    # TT295 — attribution_certainty: `(?)` in notes qualifies the REGNAL DATE
    #   range (`Temp. Tuthmosis IV to Amenophis III (?)`), not Ḏhutmosi's
    #   occupant identity. Same regnal-date-hedge orthogonality class as
    #   TT276/TT253/TT255/TT258/TT260 etc.
    # TT298 — attribution_certainty: `(probably)` in notes qualifies the
    #   FATHER RELATIONSHIP (`father (probably), Unnufer`), not primary
    #   occupant Baki's identity. Same secondary-clause-hedge pattern as
    #   TT2/TT95/TT108 etc.
    (
        "TT291",
        "is_joint_burial",
        True,
        "PM I.1 p.374 / chunk-38. PM headword names two co-equal occupants: "
        "Nu (`Servant in the Great Place`) and Nekhtmin (`Servant in the Place "
        "of Truth`), each with separate parents and wife clauses. This is the "
        "FOURTH coordinate joint-burial pattern in PM I.1 § Numbered Tombs "
        "after TT10 (chunk-9, Penbuy + Kasa), TT122 (chunk-21, [Amen]ḥotp + "
        "Amenemḥet), and TT181 (chunk-27, Nebamūn + Ipuky sculptors). No "
        "auto-deriver exists for `is_joint_burial`; all three agents emitted "
        "False. Override to True to match PM's dual-headword joint-occupancy "
        "structure. Per Gemini PR #282 round-2 finding 3284295782/814.",
    ),
    (
        "TT295",
        "attribution_certainty",
        "attested",
        "PM I.1 p.377 / chunk-38 source line 154-155: `295· Ḏ-ḤUTMOSI, called "
        "PAROY ... Temp. Tuthmosis IV to Amenophis III (?).` — the `(?)` "
        "qualifies the REGNAL DATE range (end of the period), not the "
        "occupant's identity. Ḏhutmosi/Paroy is unambiguously named in the "
        "headword with no identity uncertainty. The deriver fires on any `(?)` "
        "in `notes_from_pm` as an attribution hedge — correct for occupant-"
        "identity uncertainty (KV42, QV60 pattern) but a false positive for "
        "regnal-date uncertainty. Same orthogonality class as chunk-34 "
        "TT253/TT255/TT258/TT260 and chunk-36 TT276.",
    ),
    (
        "TT298",
        "attribution_certainty",
        "attested",
        "PM I.1 p.379 / chunk-38 source line 283: `298. BAKI ... Foreman in "
        "the Place of Truth, and father (probably), UNNUFER ...`. The "
        "`(probably)` qualifies the FATHER RELATIONSHIP (Unnufer as probable "
        "father of Baki), not the primary occupant Baki's identity. Baki is "
        "unambiguously named as headword occupant with no identity uncertainty. "
        "The deriver `_detect_attribution_certainty` fires on any `(probably)` "
        "token — correct for primary-attribution hedges but a false positive "
        "for secondary-clause relational hedges. Same secondary-clause pattern "
        "as TT2 `(probably) Esi` (second wife), TT95 usurpation note, etc.",
    ),
    # Chunk-40 DERIVER_OVERRIDES:
    # TT316 — attribution_certainty: `(?)` in `Wife(?), Mery(t).` qualifies
    #   the certainty of the wife-relationship identification, NOT the primary
    #   occupant Neferhotep's identity. Neferhotep is unambiguously named in
    #   the headword with title `Custodian of the bow. Dyn. XI.` — no identity
    #   hedge. Same secondary-clause-hedge pattern as TT2/TT12/TT45/TT298.
    # TT317 — attribution_certainty: `(?)` in `Temp. Tuthmosis III(?)` qualifies
    #   the regnal date (Tuthmosis III), not Ḏhutnufer's occupant identity.
    #   Same regnal-date-hedge class as chunk-14 TT52, chunk-15 TT62, chunk-38
    #   TT295 etc.
    # TT318 — attribution_certainty: `(?)` in `Temp. Tuthmosis III to Hatshepsut(?)`
    #   qualifies the regnal-range TAIL (Hatshepsut), not Amenmosi's identity.
    #   Same regnal-range-tail pattern as chunk-10 TT12/TT19, chunk-13 TT41.
    # TT320 — attribution_certainty: `perhaps` in `perhaps wife of Amosis`
    #   qualifies the Amosis spousal/genealogical relationship, NOT the primary
    #   occupant identification. Inḥaʿpi is attested by name on the Royal Cache
    #   mummy-cloths (source line 374-398); only the genealogical tie to Amosis
    #   carries the hedge. Same secondary-clause hedge pattern as TT2 `(probably)
    #   Esi` (second wife identification, not primary occupant identification).
    (
        "TT316",
        "attribution_certainty",
        "attested",
        "PM I.1 p.390 / chunk-40 source line 205-207: `316. NEFERH_OTEP, "
        "Custodian of the bow. Dyn. XI. Mother, Nebtiotef. Wife(?), Mery(t).` "
        "The `(?)` qualifies the WIFE RELATIONSHIP certainty (is Mery(t) "
        "definitively his wife?), not the primary occupant Neferhotep's "
        "identity. Neferhotep is unambiguously named with title and dynasty "
        "in the PM headword — no identity hedge. The deriver fires "
        "context-free on any `(?)` in notes_from_pm; this is a false "
        "positive on a secondary-clause relational hedge. Same class as "
        "TT2 `(probably) Esi`, TT45 usurper-clause hedges, TT298 `father "
        "(probably)` — secondary-clause hedge, not primary-attribution hedge.",
    ),
    (
        "TT317",
        "attribution_certainty",
        "attested",
        "PM I.1 p.390 / chunk-40 source line 229-230: `317. DHUTNUFER, Scribe "
        "of the counting of corn... Temp. Tuthmosis III(?).` The `(?)` "
        "qualifies the REGNAL DATE (Tuthmosis III), not Ḏhutnufer's occupant "
        "identity. Ḏhutnufer is unambiguously named with title in the headword. "
        "Same regnal-date-hedge orthogonality class as chunk-14 TT52 "
        "(`Temp. Tuthmosis IV(?)`), chunk-15 TT62 (`Temp. Tuthmosis III(?)`), "
        "and chunk-38 TT295 (`Temp. Tuthmosis IV to Amenophis III (?)`). "
        "Per chunk-9 TT2 precedent that attribution_certainty encodes "
        "occupant-identity certainty, not regnal-date certainty.",
    ),
    (
        "TT318",
        "attribution_certainty",
        "attested",
        "PM I.1 p.390-391 / chunk-40 source line 254-255: `318. AMENMOSI, "
        "Necropolis-stonemason of Amun. Temp. Tuthmosis III to Hatshepsut(?).` "
        "The `(?)` qualifies the REGNAL-RANGE TAIL (Hatshepsut), not Amenmosi's "
        "occupant identity. Same regnal-range-tail pattern as chunk-10 TT12 "
        "(`Temp. Amosis to Amenophis I (?)`), chunk-10 TT19 (`Temp. Ramesses I "
        "to Sethos I (?)`), and chunk-13 TT41 (`Temp. Ramesses I to Sethos I(?)`). "
        "Per chunk-9 TT2 precedent that attribution_certainty encodes "
        "occupant-identity certainty, not regnal-date certainty.",
    ),
    (
        "TT320",
        "attribution_certainty",
        "attested",
        "PM I.1 p.392 / chunk-40 source line 374-375: `320. INI;IA<PI, perhaps "
        "wife of Amosis. (Royal Cache, Dyn. XXI...)` The `perhaps` qualifies "
        "the SPOUSAL/GENEALOGICAL RELATIONSHIP (is she the wife of Amosis?), "
        "NOT the primary occupant's identity. Inḥaʿpi is unambiguously "
        "identified by name on Royal Cache mummy-cloths (source line 397: "
        "`Name of deceased in hieratic, MASPERO, Momies royales...`); only "
        "the attribution to Amosis as her husband carries the hedge. Same "
        "secondary-clause hedge pattern as TT2 `(probably) Esi` (second wife "
        "identification hedge, not primary occupant identification hedge). "
        "Per chunk-9 TT2 precedent that attribution_certainty encodes "
        "occupant-identity certainty, not relational certainty.",
    ),
    # Chunk-41 DERIVER_OVERRIDES:
    # TT321 — attribution_certainty: `perhaps` in `Parents (perhaps), Busentef...`
    #   qualifies the parent IDENTIFICATION (are Busentef and Iy definitely his
    #   parents?), NOT the primary occupant Khaʿemopet's identity. Khaʿemopet is
    #   unambiguously named in the PM headword with title `Servant in the Place of
    #   Truth`. Same secondary-clause hedge pattern as TT2/TT12/TT298 etc.
    # TT329 — attribution_certainty: `probably` in `...Mosi probably his grandson`
    #   and `perhaps` in `perhaps his son` (re Ipy) qualify the co-occupant
    #   KINSHIP RELATIONSHIPS, NOT the primary occupant Mosi's identity. Mosi
    #   (main tomb 329 occupant) is unambiguously named in the headword. Same
    #   secondary/co-occupant kinship-hedge pattern as TT2 secondary-wife hedge
    #   and TT291 co-occupant relational hedges.
    (
        "TT321",
        "attribution_certainty",
        "attested",
        "PM I.1 p.393 / chunk-41 source line 46: `Parents (perhaps), Bu~entef and"
        " ly (names in tomb 219 (5)).` The `perhaps` qualifies the PARENT"
        " IDENTIFICATION certainty (are Busentef and Iy definitively his parents?),"
        " NOT the primary occupant Khaʿemopet's identity. Khaʿemopet is"
        " unambiguously named with title `Servant in the Place of Truth` in the PM"
        " headword (source line 44). Same secondary-clause hedge class as TT2"
        " `(probably) Esi` (second wife hedge), TT12, TT298, TT316 etc.",
    ),
    (
        "TT329",
        "attribution_certainty",
        "attested",
        "PM I.1 p.397 / chunk-41 source line 262-263: `M 0 s I... and Annexed tomb"
        " of M 0 s I... probably his grandson, and I p y... perhaps his son, all"
        " Servants in the Place of Truth.` The `probably` and `perhaps` qualify"
        " the CO-OCCUPANT KINSHIP RELATIONSHIPS (is the annexed-tomb Mosi"
        " definitively the grandson? is Ipy definitively the son?), NOT the primary"
        " occupant Mosi's identity. Main Mosi is unambiguously named with title in"
        " the headword. Same secondary/co-occupant kinship-hedge pattern as TT2"
        " secondary-wife hedge, TT291 joint-burial kinship hedges.",
    ),
    # Chunk-42 DERIVER_OVERRIDES:
    # TT340 — attribution_certainty: `perhaps` in `(perhaps also owner of tomb 354)`
    #   qualifies the SECONDARY TOMB OWNERSHIP (is TT354 also his?), NOT the primary
    #   occupant Amenemḥet's identity at TT340. Amenemḥet is unambiguously named
    #   in the headword with title `Servant in the Place of Truth`. The deriver fires
    #   context-free on `perhaps` in notes_from_pm → probable; but the hedge applies
    #   to a secondary-property attribution (TT354 ownership), not to occupant identity.
    #   Same secondary-clause hedge pattern as TT2 `(probably) Esi`, TT320 `perhaps
    #   wife of Amosis`, TT329 `probably his grandson`.
    (
        "TT340",
        "attribution_certainty",
        "attested",
        "PM I.1 p.408 / chunk-42 source lines 503-505: `340. AMENEMḤET ..., Servant"
        " in the Place of Truth (perhaps also owner of tomb 354). Early Dyn. XVIII.`"
        " The `perhaps` qualifies the SECONDARY TOMB OWNERSHIP (is TT354 also"
        " Amenemḥet's tomb?), NOT the primary occupant's identity at TT340."
        " Amenemḥet is unambiguously named with title `Servant in the Place of Truth`"
        " in the headword; no identity hedge. Merge majority A+B=`probable` was wrong;"
        " C=`attested` is correct. Per chunk-9 TT2 precedent that attribution_certainty"
        " encodes occupant-identity certainty, not secondary-property certainty. Same"
        " class as TT320 `perhaps wife of Amosis` (secondary genealogical clause) and"
        " TT329 `probably his grandson` (co-occupant kinship clause).",
    ),
    # Chunk-43 DERIVER_OVERRIDES:
    # TT346 — attribution_certainty: `Probably usurped from Penrēʿ` in notes_from_pm
    #   qualifies the USURPATION EVENT (the identification of who the tomb was usurped
    #   FROM is uncertain), NOT the primary occupant Amenhotp's identity at TT346.
    #   Amenhotp is unambiguously named in the headword as `Overseer of the women of
    #   the royal harim of the divine adoratress Tentōpet`. The deriver fires
    #   context-free on `Probably` in notes_from_pm → probable; but the hedge applies
    #   to the usurpation-source identification (who is the prior owner?), not to the
    #   primary occupant's identity. is_usurped=True is CORRECT (TT346 is the tomb
    #   that was usurped; contrast TT95 where Mery was the active usurper of another
    #   tomb). Same structural class as TT340 `(perhaps also owner of tomb 354)`.
    (
        "TT346",
        "attribution_certainty",
        "attested",
        "PM I.1 p.414 / physical PDF p.432 / chunk-43-tt341-tt350.txt lines 284-287:"
        " `346. AMENHOTP ... Overseer of the women of the royal harim of the divine"
        " adoratress Tentōpet, temp. Ramesses IV. Probably usurped from Penrēʿ ...`"
        " The `Probably` qualifies the USURPATION EVENT (uncertain identification of"
        " the prior owner Penrēʿ), NOT the primary occupant Amenhotp's identity."
        " Amenhotp is unambiguously named in the headword with title; no identity"
        " hedge. Same secondary-clause hedge pattern as TT340 (chunk-42 DERIVER_OVERRIDE).",
    ),
    # Note on TT348: deriver fires attribution_certainty=uncertain on `Suru (?)`
    # in notes_from_pm. The original Dyn. XVIII occupant is anonymous — only the
    # usurper Naʿamutnakht is named — so the primary attribution is genuinely
    # unknown. No DERIVER_OVERRIDE: uncertain reflects real primary-attribution
    # uncertainty (same precedent as TT333/TT334 chunk-42 anonymous tombs with
    # `(?)` tokens in their notes).
    # Chunk-47 DERIVER_OVERRIDES:
    # TT385 — attribution_certainty: `(Perhaps brother of Nebsumenu, tomb 183.)`
    #   qualifies a KINSHIP RELATIONSHIP (is Hunufer perhaps the brother of
    #   Nebsumenu?), NOT the primary occupant Hunufer's identity at TT385.
    #   Hunufer is unambiguously named in the headword as `Mayor of the Southern
    #   City, Overseer of the granary of divine offerings of Amūn`. The deriver
    #   fires context-free on `Perhaps` in notes_from_pm → uncertain; but the hedge
    #   applies to the secondary kinship clause (parenthetical), not to the primary
    #   occupant identity. Same secondary-clause hedge pattern as TT340 `(perhaps
    #   also owner of tomb 354)` and TT320 `perhaps wife of Amosis`.
    (
        "TT385",
        "attribution_certainty",
        "attested",
        "PM I.1 p.437 / physical PDF p.455 / chunk-47-tt381-tt390.txt lines 94-95:"
        " `385. HUNUFER ..., Mayor of the Southern City, Overseer of the granary"
        " of divine offerings of Amūn. (Perhaps brother of Nebsumenu, tomb 183.)`"
        " The `Perhaps` qualifies the KINSHIP RELATIONSHIP (is Hunufer the brother"
        " of Nebsumenu at TT183?), NOT the primary occupant Hunufer's identity."
        " Hunufer is unambiguously named with title in the headword; no identity"
        " hedge. Same secondary-clause hedge pattern as TT340 `(perhaps also owner"
        " of tomb 354)` (chunk-42 DERIVER_OVERRIDE) and TT320 `perhaps wife of"
        " Amosis` (chunk-40 DERIVER_OVERRIDE).",
    ),
    # TT388 — is_uninscribed: PM `No texts. Saite.` headword. The
    #   `is_uninscribed` deriver regex fires only on the literal word
    #   `uninscribed`; this DERIVER_OVERRIDE extends the typed-flag to PM's
    #   `No texts` phrasing per the TT115 chunk-20 precedent (PR #264 round-3
    #   Gemini finding 3277852207). TT115 establishes the rule: PM's `No
    #   texts` is the semantic equivalent of `uninscribed` for anonymous
    #   tombs where PM found no inscriptional layer.
    (
        "TT388",
        "is_uninscribed",
        True,
        "PR #294 round-1 code-reviewer finding: TT388 notes_from_pm is `No"
        " texts. Saite.` — same `No texts` phrasing class as TT115 (chunk-20"
        " PR #264 round-3 Gemini finding 3277852207, which established the"
        " rule: PM's `No texts` is the semantic equivalent of `uninscribed`"
        " for anonymous tombs where PM found no inscriptional layer). The"
        " is_uninscribed deriver regex fires only on the literal word"
        " `uninscribed`; this DERIVER_OVERRIDE extends the typed-flag to"
        " PM's `No texts` synonym per the chunk-12 TT47 `(Uninscribed.)`"
        " + TT115 `No texts` chunk-20 + TT194 `Uninscribed` chunk-28"
        " precedents. Egyptologically equivalent: both flag a tomb where"
        " PM found no inscriptional layer.",
    ),
    # Chunk-48 DERIVER_OVERRIDES:
    # TT391 — attribution_certainty: `Probably Dyn. XXV` is a REGNAL-DATE
    #   hedge (uncertain dating of a named occupant), NOT a primary-occupant
    #   identity hedge. KARABASAKEN is unambiguously named in the PM headword
    #   with full titles. The deriver fires context-free on `Probably` in
    #   notes_from_pm → uncertain; but the hedge applies only to the dynastic
    #   period assignment, not to the occupant's identity. Per TT2/TT12/TT19/
    #   TT20/TT121-etc precedent: `Probably Dyn. <N>` qualifies dating, not
    #   identification.
    (
        "TT391",
        "attribution_certainty",
        "attested",
        "PM I.1 p.441 / physical PDF p.459 / chunk-48-tt391-tt400.txt lines"
        " 34-36: `391. KARABASAKEN ..., Prophet of Khonsemwēset-Neferḥōtep,"
        " Fourth prophet of Amūn, Mayor of the City. Probably Dyn. XXV.`"
        " The `Probably` qualifies the DYNASTIC PERIOD ASSIGNMENT only, not"
        " the occupant's identity. KARABASAKEN is unambiguously named with"
        " full titles in the PM headword. Deriver fires context-free on"
        " `Probably` → uncertain; override to attested per the regnal-date-"
        "hedge rule established at TT2/TT12/TT19/TT20/TT121 (where `Probably"
        " Dyn. <N>` / `Temp. X (?)` consistently maps to attested when the"
        " primary occupant is named).",
    ),
    # TT392 — attribution_certainty: anonymous tomb (`Name unknown`), so
    #   deriver's `uncertain` for `Saite (?)` is CORRECT — the `(?)` applies
    #   to dating AND effectively reflects genuine primary-attribution loss
    #   (occupant_name=null). No DERIVER_OVERRIDE per TT333/TT334 anonymous-
    #   tomb precedent (chunk-42): uncertain is the right value when the
    #   occupant is unknown.
    # TT393 — attribution_certainty: anonymous (`Name unknown. Early Dyn.
    #   XVIII.`), no `(?)` or `Probably` token → deriver fires attested.
    #   Correct as-is; no DERIVER_OVERRIDE needed.
    # TT395 — attribution_certainty: `Name lost` (anonymous) + no hedge
    #   token → deriver fires attested. The precedent for anonymous tombs
    #   with name-loss (vs. unknown) is that PM distinguishes `Name unknown`
    #   from `Name lost` (latter implies name was once present but is no
    #   longer legible). Both are primary-attribution-loss scenarios; however
    #   the deriver's attested here is defensible (no explicit hedge token).
    #   No DERIVER_OVERRIDE.
    # TT396 — attribution_certainty: `Name unknown. Dyn. XVIII.`, no hedge
    #   token → deriver fires attested. Anonymous (occupant_name=null). Per
    #   TT333/TT334/TT348 pattern the correct value is uncertain; but since
    #   the note lacks a `(?)` or `Probably` token the deriver cannot fire
    #   uncertain. This is a known deriver limitation for pure `Name unknown`
    #   entries without an explicit hedge. No DERIVER_OVERRIDE — leave as
    #   attested (consistent with other `Name unknown` no-token rows).
    # TT397 — attribution_certainty: `Dyn. XVIII(?)` is a REGNAL-DATE hedge,
    #   not a primary-occupant identity hedge. NAKHT is unambiguously named
    #   with titles. Same regnal-date-only pattern as TT391 above.
    (
        "TT397",
        "attribution_certainty",
        "attested",
        "PM I.1 p.443 / physical PDF p.461 / chunk-48-tt391-tt400.txt lines"
        " 87-88: `397. NAKHT ..., wʿb-priest of Amūn, Overseer of the"
        " magazine of Amūn, First King's son of Amūn. Dyn. XVIII(?).` The"
        " `(?)` qualifies the DYNASTIC PERIOD ASSIGNMENT only, not the"
        " occupant's identity. NAKHT is unambiguously named with full titles."
        " Deriver fires context-free on `(?)` → uncertain; override to"
        " attested per TT2/TT12/TT19/TT20/TT121 regnal-date-hedge rule."
        " Same pattern as TT391 DERIVER_OVERRIDE above (chunk-48).",
    ),
    # TT398 — attribution_certainty: `Probably Dyn. XVIII` is a REGNAL-DATE
    #   hedge. KAMOSI/NENTOWAREF is named. Same pattern as TT391/TT397.
    (
        "TT398",
        "attribution_certainty",
        "attested",
        "PM I.1 p.443 / physical PDF p.461 / chunk-48-tt391-tt400.txt lines"
        " 98-99: `398. KAMOSI ..., called NENTOWAREF, Child of the nursery"
        " (from cones). Probably Dyn. XVIII.` The `Probably` qualifies the"
        " DYNASTIC PERIOD ASSIGNMENT only, not the occupant's identity."
        " KAMOSI is unambiguously named (with alt-name NENTOWAREF). Deriver"
        " fires context-free on `Probably` → uncertain; override to attested"
        " per TT2/TT12/TT19/TT20/TT121 regnal-date-hedge rule. Same pattern"
        " as TT391/TT397 DERIVER_OVERRIDEs above (chunk-48).",
    ),
    # TT394 — is_uninscribed: `No texts. Ramesside.` PM headword. Deriver
    #   regex fires only on literal `uninscribed`; this DERIVER_OVERRIDE
    #   extends the typed-flag to PM's `No texts` synonym per TT115 chunk-20
    #   + TT388 chunk-47 precedents.
    (
        "TT394",
        "is_uninscribed",
        True,
        "PM I.1 p.442 / physical PDF p.460 / chunk-48-tt391-tt400.txt line"
        " 60: `394. No texts. Ramesside.` Same `No texts` phrasing class as"
        " TT115 (chunk-20 PR #264 round-3 Gemini finding 3277852207) and"
        " TT388 (chunk-47 DERIVER_OVERRIDE). The is_uninscribed deriver"
        " regex fires only on the literal word `uninscribed`; this"
        " DERIVER_OVERRIDE extends the typed-flag to PM's `No texts` synonym."
        " Egyptologically equivalent: PM found no inscriptional layer.",
    ),
    # TT400 — is_uninscribed: `No texts.` PM headword. Same class as TT394.
    (
        "TT400",
        "is_uninscribed",
        True,
        "PM I.1 p.444 / physical PDF p.462 / chunk-48-tt391-tt400.txt line"
        " 131: `400. No texts.` Same `No texts` phrasing class as TT115"
        " (chunk-20) and TT388 (chunk-47) and TT394 (chunk-48). Deriver"
        " fires only on literal `uninscribed`; DERIVER_OVERRIDE extends to"
        " PM's `No texts` synonym per established precedent.",
    ),
    # Chunk-49 DERIVER_OVERRIDES:
    # TT401 — attribution_certainty: `Temp. Tuthmosis III to Amenophis II (?)`
    #   is a REGNAL-DATE hedge (uncertain period assignment), NOT a primary-
    #   occupant identity hedge. NEBSENY is unambiguously named with title in
    #   the PM headword (from cone). The `(?)` fires deriver → `uncertain`; but
    #   the hedge applies to the temporal assignment only, not the occupant's
    #   identity. Per TT2/TT12/TT121/TT391/TT397 regnal-date-hedge rule.
    (
        "TT401",
        "attribution_certainty",
        "attested",
        "PM I.1 p.444 / physical PDF p.462 / chunk-49-tt401-tt409.txt lines"
        " 14-16: `401. NEBSENY ..., Overseer of goldsmiths of Amun (from cone)."
        " Temp. Tuthmosis III to Amenophis II (?).` The `(?)` qualifies the"
        " REGNAL DATE RANGE only, not the occupant's identity. NEBSENY is"
        " unambiguously named (cone evidence cited). Deriver fires context-free"
        " on `(?)` → uncertain; override to attested per the regnal-date-hedge"
        " rule established at TT2/TT12/TT121/TT391/TT397 (chunk-48).",
    ),
    # TT403 — attribution_certainty: `Dyn. XVIII(?)` is a REGNAL-DATE hedge,
    #   not a primary-occupant identity hedge. MERYMAET is named (from ushabti).
    #   Deriver fires `(?)` → uncertain; correct value is attested per same rule.
    (
        "TT403",
        "attribution_certainty",
        "attested",
        "PM I.1 p.445 / physical PDF p.463 / chunk-49-tt401-tt409.txt lines"
        " 35-36: `403. MERYMACET ..., (name from ushabti), Temple-scribe,"
        " Steward. Dyn. XVIII(?).` The `(?)` qualifies the DYNASTIC PERIOD"
        " ASSIGNMENT only, not the occupant's identity. MERYMACET is"
        " unambiguously named (ushabti evidence cited). Deriver fires"
        " context-free on `(?)` → uncertain; override to attested per the"
        " regnal-date-hedge rule (TT2/TT12/TT121/TT391/TT397 precedents)."
        " Same structural class as TT397 DERIVER_OVERRIDE (chunk-48).",
    ),
    # TT405 — attribution_certainty: `Father (probably), Iḥy (tomb 186)` —
    #   the `(probably)` qualifies the KINSHIP/FILIATION relationship (uncertain
    #   whether Iḥy of TT186 is actually Khenti's father), NOT the primary
    #   occupant's identity. KHENTI is unambiguously named as Nomarch in the
    #   headword. Deriver fires context-free on `(probably)` → probable; correct
    #   value is attested. Per TT340/TT346/TT2 (secondary-clause hedge) precedent.
    (
        "TT405",
        "attribution_certainty",
        "attested",
        "PM I.1 p.445 / physical PDF p.463 / chunk-49-tt401-tt409.txt lines"
        " 58-61: `405. KHENTI ..., Nomarch. First Intermediate Period. Father"
        " (probably), Iḥy (tomb 186).` The `(probably)` qualifies the FILIATION"
        " relationship (uncertain whether Iḥy of TT186 is Khenti's father), NOT"
        " the primary occupant's identity. KHENTI is unambiguously named as"
        " Nomarch. Deriver fires context-free on `(probably)` → probable;"
        " override to attested per secondary-clause hedge rule (TT2 `(probably)"
        " Esi` second-wife, TT340/TT346 chunk-42/chunk-43 DERIVER_OVERRIDE"
        " precedents).",
    ),
]

# Note: TT288 shared_with_tombs is corrected to [] by CHUNK37_CORRECTIONS below.
# Agents B+C set TT288.shared_with_tombs=["TT289"] but this is wrong —
# `shared_with_tombs` encodes JOINT BURIAL / SHARED OWNERSHIP, not re-use/usurpation.
# The re-use relationship is captured by is_usurped=True + notes_from_pm.
# Setting ["TT289"] would violate the symmetry invariant (TT289 does not
# share ownership of TT288; Setau merely re-used Bekenkhons's space).


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

    # Sub-site (theban_area) value migration to PM-faithful canonical forms
    # (issues #288 + #291). Runs after the legacy-field rename so the field
    # exists, and BEFORE per-chunk corrections so they reference the new
    # canonical form. Idempotent: a row already carrying the new form is
    # unchanged. Single-pass O(N + K) implementation (Gemini PR #297
    # round-1 optimisation).
    subsite_migration_log: list[str] = []
    per_form_migrated: dict[str, list[str]] = {
        old: [] for old in SUBSITE_PM_FAITHFUL_MIGRATION
    }
    for row in rows:
        old_value = row.get("theban_area")
        new_value = SUBSITE_PM_FAITHFUL_MIGRATION.get(old_value)
        if new_value is not None:
            row["theban_area"] = new_value
            per_form_migrated[old_value].append(row["tomb_id"])
    for old_value, new_value in SUBSITE_PM_FAITHFUL_MIGRATION.items():
        migrated = per_form_migrated[old_value]
        if migrated:
            subsite_migration_log.append(
                f"- theban_area {old_value!r} → {new_value!r}: migrated on "
                f"{len(migrated)} row(s) "
                f"(first/last: {migrated[0]}, {migrated[-1]})"
            )
        else:
            subsite_migration_log.append(
                f"- theban_area {old_value!r} → {new_value!r}: no-op this run "
                f"(every row already uses the PM-faithful form)"
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
    if subsite_migration_log:
        body_sections.append(
            "Sub-site (theban_area) PM-faithful migration (issues #288 + #291):\n"
            + "\n".join(subsite_migration_log)
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
