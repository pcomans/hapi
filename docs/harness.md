# Harness Engineering

This project is built entirely by AI agents (Claude, Opus). The harness — the structure, contracts, docs, tests, and feedback loops surrounding the code — is the primary engineering artifact. The code is the output; the harness is the product.

This approach is informed by OpenAI's "Harness Engineering" methodology (2026), which demonstrated that 3 engineers shipped ~1 million lines of code across ~1,500 PRs without writing source code manually, by investing in the environment the agent works within.

## Constitutional rules

The root `CLAUDE.md` defines eight constitutional rules — non-negotiable principles that every agent must respect. They are the highest-authority instructions in the repo. The full list lives there (single source of truth); here we explain the reasoning behind the design.

### Why constitutional rules exist

AI agents are stateless between sessions. They don't remember that we decided "no defensive programming" three conversations ago. Without explicit, prominent, top-level rules, each new session starts from a blank slate and an agent will default to its training priors (add try/except, write defensive code, create abstractions "just in case").

Constitutional rules solve this by being:
- **Visible**: In `CLAUDE.md` at the root, loaded automatically by every agent session
- **Non-negotiable**: Framed as absolutes, not suggestions. "No defensive programming" not "prefer to avoid defensive programming"
- **Mechanically enforced where possible**: Rule 2 (deterministic enforcement over convention) is self-referential — each rule should have a corresponding test or CI check. The structural tests in `test_structure.py` already enforce several of these.

### How they relate to the rest of the harness

```
Constitutional rules (CLAUDE.md)      — What is NEVER allowed
    ↓
Procedural rules (CLAUDE.md)          — How to do specific things
    ↓
Domain instructions (pipeline/ web/)  — Where and in what order
    ↓
Structural tests (test_structure.py)  — Mechanical enforcement
```

The constitutional rules inform everything below them. "No defensive programming" shapes how mappers are written (pipeline/CLAUDE.md), how tests are structured (assert values, not absence of errors), and what code review catches. "Single source of truth" is why we use Drizzle introspection instead of hand-written types, and why authority data is JSON files instead of inline strings.

## Core principle

**If a machine can verify it, encode it in code. If it's rationale, context, or guidance for the agent's judgment, put it in markdown.**

Markdown that duplicates what code already says will drift and become misleading. The schema is the SQLAlchemy table in `pipeline/pipeline/types/models.py`, not a prose description of the schema. The field mappings are mapper code + fixture-based tests, not a document describing how fields map.

## How this repo is structured as a harness

### 1. Layered CLAUDE.md (progressive disclosure)

```
CLAUDE.md                    # Root: architecture overview, key commands, rules
├── pipeline/CLAUDE.md       # Pipeline-specific: how to add a museum, mapper protocol, testing
└── web/CLAUDE.md            # Web-specific: rendering rules, page structure, commands
```

The root file is the entry point — small and directive. Each subdirectory has domain-specific instructions. An agent working on a mapper reads the pipeline CLAUDE.md; an agent working on a component reads the web CLAUDE.md. Neither needs to load the other's context.

### 2. Pipeline owns the data schema, separate Postgres schemas (ADR-011)

Pipeline and web tables live in the same Postgres database but in separate Postgres schemas (namespaces): `catalog.*` (owned by Alembic/SQLAlchemy) and `web.*` (owned by Drizzle). The `catalog` schema contains artifact data, raw museum data, and fuzzy match reviews. The `web` schema contains app-specific tables like users, settings, and saved searches.

The Postgres table definitions in `pipeline/pipeline/types/models.py` (SQLAlchemy with `MetaData(schema="catalog")`) are the single source of truth for data tables. Alembic manages migrations with `version_table_schema="catalog"`.

This means:
- **Pipeline**: SQLAlchemy table → Alembic migration → `catalog.*` tables. Pydantic `CanonicalArtifact` is validated against the table by a structural test.
- **Web (reading catalog data)**: `drizzle-kit introspect` → generated `schema.ts` → `$inferSelect` types. No hand-written types.
- **Web (own tables)**: Drizzle schema definitions → Drizzle migrations → `web.*` tables. Independent of the pipeline.
- **CI**: Pipeline migrations run first, then web typecheck. If the pipeline changes a column and Drizzle's schema.ts isn't regenerated, the web build fails.
- **Schema creation**: `docker/init-schemas.sql` creates both schemas (`CREATE SCHEMA IF NOT EXISTS catalog; CREATE SCHEMA IF NOT EXISTS web;`) on first DB init.

The database is the contract — no separate schema file to keep in sync.

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
- **Fuzzy match routing**: All fuzzy matches (no exact variant hit) go to the review queue (see below)

Coverage metrics (% of records with ruler, site, image) are emitted as Dagster asset metadata, tracked over time in the Dagster UI.

### Layer 2: LLM data audit (sample-based)

A Dagster asset (`quality/llm_audit`) samples records and uses an LLM (Haiku for cost) to:

- **Semantic audit**: "Does this ruler attribution match the artifact's description and period?"
- **Batch anomaly detection**: "49 records from Deir el-Bahri are Dynasty 18; this one says Dynasty 26 — misattributed or unusual?"
- **Authority variant suggestion**: "Is 'Thutmosis III' a known variant of an existing entry?"

Runs on new/changed records only. Generates suggestions for human review, never auto-merges authority changes.

### Layer 3: Fuzzy match review queue

Enrichment first attempts exact match against all known variants in the authority files. When no exact match is found, fuzzy string matching guesses the closest entry — but all fuzzy matches go to the `fuzzy_match_reviews` table regardless of score (Levenshtein distances are unreliable for Egyptological names). An LLM agent triages pending reviews — approving obvious matches (e.g., "Menkheperre" → Thutmose III), rejecting clear mismatches, and escalating uncertain cases to a human. Approved variants are added to the authority files so future occurrences resolve via exact match. See [ADR-009](adr/009-review-queue.md).

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
