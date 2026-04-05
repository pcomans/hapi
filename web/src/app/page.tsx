import { Suspense } from "react";

import { ArtifactCard } from "@/components/artifact-card";
import { SearchBar } from "@/components/search-bar";
import { SearchFilters } from "@/components/search-filters";
import { searchArtifacts } from "@/lib/search";

interface PageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function Home({ searchParams }: PageProps) {
  const params = await searchParams;
  const q = typeof params.q === "string" ? params.q : "";
  const page = Number(params.page ?? "1");

  // Build filter string
  const filterFacets = [
    "source_museum",
    "period",
    "dynasty",
    "ruler_display_name",
    "object_type",
    "origin_site_display_name",
  ];
  const filters: string[] = [];
  for (const facet of filterFacets) {
    const value = params[facet];
    if (typeof value === "string" && value) {
      filters.push(`${facet}:=${value}`);
    }
  }

  let results = null;
  let error = null;
  const hasQuery = q || filters.length > 0;

  if (hasQuery) {
    try {
      results = await searchArtifacts({
        q: q || "*",
        page,
        perPage: 24,
        filterBy: filters.join(" && "),
      });
    } catch (e) {
      error = e instanceof Error ? e.message : "Search failed";
    }
  }

  return (
    <div className="flex flex-col min-h-screen">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-6">
          <h1 className="text-2xl font-bold text-gray-900">
            Hapi
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Cross-museum index of Egyptian artifacts
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-7xl w-full px-4 py-8 flex-1">
        <Suspense>
          <SearchBar />
        </Suspense>

        {!hasQuery && (
          <div className="mt-16 text-center text-gray-500">
            <p className="text-lg">
              Search by site, ruler, dynasty, or object type
            </p>
            <div className="flex flex-wrap justify-center gap-2 mt-4">
              {[
                "Karnak",
                "Thutmose III",
                "Dynasty 18",
                "Amarna",
                "scarab",
                "Valley of the Kings",
              ].map((suggestion) => (
                <a
                  key={suggestion}
                  href={`/?q=${encodeURIComponent(suggestion)}`}
                  className="rounded-full border border-gray-300 px-3 py-1 text-sm text-gray-600 hover:border-amber-500 hover:text-amber-700"
                >
                  {suggestion}
                </a>
              ))}
            </div>
          </div>
        )}

        {error && (
          <div className="mt-8 rounded-lg bg-red-50 p-4 text-red-700">
            {error}
          </div>
        )}

        {results && (
          <div className="mt-8 flex gap-8">
            <div className="w-56 flex-shrink-0 hidden lg:block">
              <Suspense>
                <SearchFilters facets={results.facets} />
              </Suspense>
            </div>

            <div className="flex-1">
              <p className="text-sm text-gray-500 mb-4">
                {results.found.toLocaleString()} artifact
                {results.found !== 1 ? "s" : ""} found
              </p>

              {results.hits.length === 0 ? (
                <p className="text-gray-500">
                  No artifacts match your search. Try broadening your query.
                </p>
              ) : (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {results.hits.map((hit) => (
                    <ArtifactCard
                      key={hit.id}
                      id={hit.id}
                      title={hit.title}
                      objectType={hit.object_type}
                      period={hit.period}
                      dynasty={hit.dynasty}
                      rulerDisplayName={hit.ruler_display_name}
                      dateDisplay={hit.date_display}
                      originSiteRaw={hit.origin_site_raw}
                      originSiteDisplayName={hit.origin_site_display_name}
                      sourceMuseum={hit.source_museum}
                      sourceUrl={hit.source_url}
                      imageUrl={hit.image_url}
                      thumbnailUrl={hit.thumbnail_url}
                      license={hit.license}
                    />
                  ))}
                </div>
              )}

              {results.totalPages > 1 && (
                <div className="mt-8 flex justify-center gap-2">
                  {page > 1 && (
                    <a
                      href={`/?${buildPageParams(params, page - 1)}`}
                      className="rounded-md border border-gray-300 px-3 py-2 text-sm hover:bg-gray-50"
                    >
                      Previous
                    </a>
                  )}
                  <span className="px-3 py-2 text-sm text-gray-500">
                    Page {page} of {results.totalPages}
                  </span>
                  {page < results.totalPages && (
                    <a
                      href={`/?${buildPageParams(params, page + 1)}`}
                      className="rounded-md border border-gray-300 px-3 py-2 text-sm hover:bg-gray-50"
                    >
                      Next
                    </a>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function buildPageParams(
  params: Record<string, string | string[] | undefined>,
  page: number,
): string {
  const p = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (typeof value === "string") {
      p.set(key, value);
    }
  }
  p.set("page", String(page));
  return p.toString();
}
