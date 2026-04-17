# Extraction prompt for Claude Code subagents

Pass this to **three** independent Claude Code subagents in parallel (general-purpose). Each agent writes its JSONL output to a distinct filename. The three outputs are then merged by `merge.py` via majority vote.

The prompt below is verbatim; the only per-agent substitution is the output-file suffix (`-a`, `-b`, `-c`).

---

You are extracting structured king data from Hölbl 2001, *A History of the Ptolemaic Empire* (Routledge 2001 English translation of *Geschichte des Ptolemäerreiches* 1994). The target is the **Appendix — Overview of the events discussed in the history of the Ptolemaic kingdom**, specifically the rubric-block covering the three Argead-dynasty rulers of Egypt: **Alexander the Great**, **Philip III Arrhidaios** (Ptolemy as Satrap), **Alexander IV** (Ptolemy as Satrap).

The rubric label **INTERREGNUM** (310/09–306 BCE) is NOT extracted — it is not an Argead ruler, it is the interval in which Ptolemy ruled Egypt de facto without an Argead king overhead. Stop at the end of Alexander IV's rubric. Do not extract Ptolemy I Soter's rubric (which begins at 306 BCE with his assumption of the royal title); that ruler is covered by other sources (`sources/pharaoh-se/`, `sources/wikipedia-ptolemaic/`).

**Input**: one OCR chunk file at `<repo_root>/pipeline/pipeline/authority/sources/holbl-2001-argead/raw/chunk-p348-p351.md`. Use absolute paths when invoking the Read tool.

**Output**: write your final JSONL to `<agent_dir>/agent-{a|b|c}.jsonl`, where `<agent_dir>` is the `raw/` directory alongside this prompt (default `<source_dir>/raw/`, gitignored via the `raw/*` pattern with a `!raw/.gitkeep` exception). One JSON object per line, no preamble, no code fences.

**Schema** — one row per Argead ruler:

```json
{
  "holbl_id": "argead.02",
  "name": "Philip III Arrhidaios",
  "alt_names": ["Philip Arrhidaeus", "Philip III"],
  "start_bce": -323,
  "end_bce": -317,
  "approximate": false,
  "polity": "Argead",
  "notes_from_holbl": "Ptolemy as Satrap of Egypt through this reign. Feeble-minded half-brother of Alexander the Great, acknowledged as joint king with the pregnant Roxane's possible son.",
  "source_citation": {"pdf_pages": "348-351", "edition": "Routledge 2001"}
}
```

## Expected rows (exactly 3, emit in this order)

| `holbl_id`   | Hölbl rubric            | Approximate years | `name` field value          |
|--------------|-------------------------|-------------------|-----------------------------|
| `argead.01`  | ALEXANDER THE GREAT     | 332–323           | `"Alexander the Great"`     |
| `argead.02`  | PHILIP III ARRHIDAIOS   | 323–317           | `"Philip III Arrhidaios"`   |
| `argead.03`  | ALEXANDER IV            | 317–310/09        | `"Alexander IV"`            |

If your row count is not exactly 3, re-read the rubric-block carefully. The three rulers are demarcated by the vertically-rotated capitalised labels in the leftmost column of the appendix table.

## Parsing rules

**`name` field.** Use the exact anglicised spelling shown in the Hölbl rubric label for each ruler. Hölbl writes "ALEXANDER THE GREAT" / "PHILIP III ARRHIDAIOS" / "ALEXANDER IV" in the rubric column; case-normalise to title case: `"Alexander the Great"`, `"Philip III Arrhidaios"`, `"Alexander IV"`. Preserve Hölbl's `Arrhidaios` spelling — do not silently anglicise to `Arrhidaeus`.

**`alt_names` field.** Populated for every row. The set of other common spellings a cross-reference might use:

- `argead.01` → `["Alexander III", "Alexander III of Macedon"]`. (Alexander the Great IS Alexander III; the Macedonian numbering is the alt name.)
- `argead.02` → `["Philip Arrhidaeus", "Philip III"]`. (The Latinised `Arrhidaeus` is the more common English form; Hölbl's translator uses the Greek-faithful `Arrhidaios`.)
- `argead.03` → `["Alexander IV of Macedon", "Alexander IV Aegus"]`. (`Alexander IV Aegus` / `Alexander Aegus` is sometimes used in older scholarship; not universal.)

**`start_bce` / `end_bce` fields.** Negative integers (1 BCE → `-1`). Hölbl's leftmost year column is the BCE year (e.g. `332` → `-332`). Rules:

- `argead.01`: start = -332 (Hölbl's rubric opens at 332 with "Alexander's invasion of Egypt"), end = -323 (last rubric year; "10 June 323: Death of Alexander").
- `argead.02`: start = -323 (Philip III's rubric opens at 323 with the "Division of empire at Babylon"), end = -317 ("Murder of Philip III Arrhidaios" entry under the 317 year label).
- `argead.03`: start = -317 (Alexander IV's rubric opens at 317), end = -310 (picked as the earlier of Hölbl's split-year `310/09`, matching where the "Murder of Alexander IV by Kassandros" entry sits immediately after the `310/09` year label).

**`approximate` field.** Boolean.

- `argead.01` → `false` (unhedged single years).
- `argead.02` → `false` (unhedged single years).
- `argead.03` → `true` (Hölbl writes the end as `310/09`, a split-year; the `/` counts as a hedge by the same convention used elsewhere in this project's Phase 0 work).

**`polity` field.** Always `"Argead"` for all three rows. This is the dynasty name (the Argead dynasty of Macedon) and is the label that distinguishes these rulers from the Ptolemaic rulers covered by adjacent authorities. Do not emit `"Macedon"`, `"Macedonian"`, or `"Greek"` — those are broader than what this source attests.

**`notes_from_holbl` field.** Free-text string distilled from Hölbl's rubric block. Capture, concisely:

- For `argead.01`: Alexander the Great's Egyptian accession after his 332 invasion; his visit to the Ammoneion / Siwa oracle; his foundation of Alexandria; his departure in spring 331; his death in Babylon 10 June 323. (Keep the note under ~2 sentences; this is a brief-summary field, not a retranscription of the rubric.)
- For `argead.02`: Hölbl's characterisation of Philip III Arrhidaios as the "feeble-minded half-brother of Alexander" acknowledged as joint king with the pregnant Roxane's possible son; Ptolemy as Satrap of Egypt through this reign; murdered 317.
- For `argead.03`: Alexander IV born 323 (the posthumous son of Alexander the Great and Roxane); joint king with Philip III Arrhidaios until Philip's murder in 317; thereafter sole nominal king; murdered 310/09 by Kassandros; Ptolemy as Satrap throughout.

Preserve Hölbl's own wording (e.g. `feeble-minded half-brother`, `Ptolemy as Satrap`) when it is scholar-legible and not judgmental beyond Hölbl's own usage. Do not introduce facts Hölbl's table does not state.

**`source_citation` field.** Every row: `{"pdf_pages": "348-351", "edition": "Routledge 2001"}` — the chunk's full range, not per-row.

## Sort order

By `holbl_id` ascending (`argead.01`, `argead.02`, `argead.03`). The numeric suffix follows the order the rubric block presents the three rulers.

## Expected row count

Exactly 3. If you emit 2 or 4 rows, stop and re-read the rubric-block: the three Argead rulers are demarcated by the rotated all-caps labels `ALEXANDER THE GREAT`, `PHILIP III ARRHIDAIOS`, `ALEXANDER IV` in the leftmost margin. `INTERREGNUM` is NOT a ruler. `PTOLEMY I SOTER` is NOT in this extract.

## Output

Final JSONL at the designated path. In your response message, give a one-line summary stating how many rows you wrote plus any anomalies. Under 80 words.
