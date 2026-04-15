"""Merge three independent Claude Code subagent extractions into reconciled.jsonl.

Kitchen 1996 TIPE Tables 1, 3, 4 have several error-prone micro-features
(`c.` date prefixes, hedge markers, co-regency annotations, bracketed
`[Prenomen unknown]` placeholders, `'III'` vs `(II)` Roman-numeral
typography). The three-subagent + majority-vote pipeline absorbs stochastic
transcription drift on those features.

Structure cloned from ryholt-1997-sip/merge.py with three adaptations:

1. `ryholt_id` → `kitchen_id` everywhere.
2. `_sort_key` recognises Kitchen's compound stream prefixes
   (`20`, `21`, `21H`, `22`, `23`, `24E`, `24`, `24P`, `25`, `26`) and
   orders them by `(dynasty_int, polity_rank)` so parallel lines within the
   same dynasty interleave predictably.
3. `DEFAULT_AGENT_DIR` is kitchen-specific.

The sentinel-null normalisation and the majority-vote logic are copied
verbatim — they are source-agnostic. See the Ryholt merge.py docstring for
the rationale.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/kitchen-tipe/merge.py
    KITCHEN_AGENT_DIR=/some/path uv run python \\
        pipeline/authority/sources/kitchen-tipe/merge.py

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


# (dynasty_int, polity_rank) for each stream prefix. Polity rank orders
# parallel lines within a dynasty: the "main" line sits at rank 0, others
# follow in the order Kitchen introduces them.
STREAM_ORDER: dict[str, tuple[int, int]] = {
    "20": (20, 0),
    "21": (21, 0),  # Tanite kings
    "21H": (21, 1),  # Theban High Priests of Amun
    "22": (22, 0),
    "23": (23, 0),
    "24E": (24, 0),  # Early Saite Princes (pre-Dyn-24 Mā chiefs)
    "24": (24, 1),  # Tefnakht I, Bakenranef
    "24P": (24, 2),  # Proto-Saite Dynasty
    "25": (25, 0),
    "26": (26, 0),
}


def _load(p: Path) -> dict[str, dict]:
    """Load a single agent's JSONL. Raises on duplicate kitchen_id within a file."""
    rows: dict[str, dict] = {}
    seen_line: dict[str, int] = {}
    for line_no, line in enumerate(p.read_text().splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        r = json.loads(s)
        kid = r["kitchen_id"]
        if kid in rows:
            raise ValueError(
                f"Duplicate kitchen_id {kid!r} in {p} "
                f"(first seen on line {seen_line[kid]}, again on line {line_no})"
            )
        rows[kid] = r
        seen_line[kid] = line_no
    return rows


SENTINEL_NULL_STRINGS = frozenset({"none", "-", "—", "n/a", "na", "unknown"})


def _normalise_value(v: object) -> object:
    """Collapse sentinel strings that mean 'null' into actual None.

    Kitchen prints literal `[Prenomen unknown]` in a handful of table cells
    (Takeloth I, Iuput II, etc.) — those are NOT sentinel-null, they are a
    specific Kitchen-ism that downstream consumers want to see. The subagent
    prompt preserves them verbatim; this normaliser is for `"-"` / `"none"`
    style cells only.
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


_KID_RE = re.compile(r"^(?P<prefix>[0-9]+[A-Za-z]*)\.(?P<seq>\d+)$")


def _sort_key(kid: str) -> tuple[int, int, str, int]:
    """Sort by (dynasty_int, polity_rank, prefix, sequence_in_stream).

    Prefixes outside `STREAM_ORDER` sort to the end. Sequences that aren't
    pure integers sort after integer sequences within their prefix.
    """
    m = _KID_RE.match(kid)
    if not m:
        return (9999, 9999, kid, -1)
    prefix = m.group("prefix")
    seq = int(m.group("seq"))
    dyn, rank = STREAM_ORDER.get(prefix, (9999, 9999))
    return (dyn, rank, prefix, seq)


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

    for kid in all_ids:
        versions = [(tag, agents[tag].get(kid)) for tag in "abc"]
        present = [(t, v) for t, v in versions if v is not None]
        if len(present) < 2:
            final.append(present[0][1])
            report.append(f"{kid}: only 1/3 agents found this entry (kept it).\n")
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
                f"{kid} ({merged.get('name', '?')}):\n"
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
        default=Path(os.environ.get("KITCHEN_AGENT_DIR", DEFAULT_AGENT_DIR)),
        help=f"Directory containing agent-a/b/c.jsonl (default: {DEFAULT_AGENT_DIR}).",
    )
    args = parser.parse_args()
    main(args.agent_dir)
