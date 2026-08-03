import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hapi · Claim Graph",
  description:
    "A source-attributed claim graph that reunifies Egyptian rulers across five scholarly sources — with every cross-source identity link individually reviewed and cited.",
};

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/reunifications", label: "Reunifications" },
  { href: "/rulers", label: "Rulers" },
  { href: "/escalations", label: "Escalations" },
  { href: "/sources", label: "Sources" },
  { href: "/about", label: "About" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="masthead">
          <div className="wrap">
            <Link href="/" className="brand">
              <span className="glyph">◈</span> Hapi Claim Graph
            </Link>
            <nav className="nav">
              {NAV.map((n) => (
                <Link key={n.href} href={n.href}>
                  {n.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="wrap" style={{ paddingTop: 28, paddingBottom: 72 }}>
          {children}
        </main>
        <footer className="wrap" style={{ paddingBottom: 40, color: "var(--muted)", fontSize: "0.8rem" }}>
          Proof of concept · ADR-018 source-attributed claim graph + ADR-020 matcher policy ·
          data baked at build time, served from embedded Postgres (PGlite).
        </footer>
      </body>
    </html>
  );
}
