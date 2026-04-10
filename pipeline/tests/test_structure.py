"""Structural tests that verify the harness itself.

These tests enforce architectural invariants so that an agent adding a new
museum gets immediate, actionable feedback when any piece is missing.

Every assertion message is a remediation instruction: it tells the agent
exactly what file to create or what line to add. This is the mechanical
enforcement layer — if a rule can be a test, it must be a test.

When adding a new museum, these tests form the checklist. Run them with:
    uv run pytest tests/test_structure.py -v
"""

import importlib
from pathlib import Path

import pytest

from pipeline.types.canonical import CanonicalArtifact
from pipeline.types.models import artifacts_table, metadata as catalog_metadata
from pipeline.types.sources import MUSEUM_LICENSE, MuseumSource

PIPELINE_ROOT = Path(__file__).parent.parent
DOCS_ROOT = PIPELINE_ROOT.parent / "docs"


def _implemented_museums() -> list[MuseumSource]:
    """Return museums that have at least an ingest asset (i.e., implementation has started)."""
    return [
        source
        for source in MuseumSource
        if (PIPELINE_ROOT / "pipeline" / "assets" / "ingest" / f"{source.value}.py").exists()
    ]


# ---------------------------------------------------------------------------
# Per-museum structural tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("source", _implemented_museums(), ids=lambda s: s.value)
class TestMuseumHasAllPieces:
    """Every implemented museum must have the full set of pipeline components."""

    def test_ingest_asset(self, source: MuseumSource):
        path = PIPELINE_ROOT / "pipeline" / "assets" / "ingest" / f"{source.value}.py"
        assert path.exists(), (
            f"Create {path.relative_to(PIPELINE_ROOT)} — ingest asset for {source.value}. "
            f"See pipeline/assets/ingest/met.py for the pattern."
        )

    def test_normalize_mapper(self, source: MuseumSource):
        path = PIPELINE_ROOT / "pipeline" / "assets" / "normalize" / f"{source.value}.py"
        assert path.exists(), (
            f"Create {path.relative_to(PIPELINE_ROOT)} — normalize mapper for {source.value}. "
            f"It must implement MapperProtocol from pipeline/types/protocol.py. "
            f"See pipeline/assets/normalize/met.py for the pattern."
        )

    def test_normalize_asset(self, source: MuseumSource):
        path = PIPELINE_ROOT / "pipeline" / "assets" / "normalize" / f"{source.value}_asset.py"
        assert path.exists(), (
            f"Create {path.relative_to(PIPELINE_ROOT)} — Dagster normalize asset for {source.value}. "
            f"This is the Dagster @asset wrapper that reads raw_{source.value} and writes "
            f"to the artifacts table using the mapper. "
            f"See pipeline/assets/normalize/met_asset.py for the pattern."
        )

    def test_fixtures_exist(self, source: MuseumSource):
        fixture_dir = PIPELINE_ROOT / "tests" / "fixtures" / source.value
        assert fixture_dir.is_dir(), (
            f"Create directory tests/fixtures/{source.value}/ and add 3-5 real API "
            f"responses as JSON files. Choose diverse cases: one rich object, one sparse "
            f"record, one with ambiguous provenance."
        )
        fixtures = list(fixture_dir.glob("*.json"))
        assert len(fixtures) >= 3, (
            f"Add at least 3 fixture JSON files to tests/fixtures/{source.value}/. "
            f"Found {len(fixtures)}. Need diverse cases: rich, sparse, ambiguous."
        )

    def test_mapper_tests_exist(self, source: MuseumSource):
        path = PIPELINE_ROOT / "tests" / "test_mappers" / f"test_{source.value}.py"
        assert path.exists(), (
            f"Create {path.relative_to(PIPELINE_ROOT)} — mapper tests for {source.value}. "
            f"Test against every fixture file in tests/fixtures/{source.value}/. "
            f"Assert specific field values, not just 'it doesn't crash'. "
            f"See tests/test_mappers/test_met.py for the pattern."
        )

    def test_raw_table_exists(self, source: MuseumSource):
        table_name = f"raw_{source.value}"
        table_names = {t.name for t in catalog_metadata.sorted_tables}
        assert table_name in table_names, (
            f"Add raw_{source.value}_table to pipeline/types/models.py:\n"
            f"    raw_{source.value}_table = Table(\n"
            f'        "{table_name}",\n'
            f"        metadata,\n"
            f'        Column("object_id", String, primary_key=True),\n'
            f'        Column("data", Text, nullable=False),\n'
            f"    )\n"
            f"Then run: uv run alembic revision --autogenerate -m 'add raw_{source.value} table'"
        )

    def test_source_docs_exist(self, source: MuseumSource):
        path = DOCS_ROOT / "museum-sources" / f"{source.value}.md"
        assert path.exists(), (
            f"Create {path.relative_to(PIPELINE_ROOT.parent)} — document the {source.value} "
            f"museum API: access method, rate limits, auth requirements, data quality notes, "
            f"license terms, and known quirks. This must be written BEFORE the ingest asset."
        )

    def test_license_entry(self, source: MuseumSource):
        assert source in MUSEUM_LICENSE, (
            f"Add MUSEUM_LICENSE[MuseumSource.{source.name}] = License.<type> "
            f"in pipeline/types/sources.py. "
            f"Check docs/museum-sources/{source.value}.md for license terms."
        )

    def test_dagster_registration(self, source: MuseumSource):
        """Verify the museum's assets are registered in Dagster definitions."""
        definitions_mod = importlib.import_module("pipeline.definitions")
        defs = definitions_mod.defs
        asset_keys = {key.path[-1] for key in defs.resolve_asset_graph().get_all_asset_keys()}

        raw_key = f"raw_{source.value}"
        assert raw_key in asset_keys, (
            f"Register the raw_{source.value} ingest asset in pipeline/definitions.py. "
            f"Import it and add it to the assets list in the Definitions() call."
        )

        normalize_key = f"normalize_{source.value}"
        assert normalize_key in asset_keys, (
            f"Register the normalize_{source.value} asset in pipeline/definitions.py. "
            f"Import it and add it to the assets list in the Definitions() call."
        )


# ---------------------------------------------------------------------------
# Schema consistency
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Mapper protocol compliance
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("source", _implemented_museums(), ids=lambda s: s.value)
def test_mapper_implements_protocol(source: MuseumSource):
    """Every mapper module must export a class with a map_to_canonical method and source attr."""
    mod = importlib.import_module(f"pipeline.assets.normalize.{source.value}")
    mapper_classes = [
        obj for name, obj in vars(mod).items()
        if isinstance(obj, type) and hasattr(obj, "map_to_canonical") and hasattr(obj, "source")
    ]
    assert len(mapper_classes) >= 1, (
        f"pipeline/assets/normalize/{source.value}.py must export a class with "
        f"'source' attribute and 'map_to_canonical' method (MapperProtocol). "
        f"See pipeline/assets/normalize/met.py for the pattern."
    )
    mapper_cls = mapper_classes[0]
    try:
        instance = mapper_cls()
    except TypeError as exc:
        raise AssertionError(
            f"Mapper {mapper_cls.__name__} in pipeline/assets/normalize/{source.value}.py "
            f"must be constructible with no arguments so the harness can instantiate it. "
            f"Constructor error: {exc}"
        ) from exc
    assert instance.source == source, (
        f"Mapper in pipeline/assets/normalize/{source.value}.py has "
        f"source={instance.source!r}, expected MuseumSource.{source.name} ({source.value!r}). "
        f"Set: source = MuseumSource.{source.name}"
    )


# ---------------------------------------------------------------------------
# Normalize asset wires to sync_search
# ---------------------------------------------------------------------------


def test_sync_search_depends_on_all_normalize_assets():
    """sync_search must depend on every museum's normalize asset."""
    definitions_mod = importlib.import_module("pipeline.definitions")
    defs = definitions_mod.defs
    graph = defs.resolve_asset_graph()

    sync_key = None
    for key in graph.get_all_asset_keys():
        if key.path[-1] == "sync_search":
            sync_key = key
            break

    assert sync_key is not None, "sync_search asset not found in Dagster definitions."

    parent_keys = {k.path[-1] for k in graph.get(sync_key).parent_keys}

    for source in _implemented_museums():
        normalize_key = f"normalize_{source.value}"
        assert normalize_key in parent_keys, (
            f"Add normalize_{source.value} as a dependency of sync_search. "
            f"In pipeline/assets/index/sync_search.py, add 'normalize_{source.value}' "
            f"to the deps list of the @asset decorator."
        )
