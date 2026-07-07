import "server-only";
import { PGlite } from "@electric-sql/pglite";
import { artifact } from "./artifact";

/**
 * Embedded Postgres (PGlite, WASM) seeded once from the baked claim-graph artifact. This
 * is the "database that works on Vercel" — no external service, no connection string, no
 * secret. It gives real SQL over the source-attributed E13 tables (ADR-018 relational
 * encoding) and is queried from server components.
 *
 * A single instance is memoised on globalThis so warm serverless invocations reuse it;
 * a cold start re-seeds (~1s for this corpus). Concurrent first requests share one seed
 * via the cached promise.
 */

type Global = typeof globalThis & { __claimgraphDb__?: Promise<PGlite> };
const g = globalThis as Global;

const DDL = `
CREATE TABLE ruler (
  id text PRIMARY KEY,
  source_id text NOT NULL,
  display_name text NOT NULL,
  dynasty int,
  dynasty_label text,
  reign_start_bce int,
  reign_end_bce int,
  stage_group text
);
CREATE INDEX ruler_source ON ruler(source_id);
CREATE INDEX ruler_dynasty ON ruler(dynasty);

CREATE TABLE claim (
  id text PRIMARY KEY,
  subject_id text NOT NULL,
  predicate text NOT NULL,
  value_text text NOT NULL,
  value_translit text,
  is_variant boolean NOT NULL,
  scholar_name text NOT NULL,
  publication_citation text NOT NULL,
  cited_page int,
  cited_pdf_page text
);
CREATE INDEX claim_subject ON claim(subject_id);

CREATE TABLE approved_edge (
  candidate_id text PRIMARY KEY,
  a_id text NOT NULL, b_id text NOT NULL,
  a_source text NOT NULL, b_source text NOT NULL,
  a_name text NOT NULL, b_name text NOT NULL,
  basis text NOT NULL,
  shared_prenomen_keys text NOT NULL,
  reason text NOT NULL,
  reviewer text NOT NULL
);
CREATE INDEX edge_a ON approved_edge(a_id);
CREATE INDEX edge_b ON approved_edge(b_id);

CREATE TABLE escalation (
  candidate_id text PRIMARY KEY,
  a_id text NOT NULL, b_id text NOT NULL,
  a_source text NOT NULL, b_source text NOT NULL,
  a_name text NOT NULL, b_name text NOT NULL,
  basis text NOT NULL,
  reason text NOT NULL,
  homonym_trap text,
  reviewer text NOT NULL
);
CREATE INDEX esc_a ON escalation(a_id);
CREATE INDEX esc_b ON escalation(b_id);

CREATE TABLE cluster (
  id text PRIMARY KEY,
  label text NOT NULL,
  source_count int NOT NULL,
  member_count int NOT NULL,
  sources text NOT NULL,
  member_ids text NOT NULL,
  edges text NOT NULL
);
CREATE INDEX cluster_sc ON cluster(source_count DESC, member_count DESC);

CREATE TABLE intra_identity (
  subject_id text NOT NULL,
  object_id text NOT NULL,
  scholar_name text NOT NULL,
  publication_citation text NOT NULL
);
`;

async function bulkInsert(
  db: PGlite,
  table: string,
  columns: string[],
  rows: unknown[][],
) {
  if (rows.length === 0) return;
  // Keep each INSERT's bound-parameter count well under the Postgres wire-protocol limit
  // of 65535 bound parameters per statement (a 16-bit unsigned count); overflowing it
  // throws "RangeError: Invalid array length" in PGlite. 20000 is a safe margin.
  const maxParams = 20000;
  const perRow = columns.length;
  const chunk = Math.max(1, Math.floor(maxParams / perRow));
  for (let start = 0; start < rows.length; start += chunk) {
    const slice = rows.slice(start, start + chunk);
    const params: unknown[] = [];
    const tuples = slice.map((row) => {
      const ph = row.map((_, j) => `$${params.length + j + 1}`);
      params.push(...row);
      return `(${ph.join(",")})`;
    });
    await db.query(
      `INSERT INTO ${table} (${columns.join(",")}) VALUES ${tuples.join(",")}`,
      params,
    );
  }
}

async function seed(): Promise<PGlite> {
  const db = new PGlite();
  await db.exec(DDL);

  await bulkInsert(
    db,
    "ruler",
    ["id", "source_id", "display_name", "dynasty", "dynasty_label", "reign_start_bce", "reign_end_bce", "stage_group"],
    artifact.rulers.map((r) => [
      r.id, r.source_id, r.display_name, r.dynasty, r.dynasty_label,
      r.reign_start_bce, r.reign_end_bce, r.stage_group,
    ]),
  );

  await bulkInsert(
    db,
    "claim",
    ["id", "subject_id", "predicate", "value_text", "value_translit", "is_variant", "scholar_name", "publication_citation", "cited_page", "cited_pdf_page"],
    artifact.claims.map((c) => [
      c.id, c.subject_id, c.predicate, c.value_text, c.value_translit,
      c.is_variant, c.scholar_name, c.publication_citation, c.cited_page, c.cited_pdf_page,
    ]),
  );

  await bulkInsert(
    db,
    "approved_edge",
    ["candidate_id", "a_id", "b_id", "a_source", "b_source", "a_name", "b_name", "basis", "shared_prenomen_keys", "reason", "reviewer"],
    artifact.approvedEdges.map((e) => [
      e.candidate_id, e.a_id, e.b_id, e.a_source, e.b_source, e.a_name, e.b_name,
      e.basis, e.shared_prenomen_keys.join(", "), e.reason, e.reviewer,
    ]),
  );

  await bulkInsert(
    db,
    "escalation",
    ["candidate_id", "a_id", "b_id", "a_source", "b_source", "a_name", "b_name", "basis", "reason", "homonym_trap", "reviewer"],
    artifact.escalations.map((e) => [
      e.candidate_id, e.a_id, e.b_id, e.a_source, e.b_source, e.a_name, e.b_name,
      e.basis, e.reason, e.homonym_trap, e.reviewer,
    ]),
  );

  await bulkInsert(
    db,
    "cluster",
    ["id", "label", "source_count", "member_count", "sources", "member_ids", "edges"],
    artifact.clusters.map((c) => [
      c.id, c.label, c.source_count, c.member_ids.length,
      JSON.stringify(c.sources), JSON.stringify(c.member_ids), JSON.stringify(c.edges),
    ]),
  );

  await bulkInsert(
    db,
    "intra_identity",
    ["subject_id", "object_id", "scholar_name", "publication_citation"],
    artifact.intraSourceIdentities.map((i) => [
      i.subject_id, i.object_id, i.scholar_name, i.publication_citation,
    ]),
  );

  return db;
}

export function getDb(): Promise<PGlite> {
  if (!g.__claimgraphDb__) g.__claimgraphDb__ = seed();
  return g.__claimgraphDb__;
}
