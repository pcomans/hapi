import Link from "next/link";
import { DraftBanner } from "@/components/DraftBanner";
import { Constellation } from "@/components/Constellation";
import { SourceChip } from "@/components/SourceChip";
import {
  getMeta,
  getMultiSourceClusters,
  getRulersByIds,
  type RulerRow,
} from "@/lib/queries";
import { SOURCE_ORDER } from "@/lib/types";

export const dynamic = "force-static";

export default async function Home() {
  const meta = getMeta();
  const featured = await getMultiSourceClusters(9);
  const memberIds = [...new Set(featured.flatMap((c) => c.member_ids))];
  const rulers = await getRulersByIds(memberIds);
  const byId = new Map(rulers.map((r) => [r.id, r]));

  const s = meta.stats;

  return (
    <div className="stack" style={{ ["--gap" as string]: "34px" }}>
      <DraftBanner />

      <section className="stack" style={{ ["--gap" as string]: "14px" }}>
        <span className="eyebrow">Cross-museum authority · proof of concept</span>
        <h1>
          One king, five scholars,
          <br />
          one reunified record.
        </h1>
        <p className="lede">
          Every source names Egypt&apos;s rulers differently — Leprohon&apos;s{" "}
          <em>Amenhotep&nbsp;III</em> is Beckerath&apos;s <em>Amenophis&nbsp;III.</em> This graph
          keeps each source&apos;s record intact and draws a link between them only when a shared{" "}
          <strong>throne name</strong> corroborates it — precision-first, escalating to a human
          when in doubt. No source is overwritten; nothing is silently merged.
        </p>
      </section>

      <section className="tiles">
        <Stat n={s.multiSourceClusters} l="cross-source reunifications" sub="kings linked across ≥2 sources" />
        <Stat n={s.approvedLinks} l="approved identity links" sub="each cited & individually reviewed" />
        <Stat n={s.escalations} l="escalated to curator" sub="matcher refused to guess" />
        <Stat n={s.rulers.toLocaleString()} l="source records" sub={`${Object.keys(meta.sources).length} sources`} />
        <Stat n={s.claims.toLocaleString()} l="attributed claims" sub="every one carries provenance" />
      </section>

      <section className="card" style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
        <span className="eyebrow" style={{ marginRight: 6 }}>Sources</span>
        {SOURCE_ORDER.filter((sid) => meta.sources[sid]).map((sid) => (
          <span key={sid} style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <SourceChip source={sid} />
            <span className="muted" style={{ fontSize: "0.82rem" }}>
              {meta.sources[sid].rulers} records
            </span>
          </span>
        ))}
      </section>

      <section className="stack" style={{ ["--gap" as string]: "16px" }}>
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12 }}>
          <h2>Featured reunifications</h2>
          <Link href="/reunifications" className="link-strong">
            See all {meta.stats.multiSourceClusters} →
          </Link>
        </div>
        <p className="sec" style={{ maxWidth: "60ch", marginTop: -6 }}>
          Each constellation is one historical king, with a node per source record. Links are
          approved cross-source identities. Click any node to inspect its cited claims.
        </p>
        <div className="grid-cards">
          {featured.map((c) => {
            const members = c.member_ids
              .map((id) => byId.get(id))
              .filter((r): r is RulerRow => !!r)
              .map((r) => ({ id: r.id, source_id: r.source_id, display_name: r.display_name }));
            return (
              <Link key={c.id} href={`/reunifications/${encodeURIComponent(c.id)}`} className="card" style={{ display: "block" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
                  <h3>{c.label}</h3>
                  <span className="muted" style={{ fontSize: "0.78rem" }}>{c.source_count} sources</span>
                </div>
                <Constellation members={members} edges={c.edges} linkNodes={false} />
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function Stat({ n, l, sub }: { n: number | string; l: string; sub?: string }) {
  return (
    <div className="tile">
      <div className="n">{n}</div>
      <div className="l">{l}</div>
      {sub && <div className="s">{sub}</div>}
    </div>
  );
}
