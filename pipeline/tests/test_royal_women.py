"""Royal women (Dodson & Hilton) as an authority for queen-cued ruler mentions, on the
committed source data."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.authority import royal_women as rw

# A stand-in for the claim-graph king resolver: the kings these tests' records name, and the
# king names the female-king crosswalk uses.
KINGS = {
    "Amenhotep III": "king:amenhotep-iii",
    "Mentuhotep II": "king:mentuhotep-ii",
    "Akhenaten": "king:akhenaten",
    "Setnakhte": "king:setnakhte",
    "Ramesses III": "king:ramesses-iii",
    "Maatkare": "king:hatshepsut",
    "Hatshepsut": "king:hatshepsut",
    "Tausret": "king:tausret",
    "Neferusobek": "king:sobekneferu",
}


def resolve_king(name: str) -> dict:
    if name in KINGS:
        return {"status": "resolved", "target_ids": [KINGS[name]], "resolution_method": "raw_exact"}
    return {"status": "unmatched", "target_ids": [], "resolution_method": None}


@pytest.fixture(scope="module")
def women() -> dict[str, rw.RoyalWoman]:
    return {w.target_id: w for w in rw.load_royal_women()}


@pytest.fixture(scope="module")
def index(women) -> rw.RoyalWomenIndex:
    return rw.build_index(women.values(), resolve_king)


def test_the_women_are_dodson_and_hiltons(women) -> None:
    assert len(women) == 317
    tiye = women["dodson_hilton:Tiye A"]
    assert (tiye.label, tiye.labels, tiye.dynasties, tiye.king_name) == ("Tiye A", ("Tiye A", "Tiye"), (18,), None)
    assert tiye.dh_rows == (("Tiye A", "The Amarna Interlude"),)
    assert tiye.family_names == ("Amenhotep III", "Yuya", "Tjuiu", "Akhenaten")
    assert tiye.source_citations == ({"edition": "Thames & Hudson 2004 hardback", "pdf_pages": "142-145"},)


def test_a_woman_in_two_chapters_is_one_woman_as_classified(women) -> None:
    henttawy = women["dodson_hilton:Henttawy Q"]
    assert henttawy.dh_rows == (("Henttawy Q", "Of Kings and Priests"), ("Henttawy Q", "The Decline of the Ramessides"))
    assert henttawy.dynasties == (20, 21)
    # Her stub's "Ramesses XI (probable)" is hedged; the full entry's family links stand.
    assert henttawy.family_names == ("Pinudjem I", "Ramesses XI", "Pasebkhanut I", "Djedkhonsiufankh I")
    assert {"dodson_hilton:Takhat A", "dodson_hilton:Isetneferet C", "dodson_hilton:Tentamun B",
            "dodson_hilton:Hetepti"} <= set(women)


def test_an_unclassified_repeated_woman_is_refused(tmp_path: Path) -> None:
    row = {"alt_names": [], "children_names": [], "dh_id": "Nebet Z", "dynasty": 5, "father_name": None,
           "is_group_entry": False, "mother_name": None, "name": "Nebet Z", "roles": [], "sex": "female",
           "source_citation": {}, "spouse_names": [], "unplaced": False}
    data = tmp_path / "rows.jsonl"
    data.write_text("\n".join(json.dumps({**row, "sub_period": p}) for p in ("One", "Two")))
    empty = tmp_path / "same.json"
    empty.write_text(json.dumps({"entries": []}))
    kings = tmp_path / "kings.json"
    kings.write_text(json.dumps({"entries": []}))
    with pytest.raises(ValueError, match=r"Dodson & Hilton woman Nebet Z under \['One', 'Two'\] is not classified"):
        rw.load_royal_women(data, empty, kings)
    empty.write_text(json.dumps({"entries": [{"dh_id": "Nebet Z", "same_woman": False, "sub_periods": ["One", "Two"]}]}))
    assert [w.target_id for w in rw.load_royal_women(data, empty, kings)] == [
        "dodson_hilton:Nebet Z|One", "dodson_hilton:Nebet Z|Two"]


def test_labels_drop_disambiguators_and_lacunae() -> None:
    assert rw.labels_for("Tiye B Mereniset") == ["Tiye B Mereniset", "Tiye Mereniset", "Tiye"]
    assert rw.labels_for("Neferu II") == ["Neferu II", "Neferu"]
    assert rw.labels_for("Nefertiti") == ["Nefertiti"]
    assert rw.labels_for("[Mut]metennefer") == ["Mutmetennefer"]
    assert rw.labels_for("Seneb[henas A]") == ["Senebhenas A", "Senebhenas"]
    assert rw.labels_for("Henut[...]") == [] == rw.labels_for("[...]taweret")


def test_a_hedged_or_lettered_kinship_name_is_not_a_family_link() -> None:
    assert [rw.usable_kinship_name(n) for n in (
        "Amenhotep III", "Ramesses XI (probable)", "Hor-Aha (presumably)", "Nakhtmin B (if she were his mother)",
        "Ay A", "Khaemwaset C", "Psusennes I", None)] == [True, False, False, False, False, False, True, False]


def test_a_bare_name_is_chosen_by_the_records_family_then_dynasty(index) -> None:
    def tiye(kings, dynasty):
        found = rw.resolve_royal_woman(index, "Tiye", record_king_ids=kings, record_dynasty=dynasty)
        return found["status"], found["target_ids"], found["context_rule"]

    assert tiye({"king:amenhotep-iii"}, None) == ("resolved", ["dodson_hilton:Tiye A"], "family")
    assert tiye(set(), 18) == ("resolved", ["dodson_hilton:Tiye A"], "dynasty")
    assert tiye({"king:setnakhte"}, 20) == ("resolved", ["dodson_hilton:Tiye B Mereniset"], "family")
    # Two Dynasty 20 Tiyes and no family link: nothing chooses.
    found = rw.resolve_royal_woman(index, "Tiye", record_king_ids=set(), record_dynasty=20)
    assert found["status"] == "ambiguous"
    assert found["target_ids"] == found["candidate_ids"] == [
        "dodson_hilton:Tiye A", "dodson_hilton:Tiye B Mereniset", "dodson_hilton:Tiye C"]


def test_neferu_needs_her_husband_dynasty_11_has_two(index) -> None:
    found = rw.resolve_royal_woman(index, "Neferu", record_king_ids={"king:mentuhotep-ii"}, record_dynasty=11)
    assert (found["status"], found["target_ids"], found["context_rule"]) == (
        "resolved", ["dodson_hilton:Neferu II"], "family")
    assert rw.resolve_royal_woman(index, "Neferu", record_king_ids=set(), record_dynasty=11)["status"] == "ambiguous"


def test_the_dynasty_narrows_among_several_family_matches() -> None:
    def woman(name, dynasty):
        return rw.RoyalWoman(target_id=f"dodson_hilton:{name}", label=name, labels=(name, "Iset"),
                             dynasties=(dynasty,), family_names=("Amenhotep III",), dh_rows=((name, "x"),),
                             source_citations=({},), king_name=None)
    other = rw.RoyalWoman(target_id="dodson_hilton:Iset C", label="Iset C", labels=("Iset C", "Iset"),
                          dynasties=(18,), family_names=(), dh_rows=(("Iset C", "x"),), source_citations=({},),
                          king_name=None)
    index = rw.build_index([woman("Iset A", 18), woman("Iset B", 19), other], resolve_king)
    found = rw.resolve_royal_woman(index, "Iset", record_king_ids={"king:amenhotep-iii"}, record_dynasty=18)
    # Both A and B are family matches; of those, only A is of the record's dynasty (C is not family).
    assert (found["status"], found["target_ids"], found["context_rule"]) == ("resolved", ["dodson_hilton:Iset A"], "dynasty")


def test_a_queen_cue_keeps_queens_and_kings_apart(index) -> None:
    def resolve(text, cue, dynasty=21):
        found = rw.resolve_ruler_mention(index, resolve_king, text, queen_cue=cue, record_king_ids=set(),
                                         record_dynasty=dynasty)
        return found["authority"], found["status"], found["target_ids"]

    # "Queen Maatkare" is the Dynasty 21 God's Wife, not King Hatshepsut (throne name Maatkare).
    assert resolve("Maatkare", True) == ("royal_women", "resolved", ["dodson_hilton:Maatkare A"])
    assert resolve("Maatkare", False) == ("kings", "resolved", ["king:hatshepsut"])
    # A queen-cued name no royal woman bears stays unmatched; it never falls to a king.
    assert resolve("Ahmose", True) == ("royal_women", "unmatched", [])
    assert resolve("Nefertiti", True) == ("royal_women", "resolved", ["dodson_hilton:Nefertiti"])


def test_a_woman_who_later_reigned_is_the_king(index) -> None:
    def resolve(text, dynasty):
        found = rw.resolve_ruler_mention(index, resolve_king, text, queen_cue=True, record_king_ids=set(),
                                         record_dynasty=dynasty)
        return found["status"], found["target_ids"], found.get("royal_woman_id")

    # Either spelling reaches Tawosret, and she is the king Tausret.
    assert resolve("Tawosret", 19) == resolve("Tausret", 19) == ("resolved", ["king:tausret"], "dodson_hilton:Tawosret")
    # Hatshepsut D is the Dynasty 18 Hatshepsut (B and C are Dynasty 13).
    assert resolve("Hatshepsut", 18) == ("resolved", ["king:hatshepsut"], "dodson_hilton:Hatshepsut D")
    assert resolve("Sobkneferu", 12) == ("resolved", ["king:sobekneferu"], "dodson_hilton:Sobkneferu")


def test_the_normalized_path_finds_a_spelling_variant(index) -> None:
    found = rw.resolve_royal_woman(index, "NEFERTITI", record_king_ids=set(), record_dynasty=None)
    assert (found["status"], found["target_ids"]) == ("resolved", ["dodson_hilton:Nefertiti"])
    found = rw.resolve_royal_woman(index, "Néfertiti", record_king_ids=set(), record_dynasty=None)
    assert (found["status"], found["resolution_method"], found["target_ids"]) == (
        "resolved", "committed_normalized", ["dodson_hilton:Nefertiti"])


def test_the_queen_cue_and_the_records_dynasty_are_read_exactly() -> None:
    assert [rw.queen_cued(text, len(text)) for text in (
        "Relief of Queen ", "Queen Mother ", "King's Wife ", "King’s Great Wife ", "Great Royal Wife ",
        "God's Wife ", "Relief of ", "Statue of King ")] == [True, True, True, True, True, True, False, False]
    assert [rw.single_dynasty(v) for v in ("Dynasty 18", "late Dynasty 18", "Dynasty 12, late", "18th Dynasty",
                                           "Dynasty 19–20", "Dynasty 26, or later", "", None)] == [
        18, 18, 12, 18, None, None, None, None]
