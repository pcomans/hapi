#!/usr/bin/env python3
"""Authentication and public-boundary checks for private evaluation ledgers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_baseline import (
    canonical_json_sha256,
    canonical_list_sha256,
    gzip_ledger_digest,
    read_json,
    sha256,
)
from contract_constants import MUSEUMS, PAIRS


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
        "field_path",
        "field_paths",
        "mention_text",
        "mention_texts",
        "mention_text_examples",
        "normalized_expression_key",
    }
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
    if ledger.get("schema_version") != "site-graph-v0-private-opportunity-ledger/2":
        raise RuntimeError("private opportunity ledger schema mismatch")
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

    public_opportunities = {
        row["opportunity_id"]: row for row in summary["opportunities"]
    }
    if len(public_opportunities) != summary["selected_signature_count"]:
        raise RuntimeError("public opportunity IDs are not unique")
    private_opportunities = {row["opportunity_id"]: row for row in ledger["opportunities"]}
    if set(private_opportunities) != set(public_opportunities):
        raise RuntimeError("public/private opportunity ID set mismatch")
    for opportunity_id in sorted(private_opportunities):
        private_row = private_opportunities[opportunity_id]
        artifact_ids = private_row["artifact_ids"]
        if artifact_ids != sorted(set(artifact_ids)):
            raise RuntimeError(f"private opportunity {opportunity_id} artifacts not sorted/unique")
        if private_row["artifact_count"] != len(artifact_ids):
            raise RuntimeError(f"private opportunity {opportunity_id} artifact count mismatch")
        if private_row["artifact_expansion_sha256"] != canonical_list_sha256(artifact_ids):
            raise RuntimeError(f"private opportunity {opportunity_id} artifact hash mismatch")
        public_projection = {
            key: value
            for key, value in private_row.items()
            if key not in {
                "artifact_ids",
                "field_paths",
                "mention_text_examples",
                "normalized_expression_key",
            }
        }
        if public_projection != public_opportunities[opportunity_id]:
            raise RuntimeError(f"public opportunity {opportunity_id} aggregate mismatch")

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
