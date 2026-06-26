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
import os
from pathlib import Path

SOURCE_DIR = Path(__file__).resolve().parent
RECONCILED = SOURCE_DIR / "reconciled.jsonl"
DISAGREEMENTS = SOURCE_DIR / "merge-disagreements.txt"


def _atomic_write(path: Path, content: str) -> None:
    """Write `content` to `path` atomically: stage to a sibling `.tmp` file
    then `os.replace()`, so an interrupted run cannot leave the target in a
    corrupted or partial state. Matches the in-directory precedent in
    `pre_merge.py` (Gemini PR #218 round-3)."""
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(content, encoding="utf-8")
    os.replace(temp_path, path)

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


def _drop_prose_overrides(post: str) -> str:
    """Drop fix_rows override entries targeting a PROSE_FIELDS field from the
    post-marker section.

    Defensive completeness: `fix_rows.py` no longer emits `notes` corrections,
    so on a current artifact this is a no-op (and returns `post` byte-for-byte).
    But if this terminal stage is ever run on a `merge-disagreements.txt`
    produced by an OLDER `fix_rows.py` that still wrote `notes` corrections,
    their verbatim `value:`/`was:`/`now:` lines would otherwise survive here —
    so this stage cleans them too, making it a self-sufficient scrubber rather
    than one coupled to fix_rows' state. Override entries have the shape
    `- <dh_id> [<sub_period>]: <field> corrected (...)` followed by indented
    continuation lines.
    """
    drop_headers = tuple(f": {f} corrected" for f in PROSE_FIELDS)
    if not any(h in post for h in drop_headers):
        return post  # nothing to drop — preserve exactly
    out: list[str] = []
    dropping = False
    for line in post.splitlines():
        if line.startswith("- "):
            dropping = any(h in line for h in drop_headers)
            if not dropping:
                out.append(line)
            continue
        if dropping and (line.startswith("    ") or not line.strip()):
            continue  # indented continuation / blank inside the dropped entry
        dropping = False
        out.append(line)
    return "\n".join(out) + ("\n" if post.endswith("\n") else "")


def sanitize_disagreements(text: str) -> str:
    """Strip verbatim-prose from the merge-disagreements audit log.

    The pre-marker portion records the 3 agents' per-field disagreements as
    `  <field>: a="..." | b="..." -> chose "..."` lines — for `notes` those
    carry full D&H paragraphs verbatim. Drop every `  <field>:` line for a
    PROSE_FIELDS field, plus any row header left with no remaining field lines.
    The post-marker override section is also scrubbed of any prose-field
    override entries (`_drop_prose_overrides`) so the stage is a self-sufficient
    scrubber, not coupled to fix_rows.py having regenerated it. Pure; idempotent.
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
            # Append a blank separator only when it follows a non-blank line, so
            # that dropping an orphaned header (its sole field was prose) does
            # not leave consecutive blank lines.
            if not line.strip() and out and out[-1].strip():
                out.append(line)
    # rstrip() drops any trailing blank line `out` may carry, so the trailing
    # newline is re-added deliberately below and can't be doubled.
    pre_clean = "\n".join(out).rstrip()
    if marker:
        # Only separate the pre-portion from the marker when there IS a
        # pre-portion; otherwise (every disagreement was a stripped prose
        # field) the leading "\n\n" would prepend blank lines to the marker.
        sep = "\n\n" if pre_clean else ""
        return pre_clean + sep + marker + _drop_prose_overrides(post)
    if not pre_clean:
        return ""
    return pre_clean + ("\n" if text.endswith("\n") else "")


def main() -> None:
    rows = [
        json.loads(line)
        for line in RECONCILED.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    stripped = sum(1 for r in rows if any(f in r for f in PROSE_FIELDS))
    rows = destructure(rows)
    _atomic_write(
        RECONCILED,
        "\n".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows
        )
        + "\n",
    )
    print(
        f"destructure_notes: removed {PROSE_FIELDS} from {stripped}/{len(rows)} rows"
    )

    if DISAGREEMENTS.exists():
        before = DISAGREEMENTS.read_text(encoding="utf-8")
        after = sanitize_disagreements(before)
        _atomic_write(DISAGREEMENTS, after)
        removed = before.count("\n") - after.count("\n")
        print(f"destructure_notes: sanitized {DISAGREEMENTS.name} (-{removed} line(s))")


if __name__ == "__main__":
    main()
