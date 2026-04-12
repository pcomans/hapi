"""Integrity tests for authority source data.

These tests enforce structural invariants on authority source files
(e.g. reconciled.jsonl) so that silent corruption from future edits
is caught immediately.
"""

import json
from pathlib import Path

import pytest

AUTHORITY_SOURCES = Path(__file__).parent.parent / "pipeline" / "authority" / "sources"
HKW_DIR = AUTHORITY_SOURCES / "hkw-chronology-2006"


@pytest.fixture
def hkw_rows():
    path = HKW_DIR / "reconciled.jsonl"
    rows = []
    with open(path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pytest.fail(f"Invalid JSON on line {i}: {line[:80]}")
    return rows


class TestHKWIntegrity:
    def test_row_count(self, hkw_rows):
        assert len(hkw_rows) == 203

    def test_valid_kinds(self, hkw_rows):
        valid = {"period", "dynasty", "ruler"}
        for i, row in enumerate(hkw_rows, 1):
            assert row["kind"] in valid, f"Row {i}: invalid kind {row['kind']!r}"

    def test_ruler_dynasty_references_exist(self, hkw_rows):
        dynasty_numbers = {
            r["number"] for r in hkw_rows if r["kind"] == "dynasty" and r.get("number") is not None
        }
        for i, row in enumerate(hkw_rows, 1):
            if row["kind"] == "ruler" and row.get("dynasty") is not None:
                assert row["dynasty"] in dynasty_numbers, (
                    f"Row {i} ({row['display']}): dynasty {row['dynasty']} "
                    f"has no matching dynasty row"
                )

    def test_dynasty_parent_period_references_exist(self, hkw_rows):
        period_labels = {r["label"] for r in hkw_rows if r["kind"] == "period"}
        for i, row in enumerate(hkw_rows, 1):
            if row["kind"] == "dynasty" and row.get("parent_period") is not None:
                assert row["parent_period"] in period_labels, (
                    f"Row {i} ({row.get('label')}): parent_period "
                    f"{row['parent_period']!r} has no matching period row"
                )

    def test_dates_are_negative_or_null(self, hkw_rows):
        for i, row in enumerate(hkw_rows, 1):
            for field in ("start_bce", "end_bce"):
                val = row.get(field)
                if val is not None:
                    assert val < 0, (
                        f"Row {i} ({row.get('display') or row.get('label')}): "
                        f"{field}={val} should be negative (BCE)"
                    )

    def test_uncertainty_is_positive_or_null(self, hkw_rows):
        for i, row in enumerate(hkw_rows, 1):
            val = row.get("uncertainty_plus_years")
            if val is not None:
                assert val > 0, (
                    f"Row {i} ({row.get('display') or row.get('label')}): "
                    f"uncertainty_plus_years={val} should be positive"
                )

    def test_page_numbers_in_range(self, hkw_rows):
        valid_pages = set(range(490, 499))
        for i, row in enumerate(hkw_rows, 1):
            assert row["page"] in valid_pages, (
                f"Row {i}: page {row['page']} outside expected range 490-498"
            )
