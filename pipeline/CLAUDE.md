# Pipeline — Agent Instructions

Python / Dagster data pipeline. Ingests museum data, normalizes to canonical schema, enriches with authority data, syncs to Typesense.

## Critical rule

**Never run pipeline assets outside of Dagster.** All ingest, normalize, enrich, and index operations must be executed through Dagster. Do not write ad-hoc Python scripts that call asset functions directly — Dagster is the orchestrator for all data operations.

**The agent operates Dagster, not the user.** Use the Dagster CLI to materialize assets:

```bash
cd pipeline && uv run dagster asset materialize -m pipeline.definitions --select raw_met          # single asset
cd pipeline && uv run dagster asset materialize -m pipeline.definitions --select raw_met,normalize_met  # multiple
cd pipeline && uv run dagster asset materialize -m pipeline.definitions --select '*'              # all assets
```

Do not tell the user to open the Dagster UI and click buttons. The agent is responsible for triggering pipeline runs.

**Dagster dev server uses port 3001** (Next.js uses 3000):

```bash
cd pipeline && uv run dagster dev -p 3001
```

## How it works

Dagster assets form a dependency chain:

```
ingest/{museum} → normalize/{museum} → enrich/rulers + enrich/sites → index/sync_search
```

Each museum has its own ingest asset and its own normalize mapper. They are independent of each other. The enrichment and indexing stages operate on all normalized data regardless of source.

## Adding a new museum

Follow the step-by-step playbook: **[docs/playbook-new-museum.md](../docs/playbook-new-museum.md)**

The playbook has two phases: **ingest** (parallelizable, one agent per museum) and **normalization** (sequential, each museum refines the canonical vocabulary). Structural tests in `tests/test_structure.py` mechanically enforce every step — run them early and often. When a test fails, the assertion message tells you exactly what to fix.

## MapperProtocol

Every mapper must implement:

```python
class MapperProtocol(Protocol):
    source: MuseumSource

    def map_to_canonical(self, raw: dict) -> CanonicalArtifact:
        """Map a single raw museum record to the canonical schema.

        Returns a CanonicalArtifact with None for unmappable optional fields.
        Raises ValueError or KeyError if the record is malformed or missing
        data required for a valid mapping (id, source_url).

        Ruler/site matching uses authority list lookup via the enrich stage,
        NOT this mapper. This mapper only does field-level transformation.
        """
        ...
```

**When to raise vs return None:**
- **Raise** if the record is structurally broken: missing `id`, missing `source_url`, unparseable JSON, unexpected top-level shape. These indicate a bug in the ingest or a breaking API change.
- **Return None** for absent optional metadata: no dynasty, no image, no dimensions. Most museum records are sparse — this is expected, not an error.

## Schema ownership

The pipeline owns the `catalog` Postgres schema. All data tables (artifacts, raw data, fuzzy match reviews) live in `catalog.*`. Table definitions are in `pipeline/types/models.py` (SQLAlchemy with `MetaData(schema="catalog")`). Alembic manages migrations with `version_table_schema="catalog"` so migration history also lives in the `catalog` schema.

The web app has its own `web` Postgres schema for app-specific tables (users, settings). Both schemas live in the same database — cross-schema joins work natively. See ADR-011.

To change the data schema:
1. Update SQLAlchemy table in `pipeline/types/models.py`
2. Update Pydantic model in `pipeline/types/canonical.py`
3. Run `uv run alembic revision --autogenerate -m "description"`
4. Run `uv run alembic upgrade head`
5. In web/: `pnpm drizzle-kit introspect`
6. Commit the migration, models, and regenerated Drizzle schema together

## Key conventions

- **Raw data is sacred.** Ingest assets store the museum's response byte-for-byte. Never transform during ingest.
- **Mappers are pure transforms.** They take a dict, return a `CanonicalArtifact`. No network calls, no database writes, no side effects. This makes them trivially testable.
- **Authority matching happens in the enrich stage**, not in mappers. Mappers extract the raw text values (e.g., `reign: "Thutmose III"`). The enrichment assets resolve these to canonical authority IDs.
- **Idempotent re-runs.** Every asset can be re-materialized without side effects. Ingest overwrites raw data. Normalize overwrites canonical records. Enrich updates authority links.

## Testing

```bash
uv run pytest                           # Run all tests
uv run pytest tests/test_mappers/       # Run mapper tests only
uv run pytest -k "test_met"             # Run Met-specific tests
```

- Tests use real fixture data from `tests/fixtures/`, never mocks
- Every fixture file must have a corresponding test asserting specific mapped values
- Structural tests in `tests/test_structure.py` verify that every registered museum has ingest + mapper + fixtures
