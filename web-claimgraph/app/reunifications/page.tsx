import Link from "next/link";
import { Constellation } from "@/components/Constellation";
import { getMultiSourceClusters, getRulersByIds, type RulerRow } from "@/lib/queries";

export const dynamic = "force-static";

export default async function Reunifications() {
  const clusters = await getMultiSourceClusters();
  const memberIds = [...new Set(clusters.flatMap((c) => c.member_ids))];
  const rulers = await getRulersByIds(memberIds);
  const byId = new Map(rulers.map((r) => [r.id, r]));

  return (
    <div className="stack" style={{ ["--gap" as string]: "22px" }}>
      <div className="stack" style={{ ["--gap" as string]: "10px" }}>
        <span className="eyebrow">Cross-source reunifications</span>
        <h1>{clusters.length} kings, reunified across sources</h1>
        <p className="lede">
          Each is a connected set of per-source records joined by approved throne-name links. The
          records are never merged into one — the constellation just makes the agreement visible,
          with every edge independently reviewed.
        </p>
      </div>
      <div className="grid-cards">
        {clusters.map((c) => {
          const members = c.member_ids
            .map((id) => byId.get(id))
            .filter((r): r is RulerRow => !!r)
            .map((r) => ({ id: r.id, source_id: r.source_id, display_name: r.display_name }));
          return (
            <Link key={c.id} href={`/reunifications/${encodeURIComponent(c.id)}`} className="card" style={{ display: "block" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
                <h3>{c.label}</h3>
                <span className="muted" style={{ fontSize: "0.78rem" }}>{c.source_count} src</span>
              </div>
              <Constellation members={members} edges={c.edges} linkNodes={false} />
            </Link>
          );
        })}
      </div>
    </div>
  );
}
