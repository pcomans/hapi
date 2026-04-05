# Harness Engineering

This project is built entirely by AI agents (Claude, Opus). The harness — the structure, contracts, docs, tests, and feedback loops surrounding the code — is the primary engineering artifact. The code is the output; the harness is the product.

This approach is informed by OpenAI's "Harness Engineering" methodology (2026), which demonstrated that 3 engineers shipped ~1 million lines of code across ~1,500 PRs without writing source code manually, by investing in the environment the agent works within.

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

### 2. Shared schema as mechanical contract

`shared/schema.json` is the single source of truth for the canonical artifact record. Both sides derive from it:

- **Pipeline**: Pydantic models validated against the JSON Schema
- **Web**: TypeScript types generated from the same JSON Schema
- **CI**: A structural test verifies both sides conform

This makes it impossible for the two halves to drift apart. The agent doesn't need to remember to update both — CI catches it.

### 3. Protocol + structural tests (encode architecture as assertions)

Rather than relying on the agent to understand architectural patterns, encode them mechanically:

- `MapperProtocol` — every museum mapper must implement this typed interface
- `test_structure.py` — verifies every registered museum has an ingest asset, a mapper, and fixture data
- Schema conformance tests — verify Pydantic and Drizzle types match `schema.json`

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

## What lives where

| Content | Where | Why |
|---|---|---|
| Canonical artifact schema | `shared/schema.json` (JSON Schema with `description` per field) | Machine-readable, generates types for both languages |
| Field mapping logic | Mapper code + fixture-based tests | Tests are the spec, can't drift |
| Mapper interface contract | Python `Protocol` class + structural test | CI enforces it |
| Schema consistency (Python <-> TS) | CI test that validates both derive from `schema.json` | Mechanical enforcement |
| Ruler authority data | `pipeline/pipeline/authority/rulers.json` (typed, with variant arrays) | Queryable data, not prose |
| Site hierarchy | `pipeline/pipeline/authority/sites.json` (with Pleiades IDs, parent refs) | Queryable data, not prose |
| Museum API quirks + rate limits | `docs/museum-sources/{museum}.md` | Judgment context for the agent |
| Architecture decisions | `docs/architecture.md` | Prevents undoing decisions |
| "How to add a museum" playbook | `pipeline/CLAUDE.md` | Step-by-step for agent |
| License terms per museum | Typed enum/config in code | Rendering logic depends on it |
| Confidence tier definitions | Code constants + comments | Matching logic uses these directly |
