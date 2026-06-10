"""End-to-end ADR-018 POC orchestration (Leprohon + Beckerath).

Ties the whole vertical slice together:

    load both sources → seed curator display names → stage-1 deterministic
    matcher → approve candidates (curator human-escalation path by default, or a
    stage-2 LLM reviewer when a review_fn / API key is supplied) → emit gated
    shortcuts.

The resulting ClaimGraph is the one canonical artifact; ``export_all`` serialises
it to whichever substrate adapters are reachable (strict-RDF always; Postgres /
Neo4j when their services are up). This is the substrate-neutral, anti-lock-in
shape: no storage decision is baked in (ADR-019 stays open).
"""

from __future__ import annotations

from collections import defaultdict

from .ir import ClaimGraph, Node
from .loader import load_poc_graph, load_poc_graph_3way
from .matcher.stage1_deterministic import run_stage1_matcher
from .matcher.stage2_reviewer import ReviewFn, run_stage2_reviewer
from .resolution import CURATORIAL_GROUP, load_curator_display_names
from .verdicts import (
    SAME_ENTITY_AS,
    VERDICT_APPROVED,
    add_verdict,
    emit_shortcuts,
)

_MATCH_REVIEW_DOC = "document::curator_match_review_2026_05"


def approve_candidates_via_curator(g: ClaimGraph, candidate_ids: list[str]) -> list[str]:
    """Human-escalation path: a curator approves each candidate identity claim.

    Uses the ADR's human-documentary verdict shape (P14 → curatorial Group,
    P70i → curator_decision_batch). This is what makes the POC end-to-end
    demonstrable without the live LLM reviewer.
    """
    g.add_node(Node(CURATORIAL_GROUP, ("E74",), {"name": "Hapi curatorial body"}, "Group"))
    g.add_node(
        Node(
            _MATCH_REVIEW_DOC,
            ("E31",),
            {"kind": "curator_decision_batch", "decided_at": "2026-05-17"},
            "Document",
        )
    )
    verdicts: list[str] = []
    for cid in candidate_ids:
        vid = f"verdict::{cid}"
        add_verdict(
            g,
            matcher_stmt_id=cid,
            outcome=VERDICT_APPROVED,
            verdict_id=vid,
            curator_actor=CURATORIAL_GROUP,
            curator_document=_MATCH_REVIEW_DOC,
        )
        verdicts.append(vid)
    return verdicts


def build_poc_graph(review_fn: ReviewFn | None = None, *, output_dir=None) -> ClaimGraph:
    """Build the complete POC claim graph.

    ``review_fn`` (or a real ANTHROPIC_API_KEY) routes approval through the
    stage-2 LLM reviewer; otherwise the curator human-escalation path approves
    the deterministic candidates. ``output_dir`` is the reviewer-outputs location
    (defaults to the committed dir; offline tests pass a tmp dir).
    """
    g = load_poc_graph()
    load_curator_display_names(g)
    candidates = run_stage1_matcher(g)
    if review_fn is not None:
        run_stage2_reviewer(g, candidates, review_fn=review_fn, output_dir=output_dir)
    else:
        approve_candidates_via_curator(g, candidates)
    emit_shortcuts(g)
    return g


def build_poc_graph_live() -> tuple[ClaimGraph, list[str], list[str]]:
    """Build via the LIVE stage-2 Anthropic reviewer (real SDK calls).

    Requires ``ANTHROPIC_API_KEY`` — raises loudly otherwise (no silent fallback).
    Returns (graph, verdict_ids, escalated_candidate_ids).
    """
    g = load_poc_graph()
    load_curator_display_names(g)
    candidates = run_stage1_matcher(g)
    verdicts, escalations = run_stage2_reviewer(g, candidates)  # default = real SDK
    emit_shortcuts(g)
    return g, verdicts, escalations


def build_3way_graph() -> ClaimGraph:
    """Leprohon + Beckerath + Kitchen, deterministically matched across all three
    source pairs and curator-approved, so same_entity_as clusters can span 3 sources.

    Uses the exact (stage-1) matcher only — no API — so 3-way clustering is
    demonstrable offline. Cross-spelling pairs (e.g. Kitchen 'Takeloth' vs Leprohon
    'Takelot') need the constraint-narrowed LLM pick and are out of this exact pass.
    """
    g = load_poc_graph_3way()
    load_curator_display_names(g)
    pairs = [
        ("leprohon", "beckerath", "cn_lb"),
        ("leprohon", "kitchen", "cn_lk"),
        ("beckerath", "kitchen", "cn_bk"),
    ]
    all_candidates: list[str] = []
    for left, right, run_id in pairs:
        all_candidates += run_stage1_matcher(
            g, left_source=left, right_source=right, run_id=run_id
        )
    approve_candidates_via_curator(g, all_candidates)
    emit_shortcuts(g)
    return g


def same_entity_clusters(g: ClaimGraph) -> list[frozenset[str]]:
    """Connected components over approved hapi:same_entity_as shortcut edges.

    same_entity_as is symmetric, so edges are treated as undirected. Returns the
    multi-member clusters (singletons omitted), each a frozenset of ruler ids.
    """
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for e in g.edges_with_predicate(SAME_ENTITY_AS):
        union(e.subject_id, e.object_id)

    groups: dict[str, set[str]] = defaultdict(set)
    for node in list(parent):
        groups[find(node)].add(node)
    return [frozenset(members) for members in groups.values() if len(members) > 1]


def guarded_same_entity_clusters(
    g: ClaimGraph, cannot_link_fn=None
) -> tuple[list[frozenset[str]], list[tuple[str, str, str]]]:
    """Constraint-aware clustering (advisor Priority 2 / ADR-020 merge guard).

    Like ``same_entity_clusters`` but order-independent and guarded: any connected
    component that contains a cannot-link member-pair is escalated *whole* (every
    edge in it), never split edge-by-edge in arrival order — so one bad pairwise
    edge can't metastasize (the Pinudjem I / Menkheperre over-merge) and the
    result does not depend on edge order (Rule 2). Returns (clusters, conflicts)
    where each conflict is (a, b, reason) — the escalation queue.
    """
    if cannot_link_fn is None:
        from .matcher.constraints import cannot_link, documentary_same_entity_pairs
        doc_pairs = documentary_same_entity_pairs(g)

        def cannot_link_fn(x: str, y: str) -> str | None:  # noqa: ANN001
            return cannot_link(g, x, y, doc_pairs=doc_pairs)

    pairs = [
        (e.subject_id, e.object_id) for e in g.edges_with_predicate(SAME_ENTITY_AS)
    ]
    return _guarded_components(pairs, cannot_link_fn)


def _connected_components(pairs) -> list[set[str]]:
    """Raw connected components over an iterable of (a, b) pairs. Constraint-free
    union-find: the resulting partition is a pure function of the pair *set*,
    independent of iteration order."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    nodes: set[str] = set()
    for a, b in pairs:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
        nodes.add(a)
        nodes.add(b)
    comps: dict[str, set[str]] = defaultdict(set)
    for n in nodes:
        comps[find(n)].add(n)
    return list(comps.values())


def _guarded_components(pairs, cannot_link_fn):
    """Order-independent guarded clustering. Returns (clusters, conflicts).

    Computes the raw connected components over ``pairs`` (constraint-free, so
    order-independent), then decides each component as a SET, never edge-by-edge:

    - if no member-pair is cannot-link → accept the whole component as a cluster;
    - if ANY member-pair is cannot-link → the component is internally
      contradictory, so EVERY edge in it is escalated (Rule 2: a human resolves
      the whole ambiguous component; we never order-dependently keep a "winner"
      and drop the edge that happened to arrive second).

    A node's outcome is thus a pure function of its component's node-set and
    edge-set — independent of pair/iteration/hash order.
    """
    pairs = [tuple(p) for p in pairs]
    clusters: list[frozenset[str]] = []
    conflicts: list[tuple[str, str, str]] = []
    for comp in _connected_components(pairs):
        members = sorted(comp)
        bad: tuple[str, str, str] | None = None
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                reason = cannot_link_fn(members[i], members[j])
                if reason:
                    bad = (members[i], members[j], reason)
                    break
            if bad:
                break
        if bad is None:
            if len(comp) > 1:
                clusters.append(frozenset(comp))
            continue
        bx, by, breason = bad
        comp_edges = {
            tuple(sorted((a, b))) for a, b in pairs if a in comp and b in comp and a != b
        }
        for a, b in sorted(comp_edges):
            conflicts.append(
                (a, b, f"contradictory component (cannot-link {bx} / {by}: {breason})")
            )
    clusters.sort(key=lambda c: tuple(sorted(c)))
    return clusters, conflicts


def resolve_matches(g: ClaimGraph) -> tuple[list[frozenset[str]], list[tuple[str, str, str]]]:
    """Resolve same_entity_as matches into (clusters, escalations), precision-first
    and ORDER-INDEPENDENT (no incumbent, no re-prompt — ADR-020 §6).

    - Regnal mismatch (Fix 2) → escalate (sources may number the same name
      differently; never silently block or accept).
    - Uniqueness clash (Fix 1): if two DISTINCT rulers from one source both claim
      a single target ruler — and they are not the same person (phase split) —
      escalate ALL the clashing edges (set-based detection; the correct one is
      re-confirmed by a human, never auto-kept).
    - Remaining edges cluster under the hard guard (disjoint reign, same-source
      distinct); held-apart pairs are escalated too.
    """
    from .matcher.constraints import (
        cannot_link,
        documentary_same_entity_pairs,
        regnal_mismatch,
        same_person,
    )

    doc = documentary_same_entity_pairs(g)
    pairs = {frozenset((e.subject_id, e.object_id)): (e.subject_id, e.object_id)
             for e in g.edges_with_predicate(SAME_ENTITY_AS)}.values()

    escalated: set[frozenset[str]] = set()
    escalations: list[tuple[str, str, str]] = []

    def _src(x):
        return g.node(x).props.get("source")

    # Fix 2 — regnal mismatch escalates.
    for a, b in pairs:
        reason = regnal_mismatch(g, a, b)
        if reason:
            escalated.add(frozenset((a, b)))
            escalations.append((a, b, reason))

    # Fix 1 — uniqueness clash escalates ALL clashers (order-independent).
    adj: dict[str, list[str]] = defaultdict(list)
    for a, b in pairs:
        if frozenset((a, b)) in escalated:
            continue
        adj[a].append(b)
        adj[b].append(a)
    for target, neighbours in adj.items():
        by_source: dict[str, list[str]] = defaultdict(list)
        for n in neighbours:
            by_source[_src(n)].append(n)
        for source, members in by_source.items():
            members = list(dict.fromkeys(members))
            if len(members) < 2:
                continue
            all_same = all(
                same_person(g, members[i], members[j], doc)
                for i in range(len(members)) for j in range(i + 1, len(members))
            )
            if all_same:
                continue  # legitimate phase-split many-to-one
            for m in members:
                key = frozenset((target, m))
                if key not in escalated:
                    escalated.add(key)
                    escalations.append(
                        (target, m, f"uniqueness clash: target claimed by >1 distinct {source} ruler")
                    )

    remaining = [(a, b) for a, b in pairs if frozenset((a, b)) not in escalated]
    clusters, conflicts = _guarded_components(
        remaining, lambda x, y: cannot_link(g, x, y, doc_pairs=doc)
    )
    escalations.extend(conflicts)
    return clusters, escalations


def summarize(g: ClaimGraph) -> dict[str, int]:
    """Headline counts for the built graph."""
    shortcuts = len(g.edges_with_predicate(SAME_ENTITY_AS))
    return {
        "rulers": len(g.nodes_of_class("E21")),
        "statements": len(g.nodes_of_class("E13")),
        "appellations": len(g.nodes_of_class("E41")),
        "same_entity_shortcuts": shortcuts,
        "nodes": len(g.nodes),
        "edges": len(g.edges),
    }


def export_all(g: ClaimGraph) -> dict[str, object]:
    """Serialise the IR to every reachable substrate.

    Only a *down service* is tolerated (reported as ``unavailable: ...``); any
    other exception — a bug in an adapter's ``write_graph``, a mapping error —
    propagates (Rule 2: no swallowed failures). The tolerated types are the
    narrow connectivity errors each driver raises when its service is unreachable.
    """
    from sqlalchemy.exc import OperationalError
    from neo4j.exceptions import ServiceUnavailable

    from .adapters import rdf_adapter

    results: dict[str, object] = {}
    # Strict-RDF always available (in-memory).
    rdf = rdf_adapter.to_rdf(g)
    results["rdf_triples"] = len(rdf)

    try:
        from .adapters import relational_adapter
        engine = relational_adapter.get_engine()
        results["postgres"] = relational_adapter.write_graph(engine, g)
    except OperationalError as exc:  # Postgres unreachable — report, don't fail.
        results["postgres"] = f"unavailable: {type(exc).__name__}"

    try:
        from .adapters import neo4j_adapter
        driver = neo4j_adapter.get_driver()
        driver.verify_connectivity()
        results["neo4j"] = neo4j_adapter.write_graph(driver, g)
        driver.close()
    except ServiceUnavailable as exc:  # Neo4j unreachable — report, don't fail.
        results["neo4j"] = f"unavailable: {type(exc).__name__}"

    return results
