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
  4. Write the field-level disagreement report to `merge-disagreements.txt`
     for downstream review (LLM reviewer pass first, then eventually
     an actual scholar — see ADR-017 step 6).

The extraction step is non-deterministic (LLM output); the merge step IS
deterministic. The committed `reconciled.jsonl` is the source of truth;
anyone can re-run the 3-agent extraction and diff.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/ryholt-1997-sip/merge.py
    cd pipeline && uv run python pipeline/authority/sources/ryholt-1997-sip/merge.py \\
        --agent-dir /some/other/path
    RYHOLT_AGENT_DIR=/some/other/path \\
        uv run python pipeline/authority/sources/ryholt-1997-sip/merge.py

Outputs:
    reconciled.jsonl                 (this source dir)
    merge-disagreements.txt          (this source dir; committed for audit)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
DEFAULT_AGENT_DIR = Path("/tmp/claude-501/ryholt")
OUT = SOURCE_DIR / "reconciled.jsonl"
DIFF = SOURCE_DIR / "merge-disagreements.txt"


def _load(p: Path) -> dict[str, dict]:
    """Load a single agent's JSONL. Raises on duplicate ryholt_id within a file."""
    rows: dict[str, dict] = {}
    seen_line: dict[str, int] = {}
    for line_no, line in enumerate(p.read_text().splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        r = json.loads(s)
        rid = r["ryholt_id"]
        if rid in rows:
            raise ValueError(
                f"Duplicate ryholt_id {rid!r} in {p} "
                f"(first seen on line {seen_line[rid]}, again on line {line_no})"
            )
        rows[rid] = r
        seen_line[rid] = line_no
    return rows


SENTINEL_NULL_STRINGS = frozenset({"none", "-", "—", "n/a", "na", "unknown"})


def _normalise_value(v: object) -> object:
    """Collapse sentinel strings that mean 'null' into actual None.

    Ryholt prints literal words like `none` in some Chron Table cells
    (e.g. Sakir-Har at 15.3, whose cartouche carries no sꜣ-rꜥ prenomen).
    Subagents faithfully transcribe those strings; we do not want them in
    the authority JSONL as string values — downstream consumers would
    treat them as real data.
    """
    if isinstance(v, str):
        stripped = v.strip().lower()
        if stripped in SENTINEL_NULL_STRINGS:
            return None
    return v


def _majority(values: list) -> tuple[object, int]:
    """Return (chosen_value, count_of_agreers) from a list of per-agent values.

    Values are normalised first so that `"none"` and `null` count as the
    same vote.
    """
    normalised = [_normalise_value(v) for v in values]

    def key(v):
        return json.dumps(v, ensure_ascii=False, sort_keys=True)

    counts = Counter(key(v) for v in normalised)
    top_key, top_count = counts.most_common(1)[0]
    for v in normalised:
        if key(v) == top_key:
            return v, top_count
    return None, 0


_RID_RE = re.compile(r"^(?P<prefix>[A-Za-z]+|\d+)(?:\.(?P<seq>\d+)(?P<suffix>[a-z]*))?$")


def _sort_key(rid: str) -> tuple[int, str, int, str]:
    """Sort order: numeric dynasty (13-17) ascending, then sequence number
    ascending (not lexicographic — so 13.10 sorts AFTER 13.9), then suffix.
    Non-numeric prefixes (Abyd, N, P, H, D, G) sort after numeric dynasties,
    alphabetically by prefix then by sequence.
    """
    m = _RID_RE.match(rid)
    if not m:
        return (9999, rid, 0, "")
    prefix = m.group("prefix")
    seq = int(m.group("seq")) if m.group("seq") else -1
    suffix = m.group("suffix") or ""
    if prefix.isdigit():
        return (int(prefix), "", seq, suffix)
    return (9999, prefix, seq, suffix)


def main(agent_dir: Path) -> None:
    agent_files = {tag: agent_dir / f"agent-{tag}.jsonl" for tag in "abc"}
    missing = [p for p in agent_files.values() if not p.exists()]
    if missing:
        sys.exit(
            f"ERROR: missing agent output files: {', '.join(str(p) for p in missing)}\n"
            f"Expected three files at {agent_dir}. See transcribe.md."
        )

    agents = {tag: _load(p) for tag, p in agent_files.items()}
    all_ids = sorted(
        set().union(*[a.keys() for a in agents.values()]),
        key=_sort_key,
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

    print("Agents: " + ", ".join(f"{t}={len(a)}" for t, a in agents.items()))
    print(f"Merged rows: {len(final)}")
    rows_with_disagreement = sum(1 for r in report if r.strip())
    print(f"Rows with ≥1 field disagreement: {rows_with_disagreement}")
    print(f"Wrote {OUT.relative_to(OUT.parents[4])}")
    print(f"Wrote {DIFF.relative_to(DIFF.parents[4])}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent-dir",
        type=Path,
        default=Path(os.environ.get("RYHOLT_AGENT_DIR", DEFAULT_AGENT_DIR)),
        help=f"Directory containing agent-a/b/c.jsonl (default: {DEFAULT_AGENT_DIR}).",
    )
    args = parser.parse_args()
    main(args.agent_dir)
