# Brooklyn Museum

## Access

- **API**: REST, requires API key (free registration)
- **Base URL**: `https://www.brooklynmuseum.org/api/v2`
- **Auth**: API key in header (`api_key`)
- **Egyptian collection**: ~3,000+ objects, renowned collection including the Wilbour Library of Egyptology

## Endpoints

- `GET /collection?collection_id={id}` — objects in a collection
- `GET /object/{id}` — single object detail
- Search and filtering endpoints available (confirm during implementation)

## License

**CC BY-NC-ND (images).** Images can be displayed with attribution for non-commercial use but cannot be modified. Metadata terms should be confirmed — likely more permissive than images. The project is non-commercial, so CC BY-NC-ND is usable with proper attribution.

## Data quality notes

- **Different field conventions from the Met.** Field names and structure differ — this is deliberately why Brooklyn is a v1 source (to stress-test normalization).
- **First museum to adopt Creative Commons (2004).** Long history of open access.
- **Provenance data quality varies.** Some objects have detailed excavation records; others have dealer provenance only.
- **Period/dynasty fields**: Need to confirm exact field names and conventions during initial API exploration. Likely less structured than the Met's dedicated fields.

## Known quirks

- API key required — need to register and store key securely (not in repo).
- Rate limits and pagination behavior need to be confirmed during implementation.
- The Brooklyn Museum was one of Cleo's four sources — their data has been aggregated before, which validates API stability.
