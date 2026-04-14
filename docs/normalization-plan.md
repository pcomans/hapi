# Normalization Plan — Periods, Dynasties, Rulers, Sites

This is the operational plan for turning the raw text fields on `catalog.artifacts` (`period`, `dynasty`, `ruler_display_name`, `origin_site_raw`) into resolved authority IDs that the web app can search, group, and reunify across museums.

It is the egyptologist-facing companion to `playbook-new-museum.md`. Where the museum playbook is parallelizable (one agent per museum), normalization is sequential: each authority list is built once and consumed by all museums.

The architectural decisions are in ADRs and not restated here:

- [ADR-012](adr/012-authoritative-sources.md) — sources for chronology, rulers, sites
- [ADR-013](adr/013-structured-dating-fields.md) — structured dating fields with qualifier, certainty, relation
- [ADR-014](adr/014-exclude-non-ancient-records.md) — exclude non-ancient records during normalization
- [ADR-015](adr/015-findspot-and-production-place.md) — findspot and production place are separate fields
- [ADR-016](adr/016-royal-display-name-anglicized-nomen.md) — Anglicized Nomen as the canonical display name

This document covers the *order* of work, not the *shape* of the work.

## Current state (as of 2026-04-11)

- 36,245 normalized records in `catalog.artifacts`: Met 27,969 · Brooklyn 7,554 · Harvard 722
- Mappers extract raw text into `period`, `dynasty`, `ruler_display_name`, `origin_site_raw`
- `pipeline/pipeline/authority/` is empty — constitutional rule 7 has nothing backing it yet
- `pipeline/pipeline/assets/enrich/` is empty
- The `ruler_id`, `origin_site_id` columns are unpopulated and will be replaced per ADR-015

## Vocabulary observed in the data

A scan of distinct values across the three museums shows what the enrich stage has to handle:

**Period.** Overlapping vocabularies, not identical. "Roman Period" (Met/Brooklyn) vs "Roman Imperial period" (Harvard). Case drift ("Ptolemaic Period" vs "Ptolemaic period"). Compound forms ("Late Period–Ptolemaic Period", "Late Period to Ptolemaic"). Brooklyn qualifiers ("Late Period (probably)"). Sub-periods folded into the period field ("New Kingdom, Ramesside", "New Kingdom, Amarna Period", "Late Period, Saite").

**Dynasty.** Mostly "Dynasty N" but with ranges ("Dynasty 19–20", "Dynasty 26–30"), qualifiers ("late Dynasty 18", "Dynasty 18, early", "Dynasty 26, or later"), and period-mixed forms ("Dynasty 18, Amarna period").

**Ruler.** Met extracts them (Amenhotep III, Hatshepsut & Thutmose III joint, "Possibly Senwosret I"). Brooklyn and Harvard mappers hardcode `None` — rulers are buried in date strings ("reign of Necho II") and need extraction during enrich.

**Origin site.** Met delivers a hierarchical comma-path ("Egypt, Upper Egypt, Thebes, Deir el-Bahri, Tomb of Meritamun (TT 358, MMA 65)"). Brooklyn is flat with parens ("Thebes (Deir el-Bahri), Egypt", "Tomb D303, Abydos, Egypt"). Tomb codes (KV 47, TT 280, MMA 60/509/1101) are embedded in the strings and must be extracted into `tomb_temple_id` / `excavation_id` per ADR-008.

## Phases

```
Phase 0 — Source acquisition       (parallelizable per source)
Phase A — Authority curation       (sequential: dynasties → periods → rulers → sites)
Phase B — Enrich assets            (one Dagster asset per authority, in the same order)
Phase C — Feedback loop            (continuous: discoveries → aliases or mapper fixes)
Phase D — Future authorities       (object typology, materials, deities — out of scope for first pass)
```

### Phase 0: Source acquisition

Acquire the raw reference data per ADR-012. Each source goes into `pipeline/pipeline/authority/sources/` with a header citation.

| Source | Method | Used by |
|---|---|---|
| Hornung/Krauss/Warburton (2006) | Manual transcription of chronology table from PDF, with page citations | dynasties.json, periods.json |
| Pharaoh.se royal titulary database | HTML scrape, reconciled JSONL (CC BY 4.0) | rulers.json |
| Wikipedia Ptolemaic dynasty | Scraped table, JSONL (CC BY-SA 4.0) | rulers.json, dynasties.json (Ptolemaic fill-in) |
| Beckerath *Handbuch* (1999) | Manual cross-check pass against pharaoh.se results | rulers.json |
| iDAI.gazetteer Egyptian places | REST API, reconciled JSONL (CC BY 4.0) | sites.json |

These can run in parallel.

### Phase A: Authority curation

Each curated authority file is hand-built from the raw sources, following the structures defined in ADRs 013 and 016. Order matters: each tier consumes the previous.

1. **`dynasties.json`** — Dynasties 0–31 + Ptolemaic + Roman. Each entry: `id`, `display`, `dates`, `parent_period`, `polity` (for concurrent Intermediate-Period dynasties — 13th, 14th, 15th, 16th, 17th in different regions), `concurrent_with`, `aliases` drawn from real raw values
2. **`periods.json`** — Predynastic through Roman. Sub-periods (Amarna, Ramesside, Saite) are their own entries with `parent_id` linking up. Sub-period replaces parent when the raw text resolves more specifically
3. **`rulers.json`** — Per ADR-016 schema: canonical `display` (Anglicized Nomen), structured `titulary` object with all five name parts, flat `aliases` for the matcher. Coverage priority: New Kingdom and Late Period (most data coverage)
4. **`sites.json`** — Hierarchical structure (`egypt > upper_egypt > thebes > deir_el_bahri > tt_358`). Coverage target: ~100 most-referenced sites + KV/TT tombs

### Phase B: Enrich assets

One Dagster asset per authority, in `pipeline/pipeline/assets/enrich/`, in the same order as Phase A. Each reads `catalog.artifacts`, deterministically matches the raw text against the authority's `aliases`, and writes resolved IDs back to the same row. No fuzzy matching as the primary path — anything that doesn't match exactly goes to the review queue (ADR-009).

`sync_search` gains all four as upstream deps.

```
enrich_dynasties  → populates dynasty_ids, dynasty_qualifier, dynasty_certainty, dynasty_relation
enrich_periods    → populates period_ids, period_qualifier, period_certainty, period_relation
enrich_rulers     → populates ruler_ids (list, for joint reigns); also regex-scans date_display for "reign of X"
enrich_sites      → populates production_site_id, findspot_site_id (per ADR-015), tomb_temple_id, excavation_id
```

### Phase C: Feedback loop

Enrichment will surface raw-text variants we did not anticipate. Each variant gets handled in one of three ways:

1. Add it as an alias to the authority file (most common)
2. Fix the mapper if it is mangling the source data
3. Add it to the exclusion list (ADR-014) if it identifies a record that should never have been indexed

Each pass through this loop tightens the vocabulary. The review queue should shrink monotonically.

### Phase D: Future authorities

Out of scope for the first pass but real future work, in roughly this order:

- **`object_types.json`** sourced from Getty Art & Architecture Thesaurus (Egyptian object hierarchy: shabti, stela, scarab, canopic jar, etc.). AAT is open data with stable IDs
- **`materials.json`** also from Getty AAT. Solves the wood/wooden/cedar/timber free-text problem
- **`deities.json`** — Lexikon der ägyptischen Götter und Götterbezeichnungen (LGG, 2002–2003) is the academic standard. Trismegistos has a deity subset that may be openly licensed and worth investigating

## First slice — dynasties end-to-end

Dynasties are the narrowest, most constrained vocabulary. The smallest meaningful slice that exercises Phases 0 → A → B end-to-end:

1. Acquire the HKW chronology data (Phase 0)
2. Curate `dynasties.json`: Dynasties 0–31 + Ptolemaic + Roman, aliases drawn from the top ~50 distinct `dynasty` values across all three museums (Phase A)
3. Add `Qualifier`, `Certainty`, `Relation` enums to `pipeline/types/sources.py` (per ADR-013)
4. Schema migration: add `dynasty_ids` (list), `dynasty_qualifier`, `dynasty_certainty`, `dynasty_relation` columns. SQLAlchemy → Pydantic → Alembic → Drizzle introspect, per rule 1
5. Build `enrich_dynasties` Dagster asset with fixture-backed tests asserting:
   - `"late Dynasty 18"` → `dynasty_ids=[dynasty_18]`, `qualifier=late`
   - `"Dynasty 19–20"` → `dynasty_ids=[dynasty_19, dynasty_20]`, `relation=to`
   - `"Dynasty 26, or later"` → `dynasty_ids=[dynasty_26]`, `relation=or_later`
6. Materialize, query the misses, iterate

If the authority/enrich pattern survives contact with real data here, extend it to periods, then rulers, then sites — in that order.
