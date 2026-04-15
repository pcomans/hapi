# Extraction prompt for Claude Code subagents

Pass this to **three** independent Claude Code subagents in parallel (general-purpose). Each agent writes its JSONL output to a distinct filename. The three outputs are then merged by `merge.py` via majority vote.

The prompt below is verbatim; the only per-agent substitution is the output-file suffix (`-a`, `-b`, `-c`).

---

You are extracting structured king data from Kitchen 1996, *The Third Intermediate Period in Egypt (1100–650 BC)*, 3rd ed. (Aris & Phillips). The target is **Part VI Section I — Dates of Kings**, specifically **Tables 1, 3, and 4** (Table 2 is deliberately skipped — it gives alternative dates for the same Dyn 21 kings already captured in Table 1).

**Input**: one OCR chunk file at `<repo_root>/pipeline/pipeline/authority/sources/kitchen-tipe/raw/chunk-p240-p243.md`. Use absolute paths when invoking the Read tool.

**Output**: write your final JSONL to `<agent_dir>/agent-{a|b|c}.jsonl`, where `<agent_dir>` is passed to `merge.py --agent-dir` (default `<source_dir>/raw/` (gitignored via the `raw/agent-*.jsonl` pattern)). One JSON object per line, no preamble, no code fences.

**Schema** — one row per king Kitchen lists in Tables 1, 3, 4:

```json
{
  "kitchen_id": "22.03",
  "dynasty": 22,
  "sequence_in_dynasty": 3,
  "name": "Osorkon I",
  "prenomen": "Sekhemkheperre Setepenre",
  "start_bce": -924,
  "end_bce": -889,
  "length_of_reign_years": 35,
  "approximate": false,
  "polity": "Tanis",
  "concurrent_with_kings": [],
  "notes_from_kitchen": null,
  "source_citation": {"pdf_pages": "240-243", "edition": "Aris & Phillips 3rd ed. 1996"}
}
```

## `kitchen_id` stream prefixes (exact)

One stream per (dynasty, sub-line). Emit rows in stream order, `NN` zero-padded two-digit starting from `01`:

| Prefix  | `dynasty` | Stream content                                                       | Polity              |
|---------|-----------|----------------------------------------------------------------------|---------------------|
| `20`    | 20        | Ramesses XI (Table 1 opening row)                                    | `"Tanis"`           |
| `21`    | 21        | Table 1 left column, *Kings* group: Smendes I → Psusennes II         | `"Tanis"`           |
| `21H`   | 21        | Table 1 right column, HPA group: Herihor → Psusennes 'III'           | `"Theban (HPA)"`    |
| `22`    | 22        | Table 3 22nd Dynasty block — all kings                               | `"Tanis"` except Harsiese A → `"Theban (HPA)"` |
| `23`    | 23        | Table 3 23rd Dynasty block                                            | `"Leontopolis"`     |
| `24E`   | 24        | Table 4 *Early Saite Princes* group (pre-Dyn-24)                     | `"Sais (Mā)"`       |
| `24`    | 24        | Table 4 *24th Dynasty*: Tefnakht I, Bakenranef                       | `"Sais"`            |
| `24P`   | 24        | Table 4 *Proto-Saite Dynasty*: Ammeris → Necho I                     | `"Sais"`            |
| `25`    | 25        | Table 4 *25th (Nubian) Dynasty*: Alara → Tantamani                   | `"Nubia (Napata)"`  |
| `26`    | 26        | Table 4 *26th Dynasty*: Psammetichus I → Psammetichus III            | `"Sais"`            |

The `dynasty` integer follows the table (HPAs → 21; Early-Saite Princes → 24; Proto-Saite → 24). `sequence_in_dynasty` is the integer `NN`.

## Parsing rules

**Table 1 row format**: left-column kings carry `(length y)` e.g. `"Smendes I (26 y)"`. Right-column HPAs same, e.g. `"Pinudjem I, hp (15 y)"`. Most Table-1 rows do NOT carry a prenomen inline — leave `prenomen: null` for those. Two HPA rows carry parenthetical annotations (`"hp"`, `"'kg'"`) which are Kitchen's own shorthand for "high priest" and "self-declared king"; preserve as `notes_from_kitchen: "hp"` and `"'kg'"` respectively. Amenemope's line `"Amenemope (9 y; 2, co-rgt)"` sets `length_of_reign_years: 9` and `notes_from_kitchen: "2 yrs co-rgt"`. Osochor's line `"Osochor (6 y; 3, co-rgt)"` analogously: `6`, `"3 yrs co-rgt"`.

**Tables 3 and 4 row format**: `"{start}–{end}: {Name}, {Prenomen} ({length} y)"` or a variant thereof. Examples:

- `"945–924: Shoshenq I, Hedjkheperre Setepenre (21 y)"` → `name:"Shoshenq I"`, `prenomen:"Hedjkheperre Setepenre"`, `start_bce:-945`, `end_bce:-924`, `length_of_reign_years:21`, `approximate:false`.
- `"c. 890: Shoshenq II, Heqakheperre Setepenre (x yrs; co-rgt only)"` → `name:"Shoshenq II"`, `prenomen:"Heqakheperre Setepenre"`, `start_bce:-890`, `end_bce:-890` (single-point date), `length_of_reign_years: null`, `approximate: true`, `notes_from_kitchen: "co-rgt only"`.
- `"889–874: Takeloth I, [Prenomen unknown] (15 y)"` → `prenomen:"[Prenomen unknown]"` verbatim (do NOT null this out — downstream knows to treat the bracketed phrase as "unknown").
- `"(720–715): Shoshenq VI, Wasneterre Setepenre (c. 5 y??); existence, doubtful."` → `start_bce:-720`, `end_bce:-715`, `length_of_reign_years:5`, `approximate:true`, `notes_from_kitchen:"existence, doubtful"`.
- `"731–720: Iuput II, [Prenomen unknown] (c. 11/16 y?) (or 715)"` → `length_of_reign_years: 11` (take the lower value of `11/16`), `approximate: true`, `notes_from_kitchen: "11/16 y alternative; end date alternative 715"`.
- `"818–793: Pedubast I, Usimare Setepenamun (25 y). [Start of Dyn. 23.]"` → treat `[Start of Dyn. 23.]` as a structural marker, not a note; omit from `notes_from_kitchen`.

**Approximate marker**: set `approximate: true` when ANY of the following appear on the row:

- The date is prefixed with `"c."` (e.g. `"c. 890: …"`).
- The length is hedged with `(c. N y)` or `(c. N y?)` or `(N y??)`.
- Parentheses surround the whole date range `(720–715)` indicating Kitchen's own uncertainty.
- Name is parenthesised like `(Shoshenq VI?)` or `(Iuput II)` in the alternative-dates position — Kitchen uses this for speculative kings.

Otherwise `approximate: false`.

**Length parsing**: `"(21 y)"` → 21. `"(x yrs)"` or `"(x y)"` → null (x = unknown). `"(c. 15 y?)"` → 15, approximate. `"(y'); existence, doubtful."` → note only, length null. `"(8 y, in S. Egypt)"` → 8, `notes_from_kitchen: "in S. Egypt"`.

**Name with Roman-numeral disambiguator**: preserve Kitchen's form verbatim including quotes. `"Psusennes 'III'"` stays `"Psusennes 'III'"`. `"Shoshenq (II)"` stays `"Shoshenq (II)"`.

## Concurrency

Emit `concurrent_with_kings: []` for **every row, without exception**. This field is deterministically recomputed in `fix_rows.py` from `start_bce` / `end_bce` as an interval-overlap calculation — LLM agents doing interval arithmetic in parallel produced inconsistent results and polluted the merge with spurious disagreements. Do not hand-populate overlaps from Table 1's side-by-side layout. Whatever you emit here will be overwritten downstream; emitting `[]` keeps the three-agent merge clean.

## `source_citation`

Every row has `source_citation: {"pdf_pages": "240-243", "edition": "Aris & Phillips 3rd ed. 1996"}` — the chunk's full range, not per-row.

## Sort order

By dynasty ascending, within dynasty by prefix-alphabetical (`21` before `21H`; `24E` before `24` before `24P`), then by `sequence_in_dynasty` ascending.

## Expected row count

~55–65 rows. Our first calibration target is 60.

## Output

Final JSONL at the designated path. In your response message, give a one-line summary stating how many rows you wrote plus any anomalies. Under 80 words.
