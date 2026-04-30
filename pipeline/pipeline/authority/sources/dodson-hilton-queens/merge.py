"""Merge independent Claude Code subagent extractions into reconciled.jsonl.

Dodson & Hilton 2004 Brief Lives. Structure cloned from Kitchen (Ryholt
lineage). Adaptations:

- `kitchen_id` → `dh_id` throughout.
- **Composite primary key `(dh_id, sub_period)`.** D&H occasionally lists
  the same individual under two Brief Lives sub-sections when their
  family role spans both (e.g. `Takhat A` appears in "The House of
  Ramesses" as a daughter of Ramesses II and again in "The Feud of
  the Ramessides" as the wife of Sety II, each entry contributing
  distinct prose and role codes). Keying on `dh_id` alone would
  collapse such entries; keying on the composite preserves D&H's
  authorial choice. Phase A reconciles to one individual downstream.
  Chunks 1 and 2 continue to work unchanged — their `dh_id`s were
  already globally unique, so the composite key reduces to the old
  behaviour for them.
- `_sort_key` alphabetical by `dh_id` (D&H's own Brief Lives ordering);
  rows where `unplaced=True` sort after the main alphabetical run;
  names with leading `[` / `–` (lacunae) sort last; `sub_period` acts
  as a final tiebreaker so composite-key duplicates land adjacently.
- `DEFAULT_AGENT_DIR` is `<source_dir>/raw/` — the sandbox-writable path
  per the Phase-0 playbook.
- `SENTINEL_NULL_STRINGS` unchanged from Kitchen.
- **Multi-chunk support.** Each chunk (Pre-Amarna p126–p130, Amarna
  p142–p145, Ramesside p157–p162/p169–p170/p178–p180, ...) lands its
  three agents' extractions as `agent-{a,b,c}-<chunk>.jsonl`. Per-tag
  rows are collected across all matching `agent-{tag}-*.jsonl` files
  under `agent_dir`; `_load` raises on duplicate `(dh_id, sub_period)`
  within a single file AND across chunk files.

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


RowKey = tuple[str, str]  # (dh_id, sub_period)


def _row_key(r: dict) -> RowKey:
    return (r["dh_id"], r["sub_period"])


def _load(p: Path) -> dict[RowKey, dict]:
    """Load a single agent's JSONL. Raises on duplicate (dh_id, sub_period)."""
    rows: dict[RowKey, dict] = {}
    seen_line: dict[RowKey, int] = {}
    for line_no, line in enumerate(p.read_text().splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        r = json.loads(s)
        key = _row_key(r)
        if key in rows:
            raise ValueError(
                f"Duplicate (dh_id, sub_period)={key!r} in {p} "
                f"(first seen on line {seen_line[key]}, again on line {line_no})"
            )
        rows[key] = r
        seen_line[key] = line_no
    return rows


def _load_agent_chunks(agent_dir: Path, tag: str) -> dict[RowKey, dict]:
    """Load every chunk file for one agent tag, union the rows across chunks.

    Matches `agent-{tag}-<chunk>.jsonl` (e.g. `agent-a-power.jsonl`,
    `agent-a-amarna.jsonl`, `agent-a-ramesside.jsonl`). Every agent
    output must carry a chunk suffix — the legacy unsuffixed
    `agent-{tag}.jsonl` form (used by Pre-Amarna before chunk 2)
    was retired in the Ramesside PR. PR #38 (Amarna) deferred the
    rename to reduce review surface-area; this PR collected it
    alongside the composite-key change.

    Raises on duplicate `(dh_id, sub_period)` across chunk files —
    a composite-key collision means two extractions produced the
    same logical row, so it's a bug. A `dh_id` that appears with
    distinct `sub_period`s is legitimate (D&H cross-section duplicates).
    """
    files = sorted(agent_dir.glob(f"agent-{tag}-*.jsonl"))
    if not files:
        return {}

    combined: dict[RowKey, dict] = {}
    source_of: dict[RowKey, Path] = {}
    for p in files:
        rows = _load(p)
        for key, row in rows.items():
            if key in combined:
                raise ValueError(
                    f"Duplicate (dh_id, sub_period)={key!r} across chunk files: "
                    f"first in {source_of[key]}, again in {p}"
                )
            combined[key] = row
            source_of[key] = p
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
    # Unreachable: top_key was generated from `normalised`, so the loop
    # above must find a match. Raise rather than return None silently.
    raise RuntimeError(f"_majority loop failed to find top_key {top_key!r} in {normalised!r}")


LACUNA_PREFIXES: tuple[str, ...] = ("[", "–")


def _sort_key_for(unplaced_keys: frozenset[RowKey]):
    """Return a sort-key function that bins rows by Unplaced-ness,
    then by lacuna-prefix (lacunae last within each bin), then by
    case-insensitive alphabetical order, with `sub_period` as a
    final tiebreaker for cross-section duplicates.

    Top-level bins:
    Bin 0: placed entries (D&H's main alphabetical Brief Lives list).
    Bin 1: unplaced entries (D&H's trailing `Unplaced` sub-section).
           Includes both `Q`-suffixed ids (Amenemhat Q, Henut Q,
           Thutmose Q) AND plain-name unplaced entries (Henutiunu,
           Sithori, Tatau, Ti, etc.) that D&H place under the Unplaced
           heading without a disambiguator.

    Secondary bin (applied inside each top-level bin):
    Sub-bin 0: names with letter-prefix first character.
    Sub-bin 1: lacuna-prefixed ids (names starting with `[` such as
           `[...]pentepkau`, `[...]18A–H` or with `–` such as `–18P`,
           `–18Q`). D&H groups these at the foot of the alphabetical
           run within the sub-section they belong to (they are
           tentative-identity entries whose names are only partially
           attested). Without the sub-bin, ASCII/Unicode default
           ordering puts `[` BEFORE every letter and `–` AFTER every
           letter, scattering lacunae across both ends of the output.
           This was the source of a review-flagged bug on PR #38 —
           before the fix, `[...]18A–H` / `[...]18J` / `[...]18K–N`
           appeared at the TOP of `reconciled.jsonl`.

    This arrangement keeps `[...]pentepkau` (Pre-Amarna, unplaced=True,
    lacuna) at the very end of the file — just after the other unplaced
    non-lacuna entries — and Amarna's 5 placed lacunae (`[...]18A–H`,
    `[...]18J`, `[...]18K–N`, `–18P`, `–18Q`) at the end of the placed
    block (just before the unplaced sub-section). Matches D&H's own
    layout in both chunks.

    Sort order cannot be determined from dh_id alone because `unplaced`
    is a per-row field, not a name-suffix convention — hence the closure
    over the unplaced-keys set computed from the merged rows.
    """
    def _sort_key(key: RowKey) -> tuple[int, int, str, str]:
        dh_id, sub_period = key
        top_bin = 1 if key in unplaced_keys else 0
        sub_bin = 1 if dh_id.startswith(LACUNA_PREFIXES) else 0
        return (top_bin, sub_bin, dh_id.lower(), sub_period)

    return _sort_key


def main(agent_dir: Path) -> None:
    agents = {tag: _load_agent_chunks(agent_dir, tag) for tag in "abc"}
    empty = [tag for tag, a in agents.items() if not a]
    if empty:
        sys.exit(
            f"ERROR: agent(s) {', '.join(empty)} produced no rows in {agent_dir}. "
            f"Expected at least one `agent-{{tag}}-<chunk>.jsonl` per agent. "
            f"See transcribe.md."
        )

    # Compute the set of unplaced composite keys once, by majority-vote of the
    # three agents' `unplaced` fields per row. This lets _sort_key_for() bin
    # the output correctly without making the sort-key function itself depend
    # on the per-row merge result (which is computed below).
    all_keys_unsorted = set().union(*[a.keys() for a in agents.values()])
    unplaced_keys: set[RowKey] = set()
    for key in all_keys_unsorted:
        votes = [a[key].get("unplaced", False) for a in agents.values() if key in a]
        if sum(1 for v in votes if v) > len(votes) / 2:
            unplaced_keys.add(key)

    all_keys = sorted(all_keys_unsorted, key=_sort_key_for(frozenset(unplaced_keys)))

    # A `dh_id` that occurs under more than one `sub_period` is a D&H
    # cross-section duplicate (e.g. Takhat A as daughter-of-Ramesses-II in
    # House of Ramesses AND as wife-of-Sety-II in Feud of the Ramessides).
    # Disambiguate those in the report; leave the common case bare.
    dh_id_counts = Counter(dh for dh, _ in all_keys_unsorted)
    duplicated_dh_ids = {dh for dh, n in dh_id_counts.items() if n > 1}

    # Schema uniformity: every row in reconciled.jsonl must carry every
    # field that ANY agent produced on ANY row, and the per-row field
    # iteration must be sorted so `merge-disagreements.txt` is byte-stable
    # across runs. The old `set().union(*[v.keys() for _, v in present])`
    # pattern (computed inside the row loop, unsorted) had two failure
    # modes — it let a field that one agent omitted on one row vanish
    # from the merged output for that row, and it iterated set-order so
    # the audit log diffed noisily on every regenerate. Computing the
    # field set once across the full agent output and sorting it closes
    # both. Mirrors the Baud / Kitchen / Beckerath / etc. shape.
    all_fields = sorted(
        set().union(*[set(row.keys()) for a in agents.values() for row in a.values()])
    )

    final: list[dict] = []
    report: list[str] = []

    for key in all_keys:
        dh_id, sub_period = key
        label = f"{dh_id} [{sub_period}]" if dh_id in duplicated_dh_ids else dh_id
        versions = [(tag, agents[tag].get(key)) for tag in "abc"]
        present = [(t, v) for t, v in versions if v is not None]
        if len(present) < 2:
            # 3-agent majority-vote safety model requires ≥2 agents to
            # corroborate a row (issue #114). Loud failure per rule 2.
            only_tag = present[0][0] if present else "(none)"
            raise ValueError(
                f"merge.py: row {label!r} appears in only {len(present)}/3 "
                f"agents (agent {only_tag!r}). Re-run extraction agent(s) "
                f"that missed this row, or hand-resolve before merging."
            )

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
                f"{label} ({merged.get('name', '?')}):\n"
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
