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

from .ir import ClaimGraph, Edge, Node
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


def build_poc_graph(review_fn: ReviewFn | None = None) -> ClaimGraph:
    """Build the complete POC claim graph.

    ``review_fn`` (or a real ANTHROPIC_API_KEY) routes approval through the
    stage-2 LLM reviewer; otherwise the curator human-escalation path approves
    the deterministic candidates.
    """
    g = load_poc_graph()
    load_curator_display_names(g)
    candidates = run_stage1_matcher(g)
    if review_fn is not None:
        run_stage2_reviewer(g, candidates, review_fn=review_fn)
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
    """Serialise the IR to every reachable substrate. Never raises on a down service."""
    from .adapters import rdf_adapter

    results: dict[str, object] = {}
    # Strict-RDF always available (in-memory).
    rdf = rdf_adapter.to_rdf(g)
    results["rdf_triples"] = len(rdf)

    try:
        from .adapters import relational_adapter
        engine = relational_adapter.get_engine()
        results["postgres"] = relational_adapter.write_graph(engine, g)
    except Exception as exc:  # noqa: BLE001 - report, never fail the export
        results["postgres"] = f"unavailable: {type(exc).__name__}"

    try:
        from .adapters import neo4j_adapter
        driver = neo4j_adapter.get_driver()
        driver.verify_connectivity()
        results["neo4j"] = neo4j_adapter.write_graph(driver, g)
        driver.close()
    except Exception as exc:  # noqa: BLE001
        results["neo4j"] = f"unavailable: {type(exc).__name__}"

    return results
