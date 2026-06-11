"""Stage-1 deterministic matcher — ``normalized_name_v1`` (ADR-018 schema 4a).

A pure, replayable matcher (NOT an LLM): it proposes candidate cross-source
``hapi:same_entity_as`` claims by normalising display names (lowercase + strip
diacritics + strip punctuation) and requiring token-set equality within the same
dynasty (``min_dynasty_match``). Every candidate E13 carries the machine-derived
provenance shape — ``hapi:derived_by_run → :MatcherRun (D10)`` — and the D10
references its algorithm (D14) and input/output data (D1) via CRMdig L23/L10/L11.

Determinism is the whole point: a candidate's confidence is reproducible by
replaying this D10 against its L10 inputs with the recorded parameters. No P14,
no P70i (matcher provenance is algorithmic, not documentary).
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass

from ..ir import ClaimGraph, Edge, Node

ALGORITHM_ID = "normalized_name_v1"
ALGORITHM_VERSION = "0.1.0"
HYPERPARAMETERS = {"min_dynasty_match": True}

# CRMdig provenance property local names.
DERIVED_BY_RUN = "hapi:derived_by_run"
L23 = "L23_used_software_or_firmware"
L10 = "L10_had_input"
L11 = "L11_had_output"

# Spine.
P140 = "P140_assigned_attribute_to"
P141 = "P141_assigned"
P177 = "P177_assigned_property_of_type"


def normalize_name(name: str) -> frozenset[str]:
    """lowercase + strip diacritics + strip punctuation → token set."""
    decomposed = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    cleaned = "".join(c if c.isalnum() or c.isspace() else " " for c in stripped.lower())
    return frozenset(t for t in cleaned.split() if t)


@dataclass(frozen=True)
class _Entity:
    node_id: str
    tokens: frozenset[str]
    dynasty: int | None


def _entities_for_source(g: ClaimGraph, source: str) -> list[_Entity]:
    """Collect (ruler, normalized display tokens, dynasty) for one source."""
    out: list[_Entity] = []
    for ruler in g.nodes_of_class("E21"):
        if ruler.props.get("source") != source:
            continue
        # display_name appellation via this ruler's display_name statement.
        appel_id = f"appellation::{ruler.id}::display_name"
        try:
            appel = g.node(appel_id)
        except KeyError:
            continue
        # dynasty via the ruler's in_dynastic_period statement value.
        dynasty = None
        stmt = f"stmt::{ruler.id}::in_dynastic_period"
        for e in g.out_edges(stmt):
            if e.predicate == P141:
                dynasty = g.node(e.object_id).props.get("number")
        out.append(_Entity(ruler.id, normalize_name(appel.props["symbolic_content"]), dynasty))
    return out


def _parameters_hash() -> str:
    payload = json.dumps(
        {"algorithm": ALGORITHM_ID, "version": ALGORITHM_VERSION, "hyperparameters": HYPERPARAMETERS},
        sort_keys=True,
    )
    return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


def run_stage1_matcher(
    g: ClaimGraph,
    *,
    left_source: str = "leprohon",
    right_source: str = "beckerath",
    run_id: str = "matcher_run_poc_0001",
    started_at: str = "2026-05-17T14:22:31Z",
    completed_at: str = "2026-05-17T14:24:08Z",
    input_dataset_commit: str = "poc",
) -> list[str]:
    """Emit candidate same_entity_as E13s into ``g``; return their statement ids.

    Idempotent: re-running with the same ``run_id`` rebuilds identical nodes/edges
    (the IR's add_node raises only on a *conflicting* redefinition).
    """
    # Provenance catalogue: D14 algorithm, D10 run, D1 inputs/outputs.
    algo = f"algorithm::{ALGORITHM_ID}"
    g.add_node(
        Node(
            algo,
            ("D14",),
            {
                "id": ALGORITHM_ID,
                "version": ALGORITHM_VERSION,
                "algorithm": "lowercase+strip_diacritics+token_match",
                "hyperparameters_json": json.dumps(HYPERPARAMETERS, sort_keys=True),
            },
            "MatcherAlgorithm",
        )
    )
    run = f"run::{run_id}"
    g.add_node(
        Node(
            run,
            ("D10",),
            {
                "run_id": run_id,
                "input_dataset_commit": input_dataset_commit,
                "parameters_hash": _parameters_hash(),
                "started_at": started_at,
                "completed_at": completed_at,
            },
            "MatcherRun",
        )
    )
    in_left = f"sourcedata::{left_source}::reconciled"
    in_right = f"sourcedata::{right_source}::reconciled"
    out_data = f"sourcedata::matcher_output::{run_id}"
    g.add_node(Node(in_left, ("D1",), {"path": f"{left_source}/reconciled.jsonl"}, "SourceData"))
    g.add_node(Node(in_right, ("D1",), {"path": f"{right_source}/reconciled.jsonl"}, "SourceData"))
    g.add_node(Node(out_data, ("D1",), {"path": f"matcher_outputs/{run_id}.jsonl"}, "SourceData"))
    g.add_edge(Edge(run, L23, algo))
    g.add_edge(Edge(run, L10, in_left))
    g.add_edge(Edge(run, L10, in_right))
    g.add_edge(Edge(run, L11, out_data))

    # The same_entity_as predicate-type :E55 Type node (primary P177 target).
    same_type = "type::hapi:same_entity_as"
    g.add_node(Node(same_type, ("E55",), {"id": "hapi:same_entity_as"}, "Type"))

    left = _entities_for_source(g, left_source)
    right = _entities_for_source(g, right_source)
    # Index right side by token set for O(n) candidate generation.
    right_by_tokens: dict[frozenset[str], list[_Entity]] = {}
    for r in right:
        right_by_tokens.setdefault(r.tokens, []).append(r)

    candidates: list[str] = []
    for le in left:
        for re_ in right_by_tokens.get(le.tokens, []):
            if HYPERPARAMETERS["min_dynasty_match"] and le.dynasty != re_.dynasty:
                continue
            stmt_id = f"stmt::match::{le.node_id}::{re_.node_id}"
            g.add_node(Node(stmt_id, ("E13",), {"confidence": 1.0}, "Statement"))
            g.add_edge(Edge(stmt_id, P140, le.node_id))
            g.add_edge(Edge(stmt_id, P141, re_.node_id))
            g.add_edge(Edge(stmt_id, P177, same_type))
            g.add_edge(Edge(stmt_id, DERIVED_BY_RUN, run))
            candidates.append(stmt_id)
    return candidates
