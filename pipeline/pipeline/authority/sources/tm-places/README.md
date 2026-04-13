# Trismegistos — TM Places (Egypt + Nubia)

Source: Trismegistos Data Services, Geographical data dump tool.
https://www.trismegistos.org/dataservices/tabledump/

Retrieved: April 2026. License: CC BY-SA 4.0.

## Why this source

Trismegistos Geo (TM Places) is the authoritative cross-reference for
ancient place names in papyrological and epigraphical scholarship. It
assigns a stable numeric identifier (TM Geo ID) to every attested
location in the ancient world, with multilingual name variants, Roman
province, and Egyptian nomos coding. It is the designated source for the
`sites.json` authority file per ADR-012.

## Layout

```
pipeline/pipeline/authority/sources/tm-places/
  README.md          — this file
  acquire.py         — one-time download + transform script
  reconciled.jsonl   — committed output (Egypt + Sudan, 13,995 rows)
```

## Coverage

13,995 rows:
- **Egypt** (13,559) — Nile Valley, Delta, Sinai, Fayum, Oases
- **Sudan** (436) — ancient Nubia: Meroe, Napata, Kerma, Soleb, Semna,
  and other sites in the region ruled by pharaonic Egypt. These appear
  regularly in Egyptian art collections at Met, Brooklyn, and Harvard.

Libya and Levantine countries are excluded: their TM Places entries are
predominantly Greek/Roman colonial sites not relevant to Egyptian artifact
provenance.

Note: Wadi el-Natrun (TM 14240) is assigned to Sudan in the source data
but is located in modern Egypt — a known data-quality issue in TM Places.

## Schema

One JSON object per line. `kind` is always `"site"`.

| Field | Source column | Notes |
|---|---|---|
| `tm_id` | `id` | Unique TM Geo ID. Stable across TM releases. |
| `name_standard` | `name_standard` | Trismegistos standard notation. Primary match key. |
| `name_latin` | `name_latin` | Latin notation (ISO 215). Pipe-delimited variants. |
| `name_greek` | `unicode_greek` | Greek notation in Unicode (ISO 200). |
| `name_egyptian` | `unicode_egyptian` | Demotic/hieroglyphic notation in Unicode (ISO 070). |
| `name_coptic` | `unicode_coptic` | Coptic notation in Unicode (ISO 204). |
| `country` | `country` | Modern country. Either `"Egypt"` or `"Sudan"` here. |
| `region` | `region` | Ancient region code: `"U"` Upper Egypt, `"L"` Lower Egypt, `"00"` Fayum, `"N/A"` Nubia. |
| `nomos_code` | `nomos_code` | Egyptian nome code (e.g. `"U04b"` for Theban nome). Null for Nubian sites. |
| `status` | `status` | Place type vocabulary (e.g. `"city: polis"`, `"village: kome"`). |
| `ethnicon` | `ethnicon` | Demonym(s) for the place. |
| `location` | `location` | Free-text location description relative to nearby sites or cataracts. |
| `provincia` | `provincia` | Roman province as of AD 200. Nubian sites: `"outside the Imperium Romanum"`. |
| `latitude` | `coordinates` (first value) | Decimal degrees. Null when TM lacks coordinates. |
| `longitude` | `coordinates` (second value) | Decimal degrees. Null when TM lacks coordinates. |
| `begin_date` | `begin_date` | Earliest attested year (negative = BCE). Null when unattested (TM source value 0). |
| `end_date` | `end_date` | Latest attested year. Null when unattested (TM source value 0). |
| `note` | — | Null in acquisition pass. Reserved for reconciliation notes in sites.json curation. |

## Known data-quality issues

- **Coordinates sparse**: Many Egyptian records have null coordinates even
  though TM Geo has them — they are available via the GeoResponder API
  (`/dataservices/georesponder/georesponder.php?id=<TM_GEO_ID>`) but not
  in the bulk CSV export. Coordinates should be enriched per-record during
  sites.json curation (task 3.2) if needed for map view (Milestone 6).
- **`begin_date` / `end_date` = 0**: TM uses 0 as a sentinel for "no
  attestation date known". Converted to `null` in this JSONL.
- **`name_latin` pipe-delimited variants**: e.g. `"Alexandria - Alexandrea"`.
  The aliases matcher in `enrich_sites` must split on ` - ` to populate
  the `aliases` array in sites.json.
- **`status` verbose strings**: e.g.
  `"city: polis, metropolis, megalopolis (megale polis), civitas, urbs, oppidum"`.
  Extract the first token before `:` for a normalised type label.

## Design decisions

- **Egypt + Sudan only**: The full dump covers the entire ancient world
  (64,858 records). We keep only `country ∈ {"Egypt", "Sudan"}` since
  artifact provenance in these collections is overwhelmingly from the Nile
  Valley and ancient Nubia.
- **All TM fields included**: All 19 available dump fields are requested.
  `pleiades_id` and `geonames` fields are commented out in the form HTML
  but can be added if TM exposes them in a future release.
- **Pleiades IDs deferred**: Available via GeoResponder API `links.close
  matches.Pleiades`, not in the bulk CSV. Add during sites.json curation.
- **No filtering by status**: Villages, cities, nomes, rivers, and oases
  are all retained. Artifact provenance can reference any place type.
