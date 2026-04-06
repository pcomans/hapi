# Harvard Art Museums

## Access

- **API**: REST, requires API key (free registration)
- **Base URL**: `https://api.harvardartmuseums.org`
- **Auth**: API key as query parameter (`apikey`)
- **Egyptian collection**: 722 objects (filtered by `culture=Egyptian`)
- **Documentation**: https://github.com/harvardartmuseums/api-docs

## Endpoints

- `GET /object?culture=Egyptian&size=100&page=1` — paginated object list
- `GET /object/{id}` — single object detail
- Max page size: 100. At 722 objects, that's 8 pages.

## License

**Non-commercial educational use.** Images and data available for non-commercial educational and scholarly purposes. `imagepermissionlevel` field controls per-object image display: 0 = allowed, 1+ = restricted.

## Data quality notes

- **722 objects total.** Small collection compared to Met (~28k). Department is "Ancient and Byzantine Art & Numismatics".
- **No ruler/reign field.** Harvard has no equivalent of Met's `reign` field. Ruler identification deferred to enrichment stage.
- **Period sometimes includes dynasty.** E.g., "Late Period, Dynasty 26" — mapper splits this into separate period and dynasty fields.
- **Places field.** Array of objects with `displayname` and `type`. "Creation Place" entries use hierarchical format: "Ancient & Byzantine World, Africa, Egypt (Ancient)" or more specific like "Ancient & Byzantine World, Africa, Antinoopolis (Egypt)".
- **No geographic confidence.** Unlike the Met's `geographyType` ("From", "Said to be from"), Harvard places don't indicate certainty.
- **Medium can be multiline.** Uses `\r\n` delimiters with labeled sections: "Binder: Beeswax\r\nPigments: Lead white...".
- **Dates.** `datebegin`/`dateend` are integers (negative for BCE, positive for CE). **0 means unknown**, not year zero — mapper treats 0 as null.
- **No provenance hierarchy.** Unlike Met's structured geography (country, region, subregion, locale, locus), Harvard has a flat `places` array.
- **Worktypes for object type.** Array of objects; mapper uses the first entry's `worktype` field.
- **Many objects lack images.** `primaryimageurl` is null for unphoto­graphed objects. `imagepermissionlevel` may still be 0 (display allowed) even when no image exists.

## Known quirks

- API key required — register at https://harvardartmuseums.org/collections/api
- No observed rate limiting at the volumes we fetch (~8 requests total).
- `culture=Egyptian` is the correct filter. Other filters like `classification` or `place` are too narrow or miss objects.
- Collection includes Roman-era Egyptian material (Fayum portraits, Coptic textiles) — these are valid for this project's scope.
- `objectid` and `id` fields both exist and contain the same value.
