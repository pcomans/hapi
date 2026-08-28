"""Static, versioned release inventory independent of the generated manifest."""

from __future__ import annotations


CONTRACT_VERSION = "site-graph-v0-release/2"
PYCACHE_EXCLUSION = (
    "Python cache directories (__pycache__, .pytest_cache) and bytecode suffixes "
    "(.pyc, .pyo) are runtime by-products, are never required release files, and are "
    "ignored during exact-inventory discovery. No other file or directory is ignored."
)
# Changing this set is a contract-version migration and requires separate review. The
# manifest generator may hash exactly this set; it may not infer or expand it.
REQUIRED_RELEASE_FILES = frozenset(
    {
        "docs/evaluations/site-graph-v0/README.md",
        "docs/evaluations/site-graph-v0/baseline-metrics.json",
        "docs/evaluations/site-graph-v0/baseline-node-scope.json",
        "docs/evaluations/site-graph-v0/baseline-rerun-evidence.json",
        "docs/evaluations/site-graph-v0/corpus-provenance/NOTICE",
        "docs/evaluations/site-graph-v0/corpus-provenance/bundle-README.md",
        "docs/evaluations/site-graph-v0/corpus-provenance/bundle-SHA256SUMS",
        "docs/evaluations/site-graph-v0/corpus-provenance/manifest.json",
        "docs/evaluations/site-graph-v0/corpus-provenance/validation/queries.sql",
        "docs/evaluations/site-graph-v0/corpus-provenance/validation/results.json",
        "docs/evaluations/site-graph-v0/corpus-provenance/validation/verify_bundle.sh",
        "docs/evaluations/site-graph-v0/correction-policy.json",
        "docs/evaluations/site-graph-v0/implementation-evidence.json",
        "docs/evaluations/site-graph-v0/input-snapshot.json",
        "docs/evaluations/site-graph-v0/planned-opportunity-summary.json",
        "docs/evaluations/site-graph-v0/preregistration.json",
        "docs/evaluations/site-graph-v0/private-ledger-digests.json",
        "docs/evaluations/site-graph-v0/reviews/round-1/disposition.json",
        "docs/evaluations/site-graph-v0/reviews/round-1/metadata.json",
        "docs/evaluations/site-graph-v0/reviews/round-1/prompt.md",
        "docs/evaluations/site-graph-v0/reviews/round-1/raw-output.txt",
        "docs/evaluations/site-graph-v0/reviews/round-2/disposition.json",
        "docs/evaluations/site-graph-v0/reviews/round-2/metadata.json",
        "docs/evaluations/site-graph-v0/reviews/round-2/prompt.md",
        "docs/evaluations/site-graph-v0/reviews/round-2/raw-output.txt",
        "docs/evaluations/site-graph-v0/schemas/candidate-freeze-manifest.schema.json",
        "docs/evaluations/site-graph-v0/schemas/candidate-hierarchy.schema.json",
        "docs/evaluations/site-graph-v0/schemas/candidate-source-snapshot.schema.json",
        "docs/evaluations/site-graph-v0/schemas/candidate.schema.json",
        "docs/evaluations/site-graph-v0/schemas/comparison-report.schema.json",
        "docs/evaluations/site-graph-v0/schemas/correction-ledger.schema.json",
        "docs/evaluations/site-graph-v0/schemas/opportunity-summary.schema.json",
        "docs/evaluations/site-graph-v0/schemas/private-opportunity-ledger.schema.json",
        "docs/evaluations/site-graph-v0/schemas/prompt-leakage-audit.schema.json",
        "docs/evaluations/site-graph-v0/schemas/relation-ledger.schema.json",
        "docs/evaluations/site-graph-v0/schemas/review-artifact.schema.json",
        "docs/evaluations/site-graph-v0/schemas/review-ledger.schema.json",
        "docs/evaluations/site-graph-v0/scripts/apply_corrections.py",
        "docs/evaluations/site-graph-v0/scripts/build_baseline.py",
        "docs/evaluations/site-graph-v0/scripts/candidate_git.py",
        "docs/evaluations/site-graph-v0/scripts/compare_baseline_runs.py",
        "docs/evaluations/site-graph-v0/scripts/compare_candidate.py",
        "docs/evaluations/site-graph-v0/scripts/contract_constants.py",
        "docs/evaluations/site-graph-v0/scripts/freeze_candidate_inputs.py",
        "docs/evaluations/site-graph-v0/scripts/freeze_release.py",
        "docs/evaluations/site-graph-v0/scripts/generate_validation_report.py",
        "docs/evaluations/site-graph-v0/scripts/integrity.py",
        "docs/evaluations/site-graph-v0/scripts/metrics_core.py",
        "docs/evaluations/site-graph-v0/scripts/private_ledgers.py",
        "docs/evaluations/site-graph-v0/scripts/release_contract.py",
        "docs/evaluations/site-graph-v0/scripts/run_baseline.py",
        "docs/evaluations/site-graph-v0/scripts/run_two_baselines.py",
        "docs/evaluations/site-graph-v0/scripts/schema_validation.py",
        "docs/evaluations/site-graph-v0/scripts/validate_contract.py",
        "docs/evaluations/site-graph-v0/top-unmatched-components.json",
        "docs/evaluations/site-graph-v0/type-crosswalk.json",
        "docs/evaluations/site-graph-v0/validation-report.json",
        "pipeline/pyproject.toml",
        "pipeline/tests/test_site_graph_v0_contract.py",
        "pipeline/uv.lock",
    }
)
