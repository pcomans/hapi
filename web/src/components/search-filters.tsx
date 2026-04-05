"use client";

import { useRouter, useSearchParams } from "next/navigation";

interface FacetValue {
  value: string;
  count: number;
}

interface SearchFiltersProps {
  facets: Record<string, FacetValue[]>;
}

const FACET_LABELS: Record<string, string> = {
  source_museum: "Museum",
  period: "Period",
  dynasty: "Dynasty",
  ruler_display_name: "Ruler",
  origin_site_display_name: "Origin Site",
  object_type: "Object Type",
};

const FACET_ORDER = [
  "source_museum",
  "origin_site_display_name",
  "dynasty",
  "ruler_display_name",
  "period",
  "object_type",
];

export function SearchFilters({ facets }: SearchFiltersProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  function toggleFilter(facet: string, value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (params.get(facet) === value) {
      params.delete(facet);
    } else {
      params.set(facet, value);
    }
    params.delete("page");
    router.push(`/?${params.toString()}`);
  }

  function clearFilters() {
    const params = new URLSearchParams();
    const q = searchParams.get("q");
    if (q) params.set("q", q);
    router.push(`/?${params.toString()}`);
  }

  const hasActiveFilters = FACET_ORDER.some((f) => searchParams.has(f));

  return (
    <aside className="space-y-4">
      {hasActiveFilters && (
        <button
          onClick={clearFilters}
          className="text-sm text-amber-600 hover:text-amber-700"
        >
          Clear all filters
        </button>
      )}
      {FACET_ORDER.map((facetKey) => {
        const values = facets[facetKey];
        if (!values || values.length === 0) return null;
        const active = searchParams.get(facetKey);
        return (
          <div key={facetKey}>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              {FACET_LABELS[facetKey] ?? facetKey}
            </h3>
            <ul className="space-y-1 max-h-48 overflow-y-auto">
              {values.slice(0, 20).map((v) => (
                <li key={v.value}>
                  <button
                    onClick={() => toggleFilter(facetKey, v.value)}
                    className={`text-sm w-full text-left px-2 py-1 rounded hover:bg-gray-100 ${
                      active === v.value
                        ? "bg-amber-50 text-amber-700 font-medium"
                        : "text-gray-600"
                    }`}
                  >
                    {v.value}{" "}
                    <span className="text-gray-400">({v.count})</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </aside>
  );
}
