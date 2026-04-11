# ADR-014: Exclude Non-Ancient Records During Normalization

## Status
Accepted

## Context
The three currently-ingested museums each catalog more than just ancient Egyptian artifacts in their Egyptian collections. Real raw values seen across the data include:

- `"Modern, in the style of the New Kingdom, Amarna Period"` — a 20th-century work
- `"Mamluk period"` — Islamic-era Egypt
- `"Fatimid period"` — Islamic-era Egypt
- `"Byzantine period, Early"` — post-Roman Christian Egypt
- `"Late Antique Period"` — Brooklyn's heading for Coptic-era material

The product is a search index of *ancient* Egyptian artifacts. Modern works, replicas, and post-Roman material fall outside that scope. Storing them and then trying to filter at query time is fragile — every query everywhere has to remember the exclusion. Filtering at normalize time keeps the artifacts table aligned with the product definition.

Brooklyn already has the precedent: `is_egyptian()` in `pipeline/pipeline/assets/normalize/brooklyn.py` excludes records tagged with non-Egyptian cultures (Cypriot, Roman, Greek). The same pattern extends to non-ancient records.

## Decision

Records matching any of the following triggers are excluded during normalization, with the trigger reason logged. The record is not written to `catalog.artifacts`.

### Period-based exclusions

Any period field equal to or starting with one of:

- `"Modern"`
- `"Mamluk"`
- `"Fatimid"`
- `"Byzantine"`
- `"Late Antique"`
- `"Coptic"` *(when used as a period label, not a culture or material)*
- `"Islamic"`

### Phrase-based exclusions

Any of these substrings in `period`, `dynasty`, or `title`:

- `"in the style of"`
- `"replica"`
- `"forgery"`
- `"reproduction"`
- `"after [pharaoh name]"` (regex: `^after\s+`)

### Implementation

The exclusion list will live in a single file (`pipeline/pipeline/assets/normalize/exclusions.py`, to be created as part of MVP task 3.3) and export a single function `is_in_scope(raw: dict) -> bool`. Every museum's normalize asset will call it before mapping. Per-museum overrides go in `docs/museum-sources/{museum}.md` if a museum legitimately uses one of these phrases for an in-scope record.

Excluded records are logged as Dagster events with the count and the trigger reason:

```
context.log.info(f"Excluded {n} records: trigger='Modern, in the style of'")
```

A structural test (to be added as part of MVP task 3.2) will assert that the exclusions module exists, exports `is_in_scope`, and is imported by every normalize asset.

## Consequences
- The `catalog.artifacts` table contains only in-scope ancient Egyptian artifacts; downstream code (web app, sync_search, enrich) does not need to re-filter
- The exclusion list is one place to edit when a new out-of-scope pattern is discovered
- Excluded records are still in `catalog.raw_{museum}` (raw data is sacred) — re-running normalization with an updated exclusion list is idempotent
- The exclusion log is the audit trail: we can always answer "why isn't this object in Hapi?" by grepping for the source ID in Dagster logs
- This is intentionally narrower than ADR-009's review queue. The review queue handles ambiguous *ancient* records; the exclusion list handles records that are clearly out of scope. They do not overlap
- A record like `"Modern, in the style of the New Kingdom"` is excluded outright and does not generate a review queue entry
