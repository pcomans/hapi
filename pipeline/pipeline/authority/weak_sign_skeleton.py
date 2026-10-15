"""Weak-sign skeleton: a consonantal key for Egyptian royal women's names across modern
spelling conventions.

Egyptian script writes consonants only; a modern rendering adds vowels by convention and
renders the three weak consonants (semi-vowels) ꞽ, y and w either as vowels, as y/w, or not
at all. Two renderings of one name therefore differ in exactly those letters, and in the
feminine ending -t, which some renderings keep and others drop. This key deletes what the
conventions disagree on and keeps the rest, so that the D&H label and another convention's
rendering of the same name meet on one string. It is lossy and recall-oriented: it is the
third and last tier of the royal-women resolver, used only when the exact and the claim-graph
keys find nothing, and never against the kings.

Every rule is a documented convention. Sources on disk are cited by path; the one standard
reference that is not on disk (Gardiner) is marked as such.

Rules, in the order applied
---------------------------
0. **Disambiguators are not the name.** A lone capital letter or roman numeral token is
   dropped: D&H's own letters ("Tiye A", "Neferu Q") and regnal numerals ("Cleopatra VII")
   are modern conventions, not parts of the Egyptian name (Leprohon 2013, 19 = PDF p. 40:
   numerals are "a modern convention, one not used by the ancient Egyptians").
1. **The committed cross-convention fold** (`claimgraph.normalize.translit_key`, unchanged):
   Beckerath's German digraphs (ch→kh, sch→sh, dsch/tsch→dj/tj), the transliteration glyphs
   (ꜣ ꜥ→a, ḥ→h, ḫ ẖ→kh, š→sh, ṯ→tj, ḏ→dj, ḳ→q, ꞽ→i), diacritics stripped, brackets removed,
   and every non-alphanumeric dropped — so hyphens, spaces, apostrophes and the half-rings
   Porter & Moss use for ꜥ/ꜣ do not count. Hyphenation is editorial: Leprohon hyphenates
   adjective-noun phrases as his own convention (Leprohon 2013, 1 = PDF p. 22); the same
   queen is "Ahmes-Nefertiry" in D&H and "ʿAhmosi Nefertere" in PM I.2, 599; "Meryetamun"
   in D&H, "Merytamun" in PM I.2, 765 and "Meryet-Amun" in PM I.1, 421 (all in
   `sources/porter-moss-theban-necropolis/reconciled.jsonl`). Digits are then dropped
   (D&H's placeholder ids "–18P" carry no name).
2. **The feminine ending -t.** One final "t" of the rendering is dropped. Egyptian feminine
   nouns and names end in -t (Gardiner, *Egyptian Grammar*, 3rd ed. 1957, §26 — not on
   disk), which modern renderings keep or drop: PM writes "Tanezem(t)" (PM I.2, 751);
   Leprohon's note on Ahmose I names the Donation Stela "from the Tetisheri pyramid"
   (leprohon-18.01, printed p. 95, `sources/leprohon-2013-titulary/reconciled.jsonl`) where
   D&H writes "Tetisherit" (pp. 118–119). Applied to the surface, before rule 3, so that a
   "t" exposed only by dropping a final weak sign ("Henttawy" → hntt) is kept.
3. **Vowels and weak signs are dropped: a e i o u, y, w, and j when not part of dj/tj.**
   * Vowels are the renderer's: Leprohon offers Gardiner's consonantal transliteration
     with an "anglicized version" that inserts them (`wꜣḥ-ꜥnḫ` → "wah ankh", Leprohon
     2013, 1 = PDF p. 22; `imn m ipt` → "imen em ipet", leprohon-21.05, p. 140), and notes
     that the same `imn` is "Amun" alone but "Amen-" in Amenhotep (ibid., 5 = PDF p. 26).
     One name, `iꜥḥ-ms(w)`, is "iah mes(u)" in Leprohon (18.01), "Iah mesu" / "Ahmose I" in
     pharaoh.se (`sources/pharaoh-se/reconciled.jsonl`, slug Ahmose-I), "Ahmes" in D&H and
     "ʿAhmosi" in PM I.2, 599.
   * ꞽ (reed leaf) and y (double reed leaf) are rendered i or y interchangeably: pharaoh.se
     renders `ḫꜣstꞽ` as "Khasty" (Den) and `nṯrꞽ-ẖt` as "Netjery khet" (Djoser), but `mny`
     as "Meni" (Narmer) and `tty` as "Teti"; Leprohon renders `ḏḥwty` as "djehuty"
     (16.02, p. 83). The German Umschrift writes the same sign j (Beckerath 1999,
     *Handbuch der ägyptischen Königsnamen*, PDF pp. 42 "mrj-Jmn", "Rꜥ-msj-sw" and 100
     "Jmn-m-ḥꜣt", "Jmny"). After rule 1, j also stands in the digraphs dj/tj for ḏ/ṯ, which
     are kept apart from d/t; only a j elsewhere is the weak sign.
   * w (quail chick) is rendered w or u, or omitted: pharaoh.se renders `smsw` as "Semsu",
     `ḳbhw` as "Qebehu", `t-ꞽ-w` as "Tiu" and `ḏḥwty ꜥꜣ(.w)` as "Tao"; Leprohon renders
     `nṯrw` as "netjeru" (17.23, p. 90) and `ms(w)` as "mes(u)"; D&H writes "Nebettawy A"
     where PM I.2, 761 writes "Nebttaui", and "Ahmes" where pharaoh.se writes "Iah mesu".
   * The signs themselves: Gardiner 1957 §§19–20 (the alphabet; ꞽ, y, w as semi-vowels /
     weak consonants) — not on disk; the section numbers are quoted from memory.
4. **Minimum length.** A residue shorter than `MIN_WEAK_SIGN_SKELETON_LEN` (4) is no key
   (the function returns ""), the threshold the claim graph's skeleton key already fixes
   (`normalize._MIN_SKELETON_LEN`). On the 352 D&H women a threshold of 3 would merge the
   distinct names Neferu (nfrw) and Neferet (nfrt) into one eleven-woman group "nfr", and
   would let the cue "Ahmose" reach the princesses Ahmes A/B; 4 keeps them apart. The cost is that names of three consonants (Inhapy nhp, Ahmes hms,
   Sitre str, Mutemwia mtm) and shorter (Tiye, Tey, Ti, Tuy, Kiya, Iset: t, t, t, t, k, s)
   are not reachable by this key at all.

Not adopted
-----------
* Greek and Coptic forms (Amenophis for Amenhotep, Nitocris for Neith-Iqeret, Isis for
  Iset): no letter rule produces them; they are alternative names, which belong in the
  authority's alt-name lists.
* th/t (PM "Bentʿanta", D&H "Bintanath"), s/z, k/q/c, and gemination: not weak-sign
  conventions; left to the exact and claim-graph tiers.
* Element tables (Re/Ra, Amun/Amen): unnecessary here, since the vowels go anyway.
"""

from __future__ import annotations

import re

from .claimgraph.normalize import translit_key

MIN_WEAK_SIGN_SKELETON_LEN = 4

# A D&H letter or a regnal numeral standing alone as a token.
DISAMBIGUATOR = re.compile(r"^(?:[A-Z]|[IVX]+)$")
_DIGITS = re.compile(r"[0-9]")
# Rule 3: vowels, y, w, and a j that is not the second letter of dj/tj.
_WEAK_SIGNS = re.compile(r"[aeiouyw]|(?<![dt])j")


def weak_sign_skeleton(text: str) -> str:
    """The weak-sign skeleton of a name, or "" when it is shorter than the minimum."""
    tokens = [t for t in text.split() if not DISAMBIGUATOR.match(t)]
    folded = _DIGITS.sub("", translit_key(" ".join(tokens)))
    if folded.endswith("t"):
        folded = folded[:-1]
    residue = _WEAK_SIGNS.sub("", folded)
    return residue if len(residue) >= MIN_WEAK_SIGN_SKELETON_LEN else ""
