# Playbook: Adding a New Museum

This is an operational playbook for agents adding a new Egyptian artifact source to Hapi. It is designed to be followed step-by-step with verification at each stage. An agent should be able to complete Phase 1 (ingest) independently; Phase 2 (normalization) requires sequential coordination with other museums.

## Phase boundary

```
PHASE 1 — INGEST (parallelizable, one agent per museum)
  Steps 1–7: API exploration → fixtures → raw table → ingest asset → registration
  Output: raw JSON in catalog.raw_{museum}, structural tests passing
  Can run ahead of normalization for other museums.

───────────────────────────────────────────────────────────────

PHASE 2 — NORMALIZATION (sequential, builds on prior museums)
  Steps 8–10: mapper → tests → normalize asset
  Each museum X+1 either confirms or forces revisions to the canonical
  vocabulary (periods, dynasties, geography formats, confidence encoding).
  May require updating earlier museums' mappers if the vocabulary changes.
```

## Before you start

- Docker must be running: `docker compose up -d` (Postgres + Typesense)
- Pipeline deps installed: `cd pipeline && uv sync`
- Confirm existing tests pass: `cd pipeline && uv run pytest`
- Read `CLAUDE.md` at the repo root for constitutional rules

## Phase 1: Ingest

### Step 1: Explore the API

**Goal:** Understand how to get Egyptian artifact data from this museum.

Research the museum's API: authentication, pagination, rate limits, data format, Egyptian collection filtering. Use browser network inspection, API docs, or direct experimentation.

Key questions to answer:
- How do you list all Egyptian artifacts? (department filter, culture filter, collection ID?)
- What fields come back? Which are useful for the canonical schema?
- What pagination mechanism? (page numbers, cursor, offset?)
- Authentication required? (API key, OAuth, none?)
- Rate limits or bot protection?
- What license applies to images?

**Examples from existing museums:**
- Met: Public REST API, department=10 for Egyptian, no auth, 80 objects/page. `docs/museum-sources/met.md`
- Harvard: Public API with API key, `culture=Egyptian`, 100/page. `docs/museum-sources/harvard.md`
- Brooklyn: Undocumented search API + RSC detail pages via Playwright (bot protection). `docs/museum-sources/brooklyn.md`

### Step 2: Document the source

**Goal:** Create `docs/museum-sources/{museum}.md` before writing any code.

This document is the agent's context for all future work on this museum. It must cover:
- API access method (endpoints, auth, headers)
- Pagination details (max page size, total count mechanism)
- Rate limits and bot protection
- Field inventory (what fields exist, which map to canonical schema)
- Data quality observations (sparse fields, encoding quirks, date formats)
- License terms for images
- Known quirks (anything surprising discovered during exploration)

**Verification:** The file must exist before proceeding. Structural tests enforce this.

```bash
ls docs/museum-sources/{museum}.md
```

### Step 3: Add fixture data

**Goal:** Save 3–5 real API responses to `pipeline/tests/fixtures/{museum}/`.

Choose diverse cases that exercise different mapper code paths:

| Fixture | Purpose | Example |
|---|---|---|
| `rich_object.json` | Well-catalogued, all fields populated | Isis Nursing Horus (Brooklyn 4035) |
| `sparse_no_image.json` | Minimal metadata, no image | Model of Hoe (Brooklyn 123351) |
| `ambiguous_provenance.json` | "Said to be from", "Reportedly from" | Funerary Cone (Brooklyn 118436) |
| Optional: culture edge case | Non-Egyptian in Egyptian dept | Cypriot Juglet (Brooklyn 3198) |
| Optional: date/dynasty quirk | Unusual date encoding or typo | Head of Akhenaten (Brooklyn 60260) |

Save the raw API response verbatim — do not modify the JSON. These fixtures are ground truth for mapper tests.

**Verification:**
```bash
ls pipeline/tests/fixtures/{museum}/*.json  # Should show 3+ files
```

### Step 4: Register the museum source

**Goal:** Add the museum to the type system.

**4a.** Add to `MuseumSource` enum in `pipeline/pipeline/types/sources.py`:
```python
class MuseumSource(str, Enum):
    MET = "met"
    BROOKLYN = "brooklyn"
    HARVARD = "harvard"
    YOUR_MUSEUM = "your_museum"  # lowercase, underscore-separated
```

**4b.** Add license to `MUSEUM_LICENSE` in the same file:
```python
MUSEUM_LICENSE: dict[MuseumSource, License] = {
    ...
    MuseumSource.YOUR_MUSEUM: License.CC0,  # or appropriate license
}
```

Check `docs/museum-sources/{museum}.md` for the correct license type.

**Verification:**
```bash
uv run pytest tests/test_structure.py::test_every_museum_has_license -v
```

### Step 5: Add the raw table

**Goal:** Create a Postgres table to store raw API responses verbatim.

**5a.** Add to `pipeline/pipeline/types/models.py`:
```python
raw_{museum}_table = Table(
    "raw_{museum}",
    metadata,
    Column("object_id", String, primary_key=True),
    Column("data", Text, nullable=False),
)
```

**5b.** Create and apply the Alembic migration:
```bash
uv run alembic revision --autogenerate -m "add raw_{museum} table"
uv run alembic upgrade head
```

**Verification:**
```bash
uv run pytest tests/test_structure.py -k "raw_table" -v
```

### Step 6: Create the ingest asset

**Goal:** Dagster asset that fetches all Egyptian objects and stores raw JSON.

Create `pipeline/pipeline/assets/ingest/{museum}.py` with:
- A `@asset(group_name="ingest")` function named `raw_{museum}`
- Pagination over the full Egyptian collection
- Each record stored verbatim as JSON in `raw_{museum}_table`
- Upsert (idempotent re-runs)
- Progress logging via `context.log.info`

**Pattern:** See `pipeline/assets/ingest/met.py` (simple HTTP) or `pipeline/assets/ingest/brooklyn.py` (Playwright for bot protection).

**Key rules:**
- Raw data is sacred. Store the API response byte-for-byte. Never transform during ingest.
- Raise on HTTP errors. No silent fallbacks.
- Batch DB writes (250 rows per batch is a good default).

### Step 7: Register in Dagster and verify

**Goal:** Wire the ingest asset into Dagster definitions.

**7a.** Import and register in `pipeline/pipeline/definitions.py`:
```python
from pipeline.assets.ingest.{museum} import raw_{museum}

defs = Definitions(
    assets=[
        ...,
        raw_{museum},
        ...,
    ],
    ...
)
```

**7b.** Run all structural tests:
```bash
uv run pytest tests/test_structure.py -v
```

All tests for this museum should pass except normalize-related ones (mapper, normalize asset, sync_search dep). Those come in Phase 2.

**7c.** Run the ingest via Dagster:
```bash
uv run dagster asset materialize -m pipeline.definitions --select raw_{museum}
```

**7d.** Verify data landed:
```sql
-- via: docker compose exec postgres psql -U hapi -d hapi
SELECT COUNT(*) FROM catalog.raw_{museum};
SELECT data::jsonb->>'title' FROM catalog.raw_{museum} ORDER BY random() LIMIT 5;
```

**Phase 1 is complete.** The raw data is in Postgres. Everything below requires understanding the canonical vocabulary and may affect other museums.

---

## Phase 2: Normalization

> **Sequential work.** Each museum's normalization builds on the canonical vocabulary established by prior museums. Expect to discover new patterns that require refining the vocabulary or updating earlier mappers.

### Step 8: Create the mapper

**Goal:** Pure function that transforms raw JSON → `CanonicalArtifact`.

Create `pipeline/pipeline/assets/normalize/{museum}.py` with a class implementing `MapperProtocol`:

```python
from pipeline.types.canonical import CanonicalArtifact
from pipeline.types.protocol import MapperProtocol
from pipeline.types.sources import MUSEUM_LICENSE, License, MuseumSource

class YourMuseumMapper(MapperProtocol):
    source = MuseumSource.YOUR_MUSEUM

    def map_to_canonical(self, raw: dict) -> CanonicalArtifact:
        source_id = str(raw["id"])  # adjust to actual ID field
        return CanonicalArtifact(
            id=f"{self.source.value}-{source_id}",
            source_museum=self.source.value,
            source_url=f"https://museum.example.org/objects/{source_id}",
            ...  # map all available fields
        )
```

**Key rules:**
- Mappers are pure transforms. No network calls, no DB writes, no side effects.
- Return `None` for absent optional fields. Most records are sparse — this is expected.
- Raise on structurally broken records (missing ID, unparseable data).
- Ruler/site matching happens in the enrich stage, NOT in mappers. Set `ruler_display_name` to the raw text value (or `None`). Don't try to resolve it.
- No string literals for domain values. Raw text goes in; authority resolution happens later.

**Decision points (may require vocabulary changes):**
- Does this museum have geography types not in the existing mapping? (Brooklyn had 11 types.)
- Does the department include non-Egyptian objects? (Brooklyn needed `is_egyptian()` filter.)
- Are there new date encoding patterns? (Brooklyn's ±3 offset for "ca." dates.)
- Does the museum have fields not in the canonical schema? (Brooklyn had `provenance`.)

If the canonical schema needs a new column: update SQLAlchemy model → Pydantic model → Alembic migration → Drizzle introspect → update ALL mappers that can populate the field.

### Step 9: Write mapper tests

**Goal:** Test every fixture with specific field value assertions.

Create `pipeline/tests/test_mappers/test_{museum}.py`:

```python
class TestRichObject:
    @pytest.fixture(autouse=True)
    def setup(self, mapper):
        raw = _load_fixture("rich_object.json")
        self.result = mapper.map_to_canonical(raw)

    def test_id(self):
        assert self.result.id == "{museum}-{expected_id}"

    def test_title(self):
        assert self.result.title == "Expected Title"

    # ... assert EVERY mapped field for this fixture
```

**Key rules (constitutional):**
- Assert specific values, not absence of errors. `assert self.result.title == "Exact Title"`, never just `assert self.result is not None`.
- Every fixture must have a corresponding test class.
- Every fixture test class must assert ALL mappable fields that the fixture populates.

**Verification:**
```bash
uv run pytest tests/test_mappers/test_{museum}.py -v
uv run pytest tests/test_structure.py -v  # mapper + fixture tests should now pass
```

### Step 10: Create the normalize asset and register

**Goal:** Dagster asset that reads raw data, runs the mapper, writes to artifacts table.

**10a.** Create `pipeline/pipeline/assets/normalize/{museum}_asset.py`:
- `@asset(group_name="normalize", deps=["raw_{museum}"])`
- Read from `raw_{museum}_table`, map via the mapper, upsert to `artifacts_table`
- Include any culture/collection filtering if the department has non-Egyptian objects
- Log counts (total raw, mapped, skipped)

See `pipeline/assets/normalize/met_asset.py` (simple) or `pipeline/assets/normalize/brooklyn_asset.py` (with culture filtering).

**10b.** Register in `pipeline/pipeline/definitions.py`:
```python
from pipeline.assets.normalize.{museum}_asset import normalize_{museum}

defs = Definitions(
    assets=[..., raw_{museum}, normalize_{museum}, ...],
    ...
)
```

**10c.** Add as dependency of `sync_search` in `pipeline/assets/index/sync_search.py`:
```python
@asset(
    ...
    deps=["normalize_met", "normalize_harvard", "normalize_brooklyn", "normalize_{museum}"],
)
```

**10d.** Full verification:
```bash
uv run pytest -v                                    # ALL tests pass
uv run dagster asset materialize -m pipeline.definitions --select normalize_{museum}
uv run dagster asset materialize -m pipeline.definitions --select sync_search
```

**10e.** Spot check:
```sql
SELECT COUNT(*) FROM catalog.artifacts WHERE source_museum = '{museum}';
SELECT title, period, dynasty FROM catalog.artifacts WHERE source_museum = '{museum}' ORDER BY random() LIMIT 5;
```

## Structural test enforcement

`pipeline/tests/test_structure.py` mechanically verifies every step above. When a test fails, the assertion message tells you exactly what file to create or what line to add. Run structural tests early and often:

```bash
uv run pytest tests/test_structure.py -v
```

These tests are the checklist. If they all pass for your museum, the integration is complete.

## Checklist summary

| Step | File(s) | Verification |
|---|---|---|
| 1. Explore API | (research) | You can answer all key questions |
| 2. Document source | `docs/museum-sources/{museum}.md` | File exists |
| 3. Fixtures | `tests/fixtures/{museum}/*.json` | 3+ diverse JSON files |
| 4. Register source | `pipeline/types/sources.py` | `test_every_museum_has_license` passes |
| 5. Raw table | `pipeline/types/models.py` + migration | `test_raw_table_exists` passes |
| 6. Ingest asset | `pipeline/assets/ingest/{museum}.py` | `test_ingest_asset` passes |
| 7. Dagster registration | `pipeline/definitions.py` | `test_dagster_registration` passes, data in DB |
| 8. Mapper | `pipeline/assets/normalize/{museum}.py` | `test_normalize_mapper` + `test_mapper_implements_protocol` pass |
| 9. Mapper tests | `tests/test_mappers/test_{museum}.py` | `test_mapper_tests_exist` passes, all assertions pass |
| 10. Normalize asset | `pipeline/assets/normalize/{museum}_asset.py` + definitions + sync_search dep | All structural tests pass, data in artifacts table |
