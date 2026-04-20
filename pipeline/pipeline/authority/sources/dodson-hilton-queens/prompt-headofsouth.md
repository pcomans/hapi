# Extraction prompt for Dodson & Hilton Brief Lives — Head of the South (Dyn 11 transition)

Pass this to **three** independent Claude Code subagents in parallel. Each writes JSONL to a distinct filename (`agent-{a|b|c}-headofsouth.jsonl`) under the agent directory (default `<source_dir>/raw/`). `merge.py` majority-votes across all chunk batches by `agent-{tag}-*.jsonl` glob.

---

You are extracting structured royal-family-member rows from OCR'd Brief Lives entries of Dodson & Hilton (2004) *The Complete Royal Families of Ancient Egypt*, 1st ed. hardback (Thames & Hudson).

## Inputs

One OCR chunk file covering D&H's chapter 2 "Head of the South" Brief Lives sub-block (11th Dynasty transition, the unification of Upper Egypt under the Theban kings that closes the First Intermediate Period):

1. `<repo_root>/pipeline/pipeline/authority/sources/dodson-hilton-queens/raw/chunk-p81-p82.md` — printed pp. 88–89, physical PDF pp. 81–82. 13 entries expected (12 placed + 1 unplaced).

## Output

Write JSONL to `<agent_dir>/agent-{a|b|c}-headofsouth.jsonl`, where `<agent_dir>` defaults to `<source_dir>/raw/` (gitignored via `raw/agent-*.jsonl`). One JSON object per line, no preamble, no code fences.

## Task

Every Brief Lives entry gets one row. Entries begin with a bold name (`**Name**` upright for males, `***Name***` italic for females — this is the D&H typographic convention for sex) followed by role codes in parentheses, then a 1–3 sentence prose paragraph. Read the chunk in order and preserve every entry.

## Schema

```json
{
  "dh_id": "Neferu II",
  "name": "Neferu II",
  "alt_names": [],
  "roles": ["KW", "KD"],
  "sex": "female",
  "spouse_names": ["Mentuhotep II"],
  "father_name": "Inyotef III",
  "mother_name": "Iah",
  "children_names": [],
  "dynasty": 11,
  "sub_period": "The Head of the South",
  "unplaced": false,
  "notes": "Daughter of Inyotef III and Iah, and wife of Mentuhotep II; buried in tomb TT319 at Deir el-Bahari.",
  "source_citation": {"pdf_pages": "81-82", "edition": "Thames & Hudson 2004 hardback"}
}
```

## Field semantics

- **`dh_id`** — D&H's name-with-disambiguator exactly as printed in bold. Letter suffixes (`Inyotef A`, `Neferu I`, `Neferu II`) are part of the id. The chunk contains no lacuna-prefixed names and no compound-form name-change slashes.

  **Duplicates within this chunk**: the chunk is expected to have no cross-section duplicates (the "Head of the South" is one sub_period in isolation — other Ch 2 sub-blocks are extracted in separate PRs). Each `dh_id` appears once within this extract. If you observe any `dh_id` twice, flag it in your final report.

- **`name`** — same string as `dh_id` for this source. Kept separate for cross-source schema parity.

- **`alt_names`** — list of variant name strings D&H records inline. Empty for every entry in this chunk (no inline `"Also known as …"` phrases appear in the source). Return `[]`.

- **`roles`** — list of role-code strings from the parenthetical after the name. Split on `;` with whitespace trimmed. Known codes (carried forward from Ramesside / Amarna / Power chunks): `K`, `KD`, `KDB`, `KM`, `KW`, `KGW`, `KSis`, `KSon`. Additional codes expected in this chunk, preserved verbatim even if new:
  - `PH` — appears on several female wives buried in Deir el-Bahari mortuary complex tombs (Ashayet, Henhenet, Kawit, Kemsit, Sadhe). Do NOT expand the code; keep as `"PH"`.
  - `GS` — appears on Tem (wife of Mentuhotep II). Keep as `"GS"`.
  - `Nomarch` — on Inyotef A (provincial governor, male non-king). Keep verbatim as a single token `"Nomarch"`.

  Preserve code strings verbatim even if unfamiliar — D&H's role-code glossary is a Phase-A concern. For hedged codes like `"(PH; KW?)"` with a question mark inside the parentheses, split as two codes: `["PH", "KW?"]` — the `?` is part of the code string and reflects D&H's authorial hedge on whether the individual actually held that role. Keep it.

- **`sex`** — `"male"` or `"female"`:
  - **male**: `Nomarch`, `KSon`, `K`; BOLD upright entry rendering (`**Name**`); prose uses `"son of"`, `"he"`, `"his"`.
  - **female**: `KD`, `KDB`, `KM`, `KW`, `KGW`, `KSis`, `PH`, `GS`; BOLD ITALIC entry rendering (`***Name***`); prose uses `"daughter of"`, `"wife of"`, `"mother of"`, `"she"`, `"her"`.
  - In this chunk, the only male entry is `Inyotef A` (Nomarch). All other 12 entries are female (wives, mothers, and daughters of Mentuhotep II and surrounding Dyn-11 transition kings).

- **`spouse_names`** — list of spouse names from `"wife of X"`, `"husband of Y"`. Hedges preserved verbatim in the string (e.g. `"Mentuhotep II (possibly)"`). Empty list when no spouse is named in the prose. Do NOT include cross-reference mentions like `"mother of"` or `"daughter of"` — those fill `mother_name` / `father_name` not `spouse_names`.

- **`father_name`** / **`mother_name`** — single strings from `"son of X"`, `"daughter of Y"`, `"mother Z"` / `"father W"`. `null` when D&H doesn't state the parent. Hedges preserved verbatim.

- **`children_names`** — list of children named in this entry's own prose. The cross-entry-inference rule from chunk 2 is NOT extended to this chunk — every `children_names` list is either empty or populated from names the current entry's own prose explicitly mentions as the subject's children. Example: `Iah`'s entry says "mother of Mentuhotep II and Neferu II" → `children_names: ["Mentuhotep II", "Neferu II"]`. `Tem`'s entry says "mother of Mentuhotep III" → `children_names: ["Mentuhotep III"]`. `Neferu I`'s entry says "Mother of Inyotef II" → `children_names: ["Inyotef II"]`. `Ikui`'s entry says "Mother of Inyotef A" → `children_names: ["Inyotef A"]`. `Imi`'s entry says "Mother of Mentuhotep IV" → `children_names: ["Mentuhotep IV"]`. Entries that say "wife of X" without naming children: `children_names: []`.

- **`dynasty`** — integer `11` for every row in this chunk. (The 11th Dynasty spans both the late First Intermediate Period and the early Middle Kingdom; D&H groups the entire dynasty under this sub_period.)

- **`sub_period`** — string, exactly `"The Head of the South"` on every row.

- **`unplaced`** — `true` only for entries that appear under the `### Unplaced` sub-heading (at least `Neferkayet` on p. 89). `false` for every other entry.

- **`notes`** — the full prose paragraph verbatim, single-line-joined. Preserve museum catalogue locations (`Cairo Museum`, `British Museum`, `Metropolitan Museum of Art`, `Ny Carlsberg`, `Moscow`, `Brussels`), tomb IDs (`DBXI.7`, `DBXI.9`, `DBXI.11`, `DBXI.15`, `DBXI.17`, `TT308`, `TT319`), and named stela / statue / block references (`stela of Tjetji (British Museum)`, `stelae of Tjetji`, `scribe-statue dedicated by Senwosret I`, `block now in the British Museum`, `Karnak king list`). Trim leading / trailing whitespace. Do NOT summarise, editorialise, or add scope commentary.

- **`source_citation`** — fixed literal `{"pdf_pages": "81-82", "edition": "Thames & Hudson 2004 hardback"}` on every row.

## Parsing hazards (Head of the South)

- **`Inyotef A` vs `Inyotef II` vs `Inyotef III`**. `Inyotef A` is the nomarch-father of Mentuhotep I (letter-suffix = non-regnal individual, predynasty-11 in the numbering convention). `Inyotef II` and `Inyotef III` are regnal numerals for kings of the 11th Dynasty and appear ONLY as cross-references in prose (e.g. `"mother of Inyotef II"`), NOT as their own Brief Lives entries in this chunk. Only `Inyotef A` is a row here; do NOT extract `Inyotef II` or `Inyotef III` as entries.
- **`Mentuhotep I/II/III/IV`** appear only as cross-references (husband / son / father of the women listed). No Mentuhotep gets his own Brief Lives entry in this chunk. `Mentuhotep II` is the most-cited spouse. Do NOT extract regnal-name kings as separate rows for this chunk.
- **`Neferu I` vs `Neferu II`**. Two distinct women — `Neferu I` is the *mother of Inyotef II* (her son is named with the epithet "born of Neferu" on several stelae), `Neferu II` is the *wife of Mentuhotep II* and daughter of Inyotef III + Iah. Two separate rows; D&H's Roman-numeral suffix is the disambiguator.
- **`Kawit` and `Kemsit` shared hedging**: D&H lists both with `(PH; KW?)` — the `KW?` hedge is preserved verbatim as the code string `"KW?"`. Do NOT drop the `?`.
- **`Neferkayet` is Unplaced**: she appears under the `### Unplaced` sub-heading on p. 89. `unplaced: true`. D&H says she is "Daughter and wife of unknown kings" — `father_name` and `spouse_names` each carry `"unknown king"` or similar per the prose wording, OR `null` if you judge the phrase "unknown kings" to be too vague to commit to. Per constitutional rule 1 (scholarly traceability), prefer capturing D&H's phrase verbatim over normalizing to `null` — use `father_name: "unknown king"` and `spouse_names: ["unknown king"]`.

## Sort order

Alphabetical by `dh_id`, case-insensitive. Unplaced entries sort after placed entries. Expected order: `Ashayet, Henhenet, Iah, Ikui, Imi, Inyotef A, Kawit, Kemsit, Neferu I, Neferu II, Sadhe, Tem, [Neferkayet unplaced]`.

## Expected row count

**13 rows**: 12 placed (`Ashayet`, `Henhenet`, `Iah`, `Ikui`, `Imi`, `Inyotef A`, `Kawit`, `Kemsit`, `Neferu I`, `Neferu II`, `Sadhe`, `Tem`) + 1 unplaced (`Neferkayet`).

If your row count is below 12 or above 14, re-read the chunk and count entries before writing.

## Output

Write the JSONL. In your final response, report:
1. Total row count and confirmation of the 12 placed + 1 unplaced split.
2. Any cross-section duplicate `dh_id`s (expected: none).
3. Any novel role code beyond `PH`, `GS`, `Nomarch`, `KW?` that you encountered and preserved verbatim.
4. Anything anomalous in the OCR (entry that didn't fit the template, unclear bold-vs-italic typography, ambiguous parental clause).

Under 100 words.
