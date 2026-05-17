"""Apply post-merge corrections to reconciled.jsonl.

Runs AFTER merge.py. Carries two classes of fix:

1. **Source-wide deterministic OCR substitutions** that should ideally happen
   pre-extraction at the `postprocess.py` layer but were not present when the
   chunk's raw text-layer was read. Currently: PM's Reisner-Roman-numeral
   tokens `G II` and `G III` render in the Griffith Institute text layer as
   Arabic `G 11` and `G 111` (the same OCR engine renders `G I` correctly,
   confirmed by the egyptologist-reviewer pass — chunk 1 PM III.1 review,
   2026-05-15). These appear in `notes_from_pm` cells where the source-faithful
   form is the Roman. Deterministic substring fix, longest-match first.

2. **Per-chunk reviewer-cited corrections** (`<CHUNK>_CORRECTIONS` dicts) for
   row-specific egyptologist findings beyond the source-wide substring rules.
   Currently empty for chunk 1 (clean review pass, 0 P1, 1 P2 already handled
   by the substring rule, 2 P3 nits).

Invocation:
    cd pipeline && uv run python pipeline/authority/sources/porter-moss-memphis/fix_rows.py

Idempotent: re-running on already-fixed reconciled.jsonl is a no-op (each
substitution's right-hand side does not contain the left-hand side).
"""

from __future__ import annotations

import json
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
RECONCILED = SOURCE_DIR / "reconciled.jsonl"
DIFF = SOURCE_DIR / "merge-disagreements.txt"

# Marker that delimits the auto-appended audit-trail section in
# `merge-disagreements.txt`. Re-running fix_rows.py strips any existing
# section that begins at this marker before re-appending, so the file
# remains byte-identical across consecutive runs (constitutional rule 2
# + playbook idempotence guard).
_AUDIT_MARKER = "\nLLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED\n"


# Source-wide OCR-drift fixes applied to `notes_from_pm`.
# Ordered LONGEST-MATCH FIRST so that `G 111` is rewritten before any
# overlapping `G 11` rule could fire on the same string.
_NOTES_OCR_FIXES: list[tuple[str, str]] = [
    ("Reisner, G 111-", "Reisner, G III-"),  # subsidiary-pyramid form first
    ("Reisner, G 111;", "Reisner, G III;"),
    ("Reisner, G 111.", "Reisner, G III."),
    ("Reisner, G 111", "Reisner, G III"),
    ("Reisner, G 11-", "Reisner, G II-"),
    ("Reisner, G 11;", "Reisner, G II;"),
    ("Reisner, G 11.", "Reisner, G II."),
    ("Reisner, G 11", "Reisner, G II"),
]


# Per-chunk reviewer-cited corrections.
# Format: `{(tomb_id, field): {"value": ..., "rationale": "..."}}`.
# `CHUNK<N>_CORRECTIONS` is per-chunk; a dict is empty when the
# egyptologist pass clears that chunk with no row-specific P1 findings
# (chunk 1 case).
CHUNK1_CORRECTIONS: dict[tuple[str, str], dict[str, object]] = {}

# Chunk-2 corrections from the egyptologist-reviewer pass on the printed PM
# III.1 source (2026-05-15). The pypdf text-layer renders `D` and `O`
# ambiguously in PM's all-caps headwords; pypdf chose `O` for the `D` in
# `IDU`. Two corrections needed:
#   1. `occupant_name`: "Iou" → "Idu"
#   2. `notes_from_pm`: rewrite the verbatim "IOU" token to "IDU" so the
#      stored headword form matches what PM prints (the OCR misread is
#      not PM-faithful).
CHUNK2_CORRECTIONS: dict[tuple[str, str], dict[str, object]] = {
    ("G7102", "occupant_name"): {
        "value": "Idu",
        "rationale": (
            "Egyptologist-reviewer pass against PM III.1 2nd ed. 1974 "
            "printed p.185: PM's all-caps headword unambiguously reads "
            "`G 7102. IDU`. pypdf text-layer misread D→O producing `IOU`, "
            "which all three extraction agents inherited and majority-voted. "
            "Corroborated by the already-correctly-OCR'd footnote on "
            "printed p.184 (`Textual evidence also permits Meryrēᶜnūfer "
            "Kar to be son of Idu (tomb G 7102)`) and by Simpson, *Mastabas "
            "of the Western Cemetery I* (1980)."
        ),
    },
}

# Chunk-3 corrections from the egyptologist-reviewer pass (PR #220 / PM
# III.1 printed pp.288-292). The Saite joint-burial rows (LG 83, LG 97)
# need typed roles for their co-occupants — PM explicitly types Queen
# Nekhtubasterau (LG 83) and pairs Harsiesi + Harwoz as both wnrw-priests
# (LG 97). Currently `co_occupants` is `list[str]` (names only) and the
# co-occupant's role is lost. Solution: a parallel `co_occupant_roles`
# field. Order-coupled with `co_occupants`. The schema addition matters
# for downstream Phase-A queen-of-Amasis queries, which must surface
# LG 83 as a Queen tomb even though its primary occupant is a Commander.
CHUNK3_CORRECTIONS: dict[tuple[str, str], dict[str, object]] = {
    ("LG83", "co_occupant_roles"): {
        "value": ["Queen"],
        "rationale": (
            "Egyptologist-reviewer pass against PM III.1 2nd ed. 1974 "
            "printed p.289: PM's joint-burial headword reads `LG 83. "
            "aAHMOSI Commander of the army, and his mother Queen "
            "NEKHTUBASTERAU (wife of Amasis). Dyn. XXVI.`. The secondary "
            "occupant carries an explicit `Queen <NAME>` token AND a "
            "`wife of <king>` parenthetical — both attributes that PM "
            "types as primary-source facts about her. Without a parallel "
            "`co_occupant_roles` list, this typed role is lost into "
            "prose, and Phase-A queries for 'queens of Amasis' will not "
            "surface LG 83. Adds `co_occupant_roles: [\"Queen\"]` so "
            "downstream enrichment can route Nekhtubasterau as a Queen "
            "without losing the joint-burial-with-son-ʿAhmosi context."
        ),
    },
    ("LG97", "co_occupant_roles"): {
        "value": ["Official"],
        "rationale": (
            "Egyptologist-reviewer pass against PM III.1 2nd ed. 1974 "
            "printed p.291: PM's joint-burial headword reads `LG 97. "
            "HARSIESI and HARWOZ both wnrw-priests. Dyn. XXVI.`. The "
            "`both <shared title>` phrasing types BOTH occupants with the "
            "same priestly role; the secondary (Harwoz) inherits the same "
            "`Official` role as the primary (Harsiesi). Parallel "
            "`co_occupant_roles` array preserves the symmetric typing."
        ),
    },
    ("LG97", "notes_from_pm"): {
        "value": "LG 97. HARSIESI and HARWOZ both wnrw-priests. Dyn. XXVI. Mother, Tentamūn.",
        "rationale": (
            "Egyptologist-reviewer pass F5 + Gemini PR #220 round-1 inline "
            "comment id=3253276720 (both reviewers converged on the same "
            "finding). PM III.1 2nd ed. 1974 printed p.291 prints the "
            "parental relation as `Mother, Tentamūn.` (with a trailing "
            "period and a macron over the `u`). Two issues with the "
            "majority-voted notes value: (1) pypdf rendered the macron-u "
            "as the digraph `ii`, producing `Tentamiin` (analogous OCR "
            "drift to chunks 1-2 raised-ayin `a` / `c` patterns); (2) "
            "the trailing period was dropped because pypdf concatenated "
            "the next sub-heading `Names and titles from ushabtis.` "
            "onto the same line as `Mother, Tentamūn`, and the agents "
            "(correctly) stopped extraction at the sub-heading boundary "
            "but lost the headword's terminal period. Restoration: "
            "`Tentamiin` → `Tentamūn` + trailing period."
        ),
    },
}

# Chunk-4 corrections from the egyptologist-reviewer pass (PR #222 / PM
# III.2 Saqqâra Dyn V/VI pyramids).
CHUNK4_CORRECTIONS: dict[tuple[str, str], dict[str, object]] = {
    ("SAQ-MerenreI", "occupant_name"): {
        "value": "Merenreʿ I",
        "rationale": (
            "Egyptologist-reviewer pass F1 against PM III.2 2nd ed. 1978/1981 "
            "printed p.425 (physical p.65): PM prints `MERENRĒʿ I` (macron-ē + "
            "raised-ayin). pypdf rendered the macron-ē-plus-raised-ayin glyph "
            "cluster as the 2-character sequence `£c`, where `£` represents "
            "the underlying `Ē` (or `É` with combining marks) and `c` "
            "represents the raised-ayin. The chunk-4 prompt's rule "
            "`£c → ʿ` correctly converts the raised-ayin glyph but DROPS the "
            "underlying vowel — producing the non-standard form `Merenrʿ I`. "
            "The conventional Egyptological transcription is `Merenreʿ I` "
            "(mer-en-Reʿ, \"Beloved of Re\") with the `e` vowel of the `Re` "
            "element preserved. Parallel to chunk-1's `Menkaureʿ` (PM "
            "`MENKAUREa` → drop the raised-`a` glyph, keep the `e` vowel that "
            "precedes it). Restoration: `Merenrʿ I` → `Merenreʿ I`. Egyptologist "
            "F1 finding."
        ),
    },
    ("SAQ-IputII", "source_citation"): {
        "value": {"page": 432, "edition": "PM III.2 2nd ed. 1978/1981", "section": "I"},
        "rationale": (
            "Gemini PR #222 round-1 caught a 2/1 majority that happened to be "
            "wrong: agents A and C reported `page: 431`, agent B reported "
            "`page: 432`. The IPUT II headword `PYRAMID-ENCLOSURE OF IPUT [II]¹` "
            "appears on physical p.72 of the chunk file. The PM III.2 printed-vs-"
            "physical offset is `printed = physical + 360`, so physical p.72 = "
            "printed p.432. Agent B's reported page (432) is correct; A and C "
            "are off by one (likely confused by the prior right-page running "
            "header `Pyramid-complex of Pepy II 431` on physical p.71). Override "
            "the majority with the cited correct page. The `SAQ-IputII|"
            "notes_from_pm` tie-break-overrides.json rationale already states "
            "`printed p.432 (physical p.72)`; this fix aligns source_citation "
            "with the documented page reference."
        ),
    },
}

# Chunk-5 corrections (PM III.2 § I.A–E Saqqâra front-half pyramid
# complexes: Teti+Iput-I+Khuit, Userkaf, Neterikhet/Zoser, Sekhemkhet,
# Great Enclosure). Findings from the printed-source egyptologist-reviewer
# pass against PM III.2 pp.393–417.
CHUNK5_CORRECTIONS: dict[tuple[str, str], dict[str, object]] = {
    ("SAQ-IputI", "occupant_name"): {
        "value": "Iput",
        "rationale": (
            "Egyptologist-reviewer printed-source pass against PM III.2 "
            "p.396: PM prints `PYRAMID-ENCLOSURE OF IPUT¹` (bare IPUT with "
            "footnote anchor `¹` keyed to `1 King's wife (of Teti), "
            "King's mother (of Pepy I).` at the bottom of the same page). "
            "The agents' converged extraction `Iput I` interpolates the "
            "regnal numeral `I` from Egyptological convention — but PM "
            "itself does NOT print `[I]` on this heading. Contrast with "
            "chunk-4's SAQ-IputII row where PM explicitly prints `IPUT "
            "[II]¹` with the bracket-regnal. The chunk-4 [II] bracket is "
            "PM's editorial regnal disambiguation; chunk-5's bare IPUT "
            "(without bracket) is PM's faithful headword form. Per rule 1 "
            "(work like a scholar — every fact traces to a documented "
            "source), `occupant_name` must match PM's printed form. The "
            "museum-side disambiguating form `Iput I` is preserved in "
            "`occupant_alt_names` for Phase-A matching coverage. "
            "Restoration: `Iput I` → `Iput`."
        ),
    },
    ("SAQ-IputI", "occupant_alt_names"): {
        "value": ["Iput I"],
        "rationale": (
            "Companion fix to the SAQ-IputI `occupant_name` correction. "
            "`Iput I` is the museum-conventional disambiguating form "
            "(distinguishing Teti's queen-consort from Pepy II's queen "
            "Iput II covered in chunk 4). Phase-A name-authority matching "
            "needs this alias because museum records will say `Iput I` "
            "even though PM's headword is bare `IPUT`. Egyptologist "
            "F1 finding."
        ),
    },
    ("SAQ-IputI", "notes_from_pm"): {
        "value": (
            "PYRAMID-ENCLOSURE OF IPUT. Dyn. VI. PYRAMID. "
            "¹ [King's daughter of his] body, King's wife (of Teti), "
            "King's mother (of Pepy I)."
        ),
        "rationale": (
            "Egyptologist-reviewer second-pass printed-source verification "
            "against PM III.2 p.396: the full footnote text is "
            "`¹ [King's daughter of his] body, King's wife (of Teti), "
            "King's mother (of Pepy I).` — three titles, with the first "
            "(`King's daughter of his body`, restoring the lost original "
            "title `sꜣt-nsw-n(t)-ẖt.f`) in editorial brackets per PM's "
            "convention for restored text. First-pass review F3 fix "
            "captured only the last two titles (`King's wife (of Teti), "
            "King's mother (of Pepy I).`) — a rule-1 fidelity loss that "
            "would lead Phase-A consumers to wrongly conclude PM prints "
            "only two titles. Second-pass fix restores PM's bracketed "
            "first clause. Verbatim form (no `(Footnote: ...)` editorial "
            "wrapper) per the README's `notes_from_pm` convention; the "
            "`¹` superscript marker is PM's own footnote-anchor character "
            "and stays as PM's contextual signal that this clause is "
            "footnote prose rather than the headline-block continuation."
        ),
    },
    ("SAQ-Khuit", "notes_from_pm"): {
        "value": (
            "PYRAMID-ENCLOSURE OF KHUIT. Dyn. VI. "
            "¹ King's wife (of Teti)."
        ),
        "rationale": (
            "Egyptologist-reviewer printed-source pass against PM III.2 "
            "p.397: PM prints `PYRAMID-ENCLOSURE OF KHUIT¹` with footnote "
            "anchor `¹` keyed to `¹ King's wife (of Teti).` at the bottom "
            "of the same page. Parallel to the SAQ-IputI fix above. The "
            "footnote text supports the `occupant_role: \"Queen\"` "
            "classification and Teti's spouse identification — both "
            "Phase-A-relevant facts that need a documented PM trace. "
            "Restoration: append PM's verbatim footnote text (with PM's "
            "own `¹` anchor) to the headword condensation, no "
            "editorial `(Footnote: ...)` wrapper. Egyptologist F3 finding."
        ),
    },
    ("SAQ-Neterikhet", "occupant_alt_names"): {
        "value": ["Zoser", "Djoser"],
        "rationale": (
            "Egyptologist-reviewer printed-source pass against PM III.2 "
            "p.399: PM prints `STEP PYRAMID ENCLOSURE OF NETERIKHET "
            "(Zoser)` — the parenthetical `Zoser` is PM's printed alias "
            "(post-OK reception of the king's birth-name). Modern museum "
            "records (Met, Brooklyn, Harvard, BM) overwhelmingly use the "
            "spelling `Djoser` rather than PM's `Zoser`. Adding `Djoser` "
            "as a second alt_name gives Phase-A name-authority matching "
            "the museum-conventional spelling without altering PM's "
            "printed primary form. Egyptologist F4 finding (P2)."
        ),
    },
}

# Registry of all per-chunk correction dicts. New chunks add their
# `CHUNK<N>_CORRECTIONS` constant to THIS list (single source of truth);
# `main`'s correction loop iterates this list rather than hardcoding the
# tuple inline. Gemini PR #219 round-1 medium-priority finding.
_ALL_CHUNK_CORRECTIONS: list[dict[tuple[str, str], dict[str, object]]] = [
    CHUNK1_CORRECTIONS,
    CHUNK2_CORRECTIONS,
    CHUNK3_CORRECTIONS,
    CHUNK4_CORRECTIONS,
    CHUNK5_CORRECTIONS,
]

# Schema-uniformity backfill: every reconciled row carries
# `co_occupant_roles: list[str]` (default `[]` for single-occupant rows
# and rows whose co-occupants are not typed by PM). Rows in
# `CHUNK<N>_CORRECTIONS` that set this key override the default.
def _ensure_co_occupant_roles_default(row: dict) -> bool:
    """Backfill `co_occupant_roles: []` on rows that don't already have
    the field. Idempotent — re-running on a row that already has the
    field is a no-op. Returns True if the row was modified.
    """
    if "co_occupant_roles" not in row:
        row["co_occupant_roles"] = []
        return True
    return False


def _apply_chunk2_notes_ocr_fixes(notes: str | None, tid: str) -> str | None:
    """Per-row OCR fixes inside `notes_from_pm` that are scoped to a single
    chunk-2 row. Separate from the source-wide `_NOTES_OCR_FIXES` table
    because these substitutions are narrow enough that the global table
    would carry risk of misfiring on a future chunk.

    Currently: G7102 — rewrite the all-caps `IOU` (pypdf D→O misread) to
    `IDU` so the stored verbatim notes match what PM printed. The
    `notes_from_pm` stored form was `"IOU Tenant of the Pyramid of Pepy
    I, ..."`; rewrite the leading token only.
    """
    if notes is None:
        return None
    if tid == "G7102" and notes.startswith("IOU "):
        return "IDU " + notes[len("IOU "):]
    return notes


def _apply_ocr_fixes(notes: str | None) -> str | None:
    if notes is None:
        return None
    out = notes
    for src, dst in _NOTES_OCR_FIXES:
        out = out.replace(src, dst)
    return out


def main() -> None:
    rows = [json.loads(line) for line in RECONCILED.read_text(encoding="utf-8").splitlines() if line.strip()]

    ocr_applied: list[tuple[str, str]] = []
    overrides_applied: list[tuple[str, str, object, object]] = []

    for row in rows:
        tid = row["tomb_id"]
        # Schema-uniformity backfill: ensure every row carries
        # `co_occupant_roles: []` before the per-chunk correction loop runs
        # (so that `CHUNK3_CORRECTIONS`'s `co_occupant_roles` overrides
        # treat the default as `[]`, not as absent).
        _ensure_co_occupant_roles_default(row)

        original_notes = row.get("notes_from_pm")
        fixed_notes = _apply_ocr_fixes(original_notes)
        fixed_notes = _apply_chunk2_notes_ocr_fixes(fixed_notes, tid)
        if fixed_notes != original_notes:
            row["notes_from_pm"] = fixed_notes
            ocr_applied.append((tid, original_notes or ""))

        for corrections in _ALL_CHUNK_CORRECTIONS:
            for (override_tid, field), spec in corrections.items():
                if override_tid == tid:
                    previous = row.get(field)
                    # Skip no-op corrections (value already matches) so the audit
                    # trail in `merge-disagreements.txt` does not accrue
                    # misleading `X → X` entries on subsequent runs.
                    if previous == spec["value"]:
                        continue
                    row[field] = spec["value"]
                    overrides_applied.append((tid, field, previous, spec["value"]))

    RECONCILED.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows) + "\n",
        encoding="utf-8",
    )

    if ocr_applied or overrides_applied:
        existing = DIFF.read_text(encoding="utf-8") if DIFF.exists() else ""
        # Strip any prior auto-appended audit-trail section so the merge
        # diff stays byte-identical across consecutive `fix_rows.py` runs.
        marker_idx = existing.find(_AUDIT_MARKER)
        if marker_idx >= 0:
            existing = existing[:marker_idx]
        annotations: list[str] = []
        annotations.append(_AUDIT_MARKER)
        annotations.append("============================================\n")
        if ocr_applied:
            annotations.append("\nOCR-drift fixes (Roman-numeral restore in notes_from_pm):\n")
            for tid, original in ocr_applied:
                annotations.append(f"  {tid}: {original}\n")
        if overrides_applied:
            annotations.append("\nReviewer-cited row corrections:\n")
            for tid, field, before, after in overrides_applied:
                annotations.append(
                    f"  {tid}.{field}: {json.dumps(before, ensure_ascii=False)} "
                    f"→ {json.dumps(after, ensure_ascii=False)}\n"
                )
        DIFF.write_text(existing + "".join(annotations), encoding="utf-8")

    print(f"Rows: {len(rows)}")
    print(f"OCR-drift fixes applied: {len(ocr_applied)}")
    print(f"Reviewer corrections applied: {len(overrides_applied)}")


if __name__ == "__main__":
    main()
