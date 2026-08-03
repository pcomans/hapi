import { getMeta } from "@/lib/queries";
import { SOURCE_ORDER } from "@/lib/types";
import { sourceColor, sourceLabel } from "@/lib/ui";

export const dynamic = "force-static";

// Editorial descriptions of the five authority works. The citations here match the
// committed provenance in pipeline/…/claimgraph/sources.py (SOURCE_AUTHORITY) and were
// validated by the egyptologist review; record counts come from the baked artifact.
type SourceIntro = {
  title: string;
  author: string;
  citation: string;
  covers: string;
  blurb: string;
  role: string;
  peerReviewed: boolean;
  url?: string;
};

const INTRO: Record<string, SourceIntro> = {
  leprohon: {
    title: "The Great Name: Ancient Egyptian Royal Titulary",
    author: "Ronald J. Leprohon, 2013",
    citation: "SBL Writings from the Ancient World 33",
    covers: "Every dynasty — Dynasty 1 to the Roman period",
    blurb:
      "A complete catalogue of the fivefold royal titulary — Horus, Two Ladies, Golden Horus, throne name (prenomen) and birth name (nomen) — for every king of Egypt, each name given in hieroglyphic transliteration with an English translation.",
    role: "Our primary source of anglicised throne-name forms.",
    peerReviewed: true,
  },
  beckerath: {
    title: "Chronologie des pharaonischen Ägypten",
    author: "Jürgen von Beckerath, 1997",
    citation: "Münchner Ägyptologische Studien 46",
    covers: "All of pharaonic Egypt — chronology & king lists",
    blurb:
      "The standard German reference for the absolute and relative chronology of pharaonic Egypt, listing rulers with their regnal dates. Written in German Egyptological transcription — “Chnem-ib-rê” where an English source writes “Khnemibre”.",
    role: "The one non-anglicised source — the reason the matcher carries a German-transcription normaliser.",
    peerReviewed: true,
  },
  kitchen: {
    title: "The Third Intermediate Period in Egypt (1100–650 BC)",
    author: "Kenneth A. Kitchen, 3rd ed. 1996",
    citation: "Aris & Phillips",
    covers: "Third Intermediate Period — Dynasties 21–25",
    blurb:
      "The foundational modern reconstruction of the Third Intermediate Period, untangling its overlapping dynasties, co-regencies and rival lines. It records the cases where a single king changed throne name during his reign.",
    role: "Source for the TIP kings and their multiple prenomina.",
    peerReviewed: true,
  },
  pharaoh_se: {
    title: "pharaoh.se — The Kings & Queens of Egypt",
    author: "Peter Lundström",
    citation: "Independently compiled online resource (self-published)",
    covers: "All periods — online titulary compilation",
    blurb:
      "An independently compiled, source-referenced online catalogue of Egyptian royal names and dates. Self-published and not peer-reviewed, so it is weighted below the four print references in adjudication — but valuable for breadth and cross-referencing.",
    role: "Breadth and cross-checking across the whole span.",
    peerReviewed: false,
    url: "https://pharaoh.se/",
  },
  ryholt: {
    title:
      "The Political Situation in Egypt during the Second Intermediate Period, c.1800–1550 B.C.",
    author: "Kim Ryholt, 1997",
    citation: "Carsten Niebuhr Institute Publications 20",
    covers: "Second Intermediate Period — Dynasties 13–17",
    blurb:
      "The reference reconstruction of the Second Intermediate Period and the Hyksos, built largely on the Turin King List. Ryholt renumbered several Dynasty-13 kings (the Sobekhoteps) against earlier schemes.",
    role: "Source for the SIP kings — and a reminder that regnal numerals are convention-relative.",
    peerReviewed: true,
  },
};

export default function Sources() {
  const meta = getMeta();
  return (
    <div className="stack" style={{ ["--gap" as string]: "20px", maxWidth: "78ch" }}>
      <div className="stack" style={{ ["--gap" as string]: "8px" }}>
        <span className="eyebrow">The authority data</span>
        <h1>Five scholars, five books</h1>
        <p className="sec">
          Every record in this graph is traced to one of five published references for Egyptian
          royal names and chronology. They disagree on spelling, numbering and dates — which is the
          whole point: the graph keeps each one intact and links them only where the evidence holds.
          Four are peer-reviewed print works; one is a carefully-sourced independent website, and is
          weighted accordingly.
        </p>
      </div>

      <div className="stack" style={{ ["--gap" as string]: "16px" }}>
        {SOURCE_ORDER.map((id) => {
          const s = INTRO[id];
          const count = meta.sources[id]?.rulers ?? 0;
          return (
            <article key={id} className="card stack" style={{ ["--gap" as string]: "10px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12, flexWrap: "wrap" }}>
                <span className="chip">
                  <span className="dot" style={{ ["--c" as string]: sourceColor(id) }} />
                  {sourceLabel(id)}
                </span>
                <span className="muted" style={{ fontSize: "0.82rem" }}>
                  {count.toLocaleString()} records
                </span>
              </div>

              <div>
                <h3 style={{ marginBottom: 2 }}>
                  <em>{s.title}</em>
                </h3>
                <p className="muted" style={{ fontSize: "0.85rem" }}>
                  {s.author} · {s.citation}
                  {!s.peerReviewed && " · not peer-reviewed"}
                </p>
              </div>

              <p className="sec">{s.blurb}</p>

              <div className="stack" style={{ ["--gap" as string]: "3px", fontSize: "0.88rem" }}>
                <div>
                  <strong>Covers</strong> · <span className="sec">{s.covers}</span>
                </div>
                <div>
                  <strong>In this graph</strong> · <span className="sec">{s.role}</span>
                </div>
              </div>

              {s.url && (
                <a href={s.url} target="_blank" rel="noopener noreferrer" className="link-strong" style={{ fontSize: "0.88rem" }}>
                  {s.url.replace(/^https?:\/\//, "").replace(/\/$/, "")} ↗
                </a>
              )}
            </article>
          );
        })}
      </div>

      <p className="muted" style={{ fontSize: "0.82rem" }}>
        Full citations and per-record page references travel with every claim in the graph — open
        any ruler to see them.
      </p>
    </div>
  );
}
