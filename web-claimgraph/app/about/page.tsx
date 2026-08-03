import { getMeta } from "@/lib/queries";
import { modelLabel } from "@/lib/ui";

export const dynamic = "force-static";

export default function About() {
  const meta = getMeta();
  return (
    <div className="stack" style={{ ["--gap" as string]: "18px", maxWidth: "72ch" }}>
      <span className="eyebrow">About this proof of concept</span>
      <h1>A source-attributed claim graph</h1>

      <p className="sec">
        Egyptian rulers are recorded across hundreds of publications, each with its own naming
        convention. This POC ingests five scholarly sources and models them as a{" "}
        <strong>claim graph</strong> (ADR-018): every fact is a source-attributed statement, and no
        source is ever overwritten or silently merged into another.
      </p>

      <h3>How matching works</h3>
      <p className="sec">
        Cross-source identity is a substantive scholarly claim, not string equality (ADR-020). A
        deterministic first stage proposes candidate links only when a{" "}
        <strong>normalized throne name (prenomen)</strong> is shared — set-valued, over structured
        titulary fields, via a committed cross-convention normalization table. A second stage — the
        live LLM reviewer — decides each candidate <em>precision-first</em>: name agreement alone is
        never enough to approve, known homonyms and ambiguous cases are{" "}
        <strong>escalated to a human</strong>, and no two distinct kings are ever silently conflated.
        There is no transitive auto-merge.
      </p>
      <p className="sec">
        Records that share <em>only a similar name</em>, with no throne name to back it up, are{" "}
        <strong>never auto-linked</strong> — they are set aside for a person to check. Confirming
        such a pair (for example that the Greek name <em>Usaphais</em> denotes King Den) requires{" "}
        <strong>external documented evidence</strong> — a cited scholarly source, verified by a
        human — not the reviewer&apos;s unsupported say-so. &ldquo;The model knows&rdquo; is not a
        source, so the pipeline never even asks the reviewer to judge a name-only pair.
      </p>

      <h3>Provenance</h3>
      <p className="sec">
        This build&apos;s links were decided by the{" "}
        <strong>{meta.reviewer === "llm" ? modelLabel(meta.model) : "deterministic policy (draft)"}</strong>.
        Every approved link is gated on an approved verdict and every claim carries its scholar and
        page citation. The full reviewer interaction is captured for replay.
      </p>

      <h3>Architecture</h3>
      <ul className="sec" style={{ paddingLeft: 20, lineHeight: 1.7 }}>
        <li>Graph built at <strong>build time</strong> by the Python pipeline; the reviewed result is baked to a committed JSON artifact.</li>
        <li>The deployed app reads only that artifact — <strong>no runtime API key</strong>.</li>
        <li>Served from <strong>embedded Postgres (PGlite)</strong>, seeded in-process — no external database, turnkey on Vercel.</li>
      </ul>

      <div className="card card-tight">
        <div className="muted" style={{ fontSize: "0.8rem" }}>
          {meta.stats.rulers.toLocaleString()} records · {meta.stats.claims.toLocaleString()} claims ·{" "}
          {meta.stats.candidates.toLocaleString()} candidates · {meta.stats.approvedLinks} approved ·{" "}
          {meta.stats.escalations} escalated
        </div>
      </div>
    </div>
  );
}
