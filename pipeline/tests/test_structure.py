"""Structural tests that verify the harness itself.

These tests enforce architectural invariants:
- Every registered museum has ingest + mapper + fixtures
- The Pydantic model matches shared/schema.json
- All mappers implement the protocol
"""

import json
from pathlib import Path

import pytest

from pipeline.types.canonical import CanonicalArtifact
from pipeline.types.sources import MUSEUM_LICENSE, MuseumSource

# Tests marked needs_implementation are expected to fail until museum
# mappers, fixtures, and test files are created. They are skipped in CI
# and will be un-skipped as each museum is implemented.
needs_implementation = pytest.mark.skipif(
    not (Path(__file__).parent.parent / "pipeline" / "assets" / "ingest" / "met.py").exists(),
    reason="Museum implementation not started yet",
)

PROJECT_ROOT = Path(__file__).parent.parent.parent
PIPELINE_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = PROJECT_ROOT / "shared" / "schema.json"


@needs_implementation
def test_every_museum_has_ingest_asset():
    """Every museum in MuseumSource must have an ingest asset file."""
    for source in MuseumSource:
        path = PIPELINE_ROOT / "pipeline" / "assets" / "ingest" / f"{source.value}.py"
        assert path.exists(), (
            f"Missing ingest asset for {source.value}. "
            f"Expected: {path}. "
            f"See pipeline/CLAUDE.md for the 'Adding a new museum' checklist."
        )


@needs_implementation
def test_every_museum_has_normalize_mapper():
    """Every museum in MuseumSource must have a normalize mapper file."""
    for source in MuseumSource:
        path = PIPELINE_ROOT / "pipeline" / "assets" / "normalize" / f"{source.value}.py"
        assert path.exists(), (
            f"Missing normalize mapper for {source.value}. "
            f"Expected: {path}. "
            f"See pipeline/CLAUDE.md for the 'Adding a new museum' checklist."
        )


@needs_implementation
def test_every_museum_has_fixtures():
    """Every museum in MuseumSource must have fixture data."""
    for source in MuseumSource:
        fixture_dir = PIPELINE_ROOT / "tests" / "fixtures" / source.value
        assert fixture_dir.is_dir(), (
            f"Missing fixture directory for {source.value}. "
            f"Expected: {fixture_dir}"
        )
        fixtures = list(fixture_dir.glob("*.json"))
        assert len(fixtures) > 0, (
            f"No fixture JSON files for {source.value} in {fixture_dir}. "
            f"Add 3-5 real API responses as fixture data."
        )


@needs_implementation
def test_every_museum_has_mapper_tests():
    """Every museum in MuseumSource must have mapper tests."""
    for source in MuseumSource:
        path = PIPELINE_ROOT / "tests" / "test_mappers" / f"test_{source.value}.py"
        assert path.exists(), (
            f"Missing mapper tests for {source.value}. "
            f"Expected: {path}"
        )


def test_canonical_model_matches_schema_json():
    """The Pydantic CanonicalArtifact model must match shared/schema.json."""
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)

    schema_fields = set(schema["properties"].keys())
    model_fields = set(CanonicalArtifact.model_fields.keys())

    missing_from_model = schema_fields - model_fields
    extra_in_model = model_fields - schema_fields

    assert not missing_from_model, (
        f"Fields in schema.json but missing from CanonicalArtifact: {missing_from_model}"
    )
    assert not extra_in_model, (
        f"Fields in CanonicalArtifact but missing from schema.json: {extra_in_model}"
    )


def test_every_museum_has_license():
    """Every museum in MuseumSource must have an entry in MUSEUM_LICENSE."""
    for source in MuseumSource:
        assert source in MUSEUM_LICENSE, (
            f"Missing license entry for {source.value} in MUSEUM_LICENSE. "
            f"Add it to pipeline/types/sources.py."
        )


def test_required_fields_match():
    """The required fields in schema.json must match the non-optional Pydantic fields."""
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)

    schema_required = set(schema.get("required", []))

    # In Pydantic, required fields are those without a default value
    model_required = set()
    for name, field in CanonicalArtifact.model_fields.items():
        if field.is_required():
            model_required.add(name)

    assert schema_required == model_required, (
        f"Required field mismatch.\n"
        f"  schema.json requires: {schema_required}\n"
        f"  Pydantic requires: {model_required}"
    )
