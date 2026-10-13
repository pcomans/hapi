"""Audit of the claim graph's escalation queue: why each same-entity candidate was parked,
what evidence the pair carries, and which museum mentions each parked pair leaves ambiguous.

Deterministic, no model call. The candidates and the uniqueness-clash groups are recomputed
with the committed matcher from the committed sources and must equal the committed graph's
escalations exactly; the museum-side impact comes from the #337 ruler resolver run over the
frozen #337 mention ledger against the committed graph. Output is aggregate: authority pairs
(public sources) and mention counts, never museum rows.

    pipeline/.venv/bin/python docs/evaluations/ruler-escalation-queue/scripts/audit_escalations.py \\
      --ledger <dir>/mentions.ndjson.gz --extraction-manifest <dir>/extraction-manifest.json \\
      --graph web-claimgraph/data/claim-graph.json \\
      --out docs/evaluations/ruler-escalation-queue/results/escalation-queue.json
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "pipeline"))

from pipeline.authority.claimgraph.build_graph import AUTHORITY_ROOT  # noqa: E402
from pipeline.authority.claimgraph.matcher import (  # noqa: E402
    _shared_dynasty_reliable,
    clash_groups,
    generate_candidates,
    regnal_number_of,
    same_person_groups,
    uniqueness_clashes,
)
from pipeline.authority.claimgraph.sources import load_all_sources  # noqa: E402

CONTROL = ROOT / "docs/evaluations/authority-independent-control-2026-09-13/scripts/compare_arms.py"
LINKABILITY = ROOT / "docs/evaluations/hapi-linkability-mvp-2026-08-28/scripts/run_linkability.py"
MATCHER = ROOT / "pipeline/pipeline/authority/claimgraph/matcher.py"

OVERRIDE = re.compile(
    r"\[overridden to escalate: (?P<why>uniqueness clash|shared prenomen|king-name route|a record "
    r"carries a name its source marks as an uncertain reading)"
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def park_reason(escalation: dict) -> str:
    """Why the pair is parked, from the committed verdict.

    `name_only`: no throne or Horus name in common, escalated by policy and never reviewed.
    `uniqueness_clash` / `homonym_list`: the reviewer approved, a code guard overrode it.
    `king_name_route`: the reviewer approved a record without titulary by its name; the
    windows or regnal numbers do not corroborate it and a code guard overrode it.
    `uncertain_reading`: the reviewer rejected on a name its source marks uncertain; a code
    guard overrode it. `reviewer_escalated`: the reviewer itself declined to approve."""
    if escalation["basis"] == "name_only":
        return "name_only"
    override = OVERRIDE.search(escalation["reason"])
    if override is None:
        return "reviewer_escalated"
    return {
        "uniqueness clash": "uniqueness_clash",
        "shared prenomen": "homonym_list",
        "king-name route": "king_name_route",
        "a record carries a name its source marks as an uncertain reading": "uncertain_reading",
    }[override["why"]]


def evidence(a, b) -> dict:
    oa, ob = regnal_number_of(a.display_name), regnal_number_of(b.display_name)
    same_dynasty = a.dynasty is not None and a.dynasty == b.dynasty
    return {
        "dynasty": [a.dynasty, b.dynasty],
        "same_dynasty": same_dynasty,
        "same_dynasty_reliable": same_dynasty and _shared_dynasty_reliable(a.dynasty),
        "ordinal": [oa, ob],
        "ordinal_relation": (
            "both_absent" if oa is None and ob is None
            else "one_absent" if oa is None or ob is None
            else "same" if oa == ob else "different"
        ),
        "reign_start_bce": [a.reign_start_bce, b.reign_start_bce],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", type=Path, required=True)
    ap.add_argument("--extraction-manifest", type=Path, required=True)
    ap.add_argument("--graph", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    graph = json.loads(args.graph.read_text("utf-8"))
    load = load_all_sources(AUTHORITY_ROOT)
    records = {r.local_id: r for r in load.records}
    person_of = same_person_groups(load.records)
    candidates = {c.id: c for c in generate_candidates(load.records)}
    forced = uniqueness_clashes(list(candidates.values()), person_of)

    escalations = graph["escalations"]
    unknown = [e["candidate_id"] for e in escalations if e["candidate_id"] not in candidates]
    if unknown:
        raise ValueError(f"committed escalations the current matcher does not generate: {unknown[:5]}")

    # The competing pairs behind each clash: for a forced candidate, every other approvable
    # candidate sharing one of its records' persons against the same other source.
    groups = clash_groups(list(candidates.values()), person_of)

    def rivals(c) -> list[str]:
        found = set()
        for key in (f"{person_of[c.a_id]}|{c.b_source}", f"{person_of[c.b_id]}|{c.a_source}"):
            for other in groups.get(key, []):
                if other.id != c.id:
                    found.add(f"{other.a_id} ({other.a_name}) ~ {other.b_id} ({other.b_name}) "
                              f"via {', '.join(other.shared_prenomen_keys) or other.basis}")
        return sorted(found)

    rows = {}
    for e in escalations:
        c = candidates[e["candidate_id"]]
        reason = park_reason(e)
        if reason == "uniqueness_clash" and c.id not in forced:
            raise ValueError(f"{c.id}: committed as a clash, not a clash under the current matcher")
        row = {
            "a": f"{c.a_id} ({c.a_name})",
            "b": f"{c.b_id} ({c.b_name})",
            "park_reason": reason,
            "shared_prenomen_keys": c.shared_prenomen_keys,
            "shared_name_keys": c.shared_name_keys,
            **evidence(records[c.a_id], records[c.b_id]),
        }
        if reason == "uniqueness_clash":
            row["rival_pairs"] = rivals(c)
        if reason == "homonym_list":
            row["homonym_key"] = c.homonym_trap
        rows[c.id] = row

    # Museum-side impact: every ambiguous ruler mention, by its candidate target set, with
    # the parked pairs that keep those targets apart.
    os.environ["HAPI_ROOT"] = str(ROOT)
    compare = _load("_esc_compare_arms", CONTROL)
    linkability = _load("_esc_run_linkability", LINKABILITY)
    manifest = json.loads(args.extraction_manifest.read_text("utf-8"))
    ledger, ledger_proof = compare.read_ledger(args.ledger, manifest)
    rulers = [m for m in ledger if m["entity_type"] == "ruler"]
    resolver, _ = linkability.build_ruler_resolver(graph)
    resolved = compare.resolve_mentions(
        rulers, "current_authority", {"ruler": (resolver, linkability.ruler_norm)}
    )
    members = {c["id"]: c["member_ids"] for c in graph["clusters"]}
    by_pair: dict[frozenset, list[str]] = collections.defaultdict(list)
    for cid, row in rows.items():
        c = candidates[cid]
        by_pair[frozenset((c.a_id, c.b_id))].append(cid)

    target_sets = collections.defaultdict(lambda: {"mentions": 0, "artifacts": set()})
    for m in resolved:
        if m["status"] == "ambiguous":
            entry = target_sets[tuple(sorted(m["target_ids"]))]
            entry["mentions"] += 1
            entry["artifacts"].add((m["museum"], m["artifact_id"]))
    ambiguous_sets = []
    blocked = collections.Counter()
    for targets, entry in sorted(target_sets.items(), key=lambda kv: -kv[1]["mentions"]):
        units = [members.get(t, [t]) for t in targets]
        parked = sorted({
            cid
            for i in range(len(units)) for j in range(i + 1, len(units))
            for x in units[i] for y in units[j]
            for cid in by_pair.get(frozenset((x, y)), [])
        })
        for cid in parked:
            blocked[cid] += entry["mentions"]
        ambiguous_sets.append({
            "targets": list(targets),
            "labels": [records[u[0]].display_name for u in units],
            "mentions": entry["mentions"],
            "artifacts": len(entry["artifacts"]),
            "parked_pairs_between_targets": [
                {"candidate": cid, "park_reason": rows[cid]["park_reason"]} for cid in parked
            ],
        })
    for cid, row in rows.items():
        row["ambiguous_mentions_between_its_targets"] = blocked.get(cid, 0)

    reasons = collections.Counter(r["park_reason"] for r in rows.values())
    ordinal_by_reason = collections.defaultdict(collections.Counter)
    for r in rows.values():
        key = (r["ordinal_relation"] + ("+same_dynasty" if r["same_dynasty"] else ""))
        ordinal_by_reason[r["park_reason"]][key] += 1
    result = {
        "schema_version": "hapi-ruler-escalation-queue/1",
        "inputs": {
            "graph_sha256": _sha256(args.graph),
            "matcher_sha256": _sha256(MATCHER),
            "mention_ledger": ledger_proof,
            "resolver_sha256": _sha256(LINKABILITY),
            "control_sha256": _sha256(CONTROL),
            "script_sha256": _sha256(Path(__file__)),
        },
        "escalations": len(rows),
        "by_park_reason": dict(sorted(reasons.items())),
        "evidence_by_park_reason": {k: dict(sorted(v.items())) for k, v in sorted(ordinal_by_reason.items())},
        "ruler_mentions": len(rulers),
        "ambiguous_mentions": sum(s["mentions"] for s in ambiguous_sets),
        "ambiguous_target_sets": ambiguous_sets,
        "pairs": dict(sorted(rows.items())),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True) + "\n", "utf-8")
    print(json.dumps({k: result[k] for k in ("escalations", "by_park_reason", "evidence_by_park_reason",
                                             "ruler_mentions", "ambiguous_mentions")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
