"""Shared deterministic scope partition and concentration metrics."""

from __future__ import annotations

from collections import defaultdict


TOP_K = (1, 5, 10)


def ratio(numerator: int, denominator: int) -> dict:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def partition_scopes(scopes: set[str]) -> str:
    """Apply the same any-specific / any-broad precedence to either arm."""
    if "specific_candidate" in scopes:
        return "specific_candidate_present"
    if "broad" in scopes:
        return "broad_only"
    if scopes:
        return "unclassified_only"
    return "no_link"


def concentration(
    links_by_artifact: dict[str, set[str]],
    artifacts: set[str],
    eligible_targets: set[str],
) -> dict:
    """Top-k uses unique-record unions; HHI separately uses node incidences."""
    node_artifacts: dict[str, set[str]] = defaultdict(set)
    for artifact_id in sorted(artifacts):
        for target_id in sorted(links_by_artifact.get(artifact_id, set()) & eligible_targets):
            node_artifacts[target_id].add(artifact_id)
    ordered = sorted(node_artifacts, key=lambda target: (-len(node_artifacts[target]), target))
    all_artifacts = (
        set().union(*(node_artifacts[target] for target in ordered)) if ordered else set()
    )
    incidence = sum(len(node_artifacts[target]) for target in ordered)
    result = {
        "shared_node_count": len(ordered),
        "distinct_connected_records": len(all_artifacts),
        "node_incidence_total": incidence,
        "node_incidence_hhi": ratio(
            sum(len(node_artifacts[target]) ** 2 for target in ordered),
            incidence**2,
        ),
        "top_k_unique_record_concentration": {},
    }
    for k in TOP_K:
        selected = ordered[:k]
        selected_artifacts = (
            set().union(*(node_artifacts[target] for target in selected)) if selected else set()
        )
        result["top_k_unique_record_concentration"][str(k)] = {
            "selected_target_ids": selected,
            "ratio": ratio(len(selected_artifacts), len(all_artifacts)),
        }
    return result
