"""Structural tests that verify the harness itself.

These tests enforce architectural invariants:
- Every registered museum has ingest + mapper + fixtures
- The SQLAlchemy table model matches the Pydantic canonical model
- All museums have license entries
"""

from pathlib import Path

import pytest

from pipeline.types.canonical import CanonicalArtifact
from pipeline.types.models import artifacts_table
from pipeline.types.sources import MUSEUM_LICENSE, MuseumSource

# Tests marked needs_implementation are expected to fail until museum
# mappers, fixtures, and test files are created. They are skipped in CI
# and will be un-skipped as each museum is implemented.
needs_implementation = pytest.mark.skipif(
    not (Path(__file__).parent.parent / "pipeline" / "assets" / "ingest" / "met.py").exists(),
    reason="Museum implementation not started yet",
)

PIPELINE_ROOT = Path(__file__).parent.parent


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


def test_sqlalchemy_columns_match_pydantic_fields():
    """The SQLAlchemy artifacts table must have the same columns as the Pydantic model fields."""
    sa_columns = set(artifacts_table.columns.keys())
    pydantic_fields = set(CanonicalArtifact.model_fields.keys())

    missing_from_table = pydantic_fields - sa_columns
    extra_in_table = sa_columns - pydantic_fields

    assert not missing_from_table, (
        f"Fields in CanonicalArtifact but missing from artifacts_table: {missing_from_table}"
    )
    assert not extra_in_table, (
        f"Columns in artifacts_table but missing from CanonicalArtifact: {extra_in_table}"
    )


def test_every_museum_has_license():
    """Every museum in MuseumSource must have an entry in MUSEUM_LICENSE."""
    for source in MuseumSource:
        assert source in MUSEUM_LICENSE, (
            f"Missing license entry for {source.value} in MUSEUM_LICENSE. "
            f"Add it to pipeline/types/sources.py."
        )
