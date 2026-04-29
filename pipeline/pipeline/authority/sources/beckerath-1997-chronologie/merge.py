"""Merge three independent Claude Code subagent extractions into reconciled.jsonl.

Beckerath 1997 Anhang A has several error-prone micro-features (slash-separated
high/low alternative endpoints, mixed-certainty per-endpoint approximate flags,
Egyptian-language parenthetical name forms with non-ASCII diacritics like
``-rê`` / ``-rî`` / ``-ê`` / ``-â``, Dyn 16 Hyksos-vassal labelling, the Dyn 22
Oberägyptische Linie sub-line). The three-subagent + majority-vote pipeline
absorbs stochastic transcription drift on those features.

Tie-break enforcement (issue #144). Mirrors Leprohon PR #128. Beckerath's row
schema is flat scalars (no nested name-list dicts), so the tie-classification
logic collapses to "every field is IDENTIFIER": any tie that is not unanimous
or a real majority either resolves through an explicit ``tie-break-overrides
.json`` entry (with a citation in the rationale) or RAISES. Constitutional
rule 2 — ``Counter.most_common(1)[0]`` is a silent first-seen-pick at a tie
and is not authority data.

Beckerath has no pre-merge normalisation candidates analogous to Leprohon's
MdC → IFAO mapping (no ``transliteration`` sub-fields). ``_normalise_for_merge``
is retained as a stub / extension point: if a future re-extraction surfaces
spurious ties from encoding-style differences, this is where they collapse
pre-vote.

Structure cloned from kitchen-tipe/merge.py with these adaptations:

1. ``kitchen_id`` → ``beckerath_id`` everywhere.
2. ``_sort_key`` orders rows by ``(dynasty_int, sub_line_rank, sequence)`` —
   Beckerath uses a ``sub_line`` field rather than compound ID prefixes, so
   the sort key reads it directly off the row.
3. ``DEFAULT_AGENT_DIR`` is beckerath-specific.
4. ``_majority`` enforces the option-(a) tie-break per issue #144 (see above).

Sentinel-null normalisation is copied verbatim from kitchen-tipe — source-
agnostic.

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


SENTINEL_NULL_STRINGS = frozenset({"none", "-", "—", "n/a", "na", "unknown", "null"})


# === TIE_BREAK_OVERRIDES =====================================================
#
# Authoritative resolutions for (beckerath_id, field) tuples where the three
# extraction agents tie (1/1/1 across three agents, or 1/1 when one agent
# missed a row). Loaded from ``tie-break-overrides.json`` (alongside this
# file). Each entry's key is ``"<beckerath_id>|<field>"`` (JSON keys must be
# strings; the loader splits back to a tuple). Each value is
# ``{"value": ..., "rationale": "..."}``.
#
# ``rationale`` MUST cite the source page (Beckerath 1997 printed Anhang A
# page or scan-NNN-{left,right}.jpg) and the basis for the resolution.
#
# When ``_majority`` hits a tie with no override, it RAISES — option (a)
# enforcement: data is sacred, fail loudly. The merge is broken until every
# uncovered tie has an entry here. This is intentional.
#
# Adding a new override requires (1) the citation in ``rationale``, (2) a
# corresponding test in ``test_beckerath_merge_tie_break.py`` that pins the
# resolved value on disk, (3) re-running merge.py to apply it.
_OVERRIDES_PATH = SOURCE_DIR / "tie-break-overrides.json"


def _load_overrides() -> dict[tuple[str, str], dict[str, object]]:
    if not _OVERRIDES_PATH.exists():
        return {}
    raw = json.loads(_OVERRIDES_PATH.read_text())
    out: dict[tuple[str, str], dict[str, object]] = {}
    for k, v in raw.items():
        if "|" not in k:
            raise ValueError(
                f"merge.py: {_OVERRIDES_PATH} key {k!r} missing '|' "
                f"separator (expected '<beckerath_id>|<field>')"
            )
        bid, field = k.split("|", 1)
        if not bid or not field:
            raise ValueError(
                f"merge.py: {_OVERRIDES_PATH} key {k!r} has empty bid or field "
                f"after splitting on '|' (expected '<beckerath_id>|<field>' "
                f"with both halves non-empty)"
            )
        out[(bid, field)] = v
    return out


TIE_BREAK_OVERRIDES: dict[tuple[str, str], dict[str, object]] = _load_overrides()


def _normalise_value(v: object) -> object:
    """Collapse sentinel strings that mean 'null' into actual None.

    Beckerath uses ``-`` in a few cells (e.g. when no Egyptian titulary is
    given for an obscure king) and the bracketed ``[?]`` form for unknown
    Horus names; the subagent prompt preserves the bracketed phrase
    verbatim, so this normaliser is for ``-`` / ``none`` style cells only.
    """
    if isinstance(v, str):
        stripped = v.strip().lower()
        if stripped in SENTINEL_NULL_STRINGS:
            return None
    return v


def _deep_normalise(v: object) -> object:
    """Recursively apply sentinel-null normalisation across dicts and lists.

    Beckerath's ``source_citation`` is a small dict and the rest of the
    schema is flat scalars, so this is mostly a passthrough — but applied
    uniformly so a future schema addition that nests a dict under a top-
    level key gets normalisation for free.
    """
    if isinstance(v, list):
        return [_deep_normalise(item) for item in v]
    if isinstance(v, dict):
        return {k: _deep_normalise(val) for k, val in v.items()}
    return _normalise_value(v)


def _normalise_for_merge(row: dict) -> dict:
    """Apply pre-merge canonicalisations that should NOT be silent first-seen-
    pick at vote time. Currently a stub — Beckerath has no encoding-style
    normalisation candidates analogous to Leprohon's MdC → IFAO map (no
    ``transliteration`` sub-fields).

    Extension point. If a future re-extraction surfaces spurious ties from
    encoding-style differences (e.g. ``rê`` / ``re`` diacritic variance,
    ``-`` / ``–`` / ``—`` punctuation drift), normalise them here BEFORE
    the per-field counter sees the values, so the override table doesn't
    accumulate entries that are pure encoding-diffs rather than real
    scholarly disagreements.

    Returns a new dict; does not mutate the input.
    """
    if not isinstance(row, dict):
        return row
    return dict(row)


def _majority(values: list, *, bid: str, field: str) -> tuple[object, int]:
    """Return (chosen_value, count_of_agreers) from a list of per-agent values.

    Values are deep-normalised first so that sentinel nulls do not force
    spurious disagreements. JSON serialisation with sorted keys is the
    equality key — handles nested dicts (``source_citation``) correctly
    by value.

    Tie handling (option (a) enforcement, issue #144):
      - Clear majority (top count > second count): use it.
      - Tie at the top (top count == second count):
          1. Look up ``(bid, field)`` in TIE_BREAK_OVERRIDES → use override.
          2. Otherwise → raise. Data is sacred. Fail loudly.

    Beckerath's row schema is flat scalars (no nested name-list dicts), so
    every tied field is treated as IDENTIFIER — no ``_classify_tie`` /
    ``_resolve_prose_tie`` step. ``notes_from_beckerath`` is verbatim cell
    text from Beckerath's Anhang A; resolving it deterministically by
    "longest wins" or similar would be a heuristic without scholarly
    grounding (constitutional rule 6 distinguishes "deterministic-with-
    documented-policy" from "heuristic that mostly works"). Verbatim cell-
    text ties belong in the override table with a printed-page citation.

    ``bid`` and ``field`` are keyword-only required arguments. Constitutional
    rule 10 (no backwards compatibility): no Optional fallback, no silent
    first-seen path for "legacy callers" — that path is exactly the slop
    pattern this module exists to kill.
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
    override = TIE_BREAK_OVERRIDES.get((bid, field))
    if override is not None:
        # Override carries the resolved value; treat as if it had top_count
        # agreers (it's an authoritative reviewer-set value).
        return override["value"], top_count

    # 2. Tie with no override → raise. Build a diagnostic that names every
    # distinct value so the agent adding the override has the candidates in
    # front of it.
    candidates = [
        f"  candidate {i+1} (count={cnt}): {k}"
        for i, (k, cnt) in enumerate(most)
    ]
    raise ValueError(
        f"Unresolved IDENTIFIER tie at ({bid!r}, {field!r}). "
        f"Add an entry to tie-break-overrides.json (key '{bid}|{field}') "
        f"with a cited rationale, or extend the agents' extractions until "
        f"a majority emerges. Candidates:\n" + "\n".join(candidates)
    )


_BID_RE = re.compile(r"^(?P<dyn>\d+)\.(?P<seq>\d+)$")


def _sort_key(row: dict) -> tuple:
    """Sort by (dynasty_int, sub_line_rank, sequence_in_dynasty).

    Reads ``dynasty``, ``sub_line``, ``sequence_in_dynasty`` directly off the
    row rather than parsing the ID, because Beckerath's IDs are pure
    ``{dyn:02}.{seq:02}`` without sub-line encoding.

    Raises ``TypeError`` if ``dynasty`` or ``sequence_in_dynasty`` is not
    an integer. Per constitutional rule 2, malformed agent output is a
    loud failure, not silently coerced to a sentinel.
    """
    dyn = row["dynasty"]
    if not isinstance(dyn, int):
        raise TypeError(
            f"merge.py: row {row.get('beckerath_id')!r} has non-int dynasty: "
            f"{dyn!r} (type {type(dyn).__name__})"
        )
    sub_rank = _sub_line_rank(row.get("sub_line"))
    seq = row["sequence_in_dynasty"]
    if not isinstance(seq, int):
        raise TypeError(
            f"merge.py: row {row.get('beckerath_id')!r} has non-int "
            f"sequence_in_dynasty: {seq!r} (type {type(seq).__name__})"
        )
    return (dyn, sub_rank, seq)


def _row_sort_key_from_id(bid: str, agents: dict) -> tuple:
    """Look up sort key for a beckerath_id by finding the row in any agent.

    Used during merge before we know which row content to keep — the sort
    key has to be derivable from the ID + an exemplar row from any agent.

    Raises ``KeyError`` if ``bid`` is not present in any agent's output
    (impossible by construction in ``main()`` but explicit for clarity).
    """
    for agent in agents.values():
        if bid in agent:
            return _sort_key(agent[bid])
    raise KeyError(
        f"merge.py: beckerath_id {bid!r} was in the union of agent IDs but "
        f"not found when looking up an exemplar row — agent dict mutated "
        f"between collection and lookup?"
    )


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
            # 3-agent majority-vote safety model requires ≥2 agents to
            # corroborate a row. A single hallucinated or mis-keyed
            # beckerath_id silently writing into reconciled.jsonl
            # undermines the entire merge architecture (codex review on
            # PR #113, issue #114). Loud failure per rule 2 — re-run the
            # extractors or hand-resolve the singleton before merging.
            only_tag = present[0][0] if present else "(none)"
            raise ValueError(
                f"merge.py: row {bid!r} appears in only {len(present)}/3 "
                f"agents (agent {only_tag!r}). Majority-vote merge "
                f"requires ≥2 agents to corroborate. Re-run the extraction "
                f"agent(s) that missed this row, or hand-resolve the "
                f"singleton before merging."
            )

        # Apply pre-merge canonicalisations (currently a stub for
        # Beckerath; see _normalise_for_merge docstring).
        present = [(t, _normalise_for_merge(v)) for t, v in present]

        # Sort field iteration so the disagreement report is deterministic
        # across re-runs. Without this, Python's set-iteration order
        # reshuffles the per-field blocks on every run and produces a huge
        # noise diff against merge-disagreements.txt.
        all_fields = sorted(set().union(*[v.keys() for _, v in present]))
        merged: dict = {}
        row_disagreements: list[str] = []
        for field in all_fields:
            values = [v.get(field) for _, v in present]
            chosen, count = _majority(values, bid=bid, field=field)
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
