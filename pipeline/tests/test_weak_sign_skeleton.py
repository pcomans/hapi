"""The weak-sign skeleton key: each documented rule on D&H labels and on the renderings the
other committed authority sources give the same names; every committed-source citation of
the module docstring checked row by row; the minimum length; and the authority-side
collision table over the Dodson & Hilton women, with the threshold decision it rests on."""

from __future__ import annotations

import collections
import json
import re
from pathlib import Path

import pytest

from pipeline.authority import royal_women as rw
from pipeline.authority import weak_sign_skeleton as module
from pipeline.authority.weak_sign_skeleton import MIN_WEAK_SIGN_CONSONANTS, consonant_count, weak_sign_skeleton

SOURCES = Path(rw.__file__).resolve().parent / "sources"


@pytest.fixture(scope="module")
def women() -> list[rw.RoyalWoman]:
    return rw.load_royal_women()


# --- The rules, on cited examples ----------------------------------------------------------

def test_rule_1_brackets_separators_half_rings_and_the_fold() -> None:
    # Restored letters stay, as labels_for reads them; the brackets go.
    assert weak_sign_skeleton("[Mut]metennefer") == weak_sign_skeleton("Mutmetennefer") == "mtmtnnfr"
    assert weak_sign_skeleton("Seneb[henas]") == weak_sign_skeleton("Senebhenas") == "snbhns"
    # D&H "Ahmes-Nefertiry"; PM I.2, 599 "ʿAhmosi Nefertere" (space, ʿ for the ꜥ of iꜥḥ).
    assert weak_sign_skeleton("Ahmes-Nefertiry") == weak_sign_skeleton("ʿAhmosi Nefertere") == "hmsnfrtr"
    # One name, mryt-ꞽmn: D&H "Meryetamun", PM I.2, 765 "Merytamun", PM I.1, 421 "Meryet-Amun".
    assert weak_sign_skeleton("Meryetamun") == weak_sign_skeleton("Merytamun") == weak_sign_skeleton("Meryet-Amun") == "mrtmn"
    # The transliteration glyphs and the German digraphs fold as the committed table says;
    # ꜣ and ꜥ fold to "a" and go with the vowels.
    assert weak_sign_skeleton("ꜥꜣ-ḫpr-kꜣ-rꜥ") == weak_sign_skeleton("Aakheperkare") == "ḫprkr"
    assert weak_sign_skeleton("Chnemetneferhedjet") == weak_sign_skeleton("Khnemetneferhedjet") == "ḫnmtnfrhḏ"
    assert weak_sign_skeleton("Nofretete") == weak_sign_skeleton("Nefertiti") == "nfrtt"
    assert weak_sign_skeleton("Meryetre(-Hatshepsut)") == weak_sign_skeleton("Meryetre-Hatshepsut") == "mrtrhtšps"
    # Digits are not a name.
    assert weak_sign_skeleton("–18P") == ""
    # The key strips no disambiguator: that is the resolver's, on the authority side.
    assert weak_sign_skeleton("Cleopatra VII") == "klptrv" != weak_sign_skeleton("Cleopatra") == "klptr"
    assert weak_sign_skeleton("Tiye B Mereniset") == "tbmrns" != weak_sign_skeleton("Tiye Mereniset") == "tmrns"


def test_rule_1_the_digraphs_dj_and_tj_are_decided_within_a_token() -> None:
    """German Umschrift with j for ꞽ: a j that opens a token after a d or t of the token
    before is the weak sign, not ḏ/ṯ."""
    assert weak_sign_skeleton("Sꜣt-Jmn") == weak_sign_skeleton("Sitamun") == "stmn"
    assert weak_sign_skeleton("Mrjt-Jmn") == weak_sign_skeleton("Meryetamun") == "mrtmn"
    assert weak_sign_skeleton("Nfrt-jrj") == weak_sign_skeleton("Nefertiry") == "nfrtr"
    assert weak_sign_skeleton("Jꜥḥ-ms-nfrt-jrj") == weak_sign_skeleton("Ahmes-Nefertiry") == "hmsnfrtr"
    # Within a token the digraph stands: ḏ is not d, ṯ is not t.
    assert weak_sign_skeleton("Nodjmet") == weak_sign_skeleton("Nedjemet") == "nḏm"
    assert weak_sign_skeleton("Djedmutesankh") == weak_sign_skeleton("ḏd-mwt-s-ꜥnḫ") == "ḏdmtsnḫ"
    assert weak_sign_skeleton("Sitdjehuty") == weak_sign_skeleton("Satdjehuti") == "stḏht"
    assert weak_sign_skeleton("Nedjmetes") == "nḏmts" != weak_sign_skeleton("Nedmetes") == "ndmts"


def test_rule_2_c_and_q_are_k() -> None:
    # pharaoh.se row Cleopatra-VII: display "Cleopatra VII", alt_labels "Kleopatra", nomen "Qliu pa dra …".
    assert weak_sign_skeleton("Cleopatra") == weak_sign_skeleton("Kleopatra") == "klptr"
    assert weak_sign_skeleton("Qliu pa dra") == weak_sign_skeleton("Kleopadra") == "klpdr"
    assert weak_sign_skeleton("Berenice") == weak_sign_skeleton("Berenike") == "brnk"
    # D&H's own Anuket- / Anuq- for the goddess ꜥnqt.
    assert weak_sign_skeleton("Anuketemheb") == weak_sign_skeleton("Anuqetemheb") == "nktmhb"
    assert weak_sign_skeleton("Dedetanuq") == weak_sign_skeleton("Dedetanuk") == "ddtnk"
    # After the fold: the German ch is kh, not k-h.
    assert weak_sign_skeleton("Chnemet") == weak_sign_skeleton("Khnemet") == "ḫnm"


def test_rule_3_one_final_t_of_the_folded_string_is_dropped() -> None:
    # D&H "Tetisherit" (pp. 118-119); Leprohon 18.01's note, "the Tetisheri pyramid".
    assert weak_sign_skeleton("Tetisherit") == weak_sign_skeleton("Tetisheri") == "ttšr"
    # PM I.2, 751 writes the optional ending in parentheses.
    assert weak_sign_skeleton("Tanezem(t)") == weak_sign_skeleton("Tanezem") == "tnzm"
    assert weak_sign_skeleton("Meryetaten-tasherit") == weak_sign_skeleton("Meryetaten-tasheri") == "mrttntšr"
    # The last token's final t only; a t exposed by dropping a final weak sign is kept, so
    # "Henttawy" keeps its hntt and "Ahhotepti" is not "Ahhotep".
    assert weak_sign_skeleton("Henttawy") == "hntt"
    assert weak_sign_skeleton("Ahhotepti") == "hhtpt" != weak_sign_skeleton("Ahhotep") == "hhtp"
    assert weak_sign_skeleton("Nubhotepti") == "nbhtpt" != weak_sign_skeleton("Nubhotepet") == "nbhtp"
    assert weak_sign_skeleton("Iset Ta-Hemdjert") == weak_sign_skeleton("Iset Ta-Hemdjer") == "stthmḏr"


def test_rule_4_vowels_and_the_weak_signs_i_y_w_j_are_dropped() -> None:
    # Vowels: D&H "Ahmes", pharaoh.se "Iah mesu" / "Ahmose", Leprohon "iah mes(u)".
    assert weak_sign_skeleton("Ahmes-Nefertiry") == weak_sign_skeleton("Ahmose-Nefertiry") == "hmsnfrtr"
    assert weak_sign_skeleton("Ahmes") == weak_sign_skeleton("Iah mesu") == weak_sign_skeleton("Ahmose") == "hms"
    assert weak_sign_skeleton("Ankhesenamun") == weak_sign_skeleton("Ankhesenamon") == "nḫsnmn"
    # ꞽ/y: D&H "Nefertiry", PM I.2, 762 "Nefertari", PM I.2, 599 "Nefertere".
    assert weak_sign_skeleton("Nefertiry") == weak_sign_skeleton("Nefertari") == weak_sign_skeleton("Nefertere") == "nfrtr"
    assert weak_sign_skeleton("ḫꜣstꞽ") == weak_sign_skeleton("Khasty") == weak_sign_skeleton("Khasti") == "ḫst"
    # w/u: D&H "Nebettawy", PM I.2, 761 "Nebttaui"; pharaoh.se "Semsu" for smsw.
    assert weak_sign_skeleton("Nebettawy") == weak_sign_skeleton("Nebttaui") == "nbtt"
    assert weak_sign_skeleton("smsw") == weak_sign_skeleton("Semsu") == "sms"
    # j outside dj/tj is the weak sign.
    assert weak_sign_skeleton("Jah") == weak_sign_skeleton("Iah") == ""  # one consonant left
    assert weak_sign_skeleton("Mutnodjmet") == weak_sign_skeleton("Mutnedjmet") == "mtnḏm"


def test_rule_5_the_minimum_is_three_consonants_digraphs_counting_one() -> None:
    assert MIN_WEAK_SIGN_CONSONANTS == 3
    # A digraph is one unit, written ḫ š ḏ ṯ, so the count is the key's length.
    assert [consonant_count(k) for k in ("ḫnm", "hntt", "ḏdmtsnḫ", "sththr", "tḫ", "nḏm", "")] == [3, 4, 7, 6, 2, 3, 0]
    # Three consonants: a key (the resolver takes it with a named family king only).
    assert [weak_sign_skeleton(n) for n in ("Inhapy", "Ahmes", "Sitre", "Mutemwia", "Khnemet", "Tawosret", "Hrere")] == [
        "nhp", "hms", "str", "mtm", "ḫnm", "tsr", "hrr"]
    # Two or fewer: no key.
    assert [weak_sign_skeleton(n) for n in (
        "Tiye", "Tey", "Ti", "Tuy", "Tyti", "Kiya", "Iset", "Huy", "Iy", "Takhat", "Tjuiu", "Aat", "Tem")] == [""] * 13
    assert [weak_sign_skeleton(n) for n in ("Neferu", "Neferet", "Nebtit")] == ["nfr", "nfr", "nbt"]
    # "Takhat" is tkh once the final t is dropped: two consonants, not three letters.
    assert weak_sign_skeleton("Takhat") == "" and weak_sign_skeleton("Takhaut") == ""


def test_distinct_names_that_differ_only_in_what_the_key_keeps_stay_apart() -> None:
    assert weak_sign_skeleton("Isetneferet") == "stnfr" != weak_sign_skeleton("Isetemkheb") == "stmḫb"
    assert weak_sign_skeleton("Sitamun") == "stmn" != weak_sign_skeleton("Sitmut") == "stm"
    assert weak_sign_skeleton("Bintanath") == "bntnth" != weak_sign_skeleton("Bentʿanta") == "bntnt"
    assert weak_sign_skeleton("Henuttaneb") == "hnttnb" != weak_sign_skeleton("Henttawy") == "hntt"
    assert weak_sign_skeleton("Neferure") == "nfrr" != weak_sign_skeleton("Nefertiry") == "nfrtr"


# --- Every committed-source citation in the module docstring, row by row -------------------

def _rows(source: str) -> list[dict]:
    return [json.loads(line) for line in (SOURCES / source / "reconciled.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _field(row: dict, path: str):
    for part in re.split(r"\.|\[|\]", path):
        if part == "":
            continue
        row = row[int(part)] if part.isdigit() else row[part]
    return row


CITATIONS = [
    # (source, row-id field, row id, field path, exact value, page field, page)
    ("porter-moss-theban-necropolis", "tomb_id", "QV68", "occupant_name", "Merytamun", "source_citation.page", 765),
    ("porter-moss-theban-necropolis", "tomb_id", "TT358", "occupant_alt_names[0]", "Meryet-Amun", "source_citation.page", 421),
    ("porter-moss-theban-necropolis", "tomb_id", "DAN-AhmosiNefertere", "occupant_name", "ʿAhmosi Nefertere",
     "source_citation.page", 599),
    ("porter-moss-theban-necropolis", "tomb_id", "QV33", "occupant_name", "Tanezem(t)", "source_citation.page", 751),
    ("porter-moss-theban-necropolis", "tomb_id", "QV60", "occupant_name", "Nebttaui", "source_citation.page", 761),
    ("porter-moss-theban-necropolis", "tomb_id", "QV66", "occupant_name", "Nefertari", "source_citation.page", 762),
    ("porter-moss-theban-necropolis", "tomb_id", "TT38", "occupant_name", "Zeserkaraʿsonb", "source_citation.page", 69),
    ("leprohon-2013-titulary", "leprohon_id", "leprohon-21.05", "birth_names[0].transliteration", "imn m ipt",
     "source_citation.printed_page", 140),
    ("leprohon-2013-titulary", "leprohon_id", "leprohon-21.05", "birth_names[0].anglicised", "imen em ipet",
     "source_citation.printed_page", 140),
    ("leprohon-2013-titulary", "leprohon_id", "leprohon-18.01", "birth_names[0].transliteration", "iꜥḥ ms(w)",
     "source_citation.printed_page", 95),
    ("leprohon-2013-titulary", "leprohon_id", "leprohon-18.01", "birth_names[0].anglicised", "iah mes(u)",
     "source_citation.printed_page", 95),
    ("leprohon-2013-titulary", "leprohon_id", "leprohon-18.01", "horus_names[1].source_note",
     "Found on the so-called Donation Stela from the Tetisheri pyramid at Abydos (CG 34002), for which see Klug "
     "2002, 15–21. The name change probably coincided with the expulsion of the Hyksos; see Leprohon 2010a, 11 n. "
     "21, and the references there.", "source_citation.printed_page", 95),
    ("leprohon-2013-titulary", "leprohon_id", "leprohon-16.02", "nebty_names[0].transliteration", "/// ḏḥwty",
     "source_citation.printed_page", 83),
    ("leprohon-2013-titulary", "leprohon_id", "leprohon-16.02", "nebty_names[0].anglicised", "/// djehuty",
     "source_citation.printed_page", 83),
    ("leprohon-2013-titulary", "leprohon_id", "leprohon-17.23", "golden_horus_names[0].transliteration", "/// nṯrw",
     "source_citation.printed_page", 90),
    ("leprohon-2013-titulary", "leprohon_id", "leprohon-17.23", "golden_horus_names[0].anglicised", "/// netjeru",
     "source_citation.printed_page", 90),
    ("leprohon-2013-titulary", "leprohon_id", "leprohon-33.03a", "display_name", "Berenike II", None, None),
    ("pharaoh-se", "slug", "Cleopatra-VII", "display", "Cleopatra VII", None, None),
    ("pharaoh-se", "slug", "Cleopatra-VII", "alt_labels[0]", "Kleopatra", None, None),
    ("pharaoh-se", "slug", "Cleopatra-VII", "nomen", "Qliu pa dra netjeret meret ites", None, None),
    ("pharaoh-se", "slug", "Ahmose-I", "birth_names[0].name", "Iah mesu", None, None),
    ("pharaoh-se", "slug", "Ahmose-I", "display", "Ahmose I", None, None),
    ("pharaoh-se", "slug", "Den", "throne_names[0].name", "Khasty", None, None),
    ("pharaoh-se", "slug", "Den", "throne_names[0].transliteration", "ḫꜢstꞽ", None, None),
    ("pharaoh-se", "slug", "Djoser", "horus_names[0].name", "Netjery khet", None, None),
    ("pharaoh-se", "slug", "Djoser", "horus_names[0].transliteration", "nṯrꞽ-ẖt", None, None),
    ("pharaoh-se", "slug", "Narmer", "throne_names[3].name", "Meni", None, None),
    ("pharaoh-se", "slug", "Narmer", "throne_names[3].transliteration", "mny", None, None),
    ("pharaoh-se", "slug", "Teti", "birth_names[1].name", "Teti", None, None),
    ("pharaoh-se", "slug", "Teti", "birth_names[1].transliteration", "tty", None, None),
    ("pharaoh-se", "slug", "Semerkhet", "throne_names[1].name", "Semsu", None, None),
    ("pharaoh-se", "slug", "Semerkhet", "throne_names[1].transliteration", "smsw", None, None),
    ("pharaoh-se", "slug", "Qaa", "throne_names[2].name", "Qebehu", None, None),
    ("pharaoh-se", "slug", "Qaa", "throne_names[2].transliteration", "ḳbhw", None, None),
    ("pharaoh-se", "slug", "Qaa", "throne_names[2].gardiner", "q-b-H-w-W15", None, None),
    ("pharaoh-se", "slug", "Tiu", "birth_names[0].name", "Tiu", None, None),
    ("pharaoh-se", "slug", "Tiu", "birth_names[0].transliteration", "t-ꞽ-w", None, None),
    ("tla-2018-names", "tla_id", "400409", "transliteration", "H̱nm.w", None, None),
    ("tla-2018-names", "tla_id", "400409", "translations[1].value", "Khnum", None, None),
    ("tla-2018-names", "tla_id", "400051", "transliteration", "Z-n-wsr.t", None, None),
    ("tla-2018-names", "tla_id", "400058", "transliteration", "Z-n-wsr.t", None, None),
    ("tla-2018-names", "tla_id", "400058", "translations[1].value", "Senwosret", None, None),
    ("tla-2018-names", "tla_id", "400020", "transliteration", "Mnṯ.w-ḥtp.w", None, None),
    ("tla-2018-names", "tla_id", "400020", "translations[1].value", "Mentuhotep", None, None),
    ("dodson-hilton-queens", "dh_id", "Ahmes-Nefertiry", "name", "Ahmes-Nefertiry", "source_citation.pdf_pages", "118-119"),
    ("dodson-hilton-queens", "dh_id", "Tetisherit", "name", "Tetisherit", "source_citation.pdf_pages", "118-119"),
    ("dodson-hilton-queens", "dh_id", "Ahmes B", "name", "Ahmes B", "source_citation.pdf_pages", "126-130"),
    ("dodson-hilton-queens", "dh_id", "Nebettawy A", "name", "Nebettawy A", "source_citation.pdf_pages", "157-162"),
    ("dodson-hilton-queens", "dh_id", "Meryetamun A", "name", "Meryetamun A", "source_citation.pdf_pages", "118-119"),
    ("dodson-hilton-queens", "dh_id", "Anuketemheb", "name", "Anuketemheb", "source_citation.pdf_pages", "178-180"),
    ("dodson-hilton-queens", "dh_id", "Anuqneferetweben", "name", "Anuqneferetweben", "source_citation.pdf_pages", "98-103"),
    ("dodson-hilton-queens", "dh_id", "Dedetanuq", "name", "Dedetanuq", "source_citation.pdf_pages", "98-103"),
    # The DIFFERENT_NAMES readings (royal_women.py) cite these pages.
    ("dodson-hilton-queens", "dh_id", "Henttawy A", "name", "Henttawy A", "source_citation.pdf_pages", "157-162"),
    ("dodson-hilton-queens", "dh_id", "Henttawy Q", "name", "Henttawy Q", "source_citation.pdf_pages", "190-194"),
    ("dodson-hilton-queens", "dh_id", "Henutwati", "spouse_names[0]", "Ramesses V", "source_citation.pdf_pages", "178-180"),
    ("dodson-hilton-queens", "dh_id", "Neferu I", "name", "Neferu I", "source_citation.pdf_pages", "81-82"),
    ("dodson-hilton-queens", "dh_id", "Neferu III", "name", "Neferu III", "source_citation.pdf_pages", "88-91"),
    ("dodson-hilton-queens", "dh_id", "Neferu A", "name", "Neferu A", "source_citation.pdf_pages", "98-103"),
    ("dodson-hilton-queens", "dh_id", "Neferu B", "name", "Neferu B", "source_citation.pdf_pages", "118-119"),
    ("dodson-hilton-queens", "dh_id", "Neferet I", "name", "Neferet I", "source_citation.pdf_pages", "88-91"),
    ("dodson-hilton-queens", "dh_id", "Neferet R", "name", "Neferet R", "source_citation.pdf_pages", "98-103"),
    ("dodson-hilton-queens", "dh_id", "Nebetia", "dynasty", 18, "source_citation.pdf_pages", "126-130"),
    ("dodson-hilton-queens", "dh_id", "Nebtu", "dynasty", 18, "source_citation.pdf_pages", "126-130"),
    ("dodson-hilton-queens", "dh_id", "Nebtit", "dynasty", 13, "source_citation.pdf_pages", "98-103"),
]


@pytest.mark.parametrize(("source", "id_field", "row_id", "path", "value", "page_field", "page"), CITATIONS,
                         ids=[f"{c[0]}/{c[2]}/{c[3]}" for c in CITATIONS])
def test_each_citation_names_a_committed_row_field_and_value(source, id_field, row_id, path, value, page_field, page) -> None:
    rows = [r for r in _rows(source) if r.get(id_field) == row_id]  # TLA's first row is a `_source` header
    assert rows, (source, row_id)
    matching = [r for r in rows if _field(r, path) == value]
    assert matching, (source, row_id, path, [_field(r, path) for r in rows])
    if page_field is not None:
        assert page in [_field(r, page_field) for r in matching], (source, row_id, page)


def test_the_docstring_cites_each_row_and_marks_the_uncommitted_books() -> None:
    doc = module.__doc__
    for source, _, row_id, _, _, _, _ in CITATIONS:
        if source != "dodson-hilton-queens":
            assert row_id in doc, row_id
    for cited_value in ("Merytamun", "Meryet-Amun", "ʿAhmosi Nefertere", "Tanezem(t)", "Nebttaui", "imen em ipet",
                        "iah mes(u)", "Tetisheri pyramid", "djehuty", "netjeru", "Berenike", "Kleopatra", "Qliu pa dra",
                        "Iah mesu", "Khasty", "Netjery khet", "Meni", "Teti", "Semsu", "Qebehu", "Tiu", "Anuketemheb",
                        "Anuqneferetweben", "Dedetanuq", "Tetisherit", "Nebettawy A", "H̱nm.w", "Z-n-wsr.t",
                        "Mnṯ.w-ḥtp.w", "Zeserkaraʿsonb", "Menkauhor", "Raʿdjedef", "Wadjkheperreʿ"):
        assert cited_value in doc, cited_value
    # The books that are on disk but not committed are marked so wherever they are cited; no
    # Gardiner section numbers are quoted; the rendering that contradicted the rules ("Tao"
    # for ḏḥwty-ꜥꜣ) is gone.
    assert "on\ndisk but NOT committed" in doc
    assert doc.count("not committed") == 4  # Leprohon's introduction three times, Beckerath 1999 once
    assert "Beckerath 1999" in doc and "Leprohon 2013, printed p. 1" in doc
    assert "Tao" not in doc and "§" not in doc


# --- The authority-side collision table and the threshold -----------------------------------

def women_collisions(women: list[rw.RoyalWoman]) -> tuple[int, dict[str, tuple[str, ...]], dict[str, tuple[str, ...]], list[str]]:
    """Over the D&H women alone, keyed as the authority side keys them (letters and numerals
    stripped): how many have a key, every key several women share, the groups no exact or
    claim-graph key already holds whole, and the women without a key."""
    groups: dict[str, set[str]] = collections.defaultdict(set)
    exact: dict[str, set[str]] = collections.defaultdict(set)
    normalized: dict[str, set[str]] = collections.defaultdict(set)
    keyed, unkeyed = 0, []
    for woman in women:
        names = [*woman.labels, *woman.alt_names]
        keys = {rw.weak_sign_entry(n)[0] for n in names} - {""}
        keyed += bool(keys)
        if not keys:
            unkeyed.append(woman.label)
        for key in keys:
            groups[key].add(woman.target_id)
        for name in names:
            exact[rw.surface_key(name)].add(woman.target_id)
            for key in rw.name_keys(name):
                normalized[key].add(woman.target_id)
    existing = [*exact.values(), *normalized.values()]
    colliding = {k: tuple(sorted(v)) for k, v in sorted(groups.items()) if len(v) > 1}
    new = {k: m for k, m in colliding.items() if not any(set(m) <= g for g in existing)}
    return keyed, colliding, new, unkeyed


UNREACHABLE = [
    "Aat", "Amenia", "Ashayet", "Bebi A", "Bebi B", "Didit", "Hapyu", "Harit", "Henut A", "Henut Q", "Henut[...]",
    "Henutpahuro[...]", "Henutpre[...]", "Huy", "Iah", "Iaret", "Ikui", "Imi", "Inni", "Ipu B", "Iryet", "Iset A",
    "Iset B", "Iset C", "Iset E", "Ita", "Itakayet A", "Itakayet B", "Itakayet C", "Itaweret", "Itawy A", "Iuef", "Iy",
    "Kawit", "Kayet", "Kemi A", "Kemi B", "Khnemet[...]", "Kiya", "Menet", "Menwi", "Nauny", "Nebet[...]h[...]a", "Neni",
    "Nensed[...]", "Nesta[...]", "Nubhir[...]", "Peshu", "Pyihia", "Pypuy", "Redji", "Resi", "Sebat", "Semat",
    "Sit[...]B", "Sit[...]JA", "Taiay", "Takhat A", "Takhat B", "Tani", "Tatau", "Tem", "Tey", "Ti", "Tia C", "Tia Q",
    "Tiaa A", "Tiaa B", "Tiye A", "Tiye C", "Tjin", "Tjuiu", "Tuia", "Tyti", "Wiay A", "Wiay B", "Ziwat", "[...]12A",
    "[...]12B", "[...]13E", "[...]17A", "[...]17B", "[...]19A", "[...]19B", "[...]19C", "[...]1A", "[...]21C",
    "[...]21D", "[...]21E", "[...]Jamenweret", "[...]Jheb", "[...]djeb", "[...]khesbed", "[...]taweret", "[R]uia",
    "–18P", "–18Q"]


def test_the_collision_table_over_the_dodson_and_hilton_women(women) -> None:
    """The authority-side collision analysis at the chosen threshold (three consonants),
    pinned. Of the 352 women, 255 have a key; 97 (two consonants or fewer, or lacunose) are
    unreachable on this tier. 34 keys are shared, by 106 women; 30 of those groups are D&H's
    own same-named women ("Tiye A"/"Tiye C"), which the exact tier already returns
    together. The key introduces four groups: three of different names (listed in
    `DIFFERENT_NAMES`, confirmed by a named family king only) and Tentamun/Tintamun, one
    name. Adding D&H chapters changes these numbers: update them with the new groups
    reviewed, never silently."""
    assert len(women) == 352
    keyed, colliding, new, unkeyed = women_collisions(women)
    assert keyed == 255
    assert unkeyed == UNREACHABLE and len(unkeyed) == 97
    assert len(colliding) == 34
    assert len({t for members in colliding.values() for t in members}) == 106
    assert sorted(colliding) == [
        "dnfr", "hhtp", "hms", "hntt", "hnttnb", "htb", "htšps", "mrtmn", "mrtpth", "mtnḏm", "mtt", "nbhtpt", "nbt",
        "nbtn", "nbtnh", "nbḫs", "nfr", "nfrhtp", "nfrpth", "nfrr", "nfrtr", "nsḫns", "nthhtp", "rdtns", "rnsnb",
        "sbkmsf", "snbhns", "sththr", "stmn", "stmḫb", "stnfr", "tntmn", "ḫnmtnfrhḏ", "ḫnmtnfrhḏtr"]
    assert new == {
        "hntt": rw.DIFFERENT_NAMES["hntt"]["members"],
        "nbt": rw.DIFFERENT_NAMES["nbt"]["members"],
        "nfr": rw.DIFFERENT_NAMES["nfr"]["members"],
        # Tentamun (Dyns 20-21) and Tintamun (Dyn 18): one name, a vowel apart.
        "tntmn": ("dodson_hilton:Tentamun A", "dodson_hilton:Tentamun B", "dodson_hilton:Tintamun"),
    }
    assert set(new) - set(rw.DIFFERENT_NAMES) == {"tntmn"}
    # The three-consonant keys several women share: two same-named groups, the alt-name
    # pair Tuy A / Mut-Tuy B (an exact-tier group), and the two different-name groups.
    assert {k: [m.split(":", 1)[1] for m in v] for k, v in colliding.items() if consonant_count(k) == 3} == {
        "hms": ["Ahmes A", "Ahmes B"],
        "htb": ["Iuhetibu A", "Iuhetibu B Fendy", "Iuhetibu C", "Iuhetibu Q"],
        "mtt": ["Mut-Tuy B", "Tuy A"],
        "nbt": ["Nebetia", "Nebtit", "Nebtu"],
        "nfr": ["Neferet B", "Neferet I", "Neferet II", "Neferet Q", "Neferet R", "Neferu A", "Neferu B", "Neferu I",
                "Neferu II", "Neferu III", "Neferu Q"]}


def test_the_threshold_decision_three_consonants_with_a_named_king_against_four(women, monkeypatch) -> None:
    """At four consonants the key never merges different names on its own, but 44 more women
    are unreachable, among them Ahmes A/B (hms), Inhapy (nhp), Sitre A (str), Mutemwia (mtm)
    and Khnemet (ḫnm, three consonants in four letters). At three it reaches them, and the
    resolver takes a three-consonant match with a named family king only, which is what
    the different-name groups need anyway."""
    keyed3, colliding3, new3, unkeyed3 = women_collisions(women)
    monkeypatch.setattr(module, "MIN_WEAK_SIGN_CONSONANTS", 4)
    keyed4, colliding4, new4, unkeyed4 = women_collisions(women)
    assert (keyed3, len(colliding3), sorted(new3)) == (255, 34, ["hntt", "nbt", "nfr", "tntmn"])
    assert (keyed4, len(colliding4), sorted(new4)) == (211, 29, ["hntt", "tntmn"])
    gained = sorted(set(unkeyed4) - set(unkeyed3))
    assert len(gained) == 44
    assert {"Ahmes A", "Ahmes B", "Inhapy", "Sitre A", "Mutemwia", "Khnemet", "Tawosret", "Hrere", "Nodjmet",
            "Neferet I", "Neferu II", "Nebtit", "Nebtu", "Nebetia", "Seneb A", "Sitmut"} <= set(gained)


class _StubKings:
    """Enough of a king authority to build the full index: the female rulers' king names."""

    NAMES = {"Hatshepsut": "king:hatshepsut", "Neferusobek": "king:sobekneferu", "Tausret": "king:tausret",
             "Queen Neith-Iqeret": "king:neith-iqeret", "Arsinoe II": "king:arsinoe-ii", "Berenike II": "king:berenike-ii",
             "Cleopatra I": "king:cleopatra-i", "Cleopatra II": "king:cleopatra-ii", "Berenike": "king:berenike",
             "Cleopatra VII Philopator": "king:cleopatra-vii-l", "Cleopatra VII": "king:cleopatra-vii-p"}

    def resolve(self, name: str) -> dict:
        found = [self.NAMES[name]] if name in self.NAMES else []
        return {"status": "resolved" if found else "unmatched", "target_ids": found}

    def labels(self, target_id: str) -> list[str]:
        return [n for n, t in self.NAMES.items() if t == target_id]

    def dynasties(self, target_id: str) -> tuple[int, ...]:
        return ()


def test_the_different_name_groups_are_exactly_the_index_members_or_the_index_refuses(women) -> None:
    index = rw.build_index(women, _StubKings())
    for key, group in rw.DIFFERENT_NAMES.items():
        assert tuple(sorted(index.weak_sign[key])) == group["members"], key
        assert consonant_count(key) >= MIN_WEAK_SIGN_CONSONANTS
        assert group["reading"]
    # A woman who leaves or joins a listed group is refused until the list is reviewed.
    without = [w for w in women if w.label != "Henutwati"]
    with pytest.raises(ValueError, match=r"DIFFERENT_NAMES\['hntt'\] lists .* but the index keys"):
        rw.build_index(without, _StubKings())
    # A partial index that holds none of a group is not asked about it.
    rw.build_index([w for w in women if w.label in ("Hatshepsut D", "Sobkneferu", "Tawosret", "Nefertiti")], _StubKings())


def test_a_capital_h_with_line_below_folds_as_kh() -> None:
    """TLA 400409 `H̱nm.w` = Khnum: H̱ has no precomposed capital, so the text is composed
    (NFC) after lowercasing, before the fold."""
    assert weak_sign_skeleton("H̱nm.w") == weak_sign_skeleton("Khnum") == weak_sign_skeleton("Chnum") == "ḫnm"
    assert weak_sign_skeleton("H\u0331nm.w") == weak_sign_skeleton("ẖnm.w") == "ḫnm"


def test_a_digraph_is_a_unit_of_the_folded_letters_never_of_letters_a_dropped_vowel_joins() -> None:
    """Menkauhor (mn-kꜣw-ḥr) is k + h, not the ḫ of Menkheperre; ḏ written dj stays ḏ."""
    assert weak_sign_skeleton("Menkauhor") == "mnkhr" != weak_sign_skeleton("Menkheperre") == "mnḫprr"
    assert weak_sign_skeleton("Menkauhor") != weak_sign_skeleton("Menkhor")
    # Porter & Moss renderings: the half-ring does not count, ḏ is kept.
    assert weak_sign_skeleton("Wadjkheperreʿ") == weak_sign_skeleton("Wadjkheperre") == "ḏḫprr"
    assert weak_sign_skeleton("Raʿdjedef") == weak_sign_skeleton("Radjedef") == "rḏdf" != weak_sign_skeleton("Radedef")
    # Within a token only: a separator between s and h is kept information.
    assert weak_sign_skeleton("Ahmes-Henutemipet") == "hmshntmp" != weak_sign_skeleton("Ahmeshenutemipet") == "hmšntmp"


def test_z_and_s_are_under_evaluation_and_stay_apart_for_now() -> None:
    """TLA 400051 `Z-n-wsr.t` is "Senwosret" and PM writes "Zeserkaraʿsonb": z/s is an
    attested convention, not adopted until the TLA measurement is redone."""
    assert weak_sign_skeleton("Z-n-wsr.t") == "znsr" != weak_sign_skeleton("Senwosret") == "snsr"
    assert weak_sign_skeleton("Zeserkaraʿsonb") == "zsrkrsnb" != weak_sign_skeleton("Djeserkaresonb") == "ḏsrkrsnb"
    assert weak_sign_skeleton("Mnṯ.w-ḥtp.w") == "mnṯhtp" != weak_sign_skeleton("Mentuhotep") == "mnthtp"
