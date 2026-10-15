"""Spelling links between Dodson & Hilton's women and the TLA's names.

The TLA's lemma list (`sources/tla-2018-names/`) gives each personal name its Egyptological
transliteration and German and English renderings. Where a D&H name and a TLA lemma are the
same name, the lemma's renderings are further spellings of that name, and the royal-women
resolver can match a museum's spelling against them before it falls back to the weak-sign
key. A link is name to name, never a decision about a person: "Henttawy" links to every D&H
woman of that name, and the resolver still chooses among them by the record's numeral,
family and dynasty.

Candidates are generated deterministically (`candidate_pairs`): a D&H name (a label without
D&H's disambiguating letter or numeral) and a TLA personal-name lemma whose renderings meet
it on one of the resolver's three tiers. A pair meeting on the exact or the claim-graph keys
is linked by rule, as the resolver already treats those tiers as one name. A pair meeting on
the weak-sign key only, which can merge different names, is decided by two independent model
reviews and a reconciler, every interaction stored (`links/`; Rule 13, Rule 14).

The linked renderings are TLA data (CC BY-SA 4.0): they live in that source's directory and
carry its attribution.
"""

from __future__ import annotations

import collections
import json
import re
from dataclasses import dataclass
from pathlib import Path

from . import royal_women as rw
from .weak_sign_skeleton import weak_sign_skeleton

TLA_DIR = Path(__file__).resolve().parent / "sources" / "tla-2018-names"
TLA = TLA_DIR / "reconciled.jsonl"
LINKS_DIR = TLA_DIR / "links"
GLOSS = re.compile(r"\s*[\(;,].*$")

BY_RULE = ("raw_exact", "committed_normalized")
BY_REVIEW = "weak_sign_skeleton"


@dataclass(frozen=True)
class Pair:
    pair_id: str
    dh_name: str
    tla_id: str
    tier: str  # raw_exact | committed_normalized | weak_sign_skeleton
    dh_target_ids: tuple[str, ...]


def tla_rows() -> list[dict]:
    lines = TLA.read_text(encoding="utf-8").splitlines()
    if "_source" not in json.loads(lines[0]):
        raise ValueError(f"{TLA} does not start with its _source header")
    return [json.loads(line) for line in lines[1:]]


def renderings(row: dict) -> list[str]:
    """The lemma's transliteration, then each translation value with its gloss removed; a
    bracketed value is a description, not a name."""
    out = [row["transliteration"]]
    for value in (t["value"] for t in row["translations"] if t.get("value")):
        if value.startswith("["):
            continue
        value = GLOSS.sub("", value).strip()
        if value and value not in out:
            out.append(value)
    return out


def dh_names(women: list[rw.RoyalWoman]) -> dict[str, tuple[str, ...]]:
    """Each D&H name (a label without a disambiguating token) and the women who bear it."""
    names: dict[str, set[str]] = collections.defaultdict(set)
    for woman in women:
        if woman.target_id.startswith("king:"):
            continue
        for label in woman.labels:
            if not any(rw.DISAMBIGUATOR.match(token) for token in label.split()):
                names[label].add(woman.target_id)
    return {name: tuple(sorted(ids)) for name, ids in sorted(names.items())}


def withheld_keys(women: list[rw.RoyalWoman]) -> set[str]:
    """The weak-sign keys that D&H's labels spell differently for different women (the
    resolver's `different_spellings`, over the labels alone): the key cannot tell whether those
    spellings are one name, so it proposes no pair on them."""
    index = rw.RoyalWomenIndex(women={}, dynasties={}, family_king_ids={}, family_names_not_resolved={},
                               king_ids={}, alt_names_dropped_as_king_names={})
    for woman in women:
        rw._add_weak_sign(index, woman.target_id, woman.labels)
    return set(rw.different_spellings(index))


def candidate_pairs(women: list[rw.RoyalWoman], rows: list[dict]) -> list[Pair]:
    """Every (D&H name, TLA personal-name lemma) pair whose spellings meet, with the first tier
    they meet on. A withheld weak-sign key (`withheld_keys`) proposes nothing."""
    exact: dict[str, set[str]] = collections.defaultdict(set)
    normalized: dict[str, set[str]] = collections.defaultdict(set)
    weak: dict[str, set[str]] = collections.defaultdict(set)
    for row in rows:
        if row["subtype"] != "person_name":
            continue
        for form in renderings(row):
            exact[rw.surface_key(form)].add(row["tla_id"])
            for key in rw.name_keys(form):
                normalized[key].add(row["tla_id"])
            if skeleton := weak_sign_skeleton(form):
                weak[skeleton].add(row["tla_id"])
    withheld = withheld_keys(women)
    pairs: list[Pair] = []
    for name, targets in dh_names(women).items():
        by_tier: dict[str, str] = {}
        for tla_id in exact.get(rw.surface_key(name), ()):
            by_tier.setdefault(tla_id, "raw_exact")
        for key in rw.name_keys(name):
            for tla_id in normalized.get(key, ()):
                by_tier.setdefault(tla_id, "committed_normalized")
        skeleton = weak_sign_skeleton(name)
        if skeleton and skeleton not in withheld:
            for tla_id in weak.get(skeleton, ()):
                by_tier.setdefault(tla_id, "weak_sign_skeleton")
        for tla_id, tier in sorted(by_tier.items()):
            pairs.append(Pair(f"{name}|{tla_id}", name, tla_id, tier, targets))
    return pairs


def linked_spellings(decisions_path: Path | None = None) -> dict[str, tuple[str, ...]]:
    """The TLA renderings of every lemma decided to be a D&H woman's name, by her target id,
    from the committed decisions (`links/decisions.jsonl`)."""
    path = decisions_path or LINKS_DIR / "decisions.jsonl"
    rows = {r["tla_id"]: r for r in tla_rows()}
    out: dict[str, list[str]] = collections.defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        decision = json.loads(line)
        if decision["verdict"] != "same_name":
            continue
        for target in decision["dh_target_ids"]:
            for form in renderings(rows[decision["tla_id"]]):
                if form not in out[target]:
                    out[target].append(form)
    return {target: tuple(forms) for target, forms in sorted(out.items())}
