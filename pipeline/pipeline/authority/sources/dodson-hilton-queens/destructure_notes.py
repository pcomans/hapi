"""Terminal pipeline stage: drop the verbatim `notes` prose from reconciled.jsonl.

Pipeline order for this source is:

    transcribe (Gemini OCR) -> 3-agent extraction -> merge.py
        -> egyptologist-reviewer pass -> fix_rows.py -> **destructure_notes.py**

Why this stage exists
---------------------
The `notes` field reproduced Dodson & Hilton's *Brief Lives* paragraphs (30-80
words/entry) **verbatim**. Names, kinships, royal titles, dynasty numbers and
monument references are uncopyrightable facts and live in their own structured
fields (`name`, `alt_names`, `father_name`, `mother_name`, `spouse_names`,
`children_names`, `roles`, `dynasty`, ...). D&H's *specific phrasing* of the
narrative around those facts is their protectable expression. The source README
("Rights" section) always flagged that, before any public release, the `notes`
field must be "summarised, dropped, or re-sourced".

This stage **drops** it. A harvest pass (committed in the PR that introduced this
file) verified that every matchable fact already lives in a structured field —
0 name-variant gaps and 0 kinship gaps across all 549 rows — so removing the
prose loses no matching data. The only matching-flavoured prose was D&H's
intra-source disambiguator cross-references ("X identical with Y") between rows
that both already exist as structured entries; several are deliberately
ambiguous and are left as Phase-A / human-review items rather than auto-promoted
(constitutional rules 2 & 6).

Properties
----------
- **Deterministic & idempotent.** Re-running on an already-destructured file is a
  no-op. It is a pure function of the rows: it can run as the documented terminal
  stage after `fix_rows.py`, or be applied directly to the committed
  reconciled.jsonl (raw extraction inputs are not needed).
- **Write format matches `fix_rows.py`** byte-for-byte: one
  `json.dumps(..., ensure_ascii=False, sort_keys=True)` object per line, trailing
  newline. Running this stage on a file that still carries `notes` produces a diff
  that removes only the `notes` key.
"""

from __future__ import annotations

import json
from pathlib import Path

SOURCE_DIR = Path(__file__).resolve().parent
RECONCILED = SOURCE_DIR / "reconciled.jsonl"
DISAGREEMENTS = SOURCE_DIR / "merge-disagreements.txt"

# Verbatim-prose fields stripped before publication. `notes` is the only one this
# source carries; the list makes the intent explicit and future-proof.
PROSE_FIELDS = ("notes",)

# Marker separating the merge-time agent disagreements (which include verbatim
# `notes:` lines) from the fix_rows.py override section. Kept in sync with
# fix_rows.py and the audit-trail tests.
_OVERRIDE_MARKER = "LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED"


def destructure_row(row: dict) -> dict:
    """Return a copy of `row` with verbatim-prose fields removed."""
    return {k: v for k, v in row.items() if k not in PROSE_FIELDS}


def destructure(rows: list[dict]) -> list[dict]:
    """Drop verbatim-prose fields from every row. Pure; idempotent."""
    return [destructure_row(r) for r in rows]


def sanitize_disagreements(text: str) -> str:
    """Strip verbatim-prose field lines from the merge-disagreements audit log.

    The pre-marker portion records the 3 agents' per-field disagreements as
    `  <field>: a="..." | b="..." -> chose "..."` lines — for `notes` those
    carry full D&H paragraphs verbatim. Drop every `  <field>:` line for a
    PROSE_FIELDS field, plus any row header left with no remaining field lines.
    The override section (post-marker) is regenerated notes-free by fix_rows.py,
    so it is passed through unchanged. Pure; idempotent.
    """
    pre, marker, post = text.partition(_OVERRIDE_MARKER)
    drop_prefixes = tuple(f"  {f}:" for f in PROSE_FIELDS)
    out: list[str] = []
    header: str | None = None
    header_has_fields = False
    for line in pre.splitlines():
        if line.startswith("  "):
            if line.startswith(drop_prefixes):
                continue  # drop the verbatim-prose disagreement line
            if header is not None and not header_has_fields:
                out.append(header)
                header_has_fields = True
            out.append(line)
        else:
            # Boundary (row header or blank). Flush nothing for a header whose
            # only field line was a dropped prose field (orphaned header).
            header = line if line.strip() else None
            header_has_fields = False
            if not line.strip():
                out.append(line)
    pre_clean = "\n".join(out)
    if marker:
        return pre_clean.rstrip() + "\n\n" + marker + post
    return pre_clean + ("\n" if text.endswith("\n") else "")


def main() -> None:
    rows = [
        json.loads(line)
        for line in RECONCILED.read_text().splitlines()
        if line.strip()
    ]
    stripped = sum(1 for r in rows if any(f in r for f in PROSE_FIELDS))
    rows = destructure(rows)
    RECONCILED.write_text(
        "\n".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows
        )
        + "\n"
    )
    print(
        f"destructure_notes: removed {PROSE_FIELDS} from {stripped}/{len(rows)} rows"
    )

    if DISAGREEMENTS.exists():
        before = DISAGREEMENTS.read_text()
        after = sanitize_disagreements(before)
        DISAGREEMENTS.write_text(after)
        removed = before.count("\n") - after.count("\n")
        print(f"destructure_notes: removed {removed} prose line(s) from {DISAGREEMENTS.name}")


if __name__ == "__main__":
    main()
