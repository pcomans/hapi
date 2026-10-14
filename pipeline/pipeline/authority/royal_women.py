"""Royal women as an authority for museum ruler mentions (Dodson & Hilton 2004).

Museum records name queens the way they name kings ("Relief of Queen Neferu", "Queen
Tiye"), but the king lists (the claim graph) hold no queens, so such a mention could not
resolve at all. This module resolves them against the royal women of Dodson & Hilton, *The
Complete Royal Families of Ancient Egypt* (`sources/dodson-hilton-queens/reconciled.jsonl`,
page-cited, reconciled), approved as an authority on 2026-10-14.

The rule, which is deterministic and fixed here:

* A name after a queen cue ("Queen", "Queen Mother", "King's (Great) Wife", "Great Royal
  Wife", "God's Wife") resolves among the royal women, never among the kings, so a queen is
  never merged with a king of her name. A queen-cued name no royal woman bears stays
  unmatched. Every other ruler mention resolves among the kings, as before.
* The women who later reigned as kings (Hatshepsut D, Sobkneferu, Tawosret) are the kings:
  a mention that lands on one resolves to the king (`female-kings-crosswalk.json`).
* D&H tells same-named women apart by a letter or numeral ("Tiye A", "Neferu II"); museum
  records name them without it. When a bare name fits several women, the record's own
  context chooses, and only if exactly one woman remains:
    1. family: the women whose husband, father, mother or child, as D&H names them without
       any parenthetical hedge, is a king the same record names and the king authority
       resolves;
    2. dynasty: among the family matches if there are several, else among all, the women of
       the record's dynasty, when the record gives exactly one.
  Otherwise the mention stays ambiguous.
* D&H keys a row by (dh_id, sub_period). Every female dh_id under more than one sub_period
  is classified in `same-woman-across-sub-periods.json` as one woman or several; an
  unclassified one raises.
"""

from __future__ import annotations

import collections
import json
import re
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .claimgraph.normalize import NameForm, keys_for_form

SOURCE_DIR = Path(__file__).resolve().parent / "sources" / "dodson-hilton-queens"
DODSON_HILTON = SOURCE_DIR / "reconciled.jsonl"
SAME_WOMAN = SOURCE_DIR / "same-woman-across-sub-periods.json"
FEMALE_KINGS = SOURCE_DIR / "female-kings-crosswalk.json"
TARGET_PREFIX = "dodson_hilton:"

APOSTROPHE = "['’]"
QUEEN_CUE_BEFORE = re.compile(
    rf"\b(?:queen(?:\s+mother)?|king{APOSTROPHE}s\s+(?:great\s+)?wife|great\s+royal\s+wife|god{APOSTROPHE}s\s+wife)\s*$",
    re.I,
)
PARENTHETICAL = re.compile(r"\(")
LACUNA = re.compile(r"\[\s*(?:\.\.\.|…)\s*\]")
DISAMBIGUATOR = re.compile(r"^(?:[A-Z]|[IVX]+)$")
# A D&H letter on a kinship name marks one of D&H's own individuals, not a king-list name;
# I, V and X are left out because they are also regnal numerals.
DH_LETTER = re.compile(r"^[A-HJ-UWYZ]$")
SINGLE_DYNASTY = re.compile(
    r"^\s*(?:(?:early|late|middle|mid)\s+)?(?:Dynasty\s+(\d+)|(\d+)(?:st|nd|rd|th)\s+Dynasty)"
    r"\s*(?:,\s*(?:early|late|middle|mid))?\s*$",
    re.I,
)

# A king resolver: a name -> {"status": "resolved"|"ambiguous"|"unmatched", "target_ids": [...], ...}
KingResolver = Callable[[str], dict]


@dataclass(frozen=True)
class RoyalWoman:
    target_id: str
    label: str
    labels: tuple[str, ...]
    dynasties: tuple[int, ...]
    family_names: tuple[str, ...]
    dh_rows: tuple[tuple[str, str], ...]
    source_citations: tuple[dict, ...]
    king_name: str | None


@dataclass
class RoyalWomenIndex:
    women: dict[str, RoyalWoman]
    family_king_ids: dict[str, frozenset[str]]
    family_names_not_resolved: dict[str, tuple[str, ...]]
    king_ids: dict[str, str]
    exact: dict[str, set[str]] = field(default_factory=lambda: collections.defaultdict(set))
    normalized: dict[str, set[str]] = field(default_factory=lambda: collections.defaultdict(set))


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


def load_royal_women(path: Path = DODSON_HILTON, same_woman_path: Path = SAME_WOMAN,
                     female_kings_path: Path = FEMALE_KINGS) -> list[RoyalWoman]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    women_rows = [r for r in rows if r["sex"] == "female" and not r["is_group_entry"]]
    same_woman = {e["dh_id"]: e for e in json.loads(same_woman_path.read_text(encoding="utf-8"))["entries"]}
    king_name = {e["dh_id"]: e["king_name"] for e in json.loads(female_kings_path.read_text(encoding="utf-8"))["entries"]}
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
    for dh_id in king_name:
        if dh_id not in sub_periods:
            raise ValueError(f"{female_kings_path.name} lists {dh_id}, which is not a D&H woman")

    grouped: dict[str, list[dict]] = collections.defaultdict(list)
    for row in women_rows:
        one = row["dh_id"] in same_woman and same_woman[row["dh_id"]]["same_woman"]
        key = row["dh_id"] if one or len(sub_periods[row["dh_id"]]) == 1 else f"{row['dh_id']}|{row['sub_period']}"
        grouped[TARGET_PREFIX + key].append(row)
    women = []
    for target_id, entries in sorted(grouped.items()):
        labels: list[str] = []
        family: list[str] = []
        for row in entries:
            labels += labels_for(row["name"]) + [alt for alt in row["alt_names"] if not PARENTHETICAL.search(alt)]
            family += [n for n in (*row["spouse_names"], row["father_name"], row["mother_name"],
                                   *row["children_names"]) if usable_kinship_name(n)]
        crosswalk = king_name.get(entries[0]["dh_id"])
        if crosswalk:
            labels.append(crosswalk)
        women.append(RoyalWoman(
            target_id=target_id,
            label=entries[0]["name"],
            labels=tuple(dict.fromkeys(labels)),
            dynasties=tuple(sorted({r["dynasty"] for r in entries if r["dynasty"] is not None})),
            family_names=tuple(dict.fromkeys(family)),
            dh_rows=tuple((r["dh_id"], r["sub_period"]) for r in entries),
            source_citations=tuple(r["source_citation"] for r in entries),
            king_name=crosswalk,
        ))
    return women


def build_index(women: Iterable[RoyalWoman], resolve_king: KingResolver) -> RoyalWomenIndex:
    """Index the women's names and resolve each one's family names, and each female king's
    king name, through the king authority. A family name that is not exactly one king is
    recorded, never guessed; a female king's name that is not exactly one king raises."""
    women = list(women)
    index = RoyalWomenIndex(women={w.target_id: w for w in women}, family_king_ids={},
                            family_names_not_resolved={}, king_ids={})
    for woman in women:
        if woman.king_name is not None:
            found = resolve_king(woman.king_name)
            if found["status"] != "resolved":
                raise ValueError(f"female king {woman.label}: {woman.king_name!r} is {found['status']} among the kings")
            index.king_ids[woman.target_id] = found["target_ids"][0]
        kings, unresolved = set(), []
        for name in woman.family_names:
            found = resolve_king(name)
            if found["status"] == "resolved":
                kings.add(found["target_ids"][0])
            else:
                unresolved.append(name)
        index.family_king_ids[woman.target_id] = frozenset(kings)
        index.family_names_not_resolved[woman.target_id] = tuple(unresolved)
        for label in woman.labels:
            index.exact[surface_key(label)].add(woman.target_id)
            for key in name_keys(label):
                index.normalized[key].add(woman.target_id)
    return index


def single_dynasty(value: str | None) -> int | None:
    """The record's dynasty when it gives exactly one ("Dynasty 18", "late Dynasty 18",
    "18th Dynasty"); a range ("Dynasty 19–20") or "or later" gives none."""
    if not value:
        return None
    m = SINGLE_DYNASTY.match(value)
    return int(m.group(1) or m.group(2)) if m else None


def queen_cued(field_value: str, span_start: int) -> bool:
    """Whether the mention at `span_start` follows a queen cue."""
    return bool(QUEEN_CUE_BEFORE.search(field_value[:span_start]))


def resolve_royal_woman(index: RoyalWomenIndex, text: str, *, record_king_ids: set[str],
                        record_dynasty: int | None) -> dict:
    exact = sorted(index.exact.get(surface_key(text), ()))
    if exact:
        candidates, method = exact, "raw_exact"
    else:
        candidates = sorted({t for key in name_keys(text) for t in index.normalized.get(key, ())})
        method = "committed_normalized" if candidates else None
    base = {"resolution_method": method, "candidate_ids": candidates, "context_rule": None}
    chosen, rule = None, None
    if len(candidates) == 1:
        chosen = candidates[0]
    elif candidates:
        family = [t for t in candidates if index.family_king_ids[t] & record_king_ids]
        if len(family) == 1:
            chosen, rule = family[0], "family"
        elif record_dynasty is not None:
            dynasty = [t for t in (family or candidates) if record_dynasty in index.women[t].dynasties]
            if len(dynasty) == 1:
                chosen, rule = dynasty[0], "dynasty"
    if chosen is None:
        return {**base, "status": "ambiguous" if candidates else "unmatched", "target_ids": candidates}
    # A woman who later reigned resolves to the king.
    return {**base, "status": "resolved", "target_ids": [index.king_ids.get(chosen, chosen)], "context_rule": rule,
            "royal_woman_id": chosen}


def resolve_ruler_mention(index: RoyalWomenIndex, resolve_king: KingResolver, text: str, *, queen_cue: bool,
                          record_king_ids: set[str], record_dynasty: int | None) -> dict:
    """One ruler mention by the module's rule. `record_king_ids` are the kings the record's
    other (not queen-cued) ruler mentions resolve to."""
    if queen_cue:
        found = resolve_royal_woman(index, text, record_king_ids=record_king_ids, record_dynasty=record_dynasty)
        return {**found, "authority": "royal_women"}
    return {**resolve_king(text), "context_rule": None, "authority": "kings"}
