"""Structural value-assertion test for the Hölbl 2001 Argead-bridge extract.

Per constitutional rule 5: tests assert values, and every populated field
on a sampled fixture row is asserted — not just fields "relevant to the
theme" of the test. Because this extract is exactly three rows, each row
gets a dedicated test that asserts every field.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

SOURCE_DIR = (
    Path(__file__).parent.parent
    / "pipeline"
    / "authority"
    / "sources"
    / "holbl-2001-argead"
)
JSONL = SOURCE_DIR / "reconciled.jsonl"

EDITION = "Routledge 2001"
PDF_PAGES = "349-351"


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    return tuple(
        json.loads(line) for line in JSONL.read_text().splitlines() if line.strip()
    )


def _row_for_id(holbl_id: str) -> dict:
    matches = [r for r in _rows() if r["holbl_id"] == holbl_id]
    if len(matches) != 1:
        raise AssertionError(
            f"Expected exactly one row for {holbl_id!r}, found {len(matches)}"
        )
    return matches[0]


def test_row_count_and_id_set() -> None:
    """Hölbl's Appendix opens with three Argead reign banners on pp 349–351.

    Everything after the Alexander IV banner (Interregnum, Ptolemy I, Ptolemies
    II–XV) is out of scope — pharaoh.se covers the Ptolemaic dynasty.
    """
    rows = _rows()
    assert len(rows) == 3, f"Expected 3 Argead rows, got {len(rows)}"
    ids = sorted(r["holbl_id"] for r in rows)
    assert ids == ["argead.01", "argead.02", "argead.03"]


def test_all_rows_share_citation_and_fixed_fields() -> None:
    """Every row shares the per-source literals: kind, source_citation, and
    the five always-null schema slots (greek_form, alternative_reading,
    prenomen, uncertainty_plus_years, dynasty) plus approximate=false.
    """
    always_null = (
        "greek_form",
        "alternative_reading",
        "prenomen",
        "uncertainty_plus_years",
        "dynasty",
    )
    for row in _rows():
        assert row["kind"] == "ruler", row
        assert row["approximate"] is False, row
        for field in always_null:
            assert row[field] is None, f"{field} must be null on {row['holbl_id']}"
        assert row["source_citation"] == {"pdf_pages": PDF_PAGES, "edition": EDITION}


def test_alexander_the_great_row() -> None:
    """argead.01 — banner 'ALEXANDER THE GREAT', reign 332 → 323 BCE, p. 349."""
    row = _row_for_id("argead.01")
    assert row["display"] == "Alexander the Great"
    assert row["start_year"] == -332
    assert row["end_year"] == -323
    assert row["page"] == 349
    assert "ALEXANDER THE GREAT" in row["note"]
    assert "332" in row["note"]
    assert "323" in row["note"]


def test_philip_iii_arrhidaios_row() -> None:
    """argead.02 — banner 'PHILIP III ARRHIDAIOS // Ptolemy as Satrap',
    reign 323 → 317 BCE (murdered Autumn 317), p. 349.
    """
    row = _row_for_id("argead.02")
    assert row["display"] == "Philip III Arrhidaios"
    assert row["start_year"] == -323
    assert row["end_year"] == -317
    assert row["page"] == 349
    assert "PHILIP III ARRHIDAIOS" in row["note"]
    assert "Ptolemy as Satrap" in row["note"]


def test_alexander_iv_row_compound_date_convention() -> None:
    """argead.03 — banner 'ALEXANDER IV // Ptolemy as Satrap', reign
    317 → 310 BCE. Hölbl prints the terminal year as '310/09'; we take the
    earlier boundary per the compound-date convention documented in
    transcribe.md § 'Compound dates'. The compound form is preserved in
    the `note` cell for reviewer audit.
    """
    row = _row_for_id("argead.03")
    assert row["display"] == "Alexander IV"
    assert row["start_year"] == -317
    assert row["end_year"] == -310
    assert row["page"] == 350
    assert "ALEXANDER IV" in row["note"]
    assert "Ptolemy as Satrap" in row["note"]
    assert "310/09" in row["note"]
