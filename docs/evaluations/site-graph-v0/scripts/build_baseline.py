#!/usr/bin/env python3
"""Build the site-graph-v0 baseline from the frozen linkability adapter outputs.

This module does not extract, normalize, or resolve museum text.  It consumes the
outputs of the archived adapter pinned in ``input-snapshot.json`` and derives only the
pre-registered record, connectivity, scope, and concentration accounting.
"""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import io
import json
from pathlib import Path
from typing import Iterable

from contract_constants import (
    MINIMUM_AFFECTED_FRACTION,
    MUSEUMS,
    OPPORTUNITY_MUSEUM_PROTECTION,
    OPPORTUNITY_TOTAL_SIGNATURES,
    PAIRS,
)
from corpus_archive import validate_archive_attestation
from metrics_core import concentration, partition_scopes, ratio

ATTEMPT_STATUSES = {"resolved", "ambiguous", "unmatched"}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_gzip_jsonl(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def write_json(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_gzip_jsonl(path: Path, rows: Iterable[dict]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", compresslevel=9, mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding="utf-8") as handle:
                for row in rows:
                    handle.write(
                        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                        + "\n"
                    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def uncompressed_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with gzip.open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_json_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def validate_site_mention(mention: dict) -> None:
    """Reject resolution states that could not have produced direct links."""
    status = mention["status"]
    if status not in ATTEMPT_STATUSES:
        raise RuntimeError(
            f"site mention {mention['mention_id']} has unsupported status {status!r}"
        )
    target_ids = mention.get("target_ids")
    if not isinstance(target_ids, list) or target_ids != sorted(set(target_ids)):
        raise RuntimeError(
            f"site mention {mention['mention_id']} target IDs must be a sorted unique list"
        )
    if status == "resolved" and len(target_ids) != 1:
        raise RuntimeError(
            f"resolved site mention {mention['mention_id']} must have exactly one target"
        )
    if status == "unmatched" and target_ids:
        raise RuntimeError(
            f"unmatched site mention {mention['mention_id']} must have no targets"
        )
    if status == "ambiguous" and len(target_ids) < 2:
        raise RuntimeError(
            f"ambiguous site mention {mention['mention_id']} must have at least two targets"
        )


def mention_binding(mention: dict) -> dict:
    """Return the complete resolution primitive used in opportunity membership."""
    validate_site_mention(mention)
    return {
        "mention_id": mention["mention_id"],
        "field_path": mention["field_path"],
        "status": mention["status"],
        "target_ids": mention["target_ids"],
        "normalized_keys": mention.get("normalized_keys") or [],
        "mention_text_sha256": hashlib.sha256(
            mention["mention_text"].encode("utf-8")
        ).hexdigest(),
    }


def opportunity_binding(
    opportunity_id: str,
    museum: str,
    normalized_expression_key: str,
    artifact_id: str,
    mentions: list[dict],
) -> dict:
    """Bind one ITT artifact to the exact private mentions that selected it."""
    exact_mentions = sorted(
        (mention_binding(mention) for mention in mentions),
        key=lambda row: row["mention_id"],
    )
    if not exact_mentions:
        raise RuntimeError(f"{opportunity_id}/{artifact_id} has no selecting mentions")
    payload = {
        "opportunity_id": opportunity_id,
        "museum": museum,
        "normalized_expression_key": normalized_expression_key,
        "artifact_id": artifact_id,
        "mentions": exact_mentions,
    }
    return {
        "artifact_id": artifact_id,
        "opportunity_binding_sha256": canonical_json_sha256(payload),
        "mentions": exact_mentions,
    }


def gzip_ledger_digest(path: Path) -> dict:
    """Authenticate both transport bytes and canonical uncompressed row bytes."""
    leaves: list[bytes] = []
    uncompressed = hashlib.sha256()
    row_count = 0
    with gzip.open(path, "rb") as handle:
        for line in handle:
            uncompressed.update(line)
            leaves.append(hashlib.sha256(line).digest())
            row_count += 1
    if not leaves:
        merkle_root = hashlib.sha256(b"").hexdigest()
    else:
        level = leaves
        while len(level) > 1:
            if len(level) % 2:
                level = [*level, level[-1]]
            level = [
                hashlib.sha256(level[index] + level[index + 1]).digest()
                for index in range(0, len(level), 2)
            ]
        merkle_root = level[0].hex()
    return {
        "row_count": row_count,
        "transport_gzip_sha256": sha256(path),
        "canonical_uncompressed_ndjson_sha256": uncompressed.hexdigest(),
        "canonical_row_merkle_sha256": merkle_root,
        "merkle_algorithm": (
            "sha256(canonical compact sorted-key JSON row plus LF) leaves; "
            "sha256(left_digest || right_digest), duplicating an odd final digest"
        ),
    }


def classify_current_nodes(
    idai_rows: list[dict], raw_hierarchy: list[dict], crosswalk: dict,
    expected_target_count: int,
) -> tuple[list[dict], dict[str, str], dict]:
    sites = sorted((row for row in idai_rows if row.get("kind") == "site"), key=lambda row: row["id"])
    filtered_ids = {row["id"] for row in sites}
    raw_ids = {f"idai:{row['gazId']}" for row in raw_hierarchy}
    children: dict[str, list[str]] = collections.defaultdict(list)
    for row in raw_hierarchy:
        parent = row.get("parent")
        if parent:
            children[f"idai:{parent.rsplit('/', 1)[-1]}"].append(f"idai:{row['gazId']}")

    mappings = crosswalk["idai_gazetteer_actual_hyphenated_types"]
    output = []
    scope_by_target = {}
    for row in sites:
        types = set(row.get("types") or [])
        unmapped = sorted(types - set(mappings))
        if unmapped:
            raise RuntimeError(f"unmapped actual iDAI types for {row['id']}: {unmapped}")
        mapped_scopes = {mappings[source_type]["scope"] for source_type in types}
        broad_reasons = []
        if "broad" in mapped_scopes:
            broad_reasons.append("current_upstream_broad_type")
        if children[row["id"]]:
            broad_reasons.append("has_child_in_complete_available_raw_hierarchy")
        if broad_reasons:
            scope = "broad"
            reasons = broad_reasons
        elif "specific_candidate" in mapped_scopes:
            scope = "specific_candidate"
            reasons = ["current_upstream_specific_type_without_raw_hierarchy_child"]
        else:
            scope = "unclassified"
            reasons = ["no_frozen_scope_rule_applies"]
        scope_by_target[row["id"]] = scope
        output.append(
            {
                "target_id": row["id"],
                "authority_identity_locator": row["id"],
                "target_label": row["display"],
                "source_types": sorted(types),
                "raw_hierarchy_child_ids": sorted(children[row["id"]]),
                "child_count_in_complete_available_raw_hierarchy": len(children[row["id"]]),
                "child_count_omitted_from_filtered_1000": sum(
                    child not in filtered_ids for child in children[row["id"]]
                ),
                "scope_class": scope,
                "scope_reasons": reasons,
                "warning": (
                    "Descriptive baseline class only; specific_candidate is not reviewed "
                    "specificity support and cannot satisfy a future success gate."
                ),
            }
        )
    if len(output) != expected_target_count or len(scope_by_target) != expected_target_count:
        raise RuntimeError(
            f"expected {expected_target_count:,} current site targets, got {len(output)}"
        )
    hierarchy_summary = {
        "complete_available_raw_records": len(raw_hierarchy),
        "complete_available_raw_ids": len(raw_ids),
        "raw_records_with_parent_outside_available_hierarchy": sum(
            bool(row.get("parent"))
            and f"idai:{row['parent'].rsplit('/', 1)[-1]}" not in raw_ids
            for row in raw_hierarchy
        ),
        "filtered_targets": len(filtered_ids),
        "filtered_targets_with_any_raw_child": sum(bool(children[target]) for target in filtered_ids),
        "filtered_targets_with_children_omitted_from_filtered_set": sum(
            any(child not in filtered_ids for child in children[target]) for target in filtered_ids
        ),
        "omitted_raw_child_edges_from_filtered_targets": sum(
            child not in filtered_ids for target in filtered_ids for child in children[target]
        ),
        "limitation": (
            "Complete means all 2,075 records in the pinned available raw iDAI acquisition, "
            "not a claim that the external gazetteer or world hierarchy is complete."
        ),
    }
    return output, scope_by_target, hierarchy_summary


def resolution_state(statuses: set[str]) -> str:
    if not statuses:
        return "no_extracted_site_evidence"
    if not statuses <= ATTEMPT_STATUSES:
        raise RuntimeError(f"site evidence includes a non-attempt status: {sorted(statuses)}")
    resolved = "resolved" in statuses
    ambiguous = "ambiguous" in statuses
    unmatched = "unmatched" in statuses
    if resolved:
        return "resolved_with_unresolved_mentions" if ambiguous or unmatched else "resolved_only"
    if ambiguous and unmatched:
        return "blocking_ambiguous_and_unmatched"
    if ambiguous:
        return "blocking_ambiguous_only"
    if unmatched:
        return "unmatched_only"
    raise RuntimeError(f"unhandled site resolution status set: {sorted(statuses)}")


def build_record_rows(
    canonical: list[dict], mentions: list[dict], links: list[dict], scope_by_target: dict[str, str]
) -> list[dict]:
    site_mentions: dict[str, list[dict]] = collections.defaultdict(list)
    seen_site_mention_ids: set[str] = set()
    for mention in mentions:
        if mention["entity_type"] == "site":
            validate_site_mention(mention)
            if mention["mention_id"] in seen_site_mention_ids:
                raise RuntimeError(f"duplicate site mention id {mention['mention_id']}")
            seen_site_mention_ids.add(mention["mention_id"])
            site_mentions[mention["artifact_id"]].append(mention)

    site_links: dict[str, list[dict]] = collections.defaultdict(list)
    for link in links:
        if link["entity_type"] == "site":
            if link["target_id"] not in scope_by_target:
                raise RuntimeError(f"unknown current site target {link['target_id']}")
            site_links[link["artifact_id"]].append(link)

    rows = []
    seen = set()
    for artifact in sorted(canonical, key=lambda row: row["id"]):
        artifact_id = artifact["id"]
        if artifact_id in seen:
            raise RuntimeError(f"duplicate canonical artifact id {artifact_id}")
        seen.add(artifact_id)
        artifact_mentions = site_mentions.get(artifact_id, [])
        artifact_links = site_links.get(artifact_id, [])
        statuses = {mention["status"] for mention in artifact_mentions}
        status_counts = collections.Counter(mention["status"] for mention in artifact_mentions)
        target_ids = sorted({link["target_id"] for link in artifact_links})
        resolved_targets_from_mentions = sorted(
            {
                mention["target_ids"][0]
                for mention in artifact_mentions
                if mention["status"] == "resolved" and len(mention["target_ids"]) == 1
            }
        )
        if target_ids != resolved_targets_from_mentions:
            raise RuntimeError(f"site link/mention target mismatch for {artifact_id}")
        if len(target_ids) > status_counts["resolved"]:
            raise RuntimeError(
                f"site record {artifact_id} has more unique direct targets than resolved mentions"
            )
        if bool(artifact_mentions) != bool(statuses):
            raise RuntimeError(f"invalid mention/status accounting for {artifact_id}")

        scope_counts = collections.Counter(scope_by_target[target] for target in target_ids)
        local_scope = partition_scopes(set(scope_counts))

        rows.append(
            {
                "artifact_id": artifact_id,
                "museum": artifact["source_museum"],
                "extracted_site_text_evidence": bool(artifact_mentions),
                "extracted_site_text_rule": "at_least_one_frozen_site_mention_with_resolution_attempt; no independent evidence-quality judgment",
                "site_mention_count": len(artifact_mentions),
                "site_mention_status_counts": dict(sorted(status_counts.items())),
                "baseline_resolution_state": resolution_state(statuses),
                "baseline_site_target_ids": target_ids,
                "baseline_site_target_scope_counts": dict(sorted(scope_counts.items())),
                "baseline_record_scope": local_scope,
                "has_any_ambiguity": "ambiguous" in statuses,
                "has_blocking_ambiguity": bool(artifact_mentions)
                and not target_ids
                and "ambiguous" in statuses,
                "has_any_unmatched_expression": "unmatched" in statuses,
            }
        )

    unknown_mentions = sorted(set(site_mentions) - seen)
    unknown_links = sorted(set(site_links) - seen)
    if unknown_mentions or unknown_links:
        raise RuntimeError(
            f"derived rows reference non-canonical artifacts: mentions={unknown_mentions[:3]} "
            f"links={unknown_links[:3]}"
        )
    return rows


def scope_partition(
    museum: str, shared_targets: set[str], site_links: list[dict], scope_by_target: dict[str, str]
) -> tuple[dict, set[str]]:
    target_sets: dict[str, set[str]] = collections.defaultdict(set)
    for link in site_links:
        if link["museum"] == museum and link["target_id"] in shared_targets:
            target_sets[link["artifact_id"]].add(link["target_id"])
    counts = collections.Counter()
    for targets in target_sets.values():
        counts[partition_scopes({scope_by_target[target] for target in targets})] += 1
    return (
        {
            "connected_records": len(target_sets),
            "mutually_exclusive_scope_counts": {
                key: counts[key]
                for key in ("specific_candidate_present", "broad_only", "unclassified_only")
            },
        },
        set(target_sets),
    )


def connectivity_metrics(
    site_links: list[dict], record_counts: dict[str, int], evidence_counts: dict[str, int],
    scope_by_target: dict[str, str],
) -> dict:
    links_by_artifact: dict[str, set[str]] = collections.defaultdict(set)
    artifacts_by_museum: dict[str, set[str]] = {museum: set() for museum in MUSEUMS}
    for link in site_links:
        links_by_artifact[link["artifact_id"]].add(link["target_id"])
        artifacts_by_museum[link["museum"]].add(link["artifact_id"])
    targets_by_museum = {
        museum: {link["target_id"] for link in site_links if link["museum"] == museum}
        for museum in MUSEUMS
    }

    pairs = {}
    for left, right in PAIRS:
        shared = targets_by_museum[left] & targets_by_museum[right]
        pair_links = [link for link in site_links if link["museum"] in (left, right)]
        sides = {}
        for museum in (left, right):
            partition, connected = scope_partition(
                museum, shared, pair_links, scope_by_target
            )
            sides[museum] = {
                **partition,
                "overall_connection_rate": ratio(len(connected), record_counts[museum]),
                "extracted_site_text_conditional_connection_rate": ratio(
                    len(connected), evidence_counts[museum]
                ),
            }
        pairs[f"{left}__{right}"] = {
            "membership": "inclusive; an all-three node also belongs to each constituent pair",
            "shared_target_ids": sorted(shared),
            "shared_node_count": len(shared),
            "shared_node_scope_counts": dict(
                sorted(collections.Counter(scope_by_target[target] for target in shared).items())
            ),
            "sides": sides,
            "concentration_by_museum_side": {
                museum: concentration(
                    links_by_artifact,
                    artifacts_by_museum[museum],
                    shared,
                )
                for museum in (left, right)
            },
            "pooled_concentration_descriptive_only": concentration(
                links_by_artifact,
                artifacts_by_museum[left] | artifacts_by_museum[right],
                shared,
            ),
        }

    all_three = set.intersection(*(targets_by_museum[museum] for museum in MUSEUMS))
    all_three_sides = {}
    for museum in MUSEUMS:
        partition, connected = scope_partition(
            museum, all_three, site_links, scope_by_target
        )
        all_three_sides[museum] = {
            **partition,
            "overall_connection_rate": ratio(len(connected), record_counts[museum]),
            "extracted_site_text_conditional_connection_rate": ratio(
                len(connected), evidence_counts[museum]
            ),
        }

    target_museums: dict[str, set[str]] = collections.defaultdict(set)
    for link in site_links:
        target_museums[link["target_id"]].add(link["museum"])
    any_shared = {target for target, museums in target_museums.items() if len(museums) >= 2}
    exact_combinations = collections.Counter(
        "+".join(sorted(museums))
        for target, museums in target_museums.items()
        if len(museums) >= 2
    )
    return {
        "model": "deduplicated direct artifact-to-site-node incidence; no artifact all-pairs table",
        "pairs": pairs,
        "all_three": {
            "shared_target_ids": sorted(all_three),
            "shared_node_count": len(all_three),
            "shared_node_scope_counts": dict(
                sorted(collections.Counter(scope_by_target[target] for target in all_three).items())
            ),
            "sides": all_three_sides,
            "concentration_by_museum_side": {
                museum: concentration(
                    links_by_artifact,
                    artifacts_by_museum[museum],
                    all_three,
                )
                for museum in MUSEUMS
            },
            "pooled_concentration_descriptive_only": concentration(
                links_by_artifact,
                set().union(*artifacts_by_museum.values()),
                all_three,
            ),
        },
        "any_two_or_more": {
            "shared_target_ids": sorted(any_shared),
            "shared_node_count": len(any_shared),
            "exact_museum_combination_counts": dict(sorted(exact_combinations.items())),
            "shared_node_scope_counts": dict(
                sorted(collections.Counter(scope_by_target[target] for target in any_shared).items())
            ),
            "concentration_by_museum_side": {
                museum: concentration(
                    links_by_artifact,
                    artifacts_by_museum[museum],
                    any_shared,
                )
                for museum in MUSEUMS
            },
            "pooled_concentration_descriptive_only": concentration(
                links_by_artifact,
                set().union(*artifacts_by_museum.values()),
                any_shared,
            ),
        },
    }


def build_metrics(record_rows: list[dict], site_links: list[dict], scope_by_target: dict[str, str]) -> dict:
    record_counts = collections.Counter(row["museum"] for row in record_rows)
    evidence_counts = collections.Counter(
        row["museum"] for row in record_rows if row["extracted_site_text_evidence"]
    )
    linked_counts = collections.Counter(
        row["museum"] for row in record_rows if row["baseline_site_target_ids"]
    )
    per_museum = {}
    for museum in MUSEUMS:
        rows = [row for row in record_rows if row["museum"] == museum]
        total = record_counts[museum]
        evidence = evidence_counts[museum]
        linked = linked_counts[museum]
        no_link = evidence - linked
        per_museum[museum] = {
            "canonical_records": total,
            "extracted_site_text_evidence_records": evidence,
            "no_extracted_site_evidence_records": total - evidence,
            "records_with_unique_site_link": linked,
            "extracted_site_text_without_unique_site_link": no_link,
            "extracted_site_text_availability_rate": ratio(evidence, total),
            "overall_linkability": ratio(linked, total),
            "extracted_site_text_conditional_linkability": ratio(linked, evidence),
            "records_with_any_ambiguity": sum(row["has_any_ambiguity"] for row in rows),
            "records_with_blocking_ambiguity": sum(row["has_blocking_ambiguity"] for row in rows),
            "records_with_any_unmatched_expression": sum(
                row["has_any_unmatched_expression"] for row in rows
            ),
            "resolution_state_counts": dict(
                sorted(collections.Counter(row["baseline_resolution_state"] for row in rows).items())
            ),
            "absolute_authority_only_maximum_measurable_gain": {
                "records": no_link,
                "overall_percentage_point_ceiling": ratio(no_link, total),
                "conditional_percentage_point_ceiling": ratio(no_link, evidence),
                "interpretation": (
                    "Upper bound if every already-extracted-site-text record lacking a unique link "
                    "became uniquely resolvable; not an expected effect or an accuracy claim."
                ),
            },
        }

    return {
        "baseline_label": "immutable pre-authority-change site-linkability baseline",
        "canonical_records": len(record_rows),
        "record_counts_by_museum": dict(sorted(record_counts.items())),
        "per_museum": per_museum,
        "connectivity": connectivity_metrics(
            site_links, dict(record_counts), dict(evidence_counts), scope_by_target
        ),
        "scope_warning": (
            "specific_candidate is a deterministic descriptive class, not quality evidence. "
            "Only independently supported decision-ledger links can receive specificity credit."
        ),
    }


def canonical_list_sha256(values: list[str]) -> str:
    encoded = json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def unresolved_site_groups(mentions: list[dict]) -> dict[tuple[str, str], dict]:
    groups: dict[tuple[str, str], dict] = {}
    seen_mention_ids: set[str] = set()
    for mention in mentions:
        if mention.get("entity_type") != "site":
            continue
        validate_site_mention(mention)
        mention_id = mention["mention_id"]
        if mention_id in seen_mention_ids:
            raise RuntimeError(f"duplicate site mention id {mention_id}")
        seen_mention_ids.add(mention_id)
        if mention["status"] not in {"unmatched", "ambiguous"}:
            continue
        keys = mention.get("normalized_keys") or []
        normalized_key = "\u241f".join(keys)
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
        group["mention_ids"].add(mention["mention_id"])
        group["statuses"][mention["status"]] += 1
        group["mention_texts"].add(mention["mention_text"])
        group["field_paths"].add(mention["field_path"])
        group["mentions_by_artifact"][mention["artifact_id"]].append(mention)
    return groups


def ranked_groups(groups: dict[tuple[str, str], dict]) -> list[dict]:
    return sorted(
        groups.values(),
        key=lambda row: (
            -len(row["artifact_ids"]), row["museum"], row["normalized_expression_key"]
        ),
    )


def build_opportunity_queue(
    mentions: list[dict], record_rows: list[dict], site_links: list[dict],
    scope_by_target: dict[str, str], record_counts: dict[str, int], evidence_counts: dict[str, int],
) -> tuple[dict, dict, dict]:
    """Build public aggregates and a private result-blind ITT membership ledger."""
    groups = unresolved_site_groups(mentions)
    ranked = ranked_groups(groups)
    selected_keys: set[tuple[str, str]] = set()
    selection_reason: dict[tuple[str, str], str] = {}
    # Museum protection is applied before the global frequency fill.
    for museum in MUSEUMS:
        museum_rows = [row for row in ranked if row["museum"] == museum][
            :OPPORTUNITY_MUSEUM_PROTECTION
        ]
        for row in museum_rows:
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

    selected = [row for row in ranked if (row["museum"], row["normalized_expression_key"]) in selected_keys]
    selected.sort(key=lambda row: (-len(row["artifact_ids"]), row["museum"], row["normalized_expression_key"]))
    private_queue_rows = []
    public_queue_rows = []
    selected_artifacts: dict[str, set[str]] = collections.defaultdict(set)
    artifact_opportunity_bindings: dict[str, list[dict]] = collections.defaultdict(list)
    for rank, row in enumerate(selected, 1):
        artifact_ids = sorted(row["artifact_ids"])
        key = (row["museum"], row["normalized_expression_key"])
        # Opaque rank identifiers avoid publishing a dictionary-testable hash of source text.
        opportunity_id = f"opp-{rank:04d}"
        selected_artifacts[row["museum"]].update(artifact_ids)
        artifact_memberships = [
            opportunity_binding(
                opportunity_id,
                row["museum"],
                row["normalized_expression_key"],
                artifact_id,
                row["mentions_by_artifact"][artifact_id],
            )
            for artifact_id in artifact_ids
        ]
        for membership in artifact_memberships:
            artifact_opportunity_bindings[membership["artifact_id"]].append(
                {
                    "opportunity_id": opportunity_id,
                    "opportunity_binding_sha256": membership[
                        "opportunity_binding_sha256"
                    ],
                }
            )
        common = {
            "opportunity_id": opportunity_id,
            "selection_rank": rank,
            "selection_reason": selection_reason[key],
            "museum": row["museum"],
            "unresolved_status_counts": dict(sorted(row["statuses"].items())),
            "mention_count": len(row["mention_ids"]),
            "artifact_count": len(artifact_ids),
            "artifact_expansion_sha256": canonical_list_sha256(artifact_ids),
            "intent_to_treat": True,
        }
        private_queue_rows.append(
            {
                **common,
                "normalized_expression_key": row["normalized_expression_key"],
                "artifact_ids": artifact_ids,
                "artifact_memberships": artifact_memberships,
                "mention_text_examples": sorted(row["mention_texts"])[:5],
                "field_paths": sorted(row["field_paths"]),
            }
        )
        public_queue_rows.append(common)

    record_by_id = {row["artifact_id"]: row for row in record_rows}
    summary_by_museum = {}
    for museum in MUSEUMS:
        artifact_ids = selected_artifacts[museum]
        categories = collections.Counter(
            record_by_id[artifact_id]["baseline_record_scope"] for artifact_id in artifact_ids
        )
        unlinked = categories["no_link"]
        broad = categories["broad_only"]
        summary_by_museum[museum] = {
            "selected_signature_count": sum(
                row["museum"] == museum for row in private_queue_rows
            ),
            "intent_to_treat_record_count": len(artifact_ids),
            "baseline_record_scope_counts": dict(sorted(categories.items())),
            "new_record_link_ceiling_records": unlinked,
            "strict_refinement_reassignment_ceiling_records": broad,
            "maximum_credited_affected_records": unlinked + broad,
            "maximum_overall_effect": ratio(unlinked + broad, record_counts[museum]),
            "maximum_extracted_site_text_conditional_effect": ratio(
                unlinked + broad, evidence_counts[museum]
            ),
        }

    targets_by_museum = {
        museum: {link["target_id"] for link in site_links if link["museum"] == museum}
        for museum in MUSEUMS
    }
    links_by_artifact: dict[str, set[str]] = collections.defaultdict(set)
    for link in site_links:
        links_by_artifact[link["artifact_id"]].add(link["target_id"])
    pair_sides = {}
    private_pair_memberships = {}
    for left, right in PAIRS:
        pair_key = f"{left}__{right}"
        shared = targets_by_museum[left] & targets_by_museum[right]
        sides = {}
        private_sides = {}
        for museum in (left, right):
            counts = collections.Counter()
            credited_members = []
            for artifact_id in selected_artifacts[museum]:
                pair_targets = links_by_artifact[artifact_id] & shared
                scopes = {scope_by_target[target] for target in pair_targets}
                if not pair_targets:
                    counts["no_baseline_pair_connection"] += 1
                    credited_members.append(
                        {
                            "artifact_id": artifact_id,
                            "category": "no_baseline_pair_connection",
                            "opportunity_bindings": sorted(
                                artifact_opportunity_bindings[artifact_id],
                                key=lambda item: item["opportunity_id"],
                            ),
                        }
                    )
                elif "specific_candidate" in scopes:
                    counts["baseline_specific_present"] += 1
                elif "broad" in scopes:
                    counts["baseline_broad_only"] += 1
                    credited_members.append(
                        {
                            "artifact_id": artifact_id,
                            "category": "broad_only_pair_connection",
                            "opportunity_bindings": sorted(
                                artifact_opportunity_bindings[artifact_id],
                                key=lambda item: item["opportunity_id"],
                            ),
                        }
                    )
                else:
                    counts["baseline_unclassified_only"] += 1
            credited_members.sort(key=lambda row: row["artifact_id"])
            fixed_opportunity = counts["no_baseline_pair_connection"] + counts["baseline_broad_only"]
            minimum = (
                max(
                    1,
                    (
                        fixed_opportunity * MINIMUM_AFFECTED_FRACTION.numerator
                        + MINIMUM_AFFECTED_FRACTION.denominator
                        - 1
                    )
                    // MINIMUM_AFFECTED_FRACTION.denominator,
                )
                if fixed_opportunity
                else 0
            )
            sides[museum] = {
                "intent_to_treat_record_count": len(selected_artifacts[museum]),
                "baseline_pair_partition": dict(sorted(counts.items())),
                "new_pair_connection_ceiling_records": counts["no_baseline_pair_connection"],
                "strict_refinement_pair_reassignment_ceiling_records": counts["baseline_broad_only"],
                "credited_effect_opportunity_denominator": fixed_opportunity,
                "minimum_credited_affected_records_for_continue": minimum,
                "credited_pair_opportunity_membership_sha256": canonical_json_sha256(
                    credited_members
                ),
            }
            private_sides[museum] = credited_members
        pair_sides[pair_key] = {"sides": sides}
        private_pair_memberships[pair_key] = {"sides": private_sides}

    top_components = {
        "schema_version": "site-graph-v0-top-unmatched-components/1",
        "definition": "Top unresolved site-expression groups from the complete pinned baseline mentions, not the 500-row archived top-gaps truncation.",
        "per_museum": {
            museum: [
                {
                    "component_id": f"component-{museum}-{rank:02d}",
                    "artifact_count": len(row["artifact_ids"]),
                    "mention_count": len(row["mention_ids"]),
                    "unresolved_status_counts": dict(sorted(row["statuses"].items())),
                }
                for rank, row in enumerate(
                    [item for item in ranked if item["museum"] == museum][:20], 1
                )
            ]
            for museum in MUSEUMS
        },
    }
    selection_algorithm = {
        "eligible_population": "unmatched or ambiguous site mentions emitted by the frozen baseline adapter",
        "group_key": "(museum, exact ordered normalized_keys joined with U+241F; deterministic normalized mention fallback only when keys are empty)",
        "ranking": "descending distinct artifact count, then museum, then normalized expression key",
        "museum_protection": "select each museum's first 10 groups before global fill",
        "global_fill": "select the next ranked groups until exactly 50 total",
        "result_blind": "selection uses baseline inputs only and predates candidate research, review, graph, or matching results",
    }
    public_summary = {
        "schema_version": "site-graph-v0-opportunity-summary/2",
        "public_data_boundary": (
            "Aggregate-only release: no artifact IDs, raw mention text, field paths, or "
            "normalized expression text. Exact membership is regenerated privately and "
            "authenticated by the committed digests."
        ),
        "selection_algorithm": selection_algorithm,
        "minimum_affected_opportunity_fraction": {
            "numerator": MINIMUM_AFFECTED_FRACTION.numerator,
            "denominator": MINIMUM_AFFECTED_FRACTION.denominator,
        },
        "denominator_policy": "Every expanded artifact remains in its fixed intent-to-treat denominator after research failure, abstention, disagreement, or unsupported scope.",
        "credit_warning": "Selection is not identity support. Broad or administrative links and unsupported narrower links receive zero improvement credit.",
        "selected_signature_count": len(public_queue_rows),
        "opportunities": public_queue_rows,
        "per_museum": summary_by_museum,
        "pair_side_ceilings": pair_sides,
    }
    private_records = {
        museum: [
            {
                "artifact_id": artifact_id,
                "opportunity_bindings": sorted(
                    artifact_opportunity_bindings[artifact_id],
                    key=lambda item: item["opportunity_id"],
                ),
                "baseline_record_scope": record_by_id[artifact_id]["baseline_record_scope"],
            }
            for artifact_id in sorted(selected_artifacts[museum])
        ]
        for museum in MUSEUMS
    }
    private_ledger = {
        "schema_version": "site-graph-v0-private-opportunity-ledger/3",
        "privacy": "private runtime derivative; must not be committed or redistributed",
        "selection_algorithm": selection_algorithm,
        "selected_signature_count": len(private_queue_rows),
        "opportunities": private_queue_rows,
        "intent_to_treat_records_by_museum": private_records,
        "credited_pair_opportunity_memberships": private_pair_memberships,
    }
    return public_summary, private_ledger, top_components


def private_opportunity_source(mentions: list[dict]) -> list[dict]:
    """Preserve every site mention primitive needed for correction replay."""
    rows = []
    seen_ids: set[str] = set()
    for mention in mentions:
        if mention.get("entity_type") != "site":
            continue
        validate_site_mention(mention)
        if mention["mention_id"] in seen_ids:
            raise RuntimeError(f"duplicate site mention id {mention['mention_id']}")
        seen_ids.add(mention["mention_id"])
        rows.append(
            {
                "artifact_id": mention["artifact_id"],
                "field_path": mention["field_path"],
                "mention_id": mention["mention_id"],
                "mention_text": mention["mention_text"],
                "museum": mention["museum"],
                "normalized_keys": mention.get("normalized_keys") or [],
                "status": mention["status"],
                "target_ids": mention["target_ids"],
                "entity_type": "site",
            }
        )
    return sorted(rows, key=lambda row: row["mention_id"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()

    evaluation_root = args.repo_root / "docs/evaluations/site-graph-v0"
    snapshot = read_json(evaluation_root / "input-snapshot.json")
    archive_attestation_path = args.run_dir / "corpus-archive-attestation.json"
    if not archive_attestation_path.is_file():
        raise RuntimeError(
            "baseline derivation requires the authenticated runtime corpus archive attestation"
        )
    archive_attestation = read_json(archive_attestation_path)
    validate_archive_attestation(snapshot["corpus"], archive_attestation)
    crosswalk = read_json(evaluation_root / "type-crosswalk.json")
    canonical = read_gzip_jsonl(args.corpus / "data" / "artifacts.ndjson.gz")
    mentions = read_gzip_jsonl(args.run_dir / "mentions.ndjson.gz")
    links = read_gzip_jsonl(args.run_dir / "artifact_authority_links.ndjson.gz")
    idai_rows = read_jsonl(
        args.repo_root
        / "pipeline/pipeline/authority/sources/idai-gazetteer/reconciled.jsonl"
    )
    raw_hierarchy = read_json(
        args.repo_root / "pipeline/pipeline/authority/sources/idai-gazetteer/raw.json"
    )
    expected_records = snapshot["corpus"]["canonical_record_count"]
    expected_targets = snapshot["current_authority"]["site_snapshot"]["site_target_count"]
    if len(canonical) != expected_records:
        raise RuntimeError(
            f"expected {expected_records:,} canonical records, got {len(canonical)}"
        )

    node_rows, scope_by_target, hierarchy_summary = classify_current_nodes(
        idai_rows, raw_hierarchy, crosswalk, expected_targets
    )
    record_rows = build_record_rows(canonical, mentions, links, scope_by_target)
    site_links = [link for link in links if link["entity_type"] == "site"]
    metrics = build_metrics(record_rows, site_links, scope_by_target)
    record_counts = collections.Counter(row["museum"] for row in record_rows)
    evidence_counts = collections.Counter(
        row["museum"] for row in record_rows if row["extracted_site_text_evidence"]
    )
    opportunity_summary, private_opportunity_ledger, top_components = build_opportunity_queue(
        mentions, record_rows, site_links, scope_by_target,
        dict(record_counts), dict(evidence_counts),
    )
    metrics["planned_slice_maximum_measurable_effect"] = {
        "source": "planned-opportunity-summary.json",
        "per_museum": opportunity_summary["per_museum"],
        "pair_side_ceilings": opportunity_summary["pair_side_ceilings"],
        "interpretation": (
            "Numeric intent-to-treat upper bounds, not expected effects or accuracy claims. "
            "Unsupported, broad/administrative, abstained, failed, and disputed research remains in denominators and earns zero credit."
        ),
    }

    write_json(
        args.run_dir / "baseline-node-scope.json",
        {
            "schema_version": "site-graph-v0-baseline-node-scope/2",
            "hierarchy_context": hierarchy_summary,
            "nodes": node_rows,
        },
    )
    private_record_path = args.run_dir / "private-record-evidence.ndjson.gz"
    private_source_path = args.run_dir / "private-opportunity-source.ndjson.gz"
    private_opportunity_path = args.run_dir / "private-opportunity-ledger.json"
    write_gzip_jsonl(private_record_path, record_rows)
    write_gzip_jsonl(
        private_source_path,
        private_opportunity_source(mentions),
    )
    write_json(private_opportunity_path, private_opportunity_ledger)

    private_opportunity_digest = {
        "bytes": private_opportunity_path.stat().st_size,
        "transport_json_sha256": sha256(private_opportunity_path),
        "canonical_json_sha256": canonical_json_sha256(private_opportunity_ledger),
        "selected_signature_count": private_opportunity_ledger[
            "selected_signature_count"
        ],
        "intent_to_treat_record_counts_by_museum": {
            museum: len(rows)
            for museum, rows in private_opportunity_ledger[
                "intent_to_treat_records_by_museum"
            ].items()
        },
    }
    opportunity_summary["private_ledger_authentication"] = {
        "canonical_json_sha256": private_opportunity_digest["canonical_json_sha256"],
        "transport_json_sha256": private_opportunity_digest["transport_json_sha256"],
    }
    private_digests = {
        "schema_version": "site-graph-v0-private-ledger-digests/1",
        "public_data_boundary": (
            "This file contains counts and cryptographic digests only. Private ledger "
            "rows must be regenerated from the separately supplied verified corpus."
        ),
        "canonical_serialization": (
            "UTF-8 compact sorted-key JSON per row followed by LF for NDJSON; "
            "UTF-8 compact sorted-key JSON for JSON ledgers"
        ),
        "external_private_input": {
            "canonical_record_count": expected_records,
            "canonical_artifact_transport_gzip_sha256": snapshot["corpus"]["files"]
            ["data/artifacts.ndjson.gz"]["sha256"],
            "archive_sha256": archive_attestation["archive"]["sha256"],
            "snapshot_acquisition_integrity": archive_attestation["status"][
                "snapshot_acquisition_integrity"
            ],
            "upstream_production_lineage": archive_attestation["status"][
                "upstream_production_lineage"
            ],
            "historical_export_reproducibility": "UNAVAILABLE_DISCLOSED",
            "unavailable_lineage_effect": snapshot["corpus"]["production_lineage"][
                "effect"
            ],
        },
        "ledgers": {
            "private_record_evidence": gzip_ledger_digest(private_record_path),
            "private_opportunity_source": gzip_ledger_digest(private_source_path),
            "private_opportunity_membership": private_opportunity_digest,
        },
        "pair_side_membership": {
            pair_key: {
                museum: {
                    "record_count": len(rows),
                    "canonical_json_sha256": canonical_json_sha256(rows),
                    "category_counts": dict(
                        sorted(collections.Counter(row["category"] for row in rows).items())
                    ),
                }
                for museum, rows in pair["sides"].items()
            }
            for pair_key, pair in private_opportunity_ledger[
                "credited_pair_opportunity_memberships"
            ].items()
        },
    }
    write_json(args.run_dir / "baseline-metrics.json", metrics)
    write_json(args.run_dir / "planned-opportunity-summary.json", opportunity_summary)
    write_json(args.run_dir / "private-ledger-digests.json", private_digests)
    write_json(args.run_dir / "top-unmatched-components.json", top_components)
    print(
        json.dumps(
            {
                "canonical_records": len(record_rows),
                "private_record_evidence_sha256": sha256(private_record_path),
                "private_record_evidence_uncompressed_sha256": uncompressed_sha256(
                    private_record_path
                ),
                "records_by_museum": metrics["record_counts_by_museum"],
                "site_shared_nodes": metrics["connectivity"]["any_two_or_more"][
                    "shared_node_count"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
