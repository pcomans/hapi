# ADR-010: Quality Evaluation — Deterministic Checks + LLM Layers

## Status
Accepted

## Context
The project has linting and type checks for technical correctness, but no tooling for evaluating whether the data and the UI are actually good. Two distinct quality problems exist:

1. **Data quality**: Is the ingested/normalized data complete and correct?
2. **Web quality**: Does the website work well, look right, and serve users effectively?

Both need a mix of deterministic checks (fast, cheap, reliable) and LLM evaluation (for judgment calls that can't be reduced to assertions).

## Decision

### Data Quality — Dagster Asset Checks

All data quality checks are implemented as Dagster `@asset_check` decorators, co-located with the assets they validate. No external frameworks (Great Expectations, Soda) — Dagster's native asset checks are sufficient at this scale.

#### Deterministic checks (every pipeline run)

| Check | Asset stage | What it catches |
|---|---|---|
| Record count vs API total | Ingest | Missed artifacts during ingest |
| Field fill rate (% with ruler, site, image) | Normalize | Authority list gaps, sparse data |
| Value range validation (dates > -4000 BCE, `date_start < date_end`) | Normalize | Bad date parsing |
| Format validation (Wikidata IDs match `Q\d+`, enums valid) | Normalize | Mapper field errors |
| Unmatched value frequency ranking | Enrich | Authority list gaps (200 records saying "Thutmosis III" with no match = gap) |
| Fuzzy match confidence threshold | Enrich | False matches → review queue (ADR-009) |
| Cross-museum site consistency | Enrich | Different museums resolving to different site IDs for the same place |
| Change detection (content hash diff) | Ingest | Museum data updates between runs |

Coverage metrics are emitted as Dagster asset metadata, giving time-series tracking in the Dagster UI for free.

#### LLM checks (sample-based, on new/changed records)

| Check | What it catches |
|---|---|
| Semantic audit: "Does ruler attribution match the artifact description?" | Mapper pulling the wrong field, plausible-but-wrong attributions |
| Batch anomaly detection: "49 records from Deir el-Bahri are Dynasty 18; this one says Dynasty 26" | Outliers hiding in bulk data |
| Authority variant suggestion: "Is 'Thutmosis III' a variant of an existing entry?" | Unknown name variants for human review |

LLM checks use Haiku for cost efficiency. They run as a Dagster asset (`quality/llm_audit`) that samples N records per run (default 50).

### Web Quality — Playwright + Playwright MCP

#### Deterministic checks (CI on every PR)

| Check | Tool |
|---|---|
| E2E functional tests (search, filters, detail pages) | Playwright assertions |
| Visual regression (layout broke?) | Playwright `toHaveScreenshot()` pixel-diff |
| License rendering correctness | Playwright DOM assertions (check `img` vs `a` tag based on license field) |

#### LLM usability evaluation (Playwright MCP)

Instead of taking screenshots and asking an LLM "does this look usable?" (expensive in vision tokens, and just an opinion), we use Playwright MCP to have the LLM actually attempt user tasks.

The LLM drives the browser — it types, clicks, navigates, reads DOM text — and tries to accomplish the same tasks a real user would. If the LLM can't do it, a human probably can't either.

| Evaluation | LLM task |
|---|---|
| Search usability | "Find all artifacts from Karnak. Use the search and filters." |
| Artifact discovery | "Find companion pieces for this artifact. Navigate from the detail page." |
| Museum browsing | "Browse the Met's Dynasty 18 collection filtered by ruler." |
| Mobile usability | "Complete a search on a 375px viewport. Can you access all filters?" |

This is cheaper than vision (DOM text vs image tokens) and more meaningful (actual task completion vs subjective assessment).

**Screenshots are still used for one thing:** Playwright's `toHaveScreenshot()` pixel-diff for visual regression. This is deterministic and doesn't involve an LLM.

## Consequences
- Data quality issues are caught at the pipeline level, not discovered by users
- Coverage metrics track data completeness over time
- The review queue (ADR-009) handles fuzzy match uncertainty without blocking the pipeline
- Web quality is validated by task completion (can the LLM use the site?) not opinions about screenshots
- LLM costs are controlled: Haiku for data audit, sample-based (not exhaustive), DOM text not images
- Deterministic checks run on every PR/pipeline execution; LLM checks are periodic/on-demand
