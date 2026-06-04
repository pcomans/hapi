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

from .ir import ClaimGraph, Edge, Node
from .loader import load_poc_graph
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
