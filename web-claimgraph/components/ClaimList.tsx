import type { ClaimRow } from "@/lib/queries";
import { PREDICATE_LABEL } from "@/lib/types";

/** Renders a ruler's E13 claims with their documentary provenance (P70i + page). */
export function ClaimList({ claims }: { claims: ClaimRow[] }) {
  return (
    <div className="overflow-x">
      <table className="claims">
        <tbody>
          {claims.map((c) => {
            const page =
              c.cited_page != null
                ? `p. ${c.cited_page}`
                : c.cited_pdf_page
                  ? `pdf ${c.cited_pdf_page}`
                  : null;
            return (
              <tr key={c.id}>
                <td className="pred">
                  {PREDICATE_LABEL[c.predicate] ?? c.predicate}
                  {c.is_variant ? " ·var" : ""}
                </td>
                <td>
                  <span style={{ fontWeight: 550 }}>{c.value_text || "—"}</span>
                  {c.value_translit && (
                    <span className="translit"> · {c.value_translit}</span>
                  )}
                  <div className="prov">
                    {c.scholar_name}
                    {page ? ` · ${page}` : ""}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
