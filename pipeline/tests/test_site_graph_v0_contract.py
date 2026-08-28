"""Executable enforcement for issue #327.

Committed baseline assertions below use only the pinned real-corpus derivatives.  Tiny
temporary files are used solely for adversarial control-flow tests and make no corpus
or evaluation claim.
"""

from __future__ import annotations

import copy
import gzip
from collections import Counter
import importlib.util
import json
import shutil
import subprocess
import sys
import os
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_ROOT = REPO_ROOT / "docs/evaluations/site-graph-v0"
SCRIPTS = EVAL_ROOT / "scripts"
sys.path.append(str(SCRIPTS))


def _load_script_module(name: str):
    """Load release tooling under a test-only namespace to avoid import collisions."""
    qualified_name = f"_hapi_site_graph_v0_{name}"
    spec = importlib.util.spec_from_file_location(qualified_name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified_name] = module
    spec.loader.exec_module(module)
    return module


compare_baseline_runs_module = _load_script_module("compare_baseline_runs")
compare_candidate_module = _load_script_module("compare_candidate")
corrections_module = _load_script_module("apply_corrections")
build_baseline_module = _load_script_module("build_baseline")
integrity_module = _load_script_module("integrity")
run_baseline_module = _load_script_module("run_baseline")

compare = compare_baseline_runs_module.compare
AMBIGUITY_MAXIMUM_INCREASE = compare_candidate_module.AMBIGUITY_MAXIMUM_INCREASE
CONCENTRATION_MAXIMUM_INCREASE = compare_candidate_module.CONCENTRATION_MAXIMUM_INCREASE
MINIMUM_AFFECTED_FRACTION = compare_candidate_module.MINIMUM_AFFECTED_FRACTION
MINIMUM_GAINED_IDENTITIES = compare_candidate_module.MINIMUM_GAINED_IDENTITIES
REVIEWS_PER_CREDITED_DECISION = compare_candidate_module.REVIEWS_PER_CREDITED_DECISION
canonical_sha256 = compare_candidate_module.canonical_sha256
compare_core = compare_candidate_module.compare_core
decision_key = compare_candidate_module.decision_key
_load_candidate_freeze = compare_candidate_module._load_candidate_freeze
_validate_review_artifacts = compare_candidate_module._validate_review_artifacts
apply_corrections = corrections_module.apply
record_hash = corrections_module.record_hash
classify_current_nodes = build_baseline_module.classify_current_nodes
OPPORTUNITY_MUSEUM_PROTECTION = build_baseline_module.OPPORTUNITY_MUSEUM_PROTECTION
OPPORTUNITY_TOTAL_SIGNATURES = build_baseline_module.OPPORTUNITY_TOTAL_SIGNATURES
read_jsonl = build_baseline_module.read_jsonl
write_gzip_jsonl = build_baseline_module.write_gzip_jsonl
gzip_ledger_digest = build_baseline_module.gzip_ledger_digest
IntegrityError = integrity_module.IntegrityError
sha256 = integrity_module.sha256
verify_release = integrity_module.verify_release
DETERMINISTIC_OUTPUTS = run_baseline_module.DETERMINISTIC_OUTPUTS
FINAL_OUTPUTS = run_baseline_module.FINAL_OUTPUTS
preflight = run_baseline_module.preflight


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _logic_only_run(path: Path, run_id: str | None = None) -> None:
    """Create authenticated-shaped bytes only to attack comparator invariants."""
    path.mkdir()
    for name in sorted(DETERMINISTIC_OUTPUTS):
        (path / name).write_bytes((name + "\n").encode())
    hashes = {name: sha256(path / name) for name in sorted(DETERMINISTIC_OUTPUTS)}
    stable = {
        "schema_version": "site-graph-v0-baseline-run-manifest/1",
        "commands": [],
        "deterministic_output_hashes": hashes,
        "input_snapshot_sha256": "1" * 64,
        "runner_sha256": "2" * 64,
        "builder_sha256": "3" * 64,
        "inventory_path_canonicalization": "test",
        "scope": "logic-only comparator unit input; no corpus claim",
    }
    _write_json(path / "run-output-manifest.json", stable)
    _write_json(
        path / "run-provenance.json",
        {
            "schema_version": "site-graph-v0-baseline-run-provenance/1",
            "run_id": run_id or str(uuid.uuid4()),
            "started_at_utc": "2026-08-28T00:00:00+00:00",
            "finished_at_utc": "2026-08-28T00:00:01+00:00",
            "requested_output": str(path.resolve()),
            "publication": "logic-only",
            "repo_root": str(REPO_ROOT),
            "corpus_root": "/logic-only",
            "canonical_records": 1,
            "records_by_museum": {"logic-only": 1},
            "input_snapshot_sha256": stable["input_snapshot_sha256"],
            "runner_sha256": stable["runner_sha256"],
            "builder_sha256": stable["builder_sha256"],
        },
    )
    assert {item.name for item in path.iterdir()} == FINAL_OUTPUTS


def _temporary_release(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    target = repo / "docs/evaluations/site-graph-v0"
    shutil.copytree(EVAL_ROOT, target, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    ci_target = repo / "pipeline/tests"
    ci_target.mkdir(parents=True)
    shutil.copy2(Path(__file__), ci_target / Path(__file__).name)
    shutil.copy2(REPO_ROOT / "pipeline/pyproject.toml", repo / "pipeline/pyproject.toml")
    shutil.copy2(REPO_ROOT / "pipeline/uv.lock", repo / "pipeline/uv.lock")
    manifest = target / "release-manifest.json"
    manifest.unlink(missing_ok=True)
    subprocess.run(
        [sys.executable, str(target / "scripts/freeze_release.py"), "--repo-root", str(repo)],
        check=True,
        capture_output=True,
        text=True,
    )
    verify_release(repo)
    return repo


@pytest.mark.parametrize(
    ("operation", "target"),
    [
        ("corrupt", "docs/evaluations/site-graph-v0/preregistration.json"),
        ("delete", "docs/evaluations/site-graph-v0/scripts/compare_baseline_runs.py"),
    ],
)
def test_validator_rejects_release_corruption_before_semantics(
    tmp_path: Path, operation: str, target: str
) -> None:
    repo = _temporary_release(tmp_path)
    path = repo / target
    if operation == "corrupt":
        # Specifically attack a machine-readable formula while retaining valid JSON.
        value = json.loads(path.read_text(encoding="utf-8"))
        value["metric_formulas"]["overall_linkability"]["expression"] = "wrong / denominator"
        _write_json(path, value)
    else:
        path.unlink()
    before = {
        item.relative_to(repo).as_posix(): item.read_bytes()
        for item in repo.rglob("*") if item.is_file()
    }
    result = subprocess.run(
        [sys.executable, "-B", str(repo / "docs/evaluations/site-graph-v0/scripts/validate_contract.py"),
         "--repo-root", str(repo), "--corpus", "/does/not/matter",
         "--private-run", "/does/not/matter"],
        check=False,
        capture_output=True,
        text=True,
    )
    after = {
        item.relative_to(repo).as_posix(): item.read_bytes()
        for item in repo.rglob("*") if item.is_file()
    }
    assert result.returncode == 1
    assert '"phase": "release_integrity"' in result.stdout
    assert before == after, "read-only validation must not repair or rewrite the release"


def test_release_inventory_rejects_extra_file(tmp_path: Path) -> None:
    repo = _temporary_release(tmp_path)
    (repo / "docs/evaluations/site-graph-v0/undeclared.txt").write_text("extra")
    with pytest.raises(IntegrityError, match="extra"):
        verify_release(repo)


def test_rerun_comparator_rejects_same_resolved_directory(tmp_path: Path) -> None:
    run = tmp_path / "run"
    _logic_only_run(run)
    with pytest.raises(RuntimeError, match="different directories"):
        compare(run, run / ".." / "run")


@pytest.mark.parametrize("attack", ["corrupt", "delete", "extra", "same_run_id"])
def test_rerun_comparator_authenticates_outputs_and_provenance(tmp_path: Path, attack: str) -> None:
    left, right = tmp_path / "left", tmp_path / "right"
    shared_id = str(uuid.uuid4()) if attack == "same_run_id" else None
    _logic_only_run(left, shared_id)
    _logic_only_run(right, shared_id)
    if attack == "corrupt":
        (right / "baseline-metrics.json").write_text("corrupted after manifest\n")
    elif attack == "delete":
        (right / "top_gaps.json").unlink()
    elif attack == "extra":
        (right / "not-declared.txt").write_text("extra")
    with pytest.raises(RuntimeError):
        compare(left, right)


def test_runner_preflight_failure_leaves_no_output(tmp_path: Path) -> None:
    output = tmp_path / "never-created"
    with pytest.raises((RuntimeError, FileNotFoundError)):
        preflight(REPO_ROOT, tmp_path / "missing-corpus", output)
    assert not output.exists()


def test_public_release_excludes_private_corpus_derivatives() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(SCRIPTS / "private_ledgers.py"),
            "--public-root",
            str(EVAL_ROOT),
            "--public-only",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "frozen-record-evidence.ndjson.gz" in result.stdout
    assert "frozen-opportunity-source.ndjson.gz" in result.stdout


def test_public_boundary_rejects_reintroduced_bulk_derivative(tmp_path: Path) -> None:
    public_root = tmp_path / "public"
    public_root.mkdir()
    for name in (
        "baseline-metrics.json",
        "baseline-node-scope.json",
        "planned-opportunity-summary.json",
        "private-ledger-digests.json",
        "top-unmatched-components.json",
    ):
        shutil.copy2(EVAL_ROOT / name, public_root / name)
    (public_root / "frozen-record-evidence.ndjson.gz").write_bytes(b"private")
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(SCRIPTS / "private_ledgers.py"),
            "--public-root",
            str(public_root),
            "--public-only",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "private/bulk files present" in result.stderr


def _fraction(numerator: int, denominator: int) -> dict:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def _legacy_comparator_case(tmp_path: Path) -> dict:
    """Purpose-built logical case; it is not evidence about the Hapi corpus."""
    museums = {
        "met": ["met-a", "met-b"],
        "brooklyn": ["brooklyn-a", "brooklyn-b"],
        "harvard": ["harvard-a"],
    }
    baseline = []
    for museum, artifact_ids in museums.items():
        for artifact_id in artifact_ids:
            target_ids = [] if museum == "harvard" else ["broad-0"]
            baseline.append(
                {
                    "artifact_id": artifact_id,
                    "museum": museum,
                    "extracted_site_text_evidence": True,
                    "baseline_site_target_ids": target_ids,
                    "baseline_record_scope": "no_link" if not target_ids else "broad_only",
                    "has_blocking_ambiguity": False,
                }
            )
    baseline_concentration = {
        "shared_node_count": 1,
        "top_k_unique_record_concentration": {
            "1": {"selected_target_ids": ["broad-0"], "ratio": _fraction(2, 2)}
        },
        "node_incidence_hhi": _fraction(4, 4),
    }
    empty_concentration = {
        "shared_node_count": 0,
        "top_k_unique_record_concentration": {
            "1": {"selected_target_ids": [], "ratio": _fraction(0, 0)}
        },
        "node_incidence_hhi": _fraction(0, 0),
    }
    metrics = {
        "record_counts_by_museum": {museum: len(ids) for museum, ids in museums.items()},
        "per_museum": {
            museum: {"extracted_site_text_evidence_records": len(ids)}
            for museum, ids in museums.items()
        },
        "connectivity": {
            "pairs": {
                "met__brooklyn": {
                    "concentration_by_museum_side": {
                        "met": copy.deepcopy(baseline_concentration),
                        "brooklyn": copy.deepcopy(baseline_concentration),
                    }
                },
                "met__harvard": {
                    "concentration_by_museum_side": {
                        "met": copy.deepcopy(empty_concentration),
                        "harvard": copy.deepcopy(empty_concentration),
                    }
                },
                "brooklyn__harvard": {
                    "concentration_by_museum_side": {
                        "brooklyn": copy.deepcopy(empty_concentration),
                        "harvard": copy.deepcopy(empty_concentration),
                    }
                },
            }
        },
    }
    node_scope = {
        "schema_version": "site-graph-v0-baseline-node-scope/2",
        "nodes": [{"target_id": "broad-0", "scope_class": "broad"}],
    }
    opportunities = []
    for museum, artifact_ids in museums.items():
        opportunities.append(
            {
                "opportunity_id": f"opp-{museum}",
                "museum": museum,
                "artifact_ids": artifact_ids,
                "artifact_count": len(artifact_ids),
                "artifact_expansion_sha256": canonical_sha256(artifact_ids),
            }
        )
    side = lambda count: {  # noqa: E731
        "credited_effect_opportunity_denominator": count,
        "minimum_credited_affected_records_for_continue": 1 if count else 0,
    }
    queue = {
        "schema_version": "site-graph-v0-opportunity-ledger/1",
        "selection_algorithm": {"logic_only": True},
        "denominator_policy": "logic-only fixed population",
        "credit_warning": "logic-only inputs make no corpus claim",
        "selected_signature_count": 3,
        "opportunities": opportunities,
        "per_museum": {},
        "pair_side_ceilings": {
            "met__brooklyn": {"sides": {"met": side(2), "brooklyn": side(2)}},
            "met__harvard": {"sides": {"met": side(2), "harvard": side(1)}},
            "brooklyn__harvard": {"sides": {"brooklyn": side(2), "harvard": side(1)}},
        },
    }
    crosswalk = json.loads((EVAL_ROOT / "type-crosswalk.json").read_text())
    hierarchy = {
        "schema_version": "site-graph-v0-candidate-hierarchy/1",
        "coverage": "every_candidate_direct_target_from_complete_available_pinned_sources_not_only_evaluated_slice",
        "source_snapshots": [{"id": "logic-only"}],
        "known_incompleteness": {"logic_only": True},
        "nodes": [
            {
                "target_id": target,
                "candidate_e55_type": "temple",
                "identity_class_id": f"identity-{target}",
                "child_ids": [],
            }
            for target in ("specific-1", "specific-2")
        ],
    }
    queue_path, crosswalk_path, hierarchy_path = (
        tmp_path / "queue.json", tmp_path / "crosswalk.json", tmp_path / "hierarchy.json"
    )
    _write_json(queue_path, queue)
    _write_json(crosswalk_path, crosswalk)
    _write_json(hierarchy_path, hierarchy)
    candidate_records = []
    for museum, artifact_ids in museums.items():
        for index, artifact_id in enumerate(artifact_ids):
            if museum == "harvard":
                candidate_records.append(
                    {
                        "artifact_id": artifact_id, "museum": museum,
                        "opportunity_ids": [f"opp-{museum}"], "resolution_status": "unmatched",
                        "abstention_reason": None, "has_blocking_ambiguity": False,
                        "direct_links": [],
                    }
                )
                continue
            target = f"specific-{index + 1}"
            candidate_records.append(
                {
                    "artifact_id": artifact_id, "museum": museum,
                    "opportunity_ids": [f"opp-{museum}"], "resolution_status": "linked",
                    "abstention_reason": None, "has_blocking_ambiguity": False,
                    "direct_links": [
                        {
                            "target_id": target, "candidate_e55_type": "temple",
                            "scope_class": "specific_candidate", "identity_class_id": f"identity-{target}",
                            "complete_hierarchy_child_count": 0,
                            "ancestor_target_ids": ["broad-0"],
                            "support_decision_id": f"link-{artifact_id}-{target}",
                        }
                    ],
                }
            )
    relations = [
        {
            "baseline_target_id": "broad-0", "candidate_target_id": target,
            "relation": "strict_refinement", "reassignment_review_decision_id": f"refine-{target}",
        }
        for target in ("specific-1", "specific-2")
    ]
    candidate = {
        "schema_version": "site-graph-v0-candidate/1", "candidate_id": "logic-only",
        "scope": "frozen_intent_to_treat_queue", "non_queue_policy": "carry_forward_exact_baseline",
        "opportunity_ledger_sha256": sha256(queue_path),
        "type_crosswalk_sha256": sha256(crosswalk_path),
        "complete_hierarchy_context_sha256": sha256(hierarchy_path),
        "relations_frozen_at_utc": "2026-08-28T00:00:00+00:00",
        "candidate_run_started_at_utc": "2026-08-28T00:01:00+00:00",
        "relations_sha256": canonical_sha256(relations),
        "records": candidate_records,
        "relations": relations,
    }
    review_a, review_b = tmp_path / "review-a.txt", tmp_path / "review-b.txt"
    review_a.write_text("independent human review A\n")
    review_b.write_text("independent human review B\n")

    def decision(decision_id: str, kind: str, subject: dict) -> dict:
        return {
            "decision_id": decision_id, "decision_kind": kind, "subject": subject,
            "independent_source_citations": ["source:logic-only"],
            "reviews": [
                {
                    "reviewer_id": reviewer, "independence_group": reviewer,
                    "outcome": "supported", "method": "human",
                    "artifact_path": path.name, "artifact_sha256": sha256(path),
                    "prompt_path": None, "prompt_sha256": None, "model_selector": None,
                    "backend_model_id": None, "raw_response_path": None,
                    "raw_response_sha256": None,
                }
                for reviewer, path in (("reviewer-a", review_a), ("reviewer-b", review_b))
            ],
        }

    decisions = []
    for record in candidate_records:
        for link in record["direct_links"]:
            decisions.append(
                decision(
                    link["support_decision_id"], "link_support",
                    {"artifact_id": record["artifact_id"], "target_id": link["target_id"],
                     "opportunity_ids": record["opportunity_ids"]},
                )
            )
    for relation in relations:
        decisions.append(
            decision(
                relation["reassignment_review_decision_id"], "strict_refinement_support",
                {"baseline_target_id": relation["baseline_target_id"],
                 "candidate_target_id": relation["candidate_target_id"]},
            )
        )
    reviews = {
        "schema_version": "site-graph-v0-review-ledger/1",
        "review_scope": "census_of_every_candidate_changed_link_and_claimed_strict_refinement",
        "decisions": decisions,
    }
    return {
        "baseline": baseline, "metrics": metrics, "node_scope": node_scope,
        "queue": queue, "crosswalk": crosswalk, "candidate": candidate,
        "hierarchy": hierarchy, "reviews": reviews,
        "paths": {"queue": queue_path, "crosswalk": crosswalk_path, "hierarchy": hierarchy_path},
        "review_root": tmp_path,
    }


def _legacy_run_case(case: dict) -> dict:
    return compare_core(
        case["baseline"], case["metrics"], case["node_scope"], case["queue"],
        case["crosswalk"], case["candidate"], case["hierarchy"], case["reviews"],
        case["paths"], case["review_root"],
    )


def _comparator_case(tmp_path: Path) -> dict:
    """Purpose-built pure-core input; it makes no claim about the Hapi corpus."""
    museums = {
        "met": ["met-a", "met-b"],
        "brooklyn": ["brooklyn-a", "brooklyn-b"],
        "harvard": ["harvard-a"],
    }
    baseline = []
    for museum, artifact_ids in museums.items():
        for artifact_id in artifact_ids:
            targets = [] if museum == "harvard" else ["broad-0"]
            baseline.append(
                {
                    "artifact_id": artifact_id,
                    "museum": museum,
                    "extracted_site_text_evidence": True,
                    "baseline_site_target_ids": targets,
                    "baseline_record_scope": "no_link" if not targets else "broad_only",
                    "has_blocking_ambiguity": False,
                }
            )
    metrics = {
        "record_counts_by_museum": {museum: len(ids) for museum, ids in museums.items()},
        "per_museum": {
            museum: {"extracted_site_text_evidence_records": len(ids)}
            for museum, ids in museums.items()
        },
    }
    node_scope = {
        "schema_version": "site-graph-v0-baseline-node-scope/2",
        "nodes": [{"target_id": "broad-0", "scope_class": "broad"}],
    }
    opportunities = []
    itt_records = {}
    for rank, (museum, artifact_ids) in enumerate(museums.items(), 1):
        opportunity_id = f"opp-{rank:04d}"
        opportunities.append(
            {
                "opportunity_id": opportunity_id,
                "selection_rank": rank,
                "selection_reason": "logic_only",
                "museum": museum,
                "unresolved_status_counts": {"unmatched": len(artifact_ids)},
                "mention_count": len(artifact_ids),
                "artifact_count": len(artifact_ids),
                "artifact_expansion_sha256": canonical_sha256(artifact_ids),
                "intent_to_treat": True,
            }
        )
        itt_records[museum] = [
            {
                "artifact_id": artifact_id,
                "opportunity_ids": [opportunity_id],
                "baseline_record_scope": "no_link" if museum == "harvard" else "broad_only",
            }
            for artifact_id in artifact_ids
        ]

    pair_memberships = {}
    pair_summaries = {}
    for left, right in (("met", "brooklyn"), ("met", "harvard"), ("brooklyn", "harvard")):
        key = f"{left}__{right}"
        private_sides, public_sides = {}, {}
        for museum in (left, right):
            category = (
                "broad_only_pair_connection"
                if {left, right} == {"met", "brooklyn"}
                else "no_baseline_pair_connection"
            )
            rows = [
                {"artifact_id": artifact_id, "category": category}
                for artifact_id in museums[museum]
            ]
            private_sides[museum] = rows
            public_sides[museum] = {
                "credited_effect_opportunity_denominator": len(rows),
                "minimum_credited_affected_records_for_continue": 1,
            }
        pair_memberships[key] = {"sides": private_sides}
        pair_summaries[key] = {"sides": public_sides}
    queue = {
        "schema_version": "site-graph-v0-opportunity-summary/2",
        "minimum_affected_opportunity_fraction": {"numerator": 1, "denominator": 10},
        "selected_signature_count": 3,
        "opportunities": opportunities,
        "pair_side_ceilings": pair_summaries,
    }
    private_opportunity = {
        "schema_version": "site-graph-v0-private-opportunity-ledger/2",
        "intent_to_treat_records_by_museum": itt_records,
        "credited_pair_opportunity_memberships": pair_memberships,
    }
    crosswalk = json.loads((EVAL_ROOT / "type-crosswalk.json").read_text())
    snapshot = {
        "schema_version": "site-graph-v0-candidate-source-snapshot/1",
        "source_snapshot_id": "logic-source",
        "authority_name": "logic only",
        "source_kind": "unit-test",
        "acquired_at_utc": "2026-08-28T00:00:00Z",
        "provenance": {"scope": "logic-only"},
        "completeness": {
            "coverage_statement": "all two logic-only records",
            "known_incompleteness": ["not corpus evidence"],
            "complete_for_candidate_target_derivation": True,
        },
        "records": [
            {
                "source_record_id": f"source-{target}",
                "target_id": target,
                "source_types": ["temple"],
                "parent_ids": ["broad-0"],
                "child_ids": [],
                "authority_citations": [f"logic:{target}"],
            }
            for target in ("specific-1", "specific-2")
        ],
    }
    hierarchy = {
        "schema_version": "site-graph-v0-candidate-hierarchy/2",
        "coverage": "every_candidate_target_from_all_frozen_available_source_snapshot_records_not_only_evaluated_slice",
        "known_incompleteness": {"logic_only": True},
        "nodes": [
            {
                "target_id": target,
                "candidate_e55_type": "temple",
                "child_ids": [],
                "ancestor_target_ids": ["broad-0"],
                "source_snapshot_ids": ["logic-source"],
                "source_record_ids": [f"source-{target}"],
            }
            for target in ("specific-1", "specific-2")
        ],
    }
    candidate_records = []
    decisions = {}
    for museum, artifact_ids in museums.items():
        for index, artifact_id in enumerate(artifact_ids):
            if museum == "harvard":
                candidate_records.append(
                    {
                        "artifact_id": artifact_id,
                        "resolution_status": "unmatched",
                        "abstention_reason": None,
                        "has_blocking_ambiguity": False,
                        "direct_links": [],
                    }
                )
                continue
            target = f"specific-{index + 1}"
            subject = {"artifact_id": artifact_id, "target_id": target}
            key = decision_key("link_support", subject)
            decisions[key] = {
                "decision_kind": "link_support",
                "subject": subject,
                "supported": True,
                "disagreement": False,
            }
            candidate_records.append(
                {
                    "artifact_id": artifact_id,
                    "resolution_status": "linked",
                    "abstention_reason": None,
                    "has_blocking_ambiguity": False,
                    "direct_links": [{"target_id": target, "support_decision_key": key}],
                }
            )
    relations = []
    for target in ("specific-1", "specific-2"):
        subject = {
            "left_target_id": target,
            "right_target_id": "broad-0",
            "relation": "strict_refinement",
        }
        key = decision_key("strict_refinement_support", subject)
        decisions[key] = {
            "decision_kind": "strict_refinement_support",
            "subject": subject,
            "supported": True,
            "disagreement": False,
        }
        relations.append(
            {
                "relation_id": f"refine-{target}",
                **subject,
                "review_decision_key": key,
            }
        )
    relation_ledger = {
        "schema_version": "site-graph-v0-relation-ledger/1",
        "strict_refinement_direction": "left_target_id_is_narrower_than_right_target_id",
        "relations": relations,
    }
    candidate = {"schema_version": "site-graph-v0-candidate-result/2", "records": candidate_records}
    return {
        "baseline": baseline,
        "metrics": metrics,
        "node_scope": node_scope,
        "queue": queue,
        "private_opportunity": private_opportunity,
        "crosswalk": crosswalk,
        "candidate": candidate,
        "hierarchy": hierarchy,
        "snapshots": [snapshot],
        "relations": relation_ledger,
        "decisions": decisions,
    }


def _run_case(case: dict) -> dict:
    return compare_core(
        case["baseline"],
        case["metrics"],
        case["node_scope"],
        case["queue"],
        case["private_opportunity"],
        case["crosswalk"],
        case["candidate"],
        case["hierarchy"],
        case["snapshots"],
        case["relations"],
        case["decisions"],
    )


def test_supported_strict_refinement_replaces_direct_edge_without_counting_loss(tmp_path: Path) -> None:
    report = _run_case(_comparator_case(tmp_path))
    assert report["outcome"] == "CONTINUE"
    assert report["event_counts"]["strict_refinement_reassignment"] == 4
    assert report["event_counts"]["loss"] == 0
    assert report["reassignment_edge_modes"] == {
        "old_direct_edge_replaced_ancestor_semantics_preserved": 4
    }
    assert report["pairs"]["met__brooklyn"][
        "gained_credited_specific_shared_identity_class_count"
    ] == 2


def test_narrower_node_without_review_support_gets_zero_credit(tmp_path: Path) -> None:
    case = _comparator_case(tmp_path)
    for value in case["decisions"].values():
        value["supported"] = False
    report = _run_case(case)
    assert report["outcome"] == "REDESIGN"  # unsupported replacement is a loss
    assert report["event_counts"]["strict_refinement_reassignment"] == 0
    assert report["event_counts"]["new_link"] == 0
    assert report["event_counts"]["loss"] == 4


def test_slice_leafness_cannot_override_complete_hierarchy_context(tmp_path: Path) -> None:
    case = _comparator_case(tmp_path)
    case["hierarchy"]["nodes"][0]["child_ids"] = ["omitted-from-slice-child"]
    case["snapshots"][0]["records"][0]["child_ids"] = ["omitted-from-slice-child"]
    report = _run_case(case)
    assert report["outcome"] == "INVALID"
    assert any("narrower target is not specific" in error for error in report["integrity"]["errors"])


def test_reviewer_disagreement_is_uncredited_and_unresolved(tmp_path: Path) -> None:
    case = _comparator_case(tmp_path)
    first_link = next(
        value for value in case["decisions"].values()
        if value["decision_kind"] == "link_support"
    )
    first_link["supported"] = False
    first_link["disagreement"] = True
    report = _run_case(case)
    assert report["outcome"] == "REDESIGN"
    assert report["ambiguity_and_abstention"]["reviewer_disagreement_decisions_uncredited"] == 1
    assert report["event_counts"]["loss"] == 1


def test_concentration_is_gated_per_side_against_comparable_baseline(tmp_path: Path) -> None:
    from metrics_core import concentration

    links = {
        "a": {"x", "y"},
        "b": {"x"},
        "c": {"y"},
    }
    result = concentration(links, {"a", "b", "c"}, {"x", "y"})
    assert result["top_k_unique_record_concentration"]["1"]["ratio"] == _fraction(2, 3)
    assert result["top_k_unique_record_concentration"]["5"]["ratio"] == _fraction(3, 3)
    assert result["top_k_unique_record_concentration"]["10"]["ratio"] == _fraction(3, 3)
    assert result["node_incidence_hhi"] == _fraction(8, 16)


def test_equivalent_identity_classes_cannot_fake_two_gained_nodes(tmp_path: Path) -> None:
    case = _comparator_case(tmp_path)
    subject = {
        "left_target_id": "specific-1",
        "right_target_id": "specific-2",
        "relation": "equivalent",
    }
    key = decision_key("equivalence_support", subject)
    case["decisions"][key] = {
        "decision_kind": "equivalence_support",
        "subject": subject,
        "supported": True,
        "disagreement": False,
    }
    case["relations"]["relations"].append(
        {
            "relation_id": "equivalent-specific-aliases",
            **subject,
            "review_decision_key": key,
        }
    )
    report = _run_case(case)
    assert report["outcome"] == "STOP"
    assert report["pairs"]["met__brooklyn"][
        "gained_credited_specific_shared_identity_class_count"
    ] == 1


def test_pair_numerator_intersects_exact_private_membership_and_category(tmp_path: Path) -> None:
    case = _comparator_case(tmp_path)
    private_side = case["private_opportunity"]["credited_pair_opportunity_memberships"][
        "met__brooklyn"
    ]["sides"]["met"]
    private_side[:] = [
        {"artifact_id": "met-a", "category": "no_baseline_pair_connection"}
    ]
    public_side = case["queue"]["pair_side_ceilings"]["met__brooklyn"]["sides"]["met"]
    public_side["credited_effect_opportunity_denominator"] = 1
    public_side["minimum_credited_affected_records_for_continue"] = 1
    report = _run_case(case)
    side = report["pairs"]["met__brooklyn"]["sides"]["met"]
    assert side["credited_affected_records"] == 1
    assert side["credited_pair_event_counts"] == {
        "new_pair_connection": 1,
        "supported_broad_to_specific_pair_refinement": 0,
    }


def test_existing_target_cannot_be_relabelled_by_candidate_snapshot(tmp_path: Path) -> None:
    case = _comparator_case(tmp_path)
    case["snapshots"][0]["records"].append(
        {
            "source_record_id": "source-broad-0",
            "target_id": "broad-0",
            "source_types": ["temple"],
            "parent_ids": [],
            "child_ids": [],
            "authority_citations": ["logic:broad-0"],
        }
    )
    case["hierarchy"]["nodes"].append(
        {
            "target_id": "broad-0",
            "candidate_e55_type": "temple",
            "child_ids": [],
            "ancestor_target_ids": [],
            "source_snapshot_ids": ["logic-source"],
            "source_record_ids": ["source-broad-0"],
        }
    )
    report = _run_case(case)
    assert report["outcome"] == "INVALID"
    assert any("cannot be relabeled" in error for error in report["integrity"]["errors"])


def test_minimum_fraction_cannot_be_overridden_by_public_aggregate(tmp_path: Path) -> None:
    case = _comparator_case(tmp_path)
    case["queue"]["minimum_affected_opportunity_fraction"] = {
        "numerator": 1,
        "denominator": 2,
    }
    report = _run_case(case)
    assert report["outcome"] == "INVALID"
    assert any("executable constant" in error for error in report["integrity"]["errors"])


def test_multi_target_concentration_is_hash_seed_deterministic() -> None:
    code = f"""
import json, sys
sys.path.insert(0, {str(SCRIPTS)!r})
from metrics_core import concentration
links = {{'a': {{'x', 'y'}}, 'b': {{'x'}}, 'c': {{'y'}}}}
print(json.dumps(concentration(links, {{'a','b','c'}}, {{'x','y'}}), sort_keys=True, separators=(',', ':')))
"""
    outputs = []
    for seed in ("1", "99991"):
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = seed
        result = subprocess.run(
            [sys.executable, "-B", "-c", code],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        outputs.append(result.stdout.encode())
    assert outputs[0] == outputs[1]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _candidate_git_fixture(tmp_path: Path) -> dict:
    repo = tmp_path / "candidate-repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "logic@example.invalid")
    _git(repo, "config", "user.name", "Logic Fixture")
    paths = {
        "hierarchy": "candidate/hierarchy.json",
        "relations": "candidate/relations.json",
        "source": "candidate/source.json",
        "freeze": "candidate/freeze.json",
        "result": "candidate/result.json",
        "reviews": "candidate/reviews.json",
    }
    (repo / "candidate").mkdir()
    source = {
        "schema_version": "site-graph-v0-candidate-source-snapshot/1",
        "source_snapshot_id": "logic-source",
        "authority_name": "logic only",
        "source_kind": "unit-test",
        "acquired_at_utc": "2026-08-28T00:00:00Z",
        "provenance": {"purpose": "logic-only"},
        "completeness": {
            "coverage_statement": "complete one-row logic input",
            "known_incompleteness": ["not corpus evidence"],
            "complete_for_candidate_target_derivation": True,
        },
        "records": [
            {
                "source_record_id": "source-specific",
                "target_id": "specific",
                "source_types": ["temple"],
                "parent_ids": ["broad"],
                "child_ids": [],
                "authority_citations": ["logic:specific"],
            }
        ],
    }
    hierarchy = {
        "schema_version": "site-graph-v0-candidate-hierarchy/2",
        "coverage": "every_candidate_target_from_all_frozen_available_source_snapshot_records_not_only_evaluated_slice",
        "known_incompleteness": {"logic_only": True},
        "nodes": [
            {
                "target_id": "specific",
                "candidate_e55_type": "temple",
                "child_ids": [],
                "ancestor_target_ids": ["broad"],
                "source_snapshot_ids": ["logic-source"],
                "source_record_ids": ["source-specific"],
            }
        ],
    }
    relations = {
        "schema_version": "site-graph-v0-relation-ledger/1",
        "strict_refinement_direction": "left_target_id_is_narrower_than_right_target_id",
        "relations": [],
    }
    for key, value in (("source", source), ("hierarchy", hierarchy), ("relations", relations)):
        _write_json(repo / paths[key], value)
    _git(repo, "add", "candidate")
    _git(repo, "commit", "-qm", "candidate inputs")
    input_commit = _git(repo, "rev-parse", "HEAD")
    schema_by_role = {
        "hierarchy": hierarchy["schema_version"],
        "relations": relations["schema_version"],
        "source": source["schema_version"],
    }
    role_by_key = {
        "hierarchy": "hierarchy",
        "relations": "relation_ledger",
        "source": "source_snapshot",
    }
    files = []
    for key in ("hierarchy", "relations", "source"):
        files.append(
            {
                "role": role_by_key[key],
                "path": paths[key],
                "sha256": sha256(repo / paths[key]),
                "git_blob_oid": _git(repo, "rev-parse", f"HEAD:{paths[key]}"),
                "schema_version": schema_by_role[key],
            }
        )
    release_hash, private_hash = "a" * 64, "b" * 64
    freeze = {
        "schema_version": "site-graph-v0-candidate-freeze-manifest/1",
        "contract_version": "site-graph-v0/2",
        "release_manifest_sha256": release_hash,
        "private_opportunity_ledger_canonical_sha256": private_hash,
        "created_at_utc": "2026-08-28T00:01:00Z",
        "created_by": "logic-fixture",
        "provenance": {"input_commit": input_commit},
        "files": files,
    }
    _write_json(repo / paths["freeze"], freeze)
    _git(repo, "add", paths["freeze"])
    _git(repo, "commit", "-qm", "freeze candidate inputs")
    freeze_commit = _git(repo, "rev-parse", "HEAD")
    freeze_blob = _git(repo, "rev-parse", f"HEAD:{paths['freeze']}")
    candidate = {
        "schema_version": "site-graph-v0-candidate-result/2",
        "candidate_id": "logic-only",
        "release_manifest_sha256": release_hash,
        "private_opportunity_ledger_canonical_sha256": private_hash,
        "freeze_commit": freeze_commit,
        "freeze_manifest_path": paths["freeze"],
        "freeze_manifest_blob_oid": freeze_blob,
        "run_started_at_utc": "2026-08-28T00:02:00Z",
        "records": [],
    }
    reviews = {
        "schema_version": "site-graph-v0-review-ledger/2",
        "review_scope": "census_of_every_credited_new_link_strict_refinement_and_equivalence_decision",
        "decisions": [],
    }
    _write_json(repo / paths["result"], candidate)
    _write_json(repo / paths["reviews"], reviews)
    _git(repo, "add", "candidate")
    _git(repo, "commit", "-qm", "candidate result")
    result_commit = _git(repo, "rev-parse", "HEAD")
    return {
        "repo": repo,
        "paths": paths,
        "freeze_commit": freeze_commit,
        "result_commit": result_commit,
        "release_hash": release_hash,
        "private_hash": private_hash,
    }


def test_production_candidate_inputs_are_bound_to_distinct_git_commits(tmp_path: Path) -> None:
    fixture = _candidate_git_fixture(tmp_path)
    loaded = _load_candidate_freeze(
        fixture["repo"],
        fixture["freeze_commit"],
        fixture["paths"]["freeze"],
        fixture["result_commit"],
        fixture["paths"]["result"],
        fixture["paths"]["reviews"],
        fixture["release_hash"],
        fixture["private_hash"],
        EVAL_ROOT / "schemas",
    )
    assert loaded[0]["candidate_id"] == "logic-only"
    with pytest.raises(ValueError, match="distinct ancestor"):
        _load_candidate_freeze(
            fixture["repo"],
            fixture["result_commit"],
            fixture["paths"]["freeze"],
            fixture["result_commit"],
            fixture["paths"]["result"],
            fixture["paths"]["reviews"],
            fixture["release_hash"],
            fixture["private_hash"],
            EVAL_ROOT / "schemas",
        )


def test_production_candidate_binding_rejects_alternate_release(tmp_path: Path) -> None:
    fixture = _candidate_git_fixture(tmp_path)
    with pytest.raises(ValueError, match="release manifest binding mismatch"):
        _load_candidate_freeze(
            fixture["repo"],
            fixture["freeze_commit"],
            fixture["paths"]["freeze"],
            fixture["result_commit"],
            fixture["paths"]["result"],
            fixture["paths"]["reviews"],
            "c" * 64,
            fixture["private_hash"],
            EVAL_ROOT / "schemas",
        )


def test_production_cli_has_no_arbitrary_baseline_or_crosswalk_paths() -> None:
    result = subprocess.run(
        [sys.executable, "-B", str(SCRIPTS / "compare_candidate.py"), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "--repo-root" in result.stdout
    assert "--private-run" in result.stdout
    assert "--baseline-records" not in result.stdout
    assert "--baseline-metrics" not in result.stdout
    assert "--opportunity-ledger" not in result.stdout
    assert "--type-crosswalk" not in result.stdout


def _structured_review_fixture(tmp_path: Path) -> tuple[Path, str, dict]:
    fixture = _candidate_git_fixture(tmp_path)
    repo = fixture["repo"]
    subject = {"artifact_id": "logic-artifact", "target_id": "logic-target"}
    key = decision_key("link_support", subject)
    paths = []
    for suffix in ("a", "b"):
        relative = f"candidate/review-{suffix}.json"
        paths.append(relative)
        _write_json(
            repo / relative,
            {
                "schema_version": "site-graph-v0-review-artifact/1",
                "review_id": f"review-{suffix}",
                "decision_key": key,
                "decision_kind": "link_support",
                "subject": subject,
                "reviewer": {
                    "reviewer_id": f"reviewer-{suffix}",
                    "independence_group": f"group-{suffix}",
                },
                "outcome": "supported",
                "method": "human",
                "citations": [
                    {
                        "source_id": f"authority-{suffix}",
                        "source_kind": "independent_authority",
                        "locator": f"record-{suffix}",
                        "evidence_summary": f"independent logic evidence {suffix}",
                        "originating_museum": False,
                    }
                ],
                "reasoning": f"logic-only structured review {suffix}",
                "llm_interaction": None,
            },
        )
    _git(repo, "add", "candidate")
    _git(repo, "commit", "-qm", "structured review artifacts")
    result_commit = _git(repo, "rev-parse", "HEAD")
    references = []
    for relative in paths:
        value = json.loads((repo / relative).read_text())
        references.append(
            {
                "path": relative,
                "sha256": sha256(repo / relative),
                "git_blob_oid": _git(repo, "rev-parse", f"HEAD:{relative}"),
                "canonical_record_sha256": canonical_sha256(value),
            }
        )
    ledger = {
        "schema_version": "site-graph-v0-review-ledger/2",
        "review_scope": "census_of_every_credited_new_link_strict_refinement_and_equivalence_decision",
        "decisions": [
            {
                "decision_key": key,
                "decision_kind": "link_support",
                "subject": subject,
                "review_artifacts": references,
            }
        ],
    }
    return repo, result_commit, ledger


def test_structured_review_census_requires_two_distinct_subject_bound_artifacts(
    tmp_path: Path,
) -> None:
    repo, result_commit, ledger = _structured_review_fixture(tmp_path)
    decisions = _validate_review_artifacts(
        repo, result_commit, ledger, EVAL_ROOT / "schemas"
    )
    assert next(iter(decisions.values()))["supported"] is True
    duplicate = copy.deepcopy(ledger)
    duplicate["decisions"][0]["review_artifacts"][1] = copy.deepcopy(
        duplicate["decisions"][0]["review_artifacts"][0]
    )
    with pytest.raises(ValueError, match="reused|distinct"):
        _validate_review_artifacts(repo, result_commit, duplicate, EVAL_ROOT / "schemas")


def test_structured_review_artifact_cannot_cover_a_different_decision(tmp_path: Path) -> None:
    repo, result_commit, ledger = _structured_review_fixture(tmp_path)
    wrong_subject = {"artifact_id": "other", "target_id": "logic-target"}
    ledger["decisions"][0]["subject"] = wrong_subject
    ledger["decisions"][0]["decision_key"] = decision_key("link_support", wrong_subject)
    with pytest.raises(ValueError, match="not bound"):
        _validate_review_artifacts(repo, result_commit, ledger, EVAL_ROOT / "schemas")


def _legacy_test_append_only_correction_changes_only_separate_sensitivity_output(tmp_path: Path) -> None:
    baseline = EVAL_ROOT / "frozen-record-evidence.ndjson.gz"
    baseline_hash_before = sha256(baseline)
    primary_metrics_hash_before = sha256(EVAL_ROOT / "baseline-metrics.json")
    with gzip.open(baseline, "rt", encoding="utf-8") as handle:
        first = json.loads(next(handle))
    field = "has_any_unmatched_expression"
    correction = {
        "sequence": 1,
        "correction_id": "logic-only-correction-1",
        "previous_record_sha256": None,
        "record_sha256": "",
        "artifact_id": first["artifact_id"],
        "field": field,
        "baseline_value": first[field],
        "corrected_value": not first[field],
        "reason": "purpose-built sensitivity isolation test",
        "citations": ["logic-only:test"],
        "reviewer_ids": ["reviewer-a", "reviewer-b"],
        "decision_commit": "abcdef1",
        "recorded_at_utc": "2026-08-28T00:00:00+00:00",
    }
    correction["record_sha256"] = record_hash(correction)
    committed = json.loads((EVAL_ROOT / "evidence-corrections.json").read_text())
    ledger = {**committed, "corrections": [correction]}
    ledger_path = tmp_path / "corrections.json"
    _write_json(ledger_path, ledger)
    output = tmp_path / "sensitivity"
    metadata = apply_corrections(baseline, ledger_path, output)
    assert sha256(baseline) == baseline_hash_before
    assert sha256(EVAL_ROOT / "baseline-metrics.json") == primary_metrics_hash_before
    assert metadata["primary_baseline_unchanged_sha256"] == baseline_hash_before
    assert metadata["sensitivity_record_evidence_sha256"] != baseline_hash_before
    assert metadata["sensitivity_metrics_sha256"] == sha256(output / "sensitivity-metrics.json")
    with gzip.open(output / "sensitivity-record-evidence.ndjson.gz", "rt", encoding="utf-8") as handle:
        sensitivity_first = json.loads(next(handle))
    assert {key for key in first if first[key] != sensitivity_first[key]} == {field}
    assert sensitivity_first[field] is not first[field]


def _legacy_test_correction_records_reject_empty_required_evidence(tmp_path: Path) -> None:
    baseline = EVAL_ROOT / "frozen-record-evidence.ndjson.gz"
    ledger = json.loads((EVAL_ROOT / "evidence-corrections.json").read_text())
    bad = {
        "sequence": 1, "correction_id": "bad", "previous_record_sha256": None,
        "record_sha256": "", "artifact_id": "missing", "field": "has_any_ambiguity",
        "baseline_value": False, "corrected_value": True, "reason": "",
        "citations": [], "reviewer_ids": [], "decision_commit": "",
        "recorded_at_utc": "",
    }
    bad["record_sha256"] = record_hash(bad)
    path = tmp_path / "bad.json"
    _write_json(path, {**ledger, "corrections": [bad]})
    with pytest.raises(ValueError):
        apply_corrections(baseline, path, tmp_path / "never")


def _correction_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    repo = tmp_path / "repo"
    evaluation = repo / "docs/evaluations/site-graph-v0"
    schemas = evaluation / "schemas"
    schemas.mkdir(parents=True)
    shutil.copy2(
        EVAL_ROOT / "schemas/correction-ledger.schema.json",
        schemas / "correction-ledger.schema.json",
    )
    private_run = tmp_path / "private-run"
    private_run.mkdir()
    records = []
    mentions = []
    for museum in ("met", "brooklyn", "harvard"):
        artifact_id = f"{museum}-logic"
        records.append(
            {
                "artifact_id": artifact_id,
                "museum": museum,
                "extracted_site_text_evidence": True,
                "extracted_site_text_rule": "logic-only",
                "site_mention_count": 1,
                "site_mention_status_counts": {"unmatched": 1},
                "baseline_resolution_state": "unmatched_only",
                "baseline_site_target_ids": [],
                "baseline_site_target_scope_counts": {},
                "baseline_record_scope": "no_link",
                "has_any_ambiguity": False,
                "has_blocking_ambiguity": False,
                "has_any_unmatched_expression": True,
            }
        )
        mentions.append(
            {
                "artifact_id": artifact_id,
                "field_path": "logic.place",
                "mention_id": f"mention-{museum}",
                "mention_text": f"logic {museum}",
                "museum": museum,
                "normalized_keys": [f"logic-{museum}"],
                "status": "unmatched",
                "entity_type": "site",
            }
        )
    baseline_path = private_run / "private-record-evidence.ndjson.gz"
    write_gzip_jsonl(baseline_path, records)
    write_gzip_jsonl(private_run / "private-opportunity-source.ndjson.gz", mentions)
    digest = gzip_ledger_digest(baseline_path)
    _write_json(
        evaluation / "private-ledger-digests.json",
        {"ledgers": {"private_record_evidence": digest}},
    )
    _write_json(
        evaluation / "baseline-node-scope.json",
        {
            "schema_version": "site-graph-v0-baseline-node-scope/2",
            "nodes": [{"target_id": "broad-0", "scope_class": "broad"}],
        },
    )
    monkeypatch.setattr(corrections_module, "verify_private_ledgers", lambda *_: {})
    corrections = []
    operations = [
        {
            "kind": "set_site_mention_status_count",
            "status": "unmatched",
            "from_count": 1,
            "to_count": 0,
        },
        {
            "kind": "set_site_mention_status_count",
            "status": "resolved",
            "from_count": 0,
            "to_count": 1,
        },
        {"kind": "add_direct_target", "target_id": "broad-0"},
    ]
    previous = None
    for sequence, operation in enumerate(operations, 1):
        correction = {
            "sequence": sequence,
            "correction_id": f"logic-correction-{sequence}",
            "previous_correction_sha256": previous,
            "supersedes_correction_id": None,
            "artifact_id": "met-logic",
            "operation": operation,
            "reason": "purpose-built correction isolation test",
            "citations": [
                {
                    "source_id": "logic-authority",
                    "locator": f"record-{sequence}",
                    "evidence_summary": "logic-only evidence",
                }
            ],
            "reviewer_ids": ["reviewer-a", "reviewer-b"],
            "decision_commit": "a" * 40,
            "recorded_at_utc": f"2026-08-28T00:00:0{sequence}Z",
            "record_sha256": "",
        }
        correction["record_sha256"] = record_hash(correction)
        previous = correction["record_sha256"]
        corrections.append(correction)
    ledger = {
        "schema_version": "site-graph-v0-correction-ledger/2",
        "baseline_mutated": False,
        "private_record_evidence_canonical_sha256": digest[
            "canonical_uncompressed_ndjson_sha256"
        ],
        "corrections": corrections,
    }
    ledger_path = tmp_path / "private-corrections.json"
    _write_json(ledger_path, ledger)
    return {
        "repo": repo,
        "evaluation": evaluation,
        "private_run": private_run,
        "baseline_path": baseline_path,
        "ledger_path": ledger_path,
        "ledger": ledger,
    }


def test_append_only_primitive_correction_changes_only_sensitivity_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _correction_fixture(tmp_path, monkeypatch)
    baseline_hash = sha256(fixture["baseline_path"])
    public_before = {
        path.relative_to(fixture["evaluation"]).as_posix(): sha256(path)
        for path in fixture["evaluation"].rglob("*")
        if path.is_file()
    }
    output = tmp_path / "sensitivity"
    summary = apply_corrections(
        fixture["repo"], fixture["private_run"], fixture["ledger_path"], output
    )
    assert sha256(fixture["baseline_path"]) == baseline_hash
    assert public_before == {
        path.relative_to(fixture["evaluation"]).as_posix(): sha256(path)
        for path in fixture["evaluation"].rglob("*")
        if path.is_file()
    }
    assert summary["primary_baseline_immutable"] is True
    assert summary["correction_count"] == 3
    assert summary["sensitivity_private_record_evidence"][
        "canonical_uncompressed_ndjson_sha256"
    ] != summary["primary_private_record_evidence"]["canonical_uncompressed_ndjson_sha256"]
    with gzip.open(
        output / "private-sensitivity-record-evidence.ndjson.gz", "rt", encoding="utf-8"
    ) as handle:
        rows = [json.loads(line) for line in handle]
    met = next(row for row in rows if row["museum"] == "met")
    assert met["site_mention_status_counts"] == {"resolved": 1}
    assert met["baseline_site_target_ids"] == ["broad-0"]
    assert met["has_any_unmatched_expression"] is False
    assert (output / "sensitivity-metrics.json").is_file()
    assert (output / "private-sensitivity-opportunity-ledger.json").is_file()


def test_corrections_reject_invented_target_string_boolean_and_ambiguous_repeat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _correction_fixture(tmp_path, monkeypatch)
    invented = copy.deepcopy(fixture["ledger"])
    invented["corrections"][2]["operation"]["target_id"] = "invented"
    invented["corrections"][2]["record_sha256"] = record_hash(invented["corrections"][2])
    path = tmp_path / "invented.json"
    _write_json(path, invented)
    with pytest.raises(ValueError, match="unknown targets"):
        apply_corrections(fixture["repo"], fixture["private_run"], path, tmp_path / "never-a")

    wrong_type = copy.deepcopy(fixture["ledger"])
    wrong_type["corrections"][0]["operation"]["from_count"] = "1"
    wrong_type["corrections"][0]["record_sha256"] = record_hash(wrong_type["corrections"][0])
    path = tmp_path / "wrong-type.json"
    _write_json(path, wrong_type)
    with pytest.raises(ValueError, match="schema validation"):
        apply_corrections(fixture["repo"], fixture["private_run"], path, tmp_path / "never-b")

    repeated = copy.deepcopy(fixture["ledger"])
    extra = copy.deepcopy(repeated["corrections"][2])
    extra.update(
        {
            "sequence": 4,
            "correction_id": "logic-correction-4",
            "previous_correction_sha256": repeated["corrections"][2]["record_sha256"],
            "record_sha256": "",
        }
    )
    extra["operation"] = {"kind": "remove_direct_target", "target_id": "broad-0"}
    extra["record_sha256"] = record_hash(extra)
    repeated["corrections"].append(extra)
    path = tmp_path / "repeat.json"
    _write_json(path, repeated)
    with pytest.raises(ValueError, match="without exact supersession"):
        apply_corrections(fixture["repo"], fixture["private_run"], path, tmp_path / "never-c")


def test_committed_real_corpus_headlines_recompute_from_pinned_inputs() -> None:
    snapshot = json.loads((EVAL_ROOT / "input-snapshot.json").read_text())
    idai = read_jsonl(REPO_ROOT / "pipeline/pipeline/authority/sources/idai-gazetteer/reconciled.jsonl")
    raw = json.loads((REPO_ROOT / "pipeline/pipeline/authority/sources/idai-gazetteer/raw.json").read_text())
    crosswalk = json.loads((EVAL_ROOT / "type-crosswalk.json").read_text())
    expected_targets = snapshot["current_authority"]["site_snapshot"]["site_target_count"]
    nodes, scope_by_target, hierarchy = classify_current_nodes(
        idai, raw, crosswalk, expected_targets
    )
    assert json.loads((EVAL_ROOT / "baseline-node-scope.json").read_text()) == {
        "schema_version": "site-graph-v0-baseline-node-scope/2",
        "hierarchy_context": hierarchy,
        "nodes": nodes,
    }

    metrics = json.loads((EVAL_ROOT / "baseline-metrics.json").read_text())
    opportunity = json.loads((EVAL_ROOT / "planned-opportunity-summary.json").read_text())
    assert metrics["canonical_records"] == sum(snapshot["corpus"]["records_by_museum"].values())
    assert metrics["record_counts_by_museum"] == snapshot["corpus"]["records_by_museum"]

    def assert_ratio(value: dict, numerator: int, denominator: int) -> None:
        assert value["numerator"] == numerator
        assert value["denominator"] == denominator
        assert value["value"] == pytest.approx(numerator / denominator)

    for museum, row in metrics["per_museum"].items():
        total = snapshot["corpus"]["records_by_museum"][museum]
        extracted = row["extracted_site_text_evidence_records"]
        linked = row["records_with_unique_site_link"]
        assert row["canonical_records"] == total
        assert row["no_extracted_site_evidence_records"] + extracted == total
        assert row["extracted_site_text_without_unique_site_link"] + linked == extracted
        assert sum(row["resolution_state_counts"].values()) == total
        assert_ratio(row["extracted_site_text_availability_rate"], extracted, total)
        assert_ratio(row["overall_linkability"], linked, total)
        assert_ratio(row["extracted_site_text_conditional_linkability"], linked, extracted)
        ceiling = row["absolute_authority_only_maximum_measurable_gain"]
        assert ceiling["records"] == extracted - linked
        assert_ratio(ceiling["overall_percentage_point_ceiling"], extracted - linked, total)
        assert_ratio(ceiling["conditional_percentage_point_ceiling"], extracted - linked, extracted)

    def assert_connectivity(block: dict) -> None:
        shared = set(block["shared_target_ids"])
        assert block["shared_node_count"] == len(shared)
        assert block["shared_node_scope_counts"] == dict(
            sorted(Counter(scope_by_target[target] for target in shared).items())
        )
        for museum, side in block["sides"].items():
            connected = side["connected_records"]
            assert connected == sum(side["mutually_exclusive_scope_counts"].values())
            assert_ratio(
                side["overall_connection_rate"], connected,
                snapshot["corpus"]["records_by_museum"][museum],
            )
            assert_ratio(
                side["extracted_site_text_conditional_connection_rate"], connected,
                metrics["per_museum"][museum]["extracted_site_text_evidence_records"],
            )
        for museum, concentration in block["concentration_by_museum_side"].items():
            assert concentration["shared_node_count"] == len(shared)
            assert concentration["distinct_connected_records"] == block["sides"][museum]["connected_records"]
            hhi = concentration["node_incidence_hhi"]
            assert hhi["denominator"] == concentration["node_incidence_total"] ** 2
            assert hhi["value"] == pytest.approx(hhi["numerator"] / hhi["denominator"])
            for k in ("1", "5", "10"):
                top = concentration["top_k_unique_record_concentration"][k]
                assert len(top["selected_target_ids"]) <= min(int(k), len(shared))
                assert set(top["selected_target_ids"]) <= shared
                assert_ratio(
                    top["ratio"], top["ratio"]["numerator"],
                    concentration["distinct_connected_records"],
                )

    for pair in metrics["connectivity"]["pairs"].values():
        assert_connectivity(pair)
    assert_connectivity(metrics["connectivity"]["all_three"])

    for museum, row in opportunity["per_museum"].items():
        partition = row["baseline_record_scope_counts"]
        assert row["intent_to_treat_record_count"] == sum(partition.values())
        maximum = row["new_record_link_ceiling_records"] + row["strict_refinement_reassignment_ceiling_records"]
        assert row["maximum_credited_affected_records"] == maximum
        assert_ratio(
            row["maximum_overall_effect"], maximum,
            snapshot["corpus"]["records_by_museum"][museum],
        )
        assert_ratio(
            row["maximum_extracted_site_text_conditional_effect"], maximum,
            metrics["per_museum"][museum]["extracted_site_text_evidence_records"],
        )
    for pair in opportunity["pair_side_ceilings"].values():
        for side in pair["sides"].values():
            partition = side["baseline_pair_partition"]
            denominator = partition["no_baseline_pair_connection"] + partition["baseline_broad_only"]
            assert side["credited_effect_opportunity_denominator"] == denominator
            assert side["minimum_credited_affected_records_for_continue"] == (denominator + 9) // 10


def test_release_manifest_authenticates_exact_ci_surface_read_only() -> None:
    before = {
        path.relative_to(REPO_ROOT).as_posix(): (path.stat().st_size, sha256(path))
        for path in EVAL_ROOT.rglob("*") if path.is_file() and "__pycache__" not in path.parts
    }
    result = verify_release(REPO_ROOT)
    after = {
        path.relative_to(REPO_ROOT).as_posix(): (path.stat().st_size, sha256(path))
        for path in EVAL_ROOT.rglob("*") if path.is_file() and "__pycache__" not in path.parts
    }
    assert result["verified_file_count"] > 30
    assert before == after


def test_every_machine_formula_and_decision_threshold_matches_executable_values() -> None:
    prereg = json.loads((EVAL_ROOT / "preregistration.json").read_text())
    assert {
        key: value["expression"] for key, value in prereg["metric_formulas"].items()
    } == {
        "extracted_site_text_availability": "|X_m| / |A_m|",
        "overall_linkability": "|L_m| / |A_m|",
        "extracted_site_text_conditional_linkability": "|L_m| / |X_m|",
        "blocking_ambiguity": "|{r in X_m: direct targets empty and any site mention ambiguous}| / |X_m|",
        "planned_maximum_overall_effect": "(|new-link-eligible records in O_m| + |broad-only strict-refinement-eligible records in O_m|) / |A_m|",
        "planned_maximum_extracted_site_text_conditional_effect": "(|new-link-eligible records in O_m| + |broad-only strict-refinement-eligible records in O_m|) / |X_m|",
        "pair_side_coverage_overall": "D_(m->n) / |A_m|",
        "pair_side_coverage_extracted_site_text_conditional": "D_(m->n) / |X_m|",
        "top_k_concentration": "|union of museum-side records incident on its top-k shared identity classes| / |union of museum-side records incident on all its shared identity classes|",
        "hhi": "sum_j(I_j^2) / (sum_j I_j)^2",
    }
    assert prereg["machine_thresholds"] == {
        "ambiguity_maximum_increase": {
            "numerator": AMBIGUITY_MAXIMUM_INCREASE.numerator,
            "denominator": AMBIGUITY_MAXIMUM_INCREASE.denominator,
        },
        "concentration_maximum_increase": {
            "numerator": CONCENTRATION_MAXIMUM_INCREASE.numerator,
            "denominator": CONCENTRATION_MAXIMUM_INCREASE.denominator,
        },
        "minimum_gained_distinct_specific_identity_classes": MINIMUM_GAINED_IDENTITIES,
        "minimum_affected_opportunity_fraction": {
            "numerator": MINIMUM_AFFECTED_FRACTION.numerator,
            "denominator": MINIMUM_AFFECTED_FRACTION.denominator,
        },
        "minimum_reviews_per_credited_decision": REVIEWS_PER_CREDITED_DECISION,
        "opportunity_museum_protection_signatures": OPPORTUNITY_MUSEUM_PROTECTION,
        "opportunity_total_signatures": OPPORTUNITY_TOTAL_SIGNATURES,
    }
    assert prereg["ordered_decision_rule"]["precedence"] == [
        "INVALID", "REDESIGN", "CONTINUE", "STOP"
    ]
    assert prereg["ordered_decision_rule"]["raw_link_rate_growth_can_satisfy_continue"] is False
    assert prereg["ordered_decision_rule"]["museum_equality_required"] is False
    assert prereg["ordered_decision_rule"]["narrowness_without_support_can_satisfy_continue"] is False
