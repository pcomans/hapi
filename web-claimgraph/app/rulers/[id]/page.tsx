import Link from "next/link";
import { notFound } from "next/navigation";
import { Constellation } from "@/components/Constellation";
import { SourceChip } from "@/components/SourceChip";
import { ClaimList } from "@/components/ClaimList";
import {
  getRuler,
  getClaimsFor,
  getEdgesTouching,
  getEscalationsTouching,
  getRulersByIds,
  type RulerRow,
} from "@/lib/queries";
import { reignLabel, dynastyLabel } from "@/lib/ui";

export default async function RulerDetail({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const rid = decodeURIComponent(id);
  const ruler = await getRuler(rid);
  if (!ruler) notFound();

  const claims = await getClaimsFor(rid);
  const edges = await getEdgesTouching(rid);
  const escalations = await getEscalationsTouching(rid);

  const otherIds = [
    ...new Set(edges.map((e) => (e.a_id === rid ? e.b_id : e.a_id))),
  ];
  const others = await getRulersByIds(otherIds);
  const allNodes = [ruler, ...others];
  const constMembers = allNodes.map((r) => ({
    id: r.id,
    source_id: r.source_id,
    display_name: r.display_name,
  }));
  const constEdges = edges.map((e) => ({ a_id: e.a_id, b_id: e.b_id, basis: e.basis }));

  return (
    <div className="stack" style={{ ["--gap" as string]: "24px" }}>
      <Link href="/rulers" className="muted" style={{ fontSize: "0.85rem" }}>
        ← All rulers
      </Link>

      <div className="stack" style={{ ["--gap" as string]: "8px" }}>
        <SourceChip source={ruler.source_id} />
        <h1>{ruler.display_name}</h1>
        <p className="sec">
          {dynastyLabel(ruler.dynasty, ruler.dynasty_label)}
          {reignLabel(ruler.reign_start_bce, ruler.reign_end_bce)
            ? ` · ${reignLabel(ruler.reign_start_bce, ruler.reign_end_bce)}`
            : ""}
          <span className="muted"> · {ruler.id}</span>
        </p>
      </div>

      <div className="grid-cards" style={{ gridTemplateColumns: "minmax(0, 1.1fr) minmax(0, 1fr)" }}>
        <section className="card stack" style={{ ["--gap" as string]: "10px" }}>
          <h3>Attributed claims</h3>
          <ClaimList claims={claims} />
        </section>

        <section className="card stack" style={{ ["--gap" as string]: "10px" }}>
          <h3>Linked across sources</h3>
          {edges.length === 0 ? (
            <p className="muted" style={{ fontSize: "0.88rem" }}>
              No approved cross-source identity link yet — this record stands alone (or its
              candidates were escalated).
            </p>
          ) : (
            <>
              <Constellation members={constMembers} edges={constEdges} size="sm" />
              <div className="rowlist" style={{ marginTop: 4 }}>
                {edges.map((e) => {
                  const other = e.a_id === rid ? e.b_name : e.a_name;
                  return (
                    <div key={e.candidate_id} style={{ fontSize: "0.85rem" }}>
                      <span className="pill approved">✓</span> {other}
                      <div className="muted" style={{ fontSize: "0.8rem", marginTop: 2 }}>
                        {e.reason}
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </section>
      </div>

      {escalations.length > 0 && (
        <section className="stack" style={{ ["--gap" as string]: "10px" }}>
          <h3>Escalated candidates</h3>
          <div className="card card-tight rowlist">
            {escalations.map((e) => {
              const other = e.a_id === rid ? e.b_name : e.a_name;
              return (
                <div key={e.candidate_id} style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
                  <span className={`pill ${e.homonym_trap ? "homonym" : "escalated"}`}>
                    {e.homonym_trap ? "⚠ homonym" : "→ escalated"}
                  </span>
                  <span style={{ fontSize: "0.88rem" }}>{other}</span>
                  <span className="muted" style={{ fontSize: "0.8rem", flexBasis: "100%" }}>{e.reason}</span>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
