"""Apply LLM-reviewer-identified corrections to reconciled.jsonl.

Run AFTER merge.py to layer scholarly corrections on top of the 3-subagent
majority vote. Every correction is recorded in merge-disagreements.txt under
the `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED` section so the audit trail
is preserved.

Two classes of correction are applied:

1. **Deterministic Dyn-21 concurrency recomputation.** The 3-subagent merge
   produced inconsistent `concurrent_with_kings` values because each agent
   independently re-derived interval overlaps from BCE dates, and small
   arithmetic errors compounded. Concurrency is a function of the extracted
   dates, not a field the LLM should "decide" — this script recomputes it
   deterministically by interval overlap. Ramesses XI (`20.01`) is also
   recomputed because Table 1's Renaissance-Era block explicitly aligns it
   with the first three HPAs.
2. **Spot corrections from the egyptologist-reviewer LLM pass.** Specific
   rows where majority vote picked the wrong `notes_from_kitchen` (e.g.
   21H.01 Herihor was tagged "hp" but Kitchen reserves that marker for
   Pinudjem I) and where Kitchen's own typo needs annotating (21H.06
   Djed-Khons-ef-ankh "1046–1056").

Run:
    cd pipeline && uv run python pipeline/authority/sources/kitchen-tipe/fix_rows.py
"""

from __future__ import annotations

import json
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
RECONCILED = SOURCE_DIR / "reconciled.jsonl"
DIFF = SOURCE_DIR / "merge-disagreements.txt"


# kitchen_id → interval [start_bce, end_bce] used for deterministic overlap
# computation. Keyed copy of rows' start_bce / end_bce EXCEPT for Djed-Khons-
# ef-ankh, where Kitchen's printed "1046–1056" is a typographic reversal
# (length is 1 y; predecessor Masaharta ends 1046, successor Menkheperre
# starts 1045). For concurrency math we use the corrected interval; the
# `end_bce` field remains verbatim -1056 (with a notes_from_kitchen flag).
DKF_INTERVAL = (-1046, -1045)


def _compute_concurrency(rows: list[dict]) -> dict[str, list[str]]:
    """Recompute `concurrent_with_kings` for every Dyn-21 row deterministically.

    Rule: two rows are concurrent if the open interval (start_bce, end_bce)
    pairs strictly overlap — i.e. `max(starts) < min(ends)` in absolute-value
    terms. Touching at a single boundary year (e.g. successor's start = predecessor's
    end) does NOT count as concurrency; that is the succession boundary.

    Only Dyn-21 Tanite↔HPA pairs get populated — plus Ramesses XI (20.01)
    because Kitchen's Table 1 Renaissance-Era block aligns him with the
    first three HPAs.
    """
    def interval(r: dict) -> tuple[int, int]:
        if r["kitchen_id"] == "21H.06":
            return DKF_INTERVAL
        s, e = r["start_bce"], r["end_bce"]
        if s >= e:
            raise ValueError(
                f"{r['kitchen_id']}: start_bce {s} not strictly earlier than "
                f"end_bce {e}. Dyn-21 rows must have ordered intervals "
                f"(any Kitchen-typo exceptions must be hard-coded at the top "
                f"of this file, like DKF_INTERVAL for 21H.06)."
            )
        return (s, e)

    tanite = [r for r in rows if r["kitchen_id"].startswith("21.") or r["kitchen_id"] == "20.01"]
    hpa = [r for r in rows if r["kitchen_id"].startswith("21H.")]

    result: dict[str, list[str]] = {}
    for t in tanite:
        ti = interval(t)
        if ti is None:
            result[t["kitchen_id"]] = []
            continue
        result[t["kitchen_id"]] = sorted(
            h["kitchen_id"] for h in hpa
            if (hi := interval(h)) is not None
            and max(ti[0], hi[0]) < min(ti[1], hi[1])
        )
    for h in hpa:
        hi = interval(h)
        if hi is None:
            result[h["kitchen_id"]] = []
            continue
        result[h["kitchen_id"]] = sorted(
            t["kitchen_id"] for t in tanite
            if (ti := interval(t)) is not None
            and max(ti[0], hi[0]) < min(ti[1], hi[1])
        )
    return result


# Spot corrections identified by the egyptologist-reviewer subagent pass.
# Each entry: (kitchen_id, field, new_value, rationale).
SPOT_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "21H.01",
        "notes_from_kitchen",
        None,
        'Table 1 shows "Herihor in S (6 y)" — the "hp" marker Kitchen '
        'uses to disambiguate Pinudjem I hp vs Pinudjem I \'kg\' does not '
        'appear on Herihor. Majority vote picked "hp" from a confused agent.',
    ),
    (
        "21H.06",
        "notes_from_kitchen",
        "Kitchen prints the date range as '1046–1056' with a 1 y "
        "length; predecessor Masaharta ends 1046 and successor Menkheperre "
        "starts 1045, so the printed 1056 is a typographic reversal and the "
        "true end is 1045. end_bce preserved verbatim as -1056; concurrency "
        "computed against the corrected interval.",
        "Annotate Kitchen's 1046–1056 typo explicitly so downstream consumers "
        "don't silently compute a -11 year reign from the BCE endpoints.",
    ),
]


def main() -> None:
    rows = [json.loads(line) for line in RECONCILED.read_text().splitlines() if line.strip()]

    override_log: list[str] = []

    # 1. Deterministic Dyn-21 concurrency recomputation.
    new_conc = _compute_concurrency(rows)
    for r in rows:
        kid = r["kitchen_id"]
        if kid not in new_conc:
            continue
        old = r.get("concurrent_with_kings", [])
        new = new_conc[kid]
        if old != new:
            override_log.append(
                f"{kid}: concurrent_with_kings {json.dumps(old)} → {json.dumps(new)} "
                f"(deterministic interval-overlap recomputation from start_bce/end_bce)"
            )
            r["concurrent_with_kings"] = new

    # 2. Spot corrections from the egyptologist-reviewer pass.
    for kid, field, new_val, rationale in SPOT_CORRECTIONS:
        row = next((r for r in rows if r["kitchen_id"] == kid), None)
        if row is None:
            raise KeyError(f"No row with kitchen_id {kid!r}")
        old_val = row.get(field)
        if old_val == new_val:
            continue
        override_log.append(
            f"{kid}: {field} {json.dumps(old_val, ensure_ascii=False)} → "
            f"{json.dumps(new_val, ensure_ascii=False)} ({rationale})"
        )
        row[field] = new_val

    RECONCILED.write_text(
        "\n".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows
        )
        + "\n"
    )

    existing_diff = DIFF.read_text()
    # Guard against double-append if the script is re-run.
    marker = "LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED"
    if marker in existing_diff:
        head, _, _ = existing_diff.partition(f"\n\n{marker}")
        existing_diff = head
    appended = (
        f"{existing_diff.rstrip()}\n\n"
        f"{marker}\n"
        + "=" * len(marker) + "\n"
        "Corrections applied by fix_rows.py AFTER the 3-subagent majority-vote\n"
        "merge. Source of each correction: either (a) deterministic\n"
        "recomputation from extracted fields where LLM agents disagreed on\n"
        "arithmetic, or (b) egyptologist-reviewer Claude Code subagent pass\n"
        "against the source PDF. No human scholar has signed off on this\n"
        "extract yet — per ADR-017 step 6, the extract is provisional until\n"
        "that happens.\n\n"
        + "\n".join(f"- {line}" for line in override_log) + "\n"
    )
    DIFF.write_text(appended)

    print(f"Applied {len(override_log)} override(s).")
    print(f"Updated {RECONCILED.relative_to(RECONCILED.parents[4])}")
    print(f"Updated {DIFF.relative_to(DIFF.parents[4])}")


if __name__ == "__main__":
    main()
