#!/usr/bin/env python3
"""Authentication and public-boundary checks for private evaluation ledgers."""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path

from build_baseline import (
    canonical_json_sha256,
    canonical_list_sha256,
    gzip_ledger_digest,
    read_json,
    sha256,
)
from contract_constants import (
    MUSEUMS,
    OPPORTUNITY_MUSEUM_PROTECTION,
    OPPORTUNITY_TOTAL_SIGNATURES,
    PAIRS,
)
from schema_validation import validate_schema


PRIVATE_LEDGER_FILES = frozenset(
    {
        "private-record-evidence.ndjson.gz",
        "private-opportunity-source.ndjson.gz",
        "private-opportunity-ledger.json",
    }
)
PUBLIC_AGGREGATE_FILES = frozenset(
    {
        "baseline-metrics.json",
        "baseline-node-scope.json",
        "planned-opportunity-summary.json",
        "private-ledger-digests.json",
        "top-unmatched-components.json",
    }
)
FORBIDDEN_PUBLIC_FILES = frozenset(
    {
        "frozen-record-evidence.ndjson.gz",
        "frozen-opportunity-source.ndjson.gz",
        "planned-opportunity-queue.json",
        *PRIVATE_LEDGER_FILES,
    }
)
FORBIDDEN_PUBLIC_KEYS = frozenset(
    {
        "artifact_id",
        "artifact_ids",
        "artifact_memberships",
        "field_path",
        "field_paths",
        "mention_id",
        "mention_ids",
        "mention_text",
        "mention_text_sha256",
        "mention_texts",
        "mention_text_examples",
        "mentions",
        "normalized_keys",
        "normalized_expression_key",
        "opportunity_binding_sha256",
        "opportunity_bindings",
        "target_ids",
    }
)

PUBLIC_OPPORTUNITY_FIELDS = (
    "opportunity_id",
    "selection_rank",
    "selection_reason",
    "museum",
    "unresolved_status_counts",
    "mention_count",
    "artifact_count",
    "artifact_expansion_sha256",
    "intent_to_treat",
)
PRIVATE_SOURCE_FIELDS = frozenset(
    {
        "artifact_id",
        "entity_type",
        "field_path",
        "mention_id",
        "mention_text",
        "museum",
        "normalized_keys",
        "status",
        "target_ids",
    }
)
RECORD_SCOPES = frozenset(
    {"no_link", "broad_only", "specific_candidate_present", "unclassified_only"}
)


def _walk_keys(value: object, location: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_location = f"{location}.{key}"
            if key in FORBIDDEN_PUBLIC_KEYS:
                errors.append(child_location)
            errors.extend(_walk_keys(child, child_location))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_walk_keys(child, f"{location}[{index}]"))
    return errors


def verify_public_boundary(public_root: Path) -> dict:
    present_forbidden = sorted(
        name for name in FORBIDDEN_PUBLIC_FILES if (public_root / name).exists()
    )
    if present_forbidden:
        raise RuntimeError(f"private/bulk files present in public release: {present_forbidden}")
    missing = sorted(name for name in PUBLIC_AGGREGATE_FILES if not (public_root / name).is_file())
    if missing:
        raise RuntimeError(f"public aggregate files missing: {missing}")
    leaked_locations: dict[str, list[str]] = {}
    for name in sorted(PUBLIC_AGGREGATE_FILES):
        value = read_json(public_root / name)
        locations = _walk_keys(value)
        if locations:
            leaked_locations[name] = locations
    if leaked_locations:
        raise RuntimeError(f"private record/source keys present in public aggregates: {leaked_locations}")
    return {
        "public_aggregate_files": sorted(PUBLIC_AGGREGATE_FILES),
        "forbidden_public_files_absent": sorted(FORBIDDEN_PUBLIC_FILES),
    }


def _verify_digest(label: str, actual: dict, expected: dict) -> None:
    if actual != expected:
        raise RuntimeError(f"{label} digest mismatch: expected {expected}, got {actual}")


def _read_gzip_jsonl(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _validate_source_mention(row: dict, index: int) -> None:
    if set(row) != PRIVATE_SOURCE_FIELDS:
        raise RuntimeError(
            f"private opportunity source row {index} field inventory mismatch"
        )
    for key in ("artifact_id", "field_path", "mention_id", "mention_text"):
        if not isinstance(row[key], str) or not row[key]:
            raise RuntimeError(
                f"private opportunity source row {index} has invalid {key}"
            )
    if row["entity_type"] != "site":
        raise RuntimeError(
            f"private opportunity source row {index} is not a site mention"
        )
    if row["museum"] not in MUSEUMS:
        raise RuntimeError(
            f"private opportunity source row {index} has invalid museum"
        )
    normalized_keys = row["normalized_keys"]
    if not isinstance(normalized_keys, list) or not all(
        isinstance(value, str) for value in normalized_keys
    ):
        raise RuntimeError(
            f"private opportunity source row {index} has invalid normalized keys"
        )
    target_ids = row["target_ids"]
    if (
        not isinstance(target_ids, list)
        or not all(isinstance(value, str) and value for value in target_ids)
        or target_ids != sorted(set(target_ids))
    ):
        raise RuntimeError(
            f"private opportunity source row {index} target IDs are not sorted/unique"
        )
    status = row["status"]
    if status == "resolved" and len(target_ids) != 1:
        raise RuntimeError(
            f"resolved source mention {row['mention_id']} must have one target"
        )
    if status == "unmatched" and target_ids:
        raise RuntimeError(
            f"unmatched source mention {row['mention_id']} must have no targets"
        )
    if status == "ambiguous" and len(target_ids) < 2:
        raise RuntimeError(
            f"ambiguous source mention {row['mention_id']} must have two or more targets"
        )
    if status not in {"resolved", "unmatched", "ambiguous"}:
        raise RuntimeError(
            f"private opportunity source row {index} has invalid status {status!r}"
        )


def _mention_binding(mention: dict) -> dict:
    return {
        "mention_id": mention["mention_id"],
        "field_path": mention["field_path"],
        "status": mention["status"],
        "target_ids": mention["target_ids"],
        "normalized_keys": mention["normalized_keys"],
        "mention_text_sha256": hashlib.sha256(
            mention["mention_text"].encode("utf-8")
        ).hexdigest(),
    }


def _selected_source_groups(source_rows: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str], dict] = {}
    mention_ids: set[str] = set()
    source_order: list[str] = []
    for index, mention in enumerate(source_rows):
        _validate_source_mention(mention, index)
        mention_id = mention["mention_id"]
        if mention_id in mention_ids:
            raise RuntimeError(f"duplicate private source mention ID {mention_id}")
        mention_ids.add(mention_id)
        source_order.append(mention_id)
        if mention["status"] not in {"unmatched", "ambiguous"}:
            continue
        normalized_key = "\u241f".join(mention["normalized_keys"])
        if not normalized_key:
            normalized_key = " ".join(mention["mention_text"].casefold().split())
        key = (mention["museum"], normalized_key)
        group = groups.setdefault(
            key,
            {
                "museum": mention["museum"],
                "normalized_expression_key": normalized_key,
                "artifact_ids": set(),
                "mention_ids": set(),
                "statuses": collections.Counter(),
                "mention_texts": set(),
                "field_paths": set(),
                "mentions_by_artifact": collections.defaultdict(list),
            },
        )
        group["artifact_ids"].add(mention["artifact_id"])
        group["mention_ids"].add(mention_id)
        group["statuses"][mention["status"]] += 1
        group["mention_texts"].add(mention["mention_text"])
        group["field_paths"].add(mention["field_path"])
        group["mentions_by_artifact"][mention["artifact_id"]].append(mention)

    if source_order != sorted(source_order):
        raise RuntimeError("private opportunity source is not sorted by mention ID")

    ranked = sorted(
        groups.values(),
        key=lambda row: (
            -len(row["artifact_ids"]),
            row["museum"],
            row["normalized_expression_key"],
        ),
    )
    selected_keys: set[tuple[str, str]] = set()
    selection_reason: dict[tuple[str, str], str] = {}
    for museum in MUSEUMS:
        for row in [item for item in ranked if item["museum"] == museum][
            :OPPORTUNITY_MUSEUM_PROTECTION
        ]:
            key = (museum, row["normalized_expression_key"])
            selected_keys.add(key)
            selection_reason[key] = "museum_protection_top_10"
    for row in ranked:
        if len(selected_keys) >= OPPORTUNITY_TOTAL_SIGNATURES:
            break
        key = (row["museum"], row["normalized_expression_key"])
        if key not in selected_keys:
            selected_keys.add(key)
            selection_reason[key] = "global_frequency_fill_to_50"
    selected = [
        row
        for row in ranked
        if (row["museum"], row["normalized_expression_key"]) in selected_keys
    ]
    selected.sort(
        key=lambda row: (
            -len(row["artifact_ids"]),
            row["museum"],
            row["normalized_expression_key"],
        )
    )
    if len(selected) != OPPORTUNITY_TOTAL_SIGNATURES:
        raise RuntimeError(
            "private opportunity source cannot realize the frozen 50-signature queue"
        )
    for row in selected:
        row["selection_reason"] = selection_reason[
            (row["museum"], row["normalized_expression_key"])
        ]
    return selected


def _expected_membership(
    opportunity_id: str, group: dict, artifact_id: str
) -> dict:
    mentions = sorted(
        (_mention_binding(row) for row in group["mentions_by_artifact"][artifact_id]),
        key=lambda row: row["mention_id"],
    )
    payload = {
        "opportunity_id": opportunity_id,
        "museum": group["museum"],
        "normalized_expression_key": group["normalized_expression_key"],
        "artifact_id": artifact_id,
        "mentions": mentions,
    }
    return {
        "artifact_id": artifact_id,
        "opportunity_binding_sha256": canonical_json_sha256(payload),
        "mentions": mentions,
    }


def _verify_exact_opportunities(ledger: dict, source_rows: list[dict]) -> dict[str, dict]:
    selected = _selected_source_groups(source_rows)
    if ledger["selected_signature_count"] != OPPORTUNITY_TOTAL_SIGNATURES:
        raise RuntimeError("private selected-signature count mismatch")
    if len(ledger["opportunities"]) != OPPORTUNITY_TOTAL_SIGNATURES:
        raise RuntimeError("private opportunity row count mismatch")

    artifact_bindings: dict[str, dict] = collections.defaultdict(
        lambda: {"museum": None, "bindings": []}
    )
    for rank, (actual, group) in enumerate(zip(ledger["opportunities"], selected), 1):
        opportunity_id = f"opp-{rank:04d}"
        artifact_ids = sorted(group["artifact_ids"])
        expected_scalars = {
            "opportunity_id": opportunity_id,
            "selection_rank": rank,
            "selection_reason": group["selection_reason"],
            "museum": group["museum"],
            "unresolved_status_counts": dict(sorted(group["statuses"].items())),
            "mention_count": len(group["mention_ids"]),
            "artifact_count": len(artifact_ids),
            "artifact_expansion_sha256": canonical_list_sha256(artifact_ids),
            "intent_to_treat": True,
            "normalized_expression_key": group["normalized_expression_key"],
            "artifact_ids": artifact_ids,
            "mention_text_examples": sorted(group["mention_texts"])[:5],
            "field_paths": sorted(group["field_paths"]),
        }
        for key, expected in expected_scalars.items():
            if actual[key] != expected:
                raise RuntimeError(
                    f"private opportunity {opportunity_id} {key} is not source-realizable"
                )
        expected_memberships = [
            _expected_membership(opportunity_id, group, artifact_id)
            for artifact_id in artifact_ids
        ]
        if actual["artifact_memberships"] != expected_memberships:
            raise RuntimeError(
                f"private opportunity {opportunity_id} exact mention binding mismatch"
            )
        for membership in expected_memberships:
            artifact_id = membership["artifact_id"]
            entry = artifact_bindings[artifact_id]
            if entry["museum"] not in {None, group["museum"]}:
                raise RuntimeError(f"artifact {artifact_id} appears under multiple museums")
            entry["museum"] = group["museum"]
            entry["bindings"].append(
                {
                    "opportunity_id": opportunity_id,
                    "opportunity_binding_sha256": membership[
                        "opportunity_binding_sha256"
                    ],
                }
            )
    for entry in artifact_bindings.values():
        entry["bindings"].sort(key=lambda row: row["opportunity_id"])
    return artifact_bindings


def _record_evidence(private_run: Path, scope_by_target: dict[str, str]) -> dict[str, dict]:
    records: dict[str, dict] = {}
    for index, row in enumerate(
        _read_gzip_jsonl(private_run / "private-record-evidence.ndjson.gz")
    ):
        required = {"artifact_id", "museum", "baseline_record_scope", "baseline_site_target_ids"}
        if not required <= set(row):
            raise RuntimeError(f"private record evidence row {index} lacks required fields")
        artifact_id = row["artifact_id"]
        if not isinstance(artifact_id, str) or not artifact_id:
            raise RuntimeError(f"private record evidence row {index} has invalid artifact ID")
        if artifact_id in records:
            raise RuntimeError(f"duplicate private record evidence artifact {artifact_id}")
        if row["museum"] not in MUSEUMS:
            raise RuntimeError(f"private record evidence row {index} has invalid museum")
        targets = row["baseline_site_target_ids"]
        if targets != sorted(set(targets)):
            raise RuntimeError(f"private record {artifact_id} target IDs are not sorted/unique")
        try:
            scopes = {scope_by_target[target] for target in targets}
        except KeyError as error:
            raise RuntimeError(
                f"private record {artifact_id} references unknown baseline target {error.args[0]}"
            ) from error
        if not targets:
            expected_scope = "no_link"
        elif "specific_candidate" in scopes:
            expected_scope = "specific_candidate_present"
        elif "broad" in scopes:
            expected_scope = "broad_only"
        else:
            expected_scope = "unclassified_only"
        if row["baseline_record_scope"] not in RECORD_SCOPES:
            raise RuntimeError(f"private record {artifact_id} has invalid baseline scope")
        if row["baseline_record_scope"] != expected_scope:
            raise RuntimeError(f"private record {artifact_id} baseline scope mismatch")
        records[artifact_id] = row
    return records


def _expected_itt_records(
    artifact_bindings: dict[str, dict], records: dict[str, dict]
) -> dict[str, list[dict]]:
    expected: dict[str, list[dict]] = {museum: [] for museum in MUSEUMS}
    for artifact_id in sorted(artifact_bindings):
        if artifact_id not in records:
            raise RuntimeError(f"ITT artifact {artifact_id} is absent from record evidence")
        entry = artifact_bindings[artifact_id]
        record = records[artifact_id]
        if record["museum"] != entry["museum"]:
            raise RuntimeError(f"ITT artifact {artifact_id} museum mismatch")
        expected[entry["museum"]].append(
            {
                "artifact_id": artifact_id,
                "opportunity_bindings": entry["bindings"],
                "baseline_record_scope": record["baseline_record_scope"],
            }
        )
    return expected


def _expected_pair_memberships(
    artifact_bindings: dict[str, dict],
    records: dict[str, dict],
    scope_by_target: dict[str, str],
) -> dict[str, dict]:
    targets_by_museum = {
        museum: {
            target
            for record in records.values()
            if record["museum"] == museum
            for target in record["baseline_site_target_ids"]
        }
        for museum in MUSEUMS
    }
    artifacts_by_museum = {
        museum: sorted(
            artifact_id
            for artifact_id, entry in artifact_bindings.items()
            if entry["museum"] == museum
        )
        for museum in MUSEUMS
    }
    expected = {}
    for left, right in PAIRS:
        pair_key = f"{left}__{right}"
        shared = targets_by_museum[left] & targets_by_museum[right]
        sides = {}
        for museum in (left, right):
            rows = []
            for artifact_id in artifacts_by_museum[museum]:
                pair_targets = set(records[artifact_id]["baseline_site_target_ids"]) & shared
                scopes = {scope_by_target[target] for target in pair_targets}
                if not pair_targets:
                    category = "no_baseline_pair_connection"
                elif "specific_candidate" in scopes:
                    continue
                elif "broad" in scopes:
                    category = "broad_only_pair_connection"
                else:
                    continue
                rows.append(
                    {
                        "artifact_id": artifact_id,
                        "category": category,
                        "opportunity_bindings": artifact_bindings[artifact_id]["bindings"],
                    }
                )
            sides[museum] = rows
        expected[pair_key] = {"sides": sides}
    return expected


def _verify_archive_attestation(private_run: Path, digest_registry: dict) -> dict:
    path = private_run / "corpus-archive-attestation.json"
    if not path.is_file():
        raise RuntimeError("runtime corpus archive attestation is missing")
    attestation = read_json(path)
    external = digest_registry.get("external_private_input")
    if not isinstance(external, dict):
        raise RuntimeError("public private-ledger digest lacks external input binding")
    expected_status = {
        "snapshot_acquisition_integrity": external.get(
            "snapshot_acquisition_integrity"
        ),
        "upstream_production_lineage": external.get("upstream_production_lineage"),
    }
    if expected_status != {
        "snapshot_acquisition_integrity": "PASS",
        "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
    }:
        raise RuntimeError("public private-ledger digest has invalid archive status")
    if attestation.get("schema_version") != "site-graph-v0-corpus-archive-attestation/1":
        raise RuntimeError("runtime corpus archive attestation schema mismatch")
    if attestation.get("status") != expected_status:
        raise RuntimeError("runtime corpus archive attestation status mismatch")
    archive = attestation.get("archive")
    if not isinstance(archive, dict) or archive.get("sha256") != external.get(
        "archive_sha256"
    ):
        raise RuntimeError("runtime corpus archive attestation digest mismatch")
    lineage = attestation.get("production_lineage")
    if (
        not isinstance(lineage, dict)
        or lineage.get("status") != external["upstream_production_lineage"]
        or lineage.get("effect") != external.get("unavailable_lineage_effect")
        or external.get("historical_export_reproducibility")
        != "UNAVAILABLE_DISCLOSED"
    ):
        raise RuntimeError("runtime corpus archive lineage disclosure mismatch")
    return {
        "archive_sha256": archive["sha256"],
        **expected_status,
    }


def verify_private_ledgers(private_run: Path, public_root: Path) -> dict:
    """Authenticate regenerated private ledgers against committed aggregate digests."""
    private_run = private_run.resolve()
    public_root = public_root.resolve()
    verify_public_boundary(public_root)
    missing = sorted(name for name in PRIVATE_LEDGER_FILES if not (private_run / name).is_file())
    if missing:
        raise RuntimeError(f"private runtime ledgers missing: {missing}")

    digest_registry = read_json(public_root / "private-ledger-digests.json")
    summary = read_json(public_root / "planned-opportunity-summary.json")
    if digest_registry.get("schema_version") != "site-graph-v0-private-ledger-digests/1":
        raise RuntimeError("private ledger digest registry schema mismatch")
    if summary.get("schema_version") != "site-graph-v0-opportunity-summary/2":
        raise RuntimeError("opportunity summary schema mismatch")
    archive_authentication = _verify_archive_attestation(private_run, digest_registry)

    expected_ledgers = digest_registry["ledgers"]
    _verify_digest(
        "private record evidence",
        gzip_ledger_digest(private_run / "private-record-evidence.ndjson.gz"),
        expected_ledgers["private_record_evidence"],
    )
    _verify_digest(
        "private opportunity source",
        gzip_ledger_digest(private_run / "private-opportunity-source.ndjson.gz"),
        expected_ledgers["private_opportunity_source"],
    )

    ledger_path = private_run / "private-opportunity-ledger.json"
    ledger = read_json(ledger_path)
    validate_schema(
        ledger,
        Path(__file__).resolve().parent.parent
        / "schemas/private-opportunity-ledger.schema.json",
        "private opportunity ledger",
    )
    ledger_digest = {
        "bytes": ledger_path.stat().st_size,
        "transport_json_sha256": sha256(ledger_path),
        "canonical_json_sha256": canonical_json_sha256(ledger),
        "selected_signature_count": ledger["selected_signature_count"],
        "intent_to_treat_record_counts_by_museum": {
            museum: len(rows)
            for museum, rows in ledger["intent_to_treat_records_by_museum"].items()
        },
    }
    _verify_digest(
        "private opportunity membership",
        ledger_digest,
        expected_ledgers["private_opportunity_membership"],
    )
    if summary["private_ledger_authentication"] != {
        "canonical_json_sha256": ledger_digest["canonical_json_sha256"],
        "transport_json_sha256": ledger_digest["transport_json_sha256"],
    }:
        raise RuntimeError("public opportunity summary private-ledger hash mismatch")

    source_rows = _read_gzip_jsonl(
        private_run / "private-opportunity-source.ndjson.gz"
    )
    artifact_bindings = _verify_exact_opportunities(ledger, source_rows)

    if len(summary["opportunities"]) != summary["selected_signature_count"]:
        raise RuntimeError("public opportunity row count mismatch")
    public_opportunity_ids = [
        row["opportunity_id"] for row in summary["opportunities"]
    ]
    if len(public_opportunity_ids) != len(set(public_opportunity_ids)):
        raise RuntimeError("public opportunity IDs are not unique")
    public_projection = [
        {key: row[key] for key in PUBLIC_OPPORTUNITY_FIELDS}
        for row in ledger["opportunities"]
    ]
    if public_projection != summary["opportunities"]:
        raise RuntimeError("public/private opportunity aggregate projection mismatch")

    node_scope = read_json(public_root / "baseline-node-scope.json")
    scope_by_target: dict[str, str] = {}
    for row in node_scope.get("nodes", []):
        target_id = row.get("target_id")
        scope = row.get("scope_class")
        if not isinstance(target_id, str) or scope not in {
            "broad",
            "specific_candidate",
            "unclassified",
        }:
            raise RuntimeError("public baseline node scope row is invalid")
        if target_id in scope_by_target:
            raise RuntimeError(f"duplicate public baseline target {target_id}")
        scope_by_target[target_id] = scope
    records = _record_evidence(private_run, scope_by_target)
    expected_itt = _expected_itt_records(artifact_bindings, records)
    if ledger["intent_to_treat_records_by_museum"] != expected_itt:
        raise RuntimeError(
            "private intent-to-treat records do not carry the exact source bindings"
        )

    expected_private_pairs = _expected_pair_memberships(
        artifact_bindings, records, scope_by_target
    )
    if ledger["credited_pair_opportunity_memberships"] != expected_private_pairs:
        raise RuntimeError(
            "private pair-side categories or exact opportunity bindings mismatch"
        )

    expected_pairs = {f"{left}__{right}" for left, right in PAIRS}
    private_pairs = ledger["credited_pair_opportunity_memberships"]
    if set(private_pairs) != expected_pairs:
        raise RuntimeError("private pair membership key mismatch")
    for pair_key in sorted(expected_pairs):
        public_sides = summary["pair_side_ceilings"][pair_key]["sides"]
        digest_sides = digest_registry["pair_side_membership"][pair_key]
        expected_museums = pair_key.split("__")
        private_sides = private_pairs[pair_key]["sides"]
        if set(private_sides) != set(expected_museums):
            raise RuntimeError(f"{pair_key} museum-side membership mismatch")
        for museum in expected_museums:
            rows = private_sides[museum]
            if rows != sorted(rows, key=lambda row: row["artifact_id"]):
                raise RuntimeError(f"{pair_key}/{museum} membership is not sorted")
            artifact_ids = [row["artifact_id"] for row in rows]
            if len(artifact_ids) != len(set(artifact_ids)):
                raise RuntimeError(f"{pair_key}/{museum} membership has duplicate artifacts")
            categories: dict[str, int] = {}
            for row in rows:
                category = row["category"]
                if category not in {
                    "no_baseline_pair_connection",
                    "broad_only_pair_connection",
                }:
                    raise RuntimeError(f"{pair_key}/{museum} invalid category {category}")
                categories[category] = categories.get(category, 0) + 1
            actual = {
                "record_count": len(rows),
                "canonical_json_sha256": canonical_json_sha256(rows),
                "category_counts": dict(sorted(categories.items())),
            }
            _verify_digest(f"{pair_key}/{museum} membership", actual, digest_sides[museum])
            public_side = public_sides[museum]
            if public_side["credited_effect_opportunity_denominator"] != len(rows):
                raise RuntimeError(f"{pair_key}/{museum} denominator mismatch")
            if public_side["credited_pair_opportunity_membership_sha256"] != actual[
                "canonical_json_sha256"
            ]:
                raise RuntimeError(f"{pair_key}/{museum} public membership hash mismatch")
            if public_side["new_pair_connection_ceiling_records"] != categories.get(
                "no_baseline_pair_connection", 0
            ):
                raise RuntimeError(f"{pair_key}/{museum} new-link ceiling mismatch")
            if public_side["strict_refinement_pair_reassignment_ceiling_records"] != (
                categories.get("broad_only_pair_connection", 0)
            ):
                raise RuntimeError(f"{pair_key}/{museum} refinement ceiling mismatch")

    return {
        "archive_authentication": archive_authentication,
        "private_record_count": expected_ledgers["private_record_evidence"]["row_count"],
        "private_opportunity_source_count": expected_ledgers[
            "private_opportunity_source"
        ]["row_count"],
        "selected_signature_count": ledger["selected_signature_count"],
        "pair_side_membership_count": sum(
            len(rows)
            for pair in private_pairs.values()
            for rows in pair["sides"].values()
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-run", type=Path)
    parser.add_argument("--public-root", type=Path, required=True)
    parser.add_argument("--public-only", action="store_true")
    args = parser.parse_args()
    if args.public_only:
        result = verify_public_boundary(args.public_root)
    else:
        if args.private_run is None:
            parser.error("--private-run is required unless --public-only is used")
        result = verify_private_ledgers(args.private_run, args.public_root)
    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
