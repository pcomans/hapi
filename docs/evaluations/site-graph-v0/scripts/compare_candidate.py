#!/usr/bin/env python3
"""Authenticated production comparator plus a deterministic pure comparison core."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import combinations
from pathlib import Path

from build_baseline import build_metrics
from candidate_git import (
    CandidateGitError,
    blob_oid,
    ed25519_key_id,
    is_ancestor,
    read_authenticated_bytes,
    read_authenticated_json,
    read_bytes,
    resolve_commit,
    verify_ed25519_signature,
)
from contract_constants import (
    MAXIMUM_NEWLY_BLOCKING_FRACTION,
    CONCENTRATION_MAXIMUM_INCREASE,
    MINIMUM_AFFECTED_FRACTION,
    MINIMUM_GAINED_IDENTITIES,
    MUSEUMS,
    PAIRS,
    REVIEWS_PER_CREDITED_DECISION,
)
from integrity import verify_release
from metrics_core import TOP_K, concentration, partition_scopes, ratio
from private_ledgers import verify_private_ledgers
from review_auth import (
    ArtifactUsageTracker,
    ReviewAuthenticationError,
    authenticate_prompt_audit,
    authenticate_review_artifact,
    authenticate_semantic_prompt_audit,
    canonical_forbidden_values,
    load_reviewer_registry,
    require_distinct_registered_reviewers,
    strict_json_object,
)
from schema_validation import SchemaValidationError, validate_schema
from source_exports import (
    TRUSTED_SOURCE_EXPORTERS_RELATIVE,
    authenticate_source_export,
    load_source_exporter_policy,
)
from trusted_completion import verify_trusted_completion


EVENTS = (
    "new_link",
    "strict_refinement_reassignment",
    "additional_identity",
    "unchanged",
    "loss",
    "uncredited_change",
)
MECHANICAL_REVIEW_ANSWER_TOKENS = frozenset(
    {
        "supported",
        "unsupported",
        "uncertain",
        "equivalent",
        "distinct",
        "strict_refinement",
    }
)
ABSTENTION_REASONS = {
    "compound_expression",
    "conflicting_evidence",
    "insufficient_identity_evidence",
    "non_place_context",
    "reviewer_disagreement",
    "role_not_supported",
    "uncertain_expression",
}
TRUSTED_ATTESTORS_RELATIVE = "docs/evaluations/site-graph-v0/trusted-run-attestors.json"


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def read_records(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def decision_key(kind: str, subject: dict) -> str:
    return f"{kind}:{canonical_sha256(subject)}"


def ceil_fraction(value: int, fraction: Fraction) -> int:
    if value == 0:
        return 0
    return max(
        1,
        (value * fraction.numerator + fraction.denominator - 1)
        // fraction.denominator,
    )


class UnionFind:
    """Stable identity classes: the lexicographically smallest member is the root."""

    def __init__(self, values: set[str]):
        self.parent = {value: value for value in sorted(values)}

    def find(self, value: str) -> str:
        if value not in self.parent:
            self.parent[value] = value
        current = value
        while self.parent[current] != current:
            current = self.parent[current]
        root = current
        current = value
        while self.parent[current] != current:
            parent = self.parent[current]
            self.parent[current] = root
            current = parent
        return root

    def union(self, left: str, right: str) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root == right_root:
            return
        low, high = sorted((left_root, right_root))
        self.parent[high] = low


def _raw_type_crosswalk(crosswalk: dict, errors: list[str]) -> dict[str, tuple[str, str]]:
    """Build the executable raw-type mapping from every declared mapping section."""
    mapping: dict[str, tuple[str, str]] = {}
    for section_name, section in sorted(crosswalk.items()):
        if not isinstance(section, dict):
            continue
        for raw_type, value in sorted(section.items()):
            if not isinstance(value, dict) or set(value) != {"candidate_e55_type", "scope"}:
                continue
            mapped = (value["candidate_e55_type"], value["scope"])
            if raw_type in mapping and mapping[raw_type] != mapped:
                errors.append(f"raw source type has conflicting crosswalk entries: {raw_type}")
            mapping[raw_type] = mapped
    return mapping


def _derive_candidate_scope(
    hierarchy: dict, source_exports: list[dict], crosswalk: dict, errors: list[str]
) -> tuple[dict[str, str], dict[str, str]]:
    raw_mapping = _raw_type_crosswalk(crosswalk, errors)
    exports: dict[str, dict] = {}
    source_records: dict[str, tuple[str, dict]] = {}
    target_records: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for source_export in source_exports:
        export_id = source_export.get("source_export_id")
        if not export_id or export_id in exports:
            errors.append("authenticated source export IDs must be nonempty and unique")
            continue
        exports[export_id] = source_export
        records = source_export.get("records", [])
        completeness = source_export.get("completeness", {})
        if completeness.get("record_count") != len(records):
            errors.append(f"source export {export_id} complete record count mismatch")
        if completeness.get("records_canonical_sha256") != canonical_sha256(records):
            errors.append(f"source export {export_id} complete-record hash mismatch")
        if records != sorted(records, key=lambda row: row.get("source_record_id", "")):
            errors.append(f"source export {export_id} records are not canonically sorted")
        for record in records:
            record_id = record.get("source_record_id")
            target_id = record.get("target_id")
            if not record_id or record_id in source_records:
                errors.append("source record IDs must be nonempty and globally unique")
                continue
            if not target_id:
                errors.append(f"source record {record_id} lacks a target ID")
                continue
            for field in ("raw_source_types", "parent_ids", "child_ids", "authority_citations"):
                values = record.get(field, [])
                if values != sorted(set(values)):
                    errors.append(f"source record {record_id} {field} is not sorted/unique")
            source_records[record_id] = (export_id, record)
            target_records[target_id].append((export_id, record))

    parent_by_target: dict[str, set[str]] = defaultdict(set)
    children_by_target: dict[str, set[str]] = defaultdict(set)
    for target_id, records in target_records.items():
        for _, record in records:
            for parent in record.get("parent_ids", []):
                parent_by_target[target_id].add(parent)
                children_by_target[parent].add(target_id)
            for child in record.get("child_ids", []):
                children_by_target[target_id].add(child)
                parent_by_target[child].add(target_id)
    referenced_targets = set(parent_by_target) | set(children_by_target)
    dangling_targets = sorted(referenced_targets - set(target_records))
    if dangling_targets:
        errors.append(
            f"candidate source topology references targets without source records: {dangling_targets}"
        )
    for parent, children in sorted(children_by_target.items()):
        for child in sorted(children):
            parent_declares_child = any(
                child in record.get("child_ids", [])
                for _, record in target_records.get(parent, [])
            )
            child_declares_parent = any(
                parent in record.get("parent_ids", [])
                for _, record in target_records.get(child, [])
            )
            if parent_declares_child != child_declares_parent:
                errors.append(
                    f"candidate source topology is not inverse-closed: {parent}/{child}"
                )

    def ancestors(target_id: str) -> set[str]:
        output: set[str] = set()
        frontier = sorted(parent_by_target.get(target_id, set()))
        while frontier:
            parent = frontier.pop(0)
            if parent == target_id:
                errors.append(f"candidate source hierarchy contains a cycle at {target_id}")
                continue
            if parent in output:
                continue
            output.add(parent)
            frontier.extend(sorted(parent_by_target.get(parent, set()) - output))
        return output

    scope_by_target: dict[str, str] = {}
    locator_by_target: dict[str, str] = {}
    nodes_by_target: dict[str, dict] = {}
    for node in hierarchy.get("nodes", []):
        target_id = node.get("target_id")
        if not target_id or target_id in nodes_by_target:
            errors.append("candidate hierarchy target IDs must be nonempty and unique")
            continue
        nodes_by_target[target_id] = node
    if set(nodes_by_target) != set(target_records):
        errors.append(
            "candidate hierarchy must census every authenticated source-export target: "
            f"missing={sorted(set(target_records) - set(nodes_by_target))}, "
            f"extra={sorted(set(nodes_by_target) - set(target_records))}"
        )

    for target_id, node in sorted(nodes_by_target.items()):
        all_records = target_records.get(target_id, [])
        expected_record_ids = sorted(row["source_record_id"] for _, row in all_records)
        expected_export_ids = sorted({export_id for export_id, _ in all_records})
        if node.get("source_record_ids") != expected_record_ids:
            errors.append(
                f"candidate hierarchy {target_id} must bind all and only its source records"
            )
        if node.get("source_export_ids") != expected_export_ids:
            errors.append(
                f"candidate hierarchy {target_id} source export census mismatch"
            )
        locators = {row.get("authority_identity_locator") for _, row in all_records}
        if None in locators or len(locators) != 1:
            errors.append(f"candidate hierarchy {target_id} must have one authority locator")
        else:
            locator_by_target[target_id] = min(locators)
        raw_types = {
            raw_type
            for _, record in all_records
            for raw_type in record.get("raw_source_types", [])
        }
        unknown_types = sorted(raw_types - set(raw_mapping))
        if unknown_types:
            errors.append(
                f"candidate hierarchy {target_id} has unmapped raw source types {unknown_types}"
            )
        mapped = {raw_mapping[value] for value in raw_types if value in raw_mapping}
        mapped_e55_types = {value[0] for value in mapped}
        if node.get("candidate_e55_type") not in mapped_e55_types:
            errors.append(
                f"candidate hierarchy {target_id} E55 type is not crosswalk-derived"
            )
        expected_children = sorted(children_by_target.get(target_id, set()))
        if node.get("child_ids") != expected_children:
            errors.append(
                f"candidate hierarchy {target_id} child topology must include explicit and inverse-parent edges"
            )
        expected_ancestors = sorted(ancestors(target_id))
        if node.get("ancestor_target_ids") != expected_ancestors:
            errors.append(
                f"candidate hierarchy {target_id} ancestor topology not derived from all sources"
            )
        mapped_scopes = {value[1] for value in mapped}
        if "broad" in mapped_scopes or expected_children:
            scope = "broad"
        elif "specific_candidate" in mapped_scopes:
            scope = "specific_candidate"
        else:
            scope = "unclassified"
        vocabulary = crosswalk.get("candidate_e55_vocabulary", {}).get(scope, [])
        if node.get("candidate_e55_type") not in vocabulary:
            errors.append(
                f"candidate hierarchy {target_id} E55 type is inconsistent with "
                f"derived broad-precedence scope {scope}"
            )
        scope_by_target[target_id] = scope
    return scope_by_target, locator_by_target


def _decision_supports(
    decisions: dict[str, dict], key: object, kind: str, subject: dict
) -> bool:
    decision = decisions.get(key) if isinstance(key, str) else None
    return bool(
        decision
        and decision.get("decision_kind") == kind
        and decision.get("subject") == subject
        and decision.get("supported") is True
    )


def _require_citation_in_authenticated_export(
    citation: dict, source_export: dict, *, label: str
) -> str:
    """Bind one claimed independent citation to exact trusted-export bytes."""
    if (
        source_export.get("originating_museum") is not False
        or citation.get("source_kind") != source_export.get("source_kind")
    ):
        raise ReviewAuthenticationError(
            "review citation source kind or museum independence differs "
            f"from authenticated export: {label}"
        )
    for record in source_export.get("records", []):
        if (
            record.get("source_record_id") == citation.get("source_id")
            and citation.get("locator") in record.get("authority_citations", [])
        ):
            return record["target_id"]
    raise ReviewAuthenticationError(
        f"review citation source/locator is absent from authenticated export: {label}"
    )


def _require_subject_target_citation_coverage(
    subject: dict, cited_target_ids: set[str], *, label: str
) -> None:
    """Require exact authenticated source-record coverage for every subject target."""
    subject_target_ids = {
        value
        for field, value in subject.items()
        if (field == "target_id" or field.endswith("_target_id"))
        and isinstance(value, str)
        and value
    }
    if not subject_target_ids:
        raise ReviewAuthenticationError(
            f"review decision subject has no target IDs to cite: {label}"
        )
    missing = sorted(subject_target_ids - cited_target_ids)
    if missing:
        raise ReviewAuthenticationError(
            "review citations lack authenticated source-record coverage for subject "
            f"targets {missing}: {label}"
        )


def _fraction_from_ratio(value: dict) -> Fraction:
    denominator = value.get("denominator", 0)
    return Fraction(value.get("numerator", 0), denominator) if denominator else Fraction(0)


def _post_candidate_connectivity(
    class_links_by_artifact: dict[str, set[str]],
    artifacts_by_museum: dict[str, set[str]],
    record_counts: dict[str, int],
    evidence_counts: dict[str, int],
    identity_scope: dict[str, str],
) -> dict:
    """Compute every preregistered connectivity aggregation over identity classes."""
    classes_by_museum = {
        museum: set().union(
            *(class_links_by_artifact[artifact] for artifact in artifacts_by_museum[museum])
        )
        if artifacts_by_museum[museum]
        else set()
        for museum in MUSEUMS
    }

    def side(museum: str, eligible: set[str]) -> dict:
        connected = {
            artifact
            for artifact in artifacts_by_museum[museum]
            if class_links_by_artifact[artifact] & eligible
        }
        partitions = Counter(
            partition_scopes(
                {
                    identity_scope[root]
                    for root in class_links_by_artifact[artifact] & eligible
                }
            )
            for artifact in connected
        )
        return {
            "connected_records": len(connected),
            "overall_connection_rate": ratio(
                len(connected), record_counts[museum]
            ),
            "extracted_site_text_conditional_connection_rate": ratio(
                len(connected), evidence_counts[museum]
            ),
            "mutually_exclusive_scope_counts": {
                key: partitions[key]
                for key in (
                    "specific_candidate_present",
                    "broad_only",
                    "unclassified_only",
                )
            },
        }

    pairs: dict[str, dict] = {}
    for left, right in PAIRS:
        shared = classes_by_museum[left] & classes_by_museum[right]
        pairs[f"{left}__{right}"] = {
            "shared_identity_class_ids": sorted(shared),
            "shared_identity_class_count": len(shared),
            "sides": {
                left: side(left, shared),
                right: side(right, shared),
            },
        }

    all_three = set.intersection(
        *(classes_by_museum[museum] for museum in MUSEUMS)
    )
    class_museums: dict[str, set[str]] = defaultdict(set)
    for museum, roots in classes_by_museum.items():
        for root in roots:
            class_museums[root].add(museum)
    any_two = {
        root for root, museums in class_museums.items() if len(museums) >= 2
    }
    exact_combinations = Counter(
        "+".join(sorted(museums))
        for museums in class_museums.values()
        if len(museums) >= 2
    )

    def aggregation(eligible: set[str]) -> dict:
        return {
            "shared_identity_class_ids": sorted(eligible),
            "shared_identity_class_count": len(eligible),
            "sides": {
                museum: side(museum, eligible) for museum in MUSEUMS
            },
        }

    return {
        "pairs": pairs,
        "all_three": aggregation(all_three),
        "any_two_or_more": {
            **aggregation(any_two),
            "exact_museum_combination_counts": dict(
                sorted(exact_combinations.items())
            ),
        },
    }


def _logic_only_provenance(outcome: str) -> dict:
    return {
        "evidence_scope": "LOGIC_ONLY_TEST_INPUT",
        "archive_sha256": "LOGIC_ONLY_NO_ARCHIVE",
        "snapshot_acquisition_integrity": "NOT_APPLICABLE_LOGIC_ONLY",
        "upstream_production_lineage": "NOT_APPLICABLE_LOGIC_ONLY",
        "overall_contract_status": "NOT_APPLICABLE_LOGIC_ONLY",
        "downstream_product_verdict": outcome,
    }


def _invalid_report(
    errors: list[str], provenance_status: dict | None = None
) -> dict:
    return {
        "schema_version": "site-graph-v0-comparison-report/4",
        "outcome": "INVALID",
        "ordered_decision_trace": [
            {"step": "integrity", "passed": False, "errors": sorted(set(errors))}
        ],
        "integrity": {"passed": False, "errors": sorted(set(errors))},
        "safety_gates": {},
        "event_counts": {event: 0 for event in EVENTS},
        "event_records": [],
        "reassignment_edge_modes": {},
        "per_museum": {},
        "post_candidate_metrics": {},
        "pairs": {},
        "ambiguity_and_abstention": {},
        "run_binding": None,
        "provenance_status": provenance_status or _logic_only_provenance("INVALID"),
    }


def compare_core(
    baseline_records: list[dict],
    metrics: dict,
    node_scope: dict,
    opportunity_summary: dict,
    private_opportunity: dict,
    crosswalk: dict,
    candidate: dict,
    hierarchy: dict,
    source_exports: list[dict],
    relation_ledger: dict,
    decisions: dict[str, dict],
) -> dict:
    """Pure deterministic comparator. Fixture callers make no corpus claim."""
    errors: list[str] = []
    threshold = opportunity_summary.get("minimum_affected_opportunity_fraction")
    expected_threshold = {
        "numerator": MINIMUM_AFFECTED_FRACTION.numerator,
        "denominator": MINIMUM_AFFECTED_FRACTION.denominator,
    }
    if threshold != expected_threshold:
        errors.append("public opportunity minimum fraction differs from executable constant")

    baseline_by_id = {row.get("artifact_id"): row for row in baseline_records}
    if None in baseline_by_id or len(baseline_by_id) != len(baseline_records):
        errors.append("baseline record IDs must be nonempty and unique")
    for artifact_id, row in baseline_by_id.items():
        status_counts = row.get("site_mention_status_counts", {})
        mention_count = row.get("site_mention_count")
        if (
            not isinstance(status_counts, dict)
            or not isinstance(mention_count, int)
            or mention_count < 0
            or sum(status_counts.values()) != mention_count
            or any(
                status not in {"resolved", "ambiguous", "unmatched"}
                or not isinstance(count, int)
                or count < 0
                for status, count in status_counts.items()
            )
        ):
            errors.append(
                f"baseline {artifact_id} has invalid complete site-mention status accounting"
            )
            continue
        has_any_ambiguity = status_counts.get("ambiguous", 0) > 0
        has_blocking_ambiguity = (
            not row.get("baseline_site_target_ids") and has_any_ambiguity
        )
        if row.get("has_any_ambiguity") is not has_any_ambiguity:
            errors.append(
                f"baseline {artifact_id} has_any_ambiguity differs from the frozen predicate"
            )
        if row.get("has_blocking_ambiguity") is not has_blocking_ambiguity:
            errors.append(
                f"baseline {artifact_id} has_blocking_ambiguity differs from the frozen predicate"
            )
    baseline_scope = {
        row.get("target_id"): row.get("scope_class") for row in node_scope.get("nodes", [])
    }
    if None in baseline_scope or len(baseline_scope) != len(node_scope.get("nodes", [])):
        errors.append("baseline node scope target IDs must be nonempty and unique")

    derived_scope, candidate_authority_locator = _derive_candidate_scope(
        hierarchy, source_exports, crosswalk, errors
    )
    authority_locator: dict[str, str] = {}
    for row in node_scope.get("nodes", []):
        target_id = row.get("target_id")
        locator = row.get("authority_identity_locator")
        if not isinstance(locator, str) or not locator:
            errors.append(f"baseline target {target_id} lacks an authenticated authority locator")
            continue
        authority_locator[target_id] = locator
    for target_id, locator in candidate_authority_locator.items():
        if target_id in authority_locator and authority_locator[target_id] != locator:
            errors.append(f"candidate target {target_id} authority locator conflicts with baseline")
        authority_locator[target_id] = locator
    for target_id in sorted(set(derived_scope) & set(baseline_scope)):
        if derived_scope[target_id] != baseline_scope[target_id]:
            errors.append(
                f"existing target {target_id} cannot be relabeled by candidate sources"
            )
    target_scope = dict(baseline_scope)
    for target_id, scope in derived_scope.items():
        target_scope.setdefault(target_id, scope)

    itt_by_id: dict[str, dict] = {}
    itt_bindings_by_id: dict[str, set[tuple[str, str]]] = {}
    museum_by_id: dict[str, str] = {}
    for museum in MUSEUMS:
        rows = private_opportunity.get("intent_to_treat_records_by_museum", {}).get(museum, [])
        for row in rows:
            artifact_id = row.get("artifact_id")
            if not artifact_id or artifact_id in itt_by_id:
                errors.append("private ITT artifact IDs must be nonempty and unique by museum")
                continue
            if artifact_id not in baseline_by_id or baseline_by_id[artifact_id].get("museum") != museum:
                errors.append(f"private ITT artifact {artifact_id} baseline museum mismatch")
            bindings = row.get("opportunity_bindings", [])
            normalized_bindings = [
                (binding.get("opportunity_id"), binding.get("opportunity_binding_sha256"))
                for binding in bindings
            ]
            if (
                not normalized_bindings
                or any(not left or not right for left, right in normalized_bindings)
                or normalized_bindings != sorted(set(normalized_bindings))
            ):
                errors.append(
                    f"private ITT artifact {artifact_id} opportunity bindings must be nonempty, sorted, and unique"
                )
            itt_by_id[artifact_id] = row
            itt_bindings_by_id[artifact_id] = set(normalized_bindings)
            museum_by_id[artifact_id] = museum

    binding_mentions: dict[tuple[str, str, str], list[dict]] = {}
    for opportunity in private_opportunity.get("opportunities", []):
        opportunity_id = opportunity.get("opportunity_id")
        for membership in opportunity.get("artifact_memberships", []):
            artifact_id = membership.get("artifact_id")
            binding_sha256 = membership.get("opportunity_binding_sha256")
            key = (artifact_id, opportunity_id, binding_sha256)
            mentions = membership.get("mentions", [])
            if (
                not all(isinstance(value, str) and value for value in key)
                or key in binding_mentions
                or mentions
                != sorted(mentions, key=lambda row: row.get("mention_id", ""))
                or not mentions
            ):
                errors.append(
                    "private opportunity mention bindings must be nonempty, unique, and "
                    "sorted by mention ID"
                )
                continue
            mention_ids = [row.get("mention_id") for row in mentions]
            if (
                any(not mention_id for mention_id in mention_ids)
                or len(mention_ids) != len(set(mention_ids))
                or any(
                    row.get("status") not in {"resolved", "ambiguous", "unmatched"}
                    for row in mentions
                )
            ):
                errors.append(
                    f"private opportunity {opportunity_id}/{artifact_id} has invalid mention census"
                )
            binding_mentions[key] = mentions
    expected_binding_keys = {
        (artifact_id, opportunity_id, binding_sha256)
        for artifact_id, bindings in itt_bindings_by_id.items()
        for opportunity_id, binding_sha256 in bindings
    }
    if set(binding_mentions) != expected_binding_keys:
        errors.append(
            "private opportunity ledger mention census differs from exact ITT bindings: "
            f"missing={len(expected_binding_keys - set(binding_mentions))}, "
            f"extra={len(set(binding_mentions) - expected_binding_keys)}"
        )

    candidate_records = candidate.get("records", [])
    candidate_by_id: dict[str, dict] = {}
    for record in candidate_records:
        artifact_id = record.get("artifact_id")
        if not artifact_id or artifact_id in candidate_by_id:
            errors.append("candidate artifact IDs must be nonempty and unique")
            continue
        candidate_by_id[artifact_id] = record
    if set(candidate_by_id) != set(itt_by_id):
        errors.append(
            "candidate result must census exact private ITT membership: "
            f"missing={len(set(itt_by_id) - set(candidate_by_id))}, "
            f"extra={len(set(candidate_by_id) - set(itt_by_id))}"
        )

    all_targets = set(baseline_scope) | set(derived_scope)
    relations = relation_ledger.get("relations", [])
    supported_equivalences: list[tuple[str, str]] = []
    supported_distinct: set[tuple[str, str]] = set()
    supported_strict: dict[tuple[str, str], dict] = {}
    relation_ids: set[str] = set()
    relation_pairs: set[tuple[str, str]] = set()
    referenced_decisions: set[str] = set()
    unresolved_disagreements: set[str] = set()
    for relation in relations:
        relation_id = relation.get("relation_id")
        left, right = relation.get("left_target_id"), relation.get("right_target_id")
        kind = relation.get("relation")
        review_key = relation.get("review_decision_key")
        if not relation_id or relation_id in relation_ids or left == right:
            errors.append("relations must have unique IDs and distinct targets")
            continue
        relation_ids.add(relation_id)
        if left not in all_targets or right not in all_targets:
            errors.append(f"relation {relation_id} references unknown target")
            continue
        pair = tuple(sorted((left, right)))
        if pair in relation_pairs:
            errors.append(f"relation pair is duplicated or contradictory: {pair}")
            continue
        relation_pairs.add(pair)
        decision_kind = {
            "equivalent": "equivalence_support",
            "distinct": "distinctness_support",
            "strict_refinement": "strict_refinement_support",
        }.get(kind)
        if decision_kind is None:
            errors.append(f"relation {relation_id} has an unsupported relation kind")
            continue
        subject = {"left_target_id": left, "right_target_id": right, "relation": kind}
        expected_key = decision_key(decision_kind, subject)
        if review_key != expected_key or review_key not in decisions:
            errors.append(f"relation {relation_id} lacks its exact two-review census decision")
            continue
        referenced_decisions.add(review_key)
        if decisions[review_key].get("disagreement"):
            unresolved_disagreements.add(review_key)
        if not _decision_supports(decisions, review_key, decision_kind, subject):
            continue
        if kind == "equivalent":
            supported_equivalences.append((left, right))
        elif kind == "distinct":
            if (
                authority_locator.get(left) is not None
                and authority_locator.get(left) == authority_locator.get(right)
            ):
                errors.append(
                    f"distinct relation {relation_id} contradicts a shared authority locator"
                )
                continue
            supported_distinct.add(pair)
        else:
            if target_scope.get(left) != "specific_candidate":
                errors.append(f"strict refinement {relation_id} narrower target is not specific")
                continue
            if baseline_scope.get(right) != "broad":
                errors.append(f"strict refinement {relation_id} broader target is not frozen broad")
                continue
            node = next(
                (item for item in hierarchy.get("nodes", []) if item.get("target_id") == left),
                None,
            )
            if node is None or right not in node.get("ancestor_target_ids", []):
                errors.append(f"strict refinement {relation_id} lacks source-derived ancestry")
                continue
            supported_strict[(left, right)] = relation

    identity = UnionFind(all_targets)
    targets_by_locator: dict[str, list[str]] = defaultdict(list)
    for target_id, locator in sorted(authority_locator.items()):
        targets_by_locator[locator].append(target_id)
    for locator_targets in targets_by_locator.values():
        for target_id in locator_targets[1:]:
            identity.union(locator_targets[0], target_id)
    for left, right in sorted(supported_equivalences):
        identity.union(left, right)

    class_members: dict[str, set[str]] = defaultdict(set)
    for target_id in sorted(all_targets):
        class_members[identity.find(target_id)].add(target_id)
    identity_scope: dict[str, str] = {}
    for root, members in class_members.items():
        scopes = {target_scope[target] for target in members}
        if "broad" in scopes:
            identity_scope[root] = "broad"
        elif "specific_candidate" in scopes:
            identity_scope[root] = "specific_candidate"
        else:
            identity_scope[root] = "unclassified"

    baseline_links = {
        artifact_id: set(row.get("baseline_site_target_ids", []))
        for artifact_id, row in baseline_by_id.items()
    }
    candidate_links: dict[str, set[str]] = {
        artifact_id: set(targets) for artifact_id, targets in baseline_links.items()
    }
    credited_links: dict[str, set[str]] = defaultdict(set)
    credited_link_bindings: dict[
        str, dict[str, set[tuple[str, str]]]
    ] = defaultdict(lambda: defaultdict(set))
    strict_pairs_by_artifact: dict[str, set[tuple[str, str]]] = defaultdict(set)
    events: list[dict] = []
    refinement_modes: Counter[str] = Counter()
    opportunity_outcomes_by_museum: dict[str, Counter[str]] = {
        museum: Counter() for museum in MUSEUMS
    }
    opportunity_abstention_reasons: Counter[str] = Counter()
    artifact_candidate_blocking: dict[str, bool] = {}
    artifact_candidate_status_counts: dict[str, Counter[str]] = {}
    artifact_authenticated_status_resolution: dict[str, bool] = {}

    for artifact_id in sorted(itt_by_id):
        baseline = baseline_by_id[artifact_id]
        baseline_targets = baseline_links[artifact_id]
        record = candidate_by_id.get(artifact_id)
        if record is None:
            continue
        outcomes = record.get("opportunity_outcomes", [])
        outcome_bindings = [
            (
                outcome.get("opportunity_id"),
                outcome.get("opportunity_binding_sha256"),
            )
            for outcome in outcomes
        ]
        expected_bindings = itt_bindings_by_id.get(artifact_id, set())
        bindings_well_formed = all(
            isinstance(opportunity_id, str)
            and bool(opportunity_id)
            and isinstance(binding_sha256, str)
            and bool(binding_sha256)
            for opportunity_id, binding_sha256 in outcome_bindings
        )
        if (
            not bindings_well_formed
            or outcome_bindings != sorted(outcome_bindings)
            or len(outcome_bindings) != len(set(outcome_bindings))
            or set(outcome_bindings) != expected_bindings
        ):
            errors.append(
                f"candidate {artifact_id} must report exactly one canonically sorted outcome "
                "for every frozen opportunity binding"
            )
        final_target_rows = record.get("final_supported_direct_target_ids", [])
        removed_target_rows = record.get("removed_baseline_target_ids", [])
        if final_target_rows != sorted(set(final_target_rows)):
            errors.append(
                f"candidate {artifact_id} final supported direct targets must be sorted and unique"
            )
        if removed_target_rows != sorted(set(removed_target_rows)):
            errors.append(
                f"candidate {artifact_id} removed baseline targets must be sorted and unique"
            )
        final_targets = set(final_target_rows)
        removed_targets = set(removed_target_rows)
        unknown_final = final_targets - all_targets
        if unknown_final:
            errors.append(
                f"candidate {artifact_id} final direct targets lack authenticated scope: "
                f"{sorted(unknown_final)}"
            )
        expected_removed = baseline_targets - final_targets
        if removed_targets != expected_removed:
            errors.append(
                f"candidate {artifact_id} must explicitly and exactly partition every "
                "baseline direct target as retained or removed"
            )
        if removed_targets & final_targets:
            errors.append(
                f"candidate {artifact_id} cannot both retain and remove a baseline direct target"
            )

        supported_targets: set[str] = set()
        unsupported_targets: set[str] = set()
        selected_original_mentions: dict[str, dict] = {}
        selected_candidate_states: dict[str, tuple[str, tuple[str, ...]]] = {}
        artifact_authenticated_status_resolution[artifact_id] = False
        for outcome in outcomes:
            status = outcome.get("resolution_status")
            direct_links = outcome.get("direct_links", [])
            uncredited_claims = outcome.get("uncredited_link_claims", [])
            abstention_reason = outcome.get("abstention_reason")
            status_support_key = outcome.get("status_support_decision_key")
            opportunity_binding = (
                outcome.get("opportunity_id"),
                outcome.get("opportunity_binding_sha256"),
            )
            if status not in {
                "linked",
                "ambiguous",
                "abstained",
                "unmatched",
                "unresolved",
                "research_failure",
            }:
                errors.append(
                    f"candidate {artifact_id}/{opportunity_binding[0]} resolution status invalid"
                )
                continue
            opportunity_outcomes_by_museum[museum_by_id[artifact_id]][status] += 1
            mention_rows = binding_mentions.get(
                (artifact_id, opportunity_binding[0], opportunity_binding[1]), []
            )
            if not mention_rows:
                errors.append(
                    f"candidate {artifact_id}/{opportunity_binding[0]} lacks its exact "
                    "private selecting-mention binding"
                )
            if (status == "linked") != bool(direct_links):
                errors.append(
                    f"candidate {artifact_id}/{opportunity_binding[0]} linked status/direct links mismatch"
                )
            if status != "unresolved" and uncredited_claims:
                errors.append(
                    f"candidate {artifact_id}/{opportunity_binding[0]} rejected link claims "
                    "must use unresolved status"
                )
            if status == "abstained":
                if abstention_reason not in ABSTENTION_REASONS:
                    errors.append(
                        f"candidate {artifact_id}/{opportunity_binding[0]} abstention reason invalid"
                    )
                else:
                    opportunity_abstention_reasons[abstention_reason] += 1
            elif abstention_reason is not None:
                errors.append(
                    f"candidate {artifact_id}/{opportunity_binding[0]} abstention reason only applies to abstention"
                )
            targets_seen: set[str] = set()
            outcome_supported_targets: set[str] = set()
            for link in direct_links:
                target_id = link.get("target_id")
                support_key = link.get("support_decision_key")
                if not target_id or target_id in targets_seen:
                    errors.append(
                        f"candidate {artifact_id}/{opportunity_binding[0]} direct targets must be nonempty and unique"
                    )
                    continue
                targets_seen.add(target_id)
                if opportunity_binding not in expected_bindings:
                    errors.append(
                        f"candidate link {artifact_id}/{target_id} is not bound to an exact private opportunity"
                    )
                    unsupported_targets.add(target_id)
                    continue
                if target_id not in all_targets:
                    errors.append(
                        f"candidate {artifact_id} target {target_id} lacks authenticated scope"
                    )
                    continue
                subject = {
                    "artifact_id": artifact_id,
                    "target_id": target_id,
                    "opportunity_id": opportunity_binding[0],
                    "opportunity_binding_sha256": opportunity_binding[1],
                }
                expected_key = decision_key("link_support", subject)
                if support_key is None:
                    errors.append(
                        f"candidate linked outcome {artifact_id}/{target_id} lacks authenticated "
                        "support and must instead be unresolved"
                    )
                    unsupported_targets.add(target_id)
                    continue
                if support_key != expected_key or support_key not in decisions:
                    errors.append(
                        f"candidate link {artifact_id}/{target_id} lacks exact review decision"
                    )
                    unsupported_targets.add(target_id)
                    continue
                referenced_decisions.add(support_key)
                if decisions[support_key].get("disagreement"):
                    unresolved_disagreements.add(support_key)
                if _decision_supports(
                    decisions, support_key, "link_support", subject
                ):
                    supported_targets.add(target_id)
                    outcome_supported_targets.add(target_id)
                    if target_scope[target_id] == "specific_candidate":
                        credited_links[artifact_id].add(target_id)
                        credited_link_bindings[artifact_id][target_id].add(
                            opportunity_binding
                        )
                else:
                    errors.append(
                        f"candidate linked outcome {artifact_id}/{target_id} is disputed or "
                        "unsupported and must instead be unresolved"
                    )
                    unsupported_targets.add(target_id)
            rejected_targets_seen: set[str] = set()
            for claim in uncredited_claims:
                target_id = claim.get("target_id")
                support_key = claim.get("support_decision_key")
                if (
                    not target_id
                    or target_id in rejected_targets_seen
                    or target_id in targets_seen
                ):
                    errors.append(
                        f"candidate {artifact_id}/{opportunity_binding[0]} rejected link "
                        "targets must be nonempty, unique, and disjoint from supported links"
                    )
                    continue
                rejected_targets_seen.add(target_id)
                if target_id not in all_targets:
                    errors.append(
                        f"candidate rejected link {artifact_id}/{target_id} lacks authenticated scope"
                    )
                    continue
                subject = {
                    "artifact_id": artifact_id,
                    "target_id": target_id,
                    "opportunity_id": opportunity_binding[0],
                    "opportunity_binding_sha256": opportunity_binding[1],
                }
                expected_key = decision_key("link_support", subject)
                if support_key != expected_key or support_key not in decisions:
                    errors.append(
                        f"candidate rejected link {artifact_id}/{target_id} lacks exact review decision"
                    )
                    continue
                referenced_decisions.add(support_key)
                if decisions[support_key].get("disagreement"):
                    unresolved_disagreements.add(support_key)
                if _decision_supports(
                    decisions, support_key, "link_support", subject
                ):
                    errors.append(
                        f"candidate rejected link {artifact_id}/{target_id} is supported by its reviews"
                    )
                    continue
                unsupported_targets.add(target_id)
            direct_target_tuple = tuple(sorted(outcome_supported_targets))
            if status == "linked" and len(outcome_supported_targets) > len(mention_rows):
                errors.append(
                    f"candidate {artifact_id}/{opportunity_binding[0]} claims more unique "
                    "authenticated supported targets than its exact selecting mentions"
                )

            # Candidate dispositions are not trusted mention post-states.  Only an exact,
            # independently reviewed status-resolution decision may change a frozen mention
            # status.  Abstention, unresolved work, and research failure preserve the frozen
            # status by construction.
            proposed_status = {
                "linked": "resolved",
                "ambiguous": "ambiguous",
                "unmatched": "unmatched",
            }.get(status)
            baseline_statuses = [
                {"mention_id": mention["mention_id"], "status": mention["status"]}
                for mention in sorted(mention_rows, key=lambda value: value["mention_id"])
            ]
            changes_frozen_status = bool(
                proposed_status is not None
                and any(row["status"] != proposed_status for row in baseline_statuses)
            )
            status_resolution_supported = False
            if changes_frozen_status:
                status_subject = {
                    "artifact_id": artifact_id,
                    "opportunity_id": opportunity_binding[0],
                    "opportunity_binding_sha256": opportunity_binding[1],
                    "mention_ids": [row["mention_id"] for row in baseline_statuses],
                    "baseline_statuses": baseline_statuses,
                    "proposed_status": proposed_status,
                }
                expected_status_key = decision_key(
                    "mention_status_resolution", status_subject
                )
                if (
                    status_support_key != expected_status_key
                    or status_support_key not in decisions
                ):
                    errors.append(
                        f"candidate {artifact_id}/{opportunity_binding[0]} cannot change "
                        "a frozen mention status without its exact authenticated "
                        "mention-status-resolution decision"
                    )
                else:
                    referenced_decisions.add(status_support_key)
                    if decisions[status_support_key].get("disagreement"):
                        unresolved_disagreements.add(status_support_key)
                    status_resolution_supported = _decision_supports(
                        decisions,
                        status_support_key,
                        "mention_status_resolution",
                        status_subject,
                    )
                    if not status_resolution_supported:
                        errors.append(
                            f"candidate {artifact_id}/{opportunity_binding[0]} mention "
                            "status change is disputed or unsupported"
                        )
                    else:
                        artifact_authenticated_status_resolution[artifact_id] = True
            elif status_support_key is not None:
                errors.append(
                    f"candidate {artifact_id}/{opportunity_binding[0]} supplies an unused "
                    "mention-status-resolution decision"
                )
            for mention in mention_rows:
                mention_id = mention["mention_id"]
                prior_original = selected_original_mentions.get(mention_id)
                if prior_original is not None and prior_original != mention:
                    errors.append(
                        f"private selecting mention {mention_id} has contradictory frozen bindings"
                    )
                    continue
                selected_original_mentions[mention_id] = mention
                effective_status = (
                    proposed_status
                    if changes_frozen_status and status_resolution_supported
                    else proposed_status
                    if proposed_status == mention["status"]
                    else mention["status"]
                )
                candidate_state = (effective_status, direct_target_tuple)
                prior_state = selected_candidate_states.get(mention_id)
                if prior_state is not None and prior_state != candidate_state:
                    errors.append(
                        f"candidate outcomes give selecting mention {mention_id} contradictory post-states"
                    )
                selected_candidate_states[mention_id] = candidate_state

        unjustified_final = (final_targets - baseline_targets) - supported_targets
        omitted_supported = supported_targets - final_targets
        if unjustified_final:
            errors.append(
                f"candidate {artifact_id} final direct targets lack exact supported "
                f"opportunity reviews: {sorted(unjustified_final)}"
            )
        if omitted_supported:
            errors.append(
                f"candidate {artifact_id} supported opportunity links are absent from the "
                f"record-level final direct set: {sorted(omitted_supported)}"
            )
        candidate_links[artifact_id] = final_targets

        baseline_status_counts = Counter(baseline.get("site_mention_status_counts", {}))
        baseline_mention_count = baseline.get("site_mention_count")
        if (
            not isinstance(baseline_mention_count, int)
            or baseline_mention_count < 0
            or sum(baseline_status_counts.values()) != baseline_mention_count
            or any(
                status not in {"resolved", "ambiguous", "unmatched"}
                or not isinstance(count, int)
                or count < 0
                for status, count in baseline_status_counts.items()
            )
        ):
            errors.append(
                f"baseline {artifact_id} has invalid complete site-mention status accounting"
            )
        candidate_status_counts = Counter(baseline_status_counts)
        for mention in selected_original_mentions.values():
            original_status = mention["status"]
            candidate_status_counts[original_status] -= 1
            if candidate_status_counts[original_status] < 0:
                errors.append(
                    f"private selecting mention census exceeds baseline {original_status} "
                    f"count for {artifact_id}"
                )
        for effective_status, _ in selected_candidate_states.values():
            candidate_status_counts[effective_status] += 1
        artifact_candidate_status_counts[artifact_id] = candidate_status_counts
        artifact_candidate_blocking[artifact_id] = (
            not final_targets and candidate_status_counts["ambiguous"] > 0
        )

        baseline_identity_roots = {identity.find(target) for target in baseline_targets}
        final_identity_roots = {identity.find(target) for target in final_targets}
        equivalent_pairs: set[tuple[str, str]] = set()
        strict_pairs: set[tuple[str, str]] = set()
        for baseline_target in sorted(baseline_targets):
            for candidate_target in sorted(final_targets - baseline_targets):
                if identity.find(candidate_target) == identity.find(baseline_target):
                    equivalent_pairs.add((baseline_target, candidate_target))
                if (candidate_target, baseline_target) in supported_strict:
                    strict_pairs.add((baseline_target, candidate_target))
        strict_pairs_by_artifact[artifact_id] = strict_pairs
        preserved_baseline_roots = set(final_identity_roots) | {
            identity.find(baseline_target)
            for baseline_target, _ in strict_pairs
        }
        lost_identity_roots = baseline_identity_roots - preserved_baseline_roots
        losses = {
            target
            for target in baseline_targets
            if identity.find(target) in lost_identity_roots
        }
        raw_removed_edges = baseline_targets - final_targets
        unrelated_credited = {
            target
            for target in credited_links[artifact_id]
            if identity.find(target)
            not in {identity.find(value) for value in baseline_targets}
            if not any(
                (baseline_target, target) in equivalent_pairs | strict_pairs
                for baseline_target in baseline_targets
            )
        }
        if losses:
            event = "loss"
        elif strict_pairs:
            event = "strict_refinement_reassignment"
            for baseline_target, _ in sorted(strict_pairs):
                mode = (
                    "old_direct_edge_preserved"
                    if baseline_target in final_targets
                    else "old_direct_edge_replaced_ancestor_semantics_preserved"
                )
                refinement_modes[mode] += 1
        elif not baseline_targets and credited_links[artifact_id]:
            event = "new_link"
        elif baseline_targets and unrelated_credited:
            event = "additional_identity"
        elif {identity.find(target) for target in final_targets} == {
            identity.find(target) for target in baseline_targets
        }:
            # A supported equivalent alias changes spelling/direct edge, not identity.
            event = "unchanged"
        elif final_targets != baseline_targets:
            event = "uncredited_change"
        else:
            event = "unchanged"
        events.append(
            {
                "artifact_id": artifact_id,
                "museum": museum_by_id[artifact_id],
                "event": event,
                "baseline_direct_target_ids": sorted(baseline_targets),
                "candidate_supported_direct_target_ids": sorted(final_targets),
                "explicitly_removed_baseline_target_ids": sorted(removed_targets),
                "raw_removed_baseline_direct_target_ids": sorted(raw_removed_edges),
                "uncredited_candidate_target_ids": sorted(unsupported_targets),
                "baseline_site_mention_status_counts": dict(
                    sorted(baseline_status_counts.items())
                ),
                "candidate_site_mention_status_counts": dict(
                    sorted(candidate_status_counts.items())
                ),
                "supported_strict_refinement_pairs": [
                    list(pair) for pair in sorted(strict_pairs)
                ],
                "lost_baseline_target_ids": sorted(losses),
                "lost_baseline_identity_class_ids": sorted(lost_identity_roots),
            }
        )

    def positively_distinct(left: str, right: str) -> bool:
        left_root, right_root = identity.find(left), identity.find(right)
        if left_root == right_root:
            return False
        reviewed_pairs = set(supported_distinct) | {
            tuple(sorted(pair)) for pair in supported_strict
        }
        return any(
            {identity.find(first), identity.find(second)} == {left_root, right_root}
            for first, second in reviewed_pairs
        )

    baseline_roots_by_museum = {
        museum: {
            identity.find(target)
            for artifact_id, targets in baseline_links.items()
            if baseline_by_id[artifact_id].get("museum") == museum
            for target in targets
        }
        for museum in MUSEUMS
    }
    candidate_roots_by_museum = {
        museum: {
            identity.find(target)
            for artifact_id, targets in candidate_links.items()
            if baseline_by_id[artifact_id].get("museum") == museum
            for target in targets
        }
        for museum in MUSEUMS
    }
    credited_roots = {
        identity.find(target)
        for targets in credited_links.values()
        for target in targets
    }
    gained_specific_roots_by_pair: dict[tuple[str, str], set[str]] = {}
    for left, right in PAIRS:
        baseline_shared = baseline_roots_by_museum[left] & baseline_roots_by_museum[right]
        final_shared = candidate_roots_by_museum[left] & candidate_roots_by_museum[right]
        gained_specific_roots_by_pair[(left, right)] = {
            root
            for root in final_shared - baseline_shared
            if identity_scope.get(root) == "specific_candidate"
            and root in credited_roots
            and all(
                any(
                    identity.find(target) == root
                    and target_scope[target] == "specific_candidate"
                    for artifact_id, targets in candidate_links.items()
                    if baseline_by_id[artifact_id].get("museum") == museum
                    for target in targets
                )
                for museum in (left, right)
            )
        }

    # Freeze the complete prospective gained-root census before pair-side credit is
    # counted.  In particular, crossed additions (each side supplying the other side's
    # existing identity) cannot evade the pairwise distinctness census.
    gained_roots = set().union(*gained_specific_roots_by_pair.values())
    representative_by_root = {
        root: min(members) for root, members in class_members.items()
    }
    for left_root, right_root in combinations(sorted(gained_roots), 2):
        left = representative_by_root[left_root]
        right = representative_by_root[right_root]
        if not positively_distinct(left, right):
            errors.append(
                "prospective gained identity roots lack positive distinctness evidence: "
                f"{left}/{right}"
            )
    relevant_baseline_roots = set().union(*baseline_roots_by_museum.values())
    for gained_root in sorted(gained_roots):
        candidate_target = representative_by_root[gained_root]
        for baseline_root in sorted(relevant_baseline_roots - {gained_root}):
            baseline_target = representative_by_root[baseline_root]
            if not positively_distinct(candidate_target, baseline_target):
                errors.append(
                    "prospective gained target lacks positive distinctness from a relevant "
                    "frozen baseline identity (including crossed and one-sided identities): "
                    f"{candidate_target}/{baseline_target}"
                )

    unused_decisions = sorted(set(decisions) - referenced_decisions)
    if unused_decisions:
        errors.append(f"review ledger contains decisions outside the exact census: {unused_decisions}")
    if errors:
        return _invalid_report(errors)

    event_counts = Counter(event["event"] for event in events)
    record_counts = metrics["record_counts_by_museum"]
    evidence_counts = {
        museum: metrics["per_museum"][museum]["extracted_site_text_evidence_records"]
        for museum in MUSEUMS
    }
    per_museum = {}
    for museum in MUSEUMS:
        counts = Counter(event["event"] for event in events if event["museum"] == museum)
        per_museum[museum] = {
            "event_counts": {event: counts[event] for event in EVENTS},
            "new_link_rate_over_all_records": ratio(counts["new_link"], record_counts[museum]),
            "new_link_rate_over_extracted_site_text": ratio(
                counts["new_link"], evidence_counts[museum]
            ),
            "strict_refinement_rate_over_all_records": ratio(
                counts["strict_refinement_reassignment"], record_counts[museum]
            ),
            "strict_refinement_rate_over_extracted_site_text": ratio(
                counts["strict_refinement_reassignment"], evidence_counts[museum]
            ),
        }

    artifacts_by_museum = {
        museum: {
            artifact_id
            for artifact_id, row in baseline_by_id.items()
            if row.get("museum") == museum
        }
        for museum in MUSEUMS
    }
    baseline_class_links = {
        artifact_id: {identity.find(target) for target in targets}
        for artifact_id, targets in baseline_links.items()
    }
    candidate_class_links = {
        artifact_id: {identity.find(target) for target in targets}
        for artifact_id, targets in candidate_links.items()
    }
    post_candidate_linkability = {}
    for museum in MUSEUMS:
        linked_records = sum(
            bool(candidate_class_links[artifact_id])
            for artifact_id in artifacts_by_museum[museum]
        )
        post_candidate_linkability[museum] = {
            "records_with_supported_direct_links": linked_records,
            "overall_linkability": ratio(linked_records, record_counts[museum]),
            "extracted_site_text_conditional_linkability": ratio(
                linked_records, evidence_counts[museum]
            ),
        }
    post_candidate_metrics = {
        "linkability_by_museum": post_candidate_linkability,
        "connectivity": _post_candidate_connectivity(
            candidate_class_links,
            artifacts_by_museum,
            record_counts,
            evidence_counts,
            identity_scope,
        ),
    }
    baseline_classes_by_museum = {
        museum: set().union(
            *(baseline_class_links[artifact] for artifact in artifacts_by_museum[museum])
        )
        if artifacts_by_museum[museum]
        else set()
        for museum in MUSEUMS
    }
    candidate_classes_by_museum = {
        museum: set().union(
            *(candidate_class_links[artifact] for artifact in artifacts_by_museum[museum])
        )
        if artifacts_by_museum[museum]
        else set()
        for museum in MUSEUMS
    }

    private_pair_memberships = private_opportunity[
        "credited_pair_opportunity_memberships"
    ]
    pairs = {}
    concentration_pass = True
    utility_pair_passes: list[bool] = []
    for left, right in PAIRS:
        pair_key = f"{left}__{right}"
        baseline_shared = baseline_classes_by_museum[left] & baseline_classes_by_museum[right]
        candidate_shared = candidate_classes_by_museum[left] & candidate_classes_by_museum[right]
        gained_specific = gained_specific_roots_by_pair[(left, right)]

        sides = {}
        broad_deltas: dict[str, Fraction] = {}
        pair_concentration_pass = True
        for museum in (left, right):
            baseline_connected = {
                artifact
                for artifact in artifacts_by_museum[museum]
                if baseline_class_links[artifact] & baseline_shared
            }
            candidate_connected = {
                artifact
                for artifact in artifacts_by_museum[museum]
                if candidate_class_links[artifact] & candidate_shared
            }
            baseline_broad = {
                artifact
                for artifact in baseline_connected
                if partition_scopes(
                    {
                        identity_scope[identity.find(target)]
                        for target in baseline_links[artifact]
                        if identity.find(target) in baseline_shared
                    }
                )
                == "broad_only"
            }
            candidate_broad = {
                artifact
                for artifact in candidate_connected
                if partition_scopes(
                    {
                        identity_scope[identity.find(target)]
                        for target in candidate_links[artifact]
                        if identity.find(target) in candidate_shared
                    }
                )
                == "broad_only"
            }

            member_rows = private_pair_memberships[pair_key]["sides"][museum]
            member_category: dict[str, str] = {}
            member_bindings: dict[str, set[tuple[str, str]]] = {}
            for row in member_rows:
                artifact_id = row["artifact_id"]
                binding_rows = [
                    (
                        binding.get("opportunity_id"),
                        binding.get("opportunity_binding_sha256"),
                    )
                    for binding in row.get("opportunity_bindings", [])
                ]
                bindings = set(binding_rows)
                if artifact_id in member_category:
                    return _invalid_report(
                        [f"{pair_key}/{museum} has duplicate private pair-side artifact"]
                    )
                if (
                    binding_rows != sorted(bindings)
                    or bindings != itt_bindings_by_id.get(artifact_id, set())
                    or museum_by_id.get(artifact_id) != museum
                ):
                    return _invalid_report(
                        [
                            f"{pair_key}/{museum}/{artifact_id} pair-side opportunity binding differs from frozen ITT"
                        ]
                    )
                baseline_pair_roots = (
                    baseline_class_links.get(artifact_id, set()) & baseline_shared
                )
                if not baseline_pair_roots:
                    expected_category = "no_baseline_pair_connection"
                elif partition_scopes(
                    {identity_scope[root] for root in baseline_pair_roots}
                ) == "broad_only":
                    expected_category = "broad_only_pair_connection"
                else:
                    return _invalid_report(
                        [
                            f"{pair_key}/{museum}/{artifact_id} is not an eligible frozen "
                            "raw-category/identity-class opportunity"
                        ]
                    )
                if row.get("category") != expected_category:
                    return _invalid_report(
                        [
                            f"{pair_key}/{museum}/{artifact_id} frozen pair-side raw category "
                            "is inconsistent with authenticated baseline identity classes"
                        ]
                    )
                member_category[artifact_id] = expected_category
                member_bindings[artifact_id] = bindings
            pair_event_counts: Counter[str] = Counter()
            affected_artifacts: set[str] = set()
            for artifact_id in sorted(member_category):
                gained_credited_targets = {
                    target
                    for target in credited_links.get(artifact_id, set())
                    if identity.find(target) in gained_specific
                    and identity.find(target)
                    not in baseline_class_links.get(artifact_id, set())
                    and bool(
                        credited_link_bindings.get(artifact_id, {}).get(target, set())
                        & member_bindings[artifact_id]
                    )
                }
                if not gained_credited_targets:
                    continue
                category = member_category[artifact_id]
                if category == "no_baseline_pair_connection":
                    pair_event_counts["new_pair_connection"] += 1
                    affected_artifacts.add(artifact_id)
                elif category == "broad_only_pair_connection" and any(
                    baseline_target in baseline_links[artifact_id]
                    and identity.find(candidate_target) in gained_specific
                    and identity.find(baseline_target) in baseline_shared
                    for baseline_target, candidate_target in strict_pairs_by_artifact.get(
                        artifact_id, set()
                    )
                ):
                    pair_event_counts["supported_broad_to_specific_pair_refinement"] += 1
                    affected_artifacts.add(artifact_id)

            public_side = opportunity_summary["pair_side_ceilings"][pair_key]["sides"][museum]
            denominator = len(member_rows)
            minimum = ceil_fraction(denominator, MINIMUM_AFFECTED_FRACTION)
            if public_side["credited_effect_opportunity_denominator"] != denominator:
                return _invalid_report([f"{pair_key}/{museum} public/private denominator mismatch"])
            if public_side["minimum_credited_affected_records_for_continue"] != minimum:
                return _invalid_report([f"{pair_key}/{museum} minimum not derived from 1/10 constant"])

            baseline_conc = concentration(
                baseline_class_links, artifacts_by_museum[museum], baseline_shared
            )
            candidate_conc = concentration(
                candidate_class_links, artifacts_by_museum[museum], candidate_shared
            )
            top_k_pass: dict[str, bool] = {}
            for k in TOP_K:
                key = str(k)
                base_value = _fraction_from_ratio(
                    baseline_conc["top_k_unique_record_concentration"][key]["ratio"]
                )
                candidate_value = _fraction_from_ratio(
                    candidate_conc["top_k_unique_record_concentration"][key]["ratio"]
                )
                top_k_pass[key] = (
                    candidate_value <= base_value + CONCENTRATION_MAXIMUM_INCREASE
                )
            hhi_pass = _fraction_from_ratio(candidate_conc["node_incidence_hhi"]) <= (
                _fraction_from_ratio(baseline_conc["node_incidence_hhi"])
                + CONCENTRATION_MAXIMUM_INCREASE
            )
            side_concentration_pass = all(top_k_pass.values()) and hhi_pass
            pair_concentration_pass = pair_concentration_pass and side_concentration_pass
            broad_deltas[museum] = Fraction(
                len(candidate_broad) - len(baseline_broad), evidence_counts[museum]
            )
            sides[museum] = {
                "credited_affected_record_definition": (
                    "artifact is in this exact private pair-side ITT membership, has a "
                    "doubly reviewed specific link in a gained shared identity class, and "
                    "satisfies its frozen no-connection or broad-only category transition"
                ),
                "credited_pair_event_counts": {
                    "new_pair_connection": pair_event_counts["new_pair_connection"],
                    "supported_broad_to_specific_pair_refinement": pair_event_counts[
                        "supported_broad_to_specific_pair_refinement"
                    ],
                },
                "credited_affected_records": len(affected_artifacts),
                "fixed_opportunity_denominator": denominator,
                "minimum_for_continue": minimum,
                "affected_threshold_pass": len(affected_artifacts) >= minimum and minimum > 0,
                "baseline_broad_only_conditional_share": ratio(
                    len(baseline_broad), evidence_counts[museum]
                ),
                "candidate_broad_only_conditional_share": ratio(
                    len(candidate_broad), evidence_counts[museum]
                ),
                "candidate_concentration": candidate_conc,
                "comparable_baseline_concentration": baseline_conc,
                "concentration_limits": {
                    "top_k_unique_record_union": (
                        "each of top-1/top-5/top-10 candidate ratios <= comparable "
                        "baseline ratio + 1/20"
                    ),
                    "node_incidence_hhi": "candidate <= comparable baseline + 1/20",
                },
                "top_k_concentration_pass": top_k_pass,
                "hhi_concentration_pass": hhi_pass,
                "concentration_pass": side_concentration_pass,
            }
        concentration_pass = concentration_pass and pair_concentration_pass
        broad_utility = (
            any(delta < 0 for delta in broad_deltas.values())
            and all(delta <= 0 for delta in broad_deltas.values())
        )
        utility = (
            len(gained_specific) >= MINIMUM_GAINED_IDENTITIES
            and all(side["affected_threshold_pass"] for side in sides.values())
            and broad_utility
        )
        utility_pair_passes.append(utility)
        pairs[pair_key] = {
            "gained_credited_specific_identity_class_ids": sorted(gained_specific),
            "gained_credited_specific_shared_identity_class_count": len(gained_specific),
            "sides": sides,
            "broad_only_utility_pass": broad_utility,
            "concentration_safety_pass": pair_concentration_pass,
            "utility_pass": utility,
        }

    baseline_blocking = Counter(
        row["museum"] for row in baseline_records if row.get("has_blocking_ambiguity")
    )
    candidate_blocking = Counter(baseline_blocking)
    newly_blocking = Counter()
    authenticated_resolved_blocking = Counter()
    for artifact_id in sorted(candidate_by_id):
        museum = museum_by_id[artifact_id]
        baseline_value = bool(baseline_by_id[artifact_id].get("has_blocking_ambiguity"))
        candidate_value = artifact_candidate_blocking.get(artifact_id, False)
        candidate_blocking[museum] += int(candidate_value) - int(baseline_value)
        if candidate_value and not baseline_value:
            newly_blocking[museum] += 1
        if (
            baseline_value
            and not candidate_value
            and artifact_authenticated_status_resolution.get(artifact_id, False)
        ):
            authenticated_resolved_blocking[museum] += 1
    ambiguity_by_museum = {}
    ambiguity_pass = True
    for museum in MUSEUMS:
        net_delta = Fraction(
            candidate_blocking[museum] - baseline_blocking[museum], evidence_counts[museum]
        )
        newly_blocking_rate = Fraction(
            newly_blocking[museum], evidence_counts[museum]
        )
        passed = newly_blocking_rate <= MAXIMUM_NEWLY_BLOCKING_FRACTION
        ambiguity_pass = ambiguity_pass and passed
        ambiguity_by_museum[museum] = {
            "baseline_blocking": ratio(baseline_blocking[museum], evidence_counts[museum]),
            "candidate_blocking": ratio(candidate_blocking[museum], evidence_counts[museum]),
            "newly_blocking_records": newly_blocking[museum],
            "newly_blocking_rate": {
                "numerator": newly_blocking_rate.numerator,
                "denominator": newly_blocking_rate.denominator,
            },
            "authenticated_resolved_blocking_records": authenticated_resolved_blocking[
                museum
            ],
            "net_delta_descriptive": {
                "numerator": net_delta.numerator,
                "denominator": net_delta.denominator,
            },
            "maximum_allowed_newly_blocking_rate": {
                "numerator": MAXIMUM_NEWLY_BLOCKING_FRACTION.numerator,
                "denominator": MAXIMUM_NEWLY_BLOCKING_FRACTION.denominator,
            },
            "passed": passed,
        }

    retention_pass = event_counts["loss"] == 0
    safety = {
        "review_census_and_attribution": {
            "passed": True,
            "credited_changed_link_count": sum(len(values) for values in credited_links.values()),
            "unresolved_reviewer_disagreement_count": len(unresolved_disagreements),
            "policy": (
                "two structured independent evidence reviews are required; disagreement "
                "or non-support earns no credit and is unresolved, not gold truth"
            ),
        },
        "baseline_retention": {"passed": retention_pass, "loss_count": event_counts["loss"]},
        "ambiguity": {"passed": ambiguity_pass, "per_museum": ambiguity_by_museum},
        "per_museum_side_concentration": {
            "passed": concentration_pass,
            "policy": (
                "top-1/top-5/top-10 unique-record union ratios and incidence HHI are "
                "independently gated per museum side; pooled concentration is descriptive only"
            ),
        },
    }
    safety_pass = retention_pass and ambiguity_pass and concentration_pass
    utility_pass = any(utility_pair_passes)
    if not safety_pass:
        outcome = "REDESIGN"
    elif utility_pass:
        outcome = "CONTINUE"
    else:
        outcome = "STOP"
    ordered_trace = [
        {"step": "integrity", "passed": True},
        {"step": "safety", "passed": safety_pass},
        {"step": "utility", "passed": utility_pass, "outcome": outcome},
    ]
    return {
        "schema_version": "site-graph-v0-comparison-report/4",
        "outcome": outcome,
        "ordered_decision_trace": ordered_trace,
        "integrity": {"passed": True, "errors": []},
        "safety_gates": safety,
        "event_counts": {event: event_counts[event] for event in EVENTS},
        "event_records": events,
        "reassignment_edge_modes": dict(sorted(refinement_modes.items())),
        "per_museum": per_museum,
        "post_candidate_metrics": post_candidate_metrics,
        "pairs": pairs,
        "ambiguity_and_abstention": {
            "per_museum": ambiguity_by_museum,
            "opportunity_outcome_counts_by_museum": {
                museum: {
                    status: opportunity_outcomes_by_museum[museum][status]
                    for status in (
                        "linked",
                        "ambiguous",
                        "abstained",
                        "unmatched",
                        "unresolved",
                        "research_failure",
                    )
                }
                for museum in MUSEUMS
            },
            "candidate_abstention_reason_counts": dict(
                sorted(opportunity_abstention_reasons.items())
            ),
            "reviewer_disagreement_decisions_uncredited": len(unresolved_disagreements),
        },
        "run_binding": None,
        "provenance_status": _logic_only_provenance(outcome),
    }


def _validate_review_artifacts(
    repo: Path,
    result_commit: str,
    ledger: dict,
    schema_root: Path,
    *,
    freeze_commit: str | None = None,
    frozen_files: dict[str, dict] | None = None,
    source_exports: list[dict] | None = None,
    source_export_groups: list[dict] | None = None,
    candidate_id: str | None = None,
) -> dict[str, dict]:
    """Authenticate the exact two-review census against release trust roots."""
    if freeze_commit is None:
        raise ReviewAuthenticationError(
            "review evidence cannot be authenticated without its pre-run freeze"
        )
    frozen_files = frozen_files or {}
    source_exports = source_exports or []
    source_export_groups = source_export_groups or []
    if not source_exports or len(source_exports) != len(source_export_groups):
        raise ReviewAuthenticationError(
            "review evidence requires the complete authenticated authority-export census"
        )
    reviewer_registry, _ = load_reviewer_registry(repo, schema_root)
    usage = ArtifactUsageTracker()
    decisions: dict[str, dict] = {}
    export_by_reference: dict[tuple[str, str, str], dict] = {}
    identifiers: set[str] = set()
    preferred_labels: set[str] = set()
    aliases: set[str] = set()
    locators: set[str] = set()
    for source_export, group in zip(
        source_exports, source_export_groups, strict=True
    ):
        reference = group["export"]
        reference_key = (
            reference["path"],
            reference["sha256"],
            reference["git_blob_oid"],
        )
        export_by_reference[reference_key] = source_export
        identifiers.add(source_export["source_export_id"])
        locators.add(source_export["provenance"]["source_locator"])
        for record in source_export["records"]:
            source_id = record["source_record_id"]
            identifiers.update(
                {
                    source_id,
                    record["target_id"],
                    *record["parent_ids"],
                    *record["child_ids"],
                }
            )
            preferred_labels.add(record["preferred_label"])
            aliases.update(record["aliases"])
            locators.add(record["authority_identity_locator"])
            locators.update(record["authority_citations"])

    def read_bound(reference: dict) -> bytes:
        path = reference["path"]
        frozen = frozen_files.get(path)
        commit = result_commit
        if frozen is not None:
            if any(
                reference[field] != frozen[field]
                for field in ("path", "sha256", "git_blob_oid")
            ):
                raise ReviewAuthenticationError(
                    f"review dependency differs from frozen bytes: {path}"
                )
            commit = freeze_commit
        raw, _ = read_authenticated_bytes(
            repo,
            commit,
            path,
            expected_sha256=reference["sha256"],
            expected_blob_oid=reference["git_blob_oid"],
        )
        return raw

    for ledger_decision in ledger["decisions"]:
        key = ledger_decision["decision_key"]
        kind = ledger_decision["decision_kind"]
        subject = ledger_decision["subject"]
        if key != decision_key(kind, subject) or key in decisions:
            raise ValueError("review decision keys must be canonical and unique")
        authenticated_reviews = []
        for reference in ledger_decision["review_artifacts"]:
            path = reference["path"]
            raw_artifact, metadata = read_authenticated_bytes(
                repo,
                result_commit,
                path,
                expected_sha256=reference["sha256"],
                expected_blob_oid=reference["git_blob_oid"],
            )
            artifact = strict_json_object(raw_artifact, label=f"review artifact {path}")
            if canonical_sha256(artifact) != reference["canonical_record_sha256"]:
                raise ValueError(f"review artifact canonical record hash mismatch: {path}")
            artifact_owner = (
                artifact["llm_interaction"]["review_invocation_id"]
                if artifact["method"] == "llm"
                else f"human:{artifact['human_provenance']['review_session_id']}"
            )
            usage.claim_reference(
                reference,
                owner=artifact_owner,
                role="review_artifact",
                label="review artifact",
            )
            if (
                artifact["decision_key"] != key
                or artifact["decision_kind"] != kind
                or artifact["subject"] != subject
            ):
                raise ValueError(f"review artifact is not bound to ledger decision: {path}")
            cited_target_ids: set[str] = set()
            for citation in artifact["citations"]:
                source_reference = citation["source_artifact"]
                reference_key = (
                    source_reference["path"],
                    source_reference["sha256"],
                    source_reference["git_blob_oid"],
                )
                if reference_key not in export_by_reference:
                    raise ReviewAuthenticationError(
                        f"review citation is not an authenticated authority export: {path}"
                    )
                cited_export = export_by_reference[reference_key]
                cited_target_ids.add(
                    _require_citation_in_authenticated_export(
                        citation, cited_export, label=path
                    )
                )
            if kind != "mention_status_resolution":
                _require_subject_target_citation_coverage(
                    subject, cited_target_ids, label=path
                )

            authenticated_audit = None
            authenticated_semantic_audit = None
            if artifact["method"] == "llm":
                interaction = artifact["llm_interaction"]
                audit_reference = interaction["prompt_leakage_audit"]
                semantic_audit_reference = interaction["semantic_prompt_audit"]
                audit_entry = frozen_files.get(audit_reference["path"])
                semantic_audit_entry = frozen_files.get(
                    semantic_audit_reference["path"]
                )
                if (
                    audit_entry is None
                    or audit_entry.get("role") != "prompt_leakage_audit"
                    or any(
                        audit_reference[field] != audit_entry[field]
                        for field in ("path", "sha256", "git_blob_oid")
                    )
                ):
                    raise ValueError(
                        f"LLM prompt audit was not an exact pre-generation frozen input: {path}"
                    )
                if (
                    semantic_audit_entry is None
                    or semantic_audit_entry.get("role") != "semantic_prompt_audit"
                    or any(
                        semantic_audit_reference[field]
                        != semantic_audit_entry[field]
                        for field in ("path", "sha256", "git_blob_oid")
                    )
                ):
                    raise ValueError(
                        "LLM semantic prompt audit was not an exact pre-generation "
                        f"frozen input: {path}"
                    )
                raw_audit = read_bound(audit_reference)
                audit = strict_json_object(raw_audit, label="prompt leakage audit")
                audit_signature = audit["authentication"]["signature"]
                raw_semantic_audit = read_bound(semantic_audit_reference)
                semantic_audit = strict_json_object(
                    raw_semantic_audit, label="semantic prompt audit"
                )
                semantic_audit_signature = semantic_audit["authentication"][
                    "signature"
                ]
                identifier_values = sorted(
                    {
                        str(value)
                        for field, value in subject.items()
                        if (
                            field.endswith("_id") or field.endswith("_sha256")
                        )
                        and isinstance(value, str)
                    }
                )
                review_identifiers = canonical_forbidden_values(
                    sorted(
                        identifiers
                        | {candidate_id or "candidate-id-unavailable", *identifier_values}
                    )
                )
                authenticated_audit = authenticate_prompt_audit(
                    raw_audit,
                    registry=reviewer_registry,
                    schema_root=schema_root,
                    signature_bytes=read_bound(audit_signature),
                    signature_reference=audit_signature,
                    read_artifact=read_bound,
                    preferred_labels=canonical_forbidden_values(
                        sorted(preferred_labels)
                    ),
                    aliases=canonical_forbidden_values(sorted(aliases)),
                    answer_names=sorted(MECHANICAL_REVIEW_ANSWER_TOKENS),
                    identifiers=review_identifiers,
                    locators=canonical_forbidden_values(sorted(locators)),
                    invocation_started_at_utc=interaction["invoked_at_utc"],
                    usage=usage,
                )
                authenticated_semantic_audit = authenticate_semantic_prompt_audit(
                    raw_semantic_audit,
                    registry=reviewer_registry,
                    schema_root=schema_root,
                    signature_bytes=read_bound(semantic_audit_signature),
                    signature_reference=semantic_audit_signature,
                    read_artifact=read_bound,
                    preferred_labels=canonical_forbidden_values(
                        sorted(preferred_labels)
                    ),
                    aliases=canonical_forbidden_values(sorted(aliases)),
                    answer_names=sorted(MECHANICAL_REVIEW_ANSWER_TOKENS),
                    identifiers=review_identifiers,
                    locators=canonical_forbidden_values(sorted(locators)),
                    invocation_started_at_utc=interaction["invoked_at_utc"],
                    usage=usage,
                )
            signature_reference = artifact["authentication"]["signature"]
            authenticated = authenticate_review_artifact(
                raw_artifact,
                registry=reviewer_registry,
                schema_root=schema_root,
                signature_bytes=read_bound(signature_reference),
                signature_reference=signature_reference,
                read_artifact=read_bound,
                usage=usage,
                authenticated_prompt_audit=authenticated_audit,
                authenticated_semantic_prompt_audit=authenticated_semantic_audit,
            )
            authenticated_reviews.append(authenticated)
        require_distinct_registered_reviewers(
            authenticated_reviews,
            required_count=REVIEWS_PER_CREDITED_DECISION,
        )
        outcomes = [review["outcome"] for review in authenticated_reviews]
        decisions[key] = {
            "decision_kind": kind,
            "subject": subject,
            "supported": all(outcome == "supported" for outcome in outcomes),
            "disagreement": len(set(outcomes)) > 1,
            "review_artifact_sha256": sorted(
                review["artifact_sha256"] for review in authenticated_reviews
            ),
            "authenticated_reviewer_ids": sorted(
                review["reviewer_id"] for review in authenticated_reviews
            ),
        }
    return decisions


def _load_trusted_attestor_policy(
    repo: Path, schema_root: Path
) -> tuple[dict, dict]:
    path = repo / TRUSTED_ATTESTORS_RELATIVE
    raw = path.read_bytes()
    try:
        policy = json.loads(raw)
    except json.JSONDecodeError as error:
        raise CandidateGitError("release-pinned trusted run attestor policy is not JSON") from error
    validate_schema(
        policy,
        schema_root / "trusted-run-attestors.schema.json",
        "release-pinned trusted run attestors",
    )
    if policy["registry_scope"] != "production_release":
        raise CandidateGitError("test-only run-attestor registry rejected in production")
    if policy["status"] != "CONFIGURED":
        raise CandidateGitError(
            "production candidate comparison blocked: trusted run attestors are NOT_CONFIGURED"
        )
    attestor_ids = [row["attestor_id"] for row in policy["attestors"]]
    key_ids = [row["key_id"] for row in policy["attestors"]]
    if len(attestor_ids) != len(set(attestor_ids)) or len(key_ids) != len(set(key_ids)):
        raise CandidateGitError("trusted run attestor IDs and key IDs must be unique")
    for attestor in policy["attestors"]:
        if ed25519_key_id(attestor["public_key_base64"]) != attestor["key_id"]:
            raise CandidateGitError(
                f"trusted run attestor key ID mismatch: {attestor['attestor_id']}"
            )
    return policy, {
        "path": TRUSTED_ATTESTORS_RELATIVE,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "canonical_sha256": canonical_sha256(policy),
    }


def _load_candidate_run(
    repo: Path,
    audit_commit: str,
    run_result_manifest_path: str,
    completion_attestation_path: str,
    completion_signature_path: str,
    release_manifest_sha256: str,
    private_ledger_sha256: str,
    schema_root: Path,
) -> tuple[dict, dict, list[dict], dict, dict, dict, dict, str, str]:
    """Load one result only through its post-result manifest and release trust root."""
    policy, policy_metadata = _load_trusted_attestor_policy(repo, schema_root)
    source_exporter_policy, source_exporter_policy_metadata = (
        load_source_exporter_policy(repo, schema_root, production=True)
    )
    audit_commit = resolve_commit(repo, audit_commit)
    completion_verification = verify_trusted_completion(
        repo,
        audit_commit,
        run_result_manifest_path,
        completion_attestation_path,
        completion_signature_path,
        release_manifest_sha256,
        schema_root=schema_root,
        production=True,
    )
    run_manifest, run_manifest_metadata = read_authenticated_json(
        repo, audit_commit, run_result_manifest_path
    )
    validate_schema(
        run_manifest,
        schema_root / "run-result-manifest.schema.json",
        "candidate run-result manifest",
    )
    if run_manifest["release_manifest_sha256"] != release_manifest_sha256:
        raise CandidateGitError("run-result manifest release binding mismatch")
    if (
        run_manifest["trusted_run_attestors_canonical_sha256"]
        != policy_metadata["canonical_sha256"]
    ):
        raise CandidateGitError("run-result manifest trusted-attestor binding mismatch")

    result_commit = resolve_commit(repo, run_manifest["result_commit"])
    freeze_commit = resolve_commit(repo, run_manifest["freeze_commit"])
    if freeze_commit == result_commit or not is_ancestor(repo, freeze_commit, result_commit):
        raise CandidateGitError(
            "candidate freeze commit must be a distinct ancestor of the result commit"
        )
    if result_commit == audit_commit or not is_ancestor(repo, result_commit, audit_commit):
        raise CandidateGitError(
            "candidate result commit must be a distinct ancestor of the audit-manifest commit"
        )

    candidate_reference = run_manifest["candidate_result"]
    review_reference = run_manifest["review_ledger"]
    receipt_reference = run_manifest["run_start_receipt"]
    start_signature_reference = run_manifest["run_start_signature"]
    freeze_reference = run_manifest["freeze_manifest"]
    bound_paths = {
        reference["path"]
        for reference in (
            candidate_reference,
            review_reference,
            receipt_reference,
            start_signature_reference,
            freeze_reference,
        )
    }
    if len(bound_paths) != 5:
        raise CandidateGitError("run-result manifest artifact paths must be unique")
    candidate, _ = read_authenticated_json(
        repo,
        result_commit,
        candidate_reference["path"],
        expected_sha256=candidate_reference["sha256"],
        expected_blob_oid=candidate_reference["git_blob_oid"],
    )
    reviews, _ = read_authenticated_json(
        repo,
        result_commit,
        review_reference["path"],
        expected_sha256=review_reference["sha256"],
        expected_blob_oid=review_reference["git_blob_oid"],
    )
    receipt_raw, _ = read_authenticated_bytes(
        repo,
        result_commit,
        receipt_reference["path"],
        expected_sha256=receipt_reference["sha256"],
        expected_blob_oid=receipt_reference["git_blob_oid"],
    )
    signature_raw, _ = read_authenticated_bytes(
        repo,
        result_commit,
        start_signature_reference["path"],
        expected_sha256=start_signature_reference["sha256"],
        expected_blob_oid=start_signature_reference["git_blob_oid"],
    )
    try:
        receipt = json.loads(receipt_raw)
    except json.JSONDecodeError as error:
        raise CandidateGitError("run-start receipt is not JSON") from error
    validate_schema(candidate, schema_root / "candidate.schema.json", "candidate result")
    validate_schema(reviews, schema_root / "review-ledger.schema.json", "review ledger")
    validate_schema(receipt, schema_root / "run-start-receipt.schema.json", "run-start receipt")
    if candidate["review_ledger"] != review_reference:
        raise CandidateGitError("candidate result exact review-ledger binding mismatch")
    if candidate["run_start_receipt"] != receipt_reference:
        raise CandidateGitError("candidate result exact run-start receipt binding mismatch")
    if candidate["run_start_signature"] != start_signature_reference:
        raise CandidateGitError("candidate result exact run-start signature binding mismatch")
    if candidate["freeze_commit"] != freeze_commit or candidate["freeze_manifest"] != freeze_reference:
        raise CandidateGitError("candidate result exact freeze binding mismatch")

    freeze, freeze_metadata = read_authenticated_json(
        repo,
        freeze_commit,
        freeze_reference["path"],
        expected_sha256=freeze_reference["sha256"],
        expected_blob_oid=freeze_reference["git_blob_oid"],
    )
    validate_schema(
        freeze, schema_root / "candidate-freeze-manifest.schema.json", "candidate freeze"
    )
    for label, field, expected in (
        ("release manifest", "release_manifest_sha256", release_manifest_sha256),
        (
            "private opportunity ledger",
            "private_opportunity_ledger_canonical_sha256",
            private_ledger_sha256,
        ),
    ):
        if candidate[field] != expected:
            raise CandidateGitError(f"candidate {label} binding mismatch")
        if freeze[field] != expected:
            raise CandidateGitError(f"freeze manifest {label} binding mismatch")
    if candidate["candidate_id"] != freeze["candidate_id"]:
        raise CandidateGitError("candidate ID differs from pre-run freeze")

    policy_binding = freeze["trusted_run_attestors"]
    policy_at_freeze, policy_at_freeze_metadata = read_authenticated_json(
        repo,
        freeze_commit,
        TRUSTED_ATTESTORS_RELATIVE,
        expected_sha256=policy_binding["raw_sha256"],
        expected_blob_oid=policy_binding["git_blob_oid"],
    )
    if policy_at_freeze != policy:
        raise CandidateGitError("freeze used a different trusted-attestor policy")
    if (
        policy_binding["path"] != TRUSTED_ATTESTORS_RELATIVE
        or policy_binding["raw_sha256"] != policy_metadata["raw_sha256"]
        or policy_binding["canonical_sha256"] != policy_metadata["canonical_sha256"]
        or policy_binding["status"] != "CONFIGURED"
        or policy_binding["attestor_key_ids"]
        != sorted(attestor["key_id"] for attestor in policy["attestors"])
        or policy_at_freeze_metadata["git_blob_oid"] != policy_binding["git_blob_oid"]
    ):
        raise CandidateGitError("freeze trusted-attestor policy binding mismatch")

    source_policy_binding = freeze["trusted_source_exporters"]
    source_policy_at_freeze, source_policy_at_freeze_metadata = (
        read_authenticated_json(
            repo,
            freeze_commit,
            TRUSTED_SOURCE_EXPORTERS_RELATIVE,
            expected_sha256=source_policy_binding["raw_sha256"],
            expected_blob_oid=source_policy_binding["git_blob_oid"],
        )
    )
    if source_policy_at_freeze != source_exporter_policy:
        raise CandidateGitError(
            "freeze used a different trusted source-exporter policy"
        )
    if (
        source_policy_binding["path"] != TRUSTED_SOURCE_EXPORTERS_RELATIVE
        or source_policy_binding["raw_sha256"]
        != source_exporter_policy_metadata["raw_sha256"]
        or source_policy_binding["canonical_sha256"]
        != source_exporter_policy_metadata["canonical_sha256"]
        or source_policy_binding["status"] != "CONFIGURED"
        or source_policy_binding["exporter_key_ids"]
        != sorted(
            exporter["key_id"]
            for exporter in source_exporter_policy["exporters"]
        )
        or source_policy_at_freeze_metadata["git_blob_oid"]
        != source_policy_binding["git_blob_oid"]
    ):
        raise CandidateGitError("freeze trusted source-exporter policy binding mismatch")

    expected_receipt_bindings = {
        "release_manifest_sha256": release_manifest_sha256,
        "trusted_run_attestors_canonical_sha256": policy_metadata["canonical_sha256"],
        "candidate_id": candidate["candidate_id"],
        "freeze_commit": freeze_commit,
        "freeze_manifest": freeze_reference,
        "freeze_nonce": freeze["run_nonce"],
        "attestor_key_id": run_manifest["attestor_key_id"],
        "signature_context": policy["signature_context"],
    }
    for field, expected in expected_receipt_bindings.items():
        if receipt[field] != expected:
            raise CandidateGitError(f"run-start receipt {field} binding mismatch")
    attestor = next(
        (
            row
            for row in policy["attestors"]
            if row["key_id"] == receipt["attestor_key_id"]
            and row["attestor_id"] == receipt["attestor_id"]
        ),
        None,
    )
    if attestor is None:
        raise CandidateGitError("run-start receipt was not signed by a release-trusted attestor")
    verify_ed25519_signature(
        receipt_raw,
        signature_raw,
        public_key_base64=attestor["public_key_base64"],
    )

    by_role: dict[str, list[dict]] = defaultdict(list)
    seen_paths: set[str] = set()
    seen_hashes: set[str] = set()
    loaded: dict[str, dict] = {}
    loaded_raw: dict[str, bytes] = {}
    frozen_files: dict[str, dict] = {}
    schema_by_role = {
        "hierarchy": "candidate-hierarchy.schema.json",
        "relation_ledger": "relation-ledger.schema.json",
        "authority_source_export": "authority-source-export.schema.json",
        "authority_source_export_attestation": (
            "authority-source-export-attestation.schema.json"
        ),
        "prompt_leakage_audit": "prompt-leakage-audit.schema.json",
        "semantic_prompt_audit": "prompt-leakage-audit.schema.json",
    }
    for entry in freeze["files"]:
        if entry["path"] in seen_paths or entry["sha256"] in seen_hashes:
            raise CandidateGitError("freeze manifest paths and content hashes must be unique")
        seen_paths.add(entry["path"])
        seen_hashes.add(entry["sha256"])
        by_role[entry["role"]].append(entry)
        frozen_files[entry["path"]] = entry
        if entry["role"] in {
            "review_prompt",
            "review_input",
            "authority_source_export_signature",
            "prompt_leakage_audit_signature",
            "semantic_prompt_audit_signature",
        }:
            raw, _ = read_authenticated_bytes(
                repo,
                freeze_commit,
                entry["path"],
                expected_sha256=entry["sha256"],
                expected_blob_oid=entry["git_blob_oid"],
            )
            if not raw.strip() or entry["schema_version"] is not None:
                raise CandidateGitError(
                    f"frozen opaque input is empty or mislabeled: {entry['path']}"
                )
            if entry["role"] in {
                "authority_source_export_signature",
                "prompt_leakage_audit_signature",
                "semantic_prompt_audit_signature",
            } and len(raw) != 64:
                raise CandidateGitError(
                    f"frozen source-export signature has invalid length: {entry['path']}"
                )
            loaded_raw[entry["path"]] = raw
            continue
        raw = read_bytes(repo, freeze_commit, entry["path"])
        value, _ = read_authenticated_json(
            repo,
            freeze_commit,
            entry["path"],
            expected_sha256=entry["sha256"],
            expected_blob_oid=entry["git_blob_oid"],
        )
        loaded_raw[entry["path"]] = raw
        if value.get("schema_version") != entry["schema_version"]:
            raise CandidateGitError(f"freeze file schema mismatch: {entry['path']}")
        validate_schema(
            value,
            schema_root / schema_by_role[entry["role"]],
            f"frozen {entry['role']} {entry['path']}",
        )
        loaded[entry["path"]] = value
    if len(by_role["hierarchy"]) != 1 or len(by_role["relation_ledger"]) != 1:
        raise CandidateGitError("freeze must contain exactly one hierarchy and relation ledger")
    source_roles = {
        "authority_source_export",
        "authority_source_export_attestation",
        "authority_source_export_signature",
    }
    source_entries_by_group: dict[str, dict[str, dict]] = defaultdict(dict)
    for role in sorted(source_roles):
        for entry in by_role[role]:
            group_id = entry.get("source_export_group_id")
            if not group_id or role in source_entries_by_group[group_id]:
                raise CandidateGitError(
                    "authority source-export freeze groups must have one entry per role"
                )
            source_entries_by_group[group_id][role] = entry
    if not source_entries_by_group or any(
        set(group) != source_roles for group in source_entries_by_group.values()
    ):
        raise CandidateGitError(
            "freeze must contain one complete authenticated triplet per authority source export"
        )
    source_exports: list[dict] = []
    for group_id, group in sorted(source_entries_by_group.items()):
        export_entry = group["authority_source_export"]
        attestation_entry = group["authority_source_export_attestation"]
        signature_entry = group["authority_source_export_signature"]
        source_export = loaded[export_entry["path"]]
        attestation = loaded[attestation_entry["path"]]
        if (
            source_export["source_export_id"] != group_id
            or attestation["source_export_id"] != group_id
            or attestation["detached_signature_path"] != signature_entry["path"]
        ):
            raise CandidateGitError(
                f"authority source-export freeze group binding mismatch: {group_id}"
            )
        authenticated = authenticate_source_export(
            source_export=source_export,
            source_export_raw=loaded_raw[export_entry["path"]],
            source_export_metadata={
                field: export_entry[field]
                for field in ("path", "sha256", "git_blob_oid")
            },
            attestation=attestation,
            attestation_raw=loaded_raw[attestation_entry["path"]],
            signature_raw=loaded_raw[signature_entry["path"]],
            policy=source_exporter_policy,
            production=True,
        )
        source_exports.append(authenticated)
    audit_count = len(by_role["prompt_leakage_audit"])
    if any(
        len(by_role[role]) != audit_count
        for role in (
            "review_prompt",
            "review_input",
            "prompt_leakage_audit_signature",
            "semantic_prompt_audit",
            "semantic_prompt_audit_signature",
        )
    ):
        raise CandidateGitError(
            "every frozen review prompt/input must have one signed deterministic and "
            "one signed semantic leakage audit"
        )
    for role, signature_role in (
        ("prompt_leakage_audit", "prompt_leakage_audit_signature"),
        ("semantic_prompt_audit", "semantic_prompt_audit_signature"),
    ):
        for entry in by_role[role]:
            audit = loaded[entry["path"]]
            prompt_entry = frozen_files.get(audit["prompt"]["path"])
            input_entry = frozen_files.get(audit["input"]["path"])
            audit_signature_reference = audit["authentication"]["signature"]
            signature_entry = frozen_files.get(audit_signature_reference["path"])
            if (
                prompt_entry is None
                or prompt_entry["role"] != "review_prompt"
                or any(
                    audit["prompt"][field] != prompt_entry[field]
                    for field in ("path", "sha256", "git_blob_oid")
                )
                or input_entry is None
                or input_entry["role"] != "review_input"
                or any(
                    audit["input"][field] != input_entry[field]
                    for field in ("path", "sha256", "git_blob_oid")
                )
                or signature_entry is None
                or signature_entry["role"] != signature_role
                or any(
                    audit_signature_reference[field] != signature_entry[field]
                    for field in ("path", "sha256", "git_blob_oid")
                )
            ):
                raise CandidateGitError(
                    f"frozen {role} binding mismatch: {entry['path']}"
                )
    hierarchy = loaded[by_role["hierarchy"][0]["path"]]
    relations = loaded[by_role["relation_ledger"][0]["path"]]
    run_binding = {
        "audit_commit": audit_commit,
        "run_result_manifest": {"path": run_result_manifest_path, **run_manifest_metadata},
        "result_commit": result_commit,
        "freeze_commit": freeze_commit,
        "freeze_manifest": {**freeze_reference, "verified": freeze_metadata},
        "candidate_result": candidate_reference,
        "review_ledger": review_reference,
        "run_start_receipt": receipt_reference,
        "run_start_signature": start_signature_reference,
        "trusted_attestor_id": attestor["attestor_id"],
        "trusted_attestor_key_id": attestor["key_id"],
        "trusted_source_exporters": source_policy_binding,
        "authority_source_exports": [
            {
                "source_export_group_id": group_id,
                "export": {
                    field: group["authority_source_export"][field]
                    for field in ("path", "sha256", "git_blob_oid")
                },
                "trusted_export_attestation": {
                    field: group["authority_source_export_attestation"][field]
                    for field in ("path", "sha256", "git_blob_oid")
                },
                "trusted_export_signature": {
                    field: group["authority_source_export_signature"][field]
                    for field in ("path", "sha256", "git_blob_oid")
                },
            }
            for group_id, group in sorted(source_entries_by_group.items())
        ],
        "trusted_completion": completion_verification,
    }
    return (
        candidate,
        hierarchy,
        source_exports,
        relations,
        reviews,
        run_binding,
        frozen_files,
        freeze_commit,
        result_commit,
    )


# Historical test imports use this private name. It now resolves only the secure
# run-result-manifest loader; the old caller-selected candidate/ledger interface is gone.
_load_candidate_freeze = _load_candidate_run


def compare_production(
    repo_root: Path,
    private_run: Path,
    audit_commit: str,
    run_result_manifest_path: str,
    completion_attestation_path: str,
    completion_signature_path: str,
) -> dict:
    repo_root = repo_root.resolve()
    evaluation_root = repo_root / "docs/evaluations/site-graph-v0"
    schema_root = evaluation_root / "schemas"
    release = verify_release(repo_root)
    private_verification = verify_private_ledgers(private_run, evaluation_root)

    opportunity_summary = read_json(evaluation_root / "planned-opportunity-summary.json")
    private_opportunity = read_json(private_run / "private-opportunity-ledger.json")
    validate_schema(
        opportunity_summary,
        schema_root / "opportunity-summary.schema.json",
        "public opportunity summary",
    )
    validate_schema(
        private_opportunity,
        schema_root / "private-opportunity-ledger.schema.json",
        "private opportunity ledger",
    )
    private_digest = read_json(evaluation_root / "private-ledger-digests.json")
    private_ledger_sha = private_digest["ledgers"]["private_opportunity_membership"][
        "canonical_json_sha256"
    ]
    (
        candidate,
        hierarchy,
        source_exports,
        relations,
        reviews,
        run_binding,
        frozen_files,
        freeze_commit,
        result_commit,
    ) = _load_candidate_run(
        repo_root,
        audit_commit,
        run_result_manifest_path,
        completion_attestation_path,
        completion_signature_path,
        release["manifest_sha256"],
        private_ledger_sha,
        schema_root,
    )
    decisions = _validate_review_artifacts(
        repo_root,
        result_commit,
        reviews,
        schema_root,
        freeze_commit=freeze_commit,
        frozen_files=frozen_files,
        source_exports=source_exports,
        source_export_groups=run_binding["authority_source_exports"],
        candidate_id=candidate["candidate_id"],
    )
    baseline_records = read_records(private_run / "private-record-evidence.ndjson.gz")
    metrics = read_json(evaluation_root / "baseline-metrics.json")
    node_scope = read_json(evaluation_root / "baseline-node-scope.json")
    crosswalk = read_json(evaluation_root / "type-crosswalk.json")

    scope_by_target = {
        row["target_id"]: row["scope_class"] for row in node_scope["nodes"]
    }
    links = [
        {"artifact_id": row["artifact_id"], "museum": row["museum"], "target_id": target}
        for row in baseline_records
        for target in row["baseline_site_target_ids"]
    ]
    recomputed = build_metrics(baseline_records, links, scope_by_target)
    recomputed["planned_slice_maximum_measurable_effect"] = {
        "source": "planned-opportunity-summary.json",
        "per_museum": opportunity_summary["per_museum"],
        "pair_side_ceilings": opportunity_summary["pair_side_ceilings"],
        "interpretation": (
            "Numeric intent-to-treat upper bounds, not expected effects or accuracy claims. "
            "Unsupported, broad/administrative, abstained, failed, and disputed research "
            "remains in denominators and earns zero credit."
        ),
    }
    if recomputed != metrics:
        raise ValueError("committed baseline metrics do not recompute from authenticated private ledger")

    report = compare_core(
        baseline_records,
        metrics,
        node_scope,
        opportunity_summary,
        private_opportunity,
        crosswalk,
        candidate,
        hierarchy,
        source_exports,
        relations,
        decisions,
    )
    report["run_binding"] = run_binding
    archive_authentication = private_verification["archive_authentication"]
    report["provenance_status"] = {
        "evidence_scope": "AUTHENTICATED_RELEASE_SNAPSHOT",
        "archive_sha256": archive_authentication["archive_sha256"],
        "snapshot_acquisition_integrity": archive_authentication[
            "snapshot_acquisition_integrity"
        ],
        "upstream_production_lineage": archive_authentication[
            "upstream_production_lineage"
        ],
        "overall_contract_status": (
            "READY_SNAPSHOT_CONDITIONAL"
            if report["outcome"] != "INVALID"
            else "INVALID"
        ),
        "downstream_product_verdict": report["outcome"],
    }
    validate_schema(report, schema_root / "comparison-report.schema.json", "comparison report")
    return report


def _invalid_production_provenance(repo_root: Path, private_run: Path) -> dict:
    """Keep verified snapshot acquisition separate from candidate/comparator failure."""
    repo_root = repo_root.resolve()
    evaluation_root = repo_root / "docs/evaluations/site-graph-v0"
    archive_sha = "UNAVAILABLE_DUE_TO_INVALID_CONTRACT"
    snapshot_status = "INVALID"
    lineage_status = "UNAVAILABLE_DISCLOSED"
    try:
        private_verification = verify_private_ledgers(
            private_run.resolve(), evaluation_root
        )
        archive_authentication = private_verification["archive_authentication"]
        archive_sha = archive_authentication["archive_sha256"]
        snapshot_status = archive_authentication["snapshot_acquisition_integrity"]
        lineage_status = archive_authentication["upstream_production_lineage"]
    except (OSError, KeyError, ValueError, RuntimeError, json.JSONDecodeError):
        try:
            snapshot = read_json(evaluation_root / "input-snapshot.json")
            archive_sha = snapshot["corpus"]["archive_acquisition"]["archive_sha256"]
        except (OSError, KeyError, ValueError, json.JSONDecodeError):
            pass
    return {
        "evidence_scope": "PRODUCTION_COMPARATOR_INVALID",
        "archive_sha256": archive_sha,
        "snapshot_acquisition_integrity": snapshot_status,
        "upstream_production_lineage": lineage_status,
        "overall_contract_status": "INVALID",
        "downstream_product_verdict": "INVALID",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Production mode accepts only an authenticated release root, its pinned private "
            "runtime ledgers, and candidate bytes read from immutable Git commits."
        )
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--private-run", type=Path, required=True)
    parser.add_argument("--audit-commit", required=True)
    parser.add_argument("--run-result-manifest-path", required=True)
    parser.add_argument("--completion-attestation-path", required=True)
    parser.add_argument("--completion-signature-path", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = compare_production(
            args.repo_root,
            args.private_run,
            args.audit_commit,
            args.run_result_manifest_path,
            args.completion_attestation_path,
            args.completion_signature_path,
        )
    except (
        CandidateGitError,
        SchemaValidationError,
        ValueError,
        RuntimeError,
    ) as error:
        report = _invalid_report(
            [str(error)],
            _invalid_production_provenance(args.repo_root, args.private_run),
        )
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"outcome": report["outcome"], "integrity": report["integrity"]["passed"]},
            sort_keys=True,
        )
    )
    if report["outcome"] == "INVALID":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
