import { NextRequest, NextResponse } from "next/server";

import { searchArtifacts } from "@/lib/search";

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;

  const q = params.get("q") ?? "*";
  const parsedPage = Number(params.get("page"));
  const page = Number.isFinite(parsedPage) && parsedPage >= 1 ? Math.floor(parsedPage) : 1;
  const parsedPerPage = Number(params.get("perPage"));
  const perPage = Number.isFinite(parsedPerPage) && parsedPerPage >= 1 ? Math.min(Math.floor(parsedPerPage), 100) : 24;

  // Build Typesense filter string from query params
  const filters: string[] = [];
  for (const facet of [
    "source_museum",
    "period",
    "dynasty",
    "ruler_display_name",
    "object_type",
    "origin_site_display_name",
  ]) {
    const value = params.get(facet);
    if (value) {
      filters.push(`${facet}:=\`${value.replace(/`/g, "")}\``);
    }
  }

  const result = await searchArtifacts({
    q,
    page,
    perPage,
    filterBy: filters.join(" && "),
  });

  return NextResponse.json(result);
}
