# Cleveland Museum of Art

Explored and ingested 2026-10-16.

The counts below are from `cleveland-profile/profile.json`, made by `cleveland-profile/profile.py` from the ingested `catalog.raw_cleveland` table. `raw_sha256` names the rows it read, and `code_sha256` names the code. A later edit to that code needs a re-run before the counts describe it. The paging observations are from exploration calls, which are not committed.

## Access

- **API**: Open Access API, REST/JSON, no authentication. Base URL `https://openaccess-api.clevelandart.org/api`.
- **Department**: `GET /artworks/?department=Egyptian and Ancient Near Eastern Art&limit=1000&skip=N`. It reported 1,070 records on 2026-10-16.
- **Detail**: `GET /artworks/{id}` returns `{"data": {...}}`. The list endpoint returns the same full record, so the ingest reads the list only, which takes two requests for the whole department.
  - The test fixtures were saved from the detail endpoint.
  - All eight are equal to their records as the list endpoint gave them to the ingest (`profile.json`, `fixtures`).
- **Documentation**: https://openaccess-api.clevelandart.org/ (the parameter list) and https://github.com/ClevelandMuseumArt/openaccess.

## Pagination

- `limit` caps at 1,000. A `limit=2000` request returns 1,000.
- `skip` is an offset. The API has no documented sort parameter, and `sort=id` is accepted but ignored.
- **Pages of 500 are not stable.** On 2026-10-16, three pages of 500 returned 1,070 rows but only 1,069 distinct ids: record 94761 appeared twice and one record was missed. Pages of 1,000 (`skip=0` and `skip=1000`) returned all 1,070 distinct ids with no overlap, and repeated calls returned the same order.
- The ingest uses pages of 1,000 and raises unless it read exactly the reported total of distinct ids, and unless that total stayed the same across pages.

## Rate limits

None seen at this volume (a handful of requests).

## License

- **Data**: CC0. "High-resolution images and data related to the CMA's collection are made available under a Creative Commons Zero (CC0) designation" (https://www.clevelandart.org/open-access).
- **Images**: per record. `share_license_status` is `"CC0"` or `"Copyrighted"`.
  - In the department, 1,069 records are CC0 and one is Copyrighted (101400, Boomerang, which has no image). 1,066 records have images.
  - The mapper takes the license from each record: no `images` → `none`, `CC0` → `cc0`, `Copyrighted` → `restricted` (no image shown).
  - An unknown status raises. `MUSEUM_LICENSE` is CC0, as the museum-level default the open access page states.

## Field inventory (canonical mapping)

| Cleveland field | Canonical | Notes |
|---|---|---|
| `id` | `id` (`cleveland-{id}`), `source_id` | Integer "athena" id |
| `url` | `source_url` | `https://clevelandart.org/art/{accession}` |
| `title` | `title` | |
| `description` | `description` | Verbatim. Sometimes contains HTML (`<em>`). |
| `type` | `object_type` | E.g. "Sculpture", "Cosmetic Objects" |
| `technique` | `materials` | One string, not split. "limestone, originally painted" is one material phrase. |
| `measurements` | `dimensions` | |
| `collection` | `period` | "Egypt - New Kingdom" → "New Kingdom". "Egyptian" → none. |
| `culture` | `dynasty`, `ruler_display_name` | See below |
| `creation_date_earliest` / `_latest` | `date_start` / `date_end` | Integers, negative for BCE |
| `creation_date` | `date_display` | |
| `find_spot` | `origin_site_raw` | 9 records in the department, 6 in scope |
| `provenance[].description` | `provenance` | Joined with "; " in API order. `sortorder` can be null. |
| `current_location` | `current_location` | Gallery, e.g. "107 Egyptian" |
| `accession_number`, `creditline` | `accession_number`, `credit_line` | |
| `images.web.url` | `image_url`, `thumbnail_url` | `web` is the smallest rendition (`print` and `full` are larger). |
| `external_resources.wikidata` | `wikidata_id` | One Q-id URL; more than one raises |

### `culture`

`culture` is a list. In the department it has one entry, or none for two records. That entry is a comma-separated string. Components are split as the mention reader splits them, so a comma inside parentheses does not split:

```
Egypt, Thebes(?), New Kingdom (1540–1069 BCE), Dynasty 18, reign of Tuthmosis III (1479–1425 BCE)
```

- The `Dynasty N` segments become `dynasty`. Three composite records name two, e.g. 94373, "Dynasty 12 (barrel beads) and New Kingdom, Dynasty 19 (eye beads)". All of them are kept, joined in the museum's order.
- **The reign component.** It is any component that opens as a reign does: "reign of", "probably reign of", "late reign of", "joint reign of". `cleveland_reign_components` in `pipeline/enrich/mentions.py` decides this, and both the mapper and the mention reader use it.
  - It becomes `ruler_display_name`, with two things removed:
    - its trailing dates. A final parenthesis is cut only if it holds a digit, so "(?)" stays.
    - a plain leading "reign of".
  - Everything else stays as written, e.g.:
    - qualifiers: "probably reign of Senusret I";
    - ranges: "Tuthmosis III (1479–1425 BCE)–reign of Amenhotep III";
    - "Nyuserre (2445–2422 BCE) or later".
  - This is raw text. The enrichment resolves it, as it does for the Met's `reign`.
- More than one reign component raises. None was seen.
- Places in `culture` ("Thebes(?)", "Karnak", "Haraga, cemetery G, tomb 413") are left to enrichment.

125 department records have a reign component, and 111 of them are in scope.
- 106 components end in a parenthesis that holds a digit (their dates).
- 19 have no final parenthesis.
- None ends in a parenthesis without a digit, such as "(?)".

Cleveland's ruler spellings differ from the Met's:
- "Tuthmosis III" (the Met has "Thutmose III");
- "Sesostris III" inside a range, and "Senusret III" elsewhere;
- "Psammetichus II-Apries";
- "Seti 1";
- "Shosheng I";
- "Amenemhat II to Sesostris III", a range.

### Enrichment (authority links)

The mention reader (`pipeline/enrich/mentions.py`, `cleveland_mentions`) reads Cleveland's catalogued reign. Those are the reign components of each `culture` entry (`cleveland_reign_components`, as above), read with the same classifier as the Met's `reign` field.

The mapper imports these helpers too. So an edit to them changes Cleveland's canonical rows, and `authority_links` refuses to run (`check_inputs`) until `normalize_cleveland` has re-run. The asset deps order a full job that way.

- Only the final parenthesis is cut, and only when it holds dates. So these stay as they are and are never resolved to one ruler:
  - a range: "reign of X (dates)–reign of Y (dates)";
  - a temporal reign: "… or later";
  - a doubt mark: "(?)", which makes the mention uncertain.
- It gave 111 ruler mentions from the 885 in-scope records:
  - 79 single identity;
  - 21 range or multiple;
  - 10 temporal;
  - 1 uncertain.

It does not yet read:
- `find_spot`;
- the places in `culture`;
- royal cues in titles or descriptions.

So Cleveland has no site links yet. Every Cleveland pair is unevaluated in `QUALIFIED_SCOPES`.

## Inclusion (Egyptian scope)

The department mixes Egyptian and Near Eastern material. Inclusion follows the museum's own `collection` field (`is_egyptian` in the mapper):

| `collection` | Records (2026-10-16) | In scope |
|---|---|---|
| `Egypt - <period>` (Predynastic … Greco-Roman, Ptolemaic Dynasty) | 883 | yes |
| `Egyptian` | 2 | yes |
| `Egypt - Modern Forgery` | 13 | **no**: the museum classifies them as modern forgeries, pastiches or modern arrangements, not ancient artifacts |
| `Near Eastern Art` | 172 | **no**: Near Eastern holdings. One of them, 135568, has culture "Egypt(?)", but the museum files it as Near Eastern. |
| **Total** | 1,070 (885 in scope) | |

- Raw ingest keeps the whole department verbatim, so these exclusions can be revisited without re-fetching.
- A collection the rule has not seen raises, so a new grouping gets decided rather than guessed.
- A few in-scope records have a `culture` that does not start with "Egypt" (`in_scope_records_whose_culture_does_not_start_with_egypt`). They stay in scope, because the collection decides.

## Known quirks

- One department record (101400, Boomerang) has `creation_date` "1920", the same year as its accession number (1920.2011). The mapper keeps it as given.
- `culture` uses "(?)" inline for doubt. There is no separate certainty field, so `origin_certainty` is left empty.
