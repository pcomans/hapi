"""Merge independent Claude Code subagent extractions into reconciled.jsonl.

Leprohon 2013, *The Great Name: Ancient Egyptian Royal Titulary*. Structure
cloned from the Ryholt / Kitchen / Dodson-Hilton lineage. Adaptations:

- **Primary key: `leprohon_id`** (e.g. `"leprohon-0.01"` for the first king
  of Dyn 0, `"leprohon-2.08"` for Khasekhem/Khasekhemwy). Leprohon entries
  are keyed on (dynasty, in-chapter-section sequence) — see README.md
  "Schema / Field semantics".
- **Multi-chunk support.** Each chunk (Early Dynastic = chunk 1, Old
  Kingdom = chunk 2, …) lands its three agents' extractions under `raw/`.
  Chunk 1 uses the playbook's default unsuffixed `agent-{tag}.jsonl`
  filenames; chunks 2+ will use `agent-{tag}-<chunk-suffix>.jsonl`. The
  `_load_agent_chunks` helper unions rows across all chunk files for a
  given tag, raising on duplicate `leprohon_id` across chunks — a
  collision would mean two chunks claimed the same king, which is an
  extraction bug.
- **Deep-structure fields** — unlike Ryholt/Kitchen/D&H where every
  schema field is a scalar (int, str, bool), Leprohon's schema has
  nested lists of name-entry dicts under `horus_names`, `nebty_names`,
  etc. `_majority` uses JSON serialisation as its equality key, which
  handles dicts/lists correctly by value (not identity). The
  disagreement report prints the full JSON of each agent's version of
  a field when they diverge — large but auditable.
- `DEFAULT_AGENT_DIR` is `<source_dir>/raw/` per the Phase-0 playbook
  (sandbox-writable cross-subagent path).
- `SENTINEL_NULL_STRINGS` retained from Kitchen/Ryholt — Leprohon
  occasionally uses `-` or similar for missing name-type entries, and
  agents may transcribe those literally.

See `docs/playbook-phase-0-ocr-transcription.md` § "Multi-chunk source
pattern" for the shared design.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/leprohon-2013-titulary/merge.py
    LEPROHON_AGENT_DIR=/some/path uv run python \\
        pipeline/authority/sources/leprohon-2013-titulary/merge.py

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


def _load(p: Path) -> dict[str, dict]:
    """Load a single agent's JSONL. Raises on duplicate `leprohon_id` in-file."""
    rows: dict[str, dict] = {}
    seen_line: dict[str, int] = {}
    for line_no, line in enumerate(p.read_text().splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        r = json.loads(s)
        lid = r["leprohon_id"]
        if lid in rows:
            raise ValueError(
                f"Duplicate leprohon_id {lid!r} in {p} "
                f"(first seen on line {seen_line[lid]}, again on line {line_no})"
            )
        rows[lid] = r
        seen_line[lid] = line_no
    return rows


def _load_agent_chunks(agent_dir: Path, tag: str) -> dict[str, dict]:
    """Load every chunk file for one agent tag, union rows across chunks.

    Matches both the unsuffixed `agent-{tag}.jsonl` (chunk-1 convention) and
    suffixed `agent-{tag}-<chunk>.jsonl` (chunks 2+). Raises on any
    `leprohon_id` collision across chunk files — IDs are meant to be
    globally unique, so a collision is an extraction bug.
    """
    base = agent_dir / f"agent-{tag}.jsonl"
    chunked = sorted(agent_dir.glob(f"agent-{tag}-*.jsonl"))
    files = ([base] if base.exists() else []) + chunked
    if not files:
        return {}
    combined: dict[str, dict] = {}
    source_of: dict[str, Path] = {}
    for p in files:
        rows = _load(p)
        for lid, row in rows.items():
            if lid in combined:
                raise ValueError(
                    f"Duplicate leprohon_id {lid!r} across chunk files: "
                    f"first in {source_of[lid]}, again in {p}"
                )
            combined[lid] = row
            source_of[lid] = p
    return combined


SENTINEL_NULL_STRINGS = frozenset({"none", "-", "—", "n/a", "na", "unknown", "null"})


def _normalise_value(v: object) -> object:
    """Collapse sentinel strings that mean 'null' into actual None.

    Applies only to scalar string values. Nested lists / dicts pass through
    unchanged — the sentinel normalisation runs recursively via
    `_deep_normalise` on dict/list values so that e.g. a name-entry with
    `"source_note": "-"` gets its source_note normalised to `None`.
    """
    if isinstance(v, str):
        stripped = v.strip().lower()
        if stripped in SENTINEL_NULL_STRINGS:
            return None
    return v


def _deep_normalise(v: object) -> object:
    """Recursively apply sentinel-null normalisation across dicts and lists.

    Leprohon's schema has nested name-entry dicts inside top-level lists
    (`horus_names`, `nebty_names`, …). A per-field majority vote on such a
    list compares entire list-of-dicts objects; without deep normalisation,
    two agents that differ only on `"source_note": "-"` vs `"source_note":
    null` would disagree on the whole list even though the semantic content
    matches.
    """
    if isinstance(v, list):
        return [_deep_normalise(item) for item in v]
    if isinstance(v, dict):
        return {k: _deep_normalise(val) for k, val in v.items()}
    return _normalise_value(v)


def _majority(values: list) -> tuple[object, int]:
    """Return (chosen_value, count_of_agreers) from a list of per-agent values.

    Values are deep-normalised first so that sentinel nulls in nested dicts
    do not force spurious disagreements. JSON serialisation with sorted keys
    is the equality key — handles nested dicts/lists correctly by value.
    """
    normalised = [_deep_normalise(v) for v in values]

    def key(v: object) -> str:
        return json.dumps(v, ensure_ascii=False, sort_keys=True)

    counts = Counter(key(v) for v in normalised)
    top_key, top_count = counts.most_common(1)[0]
    for v in normalised:
        if key(v) == top_key:
            return v, top_count
    return None, 0


# leprohon_id is `leprohon-{dynasty_group}.{NN}` where dynasty_group is one of:
# - a plain integer (`0`, `3`, `18`) — standard dynasty
# - an integer + single lowercase-letter suffix (`2a`, `3a`, `8a`, `11a`) —
#   Leprohon sub-dynasty section
# - a hyphenated range + suffix (`9-10a`, `9-10b`) — Leprohon's combined
#   labels for dynasties he considers inseparable (introduced in chapter IV
#   FIP where he bundles Dynasties 9 and 10 into groups a/b)
#
# NN is a zero-padded 2-digit sequence, optionally followed by a single
# lowercase letter (`5a`, `1b`, `10b`) that marks a *titulary stage* — same
# king adopted successive sets of names during his reign (Mentuhotep II's
# a/b/c stages, Amenemhat I's a/b pre/post-Itj-tawy-move, Amenhotep IV/
# Akhenaten's name-change years in NK). Stages are emitted as SEPARATE
# rows per stage because each stage has its own full cross-name-type
# titulary (Horus, Nebty, Throne, etc.) and the cross-name-type correlation
# ("in stage b, Throne is X AND Nebty is Y") would be lost if stages were
# collapsed into per-name-list variant entries.
#
# Sort order: the LOWER integer of the dynasty group ascending, then the
# hyphenated-range indicator (plain `9` sorts before `9-10`), then
# dynasty-suffix ascending (empty before `a`), then sequence-NUMBER
# ascending, then stage-suffix ascending (empty before `a`). This keeps
# `leprohon-3.01` between `leprohon-2a.02` and `leprohon-3a.01`,
# `leprohon-9-10a.NN` between `leprohon-8a.08` and `leprohon-11a.01`, and
# `leprohon-11b.05a < 5b < 5c < 6` inside Dyn 11b.
_LID_RE = re.compile(
    r"^leprohon-"
    r"(?P<dynasty_num>\d+)"
    r"(?:-(?P<dynasty_num_end>\d+))?"
    r"(?P<dynasty_suffix>[a-z]?)"
    r"\.(?P<seq>\d{2})"
    r"(?P<stage_suffix>[a-z]?)$"
)


def _sort_key(lid: str) -> tuple[int, int, str, int, str, str]:
    match = _LID_RE.match(lid)
    if match is None:
        return (9999, 9999, "", 9999, "", lid)
    dynasty_num = int(match.group("dynasty_num"))
    # `is_range` tiebreaker: plain `9` sorts before `9-10` because the plain
    # form is conceptually "Dynasty 9 standalone", the ranged form is a
    # grouped label Leprohon uses when he can't cleanly separate the two.
    is_range = 1 if match.group("dynasty_num_end") else 0
    return (
        dynasty_num,
        is_range,
        match.group("dynasty_suffix"),
        int(match.group("seq")),
        match.group("stage_suffix"),
        lid,
    )


def main(agent_dir: Path) -> None:
    agents = {tag: _load_agent_chunks(agent_dir, tag) for tag in "abc"}
    empty = [tag for tag, rows in agents.items() if not rows]
    if empty:
        sys.exit(
            f"ERROR: no agent output found for tags: {', '.join(empty)}\n"
            f"Expected agent-{'{a,b,c}'}.jsonl or agent-{'{a,b,c}'}-<chunk>.jsonl "
            f"under {agent_dir}. See transcribe.md."
        )

    all_ids = sorted(
        set().union(*[a.keys() for a in agents.values()]),
        key=_sort_key,
    )

    final: list[dict] = []
    report: list[str] = []

    for lid in all_ids:
        versions = [(tag, agents[tag].get(lid)) for tag in "abc"]
        present = [(t, v) for t, v in versions if v is not None]
        if len(present) < 2:
            final.append(present[0][1])
            report.append(
                f"{lid}: only {len(present)}/3 agents found this entry (kept it).\n"
            )
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
                    f"  {field}:\n"
                    + "\n".join(
                        f"    {t}: {json.dumps(v.get(field), ensure_ascii=False, sort_keys=True)}"
                        for t, v in present
                    )
                    + f"\n    → chose: {json.dumps(chosen, ensure_ascii=False, sort_keys=True)}"
                )
        if row_disagreements:
            report.append(
                f"{lid} ({merged.get('display_name', '?')}):\n"
                + "\n".join(row_disagreements)
                + "\n"
            )
        final.append(merged)

    # Deterministic JSONL output: sort keys so re-runs do not shuffle the file
    # (playbook step 10, "Deterministic JSONL output"). json.dumps sort_keys
    # handles both top-level dict keys and nested-dict keys.
    OUT.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in final)
        + "\n"
    )
    DIFF.write_text(
        "\n".join(report) if report else "No field-level disagreements.\n"
    )

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
        default=Path(os.environ.get("LEPROHON_AGENT_DIR", DEFAULT_AGENT_DIR)),
        help=f"Directory containing agent-{{a,b,c}}(-<chunk>).jsonl files "
        f"(default: {DEFAULT_AGENT_DIR}).",
    )
    args = parser.parse_args()
    main(args.agent_dir)
