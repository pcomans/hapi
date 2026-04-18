"""Merge independent Claude Code subagent extractions into reconciled.jsonl.

Baud 1999 BdE 126 *Corpus*. Structure cloned from Dodson-Hilton. Adaptations:

- `dh_id` → `baud_id` throughout.
- **Primary key `baud_id`.** Baud's Corpus is numbered 1–282, but a handful of
  sub-entries appear with a letter-suffix (e.g. `[60a] Pn-mdw` on physical
  p. 63, between `[60]` and `[61]`). The id namespace is therefore `baud-<N>`
  OR `baud-<N><letter>`, with `<letter>` a single lowercase a–z. Duplicate
  ids across agents/chunks are still bugs — `merge.py` fails loud on them.
- `_sort_key` orders first by integer N, then by letter suffix (`baud-60` < `baud-60a` < `baud-61`).
  Baud's own Corpus is alphabetical-by-Egyptian-transliteration, not numerical,
  but the merge output is numerical so that chunks concatenate cleanly across
  PRs. Phase A consumers who want alphabetical ordering re-sort.
- `DEFAULT_AGENT_DIR` is `<source_dir>/raw/` — the sandbox-writable path
  per the Phase-0 playbook.
- `SENTINEL_NULL_STRINGS` unchanged from Dodson-Hilton.
- **Multi-chunk support.** Each chunk (chunk-1 covering entries [1]–[40],
  chunk-2 [41]–[80], etc.) lands its three agents' extractions as
  `agent-{a,b,c}-chunk-<N>.jsonl`. Per-tag rows are unioned across chunks
  before merging; `_load` raises on duplicate `baud_id` within a single
  file AND across chunk files.

See Dodson-Hilton's merge.py and `docs/playbook-phase-0-ocr-transcription.md`
for rationale.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/baud-1999-ok-royal-family/merge.py
    BAUD_AGENT_DIR=/some/path uv run python \\
        pipeline/authority/sources/baud-1999-ok-royal-family/merge.py

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
DEFAULT_AGENT_DIR = SOURCE_DIR / "raw"
OUT = SOURCE_DIR / "reconciled.jsonl"
DIFF = SOURCE_DIR / "merge-disagreements.txt"


_BAUD_ID_RE = re.compile(r"^baud-(\d+)([a-z]?)$")


def _baud_num(baud_id: str) -> tuple[int, str]:
    """Extract the (N, suffix) sort key from a baud-N or baud-Na id.
    Raises on malformed ids. `baud-60` → (60, ''), `baud-60a` → (60, 'a').
    Tuple comparison gives the desired ordering: 60 < 60a < 61.
    """
    m = _BAUD_ID_RE.match(baud_id)
    if not m:
        raise ValueError(
            f"Malformed baud_id {baud_id!r}; expected 'baud-<N>' or "
            f"'baud-<N><letter>' (single a-z suffix for sub-entries)."
        )
    return (int(m.group(1)), m.group(2))


def _load(p: Path) -> dict[str, dict]:
    """Load a single agent's JSONL. Raises on duplicate baud_id."""
    rows: dict[str, dict] = {}
    seen_line: dict[str, int] = {}
    for line_no, line in enumerate(p.read_text().splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        r = json.loads(s)
        baud_id = r["baud_id"]
        _baud_num(baud_id)  # validate shape
        if baud_id in rows:
            raise ValueError(
                f"Duplicate baud_id={baud_id!r} in {p} "
                f"(first seen on line {seen_line[baud_id]}, again on line {line_no})"
            )
        rows[baud_id] = r
        seen_line[baud_id] = line_no
    return rows


def _load_agent_chunks(agent_dir: Path, tag: str) -> dict[str, dict]:
    """Load every chunk file for one agent tag, union the rows across chunks.

    Matches `agent-{tag}-chunk-<N>.jsonl`. Raises on duplicate `baud_id`
    across chunk files — Baud's numeric ID namespace is meant to be globally
    unique across all chunks (entries [1]–[282]), so a collision is a bug.
    """
    files = sorted(agent_dir.glob(f"agent-{tag}-*.jsonl"))
    if not files:
        return {}

    combined: dict[str, dict] = {}
    source_of: dict[str, Path] = {}
    for p in files:
        rows = _load(p)
        for baud_id, row in rows.items():
            if baud_id in combined:
                raise ValueError(
                    f"Duplicate baud_id={baud_id!r} across chunk files: "
                    f"first in {source_of[baud_id]}, again in {p}"
                )
            combined[baud_id] = row
            source_of[baud_id] = p
    return combined


SENTINEL_NULL_STRINGS = frozenset({"none", "-", "—", "n/a", "na", "unknown"})


def _normalise_value(v: object) -> object:
    """Collapse sentinel strings that mean 'null' into actual None.

    Bracketed placeholders like `[Snéfrou]` or hedged strings like
    `"Téti (probable)"` are NOT sentinel-null — they are Baud's authorial
    reconstruction / probability markers and must survive.
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
    empty = [tag for tag, a in agents.items() if not a]
    if empty:
        sys.exit(
            f"ERROR: agent(s) {', '.join(empty)} produced no rows in {agent_dir}. "
            f"Expected at least one `agent-{{tag}}-chunk-<N>.jsonl` per agent. "
            f"See transcribe.md."
        )

    all_ids_unsorted = set().union(*[a.keys() for a in agents.values()])
    all_ids = sorted(all_ids_unsorted, key=_baud_num)

    # Schema uniformity: every row in reconciled.jsonl must carry every
    # field that ANY agent produced on ANY row. Per-row field derivation
    # (the old `set().union(*[v.keys() for _, v in present])` pattern)
    # let a field that one agent omitted on one row vanish from the merged
    # output for that row while remaining in every other row — breaking
    # the prompt's "every row must contain every schema field" guarantee.
    # Computing the field set once across the full agent output keeps the
    # merged JSONL a rectangular table.
    all_fields = sorted(
        set().union(*[set(row.keys()) for a in agents.values() for row in a.values()])
    )

    final: list[dict] = []
    report: list[str] = []

    for baud_id in all_ids:
        versions = [(tag, agents[tag].get(baud_id)) for tag in "abc"]
        present = [(t, v) for t, v in versions if v is not None]
        if len(present) < 2:
            # Single-agent rows still go through _majority so sentinel
            # strings ("none", "-", "n/a") are normalised to null — merge
            # must produce a uniform schema regardless of how many agents
            # voted on a given row.
            report.append(f"{baud_id}: only 1/3 agents found this entry (kept it).\n")

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
                f"{baud_id} ({merged.get('name_egyptian', '?')}):\n"
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
        default=Path(os.environ.get("BAUD_AGENT_DIR", DEFAULT_AGENT_DIR)),
        help=f"Directory containing agent-{{a,b,c}}-chunk-N.jsonl (default: {DEFAULT_AGENT_DIR}).",
    )
    args = parser.parse_args()
    main(args.agent_dir)
