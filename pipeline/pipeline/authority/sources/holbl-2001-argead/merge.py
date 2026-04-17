"""Merge three independent Claude Code subagent extractions into reconciled.jsonl.

Hölbl 2001 Argead-bridge covers three rulers (Alexander the Great, Philip III
Arrhidaios, Alexander IV) — the gap between HKW 2006's Egyptian king-list
coverage (which stops at Alexander) and pharaoh.se's Ptolemaic coverage
(which starts at Ptolemy I Soter's kingship in 306 BCE).

Structure cloned from kitchen-tipe/merge.py with three adaptations:

1. `kitchen_id` → `holbl_id` everywhere.
2. `_sort_key` handles the single stream prefix `argead` (no compound prefix
   table). Rows sort by the `NN` integer suffix.
3. `DEFAULT_AGENT_DIR` is holbl-argead-specific.

The sentinel-null normalisation and the majority-vote logic are copied
verbatim — they are source-agnostic.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/holbl-2001-argead/merge.py
    HOLBL_AGENT_DIR=/some/path uv run python \\
        pipeline/authority/sources/holbl-2001-argead/merge.py

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


def _load(p: Path) -> dict[str, dict]:
    """Load a single agent's JSONL. Raises on duplicate holbl_id within a file."""
    rows: dict[str, dict] = {}
    seen_line: dict[str, int] = {}
    for line_no, line in enumerate(p.read_text().splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        r = json.loads(s)
        hid = r["holbl_id"]
        if hid in rows:
            raise ValueError(
                f"Duplicate holbl_id {hid!r} in {p} "
                f"(first seen on line {seen_line[hid]}, again on line {line_no})"
            )
        rows[hid] = r
        seen_line[hid] = line_no
    return rows


SENTINEL_NULL_STRINGS = frozenset({"none", "-", "—", "n/a", "na", "unknown"})


def _normalise_value(v: object) -> object:
    """Collapse sentinel strings that mean 'null' into actual None.

    Kept verbatim from kitchen-tipe/merge.py for source-agnostic robustness,
    even though the Hölbl extract's fields do not exercise it (every field is
    either a real string, a real integer, a boolean, a list, or a nested
    dict). Future Phase-0 sources that reuse this merge still benefit.
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


_HID_RE = re.compile(r"^(?P<prefix>[A-Za-z]+)\.(?P<seq>\d+)$")


def _sort_key(hid: str) -> tuple[str, int]:
    """Sort by (prefix, sequence_in_stream).

    Only one stream (`argead`) is defined for this source; the prefix-keyed
    tuple leaves room for future Hölbl extensions (e.g. an `interregnum`
    or `ptolemaic` stream) without restructuring the sort.
    """
    m = _HID_RE.match(hid)
    if not m:
        raise ValueError(
            f"holbl_id {hid!r} does not match expected shape "
            f"{_HID_RE.pattern!r}. Every extracted row must carry a "
            f"well-formed holbl_id."
        )
    return (m.group("prefix"), int(m.group("seq")))


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

    for hid in all_ids:
        versions = [(tag, agents[tag].get(hid)) for tag in "abc"]
        present = [(t, v) for t, v in versions if v is not None]
        if len(present) < 2:
            final.append(present[0][1])
            report.append(f"{hid}: only 1/3 agents found this entry (kept it).\n")
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
                f"{hid} ({merged.get('name', '?')}):\n"
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
        default=Path(os.environ.get("HOLBL_AGENT_DIR", DEFAULT_AGENT_DIR)),
        help=f"Directory containing agent-a/b/c.jsonl (default: {DEFAULT_AGENT_DIR}).",
    )
    args = parser.parse_args()
    main(args.agent_dir)
