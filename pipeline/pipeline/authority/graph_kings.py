"""The committed claim graph's ruler resolver as a `royal_women.KingAuthority`.

The resolver is the linkability resolver the evaluations load
(`docs/evaluations/hapi-linkability-mvp-2026-08-28/scripts/run_linkability.py`); this wraps it
so that the royal-women index can resolve a woman's family kings and read the female rulers'
king labels and dynasties from the same graph.

An evaluation adapter, not enrichment: it executes the evaluations' linkability script, which
puts the repository's `pipeline/` on `sys.path` and stays in `sys.modules`.
"""

from __future__ import annotations

import collections
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RUN_LINKABILITY = REPO / "docs/evaluations/hapi-linkability-mvp-2026-08-28/scripts/run_linkability.py"


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
        mod = load_linkability() if linkability is None else linkability
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

    @property
    def catalog(self) -> dict:
        """The resolver's targets (identity clusters) with their labels and members."""
        return self._catalog

    def resolve(self, name: str) -> dict:
        return self._resolver.resolve(name, self._norm)

    def labels(self, target_id: str) -> list[str]:
        return sorted(self._names[target_id])

    def dynasties(self, target_id: str) -> tuple[int, ...]:
        return tuple(sorted({self._node[m]["dynasty"] for m in self._catalog[target_id]["member_ids"]
                             if self._node[m]["dynasty"] is not None}))
