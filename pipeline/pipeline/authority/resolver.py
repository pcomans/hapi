"""The authority resolvers for museum mentions: rulers on the claim graph's identity clusters,
sites on the reconciled iDAI gazetteer rows, tombs on Porter & Moss's reconciled tomb rows.

Promoted for production (#338) from the evaluations' linkability adapter
(`docs/evaluations/hapi-linkability-mvp-2026-08-28/scripts/run_linkability.py`), whose file
stays as it is because earlier evaluations pin it by hash. The rule is the same: a mention's
exact surface (NFC, whitespace, casefold) first; only if it meets no label, the normalized
keys (rulers: the claim graph's transliteration and phonetic keys, never its lossy skeleton;
sites and tombs: letters and digits only, diacritics removed). One target is resolved, several are
ambiguous, none is unmatched. `pipeline/tests/test_authority_resolver.py` holds it equal to
the adapter on every label of the authority; `docs/evaluations/authority-bridge-338/results/
promotion-check.json` on every mention of the frozen corpus.
"""

from __future__ import annotations

import collections
import json
import re
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from .claimgraph.normalize import NameForm, keys_for_form

REPO = Path(__file__).resolve().parents[3]
GRAPH = REPO / "web-claimgraph" / "data" / "claim-graph.json"
SOURCES = Path(__file__).resolve().parent / "sources"
IDAI = SOURCES / "idai-gazetteer" / "reconciled.jsonl"
PM_THEBAN = SOURCES / "porter-moss-theban-necropolis" / "reconciled.jsonl"
PM_MEMPHIS = SOURCES / "porter-moss-memphis" / "reconciled.jsonl"
NAME_PREDICATES = {"hapi:display_name", "hapi:prenomen", "hapi:horus_name", "hapi:nomen"}
WS = re.compile(r"\s+")


@dataclass(frozen=True)
class Target:
    target_id: str
    label: str
    entity_type: str
    representation: str


def surface_key(text: str) -> str:
    return WS.sub(" ", unicodedata.normalize("NFC", text).strip()).casefold()


def ruler_norm(text: str) -> set[str]:
    return keys_for_form(NameForm(surface=text), skeleton=False)


def place_norm(text: str) -> str:
    s = unicodedata.normalize("NFKD", text.casefold())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.translate(str.maketrans({"ꜣ": "a", "ꜥ": "a", "ʿ": "a", "‘": "'", "’": "'"}))
    # A parenthetical qualifier is kept: it can distinguish labels.
    return re.sub(r"[^a-z0-9]+", "", s)


def place_norm_set(text: str) -> set[str]:
    key = place_norm(text)
    return {key} if key else set()


class Resolver:
    def __init__(self) -> None:
        self.targets: dict[str, Target] = {}
        self.exact: dict[str, set[str]] = collections.defaultdict(set)
        self.normalized: dict[str, set[str]] = collections.defaultdict(set)

    def add(self, target: Target, labels: Iterable[str], norm_fn: Callable[[str], set[str]]) -> None:
        self.targets[target.target_id] = target
        for label in labels:
            if not label or not label.strip():
                continue
            self.exact[surface_key(label)].add(target.target_id)
            for key in norm_fn(label):
                if key:
                    self.normalized[key].add(target.target_id)

    def resolve(self, text: str, norm_fn: Callable[[str], set[str]]) -> dict:
        exact = sorted(self.exact.get(surface_key(text), ()))
        norm_keys = sorted(set(norm_fn(text)))
        normalized = sorted({t for key in norm_keys for t in self.normalized.get(key, ())})
        if exact:
            final, method = exact, "raw_exact"
        else:
            final, method = normalized, "committed_normalized" if normalized else None
        return {
            "raw_exact_status": "unique" if len(exact) == 1 else "ambiguous" if exact else "unmatched",
            "raw_exact_target_ids": exact,
            "normalized_keys": norm_keys,
            "resolution_method": method,
            "status": "resolved" if len(final) == 1 else "ambiguous" if final else "unmatched",
            "target_ids": final,
        }


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def build_ruler_resolver(graph: dict) -> tuple[Resolver, dict]:
    """One target per approved identity cluster, and per ruler node in none; its labels are
    the members' display names and name-claim values."""
    resolver = Resolver()
    node_by_id = {r["id"]: r for r in graph["rulers"]}
    member_unit: dict[str, str] = {}
    unit_members: dict[str, list[str]] = {}
    for cluster in graph["clusters"]:
        unit_members[cluster["id"]] = sorted(cluster["member_ids"])
        for member in cluster["member_ids"]:
            if member in member_unit:
                raise RuntimeError(f"overlapping graph cluster for {member}")
            member_unit[member] = cluster["id"]
    for node_id in node_by_id:
        if node_id not in member_unit:
            unit_members[node_id] = [node_id]
            member_unit[node_id] = node_id
    claims_by_node: dict[str, list[dict]] = collections.defaultdict(list)
    for claim in graph["claims"]:
        if claim["predicate"] in NAME_PREDICATES:
            claims_by_node[claim["subject_id"]].append(claim)
    cluster_by_id = {c["id"]: c for c in graph["clusters"]}
    catalog = {}
    for unit_id in sorted(unit_members):
        members = unit_members[unit_id]
        label = cluster_by_id[unit_id]["label"] if unit_id in cluster_by_id else node_by_id[unit_id]["display_name"]
        representation = "approved_claim_graph_cluster" if unit_id in cluster_by_id else "claim_graph_singleton_source_node"
        labels, source_ids, claim_ids = [], [], []
        for member in members:
            labels.append(node_by_id[member]["display_name"])
            source_ids.append(node_by_id[member]["source_id"])
            for claim in claims_by_node[member]:
                claim_ids.append(claim["id"])
                labels.extend(v for v in (claim.get("value_text"), claim.get("value_translit")) if v)
        resolver.add(Target(unit_id, label, "ruler", representation), labels, ruler_norm)
        catalog[unit_id] = {
            "label": label,
            "entity_type": "ruler",
            "representation": representation,
            "member_ids": members,
            "source_ids": sorted(set(source_ids)),
            "name_claim_ids": sorted(set(claim_ids)),
            "label_count_including_duplicates": len(labels),
        }
    return resolver, catalog


def build_site_resolver(rows: list[dict]) -> tuple[Resolver, dict]:
    """One target per reconciled iDAI site row, labelled by its display and alternative labels."""
    resolver = Resolver()
    catalog = {}
    for row in sorted((r for r in rows if r.get("kind") == "site"), key=lambda r: r["id"]):
        resolver.add(Target(row["id"], row["display"], "site", "idai_reconciled_source_row"),
                     [row["display"], *(row.get("alt_labels") or [])], place_norm_set)
        catalog[row["id"]] = {
            "label": row["display"],
            "entity_type": "site",
            "representation": "idai_reconciled_source_row",
            "types": row.get("types") or [],
            "parent_id": row.get("parent_id"),
            "parent_in_file": row.get("parent_in_file"),
            "cross_refs": row.get("cross_refs") or {},
        }
    return resolver, catalog


def build_pm_resolver() -> tuple[Resolver, dict]:
    """One target per Porter & Moss tomb row (Theban necropolis, Memphis), labelled by its tomb
    id and tomb aliases only: never its occupants, areas or notes."""
    resolver = Resolver()
    catalog = {}
    for source, path in (("pm_theban", PM_THEBAN), ("pm_memphis", PM_MEMPHIS)):
        for row in sorted(load_jsonl(path), key=lambda r: r["tomb_id"]):
            target_id = f"{source}:{row['tomb_id']}"
            resolver.add(Target(target_id, row["tomb_id"], "tomb_monument", f"{source}_reconciled_source_row"),
                         [row["tomb_id"], *(row.get("tomb_aliases") or [])], place_norm_set)
            catalog[target_id] = {
                "label": row["tomb_id"],
                "entity_type": "tomb_monument",
                "representation": f"{source}_reconciled_source_row",
                "aliases": row.get("tomb_aliases") or [],
                "occupant_name": row.get("occupant_name"),
                "area": row.get("theban_area") or row.get("memphite_area"),
                "source_citation": row.get("source_citation"),
            }
    return resolver, catalog
