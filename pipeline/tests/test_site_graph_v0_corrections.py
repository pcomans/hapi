"""Logic-only attacks on correction and ITT binding invariants.

The temporary rows in this module exercise control flow only.  They are not corpus
evidence and make no evaluation, validation, or product claim.
"""

from __future__ import annotations

import gzip
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_ROOT = REPO_ROOT / "docs/evaluations/site-graph-v0"
SCRIPTS = EVAL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def _load_script(name: str, aliases: dict[str, object] | None = None):
    """Load a release script under a test namespace with explicit dependencies."""
    qualified = f"_hapi_site_graph_v0_corrections_{name}"
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
corrections = _load_script(
    "apply_corrections",
    {"build_baseline": baseline, "private_ledgers": private_ledgers},
)


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _mention(
    museum: str,
    artifact_id: str,
    mention_id: str,
    key: str,
    *,
    status: str = "unmatched",
    target_ids: list[str] | None = None,
) -> dict:
    return {
        "artifact_id": artifact_id,
        "field_path": "logic.place",
        "mention_id": mention_id,
        "mention_text": key.replace("-", " "),
        "museum": museum,
        "normalized_keys": [key],
        "status": status,
        "target_ids": target_ids or [],
        "entity_type": "site",
    }


def _logic_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Build a complete tiny contract shape solely for correction control-flow tests."""
    monkeypatch.setattr(baseline, "OPPORTUNITY_MUSEUM_PROTECTION", 1)
    monkeypatch.setattr(baseline, "OPPORTUNITY_TOTAL_SIGNATURES", 3)
    monkeypatch.setattr(corrections, "verify_private_ledgers", lambda *_: {})

    repo = tmp_path / "repo"
    evaluation = repo / "docs/evaluations/site-graph-v0"
    schemas = evaluation / "schemas"
    schemas.mkdir(parents=True)
    for name in ("correction-ledger.schema.json", "private-opportunity-ledger.schema.json"):
        shutil.copy2(EVAL_ROOT / "schemas" / name, schemas / name)

    scope_by_target = {
        "target-broad": "broad",
        "target-specific": "specific_candidate",
    }
    _write_json(
        evaluation / "baseline-node-scope.json",
        {
            "schema_version": "logic-only",
            "nodes": [
                {"target_id": target, "scope_class": scope}
                for target, scope in scope_by_target.items()
            ],
        },
    )

    source = [
        _mention("met", "met-a", "mention-met-a", "met-top"),
        _mention("met", "met-b", "mention-met-b", "met-top"),
        _mention("met", "met-c", "mention-met-c", "met-top"),
        _mention("met", "met-d", "mention-met-d", "met-next"),
        _mention("met", "met-e", "mention-met-e", "met-next"),
        _mention("brooklyn", "brooklyn-a", "mention-brooklyn-a", "brooklyn-top"),
        _mention("harvard", "harvard-a", "mention-harvard-a", "harvard-top"),
    ]
    source.sort(key=lambda row: row["mention_id"])
    canonical = [
        {"id": mention["artifact_id"], "source_museum": mention["museum"]}
        for mention in source
    ]
    records = baseline.build_record_rows(canonical, source, [], scope_by_target)
    record_counts = {
        museum: sum(row["museum"] == museum for row in records)
        for museum in ("met", "brooklyn", "harvard")
    }
    evidence_counts = dict(record_counts)
    _, frozen_ledger, _ = baseline.build_opportunity_queue(
        source,
        records,
        [],
        scope_by_target,
        record_counts,
        evidence_counts,
    )

    private_run = tmp_path / "private-run"
    private_run.mkdir()
    record_path = private_run / "private-record-evidence.ndjson.gz"
    source_path = private_run / "private-opportunity-source.ndjson.gz"
    baseline.write_gzip_jsonl(record_path, records)
    baseline.write_gzip_jsonl(source_path, source)
    _write_json(private_run / "private-opportunity-ledger.json", frozen_ledger)
    record_digest = baseline.gzip_ledger_digest(record_path)
    source_digest = baseline.gzip_ledger_digest(source_path)
    _write_json(
        evaluation / "private-ledger-digests.json",
        {
            "ledgers": {
                "private_record_evidence": record_digest,
                "private_opportunity_source": source_digest,
            }
        },
    )

    operations = [
        {
            "kind": "set_site_mention_resolution",
            "mention_id": f"mention-met-{suffix}",
            "from_status": "unmatched",
            "from_target_ids": [],
            "to_status": "resolved",
            "to_target_ids": ["target-broad"],
        }
        for suffix in ("a", "b", "c")
    ]
    correction_rows = []
    previous = None
    for sequence, operation in enumerate(operations, 1):
        correction = {
            "sequence": sequence,
            "correction_id": f"logic-correction-{sequence}",
            "previous_correction_sha256": previous,
            "supersedes_correction_id": None,
            "artifact_id": f"met-{chr(96 + sequence)}",
            "operation": operation,
            "reason": "logic-only exact mention resolution transition",
            "citations": [
                {
                    "source_id": "logic-only-source",
                    "locator": f"logic-row-{sequence}",
                    "evidence_summary": "purpose-built control-flow evidence",
                }
            ],
            "reviewer_ids": ["logic-reviewer-a", "logic-reviewer-b"],
            "decision_commit": "a" * 40,
            "recorded_at_utc": f"2026-08-28T00:00:0{sequence}Z",
            "record_sha256": "",
        }
        correction["record_sha256"] = corrections.record_hash(correction)
        previous = correction["record_sha256"]
        correction_rows.append(correction)
    ledger = {
        "schema_version": "site-graph-v0-correction-ledger/3",
        "baseline_mutated": False,
        "private_record_evidence_canonical_sha256": record_digest[
            "canonical_uncompressed_ndjson_sha256"
        ],
        "private_opportunity_source_canonical_sha256": source_digest[
            "canonical_uncompressed_ndjson_sha256"
        ],
        "corrections": correction_rows,
    }
    ledger_path = tmp_path / "corrections.json"
    _write_json(ledger_path, ledger)
    return {
        "repo": repo,
        "evaluation": evaluation,
        "private_run": private_run,
        "frozen_ledger": frozen_ledger,
        "ledger": ledger,
        "ledger_path": ledger_path,
    }


def test_private_source_and_itt_rows_bind_exact_selecting_mentions() -> None:
    mentions = [
        _mention(
            "met",
            "met-resolved",
            "mention-resolved",
            "resolved-key",
            status="resolved",
            target_ids=["target-broad"],
        ),
        _mention("met", "met-unmatched", "mention-unmatched", "unmatched-key"),
        _mention("brooklyn", "brooklyn-u", "mention-brooklyn", "brooklyn-key"),
        _mention("harvard", "harvard-u", "mention-harvard", "harvard-key"),
    ]
    source = baseline.private_opportunity_source(mentions)
    assert [row["mention_id"] for row in source] == [
        "mention-brooklyn",
        "mention-harvard",
        "mention-resolved",
        "mention-unmatched",
    ]
    assert source[2]["status"] == "resolved"
    assert source[2]["target_ids"] == ["target-broad"]

    scope = {"target-broad": "broad"}
    canonical = [
        {"id": mention["artifact_id"], "source_museum": mention["museum"]}
        for mention in mentions
    ]
    links = [
        {
            "entity_type": "site",
            "artifact_id": "met-resolved",
            "museum": "met",
            "target_id": "target-broad",
        }
    ]
    records = baseline.build_record_rows(canonical, mentions, links, scope)
    counts = {"met": 2, "brooklyn": 1, "harvard": 1}
    summary, ledger, _ = baseline.build_opportunity_queue(
        source, records, links, scope, counts, counts
    )
    assert summary["selected_signature_count"] == 3
    unmatched = next(
        row for row in ledger["opportunities"] if row["museum"] == "met"
    )
    membership = unmatched["artifact_memberships"][0]
    assert membership["mentions"][0]["mention_id"] == "mention-unmatched"
    assert len(membership["opportunity_binding_sha256"]) == 64
    itt = next(
        row
        for row in ledger["intent_to_treat_records_by_museum"]["met"]
        if row["artifact_id"] == "met-unmatched"
    )
    assert itt["opportunity_bindings"] == [
        {
            "opportunity_id": unmatched["opportunity_id"],
            "opportunity_binding_sha256": membership["opportunity_binding_sha256"],
        }
    ]
    pair_member = next(
        row
        for row in ledger["credited_pair_opportunity_memberships"]["met__brooklyn"][
            "sides"
        ]["met"]
        if row["artifact_id"] == "met-unmatched"
    )
    assert pair_member["opportunity_bindings"] == itt["opportunity_bindings"]


def test_resolved_mention_with_two_targets_is_rejected() -> None:
    bad = _mention(
        "met",
        "met-a",
        "mention-a",
        "bad",
        status="resolved",
        target_ids=["target-a", "target-b"],
    )
    with pytest.raises(RuntimeError, match="exactly one target"):
        baseline.build_record_rows(
            [{"id": "met-a", "source_museum": "met"}],
            [bad],
            [],
            {"target-a": "broad", "target-b": "broad"},
        )


def test_fixed_itt_stays_frozen_while_counterfactual_reports_exact_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _logic_fixture(tmp_path, monkeypatch)
    private_before = {
        path.relative_to(fixture["private_run"]).as_posix(): baseline.sha256(path)
        for path in fixture["private_run"].rglob("*")
        if path.is_file()
    }
    public_before = {
        path.relative_to(fixture["evaluation"]).as_posix(): baseline.sha256(path)
        for path in fixture["evaluation"].rglob("*")
        if path.is_file()
    }
    output = tmp_path / "sensitivity"
    summary = corrections.apply(
        fixture["repo"], fixture["private_run"], fixture["ledger_path"], output
    )
    assert summary["primary_baseline_immutable"] is True
    assert summary["frozen_intent_to_treat_membership_rewritten"] is False
    assert private_before == {
        path.relative_to(fixture["private_run"]).as_posix(): baseline.sha256(path)
        for path in fixture["private_run"].rglob("*")
        if path.is_file()
    }
    assert public_before == {
        path.relative_to(fixture["evaluation"]).as_posix(): baseline.sha256(path)
        for path in fixture["evaluation"].rglob("*")
        if path.is_file()
    }

    fixed = json.loads((output / "private-fixed-frozen-itt-analysis.json").read_text())
    frozen_met = fixture["frozen_ledger"]["intent_to_treat_records_by_museum"]["met"]
    assert [row["artifact_id"] for row in fixed["intent_to_treat_record_states_by_museum"]["met"]] == [
        row["artifact_id"] for row in frozen_met
    ]
    assert all(
        row["opportunity_bindings"] == frozen["opportunity_bindings"]
        for row, frozen in zip(
            fixed["intent_to_treat_record_states_by_museum"]["met"], frozen_met, strict=True
        )
    )
    fixed_pair = summary["fixed_frozen_intent_to_treat"]["pair_side_ceilings"][
        "met__brooklyn"
    ]["sides"]["met"]
    assert fixed_pair["frozen_credited_effect_opportunity_denominator"] == 3
    assert fixed_pair["membership_and_denominator_unchanged"] is True

    exact = json.loads(
        (output / "private-corrected-source-counterfactual-changes.json").read_text()
    )
    assert [row["normalized_expression_key"] for row in exact["signature_changes"]["removed"]] == [
        "met-top"
    ]
    assert [row["normalized_expression_key"] for row in exact["signature_changes"]["added"]] == [
        "met-next"
    ]
    assert exact["intent_to_treat_record_changes_by_museum"]["met"] == {
        "removed_artifact_ids": ["met-a", "met-b", "met-c"],
        "added_artifact_ids": ["met-d", "met-e"],
    }
    reselection = summary["corrected_source_counterfactual_reselection"]
    assert reselection["removed_signature_count"] == 1
    assert reselection["added_signature_count"] == 1
    assert reselection["per_museum"]["met"]["denominator_change"] == -1
    assert reselection["pair_side_denominator_changes"]["met__brooklyn"]["sides"][
        "met"
    ]["denominator_change"] == -1

    with gzip.open(
        output / "private-sensitivity-opportunity-source.ndjson.gz",
        "rt",
        encoding="utf-8",
    ) as handle:
        corrected_source = [json.loads(line) for line in handle]
    corrected_top = [
        row
        for row in corrected_source
        if row["normalized_keys"] == ["met-top"]
    ]
    assert len(corrected_top) == 3
    assert all(
        row["status"] == "resolved" and row["target_ids"] == ["target-broad"]
        for row in corrected_top
    )


def test_correction_rejects_one_resolved_mention_with_two_targets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _logic_fixture(tmp_path, monkeypatch)
    ledger = fixture["ledger"]
    ledger["corrections"] = [ledger["corrections"][0]]
    operation = ledger["corrections"][0]["operation"]
    operation["to_target_ids"] = ["target-broad", "target-specific"]
    ledger["corrections"][0]["record_sha256"] = corrections.record_hash(
        ledger["corrections"][0]
    )
    path = tmp_path / "invalid-two-targets.json"
    _write_json(path, ledger)
    with pytest.raises(ValueError, match="resolved mention must have exactly one target"):
        corrections.apply(
            fixture["repo"], fixture["private_run"], path, tmp_path / "never"
        )


def test_correction_rejects_unknown_target_wrong_type_and_unsuperseded_repeat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _logic_fixture(tmp_path, monkeypatch)

    unknown = json.loads(json.dumps(fixture["ledger"]))
    unknown["corrections"][0]["operation"]["to_target_ids"] = ["invented-target"]
    unknown["corrections"][0]["record_sha256"] = corrections.record_hash(
        unknown["corrections"][0]
    )
    unknown_path = tmp_path / "unknown-target.json"
    _write_json(unknown_path, unknown)
    with pytest.raises(ValueError, match="unknown targets"):
        corrections.apply(
            fixture["repo"], fixture["private_run"], unknown_path, tmp_path / "never-unknown"
        )

    wrong_type = json.loads(json.dumps(fixture["ledger"]))
    wrong_type["baseline_mutated"] = "false"
    wrong_type_path = tmp_path / "wrong-type.json"
    _write_json(wrong_type_path, wrong_type)
    with pytest.raises(ValueError, match="schema validation"):
        corrections.apply(
            fixture["repo"], fixture["private_run"], wrong_type_path, tmp_path / "never-type"
        )

    repeated = json.loads(json.dumps(fixture["ledger"]))
    extra = json.loads(json.dumps(repeated["corrections"][0]))
    extra.update(
        {
            "sequence": 4,
            "correction_id": "logic-correction-4",
            "previous_correction_sha256": repeated["corrections"][-1][
                "record_sha256"
            ],
            "supersedes_correction_id": None,
            "recorded_at_utc": "2026-08-28T00:00:04Z",
        }
    )
    extra["operation"] = {
        "kind": "set_site_mention_resolution",
        "mention_id": "mention-met-a",
        "from_status": "resolved",
        "from_target_ids": ["target-broad"],
        "to_status": "unmatched",
        "to_target_ids": [],
    }
    extra["record_sha256"] = corrections.record_hash(extra)
    repeated["corrections"].append(extra)
    repeated_path = tmp_path / "unsuperseded-repeat.json"
    _write_json(repeated_path, repeated)
    with pytest.raises(ValueError, match="without exact supersession"):
        corrections.apply(
            fixture["repo"], fixture["private_run"], repeated_path, tmp_path / "never-repeat"
        )
