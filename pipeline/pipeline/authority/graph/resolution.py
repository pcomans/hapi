"""Per-predicate resolution policy (ADR-018 §7, § Display name migration).

When a downstream consumer needs ONE value but the graph carries competing
claims, a per-predicate rule decides which to surface. The default is fail-loud
(Constitutional rule 2 — no silent arbitrary picks). The first committed policy
is for ``hapi:display_name``:

  1. Prefer the Statement whose P14 is the curatorial Group AND whose P70i
     document kind is ``curator_decision_batch``; among those, the most recent
     ``decided_at``.
  2. Else: fail loud.

Also provides the curator-decision loader that materialises curator
``hapi:display_name`` claims from the committed decision batch
(``curator_decisions/hapi_display_names_2026_05.json``).
"""

from __future__ import annotations

import json
from pathlib import Path

from .ir import ClaimGraph, Edge, Node

_CURATOR_DIR = Path(__file__).resolve().parent.parent / "curator_decisions"

CURATORIAL_GROUP = "group::hapi_curatorial"
DISPLAY_NAME_TYPE = "type::hapi:display_name"

P140 = "P140_assigned_attribute_to"
P141 = "P141_assigned"
P177 = "P177_assigned_property_of_type"
P14 = "P14_carried_out_by"
P70i = "P70i_is_documented_in"


class ResolutionError(ValueError):
    """Raised when no committed policy resolves the competing claims."""


# ---------------------------------------------------------------------------
# Curator-decision loader
# ---------------------------------------------------------------------------
def load_curator_display_names(
    g: ClaimGraph, path: Path | None = None
) -> int:
    """Materialise curator hapi:display_name claims from a decision batch."""
    path = path or _CURATOR_DIR / "hapi_display_names_2026_05.json"
    batch = json.loads(path.read_text())
    doc_id = f"document::{batch['document_id']}"

    g.add_node(Node(CURATORIAL_GROUP, ("E74",), {"name": "Hapi curatorial body"}, "Group"))
    g.add_node(
        Node(
            doc_id,
            ("E31",),
            {
                "kind": batch["kind"],
                "decided_at": batch["decided_at"],
                "rationale": batch["rationale"],
            },
            "Document",
        )
    )
    g.add_node(Node(DISPLAY_NAME_TYPE, ("E55",), {"id": "hapi:display_name"}, "Type"))

    n = 0
    for decision in batch["decisions"]:
        ruler = decision["ruler_key"]
        g.node(ruler)  # raises if the ruler isn't loaded — fail loud
        appel = f"appellation::curator::{ruler}::display_name"
        g.add_node(
            Node(
                appel,
                ("E41",),
                {
                    "symbolic_content": decision["display_name"],
                    "appellation_kind": "display_name",
                    "language": "en",
                },
                "Appellation",
            )
        )
        stmt = f"stmt::curator::{ruler}::display_name"
        g.add_node(Node(stmt, ("E13",), {}, "Statement"))
        g.add_edge(Edge(stmt, P140, ruler))
        g.add_edge(Edge(stmt, P141, appel))
        g.add_edge(Edge(stmt, P177, DISPLAY_NAME_TYPE))
        g.add_edge(Edge(stmt, P14, CURATORIAL_GROUP))
        g.add_edge(Edge(stmt, P70i, doc_id))
        n += 1
    return n


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------
def _display_name_statements(g: ClaimGraph, ruler_id: str) -> list[str]:
    out: list[str] = []
    for n in g.nodes_of_class("E13"):
        edges = {e.predicate: e.object_id for e in g.out_edges(n.id)}
        if edges.get(P177) == DISPLAY_NAME_TYPE and edges.get(P140) == ruler_id:
            out.append(n.id)
    return out


def resolve_display_name(g: ClaimGraph, ruler_id: str) -> str:
    """Return the canonical display name for a ruler, or fail loud.

    Both clauses of the rule must hold (curatorial Group P14 AND
    curator_decision_batch P70i); a Statement satisfying only one is ignored.
    """
    candidates: list[tuple[str, str]] = []  # (decided_at, display_name)
    for stmt in _display_name_statements(g, ruler_id):
        edges = {e.predicate: e.object_id for e in g.out_edges(stmt)}
        actor = edges.get(P14)
        doc = edges.get(P70i)
        if actor != CURATORIAL_GROUP or doc is None:
            continue
        doc_node = g.node(doc)
        if doc_node.props.get("kind") != "curator_decision_batch":
            continue
        decided_at = doc_node.props.get("decided_at")
        value = g.node(edges[P141]).props["symbolic_content"]
        candidates.append((decided_at, value))

    if not candidates:
        raise ResolutionError(
            f"No curator-decision display_name for {ruler_id!r}; fail-loud default "
            f"(no fallback to source-documented claims). Ruler is unrenderable "
            f"until a curator decision arrives."
        )
    # Most recent decided_at wins; a tie on decided_at is ambiguous → fail loud.
    candidates.sort(key=lambda c: c[0], reverse=True)
    if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
        raise ResolutionError(
            f"Ambiguous display_name for {ruler_id!r}: two curator batches share "
            f"decided_at={candidates[0][0]!r}"
        )
    return candidates[0][1]
