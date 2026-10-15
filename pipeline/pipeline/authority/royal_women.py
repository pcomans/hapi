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
* A woman's alternative name that is itself a king's name is not one of her names: such an
  identity (Meryetaten as the king Neferneferuaten) is disputed, and the king lists decide it.
* D&H tells same-named women apart by a letter or numeral ("Tiye A", "Neferu II"); museum
  records name them without it. When a bare name fits several women, the record's own
  context chooses, and only if exactly one woman remains:
    1. family: the women whose husband, father, mother or child, as D&H names them without
       any parenthetical hedge, is a king the same record names and the king authority
       resolves;
    2. dynasty: among the family matches if there are several, else among all, the women of
       the record's dynasty (or of no known dynasty), when the record gives exactly one.
  Otherwise the mention stays ambiguous.
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

from .claimgraph.normalize import NameForm, keys_for_form
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
SINGLE_DYNASTY = re.compile(
    r"^\s*(?:(?:early|late|middle|mid)\s+)?(?:Dynasty\s+(\d+)|(\d+)(?:st|nd|rd|th)\s+Dynasty)"
    r"\s*(?:,\s*(?:early|late|middle|mid))?\s*$",
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




def surface_key(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split()).casefold()


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
# Only a matching pair wraps a numeral: "(II]", "(II" and "II)" are unread (below), not II, since a
# broken wrapper may hide a cut numeral ("(II" of "(III)") (Codex review).
ATTACHED_NUMERAL = re.compile(r"(\w)(\([IVX]+\)|\[[IVX]+\])(?!\w)")
# A numeral left beside a bracket after the readable ones are written bare (`numeral_of`;
# attached pairs are split off first) is unread: lowercase, doubted, mismatched or with a lone
# bracket, spaced or attached ("(ii)", "[II?]", "(II]", "(II", "II)", "Cleopatre(II",
# "CleopatreII)"). A bracket followed by a letter is a restoration inside a word, not a
# numeral ("Mer[i]taten", "[I]setneferet"); one that ends a word cannot be told from a
# lowercase numeral ("Nefertit[i]" as "Berenike[ii]") and is refused (Codex review); so is one run on to the name ("CleopatreII."), and an all-uppercase word that
# ends in I, V or X ("AHHOTPII", "TETI"), where nothing tells a run-on numeral from the name's
# own letters (Codex review). The claim-graph fold and the weak-sign key would each drop it
# and accept the bare name.
# Lowercase too: "vi," or "ii." is a numeral or a name fragment, and either way unreadable.
QUALIFIED_NUMERAL = re.compile(r"(?=.*[^A-Za-z])[^A-Za-z]*[IVXivx]+[^A-Za-z]*")
UNREAD_NUMERAL = re.compile(r"[(\[][IVXivx]+\??(?:[)\]](?!\w)|(?![\w)\]]))"
                            r"|(?:(?<![A-Za-z])[IVXivx]+|(?<=[a-z])[IVX]+)\??[)\]](?!\w)"
                            r"|[a-z][IVX]+[.,;:]?(?=\s|$)"
                            r"|(?<!\S)[A-Z]*[A-HJ-UWYZ][IVX]+[.,;:]?(?!\S)")


def numeral_of(token: str) -> str | None:
    """The regnal numeral a token writes, bare or wrapped ("II", "(II)", "[II]", "II."), or
    None. Uppercase only: a lowercase "vi" or "ii" can be part of a name. A bracket must be one
    of a pair around the numeral: "(II]", "(II" and "II)" are None."""
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
                female_rulers_path: Path = FEMALE_RULERS) -> RoyalWomenIndex:
    """Index the women and the female rulers. Each woman's family names are resolved through
    the king authority; a family name that is not exactly one king is recorded, never
    guessed. A female ruler's king_name that is not exactly one king raises."""
    women = list(women)
    by_dh_id = {dh_id: w for w in women for dh_id, _ in w.dh_rows}
    index = RoyalWomenIndex(women={w.target_id: w for w in women}, dynasties={}, family_king_ids={},
                            family_names_not_resolved={}, king_ids={}, alt_names_dropped_as_king_names={})
    for woman in women:
        kept_alt = [a for a in woman.alt_names if kings.resolve(a)["status"] == "unmatched"]
        index.alt_names_dropped_as_king_names[woman.target_id] = tuple(a for a in woman.alt_names if a not in kept_alt)
        _add(index, woman.target_id, [*woman.labels, *kept_alt])
        _add_weak_sign(index, woman.target_id, [*woman.labels, *kept_alt])
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
    """The record's dynasty when it gives exactly one ("Dynasty 18", "late Dynasty 18",
    "18th Dynasty"); a range ("Dynasty 19–20") or "or later" gives none."""
    if not value:
        return None
    m = SINGLE_DYNASTY.match(value)
    return int(m.group(1) or m.group(2)) if m else None


def royal_woman_cued(field_value: str, span_start: int) -> bool:
    """Whether the mention at `span_start` follows a royal-woman cue."""
    return bool(ROYAL_WOMAN_CUE_BEFORE.search(field_value[:span_start]))


def resolve_royal_woman(index: RoyalWomenIndex, text: str, *, record_king_ids: set[str],
                        record_dynasty: int | None) -> dict:
    # A wrapped regnal numeral ("[II]", "(II)", "II.") is written bare before any tier: the
    # fold deletes bracketed text, so "Berenike [II]" would otherwise meet the bare "Berenike"
    # on the claim-graph keys and resolve to another ruler (Codex review).
    # A wrapped numeral attached to the name ("Cleopatre(II)", "Berenike[II]") is split off
    # first, as the claim-graph matcher reads it (Codex review).
    text = BRACKET_SPACE.sub(lambda m: m[1] or m[2], text)
    text = ATTACHED_NUMERAL.sub(r"\1 \2", text)
    text = " ".join(numeral_of(t) or t for t in text.split())
    # Any bracketed numeral still left (uncertain "[II?]", lowercase "[ii]", "[ II ]",
    # "Berenike[II]") would be deleted by the fold and the bare name accepted: refuse instead.
    # So is more than one numeral ("Neferu I II"): the keys would read them run together as one
    # ("neferuiii", Neferu III) (Codex review).
    # And any token still holding a numeral with a mark the readable forms lack ("II?", "?II",
    # "II!"): the keys would drop the mark and read a numeral the source doubts (Codex review).
    # A digit is never part of a name: an Arabic numeral ("Ahhotp 2") or an OCR misreading of a
    # Roman one ("Ahhotp 11") that every key would drop (Codex review).
    if UNREAD_NUMERAL.search(text) or sum(bool(NUMERAL.match(t)) for t in text.split()) > 1 \
            or any(QUALIFIED_NUMERAL.fullmatch(t) for t in text.split()) or any(c.isdigit() for c in text):
        return {"resolution_method": None, "candidate_ids": [], "context_rule": "unreadable_numeral",
                "status": "unmatched", "target_ids": []}
    # A doubt mark anywhere ("Berenike II (?)", "Berenike II ?", "Ahhotep?") questions the
    # reading, and every key drops it: refuse rather than resolve with confidence (Codex review).
    if "?" in text:
        return {"resolution_method": None, "candidate_ids": [], "context_rule": "doubted_mention",
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
    if len(candidates) == 1:
        chosen = candidates[0]
    elif candidates:
        family = [t for t in candidates if index.family_king_ids[t] & record_king_ids]
        if len(family) == 1:
            chosen, rule = family[0], "family"
        elif record_dynasty is not None:
            # A candidate whose dynasty the authority does not give stays in: it is not
            # contradicted, so it cannot be ruled out.
            dynasty = [t for t in (family or candidates)
                       if not index.dynasties[t] or record_dynasty in index.dynasties[t]]
            if len(dynasty) == 1:
                chosen, rule = dynasty[0], "dynasty"
    if chosen is None:
        return {**base, "status": "ambiguous" if candidates else "unmatched", "target_ids": candidates}
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


def resolve_ruler_mention(index: RoyalWomenIndex, kings: KingAuthority, text: str, *, royal_woman_cue: bool,
                          record_king_ids: set[str], record_dynasty: int | None) -> dict:
    """One ruler mention by the module's rule. `record_king_ids` are the kings the record's
    other (not cued) ruler mentions resolve to."""
    if royal_woman_cue:
        found = resolve_royal_woman(index, text, record_king_ids=record_king_ids, record_dynasty=record_dynasty)
        return {**found, "authority": "royal_women"}
    return {**kings.resolve(text), "context_rule": None, "authority": "kings"}
