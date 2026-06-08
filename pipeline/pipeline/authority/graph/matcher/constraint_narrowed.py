"""Constraint-narrowed candidate generation + match (ADR-018 § Implications for matching).

ADR-009 forbids surface-string acceptance (edit distance / token overlap) because
those metrics are ANTI-correlated with identity for Egyptian royal names: the
regnal numeral discriminates identity but is a tiny surface difference (Thutmose
III vs IV), while the stem transliteration preserves identity but varies wildly
(Thutmose/Tuthmosis, Amenhotep/Amenophis). So this module does NOT score names.

Instead it follows ADR-018: constraint-narrow the candidate set via STRUCTURED
graph facts (here, shared dynasty — the only structured signal both sources
carry; Leprohon dates no reigns), then have the LLM reviewer "match the name
against the narrowed set" — one pick per left ruler over its same-dynasty
candidate set. The deterministic narrowing emits candidate same_entity_as E13s;
the LLM pick is the stage-2 review that approves exactly one (or none) per left
ruler. No surface-string metric is ever used to ACCEPT a match.
"""

from __future__ import annotations

import json
import os
import random
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from ..ir import ClaimGraph, Edge, Node
from ..verdicts import VERDICT_APPROVED, add_verdict

# Raw reconciled rows are legitimate matcher INPUT (ADR-018 L10_had_input): the
# matcher may read source fields (throne name / prenomen, name variants) to
# ground its decision, even though only the OUTPUT same_entity_as claim is stored.
_SOURCES_DIR = Path(__file__).resolve().parents[2] / "sources"
_SOURCE_FILES = {
    "leprohon": ("leprohon-2013-titulary", "leprohon_id"),
    "beckerath": ("beckerath-1997-chronologie", "beckerath_id"),
    "kitchen": ("kitchen-tipe", "kitchen_id"),
}

GEN_ALGORITHM_ID = "constraint_narrowed_v1"
PICK_ALGORITHM_ID = "llm_pick_from_narrowed_v1"
DEFAULT_MODEL = "claude-opus-4-8"
MAX_TOKENS = 1024

P140 = "P140_assigned_attribute_to"
P141 = "P141_assigned"
P177 = "P177_assigned_property_of_type"
DERIVED_BY_RUN = "hapi:derived_by_run"
L23 = "L23_used_software_or_firmware"


def _dynasty_of(g: ClaimGraph, ruler_id: str) -> int | None:
    for e in g.out_edges(f"stmt::{ruler_id}::in_dynastic_period"):
        if e.predicate == P141:
            return g.node(e.object_id).props.get("number")
    return None


@lru_cache(maxsize=1)
def _raw_index() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for src, (folder, idfield) in _SOURCE_FILES.items():
        path = _SOURCES_DIR / folder / "reconciled.jsonl"
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                out[f"{src}::{row[idfield]}"] = row
    return out


def _extra_names(source: str, row: dict) -> tuple[list[str], list[str]]:
    """(throne-name/prenomen candidates, name variants) from a raw source row."""
    pren: list[str] = []
    variants: list[str] = []
    if source == "beckerath":
        if row.get("prenomen"):
            pren.append(row["prenomen"])
        variants = list(row.get("name_variants") or [])
    elif source == "kitchen":
        if row.get("prenomen"):
            pren.append(row["prenomen"])
        pren += [p for p in (row.get("prenomens") or []) if p]
    elif source == "leprohon":
        for t in row.get("throne_names") or []:
            v = t.get("anglicised") or t.get("transliteration")
            if v:
                pren.append(v)
        variants = list(row.get("alt_display_names") or [])
    return pren[:3], variants[:3]


def rich_describe(g: ClaimGraph, ruler_id: str) -> dict:
    """Full structured record for the LLM (ADR-020 §6: not the name alone)."""
    node = g.node(ruler_id)
    d: dict = {"ruler_id": ruler_id, "display_name": _display(g, ruler_id),
               "dynasty": _dynasty_of(g, ruler_id), "source": node.props.get("source")}
    try:
        ts = g.node(f"timespan::{ruler_id}::reign")
        d["reign_bce"] = [ts.props.get("begin_of_the_begin"), ts.props.get("end_of_the_end")]
    except KeyError:
        pass
    row = _raw_index().get(f"{node.props.get('source')}::{node.props.get('source_id')}")
    if row:
        pren, variants = _extra_names(node.props.get("source"), row)
        if pren:
            d["throne_name"] = pren
        if variants:
            d["name_variants"] = variants
    return d


def _display(g: ClaimGraph, ruler_id: str) -> str | None:
    try:
        return g.node(f"appellation::{ruler_id}::display_name").props["symbolic_content"]
    except KeyError:
        return None


def narrowed_sets(
    g: ClaimGraph, *, left: str = "leprohon", right: str = "beckerath", dynasty: int | None = None
) -> dict[str, list[str]]:
    """Deterministic structured narrowing: left ruler → same-dynasty right rulers.

    No name scoring — pure graph-constraint narrowing (shared dynasty).
    """
    right_by_dyn: dict[int | None, list[str]] = defaultdict(list)
    for n in g.nodes_of_class("E21"):
        if n.props.get("source") == right:
            right_by_dyn[_dynasty_of(g, n.id)].append(n.id)
    out: dict[str, list[str]] = {}
    for n in g.nodes_of_class("E21"):
        if n.props.get("source") != left:
            continue
        d = _dynasty_of(g, n.id)
        if dynasty is not None and d != dynasty:
            continue
        if d is None:
            continue
        out[n.id] = list(right_by_dyn.get(d, []))
    return out


def _ensure_gen_provenance(g: ClaimGraph, run_id: str) -> str:
    algo = f"algorithm::{GEN_ALGORITHM_ID}"
    g.add_node(Node(algo, ("D14",), {"id": GEN_ALGORITHM_ID, "algorithm": "same_dynasty_narrowing"}, "MatcherAlgorithm"))
    run = f"run::{run_id}"
    g.add_node(Node(run, ("D10",), {"run_id": run_id}, "MatcherRun"))
    g.add_edge(Edge(run, L23, algo))
    return run


def generate_candidates(
    g: ClaimGraph,
    narrowed: dict[str, list[str]],
    *,
    run_id: str = "cn_gen_poc_0001",
) -> dict[str, list[str]]:
    """Emit candidate same_entity_as E13s for every narrowed (left,right) pair.

    Returns {left_id: [candidate_stmt_id, ...]}. Deterministic, no LLM.
    """
    run = _ensure_gen_provenance(g, run_id)
    same_type = "type::hapi:same_entity_as"
    g.add_node(Node(same_type, ("E55",), {"id": "hapi:same_entity_as"}, "Type"))
    out: dict[str, list[str]] = defaultdict(list)
    for left_id, rights in narrowed.items():
        for right_id in rights:
            stmt = f"stmt::cn::{left_id}::{right_id}"
            g.add_node(Node(stmt, ("E13",), {}, "Statement"))
            g.add_edge(Edge(stmt, P140, left_id))
            g.add_edge(Edge(stmt, P141, right_id))
            g.add_edge(Edge(stmt, P177, same_type))
            g.add_edge(Edge(stmt, DERIVED_BY_RUN, run))
            out[left_id].append(stmt)
    return dict(out)


def _opaque_view(left: dict, rights: list[dict]) -> tuple[dict, list[dict], dict[str, str]]:
    """Strip answer-leaking info before the prompt.

    - Removes ``ruler_id`` from everything shown to the model: the source ids
      encode the cross-source dynasty.sequence alignment (e.g. both carry
      "18.09"), which is an answer leak.
    - Gives candidates opaque labels (C1, C2, …) in a DETERMINISTICALLY SHUFFLED
      order, so neither the id nor the position hints the match.
    Returns (target_view, candidate_view, label→ruler_id map).
    """
    rng = random.Random(str(left.get("ruler_id", "")))
    shuffled = list(rights)
    rng.shuffle(shuffled)
    label_to_id: dict[str, str] = {}
    cand_view: list[dict] = []
    for i, r in enumerate(shuffled, 1):
        label = f"C{i}"
        label_to_id[label] = r.get("ruler_id")
        cand_view.append({"label": label, **{k: v for k, v in r.items() if k != "ruler_id"}})
    target_view = {k: v for k, v in left.items() if k != "ruler_id"}
    return target_view, cand_view, label_to_id


def _default_pick(left: dict, rights: list[dict]) -> dict:
    """LLM pick: choose the candidate that is the SAME as the target, none, or escalate.

    The prompt never contains source ids or named answer pairs (no leakage).
    Requires ANTHROPIC_API_KEY. Returns
    {'choice': ruler_id|None, 'escalate': bool, 'reasoning': str}.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("constraint-narrowed pick requires ANTHROPIC_API_KEY")
    import anthropic

    target_view, cand_view, label_to_id = _opaque_view(left, rights)
    client = anthropic.Anthropic()
    tool = {
        "name": "pick_match",
        "description": "Pick which candidate denotes the SAME historical ruler as the target, none, or escalate.",
        "input_schema": {
            "type": "object",
            "properties": {
                "choice": {"type": ["string", "null"],
                           "description": "the label (C1, C2, …) of the matching candidate, or null"},
                "escalate": {"type": "boolean",
                             "description": "true if the identity is genuinely contested in scholarship and "
                             "should go to a human curator instead of an automatic pick; set choice=null"},
                "reasoning": {"type": "string"},
            },
            "required": ["choice", "escalate", "reasoning"],
        },
    }
    prompt = (
        "All candidates are in the same Egyptian dynasty as the target. Pick, by its label, the ONE "
        "candidate that denotes the SAME historical ruler as the target. The same ruler is often "
        "written very differently across sources — different transliteration conventions, different "
        "national spelling traditions, and Greek/Manetho forms vs Egyptian forms — so do NOT rely on "
        "string similarity of the display names. Decide from the structured evidence: throne "
        "name/prenomen (the strongest identity discriminator), reign dates (reign_bce), and dynasty. "
        "PRECISION-FIRST — a missing merge is FAR better than a false one. **Default to escalate=true "
        "with choice=null (\"I don't know\") UNLESS you are ~99% certain the candidate is the same "
        "ruler, or the evidence is overwhelming.** Use choice=null only when a candidate is clearly a "
        "DIFFERENT ruler; use escalate=true when you are merely unsure. Do NOT match on regnal number "
        "alone — III vs IV are different kings. Keep `reasoning` under 256 characters.\n\n"
        f"Target: {json.dumps(target_view, ensure_ascii=False)}\n"
        f"Candidates: {json.dumps(cand_view, ensure_ascii=False)}\n"
    )
    resp = client.messages.create(
        model=DEFAULT_MODEL, max_tokens=MAX_TOKENS, tools=[tool],
        tool_choice={"type": "tool", "name": "pick_match"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "pick_match":
            r = dict(block.input)
            r["choice"] = label_to_id.get(r.get("choice"))  # map label → ruler_id (None if null)
            r["_model_snapshot"] = resp.model
            return r
    raise RuntimeError("pick_match returned no tool call")


def review_narrowed(
    g: ClaimGraph,
    candidate_map: dict[str, list[str]],
    *,
    pick_fn=None,
    run_id: str = "cn_review_poc_0001",
    rich_context: bool = False,
) -> tuple[list[tuple[str, str]], list[str]]:
    """Per left ruler, LLM-pick the matching candidate from its narrowed set and
    approve that candidate's verdict. A genuinely-contested identity is ESCALATED
    to a human (no verdict emitted). Returns (matches, escalated_left_ids).

    ``rich_context`` passes the full structured record (dynasty, reign, throne
    name, variants, source) to the pick instead of the display name alone
    (ADR-020 §6).
    """
    pick_fn = pick_fn or _default_pick
    describe = (lambda rid: rich_describe(g, rid)) if rich_context else (
        lambda rid: {"ruler_id": rid, "display_name": _display(g, rid)}
    )
    algo = f"algorithm::{PICK_ALGORITHM_ID}"
    g.add_node(Node(algo, ("D14",), {"id": PICK_ALGORITHM_ID, "model_id": DEFAULT_MODEL}, "MatcherAlgorithm"))
    run = f"run::{run_id}"
    g.add_node(Node(run, ("D10",), {"run_id": run_id}, "MatcherRun"))
    g.add_edge(Edge(run, L23, algo))

    matches: list[tuple[str, str]] = []
    escalations: list[str] = []
    for left_id, cand_stmts in candidate_map.items():
        def _right_of(stmt_id: str) -> str:
            for e in g.out_edges(stmt_id):
                if e.predicate == P141:
                    return e.object_id
            raise ValueError(f"candidate {stmt_id} has no P141 value")
        right_ctx = []
        seen: set[str] = set()
        for s in cand_stmts:
            rid = _right_of(s)
            if rid not in seen:
                seen.add(rid)
                right_ctx.append(describe(rid))
        if not right_ctx:
            continue
        left_ctx = describe(left_id)
        result = pick_fn(left_ctx, right_ctx)
        if result.get("escalate"):
            escalations.append(left_id)  # contested → human queue, no verdict
            continue
        choice = result.get("choice")
        if not choice:
            continue
        stmt = f"stmt::cn::{left_id}::{choice}"
        add_verdict(
            g,
            matcher_stmt_id=stmt,
            outcome=VERDICT_APPROVED,
            verdict_id=f"verdict::{stmt}",
            reviewer_run=run,
            reasoning=result.get("reasoning"),
        )
        matches.append((left_id, choice))
    return matches, escalations
