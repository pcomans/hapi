# Sweep review notes - 2026

Reviewed `README.md`, `transcribe.md`, `merge-disagreements.txt`, `reconciled.jsonl`, and Kitchen 1996 PDF pp. 240-243 (printed pp. 465-468). No prior `reviewer-notes-*.md` files were present before this sweep.

Spot-checked rows against the PDF: `20.01`, `21.01`, `21.04`, `21H.01`, `21H.03`, `21H.06`, `22.01`, `22.03`, `22.08`, `23.02`, `23.07`, `24E.04`, `24.01`, `24P.04`, `25.03`, `25.06`, `26.01`, `26.06`.

## P1

None found in the sampled rows.

## P2

- Missing Table 1 Renaissance-era North row. Kitchen's Preferred Dates table gives `1080-1069: Smendes in N (11 y)` under the same Renaissance Era North/South block from which this source extracts `Herihor`, `Piankh`, and `Pinudjem I` on the South side. `reconciled.jsonl` has `20.01` Ramesses XI and the South/HPA entries, but no corresponding `Smendes in N` row or explicit exclusion rationale. Since the source scope says Table 1 is included and preserves the parallel Tanite/Theban structure, this is an asymmetric omission and also leaves early concurrency incomplete.

- `21H.06` encodes a knowingly impossible chronology in the primary date fields: `start_bce: -1046`, `end_bce: -1056`, `length_of_reign_years: 1`. Kitchen's printed line is indeed `1046-1056: Djed-Khons-ef-ankh (1 y?)`, which is internally contradictory and almost certainly a table typo, but the current representation makes the normalized fields violate their own semantics. A safer authority representation would set the normalized endpoint to the intended `-1045` and preserve the printed `1046-1056` in a verbatim/source-note field, rather than requiring downstream consumers to special-case the note.

- Several `polity` values are presented as table-derived when they are not. Table 3 only labels "22nd Dynasty" and "23rd Dynasty"; it does not state Tanis, Bubastis, Leontopolis, or Theban for most rows. The README says section headings drive `polity`, but `Leontopolis` for all `23.*` rows is explicitly modern consensus / prose-derived, and `Tanis` for all non-Harsiese `22.*` rows is a simplification. These are not necessarily historically wrong, but they are uncited imports relative to the claimed table-only extraction scope.

## P3

- Provenance wording is stale or contradictory for this retrospective audit. `README.md` and `transcribe.md` claim an `egyptologist-reviewer` subagent already walked `merge-disagreements.txt`; the sweep assignment says this source was merged without that subagent. The files should distinguish the prior LLM/main-agent override pass from this sweep review so future consumers do not overestimate validation status.

- Harsiese (`22.06`) is probably acceptable as a Theban co-regent in wider Kitchen context, but the README overstates the table evidence: the printed Table 3 line says `co-rgt only`, not "at Thebes". If retaining `polity: "Theban (HPA)"`, cite the prose section or soften the claim.
