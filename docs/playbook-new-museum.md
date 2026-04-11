# Playbook: Adding a New Museum

This is an operational playbook for agents adding a new Egyptian artifact source to Hapi. It is designed to be followed step-by-step with verification at each stage. An agent should be able to complete Phase 1 (ingest) independently; Phase 2 (normalization) requires sequential coordination with other museums.

## Phase boundary

```
PHASE 1 — INGEST (parallelizable, one agent per museum)
  Steps 1–7: API exploration → fixtures → raw history/current tables → ingest assets → registration
  Output: append-only raw history plus current snapshot for the source, structural tests passing
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

## Inclusion policy

Hapi is a cross-museum index of Egyptian artifacts. For new sources, use the museum's own classification as the primary inclusion signal, but do not treat it as infallible.

Rules:

- Preserve the museum's original classification signals verbatim in raw data: department, culture, geography, collection, period labels, and any similar source fields.
- Use the museum's own collection or culture classification as the default rule for what enters the ingest.
- If a source is known to mix non-Egyptian material into an Egyptian-facing collection, add explicit source-specific filtering rules during normalization and document them in `docs/museum-sources/{museum}.md`.
- Do not silently "correct" the museum's archaeology in the mapper. If a record is ambiguous, preserve the museum's labels and map uncertainty into canonical fields where possible.
- Exclude records only when they are clearly outside scope based on documented source behavior. The reason for exclusion must be legible in code comments or source notes.

Examples:

- A museum's "Egyptian Art" department is the default inclusion boundary.
- If that department is known to include Cypriot or broader Near Eastern material, add an explicit filter based on documented source fields.
- If a record is from Roman Egypt or Nubia but the museum classifies it as part of its Egyptian collection, keep it unless the product scope explicitly excludes it.

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
- What rights fields exist on each record or image?
- Is image licensing uniform across the whole museum, or does it vary per object?
- If rights data is missing on some records, what fallback policy is justified?

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
- Rights fields for images and whether they vary by object or are museum-wide defaults
- Inclusion and exclusion rules for Egyptian scope, including any known mixed-collection edge cases
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

Use `MUSEUM_LICENSE` only as a museum-level default when the source does not provide reliable per-record rights metadata. If the API exposes rights per object, the mapper should populate `CanonicalArtifact.license` from the record itself and only fall back to the museum default when necessary.

Check `docs/museum-sources/{museum}.md` for the correct default license policy.

**Verification:**
```bash
cd pipeline && uv run pytest tests/test_structure.py::test_every_museum_has_license -v
```

### Step 5: Add the raw table

**Goal:** Create Postgres tables to store both append-only source history and the latest current snapshot.

**5a.** Add to `pipeline/pipeline/types/models.py`:
```python
raw_{museum}_history_table = Table(
    "raw_{museum}_history",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("fetch_run_id", String, nullable=False, index=True),
    Column("object_id", String, nullable=False, index=True),
    Column("fetched_at", DateTime(timezone=True), nullable=False),
    Column("content_hash", String, nullable=False),
    Column("data", Text, nullable=False),
)

raw_{museum}_current_table = Table(
    "raw_{museum}_current",
    metadata,
    Column("object_id", String, primary_key=True),
    Column("history_id", Integer, nullable=False),
    Column("fetch_run_id", String, nullable=False, index=True),
    Column("fetched_at", DateTime(timezone=True), nullable=False),
    Column("content_hash", String, nullable=False),
    Column("data", Text, nullable=False),
)
```

Minimum metadata requirements:

- `object_id`: stable source identifier
- `fetch_run_id`: groups all rows observed in a single ingest execution
- `fetched_at`: when this payload was retrieved
- `content_hash`: deterministic hash of the raw payload for change detection
- `data`: the verbatim raw response

Also add a `fetch_runs` table so the pipeline can derive "current" from the latest successful ingest instead of inferring it from overwrites:

```python
fetch_runs_table = Table(
    "fetch_runs",
    metadata,
    Column("id", String, primary_key=True),
    Column("source_museum", String, nullable=False, index=True),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True)),
    Column("status", String, nullable=False),
)
```

Rationale:

- `raw_{museum}_history` is the audit log of what the museum said over time.
- `raw_{museum}_current` is the latest successful snapshot used by normalization.
- `fetch_runs` makes "current" explicit and reproducible.

**5b.** Create and apply the Alembic migration:
```bash
cd pipeline && uv run alembic revision --autogenerate -m "add raw_{museum} table"
cd pipeline && uv run alembic upgrade head
```

**Verification:**
```bash
cd pipeline && uv run pytest tests/test_structure.py -k "raw_table" -v
```

### Step 6: Create the ingest asset

**Goal:** Dagster assets that fetch all Egyptian objects into append-only history, then derive the current snapshot.

Create `pipeline/pipeline/assets/ingest/{museum}.py` with:
- A `@asset(group_name="ingest")` function named `raw_{museum}_history`
- A second `@asset(group_name="ingest", deps=["raw_{museum}_history"])` function named `raw_{museum}_current`
- Pagination over the full Egyptian collection
- Each record stored verbatim as JSON in `raw_{museum}_history_table`
- A fetch run row created in `fetch_runs`
- `raw_{museum}_current` rebuilt from the latest successful fetch run
- Progress logging via `context.log.info`

**Pattern:** See `pipeline/pipeline/assets/ingest/met.py` (simple HTTP) or `pipeline/pipeline/assets/ingest/brooklyn.py` (Playwright for bot protection).

**Key rules:**
- Raw data is sacred. Store the API response byte-for-byte. Never transform during ingest.
- Raise on HTTP errors. No silent fallbacks.
- Batch DB writes (250 rows per batch is a good default).
- Persist fetch metadata alongside the raw payload so later source changes are auditable.
- Do not apply archaeological inclusion/exclusion logic during ingest unless the source API itself requires a coarse collection filter to avoid pulling the whole museum.
- History is append-only. Do not overwrite prior source observations.
- Current is derived, not fetched separately. It must always correspond to one successful `fetch_run_id`.

### Step 7: Register in Dagster and verify

**Goal:** Wire the ingest asset into Dagster definitions.

**7a.** Import and register in `pipeline/pipeline/definitions.py`:
```python
from pipeline.assets.ingest.{museum} import raw_{museum}_current, raw_{museum}_history

defs = Definitions(
    assets=[
        ...,
        raw_{museum}_history,
        raw_{museum}_current,
        ...,
    ],
    ...
)
```

**7b.** Run structural tests to see your progress:
```bash
cd pipeline && uv run pytest tests/test_structure.py -v
```

Phase 1 tests (raw tables, source docs, Dagster registration, fixtures) should now pass. Normalize-related tests (normalize_mapper, normalize_asset, mapper_tests, sync_search dep) will fail — that is expected and becomes your Phase 2 checklist.

**7c.** Run the ingest via Dagster:
```bash
cd pipeline && uv run dagster asset materialize -m pipeline.definitions --select raw_{museum}_history,raw_{museum}_current
```

**7d.** Verify data landed:
```sql
-- via: docker compose exec postgres psql -U hapi -d hapi
SELECT COUNT(*) FROM catalog.raw_{museum}_history;
SELECT COUNT(*) FROM catalog.raw_{museum}_current;
SELECT data::jsonb->>'title' FROM catalog.raw_{museum}_current ORDER BY random() LIMIT 5;
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
- Use per-record rights metadata when available. Only fall back to `MUSEUM_LICENSE` when the source does not expose usable object-level rights information.

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
cd pipeline && uv run pytest tests/test_mappers/test_{museum}.py -v
cd pipeline && uv run pytest tests/test_structure.py -v  # mapper + fixture tests should now pass
```

### Step 10: Create the normalize asset and register

**Goal:** Dagster asset that reads raw data, runs the mapper, writes to artifacts table.

**10a.** Create `pipeline/pipeline/assets/normalize/{museum}_asset.py`:
- `@asset(group_name="normalize", deps=["raw_{museum}"])`
- Read from `raw_{museum}_current_table`, map via the mapper, upsert to `artifacts_table`
- Include any culture/collection filtering if the department has non-Egyptian objects
- Log counts (total raw, mapped, skipped)

Filtering policy:

- Use the museum's classification as the default boundary.
- Add source-specific exclusion logic only when the source is known to include clearly out-of-scope material.
- Keep filtering rules narrow, explicit, and documented in `docs/museum-sources/{museum}.md`.
- When in doubt, prefer preserving the record with uncertainty metadata over aggressive exclusion.

See `pipeline/pipeline/assets/normalize/met_asset.py` (simple) or `pipeline/pipeline/assets/normalize/brooklyn_asset.py` (with culture filtering).

**10b.** Register in `pipeline/pipeline/definitions.py`:
```python
from pipeline.assets.normalize.{museum}_asset import normalize_{museum}

defs = Definitions(
    assets=[..., raw_{museum}, normalize_{museum}, ...],
    ...
)
```

**10c.** Add as dependency of `sync_search` in `pipeline/pipeline/assets/index/sync_search.py`:
```python
@asset(
    ...
    deps=["normalize_met", "normalize_harvard", "normalize_brooklyn", "normalize_{museum}"],
)
```

**10d.** Full verification:
```bash
cd pipeline && uv run pytest -v                                    # ALL tests pass
cd pipeline && uv run dagster asset materialize -m pipeline.definitions --select normalize_{museum}
cd pipeline && uv run dagster asset materialize -m pipeline.definitions --select sync_search
```

**10e.** Spot check:
```sql
SELECT COUNT(*) FROM catalog.artifacts WHERE source_museum = '{museum}';
SELECT title, period, dynasty FROM catalog.artifacts WHERE source_museum = '{museum}' ORDER BY random() LIMIT 5;
```

## Structural test enforcement

`pipeline/tests/test_structure.py` mechanically verifies the integration scaffold: required files, registration, protocol compliance, and some schema invariants. When a test fails, the assertion message tells you exactly what file to create or what line to add. Run structural tests early and often:

```bash
cd pipeline && uv run pytest tests/test_structure.py -v
```

These tests are the checklist for structural completeness, not proof of data quality. Passing them means the integration is wired correctly enough to proceed. It does not prove:

- ingest completeness
- correct history/current snapshot derivation
- correct Egyptian-scope filtering
- accurate date parsing
- correct rights mapping
- reliable authority resolution

The integration is only complete after structural tests pass, mapper tests pass, the Dagster assets materialize successfully, and spot checks confirm the source-specific archaeological and licensing assumptions are actually correct.

## Checklist summary

| Step | File(s) | Verification |
|---|---|---|
| 1. Explore API | (research) | You can answer all key questions |
| 2. Document source | `docs/museum-sources/{museum}.md` | File exists |
| 3. Fixtures | `pipeline/tests/fixtures/{museum}/*.json` | 3+ diverse JSON files |
| 4. Register source | `pipeline/pipeline/types/sources.py` | `test_every_museum_has_license` passes |
| 5. Raw history/current tables | `pipeline/pipeline/types/models.py` + migration | raw-table structural tests pass |
| 6. Ingest assets | `pipeline/pipeline/assets/ingest/{museum}.py` | File exists; Dagster sees `raw_{museum}_history` and `raw_{museum}_current` |
| 7. Dagster registration | `pipeline/pipeline/definitions.py` | ingest assets registered, history + current data in DB |
| 8. Mapper | `pipeline/pipeline/assets/normalize/{museum}.py` | `test_normalize_mapper` + `test_mapper_implements_protocol` pass |
| 9. Mapper tests | `pipeline/tests/test_mappers/test_{museum}.py` | `test_mapper_tests_exist` passes, all assertions pass |
| 10. Normalize asset | `pipeline/pipeline/assets/normalize/{museum}_asset.py` + definitions + sync_search dep | All structural tests pass, current snapshot maps into artifacts table |
