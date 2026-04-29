"""Merge three independent Claude Code subagent extractions into reconciled.jsonl.

Ryholt's catalogue has many edge cases (bold vs plain Appellation headers,
letter-only file suffixes, lacuna markers, two Chronological-Table layouts,
kings listed with disambiguators like "Sewadjkare (I)"), and a deterministic
regex parser quickly accumulates brittle special cases. Instead, the
extraction is performed by running three independent Claude Code subagents
in parallel, each reading the same OCR chunks and emitting JSONL per the
Ryholt schema. This script deterministically merges those three outputs:

  1. Group rows by `ryholt_id`.
  2. For each field in each row, majority-vote across the three agents.
  3. Write the merged rows to `reconciled.jsonl`.
  4. Write the field-level disagreement report to `merge-disagreements.txt`
     for downstream review (LLM reviewer pass first, then eventually
     an actual scholar — see ADR-017 step 6).

The extraction step is non-deterministic (LLM output); the merge step IS
deterministic. The committed `reconciled.jsonl` is the source of truth;
anyone can re-run the 3-agent extraction and diff.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/ryholt-1997-sip/merge.py
    cd pipeline && uv run python pipeline/authority/sources/ryholt-1997-sip/merge.py \\
        --agent-dir /some/other/path
    RYHOLT_AGENT_DIR=/some/other/path \\
        uv run python pipeline/authority/sources/ryholt-1997-sip/merge.py

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
# Co-located with the source dir per the Phase-0 playbook (matches every
# other Phase-0 source's convention). Was previously pinned to
# `/tmp/claude-501/ryholt` (pre-existing pre-portability artifact);
# corrected per code-reviewer P2.2 on PR #157.
DEFAULT_AGENT_DIR = SOURCE_DIR / "raw"
OUT = SOURCE_DIR / "reconciled.jsonl"
DIFF = SOURCE_DIR / "merge-disagreements.txt"


def _load(p: Path) -> dict[str, dict]:
    """Load a single agent's JSONL. Raises on duplicate ryholt_id within a file."""
    rows: dict[str, dict] = {}
    seen_line: dict[str, int] = {}
    for line_no, line in enumerate(p.read_text().splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        r = json.loads(s)
        rid = r["ryholt_id"]
        if rid in rows:
            raise ValueError(
                f"Duplicate ryholt_id {rid!r} in {p} "
                f"(first seen on line {seen_line[rid]}, again on line {line_no})"
            )
        rows[rid] = r
        seen_line[rid] = line_no
    return rows


SENTINEL_NULL_STRINGS = frozenset({"none", "-", "—", "n/a", "na", "unknown", "null"})


def _normalise_value(v: object) -> object:
    """Collapse sentinel strings that mean 'null' into actual None.

    Ryholt prints literal words like `none` in some Chron Table cells
    (e.g. Sakir-Har at 15.3, whose cartouche carries no sꜣ-rꜥ prenomen).
    Subagents faithfully transcribe those strings; we do not want them in
    the authority JSONL as string values — downstream consumers would
    treat them as real data.
    """
    if isinstance(v, str):
        stripped = v.strip().lower()
        if stripped in SENTINEL_NULL_STRINGS:
            return None
    return v


# === TIE_BREAK_OVERRIDES =====================================================
#
# Authoritative resolutions for (ryholt_id, field) tuples where the three
# extraction agents tie (1/1/1 across three agents, or 1/1 when one agent
# missed a row). Loaded from ``tie-break-overrides.json`` (alongside this
# file). Each entry's key is ``"<ryholt_id>|<field>"`` (JSON keys must be
# strings; the loader splits back to a tuple). Each value is
# ``{"value": ..., "rationale": "..."}``.
#
# ``rationale`` MUST cite the source page (Ryholt 1997 SIP printed page or
# physical PDF page) and the basis for the resolution.
#
# When ``_majority`` hits a tie with no override, it RAISES — option (a)
# enforcement: data is sacred, fail loudly. Mirrors the Beckerath PR #146 /
# Leprohon PR #128 / Porter-Moss PR #151 / Kitchen PR #155 canonical pattern.
_OVERRIDES_PATH = SOURCE_DIR / "tie-break-overrides.json"


def _load_overrides() -> dict[tuple[str, str], dict[str, object]]:
    if not _OVERRIDES_PATH.exists():
        return {}
    raw = json.loads(_OVERRIDES_PATH.read_text(encoding="utf-8"))
    # Top-level shape check (Gemini PR #157 round-1). A list / null / string
    # at the JSON root would otherwise raise an opaque `AttributeError` at
    # `.items()` rather than a labelled ValueError pointing at the file.
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
                f"separator (expected '<ryholt_id>|<field>')"
            )
        rid, field = k.split("|", 1)
        if not rid or not field:
            raise ValueError(
                f"merge.py: {_OVERRIDES_PATH} key {k!r} has empty ryholt_id "
                f"or field after splitting on '|' (expected "
                f"'<ryholt_id>|<field>' with both halves non-empty)"
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
        out[(rid, field)] = v
    return out


TIE_BREAK_OVERRIDES: dict[tuple[str, str], dict[str, object]] = _load_overrides()


def _deep_normalise(v: object) -> object:
    """Recursively apply sentinel-null normalisation across dicts and lists.

    Ryholt rows have a `source_citation` dict and a `concurrent_with` list.
    Per-field majority comparing whole list/dict objects must normalise
    children too.
    """
    if isinstance(v, list):
        return [_deep_normalise(item) for item in v]
    if isinstance(v, dict):
        return {k: _deep_normalise(val) for k, val in v.items()}
    return _normalise_value(v)


def _normalise_for_merge(row: dict) -> dict:
    """Apply pre-merge canonicalisations that should NOT be silent first-seen-
    pick at vote time. Currently a stub — Ryholt has no encoding-style
    normalisation candidates analogous to Leprohon's MdC → IFAO map.

    Extension point. If a future re-extraction surfaces spurious ties from
    encoding-style differences, normalise them here BEFORE the per-field
    counter sees the values.

    Returns a new dict; does not mutate the input.
    """
    if not isinstance(row, dict):
        return row
    return dict(row)


def _majority(values: list, *, rid: str, field: str) -> tuple[object, int]:
    """Return (chosen_value, count_of_agreers) from a list of per-agent values.

    Values are deep-normalised first so that sentinel nulls in nested dicts
    or lists do not force spurious disagreements.

    Tie handling (option (a) enforcement, issue #133):
      - Clear majority (top count > second count): use it.
      - Tie at the top (top count == second count):
          1. Look up ``(rid, field)`` in TIE_BREAK_OVERRIDES → use override.
          2. Otherwise → raise. Data is sacred. Fail loudly.

    Ryholt's flat-scalar schema (with one list field `concurrent_with` and
    one dict field `source_citation`) is treated as IDENTIFIER throughout —
    no `_classify_tie` / `_resolve_prose_tie` step. Same rationale as PR
    #146 (Beckerath) / PR #151 (PM) / PR #155 (Kitchen).

    `rid` and `field` are keyword-only required arguments per
    constitutional rule 10 (no backwards compatibility).
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

    # ---- Tie path. ----

    override = TIE_BREAK_OVERRIDES.get((rid, field))
    if override is not None:
        # Pass override value through `_deep_normalise` for parity with
        # majority-vote values (Gemini PR #155 round-2). Sentinel-null in
        # an override `value` collapses to None just like an agent emission.
        return _deep_normalise(override["value"]), top_count

    candidates = [
        f"  candidate {i+1} (count={cnt}): {k}"
        for i, (k, cnt) in enumerate(most)
    ]
    raise ValueError(
        f"Unresolved IDENTIFIER tie at ({rid!r}, {field!r}). "
        f"Add an entry to tie-break-overrides.json (key '{rid}|{field}') "
        f"with a cited rationale, or extend the agents' extractions until "
        f"a majority emerges. Candidates:\n" + "\n".join(candidates)
    )


_RID_RE = re.compile(r"^(?P<prefix>[A-Za-z]+|\d+)(?:\.(?P<seq>\d+)(?P<suffix>[a-z]*))?$")


_NON_NUMERIC_PREFIX_RANK = 100  # "after numeric dynasties" — domain semantic, not defensive


def _sort_key(rid: str) -> tuple[int, str, int, str]:
    """Sort order: numeric dynasty (13-17) ascending, then sequence number
    ascending (not lexicographic — so 13.10 sorts AFTER 13.9), then suffix.
    Non-numeric prefixes (Abyd, N, P, H, D, G) sort after numeric dynasties,
    alphabetically by prefix then by sequence.

    Raises ``ValueError`` on a malformed ryholt_id. Per constitutional
    rule 2, no silent coercion to a sentinel sort position.
    """
    m = _RID_RE.match(rid)
    if not m:
        raise ValueError(
            f"merge.py: ryholt_id {rid!r} does not match _RID_RE pattern"
        )
    prefix = m.group("prefix")
    seq = int(m.group("seq")) if m.group("seq") else -1
    suffix = m.group("suffix") or ""
    if prefix.isdigit():
        return (int(prefix), "", seq, suffix)
    return (_NON_NUMERIC_PREFIX_RANK, prefix, seq, suffix)


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

    for rid in all_ids:
        versions = [(tag, agents[tag].get(rid)) for tag in "abc"]
        present = [(t, v) for t, v in versions if v is not None]
        if len(present) < 2:
            # 3-agent majority-vote safety model requires ≥2 agents to
            # corroborate a row (issue #114). Loud failure per rule 2.
            only_tag = present[0][0] if present else "(none)"
            raise ValueError(
                f"merge.py: row {rid!r} appears in only {len(present)}/3 "
                f"agents (agent {only_tag!r}). Re-run extraction agent(s) "
                f"that missed this row, or hand-resolve before merging."
            )

        # Pre-merge canonicalisations stub (currently a no-op for Ryholt).
        present = [(t, _normalise_for_merge(v)) for t, v in present]

        # Sorted field iteration for deterministic merge-disagreements.txt
        # (issue #142 — same incidental fix as Beckerath / PM / Kitchen).
        all_fields = sorted(set().union(*[v.keys() for _, v in present]))
        merged: dict = {}
        row_disagreements: list[str] = []
        for field in all_fields:
            values = [v.get(field) for _, v in present]
            chosen, count = _majority(values, rid=rid, field=field)
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
                f"{rid} ({merged.get('nomen', '?')}):\n"
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
        default=Path(os.environ.get("RYHOLT_AGENT_DIR", DEFAULT_AGENT_DIR)),
        help=f"Directory containing agent-a/b/c.jsonl (default: {DEFAULT_AGENT_DIR}).",
    )
    args = parser.parse_args()
    main(args.agent_dir)
