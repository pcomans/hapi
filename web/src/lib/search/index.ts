import type { License } from "@/components/artifact-image";
import Typesense from "typesense";

const typesenseClient = new Typesense.Client({
  apiKey: process.env.TYPESENSE_API_KEY ?? "hapi-dev-key",
  nodes: [
    {
      host: process.env.TYPESENSE_HOST ?? "localhost",
      port: Number(process.env.TYPESENSE_PORT ?? "8108"),
      protocol: "http",
    },
  ],
  connectionTimeoutSeconds: 5,
});

export interface SearchParams {
  q: string;
  page?: number;
  perPage?: number;
  filterBy?: string;
}

export interface SearchResult {
  id: string;
  source_museum: string;
  source_url: string;
  title?: string;
  object_type?: string;
  period?: string;
  dynasty?: string;
  ruler_display_name?: string;
  date_display?: string;
  origin_site_raw?: string;
  origin_site_display_name?: string;
  image_url?: string;
  thumbnail_url?: string;
  license: License;
}

export interface SearchResponse {
  hits: SearchResult[];
  found: number;
  page: number;
  totalPages: number;
  facets: Record<string, { value: string; count: number }[]>;
}

const SEARCH_FIELDS =
  "title,object_type,period,dynasty,ruler_display_name,origin_site_raw,origin_site_display_name,materials,excavation_id";

const FACET_FIELDS =
  "source_museum,period,dynasty,ruler_display_name,origin_site_display_name,object_type,origin_certainty";

export async function searchArtifacts(
  params: SearchParams,
): Promise<SearchResponse> {
  const perPage = params.perPage ?? 24;
  const page = params.page ?? 1;

  const result = await typesenseClient
    .collections("artifacts")
    .documents()
    .search({
      q: params.q || "*",
      query_by: SEARCH_FIELDS,
      filter_by: params.filterBy || "",
      facet_by: FACET_FIELDS,
      per_page: perPage,
      page,
      sort_by: params.q && params.q !== "*" ? "_text_match:desc" : "",
    });

  const hits: SearchResult[] = (result.hits ?? []).map(
    (hit) => hit.document as unknown as SearchResult,
  );

  const facets: Record<string, { value: string; count: number }[]> = {};
  for (const facet of result.facet_counts ?? []) {
    facets[facet.field_name] = facet.counts.map((c) => ({
      value: c.value,
      count: c.count,
    }));
  }

  return {
    hits,
    found: result.found,
    page,
    totalPages: Math.ceil(result.found / perPage),
    facets,
  };
}
