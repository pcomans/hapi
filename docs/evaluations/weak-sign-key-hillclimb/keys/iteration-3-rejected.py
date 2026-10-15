"""Weak-sign skeleton: a consonantal key for Egyptian royal women's names across modern
spelling conventions.

Egyptian script writes consonants only; a modern rendering adds vowels by convention and
renders the three weak consonants (semi-vowels) ꞽ, y and w either as vowels, as y/w, or not
at all. Two renderings of one name therefore differ in exactly those letters, and in the
feminine ending -t, which some renderings keep and others drop. This key deletes what the
conventions disagree on and keeps the rest, so that the D&H label and another convention's
rendering of the same name meet on one string. It is lossy and recall-oriented: it is the
third and last tier of the royal-women resolver (`royal_women.py`), used only when the exact
and the claim-graph keys find nothing, never against the kings, and only with the record's
confirmation. The key itself knows nothing of D&H: it strips no disambiguating letter or
numeral (the resolver does that on the authority side, and matches a numeral the mention
carries).

Sources
-------
Committed rows are cited as source / row / field = value (page); each such citation is
checked row by row in `tests/test_weak_sign_skeleton.py`. Two books are cited that are on
disk but NOT committed (the `proprietary/books/` folder beside the checkout, PDF page
numbers): Leprohon
2013, *The Great Name* (its introduction; the committed Leprohon source holds the catalogue
rows only) and Beckerath 1999, *Handbuch der ägyptischen Königsnamen* (the committed
Beckerath source is the 1997 *Chronologie*). Gardiner, *Egyptian Grammar* (3rd ed. 1957) is
the standard reference for the alphabet and the feminine ending; it is not on disk, and no
section numbers are given.

Rules, in the order applied
---------------------------
1. **Tokens and the committed cross-convention fold.** Square brackets go (the letters a
   transcriber restores in them stay: "[Mut]metennefer" is Mutmetennefer, as the resolver's
   `labels_for` reads it). The text is split on spaces, hyphens and dots, and each token is
   folded by `claimgraph.normalize.translit_key` (unchanged): Beckerath's German digraphs
   (ch→kh, sch→sh, dsch/tsch→dj/tj), the transliteration glyphs (ꜣ ꜥ→a, ḥ→h, ḫ ẖ→kh, š→sh,
   ṯ→tj, ḏ→dj, ḳ→q, ꞽ→i), diacritics stripped, and every other non-alphanumeric dropped — so
   apostrophes, parentheses and the half-rings Porter & Moss write for ꜥ and ꜣ do not count,
   and ꜣ and ꜥ themselves, folded to "a", go with the vowels in rule 4. Digits go (D&H's
   placeholder ids "–18P" carry no name). Separators are editorial: Leprohon hyphenates
   adjective-noun phrases as his own convention (Leprohon 2013, printed p. 1 = PDF p. 22,
   not committed); the one name mryt-ꞽmn is "Meryetamun" in D&H, "Merytamun" in PM I.2, 765
   (row QV68, occupant_name) and "Meryet-Amun" in PM I.1, 421 (row TT358,
   occupant_alt_names) — two different queens of that name (`porter-moss-theban-necropolis`);
   D&H "Ahmes-Nefertiry" (dh_id Ahmes-Nefertiry, pp. 118–119) is PM I.2, 599
   "ʿAhmosi Nefertere" (row DAN-AhmosiNefertere, occupant_name).
2. **c and q are k.** Latin c and Greek κ: pharaoh.se row Cleopatra-VII has display
   "Cleopatra VII" with alt_labels "Kleopatra", and renders her Egyptian nomen
   "Qliu pa dra netjeret meret ites" (q for the κ of Κλεοπάτρα); Leprohon writes "Berenike"
   (leprohon-33.03a,
   display_name "Berenike II"). The goddess ꜥnqt is "Anuket-" in D&H's Anuketemheb (dh_id
   Anuketemheb, pp. 178–180) but "Anuq-" in Anuqneferetweben and Dedetanuq (pp. 98–103):
   D&H's own rendering of one element varies between k and q. Applied after the fold, so
   the German ch (→ kh) is not touched.
3. **The feminine ending -t.** One final "t" of the folded string (the last token's) is
   dropped. Egyptian feminine nouns and names end in -t (Gardiner), which modern renderings
   keep or drop: PM I.2, 751 writes "Tanezem(t)" (row QV33, occupant_name); Leprohon's
   note on Ahmose's Horus name says "the Tetisheri pyramid" (leprohon-18.01,
   horus_names[1].source_note, printed p. 95) where D&H write "Tetisherit" (dh_id
   Tetisherit, pp. 118–119). Applied to the folded string before rule 4, so a "t" exposed
   only by dropping a final weak sign ("Henttawy" → hntt) is kept.
4. **Vowels and weak signs are dropped: a e i o u, y, w, and j when not in dj/tj.**
   * Vowels are the renderer's: Leprohon gives Gardiner's consonantal transliteration with
     an "anglicized version" that inserts them (Leprohon 2013, printed p. 1 = PDF p. 22,
     not committed; committed row leprohon-21.05 birth_names[0]: `imn m ipt` =
     "imen em ipet", printed p. 140), and says the same imn is "Amun" alone but "Amen-" in
     Amenhotep (printed p. 5 = PDF p. 26, not committed). One name, iꜥḥ-ms(w), is
     "iah mes(u)" in Leprohon (leprohon-18.01 birth_names[0], p. 95), "Iah mesu" with display
     "Ahmose I" in pharaoh.se (row Ahmose-I, birth_names[0].name), "Ahmes" in D&H (dh_id
     Ahmes B, pp. 126–130) and "ʿAhmosi" in PM I.2, 599.
   * ꞽ (reed leaf) and y (double reed leaf) are rendered i or y interchangeably: pharaoh.se
     renders ḫꜣstꞽ as "Khasty" (row Den, throne_names[0]) and nṯrꞽ-ẖt as "Netjery khet" (row
     Djoser, horus_names[0]), but mny as "Meni" (row Narmer, throne_names[3]) and tty as
     "Teti" (row Teti, birth_names[1]); Leprohon renders ḏḥwty as "djehuty" (leprohon-16.02
     nebty_names[0], p. 83); D&H's "Nefertiry" is PM I.2, 762 "Nefertari" (row QV66,
     occupant_name). The German Umschrift writes the sign j (Beckerath 1999, PDF pp.
     42 "mrj-Jmn", "Rꜥ-msj-sw", and 100 "Jmn-m-ḥꜣt", "Jmny"; not committed). After rule 1,
     j also stands in the digraphs dj/tj for ḏ/ṯ, which stay apart from d/t; the digraph is
     decided within a token, so the j that opens "Jmn" in "Sꜣt-Jmn" is the weak sign.
   * w (quail chick) is rendered w or u, or omitted: pharaoh.se renders smsw as "Semsu" (row
     Semerkhet, throne_names[1]), ḳbhw as "Qebehu" (row Qaa, throne_names[2]) and t-ꞽ-w as
     "Tiu" (row Tiu, birth_names[0]); Leprohon renders nṯrw as "netjeru" (leprohon-17.23
     golden_horus_names[0], p. 90) and ms(w) as "mes(u)"; D&H write "Nebettawy A" (dh_id
     Nebettawy A, pp. 157–162) where PM I.2, 761 writes "Nebttaui" (row QV60, occupant_name),
     and "Ahmes" where pharaoh.se writes "Iah mesu".
   * The signs themselves (reed leaf, double reed leaf, quail chick; the semi-vowels):
     Gardiner, not on disk.
5. **Minimum length, in consonants.** kh, sh, dj and tj each count as one consonant (ḫ/ẖ,
   š, ḏ, ṯ); every other letter as one (th is t + h, as in Hathor, ḥwt-ḥr). A residue of
   fewer than `MIN_WEAK_SIGN_CONSONANTS` (3) consonants is no key: the function returns "".
   The threshold rests on the collision analysis over the 352 D&H women (pinned in
   `tests/test_weak_sign_skeleton.py`): at three consonants the key reaches Ahmes (hms),
   Inhapy (nhp), Sitre (str) and Mutemwia (mtm), but also merges names that differ in a weak
   sign or the -t only (Neferu nfrw / Neferet nfrt; Nebetia / Nebtit / Nebtu), so the
   resolver accepts a three-consonant match only when the record names one of the woman's
   family kings, never on its dynasty alone. Names of two consonants or fewer (Tiye, Tey,
   Ti, Tuy, Tyti, Tia, Tiaa, Kiya, Iset, Huy, Iy, Imi, Iah, Aat, Ita, Tem …) are not
   reachable by this key at all; the resolver's tests list them.

Not adopted
-----------
* Greek and Coptic forms (Amenophis for Amenhotep, Nitocris for Neith-Iqeret, Isis for
  Iset): no letter rule produces them; they are alternative names, which belong in the
  authority's alt-name lists.
* th/t (PM "Bentʿanta", D&H "Bintanath"), s/z, and gemination: not weak-sign conventions
  and not attested as rendering variance in the committed sources; left to the exact and
  claim-graph tiers.
* Element tables (Re/Ra, Amun/Amen): unnecessary here, since the vowels go anyway.
"""

from __future__ import annotations

import re
import unicodedata

from .claimgraph.normalize import translit_key

MIN_WEAK_SIGN_CONSONANTS = 3

_SEPARATORS = re.compile(r"[\s.\-·]+")
# The signs that occur only in an Egyptological transliteration (ꜣ ꜥ ḥ ḫ ẖ š ṯ ḏ ḳ ꞽ, the
# suffix and dual markers = ⸗, the half-ring ʿ, and the combining marks of i̯ and ẖ).
_TRANSLITERATION = re.compile("[ꜣꜥḥḫẖšṯḏḳꞽ=⸗ʿ\u0331\u032f\u0323\u032e]")
_DIGITS = re.compile(r"[0-9]")
# Rule 4: vowels, y, w, and a j that is not the second letter of dj/tj.
_WEAK_SIGNS = re.compile(r"[aeiouyw]|(?<![dt])j")
# Rule 5: one consonant each.
_CONSONANT = re.compile(r"kh|sh|dj|tj|[a-z]")


def consonant_count(key: str) -> int:
    """The consonants of a key, the digraphs kh, sh, dj and tj counting one each."""
    return len(_CONSONANT.findall(key))


def weak_sign_skeleton(text: str) -> str:
    """The weak-sign skeleton of a name, or "" when it has fewer consonants than the minimum."""
    # NFC after lowercasing: a capital H̱ has no precomposed form, so it reaches the fold as
    # h + U+0331 and would read as h; lowercased and composed it is ẖ (U+1E96), which folds to kh.
    text = unicodedata.normalize("NFC", text.lower())
    # In an Egyptological transliteration ṯ and ḏ are letters of their own, so a j there is
    # always the weak sign, never the second letter of tj/dj: "Jt=j-Jmn" is t + j, Itiamun.
    if _TRANSLITERATION.search(text):
        text = text.replace("j", "i")
    tokens = [translit_key(t) for t in _SEPARATORS.split(text.replace("[", "").replace("]", "")) if t]
    tokens = [_DIGITS.sub("", t).replace("c", "k").replace("q", "k").replace("z", "s") for t in tokens]
    tokens = [t for t in tokens if t]
    if tokens and tokens[-1].endswith("t"):
        tokens[-1] = tokens[-1][:-1]
    residue = "".join(_WEAK_SIGNS.sub("", t) for t in tokens)
    return residue if consonant_count(residue) >= MIN_WEAK_SIGN_CONSONANTS else ""
