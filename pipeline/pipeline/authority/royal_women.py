"""Royal women as an authority for museum ruler mentions (Dodson & Hilton 2004).

Museum records name queens the way they name kings ("Relief of Queen Neferu", "Queen
Tiye"), but the king lists (the claim graph) hold no queens, so such a mention could not
resolve at all. This module resolves them against the royal women of Dodson & Hilton, *The
Complete Royal Families of Ancient Egypt* (`sources/dodson-hilton-queens/reconciled.jsonl`,
page-cited, reconciled), approved as an authority on 2026-10-14.

The rule, which is deterministic and fixed here:

* A name after a "queen" cue resolves among the royal women, never among the kings, so a
  queen is never merged with a king of her name ("Queen Ahmose" and King Ahmose). A
  queen-cued name no royal woman bears resolves among the kings instead, which list female
  kings and the Ptolemaic queens Leprohon includes (Tausret, Arsinoe II).
* Every other ruler mention resolves among the kings, as before.
* D&H tells same-named women apart by a letter or numeral ("Tiye A", "Neferu II"); museum
  records name them without it. When a bare name fits several women, the record's own
  context chooses, in this order, and only if exactly one woman remains:
    1. family: the women whose husband, father or child (as D&H states it, without a
       "possible"/"probable"/"conceivably" hedge) is a king the same record names and the
       king authority resolves;
    2. dynasty: the women of the record's dynasty, when the record gives exactly one.
  Otherwise the mention stays ambiguous.
* D&H keys a row by (dh_id, sub_period). The same dh_id under two sub-periods is one woman
  only where the source's README says so (a cross-reference stub and the full Brief Life:
  Takhat A, Isetneferet C); any other repeated dh_id stays two women.
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

DODSON_HILTON = Path(__file__).resolve().parent / "sources" / "dodson-hilton-queens" / "reconciled.jsonl"
TARGET_PREFIX = "dodson_hilton:"
SAME_WOMAN_ACROSS_SUB_PERIODS = frozenset({"Takhat A", "Isetneferet C"})

QUEEN_CUE_BEFORE = re.compile(r"\bqueen\s*$", re.I)
HEDGED = re.compile(r"\((?:possible|possibly|probable|probably|conceivably|perhaps|uncertain)\)", re.I)
DISAMBIGUATOR = re.compile(r"^(?:[A-Z]|[IVX]+)$")
SINGLE_DYNASTY = re.compile(
    r"^\s*(?:(?:early|late|middle|mid)\s+)?Dynasty\s+(\d+)\s*(?:,\s*(?:early|late|middle|mid))?\s*$", re.I
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


@dataclass
class RoyalWomenIndex:
    women: dict[str, RoyalWoman]
    family_king_ids: dict[str, frozenset[str]]
    family_names_not_resolved: dict[str, tuple[str, ...]]
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
    the first one: "Tiye B Mereniset" -> "Tiye B Mereniset", "Tiye Mereniset", "Tiye"."""
    tokens = name.split()
    labels = [name]
    kept = [t for t in tokens if not DISAMBIGUATOR.match(t)]
    if kept and len(kept) < len(tokens):
        labels.append(" ".join(kept))
        first = next(i for i, t in enumerate(tokens) if DISAMBIGUATOR.match(t))
        if first:
            labels.append(" ".join(tokens[:first]))
    return list(dict.fromkeys(labels))


def load_royal_women(path: Path = DODSON_HILTON) -> list[RoyalWoman]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    grouped: dict[str, list[dict]] = collections.defaultdict(list)
    for row in rows:
        if row["sex"] != "female" or row["is_group_entry"]:
            continue
        key = row["dh_id"] if row["dh_id"] in SAME_WOMAN_ACROSS_SUB_PERIODS else f"{row['dh_id']}|{row['sub_period']}"
        grouped[TARGET_PREFIX + key].append(row)
    women = []
    for target_id, entries in sorted(grouped.items()):
        keys = [(r["dh_id"], r["sub_period"]) for r in entries]
        if len(set(keys)) != len(keys):
            raise ValueError(f"duplicate Dodson & Hilton row for {target_id}: {keys}")
        labels: list[str] = []
        family: list[str] = []
        for row in entries:
            labels += labels_for(row["name"]) + [alt for alt in row["alt_names"] if not HEDGED.search(alt)]
            family += [n for n in (*row["spouse_names"], row["father_name"], *row["children_names"])
                       if n and not HEDGED.search(n)]
        women.append(RoyalWoman(
            target_id=target_id,
            label=entries[0]["name"],
            labels=tuple(dict.fromkeys(labels)),
            dynasties=tuple(sorted({r["dynasty"] for r in entries if r["dynasty"] is not None})),
            family_names=tuple(dict.fromkeys(family)),
            dh_rows=tuple(keys),
            source_citations=tuple(r["source_citation"] for r in entries),
        ))
    return women


def build_index(women: Iterable[RoyalWoman], resolve_king: KingResolver) -> RoyalWomenIndex:
    """Index the women's names and resolve each one's family names through the king
    authority; a family name that is not exactly one king is recorded, never guessed."""
    women = list(women)
    index = RoyalWomenIndex(women={w.target_id: w for w in women}, family_king_ids={}, family_names_not_resolved={})
    for woman in women:
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
    """The record's dynasty when it gives exactly one ("Dynasty 18", "late Dynasty 18"); a
    range ("Dynasty 19–20") or "or later" gives none."""
    if not value:
        return None
    m = SINGLE_DYNASTY.match(value)
    return int(m.group(1)) if m else None


def queen_cued(field_value: str, span_start: int) -> bool:
    """Whether the mention at `span_start` follows the word "queen"."""
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
    if len(candidates) <= 1:
        return {**base, "status": "resolved" if candidates else "unmatched", "target_ids": candidates}
    family = [t for t in candidates if index.family_king_ids[t] & record_king_ids]
    if len(family) == 1:
        return {**base, "status": "resolved", "target_ids": family, "context_rule": "family"}
    pool = family or candidates
    if record_dynasty is not None:
        dynasty = [t for t in pool if record_dynasty in index.women[t].dynasties]
        if len(dynasty) == 1:
            return {**base, "status": "resolved", "target_ids": dynasty, "context_rule": "dynasty"}
    return {**base, "status": "ambiguous", "target_ids": candidates}


def resolve_ruler_mention(index: RoyalWomenIndex, resolve_king: KingResolver, text: str, *, queen_cue: bool,
                          record_king_ids: set[str], record_dynasty: int | None) -> dict:
    """One ruler mention by the module's rule. `record_king_ids` are the kings the record's
    other (not queen-cued) ruler mentions resolve to."""
    if queen_cue:
        found = resolve_royal_woman(index, text, record_king_ids=record_king_ids, record_dynasty=record_dynasty)
        if found["status"] != "unmatched":
            return {**found, "authority": "royal_women"}
        return {**resolve_king(text), "context_rule": None, "authority": "kings_no_royal_woman"}
    return {**resolve_king(text), "context_rule": None, "authority": "kings"}
