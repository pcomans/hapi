"""Apply LLM-reviewer-identified corrections to reconciled.jsonl.

Run AFTER merge.py. Mirrors Kitchen / Baud / Dodson-Hilton patterns —
idempotent re-runs, append-only LLM-APPLIED OVERRIDES section in
merge-disagreements.txt, every override recorded with rationale.

For chunk 1 (KV1–KV10), the 3-subagent extraction produced zero field-level
disagreements (the per-tomb mapping in `prompt.md` was authoritative enough
that all three agents emitted identical output). This file commits with an
empty SPOT_CORRECTIONS list as a placeholder; the egyptologist-reviewer pass
runs post-PR-open per CLAUDE.md PR workflow, and any reviewer-identified
corrections land in this file's CHUNK1_CORRECTIONS list and through to
SPOT_CORRECTIONS.

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


# Chunk-1 corrections from the egyptologist-reviewer pass.
# Each entry: (tomb_id, field, new_value, rationale).
#
# Empty for the initial PR landing — the egyptologist-reviewer subagent
# runs post-PR-open per CLAUDE.md § "Pull request workflow" step 3, and
# any actionable corrections land in this list in a follow-up commit.
CHUNK1_CORRECTIONS: list[tuple[str, str, object, str]] = []


# Aggregation: every chunk's corrections list must appear here.
# `test_all_corrections_includes_every_chunk_list` asserts module-level
# `CHUNK*_CORRECTIONS` attributes are all present so dropping one silently
# destroys its audit trail.
ALL_CORRECTIONS: list[list[tuple[str, str, object, str]]] = [
    CHUNK1_CORRECTIONS,
]

SPOT_CORRECTIONS: list[tuple[str, str, object, str]] = sum(ALL_CORRECTIONS, [])

# Guard against accidental `(tomb_id, field)` duplicates across correction
# lists — a duplicate silently stomps the earlier value based on list order.
# Empty allowlist for now; add intentional-override tuples if needed.
_ALLOWED_DUPLICATES: frozenset[tuple[str, str]] = frozenset()
_seen: dict[tuple[str, str], int] = {}
for _tomb_id, _field, _, _ in SPOT_CORRECTIONS:
    _key = (_tomb_id, _field)
    _seen[_key] = _seen.get(_key, 0) + 1
    if _seen[_key] > 1 and _key not in _ALLOWED_DUPLICATES:
        raise ValueError(
            f"Duplicate SPOT_CORRECTIONS entry for {_key!r}; "
            f"later value silently overrides. Add to _ALLOWED_DUPLICATES "
            f"if intentional, or merge the two entries."
        )
del _seen
if SPOT_CORRECTIONS:
    del _tomb_id, _field, _key


def main() -> None:
    rows = [json.loads(line) for line in RECONCILED.read_text().splitlines() if line.strip()]

    # Spot corrections.
    #
    # The log must describe the *state* of reconciled.jsonl, not the *delta*
    # from the previous run. On a second run every `old_val == new_val`, so a
    # delta-style log would incorrectly report "no overrides applied" while
    # the file on disk reflects all the applied overrides. Instead: always
    # log every SPOT_CORRECTION entry.
    override_log: list[str] = []
    applied_count = 0
    for tomb_id, field, new_val, rationale in SPOT_CORRECTIONS:
        row = next((r for r in rows if r["tomb_id"] == tomb_id), None)
        if row is None:
            raise KeyError(f"No row with tomb_id={tomb_id!r}")
        old_val = row.get(field)
        if old_val != new_val:
            applied_count += 1
            override_log.append(
                f"- {tomb_id}: {field} corrected ({rationale})\n"
                f"    was: {json.dumps(old_val, ensure_ascii=False)}\n"
                f"    now: {json.dumps(new_val, ensure_ascii=False)}"
            )
            row[field] = new_val
        else:
            override_log.append(
                f"- {tomb_id}: {field} corrected ({rationale})\n"
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
