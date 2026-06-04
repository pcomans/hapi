"""Verdict layer + shortcut emission (ADR-018 schema 4b, §Shortcut emission).

A stage-2 verdict on a stage-1 matcher claim is itself an E13 whose P140 subject
IS the matcher's E13. Verdicts form a linear supersession chain over
``hapi:supersedes``; the "current verdict" for a matcher-claim is the unique tip.
Chain integrity is enforced by THREE load-time constraints (all three required):

  (a) unique successor per predecessor — at most one incoming supersedes;
  (b) unique root per matcher-claim   — at most one verdict with no outgoing
      supersedes;
  (c) insert-time tip-only rule       — a non-root verdict must supersede the
      CURRENT tip, never a mid-chain verdict.

Constraints (a)+(b) alone permit a cycle (A→B→C→A); (c) closes that gap.

A verdict carries one of two provenance shapes: the stage-2 LLM reviewer's
``hapi:derived_by_run → :MatcherRun (D10)``, OR — for the human-escalation path —
the curator's ``P14 → E39`` + ``P70i → E31`` (ADR reserves human attribution for
explicitly-curatorial decisions, e.g. a curator overriding a reviewer verdict).

Shortcut emission: for a primary ``emit_shortcut`` predicate, emit a direct
``(subject) hapi:<pred> (value)`` edge alongside the E13. Human-documentary claims
emit unconditionally; matcher-derived claims emit ONLY when the unique tip of
their verdict chain has outcome ``hapi:verdict_approved``.
"""

from __future__ import annotations

from .cidoc_spec import load_catalogue
from .ir import ClaimGraph, Edge, Node
from .registry import load_registry

# Verdict-outcome URIs (validated against the manifest at runtime).
VERDICT_APPROVED = "hapi:verdict_approved"
VERDICT_REJECTED = "hapi:verdict_rejected"
VERDICT_RETRACTED = "hapi:verdict_retracted"

VERDICT_TYPE = "hapi:matcher_review_verdict"
SAME_ENTITY_AS = "hapi:same_entity_as"
SUPERSEDES = "hapi:supersedes"
DERIVED_BY_RUN = "hapi:derived_by_run"

P140 = "P140_assigned_attribute_to"
P141 = "P141_assigned"
P177 = "P177_assigned_property_of_type"
P14 = "P14_carried_out_by"
P70i = "P70i_is_documented_in"


class VerdictError(ValueError):
    """Raised on any verdict-chain integrity violation (fail loud, Rule 2)."""


def _valid_outcomes() -> set[str]:
    # {"verdict_approved", ...} from the manifest → {"hapi:verdict_approved", ...}.
    return {f"hapi:{name}" for name in load_catalogue().controlled_vocab_e55()}


def _ensure_outcome_node(g: ClaimGraph, outcome: str) -> str:
    node_id = f"type::{outcome}"
    g.add_node(Node(node_id, ("E55",), {"id": outcome}, "Type"))
    return node_id


def _ensure_verdict_type_node(g: ClaimGraph) -> str:
    node_id = f"type::{VERDICT_TYPE}"
    g.add_node(Node(node_id, ("E55",), {"id": VERDICT_TYPE}, "Type"))
    return node_id


# ---------------------------------------------------------------------------
# Chain queries
# ---------------------------------------------------------------------------
def verdicts_for(g: ClaimGraph, matcher_stmt_id: str) -> list[str]:
    """All verdict-E13 ids whose P140 subject is ``matcher_stmt_id``."""
    verdict_type_node = f"type::{VERDICT_TYPE}"
    out: list[str] = []
    for n in g.nodes_of_class("E13"):
        edges = {e.predicate: e.object_id for e in g.out_edges(n.id)}
        if edges.get(P177) == verdict_type_node and edges.get(P140) == matcher_stmt_id:
            out.append(n.id)
    return out


def _successor_of(g: ClaimGraph, verdict_id: str) -> str | None:
    """The verdict that supersedes ``verdict_id`` (incoming supersedes), if any."""
    for e in g.edges_with_predicate(SUPERSEDES):
        if e.object_id == verdict_id:
            return e.subject_id
    return None


def tip_verdict(g: ClaimGraph, matcher_stmt_id: str) -> str | None:
    """The unique chain tip (verdict with no incoming supersedes), or None."""
    verdicts = verdicts_for(g, matcher_stmt_id)
    tips = [v for v in verdicts if _successor_of(g, v) is None]
    if not tips:
        return None
    if len(tips) > 1:
        raise VerdictError(
            f"Matcher claim {matcher_stmt_id!r} has {len(tips)} chain tips: {tips}"
        )
    return tips[0]


def verdict_outcome(g: ClaimGraph, verdict_id: str) -> str:
    """The outcome URI (e.g. hapi:verdict_approved) assigned by a verdict-E13."""
    for e in g.out_edges(verdict_id):
        if e.predicate == P141:
            return g.node(e.object_id).props["id"]
    raise VerdictError(f"Verdict {verdict_id!r} has no P141 outcome")


# ---------------------------------------------------------------------------
# Verdict construction with the three integrity constraints
# ---------------------------------------------------------------------------
def add_verdict(
    g: ClaimGraph,
    *,
    matcher_stmt_id: str,
    outcome: str,
    verdict_id: str,
    reviewer_run: str | None = None,
    curator_actor: str | None = None,
    curator_document: str | None = None,
    supersedes: str | None = None,
) -> str:
    """Add a verdict-E13 on ``matcher_stmt_id`` enforcing chain integrity.

    Exactly one provenance shape must be supplied: ``reviewer_run`` (machine,
    stage-2 LLM reviewer D10) XOR (``curator_actor`` + ``curator_document``)
    (human-escalation curator decision).
    """
    if outcome not in _valid_outcomes():
        raise VerdictError(
            f"Outcome {outcome!r} not in the manifest verdict vocabulary "
            f"{sorted(_valid_outcomes())}"
        )

    has_reviewer = reviewer_run is not None
    has_curator = curator_actor is not None and curator_document is not None
    if has_reviewer == has_curator:
        raise VerdictError(
            "Provide exactly one provenance shape: reviewer_run XOR "
            "(curator_actor + curator_document)"
        )

    # The subject must be a matcher claim (a same_entity_as E13).
    subj_edges = {e.predicate: e.object_id for e in g.out_edges(matcher_stmt_id)}
    same_type = f"type::{SAME_ENTITY_AS}"
    if subj_edges.get(P177) != same_type:
        raise VerdictError(
            f"Verdict subject {matcher_stmt_id!r} is not a same_entity_as matcher claim"
        )

    existing = verdicts_for(g, matcher_stmt_id)

    if supersedes is None:
        # Constraint (b): unique root per matcher-claim.
        roots = [
            v for v in existing
            if not any(e.subject_id == v for e in g.edges_with_predicate(SUPERSEDES))
        ]
        if roots:
            raise VerdictError(
                f"Matcher claim {matcher_stmt_id!r} already has a root verdict "
                f"{roots[0]!r}; a non-root verdict must supersede the current tip"
            )
    else:
        if supersedes not in existing:
            raise VerdictError(
                f"supersedes target {supersedes!r} is not a verdict for "
                f"matcher claim {matcher_stmt_id!r} (P140 must match)"
            )
        # Constraint (c): insert-time tip-only rule. A non-root verdict must
        # supersede the CURRENT tip. This single check simultaneously rejects
        # forks (constraint a — an already-superseded target is never the tip)
        # and mid-chain supersession in the insertion model.
        current_tip = tip_verdict(g, matcher_stmt_id)
        if supersedes != current_tip:
            raise VerdictError(
                f"supersedes target {supersedes!r} is not the current chain tip "
                f"({current_tip!r}); superseding a superseded or mid-chain verdict "
                f"is a hard load error"
            )
        # Constraint (a) backstop: the tip has no successor by definition, but
        # assert it explicitly so a malformed graph that slipped past the tip
        # check (e.g. a fabricated cycle) still fails loud.
        if _successor_of(g, supersedes) is not None:
            raise VerdictError(
                f"supersedes target {supersedes!r} already has a successor "
                f"(forking the chain is a hard load error)"
            )

    # Build the verdict-E13.
    outcome_node = _ensure_outcome_node(g, outcome)
    type_node = _ensure_verdict_type_node(g)
    g.add_node(Node(verdict_id, ("E13",), {}, "Statement"))
    g.add_edge(Edge(verdict_id, P140, matcher_stmt_id))
    g.add_edge(Edge(verdict_id, P141, outcome_node))
    g.add_edge(Edge(verdict_id, P177, type_node))
    if has_reviewer:
        g.add_edge(Edge(verdict_id, DERIVED_BY_RUN, reviewer_run))
    else:
        g.add_edge(Edge(verdict_id, P14, curator_actor))
        g.add_edge(Edge(verdict_id, P70i, curator_document))
    if supersedes is not None:
        g.add_edge(Edge(verdict_id, SUPERSEDES, supersedes))
    return verdict_id


# ---------------------------------------------------------------------------
# Shortcut-triple emission
# ---------------------------------------------------------------------------
def _is_machine_derived(g: ClaimGraph, stmt_id: str) -> bool:
    return any(e.predicate == DERIVED_BY_RUN for e in g.out_edges(stmt_id))


def emit_shortcuts(g: ClaimGraph) -> list[Edge]:
    """Emit direct (subject) hapi:<pred> (value) shortcut edges.

    Human-documentary claims emit unconditionally; matcher-derived claims emit
    only when their verdict-chain tip is hapi:verdict_approved. Returns the edges
    added. Idempotent (re-emitting an identical edge is a no-op at adapter level;
    here we skip duplicates).
    """
    reg = load_registry()
    emit_predicates = {
        f"type::{pid}": pid for pid, p in reg.items() if p.p177_target and p.emit_shortcut
    }
    existing = {(e.subject_id, e.predicate, e.object_id) for e in g.edges}
    added: list[Edge] = []
    for stmt in g.nodes_of_class("E13"):
        edges = {e.predicate: e.object_id for e in g.out_edges(stmt.id)}
        type_node = edges.get(P177)
        pid = emit_predicates.get(type_node)
        if pid is None:
            continue  # not an emit_shortcut predicate (or verdict/derived)
        subject = edges.get(P140)
        value = edges.get(P141)
        if subject is None or value is None:
            continue
        if _is_machine_derived(g, stmt.id):
            tip = tip_verdict(g, stmt.id)
            if tip is None or verdict_outcome(g, tip) != VERDICT_APPROVED:
                continue  # gated: no approved tip → no shortcut
        triple = (subject, pid, value)
        if triple in existing:
            continue
        edge = g.add_edge(Edge(subject, pid, value))
        existing.add(triple)
        added.append(edge)
    return added
