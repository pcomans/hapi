"""Structural value-assertion test for the Shaw 2000 source extract.

Per constitutional rule 5: tests assert values, and every populated field
on a sampled fixture row is asserted — not just fields "relevant to the
theme" of the test.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

SOURCE_DIR = Path(__file__).parent.parent / "pipeline" / "authority" / "sources" / "shaw-ohae-2000"
JSONL = SOURCE_DIR / "reconciled.jsonl"

EDITION = "OUP 2003 paperback (= 2000 hardback), ISBN 978-0-19-280458-7"


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    return tuple(json.loads(line) for line in JSONL.read_text().splitlines() if line.strip())


def _row_for_chapter(chapter_number: int) -> dict:
    matches = [r for r in _rows() if r["chapter_number"] == chapter_number]
    if len(matches) != 1:
        raise AssertionError(
            f"Expected exactly one row for chapter {chapter_number}, found {len(matches)}"
        )
    return matches[0]


def test_row_count_and_dated_chapter_set() -> None:
    """Shaw 2000 has 15 chapters; 13 carry a BCE date range on the opening banner.

    Excluded: ch 1 (Introduction - front matter, no BCE range) and ch 11
    (Egypt and the Outside World - thematic essay, no BCE range).
    """
    rows = _rows()
    assert len(rows) == 13, f"Expected 13 dated-period rows, got {len(rows)}"
    chapter_numbers = sorted(r["chapter_number"] for r in rows)
    assert chapter_numbers == [2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15]


def test_all_rows_share_edition_and_have_complete_citations() -> None:
    """Every row has a complete source_citation (page + edition) per rule 1."""
    for row in _rows():
        citation = row["source_citation"]
        assert citation["edition"] == EDITION, row
        assert isinstance(citation["page"], int), row
        assert citation["page"] > 0, row


def test_prehistory_row_chapter_2() -> None:
    """Ch 2 banner on p. 16: 'Prehistory: From the Palaeolithic to the Badarian Culture (c.700,000-4000 bc)'.

    `period_name` uses Shaw's running-header word 'Prehistory' as the compact
    stub (consistent with other rows which drop the chapter title's leading
    'The' and the parenthetical date).
    """
    row = _row_for_chapter(2)
    assert row["period_name"] == "Prehistory"
    assert (
        row["chapter_title"]
        == "Prehistory: From the Palaeolithic to the Badarian Culture (c.700,000-4000 bc)"
    )
    assert row["date_range_start_bce"] == -700000
    assert row["date_range_end_bce"] == -4000
    assert row["date_qualifier"] == "c."
    assert row["sub_periods"] == []
    assert "source_note" not in row
    assert row["source_citation"] == {"page": 16, "edition": EDITION}


def test_composite_rows_carry_source_notes() -> None:
    """Ch 4, 9, 10 carry Shaw-specific framings that don't map 1:1 to canonical
    Egyptological periods; each carries a `source_note` flagging this for Phase A.
    Other rows must NOT have a `source_note` (the field is for paraphrase cases only).
    """
    composite_chapters = {4, 9, 10}
    for row in _rows():
        if row["chapter_number"] in composite_chapters:
            assert "source_note" in row, row
            assert row["source_note"].strip(), row
        else:
            assert "source_note" not in row, row


def test_naqada_period_row_with_subperiods() -> None:
    """Ch 3 banner on p. 41 plus Midant-Reynes' body sub-period BCE breakdown (pp. 42-43)."""
    row = _row_for_chapter(3)
    assert row["period_name"] == "Naqada Period"
    assert row["chapter_title"] == "The Naqada Period (c.4000-3200 bc)"
    assert row["date_range_start_bce"] == -4000
    assert row["date_range_end_bce"] == -3200
    assert row["date_qualifier"] == "c."
    assert row["sub_periods"] == [
        {"name": "Naqada I (Amratian)", "start_bce": -4000, "end_bce": -3500},
        {"name": "Naqada II (Gerzean)", "start_bce": -3500, "end_bce": -3200},
    ]
    assert row["source_citation"] == {"page": 41, "edition": EDITION}


def test_old_kingdom_row() -> None:
    """Ch 5 banner on p. 83: 'The Old Kingdom (c.2686-2160 bc)'."""
    row = _row_for_chapter(5)
    assert row["period_name"] == "Old Kingdom"
    assert row["chapter_title"] == "The Old Kingdom (c.2686-2160 bc)"
    assert row["date_range_start_bce"] == -2686
    assert row["date_range_end_bce"] == -2160
    assert row["date_qualifier"] == "c."
    assert row["sub_periods"] == []
    assert row["source_citation"] == {"page": 83, "edition": EDITION}


def test_third_intermediate_row_qualifier_null_interior() -> None:
    """Ch 12 banner on p. 324: '(1069-664 bc)' - no 'c.' prefix.

    Interior row (not at the BCE/CE boundary) exercising qualifier-null
    independently of the sign-convention logic tested below.
    """
    row = _row_for_chapter(12)
    assert row["period_name"] == "Third Intermediate Period"
    assert row["chapter_title"] == "The Third Intermediate Period (1069-664 bc)"
    assert row["date_range_start_bce"] == -1069
    assert row["date_range_end_bce"] == -664
    assert row["date_qualifier"] is None
    assert row["sub_periods"] == []
    assert row["source_citation"] == {"page": 324, "edition": EDITION}


def test_roman_period_row_crosses_bce_ce_boundary() -> None:
    """Ch 15 banner on p. 414: 'The Roman Period (30 bc-ad 395)'.

    BCE negative, CE positive.
    """
    row = _row_for_chapter(15)
    assert row["period_name"] == "Roman Period"
    assert row["chapter_title"] == "The Roman Period (30 bc-ad 395)"
    assert row["date_range_start_bce"] == -30
    assert row["date_range_end_bce"] == 395
    assert row["date_qualifier"] is None
    assert row["sub_periods"] == []
    assert row["source_citation"] == {"page": 414, "edition": EDITION}
