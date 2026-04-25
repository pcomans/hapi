"""Merge three independent Claude Code subagent extractions into reconciled.jsonl.

Beckerath 1997 Anhang A has several error-prone micro-features (slash-separated
high/low alternative endpoints, mixed-certainty per-endpoint approximate flags,
Egyptian-language parenthetical name forms with non-ASCII diacritics like
``-rê`` / ``-rî`` / ``-ê`` / ``-â``, Dyn 16 Hyksos-vassal labelling, the Dyn 22
Oberägyptische Linie sub-line). The three-subagent + majority-vote pipeline
absorbs stochastic transcription drift on those features.

Structure cloned from kitchen-tipe/merge.py with three adaptations:

1. ``kitchen_id`` → ``beckerath_id`` everywhere.
2. ``_sort_key`` orders rows by ``(dynasty_int, sub_line_rank, sequence)`` —
   Beckerath uses a ``sub_line`` field rather than compound ID prefixes, so
   the sort key reads it directly off the row.
3. ``DEFAULT_AGENT_DIR`` is beckerath-specific.

Sentinel-null normalisation and majority-vote logic are copied verbatim from
kitchen-tipe — they are source-agnostic. See kitchen-tipe/merge.py for the
rationale.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/beckerath-1997-chronologie/merge.py
    BECKERATH_AGENT_DIR=/some/path uv run python \\
        pipeline/authority/sources/beckerath-1997-chronologie/merge.py

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


# Sub-line ordering within a dynasty: main line (null) sorts first, then
# alphabetical. Hohepriester comes before Oberägyptische Linie, etc.
SUB_LINE_RANK: dict[object, int] = {
    None: 0,
}


def _sub_line_rank(sub_line: object) -> tuple[int, str]:
    """Sort null first, then alphabetical."""
    if sub_line is None:
        return (0, "")
    return (1, str(sub_line))


def _load(p: Path) -> dict[str, dict]:
    """Load a single agent's JSONL. Raises on duplicate beckerath_id within a file."""
    rows: dict[str, dict] = {}
    seen_line: dict[str, int] = {}
    for line_no, line in enumerate(p.read_text().splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        r = json.loads(s)
        bid = r["beckerath_id"]
        if bid in rows:
            raise ValueError(
                f"Duplicate beckerath_id {bid!r} in {p} "
                f"(first seen on line {seen_line[bid]}, again on line {line_no})"
            )
        rows[bid] = r
        seen_line[bid] = line_no
    return rows


SENTINEL_NULL_STRINGS = frozenset({"none", "-", "—", "n/a", "na", "unknown"})


def _normalise_value(v: object) -> object:
    """Collapse sentinel strings that mean 'null' into actual None.

    Beckerath uses `-` in a few cells (e.g. when no Egyptian titulary is
    given for an obscure king) and the bracketed `[?]` form for unknown
    Horus names; the subagent prompt preserves the bracketed phrase
    verbatim, so this normaliser is for `-` / `none` style cells only.
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


_BID_RE = re.compile(r"^(?P<dyn>\d+)\.(?P<seq>\d+)$")


def _sort_key(row: dict) -> tuple:
    """Sort by (dynasty_int, sub_line_rank, sequence_in_dynasty).

    Reads ``dynasty``, ``sub_line``, ``sequence_in_dynasty`` directly off the
    row rather than parsing the ID, because Beckerath's IDs are pure
    ``{dyn:02}.{seq:02}`` without sub-line encoding.
    """
    dyn = row.get("dynasty", 9999)
    if not isinstance(dyn, int):
        dyn = 9999
    sub_rank = _sub_line_rank(row.get("sub_line"))
    seq = row.get("sequence_in_dynasty", -1)
    if not isinstance(seq, int):
        seq = -1
    return (dyn, sub_rank, seq)


def _row_sort_key_from_id(bid: str, agents: dict) -> tuple:
    """Look up sort key for a beckerath_id by finding the row in any agent.

    Used during merge before we know which row content to keep — the sort
    key has to be derivable from the ID + an exemplar row from any agent.
    """
    for agent in agents.values():
        if bid in agent:
            return _sort_key(agent[bid])
    # Pure ID-based fallback
    m = _BID_RE.match(bid)
    if not m:
        return (9999, (1, ""), -1)
    return (int(m.group("dyn")), (0, ""), int(m.group("seq")))


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
        key=lambda bid: _row_sort_key_from_id(bid, agents),
    )

    final: list[dict] = []
    report: list[str] = []

    for bid in all_ids:
        versions = [(tag, agents[tag].get(bid)) for tag in "abc"]
        present = [(t, v) for t, v in versions if v is not None]
        if len(present) < 2:
            final.append(present[0][1])
            report.append(f"{bid}: only 1/3 agents found this entry (kept it).\n")
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
                f"{bid} ({merged.get('name', '?')}):\n"
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
        default=Path(os.environ.get("BECKERATH_AGENT_DIR", DEFAULT_AGENT_DIR)),
        help=f"Directory containing agent-a/b/c.jsonl (default: {DEFAULT_AGENT_DIR}).",
    )
    args = parser.parse_args()
    main(args.agent_dir)
