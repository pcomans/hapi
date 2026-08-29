#!/usr/bin/env python3
"""Apply exact private mention corrections without rewriting the frozen ITT."""

from __future__ import annotations

import argparse
import collections
import json
import os
import shutil
import tempfile
from pathlib import Path

from build_baseline import (
    build_metrics,
    build_opportunity_queue,
    canonical_json_sha256,
    gzip_ledger_digest,
    read_gzip_jsonl,
    read_json,
    resolution_state,
    sha256,
    validate_site_mention,
    write_gzip_jsonl,
    write_json,
)
from contract_constants import MINIMUM_AFFECTED_FRACTION, MUSEUMS, PAIRS
from metrics_core import partition_scopes, ratio
from private_ledgers import verify_private_ledgers
from schema_validation import validate_schema


DERIVED_RECORD_FIELDS = (
    "extracted_site_text_evidence",
    "site_mention_count",
    "site_mention_status_counts",
    "baseline_resolution_state",
    "baseline_site_target_ids",
    "baseline_site_target_scope_counts",
    "baseline_record_scope",
    "has_any_ambiguity",
    "has_blocking_ambiguity",
    "has_any_unmatched_expression",
)


def record_hash(correction: dict) -> str:
    value = {key: child for key, child in correction.items() if key != "record_sha256"}
    return canonical_json_sha256(value)


def _operation_slot(correction: dict) -> str:
    operation = correction["operation"]
    return (
        correction["artifact_id"]
        + "\0site-mention-resolution:"
        + operation["mention_id"]
    )


def _validate_resolution_shape(status: str, target_ids: list[str], label: str) -> None:
    if target_ids != sorted(set(target_ids)):
        raise ValueError(f"{label} target IDs must be sorted and unique")
    if status == "resolved" and len(target_ids) != 1:
        raise ValueError(f"{label} resolved mention must have exactly one target")
    if status == "unmatched" and target_ids:
        raise ValueError(f"{label} unmatched mention must have no targets")
    if status == "ambiguous" and len(target_ids) < 2:
        raise ValueError(f"{label} ambiguous mention must have at least two targets")


def _validate_chain(
    ledger: dict,
    records_by_id: dict[str, dict],
    source_by_mention: dict[str, dict],
    target_ids: set[str],
) -> None:
    seen_ids: set[str] = set()
    last_by_slot: dict[str, str] = {}
    previous_hash = None
    for index, correction in enumerate(ledger["corrections"], 1):
        if correction["sequence"] != index:
            raise ValueError("correction sequences must be contiguous from one")
        correction_id = correction["correction_id"]
        if correction_id in seen_ids:
            raise ValueError("correction IDs must be unique")
        if correction["previous_correction_sha256"] != previous_hash:
            raise ValueError(f"correction {correction_id} hash chain mismatch")
        if correction["record_sha256"] != record_hash(correction):
            raise ValueError(f"correction {correction_id} record hash mismatch")
        artifact_id = correction["artifact_id"]
        if artifact_id not in records_by_id:
            raise ValueError(f"correction {correction_id} references unknown artifact")
        operation = correction["operation"]
        mention_id = operation["mention_id"]
        if mention_id not in source_by_mention:
            raise ValueError(f"correction {correction_id} references unknown site mention")
        if source_by_mention[mention_id]["artifact_id"] != artifact_id:
            raise ValueError(f"correction {correction_id} mention/artifact binding mismatch")
        for endpoint in ("from", "to"):
            _validate_resolution_shape(
                operation[f"{endpoint}_status"],
                operation[f"{endpoint}_target_ids"],
                f"correction {correction_id} {endpoint}",
            )
        referenced_targets = set(operation["from_target_ids"]) | set(
            operation["to_target_ids"]
        )
        if referenced_targets - target_ids:
            raise ValueError(
                f"correction {correction_id} references unknown targets: "
                f"{sorted(referenced_targets - target_ids)}"
            )
        if (
            operation["from_status"],
            operation["from_target_ids"],
        ) == (
            operation["to_status"],
            operation["to_target_ids"],
        ):
            raise ValueError(f"correction {correction_id} is a no-op")
        slot = _operation_slot(correction)
        supersedes = correction["supersedes_correction_id"]
        if slot in last_by_slot:
            if supersedes != last_by_slot[slot]:
                raise ValueError(
                    f"correction {correction_id} repeats primitive evidence without exact supersession"
                )
        elif supersedes is not None:
            raise ValueError(f"correction {correction_id} names a supersession without a repeat")
        last_by_slot[slot] = correction_id
        seen_ids.add(correction_id)
        previous_hash = correction["record_sha256"]


def _index_source(
    source: list[dict],
    records_by_id: dict[str, dict],
    target_ids: set[str],
) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    if source != sorted(source, key=lambda row: row["mention_id"]):
        raise ValueError("private opportunity source must be sorted by mention ID")
    source_by_mention: dict[str, dict] = {}
    mentions_by_artifact: dict[str, list[dict]] = collections.defaultdict(list)
    for mention in source:
        if mention.get("entity_type") != "site":
            raise ValueError("private opportunity source may contain only site mentions")
        try:
            validate_site_mention(mention)
        except RuntimeError as error:
            raise ValueError(str(error)) from error
        mention_id = mention["mention_id"]
        if mention_id in source_by_mention:
            raise ValueError(f"duplicate private source mention ID {mention_id}")
        artifact_id = mention["artifact_id"]
        if artifact_id not in records_by_id:
            raise ValueError(f"private source mention {mention_id} references unknown artifact")
        if records_by_id[artifact_id]["museum"] != mention["museum"]:
            raise ValueError(f"private source mention {mention_id} museum mismatch")
        unknown = set(mention["target_ids"]) - target_ids
        if unknown:
            raise ValueError(
                f"private source mention {mention_id} references unknown targets: {sorted(unknown)}"
            )
        source_by_mention[mention_id] = mention
        mentions_by_artifact[artifact_id].append(mention)
    return source_by_mention, mentions_by_artifact


def _recompute_record(
    row: dict,
    mentions: list[dict],
    scope_by_target: dict[str, str],
) -> None:
    for mention in mentions:
        try:
            validate_site_mention(mention)
        except RuntimeError as error:
            raise ValueError(str(error)) from error
    counts = collections.Counter(mention["status"] for mention in mentions)
    statuses = set(counts)
    targets = sorted(
        {
            mention["target_ids"][0]
            for mention in mentions
            if mention["status"] == "resolved"
        }
    )
    if len(targets) > counts["resolved"]:
        raise ValueError(
            f"corrected record {row['artifact_id']} has more unique direct targets "
            "than resolved mentions"
        )
    row["site_mention_status_counts"] = dict(sorted(counts.items()))
    row["site_mention_count"] = len(mentions)
    row["extracted_site_text_evidence"] = bool(mentions)
    row["baseline_resolution_state"] = resolution_state(statuses)
    row["baseline_site_target_ids"] = targets
    scope_counts = collections.Counter(scope_by_target[target] for target in targets)
    row["baseline_site_target_scope_counts"] = dict(sorted(scope_counts.items()))
    row["baseline_record_scope"] = partition_scopes(set(scope_counts))
    row["has_any_ambiguity"] = counts["ambiguous"] > 0
    row["has_blocking_ambiguity"] = bool(mentions) and not targets and counts["ambiguous"] > 0
    row["has_any_unmatched_expression"] = counts["unmatched"] > 0


def _assert_source_reproduces_records(
    baseline_rows: list[dict],
    mentions_by_artifact: dict[str, list[dict]],
    scope_by_target: dict[str, str],
) -> None:
    for baseline in baseline_rows:
        derived = json.loads(json.dumps(baseline))
        _recompute_record(
            derived,
            mentions_by_artifact.get(baseline["artifact_id"], []),
            scope_by_target,
        )
        mismatches = [
            field
            for field in DERIVED_RECORD_FIELDS
            if derived[field] != baseline[field]
        ]
        if mismatches:
            raise ValueError(
                f"private opportunity source does not reproduce record "
                f"{baseline['artifact_id']}: {mismatches}"
            )


def _apply_operation(mention: dict, correction: dict) -> None:
    operation = correction["operation"]
    if (
        mention["status"] != operation["from_status"]
        or mention["target_ids"] != operation["from_target_ids"]
    ):
        raise ValueError(f"{correction['correction_id']} mention resolution precondition failed")
    mention["status"] = operation["to_status"]
    mention["target_ids"] = operation["to_target_ids"]
    try:
        validate_site_mention(mention)
    except RuntimeError as error:
        raise ValueError(str(error)) from error


def _links_from_records(rows: list[dict]) -> list[dict]:
    return [
        {"artifact_id": row["artifact_id"], "museum": row["museum"], "target_id": target}
        for row in rows
        for target in row["baseline_site_target_ids"]
    ]


def _queue(
    source: list[dict],
    rows: list[dict],
    links: list[dict],
    scope_by_target: dict[str, str],
) -> tuple[dict, dict, dict]:
    record_counts = collections.Counter(row["museum"] for row in rows)
    evidence_counts = collections.Counter(
        row["museum"] for row in rows if row["extracted_site_text_evidence"]
    )
    return build_opportunity_queue(
        source,
        rows,
        links,
        scope_by_target,
        dict(record_counts),
        dict(evidence_counts),
    )


def _minimum_required(denominator: int) -> int:
    if not denominator:
        return 0
    return max(
        1,
        (
            denominator * MINIMUM_AFFECTED_FRACTION.numerator
            + MINIMUM_AFFECTED_FRACTION.denominator
            - 1
        )
        // MINIMUM_AFFECTED_FRACTION.denominator,
    )


def fixed_frozen_itt_analysis(
    frozen_ledger: dict,
    corrected_rows: list[dict],
    corrected_links: list[dict],
    scope_by_target: dict[str, str],
) -> tuple[dict, dict]:
    """Re-evaluate corrected outcomes over unchanged frozen memberships."""
    record_by_id = {row["artifact_id"]: row for row in corrected_rows}
    record_counts = collections.Counter(row["museum"] for row in corrected_rows)
    evidence_counts = collections.Counter(
        row["museum"] for row in corrected_rows if row["extracted_site_text_evidence"]
    )
    links_by_artifact: dict[str, set[str]] = collections.defaultdict(set)
    targets_by_museum: dict[str, set[str]] = {museum: set() for museum in MUSEUMS}
    for link in corrected_links:
        links_by_artifact[link["artifact_id"]].add(link["target_id"])
        targets_by_museum[link["museum"]].add(link["target_id"])

    per_museum = {}
    private_record_states = {}
    for museum in MUSEUMS:
        frozen_rows = frozen_ledger["intent_to_treat_records_by_museum"][museum]
        states = []
        for frozen in frozen_rows:
            current = record_by_id[frozen["artifact_id"]]
            states.append(
                {
                    "artifact_id": frozen["artifact_id"],
                    "opportunity_bindings": frozen["opportunity_bindings"],
                    "frozen_baseline_record_scope": frozen["baseline_record_scope"],
                    "corrected_record_scope": current["baseline_record_scope"],
                }
            )
        categories = collections.Counter(row["corrected_record_scope"] for row in states)
        maximum = categories["no_link"] + categories["broad_only"]
        per_museum[museum] = {
            "selected_signature_count": sum(
                opportunity["museum"] == museum
                for opportunity in frozen_ledger["opportunities"]
            ),
            "intent_to_treat_record_count": len(states),
            "frozen_intent_to_treat_membership_sha256": canonical_json_sha256(frozen_rows),
            "membership_and_denominator_unchanged": True,
            "corrected_record_scope_counts": dict(sorted(categories.items())),
            "new_record_link_ceiling_records": categories["no_link"],
            "strict_refinement_reassignment_ceiling_records": categories["broad_only"],
            "maximum_credited_affected_records": maximum,
            "maximum_overall_effect": ratio(maximum, record_counts[museum]),
            "maximum_extracted_site_text_conditional_effect": ratio(
                maximum, evidence_counts[museum]
            ),
        }
        private_record_states[museum] = states

    pair_sides = {}
    private_pair_states = {}
    for left, right in PAIRS:
        pair_key = f"{left}__{right}"
        shared = targets_by_museum[left] & targets_by_museum[right]
        public_sides = {}
        private_sides = {}
        for museum in (left, right):
            frozen_members = frozen_ledger["credited_pair_opportunity_memberships"][
                pair_key
            ]["sides"][museum]
            states = []
            counts = collections.Counter()
            for member in frozen_members:
                pair_targets = links_by_artifact[member["artifact_id"]] & shared
                scopes = {scope_by_target[target] for target in pair_targets}
                if not pair_targets:
                    state = "no_corrected_pair_connection"
                elif "specific_candidate" in scopes:
                    state = "corrected_specific_present"
                elif "broad" in scopes:
                    state = "corrected_broad_only"
                else:
                    state = "corrected_unclassified_only"
                counts[state] += 1
                states.append(
                    {
                        **member,
                        "corrected_pair_state": state,
                        "corrected_pair_target_ids": sorted(pair_targets),
                    }
                )
            denominator = len(frozen_members)
            public_sides[museum] = {
                "frozen_credited_effect_opportunity_denominator": denominator,
                "frozen_credited_pair_opportunity_membership_sha256": canonical_json_sha256(
                    frozen_members
                ),
                "membership_and_denominator_unchanged": True,
                "corrected_state_counts": dict(sorted(counts.items())),
                "new_pair_connection_ceiling_records": counts[
                    "no_corrected_pair_connection"
                ],
                "strict_refinement_pair_reassignment_ceiling_records": counts[
                    "corrected_broad_only"
                ],
                "minimum_credited_affected_records_for_continue": _minimum_required(
                    denominator
                ),
            }
            private_sides[museum] = states
        pair_sides[pair_key] = {"sides": public_sides}
        private_pair_states[pair_key] = {"sides": private_sides}

    private = {
        "schema_version": "site-graph-v0-fixed-frozen-itt-sensitivity/1",
        "privacy": "private runtime derivative; contains exact artifact memberships",
        "frozen_private_opportunity_ledger_canonical_sha256": canonical_json_sha256(
            frozen_ledger
        ),
        "frozen_membership_rewritten": False,
        "intent_to_treat_record_states_by_museum": private_record_states,
        "credited_pair_opportunity_member_states": private_pair_states,
    }
    public = {
        "schema_version": "site-graph-v0-fixed-frozen-itt-sensitivity-summary/1",
        "estimand": "corrected outcomes over the unchanged frozen intent-to-treat membership",
        "frozen_membership_rewritten": False,
        "selected_signature_count": frozen_ledger["selected_signature_count"],
        "per_museum": per_museum,
        "pair_side_ceilings": pair_sides,
        "private_exact_analysis_canonical_sha256": canonical_json_sha256(private),
    }
    return public, private


def counterfactual_selection_changes(baseline: dict, corrected: dict) -> tuple[dict, dict]:
    """Describe a reselection without treating it as the frozen ITT."""

    def opportunity_key(row: dict) -> tuple[str, str]:
        return row["museum"], row["normalized_expression_key"]

    baseline_opportunities = {opportunity_key(row): row for row in baseline["opportunities"]}
    corrected_opportunities = {opportunity_key(row): row for row in corrected["opportunities"]}
    baseline_keys = set(baseline_opportunities)
    corrected_keys = set(corrected_opportunities)
    removed_keys = sorted(baseline_keys - corrected_keys)
    added_keys = sorted(corrected_keys - baseline_keys)
    changed_keys = sorted(
        key
        for key in baseline_keys & corrected_keys
        if baseline_opportunities[key] != corrected_opportunities[key]
    )
    signature_changes = {
        "removed": [baseline_opportunities[key] for key in removed_keys],
        "added": [corrected_opportunities[key] for key in added_keys],
        "retained_but_changed": [
            {
                "museum": key[0],
                "normalized_expression_key": key[1],
                "before": baseline_opportunities[key],
                "after": corrected_opportunities[key],
            }
            for key in changed_keys
        ],
    }

    record_changes = {}
    per_museum = {}
    for museum in MUSEUMS:
        before_rows = baseline["intent_to_treat_records_by_museum"][museum]
        after_rows = corrected["intent_to_treat_records_by_museum"][museum]
        before = {row["artifact_id"] for row in before_rows}
        after = {row["artifact_id"] for row in after_rows}
        removed = sorted(before - after)
        added = sorted(after - before)
        record_changes[museum] = {"removed_artifact_ids": removed, "added_artifact_ids": added}
        per_museum[museum] = {
            "frozen_intent_to_treat_record_count": len(before),
            "counterfactual_intent_to_treat_record_count": len(after),
            "denominator_change": len(after) - len(before),
            "removed_record_count": len(removed),
            "added_record_count": len(added),
        }

    exact_pair_changes = {}
    public_pair_changes = {}
    for left, right in PAIRS:
        pair_key = f"{left}__{right}"
        exact_sides = {}
        public_sides = {}
        for museum in (left, right):
            before_rows = baseline["credited_pair_opportunity_memberships"][pair_key][
                "sides"
            ][museum]
            after_rows = corrected["credited_pair_opportunity_memberships"][pair_key][
                "sides"
            ][museum]
            before = {row["artifact_id"] for row in before_rows}
            after = {row["artifact_id"] for row in after_rows}
            removed = sorted(before - after)
            added = sorted(after - before)
            exact_sides[museum] = {
                "removed_artifact_ids": removed,
                "added_artifact_ids": added,
            }
            public_sides[museum] = {
                "frozen_credited_effect_opportunity_denominator": len(before),
                "counterfactual_credited_effect_opportunity_denominator": len(after),
                "denominator_change": len(after) - len(before),
                "removed_record_count": len(removed),
                "added_record_count": len(added),
            }
        exact_pair_changes[pair_key] = {"sides": exact_sides}
        public_pair_changes[pair_key] = {"sides": public_sides}

    private = {
        "schema_version": "site-graph-v0-corrected-source-counterfactual-changes/1",
        "privacy": "private runtime derivative; contains exact expressions and artifact IDs",
        "estimand": "counterfactual reselection from corrected source; not the frozen ITT",
        "signature_changes": signature_changes,
        "intent_to_treat_record_changes_by_museum": record_changes,
        "credited_pair_opportunity_membership_changes": exact_pair_changes,
    }
    public = {
        "schema_version": "site-graph-v0-corrected-source-counterfactual-summary/1",
        "estimand": "counterfactual reselection from corrected source; not the frozen ITT",
        "frozen_membership_rewritten": False,
        "frozen_selected_signature_count": baseline["selected_signature_count"],
        "counterfactual_selected_signature_count": corrected["selected_signature_count"],
        "removed_signature_count": len(removed_keys),
        "added_signature_count": len(added_keys),
        "retained_but_changed_signature_count": len(changed_keys),
        "per_museum": per_museum,
        "pair_side_denominator_changes": public_pair_changes,
        "private_exact_changes_canonical_sha256": canonical_json_sha256(private),
    }
    return public, private


def apply(
    repo_root: Path,
    private_run: Path,
    ledger_path: Path,
    output: Path,
) -> dict:
    repo_root = repo_root.resolve()
    private_run = private_run.resolve()
    ledger_path = ledger_path.resolve()
    output = output.resolve()
    evaluation_root = repo_root / "docs/evaluations/site-graph-v0"
    if output.exists():
        raise ValueError(f"sensitivity output must not already exist: {output}")
    if not output.parent.is_dir():
        raise ValueError(f"sensitivity output parent must exist: {output.parent}")
    verify_private_ledgers(private_run, evaluation_root)
    ledger = read_json(ledger_path)
    validate_schema(
        ledger,
        evaluation_root / "schemas/correction-ledger.schema.json",
        "private correction ledger",
    )
    digest_registry = read_json(evaluation_root / "private-ledger-digests.json")
    expected_ledgers = digest_registry["ledgers"]
    if ledger["private_record_evidence_canonical_sha256"] != expected_ledgers[
        "private_record_evidence"
    ]["canonical_uncompressed_ndjson_sha256"]:
        raise ValueError("correction ledger private record baseline binding mismatch")
    if ledger["private_opportunity_source_canonical_sha256"] != expected_ledgers[
        "private_opportunity_source"
    ]["canonical_uncompressed_ndjson_sha256"]:
        raise ValueError("correction ledger private mention source binding mismatch")

    baseline_path = private_run / "private-record-evidence.ndjson.gz"
    source_path = private_run / "private-opportunity-source.ndjson.gz"
    frozen_ledger_path = private_run / "private-opportunity-ledger.json"
    baseline_rows = read_gzip_jsonl(baseline_path)
    source = read_gzip_jsonl(source_path)
    frozen_ledger = read_json(frozen_ledger_path)
    validate_schema(
        frozen_ledger,
        evaluation_root / "schemas/private-opportunity-ledger.schema.json",
        "private frozen opportunity ledger",
    )
    node_scope = read_json(evaluation_root / "baseline-node-scope.json")
    scope_by_target = {
        row["target_id"]: row["scope_class"] for row in node_scope["nodes"]
    }
    records_by_id: dict[str, dict] = {}
    for row in baseline_rows:
        if row["artifact_id"] in records_by_id:
            raise ValueError(f"duplicate private record {row['artifact_id']}")
        records_by_id[row["artifact_id"]] = row
    source_by_mention, mentions_by_artifact = _index_source(
        source, records_by_id, set(scope_by_target)
    )
    _assert_source_reproduces_records(baseline_rows, mentions_by_artifact, scope_by_target)

    baseline_links = _links_from_records(baseline_rows)
    _, reproduced_frozen_ledger, _ = _queue(
        source, baseline_rows, baseline_links, scope_by_target
    )
    if reproduced_frozen_ledger != frozen_ledger:
        raise ValueError(
            "private mention source and record evidence do not reproduce exact frozen ITT ledger"
        )

    _validate_chain(ledger, records_by_id, source_by_mention, set(scope_by_target))
    corrected_source = json.loads(json.dumps(source))
    corrected_source_by_mention = {
        mention["mention_id"]: mention for mention in corrected_source
    }
    for correction in ledger["corrections"]:
        _apply_operation(
            corrected_source_by_mention[correction["operation"]["mention_id"]],
            correction,
        )
    _, corrected_mentions_by_artifact = _index_source(
        corrected_source, records_by_id, set(scope_by_target)
    )
    corrected_rows = [json.loads(json.dumps(row)) for row in baseline_rows]
    for row in corrected_rows:
        _recompute_record(
            row,
            corrected_mentions_by_artifact.get(row["artifact_id"], []),
            scope_by_target,
        )
    corrected_links = _links_from_records(corrected_rows)
    metrics = build_metrics(corrected_rows, corrected_links, scope_by_target)
    fixed_summary, fixed_private = fixed_frozen_itt_analysis(
        frozen_ledger, corrected_rows, corrected_links, scope_by_target
    )
    metrics["planned_slice_maximum_measurable_effect"] = {
        "source": "fixed-frozen-itt-sensitivity-summary.json",
        "estimand": fixed_summary["estimand"],
        "per_museum": fixed_summary["per_museum"],
        "pair_side_ceilings": fixed_summary["pair_side_ceilings"],
        "interpretation": (
            "Sensitivity-only recomputation from corrected mention primitives over the "
            "unchanged frozen ITT; primary baseline and denominators remain unchanged."
        ),
    }

    counterfactual_summary, counterfactual_ledger, counterfactual_components = _queue(
        corrected_source, corrected_rows, corrected_links, scope_by_target
    )
    corrected_source_timing = (
        "Counterfactual replay uses only corrected source primitives for selection. It is "
        "reported after correction review and makes no claim to predate the frozen ITT."
    )
    counterfactual_summary["selection_algorithm"]["result_blind"] = corrected_source_timing
    counterfactual_ledger["selection_algorithm"]["result_blind"] = corrected_source_timing
    validate_schema(
        counterfactual_ledger,
        evaluation_root / "schemas/private-opportunity-ledger.schema.json",
        "private corrected-source counterfactual opportunity ledger",
    )
    reselection_summary, reselection_private = counterfactual_selection_changes(
        frozen_ledger, counterfactual_ledger
    )

    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    published = False
    try:
        corrected_source_output = temporary / "private-sensitivity-opportunity-source.ndjson.gz"
        record_output = temporary / "private-sensitivity-record-evidence.ndjson.gz"
        link_output = temporary / "private-sensitivity-site-links.ndjson.gz"
        fixed_private_output = temporary / "private-fixed-frozen-itt-analysis.json"
        counterfactual_output = (
            temporary / "private-corrected-source-counterfactual-opportunity-ledger.json"
        )
        reselection_output = (
            temporary / "private-corrected-source-counterfactual-changes.json"
        )
        write_gzip_jsonl(corrected_source_output, corrected_source)
        write_gzip_jsonl(record_output, corrected_rows)
        write_gzip_jsonl(link_output, corrected_links)
        write_json(fixed_private_output, fixed_private)
        write_json(counterfactual_output, counterfactual_ledger)
        write_json(reselection_output, reselection_private)
        write_json(temporary / "sensitivity-metrics.json", metrics)
        write_json(temporary / "fixed-frozen-itt-sensitivity-summary.json", fixed_summary)
        write_json(
            temporary / "corrected-source-counterfactual-opportunity-summary.json",
            counterfactual_summary,
        )
        write_json(
            temporary / "corrected-source-counterfactual-top-components.json",
            counterfactual_components,
        )
        write_json(
            temporary / "corrected-source-counterfactual-reselection-summary.json",
            reselection_summary,
        )
        summary = {
            "schema_version": "site-graph-v0-correction-sensitivity-summary/3",
            "primary_baseline_immutable": True,
            "frozen_intent_to_treat_membership_rewritten": False,
            "correction_count": len(ledger["corrections"]),
            "private_correction_ledger_sha256": sha256(ledger_path),
            "private_correction_ledger_canonical_sha256": canonical_json_sha256(ledger),
            "primary_private_record_evidence": gzip_ledger_digest(baseline_path),
            "primary_private_opportunity_source": gzip_ledger_digest(source_path),
            "sensitivity_private_record_evidence": gzip_ledger_digest(record_output),
            "sensitivity_private_opportunity_source": gzip_ledger_digest(
                corrected_source_output
            ),
            "sensitivity_private_site_links": gzip_ledger_digest(link_output),
            "fixed_frozen_intent_to_treat": fixed_summary,
            "corrected_source_counterfactual_reselection": reselection_summary,
            "private_counterfactual_opportunity_ledger_canonical_sha256": (
                canonical_json_sha256(counterfactual_ledger)
            ),
            "sensitivity_metrics_sha256": sha256(temporary / "sensitivity-metrics.json"),
            "public_data_boundary": (
                "Only this aggregate/hash summary and aggregate metrics are eligible for "
                "release; corrected mention/record rows, exact fixed memberships, and exact "
                "counterfactual additions/removals remain private."
            ),
        }
        write_json(temporary / "sensitivity-summary.json", summary)
        os.replace(temporary, output)
        published = True
        return summary
    finally:
        if not published and temporary.exists():
            shutil.rmtree(temporary)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--private-run", type=Path, required=True)
    parser.add_argument("--correction-ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            apply(args.repo_root, args.private_run, args.correction_ledger, args.output),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
