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
# Format: `{(tomb_id, field): {"value": ..., "rationale": "..."}}`. Empty for
# chunk 1 — egyptologist pass cleared with no row-specific P1 findings.
CHUNK1_CORRECTIONS: dict[tuple[str, str], dict[str, object]] = {}


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
        original_notes = row.get("notes_from_pm")
        fixed_notes = _apply_ocr_fixes(original_notes)
        if fixed_notes != original_notes:
            row["notes_from_pm"] = fixed_notes
            ocr_applied.append((tid, original_notes or ""))

        for (override_tid, field), spec in CHUNK1_CORRECTIONS.items():
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
