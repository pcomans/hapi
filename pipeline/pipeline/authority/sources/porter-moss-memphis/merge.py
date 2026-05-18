"""Merge three independent Claude Code subagent extractions into reconciled.jsonl.

Porter-Moss Vol III (Memphis) is a multi-chunk source — chunk 1 is the three
Gîza pyramid complexes (Khufu / Khephren / Menkaureʿ) and their attested
queens' subsidiary pyramids from PM III.1 § I "PYRAMIDS". Future chunks land
the Gîza Necropolis cemeteries (G 1000–G 7000), then PM III.2 Saqqâra pyramid
complexes and mastabas. Cloned from `porter-moss-theban-necropolis/merge.py`
(post-PR-#196 canonical) with three adaptations:

1. `_TOMB_NUM_RE` accepts the Reisner G-prefix shape (`G1`, `G1a`, `G2a`,
   `G3c`) for Gîza pyramids and subsidiary pyramids. Other Memphite ID
   conventions (Mariette `D<n>`, Lepsius `LS<n>`, descriptor IDs for
   Saqqâra named features) extend the regex / `AREA_ORDER` dict as their
   first row lands.
2. `AREA_ORDER` orders by Memphite sub-area (Giza < Saqqara < Abusir < …).
3. The cross-chunk loader, sentinel-null normalisation, majority-vote, and
   disagreement-logging logic carry over verbatim — they are source-agnostic.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/porter-moss-memphis/merge.py
    PM_AGENT_DIR=/some/path uv run python \\
        pipeline/authority/sources/porter-moss-memphis/merge.py

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


# Memphite sub-area sort order. Lower rank sorts first. Add new prefixes /
# areas here as follow-up chunks introduce them. Chunk 1 only emits `G`
# (Reisner-numbered Gîza). PM III.2 chunks will introduce Saqqâra prefixes
# (Mariette `D`/`C`/`S`, Lepsius `LS`), Dahshûr letters, etc.
AREA_ORDER: dict[str, int] = {
    "G": 0,    # Reisner Gîza (G1, G1a, G2, G3, G7000X, etc.)
    "LG": 1,  # Lepsius Grab (LG 81, LG 83, LG 84, LG 97, LG 100, etc.) —
              # Saite + Old-Kingdom-Central-Field tombs from chunk 3.
              # Sorts AFTER Reisner G-numbered tombs within Gîza so the
              # reconciled.jsonl groups by prefix family then numeric.
    "SAQ": 2,  # Saqqâra descriptor-form (SAQ-Unis, SAQ-PepyI, SAQ-PepyII,
               # SAQ-Neit, SAQ-IputII, SAQ-Wezebten, etc.) — PM III.2 § I.
               # PYRAMIDS chunk 4. These pyramids lack a uniform Reisner-style
               # number scheme; Saqqâra-specific descriptor IDs synthesise
               # `SAQ-<KingOrQueenName>` from the section-heading royal name.
               # Sorts after both Reisner and Lepsius forms; pyramids are
               # Memphite but live in their own geographic sub-area.
    "JKR": 3,  # Junker (Cemetery West / Cemetery East) descriptor-form
               # (JKR-Irty, JKR-Sonb1, JKR-Inpuhotp, etc.) — PM III.1
               # § III.A West Field Junker-excavated NAMED mastabas
               # (chunk 10). PM gives no Reisner G-number for these
               # tombs; the headword IS the occupant's all-caps name.
               # Synthesise `JKR-<TitleCaseName>` from the headword.
    "S": 4,    # Steindorff S-numbers (S 4040, S 4399, S 4419, etc.) —
               # PM III.1 § III.A West Field Steindorff-excavated
               # tombs (chunk 10 + future Steindorff cemetery chunk).
               # PM prints `S <NUM>` or `S <NUM1>/<NUM2>` for twin-
               # numbered tombs.
    "STN": 5,  # Steindorff descriptor-form for the interstitial
               # named Steindorff Cemetery tombs that lack a
               # D-number (chunk 11). Parallel to JKR-/SAQ-
               # convention. Only ~3 rows per chunk-11 (WEMTETKA,
               # IBIR, etc.).
    "D": 6,    # Steindorff/Daressy D-numbers (D1, D4, D9, D14, D61,
               # D80A, etc.) — the PRIMARY identifier scheme for
               # the Steindorff Cemetery section of PM III.1 § III.A.
               # PM prints `D. <NUM>.` or `D. <NUM><letter>.` or
               # `D. <NUM1>/<NUM2>.`. Discovered via PR #229 / chunk-
               # 11 revise-priors finding: the chunk-10 attribution
               # of D-numbers as Mariette cross-references was wrong.
    "JKE": 7,  # Junker Cemetery (East) descriptor-form (JKE-Sensen,
               # JKE-Meruka, JKE-Iuf, etc.) — PM III.1 § III.A West
               # Field Junker-excavated NAMED mastabas of the EAST
               # banner (chunk 13). Parallel to chunk-10's JKR-
               # (Junker West) convention. Synthesise
               # `JKE-<TitleCaseName>` from the all-caps headword
               # since PM gives no Reisner G-number for these tombs.
    "EF": 8,   # East Field descriptor-form (EF-Kawehem, EF-Inkaf,
               # EF-Ither, EF-Neferka) — PM III.1 § III.B trailing
               # rock-cut named tombs without LG / Reisner numbers
               # (chunk 19). Parallel to JKR-/JKE-/STN- convention.
    "LS": 9,   # Lepsius Saqqara monument-list numbers (LS10 Kagemni
               # Memi, etc.) — PM III.2 § II.B AROUND TETI PYRAMID
               # opener (chunk 20). Parallel to LG (Lepsius Giza)
               # convention but routed to a distinct prefix because
               # the two numbering schemes are independent.
    "TPC": 10, # Teti Pyramid Cemetery descriptor-form (TPC-Khentka,
               # TPC-Kagemni, TPC-AnkhmaHor, etc.) — PM III.2 § II.B
               # AROUND TETI PYRAMID Old-Kingdom named mastabas
               # without LS numbers (chunk 20). Parallel to JKR- /
               # JKE- / STN- / EF- descriptor conventions.
    "SAQD": 11, # Petrie+Murray Saqqâra D-numbered mastabas (SAQD45 etc.)
                # — PM III.2 § II.C EAST OF THE STEP PYRAMID (chunk 23).
                # Distinct from chunk-11's `D<N>` for Steindorff Giza
                # cemetery (the same D-number prefix refers to a
                # completely different numbering scheme in Giza vs
                # Saqqâra; chunk-11's transcribe.md anticipated this
                # disambiguation requirement).
    "SAQF": 12, # Petrie+Murray Saqqâra F-numbered mastabas (SAQF1,
                # SAQF3) — same publication, parallel F-series.
    # NB: chunks 15 + 17 (Cemetery en Echelon South + G 7000 East Field
    # remainder) re-use Reisner G-numbers (G 4911-G 5560 + G 7152-G 7948)
    # so no new prefix is needed there. Chunks 16 (Cemetery G 6000) and
    # 18 (LG 63-80 East Field trailing) also use existing G / LG.
    # Future chunks extend this dict AS THEY LAND their first row;
    # `tests/…::test_prefix_vocabulary_consistent` pins this dict against the
    # test regex so the two stay in sync.
}

# Sentinel ranks for unrecognised prefixes / malformed IDs — they sort to
# the end so committed reconciled.jsonl stays correctly ordered for the
# known prefixes even when a malformed ID slips through.
UNRECOGNISED_AREA_RANK = 9999
MALFORMED_TOMB_RANK = 999_999


# Numbered-tomb form: `G1`, `G1a`, `G7000X`, etc.
# Prefix is one or more capitals; number is one or more digits; suffix is
# zero or one alphabetical character — lowercase letters for the typical
# subsidiary-pyramid form (`G1a`, `G3c`) and uppercase letter for Reisner's
# `G7000X` "extension" convention. `[a-zA-Z]?` is the consolidated form
# (Gemini PR #217 medium); the empty-string default keeps `_sort_key`'s
# tuple ordering deterministic.
_TOMB_NUM_RE = re.compile(r"^(?P<prefix>[A-Z]+)(?P<num>\d+)(?P<suffix>[a-zA-Z]?)$")
# Descriptor-tomb form: `GIZA-SphinxTemple`, `SAQ-PyramidUnas` — reserved
# for follow-up chunks where a named PM feature has no number.
_TOMB_DESC_RE = re.compile(r"^(?P<prefix>[A-Z]+)-(?P<desc>[A-Za-z][A-Za-z0-9]*)$")


def _sort_key(tomb_id: str) -> tuple[int, int, str, str]:
    """Sort by (area_rank, numeric_tomb_or_zero, descriptor_or_suffix, raw_id).

    Numbered IDs (`G1`, `G1a`) sort by prefix rank then numeric value then
    suffix. Descriptor IDs (future chunks) sort by prefix rank then
    alphabetically on the descriptor.
    """
    m = _TOMB_NUM_RE.match(tomb_id)
    if m:
        prefix = m.group("prefix")
        num = int(m.group("num"))
        suffix = m.group("suffix")
        rank = AREA_ORDER.get(prefix, UNRECOGNISED_AREA_RANK)
        return (rank, num, suffix, tomb_id)
    m = _TOMB_DESC_RE.match(tomb_id)
    if m:
        prefix = m.group("prefix")
        desc = m.group("desc")
        rank = AREA_ORDER.get(prefix, UNRECOGNISED_AREA_RANK)
        return (rank, 0, desc, tomb_id)
    return (UNRECOGNISED_AREA_RANK, MALFORMED_TOMB_RANK, "", tomb_id)


def _load(p: Path) -> dict[str, dict]:
    """Load a single agent's JSONL. Raises on duplicate tomb_id within a file."""
    rows: dict[str, dict] = {}
    seen_line: dict[str, int] = {}
    for line_no, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
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
    in exactly one chunk per the chunk plan in README.md.
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


# NOTE: "unknown" is intentionally NOT a sentinel-null string here. The PM
# Memphis schema treats "Unknown" as a valid controlled-vocab value for
# `occupant_role` (used for bare-headword Reisner-number rows where PM lists
# the Reisner-number with no occupant). Collapsing "Unknown" → None would
# drop legitimate role attributions and break the schema's enum contract.
# Diverges from the Theban-source merge.py here on purpose; if a real
# null-sentinel-string appears in a future chunk, add it to this frozenset
# without re-adding "unknown".
#
# DETERMINISTIC GUARDRAILS for this divergence:
#  - `tests/test_sources_porter_moss_memphis.py::test_chunk2_bare_headword_rows_are_unknown_and_uncertain`
#    pins the downstream behavioural contract on reconciled.jsonl.
#  - `tests/test_porter_moss_memphis_merge_tie_break.py::test_unknown_literal_survives_normalisation`
#    pins the upstream `_normalise_value` contract.
#  - `tests/test_porter_moss_memphis_merge_tie_break.py::test_case_mixed_unknown_does_not_silently_collapse`
#    pins the 2/1 and 1/1/1 case-mixed merge behaviour (Gemini PR #219
#    round-1 scope-accountability follow-up).
#  If a future chunk author re-adds "unknown" to this frozenset, all three
#  tests above fire — they are the loud-failure tripwire.
SENTINEL_NULL_STRINGS = frozenset({"none", "-", "—", "n/a", "na", "null"})


# === TIE_BREAK_OVERRIDES =====================================================
#
# Authoritative resolutions for (tomb_id, field) tuples where the three
# extraction agents tie (1/1/1 across three agents, or 1/1 when one agent
# missed a row). Loaded from ``tie-break-overrides.json`` (alongside this
# file). Each entry's key is ``"<tomb_id>|<field>"``. Each value is
# ``{"value": ..., "rationale": "..."}``.
#
# ``rationale`` MUST cite the source page (Porter & Moss III printed page or
# physical PDF page) and the basis for the resolution.
#
# When ``_majority`` hits a tie with no override, it RAISES. Mirrors the
# Beckerath PR #146 / Leprohon PR #128 / PM-Theban PR #196 canonical pattern.
_OVERRIDES_PATH = SOURCE_DIR / "tie-break-overrides.json"


def _load_overrides() -> dict[tuple[str, str], dict[str, object]]:
    if not _OVERRIDES_PATH.exists():
        return {}
    raw = json.loads(_OVERRIDES_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(
            f"merge.py: {_OVERRIDES_PATH} top-level JSON must be a dict; "
            f"got {type(raw).__name__}"
        )
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
        if not isinstance(v, dict):
            raise ValueError(
                f"merge.py: {_OVERRIDES_PATH} key {k!r} value must be a dict "
                f"with 'value' and 'rationale' keys; got {type(v).__name__}: {v!r}"
            )
        missing = {"value", "rationale"} - set(v.keys())
        if missing:
            raise ValueError(
                f"merge.py: {_OVERRIDES_PATH} key {k!r} value is missing "
                f"required key(s) {sorted(missing)} (expected dict with "
                f"'value' and 'rationale'); got: {v!r}"
            )
        out[(tid, field)] = v
    return out


TIE_BREAK_OVERRIDES: dict[tuple[str, str], dict[str, object]] = _load_overrides()


def _normalise_value(v: object) -> object:
    """Collapse sentinel strings that mean 'null' into actual None."""
    if isinstance(v, str):
        stripped = v.strip().lower()
        if stripped in SENTINEL_NULL_STRINGS:
            return None
    return v


def _deep_normalise(v: object) -> object:
    """Recursively apply sentinel-null normalisation across dicts and lists."""
    if isinstance(v, list):
        return [_deep_normalise(item) for item in v]
    if isinstance(v, dict):
        return {k: _deep_normalise(val) for k, val in v.items()}
    return _normalise_value(v)


def _normalise_for_merge(row: dict) -> dict:
    """Pre-merge canonicalisations that should NOT be silent first-seen-pick.

    Stub for PM Memphis — extension point if future chunks surface ties
    from encoding-style differences (e.g. PM-faithful ayin variants in
    `notes_from_pm`). Returns a new dict; does not mutate input.
    """
    if not isinstance(row, dict):
        return row
    return dict(row)


def _majority(values: list, *, tid: str, field: str) -> tuple[object, int]:
    """Return (chosen_value, count_of_agreers) from a list of per-agent values.

    Tie handling (option (a) enforcement, issue #145):
      - Clear majority (top count > second count): use it.
      - Tie at the top: TIE_BREAK_OVERRIDES lookup → else raise.
    """
    normalised = [_deep_normalise(v) for v in values]

    def key(v: object) -> str:
        return json.dumps(v, ensure_ascii=False, sort_keys=True)

    counts = Counter(key(v) for v in normalised)
    most = counts.most_common()
    top_key, top_count = most[0]

    is_tie = len(most) >= 2 and most[0][1] == most[1][1]

    if not is_tie:
        for v in normalised:
            if key(v) == top_key:
                return v, top_count
        raise RuntimeError(
            f"_majority loop failed to find top_key {top_key!r} in {normalised!r}"
        )

    override = TIE_BREAK_OVERRIDES.get((tid, field))
    if override is not None:
        return _deep_normalise(override["value"]), top_count

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
            only_tag = present[0][0] if present else "(none)"
            raise ValueError(
                f"merge.py: row {tid!r} appears in only {len(present)}/3 "
                f"agents (agent {only_tag!r}). Re-run extraction agent(s) "
                f"that missed this row, or hand-resolve before merging."
            )

        present = [(t, _normalise_for_merge(v)) for t, v in present]

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
        + "\n",
        encoding="utf-8",
    )
    DIFF.write_text(
        "\n".join(report) if report else "No field-level disagreements.\n",
        encoding="utf-8",
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
        default=Path(os.environ.get("PM_AGENT_DIR", DEFAULT_AGENT_DIR)),
        help=f"Directory containing agent-a/b/c.jsonl (default: {DEFAULT_AGENT_DIR}).",
    )
    args = parser.parse_args()
    main(args.agent_dir)
