"""Connected components over APPROVED ``same_entity_as`` links, for navigation and
visualization only.

Important: this is NOT authority data and does NOT assert a merged canonical entity. Each
edge in a cluster remains an independent, individually-verdicted pairwise claim (ADR-020
forbids treating transitive closure as authority). The cluster is an emergent view
"these records are connected by approved links" — shown so a reader can navigate a king
across sources, with every connecting edge still inspectable and sourced. We surface the
component so the UI can lay it out; we never collapse it."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .graph_ir import RulerNode
from .verdicts import MatchEdge


@dataclass
class IdentityCluster:
    id: str
    member_ids: list[str]
    sources: list[str]
    source_count: int
    label: str
    edges: list[dict] = field(default_factory=list)


class _DSU:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:  # path compression
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            # deterministic: smaller id becomes root
            if ra < rb:
                self.parent[rb] = ra
            else:
                self.parent[ra] = rb


def compute_clusters(
    rulers: list[RulerNode], approved_edges: list[MatchEdge]
) -> list[IdentityCluster]:
    dsu = _DSU()
    ruler_by_id = {r.id: r for r in rulers}
    for e in approved_edges:
        dsu.union(e.a_id, e.b_id)

    members_by_root: dict[str, list[str]] = {}
    for e in approved_edges:
        for _id in (e.a_id, e.b_id):
            root = dsu.find(_id)
            lst = members_by_root.setdefault(root, [])
            if _id not in lst:
                lst.append(_id)

    edges_by_root: dict[str, list[dict]] = {}
    for e in approved_edges:
        root = dsu.find(e.a_id)
        edges_by_root.setdefault(root, []).append(
            {"a_id": e.a_id, "b_id": e.b_id, "basis": e.basis}
        )

    clusters: list[IdentityCluster] = []
    for root, member_ids in members_by_root.items():
        member_ids.sort()
        members = [ruler_by_id[i] for i in member_ids if i in ruler_by_id]
        sources = sorted({m.source_id for m in members})
        name_counts = Counter(m.display_name for m in members)
        # most common display name; ties → lexicographically first
        label = sorted(name_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        clusters.append(
            IdentityCluster(
                id=f"cluster-{root}",
                member_ids=member_ids,
                sources=sources,
                source_count=len(sources),
                label=label,
                edges=edges_by_root.get(root, []),
            )
        )

    clusters.sort(key=lambda c: (-c.source_count, -len(c.member_ids), c.label))
    return clusters
