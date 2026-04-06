# Metropolitan Museum of Art

## Access

- **API**: REST, no authentication required
- **Base URL**: `https://collectionapi.metmuseum.org/public/collection/v1`
- **Rate limit**: 80 requests/second
- **CSV dump**: Full collection CSV available on GitHub (metmuseum/openaccess)
- **Egyptian Art department**: `departmentId=10`, ~26,000-30,000 objects

## Endpoints

- `GET /objects?departmentIds=10` — returns array of all object IDs in Egyptian Art
- `GET /objects/{id}` — returns full object record
- `GET /search?departmentId=10&q={query}` — search within department

## License

**CC0 (public domain).** Metadata and public-domain images are unrestricted. This is the most permissive source — no attribution required, commercial use allowed.

## Data quality notes

- **Richest structured source.** The Met has first-class fields for `period`, `dynasty`, `reign`, and structured geography (`geographyType`, `country`, `region`, `subregion`, `locale`, `locus`, `excavation`, `river`). Most other museums put this in free text.
- **Geography fields are hierarchical but inconsistent.** `geographyType` can be "From", "Excavated at", "Said to be from", "Possibly from" — each implies different provenance confidence. The mapper must preserve this distinction.
- **`reign` field is not always a ruler.** Sometimes contains period info ("late Dynasty 18") or co-regencies.
- **~40% of records may lack excavation/provenance data.** Many objects were acquired through purchase with no documented findspot.
- **Image availability**: `primaryImage` and `primaryImageSmall` URLs. Some objects have no image. URLs are stable IIIF endpoints.

## Known quirks

- The objects endpoint returns ALL object IDs at once (not paginated). For Egyptian Art this is ~28k IDs (27,971 as of April 2026). You then fetch each object individually.
- Some object IDs return 404 — these are deleted/deaccessioned objects. The ingest treats these as skips, not errors.
- The CSV dump is updated periodically and may lag the API by days/weeks.
- Some `objectDate` fields contain ranges like "ca. 1479-1425 B.C." that need parsing. `objectBeginDate`/`objectEndDate` are negative integers for BCE.
- The `period` field uses the Met's own periodization which is close to but not identical to standard Egyptological periods.
- Truly sparse records (no period, no dynasty, no dates) are rare — most objects have at least a period even when other fields are empty.
- Full ingest takes ~7 minutes at 66 req/sec (staying under the 80 req/sec limit).
