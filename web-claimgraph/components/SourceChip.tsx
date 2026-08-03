import { sourceColor, sourceLabel } from "@/lib/ui";

export function SourceChip({ source, className }: { source: string; className?: string }) {
  return (
    <span className={`chip ${className ?? ""}`}>
      <span className="dot" style={{ ["--c" as string]: sourceColor(source) }} />
      {sourceLabel(source)}
    </span>
  );
}

export function SourceDot({ source, size = 10 }: { source: string; size?: number }) {
  return (
    <span
      className="dot"
      style={{
        ["--c" as string]: sourceColor(source),
        width: size,
        height: size,
        display: "inline-block",
        borderRadius: "50%",
        background: sourceColor(source),
      }}
    />
  );
}
