"""Merge independent Claude Code subagent extractions into reconciled.jsonl.

Dodson & Hilton 2004 Brief Lives. Structure cloned from Kitchen (Ryholt
lineage). Adaptations:

- `kitchen_id` → `dh_id` throughout.
- `_sort_key` alphabetical by `dh_id` (D&H's own Brief Lives ordering);
  `Q`-suffix "Unplaced" entries sort after the main alphabetical run;
  names with leading `[` / `–` (lacunae) sort last.
- `DEFAULT_AGENT_DIR` is `<source_dir>/raw/` — the sandbox-writable path
  per the Phase-0 playbook.
- `SENTINEL_NULL_STRINGS` unchanged from Kitchen.
- **Multi-chunk support.** Each chunk (Pre-Amarna p126–p130, Amarna
  p142–p145, ...) lands its three agents' extractions as
  `agent-{a,b,c}<suffix>.jsonl`. Per-tag rows are collected across all
  matching `agent-{tag}*.jsonl` files under `agent_dir`; `_load` raises
  on duplicate `dh_id` within a single file AND on duplicate `dh_id`
  across chunk files (the D&H disambiguator letters make cross-chunk
  homonyms impossible within one source, so a collision is a bug).

See Kitchen's merge.py and `docs/playbook-phase-0-ocr-transcription.md`
for rationale.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/dodson-hilton-queens/merge.py
    DH_AGENT_DIR=/some/path uv run python \\
        pipeline/authority/sources/dodson-hilton-queens/merge.py

Outputs:
    reconciled.jsonl                 (this source dir)
    merge-disagreements.txt          (this source dir; committed for audit)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
DEFAULT_AGENT_DIR = SOURCE_DIR / "raw"
OUT = SOURCE_DIR / "reconciled.jsonl"
DIFF = SOURCE_DIR / "merge-disagreements.txt"


def _load(p: Path) -> dict[str, dict]:
    """Load a single agent's JSONL. Raises on duplicate dh_id within a file."""
    rows: dict[str, dict] = {}
    seen_line: dict[str, int] = {}
    for line_no, line in enumerate(p.read_text().splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        r = json.loads(s)
        did = r["dh_id"]
        if did in rows:
            raise ValueError(
                f"Duplicate dh_id {did!r} in {p} "
                f"(first seen on line {seen_line[did]}, again on line {line_no})"
            )
        rows[did] = r
        seen_line[did] = line_no
    return rows


def _load_agent_chunks(agent_dir: Path, tag: str) -> dict[str, dict]:
    """Load every chunk file for one agent tag, union the rows across chunks.

    Matches `agent-{tag}.jsonl` (legacy unsuffixed filename, retained so
    existing Pre-Amarna raw files still load without renaming) and
    `agent-{tag}-<chunk>.jsonl` (follow-up chunks, e.g. `agent-a-amarna.jsonl`).
    When chunk 3 lands, the base file should be renamed to
    `agent-{tag}-power.jsonl` and the unsuffixed-filename branch dropped;
    see the code-reviewer note on PR #38.

    Raises on duplicate `dh_id` across chunk files — D&H disambiguator letters
    (`Ahmes A`, `Ahmes B`, …) guarantee per-source uniqueness, so a collision
    means an extraction bug, not a legitimate homonym.
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
        for did, row in rows.items():
            if did in combined:
                raise ValueError(
                    f"Duplicate dh_id {did!r} across chunk files: "
                    f"first in {source_of[did]}, again in {p}"
                )
            combined[did] = row
            source_of[did] = p
    return combined


SENTINEL_NULL_STRINGS = frozenset({"none", "-", "—", "n/a", "na", "unknown"})


def _normalise_value(v: object) -> object:
    """Collapse sentinel strings that mean 'null' into actual None.

    Bracketed placeholders like `[Prenomen unknown]` or hedged strings like
    `"Ay (probable)"` are NOT sentinel-null — they are authorial positive
    assertions and must survive.
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


def _sort_key_for(unplaced_ids: frozenset[str]):
    """Return a sort-key function that bins rows by Unplaced-ness first,
    then by case-insensitive alphabetical order within each bin.

    Bin 0: placed entries (D&H's main alphabetical Brief Lives list).
    Bin 1: unplaced entries (D&H's trailing `Unplaced` sub-section). Includes
           both `Q`-suffixed ids (Amenemhat Q, Henut Q, Thutmose Q) AND
           plain-name unplaced entries (Henutiunu, Sithori, Tatau, Ti, etc.)
           that D&H place under the Unplaced heading without a disambiguator.

    Sort order cannot be determined from dh_id alone because `unplaced`
    is a per-row field, not a name-suffix convention — hence the closure
    over the unplaced-ids set computed from the merged rows.
    """
    def _sort_key(dh_id: str) -> tuple[int, str]:
        bin_ = 1 if dh_id in unplaced_ids else 0
        return (bin_, dh_id.lower())

    return _sort_key


def main(agent_dir: Path) -> None:
    agents = {tag: _load_agent_chunks(agent_dir, tag) for tag in "abc"}
    empty = [tag for tag, a in agents.items() if not a]
    if empty:
        sys.exit(
            f"ERROR: agent(s) {', '.join(empty)} produced no rows in {agent_dir}. "
            f"Expected at least one `agent-{{tag}}.jsonl` or `agent-{{tag}}-<chunk>.jsonl` "
            f"per agent. See transcribe.md."
        )

    # Compute the set of unplaced dh_ids once, by majority-vote of the three
    # agents' `unplaced` fields per row. This lets _sort_key_for() bin the
    # output correctly without making the sort-key function itself depend on
    # the per-row merge result (which is computed below).
    all_ids_unsorted = set().union(*[a.keys() for a in agents.values()])
    unplaced_ids: set[str] = set()
    for did in all_ids_unsorted:
        votes = [a[did].get("unplaced", False) for a in agents.values() if did in a]
        if sum(1 for v in votes if v) > len(votes) / 2:
            unplaced_ids.add(did)

    all_ids = sorted(all_ids_unsorted, key=_sort_key_for(frozenset(unplaced_ids)))

    final: list[dict] = []
    report: list[str] = []

    for did in all_ids:
        versions = [(tag, agents[tag].get(did)) for tag in "abc"]
        present = [(t, v) for t, v in versions if v is not None]
        if len(present) < 2:
            final.append(present[0][1])
            report.append(f"{did}: only 1/3 agents found this entry (kept it).\n")
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
                f"{did} ({merged.get('name', '?')}):\n"
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
        default=Path(os.environ.get("DH_AGENT_DIR", DEFAULT_AGENT_DIR)),
        help=f"Directory containing agent-a/b/c.jsonl (default: {DEFAULT_AGENT_DIR}).",
    )
    args = parser.parse_args()
    main(args.agent_dir)
