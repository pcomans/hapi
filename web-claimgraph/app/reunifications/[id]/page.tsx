import Link from "next/link";
import { notFound } from "next/navigation";
import { Constellation } from "@/components/Constellation";
import { SourceChip } from "@/components/SourceChip";
import { ClaimList } from "@/components/ClaimList";
import {
  getClusterById,
  getRulersByIds,
  getClaimsFor,
  getApprovedEdgesAmong,
  getEscalationsTouchingAny,
  type RulerRow,
} from "@/lib/queries";
import { reignLabel, dynastyLabel } from "@/lib/ui";

export default async function ClusterDetail({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const cluster = await getClusterById(decodeURIComponent(id));
  if (!cluster) notFound();

  const rulers = await getRulersByIds(cluster.member_ids);
  const byId = new Map(rulers.map((r) => [r.id, r]));
  const members = cluster.member_ids
    .map((mid) => byId.get(mid))
    .filter((r): r is RulerRow => !!r);
  const constMembers = members.map((r) => ({
    id: r.id,
    source_id: r.source_id,
    display_name: r.display_name,
  }));

  const edges = await getApprovedEdgesAmong(cluster.member_ids);
  const claimsByMember = await Promise.all(members.map((m) => getClaimsFor(m.id)));
  const escalations = (await getEscalationsTouchingAny(cluster.member_ids)).filter(
    (e) => !(cluster.member_ids.includes(e.a_id) && cluster.member_ids.includes(e.b_id)),
  );

  return (
    <div className="stack" style={{ ["--gap" as string]: "26px" }}>
      <Link href="/reunifications" className="muted" style={{ fontSize: "0.85rem" }}>
        ← All reunifications
      </Link>

      <div className="stack" style={{ ["--gap" as string]: "8px" }}>
        <span className="eyebrow">Reunified identity</span>
        <h1>{cluster.label}</h1>
        <p className="sec">
          {members.length} records across {cluster.source_count} sources ·{" "}
          {edges.length} approved link{edges.length === 1 ? "" : "s"}
        </p>
      </div>

      <div className="card" style={{ display: "flex", justifyContent: "center" }}>
        <Constellation members={constMembers} edges={cluster.edges} size="lg" />
      </div>

      {/* the approved links, with the reviewer's reasoning */}
      <section className="stack" style={{ ["--gap" as string]: "10px" }}>
        <h2>Why these are linked</h2>
        <div className="card card-tight rowlist">
          {edges.map((e) => (
            <div key={e.candidate_id} style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
              <span className="pill approved">✓ approved</span>
              <span style={{ fontWeight: 550 }}>
                {e.a_name} <span className="muted">↔</span> {e.b_name}
              </span>
              <span className="muted" style={{ fontSize: "0.82rem", flexBasis: "100%" }}>
                {e.reason} · reviewer: {e.reviewer}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* each source record with its cited claims */}
      <section className="stack" style={{ ["--gap" as string]: "14px" }}>
        <h2>The records, kept intact</h2>
        <div className="grid-cards">
          {members.map((m, i) => (
            <div key={m.id} className="card stack" style={{ ["--gap" as string]: "10px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <Link href={`/rulers/${encodeURIComponent(m.id)}`} className="link-strong" style={{ fontSize: "1.05rem" }}>
                  {m.display_name}
                </Link>
                <SourceChip source={m.source_id} />
              </div>
              <div className="muted" style={{ fontSize: "0.82rem" }}>
                {dynastyLabel(m.dynasty, m.dynasty_label)}
                {reignLabel(m.reign_start_bce, m.reign_end_bce)
                  ? ` · ${reignLabel(m.reign_start_bce, m.reign_end_bce)}`
                  : ""}
              </div>
              <ClaimList claims={claimsByMember[i]} />
            </div>
          ))}
        </div>
      </section>

      {escalations.length > 0 && (
        <section className="stack" style={{ ["--gap" as string]: "10px" }}>
          <h2>Also considered — and refused</h2>
          <p className="sec" style={{ maxWidth: "60ch" }}>
            Candidate links the matcher declined to approve for these records, sent to the curator
            queue instead of guessed.
          </p>
          <div className="card card-tight rowlist">
            {escalations.slice(0, 12).map((e) => (
              <div key={e.candidate_id} style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
                <span className={`pill ${e.homonym_trap ? "homonym" : "escalated"}`}>
                  {e.homonym_trap ? "⚠ homonym" : "→ escalated"}
                </span>
                <span style={{ fontWeight: 500 }}>
                  {e.a_name} <span className="muted">↮</span> {e.b_name}
                </span>
                <span className="muted" style={{ fontSize: "0.82rem", flexBasis: "100%" }}>
                  {e.reason}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
