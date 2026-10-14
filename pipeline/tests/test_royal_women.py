"""Royal women (Dodson & Hilton) and the female rulers of the king lists as an authority for
royal-woman-cued ruler mentions, on the committed source data."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.authority import royal_women as rw


class Kings:
    """A stand-in for the claim-graph king authority: the kings these tests' records name and
    the female rulers `female-rulers.json` lists, with names and dynasties as the claim graph
    gives them."""

    NAMES = {
        "king:amenhotep-iii": (["Amenhotep III"], (18,)),
        "king:mentuhotep-ii": (["Mentuhotep II"], (11,)),
        "king:akhenaten": (["Akhenaten"], (18,)),
        "king:setnakhte": (["Setnakhte"], (20,)),
        "king:ramesses-iii": (["Ramesses III"], (20,)),
        "king:hatshepsut": (["Hatshepsut", "Maatkare"], (18,)),
        "king:tausret": (["Tausret"], (19,)),
        "king:sobekneferu": (["Neferusobek", "(Queen) Sobekneferu"], (12,)),
        "king:neferneferuaten": (["Neferneferuaten"], (18,)),
        "king:neith-iqeret": (["Queen Neith-Iqeret"], (6,)),
        "king:arsinoe-ii": (["Arsinoe II"], (33,)),
        "king:berenike-ii": (["Berenike II"], (33,)),
        "king:cleopatra-i": (["Cleopatra I"], (33,)),
        "king:cleopatra-ii": (["Cleopatra II"], (33,)),
        "king:berenike": (["Berenike"], (33,)),
        "king:cleopatra-vii-l": (["Cleopatra VII Philopator"], (33,)),
        "king:cleopatra-vii-p": (["Cleopatra VII"], ()),
    }

    def resolve(self, name: str) -> dict:
        found = sorted(t for t, (names, _) in self.NAMES.items() if name in names or f"Queen {name}" in names)
        status = "resolved" if len(found) == 1 else "ambiguous" if found else "unmatched"
        return {"status": status, "target_ids": found, "resolution_method": "raw_exact" if found else None}

    def labels(self, target_id: str) -> list[str]:
        return self.NAMES[target_id][0]

    def dynasties(self, target_id: str) -> tuple[int, ...]:
        return self.NAMES[target_id][1]


KINGS = Kings()


@pytest.fixture(scope="module")
def women() -> dict[str, rw.RoyalWoman]:
    return {w.target_id: w for w in rw.load_royal_women()}


@pytest.fixture(scope="module")
def index(women) -> rw.RoyalWomenIndex:
    return rw.build_index(women.values(), KINGS)


def resolve(index, text, *, cue=True, kings=frozenset(), dynasty=None):
    found = rw.resolve_ruler_mention(index, KINGS, text, royal_woman_cue=cue, record_king_ids=set(kings),
                                     record_dynasty=dynasty)
    return found["status"], found["target_ids"], found["context_rule"]


def test_the_women_are_dodson_and_hiltons(women) -> None:
    assert len(women) == 317
    tiye = women["dodson_hilton:Tiye A"]
    assert (tiye.label, tiye.labels, tiye.alt_names, tiye.dynasties) == ("Tiye A", ("Tiye A", "Tiye"), (), (18,))
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
    classified = tmp_path / "same.json"
    classified.write_text(json.dumps({"entries": []}))
    with pytest.raises(ValueError, match=r"Dodson & Hilton woman Nebet Z under \['One', 'Two'\] is not classified"):
        rw.load_royal_women(data, classified)
    classified.write_text(json.dumps({"entries": [
        {"dh_id": "Nebet Z", "same_woman": False, "sub_periods": ["One", "Two"]}]}))
    assert [w.target_id for w in rw.load_royal_women(data, classified)] == [
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
    assert resolve(index, "Tiye", kings={"king:amenhotep-iii"}) == ("resolved", ["dodson_hilton:Tiye A"], "family")
    assert resolve(index, "Tiye", dynasty=18) == ("resolved", ["dodson_hilton:Tiye A"], "dynasty")
    assert resolve(index, "Tiye", kings={"king:setnakhte"}, dynasty=20) == (
        "resolved", ["dodson_hilton:Tiye B Mereniset"], "family")
    # Two Dynasty 20 Tiyes and no family link: nothing chooses.
    assert resolve(index, "Tiye", dynasty=20) == (
        "ambiguous", ["dodson_hilton:Tiye A", "dodson_hilton:Tiye B Mereniset", "dodson_hilton:Tiye C"], None)


def test_neferu_needs_her_husband_dynasty_11_has_two(index) -> None:
    assert resolve(index, "Neferu", kings={"king:mentuhotep-ii"}, dynasty=11) == (
        "resolved", ["dodson_hilton:Neferu II"], "family")
    assert resolve(index, "Neferu", dynasty=11)[0] == "ambiguous"


def test_the_dynasty_narrows_among_several_family_matches(women) -> None:
    def woman(name, dynasty, family):
        return rw.RoyalWoman(target_id=f"dodson_hilton:{name}", label=name, labels=(name, "Iset"), alt_names=(),
                             dynasties=(dynasty,), family_names=family, dh_rows=((name, "x"),), source_citations=({},))
    female_kings = [w for w in women.values() if w.dh_rows[0][0] in ("Hatshepsut D", "Sobkneferu", "Tawosret")]
    index = rw.build_index([woman("Iset A", 18, ("Amenhotep III",)), woman("Iset B", 19, ("Amenhotep III",)),
                            woman("Iset C", 18, ())] + female_kings, KINGS)
    # A and B are family matches; of those only A is of the record's dynasty (C is not family).
    assert resolve(index, "Iset", kings={"king:amenhotep-iii"}, dynasty=18) == (
        "resolved", ["dodson_hilton:Iset A"], "dynasty")


def test_a_candidate_of_unknown_dynasty_is_not_ruled_out_by_the_records(women) -> None:
    def woman(name, dynasties):
        return rw.RoyalWoman(target_id=f"dodson_hilton:{name}", label=name, labels=(name, "Iset"), alt_names=(),
                             dynasties=dynasties, family_names=(), dh_rows=((name, "x"),), source_citations=({},))
    female_kings = [w for w in women.values() if w.dh_rows[0][0] in ("Hatshepsut D", "Sobkneferu", "Tawosret")]
    index = rw.build_index([woman("Iset A", (18,)), woman("Iset B", ())] + female_kings, KINGS)
    assert resolve(index, "Iset", dynasty=18) == ("ambiguous", ["dodson_hilton:Iset A", "dodson_hilton:Iset B"], None)


def test_a_royal_woman_cue_keeps_queens_and_kings_apart(index) -> None:
    # "Maatkare" is the Dynasty 21 God's Wife and Hatshepsut's throne name: a Dynasty 21
    # record's "Queen Maatkare" is the God's Wife, a Dynasty 18 record's is Hatshepsut.
    assert resolve(index, "Maatkare", dynasty=21) == ("resolved", ["dodson_hilton:Maatkare A"], "dynasty")
    assert resolve(index, "Maatkare", dynasty=18) == ("resolved", ["king:hatshepsut"], "dynasty")
    assert resolve(index, "Maatkare") == ("ambiguous", ["dodson_hilton:Hatshepsut D", "dodson_hilton:Maatkare A"], None)
    assert resolve(index, "Maatkare", cue=False, dynasty=21) == ("resolved", ["king:hatshepsut"], None)
    # A cued name no royal woman or female ruler bears stays unmatched; it never falls to a king.
    assert resolve(index, "Ahmose") == ("unmatched", [], None)
    assert resolve(index, "Nefertiti") == ("resolved", ["dodson_hilton:Nefertiti"], None)


def test_a_woman_who_later_reigned_is_the_king(index) -> None:
    # Either spelling reaches Tawosret, and she is the king Tausret.
    assert resolve(index, "Tawosret", dynasty=19) == resolve(index, "Tausret", dynasty=19) == (
        "resolved", ["king:tausret"], None)
    # Hatshepsut D is the Dynasty 18 Hatshepsut (B and C are Dynasty 13).
    assert resolve(index, "Hatshepsut", dynasty=18) == ("resolved", ["king:hatshepsut"], "dynasty")
    assert resolve(index, "Sobkneferu", dynasty=12) == resolve(index, "Sobekneferu", dynasty=12) == (
        "resolved", ["king:sobekneferu"], None)


def test_a_female_ruler_only_the_king_lists_hold_is_reached_by_the_cue(index) -> None:
    assert resolve(index, "Arsinoe II") == ("resolved", ["king:arsinoe-ii"], None)
    assert resolve(index, "Cleopatra VII") == ("resolved", ["king:cleopatra-vii-p"], None)
    assert resolve(index, "Neith-Iqeret") == ("resolved", ["king:neith-iqeret"], None)


def test_an_alternative_name_that_is_a_kings_name_is_not_hers(index) -> None:
    # D&H gives Meryetaten "Neferneferuaten"; whether that king was she is disputed.
    meryetaten = next(w for w in index.women.values() if w.label == "Meryetaten")
    assert meryetaten.alt_names == ("Neferneferuaten",)
    assert index.alt_names_dropped_as_king_names[meryetaten.target_id] == ("Neferneferuaten",)
    assert resolve(index, "Neferneferuaten", dynasty=18) == ("unmatched", [], None)


def test_a_woman_is_never_chosen_against_the_records_dynasty(index) -> None:
    # Nefertiti is Dynasty 18: a Dynasty 22 record's "Queen Nefertiti" is another woman, whom
    # the transcribed chapters do not hold (D&H has no Dynasty 22 onward).
    assert resolve(index, "Nefertiti", dynasty=22) == ("unmatched", [], "record_dynasty_contradicts")
    # An unknown dynasty is not a contradiction (pharaoh.se gives Cleopatra VII none).
    assert resolve(index, "Cleopatra VII", dynasty=33) == ("resolved", ["king:cleopatra-vii-p"], None)


def test_the_normalized_path_finds_a_spelling_variant(index) -> None:
    found = rw.resolve_royal_woman(index, "Néfertiti", record_king_ids=set(), record_dynasty=None)
    assert (found["status"], found["resolution_method"], found["target_ids"]) == (
        "resolved", "committed_normalized", ["dodson_hilton:Nefertiti"])


def test_the_cue_and_the_records_dynasty_are_read_exactly() -> None:
    assert [rw.royal_woman_cued(text, len(text)) for text in (
        "Relief of Queen ", "Queen Mother ", "King's Wife ", "King’s Great Wife ", "Great Royal Wife ",
        "King's Mother ", "King's Daughter ", "Princess ", "God's Wife ", "God's Wife of Amun ",
        "Divine Adoratrice of Amun ", "Queen: ", "Queen - ", "Queen, ", "Relief of ", "Statue of King ",
        "Queen; ")] == [True] * 14 + [False, False, False]
    assert [rw.single_dynasty(v) for v in ("Dynasty 18", "late Dynasty 18", "Dynasty 12, late", "18th Dynasty",
                                           "Dynasty 19–20", "Dynasty 26, or later", "", None)] == [
        18, 18, 12, 18, None, None, None, None]
