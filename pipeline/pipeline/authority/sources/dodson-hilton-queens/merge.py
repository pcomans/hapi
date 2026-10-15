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

Usage (one chunk at a time, from the dyn15-18 chunk on):
    cd pipeline && uv run python pipeline/authority/sources/dodson-hilton-queens/merge.py dyn15-18

Inputs: `agents/<chunk>/agent-{a,b,c}.jsonl`, the three extraction agents' outputs, committed
(with `agents/<chunk>/provenance.json`) so the merge can be re-run and audited.

Outputs:
    reconciled.jsonl                       (this source dir)
    merge-disagreements-<chunk>.txt        (this source dir; committed for audit)

**One chunk per run** (2026-10-14). Chunks 1-8's agent outputs were never committed (they lay
under the gitignored `raw/`) and are gone, so the whole file can no longer be re-merged, and
the old whole-file mode, which would now overwrite every earlier row, is removed (rule 10).
A run merges the named chunk's sub-periods (`CHUNK_SUB_PERIODS`) from its agents and carries
every other `reconciled.jsonl` row forward unchanged: for those rows `reconciled.jsonl` itself
is the source of truth, `fix_rows.py`'s corrections included (removing a correction no longer
reverts its value). It raises if the agents' sub-periods are not exactly the chunk's, if a row
already in `reconciled.jsonl` for those sub-periods would be dropped, or if an agent emits a
field outside the extraction schema. Then run `fix_rows.py` and `destructure_notes.py`.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

SOURCE_DIR = Path(__file__).parent

# The sub-periods each chunk's agents extract; a run must produce exactly these.
CHUNK_SUB_PERIODS = {
    "dyn15-18": frozenset({"Rulers of Foreign Countries", "The Southern Kingdom", "The Taosids"}),
}
# The fields an extraction agent emits (`prompt-dyn15-18.md`); `is_group_entry` is
# fix_rows.py's, and prose (`notes`) is never extracted.
AGENT_FIELDS = frozenset({
    "dh_id", "name", "alt_names", "roles", "sex", "spouse_names", "father_name", "mother_name",
    "children_names", "dynasty", "sub_period", "unplaced", "source_citation",
})


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


def main(chunk: str, source_dir: Path = SOURCE_DIR) -> None:
    agent_dir = source_dir / "agents" / chunk
    agents = {tag: _load(agent_dir / f"agent-{tag}.jsonl") for tag in "abc"}
    emitted = {key[1] for a in agents.values() for key in a}
    if emitted != CHUNK_SUB_PERIODS[chunk]:
        raise ValueError(f"{chunk}: the agents emitted sub-periods {sorted(emitted)}, "
                         f"not the chunk's {sorted(CHUNK_SUB_PERIODS[chunk])}")
    stray = {f for a in agents.values() for row in a.values() for f in row} - AGENT_FIELDS
    if stray:
        raise ValueError(f"{chunk}: an agent emitted fields outside the extraction schema: {sorted(stray)}")

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

    out = source_dir / "reconciled.jsonl"
    prior = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    rebuilt = CHUNK_SUB_PERIODS[chunk]
    dropped = sorted({_row_key(r) for r in prior if r["sub_period"] in rebuilt} - set(all_keys))
    if dropped:
        raise ValueError(f"{chunk}: reviewed rows the agents no longer produce would be dropped: {dropped}")
    carried = [r for r in prior if r["sub_period"] not in rebuilt]
    print(f"Carried forward {len(carried)} rows of other sub-periods; "
          f"rebuilt {len(prior) - len(carried)} rows of {sorted(rebuilt)}")
    final = carried + final
    keys = [_row_key(r) for r in final]
    unplaced = frozenset(k for k, r in zip(keys, final) if r["unplaced"])
    final = [r for _, r in sorted(zip(keys, final), key=lambda kr: _sort_key_for(unplaced)(kr[0]))]
    diff_path = source_dir / f"merge-disagreements-{chunk}.txt"

    out.write_text(
        "\n".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) for r in final
        )
        + "\n",
        encoding="utf-8",
    )
    diff_path.write_text("\n".join(report) if report else "No field-level disagreements.\n", encoding="utf-8")

    print("Agents: " + ", ".join(f"{t}={len(a)}" for t, a in agents.items()))
    print(f"Merged rows: {len(final)}")
    rows_with_disagreement = sum(1 for r in report if r.strip())
    print(f"Rows with ≥1 field disagreement: {rows_with_disagreement}")
    print(f"Wrote {out}")
    print(f"Wrote {diff_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("chunk", choices=sorted(CHUNK_SUB_PERIODS))
    main(parser.parse_args().chunk)
