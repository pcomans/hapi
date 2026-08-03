import Link from "next/link";
import { SourceChip } from "@/components/SourceChip";
import { getEscalations, getMeta } from "@/lib/queries";

export const dynamic = "force-static";

export default async function Escalations() {
  const meta = getMeta();
  const homonyms = await getEscalations({ onlyHomonym: true });
  const all = await getEscalations({ limit: 400 });

  return (
    <div className="stack" style={{ ["--gap" as string]: "22px" }}>
      <div className="stack" style={{ ["--gap" as string]: "8px" }}>
        <span className="eyebrow">The curator queue</span>
        <h1>Where the matcher refused to guess</h1>
        <p className="lede">
          Precision-first: a false merge corrupts authority data, so an uncorroborated or ambiguous
          candidate is <strong>escalated to a human</strong>, never guessed. {meta.stats.escalations}{" "}
          candidates were escalated — including every shared prenomen that is a known homonym across
          distinct kings.
        </p>
      </div>

      <section className="stack" style={{ ["--gap" as string]: "10px" }}>
        <h2>Homonym traps caught ({homonyms.length})</h2>
        <p className="sec" style={{ maxWidth: "62ch" }}>
          Egyptian throne names were reused across unrelated kings. A shared prenomen on the
          committed trap list (Menkheperre, Nebmaatre, Usermaatre, Sekhemre-*) is <em>not</em> proof
          of identity — these are held for a curator rather than merged.
        </p>
        <div className="card card-tight rowlist">
          {homonyms.slice(0, 60).map((e) => (
            <div key={e.candidate_id} style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
              <span className="pill homonym">⚠ {e.homonym_trap}</span>
              <Link href={`/rulers/${encodeURIComponent(e.a_id)}`} className="link-strong">{e.a_name}</Link>
              <SourceChip source={e.a_source} />
              <span className="muted">↮</span>
              <Link href={`/rulers/${encodeURIComponent(e.b_id)}`} className="link-strong">{e.b_name}</Link>
              <SourceChip source={e.b_source} />
            </div>
          ))}
        </div>
      </section>

      <section className="stack" style={{ ["--gap" as string]: "10px" }}>
        <h2>All escalations (first 400)</h2>
        <div className="card card-tight rowlist">
          {all.map((e) => (
            <div key={e.candidate_id} style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
              <span className={`pill ${e.homonym_trap ? "homonym" : "escalated"}`}>
                {e.homonym_trap ? "⚠ homonym" : "→ escalated"}
              </span>
              <span style={{ fontWeight: 500, fontSize: "0.9rem" }}>{e.a_name}</span>
              <SourceChip source={e.a_source} />
              <span className="muted">↮</span>
              <span style={{ fontWeight: 500, fontSize: "0.9rem" }}>{e.b_name}</span>
              <SourceChip source={e.b_source} />
              <span className="muted" style={{ fontSize: "0.8rem", flexBasis: "100%" }}>{e.reason}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
