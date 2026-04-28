# Extraction prompt for Claude Code subagents

Pass this to **three** independent Claude Code subagents (sonnet model) in parallel. Each agent writes its JSONL output to a distinct filename. The three outputs are then merged by `merge.py` via majority vote.

The prompt below is verbatim; the only per-agent substitution is the output-file suffix (`-a`, `-b`, `-c`).

---

You are extracting structured king data from Jürgen von Beckerath (1997), *Chronologie des pharaonischen Ägypten*, MÄS 46 (von Zabern). The target is **Anhang A — *Chronologische Übersicht über die Geschichte Altägyptens*** plus the immediately following ***Supplement zu A*** (full Egyptian titularies for Dyn 19–23).

**Input**: one OCR chunk file at `<repo_root>/pipeline/pipeline/authority/sources/beckerath-1997-chronologie/raw/chunk-p105-p109.md`. Use absolute paths when invoking the Read tool.

**Output**: write your final JSONL to `<agent_dir>/agent-{a|b|c}.jsonl`, where `<agent_dir>` is passed to `merge.py --agent-dir` (default `<source_dir>/raw/`, gitignored). One JSON object per line, no preamble, no code fences.

**Schema** — one row per king listed in the Übersicht. Pull supplementary `prenomen` from the *Supplement zu A* tail and merge into the corresponding Dyn 19–23 row keyed by `name`.

```json
{
  "beckerath_id": "01.01",
  "dynasty": 1,
  "sub_line": null,
  "sequence_in_dynasty": 1,
  "name": "Menes",
  "egyptian_titulary": "Hor Aha",
  "egyptian_titulary_kind": "horus_name",
  "prenomen": null,
  "start_bce_high": -3032,
  "start_bce_low": -2982,
  "end_bce_high": -3000,
  "end_bce_low": -2950,
  "start_approximate": true,
  "end_approximate": true,
  "period": "Frühzeit",
  "notes_from_beckerath": null,
  "source_citation": {"pdf_pages": "105-109", "edition": "MÄS 46, von Zabern 1997"}
}
```

## `beckerath_id`

`{dyn:02}.{NN:02}` — zero-padded two-digit dynasty, dot, zero-padded two-digit sequence within the dynasty. Examples: `00.01` (Dyn 0 anchor), `01.01` (Menes), `22.11` (an Oberägyptische-Linie king continues main-line numbering — sub_line does NOT restart sequence). The predynastic anchor is `00.01`.

## `dynasty` and `sub_line`

- `dynasty` = integer 0..31. Beckerath's heading `1. Dynastie` → 1; `16. Dynastie (Hyksos-Vasallen, gleichzeitig mit Dynastie 15)` → 16; `0. Dynastie` → 0.
- `sub_line` = nullable string. `null` for the main line. Set to `"Oberägyptische Linie"` for Dyn 22 OAL kings (heading `Oberägyptische Linie (ca. 870–730)`, kings Har-si-ëset → Ini). Set to `"Hohepriester"` for the two HPA names that appear in the *Supplement zu A* tail paragraph for Dyn 21 (Pi-nodjem I and Pusennes — read the paragraph that begins `Den Königstitel führen außerdem in der 21. Dynastie die Hohenpriester …`). No other sub_lines exist.

## `sequence_in_dynasty`

1-indexed continuous integer within the dynasty, regardless of `sub_line`. The first Dyn 22 OAL king continues numbering after the last main-line Dyn 22 king.

## `name` and `egyptian_titulary`

- `name` = the **Greek/manethonic** form Beckerath uses, including Roman-numeral suffixes (`Schoschenq I.`, `Tuthmosis IV.`, `Ramses II.`, `Bokchoris`). Preserve diacritics and `.` punctuation verbatim.
- `egyptian_titulary` = the parenthetical Egyptian-language royal name. Examples: `Hor Aha` (Menes), `Chufu` (Cheops), `Nefer-cheprurê wa-en-rê` (Akhenaten), `Sesonchis` (Schoschenq I — note: Sesonchis is itself Greek; Beckerath uses parentheticals heterogeneously). When Beckerath's row has the form `Schoschenq I. (Sesonchis)`, the parenthetical IS `Sesonchis` — preserve. Null when no parenthetical.
- `egyptian_titulary_kind`:
  - `"horus_name"` — parenthetical begins with `Hor` (e.g. `Hor Aha`, `Hor Djer`).
  - `"prenomen"` — parenthetical ends with `-rê` / `-rî` (cartouche-style throne name: `Nefer-cheprurê wa-en-rê`, `User-maat-rê`, `Men-cheper-rê`).
  - `"nomen"` — neither pattern matches; the parenthetical is a name-form (e.g. `Heti?`, `Tosorthros`, `Sesonchis`, `Sabakon`).
  - `"mixed"` — the row gives BOTH a Horus/throne name AND a nomen separated by `,` or `/` (Dyn 19–23 *Supplement* format).
  - `null` — no parenthetical.

## `prenomen`

Populate ONLY when the *Supplement zu A* gives an extra Thronname for a Dyn 19–23 king on top of the Übersicht parenthetical. The Supplement format is `<NameInGreek>: <Thronname>, <Eigenname>`. Extract the Thronname into `prenomen` and merge into the existing row keyed by `name`. Do not create separate rows for Supplement entries.

## BCE date fields

Beckerath writes most rows as `<start_high>/<start_low>–<end_high>/<end_low>`, e.g. `3032/2982–3000/2950`. The slash separates Beckerath's high (older) and low (younger) alternative endpoints. Both must be preserved.

- `start_bce_high`, `start_bce_low`, `end_bce_high`, `end_bce_low`: negative integers, individually nullable.
- When the row has only one slash-pair endpoint (e.g. `1186/85–1183/82`), the right side is a 2-digit short form for the year following the high — `1186/85` means `-1186 / -1185`, `1183/82` means `-1183 / -1182`. **Always expand to full 4-digit BCE.**
- When Beckerath gives a single endpoint (no slash), populate both `_high` and `_low` with the same value.
- When the row has only one endpoint at all (e.g. `vor ca. 746` or `ca. 880`), populate the corresponding pair and set the other pair to null.

## `start_approximate` / `end_approximate`

Boolean flags. **True** when the corresponding endpoint is qualified by any of: `ca.`, `etwa`, `vor`, `nach`, `um`, `ungefähr`, or hedges with `?`. Also true when the entire row is in a section Beckerath introduces with `etwa N Jahre`. **False** when the endpoint is a bare number.

Examples:
- `3032/2982–3000/2950` (Dyn 1, sits inside the dynasty heading `(etwa 3032/2982–2853/2803)`) → `start_approximate: true, end_approximate: true` (the whole Dyn 1 sits under "etwa").
- `945/944–924/923` (Schoschenq I) — bare slash-pair, no `ca.` / `etwa` — but the dynasty heading is `(946/945–ca.735)` so individual rows here are `false, false` unless the row itself has hedges.
- `vor ca. 746` (Kaschta) → `start_approximate: true, start_high: null, start_low: null, end_approximate: true, end_high: -746, end_low: -746, notes_from_beckerath: "vor ca. 746"`.
- `664–ca.655` (Tanot-amun) → `start_approximate: false, end_approximate: true, start_high: -664, start_low: -664, end_high: -655, end_low: -655`.
- `ca. 837–798 (785?)` (Schoschenq III) → `start_approximate: true, end_approximate: false, start_high: -837, start_low: -837, end_high: -798, end_low: -798, notes_from_beckerath: "alternative end 785"`.
- `Herbst 1337–1333` (Semench-ka-rê) → `start_approximate: false, end_approximate: false, start_high: -1337, start_low: -1337, end_high: -1333, end_low: -1333, notes_from_beckerath: "Herbst 1337"`.
- `31.5.1279/79.3.8.1213–1203` (Ramses II accession-with-day) → numeric endpoints `-1279` start and `-1213` / `-1203` end; record full date in notes: `"Antritt 31.5.1279"`. (Beckerath gives some 19th–20th Dyn rows with day.month.year coronation dates; preserve the day/month form in `notes_from_beckerath`.)

**Dyn 0** (`0. Dynastie`, value `ungefähr 150 Jahre`) → all four `*_bce_*` are null, both approximate flags true, `notes_from_beckerath: "ungefähr 150 Jahre"`.

## `period`

One of (verbatim):
`"Vorgeschichte"`, `"Frühzeit"`, `"Altes Reich"`, `"I. Zwischenzeit"`, `"Mittleres Reich"`, `"II. Zwischenzeit"`, `"Neues Reich"`, `"III. Zwischenzeit"`, `"Spätzeit"`.

Drives from Beckerath's italicised section headings within Anhang A. `"Vorgeschichte"` is shorthand for the full `VORGESCHICHTE (PRÄDYNASTISCHE ZEIT)` heading.

## Post-processor annotations (`<!-- period: ... -->`, `<!-- dynasty-context: ... -->`)

The chunk file is run through `postprocess.py` AFTER OCR and BEFORE you read it. The post-processor injects two HTML-comment annotations to make persistent context visible at every point in the document:

- `<!-- period: <SectionTitleCase> -->` appears immediately AFTER each dynasty heading. Treat it as authoritative for the `period` field of every row in that dynasty's span. Use the value from the most recent `<!-- period: ... -->` comment as the `period` of all subsequent rows up to the next dynasty heading.
- `<!-- dynasty-context: <full-dynasty-heading-text> -->` appears AFTER a `## Book pNNN` page boundary that lands inside a dynasty's span. Treat it as the dynasty heading for the rows that follow on the new page (just as if Beckerath had repeated the heading at the top of the page). Apply ALL per-heading rules (the `etwa`/`ca.` qualifier, parenthetical placement annotations like `"in Theben"`, etc.) as if the heading appeared inline.

These comments do not introduce new schema semantics — they make the existing per-heading rules unambiguous when the heading text is on a previous page or far above the row you are extracting. If the comments are absent (older runs of the OCR pipeline), fall back to scanning upward for the nearest section/dynasty heading.

## `notes_from_beckerath`

Free text. Examples:
- `"Mitregent"` (co-regency annotation Beckerath places after a name).
- `"in Sais"`, `"in Bubastis/Tanis"`, `"in Leontopolis"`, `"in Thebes, etwa 845–1550"` (parenthetical placement annotations on dynasty headings — copy onto every row that follows).
- `"Antritt 31.5.1279"`, `"Herbst 1337"` (day-month date prefixes preserved verbatim).
- `"Gegenkönig der 3 vorigen"` (on Seth Per-ib-sen and Hor-Seth Cha-sechemui; see Dyn 2 rule).
- `"vor ca. 746"`, `"alternative end 785"`, `"alternative ende 712"` (mixed-certainty annotations).
- `"Manetho ?7 Tage"` (a Dyn 7 marker Beckerath gives without numeric data).
- `"Nachfolger regieren in Napata (Nubien)"` (Tanot-amun's tail).

Null when Beckerath gives no annotation.

## Dyn 2 *Gegenkönig* rule

Beckerath prints `Gegenkönig der 3 vorigen: Seth Per-ib-sen / Hor-Seth Cha-sechemui` as a composite annotation. Extract as **two rows** — one for `Seth Per-ib-sen`, one for `Hor-Seth Cha-sechemui` — both with `notes_from_beckerath: "Gegenkönig der 3 vorigen"` and both inheriting the bracketed BCE range Beckerath assigns to that block.

## Co-regent queen rule (Mitregentin with own titulary → separate row)

A queen co-regent printed with her own throne name in parentheses is a SEPARATE row in the dynasty's sequence. Two structural shapes Beckerath uses:

1. **Indented `mit Kgin. <name> (<titulary>)` line** placed under a king's row. The leading 4-space indent + `mit Kgin.` token signals a co-regent annotation. When followed by a parenthetical `(<titulary>)` (the queen's own throne or birth name), emit her as the next sequence row in the dynasty.

2. **Chained `<king> und Kgin. <name> (<titulary>)`** on the same line as the king. The `und Kgin.` token + parenthetical titulary signals two distinct rows: the king first, the queen as next sequence.

For both shapes:
- `name` is `"Kgin. <queen-name>"` (preserve Beckerath's `Kgin.` honorific verbatim).
- `egyptian_titulary` is the parenthetical content; `egyptian_titulary_kind` is whatever the `(<titulary>)` represents (use the same heuristic as for kings: `prenomen` if the form ends `-rê` or `-ka-rê` style throne-name suffix; `nomen` if Greek-alias-style; `mixed` otherwise).
- BCE range INHERITS from the immediately-preceding king's row (the queen co-rules during her king's reign).
- `notes_from_beckerath` is `"Mitregentin von <king-name>"` (German for "co-regent of <king>").

Discriminator: she gets her own row IF AND ONLY IF the `mit Kgin.` / `und Kgin.` is followed by a parenthetical `(<titulary>)`. If `mit Kgin.` or `Mitregent` appears without a titulary parenthetical, fold into the king's `notes_from_beckerath` instead.

## OCR-duplicate detection (one king, two rows)

If a king appears in two consecutive (or near-consecutive) lines within the same dynasty with overlapping or conflicting date ranges, it is an OCR artifact — NOT a separate row. Indicator: identical `name` field in two lines, where one has an incomplete date (`<start>–` with no end) and the other has a complete chronologically-coherent date that fits the dynasty's other entries.

Resolution: emit ONLY the chronologically-coherent occurrence. Verify by checking that the surviving entry's start date is ≥ the previous king's end date AND its end date ≤ the following king's start date — if so, it is the correct entry.

## `source_citation`

Every row has `source_citation: {"pdf_pages": "105-109", "edition": "MÄS 46, von Zabern 1997"}`.

## Sort order

By `dynasty` ascending, within dynasty by `sub_line` (null first, then alphabetical), then by `sequence_in_dynasty` ascending.

## Expected row count

**172 rows** (locked by `tests/test_sources_beckerath_1997_chronologie.py::test_row_count`). The lower-than-naive count reflects how Beckerath actually structures Anhang A: dynasties 7, 8, 9/10, 13, 14, 16, and 17 each get a single placeholder row carrying a regnal-count annotation (`"18 Könige"` etc.) rather than enumerated kings, and the Dyn 21 Hohepriester sub-line contributes only 2 names from the *Supplement zu A* tail paragraph (not a full parallel column). Aim for 172; if your count diverges, the merge step will surface the discrepancy on the per-`beckerath_id` join.

## Output

Final JSONL at the designated path. In your response message, give a one-line summary stating how many rows you wrote plus any anomalies. Under 80 words.
