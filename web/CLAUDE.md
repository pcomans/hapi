# Web App — Agent Instructions

TypeScript / Next.js frontend. Reads from Postgres (via Drizzle) and Typesense for search.

## Stack

- **Framework**: Next.js (App Router, React Server Components)
- **Database**: Drizzle ORM over Postgres
- **Search**: Typesense client for full-text search and faceted filtering
- **Map**: Leaflet or MapLibre (TBD at implementation time)
- **Styling**: Tailwind CSS

## Key conventions

- **Server Components by default.** Use client components (`"use client"`) only when the component needs interactivity (filters, map, search input). Artifact list/detail pages should be server-rendered for SEO.
- **License-aware rendering.** Every artifact has a `license` field from the canonical schema. Before displaying an image:
  - `cc0`: Embed directly
  - `cc-by-nc-nd`, `non-commercial-educational`: Embed with attribution, link back to source
  - Unknown or restrictive: Show placeholder, link to `source_url` at the museum's site
  - The rendering logic must live in a shared component, never ad-hoc per page.
- **Search goes through Typesense, not Postgres.** All user-facing search and filtering hits the Typesense index. Postgres is for detail pages and data that doesn't need full-text search.
- **Types come from the shared schema.** TypeScript types for canonical artifacts are generated from `shared/schema.json`. Do not hand-write artifact types — they must stay in sync with the pipeline's Pydantic models.

## Pages (planned)

- `/` — Home / search landing
- `/search` — Search results with faceted filters (site, ruler, dynasty, museum, object type)
- `/artifact/[id]` — Artifact detail with related candidates
- `/site/[id]` — All artifacts from an origin site
- `/map` — Geographic visualization of artifact distribution
- `/museum/[id]` — Browse a museum's Egyptian collection with Egyptology-native filters

## Commands

```bash
pnpm dev             # Dev server (http://localhost:3000)
pnpm test            # Run tests
pnpm lint            # ESLint
pnpm typecheck       # tsc --noEmit
pnpm build           # Production build
```

## Testing

- Component tests for license-aware rendering (critical path — must not display restricted images)
- Integration tests for search queries against a test Typesense instance
- Type conformance test: verify Drizzle schema matches `shared/schema.json`
