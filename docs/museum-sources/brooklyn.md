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

Returns `text/x-component` RSC payload (~300KB per object, mostly layout boilerplate). The Sanity collection object JSON is on a line matching `"accessionNumber"` and `"_type":"collectionObject"`, starting at `{"_id":...}`.

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

Separate RSC lines with `_type: "collectionGeographicalLocation"`:

```json
{ "_type": "collectionGeographicalLocation", "continent": "Africa", "country": "Egypt", "city": "El Behnasa (Oxyrhynchus)", "name": "El Behnasa (Oxyrhynchus), Egypt", "sourceId": 8036412 }
```

Referenced via: `{ "_key": "...", "geographicalLocation": "$ref", "type": "Reportedly from" }`

Geography types observed: "Place made", "Reportedly from", "Possible place made".

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
- **Geography types indicate certainty.** `type` field: "Place made" (confirmed), "Reportedly from" (uncertain), "Possible place made" (speculative). Maps to `origin_certainty`.
- **Provenance is free-text.** Full provenance chain as a single string (e.g., "Archaeological provenance not yet documented, reportedly from Cyprus; by 1900, acquired by an anonymous individual...").
- **Many objects lack images.** Not all objects have `imageUrl` in the search results.

## Performance

- **Search API**: No auth, no observed rate limiting. Hosted on Vercel CDN.
- **RSC detail pages**: ~300KB per response. 5 concurrent requests complete in ~400ms total (cached). No observed rate limiting at low concurrency.
- **Pagination**: 177 pages at size=50 for the Egyptian department.

## Ingest strategy

**Two-phase approach:**

1. **Phase 1 — Search API pagination**: Fetch all 177 pages (`size=50`) to get every `sourceId` plus basic metadata (title, dates, classification, geographicalLocations, imageUrl, accessionNumber, startYear, endYear).
2. **Phase 2 — RSC detail fetch**: For each `sourceId`, fetch the RSC page to get medium, dimensions, dynasty, period, creditLine, provenance, rightsType. Parse the Sanity JSON from the RSC payload.
3. **Store merged data**: Combine both sources into `raw_brooklyn` table as one JSON blob per object.

At 20 concurrent RSC fetches, phase 2 should complete in ~3 minutes for all 8,832 objects.

## Known quirks

- The old Brooklyn Museum REST API (`brooklynmuseum.org/api/v2`) is completely retired. No endpoints respond.
- The search API is undocumented — it powers the Next.js frontend and could change without notice.
- `sourceId` is a string in search API results but a number in the RSC Sanity data.
- The RSC payload format is Next.js-internal. Parsing relies on line-by-line text matching, not structured deserialization.
- The `maxPages` field in search metadata is always 416 regardless of actual result count — appears to be a global cap.
- Collection includes non-Egyptian material (Greek, Roman, Coptic, Near Eastern). Filtering strategy needed during normalization.
