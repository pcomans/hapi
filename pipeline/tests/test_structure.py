"""Structural tests that verify the harness itself.

These tests enforce architectural invariants:
- Every registered museum has ingest + mapper + fixtures
- The SQLAlchemy table model matches the Pydantic canonical model
- All museums have license entries

Assertion messages are written as remediation instructions for the agent.
When a test fails, the message tells the agent exactly what to do to fix it.
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
            f"Create {path} — ingest asset for {source.value}. "
            f"It must store raw API responses verbatim in the raw_{source.value} table. "
            f"Follow the 'Adding a new museum' checklist in pipeline/CLAUDE.md."
        )


@needs_implementation
def test_every_museum_has_normalize_mapper():
    """Every museum in MuseumSource must have a normalize mapper file."""
    for source in MuseumSource:
        path = PIPELINE_ROOT / "pipeline" / "assets" / "normalize" / f"{source.value}.py"
        assert path.exists(), (
            f"Create {path} — normalize mapper for {source.value}. "
            f"It must implement MapperProtocol from pipeline/types/protocol.py. "
            f"Follow the 'Adding a new museum' checklist in pipeline/CLAUDE.md."
        )


@needs_implementation
def test_every_museum_has_fixtures():
    """Every museum in MuseumSource must have fixture data."""
    for source in MuseumSource:
        fixture_dir = PIPELINE_ROOT / "tests" / "fixtures" / source.value
        assert fixture_dir.is_dir(), (
            f"Create directory {fixture_dir}/ and add 3-5 real API responses as JSON files. "
            f"Choose diverse cases: one well-catalogued artifact, one sparse record, "
            f"one with ambiguous provenance."
        )
        fixtures = list(fixture_dir.glob("*.json"))
        assert len(fixtures) > 0, (
            f"Add fixture JSON files to {fixture_dir}/. "
            f"Save 3-5 real API responses. Choose diverse cases: one well-catalogued "
            f"artifact, one sparse record, one with ambiguous provenance."
        )


@needs_implementation
def test_every_museum_has_mapper_tests():
    """Every museum in MuseumSource must have mapper tests."""
    for source in MuseumSource:
        path = PIPELINE_ROOT / "tests" / "test_mappers" / f"test_{source.value}.py"
        assert path.exists(), (
            f"Create {path} — mapper tests for {source.value}. "
            f"Test against every fixture file in tests/fixtures/{source.value}/. "
            f"Assert specific field values, not just absence of errors."
        )


def test_sqlalchemy_columns_match_pydantic_fields():
    """The SQLAlchemy artifacts table must have the same columns as the Pydantic model fields."""
    sa_columns = set(artifacts_table.columns.keys())
    pydantic_fields = set(CanonicalArtifact.model_fields.keys())

    missing_from_table = pydantic_fields - sa_columns
    extra_in_table = sa_columns - pydantic_fields

    assert not missing_from_table, (
        f"Add columns to artifacts_table in pipeline/types/models.py: {missing_from_table}. "
        f"Then run: uv run alembic revision --autogenerate -m 'add columns'"
    )
    assert not extra_in_table, (
        f"Add fields to CanonicalArtifact in pipeline/types/canonical.py: {extra_in_table}. "
        f"All fields should be Optional except id, source_museum, source_url."
    )


def test_every_museum_has_license():
    """Every museum in MuseumSource must have an entry in MUSEUM_LICENSE."""
    for source in MuseumSource:
        assert source in MUSEUM_LICENSE, (
            f"Add MUSEUM_LICENSE[MuseumSource.{source.name}] = License.<type> "
            f"in pipeline/types/sources.py. "
            f"Check docs/museum-sources/{source.value}.md for license terms."
        )
