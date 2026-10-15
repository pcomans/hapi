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
        "king:taa-ii": (["Taa II"], (17,)),
        "king:ahmose-i": (["Ahmose I"], (18,)),
        "king:akhenaten": (["Akhenaten"], (18,)),
        "king:setnakhte": (["Setnakhte"], (20,)),
        "king:ramesses-ii": (["Ramesses II"], (19,)),
        "king:ramesses-v": (["Ramesses V"], (20,)),
        "king:sety-i": (["Sety I"], (19,)),
        "king:sety-ii": (["Sety II"], (19,)),
        "king:thutmose-i": (["Thutmose I"], (18,)),
        "king:thutmose-iv": (["Thutmose IV"], (18,)),
        "king:shoshenq-i": (["Shoshenq I"], (22,)),
        "king:amenemhat-i": (["Amenemhat I"], (12,)),
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
    # 317 until 2026-10-14; the dyn15-18 chunk added 36 women, one of them (Mutneferet A's
    # Taosids stub) a woman already counted.
    assert len(women) == 352
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
    mutneferet = women["dodson_hilton:Mutneferet A"]
    assert mutneferet.dh_rows == (("Mutneferet A", "The Power and the Glory"), ("Mutneferet A", "The Taosids"))
    assert (mutneferet.dynasties, mutneferet.family_names) == ((18,), ("Thutmose I", "Thutmose II"))


def test_a_woman_of_two_dynasties_has_no_dynasty_to_be_contradicted(women) -> None:
    """Ahmes-Nefertiry, daughter of Taa II (Dyn 17) and wife of Ahmose I (Dyn 18): D&H's
    Taosids section gives her no single dynasty, so no record's dynasty rules her out."""
    ahmes_nefertiry = women["dodson_hilton:Ahmes-Nefertiry"]
    assert (ahmes_nefertiry.labels, ahmes_nefertiry.dynasties, ahmes_nefertiry.family_names) == (
        ("Ahmes-Nefertiry",), (), ("Ahmose I", "Taa II"))
    ahhotep = women["dodson_hilton:Ahhotep I"]
    assert (ahhotep.labels, ahhotep.dynasties, ahhotep.family_names) == (
        ("Ahhotep I", "Ahhotep"), (), ("Taa II", "Ahmose I"))


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


def test_ahhotep_i_is_chosen_by_her_husband_not_by_a_dynasty_she_lacks(index) -> None:
    """D&H's two Ahhoteps (The Taosids): Ahhotep I, wife of Taa II and mother of Ahmose I,
    and Ahhotep II, perhaps wife of Kamose. Neither has a single dynasty, so a Dynasty 18
    record alone cannot choose; a record naming Taa II or Ahmose I does."""
    assert resolve(index, "Ahhotep", kings={"king:taa-ii"}) == ("resolved", ["dodson_hilton:Ahhotep I"], "family")
    assert resolve(index, "Ahhotep", kings={"king:ahmose-i"}, dynasty=18) == (
        "resolved", ["dodson_hilton:Ahhotep I"], "family")
    assert resolve(index, "Ahhotep", dynasty=18) == (
        "ambiguous", ["dodson_hilton:Ahhotep I", "dodson_hilton:Ahhotep II"], None)


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
    # A cued name no royal woman or female ruler bears never falls to a king: "Ahmose" (hms)
    # reaches only D&H's princesses Ahmes A/B, on the third tier, and only a named king picks.
    assert resolve(index, "Ahmose") == ("ambiguous", ["dodson_hilton:Ahmes A", "dodson_hilton:Ahmes B"], None)
    assert resolve(index, "Ahmose I", cue=False) == ("resolved", ["king:ahmose-i"], None)
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


def found(index, text, *, kings=frozenset(), dynasty=None):
    f = rw.resolve_royal_woman(index, text, record_king_ids=set(kings), record_dynasty=dynasty)
    return f["status"], f["resolution_method"], f["target_ids"], f["context_rule"]


def test_the_weak_sign_tier_reaches_the_other_sources_renderings_of_a_dh_woman(index) -> None:
    """Spellings attested in the committed Porter & Moss and Leprohon sources for women D&H
    spell otherwise; each differs from the D&H label by the key's documented rules only. A
    weak-sign match counts only when the record confirms it: a named family king, or a single
    dynasty among hers and her family kings'."""
    # PM I.2, 599 "ʿAhmosi Nefertere" for D&H "Ahmes-Nefertiry": D&H give her no dynasty of
    # her own; her father Taa II (Dyn 17) and husband Ahmose I (Dyn 18) confirm 17 and 18.
    assert found(index, "ʿAhmosi Nefertere") == ("unmatched", "weak_sign_skeleton", [], "weak_sign_unconfirmed")
    for dynasty in (17, 18):
        assert found(index, "ʿAhmosi Nefertere", dynasty=dynasty) == (
            "resolved", "weak_sign_skeleton", ["dodson_hilton:Ahmes-Nefertiry"], None), dynasty
    assert found(index, "ʿAhmosi Nefertere", kings={"king:ahmose-i"}) == (
        "resolved", "weak_sign_skeleton", ["dodson_hilton:Ahmes-Nefertiry"], None)
    # Known limitation: a record's dynasty is the object's. A Ramesside stela of the deified
    # queen (Dyn 19-20) is not confirmed by it; only a named family king would be.
    for dynasty in (19, 20):
        assert found(index, "ʿAhmosi Nefertere", dynasty=dynasty) == (
            "unmatched", "weak_sign_skeleton", [], "weak_sign_unconfirmed"), dynasty
    # PM I.2, 761 "Nebttaui" (rule 4, w/u) for D&H "Nebettawy A" (Dyn 19, daughter of Ramesses II).
    assert found(index, "Nebttaui", dynasty=19) == ("resolved", "weak_sign_skeleton", ["dodson_hilton:Nebettawy A"], None)
    assert found(index, "Nebttaui") == ("unmatched", "weak_sign_skeleton", [], "weak_sign_unconfirmed")
    # Leprohon 18.01's "Tetisheri" (rule 3) for D&H "Tetisherit": her D&H entry names no king
    # (only her father Tjenna) and no dynasty, so no record can confirm her on this tier.
    for dynasty in (None, 17, 18):
        assert found(index, "Tetisheri", dynasty=dynasty) == ("unmatched", "weak_sign_skeleton", [], "weak_sign_unconfirmed")
    # PM I.2, 600 "ʿAhhotp": D&H's two Ahhoteps, told apart by the husband.
    assert found(index, "ʿAhhotp") == ("ambiguous", "weak_sign_skeleton",
                                       ["dodson_hilton:Ahhotep I", "dodson_hilton:Ahhotep II"], None)
    assert found(index, "ʿAhhotp", kings={"king:taa-ii"}) == ("resolved", "weak_sign_skeleton",
                                                             ["dodson_hilton:Ahhotep I"], "family")
    # PM I.2, 765 "Merytamun" (rule 4, ꞽ/y): six Meryetamuns; Ramesses II's daughter is E.
    assert found(index, "Merytamun")[:2] == ("ambiguous", "weak_sign_skeleton")
    assert found(index, "Merytamun", kings={"king:ramesses-ii"}) == ("resolved", "weak_sign_skeleton",
                                                                     ["dodson_hilton:Meryetamun E"], "family")
    # PM I.2, 762 "Nefertari": D&H's Nefertiry D (wife) and E (daughter) are both Ramesses
    # II's and both Dynasty 19, so the record cannot choose; nothing is picked.
    assert found(index, "Nefertari", kings={"king:ramesses-ii"}, dynasty=19) == (
        "ambiguous", "weak_sign_skeleton",
        ["dodson_hilton:Nefertiry B", "dodson_hilton:Nefertiry C", "dodson_hilton:Nefertiry D Meryetmut",
         "dodson_hilton:Nefertiry E", "dodson_hilton:Nefertiry F"], None)
    # An alternative name is keyed too: "Ankhesenamun" (D&H's alt for Ankhesenpaaten), rule 4.
    assert found(index, "Ankhesenamon", dynasty=18) == (
        "resolved", "weak_sign_skeleton", ["dodson_hilton:Ankhesenpaaten"], None)
    # The bracketed D&H form itself reaches her (rule 1 keeps the restored letters).
    assert found(index, "[Mut]metennefer", dynasty=19) == (
        "resolved", "weak_sign_skeleton", ["dodson_hilton:[Mut]metennefer"], None)
    # A woman who later reigned is still the king on this tier: rule 4 on "Sobkneferu".
    assert found(index, "Sobkneferu", dynasty=12) == ("resolved", "raw_exact", ["king:sobekneferu"], None)
    assert found(index, "Sebekneferu", dynasty=12) == ("resolved", "weak_sign_skeleton", ["king:sobekneferu"], None)


def test_a_three_consonant_key_takes_a_named_family_king_only(index) -> None:
    # "Ahmose" (iꜥḥ-ms, hms): D&H's Ahmes A (Dyn 17, daughter of Taa II) and Ahmes B (Dyn 18,
    # wife of Thutmose I). A dynasty narrows but cannot confirm three consonants.
    assert found(index, "Ahmose") == ("ambiguous", "weak_sign_skeleton", ["dodson_hilton:Ahmes A", "dodson_hilton:Ahmes B"], None)
    assert found(index, "Ahmose", dynasty=18) == ("unmatched", "weak_sign_skeleton", [], "weak_sign_unconfirmed")
    assert found(index, "Ahmose", kings={"king:thutmose-i"}) == ("resolved", "weak_sign_skeleton", ["dodson_hilton:Ahmes B"], "family")
    assert found(index, "Ahmose", kings={"king:taa-ii"}, dynasty=17) == (
        "resolved", "weak_sign_skeleton", ["dodson_hilton:Ahmes A"], "family")
    # "Inhapi" (rule 4) for Inhapy (Dyn 17, wife of Taa II); "Satre" for Sitre A (Ramesses I, Sety I).
    assert found(index, "Inhapi", dynasty=17) == ("unmatched", "weak_sign_skeleton", [], "weak_sign_unconfirmed")
    assert found(index, "Inhapi", kings={"king:taa-ii"}) == ("resolved", "weak_sign_skeleton", ["dodson_hilton:Inhapy"], None)
    assert found(index, "Satre", dynasty=19) == ("unmatched", "weak_sign_skeleton", [], "weak_sign_unconfirmed")
    assert found(index, "Satre", kings={"king:sety-i"}) == ("resolved", "weak_sign_skeleton", ["dodson_hilton:Sitre A"], None)
    # Four consonants: the dynasty confirms.
    assert found(index, "Ahhotepty", dynasty=13) == ("resolved", "weak_sign_skeleton", ["dodson_hilton:Ahhotepti"], None)
    assert found(index, "Nubhotpet", dynasty=12) == ("resolved", "weak_sign_skeleton", ["dodson_hilton:Nubhotepet"], None)


NFR = ["dodson_hilton:Neferet B", "dodson_hilton:Neferet I", "dodson_hilton:Neferet II", "dodson_hilton:Neferet Q",
       "dodson_hilton:Neferet R", "dodson_hilton:Neferu A", "dodson_hilton:Neferu B", "dodson_hilton:Neferu I",
       "dodson_hilton:Neferu II", "dodson_hilton:Neferu III", "dodson_hilton:Neferu Q"]
HNTT = ["dodson_hilton:Henttawy A", "dodson_hilton:Henttawy B", "dodson_hilton:Henttawy C", "dodson_hilton:Henttawy D",
        "dodson_hilton:Henttawy Q", "dodson_hilton:Henutwati"]


def test_the_differently_spelt_keys_are_derived_from_the_authority_alone(index) -> None:
    """Derived from the authority's own spellings, pinned: the base spellings of every label
    keyed under a key, per target; a key two of whose targets share no spelling is withheld.
    A single target's own spellings (Tawosret, whom the king lists call Tausret) are one name."""
    assert rw.different_spellings(index) == {
        "hntt": ("henttawy", "henutwati"),
        "nbt": ("nebetia", "nebtit", "nebtu"),
        "nfr": ("neferet", "neferu"),
        # female-rulers.json's king_name "Neferusobek" (the king Sobkneferu) beside D&H's princess.
        "nfrsbk": ("neferusobek", "neferusobk"),
        "tntmn": ("tentamun", "tintamun"),
    }
    assert index.weak_sign_spellings["nfr"]["dodson_hilton:Neferu II"] == {"neferu"}
    assert index.weak_sign_spellings["tsr"] == {"dodson_hilton:Tawosret": {"tawosret", "tausret"}}
    assert index.weak_sign_spellings["mrtrhtšps"] == {
        "dodson_hilton:Meryetre(-Hatshepsut)": {"meryetre(-hatshepsut)", "meryetre-hatshepsut"}}
    assert not rw.spelled_differently(index, "tsr") and rw.spelled_differently(index, "nfr")


def test_a_differently_spelt_key_never_resolves(index) -> None:
    """A key the authority reaches under several spellings for different women cannot tell
    whether those are one name, so nothing in the record may pick: not a dynasty, and not a
    family king either, who would pick the woman linked to him whatever her name. The mention
    is ambiguous, `weak_sign_different_spellings`, before any narrowing (egyptologist review
    of the weak-sign key, P1)."""
    withheld = ("ambiguous", "weak_sign_skeleton", NFR, "weak_sign_different_spellings")
    # The P1 case: "Nofret" (nfr) on a record naming Amenemhat I reached Neferu III, his
    # daughter, through the family filter, though Nofret is nfrt, Neferet, not nfrw.
    assert index.family_king_ids["dodson_hilton:Neferu III"] == {"king:amenemhat-i"}
    assert found(index, "Nofret", kings={"king:amenemhat-i"}) == withheld
    assert found(index, "Nofret", kings={"king:amenemhat-i"}, dynasty=12) == withheld
    assert found(index, "Nefru", kings={"king:mentuhotep-ii"}) == withheld
    assert found(index, "Nefru", dynasty=11) == withheld
    # hntt: Henttawy A-Q and Henutwati (wife of Ramesses V); no king, no dynasty picks.
    hntt = ("ambiguous", "weak_sign_skeleton", HNTT, "weak_sign_different_spellings")
    assert found(index, "Henttaui") == found(index, "Henttaui", dynasty=19) == found(index, "Henttaui", dynasty=21) == hntt
    assert found(index, "Henttaui", kings={"king:ramesses-ii"}) == found(index, "Henutwaty", kings={"king:ramesses-v"}) == hntt
    # tntmn: the authority spells Tentamun and Tintamun, so the rule withholds them too, where
    # a hand-written list once called them one name; a dynasty no longer picks Tintamun.
    tntmn = ("ambiguous", "weak_sign_skeleton", ["dodson_hilton:Tentamun A", "dodson_hilton:Tentamun B",
                                                 "dodson_hilton:Tintamun"], "weak_sign_different_spellings")
    assert found(index, "Tentamon", dynasty=18) == found(index, "Tentamon", dynasty=20) == tntmn
    assert found(index, "Tentamon", kings={"king:thutmose-iv"}) == tntmn
    # nfrsbk: "Neferusobek" (king_name) and D&H's princess "Neferusobk", both Dynasty 12.
    assert found(index, "Nefrusobk", dynasty=12) == ("ambiguous", "weak_sign_skeleton", [
        "dodson_hilton:Neferusobk", "dodson_hilton:Sobkneferu"], "weak_sign_different_spellings")
    # One woman's own spellings are not two: Tawosret / Tausret still reaches the king.
    assert found(index, "Tawosre", kings={"king:sety-ii"}) == ("resolved", "weak_sign_skeleton", ["king:tausret"], None)


def test_a_numeral_in_the_mention_must_be_the_candidates(index) -> None:
    assert rw.weak_sign_entry("Neferu II") == ("nfr", frozenset({"II"}))
    assert rw.weak_sign_entry("Tiye B Mereniset") == ("tmrns", frozenset())
    assert rw.weak_sign_entry("Cleopatra VII Philopator") == ("clptrphlptr", frozenset({"VII"}))
    # A wrapped numeral is stripped from the authority's key too (Codex review): with V or X in
    # it, a "VII." left in the label would key as "clptrv".
    for label in ("Cleopatra VII.", "Cleopatra (VII)", "Cleopatra [VII]", "Cleopatra VII"):
        assert rw.weak_sign_entry(label) == ("clptr", frozenset({"VII"})), label
    assert found(index, "Cleopatra III") == ("unmatched", None, [], None)
    assert found(index, "Ahhotep III") == ("unmatched", None, [], None)
    # A vowel variant meets on the weak-sign tier and the numeral picks; the Greek K does not
    # (c/q → k was dropped).
    assert found(index, "Cleopatre II", dynasty=33) == ("resolved", "weak_sign_skeleton", ["king:cleopatra-ii"], None)
    assert found(index, "Cleopatre", dynasty=33) == ("ambiguous", "weak_sign_skeleton",
                                                     ["king:cleopatra-i", "king:cleopatra-ii", "king:cleopatra-vii-p"], None)
    assert found(index, "Kleopatra II", dynasty=33) == ("unmatched", None, [], None)
    # A wrapped numeral is a numeral (Codex review): "(II)", "[II]", "II." pick Cleopatra II.
    for wrapped in ("(II)", "[II]", "II."):
        assert found(index, f"Cleopatre {wrapped}", dynasty=33) == (
            "resolved", "weak_sign_skeleton", ["king:cleopatra-ii"], None), wrapped
    assert [rw.numeral_of(t) for t in ("II", "(II)", "[VII]", "III.", "ii", "Vi", "()", "Ines")] == [
        "II", "II", "VII", "III", None, None, None, None]
    assert found(index, "Ahhotp I", kings={"king:taa-ii"}) == ("resolved", "weak_sign_skeleton", ["dodson_hilton:Ahhotep I"], None)
    assert found(index, "Ahhotp II") == ("unmatched", "weak_sign_skeleton", [], "weak_sign_unconfirmed")
    # "II" leaves Neferu II and Neferet II, "III" Neferu III alone; nfr is a differently spelt
    # key, so even then no king picks (the numeral narrows the candidates, nothing more).
    assert found(index, "Nefru II", kings={"king:mentuhotep-ii"}) == ("ambiguous", "weak_sign_skeleton", [
        "dodson_hilton:Neferet II", "dodson_hilton:Neferu II"], "weak_sign_different_spellings")
    assert found(index, "Nefru III", kings={"king:mentuhotep-ii"}) == ("ambiguous", "weak_sign_skeleton", [
        "dodson_hilton:Neferu III"], "weak_sign_different_spellings")


def test_a_named_family_king_overrides_the_records_dynasty_on_every_tier(index) -> None:
    """Tentsepeh A (D&H, Dynasty 21), mother of Shoshenq I (Dynasty 22): a Dynasty 22 record
    naming him is hers, on the exact, the claim-graph and the weak-sign tier alike."""
    assert found(index, "Tentsepeh", dynasty=22) == ("unmatched", "raw_exact", [], "record_dynasty_contradicts")
    assert found(index, "Tentsepeh", kings={"king:shoshenq-i"}, dynasty=22) == (
        "resolved", "raw_exact", ["dodson_hilton:Tentsepeh A"], None)
    assert found(index, "Téntsepeh", kings={"king:shoshenq-i"}, dynasty=22) == (
        "resolved", "committed_normalized", ["dodson_hilton:Tentsepeh A"], None)
    assert found(index, "Tintsepeh", dynasty=22) == ("unmatched", "weak_sign_skeleton", [], "record_dynasty_contradicts")
    assert found(index, "Tintsepeh", kings={"king:shoshenq-i"}, dynasty=22) == (
        "resolved", "weak_sign_skeleton", ["dodson_hilton:Tentsepeh A"], None)
    assert found(index, "Nebttaui", dynasty=20) == ("unmatched", "weak_sign_skeleton", [], "record_dynasty_contradicts")
    assert found(index, "Nebttaui", kings={"king:ramesses-ii"}, dynasty=20) == (
        "resolved", "weak_sign_skeleton", ["dodson_hilton:Nebettawy A"], None)
    assert found(index, "Nefertiti", kings={"king:akhenaten"}, dynasty=22) == (
        "resolved", "raw_exact", ["dodson_hilton:Nefertiti"], None)


def test_the_weak_sign_tier_runs_only_when_the_first_two_find_nothing(index) -> None:
    """Over every indexed label: the exact tier answers, and a diacritic variant of it (which
    the exact tier misses) is answered by the claim-graph keys. The third tier never sees a
    name the first two resolve, so it changes none of their results."""
    labels = [label for label in index.exact if label.strip()]
    assert len(labels) == 419
    for label in labels:
        f = rw.resolve_royal_woman(index, label, record_king_ids=set(), record_dynasty=None)
        assert f["resolution_method"] == "raw_exact", label
        assert f["candidate_ids"] == sorted(index.exact[label]), label
        if "e" in label:
            variant = label.replace("e", "é", 1)
            g = rw.resolve_royal_woman(index, variant, record_king_ids=set(), record_dynasty=None)
            assert g["resolution_method"] == "committed_normalized", variant
            assert set(g["candidate_ids"]) >= set(f["candidate_ids"]), variant
    # The tier's own method name is reported, and only when it supplies the candidates.
    assert found(index, "Nofretete", dynasty=18) == ("resolved", "weak_sign_skeleton", ["dodson_hilton:Nefertiti"], None)
    assert found(index, "Nofretete", kings={"king:akhenaten"}) == (
        "resolved", "weak_sign_skeleton", ["dodson_hilton:Nefertiti"], None)
    assert found(index, "Néfertiti")[1] == "committed_normalized"
    assert found(index, "Nefertiti")[1] == "raw_exact"


def test_the_weak_sign_tier_never_reaches_a_king_and_never_matches_below_the_minimum(index) -> None:
    # The female rulers are keyed by their female-rulers.json king_name only (a leading
    # "Queen" dropped), never by the king authority's other labels: the stub's "(Queen)
    # Sobekneferu" for the king Sobkneferu is not keyed, her D&H label and "Neferusobek" are.
    assert {t for targets in index.weak_sign.values() for t in targets if t.startswith("king:")} == {
        "king:arsinoe-ii", "king:berenike-ii", "king:cleopatra-i", "king:cleopatra-ii", "king:berenike",
        "king:cleopatra-vii-l", "king:cleopatra-vii-p", "king:neith-iqeret"}
    assert index.weak_sign["sbknfr"] == {"dodson_hilton:Sobkneferu"}
    assert index.weak_sign["nfrsbk"] == {"dodson_hilton:Neferusobk", "dodson_hilton:Sobkneferu"}
    assert index.weak_sign["nthqr"] == {"king:neith-iqeret"}
    # The kings D&H names as husbands and fathers are not reachable under a cue, even when
    # their names are spelt as the key would fold them.
    for text in ("Amenhotep III", "Amenhotep", "Amenhotpe", "Akhenaten", "Akhenaton", "Ramesses II", "Ramses",
                 "Thutmose IV", "Thutmosis", "Taa II", "Shoshenq I"):
        assert found(index, text) == ("unmatched", None, [], None), text
    # Below the minimum (two consonants or fewer): no match, so "Queen Tiye" variants and
    # the short names stay with the first two tiers only.
    for text in ("Teye", "Tiy", "Teje", "Kija", "Esi", "Aset", "Tuja"):
        assert found(index, text) == ("unmatched", None, [], None), text
    assert found(index, "Ahhotepti") == ("resolved", "raw_exact", ["dodson_hilton:Ahhotepti"], None)


def test_the_collision_helpers_agree_with_the_index(index) -> None:
    collisions = rw.weak_sign_collisions(index)
    new = rw.new_weak_sign_collisions(index)
    assert collisions["hntt"] == new["hntt"] == tuple(HNTT)
    assert new["tntmn"] == ("dodson_hilton:Tentamun A", "dodson_hilton:Tentamun B", "dodson_hilton:Tintamun")
    # Same-named women are the exact tier's collisions, not new ones.
    assert collisions["stmḫb"] == tuple(sorted(index.exact["isetemkheb"])) and "stmḫb" not in new
    # female-rulers.json's king_name "Neferusobek" for the king Sobkneferu meets D&H's
    # princess Neferusobk (both Dynasty 12); the Ptolemaic female rulers share their names.
    assert new["nfrsbk"] == ("dodson_hilton:Neferusobk", "dodson_hilton:Sobkneferu")
    assert new["clptr"] == ("king:cleopatra-i", "king:cleopatra-ii", "king:cleopatra-vii-p")
    assert set(new) == {"brnk", "clptr", "hntt", "nbt", "nfr", "nfrsbk", "tntmn"}


def test_the_cue_and_the_records_dynasty_are_read_exactly() -> None:
    assert [rw.royal_woman_cued(text, len(text)) for text in (
        "Relief of Queen ", "Queen Mother ", "King's Wife ", "King’s Great Wife ", "Great Royal Wife ",
        "King's Mother ", "King's Daughter ", "Princess ", "God's Wife ", "God's Wife of Amun ",
        "Divine Adoratrice of Amun ", "Queen: ", "Queen - ", "Queen, ", "Relief of ", "Statue of King ",
        "Queen; ")] == [True] * 14 + [False, False, False]
    assert [rw.single_dynasty(v) for v in ("Dynasty 18", "late Dynasty 18", "Dynasty 12, late", "18th Dynasty",
                                           "Dynasty 19–20", "Dynasty 26, or later", "", None)] == [
        18, 18, 12, 18, None, None, None, None]


def test_a_different_name_outside_dodson_and_hilton_can_still_meet_a_womans_key(index) -> None:
    """A known limit, pinned (egyptologist review of the climb): the spelling rule sees only
    the authority's own spellings. "Isetweret" (ꜣst-wrt, an Iset name) and D&H's Sitre A
    (zꜣt-rꜥ) both key `str`, so a record naming Sitre's family king Sety I reaches Sitre A.
    The gates bound it: a three-consonant key needs a named family king, and a contradicting
    dynasty is refused."""
    assert found(index, "Isetweret", kings={"king:sety-i"}) == (
        "resolved", "weak_sign_skeleton", ["dodson_hilton:Sitre A"], None)  # sole candidate, confirmed by Sety I
    assert found(index, "Isetweret", dynasty=19) == ("unmatched", "weak_sign_skeleton", [], "weak_sign_unconfirmed")
    assert found(index, "Isetweret", dynasty=18) == ("unmatched", "weak_sign_skeleton", [], "record_dynasty_contradicts")


def test_the_resolvers_numeral_reader_agrees_with_the_matchers() -> None:
    """Two readers of a regnal number must not drift (Rule 4): `numeral_of` reads each token
    (the resolver removes every numeral token before keying), the claim-graph matcher's
    `regnal_number_of` a trailing number on a whole name. On the matcher's documented forms,
    the last token gives the same number."""
    from pipeline.authority.claimgraph.matcher import regnal_number_of
    for name in ("Ramesses III", "Amenophis II.", "Psusennes I", "Userkare (I)", "Cleopatra VII"):
        assert rw.numeral_of(name.split()[-1]) == regnal_number_of(name), name
