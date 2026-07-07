import "server-only";
import { getDb } from "./db";
import { artifact } from "./artifact";
import type { ClaimGraphMeta } from "./types";

export interface RulerRow {
  id: string;
  source_id: string;
  display_name: string;
  dynasty: number | null;
  dynasty_label: string | null;
  reign_start_bce: number | null;
  reign_end_bce: number | null;
  stage_group: string | null;
}
export interface ClaimRow {
  id: string;
  subject_id: string;
  predicate: string;
  value_text: string;
  value_translit: string | null;
  is_variant: boolean;
  scholar_name: string;
  publication_citation: string;
  cited_page: number | null;
  cited_pdf_page: string | null;
}
export interface EdgeRow {
  candidate_id: string;
  a_id: string;
  b_id: string;
  a_source: string;
  b_source: string;
  a_name: string;
  b_name: string;
  basis: string;
  shared_prenomen_keys: string;
  reason: string;
  reviewer: string;
}
export interface EscalationRow extends Omit<EdgeRow, "shared_prenomen_keys"> {
  homonym_trap: string | null;
}
export interface ClusterRow {
  id: string;
  label: string;
  source_count: number;
  member_count: number;
  sources: string[];
  member_ids: string[];
  edges: Array<{ a_id: string; b_id: string; basis: string }>;
}

export function getMeta(): ClaimGraphMeta {
  return artifact.meta;
}

async function q<T>(sql: string, params: unknown[] = []): Promise<T[]> {
  const db = await getDb();
  const res = await db.query<T>(sql, params);
  return res.rows;
}

export async function getMultiSourceClusters(limit?: number): Promise<ClusterRow[]> {
  const rows = await q<Omit<ClusterRow, "sources" | "member_ids" | "edges"> & {
    sources: string;
    member_ids: string;
    edges: string;
  }>(
    `SELECT id, label, source_count, member_count, sources, member_ids, edges
       FROM cluster WHERE source_count > 1
       ORDER BY source_count DESC, member_count DESC, label ASC
       ${limit ? "LIMIT $1" : ""}`,
    limit ? [limit] : [],
  );
  return rows.map((r) => ({
    ...r,
    sources: JSON.parse(r.sources),
    member_ids: JSON.parse(r.member_ids),
    edges: JSON.parse(r.edges),
  }));
}

export async function getClusterById(id: string): Promise<ClusterRow | null> {
  const rows = await q<{
    id: string;
    label: string;
    source_count: number;
    member_count: number;
    sources: string;
    member_ids: string;
    edges: string;
  }>(`SELECT * FROM cluster WHERE id = $1`, [id]);
  if (rows.length === 0) return null;
  const r = rows[0];
  return {
    ...r,
    sources: JSON.parse(r.sources),
    member_ids: JSON.parse(r.member_ids),
    edges: JSON.parse(r.edges),
  };
}

export async function getRulersByIds(ids: string[]): Promise<RulerRow[]> {
  if (ids.length === 0) return [];
  const ph = ids.map((_, i) => `$${i + 1}`).join(",");
  return q<RulerRow>(`SELECT * FROM ruler WHERE id IN (${ph})`, ids);
}

export async function getRuler(id: string): Promise<RulerRow | null> {
  const rows = await q<RulerRow>(`SELECT * FROM ruler WHERE id = $1`, [id]);
  return rows[0] ?? null;
}

export async function getClaimsFor(subjectId: string): Promise<ClaimRow[]> {
  return q<ClaimRow>(
    `SELECT * FROM claim WHERE subject_id = $1
       ORDER BY CASE predicate
         WHEN 'hapi:display_name' THEN 0
         WHEN 'hapi:prenomen' THEN 1
         WHEN 'hapi:horus_name' THEN 2
         WHEN 'hapi:nomen' THEN 3
         WHEN 'hapi:in_dynastic_period' THEN 4 ELSE 5 END, is_variant, value_text`,
    [subjectId],
  );
}

export async function getApprovedEdgesAmong(ids: string[]): Promise<EdgeRow[]> {
  if (ids.length === 0) return [];
  const ph = ids.map((_, i) => `$${i + 1}`).join(",");
  return q<EdgeRow>(
    `SELECT * FROM approved_edge WHERE a_id IN (${ph}) AND b_id IN (${ph}) ORDER BY a_source, b_source`,
    ids,
  );
}

export async function getEscalationsTouchingAny(ids: string[]): Promise<EscalationRow[]> {
  if (ids.length === 0) return [];
  const ph = ids.map((_, i) => `$${i + 1}`).join(",");
  return q<EscalationRow>(
    `SELECT * FROM escalation WHERE a_id IN (${ph}) OR b_id IN (${ph})
       ORDER BY (homonym_trap IS NOT NULL) DESC, a_name`,
    ids,
  );
}

export async function getEdgesTouching(id: string): Promise<EdgeRow[]> {
  return q<EdgeRow>(
    `SELECT * FROM approved_edge WHERE a_id = $1 OR b_id = $1 ORDER BY b_source, a_source`,
    [id],
  );
}

export async function getEscalationsTouching(id: string): Promise<EscalationRow[]> {
  return q<EscalationRow>(
    `SELECT * FROM escalation WHERE a_id = $1 OR b_id = $1 ORDER BY b_source, a_source`,
    [id],
  );
}

export interface SearchParams {
  qtext?: string;
  source?: string;
  dynasty?: number;
  limit?: number;
  offset?: number;
}
export async function searchRulers(p: SearchParams): Promise<RulerRow[]> {
  const where: string[] = [];
  const params: unknown[] = [];
  if (p.qtext) {
    params.push(`%${p.qtext.toLowerCase()}%`);
    where.push(`LOWER(display_name) LIKE $${params.length}`);
  }
  if (p.source) {
    params.push(p.source);
    where.push(`source_id = $${params.length}`);
  }
  if (p.dynasty != null) {
    params.push(p.dynasty);
    where.push(`dynasty = $${params.length}`);
  }
  params.push(p.limit ?? 200);
  const limitIdx = params.length;
  params.push(p.offset ?? 0);
  const offsetIdx = params.length;
  return q<RulerRow>(
    `SELECT * FROM ruler ${where.length ? "WHERE " + where.join(" AND ") : ""}
       ORDER BY dynasty NULLS LAST, display_name
       LIMIT $${limitIdx} OFFSET $${offsetIdx}`,
    params,
  );
}

export async function countRulers(p: SearchParams): Promise<number> {
  const where: string[] = [];
  const params: unknown[] = [];
  if (p.qtext) {
    params.push(`%${p.qtext.toLowerCase()}%`);
    where.push(`LOWER(display_name) LIKE $${params.length}`);
  }
  if (p.source) {
    params.push(p.source);
    where.push(`source_id = $${params.length}`);
  }
  if (p.dynasty != null) {
    params.push(p.dynasty);
    where.push(`dynasty = $${params.length}`);
  }
  const rows = await q<{ n: number }>(
    `SELECT COUNT(*)::int AS n FROM ruler ${where.length ? "WHERE " + where.join(" AND ") : ""}`,
    params,
  );
  return rows[0]?.n ?? 0;
}

export async function getEscalations(opts: {
  onlyHomonym?: boolean;
  limit?: number;
}): Promise<EscalationRow[]> {
  const where = opts.onlyHomonym ? "WHERE homonym_trap IS NOT NULL" : "";
  return q<EscalationRow>(
    `SELECT * FROM escalation ${where} ORDER BY (homonym_trap IS NOT NULL) DESC, a_name
       ${opts.limit ? `LIMIT ${Math.floor(opts.limit)}` : ""}`,
  );
}

export async function getDynasties(): Promise<Array<{ dynasty: number; n: number }>> {
  return q<{ dynasty: number; n: number }>(
    `SELECT dynasty, COUNT(*)::int AS n FROM ruler WHERE dynasty IS NOT NULL
       GROUP BY dynasty ORDER BY dynasty`,
  );
}
