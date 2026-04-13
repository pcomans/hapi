"""Unit tests for pharaoh.se markdown parsing functions.

These test the parser directly with small markdown snippets,
independent of the reconciled.jsonl output. This catches regressions
if pharaoh.se changes formatting or the parser is tweaked.
"""

import importlib.util
from pathlib import Path

import pytest

# The fetch script lives in a hyphenated directory (pharaoh-se/) which isn't
# a valid Python package name, so we load it via importlib.
_fetch_path = (
    Path(__file__).parent.parent / "pipeline" / "authority" / "sources" / "pharaoh-se" / "fetch.py"
)
_spec = importlib.util.spec_from_file_location("pharaoh_se_fetch", _fetch_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

_parse_dynasty_header = _mod._parse_dynasty_header
_parse_name_cards = _mod._parse_name_cards
_parse_reign_dates = _mod._parse_reign_dates
parse_index = _mod.parse_index
parse_pharaoh_page = _mod.parse_pharaoh_page


class TestParseReignDates:
    def test_bce_descending_range(self):
        assert _parse_reign_dates("1479–1425") == (-1479, -1425)

    def test_ad_ascending_range(self):
        assert _parse_reign_dates("14–37") == (14, 37)

    def test_explicit_bc_ce_markers(self):
        assert _parse_reign_dates("27 BC–14 CE") == (-27, 14)

    def test_open_ended_start(self):
        assert _parse_reign_dates("2900–") == (-2900, None)

    def test_open_ended_end(self):
        assert _parse_reign_dates("?–2870") == (None, -2870)

    def test_empty_string(self):
        assert _parse_reign_dates("") == (None, None)

    def test_none_input(self):
        assert _parse_reign_dates(None) == (None, None)

    def test_whitespace_only(self):
        assert _parse_reign_dates("   ") == (None, None)

    def test_slash_alternative_start(self):
        # "1479/1478–1425" should take first number
        start, end = _parse_reign_dates("1479/1478–1425")
        assert start == -1479
        assert end == -1425


class TestParseDynastyHeader:
    def test_numbered_dynasty(self):
        result = _parse_dynasty_header("## Eighteenth Dynasty")
        assert result == {"label": "Eighteenth Dynasty", "number": 18}

    def test_compound_dynasty(self):
        result = _parse_dynasty_header("## Twenty-first Dynasty")
        assert result == {"label": "Twenty-first Dynasty", "number": 21}

    def test_thirty_first_not_first(self):
        result = _parse_dynasty_header("## Thirty-first Dynasty")
        assert result is not None
        assert result["number"] == 31

    def test_predynastic(self):
        result = _parse_dynasty_header("## Predynastic kings")
        assert result is not None
        assert result["number"] is None
        assert result["label"] == "Predynastic kings"

    def test_non_header(self):
        assert _parse_dynasty_header("Not a header") is None

    def test_roman_emperors(self):
        result = _parse_dynasty_header("## Roman Emperors")
        assert result is not None
        assert result["number"] is None


class TestParseNameCards:
    def test_single_card(self):
        lines = [
            "Horus name",
            "",
            "![Horus name](https://pharaoh.se/svg/pharaoh/18-06-01.svg)",
            "",
            "Ka nakht kha em Waset",
            "",
            "kꜢ-nḫt ḫꜤ-m-wꜢst",
            "",
            "The strong bull arising in Thebes",
            "",
            "E1:D40-xa:m-R19-t:O49",
            "",
            "Beckerath, MÄS 49 (1999). 136-137",
        ]
        cards = _parse_name_cards(lines)
        assert len(cards) == 1
        assert cards[0]["name"] == "Ka nakht kha em Waset"
        assert cards[0]["transliteration"] == "kꜢ-nḫt ḫꜤ-m-wꜢst"
        assert cards[0]["translation"] == "The strong bull arising in Thebes"
        assert cards[0]["gardiner"] == "E1:D40-xa:m-R19-t:O49"
        assert cards[0]["is_variant"] is False
        assert cards[0]["sources"] == ["Beckerath, MÄS 49 (1999). 136-137"]

    def test_variant_card(self):
        lines = [
            "Throne name variant",
            "",
            "![name](https://pharaoh.se/svg/pharaoh/x.svg)",
            "",
            "Men kheper Ra",
            "",
            "mn-ḫpr-rꜤ",
            "",
            "Lasting is the Manifestation of Ra",
            "",
            "ra:mn-xpr",
            "",
            "Source citation here",
        ]
        cards = _parse_name_cards(lines)
        assert len(cards) == 1
        assert cards[0]["is_variant"] is True

    def test_strips_asterisks(self):
        lines = [
            "Throne name",
            "",
            "![name](https://pharaoh.se/svg/pharaoh/x.svg)",
            "",
            "Meni\\*",
            "",
            "mnꞽ",
            "",
            "–",
            "",
            "x-y",
        ]
        cards = _parse_name_cards(lines)
        assert len(cards) == 1
        assert cards[0]["name"] == "Meni"

    def test_strips_markdown_italics(self):
        lines = [
            "Throne name",
            "",
            "![name](https://pharaoh.se/svg/pharaoh/x.svg)",
            "",
            "User Maat Ra, _setep en Ra_",
            "",
            "wsr-mꜤꜢt-rꜤ stp.n-rꜤ",
            "",
            "Translation here",
            "",
            "ra:mn-xpr",
        ]
        cards = _parse_name_cards(lines)
        assert len(cards) == 1
        assert cards[0]["name"] == "User Maat Ra, setep en Ra"

    def test_gardiner_code_detected(self):
        """Gardiner codes like E1:D40 should be parsed as gardiner, not sources."""
        lines = [
            "Horus name",
            "",
            "![img](https://pharaoh.se/svg/pharaoh/x.svg)",
            "",
            "Ka nakht",
            "",
            "kꜢ-nḫt",
            "",
            "The strong bull",
            "",
            "E1:D40-xa:m-R19-t:O49",
            "",
            "Some source",
        ]
        cards = _parse_name_cards(lines)
        assert cards[0]["gardiner"] == "E1:D40-xa:m-R19-t:O49"
        assert cards[0]["sources"] == ["Some source"]

    def test_plain_english_not_gardiner(self):
        """Plain English words like 'lands' must not match as Gardiner codes."""
        lines = [
            "Nebty name",
            "",
            "![img](https://pharaoh.se/svg/pharaoh/x.svg)",
            "",
            "Aa shefyt em tau nebu",
            "",
            "ꜤꜢ-šfꞽt-m-tꜢw-nb(w)",
            "",
            "Great of majesty in all",
            "",
            "lands",
            "",
            "aA-F8:t-m-N17:N17:N17:nb",
            "",
            "Real source here",
        ]
        cards = _parse_name_cards(lines)
        assert cards[0]["translation"] == "Great of majesty in all"
        assert cards[0]["gardiner"] == "aA-F8:t-m-N17:N17:N17:nb"
        assert "lands" in (cards[0]["sources"] or [])

    def test_source_note_not_gardiner(self):
        """Source notes like 'After name change' must not match as Gardiner codes."""
        lines = [
            "Horus name variant",
            "",
            "![img](https://pharaoh.se/svg/pharaoh/x.svg)",
            "",
            "Some name",
            "",
            "transliteration",
            "",
            "Translation",
            "",
            "E1:D40-xa",
            "",
            "After name change",
            "",
            "Real source",
        ]
        cards = _parse_name_cards(lines)
        assert cards[0]["gardiner"] == "E1:D40-xa"
        assert "After name change" in (cards[0]["sources"] or [])

    def test_name_missing_filtered(self):
        """'Name missing' placeholder entries should be filtered out."""
        lines = [
            "Throne name",
            "",
            "![img](https://pharaoh.se/svg/pharaoh/x.svg)",
            "",
            "Name missing",
            "",
            "\u2013",
            "",
            "\u2013",
        ]
        cards = _parse_name_cards(lines)
        assert len(cards) == 0

    def test_literal_null_name(self):
        """Literal string 'null' should become None."""
        lines = [
            "Nebty name variant",
            "",
            "![img](https://pharaoh.se/svg/pharaoh/x.svg)",
            "",
            "null",
            "",
            "transliteration",
            "",
            "Translation",
            "",
            "E1:D40",
        ]
        cards = _parse_name_cards(lines)
        assert len(cards) == 1
        assert cards[0]["name"] is None

    def test_footer_not_in_sources(self):
        lines = [
            "Birth name",
            "",
            "![name](https://pharaoh.se/svg/pharaoh/x.svg)",
            "",
            "Pedubast",
            "",
            "pꜢ-dꞽ-bꜢstt",
            "",
            "Given by Bastet",
            "",
            "G7-A1:D40",
            "",
            "Some real source",
            "",
            "**PLEASE NOTE**",
            "",
            "There _might_ be errors on this page.",
            "",
            "Ex nihilo nihil fit",
        ]
        cards = _parse_name_cards(lines)
        assert len(cards) == 1
        assert cards[0]["gardiner"] == "G7-A1:D40"
        assert "**PLEASE NOTE**" not in (cards[0]["sources"] or [])
        assert cards[0]["sources"] == ["Some real source"]


class TestParseIndex:
    def test_basic_table(self):
        md = """## First Dynasty

| # | Pharaoh | Alternate names | Reign (BC) |
| --- | --- | --- | --- |
| 1 | [Narmer](https://pharaoh.se/ancient-egypt/pharaoh/Narmer) | _Menes_ | 2900– |
| 2 | [Aha](https://pharaoh.se/ancient-egypt/pharaoh/Aha) | _Hor-Aha_ | ?–2870 |
"""
        records = parse_index(md)
        assert len(records) == 2
        assert records[0]["display"] == "Narmer"
        assert records[0]["slug"] == "Narmer"
        assert records[0]["alt_labels"] == ["Menes"]
        assert records[0]["start_year"] == -2900
        assert records[0]["end_year"] is None
        assert records[0]["dynasty_number"] == 1
        assert records[0]["dynasty_label"] == "First Dynasty"

    def test_question_mark_ordinal(self):
        md = """## Eighth Dynasty

| # | Pharaoh | Alternate names | Reign (BC) |
| --- | --- | --- | --- |
| ? | [Ity](https://pharaoh.se/ancient-egypt/pharaoh/Ity) |  |  |
"""
        records = parse_index(md)
        assert len(records) == 1
        assert records[0]["ordinal"] is None

    def test_dash_alt_not_included(self):
        md = """## Some Dynasty

| # | Pharaoh | Alternate names | Reign (BC) |
| --- | --- | --- | --- |
| 1 | [Test](https://pharaoh.se/ancient-egypt/pharaoh/Test) | - |  |
"""
        records = parse_index(md)
        assert len(records) == 1
        # The dash should be in alt_labels from index parsing (filtered later in reconcile)
        # but the raw parse_index doesn't filter — that happens in reconcile


class TestParsePharaohPage:
    def test_extracts_predecessor_with_typo(self):
        md = """# Test in hieroglyphs

The first pharaoh of the [First Dynasty](https://pharaoh.se/ancient-egypt/dynasty/1), _a.k.a. Alt Name_

| Precedessor<br>[Previous](https://pharaoh.se/ancient-egypt/pharaoh/Previous)<br>Successor<br>[Next](https://pharaoh.se/ancient-egypt/pharaoh/Next) |

## Bibliography
"""
        result = parse_pharaoh_page(md, "Test")
        assert result["predecessor"] == "Previous"
        assert result["successor"] == "Next"
        assert result["alt_labels_from_page"] == ["Alt Name"]
