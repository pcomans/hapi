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
WIKIDATA_PHARAOHS_DIR = AUTHORITY_SOURCES / "wikidata-pharaohs"


def load_jsonl(path: Path) -> list[dict]:
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


@pytest.fixture
def hkw_rows():
    return load_jsonl(HKW_DIR / "reconciled.jsonl")


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
            for field in ("start_year", "end_year"):
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
    return load_jsonl(WIKI_PTOLEMAIC_DIR / "reconciled.jsonl")


class TestWikiPtolemaicIntegrity:
    def test_row_count(self, wiki_ptolemaic_rows):
        assert len(wiki_ptolemaic_rows) == 24

    def test_valid_kinds(self, wiki_ptolemaic_rows):
        valid = {"period", "dynasty", "ruler"}
        for i, row in enumerate(wiki_ptolemaic_rows, 1):
            assert row["kind"] in valid, f"Row {i}: invalid kind {row['kind']!r}"

    def test_dates_are_negative_or_null(self, wiki_ptolemaic_rows):
        for i, row in enumerate(wiki_ptolemaic_rows, 1):
            for field in ("start_year", "end_year"):
                val = row.get(field)
                if val is not None:
                    assert val < 0, (
                        f"Row {i} ({row.get('display') or row.get('label')}): "
                        f"{field}={val} should be negative (BCE)"
                    )

    def test_all_dates_within_ptolemaic_range(self, wiki_ptolemaic_rows):
        for i, row in enumerate(wiki_ptolemaic_rows, 1):
            for field in ("start_year", "end_year"):
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
        p7 = [r for r in wiki_ptolemaic_rows if r.get("display", "").startswith("Ptolemy VII ")]
        assert len(p7) == 1, "Ptolemy VII should have exactly one row"
        assert p7[0]["start_year"] is None and p7[0]["end_year"] is None, (
            "Ptolemy VII never formally reigned; dates should be null"
        )


@pytest.fixture
def wikidata_pharaoh_rows():
    return load_jsonl(WIKIDATA_PHARAOHS_DIR / "reconciled.jsonl")


class TestWikidataPharaohsIntegrity:
    def test_row_count_minimum(self, wikidata_pharaoh_rows):
        # Wikidata is a living dataset; count may grow but should never drop below ~500
        assert len(wikidata_pharaoh_rows) >= 500, (
            f"Expected at least 500 pharaohs, got {len(wikidata_pharaoh_rows)}"
        )

    def test_all_rows_are_rulers(self, wikidata_pharaoh_rows):
        for i, row in enumerate(wikidata_pharaoh_rows, 1):
            assert row["kind"] == "ruler", f"Row {i}: kind should be 'ruler', got {row['kind']!r}"

    def test_every_row_has_qid(self, wikidata_pharaoh_rows):
        for i, row in enumerate(wikidata_pharaoh_rows, 1):
            assert row["qid"] is not None, f"Row {i}: missing qid"
            assert row["qid"].startswith("Q"), f"Row {i}: qid {row['qid']!r} should start with Q"

    def test_qids_are_unique(self, wikidata_pharaoh_rows):
        qids = [row["qid"] for row in wikidata_pharaoh_rows]
        assert len(qids) == len(set(qids)), "Duplicate QIDs found"

    def test_every_row_has_display_name(self, wikidata_pharaoh_rows):
        for i, row in enumerate(wikidata_pharaoh_rows, 1):
            assert row["display"] is not None and len(row["display"]) > 0, (
                f"Row {i}: missing display name"
            )

    def test_dates_are_negative_or_null(self, wikidata_pharaoh_rows):
        for i, row in enumerate(wikidata_pharaoh_rows, 1):
            for field in ("start_year", "end_year"):
                val = row.get(field)
                if val is not None:
                    assert val < 0, (
                        f"Row {i} ({row['display']}): {field}={val} should be negative (BCE)"
                    )

    def test_date_ranges_are_ordered(self, wikidata_pharaoh_rows):
        for i, row in enumerate(wikidata_pharaoh_rows, 1):
            s, e = row.get("start_year"), row.get("end_year")
            if s is not None and e is not None:
                assert s <= e, (
                    f"Row {i} ({row['display']}): inverted date range "
                    f"start_year={s} > end_year={e}"
                )

    def test_dynasty_numbers_in_valid_range(self, wikidata_pharaoh_rows):
        for i, row in enumerate(wikidata_pharaoh_rows, 1):
            dyn = row.get("dynasty")
            if dyn is not None:
                assert 0 <= dyn <= 31, (
                    f"Row {i} ({row['display']}): dynasty {dyn} outside range 0-31"
                )

    def test_has_minimum_dynasty_coverage(self, wikidata_pharaoh_rows):
        with_dynasty = sum(1 for r in wikidata_pharaoh_rows if r["dynasty"] is not None)
        ratio = with_dynasty / len(wikidata_pharaoh_rows)
        assert ratio >= 0.60, (
            f"Only {ratio:.0%} of rows have a dynasty number; expected at least 60%"
        )

    def test_has_minimum_date_coverage(self, wikidata_pharaoh_rows):
        with_dates = sum(1 for r in wikidata_pharaoh_rows
                         if r["start_year"] is not None or r["end_year"] is not None)
        ratio = with_dates / len(wikidata_pharaoh_rows)
        assert ratio >= 0.70, (
            f"Only {ratio:.0%} of rows have dates; expected at least 70%"
        )

    def test_well_known_pharaohs_present(self, wikidata_pharaoh_rows):
        displays_lower = {r["display"].lower() for r in wikidata_pharaoh_rows}
        expected = [
            "khufu", "thutmose iii", "hatshepsut", "akhenaten",
            "ramesses ii", "cleopatra", "tutankhamun",
        ]
        for name in expected:
            assert name in displays_lower, f"Expected well-known pharaoh {name!r} not found"

    def test_thutmose_iii_data(self, wikidata_pharaoh_rows):
        matches = [r for r in wikidata_pharaoh_rows if r["display"] == "Thutmose III"]
        assert len(matches) == 1, "Thutmose III should have exactly one row"
        t3 = matches[0]
        assert t3["qid"] == "Q157899"
        assert t3["dynasty"] == 18
        assert t3["start_year"] is not None and t3["start_year"] < -1400

    def test_alt_labels_are_lists_or_null(self, wikidata_pharaoh_rows):
        for i, row in enumerate(wikidata_pharaoh_rows, 1):
            val = row.get("alt_labels")
            assert val is None or isinstance(val, list), (
                f"Row {i} ({row['display']}): alt_labels should be list or null"
            )

    def test_page_is_always_null(self, wikidata_pharaoh_rows):
        for i, row in enumerate(wikidata_pharaoh_rows, 1):
            assert row["page"] is None, (
                f"Row {i}: page should be null for Wikidata source"
            )

    def test_raw_json_exists(self):
        raw_path = WIKIDATA_PHARAOHS_DIR / "raw.json"
        assert raw_path.exists(), "raw.json should exist alongside reconciled.jsonl"

    def test_fetch_script_exists(self):
        fetch_path = WIKIDATA_PHARAOHS_DIR / "fetch.py"
        assert fetch_path.exists(), "fetch.py should exist for reproducible re-acquisition"

    def test_known_non_pharaohs_excluded(self, wikidata_pharaoh_rows):
        """Wikidata misclassifications must not appear in the reconciled output."""
        qids = {row["qid"] for row in wikidata_pharaoh_rows}
        assert "Q113564932" not in qids, "Aknamkanon (fictional Yu-Gi-Oh character) must be excluded"
        assert "Q136446547" not in qids, "Milkyaton (Cypriot king, not a pharaoh) must be excluded"
        assert "Q471255" not in qids, "Pothinus (Ptolemaic courtier, not a pharaoh) must be excluded"
        assert "Q5131728" not in qids, "Fictional Cleopatra (HBO's Rome) must be excluded"
