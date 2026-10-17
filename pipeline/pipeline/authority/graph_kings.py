"""The committed claim graph's ruler resolver as a `royal_women.KingAuthority`.

The resolver is `resolver.build_ruler_resolver` (#338: promoted from the evaluations'
linkability adapter, `docs/evaluations/hapi-linkability-mvp-2026-08-28/scripts/
run_linkability.py`); this wraps it so that the royal-women index can resolve a woman's family
kings and read the female rulers' king labels and dynasties from the same graph. An evaluation
frozen on the adapter passes it in (`load_linkability`), which executes that script.

One rule is added to that resolver (#369). A numeral in brackets is a source's own count of the
bearers of a name. Leprohon's Dynasty 18 founder is "Ahmose (II)" (`leprohon-18.01`, Leprohon
2013 p. 95), counting Senakhtenre "Ahmose (I)" (`leprohon-17.26`, p. 91;
`sources/leprohon-2013-titulary/reconciled.jsonl`), where pharaoh.se and Beckerath call the
founder "Ahmose I" / "Amosis I.". Such a count often agrees with the usual one ("Merenre (I)"),
so it is not refused as such. But when the same king also bears the name under a different
plain numeral, the graph itself shows that the bracketed count is not the usual one, and that
label no longer keys on the normalized tier: a mention's "Ahmose II" (usually Amasis) does not
reach the Dynasty 18 king. Its exact surface, brackets included, still does. No claim-graph
label calls Amasis "Ahmose II" (pharaoh.se's alt_labels do, but the graph does not take alt
labels), so the mention stays unmatched.

The linkability script's own resolver, which earlier evaluations load directly and whose file
is hash-pinned by their manifests, does not have this rule: it still sends "Ahmose II" to the
Dynasty 18 king.
"""

from __future__ import annotations

import collections
import importlib.util
import json
import re
import sys
from pathlib import Path

from . import resolver

REPO = Path(__file__).resolve().parents[3]
RUN_LINKABILITY = REPO / "docs/evaluations/hapi-linkability-mvp-2026-08-28/scripts/run_linkability.py"
# A name with a trailing regnal numeral, plain ("Ahmose I") or bracketed ("Ahmose (II)").
NUMBERED_NAME = re.compile(r"^(?P<name>.*?\S)\s+(?:(?P<plain>[IVX]+)|\((?P<bracketed>[IVX]+)\))$")


def counted_otherwise(labels: set[str]) -> set[str]:
    """The bracketed-numeral labels of one king whose name the king also bears under a
    different plain numeral."""
    plain: dict[str, set[str]] = collections.defaultdict(set)
    bracketed: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    for label in labels:
        m = NUMBERED_NAME.match(label.strip())
        if m is None:
            continue
        name = m["name"].casefold()
        if m["plain"]:
            plain[name].add(m["plain"])
        else:
            bracketed[name].append((label, m["bracketed"]))
    return {label for name, found in bracketed.items() for label, numeral in found
            if plain[name] - {numeral}}


def load_linkability(path: Path = RUN_LINKABILITY, module_name: str = "_graph_kings_run_linkability"):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class GraphKings:
    """`resolve`, `labels` and `dynasties` over the claim graph's ruler identity clusters."""

    def __init__(self, linkability=None, graph: dict | None = None) -> None:
        mod = resolver if linkability is None else linkability
        graph = json.loads(mod.GRAPH.read_text(encoding="utf-8")) if graph is None else graph
        self._resolver, self._catalog = mod.build_ruler_resolver(graph)
        self._norm = mod.ruler_norm
        self._node = {r["id"]: r for r in graph["rulers"]}
        by_subject = collections.defaultdict(list)
        for claim in graph["claims"]:
            if claim["predicate"] in mod.NAME_PREDICATES:
                by_subject[claim["subject_id"]].append(claim)
        names: dict[str, set[str]] = collections.defaultdict(set)
        for target, info in self._catalog.items():
            for member in info["member_ids"]:
                names[target].add(self._node[member]["display_name"])
                for claim in by_subject[member]:
                    names[target].update(v for v in (claim.get("value_text"), claim.get("value_translit")) if v)
        self._names = names
        # The normalized keys each target keeps: those of every label but one counted otherwise.
        self._counted_otherwise = {target: counted_otherwise(labels) for target, labels in names.items()}
        self._kept_keys = {target: {key for label in labels - self._counted_otherwise[target]
                                    for key in self._norm(label) if key}
                           for target, labels in names.items()}

    @property
    def catalog(self) -> dict:
        """The resolver's targets (identity clusters) with their labels and members."""
        return self._catalog

    def resolve(self, name: str) -> dict:
        found = self._resolver.resolve(name, self._norm)
        if found["resolution_method"] != "committed_normalized":
            return found
        keys = set(found["normalized_keys"])
        kept = [t for t in found["target_ids"] if keys & self._kept_keys[t]]
        if kept == found["target_ids"]:
            return found
        status = "resolved" if len(kept) == 1 else "ambiguous" if kept else "unmatched"
        return {**found, "resolution_method": "committed_normalized" if kept else None, "status": status,
                "target_ids": kept, "counted_otherwise": sorted(set(found["target_ids"]) - set(kept))}

    def labels(self, target_id: str) -> list[str]:
        return sorted(self._names[target_id])

    def label(self, target_id: str) -> str:
        """The king's display label in the identity catalog."""
        return self._catalog[target_id]["label"]

    def dynasties(self, target_id: str) -> tuple[int, ...]:
        return tuple(sorted({self._node[m]["dynasty"] for m in self._catalog[target_id]["member_ids"]
                             if self._node[m]["dynasty"] is not None}))

    def reign(self, target_id: str) -> tuple[int, int] | None:
        """The span of the reign dates the king lists give this king (years, negative BCE): from the
        earliest start to the latest end over its members that date it; None when none does."""
        dated = [(self._node[m]["reign_start_bce"], self._node[m]["reign_end_bce"])
                 for m in self._catalog[target_id]["member_ids"]
                 if self._node[m]["reign_start_bce"] is not None and self._node[m]["reign_end_bce"] is not None]
        if not dated:
            return None
        start, end = min(s for s, _ in dated), max(e for _, e in dated)
        if start > end:
            raise ValueError(f"{target_id}: a reign that ends before it starts: {dated}")
        return start, end
