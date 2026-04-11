# Harness Engineering Scorecard

Date: 2026-04-10

This scorecard evaluates how well this repository aligns with the harness-engineering principles described in OpenAI's "Harness engineering: leveraging Codex in an agent-first world" (February 11, 2026).

Overall score: 7.5/10

The repository shows strong alignment on agent guidance, mechanical enforcement, schema ownership, and fixture-based feedback loops. The main gaps are in runtime observability, browser-driven validation, and closing the gap between documented harness ambitions and implemented tooling.

## Scorecard

| Category | Score | Assessment |
|---|---:|---|
| Agent guidance and progressive disclosure | 9/10 | Strong root and domain-specific instruction files with clear rules, commands, and architecture boundaries. |
| Repository as system of record | 8/10 | Good ADR coverage and harness docs, but some repo docs are still stale or scaffold-generated. |
| Mechanical enforcement | 9/10 | Structural tests encode key architectural and workflow invariants with remediation-oriented failures. |
| Feedback loops and verification | 8/10 | Pipeline and component-level loops are real and fast; browser-level and qualitative loops are still mostly planned. |
| Full-stack agent legibility | 6/10 | Pipeline is legible; web and runtime behavior are less exposed to agents than the article recommends. |
| Observability and runtime introspection | 3/10 | No visible local logs/metrics/traces stack or agent-facing observability tooling. |
| Autonomy readiness | 7/10 | The repo is shaped for agent contribution, but lacks some of the higher-order recovery and validation loops needed for deeper autonomy. |
| Documentation hygiene | 6/10 | Core docs are thoughtful, but at least one prominent README remains boilerplate and undermines trust. |

## Evidence

### 1. Agent guidance and progressive disclosure

Strong alignment.

- Root instructions establish non-negotiable rules, verification commands, and PR workflow in `CLAUDE.md`.
- Domain-specific instructions exist in `pipeline/CLAUDE.md` and `web/CLAUDE.md`.
- The harness approach is documented explicitly in `docs/harness.md`.

Why this matters:

Agents need a small, stable entry point with clear links to deeper context. This repository largely follows that model.

### 2. Repository as system of record

Good alignment, with some drift.

- Architecture and design rationale live in `docs/architecture.md` and `docs/adr/`.
- Museum-specific context is stored in `docs/museum-sources/`.
- Schema ownership is clearly documented: pipeline owns `catalog.*`, web introspects generated types from the live DB.
- However, `web/README.md` is still a default Next.js scaffold README and does not reflect the actual system.

Why this matters:

Harness engineering depends on repository-local, versioned context. Boilerplate or stale docs reduce agent trust in the repo as the source of truth.

### 3. Mechanical enforcement

Very strong alignment.

- `pipeline/tests/test_structure.py` is the clearest harness artifact in the repo.
- It enforces:
  - presence of ingest and normalize assets
  - mapper fixtures and tests
  - source documentation
  - schema consistency
  - protocol compliance
  - Dagster registration
  - dependency wiring into search sync
- Assertion failures act as remediation instructions, which is exactly the right pattern for agent work.

Why this matters:

This is the core harness-engineering move: encode invariants as tests instead of asking agents to remember them.

### 4. Feedback loops and verification

Good alignment, but uneven across subsystems.

- Pipeline tests are strong and fast: fixture-based mapper tests plus structural tests.
- Web has real tests for a critical invariant: license-aware image rendering.
- CI runs pipeline migrations before web checks, which catches schema drift.
- Local verification on 2026-04-10:
  - `cd pipeline && uv run pytest -q` -> 281 passed
  - `cd web && pnpm test` -> 8 passed
  - `cd web && pnpm typecheck` -> passed
  - `cd web && pnpm lint` -> warnings only

Gaps:

- No browser E2E suite is present.
- No Playwright config is present.
- No visible task-completion-based usability loop exists yet.

Why this matters:

The repo has deterministic code-level feedback, but not yet the application-level validation loops emphasized in the article.

### 5. Full-stack agent legibility

Moderate alignment.

- Pipeline behavior is legible through assets, tests, fixtures, and docs.
- Web conventions are documented, including server-only Typesense access and license-aware rendering.
- The current web app is still narrow in scope, and `web/CLAUDE.md` labels several key pages as planned rather than implemented.

Why this matters:

Agents work best when they can inspect, run, and validate the whole system. This repo is much closer on the pipeline side than the runtime/UI side.

### 6. Observability and runtime introspection

Weak alignment.

- `docs/harness.md` describes a mature future state with Dagster asset checks, LLM audits, fuzzy-match review automation, and Playwright-MCP-based web quality.
- The current repository does not appear to include:
  - a local observability stack
  - metrics or trace storage
  - agent-facing log/metric query tooling
  - implemented quality assets corresponding to those docs

Why this matters:

The article’s biggest leverage gains come from making runtime behavior legible to agents. That capability is largely absent here today.

### 7. Autonomy readiness

Good foundation, incomplete execution.

- The repo is clearly designed for agent contribution.
- PR workflow expectations are encoded in `CLAUDE.md`.
- The structural checks reduce common drift when extending the pipeline.

Gaps:

- No visible recurring doc-gardening or cleanup loop
- No visible background quality maintenance tasks
- No autonomous browser validation or runtime recovery loop

Why this matters:

The repo supports agent implementation well, but does not yet support the more autonomous end-to-end feature loop described in the article.

## Summary judgment

This repository is already practicing harness engineering in a meaningful way. The pipeline side, in particular, demonstrates the right instincts:

- clear agent instructions
- structured repository-local knowledge
- single-source-of-truth schema ownership
- fixture-driven tests
- mechanical enforcement of workflow and architecture

The main limitation is not philosophy but maturity. The docs describe a more advanced harness than the codebase currently implements. The next phase should focus less on adding more principles and more on closing that implementation gap.

## Highest-leverage next steps

1. Replace `web/README.md` with a real repo-specific operational document.
2. Add Playwright E2E coverage for search, filters, artifact pages, and license rendering.
3. Encode at least one deterministic Dagster `@asset_check` layer from `docs/harness.md` into actual pipeline assets.
4. Add a minimal observability surface for local agent runs: structured app logs first, then metrics if needed.
5. Add one recurring cleanup process that checks documentation freshness or structural drift.

## Recommended interpretation

If the question is "is this repo genuinely harness-oriented?", the answer is yes.

If the question is "does it already match the full sophistication of the article's agent-first environment?", the answer is no.

The current state is best described as:

"Strong harness-engineering foundation, especially in the pipeline; partial implementation of the broader agent-first operating model."
