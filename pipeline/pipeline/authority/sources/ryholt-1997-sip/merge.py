"""Merge three independent Claude Code subagent extractions into reconciled.jsonl.

Ryholt's catalogue has many edge cases (bold vs plain Appellation headers,
letter-only file suffixes, lacuna markers, two Chronological-Table layouts,
kings listed with disambiguators like "Sewadjkare (I)"), and a deterministic
regex parser quickly accumulates brittle special cases. Instead, the
extraction is performed by running three independent Claude Code subagents
in parallel, each reading the same OCR chunks and emitting JSONL per the
Ryholt schema. This script deterministically merges those three outputs:

  1. Group rows by `ryholt_id`.
  2. For each field in each row, majority-vote across the three agents.
  3. Write the merged rows to `reconciled.jsonl`.
  4. Write a human-readable disagreement report to `merge-disagreements.txt`
     for curator review.

The extraction step is non-deterministic (LLM output); the merge step IS
deterministic. The committed `reconciled.jsonl` is the source of truth;
anyone can re-run the 3-agent extraction and diff.

Inputs:
    /tmp/claude-501/ryholt/agent-a.jsonl
    /tmp/claude-501/ryholt/agent-b.jsonl
    /tmp/claude-501/ryholt/agent-c.jsonl

Outputs:
    reconciled.jsonl                 (this source dir)
    merge-disagreements.txt          (this source dir; committed for audit)

See `transcribe.md` for the full workflow and the subagent prompt.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
AGENT_DIR = Path("/tmp/claude-501/ryholt")
AGENT_FILES = {tag: AGENT_DIR / f"agent-{tag}.jsonl" for tag in "abc"}
OUT = SOURCE_DIR / "reconciled.jsonl"
DIFF = SOURCE_DIR / "merge-disagreements.txt"


def _load(p: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for line in p.read_text().splitlines():
        s = line.strip()
        if not s:
            continue
        r = json.loads(s)
        rows[r["ryholt_id"]] = r
    return rows


def _majority(values: list) -> tuple[object, int]:
    """Return (chosen_value, count_of_agreers) from a list of per-agent values."""

    def key(v):
        return json.dumps(v, ensure_ascii=False, sort_keys=True)

    counts = Counter(key(v) for v in values)
    top_key, top_count = counts.most_common(1)[0]
    for v in values:
        if key(v) == top_key:
            return v, top_count
    return None, 0


def main() -> None:
    agents = {tag: _load(p) for tag, p in AGENT_FILES.items()}
    all_ids = sorted(
        set().union(*[a.keys() for a in agents.values()]),
        key=lambda rid: (
            int(rid.split(".")[0]) if rid.split(".")[0].isdigit() else 999,
            rid,
        ),
    )

    final: list[dict] = []
    report: list[str] = []

    for rid in all_ids:
        versions = [(tag, agents[tag].get(rid)) for tag in "abc"]
        present = [(t, v) for t, v in versions if v is not None]
        if len(present) < 2:
            final.append(present[0][1])
            report.append(f"{rid}: only 1/3 agents found this entry (kept it).\n")
            continue

        all_fields = set().union(*[v.keys() for _, v in present])
        merged: dict = {}
        row_disagreements: list[str] = []
        for field in all_fields:
            values = [v.get(field) for _, v in present]
            chosen, count = _majority(values)
            merged[field] = chosen
            if count < len(present):
                row_disagreements.append(
                    f"  {field}: "
                    + " | ".join(
                        f"{t}={json.dumps(v.get(field), ensure_ascii=False)}"
                        for t, v in present
                    )
                    + f"  → chose {json.dumps(chosen, ensure_ascii=False)}"
                )
        if row_disagreements:
            report.append(
                f"{rid} ({merged.get('nomen', '?')}):\n"
                + "\n".join(row_disagreements)
                + "\n"
            )
        final.append(merged)

    OUT.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in final) + "\n"
    )
    DIFF.write_text("\n".join(report) if report else "No field-level disagreements.\n")

    print(f"Agents: " + ", ".join(f"{t}={len(a)}" for t, a in agents.items()))
    print(f"Merged rows: {len(final)}")
    rows_with_disagreement = sum(1 for r in report if r.strip())
    print(f"Rows with ≥1 field disagreement: {rows_with_disagreement}")
    print(f"Wrote {OUT.relative_to(OUT.parents[4])}")
    print(f"Wrote {DIFF.relative_to(DIFF.parents[4])}")


if __name__ == "__main__":
    main()
