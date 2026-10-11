"""The committed claim-graph artifacts and the #342 results agree with the code and with
the claims made about them (Rule 3: a claim in a README is enforced here, not trusted).

* `web-claimgraph/data/claim-graph.json` — documentary layer regenerable from the sources;
  no cluster joins two records one source keeps apart; every predicate is declared in the
  extension manifest.
* `web-claimgraph/data/claim-graph.reviewer-run.jsonl` — every LLM interaction was served
  by the pinned provider, carries reasoning, and the run used one model build.
* `docs/evaluations/ruler-cluster-reconciliation-342/results/` — pinned to these files.
"""

from __future__ import annotations

import collections
import hashlib
import importlib.util
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path

import pytest

from pipeline.authority.claimgraph.build_graph import AUTHORITY_ROOT, REPO_ROOT, WEB_DATA_DIR
from pipeline.authority.claimgraph.clusters import compute_clusters
from pipeline.authority.claimgraph.graph_ir import build_documentary_graph
from pipeline.authority.claimgraph.reviewer import (
    PROVIDER_PARAMETERS,
    VERCEL_PINNED_PROVIDER,
    VERDICT_ESCALATED,
    Verdict,
    _parse_verdict_json,
    request_digest,
)
from pipeline.authority.claimgraph.sources import load_all_sources
from pipeline.authority.claimgraph.verdicts import resolve_matches

GRAPH = WEB_DATA_DIR / "claim-graph.json"
RUN = WEB_DATA_DIR / "claim-graph.reviewer-run.jsonl"
MANIFEST = REPO_ROOT / "pipeline" / "pipeline" / "authority" / "hapi_extension.rdf"
EVAL = REPO_ROOT / "docs" / "evaluations" / "ruler-cluster-reconciliation-342"
RDF_ABOUT = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def graph() -> dict:
    return json.loads(GRAPH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def run() -> list[dict]:
    return [json.loads(line) for line in RUN.read_text(encoding="utf-8").splitlines()]


def test_committed_documentary_layer_is_what_the_sources_produce(graph):
    doc = build_documentary_graph(load_all_sources(AUTHORITY_ROOT).records)
    assert graph["rulers"] == [asdict(r) for r in doc.rulers]
    assert graph["claims"] == [asdict(c) for c in doc.claims]
    assert graph["intraSourceIdentities"] == [asdict(i) for i in doc.intra_source_identities]


def test_committed_decisions_follow_from_the_run_and_the_current_matcher(graph, run):
    """Replays the committed run offline: each LLM verdict is rebuilt from the model's own
    persisted answer and pushed through the CURRENT matcher and guards. The links,
    escalations and clusters must equal the committed graph, so a matcher change committed
    without a rebuild fails here instead of leaving a stale graph (and stale results pinned
    to it) behind a green CI."""
    by_candidate = {v["candidate_id"]: v for v in run}

    model = graph["meta"]["model"]

    def replay(candidate, a, b):
        verdict = by_candidate[candidate.id]
        assert verdict["reviewer"] == "llm", candidate.id
        # The request the run made is the request the current code would make: same records,
        # same prompts (the ones the Rule-14 audit covered), same model and parameters.
        assert verdict["request_digest"] == request_digest(
            candidate, a, b, provider="vercel", model=model,
            parameters=PROVIDER_PARAMETERS["vercel"],
        ), candidate.id
        last = verdict["interactions"][-1]
        if last["parse_error"]:
            # Every retry failed to parse: the code's own escalation path (constant reason).
            return Verdict(
                candidate_id=candidate.id, outcome=VERDICT_ESCALATED,
                reason="Reviewer output could not be parsed after retries; escalated for "
                "manual review.", reviewer="llm",
            )
        assert last["call_error"] is None, candidate.id
        outcome, reason = _parse_verdict_json(
            last["raw_response"]["choices"][0]["message"]["content"]
        )
        return Verdict(candidate_id=candidate.id, outcome=outcome, reason=reason, reviewer="llm")

    records = load_all_sources(AUTHORITY_ROOT).records
    replayed = resolve_matches(
        records, mode="llm", provider="vercel", model=graph["meta"]["model"],
        reviewer_fn=replay, max_workers=1, cache_path=None,
    )
    assert graph["meta"]["partial"] is False
    assert sorted(v.candidate_id for v in replayed.verdicts) == sorted(by_candidate)
    # The provenance file describes the decisions the code actually reaches.
    assert {v.candidate_id: (v.outcome, v.reason, v.reviewer) for v in replayed.verdicts} == {
        r["candidate_id"]: (r["outcome"], r["reason"], r["reviewer"]) for r in run
    }
    assert [asdict(e) for e in replayed.approved_edges] == graph["approvedEdges"]
    assert [asdict(e) for e in replayed.escalations] == graph["escalations"]
    doc = build_documentary_graph(records)
    clusters = compute_clusters(doc.rulers, replayed.approved_edges, doc.intra_source_identities)
    assert [asdict(c) for c in clusters] == graph["clusters"]


def test_every_claim_predicate_is_declared_in_the_extension_manifest(graph):
    declared = {
        "hapi:" + el.attrib[RDF_ABOUT][1:]
        for el in ET.parse(MANIFEST).getroot()
        if el.attrib.get(RDF_ABOUT, "").startswith("#")
    }
    used = {c["predicate"] for c in graph["claims"]}
    assert used - declared == set()
    assert used == {
        "hapi:display_name", "hapi:prenomen", "hapi:prenomen_epithet", "hapi:horus_name",
        "hapi:horus_name_epithet", "hapi:nomen", "hapi:nomen_epithet",
        "hapi:in_dynastic_period",
    }


def test_no_cluster_joins_records_their_source_keeps_apart(graph):
    """The Pinudjem I ↔ Menkheperre false-merge class (ADR-020 finding 1): two records of
    one source may share a cluster only when that source itself declares them one person."""
    source = {r["id"]: r["source_id"] for r in graph["rulers"]}
    declared = {(i["subject_id"], i["object_id"]) for i in graph["intraSourceIdentities"]}
    offenders = []
    for cluster in graph["clusters"]:
        by_source = collections.defaultdict(list)
        for member in cluster["member_ids"]:
            by_source[source[member]].append(member)
        for members in by_source.values():
            pairs = [(a, b) for a in members for b in members if a != b]
            if any(p not in declared for p in pairs):
                offenders.append((cluster["label"], members))
    assert offenders == []


def test_every_llm_interaction_was_served_by_the_pinned_build_with_reasoning(graph, run):
    assert graph["meta"]["provider"] == "vercel"
    assert graph["meta"]["model"] == "deepseek/deepseek-v4.1-flash"
    llm = [i for v in run if v["reviewer"] == "llm" for i in v["interactions"]]
    assert llm, "the committed run has no LLM interactions"
    # A transport failure that received no body (connection timeout) is recorded with
    # raw_response None and retried; every attempt that DID get a body is checked.
    unanswered = [i for i in llm if i["raw_response"] is None]
    assert all(i["call_error"] and "Timeout" in i["call_error"] for i in unanswered)
    answered = [i for i in llm if i["raw_response"] is not None]
    served = collections.Counter(
        i["raw_response"]["choices"][0]["message"]["provider_metadata"]["gateway"]["routing"][
            "finalProvider"
        ]
        for i in answered
    )
    assert served == {VERCEL_PINNED_PROVIDER: len(answered)}
    assert [i for i in answered if not i["raw_response"]["choices"][0]["message"].get("reasoning")] == []
    # The only unparseable answers are reasoning that ran into max_tokens before emitting
    # the verdict; a later attempt decided the pair, or it escalated.
    assert {
        i["raw_response"]["choices"][0]["finish_reason"] for i in answered if i["parse_error"]
    } <= {"length"}
    for verdict in run:
        if verdict["reviewer"] == "llm" and verdict["interactions"][-1]["parse_error"]:
            assert verdict["outcome"] == "hapi:verdict_escalated"
    snapshots = {i["model_snapshot"] for i in answered}
    assert len(snapshots) == 1, f"the run mixed model builds: {snapshots}"
    (snapshot,) = snapshots
    assert snapshot.startswith("deepseek/deepseek-v4.1-flash@")


def test_ruler_ambiguity_results_are_pinned_to_the_committed_graph_and_script():
    results = json.loads((EVAL / "results" / "ruler-ambiguity.json").read_text("utf-8"))
    assert results["inputs"]["after_graph_sha256"] == _sha256(GRAPH)
    assert results["inputs"]["script_sha256"] == _sha256(
        EVAL / "scripts" / "measure_ruler_ambiguity.py"
    )
    assert results["inputs"]["resolver_sha256"] == _sha256(
        REPO_ROOT / "docs/evaluations/hapi-linkability-mvp-2026-08-28/scripts/run_linkability.py"
    )
    assert results["inputs"]["control_sha256"] == _sha256(
        REPO_ROOT / "docs/evaluations/authority-independent-control-2026-09-13/scripts/compare_arms.py"
    )
    registered_graph = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show",
         f"{_list_era_rejected().REGISTERED_BASE_COMMIT}:web-claimgraph/data/claim-graph.json"],
        check=True, capture_output=True,
    ).stdout
    assert results["inputs"]["before_graph_sha256"] == hashlib.sha256(registered_graph).hexdigest()


def test_viewer_predicate_labels_are_the_manifest_labels():
    """web-claimgraph/lib/types.ts restates each predicate's label for display; it must be
    the manifest's rdfs:label (Rule 4 — one source, checked)."""
    import re

    rdfs_label = "{http://www.w3.org/2000/01/rdf-schema#}label"
    manifest = {
        "hapi:" + el.attrib[RDF_ABOUT][1:]: el.find(rdfs_label).text
        for el in ET.parse(MANIFEST).getroot()
        if el.attrib.get(RDF_ABOUT, "").startswith("#") and el.find(rdfs_label) is not None
    }
    source = (REPO_ROOT / "web-claimgraph" / "lib" / "types.ts").read_text("utf-8")
    block = source[source.index("PREDICATE_LABEL"):]
    viewer = dict(re.findall(r'"(hapi:\w+)": "([^"]+)"', block[: block.index("};")]))
    assert viewer, "PREDICATE_LABEL not found in types.ts"
    assert viewer == {predicate: manifest[predicate] for predicate in viewer}
    # ClaimList falls back to the raw predicate id, so a missing label would go unnoticed.
    used = {c["predicate"] for c in json.loads(GRAPH.read_text("utf-8"))["claims"]}
    assert set(viewer) == used


def _load(name: str, path: Path):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def _list_era_rejected():
    return _load("_342_list_era_rejected", EVAL / "scripts" / "list_era_rejected.py")


def test_registered_base_commit_is_the_one_337_registered():
    control = _load(
        "_342_compare_arms",
        REPO_ROOT / "docs/evaluations/authority-independent-control-2026-09-13/scripts/compare_arms.py",
    )
    committed = json.loads((EVAL / "results" / "era-rejected.json").read_text("utf-8"))
    assert _list_era_rejected().REGISTERED_BASE_COMMIT == control.BASE_COMMIT
    assert committed["registered_base_commit"] == control.BASE_COMMIT


def test_era_rejected_list_matches_the_current_matcher():
    module = _list_era_rejected()
    committed = json.loads((EVAL / "results" / "era-rejected.json").read_text("utf-8"))
    assert committed["pairs"] == module.era_rejected(REPO_ROOT)
    # Reviewed 2026-10-11 (results/era-rejected-review.md); no previously APPROVED link is
    # removed by the gate.
    assert collections.Counter(p["previously"] for p in committed["pairs"]) == {
        "escalated": 176, "rejected": 252, "new": 20,
    }
