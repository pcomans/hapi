# Extraction prompt for Claude Code subagents

Pass this to **three** independent Claude Code subagents in parallel (general-purpose). Each agent writes its JSONL output to a distinct filename. The three outputs are then merged by `merge.py` via majority vote.

The prompt below is verbatim; the only per-agent substitution is the output-file suffix (`-a`, `-b`, `-c`).

---

You are extracting the Argead-bridge rulers (Alexander III → Philip III Arrhidaios → Alexander IV) from Hölbl 2001, *A History of the Ptolemaic Empire* (Routledge, English translation of the 1994 German original). The target is the **Appendix** (printed pp. 318–353), specifically the opening three reign banners covering **332–310 BCE**. Everything from the `INTERREGNUM // Ptolemy as Satrap` banner onwards is **OUT OF SCOPE** — those rulers (Interregnum, Ptolemy I Soter, etc.) belong to the Ptolemaic dynasty and will be extracted from a different source.

**Input**: one OCR chunk file at `<repo_root>/pipeline/pipeline/authority/sources/holbl-2001-argead/raw/chunk-p349-p351.md`. Use absolute paths when invoking the Read tool.

**Output**: write your final JSONL to `<agent_dir>/agent-{a|b|c}.jsonl`, where `<agent_dir>` is passed to `merge.py --agent-dir` (default `<source_dir>/raw/`; gitignored via the `raw/agent-*.jsonl` pattern). One JSON object per line, no preamble, no code fences.

**Schema** — one row per Argead reign banner in Hölbl's Appendix:

```json
{
  "holbl_id": "argead.01",
  "kind": "ruler",
  "display": "Alexander the Great",
  "greek_form": null,
  "alternative_reading": null,
  "prenomen": null,
  "start_year": -332,
  "end_year": -323,
  "approximate": false,
  "uncertainty_plus_years": null,
  "dynasty": null,
  "page": 349,
  "note": "…",
  "source_citation": {"pdf_pages": "349-351", "edition": "Routledge 2001"}
}
```

## `holbl_id` — fixed three-row sequence

| `holbl_id`   | `display`               | Hölbl banner (verbatim, rotated-90° left margin)    |
|--------------|-------------------------|-----------------------------------------------------|
| `argead.01`  | `Alexander the Great`   | `ALEXANDER THE GREAT`                               |
| `argead.02`  | `Philip III Arrhidaios` | `PHILIP III ARRHIDAIOS // Ptolemy as Satrap`        |
| `argead.03`  | `Alexander IV`          | `ALEXANDER IV // Ptolemy as Satrap`                 |

Emit exactly these three rows in this order. Do NOT emit rows for `INTERREGNUM // Ptolemy as Satrap` or `PTOLEMY I SOTER` — they are out of scope for this source (Hölbl covers them elsewhere; the Ptolemaic rulers have a dedicated extraction path).

## Per-field rules

- `kind`: always `"ruler"`.
- `display`: the anglicised rendering in the table above. Hölbl's Appendix prints the names ALL-CAPS in the rotated banner; we use Title Case for `display` and preserve the all-caps banner wording only in `note` where it aids cross-referencing.
- `greek_form`, `alternative_reading`, `prenomen`, `uncertainty_plus_years`, `dynasty`: **always null** for this source. Hölbl's Appendix does not print Greek forms, alternative readings, Egyptian prenomina, uncertainty ranges, or dynasty labels in the banner cells. (Dynasty is null because the Argead kings sit between the 31st Dynasty and the Ptolemaic dynasty; Hölbl does not number this bridge.)
- `start_year`, `end_year`: negative integers (BCE). Rules:
  - `argead.01` Alexander the Great: `start_year = -332` (invasion / accession as pharaoh, end of 332), `end_year = -323` (death at Babylon, 10 June 323).
  - `argead.02` Philip III Arrhidaios: `start_year = -323` (acknowledged as king at the Babylon division of empire), `end_year = -317` (Autumn 317 murder by Kassandros' faction).
  - `argead.03` Alexander IV: `start_year = -317` (nominal accession following Philip III's murder), `end_year = -310` (Hölbl prints `310/09` — use the earlier boundary per the compound-date rule below).
- `approximate`: **always false**. Hölbl's Appendix gives these reign boundaries without `c.` / `?` / `??` hedges.
- `page`: physical PDF page where the reign banner begins — `349` for `argead.01` and `argead.02`, `350` for `argead.03`.
- `note`: one to three sentences of verbatim context from the banner cells (invasion of Egypt, Babylon division, murder clause). Include the exact banner wording as printed in the rotated margin, e.g. `"Hölbl banner: 'ALEXANDER THE GREAT'."`. Quote Hölbl's own date-hedges (e.g. `310/09`) when you explain the `end_year` choice. Stay under ~50 words per note.
- `source_citation`: fixed literal `{"pdf_pages": "349-351", "edition": "Routledge 2001"}` on every row. This is the chunk's full range, not per-row.

## Compound-date rule (`310/09`)

Hölbl writes the year of Alexander IV's murder as `310/09`, meaning "310 or 309 BCE depending on calendar convention". Use the **earlier boundary** (`-310`) for `end_year`. This keeps the convention deterministic and matches our handling of other `NNN/NN` compound dates in Phase-0 sources.

## Sort order

By `holbl_id` ascending (lexical sort works because the sequence is always `argead.01`, `argead.02`, `argead.03`).

## Expected row count

Exactly **3**.

## Output

Final JSONL at the designated path. In your response message, give a one-line summary stating how many rows you wrote plus any anomalies. Under 80 words.
