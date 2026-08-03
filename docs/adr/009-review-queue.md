# ADR-009: Fuzzy Match Review Queue with LLM Triage

## Status
Accepted

## Context
The enrichment stage resolves raw museum text ("Menkheperre", "Deir el-Bahari") to canonical authority IDs ("thutmose-iii", "deir-el-bahri"). The primary path is exact match against known variants in the authority files. When no exact match is found, a fuzzy string fallback guesses the closest entry — but fuzzy matching produces false positives, especially for: short strings, transliteration variants across languages, and names shared by multiple rulers (e.g., multiple pharaohs named Amenhotep). Levenshtein-based scores are particularly unreliable because edit distance doesn't correlate with identity ("Thutmose III" → "Thutmose IV" scores higher than "Thutmose III" → "Tuthmosis", which is the same ruler).

We need a way to catch these fuzzy matches without blocking the pipeline or requiring constant human oversight.

## Decision
Unresolved matches are written to a review queue table in Postgres rather than being silently accepted or rejected. An LLM agent processes the queue, and uncertain cases are escalated to a human.

### Two-stage matching

Authority files (rulers.json, sites.json) include explicit variant arrays for each entry (e.g., Thutmose III has variants `["Tuthmosis III", "Menkheperre", "Djehutymes III", ...]`). Matching uses a two-stage strategy:

1. **Exact match against all variants first.** Case-insensitive, whitespace-normalized. This handles known transliterations with zero ambiguity and is the primary matching path.
2. **Fuzzy fallback for unlisted variants.** If no exact match is found, fuzzy string matching (rapidfuzz, token_sort_ratio) is used against all variant strings. Any fuzzy match — regardless of score — goes to the review queue. This is deliberate: Levenshtein-based ratios are unreliable in Egyptology because edit distance doesn't correlate with identity. "Thutmose III" is closer to "Thutmose IV" (distance 1) than to "Tuthmosis" (the same ruler). Fuzzy matches are never auto-accepted.

When a fuzzy match is approved, the variant should be added to the authority file so future occurrences resolve via exact match.

### Review queue schema

```sql
CREATE TABLE fuzzy_match_reviews (
    id SERIAL PRIMARY KEY,
    artifact_id TEXT NOT NULL,
    field TEXT NOT NULL,           -- 'ruler' or 'site'
    raw_value TEXT NOT NULL,       -- what the museum record said
    matched_id TEXT,               -- authority ID the fuzzy matcher chose (NULL if no match)
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
3. Ask the LLM: "The museum record says '{raw_value}'. The fuzzy matcher's best guess is '{matched_display_name}' (known variants: {variant_list}). Given the artifact's title, period, and description, is this the same entity?"
4. LLM responds with APPROVED / REJECTED / UNCERTAIN + reasoning
5. APPROVED and REJECTED are written back with `reviewed_by = 'llm'`
6. UNCERTAIN rows remain `pending` for human review

### When triage runs

- As a Dagster asset (`quality/review_queue_triage`) that materializes after the enrich stage
- Can also be run manually via a Claude Code session: "Process the review queue"
- Uses a cheap model (Haiku) for initial triage; uncertain cases can be escalated to a stronger model

## Consequences
- All fuzzy matches are surfaced, not silently accepted — prevents false attributions from reaching users
- Exact variant matching handles the majority of cases with zero ambiguity; fuzzy is the exception
- The LLM triager handles most queued cases correctly (Egyptological name variants are well within LLM knowledge)
- Human review effort is minimized to genuinely ambiguous cases
- The review table provides an audit trail: which matches were human-verified vs LLM-verified
- Approved variants feed back into authority files, so the fuzzy path fires less over time
- The same pattern works for both ruler and site matching

## Scope: this is variant resolution, not cross-source identity

This ADR governs resolving a raw museum string to an *already-known* authority entry via
its committed variant array (e.g. confirming "Tuthmosis" is a spelling of Thutmose III) —
a task for which known name variants are indeed well within LLM knowledge. It does **not**
govern proposing that two *distinct source records* denote the same ruler. That is
cross-source identity matching, whose stricter regime lives in
[ADR-020](020-matcher-evaluation-and-cross-source-identity.md) §6: there, name agreement
alone can never be LLM-approved — a name-only pair (no shared prenomen/Horus-name
corroborator) is escalated deterministically and confirmed only by a curator attaching
external cited evidence, because per Constitutional Rule 1 "the model knows" is not a
source.
