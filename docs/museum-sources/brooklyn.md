# Brooklyn Museum

## Access

- **API**: Undocumented. No official public API exists (the old REST API at `/api/v2` was retired). Two data sources discovered via browser network inspection:
  1. **Search API**: `search.brooklynmuseum.org/api/search` — public, CORS `*`, no auth required. Returns list data with a subset of fields.
  2. **RSC detail pages**: `www.brooklynmuseum.org/objects/{sourceId}` with `RSC: 1` header — returns Next.js React Server Component payload containing the full Sanity CMS object. All fields available.
- **Auth**: None required for either endpoint.
- **Egyptian department**: 8,832 objects (collection name: "Egyptian, Classical, Ancient Near Eastern Art"). Includes Classical and Ancient Near Eastern objects alongside Egyptian — filtering needed.
- **Total collection**: 95,912 objects across all departments.

## Search API

### Endpoint

`GET https://search.brooklynmuseum.org/api/search`

### Parameters

| Parameter | Example | Notes |
|---|---|---|
| `type` | `collectionObject` | Required. Other types: `event`, `collectionArtist`, `exhibition`, etc. |
| `collection.name` | `Egyptian, Classical, Ancient Near Eastern Art` | URL-encode the full name. Collection ID is `5`. |
| `page` | `1` | 1-indexed pagination. |
| `size` | `50` | Max page size is 50. Values >50 silently fall back to 24 (the default). |
| `sortField` | `_score`, `accessionNumber` | Sort field. |
| `sortOrder` | `asc`, `desc` | Sort direction. |
| `hasImage` | `true` | Filter to objects with images. |
| `q` | `coffin` | Free-text search. |
| `classification` | `Sculpture` | Filter by classification. |
| `geographicalLocations.city` | `Thebes` | Filter by city. |
| `geographicalLocations.country` | `Egypt` | Filter by country. |
| `constituents.name` | `Egyptian` | Filter by culture/artist. |

### Response shape

```json
{
  "data": [
    {
      "source": "sanity",
      "sourceId": "60260",
      "sourceType": "collectionObject",
      "type": "collectionObject",
      "url": "https://www.brooklynmuseum.org/objects/60260",
      "title": "Head of Akhenaten Made in Two Pieces",
      "description": "...",
      "imageUrl": "https://brooklynmuseum.b-cdn.net/collections/objects/CUR.47.88a-b_NegA_print_bw.jpg",
      "accessionNumber": "47.88a-b",
      "onView": false,
      "classification": "Sculpture",
      "collection": { "id": "5", "name": "Egyptian, Classical, Ancient Near Eastern Art" },
      "dates": "1942–1943 C.E.",
      "startYear": 1942,
      "endYear": 1943,
      "geographicalLocations": [
        {
          "continent": "Africa",
          "country": "Egypt",
          "city": "Thebes",
          "name": "Thebes, Egypt",
          "id": "7093089",
          "type": "Reportedly from"
        }
      ],
      "constituents": [
        { "role": "Culture", "name": "Egyptian", "id": "190" }
      ]
    }
  ],
  "options": { "...facet counts for all filterable fields..." },
  "metadata": { "total": 8832, "pages": 177, "pageNumber": 1, "maxPages": 416 }
}
```

### Fields missing from search API (detail page only)

- `medium` — materials (e.g., "Limestone", "Clay, pigment")
- `dimensions` — physical dimensions
- `dynasty` — dynasty label (e.g., "in the style fo the late Dynasty 18")
- `period` — period label (e.g., "Predynastic Period, Naqada II")
- `section` — gallery section (e.g., "Early New Kingdom")
- `creditLine` — donor/fund credit
- `provenance` — free-text provenance chain
- `inscribed` — inscription text
- `labels` — gallery label text
- `markings` — maker's marks
- `rightsType` — license (e.g., "Creative Commons 3D")

## RSC Detail Pages

To get full object metadata, fetch the object page with RSC headers:

```
GET https://www.brooklynmuseum.org/objects/{sourceId}
Headers:
  RSC: 1
  Next-Url: /DEFAULT/objects/{sourceId}
```

Returns `text/x-component` RSC payload (~300KB per object, mostly layout boilerplate).

**Vercel bot protection:** Direct `curl` requests to `www.brooklynmuseum.org` are blocked by a Vercel Security Checkpoint, even with browser-like `User-Agent` headers. RSC fetches must be made from a real browser context (e.g., `fetch()` from a page already loaded on the domain) or a headless browser that can pass the checkpoint. The ingest asset should use a strategy that handles this (e.g., Playwright, or fetching from within the domain context).

### Parsing the RSC payload

The RSC payload uses Next.js streaming format: each line has a ref ID prefix (e.g., `4f8:`) followed by JSON data. To extract the collection object:

1. Split the payload by newlines.
2. Build a ref map: for each line, parse `{refId}:{jsonData}` where the JSON starts with `{`, `[`, or `"`.
3. Find the entry where `_type === "collectionObject"` and `accessionNumber` exists (skip the `globalConfiguration` entry).
4. Resolve `$`-prefixed string references recursively — fields like `geographicalLocations`, `constituents`, `collection`, and `images` are stored as references (e.g., `"$50e"`) that point to other ref IDs in the payload.

### Full Sanity object fields

```
_id, _type, accessionDate, accessionNumber, approvalsMask, classification,
collection, completeness, constituents, copyright, copyrightRestricted,
creditLine, dateAdded, description, dimensions, dynasty, edition,
featuredImage, geographicalLocations, images, inscribed, labels, markings,
medium, museumLocation, objectDate, objectDateBegin, objectDateEnd,
objectStatus, onView, period, portfolio, provenance, publicAccess, random,
rightsType, section, signed, sourceId, state, title, updatedAt, visible
```

### Geographical locations (in RSC payload)

Geography data is nested inside the `geographicalLocations` array after resolving refs. Each entry has a wrapper with `_key`, `type`, and a nested `geographicalLocation` object:

```json
{
  "_key": "HS8bHFoFwCoVWzp17Jxn55",
  "geographicalLocation": {
    "_type": "collectionGeographicalLocation",
    "city": "Saqqara",
    "continent": "Africa",
    "country": "Egypt",
    "name": "Saqqara, Egypt",
    "sourceId": 7127958
  },
  "type": "Reportedly from"
}
```

The `type` field is on the wrapper object (not the inner `geographicalLocation`). Some geo entries also include `state` (e.g., `"Lower Egypt"`).

Geography types observed: "Place made", "Reportedly from", "Possible place made", "Place collected".

### Constituents (in RSC payload)

Constituents are also nested with a wrapper containing `role`, `prefix`, `suffix`, and an inner `artist` object:

```json
{
  "artist": {
    "_type": "collectionArtist",
    "name": "Egyptian",
    "nationality": "Egyptian",
    "sourceId": 12429
  },
  "prefix": null,
  "role": "Culture",
  "suffix": null
}
```

### RSC dates vs search API dates

The RSC payload uses `objectDateBegin`/`objectDateEnd` while the search API uses `startYear`/`endYear`. These sometimes differ — the search API dates may include a +/-3 uncertainty offset for "ca." dates. The merged fixture stores both. The mapper should prefer `startYear`/`endYear` from the search API as these are consistently available.

## License

**Noncommercial use with attribution.** Per the image services page: "You may use and share images from the website for noncommercial purposes with proper attribution." The per-object `rightsType` field was observed as `"Creative Commons 3D"` for all Egyptian collection objects reviewed, but this should **not** be treated as confirmed CC BY 3.0 because that would allow commercial use and conflicts with the site-wide image terms. Unless Brooklyn Museum publishes clearer per-object rights documentation, treat the image services page as the governing reuse guidance for website images.

## Images

- **Full-size CDN**: `brooklynmuseum.b-cdn.net/collections/objects/{filename}`
- **Thumbnail server**: `imgsrv.brooklynmuseum.org/collections/objects/{filename}?width=400&quality=75`
- Image filenames are not limited to a single pattern. Observed names commonly start with `CUR.{accession}` but use varying suffixes/rendition markers (e.g., `CUR.47.88a-b_NegA_print_bw.jpg`), so implementers should not hard-code a specific suffix.

## Data quality notes

- **8,832 objects in department, but not all are Egyptian.** The department is "Egyptian, Classical, Ancient Near Eastern Art" — includes Greek (464), Roman (428), Ancient Near Eastern (122), Coptic (464), Cypriot (40), etc. Will need filtering during normalization.
- **Dates use negative for BCE in search API.** `startYear`/`endYear` use negative integers for BCE (e.g., `-1577`). The RSC detail page uses `objectDateBegin`/`objectDateEnd` which may differ. Search API is the reliable source for date integers.
- **Date uncertainty offset.** Search API dates sometimes have a +/-3 offset from display dates (e.g., "ca. 3500" maps to `startYear: 3497, endYear: 3503`). This appears to encode the "ca." uncertainty range.
- **Dynasty field is free-text.** Values like "in the style fo the late Dynasty 18" (note typo "fo") — mapper must handle varied formats.
- **Period field is verbose.** Values like "Modern, in the style of the New Kingdom, Amarna Period" or "Predynastic Period, Naqada II" — more descriptive than Met or Harvard.
- **Geography types indicate certainty.** `type` field: "Place made" → `made_in`, "Place excavated"/"Place found" → `excavated`, "Reportedly from"/"Possible place made"/"Possible place collected"/"Possible place purchased"/"Possible place manufactured" → `uncertain`, "Place collected" → `collected`, "Place used" → `used`, "Place modified" → `made_in`. Maps to `origin_certainty`. Some `geographicalLocations` array entries can be `null`.
- **Culture tags for filtering.** `constituents` array with `role: "Culture"` indicates object culture. Egyptian-adjacent cultures kept: Egyptian, Coptic, Demotic, Graeco-Egyptian, Egypto-Roman, Nubian. Non-Egyptian (Greek, Roman, Cypriot, Etruscan, etc.) filtered out during normalization. ~6,700 objects have no culture tag and are kept (majority of department, overwhelmingly Egyptian).
- **Provenance is free-text.** Full provenance chain as a single string (e.g., "Archaeological provenance not yet documented, reportedly from Cyprus; by 1900, acquired by an anonymous individual...").
- **Many objects lack images.** Not all objects have `imageUrl` in the search results.

## Performance

- **Search API**: No auth, no observed rate limiting. Hosted on Vercel CDN.
- **RSC detail pages**: ~300KB per response. 5 concurrent requests complete in ~400ms total (cached). No observed rate limiting at low concurrency. **Blocked by Vercel bot protection** when using `curl` or similar — requires browser context or headless browser.
- **Pagination**: 177 pages at size=50 for the Egyptian department (but `size=5` gives `pages: 1767` — `metadata.pages` is computed from the size parameter).

## Ingest strategy

**Two-phase approach using Playwright for RSC detail fetches:**

1. **Phase 1 — Search API pagination**: Fetch all pages (`size=50`, ~177 pages) via `requests` — the search API at `search.brooklynmuseum.org` has no bot protection. Gets: sourceId, title, dates, startYear, endYear, classification, geographicalLocations, imageUrl, accessionNumber, constituents, description, onView, collection.
2. **Phase 2 — RSC detail fetch via Playwright**: Launch a headless Chromium browser, navigate to `brooklynmuseum.org/opencollection` to pass the Vercel Security Checkpoint, then use `page.evaluate(fetch(...))` to fetch RSC payloads from within the browser context in batches of 20. Gets: medium, dimensions, dynasty, period, creditLine, provenance, rightsType, inscribed, objectDate, objectDateBegin, objectDateEnd, section.
3. **Store merged data**: Overlay RSC detail fields onto search API records and store in `raw_brooklyn` table as one JSON blob per object.

**Why Playwright?** Direct HTTP requests (`curl`, `requests`, `httpx`) to `www.brooklynmuseum.org` are blocked by Vercel's bot protection checkpoint — even with browser-like User-Agent headers. The search API at `search.brooklynmuseum.org` is unaffected. Fetching from within a real browser context that has already passed the checkpoint bypasses this restriction.

**Implementation:** `pipeline/assets/ingest/brooklyn.py`. The Playwright dependency is declared in `pyproject.toml`. Chromium must be installed via `uv run playwright install chromium` before the first run.

At 20 concurrent RSC fetches per batch, phase 2 should complete in ~3–5 minutes for all ~8,800 objects.

## Known quirks

- The old Brooklyn Museum REST API (`brooklynmuseum.org/api/v2`) is completely retired. No endpoints respond.
- The search API is undocumented — it powers the Next.js frontend and could change without notice.
- `sourceId` is a string in search API results but a number in the RSC Sanity data.
- The RSC payload format is Next.js-internal. Parsing uses a ref-map approach: split by newlines, parse `{refId}:{json}` pairs, then resolve `$`-prefixed references recursively. See "Parsing the RSC payload" section above.
- The `maxPages` field in search metadata varies with `size` parameter and does not reliably reflect actual page count. Use `metadata.total / size` instead.
- Collection includes non-Egyptian material (Greek, Roman, Coptic, Near Eastern). Filtered during normalization via `is_egyptian()` culture check — 1,278 objects excluded, 7,554 normalized.
- **Vercel bot protection** blocks direct HTTP requests to `www.brooklynmuseum.org`. The search API (`search.brooklynmuseum.org`) is not affected. RSC detail fetches require a browser context or headless browser.
- The search API's free-text `q` parameter does not support searching by `sourceId` directly. To find a specific object, browse pages or filter by known fields (geo, classification, etc.).
