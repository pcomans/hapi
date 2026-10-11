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
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path

import pytest

from pipeline.authority.claimgraph.build_graph import AUTHORITY_ROOT, REPO_ROOT, WEB_DATA_DIR
from pipeline.authority.claimgraph.graph_ir import build_documentary_graph
from pipeline.authority.claimgraph.reviewer import VERCEL_PINNED_PROVIDER
from pipeline.authority.claimgraph.sources import load_all_sources

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


def test_era_rejected_previously_queued_list_matches_the_current_matcher():
    spec = importlib.util.spec_from_file_location(
        "_342_list_era_rejected", EVAL / "scripts" / "list_era_rejected.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    committed = json.loads(
        (EVAL / "results" / "era-rejected-previously-queued.json").read_text("utf-8")
    )
    assert committed["pairs"] == module.era_rejected_previously_queued(REPO_ROOT)
    # Reviewed 2026-10-11: no previously APPROVED link is removed by the gate.
    assert [p for p in committed["pairs"] if p["previously"] == "approved"] == []
