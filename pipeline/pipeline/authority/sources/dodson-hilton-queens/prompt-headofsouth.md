# Extraction prompt for Dodson & Hilton Brief Lives — Head of the South (Dyn 11 transition)

Pass this to **three** independent Claude Code subagents in parallel. Each writes JSONL to a distinct filename (`agent-{a|b|c}-headofsouth.jsonl`) under the agent directory (default `<source_dir>/raw/`). `merge.py` majority-votes across all chunk batches by `agent-{tag}-*.jsonl` glob.

---

You are extracting structured royal-family-member rows from OCR'd Brief Lives entries of Dodson & Hilton (2004) *The Complete Royal Families of Ancient Egypt*, 1st ed. hardback (Thames & Hudson).

## Inputs

One OCR chunk file covering D&H's chapter 2 "Head of the South" Brief Lives sub-block (11th Dynasty transition, the unification of Upper Egypt under the Theban kings that closes the First Intermediate Period):

1. `<repo_root>/pipeline/pipeline/authority/sources/dodson-hilton-queens/raw/chunk-p81-p82.md` — printed pp. 88–89, physical PDF pp. 81–82.

## Output

Write JSONL to `<agent_dir>/agent-{a|b|c}-headofsouth.jsonl`, where `<agent_dir>` defaults to `<source_dir>/raw/` (gitignored via `raw/agent-*.jsonl`). One JSON object per line, no preamble, no code fences.

## Task

Every Brief Lives entry gets one row. Entries begin with a bold name (`**Name**` upright for males, `***Name***` italic for females — this is D&H's typographic convention for sex) followed by role codes in parentheses, then a 1–3 sentence prose paragraph. Read the chunk in order and preserve every entry. The chunk also contains a trailing `### Unplaced` sub-heading under which D&H lists any entry they cannot confidently place in the 11th-Dynasty family tree; rows beneath that heading take `unplaced: true`.

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
  "dynasty": 11,
  "sub_period": "The Head of the South",
  "unplaced": false,
  "notes": "<full prose paragraph verbatim>",
  "source_citation": {"pdf_pages": "81-82", "edition": "Thames & Hudson 2004 hardback"}
}
```

## Field semantics

- **`dh_id`** — D&H's bold name-with-disambiguator exactly as printed in the chunk. Letter suffixes (e.g. a trailing single capital letter) and Roman-numeral disambiguators are part of the id. No lacuna-prefixed names appear in this chunk and no compound-form name-change slashes. If you observe any `dh_id` twice within your own output, flag it in your final report.

- **`name`** — same string as `dh_id` for this source. Kept separate for cross-source schema parity.

- **`alt_names`** — list of variant name strings D&H records inline in the current entry's own prose (e.g. `"Also known as …"`). Empty list when D&H's prose for the entry lists no alternative. This chunk's Brief Lives does not include inline `alt_names` phrases for any entry; expect `[]` for every row.

- **`roles`** — list of role-code tokens from the parenthetical after the name. Split on `;` and trim whitespace. Preserve every token verbatim, including trailing modifiers like `?` (which encode D&H's hedge on whether the subject actually held that role). Never expand a code to long-form, never decode; Phase A owns the role-code glossary. Unfamiliar codes (i.e. codes not on the cross-chunk list below) are preserved as-is. Codes observed on prior chunks (Power, Amarna, Ramesside) include: `K`, `KD`, `KDB`, `KM`, `KW`, `KGW`, `GW`, `KSis`, `KSon`, `KSonB`, `EKSon`, `1KSonB`, `HPH`, `HPM`, `SPP`, `HPA`, `GWA`, `Ador`, `GM`, `MULE`, `MoH`, `Genmo`, `Exec`, `ExecH2L`, `L2L`, `M2L`, `GBW`, `Fanbearer`, `Nomarch`, `King of Hittites`, `King of Mitanni`, `Viz`, plus hedged forms like `KW?`. This chunk may introduce codes never seen before — preserve them verbatim.

- **`sex`** — `"male"` if the entry is typographically `**Name**` (upright bold), `"female"` if `***Name***` (bold italic). Confirm with prose pronouns (`"he/his/son of"` vs `"she/her/daughter of"`) as tiebreaker only when the typography is ambiguous in the OCR.

- **`spouse_names`** — list of spouse names from `"wife of X"`, `"husband of Y"`, `"married Z"`, `"consort of W"` phrases in the current entry's own prose. Hedges are preserved verbatim inside the string (e.g. if D&H writes `"Possibly a wife of NAME"`, emit `["NAME (possibly)"]` — the `(possibly)` suffix captures D&H's hedge). Empty list when the prose names no specific spouse; in particular, when D&H's prose says the spouse is **unknown**, anonymous, or simply "a king" without identification, emit `[]` rather than inventing an entity name — Phase A treats empty as "no resolvable target", which is the correct semantics for unidentifiable relatives. Do NOT conflate parent cross-references (`"daughter of"`, `"son of"`, `"mother of"`) with spouses.

- **`father_name`** / **`mother_name`** — single string from `"son of X"`, `"daughter of Y"`, `"mother NAME"` / `"father NAME"` prose in the entry itself. `null` when the prose either doesn't name the parent at all OR names the parent only as "unknown", anonymous, or otherwise unresolvable. Do not invent a placeholder entity (e.g. `"unknown king"`) where D&H's prose offers no specific individual — `null` is the honest encoding and Phase A handles it correctly. D&H's explicit hedges on a **named** parent (e.g. `"probably"`, `"possibly"`) are preserved verbatim inside the string (e.g. `"NAME (possibly)"`).

- **`children_names`** — list of children named in the current entry's own prose (e.g. `"mother of A and B"`, `"father of C"`). Do NOT do cross-entry inference for this chunk: if the prose of the current entry does not name a child, the list is empty even when another entry's prose names the current entry as a parent. (Cross-entry inference is reserved for specific symmetric cases in other chunks; this chunk's prose is dense enough that the straight verbatim rule suffices.)

- **`dynasty`** — integer `11` for every row in this chunk. D&H groups the entire 11th Dynasty under this sub-section regardless of whether a given individual belongs to the late First Intermediate Period or the early Middle Kingdom phase of the dynasty.

- **`sub_period`** — string, exactly `"The Head of the South"` on every row.

- **`unplaced`** — `true` for entries appearing under the `### Unplaced` sub-heading at the end of the chunk. `false` for every entry appearing above that heading.

- **`notes`** — the full prose paragraph for the entry, verbatim, single-line-joined. Preserve museum locations (Cairo Museum, British Museum, Metropolitan Museum, Moscow, Brussels, Ny Carlsberg, etc.), tomb IDs (`DBXI.N`, `TT-number`), named stela / statue / block references, and D&H's hedges (`probably`, `possibly`, `perhaps`). Trim leading / trailing whitespace. Do NOT summarise, editorialise, or add scope commentary.

- **`source_citation`** — fixed literal `{"pdf_pages": "81-82", "edition": "Thames & Hudson 2004 hardback"}` on every row.

## Abstract parsing rules (no per-row answer enumeration)

- **Non-regnal vs regnal names.** A bare name with a trailing single-letter capital suffix (`A`, `B`, `C`, ...) is D&H's per-family-tree disambiguator for a non-regnal individual. A name with a Roman-numeral suffix (`II`, `III`, `IV`) is the regnal form of a pharaoh's name and appears in the Brief Lives only as a cross-reference in other entries' prose, not as its own Brief Lives entry (even when the regnal-name king is mentioned many times). Emit rows for the letter-suffixed individuals you see; do NOT emit rows for Roman-numeral kings referenced in someone else's prose.
- **Name-disambiguator Roman numerals on non-regnal names.** Occasionally D&H uses Roman-numeral suffixes on non-regnal individuals to disambiguate homonyms (e.g. two women sharing the same given name across different generations). These ARE their own Brief Lives entries — tell them apart from regnal-king references by whether the individual has their own bold `***Name N***` entry in the chunk. If the Roman-numeral name appears in bold at the start of an entry, it's a row; if it appears only inside other entries' prose, it's a cross-reference.
- **Hedged attributions.** D&H's role-code hedges (`?`) and prose hedges (`possibly`, `probably`) are preserved verbatim — on roles inside the parenthetical, hedges attach to the code token; on relationships inside the prose, hedges attach to the name string.

## Sort order

Alphabetical by `dh_id`, case-insensitive, within each `unplaced` bin. The merge step handles the final placed-then-unplaced ordering; you may emit rows in reading order.

## Expected row count

Count the bold-name entries in the chunk (placed + under the `### Unplaced` sub-heading) before writing. If the OCR is well-formed and no entry is OCR-mangled, the count is uniquely determined by the chunk. Agents should NOT invent rows to meet an expected count — if the count differs from prior Brief Lives chunks' expectation, flag it in your final report.

## Output

Write the JSONL. In your final response, report:
1. Total row count and the placed/unplaced split.
2. Any cross-section duplicate `dh_id`s within your output (a true duplicate within a single chunk is an extraction bug — flag immediately).
3. Any novel role-code tokens you preserved verbatim (tokens not in the list above).
4. Anything anomalous in the OCR (entry that didn't fit the template, unclear bold-vs-italic typography, ambiguous parental clause).

Under 100 words.
