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
WIKI_PTOLEMAIC_DIR = AUTHORITY_SOURCES / "wikipedia-ptolemaic"


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


@pytest.fixture
def wiki_ptolemaic_rows():
    path = WIKI_PTOLEMAIC_DIR / "reconciled.jsonl"
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


class TestWikiPtolemaicIntegrity:
    def test_row_count(self, wiki_ptolemaic_rows):
        assert len(wiki_ptolemaic_rows) == 24

    def test_valid_kinds(self, wiki_ptolemaic_rows):
        valid = {"period", "dynasty", "ruler"}
        for i, row in enumerate(wiki_ptolemaic_rows, 1):
            assert row["kind"] in valid, f"Row {i}: invalid kind {row['kind']!r}"

    def test_dates_are_negative_or_null(self, wiki_ptolemaic_rows):
        for i, row in enumerate(wiki_ptolemaic_rows, 1):
            for field in ("start_bce", "end_bce"):
                val = row.get(field)
                if val is not None:
                    assert val < 0, (
                        f"Row {i} ({row.get('display') or row.get('label')}): "
                        f"{field}={val} should be negative (BCE)"
                    )

    def test_all_dates_within_ptolemaic_range(self, wiki_ptolemaic_rows):
        for i, row in enumerate(wiki_ptolemaic_rows, 1):
            for field in ("start_bce", "end_bce"):
                val = row.get(field)
                if val is not None:
                    assert -323 <= val <= -30, (
                        f"Row {i} ({row.get('display') or row.get('label')}): "
                        f"{field}={val} outside Ptolemaic range (-323 to -30)"
                    )

    def test_page_is_null(self, wiki_ptolemaic_rows):
        for i, row in enumerate(wiki_ptolemaic_rows, 1):
            assert row["page"] is None, (
                f"Row {i}: page should be null for Wikipedia source"
            )

    def test_dynasty_is_null(self, wiki_ptolemaic_rows):
        rulers = [r for r in wiki_ptolemaic_rows if r["kind"] == "ruler"]
        for row in rulers:
            assert row["dynasty"] is None, (
                f"{row['display']}: dynasty should be null for Ptolemaic rulers"
            )

    def test_has_period_entry(self, wiki_ptolemaic_rows):
        periods = [r for r in wiki_ptolemaic_rows if r["kind"] == "period"]
        assert len(periods) == 1
        assert periods[0]["label"] == "Ptolemaic Period"

    def test_ptolemy_vii_has_null_dates(self, wiki_ptolemaic_rows):
        p7 = [r for r in wiki_ptolemaic_rows if r.get("display", "").startswith("Ptolemy VII ") and not r.get("display", "").startswith("Ptolemy VIII")]
        assert len(p7) == 1, "Ptolemy VII should have exactly one row"
        assert p7[0]["start_bce"] is None and p7[0]["end_bce"] is None, (
            "Ptolemy VII never formally reigned; dates should be null"
        )
