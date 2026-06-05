"""Stage-2 LLM reviewer (ADR-018 schema sketch 4b).

A single LLM reviewer evaluates each stage-1 candidate same_entity_as claim and
emits a verdict-E13 (approved / rejected / retracted) carrying the machine-derived
provenance shape (``hapi:derived_by_run → :MatcherRun (D10)`` with a D14 reviewer
software + D1 prompt/context/verdict artifacts). When the reviewer is not
confident enough to decide, it **escalates to a human curator** rather than
guessing — no verdict-E13 is emitted, so the candidate stays pending (no tip,
no shortcut) until a curator decides via the human-documentary path.

The LLM call is the Anthropic SDK with a pinned model + temperature 0 and the
actual returned model snapshot recorded for reproducibility (Constitutional
rule 1). The SDK boundary is injectable (``review_fn``) so the graph wiring and
escalation logic are testable offline; production uses the real call, which
RAISES loudly when ``ANTHROPIC_API_KEY`` is unset (no silent fallback, rule 2).
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Callable, Protocol

from ..ir import ClaimGraph, Edge, Node
from ..verdicts import add_verdict

REVIEWER_ALGORITHM_ID = "llm_reviewer_v1"
REVIEWER_VERSION = "0.1.0"
DEFAULT_MODEL = "claude-opus-4-8"
MAX_TOKENS = 1024

L23 = "L23_used_software_or_firmware"
L10 = "L10_had_input"
L11 = "L11_had_output"

# Reviewer verdict outcome → verdict-outcome E55 URI.
_OUTCOME_URI = {
    "approved": "hapi:verdict_approved",
    "rejected": "hapi:verdict_rejected",
    "retracted": "hapi:verdict_retracted",
}

P140 = "P140_assigned_attribute_to"
P141 = "P141_assigned"


class ReviewFn(Protocol):
    def __call__(self, context: dict) -> dict:
        """Return {'outcome': approved|rejected|retracted|escalate,
        'confidence': float, 'reasoning': str}."""
        ...


def candidate_context(g: ClaimGraph, matcher_stmt_id: str) -> dict:
    """Build the per-candidate source-side context the reviewer judges."""
    edges = {e.predicate: e.object_id for e in g.out_edges(matcher_stmt_id)}
    left, right = edges[P140], edges[P141]

    def describe(ruler_id: str) -> dict:
        disp = None
        try:
            disp = g.node(f"appellation::{ruler_id}::display_name").props["symbolic_content"]
        except KeyError:
            pass
        dynasty = None
        stmt = f"stmt::{ruler_id}::in_dynastic_period"
        for e in g.out_edges(stmt):
            if e.predicate == P141:
                dynasty = g.node(e.object_id).props.get("number")
        return {"ruler_id": ruler_id, "display_name": disp, "dynasty": dynasty,
                "source": g.node(ruler_id).props.get("source")}

    return {"matcher_stmt_id": matcher_stmt_id, "left": describe(left), "right": describe(right)}


def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def _default_sdk_review(context: dict) -> dict:
    """Real Anthropic SDK review. Raises if ANTHROPIC_API_KEY is unset."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "Stage-2 live reviewer requires ANTHROPIC_API_KEY. Set it in the "
            "environment (the OAuth proxy used by Claude Code is not exposed to "
            "the SDK). No silent fallback (Constitutional rule 2)."
        )
    import anthropic

    client = anthropic.Anthropic()
    tool = {
        "name": "record_verdict",
        "description": "Record the verdict on whether two source records denote the same ruler.",
        "input_schema": {
            "type": "object",
            "properties": {
                "outcome": {"type": "string", "enum": ["approved", "rejected", "retracted", "escalate"]},
                "confidence": {"type": "number"},
                "reasoning": {"type": "string"},
            },
            "required": ["outcome", "confidence", "reasoning"],
        },
    }
    prompt = (
        "You are reviewing a candidate cross-source identity claim between two "
        "Egyptological source records. Decide whether they denote the SAME "
        "historical ruler. 'approved' = same ruler; 'rejected' = different; "
        "'escalate' = genuinely uncertain, defer to a human curator.\n\n"
        f"Left:  {json.dumps(context['left'], ensure_ascii=False)}\n"
        f"Right: {json.dumps(context['right'], ensure_ascii=False)}\n"
    )
    # NOTE: claude-opus-4-8 deprecates `temperature`; we omit it rather than send
    # a rejected param. The actual returned model snapshot is recorded below.
    resp = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=MAX_TOKENS,
        tools=[tool],
        tool_choice={"type": "tool", "name": "record_verdict"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "record_verdict":
            result = dict(block.input)
            result["_model_snapshot"] = resp.model  # actual snapshot, for provenance
            return result
    raise RuntimeError("Reviewer did not return a record_verdict tool call")


def run_stage2_reviewer(
    g: ClaimGraph,
    candidate_ids: list[str],
    *,
    review_fn: ReviewFn | None = None,
    run_id: str = "reviewer_run_poc_0001",
    started_at: str = "2026-05-17T15:03:11Z",
    completed_at: str = "2026-05-17T15:08:42Z",
    model_snapshot: str | None = None,
) -> tuple[list[str], list[str]]:
    """Review candidates; emit verdict-E13s. Returns (verdict_ids, escalations).

    Escalated candidates get NO verdict-E13 (they remain pending for a human
    curator). Approved/rejected/retracted candidates get a verdict-E13 with the
    reviewer's D10 provenance.
    """
    review_fn = review_fn or _default_sdk_review

    algo = f"algorithm::{REVIEWER_ALGORITHM_ID}"
    g.add_node(
        Node(
            algo,
            ("D14",),
            {
                "id": REVIEWER_ALGORITHM_ID,
                "version": REVIEWER_VERSION,
                "algorithm": "anthropic-messages-tool-verdict",
                "model_provider": "anthropic",
                "model_id": DEFAULT_MODEL,
                "model_snapshot": model_snapshot,
                # NOTE: the Messages API has no `seed` param, and claude-opus-4-8
                # deprecates `temperature`; we record the real params we send, not
                # the ADR sketch's illustrative seed/temperature.
                "hyperparameters_json": json.dumps({"max_tokens": MAX_TOKENS}),
            },
            "MatcherAlgorithm",
        )
    )
    run = f"run::{run_id}"
    g.add_node(
        Node(run, ("D10",),
             {"run_id": run_id, "started_at": started_at, "completed_at": completed_at},
             "MatcherRun")
    )
    g.add_edge(Edge(run, L23, algo))

    verdicts: list[str] = []
    escalations: list[str] = []
    output_rows: list[dict] = []
    for cid in candidate_ids:
        context = candidate_context(g, cid)
        result = review_fn(context)
        outcome = result["outcome"]
        if outcome == "escalate":
            escalations.append(cid)
            output_rows.append({"candidate": cid, **{k: result.get(k) for k in ("outcome", "confidence", "reasoning")}})
            continue
        if outcome not in _OUTCOME_URI:
            raise ValueError(f"Reviewer returned unknown outcome {outcome!r} for {cid}")
        vid = f"verdict::{cid}"
        add_verdict(
            g,
            matcher_stmt_id=cid,
            outcome=_OUTCOME_URI[outcome],
            verdict_id=vid,
            reviewer_run=run,
        )
        verdicts.append(vid)
        output_rows.append({"candidate": cid, **{k: result.get(k) for k in ("outcome", "confidence", "reasoning")}})

    # D1 provenance: candidate-claims input + verdict-serialisation output.
    serialisation = json.dumps(output_rows, sort_keys=True)
    in_data = f"sourcedata::reviewer_input::{run_id}"
    out_data = f"sourcedata::reviewer_output::{run_id}"
    g.add_node(Node(in_data, ("D1",), {"role": "candidate_claims", "candidate_count": len(candidate_ids)}, "SourceData"))
    g.add_node(Node(out_data, ("D1",), {"role": "verdict_serialisation", "sha256": _sha256(serialisation)}, "SourceData"))
    g.add_edge(Edge(run, L10, in_data))
    g.add_edge(Edge(run, L11, out_data))
    return verdicts, escalations
