"""Control-flow tests for private ledger binding authentication.

The small generated case below tests fail-closed verifier behavior only. It is not a
fixture substitute and makes no claim about the real Hapi corpus; the release's real
private integration run is validated separately by the contract execution.
"""

from __future__ import annotations

import collections
import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_ROOT = REPO_ROOT / "docs/evaluations/site-graph-v0"
SCRIPTS = EVAL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def _load_script(name: str, aliases: dict[str, object] | None = None):
    """Load a release script under a test namespace with explicit dependencies."""
    qualified = f"_hapi_site_graph_v0_private_ledgers_{name}"
    spec = importlib.util.spec_from_file_location(qualified, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous = {key: sys.modules.get(key) for key in aliases or {}}
    try:
        for key, value in (aliases or {}).items():
            sys.modules[key] = value
        sys.modules[qualified] = module
        spec.loader.exec_module(module)
    finally:
        for key, value in previous.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value
    return module


baseline = _load_script("build_baseline")
private_ledgers = _load_script("private_ledgers", {"build_baseline": baseline})
build_opportunity_queue = baseline.build_opportunity_queue
canonical_json_sha256 = baseline.canonical_json_sha256
gzip_ledger_digest = baseline.gzip_ledger_digest
sha256 = baseline.sha256
write_gzip_jsonl = baseline.write_gzip_jsonl
write_json = baseline.write_json
verify_private_ledgers = private_ledgers.verify_private_ledgers


ARCHIVE_SHA256 = "a" * 64
LINEAGE_EFFECT = "Control-flow-only disclosed lineage limitation."


def _ledger_digest(path: Path, ledger: dict) -> dict:
    return {
        "bytes": path.stat().st_size,
        "transport_json_sha256": sha256(path),
        "canonical_json_sha256": canonical_json_sha256(ledger),
        "selected_signature_count": ledger["selected_signature_count"],
        "intent_to_treat_record_counts_by_museum": {
            museum: len(rows)
            for museum, rows in ledger["intent_to_treat_records_by_museum"].items()
        },
    }


def _pair_digest(rows: list[dict]) -> dict:
    return {
        "record_count": len(rows),
        "canonical_json_sha256": canonical_json_sha256(rows),
        "category_counts": dict(
            sorted(collections.Counter(row["category"] for row in rows).items())
        ),
    }


def _refresh_public_authentication(case: dict) -> None:
    private_run = case["private_run"]
    public_root = case["public_root"]
    ledger = case["ledger"]
    summary = case["summary"]
    registry = case["registry"]
    ledger_path = private_run / "private-opportunity-ledger.json"
    write_json(ledger_path, ledger)
    membership_digest = _ledger_digest(ledger_path, ledger)
    registry["ledgers"]["private_opportunity_membership"] = membership_digest
    summary["private_ledger_authentication"] = {
        "canonical_json_sha256": membership_digest["canonical_json_sha256"],
        "transport_json_sha256": membership_digest["transport_json_sha256"],
    }
    for pair_key, pair in ledger["credited_pair_opportunity_memberships"].items():
        for museum, rows in pair["sides"].items():
            actual = _pair_digest(rows)
            registry["pair_side_membership"][pair_key][museum] = actual
            public_side = summary["pair_side_ceilings"][pair_key]["sides"][museum]
            public_side["credited_effect_opportunity_denominator"] = len(rows)
            public_side["credited_pair_opportunity_membership_sha256"] = actual[
                "canonical_json_sha256"
            ]
            public_side["new_pair_connection_ceiling_records"] = actual[
                "category_counts"
            ].get("no_baseline_pair_connection", 0)
            public_side["strict_refinement_pair_reassignment_ceiling_records"] = actual[
                "category_counts"
            ].get("broad_only_pair_connection", 0)
    write_json(public_root / "planned-opportunity-summary.json", summary)
    write_json(public_root / "private-ledger-digests.json", registry)


@pytest.fixture
def ledger_case(tmp_path: Path) -> dict:
    private_run = tmp_path / "private"
    public_root = tmp_path / "public"
    private_run.mkdir()
    public_root.mkdir()

    counts = {"met": 20, "brooklyn": 15, "harvard": 15}
    mentions = []
    records = []
    for museum, count in counts.items():
        artifact_id = f"{museum}-control"
        records.append(
            {
                "artifact_id": artifact_id,
                "museum": museum,
                "baseline_record_scope": "no_link",
                "baseline_site_target_ids": [],
            }
        )
        for index in range(count):
            mentions.append(
                {
                    "artifact_id": artifact_id,
                    "entity_type": "site",
                    "field_path": f"places[{index}]",
                    "mention_id": f"mention-{museum}-{index:02d}",
                    "mention_text": f"{museum} control place {index}",
                    "museum": museum,
                    "normalized_keys": [f"{museum}-control-{index:02d}"],
                    "status": "unmatched",
                    "target_ids": [],
                }
            )
    mentions.sort(key=lambda row: row["mention_id"])

    summary, ledger, top_components = build_opportunity_queue(
        mentions,
        records,
        [],
        {},
        {museum: 1 for museum in counts},
        {museum: 1 for museum in counts},
    )
    record_path = private_run / "private-record-evidence.ndjson.gz"
    source_path = private_run / "private-opportunity-source.ndjson.gz"
    ledger_path = private_run / "private-opportunity-ledger.json"
    write_gzip_jsonl(record_path, records)
    write_gzip_jsonl(source_path, mentions)
    write_json(ledger_path, ledger)

    membership_digest = _ledger_digest(ledger_path, ledger)
    summary["private_ledger_authentication"] = {
        "canonical_json_sha256": membership_digest["canonical_json_sha256"],
        "transport_json_sha256": membership_digest["transport_json_sha256"],
    }
    registry = {
        "schema_version": "site-graph-v0-private-ledger-digests/1",
        "external_private_input": {
            "archive_sha256": ARCHIVE_SHA256,
            "snapshot_acquisition_integrity": "PASS",
            "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
            "historical_export_reproducibility": "UNAVAILABLE_DISCLOSED",
            "unavailable_lineage_effect": LINEAGE_EFFECT,
        },
        "ledgers": {
            "private_record_evidence": gzip_ledger_digest(record_path),
            "private_opportunity_source": gzip_ledger_digest(source_path),
            "private_opportunity_membership": membership_digest,
        },
        "pair_side_membership": {
            pair_key: {
                museum: _pair_digest(rows)
                for museum, rows in pair["sides"].items()
            }
            for pair_key, pair in ledger[
                "credited_pair_opportunity_memberships"
            ].items()
        },
    }
    write_json(
        private_run / "corpus-archive-attestation.json",
        {
            "schema_version": "site-graph-v0-corpus-archive-attestation/1",
            "archive": {"sha256": ARCHIVE_SHA256},
            "production_lineage": {
                "status": "UNAVAILABLE_DISCLOSED",
                "effect": LINEAGE_EFFECT,
            },
            "status": {
                "snapshot_acquisition_integrity": "PASS",
                "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
            },
        },
    )
    write_json(public_root / "baseline-metrics.json", {})
    write_json(public_root / "baseline-node-scope.json", {"nodes": []})
    write_json(public_root / "planned-opportunity-summary.json", summary)
    write_json(public_root / "private-ledger-digests.json", registry)
    write_json(public_root / "top-unmatched-components.json", top_components)
    return {
        "private_run": private_run,
        "public_root": public_root,
        "ledger": ledger,
        "summary": summary,
        "registry": registry,
    }


def test_v3_private_ledgers_bind_every_membership(ledger_case: dict) -> None:
    result = verify_private_ledgers(
        ledger_case["private_run"], ledger_case["public_root"]
    )
    assert result == {
        "archive_authentication": {
            "archive_sha256": ARCHIVE_SHA256,
            "snapshot_acquisition_integrity": "PASS",
            "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
        },
        "private_record_count": 3,
        "private_opportunity_source_count": 50,
        "selected_signature_count": 50,
        "pair_side_membership_count": 6,
    }


@pytest.mark.parametrize("attack", ["opportunity", "itt", "pair", "category"])
def test_rejects_stale_missing_or_altered_bindings(
    ledger_case: dict, attack: str
) -> None:
    ledger = ledger_case["ledger"]
    if attack == "opportunity":
        ledger["opportunities"][0]["artifact_memberships"][0][
            "opportunity_binding_sha256"
        ] = "f" * 64
    elif attack == "itt":
        ledger["intent_to_treat_records_by_museum"]["met"][0][
            "opportunity_bindings"
        ].pop()
    else:
        row = ledger["credited_pair_opportunity_memberships"]["met__brooklyn"][
            "sides"
        ]["met"][0]
        if attack == "pair":
            row["opportunity_bindings"][0]["opportunity_binding_sha256"] = "e" * 64
        else:
            row["category"] = "broad_only_pair_connection"
    _refresh_public_authentication(ledger_case)
    with pytest.raises((RuntimeError, ValueError), match="binding|source-realizable|categories"):
        verify_private_ledgers(ledger_case["private_run"], ledger_case["public_root"])


@pytest.mark.parametrize("attack", ["missing", "digest", "status"])
def test_rejects_missing_or_altered_archive_attestation(
    ledger_case: dict, attack: str
) -> None:
    path = ledger_case["private_run"] / "corpus-archive-attestation.json"
    if attack == "missing":
        path.unlink()
    else:
        attestation = json.loads(path.read_text(encoding="utf-8"))
        if attack == "digest":
            attestation["archive"]["sha256"] = "b" * 64
        else:
            attestation["status"]["snapshot_acquisition_integrity"] = "INVALID"
        write_json(path, attestation)
    with pytest.raises(RuntimeError, match="archive attestation"):
        verify_private_ledgers(ledger_case["private_run"], ledger_case["public_root"])


def test_public_projection_rejects_v3_private_binding_fields(ledger_case: dict) -> None:
    path = ledger_case["public_root"] / "baseline-metrics.json"
    value = copy.deepcopy(json.loads(path.read_text(encoding="utf-8")))
    value["artifact_memberships"] = []
    write_json(path, value)
    with pytest.raises(RuntimeError, match="private record/source keys"):
        verify_private_ledgers(ledger_case["private_run"], ledger_case["public_root"])
