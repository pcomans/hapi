# ADR-009: Fuzzy Match Review Queue with LLM Triage

## Status
Accepted

## Context
The enrichment stage uses fuzzy string matching to resolve raw museum text ("Menkheperre", "Deir el-Bahari") to canonical authority IDs ("thutmose-iii", "deir-el-bahri"). Fuzzy matching produces false positives, especially for: short strings, transliteration variants across languages, and names shared by multiple rulers (e.g., multiple pharaohs named Amenhotep).

We need a way to catch low-confidence matches without blocking the pipeline or requiring constant human oversight.

## Decision
Low-confidence fuzzy matches (below a configurable threshold, initially 0.85) are written to a review queue table in Postgres rather than being silently accepted or rejected. An LLM agent processes the queue, and uncertain cases are escalated to a human.

### Review queue schema

```sql
CREATE TABLE fuzzy_match_reviews (
    id SERIAL PRIMARY KEY,
    artifact_id TEXT NOT NULL,
    field TEXT NOT NULL,           -- 'ruler' or 'site'
    raw_value TEXT NOT NULL,       -- what the museum record said
    matched_id TEXT,               -- authority ID the fuzzy matcher chose (NULL if no match)
    confidence FLOAT NOT NULL,     -- fuzzy match score (0.0 - 1.0)
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'approved', 'rejected'
    reviewed_by TEXT,              -- 'llm' or 'human'
    review_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ
);
```

### LLM triage process

1. Query all `status = 'pending'` rows
2. For each, fetch the full artifact record + the authority entry it matched against
3. Ask the LLM: "The museum record says '{raw_value}'. The fuzzy matcher mapped this to '{matched_display_name}' (variants: {variant_list}) with {confidence}% confidence. Given the artifact's title, period, and description, is this match correct?"
4. LLM responds with APPROVED / REJECTED / UNCERTAIN + reasoning
5. APPROVED and REJECTED are written back with `reviewed_by = 'llm'`
6. UNCERTAIN rows remain `pending` for human review

### When triage runs

- As a Dagster asset (`quality/review_queue_triage`) that materializes after the enrich stage
- Can also be run manually via a Claude Code session: "Process the review queue"
- Uses a cheap model (Haiku) for initial triage; uncertain cases can be escalated to a stronger model

## Consequences
- Low-confidence matches are surfaced, not silently accepted — prevents false attributions from reaching users
- The LLM handles the majority of cases correctly (Egyptological name variants are well within LLM knowledge)
- Human review effort is minimized to genuinely ambiguous cases
- The review table provides an audit trail: which matches were human-verified vs LLM-verified
- Match threshold (0.85) is tunable — lower it as confidence in the authority list grows
- The same pattern works for both ruler and site matching
