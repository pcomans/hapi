"""Weak-sign skeleton: a consonantal key for Egyptian royal women's names across modern
spelling conventions.

Egyptian script writes consonants only; a modern rendering adds vowels by convention and
renders the weak consonants ꞽ, y and w either as vowels, as y/w, or not at all, and ꜣ and ꜥ
as vowels or not at all. Two renderings of one name therefore differ in exactly those
letters, and in the feminine ending -t, which some renderings keep and others drop. This key
deletes what the conventions disagree on — the vowels, ꞽ y w, and ꜣ ꜥ — and keeps the rest,
so that the D&H label and another convention's rendering of the same name meet on one
string. Dropping ꜥ is a known cost: it is a full consonant that English renderings write as
a vowel or not at all, so the key gives it up. The key is lossy and recall-oriented: it is
the third and last tier of the royal-women resolver (`royal_women.py`), used only when the
exact and the claim-graph keys find nothing, never against the kings, and only with the
record's confirmation. The key itself knows nothing of D&H: it strips no disambiguating
letter or numeral (the resolver does that on the authority side, and matches a numeral the
mention carries).

Sources
-------
Committed rows are cited as source / row / field = value (page); each such citation is
checked row by row in `tests/test_weak_sign_skeleton.py`. Two books are cited that are on
disk but NOT committed (the `proprietary/books/` folder beside the checkout, PDF page
numbers): Leprohon 2013, *The Great Name* (its introduction; the committed Leprohon source
holds the catalogue rows only) and Beckerath 1999, *Handbuch der ägyptischen Königsnamen*
(the committed Beckerath source is the 1997 *Chronologie*). Gardiner, *Egyptian Grammar*
(3rd ed. 1957) is the standard reference for the alphabet and the feminine ending; it is
not on disk, and no section numbers are given.

Rules, in the order applied
---------------------------
1. **Tokens and the committed cross-convention fold.** The text is lowercased and composed
   (Unicode NFC) first: a capital H̱ has no precomposed form, so it would reach the fold as
   h + U+0331 and read as h; lowercased and composed it is ẖ, which folds to kh (TLA lemma
   400409 `H̱nm.w`, Khnum, `tla-2018-names`). Square brackets go (the letters a transcriber
   restores in them stay: "[Mut]metennefer" is Mutmetennefer, as the resolver's `labels_for`
   reads it). The text is split on spaces, hyphens and dots, and each token is folded by
   `claimgraph.normalize.translit_key` (unchanged): Beckerath's German digraphs (ch→kh,
   sch→sh, dsch/tsch→dj/tj), the transliteration glyphs (ꜣ ꜥ→a, ḥ→h, ḫ ẖ→kh, š→sh, ṯ→tj,
   ḏ→dj, ḳ→q, ꞽ→i), diacritics stripped, and every other non-alphanumeric dropped — so
   apostrophes, parentheses and the half-rings Porter & Moss write for ꜥ and ꜣ do not count,
   and ꜣ and ꜥ themselves, folded to "a", go with the vowels in rule 4. Digits go (D&H's
   placeholder ids "–18P" carry no name). Separators are editorial: Leprohon hyphenates
   adjective-noun phrases as his own convention (Leprohon 2013, printed p. 1 = PDF p. 22,
   not committed); the one name mryt-ꞽmn is "Meryetamun" in D&H, "Merytamun" in PM I.2, 765
   (row QV68, occupant_name) and "Meryet-Amun" in PM I.1, 421 (row TT358,
   occupant_alt_names) — two different queens of that name (`porter-moss-theban-necropolis`);
   D&H "Ahmes-Nefertiry" (dh_id Ahmes-Nefertiry, pp. 118–119) is PM I.2, 599
   "ʿAhmosi Nefertere" (row DAN-AhmosiNefertere, occupant_name).
   **Digraphs are units.** Within a folded token, kh, sh, dj and tj (from ḫ ẖ š ḏ ṯ, or
   written so in English or German) are one consonant each, decided on the folded letters
   before the weak signs go, and written ḫ š ḏ ṯ in the key. So letters that only become
   adjacent once a vowel is dropped never read as one: Menkauhor (mn-kꜣw-ḥr) is mnkhr, k + h,
   not the ḫ of Menkheperre (mnḫprr); PM's "Raʿdjedef" keeps its ḏ (rḏdf), "Wadjkheperreʿ"
   is "Wadjkheperre" (ḏḫprr). The unit is decided within a token, so a separator between
   s and h, or t and j, is kept information: D&H's "Ahmes-Henutemipet" is s + h, which
   written solid would read š.
2. **c and q stay themselves.** An earlier version wrote c and q as k; it was measured and
   dropped (see "Measured and not adopted" below), so Cleopatra and Kleopatra, Berenice and
   Berenike are different keys and must meet through the authority's alternative names.
3. **The feminine ending -t.** One final "t" of the folded string (the last token's) is
   dropped. Egyptian feminine nouns and names end in -t (Gardiner), which modern renderings
   keep or drop: PM I.2, 751 writes "Tanezem(t)" (row QV33, occupant_name); Leprohon's
   note on Ahmose's Horus name says "the Tetisheri pyramid" (leprohon-18.01,
   horus_names[1].source_note, printed p. 95) where D&H write "Tetisherit" (dh_id
   Tetisherit, pp. 118–119). Applied to the folded string before rule 4, so a "t" exposed
   only by dropping a final weak sign ("Henttawy" → hntt) is kept.
4. **Vowels and weak signs are dropped: a e i o u (ꜣ and ꜥ among them), y, w, and j outside
   a dj/tj unit.**
   * Vowels are the renderer's: Leprohon gives Gardiner's consonantal transliteration with
     an "anglicized version" that inserts them (Leprohon 2013, printed p. 1 = PDF p. 22,
     not committed; committed row leprohon-21.05 birth_names[0]: `imn m ipt` =
     "imen em ipet", printed p. 140), and says the same imn is "Amun" alone but "Amen-" in
     Amenhotep (printed p. 5 = PDF p. 26, not committed). One name, iꜥḥ-ms(w), is
     "iah mes(u)" in Leprohon (leprohon-18.01 birth_names[0], p. 95), "Iah mesu" with display
     "Ahmose I" in pharaoh.se (row Ahmose-I, birth_names[0].name), "Ahmes" in D&H (dh_id
     Ahmes B, pp. 126–130) and "ʿAhmosi" in PM I.2, 599; D&H's "Nefertiry" is PM I.2, 762
     "Nefertari" (row QV66, occupant_name), a vowel apart.
   * ꞽ (reed leaf) and y (double reed leaf) are rendered i or y interchangeably: pharaoh.se
     renders ḫꜣstꞽ as "Khasty" (row Den, throne_names[0]) and nṯrꞽ-ẖt as "Netjery khet" (row
     Djoser, horus_names[0]), but mny as "Meni" (row Narmer, throne_names[3]) and tty as
     "Teti" (row Teti, birth_names[1]); Leprohon renders ḏḥwty as "djehuty" (leprohon-16.02
     nebty_names[0], p. 83). The German Umschrift writes the sign j (Beckerath 1999, PDF pp.
     42 "mrj-Jmn", "Rꜥ-msj-sw", and 100 "Jmn-m-ḥꜣt", "Jmny"; not committed): a j outside a
     dj/tj unit is the weak sign; inside one it is the unit's (rule 1). **In an Egyptological
     transliteration every j is the weak sign**: a text with a sign only transliterations use
     (ꜣ, ꜥ, ꞽ, = or ⸗, or the inverted breve of i̯) writes ṯ and ḏ as letters of their own, so
     its t + j is t and the weak sign. TLA 600234 `Jt=j-Jmn` is "Itiamun", 600269
     `Mn-pḥ.tj-Rꜥw` "Menpehtyre", 600456 `Jni̯-jtj=f` "Intef" (`tla-2018-names`). Porter &
     Moss's half-ring ʿ does not trigger it: "Wadjkheperreʿ" keeps its ḏ. Adopted by the
     hill-climb, protocol v2 (`docs/evaluations/weak-sign-key-hillclimb/`, C1).
   * w (quail chick) is rendered w or u, or omitted: pharaoh.se renders smsw as "Semsu" (row
     Semerkhet, throne_names[1]), ḳbḥw as "Qebehu" (row Qaa, throne_names[2]: the row's
     transliteration field writes "ḳbhw", its gardiner field "q-b-H-w-W15" has the ḥ) and
     t-ꞽ-w as "Tiu" (row Tiu, birth_names[0]); Leprohon renders nṯrw as "netjeru"
     (leprohon-17.23 golden_horus_names[0], p. 90) and ms(w) as "mes(u)"; D&H write
     "Nebettawy A" (dh_id Nebettawy A, pp. 157–162) where PM I.2, 761 writes "Nebttaui" (row
     QV60, occupant_name), and "Ahmes" where pharaoh.se writes "Iah mesu".
   * The signs themselves (reed leaf, double reed leaf, quail chick; the semi-vowels):
     Gardiner, not on disk.
5. **Minimum length, in consonants.** A consonant is one unit of rule 1 (ḫ š ḏ ṯ one each;
   th is t + h, as in Hathor, ḥwt-ḥr), so `consonant_count` is the key's length. A residue
   of fewer than `MIN_WEAK_SIGN_CONSONANTS` (3) consonants is no key: the function returns
   "". The threshold rests on the collision analysis over the 352 D&H women (pinned in
   `tests/test_weak_sign_skeleton.py`): at three consonants the key reaches Ahmes (hms),
   Inhapy (nhp), Sitre (str) and Mutemwia (mtm), but also merges names that differ in a weak
   sign or the -t only (Neferu nfrw / Neferet nfrt; Nebetia / Nebtit / Nebtu), so the
   resolver accepts a three-consonant match only when the record names one of the woman's
   family kings, never on its dynasty alone. Names of two consonants or fewer (Tiye, Tey,
   Ti, Tuy, Tyti, Tia, Tiaa, Kiya, Iset, Huy, Iy, Imi, Iah, Aat, Ita, Tem …) are not
   reachable by this key at all; the resolver's tests list them.

Measured and not adopted (hill-climb protocol v2, `docs/evaluations/weak-sign-key-hillclimb/`)
--------------------------------------------------------------------------------------------
* z as s (TLA 400051 and 400058 `Z-n-wsr.t` "Senwosret") and ṯ as t (TLA 400020
  `Mnṯ.w-ḥtp.w` "Mentuhotep") are attested rendering conventions. Measured against the TLA
  names, each raised recall but merged more distinct names (strict strong merges 252 → 293 for
  z/s, 252 → 270 for ṯ/t), so neither is adopted. In English museum text z more often writes
  ḏ: PM I.1, 69 "Zeserkaraʿsonb" (row TT38) is ḏsr-kꜣ-rꜥ-snb, and PM I.2, 751 "Tanezem(t)" is
  tꜣ-nḏmt. z as ḏ outside a transliteration is a candidate for a later protocol, untested here.
* c and q as k, the key's former rule 2, dropped on 2026-10-15 by the project owner's
  decision, following the measurement. The convention is attested:
  - pharaoh.se row Cleopatra-VII has display "Cleopatra VII", alt_labels "Kleopatra", and
    renders her Egyptian nomen "Qliu pa dra netjeret meret ites" (q for the κ of Κλεοπάτρα);
  - Leprohon writes "Berenike" (leprohon-33.03a, display_name "Berenike II");
  - D&H write the goddess ꜥnqt "Anuket-" in Anuketemheb (dh_id Anuketemheb, pp. 178–180) but
    "Anuq-" in Anuqneferetweben and Dedetanuq (pp. 98–103).
  
  But as a letter rule it merged 18 more names in the TLA set (strict strong merges 234 →
  252) for half a point of recall. Measured as an addition to the key without it, it fails
  the protocol's acceptance rule as z/s and ṯ/t do. (Run as the removal C4, the protocol could
  not have accepted it, since removing a fold never raises recall; the code review of the
  climb pointed this out.) The Ptolemaic queens' Greek and Latin spellings belong in cited
  alternative names instead.

Not adopted
-----------
* Greek and Coptic forms (Amenophis for Amenhotep, Nitocris for Neith-Iqeret, Isis for
  Iset): no letter rule produces them; they are alternative names, which belong in the
  authority's alt-name lists.
* th/t (PM "Bentʿanta", D&H "Bintanath") and gemination: not weak-sign conventions and not
  attested as rendering variance in the committed sources; left to the exact and
  claim-graph tiers.
* Element tables (Re/Ra, Amun/Amen): unnecessary here, since the vowels go anyway.
"""

from __future__ import annotations

import re
import unicodedata

from .claimgraph.normalize import translit_key

MIN_WEAK_SIGN_CONSONANTS = 3

_SEPARATORS = re.compile(r"[\s.\-·]+")
_DIGITS = re.compile(r"[0-9]")
# Rule 4: the vowels and the weak signs y, w and j (a j inside dj or tj is part of that unit).
_WEAK_UNITS = frozenset("aeiouywj")
_DIGRAPHS = {"kh": "ḫ", "sh": "š", "dj": "ḏ", "tj": "ṯ"}


def _units(token: str) -> list[str]:
    """A folded token as consonant units: kh, sh, dj and tj, where the fold wrote them as
    adjacent letters (ḫ ẖ, š, ḏ, ṯ, or English kh, sh, dj, tj), are one unit each, written
    ḫ, š, ḏ, ṯ; every other letter is its own unit."""
    units, i = [], 0
    while i < len(token):
        pair = token[i:i + 2]
        if pair in _DIGRAPHS:
            units.append(_DIGRAPHS[pair])
            i += 2
        else:
            units.append(token[i])
            i += 1
    return units


def consonant_count(key: str) -> int:
    """The consonant units of a key: each letter, ḫ š ḏ ṯ included, is one."""
    return len(key)


def weak_sign_skeleton(text: str) -> str:
    """The weak-sign skeleton of a name, or "" when it has fewer consonants than the minimum."""
    # NFC after lowercasing: a capital H̱ has no precomposed form, so it reaches the fold as
    # h + U+0331 and would read as h; lowercased and composed it is ẖ (U+1E96), which folds to kh.
    text = unicodedata.normalize("NFC", text.lower())
    # C1: in an Egyptological transliteration (a sign only transliterations use: ꜣ ꜥ ꞽ = ⸗ or
    # the inverted breve of i̯) ṯ and ḏ are letters of their own, so a j is the weak sign.
    if re.search("[ꜣꜥꞽ=⸗\u032f]", text):
        text = text.replace("j", "i")
    tokens = [translit_key(t) for t in _SEPARATORS.split(text.replace("[", "").replace("]", "")) if t]
    tokens = [_DIGITS.sub("", t) for t in tokens]
    tokens = [t for t in tokens if t]
    if tokens and tokens[-1].endswith("t"):
        tokens[-1] = tokens[-1][:-1]
    # Digraphs are units before the weak signs go, so letters that only become adjacent once a
    # vowel is dropped never read as one: Menkauhor's k-a-u-h is k + h, not the ḫ of Menkheperre.
    residue = "".join(u for t in tokens for u in _units(t) if u not in _WEAK_UNITS)
    return residue if consonant_count(residue) >= MIN_WEAK_SIGN_CONSONANTS else ""
