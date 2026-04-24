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
PHARAOH_SE_DIR = AUTHORITY_SOURCES / "pharaoh-se"


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
        # 203 IV.2/IV.3 chronology-table rows + 1 Dyn-0 dynasty row
        # + 3 Dyn-0 ruler rows (Iry-Hor, Ka, Scorpion I) from Ch 2 Hendrickx.
        assert len(hkw_rows) == 207

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
        # IV.2 + IV.3 chronology table pp.490-498 PLUS the specific Ch 2
        # Hendrickx pages we actually cite (pp. 88 for Dyn-0 dynasty row,
        # 89 for Iry-Hor + Ka, 91 for Scorpion I). Tightened from
        # range(55, 94) per code-reviewer retrospective finding: allowing
        # the full 55-93 range silently permits incorrect cite pages.
        valid_pages = set(range(490, 499)) | {88, 89, 91}
        for i, row in enumerate(hkw_rows, 1):
            assert row["page"] in valid_pages, (
                f"Row {i}: page {row['page']} outside expected "
                f"pages (490-498 for IV.2/IV.3; {{88, 89, 91}} for Ch 2 "
                f"Hendrickx Dyn-0 block)"
            )

    def test_dyn0_rulers_present(self, hkw_rows):
        """Ch 2 Hendrickx Dyn-0 rulers Iry-Hor and Ka are both `dynasty=0`
        per Hendrickx p.88 ("the only consistency [in Dyn 0 usage] is the
        inclusion of Iry-Hor and Ka"). Scorpion I is a separate assertion
        (`test_scorpion_i_dynasty_null` below) — he sits in cemetery U at
        Naqada IIIA1 and pre-dates the cemetery-B Dyn-0 kings, so his
        `dynasty` is null not 0 (egyptologist-reviewer P1 finding on the
        retrospective PR #102 review).
        """
        dyn0_rulers = {
            r["display"]: r for r in hkw_rows
            if r["kind"] == "ruler" and r.get("dynasty") == 0
        }
        assert set(dyn0_rulers) == {"Iry-Hor", "Ka"}, (
            f"Expected {{Iry-Hor, Ka}}, got {sorted(dyn0_rulers)}"
        )
        for name, r in dyn0_rulers.items():
            assert r["start_year"] is None, (name, r["start_year"])
            assert r["end_year"] is None, (name, r["end_year"])
            assert r["page"] == 89, (name, r["page"])
            assert r["approximate"] is True, name
            assert r["note"] and "Hendrickx" in r["note"], name
            # Per CLAUDE.md rule 5: assert every mappable field on every
            # fixture row, not just the theme the test is named for.
            assert r["greek_form"] is None, name
            assert r["prenomen"] is None, name
            assert r["uncertainty_plus_years"] is None, name

    def test_scorpion_i_dynasty_null(self, hkw_rows):
        """Scorpion I carries `dynasty=null` (not 0) per the egyptologist-
        reviewer P1 finding on the retrospective PR #102 review:
        Hendrickx p.88 names only Iry-Hor and Ka as consistent Dyn-0
        rulers. Scorpion I is cemetery U / Naqada IIIA1, pre-dating the
        cemetery-B Dyn-0 kings. Phase-A consumers may elect Dyn 00 / Dyn 0
        / null per local convention; we pin null so downstream joins
        don't silently claim Hendrickx-sourced Dyn-0 for Scorpion I.
        """
        scorpion = [
            r for r in hkw_rows
            if r["kind"] == "ruler" and r["display"] == "Scorpion I"
        ]
        assert len(scorpion) == 1, "expected exactly one Scorpion I row"
        r = scorpion[0]
        assert r["dynasty"] is None, r["dynasty"]
        assert r["page"] == 91, r["page"]
        assert r["start_year"] is None
        assert r["end_year"] is None
        assert r["uncertainty_plus_years"] is None
        assert r["greek_form"] is None
        assert r["prenomen"] is None
        assert r["alternative_reading"] is None
        assert r["approximate"] is True
        # Note must cite Hendrickx p.88 (Dyn-0-inclusion caveat) and the
        # U-j tomb — both load-bearing facts that a reader would rely on.
        assert "p.88" in r["note"] and "U-j" in r["note"], r["note"][:200]

    def test_dyn0_ruler_alternative_readings(self, hkw_rows):
        """Iry-Hor has `Irj-Hor` (Hendrickx's occasional spelling p.89).
        Ka has `alternative_reading: null` (the earlier "Sekhen" value
        was a provenance leak — Hendrickx does not use it; removed per
        egyptologist-reviewer + code-reviewer P2 finding on the
        retrospective PR #102 review). Scorpion I similarly null.

        Filtered with BOTH `dynasty == 0` AND the explicit display-name
        allow-list to avoid homonym collisions — per Gemini round-1 finding
        on PR #103 (the prior version was a plain `display in {...}` filter
        which would silently collide if any other dynasty happens to carry
        a ruler with the same display name). Scorpion I sits at
        `dynasty: null` (per egyptologist review on PR #102 retrospective),
        so the OR-clause keeps him reachable.
        """
        by_display = {
            r["display"]: r
            for r in hkw_rows
            if r["kind"] == "ruler"
            and r["display"] in {"Iry-Hor", "Ka", "Scorpion I"}
            and (r.get("dynasty") == 0 or r["display"] == "Scorpion I")
        }
        assert by_display["Iry-Hor"]["alternative_reading"] == "Irj-Hor"
        assert by_display["Ka"]["alternative_reading"] is None
        assert by_display["Scorpion I"]["alternative_reading"] is None

    def test_dyn0_dynasty_row_present(self, hkw_rows):
        """A `kind: dynasty` row with `number: 0` exists so the
        `test_ruler_dynasty_references_exist` invariant holds for the
        Dyn-0 ruler rows.
        """
        dyn0 = [
            r for r in hkw_rows
            if r["kind"] == "dynasty" and r.get("number") == 0
        ]
        assert len(dyn0) == 1, f"expected 1 Dyn-0 dynasty row, got {len(dyn0)}"
        r = dyn0[0]
        assert r["label"] == "Dyn. 0"
        assert r["start_year"] is None
        assert r["end_year"] is None
        # Hendrickx does not assign Dyn 0 to the Early Dynastic Period —
        # it sits at the Predynastic / Early Dynastic boundary.
        assert r.get("parent_period") is None


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
def pharaoh_se_rows():
    return load_jsonl(PHARAOH_SE_DIR / "reconciled.jsonl")


class TestPharaohSeIntegrity:
    def test_row_count(self, pharaoh_se_rows):
        assert len(pharaoh_se_rows) == 381

    def test_all_rows_are_rulers(self, pharaoh_se_rows):
        for i, row in enumerate(pharaoh_se_rows, 1):
            assert row["kind"] == "ruler", f"Row {i}: kind should be 'ruler', got {row['kind']!r}"

    def test_every_row_has_slug(self, pharaoh_se_rows):
        for i, row in enumerate(pharaoh_se_rows, 1):
            assert row["slug"], f"Row {i}: missing slug"

    def test_slugs_are_unique(self, pharaoh_se_rows):
        slugs = [row["slug"] for row in pharaoh_se_rows]
        assert len(slugs) == len(set(slugs)), "Duplicate slugs found"

    def test_every_row_has_url(self, pharaoh_se_rows):
        for i, row in enumerate(pharaoh_se_rows, 1):
            assert row["url"], f"Row {i}: missing url"
            assert row["url"].startswith("https://pharaoh.se/"), (
                f"Row {i}: url should start with https://pharaoh.se/"
            )

    def test_every_row_has_display_name(self, pharaoh_se_rows):
        for i, row in enumerate(pharaoh_se_rows, 1):
            assert row["display"] and len(row["display"]) > 0, (
                f"Row {i}: missing display name"
            )

    def test_dates_are_negative_for_bce_rulers(self, pharaoh_se_rows):
        """BCE rulers have negative dates; Roman emperors may have positive (AD) dates."""
        ad_dynasties = {"Roman Emperors"}
        for i, row in enumerate(pharaoh_se_rows, 1):
            if row.get("dynasty_label") in ad_dynasties:
                continue
            for field in ("start_year", "end_year"):
                val = row.get(field)
                if val is not None:
                    assert val < 0, (
                        f"Row {i} ({row['display']}): {field}={val} should be negative (BCE)"
                    )

    def test_date_ranges_are_ordered(self, pharaoh_se_rows):
        for i, row in enumerate(pharaoh_se_rows, 1):
            s, e = row.get("start_year"), row.get("end_year")
            if s is not None and e is not None:
                assert s <= e, (
                    f"Row {i} ({row['display']}): inverted date range "
                    f"start_year={s} > end_year={e}"
                )

    def test_has_minimum_prenomen_coverage(self, pharaoh_se_rows):
        with_prenomen = sum(1 for r in pharaoh_se_rows if r["prenomen"] is not None)
        ratio = with_prenomen / len(pharaoh_se_rows)
        assert ratio >= 0.70, (
            f"Only {ratio:.0%} of rows have a prenomen; expected at least 70%"
        )

    def test_has_minimum_date_coverage(self, pharaoh_se_rows):
        with_dates = sum(1 for r in pharaoh_se_rows
                         if r["start_year"] is not None or r["end_year"] is not None)
        ratio = with_dates / len(pharaoh_se_rows)
        assert ratio >= 0.60, (
            f"Only {ratio:.0%} of rows have dates; expected at least 60%"
        )

    def test_has_minimum_alt_label_coverage(self, pharaoh_se_rows):
        with_alts = sum(1 for r in pharaoh_se_rows if r["alt_labels"] is not None)
        ratio = with_alts / len(pharaoh_se_rows)
        assert ratio >= 0.70, (
            f"Only {ratio:.0%} of rows have alt labels; expected at least 70%"
        )

    def test_well_known_pharaohs_present(self, pharaoh_se_rows):
        all_names = set()
        for r in pharaoh_se_rows:
            all_names.add(r["display"].lower())
            for a in r.get("alt_labels") or []:
                all_names.add(a.lower())
        expected = [
            "khufu", "thutmose iii", "hatshepsut", "akhenaten",
            "ramesses ii", "cleopatra vii", "tutankhamun",
        ]
        for name in expected:
            assert name in all_names, f"Expected well-known pharaoh {name!r} not found"

    def test_thutmose_iii_data(self, pharaoh_se_rows):
        matches = [r for r in pharaoh_se_rows if r["display"] == "Thutmose III"]
        assert len(matches) == 1, "Thutmose III should have exactly one row"
        t3 = matches[0]
        assert t3["slug"] == "Thutmose-III"
        assert t3["dynasty_number"] == 18
        assert t3["start_year"] == -1479
        assert t3["end_year"] == -1425
        assert t3["prenomen"] == "Men kheper Ra"
        assert t3["predecessor"] == "Hatshepsut"
        assert t3["successor"] == "Amenhotep II"
        assert t3["horus_names"] is not None and len(t3["horus_names"]) >= 5
        assert t3["throne_names"] is not None and len(t3["throne_names"]) >= 5

    def test_alt_labels_are_lists_or_null(self, pharaoh_se_rows):
        for i, row in enumerate(pharaoh_se_rows, 1):
            val = row.get("alt_labels")
            assert val is None or isinstance(val, list), (
                f"Row {i} ({row['display']}): alt_labels should be list or null"
            )

    def test_name_cards_have_required_fields(self, pharaoh_se_rows):
        name_fields = ["horus_names", "nebty_names", "golden_horus_names",
                        "throne_names", "birth_names"]
        for i, row in enumerate(pharaoh_se_rows, 1):
            for field in name_fields:
                names = row.get(field)
                if names is None:
                    continue
                assert isinstance(names, list), (
                    f"Row {i} ({row['display']}): {field} should be list"
                )
                for j, card in enumerate(names):
                    # Name or transliteration may be null for incomplete
                    # attestations, but at least one should be present.
                    assert card.get("name") or card.get("transliteration"), (
                        f"Row {i} ({row['display']}): {field}[{j}] missing both name and transliteration"
                    )

    def test_raw_directory_exists(self):
        raw_dir = PHARAOH_SE_DIR / "raw"
        assert raw_dir.is_dir(), "raw/ directory should exist with scraped markdown"
        assert (raw_dir / "index.md").exists(), "raw/index.md should exist"

    def test_fetch_script_exists(self):
        fetch_path = PHARAOH_SE_DIR / "fetch.py"
        assert fetch_path.exists(), "fetch.py should exist for reproducible re-acquisition"


IDAI_DIR = AUTHORITY_SOURCES / "idai-gazetteer"


@pytest.fixture
def idai_rows():
    return load_jsonl(IDAI_DIR / "reconciled.jsonl")


class TestIdaiGazetteerIntegrity:

    def test_source_block_is_first_line(self, idai_rows):
        src_block = idai_rows[0]
        assert "_source" in src_block
        src = src_block["_source"]
        assert src["citation"].startswith("iDAI.gazetteer")
        assert src["license"] == "CC BY 4.0"
        assert src["raw_file"] == "sources/idai-gazetteer/raw.json"
        assert len(src.get("retrieved", "")) == 10  # ISO date YYYY-MM-DD

    def test_raw_file_exists(self):
        assert (IDAI_DIR / "raw.json").exists(), "raw.json must be committed (ADR-012)"

    def test_minimum_record_count(self, idai_rows):
        site_rows = [r for r in idai_rows if "_source" not in r]
        assert len(site_rows) == 1000, f"Expected 1000 site records after filter, got {len(site_rows)}"

    def test_all_rows_have_kind_site(self, idai_rows):
        for i, row in enumerate(idai_rows, 1):
            if "_source" in row:
                continue
            assert row["kind"] == "site", f"Row {i}: expected kind='site', got {row['kind']!r}"

    def test_ids_start_with_idai_prefix(self, idai_rows):
        for i, row in enumerate(idai_rows, 1):
            if "_source" in row:
                continue
            assert row["id"].startswith("idai:"), f"Row {i}: id must start with 'idai:'"

    def test_ids_are_unique(self, idai_rows):
        ids = [r["id"] for r in idai_rows if "_source" not in r]
        assert len(ids) == len(set(ids)), "Duplicate idai: IDs found"

    def test_all_rows_have_display(self, idai_rows):
        for i, row in enumerate(idai_rows, 1):
            if "_source" in row:
                continue
            assert row.get("display"), f"Row {i} ({row.get('id')}): missing display name"

    def test_all_types_are_filtered(self, idai_rows):
        # Load ADDITIONAL_GAZ_IDS from the fetch module (path-loaded because
        # the idai-gazetteer directory has a hyphen in its name).
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "idai_fetch",
            IDAI_DIR / "fetch.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        supplementary_ids = {f"idai:{gid}" for gid, _, _ in mod.ADDITIONAL_GAZ_IDS}

        valid = {"archaeological-site", "archaeological-area", "landform"}
        for i, row in enumerate(idai_rows, 1):
            if "_source" in row:
                continue
            # Supplementary additions legitimately bypass the type filter — they
            # are curated-by-ID for museum-provenance coverage (Fayum region,
            # Nubian sites outside the Egypt ancestor tree). See ADDITIONAL_GAZ_IDS.
            if row["id"] in supplementary_ids:
                continue
            types = set(row.get("types", []))
            assert types & valid, (
                f"Row {i} ({row.get('display')}): no valid type in {types!r}"
            )

    def test_canary_sites_present(self, idai_rows):
        all_ids = {r["id"] for r in idai_rows if "_source" not in r}
        canary = {
            "idai:2110510": "Deir el-Bahari",
            "idai:2096884": "Valley of the Kings",
            "idai:2178702": "Karnak",
            "idai:2042907": "Saqqara",
            "idai:2042921": "Thebes",
            "idai:2089516": "Giza",
            "idai:2412478": "Abydos",
            "idai:2296218": "Amarna",
            "idai:2042876": "Medinet Habu",
            "idai:2751511": "Elephantine",
            # Supplementary additions — fetched explicitly because the
            # (ancestors:2042786 + type filter) search misses them.
            "idai:2042846": "al-Fayyūm (Fayum)",
            "idai:2751172": "Buhen",
            "idai:2751351": "Kerma",
            "idai:2293921": "Meroë",
            "idai:2379057": "Napata",
        }
        for gaz_id, name in canary.items():
            assert gaz_id in all_ids, f"Canary site missing: {name} ({gaz_id})"

    def test_deir_el_bahari_data(self, idai_rows):
        matches = [r for r in idai_rows if r.get("id") == "idai:2110510"]
        assert len(matches) == 1
        deb = matches[0]
        assert deb["display"] == "ad-dayr al-baḥrī"
        assert deb["coordinates"] == pytest.approx([32.60771, 25.73783], abs=0.001)
        assert deb["cross_refs"]["geonames"] == "361834"

    def test_coordinates_are_valid(self, idai_rows):
        for i, row in enumerate(idai_rows, 1):
            if "_source" in row:
                continue
            coords = row.get("coordinates")
            if coords is None:
                continue
            lon, lat = coords
            assert -180 <= lon <= 180, f"Row {i}: longitude {lon} out of range"
            assert -90 <= lat <= 90, f"Row {i}: latitude {lat} out of range"

    def test_fetch_script_exists(self):
        assert (IDAI_DIR / "fetch.py").exists()
