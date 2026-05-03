"""Apply schema-audit corrections to HKW 2006's reconciled.jsonl.

This is the first `fix_rows.py` for the HKW source — HKW is a single-
transcriber extract (no 3-agent merge), so historically the only
artifact was `reconciled.jsonl` produced once by the transcribe pass.
Issue #176 audit found 6 P1 schema-shape findings; this module
implements the strict-all-6-P1 fix per the user-confirmed plan
(see `.claude/revise-priors/resolved/1777774535-hkw-176-scope-and-row-shape.md`).

Architecture mirrors the leprohon / dodson-hilton fix_rows.py:
- SCHEMA_FIELD_DEFAULTS: idempotent backfill pass for every new
  typed field. Every row gains every key with its default value.
- SPOT_CORRECTIONS: per-row migrations for the 12 multi-name slash/
  comma rows + 9 structured-fact-from-prose migrations + 2 dynasty-
  branch flags + per-bound-approximate splits.

Run:
    cd pipeline && uv run python pipeline/authority/sources/hkw-chronology-2006/fix_rows.py

Idempotent: re-running produces byte-identical reconciled.jsonl.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
RECONCILED = SOURCE_DIR / "reconciled.jsonl"


# === SCHEMA_FIELD_DEFAULTS ===================================================
#
# Every row gains every key with its default value via `backfill_schema_fields`
# (idempotent — rows already carrying the field are not overwritten).
#
# The closure tests in `tests/test_sources_hkw_chronology_2006.py` enforce
# that every row carries every key after fix_rows runs, so downstream
# consumers don't need to branch on present-vs-absent.
SCHEMA_FIELD_DEFAULTS: dict[str, object] = {
    # Issue #176 Shape A + Shape I: alternate name forms of the SAME person
    # (transliteration variants like `'Adj-ib`/`Anedjib`, regnal-name
    # changes like `Amenhotep IV`/`Akhenaten`). Reserved for SAME-PERSON
    # variants only — multi-ruler entries use `rulers` (below).
    "alt_names": [],
    # Issue #176 Shape A + Shape B + Shape I: list of per-ruler entries
    # for HKW's compound chronological-aggregate rows where N rulers
    # share one date range because HKW doesn't know the order. Each
    # entry: {name, prenomen, alternative_reading, alt_names}.
    # User-confirmed: HKW diverges from corpus convention (one row per
    # person) to preserve HKW's own grouping signal. Phase-A consumers
    # must iterate `rulers[]` for HKW-specifically.
    "rulers": [],
    # Issue #176 Shape J: typed flag for compound-row vs single-ruler.
    # True iff `rulers` is non-empty (5 rows in current corpus).
    "is_multi_ruler_entry": False,
    # Issue #176 Shape J: typed flag for HKW's name-uncertainty hedge
    # (one ruler, two candidate names — e.g. `'Ankhkheprure'` may be
    # Smenkhkare or Nefernefruaten per HKW p.493). Single-ruler row
    # with both candidates in alt_names + this flag = the canonical
    # encoding of the hedge.
    "name_uncertain": False,
    # Issue #176 Shape J + Shape C: typed coregency flag + reciprocal
    # link list. Replaces the prose-only "Coregency with X" notes.
    "is_coregency": False,
    "coregency_with": [],
    # Issue #176 Shape J + Shape C: typed rival-claimant flag.
    # Replaces "rival claimant" prose in note (L128 Amenmesses vs Sety II).
    "is_rival_claimant": False,
    "rival_claimant_of": None,
    # Issue #176 Shape D + Shape E: per-bound approximate flag.
    # Replaces the prose convention "approximate applies to end date
    # only; row-level approximate=true" (L149/L153). Row-level
    # `approximate` is preserved for backwards compatibility but is
    # the OR of the two per-bound flags after this PR.
    "start_year_approximate": False,
    "end_year_approximate": False,
    # Issue #176 Shape J: dynasty-branch flag for HKW's UE/LE split
    # of Dyn 23 (L161 vs L167). Default null; populated for the 2
    # rows with explicit branch labels.
    "dynasty_branch": None,
    # Issue #176 Shape D + Shape J: typed reason when start_year/
    # end_year are null. Replaces the convention of recording
    # "PDF shows '?–N'" or "Source prints '... — end year unknown
    # per HKW'" in `note` prose. When non-null, both bounds may also
    # be null; the reason is the explanatory text.
    "null_dates_reason": None,
}


def backfill_schema_fields(rows: list[dict]) -> list[str]:
    """Add every SCHEMA_FIELD_DEFAULTS key to every row that's missing it.

    Idempotent. Defensive `copy.deepcopy` on default values so future
    mutable defaults don't alias across rows.
    """
    log_lines: list[str] = []
    for row in rows:
        added: list[str] = []
        for field, default in SCHEMA_FIELD_DEFAULTS.items():
            if field not in row:
                row[field] = copy.deepcopy(default)
                added.append(field)
        if added:
            ident = _row_ident(row)
            log_lines.append(f"  {ident}: backfilled {sorted(added)!r}")
    return log_lines


def _row_ident(row: dict) -> str:
    """Compact row identifier for log lines: dynasty + display name."""
    kind = row.get("kind", "?")
    if kind == "ruler":
        return f"{kind} dyn-{row.get('dynasty')} {row.get('display')!r}"
    if kind == "dynasty":
        return f"{kind} {row.get('label')!r}"
    if kind == "period":
        return f"{kind} {row.get('display')!r}"
    return f"{kind} ?"


# === Per-row migrations =====================================================
#
# Format: each entry is a dict with row-locator keys + new field values.
# The locator keys (`kind`, `display`, `dynasty`, `label`) match the row
# 1:1; the rest of the keys are the new values to set. The row's existing
# values for `display`, `note`, etc. are also updated where needed.

# Cat 1+2 slash-row splits: HKW's first-listed-name stays as `display`
# per HKW's own ordering (avoids Egyptological-judgment-call about which
# transliteration is "canonical"). Second-listed goes to `alt_names`.
# Cat 2 (Smenkhkare'/Nefernefruaten) gets `name_uncertain=True` because
# HKW p.493's table layout encodes a "could be either" hedge, not a
# name-change-over-time event.
SLASH_ROW_MIGRATIONS = [
    # Cat 1 — same-person transliteration variants (1st-vs-modern form):
    {
        "_locator": ("ruler", None, "'Adj-ib/Anedjib", None),
        "display": "'Adj-ib",
        "alt_names": ["Anedjib"],
        "_rationale": "Cat 1 split: HKW prints '{display}' as a transliteration-variant pair; first-listed kept as `display` per HKW order.",
    },
    {
        "_locator": ("ruler", None, "Ra'djedef/Djedefre'", None),
        "display": "Ra'djedef",
        "alt_names": ["Djedefre'"],
        "_rationale": "Cat 1 split: HKW prints '{display}' as a transliteration-variant pair; first-listed kept as `display` per HKW order.",
    },
    {
        "_locator": ("ruler", None, "Ra'neferef/Neferefre'", None),
        "display": "Ra'neferef",
        "alt_names": ["Neferefre'"],
        "_rationale": "Cat 1 split: HKW prints '{display}' as a transliteration-variant pair; first-listed kept as `display` per HKW order.",
    },
    {
        "_locator": ("ruler", None, "Tut'ankhaten/amun", None),
        "display": "Tut'ankhaten",
        "alt_names": ["Tut'ankhamun"],
        "_rationale": "Cat 1 split: HKW prints '{display}' as a regnal-name-change pair (Aten → Amun after Year 4); first-listed kept as `display` per HKW order. Both names refer to the same king Tutankhamun.",
    },
    {
        "_locator": ("ruler", None, "Piye/Pi'ankhy", None),
        "display": "Piye",
        "alt_names": ["Pi'ankhy"],
        "_rationale": "Cat 1 split: HKW prints '{display}' as a transliteration-variant pair; first-listed kept as `display` per HKW order.",
    },
    # Cat 2 — same-person regnal-name change OR HKW's hedge:
    {
        "_locator": ("ruler", 18, "Amenhotep IV/Akhenaten", None),
        "display": "Amenhotep IV",
        "alt_names": ["Akhenaten"],
        "_rationale": "Cat 2 split: HKW p.492 verified — Amenhotep IV took the throne-name Akhenaten in regnal Year 5. One person; no `name_uncertain` flag.",
    },
    {
        "_locator": ("ruler", 18, "Smenkhkare'/Nefernefruaten", None),
        "display": "Smenkhkare'",
        "alt_names": ["Nefernefruaten"],
        "name_uncertain": True,
        "_rationale": "Cat 2 split with name_uncertain=True: HKW p.493 verified — the chronological slot 1336-1334 under prenomen `'Ankhkheprure'` could be either Smenkhkare or Nefernefruaten per HKW's own hedge. (NB: L118 has a SEPARATE `Nefernefruaten` row for 1334-? under different prenomen `'Ankhetkheprure'` — that's a distinct ruler, not a duplicate.)",
    },
]


# Cat 3 multi-ruler chronological-aggregate rows. Each compound display
# becomes a row-level summary; per-ruler data lives in `rulers: [...]`.
# `is_multi_ruler_entry=True` flags the row.
MULTI_RULER_MIGRATIONS = [
    {
        "_locator": ("ruler", 13, "Swadjtu, Ined, Hori, Dedumose", None),
        "is_multi_ruler_entry": True,
        "rulers": [
            {"name": "Swadjtu", "prenomen": None, "alternative_reading": None, "alt_names": []},
            {"name": "Ined", "prenomen": None, "alternative_reading": None, "alt_names": []},
            {"name": "Hori", "prenomen": None, "alternative_reading": None, "alt_names": []},
            {"name": "Dedumose", "prenomen": None, "alternative_reading": None, "alt_names": []},
        ],
        "_rationale": "Cat 3 multi-ruler: HKW packs 4 short-reigning Dyn-13 kings under one chronological slot because the order is unknown. `display` preserved as HKW's compound string; per-ruler entries in `rulers` for Phase-A joining.",
    },
    {
        "_locator": ("ruler", None, "Sobekhotep VIII, Nebiriau, Rahotep, Sobekemzaf I & II, Bebiankh", None),
        "is_multi_ruler_entry": True,
        "rulers": [
            {"name": "Sobekhotep VIII", "prenomen": None, "alternative_reading": None, "alt_names": []},
            {"name": "Nebiriau", "prenomen": None, "alternative_reading": None, "alt_names": []},
            {"name": "Rahotep", "prenomen": None, "alternative_reading": None, "alt_names": []},
            {"name": "Sobekemzaf I", "prenomen": None, "alternative_reading": None, "alt_names": []},
            {"name": "Sobekemzaf II", "prenomen": None, "alternative_reading": None, "alt_names": []},
            {"name": "Bebiankh", "prenomen": None, "alternative_reading": None, "alt_names": []},
        ],
        "_rationale": "Cat 3 multi-ruler: HKW packs 6 SIP-era rulers (Sobekemzaf I & II expanded to 2 entries from the `&`) under one chronological slot. `display` preserved as HKW's compound string.",
    },
    {
        "_locator": ("ruler", 23, "Osorkon III, Takelot III", None),
        "is_multi_ruler_entry": True,
        "rulers": [
            {"name": "Osorkon III", "prenomen": None, "alternative_reading": None, "alt_names": []},
            {"name": "Takelot III", "prenomen": None, "alternative_reading": None, "alt_names": []},
        ],
        "_rationale": "Cat 3 multi-ruler: HKW packs 2 Dyn-23 (UE) rulers under one chronological slot.",
    },
    {
        "_locator": ("ruler", 23, "Shoshenq IV, Rudamun, Iny", None),
        "is_multi_ruler_entry": True,
        "rulers": [
            {"name": "Shoshenq IV", "prenomen": None, "alternative_reading": None, "alt_names": []},
            {"name": "Rudamun", "prenomen": None, "alternative_reading": None, "alt_names": []},
            {"name": "Iny", "prenomen": None, "alternative_reading": None, "alt_names": []},
        ],
        "_rationale": "Cat 3 multi-ruler: HKW packs 3 Dyn-23 (UE) rulers under one chronological slot.",
    },
    {
        "_locator": ("ruler", 23, "Petubaste II (?), Osorkon IV", None),
        "is_multi_ruler_entry": True,
        "rulers": [
            {"name": "Petubaste II", "prenomen": None, "alternative_reading": None, "alt_names": ["Petubaste II (?)"]},
            {"name": "Osorkon IV", "prenomen": None, "alternative_reading": None, "alt_names": []},
        ],
        "_rationale": "Cat 3 multi-ruler: HKW packs 2 Dyn-23 (LE) rulers under one chronological slot. Petubaste II's existence-uncertainty hedge `(?)` preserved verbatim in `alt_names` for traceability; canonical `name` strips the parenthetical.",
    },
]


# Parenthetical-Horus-name extractions: HKW prints e.g. "Djoser (Netjery-khet)"
# where the parenthetical is an alternative Horus name, not a Greek form.
# The note field already documents this; the alt name moves to `alt_names`
# and the note is cleared (data now typed).
HORUS_NAME_MIGRATIONS = [
    {
        "_locator": ("ruler", 3, "Djoser", None),
        "alt_names": ["Netjery-khet"],
        "note": None,
        "_rationale": "HKW p. note documents 'Djoser (Netjery-khet)' parenthetical as an alternative Horus name. Migrated to `alt_names`; note cleared (information now typed).",
    },
    {
        "_locator": ("ruler", 4, "Khephren", None),
        "alt_names": ["Ra'kha'ef"],
        "note": None,
        "_rationale": "HKW note documents 'Khephren (Ra'kha'ef)' parenthetical as an alternative name. Migrated to `alt_names`; note cleared.",
    },
]


# Coregency facts hidden in `note` prose. Each entry sets typed
# `is_coregency=True`, populates `coregency_with` reciprocally, and
# clears the note (information now typed). The reciprocal-link contract
# is enforced by `test_coregency_pair_consistency`.
COREGENCY_MIGRATIONS = [
    {
        "_locator": ("ruler", 12, "Senwosret I", None),
        "is_coregency": True,
        "coregency_with": ["Amenemhet I"],
        "note": None,
        "_rationale": "Coregency fact extracted from prose note: 'Dates overlap with Amenemhet I (1920–1910) indicating coregency'. Typed; note cleared.",
    },
    {
        "_locator": ("ruler", 18, "Thutmose III", None),
        "is_coregency": True,
        "coregency_with": ["Hatshepsut"],
        "note": None,
        "_rationale": "Coregency fact extracted from prose note 'Coregency with Hatshepsut 1479–1458'. Typed; note cleared.",
    },
    {
        "_locator": ("ruler", 18, "Hatshepsut", None),
        "is_coregency": True,
        "coregency_with": ["Thutmose III"],
        "note": None,
        "_rationale": "Coregency fact extracted from prose note 'Coregency with Thutmose III'. Typed; note cleared. Reciprocal of Thutmose III entry.",
    },
    {
        "_locator": ("ruler", None, "Teos", None),
        "is_coregency": True,
        "coregency_with": ["Nectanebo I"],
        # Keep the longer note about BCE-counting-down because it's
        # genuinely scholarly explanation of HOW the coregency is
        # encoded by the date ranges, not just the FACT of coregency.
        "_rationale": "Coregency fact extracted from prose note 'Teos (365-360) overlaps Nectanebo I (380-362) by three years; ... implies a coregency, not an interregnum'. is_coregency typed; note retained because it explains the date-overlap reasoning Phase-A consumers need.",
    },
    # Reciprocal entries — without these, the typed contract
    # `if A.coregency_with includes B then B.coregency_with includes A`
    # fails on B's side. The other-side rows (Amenemhet I, Nectanebo I)
    # don't have explicit notes flagging the coregency in HKW's source —
    # the fact is documented on the OTHER ruler's row — but the
    # reciprocal link is required for the typed contract to hold.
    {
        "_locator": ("ruler", 12, "Amenemhet I", None),
        "is_coregency": True,
        "coregency_with": ["Senwosret I"],
        "_rationale": "Reciprocal of Senwosret I's coregency entry. Coregency fact lives on Senwosret I's row in HKW's source; reciprocal added to maintain the typed `is_coregency / coregency_with` symmetric contract.",
    },
    {
        "_locator": ("ruler", None, "Nectanebo I", None),
        "is_coregency": True,
        "coregency_with": ["Teos"],
        "_rationale": "Reciprocal of Teos's coregency entry. Same rationale as Amenemhet I above.",
    },
]


# Rival-claimant fact (L128).
RIVAL_CLAIMANT_MIGRATIONS = [
    {
        "_locator": ("ruler", 19, "Amenmesses", None),
        "is_rival_claimant": True,
        "rival_claimant_of": "Sety II",
        "note": None,
        "_rationale": "Rival-claimant fact extracted from prose note 'Overlaps with Sety II (1202–1200); rival claimant'. Typed; note cleared.",
    },
]


# Per-bound approximate split (L149/L153).
PER_BOUND_APPROX_MIGRATIONS = [
    {
        "_locator": ("ruler", 21, "Siamun", None),
        "start_year_approximate": False,
        "end_year_approximate": True,
        "note": "PDF shows '986–ca. 968'",
        "_rationale": "Per-bound approximate split: HKW prints '986–ca. 968'; only end year is approximate. Typed `end_year_approximate=True` replaces the row-level `approximate=true` convention with per-bound granularity. Note trimmed to source-quote only.",
    },
    {
        "_locator": ("ruler", 22, "Osorkon I", None),
        "start_year_approximate": False,
        "end_year_approximate": True,
        "note": "PDF shows '922–ca. 888'",
        "_rationale": "Per-bound approximate split: HKW prints '922–ca. 888'; only end year is approximate. Note trimmed to source-quote only.",
    },
]


# Dynasty-branch flags (UE / LE for Dyn 23 split).
DYNASTY_BRANCH_MIGRATIONS = [
    {
        "_locator": ("dynasty", 23, None, "Dyn. 23 (UE) and Rival Kings"),
        "dynasty_branch": "UE",
        "_rationale": "HKW splits Dyn. 23 into Upper-Egyptian (UE) and Lower-Egyptian (LE) branches via parenthetical labels. Typed `dynasty_branch` replaces the convention of disambiguating two `Dyn. 23` rows by parenthetical-text-in-label.",
    },
    {
        "_locator": ("dynasty", 23, None, "Dyn. 23 (LE)"),
        "dynasty_branch": "LE",
        "_rationale": "HKW Dyn-23 LE branch flag.",
    },
]


# Null-dates reason (replaces the convention of explaining unknown bounds
# in `note` prose). Migrated for the most common cases (`PDF shows '?–N'`
# / `Source prints '... — end year unknown per HKW'`). The note prose
# stays for transcription provenance (e.g. "initial Claude transcription
# pass misread the '?' as a '2'") since that's information about the
# reconciliation, not about the data.
NULL_DATES_MIGRATIONS = [
    {
        "_locator": ("ruler", 1, "Nar-mer", None),
        "null_dates_reason": "HKW prints '2900–?+25' — end year unknown per HKW source.",
        "_rationale": "Null-dates reason typed. Note retained for transcription-correction provenance.",
    },
    {
        "_locator": ("ruler", 3, "Kha'ba", None),
        "null_dates_reason": "HKW prints '2559–?+25' — end year unknown per HKW source.",
        "_rationale": "Null-dates reason typed. Note retained for transcription-correction provenance.",
    },
    # Several other rows have similar "PDF shows '?–N+25'" notes; those
    # are left as-is in this pass since they don't have null bounds (the
    # `?` was reconciled to a value). The two above are the rows where
    # the audit specifically flagged the `?` → `null` reconciliation.
]


ALL_MIGRATIONS: list[list[dict]] = [
    SLASH_ROW_MIGRATIONS,
    MULTI_RULER_MIGRATIONS,
    HORUS_NAME_MIGRATIONS,
    COREGENCY_MIGRATIONS,
    RIVAL_CLAIMANT_MIGRATIONS,
    PER_BOUND_APPROX_MIGRATIONS,
    DYNASTY_BRANCH_MIGRATIONS,
    NULL_DATES_MIGRATIONS,
]


def _find_row(rows: list[dict], locator: tuple) -> dict | None:
    """Locate a row by (kind, dynasty_or_number, display, label) tuple.
    Any None in the locator is treated as a wildcard. The 2nd field
    matches `dynasty` for `kind=ruler` rows and `number` for
    `kind=dynasty` rows (HKW's schema uses different field names for
    dynasty-affiliation depending on row kind)."""
    kind, dynasty_or_number, display, label = locator
    candidates = []
    for r in rows:
        if kind is not None and r.get("kind") != kind:
            continue
        if dynasty_or_number is not None:
            r_kind = r.get("kind")
            if r_kind == "dynasty":
                if r.get("number") != dynasty_or_number:
                    continue
            else:
                if r.get("dynasty") != dynasty_or_number:
                    continue
        if display is not None and r.get("display") != display:
            continue
        if label is not None and r.get("label") != label:
            continue
        candidates.append(r)
    if len(candidates) > 1:
        raise ValueError(
            f"Locator {locator!r} matched {len(candidates)} rows; "
            f"tighten the locator to disambiguate."
        )
    return candidates[0] if candidates else None


def apply_migrations(rows: list[dict]) -> list[str]:
    """Apply every migration to its target row. Each migration sets
    each non-locator/non-rationale key to its declared value. Idempotent
    on stable input."""
    log_lines: list[str] = []
    for chunk in ALL_MIGRATIONS:
        for entry in chunk:
            locator = entry["_locator"]
            row = _find_row(rows, locator)
            if row is None:
                # Already-migrated case: locator's `display` may now
                # reflect the post-migration value rather than the
                # pre-migration compound. Try again with the new display
                # if entry sets it.
                if "display" in entry:
                    new_display = entry["display"]
                    new_locator = (locator[0], locator[1], new_display, locator[3])
                    row = _find_row(rows, new_locator)
                if row is None:
                    raise KeyError(
                        f"Migration target not found for locator {locator!r}; "
                        f"either the row was deleted or the locator is wrong."
                    )
            ident = _row_ident(row)
            for k, v in entry.items():
                if k.startswith("_"):
                    continue
                old = row.get(k)
                row[k] = v
                if old != v:
                    log_lines.append(
                        f"  {ident}: {k} = {json.dumps(v, ensure_ascii=False)} "
                        f"(was {json.dumps(old, ensure_ascii=False)})"
                    )
    return log_lines


def main() -> None:
    rows = [json.loads(line) for line in RECONCILED.read_text().splitlines() if line.strip()]
    backfill_log = backfill_schema_fields(rows)
    migration_log = apply_migrations(rows)
    RECONCILED.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows)
        + "\n"
    )
    print(f"Backfilled {len(backfill_log)} row-fields; applied "
          f"{len(migration_log)} per-row corrections this run.")
    print(f"Updated {RECONCILED.relative_to(RECONCILED.parents[4])}")


if __name__ == "__main__":
    main()
