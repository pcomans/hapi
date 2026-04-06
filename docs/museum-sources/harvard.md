# Harvard Art Museums

## Access

- **API**: REST, requires API key (free registration)
- **Base URL**: `https://api.harvardartmuseums.org`
- **Auth**: API key as query parameter (`apikey`)
- **Egyptian collection**: Size TBD — needs to be determined during initial exploration
- **Documentation**: https://github.com/harvardartmuseums/api-docs

## Endpoints

- `GET /object?classification=Egyptian&size=100&page=1` — paginated object list (classification filter needs confirmation)
- `GET /object/{id}` — single object detail
- Supports faceted search with various filter parameters

## License

**Non-commercial educational use.** Images and data available for non-commercial educational and scholarly purposes. More restrictive than Met (CC0) but compatible with this project's non-commercial nature. Exact terms should be confirmed during implementation.

## Data quality notes

- **Collection size unknown.** Egyptian holdings need to be scoped during initial API exploration. Harvard's collection is broader (not Egypt-focused), so the Egyptian subset may be smaller than Met or Brooklyn.
- **Field structure differs from both Met and Brooklyn.** This is the third normalization test case — three different data shapes mapping to one canonical schema.
- **Harvard has strong provenance research.** Objects from Harvard-affiliated excavations (e.g., Reisner expeditions at Giza) may have unusually detailed provenance records.
- **Classification system**: Harvard uses its own classification taxonomy. Mapping to Egyptology-native categories will require exploration.

## Known quirks

- API key required — register at https://harvardartmuseums.org/collections/api
- Rate limits and pagination behavior need confirmation.
- The API is well-documented on GitHub, which should speed up mapper development.
- May include objects that are "Egyptian-influenced" but not actually from ancient Egypt (e.g., Egyptianizing Roman pieces). The mapper needs to handle or filter these.
