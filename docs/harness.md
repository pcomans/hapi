# Harness Engineering

This project is built entirely by AI agents (Claude, Opus). The harness — the structure, contracts, docs, tests, and feedback loops surrounding the code — is the primary engineering artifact. The code is the output; the harness is the product.

This approach is informed by OpenAI's "Harness Engineering" methodology (2026), which demonstrated that 3 engineers shipped ~1 million lines of code across ~1,500 PRs without writing source code manually, by investing in the environment the agent works within.

## Development philosophy

**Fail fast, no defensive programming.** During development, every error should be loud and immediate. If a mapper hits a malformed record, it raises — it does not silently skip, return partial results, or wrap in try/except. A failing pipeline means a fixture is missing or the logic has a bug, and both must be fixed before proceeding.

This applies across the stack:
- **Mappers**: Raise on malformed records. Don't handle edge cases that haven't been seen in real data yet.
- **Web components**: Let TypeScript catch type errors at compile time. Don't add runtime validation for data coming from our own database.
- **Tests**: Assert specific values, not "it doesn't crash." A test that catches exceptions is hiding bugs.

Once a module is validated against real data and stable, error handling will be added for incoming data quality issues (museum APIs returning unexpected formats, missing fields in new records). Until then: loud failures, no defensive programming.

## Core principle

**If a machine can verify it, encode it in code. If it's rationale, context, or guidance for the agent's judgment, put it in markdown.**

Markdown that duplicates what code already says will drift and become misleading. The schema is `shared/schema.json`, not a prose description of the schema. The field mappings are mapper code + fixture-based tests, not a document describing how fields map.

## How this repo is structured as a harness

### 1. Layered CLAUDE.md (progressive disclosure)

```
CLAUDE.md                    # Root: architecture overview, key commands, rules
├── pipeline/CLAUDE.md       # Pipeline-specific: how to add a museum, mapper protocol, testing
└── web/CLAUDE.md            # Web-specific: rendering rules, page structure, commands
```

The root file is the entry point — small and directive. Each subdirectory has domain-specific instructions. An agent working on a mapper reads the pipeline CLAUDE.md; an agent working on a component reads the web CLAUDE.md. Neither needs to load the other's context.

### 2. Pipeline owns the DB schema (ADR-011)

The Postgres table definitions in `pipeline/pipeline/types/models.py` (SQLAlchemy) are the single source of truth. Alembic manages migrations. The web app generates its Drizzle types by running `drizzle-kit introspect` against the live database.

This means:
- **Pipeline**: SQLAlchemy table → Alembic migration → Postgres. Pydantic `CanonicalArtifact` is validated against the table by a structural test.
- **Web**: `drizzle-kit introspect` → generated `schema.ts` → `$inferSelect` types. No hand-written types.
- **CI**: Pipeline migrations run first, then web typecheck. If the pipeline changes a column and Drizzle's schema.ts isn't regenerated, the web build fails.

No `shared/schema.json` — the database is the contract.

### 3. Protocol + structural tests (encode architecture as assertions)

Rather than relying on the agent to understand architectural patterns, encode them mechanically:

- `MapperProtocol` — every museum mapper must implement this typed interface
- `test_structure.py` — verifies every registered museum has an ingest asset, a mapper, and fixture data
- Schema consistency test — verifies SQLAlchemy table columns match Pydantic model fields

These tests fail before the agent can introduce architectural drift.

### 4. Fixture data as ground truth

Real museum API responses are saved in `pipeline/tests/fixtures/{museum}/`. Mapper tests run against these fixtures with expected outputs. When the agent modifies a mapper, it gets immediate pass/fail feedback against real data shapes. No mocking, no guessing.

### 5. Feedback loops via test commands

Every agent action has a verification step:

| Agent action | Feedback command |
|---|---|
| Changes a mapper | `cd pipeline && pytest tests/test_mappers/` |
| Changes canonical schema | `cd pipeline && pytest tests/test_structure.py` + `cd web && pnpm typecheck` |
| Changes a web component | `cd web && pnpm test && pnpm lint && pnpm typecheck` |
| Adds a new museum | Follow checklist in `pipeline/CLAUDE.md`, then `pytest` |

### 6. Docs that earn their keep

Only three kinds of markdown exist in this repo:

1. **CLAUDE.md files** — instructions to the agent (what to do, where, in what order)
2. **Architecture decisions** (`docs/architecture.md`) — rationale that prevents the agent from undoing decisions
3. **Museum source notes** (`docs/museum-sources/`) — API quirks, rate limits, data quality observations, license terms. Context the agent needs *before* writing code that the code itself can't express.

Everything else is in code: types, tests, protocols, config, authority data files.

## Quality evaluation

The harness has three layers of quality checks beyond linting and type checking. The principle: **use deterministic checks where possible, LLMs where judgment is needed, and always prefer task completion over opinions.**

See [ADR-010](adr/010-quality-evaluation.md) for the full rationale.

### Layer 1: Deterministic pipeline checks (every run)

Implemented as Dagster `@asset_check` decorators, co-located with the assets they validate.

- **Ingest completeness**: Record count vs API total, change detection via content hash
- **Normalization validity**: Date ranges, enum values, ID formats, field fill rates
- **Authority coverage**: Unmatched value frequency ranking (high-frequency unmatched = authority gap)
- **Cross-museum consistency**: Same place name from different museums resolves to same site ID
- **Fuzzy match confidence**: Matches below 0.85 go to the review queue (see below)

Coverage metrics (% of records with ruler, site, image) are emitted as Dagster asset metadata, tracked over time in the Dagster UI.

### Layer 2: LLM data audit (sample-based)

A Dagster asset (`quality/llm_audit`) samples records and uses an LLM (Haiku for cost) to:

- **Semantic audit**: "Does this ruler attribution match the artifact's description and period?"
- **Batch anomaly detection**: "49 records from Deir el-Bahri are Dynasty 18; this one says Dynasty 26 — misattributed or unusual?"
- **Authority variant suggestion**: "Is 'Thutmosis III' a known variant of an existing entry?"

Runs on new/changed records only. Generates suggestions for human review, never auto-merges authority changes.

### Layer 3: Fuzzy match review queue

Low-confidence matches are written to a `fuzzy_match_reviews` table. An LLM agent processes pending reviews — approving obvious matches (e.g., "Menkheperre" → Thutmose III), rejecting clear mismatches, and escalating uncertain cases to a human. See [ADR-009](adr/009-review-queue.md).

### Layer 4: Web quality (Playwright + Playwright MCP)

**Deterministic (CI on every PR):**
- E2E functional tests: search returns results, filters work, detail pages load
- Visual regression: `toHaveScreenshot()` pixel-diff at desktop + mobile viewports
- License rendering: DOM assertions verify `img` tag for CC0, link-out for restricted

**LLM usability via Playwright MCP (periodic):**

Instead of screenshot-based opinions, the LLM drives the browser and attempts real user tasks. This is cheaper (DOM text vs vision tokens) and more meaningful (task completion vs subjective assessment).

| Evaluation | LLM task |
|---|---|
| Search usability | "Find all artifacts from Karnak. Use the search and filters." |
| Artifact discovery | "Find companion pieces for this artifact." |
| Museum browsing | "Browse the Met's Dynasty 18 collection filtered by ruler." |
| Mobile usability | "Complete a search on a 375px viewport." |

If the LLM can't accomplish the task, a human probably can't either.

## What lives where

| Content | Where | Why |
|---|---|---|
| DB schema (source of truth) | `pipeline/pipeline/types/models.py` (SQLAlchemy) + Alembic migrations | Pipeline owns the schema; web introspects from DB |
| Pydantic validation model | `pipeline/pipeline/types/canonical.py` | Validated against SQLAlchemy table by structural test |
| Web TypeScript types | `web/src/lib/db/schema.ts` (generated by `drizzle-kit introspect`) | Derived from live DB, not hand-written |
| Field mapping logic | Mapper code + fixture-based tests | Tests are the spec, can't drift |
| Mapper interface contract | Python `Protocol` class + structural test | CI enforces it |
| Ruler authority data | `pipeline/pipeline/authority/rulers.json` (typed, with variant arrays) | Queryable data, not prose |
| Site hierarchy | `pipeline/pipeline/authority/sites.json` (with Pleiades IDs, parent refs) | Queryable data, not prose |
| Museum API quirks + rate limits | `docs/museum-sources/{museum}.md` | Judgment context for the agent |
| Architecture decisions | `docs/adr/` (individual decision records) | Prevents undoing decisions |
| "How to add a museum" playbook | `pipeline/CLAUDE.md` | Step-by-step for agent |
| License terms per museum | Typed enum/config in code | Rendering logic depends on it |
| Confidence tier definitions | Code constants + comments | Matching logic uses these directly |
