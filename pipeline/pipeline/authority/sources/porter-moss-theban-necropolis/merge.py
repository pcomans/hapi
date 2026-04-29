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
# follow-up chunks introduce them. KV/QV/TT use the numbered-tomb-id form
# (`KV5`, `QV55`, `TT100`); `SWV` / `DAN` / `DEB` / `ASS` / `SAQN` / `RAM`
# etc. use the descriptor form `<PREFIX>-<Descriptor>` (chunk 7 introduced
# the descriptor convention — PM has no tomb-numbering for non-KV/QV Theban
# or Memphite sections). Descriptor IDs sort alphabetically within their
# valley rank. The prefix vocabulary below matches the test regex at
# `tests/test_sources_porter_moss_theban_necropolis.py::_TOMB_ID_RE`;
# `test_prefix_vocabulary_consistent` enforces that equality mechanically.
# Future chunks extend both structures together when they land.
VALLEY_ORDER: dict[str, int] = {
    "KV": 0,    # Valley of the Kings (PM I.2 § I)
    "QV": 1,    # Valley of the Queens (PM I.2 § X)
    "TT": 2,    # Theban Tomb — numbered private tombs (PM I.1)
    "SWV": 3,   # South-West Valleys (PM I.2 § II) — descriptor IDs
    "DAN": 4,   # Dra' Abu el-Naga (PM I.2 § III) — descriptor IDs
    # Future chunks extend this dict AS THEY LAND their first row; the
    # retrospective code-review on PR #100 flagged pre-registered prefixes
    # as speculative generality. `tests/…::test_prefix_vocabulary_consistent`
    # pins this dict against the test regex so the two stay in sync.
}

# Sentinel ranks for unrecognised prefixes / malformed IDs — they sort to
# the end so committed reconciled.jsonl stays correctly ordered for the
# known prefixes even when a malformed ID slips through (the duplicate
# detection in `_load` catches the malformed ID separately).
UNRECOGNISED_VALLEY_RANK = 9999
MALFORMED_TOMB_RANK = 999_999


# Numbered-tomb form: `KV5`, `QV55a`, `TT100`, etc.
_TOMB_NUM_RE = re.compile(r"^(?P<prefix>[A-Z]+)(?P<num>\d+)(?P<suffix>[a-z]?)$")
# Descriptor-tomb form: `SWV-HatshepsutSouth`, `DAN-KamoseWadjkheperre`.
_TOMB_DESC_RE = re.compile(r"^(?P<prefix>[A-Z]+)-(?P<desc>[A-Za-z][A-Za-z0-9]*)$")


def _sort_key(tomb_id: str) -> tuple[int, int, str, str]:
    """Sort by (valley_rank, numeric_tomb_or_zero, descriptor_or_suffix, raw_id).

    Numbered IDs (`KV5`, `KV5a`) sort by prefix rank then numeric value then
    suffix. Descriptor IDs (`DAN-AntefSehertaui`) sort by prefix rank then
    alphabetically on the descriptor. Numbered and descriptor IDs with the
    same prefix cannot coexist by design (a prefix is either numbered or
    descriptor, fixed per the PM section's convention).
    """
    m = _TOMB_NUM_RE.match(tomb_id)
    if m:
        prefix = m.group("prefix")
        num = int(m.group("num"))
        suffix = m.group("suffix")
        rank = VALLEY_ORDER.get(prefix, UNRECOGNISED_VALLEY_RANK)
        return (rank, num, suffix, tomb_id)
    m = _TOMB_DESC_RE.match(tomb_id)
    if m:
        prefix = m.group("prefix")
        desc = m.group("desc")
        rank = VALLEY_ORDER.get(prefix, UNRECOGNISED_VALLEY_RANK)
        # Descriptor rows all share numeric-slot 0 and sort by descriptor.
        return (rank, 0, desc, tomb_id)
    return (UNRECOGNISED_VALLEY_RANK, MALFORMED_TOMB_RANK, "", tomb_id)


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


SENTINEL_NULL_STRINGS = frozenset({"none", "-", "—", "n/a", "na", "unknown", "null"})


# === TIE_BREAK_OVERRIDES =====================================================
#
# Authoritative resolutions for (tomb_id, field) tuples where the three
# extraction agents tie (1/1/1 across three agents, or 1/1 when one agent
# missed a row). Loaded from ``tie-break-overrides.json`` (alongside this
# file). Each entry's key is ``"<tomb_id>|<field>"`` (JSON keys must be
# strings; the loader splits back to a tuple). Each value is
# ``{"value": ..., "rationale": "..."}``.
#
# ``rationale`` MUST cite the source page (Porter & Moss I.2 printed page or
# physical PDF page) and the basis for the resolution.
#
# When ``_majority`` hits a tie with no override, it RAISES — option (a)
# enforcement: data is sacred, fail loudly. The merge is broken until every
# uncovered tie has an entry here. This is intentional. Mirrors the
# Beckerath PR #146 / Leprohon PR #128 canonical pattern.
_OVERRIDES_PATH = SOURCE_DIR / "tie-break-overrides.json"


def _load_overrides() -> dict[tuple[str, str], dict[str, object]]:
    if not _OVERRIDES_PATH.exists():
        return {}
    raw = json.loads(_OVERRIDES_PATH.read_text(encoding="utf-8"))
    out: dict[tuple[str, str], dict[str, object]] = {}
    for k, v in raw.items():
        if "|" not in k:
            raise ValueError(
                f"merge.py: {_OVERRIDES_PATH} key {k!r} missing '|' "
                f"separator (expected '<tomb_id>|<field>')"
            )
        tid, field = k.split("|", 1)
        if not tid or not field:
            raise ValueError(
                f"merge.py: {_OVERRIDES_PATH} key {k!r} has empty tomb_id or field "
                f"after splitting on '|' (expected '<tomb_id>|<field>' "
                f"with both halves non-empty)"
            )
        out[(tid, field)] = v
    return out


TIE_BREAK_OVERRIDES: dict[tuple[str, str], dict[str, object]] = _load_overrides()


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


def _deep_normalise(v: object) -> object:
    """Recursively apply sentinel-null normalisation across dicts and lists.

    PM rows have a `source_citation` dict and `occupant_alt_names` /
    `shared_with_tombs` list fields. Per-field majority comparing whole
    list/dict objects must normalise children too — e.g. an agent emitting
    `{"page": "-"}` vs `{"page": null}` for the same source citation must
    not register as a tie.
    """
    if isinstance(v, list):
        return [_deep_normalise(item) for item in v]
    if isinstance(v, dict):
        return {k: _deep_normalise(val) for k, val in v.items()}
    return _normalise_value(v)


def _normalise_for_merge(row: dict) -> dict:
    """Apply pre-merge canonicalisations that should NOT be silent first-seen-
    pick at vote time. Currently a stub — PM has no encoding-style
    normalisation candidates analogous to Leprohon's MdC → IFAO map (no
    `transliteration` sub-fields in the PM canonical schema).

    Extension point. If a future re-extraction surfaces spurious ties from
    encoding-style differences (e.g. diacritic variance on Greek occupant
    names, hyphen-vs-en-dash in date ranges), normalise them here BEFORE
    the per-field counter sees the values, so the override table doesn't
    accumulate entries that are pure encoding-diffs rather than real
    scholarly disagreements.

    Returns a new dict; does not mutate the input.
    """
    if not isinstance(row, dict):
        return row
    return dict(row)


def _majority(values: list, *, tid: str, field: str) -> tuple[object, int]:
    """Return (chosen_value, count_of_agreers) from a list of per-agent values.

    Values are deep-normalised first so that sentinel nulls in nested dicts
    or lists do not force spurious disagreements. JSON serialisation with
    sorted keys is the equality key — handles nested dicts (`source_citation`)
    and list fields (`occupant_alt_names`, `shared_with_tombs`) correctly
    by value.

    Tie handling (option (a) enforcement, issue #145):
      - Clear majority (top count > second count): use it.
      - Tie at the top (top count == second count):
          1. Look up ``(tid, field)`` in TIE_BREAK_OVERRIDES → use override.
          2. Otherwise → raise. Data is sacred. Fail loudly.

    PM's flat-scalar schema (with two list fields and one dict field) is
    treated as IDENTIFIER throughout — no `_classify_tie` / `_resolve_prose
    _tie` step like Leprohon's nested name-list schema needs. The omission
    is INTENTIONAL: PM does not have name-list-of-dicts where a sub-field
    classifier (transliteration vs source_note) makes sense. PM's
    `notes_from_pm` is a short verbatim cell-text scalar; resolving it
    deterministically by "longest wins" or similar would be a heuristic
    without scholarly grounding (constitutional rule 6 distinguishes
    "deterministic-with-documented-policy" from "heuristic that mostly
    works"). Same rationale applies to the list fields `occupant_alt_names`
    and `shared_with_tombs` — a "union all agents' citations" policy could
    be argued for as additive, but per `feedback_egyptologist_diff_requires
    _printed_source.md` the egyptologist already validates these against
    the printed PDF; an automatic union risks burying agent hallucinations
    that the printed-source diff would catch. So tied list fields go
    through the override path with a citation just like scalars.

    Mirrors the Beckerath PR #146 design choice (advisor-validated for
    that PR; same shape applies here). If a future schema addition has
    nested name-list-of-dicts, this is the function to extend with a
    Leprohon-style classifier.

    `tid` and `field` are keyword-only required arguments. Constitutional
    rule 10 (no backwards compatibility): no Optional fallback, no silent
    first-seen path for "legacy callers".
    """
    normalised = [_deep_normalise(v) for v in values]

    def key(v: object) -> str:
        return json.dumps(v, ensure_ascii=False, sort_keys=True)

    counts = Counter(key(v) for v in normalised)
    most = counts.most_common()
    top_key, top_count = most[0]

    # Detect tie at the top. If only one distinct value (unanimous) or the
    # second distinct value has strictly fewer counts, no tie.
    is_tie = len(most) >= 2 and most[0][1] == most[1][1]

    if not is_tie:
        for v in normalised:
            if key(v) == top_key:
                return v, top_count
        raise RuntimeError(
            f"_majority loop failed to find top_key {top_key!r} in {normalised!r}"
        )

    # ---- Tie path. ----

    # 1. Explicit override.
    override = TIE_BREAK_OVERRIDES.get((tid, field))
    if override is not None:
        return override["value"], top_count

    # 2. Tie with no override → raise. Build a diagnostic that names every
    # distinct value so the agent adding the override has the candidates
    # in front of it.
    candidates = [
        f"  candidate {i+1} (count={cnt}): {k}"
        for i, (k, cnt) in enumerate(most)
    ]
    raise ValueError(
        f"Unresolved IDENTIFIER tie at ({tid!r}, {field!r}). "
        f"Add an entry to tie-break-overrides.json (key '{tid}|{field}') "
        f"with a cited rationale, or extend the agents' extractions until "
        f"a majority emerges. Candidates:\n" + "\n".join(candidates)
    )


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
            # 3-agent majority-vote safety model requires ≥2 agents to
            # corroborate a row (issue #114). The earlier "fall through to
            # _majority for sentinel-null normalisation" rationale doesn't
            # justify admitting unverified data — a hallucinated tomb_id
            # gets through with no corroboration. Loud failure per rule 2.
            only_tag = present[0][0] if present else "(none)"
            raise ValueError(
                f"merge.py: row {tid!r} appears in only {len(present)}/3 "
                f"agents (agent {only_tag!r}). Re-run extraction agent(s) "
                f"that missed this row, or hand-resolve before merging."
            )

        # Apply pre-merge canonicalisations (currently a stub for PM;
        # see _normalise_for_merge docstring).
        present = [(t, _normalise_for_merge(v)) for t, v in present]

        # Sort field iteration so the disagreement report is deterministic
        # across re-runs (issue #142 — same incidental fix as Beckerath PR #146).
        all_fields = sorted(set().union(*[v.keys() for _, v in present]))
        merged: dict = {}
        row_disagreements: list[str] = []
        for field in all_fields:
            values = [v.get(field) for _, v in present]
            chosen, count = _majority(values, tid=tid, field=field)
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
