# Hapi three-museum corpus snapshot

Private local export generated `2026-08-28T02:30:52Z` from the populated Hapi
Postgres database. The snapshot contains the Metropolitan Museum of Art,
Brooklyn Museum, and Harvard Art Museums corpus.

## Contents

```text
data/artifacts.ndjson.gz       36,245 canonical artifacts, all 30 columns
data/raw_met.ndjson.gz         27,969 raw Met API records
data/raw_brooklyn.ndjson.gz     8,832 raw Brooklyn records
data/raw_harvard.ndjson.gz        722 raw Harvard API records
database/catalog.dump          PostgreSQL custom-format dump of catalog.*
schema/catalog.sql             PostgreSQL schema-only dump
schema/artifacts.schema.json   JSON Schema for a canonical artifact
validation/queries.sql         Re-runnable database validation
validation/results.json        Validation results for this snapshot
validation/verify_bundle.sh    File-level integrity/completeness checks
manifest.json                  Machine-readable inventory and caveats
SHA256SUMS                     SHA-256 checksums for every packaged file
NOTICE                         Source rights and attribution terms
```

The JSONL files are newline-delimited JSON compressed with gzip. Each canonical
line is one object containing every field, including explicit `null` values.
Each raw line has this shape:

```json
{"object_id":"museum database identifier","data":{"the":"raw museum payload"}}
```

`data` is decoded as a nested JSON object for direct use. The Postgres dump
also preserves the exact text stored in each `catalog.raw_*` row.

## Counts

| Dataset | Rows |
|---|---:|
| Canonical Met | 27,969 |
| Canonical Brooklyn | 7,554 |
| Canonical Harvard | 722 |
| **Canonical total** | **36,245** |
| Raw Met | 27,969 |
| Raw Brooklyn | 8,832 |
| Raw Harvard | 722 |
| **Raw total** | **37,523** |

Brooklyn has 1,278 raw-only records. They were retained at ingest and
intentionally excluded during normalization because the museum department mixes
explicitly non-Egyptian material into its collection.

## Canonical fields

The canonical file includes all live columns: `id`, `source_museum`,
`source_url`, `source_id`, `title`, `description`, `object_type`, `materials`,
`dimensions`, `period`, `dynasty`, `ruler_id`, `ruler_display_name`,
`date_start`, `date_end`, `date_display`, `origin_site_id`,
`origin_site_display_name`, `origin_site_raw`, `origin_certainty`,
`excavation_id`, `tomb_temple_id`, `current_location`, `accession_number`,
`credit_line`, `image_url`, `thumbnail_url`, `license`, `wikidata_id`, and
`provenance`.

Negative integer years represent BCE; positive years represent CE. Nulls are
meaningful source sparsity and must not be treated as export omissions.

## Important enrichment caveat

The authority/enrichment stage had not been implemented when this snapshot was
created. Consequently, `ruler_id`, `origin_site_id`,
`origin_site_display_name`, and `tomb_temple_id` are null across the corpus.
The unresolved evidence is still present in `ruler_display_name`,
`origin_site_raw`, date/provenance fields, and the underlying raw payloads.
Tomb/temple codes often remain embedded in those text fields. In particular:

- `ruler_display_name` is populated for 11,256 Met records only.
- `origin_site_raw` is populated for 31,407 records across the three museums.
- `excavation_id` is populated for 16,403 Met records only.
- `provenance` is populated by Harvard/Brooklyn where their sources provide it;
  the public Met API does not provide that field.

See `validation/results.json` for the complete per-museum non-null fingerprint.

## Use the JSONL export

```bash
gzip -cd data/artifacts.ndjson.gz | jq -c 'select(.dynasty == "Dynasty 18")'
gzip -cd data/raw_met.ndjson.gz | jq -c '.data'
```

## Restore the database dump

The dump was made from PostgreSQL 16.13 with Alembic revision
`3a1c350217d9` and contains the complete `catalog` schema. Restore it into an
empty database with a compatible PostgreSQL client:

```bash
createdb hapi_import
pg_restore --no-owner --no-privileges --dbname=hapi_import database/catalog.dump
```

No `DATABASE_URL`, password, museum API key, or Typesense key is included.

## Verify

From this directory:

```bash
bash validation/verify_bundle.sh
```

The verifier checks every checksum, gzip stream, JSON record shape, row count,
ID uniqueness, canonical-to-raw link, and the expected 1,278 Brooklyn raw-only
records. Database-level queries are in `validation/queries.sql`.

## Rights and distribution

This is a private working-data handoff, not a public redistribution package.
Read `NOTICE` before sharing or publishing it. Met metadata is CC0; Brooklyn and
Harvard impose noncommercial/educational or per-object restrictions described
in that file. Image URLs and rights metadata are included, but image binaries
are not.
