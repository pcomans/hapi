"""Apply LLM-reviewer-identified corrections to reconciled.jsonl.

Run AFTER merge.py. Mirrors Kitchen's pattern — idempotent re-runs,
append-only LLM-APPLIED OVERRIDES section in merge-disagreements.txt,
every override recorded with rationale.

For this chunk, the egyptologist-reviewer Claude Code subagent flagged
a single verbatim-prose OCR drift on `Tiaa A`'s `notes`: Gemini's OCR
dropped an article and introduced a stray colon (`"including: number
of usurpations"` vs the PDF's `"including a number of usurpations"`).
Since `notes` is a verbatim-quotation field, the correction is applied
rather than left in the extract.

No deterministic recomputation is needed for this source (the schema
has no interval-overlap or cross-row fields).

Run:
    cd pipeline && uv run python pipeline/authority/sources/dodson-hilton-queens/fix_rows.py

Idempotent: re-running replaces (not duplicates) the LLM-APPLIED OVERRIDES
section in merge-disagreements.txt.
"""

from __future__ import annotations

import json
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
RECONCILED = SOURCE_DIR / "reconciled.jsonl"
DIFF = SOURCE_DIR / "merge-disagreements.txt"


# Spot corrections identified by the egyptologist-reviewer subagent pass.
# Each entry: (dh_id, field, new_value, rationale).
SPOT_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "Tiaa A",
        "notes",
        "Wife of Amenhotep II and mother of Thutmose IV. A number of "
        "monuments were created for her by the latter at Giza, Thebes "
        "and the Fayoum, including a number of usurpations of material "
        "belonging to Meryetre-Hatshepsut. She was buried in tomb KV32, "
        "where many fragments of her funerary equipment have been found; "
        "some material was washed by floodwater into the adjacent tomb "
        "KV47, where it was for a long time thought to belong to a "
        "like-named mother of Siptah.",
        'Gemini OCR dropped the article "a" in "including a number of '
        'usurpations" and left a stray colon after "including". The PDF '
        "(p. 140 col 2, Tiaa A entry) reads with the article; `notes` "
        "is a verbatim-quotation field so the reviewer's correction is "
        "applied rather than preserving the OCR artifact.",
    ),
]


def main() -> None:
    rows = [json.loads(line) for line in RECONCILED.read_text().splitlines() if line.strip()]

    override_log: list[str] = []
    for dh_id, field, new_val, rationale in SPOT_CORRECTIONS:
        row = next((r for r in rows if r["dh_id"] == dh_id), None)
        if row is None:
            raise KeyError(f"No row with dh_id {dh_id!r}")
        old_val = row.get(field)
        if old_val == new_val:
            continue
        override_log.append(
            f"- {dh_id}: {field} corrected ({rationale})\n"
            f"    was: {json.dumps(old_val, ensure_ascii=False)}\n"
            f"    now: {json.dumps(new_val, ensure_ascii=False)}"
        )
        row[field] = new_val

    RECONCILED.write_text(
        "\n".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows
        )
        + "\n"
    )

    existing_diff = DIFF.read_text()
    marker = "LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED"
    if marker in existing_diff:
        head, _, _ = existing_diff.partition(f"\n\n{marker}")
        existing_diff = head
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

    print(f"Applied {len(override_log)} override(s).")
    print(f"Updated {RECONCILED.relative_to(RECONCILED.parents[4])}")
    print(f"Updated {DIFF.relative_to(DIFF.parents[4])}")


if __name__ == "__main__":
    main()
