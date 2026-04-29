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


SENTINEL_NULL_STRINGS = frozenset({"none", "-", "—", "n/a", "na", "unknown", "null"})


# === TIE_BREAK_OVERRIDES =====================================================
#
# Authoritative resolutions for (kitchen_id, field) tuples where the three
# extraction agents tie (1/1/1 across three agents, or 1/1 when one agent
# missed a row). Loaded from ``tie-break-overrides.json`` (alongside this
# file). Each entry's key is ``"<kitchen_id>|<field>"`` (JSON keys must be
# strings; the loader splits back to a tuple). Each value is
# ``{"value": ..., "rationale": "..."}``.
#
# ``rationale`` MUST cite the source page (Kitchen TIPE 3rd ed. 1996 printed
# Tables 1/3/4 page or physical PDF page) and the basis for the resolution.
#
# When ``_majority`` hits a tie with no override, it RAISES — option (a)
# enforcement: data is sacred, fail loudly. Mirrors the Beckerath PR #146 /
# Leprohon PR #128 / Porter-Moss PR #151 canonical pattern.
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
                f"separator (expected '<kitchen_id>|<field>')"
            )
        kid, field = k.split("|", 1)
        if not kid or not field:
            raise ValueError(
                f"merge.py: {_OVERRIDES_PATH} key {k!r} has empty kitchen_id "
                f"or field after splitting on '|' (expected "
                f"'<kitchen_id>|<field>' with both halves non-empty)"
            )
        # Validate value shape per Gemini PR #155 round-1: every entry MUST
        # be a dict with `value` and `rationale` keys. A malformed entry
        # (e.g. a bare string mistakenly written instead of a dict) would
        # fail downstream at `override["value"]` lookup with an opaque
        # KeyError; raise loudly here with the offending key + actual
        # shape so the override-file author sees the problem at load time.
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
        out[(kid, field)] = v
    return out


TIE_BREAK_OVERRIDES: dict[tuple[str, str], dict[str, object]] = _load_overrides()


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


def _deep_normalise(v: object) -> object:
    """Recursively apply sentinel-null normalisation across dicts and lists.

    Kitchen rows have a `source_citation` dict and a `concurrent_with_kings`
    list field. Per-field majority comparing whole list/dict objects must
    normalise children too — e.g. an agent emitting `{"page": "-"}` vs
    `{"page": null}` must not register as a tie.
    """
    if isinstance(v, list):
        return [_deep_normalise(item) for item in v]
    if isinstance(v, dict):
        return {k: _deep_normalise(val) for k, val in v.items()}
    return _normalise_value(v)


def _normalise_for_merge(row: dict) -> dict:
    """Apply pre-merge canonicalisations that should NOT be silent first-seen-
    pick at vote time. Currently a stub — Kitchen has no encoding-style
    normalisation candidates analogous to Leprohon's MdC → IFAO map.

    Extension point. If a future re-extraction surfaces spurious ties from
    encoding-style differences (e.g. `c.` vs `ca.` date prefixes, hedge-
    marker variance), normalise them here BEFORE the per-field counter
    sees the values.

    Returns a new dict; does not mutate the input.
    """
    if not isinstance(row, dict):
        return row
    return dict(row)


def _majority(values: list, *, kid: str, field: str) -> tuple[object, int]:
    """Return (chosen_value, count_of_agreers) from a list of per-agent values.

    Values are deep-normalised first so that sentinel nulls in nested dicts
    or lists do not force spurious disagreements.

    Tie handling (option (a) enforcement, issue #136):
      - Clear majority (top count > second count): use it.
      - Tie at the top (top count == second count):
          1. Look up ``(kid, field)`` in TIE_BREAK_OVERRIDES → use override.
          2. Otherwise → raise. Data is sacred. Fail loudly.

    Kitchen's flat-scalar schema (with one list field `concurrent_with_kings`
    and one dict field `source_citation`) is treated as IDENTIFIER throughout
    — no `_classify_tie` / `_resolve_prose_tie` step. Same rationale as PR
    #146 (Beckerath) and PR #151 (PM): heuristic prose / list-union policies
    without scholarly grounding violate constitutional rule 6. Tied list /
    scalar fields go through the override path with a citation.

    `kid` and `field` are keyword-only required arguments per
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

    override = TIE_BREAK_OVERRIDES.get((kid, field))
    if override is not None:
        # Pass override value through `_deep_normalise` for parity with
        # majority-vote values (Gemini PR #155 round-2). If a future
        # override entry encodes `"-"` or another sentinel-null in its
        # `value`, this collapses it to None just like an agent emission
        # would — keeps the "value space" consistent regardless of
        # resolution path. Override values are normally non-null
        # citation-grounded strings, but the normalisation is cheap and
        # closes the consistency gap loud-vs-silent.
        return _deep_normalise(override["value"]), top_count

    candidates = [
        f"  candidate {i+1} (count={cnt}): {k}"
        for i, (k, cnt) in enumerate(most)
    ]
    raise ValueError(
        f"Unresolved IDENTIFIER tie at ({kid!r}, {field!r}). "
        f"Add an entry to tie-break-overrides.json (key '{kid}|{field}') "
        f"with a cited rationale, or extend the agents' extractions until "
        f"a majority emerges. Candidates:\n" + "\n".join(candidates)
    )


_KID_RE = re.compile(r"^(?P<prefix>[0-9]+[A-Za-z]*)\.(?P<seq>\d+)$")


def _sort_key(kid: str) -> tuple[int, int, str, int]:
    """Sort by (dynasty_int, polity_rank, prefix, sequence_in_stream).

    Raises ``ValueError`` if ``kid`` doesn't match ``{prefix}.{seq}`` or if
    the parsed prefix isn't in ``STREAM_ORDER``. Per constitutional rule 2,
    a malformed ID is a loud failure, not silently sorted to the end.
    """
    m = _KID_RE.match(kid)
    if not m:
        raise ValueError(
            f"merge.py: kitchen_id {kid!r} does not match "
            f"{{prefix}}.{{seq}} pattern"
        )
    prefix = m.group("prefix")
    seq = int(m.group("seq"))
    if prefix not in STREAM_ORDER:
        raise ValueError(
            f"merge.py: kitchen_id {kid!r} has unknown prefix {prefix!r}; "
            f"known prefixes: {sorted(STREAM_ORDER)}"
        )
    dyn, rank = STREAM_ORDER[prefix]
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
            # 3-agent majority-vote safety model requires ≥2 agents to
            # corroborate a row. A single hallucinated or mis-keyed
            # kitchen_id silently writing into reconciled.jsonl undermines
            # the entire merge architecture (issue #114). Loud failure
            # per rule 2 — re-run the extractors or hand-resolve before
            # merging.
            only_tag = present[0][0] if present else "(none)"
            raise ValueError(
                f"merge.py: row {kid!r} appears in only {len(present)}/3 "
                f"agents (agent {only_tag!r}). Majority-vote merge "
                f"requires ≥2 agents to corroborate. Re-run the extraction "
                f"agent(s) that missed this row, or hand-resolve the "
                f"singleton before merging."
            )

        # Apply pre-merge canonicalisations (currently a stub for Kitchen;
        # see _normalise_for_merge docstring).
        present = [(t, _normalise_for_merge(v)) for t, v in present]

        # Sort field iteration so the disagreement report is deterministic
        # across re-runs (issue #142).
        all_fields = sorted(set().union(*[v.keys() for _, v in present]))
        merged: dict = {}
        row_disagreements: list[str] = []
        for field in all_fields:
            values = [v.get(field) for _, v in present]
            chosen, count = _majority(values, kid=kid, field=field)
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
        default=Path(os.environ.get("KITCHEN_AGENT_DIR", DEFAULT_AGENT_DIR)),
        help=f"Directory containing agent-a/b/c.jsonl (default: {DEFAULT_AGENT_DIR}).",
    )
    args = parser.parse_args()
    main(args.agent_dir)
