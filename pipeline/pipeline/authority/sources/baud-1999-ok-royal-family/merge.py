"""Merge independent Claude Code subagent extractions into reconciled.jsonl.

Baud 1999 — Famille royale et pouvoir sous l'Ancien Empire égyptien.
Structure cloned from Dodson-Hilton / Kitchen. Adaptations:

- `dh_id` → `baud_id` throughout. Baud's `[N]` corpus numbers are zero-padded
  to 3 digits (`"001"` … `"282"`) in the extracted rows so string sort
  matches numeric sort.
- **Plain `baud_id` primary key** (NOT composite). Baud's corpus numbers
  are globally unique across entries `[1]` – `[282]`; there is no
  cross-section re-use (there are no cross-sections — the corpus is a
  single alphabetical sequence). Cross-reference stubs (e.g. `[9]`)
  carry their own `baud_id` and a `redirect_to` pointer; they are not
  duplicates.
- `_sort_key` is numeric on `baud_id` (string sort works because IDs
  are zero-padded). Redirect rows sort in-line with their own ID, not
  at the end.
- `DEFAULT_AGENT_DIR` is `<source_dir>/raw/` — the sandbox-writable
  path per the Phase-0 playbook.
- `SENTINEL_NULL_STRINGS` extended with French-style sentinels
  `"inconnue"` / `"inconnu"` in addition to the standard set, because
  Baud's PARENTÉ prose uses those words as an explicit "no data"
  assertion rather than a name.
- **Multi-chunk support.** Each chunk (chunk1 pp.19–40, chunk2
  pp.41–70, …) lands its three agents' extractions as
  `agent-{a,b,c}-<chunk>.jsonl`. Per-tag rows are collected across
  all matching `agent-{tag}-*.jsonl` files under `agent_dir`; `_load`
  raises on duplicate `baud_id` within a single file AND across
  chunk files.

See Dodson-Hilton's merge.py and
`docs/playbook-phase-0-ocr-transcription.md` for rationale.

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

BAUD_ID_PATTERN = re.compile(r"^\d{3}$")


def _load(p: Path) -> dict[str, dict]:
    """Load a single agent's JSONL. Raises on duplicate `baud_id` or malformed ID."""
    rows: dict[str, dict] = {}
    seen_line: dict[str, int] = {}
    for line_no, line in enumerate(p.read_text().splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        r = json.loads(s)
        baud_id = r["baud_id"]
        if not BAUD_ID_PATTERN.match(baud_id):
            raise ValueError(
                f"Malformed baud_id={baud_id!r} in {p} line {line_no}: "
                f"expected three-digit zero-padded corpus number."
            )
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

    Matches `agent-{tag}-<chunk>.jsonl` (e.g. `agent-a-chunk1.jsonl`,
    future `agent-a-chunk2.jsonl`). Every agent output carries a
    chunk suffix — Baud lands multi-chunk from day one, there is no
    unsuffixed legacy form.

    Raises on duplicate `baud_id` across chunk files — Baud's `[N]`
    numbers are globally unique, so a collision means an extraction
    bug in whichever chunk misplaced the row.
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


SENTINEL_NULL_STRINGS = frozenset(
    {"none", "-", "—", "n/a", "na", "unknown", "inconnue", "inconnu"}
)


def _normalise_value(v: object) -> object:
    """Collapse sentinel strings that mean 'null' into actual None.

    French `"Inconnue"` / `"Inconnu"` in a `father_name` / `mother_name`
    field maps to null (Baud's explicit "no data" assertion). Hedged
    strings like `"Snéfrou (probable)"` or bracketed lacuna markers
    like `"[ḥr?]"` are NOT sentinel-null — they are authorial positive
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


def _sort_key(baud_id: str) -> str:
    """Sort-key is the zero-padded ID itself — lexicographic sort matches
    numeric sort because extraction pads to 3 digits. A redirect row
    sorts alongside its own ID (not at the tail) so the `reconciled.jsonl`
    order matches Baud's own corpus ordering."""
    return baud_id


def main(agent_dir: Path) -> None:
    agents = {tag: _load_agent_chunks(agent_dir, tag) for tag in "abc"}
    empty = [tag for tag, a in agents.items() if not a]
    if empty:
        sys.exit(
            f"ERROR: agent(s) {', '.join(empty)} produced no rows in {agent_dir}. "
            f"Expected at least one `agent-{{tag}}-<chunk>.jsonl` per agent. "
            f"See transcribe.md."
        )

    all_ids = sorted(set().union(*[a.keys() for a in agents.values()]), key=_sort_key)

    final: list[dict] = []
    report: list[str] = []

    for baud_id in all_ids:
        versions = [(tag, agents[tag].get(baud_id)) for tag in "abc"]
        present = [(t, v) for t, v in versions if v is not None]
        if len(present) < 2:
            final.append(present[0][1])
            report.append(f"{baud_id}: only 1/3 agents found this entry (kept it).\n")
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
                f"{baud_id} ({merged.get('name', '?')}):\n"
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
        help=f"Directory containing agent-{{a,b,c}}-<chunk>.jsonl (default: {DEFAULT_AGENT_DIR}).",
    )
    args = parser.parse_args()
    main(args.agent_dir)
