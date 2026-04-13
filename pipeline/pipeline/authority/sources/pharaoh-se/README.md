# Pharaoh.se — Royal Titulary Database

Academically sourced list of Egyptian pharaohs with full five-name royal titulary, scraped from [pharaoh.se](https://pharaoh.se/ancient-egypt/pharaohs) using Firecrawl.

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
