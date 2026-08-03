import { SOURCE_SHORT } from "./types";

/** CSS custom-property reference for a source's validated categorical hue. */
export function sourceColor(sourceId: string): string {
  return `var(--src-${sourceId})`;
}

export function sourceLabel(sourceId: string): string {
  return SOURCE_SHORT[sourceId] ?? sourceId;
}

export function reignLabel(start: number | null, end: number | null): string | null {
  const bce = (y: number) => `${Math.abs(y)} BCE`;
  if (start != null && end != null) return `${bce(start)} – ${bce(end)}`;
  if (start != null) return `from ${bce(start)}`;
  if (end != null) return `to ${bce(end)}`;
  return null;
}

export function dynastyLabel(n: number | null, label: string | null): string {
  if (label) return label;
  if (n != null) return `Dynasty ${n}`;
  return "—";
}

// Friendly display name for a reviewer model id (raw slugs like "z-ai/glm-5.2" read badly).
const MODEL_LABELS: Record<string, string> = {
  "z-ai/glm-5.2": "GLM 5.2",
  "claude-sonnet-5": "Claude Sonnet 5",
  "claude-opus-4-8": "Claude Opus 4.8",
};
export function modelLabel(model: string | null): string {
  if (!model) return "an AI reviewer";
  return MODEL_LABELS[model] ?? model.split("/").pop() ?? model;
}
