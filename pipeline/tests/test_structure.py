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

PIPELINE_ROOT = Path(__file__).parent.parent


def _implemented_museums() -> list[MuseumSource]:
    """Return museums that have at least an ingest asset (i.e., implementation has started)."""
    return [
        source
        for source in MuseumSource
        if (PIPELINE_ROOT / "pipeline" / "assets" / "ingest" / f"{source.value}.py").exists()
    ]


@pytest.mark.parametrize("source", _implemented_museums(), ids=lambda s: s.value)
def test_museum_has_ingest_asset(source: MuseumSource):
    """Every implemented museum must have an ingest asset file."""
    path = PIPELINE_ROOT / "pipeline" / "assets" / "ingest" / f"{source.value}.py"
    assert path.exists()


@pytest.mark.parametrize("source", _implemented_museums(), ids=lambda s: s.value)
def test_museum_has_normalize_mapper(source: MuseumSource):
    """Every implemented museum must have a normalize mapper file."""
    path = PIPELINE_ROOT / "pipeline" / "assets" / "normalize" / f"{source.value}.py"
    assert path.exists(), (
        f"Create {path} — normalize mapper for {source.value}. "
        f"It must implement MapperProtocol from pipeline/types/protocol.py."
    )


@pytest.mark.parametrize("source", _implemented_museums(), ids=lambda s: s.value)
def test_museum_has_fixtures(source: MuseumSource):
    """Every implemented museum must have fixture data."""
    fixture_dir = PIPELINE_ROOT / "tests" / "fixtures" / source.value
    assert fixture_dir.is_dir(), (
        f"Create directory {fixture_dir}/ and add 3-5 real API responses as JSON files."
    )
    fixtures = list(fixture_dir.glob("*.json"))
    assert len(fixtures) > 0, (
        f"Add fixture JSON files to {fixture_dir}/."
    )


@pytest.mark.parametrize("source", _implemented_museums(), ids=lambda s: s.value)
def test_museum_has_mapper_tests(source: MuseumSource):
    """Every implemented museum must have mapper tests."""
    path = PIPELINE_ROOT / "tests" / "test_mappers" / f"test_{source.value}.py"
    assert path.exists(), (
        f"Create {path} — mapper tests for {source.value}. "
        f"Test against every fixture file in tests/fixtures/{source.value}/."
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
