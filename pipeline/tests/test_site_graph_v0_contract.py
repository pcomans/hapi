"""Executable enforcement for issue #327.

Committed baseline assertions below use only the pinned real-corpus derivatives.  Tiny
temporary files are used solely for adversarial control-flow tests and make no corpus
or evaluation claim.
"""

from __future__ import annotations

import copy
from collections import Counter
import importlib.util
import inspect
import json
import shutil
import subprocess
import sys
import os
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_ROOT = REPO_ROOT / "docs/evaluations/site-graph-v0"
SCRIPTS = EVAL_ROOT / "scripts"
sys.path.append(str(SCRIPTS))


def _load_script_module(name: str):
    """Load release tooling under a test-only namespace to avoid import collisions."""
    qualified_name = f"_hapi_site_graph_v0_{name}"
    spec = importlib.util.spec_from_file_location(qualified_name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified_name] = module
    spec.loader.exec_module(module)
    return module


compare_baseline_runs_module = _load_script_module("compare_baseline_runs")
compare_candidate_module = _load_script_module("compare_candidate")
build_baseline_module = _load_script_module("build_baseline")
integrity_module = _load_script_module("integrity")
run_baseline_module = _load_script_module("run_baseline")
schema_validation_module = _load_script_module("schema_validation")
release_contract_module = _load_script_module("release_contract")
validate_contract_module = _load_script_module("validate_contract")

compare = compare_baseline_runs_module.compare
MAXIMUM_NEWLY_BLOCKING_FRACTION = compare_candidate_module.MAXIMUM_NEWLY_BLOCKING_FRACTION
CONCENTRATION_MAXIMUM_INCREASE = compare_candidate_module.CONCENTRATION_MAXIMUM_INCREASE
MINIMUM_AFFECTED_FRACTION = compare_candidate_module.MINIMUM_AFFECTED_FRACTION
MINIMUM_GAINED_IDENTITIES = compare_candidate_module.MINIMUM_GAINED_IDENTITIES
REVIEWS_PER_CREDITED_DECISION = compare_candidate_module.REVIEWS_PER_CREDITED_DECISION
canonical_sha256 = compare_candidate_module.canonical_sha256
compare_core = compare_candidate_module.compare_core
decision_key = compare_candidate_module.decision_key
_load_candidate_freeze = compare_candidate_module._load_candidate_freeze
_validate_review_artifacts = compare_candidate_module._validate_review_artifacts
CandidateGitError = compare_candidate_module.CandidateGitError
ReviewAuthenticationError = compare_candidate_module.ReviewAuthenticationError
classify_current_nodes = build_baseline_module.classify_current_nodes
OPPORTUNITY_MUSEUM_PROTECTION = build_baseline_module.OPPORTUNITY_MUSEUM_PROTECTION
OPPORTUNITY_TOTAL_SIGNATURES = build_baseline_module.OPPORTUNITY_TOTAL_SIGNATURES
read_jsonl = build_baseline_module.read_jsonl
IntegrityError = integrity_module.IntegrityError
sha256 = integrity_module.sha256
verify_release = integrity_module.verify_release
DETERMINISTIC_OUTPUTS = run_baseline_module.DETERMINISTIC_OUTPUTS
FINAL_OUTPUTS = run_baseline_module.FINAL_OUTPUTS
run_baseline = run_baseline_module.run
execute_schema_contract_tests = schema_validation_module.execute_schema_contract_tests
validation_input_bindings = release_contract_module.validation_input_bindings
CONTRACT_VERSION = release_contract_module.CONTRACT_VERSION
PYCACHE_EXCLUSION = release_contract_module.PYCACHE_EXCLUSION
REQUIRED_RELEASE_FILES = release_contract_module.REQUIRED_RELEASE_FILES
authenticate_release_preimport = validate_contract_module.authenticate_release_preimport
public_boundary_evidence_passed = (
    validate_contract_module._public_boundary_evidence_passed
)
schema_execution_evidence_passed = (
    validate_contract_module._schema_execution_evidence_passed
)
scan_public_repository_boundary = (
    validate_contract_module.scan_public_repository_boundary
)


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _logic_only_run(path: Path, run_id: str | None = None) -> None:
    """Create authenticated-shaped bytes only to attack comparator invariants."""
    path.mkdir()
    for name in sorted(DETERMINISTIC_OUTPUTS):
        (path / name).write_bytes((name + "\n").encode())
    hashes = {name: sha256(path / name) for name in sorted(DETERMINISTIC_OUTPUTS)}
    stable = {
        "schema_version": "site-graph-v0-baseline-run-manifest/1",
        "commands": [],
        "deterministic_output_hashes": hashes,
        "input_snapshot_sha256": "1" * 64,
        "runner_sha256": "2" * 64,
        "builder_sha256": "3" * 64,
        "inventory_path_canonicalization": "test",
        "scope": "logic-only comparator unit input; no corpus claim",
    }
    _write_json(path / "run-output-manifest.json", stable)
    _write_json(
        path / "run-provenance.json",
        {
            "schema_version": "site-graph-v0-baseline-run-provenance/1",
            "run_id": run_id or str(uuid.uuid4()),
            "started_at_utc": "2026-08-28T00:00:00+00:00",
            "finished_at_utc": "2026-08-28T00:00:01+00:00",
            "requested_output": str(path.resolve()),
            "publication": "logic-only",
            "repo_root": str(REPO_ROOT),
            "corpus_root": "/logic-only",
            "canonical_records": 1,
            "records_by_museum": {"logic-only": 1},
            "input_snapshot_sha256": stable["input_snapshot_sha256"],
            "runner_sha256": stable["runner_sha256"],
            "builder_sha256": stable["builder_sha256"],
        },
    )
    assert {item.name for item in path.iterdir()} == FINAL_OUTPUTS


def _temporary_release(tmp_path: Path, *, freeze: bool = True) -> Path:
    repo = tmp_path / "repo"
    target = repo / "docs/evaluations/site-graph-v0"
    shutil.copytree(EVAL_ROOT, target, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    for relative in sorted(integrity_module.CI_RELEASE_FILES):
        source = REPO_ROOT / relative
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    manifest = target / "release-manifest.json"
    manifest.unlink(missing_ok=True)
    # Build a provisional, internally bound report in this isolated logic-only copy.
    # The committed report is intentionally never rewritten by tests.
    report_path = target / "validation-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["release_candidate_binding"]["files"] = validation_input_bindings(repo)
    _write_json(report_path, report)
    if freeze:
        _write_json(
            manifest,
            {
                "schema_version": "site-graph-v0-release-manifest/2",
                "contract_version": CONTRACT_VERSION,
                "hash_algorithm": "sha256",
                "pycache_exclusion": PYCACHE_EXCLUSION,
                "inventory_rule": (
                    "Exactly REQUIRED_RELEASE_FILES in scripts/release_contract.py. "
                    "Any addition, removal, or cache-exclusion change requires a "
                    "separately reviewed contract-version migration."
                ),
                "files": {
                    relative: {
                        "bytes": (repo / relative).stat().st_size,
                        "sha256": sha256(repo / relative),
                    }
                    for relative in sorted(REQUIRED_RELEASE_FILES)
                },
            },
        )
        verify_release(repo)
    return repo


@pytest.mark.parametrize(
    ("operation", "target"),
    [
        ("corrupt", "docs/evaluations/site-graph-v0/preregistration.json"),
        ("delete", "docs/evaluations/site-graph-v0/scripts/compare_baseline_runs.py"),
    ],
)
def test_validator_rejects_release_corruption_before_semantics(
    tmp_path: Path, operation: str, target: str
) -> None:
    repo = _temporary_release(tmp_path)
    path = repo / target
    if operation == "corrupt":
        # Specifically attack a machine-readable formula while retaining valid JSON.
        value = json.loads(path.read_text(encoding="utf-8"))
        value["metric_formulas"]["overall_linkability"]["expression"] = "wrong / denominator"
        _write_json(path, value)
    else:
        path.unlink()
    before = {
        item.relative_to(repo).as_posix(): item.read_bytes()
        for item in repo.rglob("*") if item.is_file()
    }
    result = subprocess.run(
        [sys.executable, "-B", str(repo / "docs/evaluations/site-graph-v0/scripts/validate_contract.py"),
         "--repo-root", str(repo),
         "--corpus-archive", "/does/not/matter",
         "--corpus-archive-sidecar", "/does/not/matter.sha256",
         "--private-run", "/does/not/matter"],
        check=False,
        capture_output=True,
        text=True,
    )
    after = {
        item.relative_to(repo).as_posix(): item.read_bytes()
        for item in repo.rglob("*") if item.is_file()
    }
    assert result.returncode == 1
    assert '"phase": "release_integrity"' in result.stdout
    assert before == after, "read-only validation must not repair or rewrite the release"


@pytest.mark.parametrize(
    "attack",
    [
        "syntax_corruption",
        "top_level_side_effect",
        "aliased_top_level_side_effect",
        "json_default_callback_side_effect",
        "collection_iterator_side_effect",
        "pathlike_callback_side_effect",
        "argument_annotation_side_effect",
        "return_annotation_side_effect",
        "annotated_assignment_side_effect",
        "annotation_subscription_side_effect",
        "unapproved_import_side_effect",
        "custom_base_side_effect",
        "custom_metaclass_side_effect",
        "stale_initializer_kind_side_effect",
        "stale_class_scope_kind_side_effect",
        "stale_class_import_alias_side_effect",
        "stale_passive_class_side_effect",
    ],
)
def test_validator_authenticates_semantic_module_before_import(
    tmp_path: Path, attack: str
) -> None:
    repo = _temporary_release(tmp_path)
    target = (
        repo
        / "docs/evaluations/site-graph-v0/scripts/build_baseline.py"
    )
    marker = tmp_path / "semantic-module-executed"
    importable = tmp_path / "importable"
    importable.mkdir()
    if attack == "syntax_corruption":
        target.write_text("def invalid syntax(:\n", encoding="utf-8")
    elif attack == "top_level_side_effect":
        target.write_text(
            target.read_text(encoding="utf-8")
            + "\n__import__('pathlib').Path("
            + repr(str(marker))
            + ").write_text('executed', encoding='utf-8')\n",
            encoding="utf-8",
        )
    elif attack == "aliased_top_level_side_effect":
        target.write_text(
            target.read_text(encoding="utf-8")
            + "\nfrom os import system as Path\n"
            + "X = Path("
            + repr(f"touch {marker}")
            + ")\n",
            encoding="utf-8",
        )
    elif attack == "json_default_callback_side_effect":
        target.write_text(
            "import json\n"
            "from pathlib import Path\n"
            "def callback(value):\n"
            "    Path("
            + repr(str(marker))
            + ").write_text('executed', encoding='utf-8')\n"
            "    return 'serialized'\n"
            "PROBE = json.dumps(Path, default=callback)\n",
            encoding="utf-8",
        )
    elif attack == "collection_iterator_side_effect":
        target.write_text(
            "from pathlib import Path\n"
            "def callback():\n"
            "    Path("
            + repr(str(marker))
            + ").write_text('executed', encoding='utf-8')\n"
            "    yield 'value'\n"
            "PROBE = list(callback())\n",
            encoding="utf-8",
        )
    elif attack == "pathlike_callback_side_effect":
        target.write_text(
            "from pathlib import Path\n"
            "class CallbackPath:\n"
            "    def __fspath__(self):\n"
            "        Path("
            + repr(str(marker))
            + ").write_text('executed', encoding='utf-8')\n"
            "        return '.'\n"
            "PROBE = Path(CallbackPath())\n",
            encoding="utf-8",
        )
    elif attack == "argument_annotation_side_effect":
        target.write_text(
            "def probe(value: __import__('pathlib').Path("
            + repr(str(marker))
            + ").write_text('executed', encoding='utf-8')):\n    pass\n",
            encoding="utf-8",
        )
    elif attack == "return_annotation_side_effect":
        target.write_text(
            "def probe() -> __import__('pathlib').Path("
            + repr(str(marker))
            + ").write_text('executed', encoding='utf-8'):\n    pass\n",
            encoding="utf-8",
        )
    elif attack == "annotated_assignment_side_effect":
        target.write_text(
            "PROBE: __import__('pathlib').Path("
            + repr(str(marker))
            + ").write_text('executed', encoding='utf-8') = None\n",
            encoding="utf-8",
        )
    elif attack == "annotation_subscription_side_effect":
        target.write_text(
            "from pathlib import Path\n"
            "class Evaluated:\n"
            "    @classmethod\n"
            "    def __class_getitem__(cls, item):\n"
            "        Path("
            + repr(str(marker))
            + ").write_text('executed', encoding='utf-8')\n"
            "        return cls\n"
            "def probe(value: Evaluated[int]):\n"
            "    pass\n",
            encoding="utf-8",
        )
    elif attack == "unapproved_import_side_effect":
        (importable / "boundary_side_effect_module.py").write_text(
            "from pathlib import Path\nPath("
            + repr(str(marker))
            + ").write_text('executed', encoding='utf-8')\n",
            encoding="utf-8",
        )
        target.write_text("import boundary_side_effect_module\n", encoding="utf-8")
    elif attack == "custom_base_side_effect":
        target.write_text(
            "from pathlib import Path\n"
            "class ExecutingBase:\n"
            "    def __init_subclass__(cls):\n"
            "        Path("
            + repr(str(marker))
            + ").write_text('executed', encoding='utf-8')\n"
            "class Probe(ExecutingBase):\n"
            "    pass\n",
            encoding="utf-8",
        )
    elif attack == "stale_initializer_kind_side_effect":
        target.write_text(
            "from pathlib import Path\n"
            "P = Path('.')\n"
            "class Callback:\n"
            "    @staticmethod\n"
            "    def resolve():\n"
            "        Path("
            + repr(str(marker))
            + ").write_text('executed', encoding='utf-8')\n"
            "P = Callback\n"
            "PROBE = P.resolve()\n",
            encoding="utf-8",
        )
    elif attack == "stale_class_scope_kind_side_effect":
        target.write_text(
            "from pathlib import Path\n"
            "P = Path('.')\n"
            "class Callback:\n"
            "    @staticmethod\n"
            "    def resolve():\n"
            "        Path("
            + repr(str(marker))
            + ").write_text('executed', encoding='utf-8')\n"
            "class Probe:\n"
            "    P = Callback\n"
            "    RESULT = P.resolve()\n",
            encoding="utf-8",
        )
    elif attack == "stale_class_import_alias_side_effect":
        target.write_text(
            "from pathlib import Path\n"
            "class Callback:\n"
            "    def __init__(self, value):\n"
            "        Path("
            + repr(str(marker))
            + ").write_text('executed', encoding='utf-8')\n"
            "class Probe:\n"
            "    Path = Callback\n"
            "    RESULT = Path('.')\n",
            encoding="utf-8",
        )
    elif attack == "stale_passive_class_side_effect":
        target.write_text(
            "from pathlib import Path\n"
            "class Base:\n"
            "    pass\n"
            "class Callback:\n"
            "    def __init_subclass__(cls):\n"
            "        Path("
            + repr(str(marker))
            + ").write_text('executed', encoding='utf-8')\n"
            "Base = Callback\n"
            "class Probe(Base):\n"
            "    pass\n",
            encoding="utf-8",
        )
    else:
        target.write_text(
            "from pathlib import Path\n"
            "class Meta(type):\n"
            "    def __new__(mcls, name, bases, namespace):\n"
            "        Path("
            + repr(str(marker))
            + ").write_text('executed', encoding='utf-8')\n"
            "        return super().__new__(mcls, name, bases, namespace)\n"
            "class Probe(metaclass=Meta):\n"
            "    pass\n",
            encoding="utf-8",
        )
    manifest_path = repo / "docs/evaluations/site-graph-v0/release-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    relative = target.relative_to(repo).as_posix()
    manifest["files"][relative] = {
        "bytes": target.stat().st_size,
        "sha256": sha256(target),
    }
    _write_json(manifest_path, manifest)
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(SCRIPTS / "validate_contract.py"),
            "--repo-root",
            str(repo),
            "--corpus-archive",
            "/does/not/matter",
            "--corpus-archive-sidecar",
            "/does/not/matter.sha256",
            "--private-run",
            "/does/not/matter",
        ],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(importable)},
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert payload["phase"] == "release_integrity"
    assert payload["semantic_release_modules_activated"] is False
    assert not marker.exists(), "unauthenticated top-level code must never execute"


def test_validator_dynamically_loads_authenticated_target_root_modules(
    tmp_path: Path,
) -> None:
    repo = _temporary_release(tmp_path)
    evidence = authenticate_release_preimport(repo)
    assert evidence["preimport_authentication"] is True
    program = """
import importlib.util
import json
import pathlib
import sys
spec = importlib.util.spec_from_file_location("isolated_validator", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module._activate_authenticated_release(pathlib.Path(sys.argv[2]))
names = ["build_baseline", "compare_candidate", "integrity", "private_ledgers"]
print(json.dumps({name: sys.modules[name].__file__ for name in names}, sort_keys=True))
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", program, str(SCRIPTS / "validate_contract.py"), str(repo)],
        check=True,
        capture_output=True,
        text=True,
    )
    scripts_root = (
        repo / "docs/evaluations/site-graph-v0/scripts"
    ).resolve()
    loaded = json.loads(result.stdout)
    assert loaded
    assert all(Path(path).resolve().parent == scripts_root for path in loaded.values())


def test_dirty_candidate_generation_entry_is_not_a_public_validator_bypass() -> None:
    with pytest.raises(
        validate_contract_module.ReleaseIntegrityPreflightError,
        match="callable only from",
    ):
        validate_contract_module.semantic_report_for_release_generation(
            REPO_ROOT,
            Path("/does/not/matter"),
            Path("/does/not/matter.sha256"),
            Path("/does/not/matter"),
        )
    generator = (SCRIPTS / "generate_validation_report.py").read_text(
        encoding="utf-8"
    )
    assert "semantic_report_for_release_generation" in generator
    assert "from validate_contract import semantic_report\n" not in generator


def test_release_inventory_rejects_extra_file(tmp_path: Path) -> None:
    repo = _temporary_release(tmp_path)
    (repo / "docs/evaluations/site-graph-v0/undeclared.txt").write_text("extra")
    with pytest.raises(IntegrityError, match="extra"):
        verify_release(repo)


def test_release_freeze_rejects_report_stale_after_candidate_byte_change(
    tmp_path: Path,
) -> None:
    repo = _temporary_release(tmp_path, freeze=False)
    readme = repo / "docs/evaluations/site-graph-v0/README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "\nstale attack\n")
    result = subprocess.run(
        [
            sys.executable,
            str(
                repo
                / "docs/evaluations/site-graph-v0/scripts/freeze_release.py"
            ),
            "--repo-root",
            str(repo),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "stale validation report" in result.stderr
    assert not (repo / "docs/evaluations/site-graph-v0/release-manifest.json").exists()


def test_every_json_schema_has_executed_valid_and_adversarial_instances() -> None:
    result = execute_schema_contract_tests(
        EVAL_ROOT / "schemas", EVAL_ROOT / "schema-test-cases.json"
    )
    schema_names = sorted(
        path.name for path in (EVAL_ROOT / "schemas").glob("*.schema.json")
    )
    cases = json.loads((EVAL_ROOT / "schema-test-cases.json").read_text())["cases"]
    invalid_count = sum(len(case["invalid"]) for case in cases.values())
    assert result["meta_valid_schema_count"] == len(schema_names)
    assert result["representative_valid_instance_count"] == len(schema_names)
    assert result["adversarial_invalid_instance_count"] == invalid_count
    assert result["schemas"] == schema_names
    assert schema_execution_evidence_passed(
        result, EVAL_ROOT / "schemas", EVAL_ROOT / "schema-test-cases.json"
    )


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("meta_valid_schema_count", 0),
        ("representative_valid_instance_count", 0),
        ("adversarial_invalid_instance_count", 0),
        ("schemas", []),
    ],
)
def test_schema_execution_check_rejects_false_returned_evidence(
    field: str, invalid_value: object
) -> None:
    schema_names = sorted(
        path.name for path in (EVAL_ROOT / "schemas").glob("*.schema.json")
    )
    cases = json.loads((EVAL_ROOT / "schema-test-cases.json").read_text())["cases"]
    evidence = {
        "meta_valid_schema_count": len(schema_names),
        "representative_valid_instance_count": len(schema_names),
        "adversarial_invalid_instance_count": sum(
            len(cases[name]["invalid"]) for name in schema_names
        ),
        "schemas": schema_names,
    }
    assert schema_execution_evidence_passed(
        evidence, EVAL_ROOT / "schemas", EVAL_ROOT / "schema-test-cases.json"
    )
    evidence[field] = invalid_value
    assert not schema_execution_evidence_passed(
        evidence, EVAL_ROOT / "schemas", EVAL_ROOT / "schema-test-cases.json"
    )


def test_rerun_comparator_rejects_same_resolved_directory(tmp_path: Path) -> None:
    run = tmp_path / "run"
    _logic_only_run(run)
    with pytest.raises(RuntimeError, match="different directories"):
        compare(run, run / ".." / "run")


@pytest.mark.parametrize("attack", ["corrupt", "delete", "extra", "same_run_id"])
def test_rerun_comparator_authenticates_outputs_and_provenance(tmp_path: Path, attack: str) -> None:
    left, right = tmp_path / "left", tmp_path / "right"
    shared_id = str(uuid.uuid4()) if attack == "same_run_id" else None
    _logic_only_run(left, shared_id)
    _logic_only_run(right, shared_id)
    if attack == "corrupt":
        (right / "baseline-metrics.json").write_text("corrupted after manifest\n")
    elif attack == "delete":
        (right / "top_gaps.json").unlink()
    elif attack == "extra":
        (right / "not-declared.txt").write_text("extra")
    with pytest.raises(RuntimeError):
        compare(left, right)


def test_runner_preflight_failure_leaves_no_output(tmp_path: Path) -> None:
    output = tmp_path / "never-created"
    with pytest.raises((RuntimeError, FileNotFoundError)):
        run_baseline(
            REPO_ROOT,
            tmp_path / "missing-corpus.tar.gz",
            tmp_path / "missing-corpus.tar.gz.sha256",
            output,
        )
    assert not output.exists()


def test_public_release_excludes_private_corpus_derivatives() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(SCRIPTS / "private_ledgers.py"),
            "--public-root",
            str(EVAL_ROOT),
            "--public-only",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "frozen-record-evidence.ndjson.gz" in result.stdout
    assert "frozen-opportunity-source.ndjson.gz" in result.stdout
    summary = json.loads((EVAL_ROOT / "planned-opportunity-summary.json").read_text())
    assert all(
        "artifact_expansion_sha256" not in row
        for row in summary["opportunities"]
    )
    readme = (EVAL_ROOT / "README.md").read_text(encoding="utf-8")
    assert "not claimed opaque or unlinkable" in readme


def test_public_boundary_check_is_derived_from_returned_evidence() -> None:
    public_files = frozenset(
        {
            "baseline-metrics.json",
            "baseline-node-scope.json",
            "planned-opportunity-summary.json",
            "private-ledger-digests.json",
            "top-unmatched-components.json",
        }
    )
    forbidden_files = frozenset(
        {
            "frozen-record-evidence.ndjson.gz",
            "frozen-opportunity-source.ndjson.gz",
            "planned-opportunity-queue.json",
            "private-record-evidence.ndjson.gz",
            "private-opportunity-source.ndjson.gz",
            "private-opportunity-ledger.json",
        }
    )
    evidence = {
        "public_aggregate_files": sorted(public_files),
        "forbidden_public_files_absent": sorted(forbidden_files),
    }
    assert public_boundary_evidence_passed(
        evidence, public_files, forbidden_files
    )
    for field in evidence:
        attacked = copy.deepcopy(evidence)
        attacked[field] = []
        assert not public_boundary_evidence_passed(
            attacked, public_files, forbidden_files
        )


def test_public_boundary_rejects_reintroduced_bulk_derivative(tmp_path: Path) -> None:
    public_root = tmp_path / "public"
    public_root.mkdir()
    for name in (
        "baseline-metrics.json",
        "baseline-node-scope.json",
        "planned-opportunity-summary.json",
        "private-ledger-digests.json",
        "top-unmatched-components.json",
    ):
        shutil.copy2(EVAL_ROOT / name, public_root / name)
    (public_root / "frozen-record-evidence.ndjson.gz").write_bytes(b"private")
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(SCRIPTS / "private_ledgers.py"),
            "--public-root",
            str(public_root),
            "--public-only",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "private/bulk files present" in result.stderr


def _init_boundary_git_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "config", "user.email", "boundary@example.invalid"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Boundary Fixture"],
        cwd=repo,
        check=True,
    )
    root = repo / "docs/evaluations/site-graph-v0"
    root.mkdir(parents=True)
    (root / "aggregate.json").write_text("{}\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)


def test_repository_boundary_scans_current_tree_and_every_head_ancestor() -> None:
    evidence = scan_public_repository_boundary(REPO_ROOT)
    assert evidence["passed"] is True
    assert evidence["status"] == "PASS"
    assert evidence["current_tree"] == {
        "recursive_scan_completed": True,
        "violations": [],
    }
    assert evidence["git_history"] == {
        "all_trees_reachable_from_head_scanned": True,
        "violations": [],
    }
    assert "does not assert rank/count unlinkability" in evidence["claim_scope"]


def test_repository_boundary_returns_explicit_inability_without_git(
    tmp_path: Path,
) -> None:
    root = tmp_path / "export"
    (root / "docs/evaluations/site-graph-v0").mkdir(parents=True)
    evidence = scan_public_repository_boundary(root)
    assert evidence["passed"] is False
    assert evidence["status"] == "UNABLE_GIT_METADATA_ABSENT"
    assert evidence["git_metadata_available"] is False
    assert "historical public-boundary claim cannot be made" in evidence[
        "inability_reason"
    ]


@pytest.mark.parametrize(
    "relative",
    [
        "private/private-record-evidence.ndjson.gz",
        "exports/artifact-ids.json",
        "exports/mention-dump.json",
    ],
)
def test_repository_boundary_rejects_recursive_current_tree_dump_names(
    tmp_path: Path, relative: str
) -> None:
    repo = tmp_path / "repo"
    _init_boundary_git_repo(repo)
    target = repo / "docs/evaluations/site-graph-v0" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("logic-only adversarial path\n", encoding="utf-8")
    evidence = scan_public_repository_boundary(repo)
    assert evidence["passed"] is False
    assert evidence["status"] == "FAIL"
    assert any(
        row["path"].endswith(relative)
        for row in evidence["current_tree"]["violations"]
    )


def test_repository_boundary_rejects_deleted_dump_in_non_tip_ancestor(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_boundary_git_repo(repo)
    leaked = (
        repo
        / "docs/evaluations/site-graph-v0/exports/mention-rows.ndjson"
    )
    leaked.parent.mkdir(parents=True)
    leaked.write_text("logic-only adversarial history\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "introduce leak"], cwd=repo, check=True)
    leaked.unlink()
    subprocess.run(["git", "add", "-u"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "remove leak"], cwd=repo, check=True)

    evidence = scan_public_repository_boundary(repo)
    assert evidence["passed"] is False
    assert evidence["current_tree"]["violations"] == []
    assert evidence["git_history"]["all_trees_reachable_from_head_scanned"] is True
    assert any(
        row["path"].endswith("exports/mention-rows.ndjson")
        for row in evidence["git_history"]["violations"]
    )


def _fraction(numerator: int, denominator: int) -> dict:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def _legacy_comparator_case(tmp_path: Path) -> dict:
    """Purpose-built logical case; it is not evidence about the Hapi corpus."""
    museums = {
        "met": ["met-a", "met-b"],
        "brooklyn": ["brooklyn-a", "brooklyn-b"],
        "harvard": ["harvard-a"],
    }
    baseline = []
    for museum, artifact_ids in museums.items():
        for artifact_id in artifact_ids:
            target_ids = [] if museum == "harvard" else ["broad-0"]
            baseline.append(
                {
                    "artifact_id": artifact_id,
                    "museum": museum,
                    "extracted_site_text_evidence": True,
                    "baseline_site_target_ids": target_ids,
                    "baseline_record_scope": "no_link" if not target_ids else "broad_only",
                    "has_blocking_ambiguity": False,
                }
            )
    baseline_concentration = {
        "shared_node_count": 1,
        "top_k_unique_record_concentration": {
            "1": {"selected_target_ids": ["broad-0"], "ratio": _fraction(2, 2)}
        },
        "node_incidence_hhi": _fraction(4, 4),
    }
    empty_concentration = {
        "shared_node_count": 0,
        "top_k_unique_record_concentration": {
            "1": {"selected_target_ids": [], "ratio": _fraction(0, 0)}
        },
        "node_incidence_hhi": _fraction(0, 0),
    }
    metrics = {
        "record_counts_by_museum": {museum: len(ids) for museum, ids in museums.items()},
        "per_museum": {
            museum: {"extracted_site_text_evidence_records": len(ids)}
            for museum, ids in museums.items()
        },
        "connectivity": {
            "pairs": {
                "met__brooklyn": {
                    "concentration_by_museum_side": {
                        "met": copy.deepcopy(baseline_concentration),
                        "brooklyn": copy.deepcopy(baseline_concentration),
                    }
                },
                "met__harvard": {
                    "concentration_by_museum_side": {
                        "met": copy.deepcopy(empty_concentration),
                        "harvard": copy.deepcopy(empty_concentration),
                    }
                },
                "brooklyn__harvard": {
                    "concentration_by_museum_side": {
                        "brooklyn": copy.deepcopy(empty_concentration),
                        "harvard": copy.deepcopy(empty_concentration),
                    }
                },
            }
        },
    }
    node_scope = {
        "schema_version": "site-graph-v0-baseline-node-scope/2",
        "nodes": [
            {
                "target_id": "broad-0",
                "scope_class": "broad",
                "authority_identity_locator": "broad-0",
            }
        ],
    }
    opportunities = []
    for museum, artifact_ids in museums.items():
        opportunities.append(
            {
                "opportunity_id": f"opp-{museum}",
                "museum": museum,
                "artifact_ids": artifact_ids,
                "artifact_count": len(artifact_ids),
                "artifact_expansion_sha256": canonical_sha256(artifact_ids),
            }
        )
    side = lambda count: {  # noqa: E731
        "credited_effect_opportunity_denominator": count,
        "minimum_credited_affected_records_for_continue": 1 if count else 0,
    }
    queue = {
        "schema_version": "site-graph-v0-opportunity-ledger/1",
        "selection_algorithm": {"logic_only": True},
        "denominator_policy": "logic-only fixed population",
        "credit_warning": "logic-only inputs make no corpus claim",
        "selected_signature_count": 3,
        "opportunities": opportunities,
        "per_museum": {},
        "pair_side_ceilings": {
            "met__brooklyn": {"sides": {"met": side(2), "brooklyn": side(2)}},
            "met__harvard": {"sides": {"met": side(2), "harvard": side(1)}},
            "brooklyn__harvard": {"sides": {"brooklyn": side(2), "harvard": side(1)}},
        },
    }
    crosswalk = json.loads((EVAL_ROOT / "type-crosswalk.json").read_text())
    hierarchy = {
        "schema_version": "site-graph-v0-candidate-hierarchy/1",
        "coverage": "every_candidate_direct_target_from_complete_available_pinned_sources_not_only_evaluated_slice",
        "source_snapshots": [{"id": "logic-only"}],
        "known_incompleteness": {"logic_only": True},
        "nodes": [
            {
                "target_id": target,
                "candidate_e55_type": "temple",
                "identity_class_id": f"identity-{target}",
                "child_ids": [],
            }
            for target in ("specific-1", "specific-2")
        ],
    }
    queue_path, crosswalk_path, hierarchy_path = (
        tmp_path / "queue.json", tmp_path / "crosswalk.json", tmp_path / "hierarchy.json"
    )
    _write_json(queue_path, queue)
    _write_json(crosswalk_path, crosswalk)
    _write_json(hierarchy_path, hierarchy)
    candidate_records = []
    for museum, artifact_ids in museums.items():
        for index, artifact_id in enumerate(artifact_ids):
            if museum == "harvard":
                candidate_records.append(
                    {
                        "artifact_id": artifact_id, "museum": museum,
                        "opportunity_ids": [f"opp-{museum}"], "resolution_status": "unmatched",
                        "abstention_reason": None, "has_blocking_ambiguity": False,
                        "direct_links": [],
                    }
                )
                continue
            target = f"specific-{index + 1}"
            candidate_records.append(
                {
                    "artifact_id": artifact_id, "museum": museum,
                    "opportunity_ids": [f"opp-{museum}"], "resolution_status": "linked",
                    "abstention_reason": None, "has_blocking_ambiguity": False,
                    "direct_links": [
                        {
                            "target_id": target, "candidate_e55_type": "temple",
                            "scope_class": "specific_candidate", "identity_class_id": f"identity-{target}",
                            "complete_hierarchy_child_count": 0,
                            "ancestor_target_ids": ["broad-0"],
                            "support_decision_id": f"link-{artifact_id}-{target}",
                        }
                    ],
                }
            )
    relations = [
        {
            "baseline_target_id": "broad-0", "candidate_target_id": target,
            "relation": "strict_refinement", "reassignment_review_decision_id": f"refine-{target}",
        }
        for target in ("specific-1", "specific-2")
    ]
    candidate = {
        "schema_version": "site-graph-v0-candidate/1", "candidate_id": "logic-only",
        "scope": "frozen_intent_to_treat_queue", "non_queue_policy": "carry_forward_exact_baseline",
        "opportunity_ledger_sha256": sha256(queue_path),
        "type_crosswalk_sha256": sha256(crosswalk_path),
        "complete_hierarchy_context_sha256": sha256(hierarchy_path),
        "relations_frozen_at_utc": "2026-08-28T00:00:00+00:00",
        "candidate_run_started_at_utc": "2026-08-28T00:01:00+00:00",
        "relations_sha256": canonical_sha256(relations),
        "records": candidate_records,
        "relations": relations,
    }
    review_a, review_b = tmp_path / "review-a.txt", tmp_path / "review-b.txt"
    review_a.write_text("independent human review A\n")
    review_b.write_text("independent human review B\n")

    def decision(decision_id: str, kind: str, subject: dict) -> dict:
        return {
            "decision_id": decision_id, "decision_kind": kind, "subject": subject,
            "independent_source_citations": ["source:logic-only"],
            "reviews": [
                {
                    "reviewer_id": reviewer, "independence_group": reviewer,
                    "outcome": "supported", "method": "human",
                    "artifact_path": path.name, "artifact_sha256": sha256(path),
                    "prompt_path": None, "prompt_sha256": None, "model_selector": None,
                    "backend_model_id": None, "raw_response_path": None,
                    "raw_response_sha256": None,
                }
                for reviewer, path in (("reviewer-a", review_a), ("reviewer-b", review_b))
            ],
        }

    decisions = []
    for record in candidate_records:
        for link in record["direct_links"]:
            decisions.append(
                decision(
                    link["support_decision_id"], "link_support",
                    {"artifact_id": record["artifact_id"], "target_id": link["target_id"],
                     "opportunity_ids": record["opportunity_ids"]},
                )
            )
    for relation in relations:
        decisions.append(
            decision(
                relation["reassignment_review_decision_id"], "strict_refinement_support",
                {"baseline_target_id": relation["baseline_target_id"],
                 "candidate_target_id": relation["candidate_target_id"]},
            )
        )
    reviews = {
        "schema_version": "site-graph-v0-review-ledger/1",
        "review_scope": "census_of_every_candidate_changed_link_and_claimed_strict_refinement",
        "decisions": decisions,
    }
    return {
        "baseline": baseline, "metrics": metrics, "node_scope": node_scope,
        "queue": queue, "crosswalk": crosswalk, "candidate": candidate,
        "hierarchy": hierarchy, "reviews": reviews,
        "paths": {"queue": queue_path, "crosswalk": crosswalk_path, "hierarchy": hierarchy_path},
        "review_root": tmp_path,
    }


def _legacy_run_case(case: dict) -> dict:
    return compare_core(
        case["baseline"], case["metrics"], case["node_scope"], case["queue"],
        case["crosswalk"], case["candidate"], case["hierarchy"], case["reviews"],
        case["paths"], case["review_root"],
    )


def _comparator_case(tmp_path: Path) -> dict:
    """Purpose-built pure-core input; it makes no claim about the Hapi corpus."""
    museums = {
        "met": ["met-a", "met-b"],
        "brooklyn": ["brooklyn-a", "brooklyn-b"],
        "harvard": ["harvard-a"],
    }
    baseline = []
    for museum, artifact_ids in museums.items():
        for artifact_id in artifact_ids:
            targets = [] if museum == "harvard" else ["broad-0"]
            baseline.append(
                {
                    "artifact_id": artifact_id,
                    "museum": museum,
                    "extracted_site_text_evidence": True,
                    "baseline_site_target_ids": targets,
                    "baseline_record_scope": "no_link" if not targets else "broad_only",
                    "site_mention_count": 1 if not targets else 2,
                    "site_mention_status_counts": (
                        {"unmatched": 1}
                        if not targets
                        else {"resolved": 1, "unmatched": 1}
                    ),
                    "has_any_ambiguity": False,
                    "has_blocking_ambiguity": False,
                }
            )
    metrics = {
        "record_counts_by_museum": {museum: len(ids) for museum, ids in museums.items()},
        "per_museum": {
            museum: {"extracted_site_text_evidence_records": len(ids)}
            for museum, ids in museums.items()
        },
    }
    node_scope = {
        "schema_version": "site-graph-v0-baseline-node-scope/2",
        "nodes": [
            {
                "target_id": "broad-0",
                "scope_class": "broad",
                "authority_identity_locator": "broad-0",
            }
        ],
    }
    opportunities = []
    itt_records = {}
    opportunity_binding_by_artifact = {}
    for rank, (museum, artifact_ids) in enumerate(museums.items(), 1):
        opportunity_id = f"opp-{rank:04d}"
        opportunity = {
            "opportunity_id": opportunity_id,
            "selection_rank": rank,
            "selection_reason": "logic_only",
            "museum": museum,
            "unresolved_status_counts": {"unmatched": len(artifact_ids)},
            "mention_count": len(artifact_ids),
            "artifact_count": len(artifact_ids),
            "intent_to_treat": True,
        }
        opportunities.append(opportunity)
        itt_records[museum] = [
            {
                "artifact_id": artifact_id,
                "opportunity_bindings": [
                    {
                        "opportunity_id": opportunity_id,
                        "opportunity_binding_sha256": canonical_sha256(
                            {"artifact_id": artifact_id, "opportunity_id": opportunity_id}
                        ),
                    }
                ],
                "baseline_record_scope": "no_link" if museum == "harvard" else "broad_only",
            }
            for artifact_id in artifact_ids
        ]
        opportunity_binding_by_artifact.update(
            {
                row["artifact_id"]: row["opportunity_bindings"][0]
                for row in itt_records[museum]
            }
        )

    pair_memberships = {}
    pair_summaries = {}
    for left, right in (("met", "brooklyn"), ("met", "harvard"), ("brooklyn", "harvard")):
        key = f"{left}__{right}"
        private_sides, public_sides = {}, {}
        for museum in (left, right):
            category = (
                "broad_only_pair_connection"
                if {left, right} == {"met", "brooklyn"}
                else "no_baseline_pair_connection"
            )
            rows = [
                {
                    "artifact_id": artifact_id,
                    "category": category,
                    "opportunity_bindings": [opportunity_binding_by_artifact[artifact_id]],
                }
                for artifact_id in museums[museum]
            ]
            private_sides[museum] = rows
            public_sides[museum] = {
                "credited_effect_opportunity_denominator": len(rows),
                "minimum_credited_affected_records_for_continue": 1,
            }
        pair_memberships[key] = {"sides": private_sides}
        pair_summaries[key] = {"sides": public_sides}
    queue = {
        "schema_version": "site-graph-v0-opportunity-summary/2",
        "minimum_affected_opportunity_fraction": {"numerator": 1, "denominator": 10},
        "selected_signature_count": 3,
        "opportunities": opportunities,
        "pair_side_ceilings": pair_summaries,
    }
    private_opportunity = {
        "schema_version": "site-graph-v0-private-opportunity-ledger/2",
        "intent_to_treat_records_by_museum": itt_records,
        "credited_pair_opportunity_memberships": pair_memberships,
        "opportunities": [
            {
                **opportunity,
                "artifact_expansion_sha256": canonical_sha256(
                    museums[opportunity["museum"]]
                ),
                "artifact_memberships": [
                    {
                        "artifact_id": artifact_id,
                        "opportunity_binding_sha256": opportunity_binding_by_artifact[
                            artifact_id
                        ]["opportunity_binding_sha256"],
                        "mentions": [
                            {
                                "mention_id": f"mention-{artifact_id}",
                                "field_path": "sites[0]",
                                "status": "unmatched",
                                "target_ids": [],
                                "normalized_keys": [opportunity["opportunity_id"]],
                            }
                        ],
                    }
                    for artifact_id in museums[opportunity["museum"]]
                ],
            }
            for opportunity in opportunities
        ],
    }
    crosswalk = json.loads((EVAL_ROOT / "type-crosswalk.json").read_text())
    snapshot = {
        "schema_version": "site-graph-v0-authority-source-export/2",
        "source_export_id": "logic-source",
        "authority_name": "logic only",
        "source_kind": "unit-test",
        "originating_museum": False,
        "acquired_at_utc": "2026-08-28T00:00:00Z",
        "provenance": {
            "source_locator": "logic://complete-source-export",
            "acquisition_method": "purpose-built unit-test construction",
            "producer_identity": "test fixture",
        },
        "completeness": {
            "coverage_statement": "all two logic-only records",
            "known_incompleteness": ["not corpus evidence"],
            "record_selection_policy": "all_records_in_authenticated_source_export",
            "record_count": 3,
            "records_canonical_sha256": "",
            "complete_for_candidate_target_derivation": True,
        },
        "records": [
            {
                "source_record_id": "source-broad-0",
                "target_id": "broad-0",
                "preferred_label": "Broad zero",
                "aliases": [],
                "authority_identity_locator": "broad-0",
                "raw_source_types": ["archaeological-area"],
                "parent_ids": [],
                "child_ids": ["specific-1", "specific-2"],
                "authority_citations": ["logic:broad-0"],
            }
        ] + [
            {
                "source_record_id": f"source-{target}",
                "target_id": target,
                "preferred_label": target.replace("-", " ").title(),
                "aliases": [],
                "authority_identity_locator": f"logic:authority:{target}",
                "raw_source_types": ["archaeological-site"],
                "parent_ids": ["broad-0"],
                "child_ids": [],
                "authority_citations": [f"logic:{target}"],
            }
            for target in ("specific-1", "specific-2")
        ],
    }
    snapshot["completeness"]["records_canonical_sha256"] = canonical_sha256(
        snapshot["records"]
    )
    hierarchy = {
        "schema_version": "site-graph-v0-candidate-hierarchy/4",
        "coverage": "every_target_and_every_record_from_all_authenticated_complete_authority_source_exports",
        "known_incompleteness": {
            "closed_world_claim": False,
            "limitations": ["logic-only; not corpus evidence"],
            "derivation_statement": "all fixture source records are included",
        },
        "nodes": [
            {
                "target_id": "broad-0",
                "candidate_e55_type": "archaeological_area",
                "child_ids": ["specific-1", "specific-2"],
                "ancestor_target_ids": [],
                "source_export_ids": ["logic-source"],
                "source_record_ids": ["source-broad-0"],
            }
        ] + [
            {
                "target_id": target,
                "candidate_e55_type": "archaeological_site",
                "child_ids": [],
                "ancestor_target_ids": ["broad-0"],
                "source_export_ids": ["logic-source"],
                "source_record_ids": [f"source-{target}"],
            }
            for target in ("specific-1", "specific-2")
        ],
    }
    candidate_records = []
    decisions = {}
    for museum, artifact_ids in museums.items():
        for index, artifact_id in enumerate(artifact_ids):
            if museum == "harvard":
                binding = opportunity_binding_by_artifact[artifact_id]
                candidate_records.append(
                    {
                        "artifact_id": artifact_id,
                        "final_supported_direct_target_ids": [],
                        "removed_baseline_target_ids": [],
                        "opportunity_outcomes": [
                            {
                                **binding,
                                "resolution_status": "unmatched",
                                "status_support_decision_key": None,
                                "abstention_reason": None,
                                "direct_links": [],
                                "uncredited_link_claims": [],
                            }
                        ],
                    }
                )
                continue
            target = f"specific-{index + 1}"
            binding = opportunity_binding_by_artifact[artifact_id]
            subject = {"artifact_id": artifact_id, "target_id": target, **binding}
            key = decision_key("link_support", subject)
            decisions[key] = {
                "decision_kind": "link_support",
                "subject": subject,
                "supported": True,
                "disagreement": False,
            }
            status_subject = {
                "artifact_id": artifact_id,
                "opportunity_id": binding["opportunity_id"],
                "opportunity_binding_sha256": binding[
                    "opportunity_binding_sha256"
                ],
                "mention_ids": [f"mention-{artifact_id}"],
                "baseline_statuses": [
                    {
                        "mention_id": f"mention-{artifact_id}",
                        "status": "unmatched",
                    }
                ],
                "proposed_status": "resolved",
            }
            status_key = decision_key(
                "mention_status_resolution", status_subject
            )
            decisions[status_key] = {
                "decision_kind": "mention_status_resolution",
                "subject": status_subject,
                "supported": True,
                "disagreement": False,
            }
            candidate_records.append(
                {
                    "artifact_id": artifact_id,
                    "final_supported_direct_target_ids": [target],
                    "removed_baseline_target_ids": ["broad-0"],
                    "opportunity_outcomes": [
                        {
                            **binding,
                            "resolution_status": "linked",
                            "status_support_decision_key": status_key,
                            "abstention_reason": None,
                            "direct_links": [
                                {"target_id": target, "support_decision_key": key}
                            ],
                            "uncredited_link_claims": [],
                        }
                    ],
                }
            )
    relations = []
    for target in ("specific-1", "specific-2"):
        subject = {
            "left_target_id": target,
            "right_target_id": "broad-0",
            "relation": "strict_refinement",
        }
        key = decision_key("strict_refinement_support", subject)
        decisions[key] = {
            "decision_kind": "strict_refinement_support",
            "subject": subject,
            "supported": True,
            "disagreement": False,
        }
        relations.append(
            {
                "relation_id": f"refine-{target}",
                **subject,
                "review_decision_key": key,
            }
        )
    distinct_subject = {
        "left_target_id": "specific-1",
        "right_target_id": "specific-2",
        "relation": "distinct",
    }
    distinct_key = decision_key("distinctness_support", distinct_subject)
    decisions[distinct_key] = {
        "decision_kind": "distinctness_support",
        "subject": distinct_subject,
        "supported": True,
        "disagreement": False,
    }
    relations.append(
        {
            "relation_id": "distinct-specific-targets",
            **distinct_subject,
            "review_decision_key": distinct_key,
        }
    )
    relation_ledger = {
        "schema_version": "site-graph-v0-relation-ledger/2",
        "strict_refinement_direction": "left_target_id_is_narrower_than_right_target_id",
        "identity_census_policy": "every_counted_candidate_class_is_censused_against_every_relevant_frozen_baseline_identity_including_one_sided_and_every_other_counted_candidate_class",
        "relations": relations,
    }
    candidate = {"schema_version": "site-graph-v0-candidate-result/6", "records": candidate_records}
    return {
        "baseline": baseline,
        "metrics": metrics,
        "node_scope": node_scope,
        "queue": queue,
        "private_opportunity": private_opportunity,
        "crosswalk": crosswalk,
        "candidate": candidate,
        "hierarchy": hierarchy,
        "snapshots": [snapshot],
        "relations": relation_ledger,
        "decisions": decisions,
    }


def _run_case(case: dict) -> dict:
    return compare_core(
        case["baseline"],
        case["metrics"],
        case["node_scope"],
        case["queue"],
        case["private_opportunity"],
        case["crosswalk"],
        case["candidate"],
        case["hierarchy"],
        case["snapshots"],
        case["relations"],
        case["decisions"],
    )


def _drop_status_resolution(case: dict, outcome: dict) -> None:
    key = outcome.get("status_support_decision_key")
    if key is not None:
        case["decisions"].pop(key)
    outcome["status_support_decision_key"] = None


def _bind_status_resolution(
    case: dict,
    *,
    artifact_id: str,
    outcome: dict,
    baseline_statuses: list[dict],
    proposed_status: str,
) -> str:
    _drop_status_resolution(case, outcome)
    subject = {
        "artifact_id": artifact_id,
        "opportunity_id": outcome["opportunity_id"],
        "opportunity_binding_sha256": outcome["opportunity_binding_sha256"],
        "mention_ids": [row["mention_id"] for row in baseline_statuses],
        "baseline_statuses": baseline_statuses,
        "proposed_status": proposed_status,
    }
    key = decision_key("mention_status_resolution", subject)
    case["decisions"][key] = {
        "decision_kind": "mention_status_resolution",
        "subject": subject,
        "supported": True,
        "disagreement": False,
    }
    outcome["status_support_decision_key"] = key
    return key


def _add_unaffected_itt_records(case: dict, museum: str, count: int) -> None:
    """Expand a logic-only ITT side with baseline-retained, non-credited records."""
    public_opportunity = next(
        row for row in case["queue"]["opportunities"] if row["museum"] == museum
    )
    private_opportunity = next(
        row
        for row in case["private_opportunity"]["opportunities"]
        if row["museum"] == museum
    )
    for index in range(count):
        artifact_id = f"{museum}-filler-{index:02d}"
        binding = {
            "opportunity_id": public_opportunity["opportunity_id"],
            "opportunity_binding_sha256": canonical_sha256(
                {
                    "artifact_id": artifact_id,
                    "opportunity_id": public_opportunity["opportunity_id"],
                }
            ),
        }
        case["baseline"].append(
            {
                "artifact_id": artifact_id,
                "museum": museum,
                "extracted_site_text_evidence": True,
                "baseline_site_target_ids": ["broad-0"],
                "baseline_record_scope": "broad_only",
                "site_mention_count": 2,
                "site_mention_status_counts": {"resolved": 1, "unmatched": 1},
                "has_any_ambiguity": False,
                "has_blocking_ambiguity": False,
            }
        )
        case["metrics"]["record_counts_by_museum"][museum] += 1
        case["metrics"]["per_museum"][museum][
            "extracted_site_text_evidence_records"
        ] += 1
        case["private_opportunity"]["intent_to_treat_records_by_museum"][museum].append(
            {
                "artifact_id": artifact_id,
                "opportunity_bindings": [binding],
                "baseline_record_scope": "broad_only",
            }
        )
        private_opportunity["artifact_memberships"].append(
            {
                "artifact_id": artifact_id,
                "opportunity_binding_sha256": binding["opportunity_binding_sha256"],
                "mentions": [
                    {
                        "mention_id": f"mention-{artifact_id}",
                        "field_path": "sites[0]",
                        "status": "unmatched",
                        "target_ids": [],
                        "normalized_keys": [binding["opportunity_id"]],
                    }
                ],
            }
        )
        case["candidate"]["records"].append(
            {
                "artifact_id": artifact_id,
                "final_supported_direct_target_ids": ["broad-0"],
                "removed_baseline_target_ids": [],
                "opportunity_outcomes": [
                    {
                        **binding,
                        "resolution_status": "unmatched",
                        "status_support_decision_key": None,
                        "abstention_reason": None,
                        "direct_links": [],
                        "uncredited_link_claims": [],
                    }
                ],
            }
        )
        for pair_key, pair in case["private_opportunity"][
            "credited_pair_opportunity_memberships"
        ].items():
            if museum not in pair["sides"]:
                continue
            pair["sides"][museum].append(
                {
                    "artifact_id": artifact_id,
                    "category": (
                        "broad_only_pair_connection"
                        if pair_key == "met__brooklyn"
                        else "no_baseline_pair_connection"
                    ),
                    "opportunity_bindings": [binding],
                }
            )
    for pair_key, pair in case["private_opportunity"][
        "credited_pair_opportunity_memberships"
    ].items():
        if museum not in pair["sides"]:
            continue
        denominator = len(pair["sides"][museum])
        public_side = case["queue"]["pair_side_ceilings"][pair_key]["sides"][museum]
        public_side["credited_effect_opportunity_denominator"] = denominator
        public_side["minimum_credited_affected_records_for_continue"] = max(
            1, (denominator + 9) // 10
        )


def test_supported_strict_refinement_replaces_direct_edge_without_counting_loss(tmp_path: Path) -> None:
    report = _run_case(_comparator_case(tmp_path))
    assert report["outcome"] == "CONTINUE"
    assert report["event_counts"]["strict_refinement_reassignment"] == 4
    assert report["event_counts"]["loss"] == 0
    assert report["reassignment_edge_modes"] == {
        "old_direct_edge_replaced_ancestor_semantics_preserved": 4
    }
    assert report["pairs"]["met__brooklyn"][
        "gained_credited_specific_shared_identity_class_count"
    ] == 2


def test_post_candidate_linkability_and_connectivity_are_computed_exactly(
    tmp_path: Path,
) -> None:
    report = _run_case(_comparator_case(tmp_path))
    schema_validation_module.validate_schema(
        report,
        EVAL_ROOT / "schemas/comparison-report.schema.json",
        "logic-only full candidate metric report",
    )
    wrong_pair_sides = copy.deepcopy(report)
    sides = wrong_pair_sides["post_candidate_metrics"]["connectivity"]["pairs"][
        "met__brooklyn"
    ]["sides"]
    sides["harvard"] = sides.pop("brooklyn")
    with pytest.raises(schema_validation_module.SchemaValidationError):
        schema_validation_module.validate_schema(
            wrong_pair_sides,
            EVAL_ROOT / "schemas/comparison-report.schema.json",
            "logic-only wrong pair-side metric report",
        )
    metrics = report["post_candidate_metrics"]
    assert metrics["linkability_by_museum"] == {
        "met": {
            "records_with_supported_direct_links": 2,
            "overall_linkability": _fraction(2, 2),
            "extracted_site_text_conditional_linkability": _fraction(2, 2),
        },
        "brooklyn": {
            "records_with_supported_direct_links": 2,
            "overall_linkability": _fraction(2, 2),
            "extracted_site_text_conditional_linkability": _fraction(2, 2),
        },
        "harvard": {
            "records_with_supported_direct_links": 0,
            "overall_linkability": _fraction(0, 1),
            "extracted_site_text_conditional_linkability": _fraction(0, 1),
        },
    }
    pair = metrics["connectivity"]["pairs"]["met__brooklyn"]
    assert pair["shared_identity_class_count"] == 2
    assert pair["sides"]["met"]["connected_records"] == 2
    assert pair["sides"]["met"]["overall_connection_rate"] == _fraction(2, 2)
    assert pair["sides"]["brooklyn"][
        "extracted_site_text_conditional_connection_rate"
    ] == _fraction(2, 2)
    assert metrics["connectivity"]["all_three"]["shared_identity_class_count"] == 0
    assert metrics["connectivity"]["any_two_or_more"][
        "shared_identity_class_count"
    ] == 2
    assert metrics["connectivity"]["any_two_or_more"][
        "exact_museum_combination_counts"
    ] == {"brooklyn+met": 2}


def test_selected_research_failure_preserves_unrelated_frozen_resolved_link(
    tmp_path: Path,
) -> None:
    case = _comparator_case(tmp_path)
    record = next(row for row in case["candidate"]["records"] if row["artifact_id"] == "met-a")
    outcome = record["opportunity_outcomes"][0]
    support_key = outcome["direct_links"][0]["support_decision_key"]
    del case["decisions"][support_key]
    _drop_status_resolution(case, outcome)
    outcome["resolution_status"] = "research_failure"
    outcome["direct_links"] = []
    record["final_supported_direct_target_ids"] = ["broad-0"]
    record["removed_baseline_target_ids"] = []
    report = _run_case(case)
    event = next(row for row in report["event_records"] if row["artifact_id"] == "met-a")
    assert report["outcome"] == "STOP"
    assert event["event"] == "unchanged"
    assert event["candidate_supported_direct_target_ids"] == ["broad-0"]
    assert event["candidate_site_mention_status_counts"] == {
        "resolved": 1,
        "unmatched": 1,
    }
    assert report["event_counts"]["loss"] == 0


def test_explicit_record_level_removal_drives_loss_and_redesign(tmp_path: Path) -> None:
    case = _comparator_case(tmp_path)
    record = next(row for row in case["candidate"]["records"] if row["artifact_id"] == "met-a")
    outcome = record["opportunity_outcomes"][0]
    del case["decisions"][outcome["direct_links"][0]["support_decision_key"]]
    _drop_status_resolution(case, outcome)
    outcome["resolution_status"] = "research_failure"
    outcome["direct_links"] = []
    record["final_supported_direct_target_ids"] = []
    record["removed_baseline_target_ids"] = ["broad-0"]
    report = _run_case(case)
    assert report["outcome"] == "REDESIGN"
    assert report["event_counts"]["loss"] == 1
    assert report["safety_gates"]["baseline_retention"]["passed"] is False


def test_supported_link_with_another_ambiguous_mention_is_not_blocking(
    tmp_path: Path,
) -> None:
    case = _comparator_case(tmp_path)
    baseline = next(row for row in case["baseline"] if row["artifact_id"] == "met-a")
    baseline["site_mention_count"] = 3
    baseline["site_mention_status_counts"] = {
        "ambiguous": 1,
        "resolved": 1,
        "unmatched": 1,
    }
    baseline["has_any_ambiguity"] = True
    baseline["has_blocking_ambiguity"] = False
    report = _run_case(case)
    event = next(row for row in report["event_records"] if row["artifact_id"] == "met-a")
    assert report["outcome"] == "CONTINUE"
    assert event["candidate_site_mention_status_counts"]["ambiguous"] == 1
    assert report["safety_gates"]["ambiguity"]["per_museum"]["met"][
        "candidate_blocking"
    ] == _fraction(0, 2)


def test_unselected_baseline_ambiguity_persists_in_candidate_population(
    tmp_path: Path,
) -> None:
    case = _comparator_case(tmp_path)
    baseline = next(row for row in case["baseline"] if row["artifact_id"] == "harvard-a")
    baseline["site_mention_count"] = 2
    baseline["site_mention_status_counts"] = {"ambiguous": 1, "unmatched": 1}
    baseline["has_any_ambiguity"] = True
    baseline["has_blocking_ambiguity"] = True
    report = _run_case(case)
    assert report["outcome"] == "CONTINUE"
    ambiguity = report["safety_gates"]["ambiguity"]["per_museum"]["harvard"]
    assert ambiguity["baseline_blocking"] == _fraction(1, 1)
    assert ambiguity["candidate_blocking"] == _fraction(1, 1)
    assert ambiguity["newly_blocking_rate"] == {"numerator": 0, "denominator": 1}
    assert ambiguity["net_delta_descriptive"] == {"numerator": 0, "denominator": 1}


def test_disputed_link_is_unresolved_and_cannot_suppress_ambiguity(
    tmp_path: Path,
) -> None:
    case = _comparator_case(tmp_path)
    baseline = next(row for row in case["baseline"] if row["artifact_id"] == "harvard-a")
    baseline["site_mention_status_counts"] = {"ambiguous": 1}
    baseline["has_any_ambiguity"] = True
    baseline["has_blocking_ambiguity"] = True
    private_opportunity = next(
        row
        for row in case["private_opportunity"]["opportunities"]
        if row["museum"] == "harvard"
    )
    private_opportunity["artifact_memberships"][0]["mentions"][0]["status"] = "ambiguous"
    record = next(row for row in case["candidate"]["records"] if row["artifact_id"] == "harvard-a")
    outcome = record["opportunity_outcomes"][0]
    _drop_status_resolution(case, outcome)
    subject = {
        "artifact_id": "harvard-a",
        "target_id": "specific-1",
        "opportunity_id": outcome["opportunity_id"],
        "opportunity_binding_sha256": outcome["opportunity_binding_sha256"],
    }
    key = decision_key("link_support", subject)
    case["decisions"][key] = {
        "decision_kind": "link_support",
        "subject": subject,
        "supported": False,
        "disagreement": True,
    }
    outcome["resolution_status"] = "unresolved"
    outcome["uncredited_link_claims"] = [
        {"target_id": "specific-1", "support_decision_key": key}
    ]
    report = _run_case(case)
    assert report["outcome"] == "CONTINUE"
    assert report["safety_gates"]["ambiguity"]["per_museum"]["harvard"][
        "candidate_blocking"
    ] == _fraction(1, 1)
    assert report["ambiguity_and_abstention"][
        "reviewer_disagreement_decisions_uncredited"
    ] == 1


def test_new_blocking_ambiguity_drives_redesign_threshold(tmp_path: Path) -> None:
    case = _comparator_case(tmp_path)
    record = next(row for row in case["candidate"]["records"] if row["artifact_id"] == "harvard-a")
    outcome = record["opportunity_outcomes"][0]
    _bind_status_resolution(
        case,
        artifact_id="harvard-a",
        outcome=outcome,
        baseline_statuses=[
            {"mention_id": "mention-harvard-a", "status": "unmatched"}
        ],
        proposed_status="ambiguous",
    )
    outcome["resolution_status"] = "ambiguous"
    report = _run_case(case)
    assert report["outcome"] == "REDESIGN"
    ambiguity = report["safety_gates"]["ambiguity"]["per_museum"]["harvard"]
    assert ambiguity["passed"] is False
    assert ambiguity["newly_blocking_rate"] == {"numerator": 1, "denominator": 1}
    assert ambiguity["net_delta_descriptive"] == {"numerator": 1, "denominator": 1}


def test_linked_outcome_without_review_support_is_invalid(tmp_path: Path) -> None:
    case = _comparator_case(tmp_path)
    first_link = next(
        value
        for value in case["decisions"].values()
        if value["decision_kind"] == "link_support"
    )
    first_link["supported"] = False
    report = _run_case(case)
    assert report["outcome"] == "INVALID"
    assert any(
        "disputed or unsupported and must instead be unresolved" in error
        for error in report["integrity"]["errors"]
    )


def test_slice_leafness_cannot_override_complete_hierarchy_context(tmp_path: Path) -> None:
    case = _comparator_case(tmp_path)
    node = next(
        row for row in case["hierarchy"]["nodes"] if row["target_id"] == "specific-1"
    )
    record = next(
        row for row in case["snapshots"][0]["records"] if row["target_id"] == "specific-1"
    )
    node["child_ids"] = ["omitted-from-slice-child"]
    record["child_ids"] = ["omitted-from-slice-child"]
    case["snapshots"][0]["completeness"]["records_canonical_sha256"] = canonical_sha256(
        case["snapshots"][0]["records"]
    )
    report = _run_case(case)
    assert report["outcome"] == "INVALID"
    assert any("without source records" in error for error in report["integrity"]["errors"])


def test_reviewer_disagreement_is_uncredited_and_unresolved(tmp_path: Path) -> None:
    case = _comparator_case(tmp_path)
    first_link = next(
        value for value in case["decisions"].values()
        if value["decision_kind"] == "link_support"
    )
    first_link["supported"] = False
    first_link["disagreement"] = True
    decision_key_value = next(
        key for key, value in case["decisions"].items() if value is first_link
    )
    record = next(
        row
        for row in case["candidate"]["records"]
        if row["opportunity_outcomes"][0]["direct_links"]
        and row["opportunity_outcomes"][0]["direct_links"][0]["support_decision_key"]
        == decision_key_value
    )
    outcome = record["opportunity_outcomes"][0]
    _drop_status_resolution(case, outcome)
    outcome["resolution_status"] = "unresolved"
    outcome["uncredited_link_claims"] = outcome.pop("direct_links")
    outcome["direct_links"] = []
    record["final_supported_direct_target_ids"] = ["broad-0"]
    record["removed_baseline_target_ids"] = []
    report = _run_case(case)
    assert report["outcome"] == "STOP"
    assert report["ambiguity_and_abstention"]["reviewer_disagreement_decisions_uncredited"] == 1
    assert report["event_counts"]["loss"] == 0
    assert report["event_counts"]["unchanged"] == 2


def test_mention_plausibility_counts_only_authenticated_supported_targets(
    tmp_path: Path,
) -> None:
    case = _comparator_case(tmp_path)
    record = next(
        row
        for row in case["candidate"]["records"]
        if row["artifact_id"] == "harvard-a"
    )
    outcome = record["opportunity_outcomes"][0]
    _drop_status_resolution(case, outcome)
    outcome["resolution_status"] = "unresolved"
    outcome["direct_links"] = []
    outcome["uncredited_link_claims"] = []
    for target_id in ("specific-1", "specific-2"):
        subject = {
            "artifact_id": "harvard-a",
            "target_id": target_id,
            "opportunity_id": outcome["opportunity_id"],
            "opportunity_binding_sha256": outcome["opportunity_binding_sha256"],
        }
        key = decision_key("link_support", subject)
        case["decisions"][key] = {
            "decision_kind": "link_support",
            "subject": subject,
            "supported": False,
            "disagreement": True,
        }
        outcome["uncredited_link_claims"].append(
            {"target_id": target_id, "support_decision_key": key}
        )
    report = _run_case(case)
    assert report["outcome"] == "CONTINUE"
    assert not any(
        "more unique authenticated supported targets" in error
        for error in report["integrity"]["errors"]
    )


def test_concentration_formulas_use_unique_record_union_and_incidence_hhi() -> None:
    from metrics_core import concentration

    links = {
        "a": {"x", "y"},
        "b": {"x"},
        "c": {"y"},
    }
    result = concentration(links, {"a", "b", "c"}, {"x", "y"})
    assert result["top_k_unique_record_concentration"]["1"]["ratio"] == _fraction(2, 3)
    assert result["top_k_unique_record_concentration"]["5"]["ratio"] == _fraction(3, 3)
    assert result["top_k_unique_record_concentration"]["10"]["ratio"] == _fraction(3, 3)
    assert result["node_incidence_hhi"] == _fraction(8, 16)


def test_top_k_and_hhi_concentration_failures_drive_redesign(tmp_path: Path) -> None:
    case = _comparator_case(tmp_path)
    for artifact_id in ("met-b", "brooklyn-b"):
        baseline = next(
            row for row in case["baseline"] if row["artifact_id"] == artifact_id
        )
        baseline["baseline_site_target_ids"] = ["broad-1"]
        record = next(
            row for row in case["candidate"]["records"] if row["artifact_id"] == artifact_id
        )
        outcome = record["opportunity_outcomes"][0]
        del case["decisions"][outcome["direct_links"][0]["support_decision_key"]]
        subject = {
            "artifact_id": artifact_id,
            "target_id": "specific-1",
            "opportunity_id": outcome["opportunity_id"],
            "opportunity_binding_sha256": outcome["opportunity_binding_sha256"],
        }
        key = decision_key("link_support", subject)
        case["decisions"][key] = {
            "decision_kind": "link_support",
            "subject": subject,
            "supported": True,
            "disagreement": False,
        }
        outcome["direct_links"] = [
            {"target_id": "specific-1", "support_decision_key": key}
        ]
        record["final_supported_direct_target_ids"] = ["specific-1"]
        record["removed_baseline_target_ids"] = ["broad-1"]

    case["node_scope"]["nodes"].append(
        {
            "target_id": "broad-1",
            "scope_class": "broad",
            "authority_identity_locator": "broad-1",
        }
    )
    snapshot = case["snapshots"][0]
    snapshot["records"].append(
        {
            "source_record_id": "source-broad-1",
            "target_id": "broad-1",
            "preferred_label": "Broad one",
            "aliases": [],
            "authority_identity_locator": "broad-1",
            "raw_source_types": ["archaeological-area"],
            "parent_ids": [],
            "child_ids": ["specific-1"],
            "authority_citations": ["logic:broad-1"],
        }
    )
    specific_record = next(
        row for row in snapshot["records"] if row["target_id"] == "specific-1"
    )
    specific_record["parent_ids"] = ["broad-0", "broad-1"]
    snapshot["records"].sort(key=lambda row: row["source_record_id"])
    snapshot["completeness"]["record_count"] = len(snapshot["records"])
    snapshot["completeness"]["records_canonical_sha256"] = canonical_sha256(
        snapshot["records"]
    )
    case["hierarchy"]["nodes"].append(
        {
            "target_id": "broad-1",
            "candidate_e55_type": "archaeological_area",
            "child_ids": ["specific-1"],
            "ancestor_target_ids": [],
            "source_export_ids": ["logic-source"],
            "source_record_ids": ["source-broad-1"],
        }
    )
    specific_node = next(
        row for row in case["hierarchy"]["nodes"] if row["target_id"] == "specific-1"
    )
    specific_node["ancestor_target_ids"] = ["broad-0", "broad-1"]
    subject = {
        "left_target_id": "specific-1",
        "right_target_id": "broad-1",
        "relation": "strict_refinement",
    }
    key = decision_key("strict_refinement_support", subject)
    case["decisions"][key] = {
        "decision_kind": "strict_refinement_support",
        "subject": subject,
        "supported": True,
        "disagreement": False,
    }
    case["relations"]["relations"].append(
        {
            "relation_id": "refine-specific-1-broad-1",
            **subject,
            "review_decision_key": key,
        }
    )
    report = _run_case(case)
    assert report["outcome"] == "REDESIGN"
    side = report["pairs"]["met__brooklyn"]["sides"]["met"]
    assert side["top_k_concentration_pass"] == {
        "1": False,
        "5": True,
        "10": True,
    }
    assert side["hhi_concentration_pass"] is False
    assert side["concentration_pass"] is False


@pytest.mark.parametrize("failed_metric", ["top_k", "hhi"])
def test_each_concentration_gate_independently_drives_redesign(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failed_metric: str
) -> None:
    """Prove neither independently preregistered concentration gate is masked."""
    baseline_metric = {
        "shared_node_count": 2,
        "distinct_connected_records": 10,
        "node_incidence_total": 20,
        "node_incidence_hhi": _fraction(1, 2),
        "top_k_unique_record_concentration": {
            "1": {"selected_target_ids": ["first"], "ratio": _fraction(1, 2)},
            "5": {
                "selected_target_ids": ["first", "second"],
                "ratio": _fraction(1, 1),
            },
            "10": {
                "selected_target_ids": ["first", "second"],
                "ratio": _fraction(1, 1),
            },
        },
    }
    calls = 0

    def controlled_concentration(*_args: object, **_kwargs: object) -> dict:
        nonlocal calls
        candidate_call = calls % 2 == 1
        calls += 1
        result = copy.deepcopy(baseline_metric)
        if candidate_call and failed_metric == "top_k":
            result["top_k_unique_record_concentration"]["1"]["ratio"] = _fraction(
                3, 5
            )
        if candidate_call and failed_metric == "hhi":
            result["node_incidence_hhi"] = _fraction(3, 5)
        return result

    monkeypatch.setattr(
        compare_candidate_module, "concentration", controlled_concentration
    )
    report = _run_case(_comparator_case(tmp_path))
    assert report["outcome"] == "REDESIGN"
    side = report["pairs"]["met__brooklyn"]["sides"]["met"]
    if failed_metric == "top_k":
        assert side["top_k_concentration_pass"]["1"] is False
        assert side["hhi_concentration_pass"] is True
    else:
        assert all(side["top_k_concentration_pass"].values())
        assert side["hhi_concentration_pass"] is False


def test_equivalent_identity_classes_cannot_fake_two_gained_nodes(tmp_path: Path) -> None:
    case = _comparator_case(tmp_path)
    subject = {
        "left_target_id": "specific-1",
        "right_target_id": "specific-2",
        "relation": "equivalent",
    }
    key = decision_key("equivalence_support", subject)
    old_relation = case["relations"]["relations"].pop()
    del case["decisions"][old_relation["review_decision_key"]]
    case["decisions"][key] = {
        "decision_kind": "equivalence_support",
        "subject": subject,
        "supported": True,
        "disagreement": False,
    }
    case["relations"]["relations"].append(
        {
            "relation_id": "equivalent-specific-aliases",
            **subject,
            "review_decision_key": key,
        }
    )
    report = _run_case(case)
    assert report["outcome"] == "STOP"
    assert report["pairs"]["met__brooklyn"][
        "gained_credited_specific_shared_identity_class_count"
    ] == 1


def test_equivalent_alias_replacement_is_unchanged_and_never_affected_credit(
    tmp_path: Path,
) -> None:
    case = _comparator_case(tmp_path)
    relation = next(
        row
        for row in case["relations"]["relations"]
        if row["relation"] == "strict_refinement"
        and row["left_target_id"] == "specific-1"
    )
    del case["decisions"][relation["review_decision_key"]]
    subject = {
        "left_target_id": "specific-1",
        "right_target_id": "broad-0",
        "relation": "equivalent",
    }
    key = decision_key("equivalence_support", subject)
    case["decisions"][key] = {
        "decision_kind": "equivalence_support",
        "subject": subject,
        "supported": True,
        "disagreement": False,
    }
    relation.clear()
    relation.update(
        {
            "relation_id": "equivalent-specific-1-broad-0",
            **subject,
            "review_decision_key": key,
        }
    )
    report = _run_case(case)
    assert report["outcome"] == "STOP"
    assert report["event_counts"]["unchanged"] == 3
    assert report["event_counts"]["strict_refinement_reassignment"] == 2
    pair = report["pairs"]["met__brooklyn"]
    assert pair["gained_credited_specific_shared_identity_class_count"] == 1
    assert pair["sides"]["met"]["credited_affected_records"] == 1
    assert pair["sides"]["brooklyn"]["credited_affected_records"] == 1


def test_pair_numerator_intersects_exact_private_membership_and_category(tmp_path: Path) -> None:
    case = _comparator_case(tmp_path)
    private_side = case["private_opportunity"]["credited_pair_opportunity_memberships"][
        "met__brooklyn"
    ]["sides"]["met"]
    private_side[:] = [
        {
            "artifact_id": "met-a",
            "category": "no_baseline_pair_connection",
            "opportunity_bindings": case["private_opportunity"]
            ["intent_to_treat_records_by_museum"]["met"][0]["opportunity_bindings"],
        }
    ]
    public_side = case["queue"]["pair_side_ceilings"]["met__brooklyn"]["sides"]["met"]
    public_side["credited_effect_opportunity_denominator"] = 1
    public_side["minimum_credited_affected_records_for_continue"] = 1
    report = _run_case(case)
    assert report["outcome"] == "INVALID"
    assert any(
        "raw category is inconsistent with authenticated baseline identity classes"
        in error
        for error in report["integrity"]["errors"]
    )


def test_exact_itt_affected_threshold_failure_drives_stop(tmp_path: Path) -> None:
    case = _comparator_case(tmp_path)
    _add_unaffected_itt_records(case, "met", 9)
    _add_unaffected_itt_records(case, "brooklyn", 9)

    met_a = next(
        row for row in case["candidate"]["records"] if row["artifact_id"] == "met-a"
    )
    met_a_outcome = met_a["opportunity_outcomes"][0]
    subject = {
        "artifact_id": "met-a",
        "target_id": "specific-2",
        "opportunity_id": met_a_outcome["opportunity_id"],
        "opportunity_binding_sha256": met_a_outcome["opportunity_binding_sha256"],
    }
    support_key = decision_key("link_support", subject)
    case["decisions"][support_key] = {
        "decision_kind": "link_support",
        "subject": subject,
        "supported": True,
        "disagreement": False,
    }
    met_a_outcome["direct_links"].append(
        {"target_id": "specific-2", "support_decision_key": support_key}
    )
    met_a["final_supported_direct_target_ids"] = ["specific-1", "specific-2"]
    met_a_baseline = next(
        row for row in case["baseline"] if row["artifact_id"] == "met-a"
    )
    met_a_baseline["site_mention_count"] = 3
    met_a_baseline["site_mention_status_counts"] = {"resolved": 1, "unmatched": 2}
    met_opportunity = next(
        row
        for row in case["private_opportunity"]["opportunities"]
        if row["museum"] == "met"
    )
    met_a_membership = next(
        row
        for row in met_opportunity["artifact_memberships"]
        if row["artifact_id"] == "met-a"
    )
    met_a_membership["mentions"].append(
        {
            "mention_id": "mention-met-a-extra",
            "field_path": "sites[1]",
            "status": "unmatched",
            "target_ids": [],
            "normalized_keys": [met_opportunity["opportunity_id"]],
        }
    )
    _bind_status_resolution(
        case,
        artifact_id="met-a",
        outcome=met_a_outcome,
        baseline_statuses=[
            {"mention_id": "mention-met-a", "status": "unmatched"},
            {"mention_id": "mention-met-a-extra", "status": "unmatched"},
        ],
        proposed_status="resolved",
    )

    met_b = next(
        row for row in case["candidate"]["records"] if row["artifact_id"] == "met-b"
    )
    met_b_outcome = met_b["opportunity_outcomes"][0]
    del case["decisions"][met_b_outcome["direct_links"][0]["support_decision_key"]]
    _drop_status_resolution(case, met_b_outcome)
    met_b_outcome["resolution_status"] = "research_failure"
    met_b_outcome["direct_links"] = []
    met_b["final_supported_direct_target_ids"] = ["broad-0"]
    met_b["removed_baseline_target_ids"] = []

    report = _run_case(case)
    assert report["outcome"] == "STOP"
    pair = report["pairs"]["met__brooklyn"]
    assert pair["gained_credited_specific_shared_identity_class_count"] == 2
    met_side = pair["sides"]["met"]
    assert met_side["credited_affected_records"] == 1
    assert met_side["fixed_opportunity_denominator"] == 11
    assert met_side["minimum_for_continue"] == 2
    assert met_side["affected_threshold_pass"] is False
    assert report["safety_gates"]["baseline_retention"]["passed"] is True


def test_existing_target_cannot_be_relabelled_by_candidate_snapshot(tmp_path: Path) -> None:
    case = _comparator_case(tmp_path)
    case["node_scope"]["nodes"].append(
        {
            "target_id": "other-broad",
            "scope_class": "broad",
            "authority_identity_locator": "logic:authority:other-broad",
        }
    )
    case["snapshots"][0]["records"].append(
        {
            "source_record_id": "source-other-broad",
            "target_id": "other-broad",
            "preferred_label": "Other broad",
            "aliases": [],
            "authority_identity_locator": "logic:authority:other-broad",
            "raw_source_types": ["archaeological-site"],
            "parent_ids": [],
            "child_ids": [],
            "authority_citations": ["logic:broad-0"],
        }
    )
    case["snapshots"][0]["records"].sort(key=lambda row: row["source_record_id"])
    case["snapshots"][0]["completeness"]["record_count"] = 4
    case["snapshots"][0]["completeness"]["records_canonical_sha256"] = canonical_sha256(
        case["snapshots"][0]["records"]
    )
    case["hierarchy"]["nodes"].append(
        {
            "target_id": "other-broad",
            "candidate_e55_type": "archaeological_site",
            "child_ids": [],
            "ancestor_target_ids": [],
            "source_export_ids": ["logic-source"],
            "source_record_ids": ["source-other-broad"],
        }
    )
    report = _run_case(case)
    assert report["outcome"] == "INVALID"
    assert any("cannot be relabeled" in error for error in report["integrity"]["errors"])


def test_candidate_e55_label_must_match_crosswalk_broad_precedence(
    tmp_path: Path,
) -> None:
    case = _comparator_case(tmp_path)
    records = case["snapshots"][0]["records"]
    specific_1 = next(row for row in records if row["target_id"] == "specific-1")
    specific_2 = next(row for row in records if row["target_id"] == "specific-2")
    specific_1["child_ids"] = ["specific-2"]
    specific_2["parent_ids"] = ["broad-0", "specific-1"]
    case["snapshots"][0]["completeness"]["records_canonical_sha256"] = canonical_sha256(
        records
    )
    hierarchy_1 = next(
        row for row in case["hierarchy"]["nodes"] if row["target_id"] == "specific-1"
    )
    hierarchy_2 = next(
        row for row in case["hierarchy"]["nodes"] if row["target_id"] == "specific-2"
    )
    hierarchy_1["child_ids"] = ["specific-2"]
    hierarchy_2["ancestor_target_ids"] = ["broad-0", "specific-1"]
    report = _run_case(case)
    assert report["outcome"] == "INVALID"
    assert any(
        "E55 type is inconsistent with derived broad-precedence scope" in error
        for error in report["integrity"]["errors"]
    )


def test_minimum_fraction_cannot_be_overridden_by_public_aggregate(tmp_path: Path) -> None:
    case = _comparator_case(tmp_path)
    case["queue"]["minimum_affected_opportunity_fraction"] = {
        "numerator": 1,
        "denominator": 2,
    }
    report = _run_case(case)
    assert report["outcome"] == "INVALID"
    assert any("executable constant" in error for error in report["integrity"]["errors"])


def test_multi_target_concentration_is_hash_seed_deterministic() -> None:
    code = f"""
import json, sys
sys.path.insert(0, {str(SCRIPTS)!r})
from metrics_core import concentration
links = {{'a': {{'x', 'y'}}, 'b': {{'x'}}, 'c': {{'y'}}}}
print(json.dumps(concentration(links, {{'a','b','c'}}, {{'x','y'}}), sort_keys=True, separators=(',', ':')))
"""
    outputs = []
    for seed in ("1", "99991"):
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = seed
        result = subprocess.run(
            [sys.executable, "-B", "-c", code],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        outputs.append(result.stdout.encode())
    assert outputs[0] == outputs[1]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _candidate_git_fixture(tmp_path: Path) -> dict:
    repo = tmp_path / "candidate-repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "logic@example.invalid")
    _git(repo, "config", "user.name", "Logic Fixture")
    paths = {
        "hierarchy": "candidate/hierarchy.json",
        "relations": "candidate/relations.json",
        "source": "candidate/source.json",
        "freeze": "candidate/freeze.json",
        "result": "candidate/result.json",
        "reviews": "candidate/reviews.json",
    }
    (repo / "candidate").mkdir()
    source = {
        "schema_version": "site-graph-v0-candidate-source-snapshot/1",
        "source_snapshot_id": "logic-source",
        "authority_name": "logic only",
        "source_kind": "unit-test",
        "acquired_at_utc": "2026-08-28T00:00:00Z",
        "provenance": {"purpose": "logic-only"},
        "completeness": {
            "coverage_statement": "complete one-row logic input",
            "known_incompleteness": ["not corpus evidence"],
            "complete_for_candidate_target_derivation": True,
        },
        "records": [
            {
                "source_record_id": "source-specific",
                "target_id": "specific",
                "source_types": ["temple"],
                "parent_ids": ["broad"],
                "child_ids": [],
                "authority_citations": ["logic:specific"],
            }
        ],
    }
    hierarchy = {
        "schema_version": "site-graph-v0-candidate-hierarchy/2",
        "coverage": "every_candidate_target_from_all_frozen_available_source_snapshot_records_not_only_evaluated_slice",
        "known_incompleteness": {"logic_only": True},
        "nodes": [
            {
                "target_id": "specific",
                "candidate_e55_type": "temple",
                "child_ids": [],
                "ancestor_target_ids": ["broad"],
                "source_snapshot_ids": ["logic-source"],
                "source_record_ids": ["source-specific"],
            }
        ],
    }
    relations = {
        "schema_version": "site-graph-v0-relation-ledger/1",
        "strict_refinement_direction": "left_target_id_is_narrower_than_right_target_id",
        "relations": [],
    }
    for key, value in (("source", source), ("hierarchy", hierarchy), ("relations", relations)):
        _write_json(repo / paths[key], value)
    _git(repo, "add", "candidate")
    _git(repo, "commit", "-qm", "candidate inputs")
    input_commit = _git(repo, "rev-parse", "HEAD")
    schema_by_role = {
        "hierarchy": hierarchy["schema_version"],
        "relations": relations["schema_version"],
        "source": source["schema_version"],
    }
    role_by_key = {
        "hierarchy": "hierarchy",
        "relations": "relation_ledger",
        "source": "source_snapshot",
    }
    files = []
    for key in ("hierarchy", "relations", "source"):
        files.append(
            {
                "role": role_by_key[key],
                "path": paths[key],
                "sha256": sha256(repo / paths[key]),
                "git_blob_oid": _git(repo, "rev-parse", f"HEAD:{paths[key]}"),
                "schema_version": schema_by_role[key],
            }
        )
    release_hash, private_hash = "a" * 64, "b" * 64
    freeze = {
        "schema_version": "site-graph-v0-candidate-freeze-manifest/1",
        "contract_version": "site-graph-v0/2",
        "release_manifest_sha256": release_hash,
        "private_opportunity_ledger_canonical_sha256": private_hash,
        "created_at_utc": "2026-08-28T00:01:00Z",
        "created_by": "logic-fixture",
        "provenance": {"input_commit": input_commit},
        "files": files,
    }
    _write_json(repo / paths["freeze"], freeze)
    _git(repo, "add", paths["freeze"])
    _git(repo, "commit", "-qm", "freeze candidate inputs")
    freeze_commit = _git(repo, "rev-parse", "HEAD")
    freeze_blob = _git(repo, "rev-parse", f"HEAD:{paths['freeze']}")
    candidate = {
        "schema_version": "site-graph-v0-candidate-result/2",
        "candidate_id": "logic-only",
        "release_manifest_sha256": release_hash,
        "private_opportunity_ledger_canonical_sha256": private_hash,
        "freeze_commit": freeze_commit,
        "freeze_manifest_path": paths["freeze"],
        "freeze_manifest_blob_oid": freeze_blob,
        "run_started_at_utc": "2026-08-28T00:02:00Z",
        "records": [],
    }
    reviews = {
        "schema_version": "site-graph-v0-review-ledger/2",
        "review_scope": "census_of_every_credited_new_link_strict_refinement_and_equivalence_decision",
        "decisions": [],
    }
    _write_json(repo / paths["result"], candidate)
    _write_json(repo / paths["reviews"], reviews)
    _git(repo, "add", "candidate")
    _git(repo, "commit", "-qm", "candidate result")
    result_commit = _git(repo, "rev-parse", "HEAD")
    policy_path = repo / "docs/evaluations/site-graph-v0/trusted-run-attestors.json"
    policy_path.parent.mkdir(parents=True)
    shutil.copy2(EVAL_ROOT / "trusted-run-attestors.json", policy_path)
    return {
        "repo": repo,
        "paths": paths,
        "freeze_commit": freeze_commit,
        "result_commit": result_commit,
        "release_hash": release_hash,
        "private_hash": private_hash,
    }


def test_production_candidate_inputs_are_bound_to_distinct_git_commits(tmp_path: Path) -> None:
    fixture = _candidate_git_fixture(tmp_path)
    with pytest.raises(CandidateGitError, match="NOT_CONFIGURED"):
        _load_candidate_freeze(
            fixture["repo"],
            fixture["result_commit"],
            fixture["paths"]["result"],
            "candidate/run-completion-attestation.json",
            "candidate/run-completion-attestation.sig",
            fixture["release_hash"],
            fixture["private_hash"],
            EVAL_ROOT / "schemas",
        )


def test_production_candidate_binding_rejects_alternate_release(tmp_path: Path) -> None:
    parameters = inspect.signature(_load_candidate_freeze).parameters
    assert "trusted_policy" not in parameters
    assert "candidate_result_path" not in parameters
    assert "review_ledger_path" not in parameters
    assert "completion_attestation_path" in parameters
    assert "completion_signature_path" in parameters


def test_production_cli_has_no_arbitrary_baseline_or_crosswalk_paths() -> None:
    result = subprocess.run(
        [sys.executable, "-B", str(SCRIPTS / "compare_candidate.py"), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "--repo-root" in result.stdout
    assert "--private-run" in result.stdout
    assert "--run-result-manifest-path" in result.stdout
    assert "--completion-attestation-path" in result.stdout
    assert "--completion-signature-path" in result.stdout
    assert "--baseline-records" not in result.stdout
    assert "--baseline-metrics" not in result.stdout
    assert "--opportunity-ledger" not in result.stdout
    assert "--type-crosswalk" not in result.stdout


def _structured_review_fixture(tmp_path: Path) -> tuple[Path, str, dict]:
    fixture = _candidate_git_fixture(tmp_path)
    repo = fixture["repo"]
    subject = {"artifact_id": "logic-artifact", "target_id": "logic-target"}
    key = decision_key("link_support", subject)
    paths = []
    for suffix in ("a", "b"):
        relative = f"candidate/review-{suffix}.json"
        paths.append(relative)
        _write_json(
            repo / relative,
            {
                "schema_version": "site-graph-v0-review-artifact/2",
                "review_id": f"review-{suffix}",
                "decision_key": key,
                "decision_kind": "link_support",
                "subject": subject,
                "reviewer": {
                    "reviewer_id": f"reviewer-{suffix}",
                    "independence_group": f"group-{suffix}",
                },
                "outcome": "supported",
                "method": "human",
                "citations": [
                    {
                        "source_id": f"authority-{suffix}",
                        "source_kind": "independent_authority",
                        "locator": f"record-{suffix}",
                        "evidence_summary": f"independent logic evidence {suffix}",
                        "originating_museum": False,
                    }
                ],
                "reasoning": f"logic-only structured review {suffix}",
                "llm_interaction": None,
            },
        )
    _git(repo, "add", "candidate")
    _git(repo, "commit", "-qm", "structured review artifacts")
    result_commit = _git(repo, "rev-parse", "HEAD")
    references = []
    for relative in paths:
        value = json.loads((repo / relative).read_text())
        references.append(
            {
                "path": relative,
                "sha256": sha256(repo / relative),
                "git_blob_oid": _git(repo, "rev-parse", f"HEAD:{relative}"),
                "canonical_record_sha256": canonical_sha256(value),
            }
        )
    ledger = {
        "schema_version": "site-graph-v0-review-ledger/3",
        "review_scope": "census_of_every_credited_link_refinement_equivalence_and_positive_distinctness_decision",
        "decisions": [
            {
                "decision_key": key,
                "decision_kind": "link_support",
                "subject": subject,
                "review_artifacts": references,
            }
        ],
    }
    return repo, result_commit, ledger


def test_legacy_unsigned_review_artifacts_cannot_enter_authenticated_census(
    tmp_path: Path,
) -> None:
    repo, result_commit, ledger = _structured_review_fixture(tmp_path)
    with pytest.raises(ReviewAuthenticationError, match="pre-run freeze"):
        _validate_review_artifacts(
            repo, result_commit, ledger, EVAL_ROOT / "schemas"
        )


def test_review_census_api_requires_authenticated_freeze_and_source_exports() -> None:
    parameters = inspect.signature(_validate_review_artifacts).parameters
    for name in (
        "freeze_commit",
        "frozen_files",
        "source_exports",
        "source_export_groups",
        "candidate_id",
    ):
        assert name in parameters


def test_committed_real_corpus_headlines_recompute_from_pinned_inputs() -> None:
    snapshot = json.loads((EVAL_ROOT / "input-snapshot.json").read_text())
    idai = read_jsonl(REPO_ROOT / "pipeline/pipeline/authority/sources/idai-gazetteer/reconciled.jsonl")
    raw = json.loads((REPO_ROOT / "pipeline/pipeline/authority/sources/idai-gazetteer/raw.json").read_text())
    crosswalk = json.loads((EVAL_ROOT / "type-crosswalk.json").read_text())
    expected_targets = snapshot["current_authority"]["site_snapshot"]["site_target_count"]
    nodes, scope_by_target, hierarchy = classify_current_nodes(
        idai, raw, crosswalk, expected_targets
    )
    assert json.loads((EVAL_ROOT / "baseline-node-scope.json").read_text()) == {
        "schema_version": "site-graph-v0-baseline-node-scope/2",
        "hierarchy_context": hierarchy,
        "nodes": nodes,
    }
    assert all(
        node["scope_class"] != "unclassified"
        for node in nodes
        if node["source_types"]
    )

    metrics = json.loads((EVAL_ROOT / "baseline-metrics.json").read_text())
    opportunity = json.loads((EVAL_ROOT / "planned-opportunity-summary.json").read_text())
    assert metrics["canonical_records"] == sum(snapshot["corpus"]["records_by_museum"].values())
    assert metrics["record_counts_by_museum"] == snapshot["corpus"]["records_by_museum"]

    def assert_ratio(value: dict, numerator: int, denominator: int) -> None:
        assert value["numerator"] == numerator
        assert value["denominator"] == denominator
        assert value["value"] == pytest.approx(numerator / denominator)

    for museum, row in metrics["per_museum"].items():
        total = snapshot["corpus"]["records_by_museum"][museum]
        extracted = row["extracted_site_text_evidence_records"]
        linked = row["records_with_unique_site_link"]
        assert row["canonical_records"] == total
        assert row["no_extracted_site_evidence_records"] + extracted == total
        assert row["extracted_site_text_without_unique_site_link"] + linked == extracted
        assert sum(row["resolution_state_counts"].values()) == total
        assert_ratio(row["extracted_site_text_availability_rate"], extracted, total)
        assert_ratio(row["overall_linkability"], linked, total)
        assert_ratio(row["extracted_site_text_conditional_linkability"], linked, extracted)
        ceiling = row["absolute_authority_only_maximum_measurable_gain"]
        assert ceiling["records"] == extracted - linked
        assert_ratio(ceiling["overall_percentage_point_ceiling"], extracted - linked, total)
        assert_ratio(ceiling["conditional_percentage_point_ceiling"], extracted - linked, extracted)

    def assert_connectivity(block: dict) -> None:
        shared = set(block["shared_target_ids"])
        assert block["shared_node_count"] == len(shared)
        assert block["shared_node_scope_counts"] == dict(
            sorted(Counter(scope_by_target[target] for target in shared).items())
        )
        for museum, side in block["sides"].items():
            connected = side["connected_records"]
            assert connected == sum(side["mutually_exclusive_scope_counts"].values())
            assert_ratio(
                side["overall_connection_rate"], connected,
                snapshot["corpus"]["records_by_museum"][museum],
            )
            assert_ratio(
                side["extracted_site_text_conditional_connection_rate"], connected,
                metrics["per_museum"][museum]["extracted_site_text_evidence_records"],
            )
        for museum, concentration in block["concentration_by_museum_side"].items():
            assert concentration["shared_node_count"] == len(shared)
            assert concentration["distinct_connected_records"] == block["sides"][museum]["connected_records"]
            hhi = concentration["node_incidence_hhi"]
            assert hhi["denominator"] == concentration["node_incidence_total"] ** 2
            assert hhi["value"] == pytest.approx(hhi["numerator"] / hhi["denominator"])
            for k in ("1", "5", "10"):
                top = concentration["top_k_unique_record_concentration"][k]
                assert len(top["selected_target_ids"]) <= min(int(k), len(shared))
                assert set(top["selected_target_ids"]) <= shared
                assert_ratio(
                    top["ratio"], top["ratio"]["numerator"],
                    concentration["distinct_connected_records"],
                )

    for pair in metrics["connectivity"]["pairs"].values():
        assert_connectivity(pair)
    assert_connectivity(metrics["connectivity"]["all_three"])

    for museum, row in opportunity["per_museum"].items():
        partition = row["baseline_record_scope_counts"]
        assert row["intent_to_treat_record_count"] == sum(partition.values())
        maximum = row["new_record_link_ceiling_records"] + row["strict_refinement_reassignment_ceiling_records"]
        assert row["maximum_credited_affected_records"] == maximum
        assert_ratio(
            row["maximum_overall_effect"], maximum,
            snapshot["corpus"]["records_by_museum"][museum],
        )
        assert_ratio(
            row["maximum_extracted_site_text_conditional_effect"], maximum,
            metrics["per_museum"][museum]["extracted_site_text_evidence_records"],
        )
    for pair in opportunity["pair_side_ceilings"].values():
        for side in pair["sides"].values():
            partition = side["baseline_pair_partition"]
            denominator = partition["no_baseline_pair_connection"] + partition["baseline_broad_only"]
            assert side["credited_effect_opportunity_denominator"] == denominator
            assert side["minimum_credited_affected_records_for_continue"] == (denominator + 9) // 10


def test_release_manifest_authenticates_exact_ci_surface_read_only() -> None:
    before = {
        path.relative_to(REPO_ROOT).as_posix(): (path.stat().st_size, sha256(path))
        for path in EVAL_ROOT.rglob("*") if path.is_file() and "__pycache__" not in path.parts
    }
    result = verify_release(REPO_ROOT)
    after = {
        path.relative_to(REPO_ROOT).as_posix(): (path.stat().st_size, sha256(path))
        for path in EVAL_ROOT.rglob("*") if path.is_file() and "__pycache__" not in path.parts
    }
    assert result["verified_file_count"] > 30
    assert before == after


def test_every_machine_formula_and_decision_threshold_matches_executable_values() -> None:
    prereg = json.loads((EVAL_ROOT / "preregistration.json").read_text())
    assert {
        key: value["expression"] for key, value in prereg["metric_formulas"].items()
    } == {
        "extracted_site_text_availability": "|X_m| / |A_m|",
        "overall_linkability": "|L_m| / |A_m|",
        "extracted_site_text_conditional_linkability": "|L_m| / |X_m|",
        "blocking_ambiguity": "|{r in X_m: direct targets empty and any site mention ambiguous}| / |X_m|",
        "newly_blocking_ambiguity_safety": "|{r in X_m: baseline blocking=false and candidate blocking=true}| / |X_m|",
        "planned_maximum_overall_effect": "(|new-link-eligible records in O_m| + |broad-only strict-refinement-eligible records in O_m|) / |A_m|",
        "planned_maximum_extracted_site_text_conditional_effect": "(|new-link-eligible records in O_m| + |broad-only strict-refinement-eligible records in O_m|) / |X_m|",
        "pair_side_coverage_overall": "D_(m->n) / |A_m|",
        "pair_side_coverage_extracted_site_text_conditional": "D_(m->n) / |X_m|",
        "top_k_concentration": "|union of museum-side records incident on its top-k shared identity classes| / |union of museum-side records incident on all its shared identity classes|",
        "hhi": "sum_j(I_j^2) / (sum_j I_j)^2",
    }
    assert prereg["machine_thresholds"] == {
        "maximum_newly_blocking_fraction": {
            "numerator": MAXIMUM_NEWLY_BLOCKING_FRACTION.numerator,
            "denominator": MAXIMUM_NEWLY_BLOCKING_FRACTION.denominator,
        },
        "concentration_maximum_increase": {
            "numerator": CONCENTRATION_MAXIMUM_INCREASE.numerator,
            "denominator": CONCENTRATION_MAXIMUM_INCREASE.denominator,
        },
        "minimum_gained_distinct_specific_identity_classes": MINIMUM_GAINED_IDENTITIES,
        "minimum_affected_opportunity_fraction": {
            "numerator": MINIMUM_AFFECTED_FRACTION.numerator,
            "denominator": MINIMUM_AFFECTED_FRACTION.denominator,
        },
        "minimum_reviews_per_credited_decision": REVIEWS_PER_CREDITED_DECISION,
        "opportunity_museum_protection_signatures": OPPORTUNITY_MUSEUM_PROTECTION,
        "opportunity_total_signatures": OPPORTUNITY_TOTAL_SIGNATURES,
    }
    assert prereg["ordered_decision_rule"]["precedence"] == [
        "INVALID", "REDESIGN", "CONTINUE", "STOP"
    ]
    assert prereg["ordered_decision_rule"]["raw_link_rate_growth_can_satisfy_continue"] is False
    assert prereg["ordered_decision_rule"]["museum_equality_required"] is False
    assert prereg["ordered_decision_rule"]["narrowness_without_support_can_satisfy_continue"] is False
