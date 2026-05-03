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

import copy
import json
import re
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
RECONCILED = SOURCE_DIR / "reconciled.jsonl"
DIFF = SOURCE_DIR / "merge-disagreements.txt"


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
        # Use `corrected_end_bce` (typed field) when present — the only
        # row currently affected is 21H.06 where Kitchen's printed
        # `end_bce=-1056` is a typographic reversal of -1045. Keep the
        # raw `end_bce` verbatim per Rule 6; the typed correction is
        # the single source of truth for downstream interval math.
        s = r["start_bce"]
        # Explicit `is not None` (not `or`) — `0` is a valid BCE year in
        # principle, even though Kitchen's TIPE only spans negative ranges.
        corr = r.get("corrected_end_bce")
        e = corr if corr is not None else r["end_bce"]
        if s >= e:
            raise ValueError(
                f"{r['kitchen_id']}: start_bce {s} not strictly earlier than "
                f"effective end {e}. Dyn-21 rows must have ordered intervals "
                f"(any Kitchen-typo exceptions must populate corrected_end_bce)."
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


# === Issue #180 schema-audit additions =======================================
#
# Strict-all-3-P1 per #176/#177/#178/#179 policy. Adds typed flags to
# disambiguate the multiple semantics overloaded onto null fields and
# in-string sentinels in Kitchen's TIPE Tables 1/3/4.

SCHEMA_FIELD_DEFAULTS_180: dict[str, object] = {
    # Shape D — disambiguate the multiple meanings of `null` on the
    # `prenomen` field. `True` means Kitchen explicitly prints
    # `[Prenomen unknown]` (a positive assertion that the king exists
    # but the value isn't recorded). `False` means the table layout
    # doesn't include this column for this row (e.g. HPA list omits
    # prenomen). The analogous `[Length unknown]` sentinel does not
    # appear in the current TIPE extract; if it surfaces in a future
    # re-extraction, add a parallel `length_is_kitchen_unknown` flag.
    "prenomen_is_kitchen_unknown": False,
    # Shape H — kitchen_id substream letter (`H` HPA, `E` Sais-Bubastis-East,
    # `P` Persian/proto-Saite, `None` main-line dynasty).
    "substream": None,
    # Shape J — typed flags for structural variants the audit flagged.
    # `is_co_regent_only`: row is a co-regent slot only (e.g. 21H.05
    # Masaharta is HPA but co-regent under Pinudjem I, not a sole ruler).
    "is_co_regent_only": False,
    # `existence_doubtful`: Kitchen marks the king's existence as
    # uncertain via `?` / `??` / quote-glyphs in `name`.
    "existence_doubtful": False,
    # `same_person_as`: kitchen_id of the row this row's king is
    # ALSO catalogued as. Pinudjem I appears at 21H.03 (HPA) and
    # 21H.04 (king-titulature) — same person, two table rows.
    "same_person_as": None,
    # Shape J — `corrected_end_bce`: Kitchen's printed `end_bce` is a
    # typographic reversal on 21H.06; the corrected interval lives here.
    # None on every other row.
    "corrected_end_bce": None,
    # Shape I — typed list for two-prenomen rows (25.03 Piankhy adopts
    # Sneferre after initially using Usimare). `prenomens` replaces the
    # legacy `prenomen` scalar's comma-joined form. Empty list when
    # only one prenomen exists; in that case the scalar `prenomen` is
    # the source of truth.
    "prenomens": [],
}

# Same-person pairs Kitchen catalogues twice. Listed as one-direction
# tuples; the migration code derives the symmetric mapping.
# - Pinudjem I: HPA capacity ↔ king titulature (Table 3)
# - Tefnakht I: Chief of Mā ↔ king (Table 4 prints "(c. 13 y; then, kg)"
#   on 24E.04 explicitly chaining to 24.01). Per egyptologist P1-3.
_SAME_PERSON_ONEWAY_PAIRS: list[tuple[str, str]] = [
    ("21H.03", "21H.04"),
    ("24E.04", "24.01"),
]
_SAME_PERSON_PAIRS: dict[str, str] = {}
for _a, _b in _SAME_PERSON_ONEWAY_PAIRS:
    _SAME_PERSON_PAIRS[_a] = _b
    _SAME_PERSON_PAIRS[_b] = _a

# `is_co_regent_only` is derived from TWO sources:
#  (a) `notes_from_kitchen` containing Kitchen's literal "co-rgt only"
#      annotation — currently 22.03 Shoshenq II + 22.06 Harsiese (per
#      egyptologist P1-1, both Table 3 cells carry the marker)
#  (b) the hardcoded scholarly-judgment additions below for HPA
#      co-regents Kitchen flags via narrative discussion rather than a
#      table-cell annotation: 21H.05 Masaharta + 21H.06 Djed-Khons-ef-ankh
# Pinned set (closure-tested): {21H.05, 21H.06, 22.03, 22.06}.
_CO_REGENT_ONLY_NOTE_RE = re.compile(r"\bco-rgt\s+only\b", re.IGNORECASE)
_CO_REGENT_SCHOLARLY_OVERRIDES = {
    "21H.05",  # Masaharta — HPA co-regent under Pinudjem I (TIPE narrative)
    "21H.06",  # Djed-Khons-ef-ankh — short-lived HPA co-regent
}

# 25.03 Piankhy temporal prenomen sequence: Kitchen's `Usimare, then
# Sneferre` decomposes to the typed list with `when` markers.
_PIANKHY_PRENOMENS = [
    {"name": "Usimare", "when": "initial"},
    {"name": "Sneferre", "when": "later"},
]

# 21H.06 — Kitchen prints `1046–1056` with a 1-year length; the printed
# `1056` is a typographic reversal of `1045` (predecessor Masaharta ends
# 1046, successor Menkheperre starts 1045). Move this from a hardcoded
# Python constant + notes_from_kitchen prose to a typed `corrected_end_bce`
# field. Per audit Shape J P1.
_CORRECTED_END_BCE: dict[str, int] = {
    "21H.06": -1045,
}


_KITCHEN_ID_SUBSTREAM_RE = re.compile(r"^\d+([A-Z])\.")


def _detect_substream(kitchen_id: str) -> str | None:
    m = _KITCHEN_ID_SUBSTREAM_RE.match(kitchen_id)
    return m.group(1) if m else None


# Existence-uncertainty markers Kitchen prints. Sources per row:
#   - trailing `?` or `??` on `name` (24E.01 `Pimay (the later king??)`,
#     24E.02 `Two further governors?`)
#   - single-quote-wrap on entire `name` (24P.01 `'Ammeris'`)
#   - literal `existence, doubtful` annotation in `notes_from_kitchen`
#     (23.08 Shoshenq VI, per egyptologist P1-2)
_NAME_QUESTION_RE = re.compile(r"\?+\s*\)?\s*$")
_NOTES_DOUBTFUL_RE = re.compile(r"\bexistence,?\s+doubtful\b", re.IGNORECASE)


def _detect_existence_doubtful(name: str, notes: str | None) -> bool:
    if name and _NAME_QUESTION_RE.search(name):
        return True
    # A whole-word quote-glyph like `'Ammeris'` is an existence hedge;
    # an inline-quoted disambiguator like `Psusennes 'III'` is a
    # numeral-glyph variation, not existence-doubtful. Use heuristic:
    # if the entire name (modulo whitespace) is wrapped in single
    # quotes, treat as doubtful.
    stripped = name.strip() if name else ""
    if stripped.startswith("'") and stripped.endswith("'"):
        return True
    # Literal Kitchen annotation in notes (23.08 Shoshenq VI).
    if notes and _NOTES_DOUBTFUL_RE.search(notes):
        return True
    return False


def _backfill_180_schema(rows: list[dict]) -> list[str]:
    log: list[str] = []
    for row in rows:
        added = []
        for f, default in SCHEMA_FIELD_DEFAULTS_180.items():
            if f not in row:
                row[f] = copy.deepcopy(default)
                added.append(f)
        if added:
            log.append(f"  {row['kitchen_id']}: backfilled {sorted(added)!r}")
    return log


def _apply_180_migrations(rows: list[dict]) -> list[str]:
    log: list[str] = []
    for row in rows:
        kid = row["kitchen_id"]

        # Substream letter
        new_sub = _detect_substream(kid)
        if row["substream"] != new_sub:
            row["substream"] = new_sub
            log.append(f"  {kid}: substream → {new_sub!r}")

        # prenomen_is_kitchen_unknown — explicit `[Prenomen unknown]`
        new_unk = (row.get("prenomen") == "[Prenomen unknown]")
        if row["prenomen_is_kitchen_unknown"] != new_unk:
            row["prenomen_is_kitchen_unknown"] = new_unk
            log.append(f"  {kid}: prenomen_is_kitchen_unknown → {new_unk}")

        # is_co_regent_only — union of regex-detected (literal "co-rgt only"
        # in notes) + scholarly overrides (narrative-discussed co-regents
        # whose table cell lacks the marker).
        notes = row.get("notes_from_kitchen")
        new_cr = bool(
            (notes and _CO_REGENT_ONLY_NOTE_RE.search(notes))
            or kid in _CO_REGENT_SCHOLARLY_OVERRIDES
        )
        if row["is_co_regent_only"] != new_cr:
            row["is_co_regent_only"] = new_cr
            log.append(f"  {kid}: is_co_regent_only → {new_cr}")

        # existence_doubtful from `name` OR `notes_from_kitchen`
        new_ed = _detect_existence_doubtful(row.get("name") or "", notes)
        if row["existence_doubtful"] != new_ed:
            row["existence_doubtful"] = new_ed
            log.append(f"  {kid}: existence_doubtful → {new_ed}")

        # same_person_as
        new_sp = _SAME_PERSON_PAIRS.get(kid)
        if row["same_person_as"] != new_sp:
            row["same_person_as"] = new_sp
            log.append(f"  {kid}: same_person_as → {new_sp!r}")

        # corrected_end_bce
        new_corr = _CORRECTED_END_BCE.get(kid)
        if row["corrected_end_bce"] != new_corr:
            row["corrected_end_bce"] = new_corr
            log.append(f"  {kid}: corrected_end_bce → {new_corr!r}")

        # prenomens list — only populate for Piankhy two-prenomen row
        if kid == "25.03":
            if row["prenomens"] != _PIANKHY_PRENOMENS:
                row["prenomens"] = copy.deepcopy(_PIANKHY_PRENOMENS)
                log.append(f"  {kid}: prenomens → 2 entries")

    return log


def main() -> None:
    rows = [json.loads(line) for line in RECONCILED.read_text().splitlines() if line.strip()]

    override_log: list[str] = []

    # 0. Schema-audit pass FIRST — must run before concurrency so that
    # `_compute_concurrency` can read `corrected_end_bce` (single source
    # of truth for the 21H.06 typo correction). Per code-reviewer P1.
    schema_log = _backfill_180_schema(rows)
    schema_log += _apply_180_migrations(rows)
    if schema_log:
        override_log.extend(schema_log)

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
    # Print paths relative to the source dir's parent (not deep-rooted)
    # so the script works when copied into a tmp dir for idempotence
    # tests. Per the Beckerath #179 CI fix.
    print(f"Updated {RECONCILED.relative_to(SOURCE_DIR.parent)}")
    print(f"Updated {DIFF.relative_to(SOURCE_DIR.parent)}")


if __name__ == "__main__":
    main()
