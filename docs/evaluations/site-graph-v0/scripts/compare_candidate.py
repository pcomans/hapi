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
    AMBIGUITY_MAXIMUM_INCREASE,
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
from schema_validation import SchemaValidationError, validate_schema


EVENTS = (
    "new_link",
    "strict_refinement_reassignment",
    "additional_identity",
    "unchanged",
    "loss",
    "uncredited_change",
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
    hierarchy: dict, source_snapshots: list[dict], crosswalk: dict, errors: list[str]
) -> tuple[dict[str, str], dict[str, str]]:
    raw_mapping = _raw_type_crosswalk(crosswalk, errors)
    snapshots: dict[str, dict] = {}
    source_records: dict[str, tuple[str, dict]] = {}
    target_records: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for snapshot in source_snapshots:
        snapshot_id = snapshot.get("source_snapshot_id")
        if not snapshot_id or snapshot_id in snapshots:
            errors.append("source snapshot IDs must be nonempty and unique")
            continue
        snapshots[snapshot_id] = snapshot
        records = snapshot.get("records", [])
        completeness = snapshot.get("completeness", {})
        if completeness.get("record_count") != len(records):
            errors.append(f"source snapshot {snapshot_id} complete record count mismatch")
        if completeness.get("records_canonical_sha256") != canonical_sha256(records):
            errors.append(f"source snapshot {snapshot_id} complete-record hash mismatch")
        if records != sorted(records, key=lambda row: row.get("source_record_id", "")):
            errors.append(f"source snapshot {snapshot_id} records are not canonically sorted")
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
            source_records[record_id] = (snapshot_id, record)
            target_records[target_id].append((snapshot_id, record))

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
            "candidate hierarchy must census every source-snapshot target: "
            f"missing={sorted(set(target_records) - set(nodes_by_target))}, "
            f"extra={sorted(set(nodes_by_target) - set(target_records))}"
        )

    for target_id, node in sorted(nodes_by_target.items()):
        all_records = target_records.get(target_id, [])
        expected_record_ids = sorted(row["source_record_id"] for _, row in all_records)
        expected_snapshot_ids = sorted({snapshot_id for snapshot_id, _ in all_records})
        if node.get("source_record_ids") != expected_record_ids:
            errors.append(
                f"candidate hierarchy {target_id} must bind all and only its source records"
            )
        if node.get("source_snapshot_ids") != expected_snapshot_ids:
            errors.append(
                f"candidate hierarchy {target_id} source snapshot census mismatch"
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


def _fraction_from_ratio(value: dict) -> Fraction:
    denominator = value.get("denominator", 0)
    return Fraction(value.get("numerator", 0), denominator) if denominator else Fraction(0)


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
        "schema_version": "site-graph-v0-comparison-report/2",
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
    source_snapshots: list[dict],
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
    baseline_scope = {
        row.get("target_id"): row.get("scope_class") for row in node_scope.get("nodes", [])
    }
    if None in baseline_scope or len(baseline_scope) != len(node_scope.get("nodes", [])):
        errors.append("baseline node scope target IDs must be nonempty and unique")

    derived_scope, candidate_authority_locator = _derive_candidate_scope(
        hierarchy, source_snapshots, crosswalk, errors
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
    credited_link_bindings: dict[str, dict[str, tuple[str, str]]] = defaultdict(dict)
    strict_pairs_by_artifact: dict[str, set[tuple[str, str]]] = defaultdict(set)
    events: list[dict] = []
    refinement_modes: Counter[str] = Counter()

    for artifact_id in sorted(itt_by_id):
        baseline = baseline_by_id[artifact_id]
        baseline_targets = baseline_links[artifact_id]
        record = candidate_by_id.get(artifact_id)
        if record is None:
            continue
        status = record.get("resolution_status")
        direct_links = record.get("direct_links", [])
        abstention_reason = record.get("abstention_reason")
        if status not in {"linked", "ambiguous", "abstained", "unmatched"}:
            errors.append(f"candidate {artifact_id} resolution status invalid")
        if (status == "linked") != bool(direct_links):
            errors.append(f"candidate {artifact_id} linked status/direct links mismatch")
        if record.get("has_blocking_ambiguity") is not (status == "ambiguous"):
            errors.append(f"candidate {artifact_id} blocking ambiguity mismatch")
        if status == "abstained":
            if abstention_reason not in ABSTENTION_REASONS:
                errors.append(f"candidate {artifact_id} abstention reason invalid")
        elif abstention_reason is not None:
            errors.append(f"candidate {artifact_id} abstention reason only applies to abstention")

        targets_seen: set[str] = set()
        supported_targets: set[str] = set()
        unsupported_targets: set[str] = set()
        for link in direct_links:
            target_id = link.get("target_id")
            support_key = link.get("support_decision_key")
            opportunity_binding = (
                link.get("opportunity_id"),
                link.get("opportunity_binding_sha256"),
            )
            if not target_id or target_id in targets_seen:
                errors.append(f"candidate {artifact_id} direct targets must be nonempty and unique")
                continue
            targets_seen.add(target_id)
            if opportunity_binding not in itt_bindings_by_id.get(artifact_id, set()):
                errors.append(
                    f"candidate link {artifact_id}/{target_id} is not bound to an exact private opportunity"
                )
                unsupported_targets.add(target_id)
                continue
            if target_id not in all_targets:
                errors.append(f"candidate {artifact_id} target {target_id} lacks authenticated scope")
                continue
            if target_id in baseline_targets:
                if support_key is not None:
                    errors.append(f"unchanged direct target {artifact_id}/{target_id} must not claim new support")
                supported_targets.add(target_id)
                continue
            subject = {
                "artifact_id": artifact_id,
                "target_id": target_id,
                "opportunity_id": opportunity_binding[0],
                "opportunity_binding_sha256": opportunity_binding[1],
            }
            expected_key = decision_key("link_support", subject)
            if support_key is None:
                unsupported_targets.add(target_id)
                continue
            if support_key != expected_key or support_key not in decisions:
                errors.append(f"candidate link {artifact_id}/{target_id} lacks exact review decision")
                unsupported_targets.add(target_id)
                continue
            referenced_decisions.add(support_key)
            if decisions[support_key].get("disagreement"):
                unresolved_disagreements.add(support_key)
            if _decision_supports(decisions, support_key, "link_support", subject):
                supported_targets.add(target_id)
                if target_scope[target_id] == "specific_candidate":
                    credited_links[artifact_id].add(target_id)
                    credited_link_bindings[artifact_id][target_id] = opportunity_binding
            else:
                unsupported_targets.add(target_id)
        candidate_links[artifact_id] = supported_targets

        covered_baseline = baseline_targets & supported_targets
        equivalent_pairs: set[tuple[str, str]] = set()
        strict_pairs: set[tuple[str, str]] = set()
        for baseline_target in sorted(baseline_targets):
            for candidate_target in sorted(supported_targets - baseline_targets):
                if identity.find(candidate_target) == identity.find(baseline_target):
                    equivalent_pairs.add((baseline_target, candidate_target))
                    covered_baseline.add(baseline_target)
                if (candidate_target, baseline_target) in supported_strict:
                    strict_pairs.add((baseline_target, candidate_target))
                    covered_baseline.add(baseline_target)
        strict_pairs_by_artifact[artifact_id] = strict_pairs
        losses = baseline_targets - covered_baseline
        unrelated_credited = {
            target
            for target in credited_links[artifact_id]
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
                    if baseline_target in supported_targets
                    else "old_direct_edge_replaced_ancestor_semantics_preserved"
                )
                refinement_modes[mode] += 1
        elif not baseline_targets and credited_links[artifact_id]:
            event = "new_link"
        elif baseline_targets and unrelated_credited:
            event = "additional_identity"
        elif unsupported_targets or any(
            not any((baseline_target, target) in equivalent_pairs for baseline_target in baseline_targets)
            for target in supported_targets - baseline_targets
        ):
            event = "uncredited_change"
        else:
            event = "unchanged"
        events.append(
            {
                "artifact_id": artifact_id,
                "museum": museum_by_id[artifact_id],
                "event": event,
                "baseline_direct_target_ids": sorted(baseline_targets),
                "candidate_supported_direct_target_ids": sorted(supported_targets),
                "uncredited_candidate_target_ids": sorted(unsupported_targets),
                "supported_strict_refinement_pairs": [
                    list(pair) for pair in sorted(strict_pairs)
                ],
                "lost_baseline_target_ids": sorted(losses),
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

    prospective_shared_targets: dict[tuple[str, str], set[str]] = {}
    for left, right in PAIRS:
        left_targets = {
            target
            for artifact_id, targets in credited_links.items()
            if museum_by_id.get(artifact_id) == left
            for target in targets
        }
        right_targets = {
            target
            for artifact_id, targets in credited_links.items()
            if museum_by_id.get(artifact_id) == right
            for target in targets
        }
        shared_roots = {identity.find(target) for target in left_targets} & {
            identity.find(target) for target in right_targets
        }
        prospective_shared_targets[(left, right)] = {
            target
            for target in left_targets | right_targets
            if identity.find(target) in shared_roots
        }

    prospective_targets = set().union(*prospective_shared_targets.values())
    for left, right in combinations(sorted(prospective_targets), 2):
        if identity.find(left) != identity.find(right) and not positively_distinct(left, right):
            errors.append(
                f"prospective counted targets lack positive distinctness evidence: {left}/{right}"
            )
    baseline_targets_by_museum = {
        museum: {
            target
            for artifact_id, targets in baseline_links.items()
            if baseline_by_id[artifact_id].get("museum") == museum
            for target in targets
        }
        for museum in MUSEUMS
    }
    for pair, prospective in prospective_shared_targets.items():
        left, right = pair
        shared_baseline_roots = {
            identity.find(target) for target in baseline_targets_by_museum[left]
        } & {identity.find(target) for target in baseline_targets_by_museum[right]}
        shared_baseline_targets = {
            target
            for museum in pair
            for target in baseline_targets_by_museum[museum]
            if identity.find(target) in shared_baseline_roots
        }
        for candidate_target in sorted(prospective):
            if identity.find(candidate_target) in shared_baseline_roots:
                continue
            for baseline_target in sorted(shared_baseline_targets):
                if not positively_distinct(candidate_target, baseline_target):
                    errors.append(
                        "prospective gained target lacks positive distinctness from a shared "
                        f"baseline identity: {candidate_target}/{baseline_target}"
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
        gained_specific = {
            root
            for root in candidate_shared - baseline_shared
            if identity_scope.get(root) == "specific_candidate"
            and any(
                identity.find(target) == root
                for museum in (left, right)
                for artifact in artifacts_by_museum[museum]
                for target in credited_links.get(artifact, set())
            )
            and all(
                any(
                    identity.find(target) == root
                    and target_scope[target] == "specific_candidate"
                    for artifact in artifacts_by_museum[museum]
                    for target in candidate_links[artifact]
                )
                for museum in (left, right)
            )
        }

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
                member_category[artifact_id] = row["category"]
                member_bindings[artifact_id] = bindings
            pair_event_counts: Counter[str] = Counter()
            affected_artifacts: set[str] = set()
            for artifact_id in sorted(member_category):
                gained_credited_targets = {
                    target
                    for target in credited_links.get(artifact_id, set())
                    if identity.find(target) in gained_specific
                    and credited_link_bindings.get(artifact_id, {}).get(target)
                    in member_bindings[artifact_id]
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
    abstentions: Counter[str] = Counter()
    for artifact_id in sorted(candidate_by_id):
        museum = museum_by_id[artifact_id]
        baseline_value = bool(baseline_by_id[artifact_id].get("has_blocking_ambiguity"))
        candidate_value = bool(candidate_by_id[artifact_id].get("has_blocking_ambiguity"))
        candidate_blocking[museum] += int(candidate_value) - int(baseline_value)
        if candidate_by_id[artifact_id].get("resolution_status") == "abstained":
            abstentions[candidate_by_id[artifact_id]["abstention_reason"]] += 1
    ambiguity_by_museum = {}
    ambiguity_pass = True
    for museum in MUSEUMS:
        delta = Fraction(
            candidate_blocking[museum] - baseline_blocking[museum], evidence_counts[museum]
        )
        passed = delta <= AMBIGUITY_MAXIMUM_INCREASE
        ambiguity_pass = ambiguity_pass and passed
        ambiguity_by_museum[museum] = {
            "baseline_blocking": ratio(baseline_blocking[museum], evidence_counts[museum]),
            "candidate_blocking": ratio(candidate_blocking[museum], evidence_counts[museum]),
            "delta": {"numerator": delta.numerator, "denominator": delta.denominator},
            "maximum_allowed_delta": {
                "numerator": AMBIGUITY_MAXIMUM_INCREASE.numerator,
                "denominator": AMBIGUITY_MAXIMUM_INCREASE.denominator,
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
        "schema_version": "site-graph-v0-comparison-report/2",
        "outcome": outcome,
        "ordered_decision_trace": ordered_trace,
        "integrity": {"passed": True, "errors": []},
        "safety_gates": safety,
        "event_counts": {event: event_counts[event] for event in EVENTS},
        "event_records": events,
        "reassignment_edge_modes": dict(sorted(refinement_modes.items())),
        "per_museum": per_museum,
        "pairs": pairs,
        "ambiguity_and_abstention": {
            "per_museum": ambiguity_by_museum,
            "candidate_abstention_reason_counts": dict(sorted(abstentions.items())),
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
) -> dict[str, dict]:
    decisions: dict[str, dict] = {}
    used_paths: set[str] = set()
    used_content_hashes: set[str] = set()
    used_invocation_ids: set[str] = set()
    frozen_files = frozen_files or {}

    def claim_unique(path: str, digest: str, label: str) -> None:
        if path in used_paths:
            raise ValueError(f"{label} path reused across reviews: {path}")
        if digest in used_content_hashes:
            raise ValueError(f"{label} bytes reused across reviews: {digest}")
        used_paths.add(path)
        used_content_hashes.add(digest)

    for ledger_decision in ledger["decisions"]:
        key = ledger_decision["decision_key"]
        kind = ledger_decision["decision_kind"]
        subject = ledger_decision["subject"]
        if key != decision_key(kind, subject) or key in decisions:
            raise ValueError("review decision keys must be canonical and unique")
        artifacts = []
        for reference in ledger_decision["review_artifacts"]:
            path = reference["path"]
            artifact, metadata = read_authenticated_json(
                repo,
                result_commit,
                path,
                expected_sha256=reference["sha256"],
                expected_blob_oid=reference["git_blob_oid"],
            )
            validate_schema(
                artifact, schema_root / "review-artifact.schema.json", f"review artifact {path}"
            )
            if canonical_sha256(artifact) != reference["canonical_record_sha256"]:
                raise ValueError(f"review artifact canonical record hash mismatch: {path}")
            claim_unique(path, metadata["sha256"], "review artifact")
            if (
                artifact["decision_key"] != key
                or artifact["decision_kind"] != kind
                or artifact["subject"] != subject
            ):
                raise ValueError(f"review artifact is not bound to ledger decision: {path}")
            if artifact["method"] == "human":
                if artifact["llm_interaction"] is not None:
                    raise ValueError(f"human review has LLM provenance: {path}")
            else:
                interaction = artifact["llm_interaction"]
                if not isinstance(interaction, dict):
                    raise ValueError(f"LLM review lacks full interaction provenance: {path}")
                invocation_id = interaction["review_invocation_id"]
                interaction_payload = {
                    "review_id": artifact["review_id"],
                    "review_invocation_id": invocation_id,
                    "decision_key": key,
                    "decision_kind": kind,
                    "subject": subject,
                    "model": interaction["model"],
                    "parameters": interaction["parameters"],
                    "prompt": interaction["prompt"],
                    "input": interaction["input"],
                    "raw_response": interaction["raw_response"],
                    "prompt_leakage_audit": interaction["prompt_leakage_audit"]["artifact"],
                }
                if interaction["interaction_binding_sha256"] != canonical_sha256(
                    interaction_payload
                ):
                    raise ValueError(f"LLM interaction binding hash mismatch: {path}")
                if invocation_id in used_invocation_ids:
                    raise ValueError(f"LLM review invocation ID reused: {invocation_id}")
                used_invocation_ids.add(invocation_id)
                if freeze_commit is None:
                    raise ValueError("LLM review cannot be validated without its pre-run freeze")
                prompt_reference = interaction["prompt"]
                prompt_entry = frozen_files.get(prompt_reference["path"])
                if (
                    prompt_entry is None
                    or prompt_entry.get("role") != "review_prompt"
                    or any(
                        prompt_reference[field] != prompt_entry[field]
                        for field in ("path", "sha256", "git_blob_oid")
                    )
                ):
                    raise ValueError(
                        f"LLM prompt was not an exact pre-generation frozen input: {path}"
                    )
                prompt_raw, _ = read_authenticated_bytes(
                    repo,
                    freeze_commit,
                    prompt_reference["path"],
                    expected_sha256=prompt_reference["sha256"],
                    expected_blob_oid=prompt_reference["git_blob_oid"],
                )
                if not prompt_raw.strip():
                    raise ValueError(f"LLM prompt is empty: {prompt_reference['path']}")
                claim_unique(
                    prompt_reference["path"], prompt_reference["sha256"], "LLM prompt"
                )
                for label in ("input", "raw_response"):
                    child = interaction[label]
                    raw, _ = read_authenticated_bytes(
                        repo,
                        result_commit,
                        child["path"],
                        expected_sha256=child["sha256"],
                        expected_blob_oid=child["git_blob_oid"],
                    )
                    if not raw.strip():
                        raise ValueError(f"LLM {label} is empty: {child['path']}")
                    claim_unique(child["path"], child["sha256"], f"LLM {label}")
                audit_reference = interaction["prompt_leakage_audit"]["artifact"]
                audit_entry = frozen_files.get(audit_reference["path"])
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
                audit, _ = read_authenticated_json(
                    repo,
                    freeze_commit,
                    audit_reference["path"],
                    expected_sha256=audit_reference["sha256"],
                    expected_blob_oid=audit_reference["git_blob_oid"],
                )
                validate_schema(
                    audit,
                    schema_root / "prompt-leakage-audit.schema.json",
                    f"prompt leakage audit {audit_reference['path']}",
                )
                if (
                    audit["review_id"] != artifact["review_id"]
                    or
                    audit["review_invocation_id"] != invocation_id
                    or audit["decision_key"] != key
                    or audit["decision_kind"] != kind
                    or audit["subject"] != subject
                    or audit["prompt"] != prompt_reference
                ):
                    raise ValueError(
                        f"prompt leakage audit is not bound to exact prompt/subject/decision: {path}"
                    )
                claim_unique(
                    audit_reference["path"],
                    audit_reference["sha256"],
                    "prompt leakage audit",
                )
            artifacts.append({**artifact, "_metadata": metadata})
        reviewer_ids = [artifact["reviewer"]["reviewer_id"] for artifact in artifacts]
        groups = [artifact["reviewer"]["independence_group"] for artifact in artifacts]
        hashes = [artifact["_metadata"]["sha256"] for artifact in artifacts]
        record_hashes = [canonical_sha256({k: v for k, v in artifact.items() if k != "_metadata"}) for artifact in artifacts]
        if (
            len(set(reviewer_ids)) != REVIEWS_PER_CREDITED_DECISION
            or len(set(groups)) != REVIEWS_PER_CREDITED_DECISION
            or len(set(hashes)) != REVIEWS_PER_CREDITED_DECISION
            or len(set(record_hashes)) != REVIEWS_PER_CREDITED_DECISION
        ):
            raise ValueError(f"review decision {key} lacks two distinct independent artifacts")
        outcomes = [artifact["outcome"] for artifact in artifacts]
        decisions[key] = {
            "decision_kind": kind,
            "subject": subject,
            "supported": outcomes == ["supported", "supported"],
            "disagreement": len(set(outcomes)) > 1,
            "review_artifact_sha256": sorted(hashes),
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
    release_manifest_sha256: str,
    private_ledger_sha256: str,
    schema_root: Path,
) -> tuple[dict, dict, list[dict], dict, dict, dict, dict, str, str]:
    """Load one result only through its post-result manifest and release trust root."""
    policy, policy_metadata = _load_trusted_attestor_policy(repo, schema_root)
    audit_commit = resolve_commit(repo, audit_commit)
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
    signature_reference = run_manifest["run_start_signature"]
    freeze_reference = run_manifest["freeze_manifest"]
    bound_paths = {
        reference["path"]
        for reference in (
            candidate_reference,
            review_reference,
            receipt_reference,
            signature_reference,
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
        signature_reference["path"],
        expected_sha256=signature_reference["sha256"],
        expected_blob_oid=signature_reference["git_blob_oid"],
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
    if candidate["run_start_signature"] != signature_reference:
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
    frozen_files: dict[str, dict] = {}
    schema_by_role = {
        "hierarchy": "candidate-hierarchy.schema.json",
        "relation_ledger": "relation-ledger.schema.json",
        "source_snapshot": "candidate-source-snapshot.schema.json",
        "prompt_leakage_audit": "prompt-leakage-audit.schema.json",
    }
    for entry in freeze["files"]:
        if entry["path"] in seen_paths or entry["sha256"] in seen_hashes:
            raise CandidateGitError("freeze manifest paths and content hashes must be unique")
        seen_paths.add(entry["path"])
        seen_hashes.add(entry["sha256"])
        by_role[entry["role"]].append(entry)
        frozen_files[entry["path"]] = entry
        if entry["role"] == "review_prompt":
            raw, _ = read_authenticated_bytes(
                repo,
                freeze_commit,
                entry["path"],
                expected_sha256=entry["sha256"],
                expected_blob_oid=entry["git_blob_oid"],
            )
            if not raw.strip() or entry["schema_version"] is not None:
                raise CandidateGitError(f"frozen review prompt is empty or mislabeled: {entry['path']}")
            continue
        value, _ = read_authenticated_json(
            repo,
            freeze_commit,
            entry["path"],
            expected_sha256=entry["sha256"],
            expected_blob_oid=entry["git_blob_oid"],
        )
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
    if not by_role["source_snapshot"]:
        raise CandidateGitError("freeze must contain at least one nonempty source snapshot")
    if len(by_role["review_prompt"]) != len(by_role["prompt_leakage_audit"]):
        raise CandidateGitError("every frozen review prompt must have one frozen leakage audit")
    for entry in by_role["prompt_leakage_audit"]:
        audit = loaded[entry["path"]]
        prompt_entry = frozen_files.get(audit["prompt"]["path"])
        if (
            prompt_entry is None
            or prompt_entry["role"] != "review_prompt"
            or any(
                audit["prompt"][field] != prompt_entry[field]
                for field in ("path", "sha256", "git_blob_oid")
            )
        ):
            raise CandidateGitError(f"frozen prompt audit binding mismatch: {entry['path']}")
    hierarchy = loaded[by_role["hierarchy"][0]["path"]]
    relations = loaded[by_role["relation_ledger"][0]["path"]]
    snapshots = [loaded[entry["path"]] for entry in by_role["source_snapshot"]]
    run_binding = {
        "audit_commit": audit_commit,
        "run_result_manifest": {"path": run_result_manifest_path, **run_manifest_metadata},
        "result_commit": result_commit,
        "freeze_commit": freeze_commit,
        "freeze_manifest": {**freeze_reference, "verified": freeze_metadata},
        "candidate_result": candidate_reference,
        "review_ledger": review_reference,
        "run_start_receipt": receipt_reference,
        "run_start_signature": signature_reference,
        "trusted_attestor_id": attestor["attestor_id"],
        "trusted_attestor_key_id": attestor["key_id"],
    }
    return (
        candidate,
        hierarchy,
        snapshots,
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
        snapshots,
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
        snapshots,
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = compare_production(
            args.repo_root,
            args.private_run,
            args.audit_commit,
            args.run_result_manifest_path,
        )
    except (
        CandidateGitError,
        SchemaValidationError,
        ValueError,
        RuntimeError,
    ) as error:
        try:
            snapshot = read_json(
                args.repo_root / "docs/evaluations/site-graph-v0/input-snapshot.json"
            )
            archive_sha = snapshot["corpus"]["archive_acquisition"]["archive_sha256"]
        except (OSError, KeyError, ValueError, json.JSONDecodeError):
            archive_sha = "UNAVAILABLE_DUE_TO_INVALID_CONTRACT"
        report = _invalid_report(
            [str(error)],
            {
                "evidence_scope": "PRODUCTION_COMPARATOR_INVALID",
                "archive_sha256": archive_sha,
                "snapshot_acquisition_integrity": "INVALID",
                "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
                "overall_contract_status": "INVALID",
                "downstream_product_verdict": "INVALID",
            },
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
