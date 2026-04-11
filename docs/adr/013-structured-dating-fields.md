# ADR-013: Structured Dating Fields with Qualifier, Certainty, Relation

## Status
Accepted

## Context
The current `CanonicalArtifact` represents `period` and `dynasty` as plain strings. Sampling the raw text from the three museum sources reveals that scalar strings are lossy: dating in Egyptology is rarely a point estimate. Real raw values include:

- `"late Dynasty 18"` — qualifier within a dynasty
- `"Dynasty 19–20"` — range across two dynasties
- `"Dynasty 26, or later"` — open-ended relation
- `"Late Period (probably)"` — certainty modifier
- `"New Kingdom, Amarna Period"` — sub-period that should resolve more specifically than its parent

Reducing these to `dynasty_id = "dynasty_18"` throws away the qualifier information that egyptologists actually use. Reducing them to a free-text field defeats the purpose of having an authority list at all.

## Decision

Each chronology field on `CanonicalArtifact` becomes a small struct, not a scalar. After enrichment:

```
period_ids:        list[str]                # list because of ranges
period_qualifier:  Qualifier | None         # early, mid, late
period_certainty:  Certainty                # confirmed, probable, uncertain
period_relation:   Relation | None          # to, or_later, or_earlier, in_style_of

dynasty_ids:       list[str]
dynasty_qualifier: Qualifier | None
dynasty_certainty: Certainty
dynasty_relation:  Relation | None
```

The three enums live in `pipeline/types/sources.py` next to `License`:

```python
class Qualifier(str, Enum):
    EARLY = "early"
    MID = "mid"
    LATE = "late"

class Certainty(str, Enum):
    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    UNCERTAIN = "uncertain"

class Relation(str, Enum):
    TO = "to"
    OR_LATER = "or_later"
    OR_EARLIER = "or_earlier"
    IN_STYLE_OF = "in_style_of"
```

Closed enums force the system to confront new variants instead of silently dropping them. Anything that doesn't match an enum value goes to the review queue (ADR-009).

The museum-asserted `date_start` and `date_end` integers on `CanonicalArtifact` are preserved verbatim — they are the museum's claimed dates and are still displayed in the UI as the museum's view. Entity links are the primary signal for time queries but they do not replace the museum dates.

### Worked examples

| Raw text | Resolved |
|---|---|
| `"late Dynasty 18"` | `dynasty_ids=[dynasty_18]`, `qualifier=late`, `certainty=confirmed` |
| `"Dynasty 19–20"` | `dynasty_ids=[dynasty_19, dynasty_20]`, `relation=to` |
| `"Dynasty 26, or later"` | `dynasty_ids=[dynasty_26]`, `relation=or_later` |
| `"Late Period (probably)"` | `period_ids=[late_period]`, `certainty=probable` |
| `"New Kingdom, Amarna Period"` | `period_ids=[amarna]` (sub-period replaces parent when more specific) |

## Consequences
- Dating qualifiers that egyptologists actually rely on are preserved through to the search index and the UI
- The schema gains six columns per artifact (three for period, three for dynasty), plus the array columns for IDs. This is a chunky migration but defensible
- New raw variants raise rather than silently coerce, surfacing real vocabulary gaps via the review queue
- The museum's own `date_start`/`date_end` remain available for display ("Museum dates: 1390 BCE – 1352 BCE") and as a fallback signal when entity resolution fails
- Time queries in the web app prefer the entity-resolved dates (joining through `dynasties.dates`) and fall back to the museum dates when no entity matched
- The `Relation` enum is the natural extension point for any future dating modifier we encounter — adding a new value requires an explicit enum addition, which is the desired friction
