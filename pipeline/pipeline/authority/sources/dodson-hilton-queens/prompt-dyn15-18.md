# Extraction prompt for Dodson & Hilton Brief Lives — Dynasties 15 to early 18

Pass this to **three** independent Claude Code subagents in parallel. Each writes JSONL to a distinct filename (`agent-{a|b|c}-dyn15-18.jsonl`) under the agent directory (`<source_dir>/raw/`). `merge.py --carry-forward` majority-votes the three files.

**Method.** As in the Of Kings and Priests chunk (`prompt-ofkingsandpriests.md` § "Method deviation"): the agents read a small sub-PDF directly with the `Read` tool, with no OCR intermediate. The sub-PDF is cut from the full book by `slice_source.py dyn15-18`, which pins both the book and the sub-PDF by SHA-256.

**No prose is extracted.** Since #308, the `notes` field is no longer part of the schema, and this chunk never produces it. Only names, role codes, kinship and dynasty are recorded.

---

You are extracting structured royal-family rows from Dodson & Hilton (2004), *The Complete Royal Families of Ancient Egypt*, 1st edition hardback (Thames & Hudson).

## Input

`<repo_root>/pipeline/pipeline/authority/sources/dodson-hilton-queens/raw/source-dyn15-18.pdf`. It has 7 pages. Open it with `Read(file_path="<that path>", pages="1-7")`.

| Sub-PDF page | Printed page | What it is | Use |
|---|---|---|---|
| 1 | 114 | Section opening, *Rulers of Foreign Countries* | Its **Royal Succession** box only |
| 2 | 115 | *Rulers of Foreign Countries*: Brief Lives | Extract every entry |
| 3 | 116 | Section opening, *The Southern Kingdom* | Its **Royal Succession** box only |
| 4 | 120 | *The Southern Kingdom*: Brief Lives, including an *Unplaced* sub-block | Extract every entry |
| 5 | 122 | Section opening, *The Taosids* | Its **Royal Succession** box only |
| 6–7 | 128–129 | *The Taosids*: Brief Lives, including an *Unplaced* sub-block | Extract every entry |

**What not to extract:**
- On pages 1, 3 and 5, read only the Royal Succession box. It lists which kings belong to which dynasty in that section, and you need it for the `dynasty` field.
- Nothing else on those pages is extracted: not the Historical Background, the Royal Family narrative, the captions or the genealogical charts.
- On pages 2, 4, 6 and 7, extract only the Brief Lives entries. Each Brief Lives block ends with a row of decorative bullets (`●●●●…`), and nothing after it is extracted.
- On every Brief Lives page, the block starts at the first bold headword after the `Brief Lives ●●●●…` header. On page 6 that header sits below the narrative text, which is not extracted.

## Output

Write JSONL to `<source_dir>/raw/agent-{a|b|c}-dyn15-18.jsonl`: one JSON object per line, with no preamble and no code fences. There is one row per Brief Lives entry, in printed reading order: column by column, page by page. (Order does not affect the merge.)

## Schema

```json
{
  "dh_id": "<the bold headword verbatim>",
  "name": "<same string as dh_id>",
  "alt_names": [],
  "roles": ["<role code>", "..."],
  "sex": "female",
  "spouse_names": [],
  "father_name": null,
  "mother_name": null,
  "children_names": [],
  "dynasty": null,
  "sub_period": "<section title, see below>",
  "unplaced": false,
  "source_citation": {"pdf_pages": "<see below>", "edition": "Thames & Hudson 2004 hardback"}
}
```

## Field semantics

- **`dh_id`**: the entry's bold headword, exactly as printed.
  - Keep disambiguators as part of the ID: Roman numerals, Latin letters and `Q`.
  - Keep hyphenated compound forms as printed.
  - Keep square-bracket restorations and lacunae, such as `[...]` with a following number and letter, or a name with a restored part in brackets. Each bracket and ellipsis character stays as printed.
  - A `(?)` or `?` printed after the headword is part of `dh_id`, not a role.
  - Do not add or drop a letter suffix.

- **`name`**: the same string as `dh_id`.

- **`alt_names`**: names the entry's own text gives as another name *of this person*, titlecased.
  - Only these phrasings are triggers: "Name also appears as X", "also known as X" and "later king as X". No other phrasing makes an alt name.
  - A king or other person merely mentioned is not an alt name.
  - Use an empty list when there is none.

- **`roles`**: the tokens in the parentheses after the headword.
  - Split on `;`, trim the whitespace, and keep each token verbatim, including any `?`.
  - Keep a spelled-out phrase (e.g. a title in words) as one token.
  - Use an empty list when there are no parentheses.
  - Never expand or decode a code.

- **`sex`**:
  - `"female"` if the headword is bold italic; `"male"` if bold upright (each Brief Lives block's own key states this convention).
  - Only when the typography is unclear: decide by the entry's kinship words (daughter/son, wife/husband, sister/brother, mother/father), then by its role codes.
  - If the typography and the kinship words disagree, use the kinship words and name the entry in your final report's anomalies.

- **`spouse_names`**: the persons the entry names as this person's spouse ("wife of X", "sister-wife of X", "husband of X", "married to X").
  - Hedges and alternatives (the rules below apply to every kinship field):
    - A **hedge** is any word that marks a relation as uncertain: "perhaps", "probably", "probable", "possibly", "possible", "presumably", "likely" and the like ("Possible wife of X", "perhaps a wife of X"). Keep the person, with the printed qualifier lowercased in parentheses after the name: `"X (possible)"`, `"X (perhaps)"`. Copy the printed word; do not normalise it to another one.
    - **Hedge scope.** A hedge at the start, before the relation word ("Probable daughter of X and Y"), qualifies every name that relation introduces. A hedge inside a list ("son of X and perhaps Y", "mother of X and perhaps a wife of Y") qualifies only the name it immediately precedes.
    - Hedges on facts other than kinship (ownership, dating, burial) do not matter here.
    - An **alternative** offers two or more relation types for one person ("mother, wife or daughter of X"). It goes in no kinship field.
    - A relation the entry itself calls mistaken or refuted goes in no kinship field, so it does not count toward `dynasty` either. A relation the entry still offers as possible is a hedge, not a refutation.

- **`father_name` / `mother_name`**: a parent the entry names ("son of X", "daughter of X and Y"). "Mother of X" is the reverse relation and goes in `children_names`.
  - Each parent field is decided on its own: a named parent beside an unnamed one still goes in its field.
  - A named parent goes in the field of that parent's sex, as the entry's own text shows (a king or "father" is male; a queen or "mother" is female). With two parents ("daughter of X and Y"), the male is the father and the female the mother. A parent whose sex the entry does not show goes in neither field; name the entry in your report's anomalies.
  - Use `null` when no parent is named, or when the parent is unnamed ("a nobleman", "an unknown king").

- **`children_names`**: children the entry names ("mother of X", "father of X").
  - Hedges follow the hedge and hedge-scope rules above.
  - Use an empty list when there are none.
  - Kinship beyond parent, spouse and child is not recorded in any field: sister/brother, grandmother, grandfather, in-laws.

- **`dynasty`**: an integer, or `null`. Set it from the section's Royal Succession box:
  - Count distinct dynasty numbers in the box: it may split a dynasty into "part 1" and "part 2", and only the number counts.
  1. If the box lists a single dynasty number, every row of that section takes it, *Unplaced* rows included.
  2. Otherwise, take the names in this row's `spouse_names`, `father_name`, `mother_name` and `children_names` that carry **no hedge**. Keep those that match a king in this section's box: same name and numeral once titlecased (each hyphen-separated element titlecased, e.g. `"Name-Name II"`), exactly. Ignore every other name, including kings of other sections. If the kept kings all belong to one dynasty number, the row takes it.
  3. If the kept kings belong to more than one dynasty number, or none is kept, the row takes `null`.
  - Do not use the charts, the narrative or outside knowledge for this field.

- **`sub_period`**: the section title as printed: `"Rulers of Foreign Countries"`, `"The Southern Kingdom"` or `"The Taosids"`.

- **`unplaced`**: `true` for entries under that section's *Unplaced* sub-heading, `false` otherwise.

- **`source_citation.pdf_pages`**: the full book's physical PDF page of the section's Brief Lives:
  - `"105"` for Rulers of Foreign Countries;
  - `"110"` for The Southern Kingdom;
  - `"118-119"` for The Taosids.

## Parsing hazards

These describe D&H's conventions in general; a given section may have none of them.

- **Repeated names.** Entries on one base name carry different letters or numerals. Every suffix is a separate person, so emit one row per printed headword and never merge two.
- **Compound names.** A hyphenated compound is one headword; do not split it.
- **Bracketed restorations and lacunae.** Copy them exactly. A one-line entry is still an entry.
- **Royal names in capitals.** The boxes print kings in BOLD CAPITALS; in kinship fields, write them titlecased with their numeral, e.g. `"Name II"`.
- **Headwords and kings.** A row always describes the person its entry describes, never a king of the same name.

## Final report

After writing the JSONL, return one line (under 80 words):

```
agent-<X>-dyn15-18: <count> rows (<per-section counts>); <M>/<F> male/female; <anomalies or "none">
```

## Rights

Only factual data is recorded: names, role codes, kinship, dynasty and page citations. D&H's prose, notes, captions and charts are not reproduced. The book PDF and the sub-PDF are not committed (ADR-017; `raw/*` is gitignored).
