"""Adversarial unit checks for candidate-contract invariants.

These purpose-built records and keys test control flow only. They are not Hapi corpus
evidence and never satisfy the release-pinned production trust policy.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

_CONTRACT_PATH = Path(__file__).with_name("test_site_graph_v0_contract.py")
_SPEC = importlib.util.spec_from_file_location("_site_graph_contract_fixture", _CONTRACT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
contract = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = contract
_SPEC.loader.exec_module(contract)

EVAL_ROOT = contract.EVAL_ROOT
compare_candidate = contract.compare_candidate_module
CandidateGitError = compare_candidate.CandidateGitError
ed25519_key_id = compare_candidate.ed25519_key_id
verify_ed25519_signature = compare_candidate.verify_ed25519_signature


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, bytes):
        path.write_bytes(value)
    else:
        path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def _reference(repo: Path, commit: str, path: str) -> dict:
    raw = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout
    return {
        "path": path,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_oid": _git(repo, "rev-parse", f"{commit}:{path}"),
    }


def test_test_only_ed25519_primitive_verifies_exact_bytes_and_rejects_tampering() -> None:
    private_key = Ed25519PrivateKey.generate()
    public_raw = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    public_base64 = base64.b64encode(public_raw).decode("ascii")
    receipt = b'{"test_only":true}\n'
    signature = private_key.sign(receipt)
    assert ed25519_key_id(public_base64) == hashlib.sha256(public_raw).hexdigest()
    verify_ed25519_signature(
        receipt, signature, public_key_base64=public_base64
    )
    with pytest.raises(CandidateGitError, match="verification failed"):
        verify_ed25519_signature(
            receipt + b" ", signature, public_key_base64=public_base64
        )


def test_production_trust_root_fails_closed_while_not_configured() -> None:
    with pytest.raises(CandidateGitError, match="NOT_CONFIGURED"):
        compare_candidate._load_trusted_attestor_policy(
            contract.REPO_ROOT, EVAL_ROOT / "schemas"
        )


def test_link_credit_requires_exact_private_opportunity_binding(tmp_path: Path) -> None:
    case = contract._comparator_case(tmp_path)
    case["candidate"]["records"][0]["direct_links"][0][
        "opportunity_binding_sha256"
    ] = "f" * 64
    report = contract._run_case(case)
    assert report["outcome"] == "INVALID"
    assert any("exact private opportunity" in error for error in report["integrity"]["errors"])


def test_pair_credit_requires_same_exact_opportunity_binding(tmp_path: Path) -> None:
    case = contract._comparator_case(tmp_path)
    row = case["private_opportunity"]["credited_pair_opportunity_memberships"][
        "met__brooklyn"
    ]["sides"]["met"][0]
    row["opportunity_bindings"] = copy.deepcopy(row["opportunity_bindings"])
    row["opportunity_bindings"][0]["opportunity_binding_sha256"] = "e" * 64
    report = contract._run_case(case)
    assert report["outcome"] == "INVALID"
    assert any("pair-side opportunity binding" in error for error in report["integrity"]["errors"])


def test_hierarchy_cannot_cherry_pick_one_of_a_targets_source_records(
    tmp_path: Path,
) -> None:
    case = contract._comparator_case(tmp_path)
    snapshot = case["snapshots"][0]
    snapshot["records"].append(
        {
            "source_record_id": "source-specific-2-z",
            "target_id": "specific-2",
            "authority_identity_locator": "logic:authority:specific-2",
            "raw_source_types": ["archaeological-site"],
            "parent_ids": ["broad-0"],
            "child_ids": [],
            "authority_citations": ["logic:specific-2-z"],
        }
    )
    snapshot["records"].sort(key=lambda row: row["source_record_id"])
    snapshot["completeness"]["record_count"] = len(snapshot["records"])
    snapshot["completeness"]["records_canonical_sha256"] = contract.canonical_sha256(
        snapshot["records"]
    )
    report = contract._run_case(case)
    assert report["outcome"] == "INVALID"
    assert any("all and only its source records" in error for error in report["integrity"]["errors"])


def test_inverse_parent_edges_are_required_in_derived_children(tmp_path: Path) -> None:
    case = contract._comparator_case(tmp_path)
    snapshot = case["snapshots"][0]
    snapshot["records"].append(
        {
            "source_record_id": "source-specific-1-child",
            "target_id": "specific-1-child",
            "authority_identity_locator": "logic:authority:specific-1-child",
            "raw_source_types": ["archaeological-site"],
            "parent_ids": ["specific-1"],
            "child_ids": [],
            "authority_citations": ["logic:specific-1-child"],
        }
    )
    snapshot["records"].sort(key=lambda row: row["source_record_id"])
    snapshot["completeness"]["record_count"] = len(snapshot["records"])
    snapshot["completeness"]["records_canonical_sha256"] = contract.canonical_sha256(
        snapshot["records"]
    )
    case["hierarchy"]["nodes"].append(
        {
            "target_id": "specific-1-child",
            "candidate_e55_type": "archaeological_site",
            "child_ids": [],
            "ancestor_target_ids": ["broad-0", "specific-1"],
            "source_snapshot_ids": ["logic-source"],
            "source_record_ids": ["source-specific-1-child"],
        }
    )
    report = contract._run_case(case)
    assert report["outcome"] == "INVALID"
    assert any("inverse-parent edges" in error for error in report["integrity"]["errors"])


def test_same_authority_locator_auto_unions_aliases(tmp_path: Path) -> None:
    case = contract._comparator_case(tmp_path)
    case["snapshots"][0]["records"][2]["authority_identity_locator"] = (
        case["snapshots"][0]["records"][1]["authority_identity_locator"]
    )
    case["snapshots"][0]["completeness"]["records_canonical_sha256"] = (
        contract.canonical_sha256(case["snapshots"][0]["records"])
    )
    distinct = case["relations"]["relations"].pop()
    del case["decisions"][distinct["review_decision_key"]]
    report = contract._run_case(case)
    assert report["outcome"] == "STOP"
    assert report["pairs"]["met__brooklyn"][
        "gained_credited_specific_shared_identity_class_count"
    ] == 1


def test_distinct_counted_classes_require_positive_review_evidence(tmp_path: Path) -> None:
    case = contract._comparator_case(tmp_path)
    distinct = case["relations"]["relations"].pop()
    del case["decisions"][distinct["review_decision_key"]]
    report = contract._run_case(case)
    assert report["outcome"] == "INVALID"
    assert any("positive distinctness" in error for error in report["integrity"]["errors"])


def test_reviewed_equivalent_replacement_is_unchanged_and_remains_broad(
    tmp_path: Path,
) -> None:
    case = contract._comparator_case(tmp_path)
    strict = next(
        relation
        for relation in case["relations"]["relations"]
        if relation["left_target_id"] == "specific-1"
        and relation["relation"] == "strict_refinement"
    )
    case["relations"]["relations"].remove(strict)
    del case["decisions"][strict["review_decision_key"]]
    subject = {
        "left_target_id": "specific-1",
        "right_target_id": "broad-0",
        "relation": "equivalent",
    }
    key = contract.decision_key("equivalence_support", subject)
    case["relations"]["relations"].append(
        {"relation_id": "equivalent-broad-alias", **subject, "review_decision_key": key}
    )
    case["decisions"][key] = {
        "decision_kind": "equivalence_support",
        "subject": subject,
        "supported": True,
        "disagreement": False,
    }
    report = contract._run_case(case)
    assert report["outcome"] != "INVALID"
    events = {
        row["artifact_id"]: row["event"] for row in report["event_records"]
    }
    assert events["met-a"] == "unchanged"
    assert events["brooklyn-a"] == "unchanged"
    share = report["pairs"]["met__brooklyn"]["sides"]["met"][
        "candidate_broad_only_conditional_share"
    ]
    assert share == {"numerator": 1, "denominator": 2, "value": 0.5}


def test_same_target_pair_cannot_be_both_equivalent_and_strict_refinement(
    tmp_path: Path,
) -> None:
    case = contract._comparator_case(tmp_path)
    subject = {
        "left_target_id": "specific-1",
        "right_target_id": "broad-0",
        "relation": "equivalent",
    }
    key = contract.decision_key("equivalence_support", subject)
    case["relations"]["relations"].append(
        {
            "relation_id": "contradictory-equivalence",
            **subject,
            "review_decision_key": key,
        }
    )
    case["decisions"][key] = {
        "decision_kind": "equivalence_support",
        "subject": subject,
        "supported": True,
        "disagreement": False,
    }
    report = contract._run_case(case)
    assert report["outcome"] == "INVALID"
    assert any(
        "duplicated or contradictory" in error
        for error in report["integrity"]["errors"]
    )


def test_candidate_locator_equal_to_frozen_baseline_locator_auto_unions(
    tmp_path: Path,
) -> None:
    case = contract._comparator_case(tmp_path)
    specific_record = next(
        row for row in case["snapshots"][0]["records"] if row["target_id"] == "specific-1"
    )
    specific_record["authority_identity_locator"] = "broad-0"
    case["snapshots"][0]["completeness"]["records_canonical_sha256"] = (
        contract.canonical_sha256(case["snapshots"][0]["records"])
    )
    strict = next(
        relation
        for relation in case["relations"]["relations"]
        if relation["left_target_id"] == "specific-1"
        and relation["relation"] == "strict_refinement"
    )
    case["relations"]["relations"].remove(strict)
    del case["decisions"][strict["review_decision_key"]]
    report = contract._run_case(case)
    assert report["outcome"] != "INVALID"
    events = {
        row["artifact_id"]: row["event"] for row in report["event_records"]
    }
    assert events["met-a"] == "unchanged"
    assert events["brooklyn-a"] == "unchanged"


def _llm_review_fixture(
    tmp_path: Path, *, reuse_prompt: bool = False, empty_response: bool = False, post_hoc_audit: bool = False
) -> tuple[Path, str, str, dict, dict[str, dict]]:
    repo = tmp_path / "llm-review"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "logic@example.invalid")
    _git(repo, "config", "user.name", "Logic Fixture")
    subject = {
        "artifact_id": "logic-artifact",
        "target_id": "logic-target",
        "opportunity_id": "opp-logic",
        "opportunity_binding_sha256": "a" * 64,
    }
    key = contract.decision_key("link_support", subject)
    prompt_paths = ["frozen/prompt-a.txt", "frozen/prompt-b.txt"]
    audit_paths = ["frozen/audit-a.json", "frozen/audit-b.json"]
    for index, path in enumerate(prompt_paths):
        _write(repo / path, f"opaque prompt {index}\n".encode())
    _git(repo, "add", "frozen")
    _git(repo, "commit", "-qm", "prompts")
    prompt_commit = _git(repo, "rev-parse", "HEAD")
    prompt_refs = [_reference(repo, prompt_commit, path) for path in prompt_paths]
    for index, path in enumerate(audit_paths):
        if post_hoc_audit and index == 1:
            continue
        _write(
            repo / path,
            {
                "schema_version": "site-graph-v0-prompt-leakage-audit/2",
                "audit_id": f"audit-{index}",
                "review_id": f"review-{index}",
                "review_invocation_id": f"invoke-{index}",
                "decision_key": key,
                "decision_kind": "link_support",
                "subject": subject,
                "prompt": prompt_refs[index],
                "passed": True,
                "opaque_shuffled_candidate_ids": True,
                "audit_method": "test-only exact prompt audit",
                "auditor_id": f"auditor-{index}",
                "executed_at_utc": "2026-08-28T00:00:00Z",
                "findings": [],
            },
        )
    _git(repo, "add", "frozen")
    _git(repo, "commit", "-qm", "pre-generation audits")
    freeze_commit = _git(repo, "rev-parse", "HEAD")
    if post_hoc_audit:
        _write(
            repo / audit_paths[1],
            {
                "schema_version": "site-graph-v0-prompt-leakage-audit/2",
                "audit_id": "audit-1",
                "review_id": "review-1",
                "review_invocation_id": "invoke-1",
                "decision_key": key,
                "decision_kind": "link_support",
                "subject": subject,
                "prompt": prompt_refs[1],
                "passed": True,
                "opaque_shuffled_candidate_ids": True,
                "audit_method": "post-hoc test audit",
                "auditor_id": "auditor-1",
                "executed_at_utc": "2026-08-28T00:01:00Z",
                "findings": [],
            },
        )
    for index in range(2):
        _write(repo / f"result/input-{index}.txt", f"opaque input {index}\n".encode())
        response = b"\n" if empty_response and index == 1 else f"raw response {index}\n".encode()
        _write(repo / f"result/response-{index}.txt", response)
    _git(repo, "add", "frozen", "result")
    _git(repo, "commit", "-qm", "review interactions")
    interaction_commit = _git(repo, "rev-parse", "HEAD")
    audit_refs = [_reference(repo, interaction_commit, path) for path in audit_paths]
    result_refs = [
        (
            _reference(repo, interaction_commit, f"result/input-{index}.txt"),
            _reference(repo, interaction_commit, f"result/response-{index}.txt"),
        )
        for index in range(2)
    ]
    review_paths = []
    for index in range(2):
        prompt_ref = prompt_refs[0] if reuse_prompt and index == 1 else prompt_refs[index]
        review_path = f"result/review-{index}.json"
        review_paths.append(review_path)
        _write(
            repo / review_path,
            {
                "schema_version": "site-graph-v0-review-artifact/2",
                "review_id": f"review-{index}",
                "decision_key": key,
                "decision_kind": "link_support",
                "subject": subject,
                "reviewer": {
                    "reviewer_id": f"reviewer-{index}",
                    "independence_group": f"group-{index}",
                },
                "outcome": "supported",
                "method": "llm",
                "citations": [
                    {
                        "source_id": f"authority-{index}",
                        "source_kind": "independent_authority",
                        "locator": f"locator-{index}",
                        "evidence_summary": f"logic evidence {index}",
                        "originating_museum": False,
                    }
                ],
                "reasoning": f"test-only reasoning {index}",
                "llm_interaction": {
                    "review_invocation_id": f"invoke-{index}",
                    "model": {
                        "provider": "test-only",
                        "model_selector": "test-model",
                        "backend_model_id": "test-model-2026-08-28",
                        "snapshot_exposure": "EXPOSED",
                        "snapshot_id": "test-model-2026-08-28",
                        "snapshot_date": "2026-08-28",
                    },
                    "parameters": {
                        "reported_parameters": {"temperature": 0},
                        "unexposed_parameters": [],
                        "completeness_statement": "all test-harness parameters are reported",
                    },
                    "prompt": prompt_ref,
                    "input": result_refs[index][0],
                    "raw_response": result_refs[index][1],
                    "prompt_leakage_audit": {
                        "passed": True,
                        "opaque_shuffled_candidate_ids": True,
                        "artifact": audit_refs[index],
                    },
                    "interaction_binding_sha256": "",
                },
            },
        )
        review_value = json.loads((repo / review_path).read_text())
        interaction = review_value["llm_interaction"]
        interaction["interaction_binding_sha256"] = contract.canonical_sha256(
            {
                "review_id": review_value["review_id"],
                "review_invocation_id": interaction["review_invocation_id"],
                "decision_key": key,
                "decision_kind": "link_support",
                "subject": subject,
                "model": interaction["model"],
                "parameters": interaction["parameters"],
                "prompt": interaction["prompt"],
                "input": interaction["input"],
                "raw_response": interaction["raw_response"],
                "prompt_leakage_audit": interaction["prompt_leakage_audit"]["artifact"],
            }
        )
        _write(repo / review_path, review_value)
    _git(repo, "add", "result")
    _git(repo, "commit", "-qm", "review artifacts")
    result_commit = _git(repo, "rev-parse", "HEAD")
    review_refs = []
    for path in review_paths:
        value = json.loads((repo / path).read_text())
        review_refs.append(
            {
                **_reference(repo, result_commit, path),
                "canonical_record_sha256": contract.canonical_sha256(value),
            }
        )
    ledger = {
        "schema_version": "site-graph-v0-review-ledger/3",
        "review_scope": "census_of_every_credited_link_refinement_equivalence_and_positive_distinctness_decision",
        "decisions": [
            {
                "decision_key": key,
                "decision_kind": "link_support",
                "subject": subject,
                "review_artifacts": review_refs,
            }
        ],
    }
    frozen_files = {}
    for index in range(2):
        frozen_files[prompt_paths[index]] = {"role": "review_prompt", **prompt_refs[index]}
        frozen_files[audit_paths[index]] = {
            "role": "prompt_leakage_audit",
            **audit_refs[index],
        }
    return repo, freeze_commit, result_commit, ledger, frozen_files


@pytest.mark.parametrize(
    ("variant", "message"),
    [
        ({"reuse_prompt": True}, "reused"),
        ({"empty_response": True}, "empty"),
        ({"post_hoc_audit": True}, "git show"),
    ],
)
def test_llm_provenance_rejects_reuse_empty_and_post_hoc_audits(
    tmp_path: Path, variant: dict, message: str
) -> None:
    repo, freeze_commit, result_commit, ledger, frozen_files = _llm_review_fixture(
        tmp_path, **variant
    )
    with pytest.raises(ValueError, match=message):
        compare_candidate._validate_review_artifacts(
            repo,
            result_commit,
            ledger,
            EVAL_ROOT / "schemas",
            freeze_commit=freeze_commit,
            frozen_files=frozen_files,
        )
