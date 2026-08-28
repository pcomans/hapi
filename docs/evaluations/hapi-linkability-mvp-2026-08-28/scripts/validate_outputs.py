#!/usr/bin/env python3
"""Deterministically rerun and validate the real-corpus linkability MVP outputs."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
from pathlib import Path


OUT = Path(os.environ.get("HAPI_EVAL_OUT", "/tmp/hapi-linkability-mvp"))
ROOT = Path(os.environ.get("HAPI_ROOT", "/workspaces/content"))
AUTH = ROOT / "pipeline" / "pipeline" / "authority" / "sources"
GRAPH = ROOT / "web-claimgraph" / "data" / "claim-graph.json"

GENERATED = [
    "corpus_inventory.json",
    "authority_inventory.json",
    "adapter_catalog_summary.json",
    "mentions.ndjson.gz",
    "artifact_authority_links.ndjson.gz",
    "linkability_metrics.json",
    "connectivity_metrics.json",
    "authority_node_connectivity.json",
    "top_gaps.json",
    "review_sample.json",
    "review_sample.csv",
    "review_sample_manifest.json",
    "review_adjudications.json",
    "review_adjudications.csv",
    "review_metrics.json",
    "web_search_log.json",
    "field_provenance_metrics.json",
    "artifact_link_coverage.json",
    "connectivity_detail.json",
    "silver_false_link_sensitivity.json",
]

COMMANDS = [
    "inventory_inputs.py",
    "run_linkability.py",
    "freeze_review_sample.py",
    "adjudicate_review.py",
    "summarize_evaluation.py",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_gzip_jsonl(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def current_target_ids() -> set[str]:
    graph = read_json(GRAPH)
    clustered_members = {member for cluster in graph["clusters"] for member in cluster["member_ids"]}
    targets = {cluster["id"] for cluster in graph["clusters"]}
    targets.update(row["id"] for row in graph["rulers"] if row["id"] not in clustered_members)

    for row in read_jsonl(AUTH / "idai-gazetteer" / "reconciled.jsonl"):
        if row.get("kind") == "site":
            # The committed row already stores the namespaced identifier.
            targets.add(row["id"])
    for namespace, relative in (
        ("pm_theban", "porter-moss-theban-necropolis/reconciled.jsonl"),
        ("pm_memphis", "porter-moss-memphis/reconciled.jsonl"),
    ):
        targets.update(f"{namespace}:{row['tomb_id']}" for row in read_jsonl(AUTH / relative))
    return targets


def write_checksums() -> None:
    files = sorted(
        path for path in OUT.rglob("*")
        if path.is_file()
        and path.name != "SHA256SUMS"
        and not path.name.startswith(".")
        and "__pycache__" not in path.parts
    )
    content = "".join(f"{sha256(path)}  {path.relative_to(OUT)}\n" for path in files)
    (OUT / "SHA256SUMS").write_text(content, encoding="utf-8")


def main() -> None:
    checks: list[dict] = []

    def check(name: str, condition: bool, evidence) -> None:
        checks.append({"check": name, "passed": bool(condition), "evidence": evidence})

    missing_before = [name for name in GENERATED if not (OUT / name).is_file()]
    check("all expected generated outputs exist before rerun", not missing_before, {"missing": missing_before})
    hashes_before = {name: sha256(OUT / name) for name in GENERATED if (OUT / name).is_file()}

    command_results = []
    for script in COMMANDS:
        result = subprocess.run(
            ["python3", str(OUT / "scripts" / script)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        command_results.append({
            "script": script,
            "returncode": result.returncode,
            "stdout_sha256": hashlib.sha256(result.stdout.encode("utf-8")).hexdigest(),
            "stderr": result.stderr[-2000:],
        })
    check("all deterministic generation commands succeeded", all(row["returncode"] == 0 for row in command_results), command_results)

    missing_after = [name for name in GENERATED if not (OUT / name).is_file()]
    hashes_after = {name: sha256(OUT / name) for name in GENERATED if (OUT / name).is_file()}
    changed = [name for name in GENERATED if hashes_before.get(name) != hashes_after.get(name)]
    check("clean rerun is byte-for-byte deterministic", not missing_after and not changed, {"missing": missing_after, "changed": changed})

    corpus = read_json(OUT / "corpus_inventory.json")
    check(
        "verified canonical and raw corpus counts",
        corpus["canonical_rows"] == 36245
        and corpus["canonical_by_museum"] == {"brooklyn": 7554, "harvard": 722, "met": 27969}
        and corpus["raw_rows"] == 37523
        and corpus["canonical_linked_raw_by_museum"] == {"brooklyn": 7554, "harvard": 722, "met": 27969},
        {
            "canonical_rows": corpus["canonical_rows"],
            "canonical_by_museum": corpus["canonical_by_museum"],
            "raw_rows": corpus["raw_rows"],
            "canonical_linked_raw_by_museum": corpus["canonical_linked_raw_by_museum"],
        },
    )

    inventory = read_json(OUT / "authority_inventory.json")
    check(
        "authority inventory represents current targets and preserves hard blockers",
        inventory["ruler"]["canonical_units_for_this_adapter"] == 974
        and inventory["site"]["site_rows"] == 1000
        and inventory["site"]["site_graph_exists"] is False
        and inventory["tomb_monument"]["sources"]["pm_theban"]["rows"] == 484
        and inventory["tomb_monument"]["sources"]["pm_memphis"]["rows"] == 873
        and inventory["temple"]["dedicated_current_authority"] is False
        and inventory["excavation"]["dedicated_current_authority"] is False,
        {
            "ruler_units": inventory["ruler"]["canonical_units_for_this_adapter"],
            "site_rows": inventory["site"]["site_rows"],
            "site_graph_exists": inventory["site"]["site_graph_exists"],
            "temple_authority": inventory["temple"]["dedicated_current_authority"],
            "excavation_authority": inventory["excavation"]["dedicated_current_authority"],
        },
    )

    mentions = read_gzip_jsonl(OUT / "mentions.ndjson.gz")
    links = read_gzip_jsonl(OUT / "artifact_authority_links.ndjson.gz")
    check("full mention and link counts", len(mentions) == 150428 and len(links) == 43930, {"mentions": len(mentions), "links": len(links)})

    bad_spans = [
        row["mention_id"] for row in mentions
        if row["span_start"] < 0
        or row["span_end"] < row["span_start"]
        or row["span_end"] > len(row["field_value"])
        or row["field_value"][row["span_start"]:row["span_end"]] != row["mention_text"]
    ]
    check("every mention has an exact valid field span", not bad_spans, {"bad_span_count": len(bad_spans), "examples": bad_spans[:10]})

    target_ids = current_target_ids()
    bad_resolution_shapes = [
        row["mention_id"] for row in mentions
        if (row["status"] == "resolved" and len(row["target_ids"]) != 1)
        or (row["status"] == "ambiguous" and len(row["target_ids"]) < 2)
        or (row["status"] not in {"resolved", "ambiguous"} and row["target_ids"])
        or any(target not in target_ids for target in row["target_ids"])
    ]
    check("resolution cardinalities and target IDs are valid", not bad_resolution_shapes, {"bad_count": len(bad_resolution_shapes), "examples": bad_resolution_shapes[:10]})

    mention_by_id = {row["mention_id"]: row for row in mentions}
    link_keys = [(row["artifact_id"], row["entity_type"], row["target_id"]) for row in links]
    bad_links = []
    for row in links:
        if row["target_id"] not in target_ids or not row["mention_ids"]:
            bad_links.append(row)
            continue
        for mention_id in row["mention_ids"]:
            mention = mention_by_id.get(mention_id)
            if (
                mention is None
                or mention["artifact_id"] != row["artifact_id"]
                or mention["entity_type"] != row["entity_type"]
                or mention["status"] != "resolved"
                or mention["target_ids"] != [row["target_id"]]
            ):
                bad_links.append(row)
                break
    check(
        "artifact-node links are unique and trace to resolved mentions",
        len(link_keys) == len(set(link_keys)) and not bad_links,
        {"duplicate_keys": len(link_keys) - len(set(link_keys)), "bad_link_count": len(bad_links)},
    )

    connectivity = read_json(OUT / "connectivity_metrics.json")
    detail = read_json(OUT / "connectivity_detail.json")
    check(
        "connectivity invariants match recomputed summary",
        connectivity["artifact_node_links"] == len(links)
        and connectivity["linked_artifacts"] == 17063
        and connectivity["linked_nodes"] == 280
        and connectivity["nodes_linked_from_at_least_two_museums"] == 56
        and connectivity["artifacts_on_shared_nodes_newly_cross_museum_discoverable"] == 15595
        and detail["base_metrics_recomputed"]["shared_nodes"] == 56
        and detail["three_museum_shared_nodes"] == 3,
        {"connectivity_metrics": connectivity, "three_museum_shared_nodes": detail["three_museum_shared_nodes"]},
    )

    sample = read_json(OUT / "review_sample.json")
    sample_manifest = read_json(OUT / "review_sample_manifest.json")
    adjudications = read_json(OUT / "review_adjudications.json")
    review_metrics = read_json(OUT / "review_metrics.json")
    sample_ids = [row["sample_id"] for row in sample]
    adjudication_ids = [row["sample_id"] for row in adjudications]
    check(
        "frozen sample and adjudication coverage are complete",
        len(sample) == 46
        and len(set(sample_ids)) == 46
        and sample_ids == adjudication_ids
        and sample_manifest["input_sha256"] == sha256(OUT / "mentions.ndjson.gz")
        and review_metrics["sample_sha256"] == sha256(OUT / "review_sample.json"),
        {
            "sample_size": len(sample),
            "adjudication_size": len(adjudications),
            "sample_input_sha256": sample_manifest["input_sha256"],
        },
    )

    bad_citations = []
    bad_accepted_targets = []
    for row in adjudications:
        citations = row.get("citations", [])
        if not citations or any(not citation.get("url", "").startswith(("https://", "http://")) for citation in citations):
            bad_citations.append(row["sample_id"])
        if any(target not in target_ids for target in row.get("accepted_target_ids", [])):
            bad_accepted_targets.append(row["sample_id"])
    check(
        "all SILVER cases carry direct URL citations and accepted IDs are current targets",
        not bad_citations and not bad_accepted_targets,
        {"bad_citations": bad_citations, "bad_accepted_targets": bad_accepted_targets},
    )
    check(
        "review remains explicitly provisional and does not report recall or estimated precision",
        all("PROVISIONAL SILVER" in row["label"] for row in adjudications)
        and review_metrics["recall"]["reported"] is False
        and review_metrics["sampled_resolved_support"]["not_an_estimated_precision"] is True,
        {
            "label": review_metrics["label"],
            "recall": review_metrics["recall"],
            "not_an_estimated_precision": review_metrics["sampled_resolved_support"]["not_an_estimated_precision"],
        },
    )

    adapter_source = (OUT / "scripts" / "run_linkability.py").read_text(encoding="utf-8")
    check(
        "resolver has no adjudication-file dependency",
        "review_adjudications" not in adapter_source and "web_search_log" not in adapter_source,
        {"forbidden_dependency_strings_present": [term for term in ("review_adjudications", "web_search_log") if term in adapter_source]},
    )

    gzip_mtime = {}
    for name in ("mentions.ndjson.gz", "artifact_authority_links.ndjson.gz"):
        data = (OUT / name).read_bytes()[:10]
        gzip_mtime[name] = int.from_bytes(data[4:8], "little")
    check("gzip outputs use deterministic zero mtime", all(value == 0 for value in gzip_mtime.values()), gzip_mtime)

    report = {
        "status": "pass" if all(row["passed"] for row in checks) else "fail",
        "scope": "real 36,245-record canonical corpus plus linked raw museum payloads; no fixtures or proxies",
        "rerun_commands": command_results,
        "generated_hashes_before_rerun": hashes_before,
        "generated_hashes_after_rerun": hashes_after,
        "checks": checks,
        "summary": {
            "checks": len(checks),
            "passed": sum(row["passed"] for row in checks),
            "failed": sum(not row["passed"] for row in checks),
            "canonical_records": corpus["canonical_rows"],
            "mentions": len(mentions),
            "artifact_node_links": len(links),
            "review_cases": len(adjudications),
        },
    }
    (OUT / "validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_checksums()
    print(json.dumps(report["summary"] | {"status": report["status"]}, sort_keys=True))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
