"""The weak-sign skeleton key: each documented rule on D&H labels and on the renderings the
other committed authority sources give the same women, the minimum length, and the
authority-side collision table over the Dodson & Hilton women."""

from __future__ import annotations

import collections

import pytest

from pipeline.authority import royal_women as rw
from pipeline.authority.claimgraph import normalize
from pipeline.authority.weak_sign_skeleton import MIN_WEAK_SIGN_SKELETON_LEN, weak_sign_skeleton


@pytest.fixture(scope="module")
def women() -> list[rw.RoyalWoman]:
    return rw.load_royal_women()


def test_rule_0_disambiguators_and_digits_are_not_the_name() -> None:
    assert weak_sign_skeleton("Tiye B Mereniset") == weak_sign_skeleton("Tiye Mereniset") == "tmrns"
    assert weak_sign_skeleton("Nefertiry D Meryetmut") == weak_sign_skeleton("Nefertiry Meryetmut") == "nfrtrmrtm"
    assert weak_sign_skeleton("Khnemetneferhedjet II Weret") == weak_sign_skeleton("Khnemetneferhedjet Weret") == "khnmtnfrhdjtr"
    assert weak_sign_skeleton("Cleopatra VII") == weak_sign_skeleton("Cleopatra") == "clptr"
    # D&H's placeholder ids for unnamed women carry no name.
    assert weak_sign_skeleton("–18P") == weak_sign_skeleton("A") == ""


def test_rule_1_hyphens_spaces_half_rings_and_german_digraphs_do_not_count() -> None:
    # D&H "Ahmes-Nefertiry"; PM I.2, 599 "ʿAhmosi Nefertere" (space, ʿ for the ꜥ of iꜥḥ).
    assert weak_sign_skeleton("Ahmes-Nefertiry") == weak_sign_skeleton("ʿAhmosi Nefertere") == "hmsnfrtr"
    # D&H "Meryetamun"; PM I.2, 765 "Merytamun"; PM I.1, 421 "Meryet-Amun".
    assert weak_sign_skeleton("Meryetamun") == weak_sign_skeleton("Merytamun") == weak_sign_skeleton("Meryet-Amun") == "mrtmn"
    # The Egyptological glyphs and the German digraphs fold as the committed table says.
    assert weak_sign_skeleton("ꜥꜣ-ḫpr-kꜣ-rꜥ") == weak_sign_skeleton("Aakheperkare") == "khprkr"
    assert weak_sign_skeleton("Chnemetneferhedjet") == weak_sign_skeleton("Khnemetneferhedjet") == "khnmtnfrhdj"
    assert weak_sign_skeleton("Nofretete") == weak_sign_skeleton("Nefertiti") == "nfrtt"
    # Brackets around restored letters are the transcriber's; the letters stay.
    assert weak_sign_skeleton("Mutmetennefer") == "mtmtnnfr"


def test_rule_2_one_final_t_is_dropped_from_the_surface() -> None:
    # D&H "Tetisherit" (pp. 118-119); Leprohon 18.01's note, "the Tetisheri pyramid".
    assert weak_sign_skeleton("Tetisherit") == weak_sign_skeleton("Tetisheri") == "ttshr"
    # PM I.2, 751 writes the optional ending in parentheses.
    assert weak_sign_skeleton("Tanezem(t)") == weak_sign_skeleton("Tanezem") == "tnzm"
    assert weak_sign_skeleton("Meryetaten-tasherit") == weak_sign_skeleton("Meryetaten-tasheri") == "mrttntshr"
    # Only a surface-final t: a t exposed by dropping a final weak sign is kept, so
    # "Henttawy" keeps its hntt and "Ahhotepti" is not "Ahhotep".
    assert weak_sign_skeleton("Henttawy") == "hntt"
    assert weak_sign_skeleton("Ahhotepti") == "hhtpt" != weak_sign_skeleton("Ahhotep") == "hhtp"
    assert weak_sign_skeleton("Nubhotepti") == "nbhtpt" != weak_sign_skeleton("Nubhotepet") == "nbhtp"


def test_rule_3_vowels_and_the_weak_signs_i_y_w_j_are_dropped() -> None:
    # Vowels: D&H "Ahmes", pharaoh.se "Iah mesu" / "Ahmose", Leprohon "iah mes(u)".
    assert weak_sign_skeleton("Ahmes-Nefertiry") == weak_sign_skeleton("Ahmose-Nefertiry") == "hmsnfrtr"
    assert weak_sign_skeleton("Ankhesenamun") == weak_sign_skeleton("Ankhesenamon") == "nkhsnmn"
    # ꞽ/y: D&H "Nefertiry", PM I.2, 762 "Nefertari", PM I.2, 599 "Nefertere".
    assert weak_sign_skeleton("Nefertiry") == weak_sign_skeleton("Nefertari") == weak_sign_skeleton("Nefertere") == "nfrtr"
    # w/u: D&H "Nebettawy", PM I.2, 761 "Nebttaui".
    assert weak_sign_skeleton("Nebettawy") == weak_sign_skeleton("Nebttaui") == "nbtt"
    # j is the weak sign (Beckerath's Umschrift) except in the digraphs dj/tj for ḏ/ṯ.
    assert weak_sign_skeleton("Nodjmet") == weak_sign_skeleton("Nedjemet") == "ndjm"
    assert weak_sign_skeleton("Djedmutesankh") == weak_sign_skeleton("ḏd-mwt-s-ꜥnḫ") == "djdmtsnkh"
    assert weak_sign_skeleton("Mutnodjmet") == weak_sign_skeleton("Mutnedjmet") == "mtndjm"
    assert weak_sign_skeleton("Jah") == weak_sign_skeleton("Iah") == ""  # one consonant left
    assert weak_sign_skeleton("Sitdjehuty") == weak_sign_skeleton("Satdjehuti") == "stdjht"


def test_rule_4_the_minimum_is_four_consonants() -> None:
    assert MIN_WEAK_SIGN_SKELETON_LEN == 4 == normalize._MIN_SKELETON_LEN
    # Three consonants or fewer: no key, so no match on this tier.
    assert [weak_sign_skeleton(n) for n in (
        "Inhapy", "Ahmes", "Sitre", "Mutemwia", "Tawosret", "Hrere", "Tiye", "Tey", "Ti", "Tuy", "Tyti",
        "Kiya", "Iset", "Neferu", "Neferet", "Nebtit", "Huy", "Iy")] == [""] * 18
    # Four: a key.
    assert weak_sign_skeleton("Ahhotep") == "hhtp"
    assert weak_sign_skeleton("Takhat") == ""  # tkh once the final t is dropped: three letters


def test_distinct_names_that_differ_only_in_what_the_key_keeps_stay_apart() -> None:
    assert weak_sign_skeleton("Isetneferet") == "stnfr" != weak_sign_skeleton("Isetemkheb") == "stmkhb"
    assert weak_sign_skeleton("Sitamun") == "stmn" != weak_sign_skeleton("Sitmut") == ""
    assert weak_sign_skeleton("Bintanath") == "bntnth" != weak_sign_skeleton("Bentʿanta") == "bntnt"
    assert weak_sign_skeleton("Henuttaneb") == "hnttnb" != weak_sign_skeleton("Henttawy") == "hntt"
    assert weak_sign_skeleton("Neferure") == "nfrr" != weak_sign_skeleton("Nefertiry") == "nfrtr"


def women_collisions(women: list[rw.RoyalWoman]) -> tuple[int, dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
    """Over the D&H women alone (their labels and alternative names): how many have a key,
    every key several women share, and those groups no exact or claim-graph key already
    holds whole."""
    groups: dict[str, set[str]] = collections.defaultdict(set)
    exact: dict[str, set[str]] = collections.defaultdict(set)
    normalized: dict[str, set[str]] = collections.defaultdict(set)
    keyed = 0
    for woman in women:
        names = [*woman.labels, *woman.alt_names]
        keys = {weak_sign_skeleton(n) for n in names} - {""}
        keyed += bool(keys)
        for key in keys:
            groups[key].add(woman.target_id)
        for name in names:
            exact[rw.surface_key(name)].add(woman.target_id)
            for key in rw.name_keys(name):
                normalized[key].add(woman.target_id)
    existing = [*exact.values(), *normalized.values()]
    colliding = {k: tuple(sorted(v)) for k, v in sorted(groups.items()) if len(v) > 1}
    new = {k: m for k, m in colliding.items() if not any(set(m) <= g for g in existing)}
    return keyed, colliding, new


def test_the_collision_table_over_the_dodson_and_hilton_women(women) -> None:
    """The authority-side collision analysis, pinned. Of the 352 women, 215 have a key
    (the rest are shorter than four consonants or lacunose); 29 keys are shared, by 84
    women; 27 of those groups are D&H's own same-named women ("Tiye A"/"Tiye C"), which
    the exact tier already returns together. The key introduces two groups of its own,
    which the record's family or dynasty must tell apart. Adding D&H chapters changes
    these numbers: update them with the new groups reviewed, never silently."""
    assert len(women) == 352
    keyed, colliding, new = women_collisions(women)
    assert keyed == 215
    assert len(colliding) == 29
    assert len({t for members in colliding.values() for t in members}) == 84
    assert sorted(colliding) == [
        "dnfr", "hhtp", "hntt", "hnttnb", "htshps", "khnmtnfrhdj", "khnmtnfrhdjtr", "mrtmn", "mrtpth", "mtndjm",
        "nbhtpt", "nbkhs", "nbtn", "nbtnh", "nfrhtp", "nfrpth", "nfrr", "nfrtr", "nskhns", "nthhtp", "rdtns", "rnsnb",
        "sbkmsf", "snbhns", "sththr", "stmkhb", "stmn", "stnfr", "tntmn"]
    assert new == {
        # ḥnwt-tꜣwy (Henttawy, Dyns 19-21) and Henutwati (Dyn 20): the w of -wati goes.
        "hntt": ("dodson_hilton:Henttawy A", "dodson_hilton:Henttawy B", "dodson_hilton:Henttawy C",
                 "dodson_hilton:Henttawy D", "dodson_hilton:Henttawy Q", "dodson_hilton:Henutwati"),
        # Tentamun (Dyns 20-21) and Tintamun (Dyn 18): a vowel apart.
        "tntmn": ("dodson_hilton:Tentamun A", "dodson_hilton:Tentamun B", "dodson_hilton:Tintamun"),
    }
    # Same-named women collide on every tier; a group of this kind is the exact tier's.
    assert colliding["nfrtr"] == ("dodson_hilton:Nefertiry B", "dodson_hilton:Nefertiry C",
                                  "dodson_hilton:Nefertiry D Meryetmut", "dodson_hilton:Nefertiry E",
                                  "dodson_hilton:Nefertiry F")
    assert colliding["hhtp"] == ("dodson_hilton:Ahhotep I", "dodson_hilton:Ahhotep II")


def test_a_threshold_of_three_would_merge_neferu_with_neferet(women, monkeypatch) -> None:
    """Why the minimum is four: at three, nfrw (Neferu) and nfrt (Neferet), two names, are
    one twelve-woman key, and the cue "Ahmose" would reach the princesses Ahmes A/B."""
    from pipeline.authority import weak_sign_skeleton as module
    monkeypatch.setattr(module, "MIN_WEAK_SIGN_SKELETON_LEN", 3)
    assert module.weak_sign_skeleton("Neferu") == module.weak_sign_skeleton("Neferet") == "nfr"
    assert module.weak_sign_skeleton("Ahmose") == module.weak_sign_skeleton("Ahmes") == "hms"
    keyed, colliding, new = women_collisions(women)
    assert (keyed, len(colliding)) == (260, 35)
    assert len(new["nfr"]) == 11
    assert set(new) == {"hntt", "nbt", "nfr", "tntmn"}
