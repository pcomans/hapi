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
  royal women and the female rulers), never against the kings, and only when the residue
  has at least `MIN_WEAK_SIGN_SKELETON_LEN` consonants. The family and dynasty narrowing
  above applies to its candidates unchanged. Any D&H label meets the first tier, so the
  third never changes a name that the first two resolve.
* A woman is never chosen against the record's own single dynasty: D&H is transcribed for
  some dynasties only (none of 4–10, 14 or 22 onward), so a lone name match of another known
  dynasty is another woman, and the mention stays unmatched. A candidate whose dynasty the
  authority does not give is not contradicted: the rows of D&H's two-dynasty sections (16 and
  17; 17 and 18) carry a dynasty only when the entry's own kin kings fall in one of them.
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
from .weak_sign_skeleton import DISAMBIGUATOR, weak_sign_skeleton

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
        if skeleton := weak_sign_skeleton(label):
            index.weak_sign[skeleton].add(target_id)


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
        index.dynasties[woman.target_id] = woman.dynasties
        family, unresolved = set(), []
        for name in woman.family_names:
            found = kings.resolve(name)
            if found["status"] == "resolved":
                family.add(found["target_ids"][0])
            else:
                unresolved.append(name)
        index.family_king_ids[woman.target_id] = frozenset(family)
        index.family_names_not_resolved[woman.target_id] = tuple(unresolved)
    for entry in json.loads(female_rulers_path.read_text(encoding="utf-8"))["entries"]:
        found = kings.resolve(entry["king_name"])
        if found["status"] != "resolved":
            raise ValueError(f"female ruler {entry['king_name']!r} is {found['status']} among the kings")
        king_id = found["target_ids"][0]
        names = [LEADING_QUEEN.sub("", label) for label in [entry["king_name"], *kings.labels(king_id)]]
        if entry["dh_id"] is None:
            _add(index, king_id, names)
            index.dynasties[king_id] = kings.dynasties(king_id)
            index.family_king_ids[king_id] = frozenset()
        else:
            if entry["dh_id"] not in by_dh_id:
                raise ValueError(f"{female_rulers_path.name} names {entry['dh_id']}, which is not a D&H woman")
            woman = by_dh_id[entry["dh_id"]]
            index.king_ids[woman.target_id] = king_id
            _add(index, woman.target_id, names)
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
    exact = sorted(index.exact.get(surface_key(text), ()))
    if exact:
        candidates, method = exact, "raw_exact"
    else:
        candidates = sorted({t for key in name_keys(text) for t in index.normalized.get(key, ())})
        method = "committed_normalized" if candidates else None
    if not candidates and (skeleton := weak_sign_skeleton(text)):
        candidates = sorted(index.weak_sign.get(skeleton, ()))
        method = "weak_sign_skeleton" if candidates else None
    base = {"resolution_method": method, "candidate_ids": candidates, "context_rule": None}
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
    if record_dynasty is not None and index.dynasties[chosen] and record_dynasty not in index.dynasties[chosen]:
        return {**base, "status": "unmatched", "target_ids": [], "context_rule": "record_dynasty_contradicts"}
    # A D&H woman who later reigned resolves to the king.
    return {**base, "status": "resolved", "target_ids": [index.king_ids.get(chosen, chosen)], "context_rule": rule,
            "royal_woman_id": chosen}


def resolve_ruler_mention(index: RoyalWomenIndex, kings: KingAuthority, text: str, *, royal_woman_cue: bool,
                          record_king_ids: set[str], record_dynasty: int | None) -> dict:
    """One ruler mention by the module's rule. `record_king_ids` are the kings the record's
    other (not cued) ruler mentions resolve to."""
    if royal_woman_cue:
        found = resolve_royal_woman(index, text, record_king_ids=record_king_ids, record_dynasty=record_dynasty)
        return {**found, "authority": "royal_women"}
    return {**kings.resolve(text), "context_rule": None, "authority": "kings"}
