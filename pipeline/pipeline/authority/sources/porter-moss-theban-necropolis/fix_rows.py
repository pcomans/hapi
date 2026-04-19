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
# rule-based prompt — no reviewer-identified corrections needed. The empty
# list is retained (rather than dropped) so `test_all_corrections_includes_
# every_chunk_list` continues to enforce ALL_CORRECTIONS aggregation.
CHUNK5_CORRECTIONS: list[tuple[str, str, object, str]] = []


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
]

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


def main() -> None:
    rows = [json.loads(line) for line in RECONCILED.read_text().splitlines() if line.strip()]
    by_id = {r["tomb_id"]: r for r in rows}

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
    body = (
        "\n".join(override_log)
        if override_log
        else "- No overrides applied. The reviewer pass produced no "
        "actionable corrections on `reconciled.jsonl` for this chunk."
    )
    appended = (
        f"{existing_diff.rstrip()}\n\n"
        f"{marker}\n"
        + "=" * len(marker) + "\n"
        "Corrections applied by fix_rows.py AFTER the 3-subagent majority-vote\n"
        "merge. Source of each correction: the egyptologist-reviewer Claude\n"
        "Code subagent pass against the source PDF. No human scholar has\n"
        "signed off on this extract yet — per ADR-017 step 6, the extract is\n"
        "provisional until that happens.\n\n"
        f"{body}\n"
    )
    DIFF.write_text(appended)

    print(f"Applied {applied_count} override(s) this run ({len(override_log)} total in log).")
    print(f"Updated {RECONCILED.relative_to(RECONCILED.parents[4])}")
    print(f"Updated {DIFF.relative_to(DIFF.parents[4])}")


if __name__ == "__main__":
    main()
