"""Precision/recall of matcher clusters vs the Wikidata silver gold (ADR-020).

Aligns each ruler in a built ClaimGraph to a Wikidata QID (via Wikidata's own
aliases), restricts to the rulers that aligned ("evaluable"), then compares the
matcher's predicted clusters (connected components over hapi:same_entity_as) to
the gold partition (group by QID). Reports pairwise P/R/F1 and B-cubed P/R/F1,
plus the actual false-positive (over-merge) and false-negative (missed) pairs so
errors like Pinudjem I / Menkheperre are visible, not just scored.

These are SILVER numbers (ADR-020): directional, not authority-grade.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations

from ..ir import ClaimGraph
from ..poc import same_entity_clusters
from .wikidata import align


def _display(g: ClaimGraph, rid: str) -> str:
    try:
        return g.node(f"appellation::{rid}::display_name").props["symbolic_content"]
    except KeyError:
        return rid


def _aligned_rulers(g: ClaimGraph) -> tuple[dict[str, str], dict[str, int]]:
    """Map ruler_id → QID for rulers that align; also return status counts."""
    qid_of: dict[str, str] = {}
    status_counts: dict[str, int] = defaultdict(int)
    for n in g.nodes_of_class("E21"):
        if n.props.get("source") is None:
            continue  # skip scholar Persons (E21 with no source)
        qid, status = align(_display(g, n.id))
        status_counts[status] += 1
        if qid is not None:
            qid_of[n.id] = qid
    return qid_of, dict(status_counts)


def _predicted_partition(
    g: ClaimGraph, universe: set[str], clusters: list[frozenset[str]] | None = None
) -> dict[str, frozenset[str]]:
    """ruler_id → its predicted cluster (restricted to ``universe``); singletons included.

    ``clusters`` lets a caller supply a precomputed partition (e.g. the guarded
    clustering); default is the unguarded connected components.
    """
    if clusters is None:
        clusters = same_entity_clusters(g)
    member_to_cluster: dict[str, frozenset[str]] = {}
    for cluster in clusters:
        restricted = frozenset(cluster & universe)
        for m in restricted:
            member_to_cluster[m] = restricted
    for r in universe:
        member_to_cluster.setdefault(r, frozenset({r}))
    return member_to_cluster


def _pairs(partition_members: dict[str, frozenset[str]]) -> set[frozenset[str]]:
    seen: set[frozenset[str]] = set()
    out: set[frozenset[str]] = set()
    for cluster in partition_members.values():
        key = frozenset(cluster)
        if key in seen or len(cluster) < 2:
            continue
        seen.add(key)
        for a, b in combinations(sorted(cluster), 2):
            out.add(frozenset((a, b)))
    return out


def evaluate(g: ClaimGraph, clusters: list[frozenset[str]] | None = None) -> dict:
    qid_of, status_counts = _aligned_rulers(g)
    universe = set(qid_of)

    # Gold partition: group evaluable rulers by QID.
    gold_clusters: dict[str, set[str]] = defaultdict(set)
    for rid, qid in qid_of.items():
        gold_clusters[qid].add(rid)
    gold_member = {rid: frozenset(gold_clusters[qid]) for rid, qid in qid_of.items()}

    pred_member = _predicted_partition(g, universe, clusters)

    pred_pairs = _pairs(pred_member)
    gold_pairs = _pairs(gold_member)
    tp = len(pred_pairs & gold_pairs)
    fp = len(pred_pairs - gold_pairs)
    fn = len(gold_pairs - pred_pairs)
    p = tp / (tp + fp) if (tp + fp) else 1.0
    r = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0

    # B-cubed over evaluable items.
    bp = br = 0.0
    for item in universe:
        pc, gc = pred_member[item], gold_member[item]
        inter = len(pc & gc)
        bp += inter / len(pc)
        br += inter / len(gc)
    n = len(universe) or 1
    bp /= n
    br /= n
    bf1 = 2 * bp * br / (bp + br) if (bp + br) else 0.0

    def _names(pair):
        return sorted(_display(g, x) for x in pair)

    return {
        "aligned": len(universe),
        "alignment_status": status_counts,
        "pairwise": {"tp": tp, "fp": fp, "fn": fn,
                     "precision": round(p, 3), "recall": round(r, 3), "f1": round(f1, 3)},
        "bcubed": {"precision": round(bp, 3), "recall": round(br, 3), "f1": round(bf1, 3)},
        "false_merges": [_names(pr) for pr in sorted(pred_pairs - gold_pairs, key=lambda s: sorted(s))],
        "missed_pairs": [_names(pr) for pr in sorted(gold_pairs - pred_pairs, key=lambda s: sorted(s))],
    }
