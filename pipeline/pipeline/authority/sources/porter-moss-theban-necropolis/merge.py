"""Merge three independent Claude Code subagent extractions into reconciled.jsonl.

Porter-Moss Vol I (Theban Necropolis) is a multi-chunk source — chunk 1 is
KV1–KV10 (PM I.2 § I.A); future chunks land more KV, then QV, then per-section
TT material from PM I.1. This file follows the playbook's "Multi-chunk source
pattern" (see `docs/playbook-phase-0-ocr-transcription.md` § "merge.py
union-across-chunks") so a chunk-2 PR can drop `agent-{a,b,c}-chunk2.jsonl`
into `raw/` without touching merge.py.

Structure cloned from kitchen-tipe/merge.py (the closest tabular reference)
with three adaptations:

1. `kitchen_id` → `tomb_id` everywhere.
2. `_sort_key` orders by valley (KV → QV → TT → ...) then numeric tomb id.
3. Cross-chunk `_load_agent_chunks` collects `agent-<tag>-*.jsonl` in
   addition to the bare `agent-<tag>.jsonl`, raising on cross-chunk
   tomb_id collisions.

The sentinel-null normalisation, majority-vote, and disagreement-logging
logic are copied verbatim — they are source-agnostic.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/porter-moss-theban-necropolis/merge.py
    PM_AGENT_DIR=/some/path uv run python \\
        pipeline/authority/sources/porter-moss-theban-necropolis/merge.py

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
DEFAULT_AGENT_DIR = Path(__file__).parent / "raw"
OUT = SOURCE_DIR / "reconciled.jsonl"
DIFF = SOURCE_DIR / "merge-disagreements.txt"


# Valley-prefix sort order. Lower rank sorts first. Add new prefixes here as
# follow-up chunks introduce them (e.g. `DAN` Dra' Abu el-Naga, `DEM` Deir
# el-Medina, `RAM` Ramesseum etc. — Phase A may use different conventions
# but the chunk-1 KV-only ordering is forward-compatible).
VALLEY_ORDER: dict[str, int] = {
    "KV": 0,  # Valley of the Kings
    "QV": 1,  # Valley of the Queens
    "TT": 2,  # Theban Tomb (Private Tombs, PM I.1)
}

# Sentinel ranks for unrecognised prefixes / malformed IDs — they sort to
# the end so committed reconciled.jsonl stays correctly ordered for the
# known prefixes even when a malformed ID slips through (the duplicate
# detection in `_load` catches the malformed ID separately).
UNRECOGNISED_VALLEY_RANK = 9999
MALFORMED_TOMB_RANK = 999_999


_TOMB_RE = re.compile(r"^(?P<prefix>[A-Z]+)(?P<num>\d+)(?P<suffix>[a-z]?)$")


def _sort_key(tomb_id: str) -> tuple[int, int, str, str]:
    """Sort by (valley_rank, numeric_tomb, suffix, raw_id).

    Suffixed IDs (`KV5a`) sort directly after the unsuffixed parent (`KV5`).
    Unrecognised valley prefixes sort to the end.
    """
    m = _TOMB_RE.match(tomb_id)
    if not m:
        return (UNRECOGNISED_VALLEY_RANK, MALFORMED_TOMB_RANK, "", tomb_id)
    prefix = m.group("prefix")
    num = int(m.group("num"))
    suffix = m.group("suffix")
    rank = VALLEY_ORDER.get(prefix, UNRECOGNISED_VALLEY_RANK)
    return (rank, num, suffix, tomb_id)


def _load(p: Path) -> dict[str, dict]:
    """Load a single agent's JSONL. Raises on duplicate tomb_id within a file."""
    rows: dict[str, dict] = {}
    seen_line: dict[str, int] = {}
    for line_no, line in enumerate(p.read_text().splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        r = json.loads(s)
        tid = r["tomb_id"]
        if tid in rows:
            raise ValueError(
                f"Duplicate tomb_id {tid!r} in {p} "
                f"(first seen on line {seen_line[tid]}, again on line {line_no})"
            )
        rows[tid] = r
        seen_line[tid] = line_no
    return rows


def _load_agent_chunks(agent_dir: Path, tag: str) -> dict[str, dict]:
    """Union all `agent-<tag>*.jsonl` files for one agent across chunks.

    Cross-chunk `tomb_id` collisions raise loudly — a tomb is meant to live
    in exactly one chunk per the chunk plan in README.md. A collision means
    either (a) chunk-overlap bug in the chunk plan or (b) an extraction-side
    bug where two chunks both extracted the same tomb. Either way it's an
    error, not a legitimate merge case.
    """
    base = agent_dir / f"agent-{tag}.jsonl"
    chunks = sorted(agent_dir.glob(f"agent-{tag}-*.jsonl"))
    files = ([base] if base.exists() else []) + chunks
    if not files:
        return {}
    combined: dict[str, dict] = {}
    source_of: dict[str, Path] = {}
    for p in files:
        rows = _load(p)
        for tid, row in rows.items():
            if tid in combined:
                raise ValueError(
                    f"Duplicate {tid!r} across chunk files for agent-{tag}: "
                    f"first in {source_of[tid]}, again in {p}"
                )
            combined[tid] = row
            source_of[tid] = p
    return combined


SENTINEL_NULL_STRINGS = frozenset({"none", "-", "—", "n/a", "na", "unknown"})


def _normalise_value(v: object) -> object:
    """Collapse sentinel strings that mean 'null' into actual None.

    PM does NOT use bracketed-known-unknown placeholders the way Kitchen
    does (`[Prenomen unknown]`) — every PM headword either names the
    occupant or doesn't have a tomb entry at all. So this normaliser is
    purely for sentinel artifacts that an agent may have emitted as a
    string instead of a JSON null.
    """
    if isinstance(v, str):
        stripped = v.strip().lower()
        if stripped in SENTINEL_NULL_STRINGS:
            return None
    return v


def _majority(values: list) -> tuple[object, int]:
    """Return (chosen_value, count_of_agreers) from a list of per-agent values."""
    normalised = [_normalise_value(v) for v in values]

    def key(v):
        return json.dumps(v, ensure_ascii=False, sort_keys=True)

    counts = Counter(key(v) for v in normalised)
    top_key, top_count = counts.most_common(1)[0]
    for v in normalised:
        if key(v) == top_key:
            return v, top_count
    return None, 0


def main(agent_dir: Path) -> None:
    agents = {tag: _load_agent_chunks(agent_dir, tag) for tag in "abc"}
    missing = [tag for tag, rows in agents.items() if not rows]
    if missing:
        sys.exit(
            f"ERROR: no JSONL output found for agent(s): {', '.join(missing)}\n"
            f"Expected agent-a.jsonl / agent-b.jsonl / agent-c.jsonl (and/or "
            f"agent-<tag>-<chunk>.jsonl follow-ups) at {agent_dir}. See transcribe.md."
        )

    all_ids = sorted(
        set().union(*[a.keys() for a in agents.values()]),
        key=_sort_key,
    )

    final: list[dict] = []
    report: list[str] = []

    for tid in all_ids:
        versions = [(tag, agents[tag].get(tid)) for tag in "abc"]
        present = [(t, v) for t, v in versions if v is not None]
        if len(present) < 2:
            # Single-agent rows fall through to the majority-vote path
            # below (which handles len(present) == 1 correctly: every
            # field is unanimous because there's only one agent). The
            # advantage over a special-case `final.append(present[0][1])`
            # is that `_normalise_value` runs uniformly across all rows
            # — so a sentinel string like `"none"` collapses to JSON null
            # whether one or three agents emitted it.
            report.append(f"{tid}: only 1/3 agents found this entry (kept it).\n")

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
                f"{tid} ({merged.get('occupant_name', '?')}):\n"
                + "\n".join(row_disagreements)
                + "\n"
            )
        final.append(merged)

    OUT.write_text(
        "\n".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) for r in final
        )
        + "\n"
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
        default=Path(os.environ.get("PM_AGENT_DIR", DEFAULT_AGENT_DIR)),
        help=f"Directory containing agent-a/b/c.jsonl (default: {DEFAULT_AGENT_DIR}).",
    )
    args = parser.parse_args()
    main(args.agent_dir)
