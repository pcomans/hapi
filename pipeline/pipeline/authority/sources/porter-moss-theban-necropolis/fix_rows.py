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
        "KV23/KV43/KV45/KV48 excavator clauses. The post-postprocessor "
        "rerun's three agents all dropped this `Excavated by ...` tail "
        "from notes_from_pm even though the postprocessor surfaced it "
        "cleanly. Restore via override (egyptologist-reviewer flagged "
        "as R1 in PR #140 review).",
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
        "KV43",
        "notes_from_pm",
        "Excavated by Davis.",
        "PM p.559 headword excavator clause for KV43 (Tuthmosis IV) — "
        "same systemic R1/R2 dropout: post-postprocessor agents lost "
        "the `Excavated by ...` tail. Egyptologist-reviewer flagged as "
        "R1/R2/R4 sibling.",
    ),
    (
        "KV45",
        "notes_from_pm",
        "Overseer of the Fields of Amun, Dyn. XVIII; re-used by Merenkhons, "
        "Doorkeeper of the House of Amun, Dyn. XXII (name from scarab). "
        "Excavated by Davis and Carter.",
        "PM p.562 headword tail `Excavated by Davis and Carter.` (chunk-3 "
        "lines 565-568) was dropped by post-postprocessor agents on "
        "rerun — same R1/R2 systemic loss. Restore the merged-value body "
        "and append the dropped tail. (The `;` separator after Dyn. XVIII "
        "is retained from the merged value; PM uses `,` but the "
        "egyptologist-reviewer marked this as a mild paraphrase.)",
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
        "Egyptologist-reviewer P1 finding on PR #100 (reviewer-notes-chunk7.md "
        "line 20): PM p.604 prints `wife of King Ḍḥuti` with both underdot-D "
        "and underdot-H, but the text-layer OCR rendered `Ql_J.uti` as "
        "`Djhuti` (no diacritics) and the agents carried that through. "
        "Restore the PM-verbatim diacritics per the `notes_from_pm` "
        "verbatim-preserve policy. tomb_id renamed to "
        "`DAN-MentuhotpIWifeOfDjhuti` via CHUNK7_RENAMES for descriptor "
        "consistency with the PM-faithful spelling convention.",
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
    ("DAN-AntefSehertaui", "occupant_name", "Antef",
     "Strip parenthetical prenomen `(Sehertaui)`; alt_names retains it. "
     "R6 in egyptologist-reviewer PR #140 review."),
    ("DAN-AntefWahankh", "occupant_name", "Antef",
     "Strip parenthetical prenomen `(Wahankh)`; alt_names retains it."),
    ("DAN-AntefNubkheperre", "occupant_name", "Antef",
     "Strip parenthetical prenomen `(Nubkheperreʿ)`; alt_names retains it."),
    ("DAN-AntefSekhemreHeruhirmaet", "occupant_name", "Antef",
     "Strip parenthetical prenomen `(Sekhemreʿ-Heruhirmaʿet)`; alt_names "
     "retains it."),
    ("DAN-AntefSekhemreWepmaet", "occupant_name", "Antef",
     "Strip parenthetical prenomen `(Sekhemreʿ-Wepmaʿet)`; alt_names "
     "retains it."),
    ("DAN-KamosiWazkheperre", "occupant_name", "Kamosi",
     "Strip parenthetical prenomen `(Wazkheperreʿ)`; alt_names retains it."),
    ("DAN-SebkemsafSekhemreShedtaui", "occupant_name", "Sebkemsaf II",
     "Strip parenthetical prenomen `(Sekhemreʿ-Shedtaui)`; alt_names "
     "retains it."),
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
