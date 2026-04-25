# Pharaoh.se — Royal Titulary Database

Academically sourced list of Egyptian pharaohs with full five-name royal titulary, scraped from [pharaoh.se](https://pharaoh.se/ancient-egypt/pharaohs) using Firecrawl.

## Role in the authority architecture

**As of 2026-04-25 (post-Beckerath landing):** pharaoh.se is a **gap-fill secondary** source. Phase-A `build_rulers.py` consumers should NOT read this source's titulary or chronology fields blindly across the whole 381-row corpus. Use it scoped to specific clusters:

- **Roman emperors (30 rows)** — pharaoh.se is currently the ONLY on-disk Phase-0 source covering imperial-period pharaohs (Augustus → Caracalla and beyond, with Egyptian throne-name cartouches). This is the cluster preventing outright drop. Replaced when **Bagnall & Rathbone 2004** lands as a Roman-period Phase-0 source.
- **Unplaced kings / Abydos Dynasty / Dyn-13–14 long-tail (~11+ rows)** — kings attested only on a single inscription that no chronology source enumerates. Beckerath, Kitchen, HKW silently omit them. Leprohon 2013 covers some via the Abydos-Dynasty section.
- **`alt_labels` (347/381 rows)** — Greek/Latin variant graph (Akoris/Akhoris, Necho/Nekau, Psamtik/Psammetichos) Leprohon does not exhaustively maintain. Used as a *supplement* to Leprohon's `alt_display_names`.
- **Argead / Ptolemaic (19 rows)** — secondary to Leprohon Ch X chunk 14 (3 Macedonian + 21 Ptolemaic rows including queen-consort sub-entries).

**What NOT to read from this source post-Beckerath:**

- **Chronology dates / `chronologies` dict.** Redundant with the project's primary chronology sources (Beckerath 1997, HKW 2006, Kitchen 1996). pharaoh.se's own dict is second-hand to the sources IT cites (Beckerath, Shaw, Dodson, etc.); the project now uses those primaries directly. Use `sources/beckerath-1997-chronologie/` (lead) + `sources/hkw-chronology-2006/` (fallback) + `sources/kitchen-tipe/` (Dyn 21–26 finer grain) via the plural-named-chronologies map in `rulers.json::chronologies` instead.
- **Titulary on rulers Leprohon covers.** Leprohon 2013 (`sources/leprohon-2013-titulary/`) is the **primary** titulary authority (395 rows across Dyn 0 → Ptolemaic). pharaoh.se titulary fields are only consulted when Leprohon is silent on a given ruler.
- **`predecessor` / `successor` chains** as the source of truth. Derive predecessor/successor from `sequence_in_dynasty` ordering across Beckerath / Leprohon / Ryholt / Kitchen instead. pharaoh.se chains remain useful as a cross-validation signal but not the source.

**End-state target:** drop pharaoh.se entirely once Bagnall & Rathbone 2004 lands (covering Roman emperors) AND the unplaced-king long-tail is curated into Leprohon's existing Abydos-Dynasty / problematic-king sections or accepted as a documented MVP gap.

**Decision audit trail:** ADR-012 (Consequences section, 2026-04-25 entry); `docs/mvp-tasks.md` § Milestone 3.2 (deferred-decision section "Deferred decision: pharaoh.se drop after Beckerath landed"); GitHub issue #112 (closed 2026-04-25 with this decision documented inline).

## Source

- **Website**: [pharaoh.se](https://pharaoh.se/) by Peter Lundstrom
- **License**: CC BY 4.0
- **Retrieved**: 2026-04-12
- **Method**: Firecrawl markdown scrape of index page + 381 individual pharaoh pages

## What this provides

| Field | Coverage | Notes |
|---|---|---|
| `display` | 100% | Common English name |
| `slug` / `url` | 100% | Pharaoh.se URL for linking from the web app |
| `alt_labels` | 75% | Alternate names/spellings from index + page intro |
| `prenomen` | 75% | Throne name (primary transliteration from titulary) |
| `nomen` | 57% | Birth name (primary transliteration from titulary) |
| `start_year` / `end_year` | 63% | Reign dates (AE Chronology, negative for BCE) |
| `dynasty_number` | varies | Parsed from index page dynasty headers |
| `chronologies` | varies | Multiple scholarly chronologies (von Beckerath, Shaw, Dodson, etc.) |
| `horus_names` | 44% | Full Horus name(s) with transliteration, translation, Gardiner codes, sources |
| `nebty_names` | varies | Nebty ("Two Ladies") name(s) |
| `golden_horus_names` | varies | Golden Horus name(s) |
| `throne_names` | 75% | Prenomen / throne name(s) with variants |
| `birth_names` | 57% | Nomen / birth name(s) with variants |
| `predecessor` / `successor` | 99% | Linked pharaoh names |

## Schema

Each line in `reconciled.jsonl` is a JSON object:

```json
{
  "kind": "ruler",
  "slug": "Thutmose-III",
  "url": "https://pharaoh.se/ancient-egypt/pharaoh/Thutmose-III/",
  "display": "Thutmose III",
  "alt_labels": ["Tuthmosis III", "Thutmosis III"],
  "prenomen": "Men kheper Ra",
  "nomen": "Djehutimes",
  "start_year": -1479,
  "end_year": -1425,
  "dynasty_label": "Eighteenth Dynasty",
  "dynasty_number": 18,
  "ordinal": 6,
  "predecessor": "Hatshepsut",
  "successor": "Amenhotep II",
  "chronologies": {
    "AE Chronology": "1479–1425",
    "von Beckerath": "1479–1425"
  },
  "horus_names": [
    {
      "name": "Ka nakht kha em Waset",
      "transliteration": "kꜢ-nḫt ḫꜤ-m-wꜢst",
      "translation": "The strong bull arising in Thebes",
      "gardiner": "E1:D40-xa:m-R19-t:O49",
      "is_variant": false,
      "sources": ["Lepsius, Denkmäler...", "Beckerath, MÄS 49 (1999)..."]
    }
  ],
  "nebty_names": [...],
  "golden_horus_names": [...],
  "throne_names": [...],
  "birth_names": [...],
  "ancient_sources": [
    {"author": "Africanus xviii, 6", "greek": "Μισφραγμουθωσις", "transcription": "Misphragmuthosis", "reign": "26 years"}
  ]
}
```

## Comparison with Wikidata source

| Dimension | Pharaoh.se | Wikidata |
|---|---|---|
| Ruler count | 381 | 517 |
| Curation | Single expert maintainer, sourced from Egyptological literature | Crowd-sourced, includes fictional characters |
| Prenomen | 75% (full transliteration) | 0% |
| Five-name titulary | Yes (with variants, Gardiner codes, source citations) | No |
| Multiple chronologies | Yes (von Beckerath, Shaw, Dodson, etc.) | Single date range |
| Stable IDs | URL slugs | Wikidata QIDs |
| License | CC BY 4.0 | CC0 |

## Re-fetching

```bash
cd pipeline && uv run python pipeline/authority/sources/pharaoh-se/fetch.py
```

To re-parse without re-scraping (uses saved raw markdown):

```bash
cd pipeline && uv run python pipeline/authority/sources/pharaoh-se/fetch.py --parse-only
```

## Raw data

Raw markdown files are saved in `raw/` for auditability:
- `raw/index.md` — the pharaohs index page
- `raw/{slug}.md` — individual pharaoh pages (381 files)

These are the Firecrawl markdown conversions of the original HTML pages.
