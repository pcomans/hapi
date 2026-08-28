#!/usr/bin/env python3
"""Apply private primitive corrections into an isolated sensitivity run."""

from __future__ import annotations

import argparse
import collections
import hashlib
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
    write_gzip_jsonl,
    write_json,
)
from metrics_core import partition_scopes
from private_ledgers import verify_private_ledgers
from schema_validation import validate_schema


def record_hash(correction: dict) -> str:
    value = {key: child for key, child in correction.items() if key != "record_sha256"}
    return canonical_json_sha256(value)


def _operation_slots(correction: dict) -> set[str]:
    operation = correction["operation"]
    kind = operation["kind"]
    prefix = correction["artifact_id"] + "\0"
    if kind == "set_site_mention_status_count":
        return {prefix + "mention-status:" + operation["status"]}
    if kind in {"add_direct_target", "remove_direct_target"}:
        return {prefix + "direct-target:" + operation["target_id"]}
    return {
        prefix + "direct-target:" + operation["from_target_id"],
        prefix + "direct-target:" + operation["to_target_id"],
    }


def _validate_chain(ledger: dict, record_ids: set[str], target_ids: set[str]) -> None:
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
        if artifact_id not in record_ids:
            raise ValueError(f"correction {correction_id} references unknown artifact")
        operation = correction["operation"]
        referenced_targets = {
            value
            for key, value in operation.items()
            if key in {"target_id", "from_target_id", "to_target_id"}
        }
        if referenced_targets - target_ids:
            raise ValueError(
                f"correction {correction_id} references unknown targets: "
                f"{sorted(referenced_targets - target_ids)}"
            )
        slots = _operation_slots(correction)
        previous_slot_corrections = {last_by_slot[slot] for slot in slots if slot in last_by_slot}
        supersedes = correction["supersedes_correction_id"]
        if previous_slot_corrections:
            if previous_slot_corrections != {supersedes}:
                raise ValueError(
                    f"correction {correction_id} repeats primitive evidence without exact supersession"
                )
        elif supersedes is not None:
            raise ValueError(f"correction {correction_id} names a supersession without a repeat")
        for slot in slots:
            last_by_slot[slot] = correction_id
        seen_ids.add(correction_id)
        previous_hash = correction["record_sha256"]


def _apply_operation(row: dict, correction: dict) -> None:
    operation = correction["operation"]
    kind = operation["kind"]
    targets = set(row["baseline_site_target_ids"])
    if kind == "add_direct_target":
        target = operation["target_id"]
        if target in targets:
            raise ValueError(f"{correction['correction_id']} adds an existing direct target")
        targets.add(target)
    elif kind == "remove_direct_target":
        target = operation["target_id"]
        if target not in targets:
            raise ValueError(f"{correction['correction_id']} removes a missing direct target")
        targets.remove(target)
    elif kind == "replace_direct_target":
        old, new = operation["from_target_id"], operation["to_target_id"]
        if old == new or old not in targets or new in targets:
            raise ValueError(f"{correction['correction_id']} direct replacement is not applicable")
        targets.remove(old)
        targets.add(new)
    elif kind == "set_site_mention_status_count":
        counts = dict(row["site_mention_status_counts"])
        status = operation["status"]
        if counts.get(status, 0) != operation["from_count"]:
            raise ValueError(f"{correction['correction_id']} mention count precondition failed")
        if operation["to_count"]:
            counts[status] = operation["to_count"]
        else:
            counts.pop(status, None)
        row["site_mention_status_counts"] = dict(sorted(counts.items()))
    else:  # schema validation makes this unreachable
        raise ValueError(f"unsupported correction operation {kind}")
    row["baseline_site_target_ids"] = sorted(targets)


def _recompute_record(row: dict, scope_by_target: dict[str, str]) -> None:
    counts = row["site_mention_status_counts"]
    if any(type(value) is not int or value < 0 for value in counts.values()):
        raise ValueError(f"invalid corrected mention counts for {row['artifact_id']}")
    statuses = {status for status, count in counts.items() if count}
    targets = row["baseline_site_target_ids"]
    if targets and counts.get("resolved", 0) == 0:
        raise ValueError(f"corrected targets lack resolved evidence for {row['artifact_id']}")
    if counts.get("resolved", 0) and not targets:
        raise ValueError(f"corrected resolved evidence lacks a direct target for {row['artifact_id']}")
    row["site_mention_count"] = sum(counts.values())
    row["extracted_site_text_evidence"] = bool(statuses)
    row["baseline_resolution_state"] = resolution_state(statuses)
    scope_counts = collections.Counter(scope_by_target[target] for target in targets)
    row["baseline_site_target_scope_counts"] = dict(sorted(scope_counts.items()))
    row["baseline_record_scope"] = partition_scopes(set(scope_counts))
    row["has_any_ambiguity"] = counts.get("ambiguous", 0) > 0
    row["has_blocking_ambiguity"] = bool(statuses) and not targets and row["has_any_ambiguity"]
    row["has_any_unmatched_expression"] = counts.get("unmatched", 0) > 0


def apply(
    repo_root: Path,
    private_run: Path,
    ledger_path: Path,
    output: Path,
) -> dict:
    repo_root = repo_root.resolve()
    private_run = private_run.resolve()
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
    expected_record_hash = digest_registry["ledgers"]["private_record_evidence"][
        "canonical_uncompressed_ndjson_sha256"
    ]
    if ledger["private_record_evidence_canonical_sha256"] != expected_record_hash:
        raise ValueError("correction ledger baseline binding mismatch")

    baseline_path = private_run / "private-record-evidence.ndjson.gz"
    baseline_rows = read_gzip_jsonl(baseline_path)
    node_scope = read_json(evaluation_root / "baseline-node-scope.json")
    scope_by_target = {
        row["target_id"]: row["scope_class"] for row in node_scope["nodes"]
    }
    rows_by_id = {row["artifact_id"]: json.loads(json.dumps(row)) for row in baseline_rows}
    _validate_chain(ledger, set(rows_by_id), set(scope_by_target))
    for correction in ledger["corrections"]:
        _apply_operation(rows_by_id[correction["artifact_id"]], correction)
    corrected_rows = [rows_by_id[row["artifact_id"]] for row in baseline_rows]
    for row in corrected_rows:
        _recompute_record(row, scope_by_target)

    links = [
        {"artifact_id": row["artifact_id"], "museum": row["museum"], "target_id": target}
        for row in corrected_rows
        for target in row["baseline_site_target_ids"]
    ]
    source = read_gzip_jsonl(private_run / "private-opportunity-source.ndjson.gz")
    record_counts = collections.Counter(row["museum"] for row in corrected_rows)
    evidence_counts = collections.Counter(
        row["museum"] for row in corrected_rows if row["extracted_site_text_evidence"]
    )
    opportunity_summary, private_opportunity, top_components = build_opportunity_queue(
        source,
        corrected_rows,
        links,
        scope_by_target,
        dict(record_counts),
        dict(evidence_counts),
    )
    metrics = build_metrics(corrected_rows, links, scope_by_target)
    metrics["planned_slice_maximum_measurable_effect"] = {
        "source": "sensitivity opportunity aggregate",
        "per_museum": opportunity_summary["per_museum"],
        "pair_side_ceilings": opportunity_summary["pair_side_ceilings"],
        "interpretation": "Sensitivity-only recomputation from corrected primitives; primary baseline unchanged.",
    }

    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    published = False
    try:
        record_output = temporary / "private-sensitivity-record-evidence.ndjson.gz"
        opportunity_output = temporary / "private-sensitivity-opportunity-ledger.json"
        write_gzip_jsonl(record_output, corrected_rows)
        write_json(opportunity_output, private_opportunity)
        write_json(temporary / "sensitivity-metrics.json", metrics)
        write_json(temporary / "sensitivity-opportunity-summary.json", opportunity_summary)
        write_json(temporary / "sensitivity-top-unmatched-components.json", top_components)
        summary = {
            "schema_version": "site-graph-v0-correction-sensitivity-summary/2",
            "primary_baseline_immutable": True,
            "correction_count": len(ledger["corrections"]),
            "private_correction_ledger_sha256": sha256(ledger_path),
            "private_correction_ledger_canonical_sha256": canonical_json_sha256(ledger),
            "primary_private_record_evidence": gzip_ledger_digest(baseline_path),
            "sensitivity_private_record_evidence": gzip_ledger_digest(record_output),
            "sensitivity_private_opportunity_ledger_canonical_sha256": canonical_json_sha256(
                private_opportunity
            ),
            "sensitivity_metrics_sha256": sha256(temporary / "sensitivity-metrics.json"),
            "sensitivity_opportunity_summary_sha256": sha256(
                temporary / "sensitivity-opportunity-summary.json"
            ),
            "public_data_boundary": (
                "Only this aggregate/hash summary and the aggregate metrics are eligible for "
                "release; private corrected rows and memberships remain private."
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
