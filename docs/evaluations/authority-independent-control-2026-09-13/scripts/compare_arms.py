#!/usr/bin/env python3
"""Compare typed surface equality with the frozen current authority resolver."""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import importlib.util
import io
import json
import os
import sys
import unicodedata
from pathlib import Path
from typing import Iterable


BASE_COMMIT = "97f2e610974f0e89b9c03d409b230dff89edbb1f"
EVALUATION_DATE = "2026-09-13"
MUSEUMS = ("met", "brooklyn", "harvard")
PAIRS = (("met", "brooklyn"), ("met", "harvard"), ("brooklyn", "harvard"))
SCORED_ENTITY_TYPES = ("ruler", "site", "tomb_monument")
OUT_OF_SCOPE = {
    "temple": "no committed canonical temple authority",
    "excavation": "no committed canonical excavation authority",
}
CLOSED_LITERAL_LOSS_CAUSES = (
    "absent_or_unmatched_authority_target",
    "ambiguous_multiple_unmerged_claim_graph_units_for_same_literal",
    "ambiguous_authority_target",
    "mixed_ambiguous_and_unmatched_authority_target",
    "different_or_nonshared_unique_authority_targets",
    "partial_unique_resolution_without_common_authority_target",
    "unavailable_authority_type",
    "expression_abstention",
)
CURRENT_INPUTS = {
    "docs/evaluations/hapi-linkability-mvp-2026-08-28/scripts/run_linkability.py":
        "16a2d212c47dc16905021fa08ec9a1225641a465e281b79f0e07589d1c3e59b0",
    "pipeline/pipeline/authority/claimgraph/normalize.py":
        "ec982b40b246ec08abdfceb84e1fb1dfae4726e0299e88fc83d5dd6da1461cc8",
    "web-claimgraph/data/claim-graph.json":
        "d8af0176c45d7a7a238665e2c26beb68d75ef759a7ddaafc1545e2810c5c9965",
    "pipeline/pipeline/authority/sources/idai-gazetteer/reconciled.jsonl":
        "607c5d6f865b6afe89efc6d7c474a554caa756b3ad723a66ddbcf7ef3219dcfd",
    "pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/reconciled.jsonl":
        "4414c5b4a3004c3b6d6669e45a4708bf2405e0c952620633cc155a6d4478a2ff",
    "pipeline/pipeline/authority/sources/porter-moss-memphis/reconciled.jsonl":
        "fa497703c1d64a6d734f8255fe9a920cb9c61e44ceb811d4f86b2306fc22e343",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_line(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_gzip_rows(path: Path, rows: Iterable[dict], id_field: str | None = "mention_id") -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    row_count = 0
    uncompressed = hashlib.sha256()
    mention_ids = hashlib.sha256()
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", compresslevel=9, mtime=0) as compressed:
            for row in rows:
                encoded = canonical_line(row)
                compressed.write(encoded)
                uncompressed.update(encoded)
                if id_field is not None:
                    mention_ids.update((row[id_field] + "\n").encode("utf-8"))
                row_count += 1
    result = {
        "rows": row_count,
        "gzip_sha256": sha256_path(path),
        "canonical_uncompressed_sha256": uncompressed.hexdigest(),
    }
    if id_field is not None:
        result["ordered_mention_ids_sha256"] = mention_ids.hexdigest()
    return result


def read_ledger(path: Path, extraction_manifest: dict) -> tuple[list[dict], dict]:
    expected = extraction_manifest["ledger"]
    actual_gzip = sha256_path(path)
    if actual_gzip != expected["gzip_sha256"]:
        raise ValueError(f"mention ledger gzip SHA-256 mismatch: {actual_gzip}")
    with gzip.open(path, "rb") as handle:
        raw = handle.read()
    if sha256_bytes(raw) != expected["canonical_uncompressed_sha256"]:
        raise ValueError("mention ledger uncompressed SHA-256 mismatch")
    rows = [json.loads(line) for line in raw.splitlines()]
    if len(rows) != expected["rows"]:
        raise ValueError(f"mention ledger row count mismatch: {len(rows)}")
    id_bytes = "".join(row["mention_id"] + "\n" for row in rows).encode("utf-8")
    id_sha = sha256_bytes(id_bytes)
    if id_sha != expected["ordered_mention_ids_sha256"]:
        raise ValueError("mention ledger ordered-ID SHA-256 mismatch")
    for row in rows:
        if row["field_value"][row["span_start"]:row["span_end"]] != row["mention_text"]:
            raise ValueError(f"mention span mismatch: {row['mention_id']}")
    if len(rows) != len({row["mention_id"] for row in rows}):
        raise ValueError("duplicate mention identifier")
    return rows, {
        "rows": len(rows),
        "gzip_sha256": actual_gzip,
        "canonical_uncompressed_sha256": sha256_bytes(raw),
        "ordered_mention_ids_sha256": id_sha,
    }


def surface_key(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split()).casefold()


def verify_current_inputs(repo_root: Path) -> None:
    for relative, expected in CURRENT_INPUTS.items():
        actual = sha256_path(repo_root / relative)
        if actual != expected:
            raise ValueError(f"current resolver input changed: {relative} has {actual}")


def load_current_resolvers(repo_root: Path):
    verify_current_inputs(repo_root)
    module_path = repo_root / "docs/evaluations/hapi-linkability-mvp-2026-08-28/scripts/run_linkability.py"
    old_root = os.environ.get("HAPI_ROOT")
    os.environ["HAPI_ROOT"] = str(repo_root)
    try:
        spec = importlib.util.spec_from_file_location("_frozen_hapi_current_resolver", module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load frozen current resolver")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    finally:
        if old_root is None:
            os.environ.pop("HAPI_ROOT", None)
        else:
            os.environ["HAPI_ROOT"] = old_root
    graph = json.loads(module.GRAPH.read_text(encoding="utf-8"))
    ruler, ruler_catalog = module.build_ruler_resolver(graph)
    site, site_catalog = module.build_site_resolver(module.load_jsonl(module.IDAI))
    tomb, tomb_catalog = module.build_pm_resolver()
    return module, {
        "ruler": (ruler, module.ruler_norm),
        "site": (site, module.place_norm_set),
        "tomb_monument": (tomb, module.place_norm_set),
    }, {
        "ruler": ruler_catalog,
        "site": site_catalog,
        "tomb_monument": tomb_catalog,
    }


def resolve_mentions(mentions: list[dict], arm: str, resolvers=None) -> list[dict]:
    if arm not in {"typed_literal", "current_authority"}:
        raise ValueError(f"unknown arm: {arm}")
    if arm == "current_authority" and resolvers is None:
        raise ValueError("current_authority arm requires resolvers")
    rows = []
    literal_keys: dict[str, str] = {}
    for mention in mentions:
        entity_type = mention["entity_type"]
        expression = mention["expression_type"]
        base = {
            "mention_id": mention["mention_id"],
            "artifact_id": mention["artifact_id"],
            "museum": mention["museum"],
            "entity_type": entity_type,
        }
        if expression != "single_identity":
            result = {
                "status": "abstained", "reason": f"expression:{expression}",
                "resolution_method": None, "target_ids": [],
            }
        elif entity_type in OUT_OF_SCOPE:
            result = {
                "status": "abstained", "reason": f"authority_unavailable:{entity_type}",
                "resolution_method": None, "target_ids": [],
            }
        elif entity_type not in SCORED_ENTITY_TYPES:
            raise ValueError(f"unclassified entity type: {entity_type}")
        elif arm == "typed_literal":
            key = f"{entity_type}\x1f{surface_key(mention['mention_text'])}"
            target_id = "literal:" + hashlib.sha256(key.encode("utf-8")).hexdigest()
            previous = literal_keys.setdefault(target_id, key)
            if previous != key:
                raise ValueError("literal target SHA-256 collision")
            result = {
                "status": "resolved", "reason": None,
                "resolution_method": "typed_nfc_whitespace_casefold_literal_equality",
                "target_ids": [target_id],
            }
        else:
            resolver, norm_fn = resolvers[entity_type]
            resolution = resolver.resolve(mention["mention_text"], norm_fn)
            status = resolution["status"]
            result = {
                "status": status,
                "reason": None if status == "resolved" else f"authority_{status}",
                "resolution_method": resolution["resolution_method"],
                "target_ids": resolution["target_ids"],
                "raw_exact_status": resolution["raw_exact_status"],
            }
        rows.append({**base, **result})
    return rows


def build_links(resolutions: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, str, str], list[str]] = collections.defaultdict(list)
    for row in resolutions:
        if row["status"] != "resolved" or len(row["target_ids"]) != 1:
            continue
        key = (row["artifact_id"], row["museum"], row["entity_type"], row["target_ids"][0])
        grouped[key].append(row["mention_id"])
    return [
        {
            "artifact_id": key[0], "museum": key[1], "entity_type": key[2],
            "target_id": key[3], "mention_ids": sorted(ids),
        }
        for key, ids in sorted(grouped.items())
    ]


def ratio(numerator: int, denominator: int) -> dict:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def concentration(node_records: dict[str, dict[str, set[str]]], nodes: set[str], museum: str) -> dict:
    rows = [(target, node_records[target].get(museum, set())) for target in nodes]
    rows = [(target, records) for target, records in rows if records]
    rows.sort(key=lambda item: (-len(item[1]), item[0]))
    connected = set().union(*(records for _, records in rows)) if rows else set()
    top_k = {}
    for k in (1, 5, 10):
        selected = rows[:k]
        union = set().union(*(records for _, records in selected)) if selected else set()
        top_k[str(k)] = {
            "selected_target_ids": [target for target, _ in selected],
            "unique_record_union_ratio": ratio(len(union), len(connected)),
        }
    incidence_counts = [len(records) for _, records in rows]
    incidence_total = sum(incidence_counts)
    hhi_numerator = sum(value * value for value in incidence_counts)
    return {
        "distinct_connected_records": len(connected),
        "node_incidence_total": incidence_total,
        "node_incidence_hhi": ratio(hhi_numerator, incidence_total * incidence_total),
        "top_k": top_k,
    }


def resolution_outcomes(resolutions: list[dict]) -> dict:
    output = {}
    for museum in MUSEUMS:
        for entity in (*SCORED_ENTITY_TYPES, *OUT_OF_SCOPE):
            rows = [row for row in resolutions if row["museum"] == museum and row["entity_type"] == entity]
            status_counts = collections.Counter(row["status"] for row in rows)
            reason_counts = collections.Counter(row["reason"] for row in rows if row["reason"])
            records_by_status = {
                status: len({row["artifact_id"] for row in rows if row["status"] == status})
                for status in sorted(status_counts)
            }
            output[f"{museum}|{entity}"] = {
                "mentions": len(rows),
                "status_counts": dict(sorted(status_counts.items())),
                "reason_counts": dict(sorted(reason_counts.items())),
                "distinct_records_by_status": records_by_status,
            }
    return output


def arm_metrics(
    mentions: list[dict], resolutions: list[dict], links: list[dict], record_counts: dict[str, int]
) -> tuple[dict, dict]:
    node_records: dict[str, dict[str, set[str]]] = collections.defaultdict(lambda: collections.defaultdict(set))
    node_entity: dict[str, str] = {}
    node_links: dict[str, list[dict]] = collections.defaultdict(list)
    for link in links:
        target = link["target_id"]
        if target in node_entity and node_entity[target] != link["entity_type"]:
            raise ValueError(f"target reused across entity types: {target}")
        node_entity[target] = link["entity_type"]
        node_records[target][link["museum"]].add(link["artifact_id"])
        node_links[target].append(link)
    any_two_nodes = {target for target, sides in node_records.items() if len(sides) >= 2}
    all_three_nodes = {target for target, sides in node_records.items() if set(sides) == set(MUSEUMS)}
    pair_nodes = {
        "__".join(pair): {
            target for target, sides in node_records.items() if pair[0] in sides and pair[1] in sides
        }
        for pair in PAIRS
    }

    extracted_by_museum = {
        museum: {row["artifact_id"] for row in mentions if row["museum"] == museum}
        for museum in MUSEUMS
    }
    eligible_by_museum = {
        museum: {
            row["artifact_id"] for row in mentions
            if row["museum"] == museum and row["entity_type"] in SCORED_ENTITY_TYPES
            and row["expression_type"] == "single_identity"
        }
        for museum in MUSEUMS
    }
    linked_by_museum = {
        museum: {link["artifact_id"] for link in links if link["museum"] == museum}
        for museum in MUSEUMS
    }

    per_museum = {}
    any_two_records = {}
    all_three_records = {}
    for museum in MUSEUMS:
        shared_records = set().union(
            *(node_records[target].get(museum, set()) for target in any_two_nodes)
        ) if any_two_nodes else set()
        three_records = set().union(
            *(node_records[target].get(museum, set()) for target in all_three_nodes)
        ) if all_three_nodes else set()
        any_two_records[museum] = shared_records
        all_three_records[museum] = three_records
        by_entity = {}
        for entity in SCORED_ENTITY_TYPES:
            nodes = {target for target in any_two_nodes if node_entity[target] == entity}
            records = set().union(*(node_records[target].get(museum, set()) for target in nodes)) if nodes else set()
            by_entity[entity] = {"shared_useful_nodes_incident": len(nodes), "records_on_shared_useful_nodes": len(records)}
        per_museum[museum] = {
            "records_denominator": record_counts[museum],
            "records_with_extracted_mentions": len(extracted_by_museum[museum]),
            "records_with_score_eligible_single_identity_mentions": len(eligible_by_museum[museum]),
            "records_with_any_unique_link": len(linked_by_museum[museum]),
            "shared_useful_nodes_incident": len({target for target in any_two_nodes if museum in node_records[target]}),
            "records_on_any_two_museum_shared_useful_nodes": len(shared_records),
            "shared_record_rate_over_all_records": ratio(len(shared_records), record_counts[museum]),
            "shared_record_rate_over_eligible_records": ratio(len(shared_records), len(eligible_by_museum[museum])),
            "concentration_on_any_two_shared_nodes": concentration(node_records, any_two_nodes, museum),
            "by_entity_type": by_entity,
        }

    per_pair = {}
    pair_record_sets = {}
    for pair in PAIRS:
        key = "__".join(pair)
        nodes = pair_nodes[key]
        side_records = {
            museum: set().union(*(node_records[target][museum] for target in nodes)) if nodes else set()
            for museum in pair
        }
        pair_record_sets[key] = side_records
        per_pair[key] = {
            "shared_useful_node_count": len(nodes),
            "shared_useful_nodes_by_entity_type": dict(sorted(collections.Counter(node_entity[target] for target in nodes).items())),
            "records_by_museum_side": {museum: len(side_records[museum]) for museum in pair},
            "records_both_sides_sum": sum(len(value) for value in side_records.values()),
            "concentration_by_museum_side": {
                museum: concentration(node_records, nodes, museum) for museum in pair
            },
        }
    all_three = {
        "shared_useful_node_count": len(all_three_nodes),
        "shared_useful_nodes_by_entity_type": dict(sorted(collections.Counter(node_entity[target] for target in all_three_nodes).items())),
        "records_by_museum_side": {museum: len(all_three_records[museum]) for museum in MUSEUMS},
        "concentration_by_museum_side": {
            museum: concentration(node_records, all_three_nodes, museum) for museum in MUSEUMS
        },
    }
    public = {
        "links": len(links),
        "linked_nodes": len(node_records),
        "linked_records": len(set().union(*linked_by_museum.values())),
        "any_two_museum_shared_useful_nodes": len(any_two_nodes),
        "all_three_museum_shared_useful_nodes": len(all_three_nodes),
        "per_museum": per_museum,
        "per_pair": per_pair,
        "all_three": all_three,
        "resolution_outcomes": resolution_outcomes(resolutions),
    }
    private = {
        "node_records": node_records,
        "node_entity": node_entity,
        "node_links": node_links,
        "any_two_nodes": any_two_nodes,
        "all_three_nodes": all_three_nodes,
        "pair_nodes": pair_nodes,
        "any_two_records": any_two_records,
        "all_three_records": all_three_records,
        "pair_record_sets": pair_record_sets,
    }
    return public, private


def _transition_counts(
    source_nodes: set[str], source_state: dict, source_resolution: dict[str, dict],
    other_resolution: dict[str, dict], required_museums: tuple[str, ...],
    positive_label: str, negative_label: str,
) -> tuple[int, int, dict]:
    positive = 0
    negative = 0
    by_entity: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for target in source_nodes:
        support = source_state["node_links"][target]
        other_targets_by_museum = collections.defaultdict(set)
        for link in support:
            for mention_id in link["mention_ids"]:
                other = other_resolution[mention_id]
                if other["status"] == "resolved":
                    other_targets_by_museum[link["museum"]].update(other["target_ids"])
        common = None
        for museum in required_museums:
            values = other_targets_by_museum[museum]
            common = set(values) if common is None else common & values
        entity = source_state["node_entity"][target]
        if common:
            positive += 1
            by_entity[entity][positive_label] += 1
        else:
            negative += 1
            by_entity[entity][negative_label] += 1
    return positive, negative, {entity: dict(sorted(counts.items())) for entity, counts in sorted(by_entity.items())}


def node_transitions(literal_state: dict, authority_state: dict, literal_rows: list[dict], authority_rows: list[dict]) -> dict:
    literal_by_id = {row["mention_id"]: row for row in literal_rows}
    authority_by_id = {row["mention_id"]: row for row in authority_rows}

    def one_scope(literal_nodes: set[str], authority_nodes: set[str], museums: tuple[str, ...]) -> dict:
        preserved, lost, literal_entity = _transition_counts(
            literal_nodes, literal_state, literal_by_id, authority_by_id, museums,
            "preserved", "lost",
        )
        surface_supported, alias_gain, authority_entity = _transition_counts(
            authority_nodes, authority_state, authority_by_id, literal_by_id, museums,
            "surface_literal_supported", "cross_literal_authority_consolidation",
        )
        return {
            "literal_shared_nodes": len(literal_nodes),
            "literal_shared_nodes_preserved_by_one_common_authority_target": preserved,
            "literal_shared_nodes_lost_by_authority": lost,
            "authority_shared_nodes": len(authority_nodes),
            "authority_shared_nodes_with_one_common_surface_literal": surface_supported,
            "authority_shared_nodes_created_only_by_cross_literal_authority_consolidation": alias_gain,
            "literal_transition_by_entity_type": literal_entity,
            "authority_transition_by_entity_type": authority_entity,
        }

    per_pair = {}
    for pair in PAIRS:
        key = "__".join(pair)
        per_pair[key] = one_scope(literal_state["pair_nodes"][key], authority_state["pair_nodes"][key], pair)
    return {
        "per_pair": per_pair,
        "all_three": one_scope(
            literal_state["all_three_nodes"], authority_state["all_three_nodes"], MUSEUMS
        ),
    }


def literal_loss_cause(authority_support: list[dict], entity_type: str) -> str:
    statuses = {row["status"] for row in authority_support}
    if statuses == {"unmatched"}:
        return "absent_or_unmatched_authority_target"
    if statuses == {"ambiguous"}:
        if entity_type == "ruler" and all(len(row["target_ids"]) > 1 for row in authority_support):
            return "ambiguous_multiple_unmerged_claim_graph_units_for_same_literal"
        return "ambiguous_authority_target"
    if statuses <= {"ambiguous", "unmatched"}:
        return "mixed_ambiguous_and_unmatched_authority_target"
    if statuses == {"resolved"}:
        return "different_or_nonshared_unique_authority_targets"
    if "resolved" in statuses:
        return "partial_unique_resolution_without_common_authority_target"
    if statuses == {"abstained"}:
        reasons = {row["reason"] for row in authority_support}
        if all(reason and reason.startswith("authority_unavailable:") for reason in reasons):
            return "unavailable_authority_type"
        return "expression_abstention"
    raise ValueError(f"unclassified literal loss statuses: {sorted(statuses)}")


def literal_loss_attribution(
    literal_state: dict, authority_state: dict, authority_rows: list[dict]
) -> dict:
    authority_by_id = {row["mention_id"]: row for row in authority_rows}
    per_pair = {}
    for pair in PAIRS:
        key = "__".join(pair)
        node_counts: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
        supporting_records: dict[str, dict[str, dict[str, set[str]]]] = collections.defaultdict(
            lambda: collections.defaultdict(lambda: collections.defaultdict(set))
        )
        lost_record_memberships: dict[str, dict[str, dict[str, set[str]]]] = collections.defaultdict(
            lambda: collections.defaultdict(lambda: collections.defaultdict(set))
        )
        lost_records = {
            museum: literal_state["pair_record_sets"][key][museum]
            - authority_state["pair_record_sets"][key][museum]
            for museum in pair
        }
        classified_nodes = 0
        for target in literal_state["pair_nodes"][key]:
            links = [link for link in literal_state["node_links"][target] if link["museum"] in pair]
            authority_targets_by_side = collections.defaultdict(set)
            support_rows = []
            for link in links:
                for mention_id in link["mention_ids"]:
                    row = authority_by_id[mention_id]
                    support_rows.append(row)
                    if row["status"] == "resolved":
                        authority_targets_by_side[link["museum"]].update(row["target_ids"])
            if authority_targets_by_side[pair[0]] & authority_targets_by_side[pair[1]]:
                continue
            classified_nodes += 1
            entity = literal_state["node_entity"][target]
            cause = literal_loss_cause(support_rows, entity)
            if cause not in CLOSED_LITERAL_LOSS_CAUSES:
                raise ValueError(f"literal loss cause is outside the closed vocabulary: {cause}")
            node_counts[entity][cause] += 1
            for link in links:
                supporting_records[link["museum"]][entity][cause].add(link["artifact_id"])
                if link["artifact_id"] in lost_records[link["museum"]]:
                    lost_record_memberships[link["museum"]][entity][cause].add(link["artifact_id"])
        per_pair[key] = {
            "literal_only_shared_nodes": classified_nodes,
            "nodes_by_entity_type_and_closed_cause": {
                entity: dict(sorted(counts.items())) for entity, counts in sorted(node_counts.items())
            },
            "supporting_unique_records_by_museum_entity_and_cause": {
                museum: {
                    entity: {cause: len(records) for cause, records in sorted(causes.items())}
                    for entity, causes in sorted(entities.items())
                }
                for museum, entities in sorted(supporting_records.items())
            },
            "actually_lost_record_cause_memberships_nonexclusive": {
                museum: {
                    entity: {cause: len(records) for cause, records in sorted(causes.items())}
                    for entity, causes in sorted(entities.items())
                }
                for museum, entities in sorted(lost_record_memberships.items())
            },
            "actual_lost_records_by_museum": {
                museum: len(records) for museum, records in lost_records.items()
            },
        }
    unavailable = collections.Counter()
    expression_abstentions = collections.Counter()
    for row in authority_rows:
        reason = row["reason"]
        if row["status"] != "abstained" or reason is None:
            continue
        key = f"{row['museum']}|{row['entity_type']}"
        if reason.startswith("authority_unavailable:"):
            unavailable[key] += 1
        else:
            expression_abstentions[key] += 1
    return {
        "per_pair": per_pair,
        "unavailable_authority_type_mentions": dict(sorted(unavailable.items())),
        "expression_abstention_mentions": dict(sorted(expression_abstentions.items())),
        "notes": [
            "Node causes are mutually exclusive and sum to literal-only shared nodes for each pair.",
            "Actual lost-record cause memberships are nonexclusive because one record can support more than one lost node.",
            "Unavailable authority types and expression abstentions are reported separately; neither is treated as a wrong match.",
        ],
    }


def record_deltas(literal_state: dict, authority_state: dict) -> dict:
    per_pair = {}
    for pair in PAIRS:
        key = "__".join(pair)
        per_pair[key] = {}
        for museum in pair:
            literal = literal_state["pair_record_sets"][key][museum]
            authority = authority_state["pair_record_sets"][key][museum]
            per_pair[key][museum] = {
                "authority_gained_records": len(authority - literal),
                "authority_lost_records": len(literal - authority),
                "connected_in_both_arms": len(authority & literal),
                "net_authority_record_change": len(authority) - len(literal),
            }
    per_museum = {}
    for museum in MUSEUMS:
        literal = literal_state["any_two_records"][museum]
        authority = authority_state["any_two_records"][museum]
        per_museum[museum] = {
            "authority_gained_records": len(authority - literal),
            "authority_lost_records": len(literal - authority),
            "connected_in_both_arms": len(authority & literal),
            "net_authority_record_change": len(authority) - len(literal),
        }
    return {"per_museum_any_two": per_museum, "per_pair": per_pair}


def concentration_deltas(literal_metrics: dict, authority_metrics: dict) -> dict:
    output = {}
    for pair in PAIRS:
        key = "__".join(pair)
        output[key] = {}
        for museum in pair:
            literal = literal_metrics["per_pair"][key]["concentration_by_museum_side"][museum]
            authority = authority_metrics["per_pair"][key]["concentration_by_museum_side"][museum]
            output[key][museum] = {
                "node_incidence_hhi_authority_minus_literal": (
                    authority["node_incidence_hhi"]["value"] - literal["node_incidence_hhi"]["value"]
                    if authority["node_incidence_hhi"]["value"] is not None and literal["node_incidence_hhi"]["value"] is not None
                    else None
                ),
                "top_k_unique_record_ratio_authority_minus_literal": {
                    k: (
                        authority["top_k"][k]["unique_record_union_ratio"]["value"]
                        - literal["top_k"][k]["unique_record_union_ratio"]["value"]
                    )
                    for k in ("1", "5", "10")
                },
            }
    return output


def compare(
    repo_root: Path, ledger_path: Path, extraction_manifest_path: Path, out: Path,
    public_out: Path | None = None,
) -> tuple[dict, dict]:
    extraction_manifest = json.loads(extraction_manifest_path.read_text(encoding="utf-8"))
    if extraction_manifest["independence_contract"]["authority_labels_aliases_ids_consulted"] is not False:
        raise ValueError("mention extraction manifest does not assert authority independence")
    extractor_path = repo_root / "docs/evaluations/authority-independent-control-2026-09-13/scripts/extract_mentions.py"
    if sha256_path(extractor_path) != extraction_manifest["extractor_sha256"]:
        raise ValueError("extractor changed after the mention ledger was frozen")
    mentions, ledger_proof = read_ledger(ledger_path, extraction_manifest)
    _module, resolvers, catalogs = load_current_resolvers(repo_root)

    literal_rows = resolve_mentions(mentions, "typed_literal")
    authority_rows = resolve_mentions(mentions, "current_authority", resolvers)
    literal_ids = [row["mention_id"] for row in literal_rows]
    authority_ids = [row["mention_id"] for row in authority_rows]
    source_ids = [row["mention_id"] for row in mentions]
    if literal_ids != source_ids or authority_ids != source_ids:
        raise ValueError("the two arms did not consume the identical ordered mention ledger")

    out.mkdir(parents=True, exist_ok=True)
    literal_arm_info = write_gzip_rows(out / "typed-literal-arm.ndjson.gz", literal_rows)
    authority_arm_info = write_gzip_rows(out / "current-authority-arm.ndjson.gz", authority_rows)
    literal_links = build_links(literal_rows)
    authority_links = build_links(authority_rows)
    write_gzip_rows(out / "typed-literal-links.ndjson.gz", literal_links, id_field=None)
    write_gzip_rows(out / "current-authority-links.ndjson.gz", authority_links, id_field=None)

    record_counts = extraction_manifest["archive"]["canonical_counts"]
    literal_metrics, literal_state = arm_metrics(mentions, literal_rows, literal_links, record_counts)
    authority_metrics, authority_state = arm_metrics(mentions, authority_rows, authority_links, record_counts)
    record_delta = record_deltas(literal_state, authority_state)
    transitions = node_transitions(literal_state, authority_state, literal_rows, authority_rows)
    loss_attribution = literal_loss_attribution(literal_state, authority_state, authority_rows)
    for pair_key, attribution in loss_attribution["per_pair"].items():
        expected = transitions["per_pair"][pair_key]["literal_shared_nodes_lost_by_authority"]
        if attribution["literal_only_shared_nodes"] != expected:
            raise ValueError(f"literal loss attribution is incomplete for {pair_key}")
    proof = {
        "identical_ordered_mentions": True,
        "mention_ledger": ledger_proof,
        "typed_literal_arm": literal_arm_info,
        "current_authority_arm": authority_arm_info,
        "arm_row_counts_equal": literal_arm_info["rows"] == authority_arm_info["rows"] == ledger_proof["rows"],
        "arm_ordered_mention_ids_equal": (
            literal_arm_info["ordered_mention_ids_sha256"]
            == authority_arm_info["ordered_mention_ids_sha256"]
            == ledger_proof["ordered_mention_ids_sha256"]
        ),
        "all_mention_spans_revalidated": True,
    }
    if not proof["arm_row_counts_equal"] or not proof["arm_ordered_mention_ids_equal"]:
        raise ValueError("arm mention membership proof failed")

    report = {
        "schema_version": "hapi-authority-independent-control-report/1",
        "question": "Does the frozen archived disposable authority adapter improve cross-museum matching over typed surface-literal equality on identical mentions?",
        "definitions": {
            "typed_literal_node": "entity type + NFC/casefolded/whitespace-collapsed mention text; punctuation and diacritics are retained",
            "shared_useful_node": "a score-eligible ruler/site/tomb node with at least one uniquely linked record on every museum side in the stated pair; this is matching utility, not accuracy or specificity",
            "shared_record": "a record incident to at least one shared useful node; deduplicated within each museum side",
            "authority_gain_node": "an authority shared node for which no one typed surface literal spans the same museum sides",
            "literal_node_loss": "a shared typed literal node whose supporting mentions do not resolve to one common authority target across those museum sides",
            "loss_cause": "a mutually exclusive resolver-outcome class for each literal-only shared node; record cause memberships are explicitly nonexclusive",
            "closed_literal_loss_cause_vocabulary": CLOSED_LITERAL_LOSS_CAUSES,
            "out_of_scope": OUT_OF_SCOPE,
        },
        "scope": {
            "evaluation_date": EVALUATION_DATE,
            "corpus_snapshot_date": extraction_manifest["archive"]["snapshot_date"],
            "base_commit": BASE_COMMIT,
            "tested_resolver": "archived disposable non-production linkability adapter",
            "production_enrichment_implemented": False,
            "site_input_status": "archived filtered iDAI rows used as raw, unclosed curation-source data; not a production canonical site graph",
            "conclusion_scope": "this adapter and committed authority-inventory snapshot only",
            "canonical_records": sum(record_counts.values()),
            "records_by_museum": record_counts,
            "scored_entity_types": SCORED_ENTITY_TYPES,
            "unavailable_entity_types_invented_as_nodes": False,
        },
        "headline": {
            "typed_literal_any_two_shared_nodes": literal_metrics["any_two_museum_shared_useful_nodes"],
            "current_authority_any_two_shared_nodes": authority_metrics["any_two_museum_shared_useful_nodes"],
            "typed_literal_shared_records_by_museum": {
                museum: literal_metrics["per_museum"][museum]["records_on_any_two_museum_shared_useful_nodes"]
                for museum in MUSEUMS
            },
            "current_authority_shared_records_by_museum": {
                museum: authority_metrics["per_museum"][museum]["records_on_any_two_museum_shared_useful_nodes"]
                for museum in MUSEUMS
            },
            "net_authority_shared_record_change_by_museum": {
                museum: record_delta["per_museum_any_two"][museum]["net_authority_record_change"]
                for museum in MUSEUMS
            },
            "authority_improves_any_two_shared_record_coverage_for_any_museum": any(
                record_delta["per_museum_any_two"][museum]["net_authority_record_change"] > 0
                for museum in MUSEUMS
            ),
            "authority_cross_literal_shared_node_gains_by_pair": {
                key: value["authority_shared_nodes_created_only_by_cross_literal_authority_consolidation"]
                for key, value in transitions["per_pair"].items()
            },
        },
        "identical_mentions_proof": proof,
        "arms": {"typed_literal": literal_metrics, "current_authority": authority_metrics},
        "comparison": {
            "record_gains_and_losses": record_delta,
            "shared_node_transitions": transitions,
            "literal_loss_attribution": loss_attribution,
            "concentration_deltas": concentration_deltas(literal_metrics, authority_metrics),
        },
        "authority_target_counts": {entity: len(catalog) for entity, catalog in catalogs.items()},
        "limitations": [
            "This measures deterministic matching/linkability, not correctness, precision, recall, or scholarly usefulness.",
            "The tested resolver is an archived disposable evaluation adapter; production enrichment is unimplemented.",
            "The site targets are archived filtered iDAI rows used as raw, unclosed curation-source data rather than a production canonical site graph.",
            "The literal arm is deliberately conservative: it does not collapse punctuation, spelling, transliteration, or aliases.",
            "Generic and broad place strings are not hand-filtered; per-side concentration exposes their effect.",
            "Free-text ruler extraction is limited to explicit royal cues and at most three syntactically bounded name tokens.",
            "Location parsing is bounded to top-level comma/semicolon components and one leading pre-parenthesis child; it is not a general nested-prose parser.",
            "Within any location variant, the word temple takes type precedence and suppresses site scoring for that variant; a separately emitted pre-parenthesis child may still be a site.",
            "Tomb extraction is limited to explicit KV/QV/TT/Tomb-code syntax; authority-recognized free-text aliases cannot cause mention emission.",
            "Temple and excavation evidence is inventoried but excluded because no committed canonical authority exists for either type.",
            "The archive proves the frozen snapshot, not upstream database regeneration or current museum API state.",
        ],
    }
    write_json(out / "report.json", report)

    output_names = (
        "typed-literal-arm.ndjson.gz", "current-authority-arm.ndjson.gz",
        "typed-literal-links.ndjson.gz", "current-authority-links.ndjson.gz", "report.json",
    )
    manifest = {
        "schema_version": "hapi-authority-independent-control-run/1",
        "base_commit": BASE_COMMIT,
        "inputs": {
            "corpus_archive": extraction_manifest["archive"],
            "mention_ledger": ledger_proof,
            "extraction_manifest_sha256": sha256_path(extraction_manifest_path),
            "current_resolver_inputs_sha256": dict(sorted(CURRENT_INPUTS.items())),
            "compare_arms_sha256": sha256_path(Path(__file__)),
        },
        "outputs_sha256": {name: sha256_path(out / name) for name in output_names},
        "identical_mentions_proof": proof,
    }
    write_json(out / "run-manifest.json", manifest)
    checksum_paths = {
        "mentions.ndjson.gz": ledger_path,
        "extraction-manifest.json": extraction_manifest_path,
        **{name: out / name for name in (*output_names, "run-manifest.json")},
    }
    checksums = "".join(f"{sha256_path(path)}  {name}\n" for name, path in sorted(checksum_paths.items()))
    (out / "SHA256SUMS").write_text(checksums, encoding="utf-8")
    if public_out is not None:
        write_json(public_out / "real-run-report.json", report)
        write_json(public_out / "real-run-manifest.json", manifest)
        public_out.mkdir(parents=True, exist_ok=True)
        (public_out / "real-run-private-output-SHA256SUMS").write_text(checksums, encoding="utf-8")
    return report, manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--extraction-manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--public-out", type=Path)
    args = parser.parse_args()
    report, manifest = compare(
        args.repo_root.resolve(), args.ledger, args.extraction_manifest, args.out, args.public_out
    )
    print(json.dumps({
        "mention_ledger_sha256": manifest["inputs"]["mention_ledger"]["gzip_sha256"],
        "typed_literal": {
            "shared_nodes": report["arms"]["typed_literal"]["any_two_museum_shared_useful_nodes"],
            "shared_records_by_museum": {
                museum: report["arms"]["typed_literal"]["per_museum"][museum]["records_on_any_two_museum_shared_useful_nodes"]
                for museum in MUSEUMS
            },
        },
        "current_authority": {
            "shared_nodes": report["arms"]["current_authority"]["any_two_museum_shared_useful_nodes"],
            "shared_records_by_museum": {
                museum: report["arms"]["current_authority"]["per_museum"][museum]["records_on_any_two_museum_shared_useful_nodes"]
                for museum in MUSEUMS
            },
        },
    }, indent=2))


if __name__ == "__main__":
    main()
