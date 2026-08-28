#!/usr/bin/env python3
"""Derive field provenance, coverage, connectivity concentration, and SILVER sensitivity.

This script does not change the resolver.  The SILVER sensitivity is explicitly a
post-hoc diagnostic that removes only sampled links adjudicated false; it is not a
corrected population metric.
"""

from __future__ import annotations

import collections
import gzip
import json
import os
from pathlib import Path


OUT = Path(os.environ.get("HAPI_EVAL_OUT", "/tmp/hapi-linkability-mvp"))


def read_gzip_jsonl(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def coverage(links: list[dict], denominators: dict[str, int]) -> dict:
    result = {}
    for museum in sorted(denominators):
        rows = [row for row in links if row["museum"] == museum]
        artifacts = {row["artifact_id"] for row in rows}
        by_entity = {}
        for entity in ("ruler", "site", "tomb_monument"):
            linked = {row["artifact_id"] for row in rows if row["entity_type"] == entity}
            by_entity[entity] = {
                "linked_artifacts": len(linked),
                "records_denominator": denominators[museum],
                "record_link_rate": len(linked) / denominators[museum],
            }
        result[museum] = {
            "linked_artifacts_any_entity": len(artifacts),
            "records_denominator": denominators[museum],
            "record_link_rate_any_entity": len(artifacts) / denominators[museum],
            "by_entity_type": by_entity,
        }
    return result


def node_connectivity(links: list[dict]) -> tuple[list[dict], dict]:
    groups: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for row in links:
        groups[(row["entity_type"], row["target_id"])].append(row)
    nodes = []
    for (entity, target), rows in sorted(groups.items()):
        museums = collections.Counter(row["museum"] for row in rows)
        nodes.append({
            "entity_type": entity,
            "target_id": target,
            "museum_count": len(museums),
            "artifact_count": len(rows),
            "artifact_counts_by_museum": dict(sorted(museums.items())),
        })
    shared_keys = {(row["entity_type"], row["target_id"]) for row in nodes if row["museum_count"] >= 2}
    shared_artifacts = {
        row["artifact_id"] for row in links
        if (row["entity_type"], row["target_id"]) in shared_keys
    }
    metrics = {
        "shared_nodes": len(shared_keys),
        "shared_nodes_by_entity_type": dict(sorted(collections.Counter(entity for entity, _ in shared_keys).items())),
        "artifacts_on_shared_nodes": len(shared_artifacts),
        "discoverable_artifacts_by_entity_type": {
            entity: len({
                row["artifact_id"] for row in links
                if row["entity_type"] == entity and (entity, row["target_id"]) in shared_keys
            })
            for entity in ("ruler", "site", "tomb_monument")
        },
    }
    return nodes, metrics


def main() -> None:
    mentions = read_gzip_jsonl(OUT / "mentions.ndjson.gz")
    links = read_gzip_jsonl(OUT / "artifact_authority_links.ndjson.gz")
    linkability = json.loads((OUT / "linkability_metrics.json").read_text(encoding="utf-8"))
    denominators = linkability["scope"]["records_by_museum"]

    grouped: dict[tuple[str, str, str], list[dict]] = collections.defaultdict(list)
    for row in mentions:
        grouped[(row["museum"], row["entity_type"], row["field_path"])].append(row)
    field_rows = []
    for (museum, entity, field_path), rows in sorted(grouped.items()):
        statuses = collections.Counter(row["status"] for row in rows)
        field_rows.append({
            "museum": museum,
            "entity_type": entity,
            "field_path": field_path,
            "source_layers": sorted({row["source_layer"] for row in rows}),
            "evidence_roles": dict(sorted(collections.Counter(row["evidence_role"] for row in rows).items())),
            "extraction_methods": dict(sorted(collections.Counter(row["extraction_method"] for row in rows).items())),
            "records_with_mentions": len({row["artifact_id"] for row in rows}),
            "mentions": len(rows),
            "status_counts": dict(sorted(statuses.items())),
            "records_with_unique_resolution": len({row["artifact_id"] for row in rows if row["status"] == "resolved"}),
            "mentions_with_unique_resolution": statuses["resolved"],
            "span_provenance_output": "mentions.ndjson.gz: field_value, span_start, span_end, mention_text",
        })
    write_json(OUT / "field_provenance_metrics.json", field_rows)
    write_json(OUT / "artifact_link_coverage.json", {
        "definition": "Distinct canonical records with at least one deduplicated artifact-to-current-authority link; exact museum record denominators shown.",
        "by_museum": coverage(links, denominators),
    })

    base_nodes, base_metrics = node_connectivity(links)
    catalog_nodes = json.loads((OUT / "authority_node_connectivity.json").read_text(encoding="utf-8"))
    labels = {(row["entity_type"], row["target_id"]): row.get("target_label") for row in catalog_nodes}
    shared = [row for row in base_nodes if row["museum_count"] >= 2]
    for row in shared:
        row["target_label"] = labels.get((row["entity_type"], row["target_id"]))
    shared.sort(key=lambda row: (-row["artifact_count"], row["entity_type"], row["target_id"]))
    shared_keys = {(row["entity_type"], row["target_id"]) for row in shared}
    discoverable = {
        row["artifact_id"] for row in links
        if (row["entity_type"], row["target_id"]) in shared_keys
    }
    concentration = {}
    for n in (1, 2, 5, 10):
        keys = {(row["entity_type"], row["target_id"]) for row in shared[:n]}
        artifacts = {row["artifact_id"] for row in links if (row["entity_type"], row["target_id"]) in keys}
        concentration[f"top_{n}_shared_nodes"] = {
            "unique_artifacts": len(artifacts),
            "discoverable_artifacts_denominator": len(discoverable),
            "fraction": len(artifacts) / len(discoverable) if discoverable else None,
        }
    write_json(OUT / "connectivity_detail.json", {
        "model": "Shared current authority-node incidence; no all-pairs materialization.",
        "base_metrics_recomputed": base_metrics,
        "museum_combination_counts": dict(sorted(collections.Counter("+".join(sorted(row["artifact_counts_by_museum"])) for row in shared).items())),
        "three_museum_shared_nodes": sum(row["museum_count"] == 3 for row in shared),
        "concentration": concentration,
        "top_shared_nodes": shared[:50],
        "interpretation_warning": "Broad and nested place mentions are separate evidence spans. Artifact counts are deduplicated per node, but an artifact may appear on several shared nodes; high-level geography can dominate discoverability.",
    })

    adjudications = json.loads((OUT / "review_adjudications.json").read_text(encoding="utf-8"))
    false_rows = [row for row in adjudications if row["resolution_judgment"] == "false_link" and len(row["target_ids"]) == 1]
    removals = {(row["artifact_id"], row["entity_type"], row["target_ids"][0]) for row in false_rows}
    retained_links = [row for row in links if (row["artifact_id"], row["entity_type"], row["target_id"]) not in removals]
    sensitive_nodes, sensitive_metrics = node_connectivity(retained_links)
    base_shared = {(row["entity_type"], row["target_id"]) for row in base_nodes if row["museum_count"] >= 2}
    sensitive_shared = {(row["entity_type"], row["target_id"]) for row in sensitive_nodes if row["museum_count"] >= 2}
    write_json(OUT / "silver_false_link_sensitivity.json", {
        "label": "POST-HOC PROVISIONAL SILVER SENSITIVITY — not corrected population truth",
        "purpose": "Shows how the raw connectivity result changes if only sampled resolved links adjudicated false are removed. Unreviewed links remain untouched.",
        "removed_sampled_links": [
            {"sample_id": row["sample_id"], "artifact_id": row["artifact_id"], "entity_type": row["entity_type"], "target_id": row["target_ids"][0], "evidence_note": row["evidence_note"]}
            for row in false_rows
        ],
        "raw_adapter_metrics": base_metrics,
        "sampled_false_links_removed_metrics": sensitive_metrics,
        "shared_nodes_lost": [
            {"entity_type": entity, "target_id": target, "target_label": labels.get((entity, target))}
            for entity, target in sorted(base_shared - sensitive_shared)
        ],
        "warning": "This is not an accuracy-adjusted estimate: the review is stratified, only sampled false links are removed, and unsupported links may remain.",
    })

    print(json.dumps({
        "field_cells": len(field_rows),
        "coverage": coverage(links, denominators),
        "base_connectivity": base_metrics,
        "sensitivity_connectivity": sensitive_metrics,
        "shared_nodes_lost": sorted(base_shared - sensitive_shared),
        "concentration": concentration,
    }, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
