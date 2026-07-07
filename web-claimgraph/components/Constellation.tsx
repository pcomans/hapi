import Link from "next/link";
import { sourceColor, sourceLabel } from "@/lib/ui";

export interface ConstellationMember {
  id: string;
  source_id: string;
  display_name: string;
}
export interface ConstellationEdge {
  a_id: string;
  b_id: string;
  basis: string;
}
export interface ConstellationEsc {
  a_id: string;
  b_id: string;
  homonym_trap?: string | null;
}

interface Props {
  members: ConstellationMember[];
  edges: ConstellationEdge[];
  escalated?: ConstellationEsc[];
  size?: "sm" | "lg";
  linkNodes?: boolean;
}

/**
 * A node-link "constellation": each per-source ruler record is a node (coloured + labelled
 * by source), each approved `same_entity_as` link a connector. Nodes sit on a circle so no
 * record is privileged as a canonical "winner" — faithful to ADR-018 (no collapse) and to
 * ADR-020 (every connecting edge stays an independent, sourced claim). Escalated links,
 * when shown, are dashed amber: the matcher considered them and deliberately refused.
 */
export function Constellation({
  members,
  edges,
  escalated = [],
  size = "sm",
  linkNodes = true,
}: Props) {
  const n = members.length;
  const chipH = size === "lg" ? 40 : 32;
  const charW = size === "lg" ? 8.6 : 7.4;
  const pad = size === "lg" ? 46 : 34;

  const truncate = (s: string, max: number) =>
    s.length > max ? s.slice(0, max - 1) + "…" : s;
  const nameMax = size === "lg" ? 22 : 17;

  const chipW = (m: ConstellationMember) => {
    const name = truncate(m.display_name, nameMax);
    const label = sourceLabel(m.source_id);
    // left inset for the dot (chipH*0.8) + right padding, plus text estimate.
    return Math.max(104, Math.round(Math.max(name.length, label.length + 1) * charW) + chipH + 18);
  };

  const maxChipW = Math.max(...members.map(chipW), 96);
  // radius sized so chips on the circle don't collide
  const circumferenceNeed = (maxChipW + 24) * Math.max(n, 1);
  const R =
    n <= 1 ? 0 : Math.max(size === "lg" ? 150 : 96, circumferenceNeed / (2 * Math.PI));

  const cx = R + maxChipW / 2 + pad;
  const cy = R + chipH / 2 + pad + (size === "lg" ? 14 : 8);
  const W = 2 * cx;
  const H = 2 * cy;

  const pos = new Map<string, { x: number; y: number; w: number }>();
  members.forEach((m, i) => {
    const angle = -Math.PI / 2 + (i * 2 * Math.PI) / Math.max(n, 1);
    const x = n <= 1 ? cx : cx + R * Math.cos(angle);
    const y = n <= 1 ? cy : cy + R * Math.sin(angle);
    pos.set(m.id, { x, y, w: chipW(m) });
  });

  const line = (aId: string, bId: string) => {
    const a = pos.get(aId);
    const b = pos.get(bId);
    if (!a || !b) return null;
    return { x1: a.x, y1: a.y, x2: b.x, y2: b.y };
  };

  return (
    <svg
      className="constellation"
      viewBox={`0 0 ${W} ${H}`}
      width="100%"
      style={{ maxWidth: W, height: "auto", display: "block" }}
      role="img"
      aria-label={`Cross-source identity constellation of ${n} records`}
    >
      {/* approved connectors (behind nodes) */}
      {edges.map((e, i) => {
        const l = line(e.a_id, e.b_id);
        if (!l) return null;
        return (
          <line
            key={`a-${i}`}
            x1={l.x1}
            y1={l.y1}
            x2={l.x2}
            y2={l.y2}
            stroke="var(--connector)"
            strokeWidth={2}
          />
        );
      })}
      {/* escalated connectors: dashed amber */}
      {escalated.map((e, i) => {
        const l = line(e.a_id, e.b_id);
        if (!l) return null;
        return (
          <line
            key={`e-${i}`}
            x1={l.x1}
            y1={l.y1}
            x2={l.x2}
            y2={l.y2}
            stroke={e.homonym_trap ? "var(--homonym)" : "var(--escalated)"}
            strokeWidth={2}
            strokeDasharray="4 4"
          >
            <title>
              {e.homonym_trap
                ? `Escalated — homonym trap (${e.homonym_trap})`
                : "Escalated to curator queue"}
            </title>
          </line>
        );
      })}
      {/* nodes */}
      {members.map((m) => {
        const p = pos.get(m.id)!;
        const w = p.w;
        const x = p.x - w / 2;
        const y = p.y - chipH / 2;
        const node = (
          <g className="node-chip">
            <title>{`${m.display_name} — ${sourceLabel(m.source_id)}`}</title>
            <rect
              x={x}
              y={y}
              width={w}
              height={chipH}
              rx={chipH / 2}
              fill="var(--surface)"
              stroke="var(--hair-strong)"
              strokeWidth={1}
            />
            <circle cx={x + chipH / 2} cy={p.y} r={chipH * 0.2} fill={sourceColor(m.source_id)} />
            <text
              x={x + chipH * 0.8}
              y={p.y - (size === "lg" ? 4 : 3)}
              fontSize={size === "lg" ? 9 : 8}
              fill="var(--muted)"
              style={{ textTransform: "uppercase", letterSpacing: "0.06em" }}
            >
              {sourceLabel(m.source_id)}
            </text>
            <text
              x={x + chipH * 0.8}
              y={p.y + (size === "lg" ? 11 : 9)}
              fontSize={size === "lg" ? 13 : 11}
              fontWeight={600}
              fill="var(--ink)"
            >
              {truncate(m.display_name, nameMax)}
            </text>
          </g>
        );
        return linkNodes ? (
          <Link key={m.id} href={`/rulers/${encodeURIComponent(m.id)}`}>
            {node}
          </Link>
        ) : (
          <g key={m.id}>{node}</g>
        );
      })}
    </svg>
  );
}
