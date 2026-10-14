"""Royal women (Dodson & Hilton) as an authority for queen-cued ruler mentions, on the
committed source data."""

from __future__ import annotations

import pytest

from pipeline.authority import royal_women as rw

# A stand-in for the claim-graph king resolver: the kings these tests' records name.
KINGS = {
    "Amenhotep III": "king:amenhotep-iii",
    "Mentuhotep II": "king:mentuhotep-ii",
    "Akhenaten": "king:akhenaten",
    "Setnakhte": "king:setnakhte",
    "Ramesses III": "king:ramesses-iii",
    "Tausret": "king:tausret",
    "Maatkare": "king:hatshepsut",
}


def resolve_king(name: str) -> dict:
    if name in KINGS:
        return {"status": "resolved", "target_ids": [KINGS[name]], "resolution_method": "raw_exact"}
    return {"status": "unmatched", "target_ids": [], "resolution_method": None}


@pytest.fixture(scope="module")
def index() -> rw.RoyalWomenIndex:
    return rw.build_index(rw.load_royal_women(), resolve_king)


def test_the_women_are_dodson_and_hiltons_keyed_by_entry() -> None:
    women = {w.target_id: w for w in rw.load_royal_women()}
    assert len(women) == 320
    tiye = women["dodson_hilton:Tiye A|The Amarna Interlude"]
    assert (tiye.label, tiye.dynasties, tiye.dh_rows) == ("Tiye A", (18,), (("Tiye A", "The Amarna Interlude"),))
    assert tiye.labels == ("Tiye A", "Tiye")
    assert tiye.family_names == ("Amenhotep III", "Yuya", "Akhenaten")
    assert tiye.source_citations == ({"edition": "Thames & Hudson 2004 hardback", "pdf_pages": "142-145"},)
    # The same dh_id under two sub-periods is one woman only where the source says so.
    takhat = women["dodson_hilton:Takhat A"]
    assert takhat.dh_rows == (("Takhat A", "The Feud of the Ramessides"), ("Takhat A", "The House of Ramesses"))
    assert {"dodson_hilton:Henttawy Q|Of Kings and Priests",
            "dodson_hilton:Henttawy Q|The Decline of the Ramessides"} <= set(women)
    # Hedged family names are not family links.
    assert women["dodson_hilton:Isetneferet C"].family_names == ("Merenptah", "Khaemwaset C")


def test_labels_drop_dodson_and_hiltons_disambiguators() -> None:
    assert rw.labels_for("Tiye B Mereniset") == ["Tiye B Mereniset", "Tiye Mereniset", "Tiye"]
    assert rw.labels_for("Neferu II") == ["Neferu II", "Neferu"]
    assert rw.labels_for("Nefertiti") == ["Nefertiti"]


def test_a_bare_name_is_chosen_by_the_records_family_then_dynasty(index) -> None:
    def tiye(kings, dynasty):
        found = rw.resolve_royal_woman(index, "Tiye", record_king_ids=kings, record_dynasty=dynasty)
        return found["status"], found["target_ids"], found["context_rule"]

    tiye_a = "dodson_hilton:Tiye A|The Amarna Interlude"
    assert tiye({"king:amenhotep-iii"}, None) == ("resolved", [tiye_a], "family")
    assert tiye(set(), 18) == ("resolved", [tiye_a], "dynasty")
    assert tiye({"king:setnakhte"}, 20) == ("resolved", ["dodson_hilton:Tiye B Mereniset|The Decline of the Ramessides"], "family")
    # Two Dynasty 20 Tiyes and no family link: nothing chooses.
    found = rw.resolve_royal_woman(index, "Tiye", record_king_ids=set(), record_dynasty=20)
    assert found["status"] == "ambiguous"
    assert found["target_ids"] == found["candidate_ids"] == [
        tiye_a, "dodson_hilton:Tiye B Mereniset|The Decline of the Ramessides", "dodson_hilton:Tiye C|The Decline of the Ramessides"]


def test_neferu_needs_her_husband_dynasty_11_has_two(index) -> None:
    found = rw.resolve_royal_woman(index, "Neferu", record_king_ids={"king:mentuhotep-ii"}, record_dynasty=11)
    assert (found["status"], found["target_ids"], found["context_rule"]) == (
        "resolved", ["dodson_hilton:Neferu II|The Head of the South"], "family")
    found = rw.resolve_royal_woman(index, "Neferu", record_king_ids=set(), record_dynasty=11)
    assert found["status"] == "ambiguous"


def test_a_queen_cue_keeps_queens_and_kings_apart(index) -> None:
    def resolve(text, cue):
        found = rw.resolve_ruler_mention(index, resolve_king, text, queen_cue=cue, record_king_ids=set(), record_dynasty=21)
        return found["authority"], found["status"], found["target_ids"]

    # "Queen Maatkare" is the Dynasty 21 God's Wife, not King Hatshepsut (throne name Maatkare).
    assert resolve("Maatkare", True) == ("royal_women", "resolved", ["dodson_hilton:Maatkare A|Of Kings and Priests"])
    assert resolve("Maatkare", False) == ("kings", "resolved", ["king:hatshepsut"])
    # A queen-cued name no royal woman bears resolves among the kings (a female king).
    assert resolve("Tausret", True) == ("kings_no_royal_woman", "resolved", ["king:tausret"])
    assert resolve("Nefertiti", True) == ("royal_women", "resolved", ["dodson_hilton:Nefertiti|The Amarna Interlude"])


def test_the_queen_cue_and_the_records_dynasty_are_read_exactly() -> None:
    assert rw.queen_cued("Relief of Queen Neferu", 15) is True
    assert rw.queen_cued("Relief of Neferu", 9) is False
    assert rw.queen_cued("Statue of King Tiye", 15) is False
    assert [rw.single_dynasty(v) for v in ("Dynasty 18", "late Dynasty 18", "Dynasty 12, late", "Dynasty 19–20",
                                           "Dynasty 26, or later", "", None)] == [18, 18, 12, None, None, None, None]
