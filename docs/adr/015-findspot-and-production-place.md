# ADR-015: Findspot and Production Place Are Separate Fields

## Status
Accepted

## Supersedes
Part of [ADR-007](007-origin-site-first-class.md): the single `origin_site_id` field and `origin_certainty` are replaced by separate findspot and production-place fields.

## Context
ADR-007 introduced `origin_site_id` as a single field on `CanonicalArtifact`, with the implicit assumption that an artifact has one canonical place of origin. The raw data does not match that assumption.

The three museum sources all distinguish *where an artifact was made* from *where it was found*:

- **Met** — `geographyType` field: `"Made in"`, `"From"`, `"Said to be from"`, `"Probably from"`, `"Possibly from"`
- **Brooklyn** — geographical location `type` field: `"Place made"`, `"Place excavated"`, `"Place found"`, `"Place collected"`, `"Place modified"`, `"Reportedly from"`, `"Possible place ..."`
- **Harvard** — `places.type` field: `"Creation Place"` (and others)

These are not the same thing. A shabti made in a Memphite workshop and buried in a Theban tomb has two different sites, both archaeologically meaningful. The current schema collapses them into one and uses `origin_certainty` as a workaround for the role distinction — but certainty and role are independent concepts. A "confirmed" findspot and a "confirmed" production place are different data.

## Decision

Replace the single `origin_site_id` with two separate columns on `CanonicalArtifact`:

- `production_site_id` — where the artifact was made
- `findspot_site_id` — where the artifact was excavated, found, or collected

Both nullable. Both can coexist on the same record. Both link into the same `sites` authority file with the same hierarchy from ADR-007.

Drop `origin_certainty`. Certainty is now expressed via the same `Certainty` enum from ADR-013 (`confirmed`, `probable`, `uncertain`) on whichever field actually holds the site:

- `production_site_certainty: Certainty | None`
- `findspot_site_certainty: Certainty | None`

Drop `origin_site_display_name`. Display names are derived from the joined `sites` authority entry.

### Mapping from museum role labels to fields

| Museum | Raw role | Maps to |
|---|---|---|
| Met | `"Made in"` | `production_site_id` |
| Met | `"From"` | `findspot_site_id` (`confirmed`) |
| Met | `"Probably from"` | `findspot_site_id` (`probable`) |
| Met | `"Possibly from"`, `"Said to be from"` | `findspot_site_id` (`uncertain`) |
| Brooklyn | `"Place made"`, `"Place modified"` | `production_site_id` |
| Brooklyn | `"Place excavated"`, `"Place found"`, `"Place collected"` | `findspot_site_id` (`confirmed`) |
| Brooklyn | `"Reportedly from"`, `"Possible place ..."` | `findspot_site_id` (`uncertain`) |
| Harvard | `"Creation Place"` | `production_site_id` |

Tomb and excavation IDs (KV 47, TT 280, MMA 60) extracted from the same source string go into `tomb_temple_id` and `excavation_id` as before — they are tied to the findspot, not the production place.

## Consequences
- Schema migration: drop `origin_site_id`, `origin_site_display_name`, `origin_certainty`; add `production_site_id`, `production_site_certainty`, `findspot_site_id`, `findspot_site_certainty`. Per rule 1: SQLAlchemy → Pydantic → Alembic → Drizzle introspect → commit together
- The web app's "from Thebes" search queries `production_site_id OR findspot_site_id` and labels the matched field in results ("Made in Thebes" vs "Found at Thebes")
- Tier C ("Explore more from this area") from ADR-008 walks the hierarchy at query time on whichever field matched
- Records with both fields populated are now expressible — previously this was impossible
- The certainty enum is consistent across dating and provenance, removing a one-off `origin_certainty` taxonomy
- ADR-007's broader claims (sites are first-class entities with hierarchy, parent-child structure, coordinates) remain in force — only the single-field assumption is superseded
