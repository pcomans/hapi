# Extraction prompt for Dodson & Hilton Brief Lives — Seizers of the Two Lands (Dyn 12 MK proper)

Pass this to **three** independent Claude Code subagents in parallel. Each writes JSONL to a distinct filename (`agent-{a|b|c}-seizers.jsonl`) under the agent directory (default `<source_dir>/raw/`). `merge.py` majority-votes across all chunk batches by `agent-{tag}-*.jsonl` glob.

---

You are extracting structured royal-family-member rows from OCR'd Brief Lives entries of Dodson & Hilton (2004) *The Complete Royal Families of Ancient Egypt*, 1st ed. hardback (Thames & Hudson).

## Inputs

One OCR chunk file covering D&H's chapter 2 "Seizers of the Two Lands" Brief Lives sub-block (12th Dynasty, the Middle Kingdom proper — Amenemhat I → Sobkneferu and their dense royal-family prosopography):

1. `<repo_root>/pipeline/pipeline/authority/sources/dodson-hilton-queens/raw/chunk-p88-p91.md` — printed pp. 96–99, physical PDF pp. 88–91. Includes a trailing `### Unplaced` sub-block.

## Output

Write JSONL to `<agent_dir>/agent-{a|b|c}-seizers.jsonl`, where `<agent_dir>` defaults to `<source_dir>/raw/` (gitignored via `raw/agent-*.jsonl`). One JSON object per line, no preamble, no code fences.

## Task

Every Brief Lives entry gets one row. Entries begin with a bold name (`**Name**` upright for males, `***Name***` italic for females — this is D&H's typographic convention for sex) followed by role codes in parentheses, then a 1–3 sentence prose paragraph. Read the chunk in order and preserve every entry. The chunk also contains a trailing `### Unplaced` sub-heading under which D&H lists entries they cannot confidently place in the 12th-Dynasty family tree; rows beneath that heading take `unplaced: true`.

## Schema

```json
{
  "dh_id": "<D&H's bold name-with-disambiguator verbatim>",
  "name": "<same string as dh_id>",
  "alt_names": [],
  "roles": ["<role code 1>", "<role code 2>", "..."],
  "sex": "female",
  "spouse_names": [],
  "father_name": null,
  "mother_name": null,
  "children_names": [],
  "dynasty": 12,
  "sub_period": "Seizers of the Two Lands",
  "unplaced": false,
  "notes": "<full prose paragraph verbatim>",
  "source_citation": {"pdf_pages": "88-91", "edition": "Thames & Hudson 2004 hardback"}
}
```

## Field semantics

- **`dh_id`** — D&H's bold name-with-disambiguator exactly as printed in the chunk. Letter suffixes (`A`, `B`, `C`, `Q`) and Roman-numeral disambiguators (`I Weret`, `II Weret`) are part of the id. Lacuna markers inside a name (e.g. `[...]` placeholder, `Name[...]` truncation) are preserved verbatim. Within-chunk duplicate `dh_id`s are an extraction bug — flag any in your final report.

- **`name`** — same string as `dh_id` for this source. Kept separate for cross-source schema parity.

- **`alt_names`** — list of variant name strings D&H records inline in the current entry's own prose (e.g. `"Also known as …"`). Return `[]` when no inline variant is named.

- **`roles`** — list of role-code tokens from the parenthetical after the name. Split on `;` and trim whitespace. Preserve every token verbatim, including trailing hedge modifiers (`?` etc.) and spelled-out role phrases. Never expand or decode a code; Phase A owns the role-code glossary. Unfamiliar codes are preserved as-is (spelled-out long-form role phrases like `"Mistress of All Women"` appear as a single verbatim token in the parenthetical — include them without splitting the phrase internally). Codes observed on prior chunks include: `K`, `KD`, `KDB`, `KM`, `KW`, `KGW`, `GW`, `KSis`, `KSon`, `KSonB`, `EKSon`, `EKSonB`, `1KSonB`, `HPH`, `HPM`, `SPP`, `HPA`, `GWA`, `Ador`, `GM`, `MULE`, `MoH`, `Genmo`, `Exec`, `ExecH2L`, `L2L`, `M2L`, `GBW`, `Fanbearer`, `Nomarch`, `King of Hittites`, `King of Mitanni`, `Viz`, `PH`, `GS`, plus hedged forms like `KW?`. This chunk may introduce codes never seen before — preserve them verbatim and list novel tokens in your final report.

- **`sex`** — `"male"` if the entry is typographically `**Name**` (upright bold), `"female"` if `***Name***` (bold italic). Confirm with prose pronouns (`"he/his/son of"` vs `"she/her/daughter of"`) as tiebreaker only when the typography is ambiguous in the OCR.

- **`spouse_names`** — list of spouse names from `"wife of X"`, `"husband of Y"`, `"married Z"`, `"consort of W"` phrases in the current entry's own prose. Hedges are preserved verbatim inside the string (e.g. `"NAME (probably)"`, `"NAME (possibly)"`). Empty list when the prose names no specific spouse; in particular, when D&H's prose names the spouse as `"an unknown king"` or otherwise unresolvable, emit `[]` rather than inventing a placeholder — Phase A's authority-matcher treats empty as "no resolvable target". Do NOT conflate parent cross-references (`"daughter of"`, `"son of"`, `"mother of"`) with spouses.

- **`father_name`** / **`mother_name`** — single string from `"son of X"`, `"daughter of Y"`, `"mother NAME"` / `"father NAME"` prose in the current entry itself. `null` when the prose either doesn't name the parent at all OR names the parent only as anonymous/unresolvable (e.g. `"an unknown king"`). Hedges on a **named** parent (`"probably"`, `"possibly"`) are preserved verbatim inside the string (e.g. `"NAME (probable)"`, `"NAME (possibly)"`).

- **`children_names`** — list of children named in the current entry's own prose (e.g. `"mother of A and B"`, `"father of C"`, `"wife of A and mother of B"`). Do NOT do cross-entry inference for this chunk: if the prose of the current entry does not name a child, the list is empty even when another entry's prose names the current entry as a parent.

- **`dynasty`** — integer `12` for every row in this chunk. D&H groups the entire 12th Dynasty under this sub-section, including the earliest-12th-Dynasty ancestor rows (Senwosret A, Neferet I, Neferitatjenen) that arguably straddle late Dyn 11 / early Dyn 12; D&H's placement is the authoritative assignment for this source.

- **`sub_period`** — string, exactly `"Seizers of the Two Lands"` on every row.

- **`unplaced`** — `true` for entries appearing under the `### Unplaced` sub-heading at the end of the chunk. `false` for every entry appearing above that heading.

- **`notes`** — the full prose paragraph for the entry, verbatim, single-line-joined. Preserve museum locations (Cairo Museum, British Museum, Metropolitan Museum, Berlin, Tübingen, Louvre, Tonbridge, Munich, New York, etc.), tomb IDs (`Dahshur tomb L.LV`, `Dahshur tomb 2`, `Pyramid II`/`III`/`IV`/`VIII`/`IX`, Hawara-South), pyramid / mortuary-complex references (Lahun, Lisht, Dahshur, Hawara, Serabit el-Khadim, Medinet Maadi), catalogue numbers (`CM CG52975-9`, `MMA 16.1.5,8`, `MMA 31.10.8`, `CM CG52641`), named papyri / stelae / statue-bases, and D&H's hedges (`probably`, `possibly`, `perhaps`, `conceivably`). Trim leading / trailing whitespace. Do NOT summarise, editorialise, or add scope commentary.

- **`source_citation`** — fixed literal `{"pdf_pages": "88-91", "edition": "Thames & Hudson 2004 hardback"}` on every row.

## Abstract parsing rules (no per-row answer enumeration)

- **Non-regnal vs regnal names.** A bare name with a trailing single-letter capital suffix (`A`, `B`, `C`, `Q`) is D&H's per-family-tree disambiguator for a non-regnal individual. A name with a Roman-numeral suffix (`I`, `II`, `III`, `IV`) is the regnal form of a pharaoh's name (e.g. `AMENEMHAT II`, `SENWOSRET III`) and appears in the Brief Lives only as a cross-reference in other entries' prose, not as its own Brief Lives entry. Emit rows for letter-suffixed individuals; do NOT emit rows for Roman-numeral kings referenced in someone else's prose.
- **Non-regnal names with embedded Roman-numeral disambiguators.** Some non-regnal queens carry a Roman-numeral suffix to disambiguate homonyms (e.g. `Khnemetneferhedjet I Weret`, `Khnemetneferhedjet II Weret`, `Neferu III`, `Neferet I`, `Neferet II`). These ARE their own Brief Lives entries — tell them apart from regnal-king references by whether the individual has their own bold entry at the start of a paragraph. If the Roman-numeral name appears in bold at the start of an entry, it's a row.
- **Lacuna-prefixed or lacuna-containing names.** Names like `[...]12A`, `[...]12B`, `Khnemet[...]`, `Nensed[...]`, `Sit[...]JA` appear in this chunk. Preserve the brackets / ellipsis verbatim as part of `dh_id`.
- **Spelled-out role phrases in the parenthetical.** Occasionally D&H spells a role out long-form in parentheses instead of using an abbreviation (e.g. `(Mistress of All Women)`). Keep the long-form phrase as a single verbatim role token — do not try to abbreviate it.
- **Hedged attributions.** D&H's role-code hedges (`?`) and prose hedges (`possibly`, `probably`, `perhaps`, `conceivably`) are preserved verbatim — on roles inside the parenthetical, hedges attach to the code token; on relationships inside the prose, hedges attach to the name string.

## Sort order

Alphabetical by `dh_id`, case-insensitive, within each `unplaced` bin. The merge step handles the final placed-then-unplaced ordering; you may emit rows in reading order.

## Expected row count

Count the bold-name entries in the chunk (placed + under the `### Unplaced` sub-heading) before writing. Agents should NOT invent rows to meet an expected count — if the count looks anomalous, flag it in your final report.

## Output

Write the JSONL. In your final response, report:
1. Total row count and the placed/unplaced split.
2. Any within-chunk duplicate `dh_id`s (extraction bug if present — flag immediately).
3. Any novel role-code tokens you preserved verbatim (tokens not in the prior-chunk list above).
4. Anything anomalous in the OCR (entry that didn't fit the template, unclear bold-vs-italic typography, ambiguous parental clause, unresolvable lacuna interpretation).

Under 120 words.
