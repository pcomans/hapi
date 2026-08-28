#!/usr/bin/env python3
"""Audit real corpus/raw evidence fields and the actually committed authority targets."""

from __future__ import annotations

import collections
import gzip
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(os.environ.get("HAPI_ROOT", "/workspaces/content"))
CORPUS = Path(os.environ.get("HAPI_CORPUS", "/tmp/hapi-corpus-2026-08-27"))
OUT = Path(os.environ.get("HAPI_EVAL_OUT", "/tmp/hapi-linkability-mvp"))
AUTH = ROOT / "pipeline" / "pipeline" / "authority"
GRAPH = ROOT / "web-claimgraph" / "data" / "claim-graph.json"
IDAI = AUTH / "sources" / "idai-gazetteer" / "reconciled.jsonl"
PM_THEBAN = AUTH / "sources" / "porter-moss-theban-necropolis" / "reconciled.jsonl"
PM_MEMPHIS = AUTH / "sources" / "porter-moss-memphis" / "reconciled.jsonl"

RULER_CUE = re.compile(r"\b(?:reigns?|pontificat(?:e|ion)|pharaoh|king|queen|ruler)\b", re.I)
SITE_CUE = re.compile(r"\b(?:from|findspot|found|excavat\w*|provenance|made in|tomb|temple|cemetery|necropolis|pyramid|site)\b", re.I)
TOMB_CODE = re.compile(r"\b(?:KV|QV|TT)\s*\d+[A-Za-z]?\b|\bTomb\s+[A-Z]{1,4}[ .-]?\d+[A-Za-z]?\b", re.I)

FIELD_POLICY = {
    "met": {
        "ruler_structured": ["reign"],
        "ruler_text": ["title", "objectDate", "locale", "locus"],
        "site_structured": ["country", "region", "subregion", "locale", "locus", "excavation"],
        "site_text": ["title"],
        "role_fields": ["geographyType"],
    },
    "brooklyn": {
        "ruler_structured": [],
        "ruler_text": ["title", "description", "inscribed", "dates", "objectDate", "provenance"],
        "site_structured": ["geographicalLocations"],
        "site_text": ["title", "description", "provenance"],
        "role_fields": ["geographicalLocations[].type"],
    },
    "harvard": {
        "ruler_structured": [],
        "ruler_text": ["title", "description", "labeltext", "commentary", "dated", "contextualtext"],
        "site_structured": ["places"],
        "site_text": ["title", "description", "labeltext", "commentary", "provenance", "contextualtext"],
        "role_fields": ["places[].type"],
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_gzip(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def strings(value, prefix: str):
    if isinstance(value, str):
        if value.strip():
            yield prefix, value
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from strings(child, f"{prefix}[{i}]")
    elif isinstance(value, dict):
        for key in sorted(value):
            yield from strings(value[key], f"{prefix}.{key}")


def field_stats(rows: list[dict], fields: list[str], cue: re.Pattern[str]) -> dict:
    output = {}
    for field in fields:
        base = field.split("[]", 1)[0]
        records_nonempty = records_with_cue = spans_with_cue = string_values = 0
        samples = []
        for row in rows:
            values = list(strings(row.get(base), base))
            if values:
                records_nonempty += 1
            row_hit = False
            for path, text in values:
                string_values += 1
                hits = list(cue.finditer(text))
                spans_with_cue += len(hits)
                if hits:
                    row_hit = True
                    if len(samples) < 5:
                        samples.append({"path": path, "text": text[:500], "cue_spans": [[m.start(), m.end()] for m in hits[:5]]})
            records_with_cue += row_hit
        output[field] = {
            "records_nonempty": records_nonempty,
            "string_values": string_values,
            "records_with_domain_cue": records_with_cue,
            "domain_cue_spans": spans_with_cue,
            "examples": samples,
        }
    return output


def tracked(path: Path) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path.relative_to(ROOT))],
        cwd=ROOT, capture_output=True, text=True,
    )
    return result.returncode == 0


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    canonical = read_gzip(CORPUS / "data" / "artifacts.ndjson.gz")
    raw_all = {
        museum: read_gzip(CORPUS / "data" / f"raw_{museum}.ndjson.gz")
        for museum in ("met", "brooklyn", "harvard")
    }
    raw_by_key = {
        museum: {row["object_id"]: row["data"] for row in rows}
        for museum, rows in raw_all.items()
    }
    if any(len(index) != len(raw_all[museum]) for museum, index in raw_by_key.items()):
        raise RuntimeError("duplicate raw object_id")
    canonical_by_museum: dict[str, list[dict]] = collections.defaultdict(list)
    linked_raw: dict[str, list[dict]] = collections.defaultdict(list)
    for row in canonical:
        museum = row["source_museum"]
        canonical_by_museum[museum].append(row)
        try:
            linked_raw[museum].append(raw_by_key[museum][row["source_id"]])
        except KeyError as exc:
            raise RuntimeError(f"canonical row lacks raw payload: {museum}/{row['source_id']}") from exc

    corpus_inventory = {
        "status": "verified real corpus and linked raw payload inventory; no fixtures/proxies",
        "canonical_rows": len(canonical),
        "canonical_by_museum": {k: len(v) for k, v in sorted(canonical_by_museum.items())},
        "raw_rows": sum(len(v) for v in raw_all.values()),
        "raw_by_museum": {k: len(v) for k, v in raw_all.items()},
        "canonical_linked_raw_by_museum": {k: len(v) for k, v in sorted(linked_raw.items())},
        "raw_only_rows_by_museum": {
            museum: len(raw_all[museum]) - len(linked_raw[museum]) for museum in raw_all
        },
        "canonical_sha256": sha256(CORPUS / "data" / "artifacts.ndjson.gz"),
        "canonical_fields": sorted(canonical[0]),
        "canonical_authority_field_coverage": {
            museum: {
                field: sum(row[field] not in (None, "", []) for row in rows)
                for field in ("ruler_display_name", "ruler_id", "origin_site_raw", "origin_site_id", "tomb_temple_id", "excavation_id")
            }
            for museum, rows in sorted(canonical_by_museum.items())
        },
        "raw_evidence_fields": {},
    }
    for museum, rows in sorted(linked_raw.items()):
        policy = FIELD_POLICY[museum]
        corpus_inventory["raw_evidence_fields"][museum] = {
            "policy": policy,
            "ruler_structured": field_stats(rows, policy["ruler_structured"], RULER_CUE),
            "ruler_text": field_stats(rows, policy["ruler_text"], RULER_CUE),
            "site_structured": field_stats(rows, policy["site_structured"], SITE_CUE),
            "site_text": field_stats(rows, policy["site_text"], SITE_CUE),
            "records_with_explicit_tomb_code_any_policy_field": sum(
                any(TOMB_CODE.search(text) for field in set(policy["ruler_text"] + policy["site_structured"] + policy["site_text"])
                    for _, text in strings(row.get(field.split("[]", 1)[0]), field.split("[]", 1)[0]))
                for row in rows
            ),
        }
        if museum == "met":
            corpus_inventory["raw_evidence_fields"][museum]["structured_role_counts"] = dict(
                collections.Counter(row.get("geographyType") for row in rows if row.get("geographyType")).most_common()
            )
        elif museum == "brooklyn":
            corpus_inventory["raw_evidence_fields"][museum]["structured_role_counts"] = dict(
                collections.Counter(
                    place.get("type") for row in rows for place in (row.get("geographicalLocations") or [])
                    if place and place.get("type")
                ).most_common()
            )
        else:
            corpus_inventory["raw_evidence_fields"][museum]["structured_role_counts"] = dict(
                collections.Counter(
                    place.get("type") for row in rows for place in (row.get("places") or [])
                    if place and place.get("type")
                ).most_common()
            )

    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    clustered = {member for cluster in graph["clusters"] for member in cluster["member_ids"]}
    if len(clustered) != sum(len(cluster["member_ids"]) for cluster in graph["clusters"]):
        raise RuntimeError("ruler belongs to multiple graph clusters")
    idai_rows = jsonl(IDAI)
    source_rows = [row for row in idai_rows if row.get("_source")]
    sites = [row for row in idai_rows if row.get("kind") == "site"]
    if len(source_rows) != 1 or len(sites) + 1 != len(idai_rows):
        raise RuntimeError("unexpected iDAI source/row shape")
    pm_rows = {"pm_theban": jsonl(PM_THEBAN), "pm_memphis": jsonl(PM_MEMPHIS)}
    pm_ids = {}
    for source, rows in pm_rows.items():
        ids = [row["tomb_id"] for row in rows]
        if len(ids) != len(set(ids)):
            raise RuntimeError(f"duplicate {source} tomb_id")
        pm_ids[source] = ids

    site_label_counts = collections.Counter(
        label.casefold().strip() for row in sites for label in [row["display"], *row["alt_labels"]] if label.strip()
    )
    authority_inventory = {
        "status": "actual current committed targets only",
        "ruler": {
            "representation": "current claim-graph cluster or singleton source-node unit",
            "path": str(GRAPH),
            "git_tracked": tracked(GRAPH),
            "sha256": sha256(GRAPH),
            "source_nodes": len(graph["rulers"]),
            "approved_clusters": len(graph["clusters"]),
            "clustered_source_nodes": len(clustered),
            "singleton_source_nodes": len(graph["rulers"]) - len(clustered),
            "canonical_units_for_this_adapter": len(graph["clusters"]) + len(graph["rulers"]) - len(clustered),
            "claims": len(graph["claims"]),
            "name_claims": sum(c["predicate"] in {"hapi:display_name", "hapi:prenomen", "hapi:horus_name", "hapi:nomen"} for c in graph["claims"]),
            "sources": graph["meta"]["sources"],
        },
        "site": {
            "representation": "iDAI reconciled source rows; no consolidated current site graph or curated sites.json exists",
            "path": str(IDAI),
            "git_tracked": tracked(IDAI),
            "sha256": sha256(IDAI),
            "site_rows": len(sites),
            "unique_ids": len({row["id"] for row in sites}),
            "display_and_alias_labels": sum(1 + len(row["alt_labels"]) for row in sites),
            "casefold_label_collisions": sum(count > 1 for count in site_label_counts.values()),
            "type_counts": dict(collections.Counter(t for row in sites for t in row["types"]).most_common()),
            "parents_resolved_in_file": sum(row["parent_in_file"] is True for row in sites),
            "parents_outside_filtered_file": sum(row["parent_in_file"] is False for row in sites),
            "curated_sites_json_exists": (AUTH / "sites.json").exists(),
            "site_graph_exists": False,
            "adapter_target_policy": "Use exact iDAI ids as closest committed site targets; do not invent a hierarchy or canonical merge.",
        },
        "tomb_monument": {
            "representation": "two separate Porter-Moss reconciled source registers; no consolidated tomb/site graph",
            "sources": {
                source: {
                    "path": str(PM_THEBAN if source == "pm_theban" else PM_MEMPHIS),
                    "git_tracked": tracked(PM_THEBAN if source == "pm_theban" else PM_MEMPHIS),
                    "sha256": sha256(PM_THEBAN if source == "pm_theban" else PM_MEMPHIS),
                    "rows": len(rows),
                    "unique_tomb_ids": len(set(pm_ids[source])),
                    "prefix_counts": dict(collections.Counter((re.match(r"[A-Za-z]+", value) or ["other"])[0] for value in pm_ids[source]).most_common()),
                    "rows_with_tomb_aliases": sum(bool(row["tomb_aliases"]) for row in rows),
                }
                for source, rows in pm_rows.items()
            },
            "adapter_target_policy": "Namespace exact current tomb_id rows by PM source; treat as tomb/monument targets, not as a fabricated unified site graph.",
        },
        "temple": {
            "dedicated_current_authority": False,
            "status": "hard blocked for a comprehensive temple-node linkability conclusion; some PM rows describe pyramid/sun-temple monuments but there is no typed, consolidated temple authority",
        },
        "excavation": {
            "dedicated_current_authority": False,
            "status": "hard blocked for canonical excavation-node resolution; retain raw/canonical excavation evidence only and do not substitute normalized literal strings as nodes",
        },
        "implementation_state": {
            "enrich_assets_present": [],
            "canonical_resolved_authority_fields_nonnull": {
                field: sum(row[field] not in (None, "", []) for row in canonical)
                for field in ("ruler_id", "origin_site_id", "tomb_temple_id")
            },
            "adr_015_production_findspot_split_implemented_in_current_canonical_schema": False,
        },
    }
    (OUT / "corpus_inventory.json").write_text(json.dumps(corpus_inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "authority_inventory.json").write_text(json.dumps(authority_inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "canonical": len(canonical), "linked_raw": {k: len(v) for k, v in linked_raw.items()},
        "ruler_units": authority_inventory["ruler"]["canonical_units_for_this_adapter"],
        "site_targets": len(sites), "pm_targets": sum(len(v) for v in pm_rows.values()),
    }, indent=2))


if __name__ == "__main__":
    main()
