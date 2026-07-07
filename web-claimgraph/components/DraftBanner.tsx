import { getMeta } from "@/lib/queries";

/**
 * Surfaces the reviewer provenance honestly. When the graph was built with the
 * deterministic policy (no live reviewer), this is a DRAFT and says so loudly — it must
 * be impossible to mistake draft data for the live-reviewed graph. When a live reviewer
 * decided the matches, it names the model.
 */
export function DraftBanner() {
  const meta = getMeta();
  // Live-reviewed graph: no banner. (Provenance still shown on the About page.)
  if (meta.reviewer === "llm") return null;
  return (
    <div className="banner">
      <span>⚠</span>
      <div>
        <strong>Draft data.</strong> These links were drawn by the fallback rule set, not checked by
        a reviewer. The records and citations are real; the links themselves are placeholders until
        the graph is rebuilt with a reviewer.
      </div>
    </div>
  );
}
