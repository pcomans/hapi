import Link from "next/link";
import { SourceChip } from "@/components/SourceChip";
import { searchRulers, countRulers } from "@/lib/queries";
import { SOURCE_ORDER, SOURCE_SHORT } from "@/lib/types";
import { dynastyLabel, reignLabel } from "@/lib/ui";

export const dynamic = "force-dynamic";
const PAGE = 150;

export default async function Rulers({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; source?: string; page?: string }>;
}) {
  const sp = await searchParams;
  const qtext = sp.q?.trim() || undefined;
  const source = sp.source || undefined;
  const page = Math.max(0, parseInt(sp.page ?? "0", 10) || 0);

  const params = { qtext, source, limit: PAGE, offset: page * PAGE };
  const [rows, total] = await Promise.all([searchRulers(params), countRulers(params)]);
  const pages = Math.ceil(total / PAGE);

  const linkFor = (patch: Record<string, string | undefined>) => {
    const merged: Record<string, string | undefined> = { q: qtext, source, ...patch };
    const usp = new URLSearchParams();
    for (const [k, v] of Object.entries(merged)) if (v) usp.set(k, v);
    const s = usp.toString();
    return `/rulers${s ? `?${s}` : ""}`;
  };

  return (
    <div className="stack" style={{ ["--gap" as string]: "18px" }}>
      <div className="stack" style={{ ["--gap" as string]: "8px" }}>
        <span className="eyebrow">Browse</span>
        <h1>Ruler records</h1>
        <p className="sec">{total.toLocaleString()} per-source records. Filter by source or search by name.</p>
      </div>

      <form action="/rulers" method="get" className="filters">
        <input
          type="search"
          name="q"
          defaultValue={qtext ?? ""}
          placeholder="Search name…"
          style={{
            padding: "7px 12px",
            borderRadius: 999,
            border: "1px solid var(--hair)",
            background: "var(--surface)",
            color: "var(--ink)",
            minWidth: 200,
            fontSize: "0.9rem",
          }}
        />
        {source && <input type="hidden" name="source" value={source} />}
        <button
          type="submit"
          style={{
            padding: "7px 16px",
            borderRadius: 999,
            border: "1px solid var(--ink)",
            background: "var(--ink)",
            color: "var(--page)",
            fontSize: "0.85rem",
            cursor: "pointer",
          }}
        >
          Search
        </button>
      </form>

      <div className="filters">
        <Link href={linkFor({ source: undefined, page: undefined })} className={!source ? "on" : ""}>
          All sources
        </Link>
        {SOURCE_ORDER.map((sid) => (
          <Link key={sid} href={linkFor({ source: sid, page: undefined })} className={source === sid ? "on" : ""}>
            {SOURCE_SHORT[sid]}
          </Link>
        ))}
      </div>

      <div className="card card-tight rowlist">
        {rows.length === 0 && <div className="muted">No records match.</div>}
        {rows.map((r) => (
          <Link
            key={r.id}
            href={`/rulers/${encodeURIComponent(r.id)}`}
            style={{ display: "flex", gap: 12, alignItems: "center" }}
          >
            <SourceChip source={r.source_id} />
            <span style={{ fontWeight: 550 }}>{r.display_name}</span>
            <span className="muted" style={{ fontSize: "0.82rem", marginLeft: "auto" }}>
              {dynastyLabel(r.dynasty, r.dynasty_label)}
              {reignLabel(r.reign_start_bce, r.reign_end_bce)
                ? ` · ${reignLabel(r.reign_start_bce, r.reign_end_bce)}`
                : ""}
            </span>
          </Link>
        ))}
      </div>

      {pages > 1 && (
        <div className="filters" style={{ justifyContent: "center" }}>
          {page > 0 && (
            <Link href={linkFor({ page: String(page - 1) })}>← Prev</Link>
          )}
          <span className="muted" style={{ fontSize: "0.82rem", alignSelf: "center" }}>
            Page {page + 1} of {pages}
          </span>
          {page < pages - 1 && (
            <Link href={linkFor({ page: String(page + 1) })}>Next →</Link>
          )}
        </div>
      )}
    </div>
  );
}
