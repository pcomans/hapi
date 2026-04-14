"""Structural value-assertion test for the Shaw 2000 source extract.

Per handoff rule 5 (tests assert values, not absence of errors) and the
workflow step "Write a source-specific test ... that loads your JSONL and
asserts specific field values for 3 known rows."
"""

from __future__ import annotations

import json
from pathlib import Path

SOURCE_DIR = Path(__file__).parent.parent / "pipeline" / "authority" / "sources" / "shaw-ohae-2000"
JSONL = SOURCE_DIR / "reconciled.jsonl"


def _rows() -> list[dict]:
    return [json.loads(line) for line in JSONL.read_text().splitlines() if line.strip()]


def _row_for_chapter(chapter_number: int) -> dict:
    matches = [r for r in _rows() if r["chapter_number"] == chapter_number]
    if len(matches) != 1:
        raise AssertionError(
            f"Expected exactly one row for chapter {chapter_number}, found {len(matches)}"
        )
    return matches[0]


def test_row_count_is_twelve_dated_chapters() -> None:
    """Shaw 2000 has 15 chapters; 12 carry a single BCE date range on the opening banner.

    Excluded: ch 1 (Introduction), ch 2 (Prehistory - no BCE range on banner),
    ch 11 (Egypt and the Outside World - thematic).
    """
    rows = _rows()
    assert len(rows) == 12, f"Expected 12 dated-period rows, got {len(rows)}"
    chapter_numbers = sorted(r["chapter_number"] for r in rows)
    assert chapter_numbers == [3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15]


def test_naqada_period_row() -> None:
    """Chapter 3 banner on p. 41: 'The Naqada Period (c.4000-3200 bc)'."""
    row = _row_for_chapter(3)
    assert row["period_name"] == "Naqada Period"
    assert row["chapter_title"] == "The Naqada Period (c.4000-3200 bc)"
    assert row["date_range_start_bce"] == -4000
    assert row["date_range_end_bce"] == -3200
    assert row["date_qualifier"] == "c."
    assert row["sub_periods"] == []
    assert row["source_citation"]["page"] == 41
    assert "978-0-19-280458-7" in row["source_citation"]["edition"]


def test_old_kingdom_row() -> None:
    """Chapter 5 banner on p. 83: 'The Old Kingdom (c.2686-2160 bc)'."""
    row = _row_for_chapter(5)
    assert row["period_name"] == "Old Kingdom"
    assert row["date_range_start_bce"] == -2686
    assert row["date_range_end_bce"] == -2160
    assert row["date_qualifier"] == "c."
    assert row["source_citation"]["page"] == 83


def test_ptolemaic_period_row_has_no_circa_qualifier() -> None:
    """Chapter 14 banner on p. 388: 'The Ptolemaic Period (332-30 bc)' - no 'c.' prefix."""
    row = _row_for_chapter(14)
    assert row["period_name"] == "Ptolemaic Period"
    assert row["date_range_start_bce"] == -332
    assert row["date_range_end_bce"] == -30
    assert row["date_qualifier"] is None, (
        "Ptolemaic banner gives unqualified dates; date_qualifier must be null"
    )
    assert row["source_citation"]["page"] == 388


def test_roman_period_row_crosses_bce_ce_boundary() -> None:
    """Chapter 15 banner on p. 414: 'The Roman Period (30 bc-ad 395)'.

    Verifies the BCE/CE sign convention: BCE negative, CE positive.
    """
    row = _row_for_chapter(15)
    assert row["date_range_start_bce"] == -30
    assert row["date_range_end_bce"] == 395
    assert row["source_citation"]["page"] == 414
