"""Persist matcher same_entity_as decisions so a run is disk-evaluable.

The lesson from a wasteful re-run (ADR-020): never re-spend tokens to *score*
existing matcher output. A run should dump its same_entity_as decisions —
subject, object, verdict outcome, and the reviewer's WHY (reasoning) — to disk;
the benchmark then reconstructs the predicted graph from that file with no API.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..ir import ClaimGraph, Edge
from ..verdicts import (
    SAME_ENTITY_AS,
    VERDICT_APPROVED,
    tip_verdict,
    verdict_outcome,
)

P140 = "P140_assigned_attribute_to"
P141 = "P141_assigned"
P177 = "P177_assigned_property_of_type"
P14 = "P14_carried_out_by"
DERIVED_BY_RUN = "hapi:derived_by_run"
_SAME_TYPE = f"type::{SAME_ENTITY_AS}"


def dump_same_entity_edges(g: ClaimGraph) -> list[dict]:
    """Serialise every same_entity_as *claim* with its current outcome + reasoning.

    - Matcher claims (carry ``hapi:derived_by_run``): outcome is the verdict-chain
      tip's outcome (or ``None`` = pending), and reasoning is the tip's WHY.
    - Documentary claims (carry ``P14`` — intra-source same_person_as): outcome is
      ``hapi:verdict_approved`` (source-attested), no reviewer reasoning.
    """
    out: list[dict] = []
    for n in g.nodes_of_class("E13"):
        ed = {e.predicate: e.object_id for e in g.out_edges(n.id)}
        if ed.get(P177) != _SAME_TYPE:
            continue  # not a same_entity_as claim (e.g. a verdict-E13)
        subject, obj = ed.get(P140), ed.get(P141)
        if subject is None or obj is None:
            continue
        rec: dict = {"claim": n.id, "subject": subject, "object": obj,
                     "outcome": None, "reasoning": None}
        if DERIVED_BY_RUN in ed:  # matcher-derived → outcome via verdict tip
            tip = tip_verdict(g, n.id)
            if tip is not None:
                rec["outcome"] = verdict_outcome(g, tip)
                rec["reasoning"] = g.node(tip).props.get("reasoning")
        elif P14 in ed:  # documentary intra-source assertion → source-attested
            rec["outcome"] = VERDICT_APPROVED
        out.append(rec)
    return out


def write_same_entity_edges(g: ClaimGraph, path: str | Path) -> int:
    records = dump_same_entity_edges(g)
    Path(path).write_text(json.dumps(records, indent=2, ensure_ascii=False))
    return len(records)


def load_same_entity_edges(
    g: ClaimGraph, records: list[dict], *, approved_only: bool = True
) -> int:
    """Re-add same_entity_as edges from persisted records (disk evaluation)."""
    n = 0
    for r in records:
        if approved_only and r.get("outcome") != VERDICT_APPROVED:
            continue
        g.node(r["subject"]); g.node(r["object"])  # fail loud on dangling refs
        g.add_edge(Edge(r["subject"], SAME_ENTITY_AS, r["object"]))
        n += 1
    return n
