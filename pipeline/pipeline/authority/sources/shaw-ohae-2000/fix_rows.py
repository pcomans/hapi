"""Apply issue #181 schema-audit typed flags to Shaw OHAE 2000 reconciled.jsonl.

Shaw OHAE is a single-transcriber extract from one printed book — there is
no merge.py / multi-agent reconciliation step. This `fix_rows.py` exists
solely to apply the issue #181 typed-flag backfill in an idempotent
script-driven way (rather than hand-editing reconciled.jsonl, which would
violate `feedback_never_edit_reconciled_jsonl.md` even though the file
isn't merge-generated here).

Run:
    cd pipeline && uv run python pipeline/authority/sources/shaw-ohae-2000/fix_rows.py

Idempotent: re-runs produce 0 schema field changes.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
RECONCILED = SOURCE_DIR / "reconciled.jsonl"


# === Issue #181 schema-audit additions =======================================
#
# Per audit: 1 conditional P1 + 6 P2. Strict-all-applicable-P1 policy
# applies. Three typed flags added; each is mechanically derivable from
# existing fields so the migration is loss-free.

SCHEMA_FIELD_DEFAULTS_181: dict[str, object] = {
    # Shape J P1 (escalates to P1 because Phase A consumers will read
    # `date_range_start_bce` arithmetically). Distinguishes the
    # geologically-dated Palaeolithic chapter (ch 2: c.700,000-4000 bc)
    # — where `-700000` is a rounded order-of-magnitude figure, NOT a
    # precise BCE year — from regnal-dated chapters where the
    # endpoints are ±decade-precise. Enum: `geological` |
    # `regnal_approximate` | `regnal_precise`.
    "date_precision": None,
    # Shape J P2: True for chapters whose chapter_title spans more than
    # one Egyptological period (ch 10 "Amarna Period and the Later New
    # Kingdom" stitches Amarna + post-Amarna 18-20 Dyn).
    "is_composite": False,
    # Shape J P2: True for chapters whose date range crosses the BCE/CE
    # boundary (ch 15 Roman Period: 30 bc–ad 395). Without this typed
    # flag, downstream arithmetic on `date_range_end_bce` (which is
    # POSITIVE 395 for the only such row) is silently wrong.
    "crosses_bce_ce": False,
}


# Composite chapters per audit's reading of Shaw's chapter_title prose.
# Conservative: only include chapters where the title literally chains
# two Egyptological period names with "and" / multiple capitalized
# period nouns.
_COMPOSITE_CHAPTERS = {
    10,  # "The Amarna Period and the Later New Kingdom"
}

# Per audit: ch 2 Palaeolithic is the only geologically-dated chapter.
# Detection: `date_range_start_bce <= -100000` is the cleanest signal
# (no Egyptological chronology spans pre-Holocene).
_GEOLOGICAL_THRESHOLD_BCE = -100_000


def _detect_date_precision(start: int | None, end: int | None) -> str:
    """Mechanical classification of date precision."""
    if start is None or end is None:
        return "regnal_approximate"
    if start <= _GEOLOGICAL_THRESHOLD_BCE:
        return "geological"
    return "regnal_approximate"


def _detect_crosses_bce_ce(start: int | None, end: int | None) -> bool:
    """True if start_bce is negative (BCE) and end_bce is positive (CE).
    The Roman Period ch 15 prints `30 bc-ad 395` and is encoded as
    `(start=-30, end=+395)` — the only such row in Shaw OHAE."""
    return (
        start is not None and end is not None
        and start < 0 and end > 0
    )


def _backfill_181_schema(rows: list[dict]) -> list[str]:
    log: list[str] = []
    for row in rows:
        added = []
        for f, default in SCHEMA_FIELD_DEFAULTS_181.items():
            if f not in row:
                row[f] = copy.deepcopy(default)
                added.append(f)
        if added:
            log.append(f"  ch {row.get('chapter_number')}: backfilled {sorted(added)!r}")
    return log


def _apply_181_migrations(rows: list[dict]) -> list[str]:
    log: list[str] = []
    for row in rows:
        ch = row.get("chapter_number")
        s = row.get("date_range_start_bce")
        e = row.get("date_range_end_bce")

        new_dp = _detect_date_precision(s, e)
        if row["date_precision"] != new_dp:
            row["date_precision"] = new_dp
            log.append(f"  ch {ch}: date_precision → {new_dp!r}")

        new_comp = ch in _COMPOSITE_CHAPTERS
        if row["is_composite"] != new_comp:
            row["is_composite"] = new_comp
            log.append(f"  ch {ch}: is_composite → {new_comp}")

        new_cross = _detect_crosses_bce_ce(s, e)
        if row["crosses_bce_ce"] != new_cross:
            row["crosses_bce_ce"] = new_cross
            log.append(f"  ch {ch}: crosses_bce_ce → {new_cross}")

    return log


def main() -> None:
    rows = [json.loads(line) for line in RECONCILED.read_text().splitlines() if line.strip()]
    log = _backfill_181_schema(rows)
    log += _apply_181_migrations(rows)
    RECONCILED.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows) + "\n"
    )
    print(f"Issue #181 schema pass: {len(log)} field changes")
    for line in log[:20]:
        print(line)
    if len(log) > 20:
        print(f"  ... and {len(log) - 20} more")
    print(f"Updated {RECONCILED.relative_to(SOURCE_DIR.parent)}")


if __name__ == "__main__":
    main()
