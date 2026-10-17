"""Royal women as an authority for museum ruler mentions (Dodson & Hilton 2004).

Museum records name queens the way they name kings ("Relief of Queen Neferu", "Queen
Tiye"), but the king lists (the claim graph) hold almost no queens, so such a mention could
not resolve. This module resolves them against the royal women of Dodson & Hilton, *The
Complete Royal Families of Ancient Egypt* (`sources/dodson-hilton-queens/reconciled.jsonl`,
page-cited, reconciled), approved as an authority on 2026-10-14, and against the women the
king lists hold as rulers (`female-rulers.json`).

The rule, which is deterministic and fixed here:

* A name after a royal-woman cue (Queen, Queen Mother, King's (Great) Wife, Great Royal Wife,
  King's Mother, King's Daughter, Princess, God's Wife (of Amun), Divine Adoratrice (of Amun))
  resolves among the royal women and the female rulers, never among the other kings, so a
  queen is never merged with a king of her name. A cued name none of them bears stays
  unmatched. Every other ruler mention resolves among the kings, as before.
* A D&H woman who later reigned (Hatshepsut D, Sobkneferu, Tawosret) is the king: a mention
  that lands on her resolves to the king.
* A mention is read before any tier (`read_mention`), and what cannot be read is refused, not
  guessed. Every token must be a regnal numeral, bare or in one matching bracket pair, or a
  name token (letters of any script, ʿ ʾ ', - . · = ⸗, a restoration in brackets inside the word;
  read as letters). At most one numeral is allowed. A whole-word parenthesis with a space
  inside is a description and is dropped, unless it doubts or holds a numeral, which is
  refused: whose numeral it is cannot be told ("Tiye (wife of Amenhotep III)" is refused too).
  A lowercase numeral run on to a name ("Ahhotpii") reads as the name's own vowels: it cannot
  be told from a name ending in -i, a known limit. Refusals are `unreadable_numeral` (a
  lowercase, broken, run-on, all-caps-final or second numeral; any numeric character,
  superscripts included), `doubted_mention` (a "?") and `unreadable_mention` (any other mark).
* A woman's alternative name that is itself a king's name is not one of her names: such an
  identity (Meryetaten as the king Neferneferuaten) is disputed, and the king lists decide it.
* D&H tells same-named women apart by a letter or numeral ("Tiye A", "Neferu II"); museum
  records name them without it. When a bare name fits several women, the record's own
  context chooses, and only if exactly one woman remains:
    1. family: the women whose husband, father, mother or child, as D&H names them without
       any parenthetical hedge, is a king the same record names and the king authority
       resolves. A king the mention's own field names as her kin counts as named by the
       record (`stated_kin_names`, #369): "Queen Ahmose, Mother of Hatshepsut", "Hatshepsut's
       Mother, Queen Ahmose", "Queen Inhapi, wife of Tao II, daughter of Tao I". Only the
       appositive forms are read, the kin word being mother, wife, daughter, sister, widow or
       consort; which kin D&H gives is not compared, as for any other king the record names.
       A stated name counts only if the king authority resolves it: the claim graph has no
       "Tao I", "Tao II" or "Taa II" (Ryholt's lone "Tao" is Seqenenre), so Inhapi's stated
       kin, like D&H's own "Taa II" family links, add nothing yet. Only
       `resolve_ruler_mention` reads them; `resolve_royal_woman` takes the record's kings as
       given;
    2. dynasty: among the family matches if there are several, else among all, the women of
       the record's dynasty (or of no known dynasty), when the record gives exactly one.
  Otherwise the mention stays ambiguous, among the women the family and dynasty leave (#369);
  when the record's dynasty leaves none and it names no family king, it is unmatched
  (`record_dynasty_contradicts`), as a lone candidate of another dynasty is.
* A name is looked up in three tiers, each tried only when the one before finds no
  candidate: the exact surface (`raw_exact`), the claim graph's transliteration and phonetic
  keys (`committed_normalized`), and the weak-sign skeleton (`weak_sign_skeleton`, see
  `weak_sign_skeleton.py`), which drops the vowels, the weak signs ꞽ/y/w and the feminine
  -t that modern renderings disagree on. The third tier runs only against this index (the
  royal women, by their D&H names, and the female rulers, by their `female-rulers.json`
  king_name only — never by the king lists' whole titulary), never against the kings, and
  only when the residue has at least `MIN_WEAK_SIGN_CONSONANTS` consonants. On the authority
  side the D&H letter and the regnal numeral are stripped before keying ("Neferu II" is
  keyed as Neferu, with its numeral remembered); a numeral the mention carries must be one
  of the candidate's ("Cleopatra III" reaches no Cleopatra I, II or VII; a bare "Cleopatra"
  reaches them all). The family and dynasty narrowing above applies to its candidates
  unchanged. Any D&H label meets the first tier, so the third never changes a name that
  the first two resolve.
* A weak-sign match must be confirmed by the record. A shared consonant skeleton is weak
  evidence, and a queen has no throne name or reign that could corroborate it, as a king's
  match in the claim graph is corroborated. So the woman it chooses counts only if the
  record names one of her family kings, or the record's single dynasty is one of hers or
  of her family kings'. The family kings' dynasties only ever add: for a woman with a
  dynasty of her own they can confirm one of hers' neighbours (Ahmes-Nefertiry has none of
  her own, so Taa II's 17 and Ahmose I's 18 are what confirms her); they never rule a
  dynasty out, which only her own dynasty does (the bullet below). Otherwise the mention
  stays unmatched (`weak_sign_unconfirmed`), even as the only candidate. A woman with
  neither (Tetisherit, whose entry names only her non-royal father) is not reachable on
  this tier. A key of exactly `MIN_WEAK_SIGN_CONSONANTS` consonants takes a named family
  king only, never a dynasty: three consonants merge names that differ in a weak sign
  alone. A key that the authority's own spellings reach in more than one form for different
  women (`different_spellings`: D&H's Henttawy / Henutwati, Neferu / Neferet, Nebetia /
  Nebtit / Nebtu, Tentamun / Tintamun, and `female-rulers.json`'s "Neferusobek" for the king
  Sobkneferu beside D&H's princess Neferusobk) never resolves at all; one woman's own
  alternative spellings (Tawosret / Tausret) are one name. The mention is ambiguous
  (`weak_sign_different_spellings`) before any narrowing, because the key cannot tell whether
  those spellings are one name, and a family king would then pick whichever woman is linked
  to him, whatever her name ("Nofret" on a record naming Amenemhat I would have reached
  Neferu III). The rule rests on the authority's own spellings, not on anyone's reading of
  the names; it replaced a hand-written list whose readings had no source on disk (Codex
  review). Known limitation: the record's dynasty is the object's,
  not her lifetime's, so a Ramesside stela of the deified Ahmes-Nefertiry (Dynasty 19–20)
  is not confirmed by its dynasty; only a named family king would do.
* A woman is never chosen against the record's own single dynasty: D&H is transcribed for
  some dynasties only (none of 4–10, 14 or 22 onward), so a lone name match of another known
  dynasty is another woman, and the mention stays unmatched. A candidate whose dynasty the
  authority does not give is not contradicted: the rows of D&H's two-dynasty sections (16 and
  17; 17 and 18) carry a dynasty only when the entry's own kin kings fall in one of them.
  A record that names one of her family kings overrides its dynasty: a monument of Shoshenq
  I (Dynasty 22) naming his mother Tentsepeh A (D&H, Dynasty 21) is hers.
* The cues are the module's rule; no committed mention extractor emits all of them yet (the
  frozen #337 one knows only Queen/King/reign cues). The first caller is the ruler
  re-registration (#361), whose extractor is to emit them.
* D&H keys a row by (dh_id, sub_period). Every female dh_id under more than one sub_period
  is classified in `same-woman-across-sub-periods.json` as one woman or several; an
  unclassified one raises.
"""

from __future__ import annotations

import collections
import json
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from . import king_context
from .claimgraph.normalize import NameForm, keys_for_form
from .resolver import surface_key
from .weak_sign_skeleton import MIN_WEAK_SIGN_CONSONANTS, consonant_count, weak_sign_skeleton

SOURCE_DIR = Path(__file__).resolve().parent / "sources" / "dodson-hilton-queens"
DODSON_HILTON = SOURCE_DIR / "reconciled.jsonl"
SAME_WOMAN = SOURCE_DIR / "same-woman-across-sub-periods.json"
FEMALE_RULERS = SOURCE_DIR / "female-rulers.json"
TARGET_PREFIX = "dodson_hilton:"

APOSTROPHE = "['’]"
ROYAL_WOMAN_CUE_BEFORE = re.compile(
    r"\b(?:queen(?:\s+mother)?|princess|great\s+royal\s+wife"
    rf"|king{APOSTROPHE}s\s+(?:great\s+wife|wife|mother|daughter)"
    rf"|god{APOSTROPHE}s\s+wife(?:\s+of\s+amun)?|divine\s+adoratrice(?:\s+of\s+amun)?)"
    # the separators the mention extractors skip between a cue and the name
    r"[\s:,\-]*$",
    re.I,
)
PARENTHETICAL = re.compile(r"\(")
LACUNA = re.compile(r"\[\s*(?:\.\.\.|…)\s*\]")
LEADING_QUEEN = re.compile(r"^\s*\(?queen\)?\s+", re.I)
# A D&H letter or a regnal numeral standing alone as a token.
DISAMBIGUATOR = re.compile(r"^(?:[A-Z]|[IVX]+)$")
NUMERAL = re.compile(r"^[IVX]+$")
# A D&H letter on a kinship name marks one of D&H's own individuals, not a king-list name;
# I, V and X are left out because they are also regnal numerals.
DH_LETTER = re.compile(r"^[A-HJ-UWYZ]$")
# A king her field names as her kin (`stated_kin_names`).
KIN_WORD = r"(?:mother|wife|daughter|sister|widow|consort)"
KIN_AFTER = re.compile(rf"\s*,\s*(?:the\s+)?{KIN_WORD}\s+of\s+(?P<name>[^,;()\[\]]*[^\s,;()\[\]])\s*(?=[,;]|$)", re.I)
KIN_BEFORE = re.compile(rf"(?:^|[,;:]\s*)(?P<name>[^,;:()\[\]]*[^\s,;:()\[\]])['’]s\s+{KIN_WORD}\s*,\s*$", re.I)
# A phase of one dynasty, or a span of two phases of it ("early-mid", "mid to late"), as the
# museums write them (#369: read from every dynasty value in the 2026-08-27 corpus).
DYNASTY_PHASE = r"(?:early|late|middle|mid|end|beginning|(?:first|second)\s+(?:half|part))"
# A hyphen (ASCII or Unicode), an en dash or an em dash.
DASH = "[-‐‑–—]"
DYNASTY_PHASES = rf"{DYNASTY_PHASE}(?:\s*(?:{DASH}to{DASH}|{DASH}|\bto\b)\s*{DYNASTY_PHASE})?"
SINGLE_DYNASTY = re.compile(
    rf"^\s*(?:{DYNASTY_PHASES}(?:\s+of)?(?:\s+|{DASH}))?(?:Dynasty\s*(\d+)|(\d+)(?:st|nd|rd|th)?\s+Dynasty)"
    rf"\s*(?:,\s*{DYNASTY_PHASES})?\s*$",
    re.I,
)


class KingAuthority(Protocol):
    """The king lists (the claim graph), as the caller resolves them."""

    def resolve(self, name: str) -> dict:
        """{"status": "resolved"|"ambiguous"|"unmatched", "target_ids": [...], ...}"""

    def labels(self, target_id: str) -> list[str]:
        """Every name the king authority gives this king."""

    def dynasties(self, target_id: str) -> tuple[int, ...]:
        """The dynasties the king lists give this king."""

    def reign(self, target_id: str) -> tuple[int, int] | None:
        """The span of the reign dates the king lists give this king, or None."""

    def label(self, target_id: str) -> str:
        """The king's display label."""


@dataclass(frozen=True)
class RoyalWoman:
    target_id: str
    label: str
    labels: tuple[str, ...]
    alt_names: tuple[str, ...]
    dynasties: tuple[int, ...]
    family_names: tuple[str, ...]
    dh_rows: tuple[tuple[str, str], ...]
    source_citations: tuple[dict, ...]


@dataclass
class RoyalWomenIndex:
    women: dict[str, RoyalWoman]
    dynasties: dict[str, tuple[int, ...]]
    family_king_ids: dict[str, frozenset[str]]
    family_names_not_resolved: dict[str, tuple[str, ...]]
    king_ids: dict[str, str]
    alt_names_dropped_as_king_names: dict[str, tuple[str, ...]]
    exact: dict[str, set[str]] = field(default_factory=lambda: collections.defaultdict(set))
    normalized: dict[str, set[str]] = field(default_factory=lambda: collections.defaultdict(set))
    weak_sign: dict[str, set[str]] = field(default_factory=lambda: collections.defaultdict(set))
    # Per weak-sign key and target: the base spellings (`base_spelling`) of the labels keyed
    # under it, so that one woman's own alternative spellings never count as two names.
    weak_sign_spellings: dict[str, dict[str, set[str]]] = field(
        default_factory=lambda: collections.defaultdict(lambda: collections.defaultdict(set)))
    # Per weak-sign key and target: the regnal numerals of the labels keyed under it.
    weak_sign_numerals: dict[str, dict[str, set[str]]] = field(
        default_factory=lambda: collections.defaultdict(lambda: collections.defaultdict(set)))
    # The dynasties of the kings a target's family names resolve to: with her own, what
    # confirms a weak-sign match.
    family_dynasties: dict[str, frozenset[int]] = field(default_factory=dict)




def name_keys(text: str) -> set[str]:
    # The claim graph's phonetic/transliteration paths, never its lossy skeleton path, as the
    # king resolver uses for artifact-to-authority resolution.
    return {key for key in keys_for_form(NameForm(surface=text), skeleton=False) if key}


def labels_for(name: str) -> list[str]:
    """D&H's name, the name without its disambiguating letters/numerals, and the part before
    the first one: "Tiye B Mereniset" -> "Tiye B Mereniset", "Tiye Mereniset", "Tiye". A name
    with a lacuna ("Henut[...]") has no label; restored letters are kept ("[Mut]metennefer"
    -> "Mutmetennefer")."""
    if LACUNA.search(name):
        return []
    name = name.replace("[", "").replace("]", "")
    tokens = name.split()
    labels = [name]
    kept = [t for t in tokens if not DISAMBIGUATOR.match(t)]
    if kept and len(kept) < len(tokens):
        labels.append(" ".join(kept))
        first = next(i for i, t in enumerate(tokens) if DISAMBIGUATOR.match(t))
        if first:
            labels.append(" ".join(tokens[:first]))
    return list(dict.fromkeys(labels))


def usable_kinship_name(name: str | None) -> bool:
    """A kinship name usable as a family link: present, without a parenthetical hedge or
    remark, and not one of D&H's own lettered individuals."""
    return bool(name) and not PARENTHETICAL.search(name) and not any(DH_LETTER.match(t) for t in name.split())


def load_royal_women(path: Path = DODSON_HILTON, same_woman_path: Path = SAME_WOMAN) -> list[RoyalWoman]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    women_rows = [r for r in rows if r["sex"] == "female" and not r["is_group_entry"]]
    same_woman = {e["dh_id"]: e for e in json.loads(same_woman_path.read_text(encoding="utf-8"))["entries"]}
    sub_periods: dict[str, set[str]] = collections.defaultdict(set)
    for row in women_rows:
        sub_periods[row["dh_id"]].add(row["sub_period"])
    for dh_id, periods in sorted(sub_periods.items()):
        if len(periods) > 1:
            if dh_id not in same_woman:
                raise ValueError(f"Dodson & Hilton woman {dh_id} under {sorted(periods)} is not classified "
                                 f"in {same_woman_path.name}")
            if set(same_woman[dh_id]["sub_periods"]) != periods:
                raise ValueError(f"{same_woman_path.name} classifies {dh_id} under other sub-periods than the data")
    for dh_id in set(same_woman) - {d for d, p in sub_periods.items() if len(p) > 1}:
        raise ValueError(f"{same_woman_path.name} lists {dh_id}, which is not a repeated female dh_id")

    grouped: dict[str, list[dict]] = collections.defaultdict(list)
    for row in women_rows:
        one = row["dh_id"] in same_woman and same_woman[row["dh_id"]]["same_woman"]
        key = row["dh_id"] if one or len(sub_periods[row["dh_id"]]) == 1 else f"{row['dh_id']}|{row['sub_period']}"
        grouped[TARGET_PREFIX + key].append(row)
    women = []
    for target_id, entries in sorted(grouped.items()):
        labels: list[str] = []
        alt: list[str] = []
        family: list[str] = []
        for row in entries:
            labels += labels_for(row["name"])
            alt += [a for a in row["alt_names"] if not PARENTHETICAL.search(a)]
            family += [n for n in (*row["spouse_names"], row["father_name"], row["mother_name"],
                                   *row["children_names"]) if usable_kinship_name(n)]
        women.append(RoyalWoman(
            target_id=target_id,
            label=entries[0]["name"],
            labels=tuple(dict.fromkeys(labels)),
            alt_names=tuple(dict.fromkeys(alt)),
            dynasties=tuple(sorted({r["dynasty"] for r in entries if r["dynasty"] is not None})),
            family_names=tuple(dict.fromkeys(family)),
            dh_rows=tuple((r["dh_id"], r["sub_period"]) for r in entries),
            source_citations=tuple(r["source_citation"] for r in entries),
        ))
    return women


def _add(index: RoyalWomenIndex, target_id: str, labels: Iterable[str]) -> None:
    for label in labels:
        index.exact[surface_key(label)].add(target_id)
        for key in name_keys(label):
            index.normalized[key].add(target_id)


BRACKET_PAIRS = {"(": ")", "[": "]"}
# Space inside a bracket is closed up first ("[ II ]" -> "[II]", "( II" -> "(II").
BRACKET_SPACE = re.compile(r"([(\[])\s+|\s+([)\]])")
# A whole-word parenthesis with a space inside is a description, dropped unless it doubts or
# holds a numeral (`_description_refusal`).
DESCRIPTION = re.compile(r"(?<!\S)\([^()]*\s[^()]*\)(?!\S)")
# Only a matching pair wraps a numeral: "(II]", "(II" and "II)" are unread, not II, since a
# broken wrapper may hide a cut numeral ("(II" of "(III)"). An attached pair is split off
# unless a letter follows: "Mer[I]taten" restores a letter.
ATTACHED_NUMERAL = re.compile(r"(\w)(\([IVX]+\)|\[[IVX]+\])(?!\w)")
# A name token: letters (any script), combining marks, ʿ ʾ ' ’, the separators - . · = ⸗, and
# a restoration in brackets inside the word ("Mer[i]taten").
NAME_LETTERS = r"[^\W\d_]|[\u0300-\u036f'’]"
_RESTORED = rf"(?:{NAME_LETTERS}|[-.·=⸗])+"
NAME_TOKEN = re.compile(rf"(?:{NAME_LETTERS}|[-.·=⸗]|\[{_RESTORED}\]|\({_RESTORED}\))+[,;:]?")
SEGMENT = re.compile(r"[-.·=⸗]")
NUMERAL_LETTERS = set("IVXivx")


def _numeral_like(token: str) -> bool:
    """Whether a token holds something a numeral may be: a piece of it, between marks, made of
    numeral letters ("(II]", "[ii?", "Ahhotp-II"), or a capital numeral run on to a lowercase
    name ("CleopatreII)")."""
    return any(piece and set(piece) <= NUMERAL_LETTERS for piece in re.split(r"[\W_]+", token)) \
        or bool(re.search(r"[a-z][IVX]+(?![a-z])", token))


def _refusal(token: str) -> str | None:
    """Why a token that is no readable numeral cannot be read as part of a name, or None. A
    numeral it may hold is unread, never dropped: the keys would delete it and accept the bare
    name (Codex reviews of PR #365)."""
    numeral_like = _numeral_like(token)
    if "?" in token:
        return "unreadable_numeral" if numeral_like else "doubted_mention"
    if not NAME_TOKEN.fullmatch(token):
        return "unreadable_numeral" if numeral_like else "unreadable_mention"
    # A truncation or a lacuna is no name: "Henut...", "Henut[...]" would key as "henut".
    groups = re.findall(r"[\[(]([^\[\]()]*)[\])]", token)
    if ".." in token or "…" in token or any(not any(c.isalpha() for c in group) for group in groups):
        return "unreadable_mention"
    core = token.rstrip(".,;:")
    # A whole-word bracket is no restoration inside a word: "(perhaps)", "[A]", "(Kamose)".
    if re.fullmatch(r"[\[(][^\[\]()]*[\])]", core):
        return "unreadable_numeral" if numeral_like else "unreadable_mention"
    # A restoration that ends the word and holds only numeral letters cannot be told from a
    # lowercase numeral ("Nefertit[i]" as "Berenike[ii]").
    if (end := re.search(r"[\[(]([^\])]*)[\])]$", core)) and set(end[1]) <= NUMERAL_LETTERS:
        return "unreadable_numeral"
    whole = re.sub(r"[\[\]()]", "", core)
    if whole and set(whole) <= NUMERAL_LETTERS:  # "ii", "vi": a lowercase numeral or no name
        return "unreadable_numeral"
    for segment in SEGMENT.split(whole):
        if not segment:
            continue
        if set(segment) <= set("IVX") or (len(segment) > 1 and set(segment) <= NUMERAL_LETTERS):
            return "unreadable_numeral"  # "Ahhotp-II", "Ahhotp-ii"
        # A name ends in a lowercase letter, so a capital I, V or X ending a longer segment may be
        # a run-on numeral: "CleopatreII", "Ahhotp'II", "AhhotpʿII", and in all caps "AHHOTPII"
        # (and so "TETI", where nothing tells the name's own letters from a numeral).
        if len(segment) > 1 and segment[-1] in "IVX":
            return "unreadable_numeral"
    return None


def _description_refusal(description: str) -> str | None:
    """Why a whole-word parenthesis cannot be dropped as a description, or None. A numeral in
    it may be the mention's own ("Ahhotep (Aahotep II)", "(perhaps II)") or someone else's
    ("Tiye (wife of Amenhotep III)"), and nothing in the text tells which: it is refused, as a
    doubt is (code review of PR #365)."""
    # The token reader's own numeral test, so no numeral shape it refuses is dropped here.
    if any(numeral_of(word) or _numeral_like(word) or _refusal(word) == "unreadable_numeral"
           for word in description[1:-1].split()):
        return "unreadable_numeral"
    return "doubted_mention" if "?" in description else None


def read_mention(text: str) -> tuple[str, str | None]:
    """The mention with its readable numerals written bare, and why it cannot be read, or None.
    Every token must be a readable numeral (`numeral_of`) or a name token; at most one numeral;
    no numeric character (a digit, "Ⅱ"). Anything else is refused, not guessed: an allow-list,
    so a form nobody foresaw fails loudly (code review of PR #365)."""
    # Composed first: a decomposed final letter ("é" as e + U+0301) is no \w, and an attached
    # numeral after it would not be split off (Codex review).
    text = unicodedata.normalize("NFC", text)
    if any(c.isnumeric() for c in text):
        return text, "unreadable_numeral"
    if LACUNA.search(text):  # as the authority side refuses it (`labels_for`)
        return text, "unreadable_mention"
    text = BRACKET_SPACE.sub(lambda m: m[1] or m[2], text)
    for description in DESCRIPTION.findall(text):
        if refusal := _description_refusal(description):
            return text, refusal
    text = DESCRIPTION.sub(" ", text)
    text = ATTACHED_NUMERAL.sub(r"\1 \2", text)
    tokens, numerals = [], 0
    for token in text.split():
        if numeral := numeral_of(token):
            if not tokens:  # "II Berenike": a list marker or stray numeral, not hers (Codex review)
                return text, "unreadable_numeral"
            tokens.append(numeral)
            numerals += 1
        elif refusal := _refusal(token):
            return text, refusal
        else:
            tokens.append(token)
    if numerals > 1:  # "Neferu I II": the keys would run them together ("neferuiii")
        return text, "unreadable_numeral"
    # A restoration is read as letters, as the authority's labels are (`labels_for`): the
    # claim-graph keys delete bracketed text, so "Ahmes-[Nefertiry]" would key as "ahmes".
    return " ".join(t.replace("[", "").replace("]", "") for t in tokens), None


def numeral_of(token: str) -> str | None:
    """The regnal numeral a token writes, bare or wrapped ("II", "(II)", "[II]", "II."), or
    None. Uppercase only: a lowercase "ii" is no readable numeral (`read_mention` refuses it). A
    bracket must be one of a pair around the numeral: "(II]", "(II" and "II)" are None."""
    core = token.rstrip(".,;:")
    if core[:1] in BRACKET_PAIRS:
        if core[-1:] != BRACKET_PAIRS[core[0]]:
            return None
        core = core[1:-1]
    elif core[-1:] in ")]":
        return None
    return core if NUMERAL.match(core) else None


def weak_sign_entry(label: str) -> tuple[str, frozenset[str]]:
    """How the authority side keys a label: the D&H letter and the regnal numeral stripped
    before the key is taken, the numerals kept ("Neferu II" -> ("nfr", {"II"}))."""
    tokens = label.split()
    key = weak_sign_skeleton(" ".join(t for t in tokens if not (DISAMBIGUATOR.match(t) or numeral_of(t))))
    return key, frozenset(n for t in tokens if (n := numeral_of(t)))


def base_spelling(label: str) -> str:
    """A label as a spelling of the name: D&H's letter and any numeral left out, case-folded."""
    return " ".join(t for t in label.split() if not (DISAMBIGUATOR.match(t) or numeral_of(t))).casefold()


def _add_weak_sign(index: RoyalWomenIndex, target_id: str, labels: Iterable[str]) -> None:
    for label in labels:
        key, numerals = weak_sign_entry(label)
        if key:
            index.weak_sign[key].add(target_id)
            index.weak_sign_numerals[key][target_id] |= numerals
            index.weak_sign_spellings[key][target_id].add(base_spelling(label))


def spelled_differently(index: RoyalWomenIndex, key: str) -> bool:
    """Whether two targets of the key are reached under no common spelling: D&H's Neferet and
    Neferu both key nfr. One target's own alternative spellings (Tawosret, whom the king lists
    call Tausret; "Meryetre(-Hatshepsut)" and its alt name) are one name, not two."""
    spellings = list(index.weak_sign_spellings[key].values())
    return any(not (a & b) for i, a in enumerate(spellings) for b in spellings[i + 1:])


def different_spellings(index: RoyalWomenIndex) -> dict[str, tuple[str, ...]]:
    """The weak-sign keys that the authority's own spellings reach in more than one form for
    different targets (`spelled_differently`), with every spelling: the key cannot tell whether
    those spellings are one name, so a match on such a key resolves nothing."""
    return {key: tuple(sorted(set().union(*by_target.values())))
            for key, by_target in sorted(index.weak_sign_spellings.items()) if spelled_differently(index, key)}


def weak_sign_collisions(index: RoyalWomenIndex) -> dict[str, tuple[str, ...]]:
    """Every weak-sign skeleton that several indexed targets share, with its members; the
    authority-side collision table of the third tier."""
    return {key: tuple(sorted(targets)) for key, targets in sorted(index.weak_sign.items()) if len(targets) > 1}


def new_weak_sign_collisions(index: RoyalWomenIndex) -> dict[str, tuple[str, ...]]:
    """The collisions the third tier introduces: the groups that no exact or claim-graph key
    already holds whole (same-named women, "Tiye A"/"Tiye C", collide on every tier)."""
    existing = [*index.exact.values(), *index.normalized.values()]
    return {key: members for key, members in weak_sign_collisions(index).items()
            if not any(set(members) <= group for group in existing)}


def build_index(women: Iterable[RoyalWoman], kings: KingAuthority,
                female_rulers_path: Path = FEMALE_RULERS,
                linked_spellings: dict[str, tuple[str, ...]] | None = None) -> RoyalWomenIndex:
    """Index the women and the female rulers. Each woman's family names are resolved through
    the king authority; a family name that is not exactly one king is recorded, never
    guessed. A female ruler's king_name that is not exactly one king raises.

    `linked_spellings` gives further spellings of a woman's name from another source, keyed by
    her target id (the TLA renderings `tla_links.linked_spellings` reads from the committed
    link decisions). They are labels of her name like D&H's own, on every tier."""
    women = list(women)
    unknown = set(linked_spellings or {}) - {w.target_id for w in women}
    if unknown:
        raise ValueError(f"linked spellings for targets that are not D&H women: {sorted(unknown)}")
    by_dh_id = {dh_id: w for w in women for dh_id, _ in w.dh_rows}
    index = RoyalWomenIndex(women={w.target_id: w for w in women}, dynasties={}, family_king_ids={},
                            family_names_not_resolved={}, king_ids={}, alt_names_dropped_as_king_names={})
    for woman in women:
        kept_alt = [a for a in woman.alt_names if kings.resolve(a)["status"] == "unmatched"]
        index.alt_names_dropped_as_king_names[woman.target_id] = tuple(a for a in woman.alt_names if a not in kept_alt)
        linked = list((linked_spellings or {}).get(woman.target_id, ()))
        _add(index, woman.target_id, [*woman.labels, *kept_alt, *linked])
        _add_weak_sign(index, woman.target_id, [*woman.labels, *kept_alt, *linked])
        index.dynasties[woman.target_id] = woman.dynasties
        family, unresolved = set(), []
        for name in woman.family_names:
            found = kings.resolve(name)
            if found["status"] == "resolved":
                family.add(found["target_ids"][0])
            else:
                unresolved.append(name)
        index.family_king_ids[woman.target_id] = frozenset(family)
        index.family_dynasties[woman.target_id] = frozenset(d for king in family for d in kings.dynasties(king))
        index.family_names_not_resolved[woman.target_id] = tuple(unresolved)
    for entry in json.loads(female_rulers_path.read_text(encoding="utf-8"))["entries"]:
        found = kings.resolve(entry["king_name"])
        if found["status"] != "resolved":
            raise ValueError(f"female ruler {entry['king_name']!r} is {found['status']} among the kings")
        king_id = found["target_ids"][0]
        names = [LEADING_QUEEN.sub("", label) for label in [entry["king_name"], *kings.labels(king_id)]]
        # The weak-sign key takes the king_name only: the king lists' other labels are the
        # whole titulary (Horus names, transliterations), which is not what a queen is called.
        if entry["dh_id"] is None:
            _add(index, king_id, names)
            _add_weak_sign(index, king_id, names[:1])
            index.dynasties[king_id] = kings.dynasties(king_id)
            index.family_king_ids[king_id] = frozenset()
            index.family_dynasties[king_id] = frozenset()
        else:
            if entry["dh_id"] not in by_dh_id:
                raise ValueError(f"{female_rulers_path.name} names {entry['dh_id']}, which is not a D&H woman")
            woman = by_dh_id[entry["dh_id"]]
            index.king_ids[woman.target_id] = king_id
            _add(index, woman.target_id, names)
            _add_weak_sign(index, woman.target_id, names[:1])
    return index


def single_dynasty(value: str | None) -> int | None:
    """The record's dynasty when it gives exactly one, with or without a phase of it ("Dynasty
    18", "late Dynasty 18", "18th Dynasty", "second part of Dynasty 11", "Dynasty 12, mid–late");
    a range ("Dynasty 19–20", "late Dynasty 12–13"), "or later", a doubt, a style ("in the style
    of Dynasty 18") or an approximation ("ca. Dynasty 30") gives none."""
    if not value:
        return None
    m = SINGLE_DYNASTY.match(value)
    return int(m.group(1) or m.group(2)) if m else None


def royal_woman_cued(field_value: str, span_start: int) -> bool:
    """Whether the mention at `span_start` follows a royal-woman cue."""
    return bool(ROYAL_WOMAN_CUE_BEFORE.search(field_value[:span_start]))


def resolve_royal_woman(index: RoyalWomenIndex, text: str, *, record_king_ids: set[str],
                        record_dynasty: int | None) -> dict:
    """A cued mention's text among the royal women, with `record_king_ids` as the record's
    kings exactly as given. It does not read the kin the mention's field states; a caller
    resolving a museum field uses `resolve_ruler_mention`, which adds them."""
    # Readable numerals are written bare before any tier ("Berenike [II]" would otherwise meet
    # the bare "Berenike" on the claim-graph keys); a mention that cannot be read is refused.
    text, refusal = read_mention(text)
    if refusal:
        return {"resolution_method": None, "candidate_ids": [], "context_rule": refusal,
                "status": "unmatched", "target_ids": []}
    exact = sorted(index.exact.get(surface_key(text), ()))
    if exact:
        candidates, method = exact, "raw_exact"
    else:
        candidates = sorted({t for key in name_keys(text) for t in index.normalized.get(key, ())})
        method = "committed_normalized" if candidates else None
    skeleton = ""
    if not candidates:
        # The mention's numeral is not keyed; a candidate must carry it.
        tokens = text.split()
        numerals = {n for t in tokens if (n := numeral_of(t))}
        skeleton = weak_sign_skeleton(" ".join(t for t in tokens if not numeral_of(t)))
        if skeleton:
            candidates = sorted(t for t in index.weak_sign.get(skeleton, ())
                                if numerals <= index.weak_sign_numerals[skeleton][t])
            method = "weak_sign_skeleton" if candidates else None
    base = {"resolution_method": method, "candidate_ids": candidates, "context_rule": None}
    if method == "weak_sign_skeleton" and spelled_differently(index, skeleton):
        # The authority spells the women of this key differently, and the key cannot tell
        # whether those spellings are one name, so nothing in the record can: a family king would
        # pick the woman linked to it whatever her name ("Nofret" and a record naming Amenemhat
        # I would reach Neferu III).
        return {**base, "status": "ambiguous", "target_ids": candidates, "context_rule": "weak_sign_different_spellings"}
    chosen, rule = None, None
    # The women the record's context leaves, reported when none is chosen (`candidate_ids` keeps
    # every woman the name meets).
    remaining = candidates
    if len(candidates) == 1:
        chosen = candidates[0]
    elif candidates:
        family = [t for t in candidates if index.family_king_ids[t] & record_king_ids]
        remaining = family or candidates
        if len(family) == 1:
            chosen, rule = family[0], "family"
        elif record_dynasty is not None:
            # A candidate whose dynasty the authority does not give stays in: it is not
            # contradicted, so it cannot be ruled out.
            dynasty = [t for t in remaining if not index.dynasties[t] or record_dynasty in index.dynasties[t]]
            if len(dynasty) == 1:
                chosen, rule = dynasty[0], "dynasty"
            elif dynasty:
                remaining = dynasty
            elif not family:
                # Every woman of the name is of another dynasty, as for a lone candidate below.
                return {**base, "status": "unmatched", "target_ids": [], "context_rule": "record_dynasty_contradicts"}
            # (A record naming her family kings overrides its dynasty: the family stay.)
    if chosen is None:
        return {**base, "status": "ambiguous" if candidates else "unmatched", "target_ids": remaining}
    family_named = bool(index.family_king_ids[chosen] & record_king_ids)
    # A record naming one of her family kings overrides its own dynasty (Tentsepeh A, Dynasty
    # 21, on a monument of her son Shoshenq I, Dynasty 22).
    if (not family_named and record_dynasty is not None and index.dynasties[chosen]
            and record_dynasty not in index.dynasties[chosen]):
        return {**base, "status": "unmatched", "target_ids": [], "context_rule": "record_dynasty_contradicts"}
    if method == "weak_sign_skeleton" and not _weak_sign_confirmed(index, chosen, skeleton, family_named, record_dynasty):
        return {**base, "status": "unmatched", "target_ids": [], "context_rule": "weak_sign_unconfirmed"}
    # A D&H woman who later reigned resolves to the king.
    return {**base, "status": "resolved", "target_ids": [index.king_ids.get(chosen, chosen)], "context_rule": rule,
            "royal_woman_id": chosen}


def _weak_sign_confirmed(index: RoyalWomenIndex, chosen: str, skeleton: str, family_named: bool,
                         record_dynasty: int | None) -> bool:
    """A weak-sign match is only a shared consonant skeleton, and a queen has no throne name
    or reign to corroborate it, so the record must: it names one of her family kings, or its
    single dynasty is one of hers or her family kings'. A key of the minimum length takes the
    named king only. (A key the authority spells in several forms never gets here: it is
    ambiguous before any narrowing.)"""
    if family_named:
        return True
    if consonant_count(skeleton) == MIN_WEAK_SIGN_CONSONANTS:
        return False
    return record_dynasty is not None and record_dynasty in (set(index.dynasties[chosen]) | index.family_dynasties[chosen])


def stated_kin_names(field_value: str, span_start: int, span_end: int) -> tuple[str, ...]:
    """The names the cued mention's own field gives as her kin: after the mention, a chain of
    ", <kin> of <Name>"; before her cue, "<Name>'s <kin>, ". A name runs to the next comma,
    semicolon or bracket."""
    cue = ROYAL_WOMAN_CUE_BEFORE.search(field_value[:span_start])
    if cue is None:
        raise ValueError(f"no royal-woman cue before the mention at {span_start}: {field_value!r}")
    names = []
    before = KIN_BEFORE.search(field_value[:cue.start()])
    if before:
        names.append(before["name"])
    rest, pos = field_value[span_end:], 0
    while m := KIN_AFTER.match(rest, pos):
        names.append(m["name"])
        pos = m.end()
    return tuple(names)


def resolve_ruler_mention(index: RoyalWomenIndex, kings: KingAuthority, field_value: str, span_start: int,
                          span_end: int, *, record_king_ids: set[str], record_dynasty: int | None,
                          record_dates: tuple[int, int] | None, catalogued_reign: bool) -> dict:
    """The ruler mention at `field_value[span_start:span_end]` by the module's rule.
    `record_king_ids` are the kings the record's other (not cued) ruler mentions resolve to; a
    cued mention adds the kings its field names as her kin. A king is resolved in the record's
    context (`king_context`): its dynasty and dates, checked strictly for a catalogued reign."""
    text = field_value[span_start:span_end]
    if royal_woman_cued(field_value, span_start):
        kin = {t for name in stated_kin_names(field_value, span_start, span_end)
               if (found := kings.resolve(name))["status"] == "resolved" for t in found["target_ids"]}
        found = resolve_royal_woman(index, text, record_king_ids=record_king_ids | kin, record_dynasty=record_dynasty)
        return {**found, "authority": "royal_women", "stated_kin_king_ids": sorted(kin)}
    found = king_context.resolve_in_context(kings, text, record_dynasty=record_dynasty, record_dates=record_dates,
                                            strict=catalogued_reign)
    return {**found, "authority": "kings"}
