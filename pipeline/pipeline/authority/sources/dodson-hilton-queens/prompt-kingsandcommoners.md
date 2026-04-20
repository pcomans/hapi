# Extraction prompt for Dodson & Hilton Brief Lives — Kings and Commoners (Dyn 13, SIP start)

Pass this to **three** independent Claude Code subagents in parallel. Each writes JSONL to a distinct filename (`agent-{a|b|c}-kingsandcommoners.jsonl`) under the agent directory (default `<source_dir>/raw/`). `merge.py` majority-votes across all chunk batches by `agent-{tag}-*.jsonl` glob.

---

You are extracting structured royal-family-member rows from OCR'd Brief Lives entries of Dodson & Hilton (2004) *The Complete Royal Families of Ancient Egypt*, 1st ed. hardback (Thames & Hudson).

## Inputs

One OCR chunk file covering D&H's chapter 2 "Kings and Commoners" Brief Lives sub-block (13th Dynasty, the start of the Second Intermediate Period):

1. `<repo_root>/pipeline/pipeline/authority/sources/dodson-hilton-queens/raw/chunk-p98-p103.md` — printed pp. 108–113, physical PDF pp. 98–103. Includes a trailing `### Unplaced` sub-block. **Printed page 110 is a full-bleed photograph with zero Brief Lives entries**; the chunk's page-header sequence skips from `## p. 109` to `## p. 111`.

## Output

Write JSONL to `<agent_dir>/agent-{a|b|c}-kingsandcommoners.jsonl`, where `<agent_dir>` defaults to `<source_dir>/raw/` (gitignored via `raw/agent-*.jsonl`). One JSON object per line, no preamble, no code fences.

## Task

Every Brief Lives entry gets one row. Entries begin with a bold name (`**Name**` upright for males, `***Name***` italic for females — this is D&H's typographic convention for sex) followed by role codes in parentheses, then a 1–3 sentence prose paragraph. Read the chunk in order and preserve every entry. The chunk also contains a trailing `### Unplaced` sub-heading; rows beneath that heading take `unplaced: true`.

## Schema

```json
{
  "dh_id": "<D&H's bold name-with-disambiguator verbatim>",
  "name": "<same string as dh_id>",
  "alt_names": [],
  "roles": ["<role code 1>", "<role code 2>", "..."],
  "sex": "male",
  "spouse_names": [],
  "father_name": null,
  "mother_name": null,
  "children_names": [],
  "dynasty": 13,
  "sub_period": "Kings and Commoners",
  "unplaced": false,
  "notes": "<full prose paragraph verbatim>",
  "source_citation": {"pdf_pages": "98-103", "edition": "Thames & Hudson 2004 hardback"}
}
```

## Field semantics

- **`dh_id`** — D&H's bold name-with-disambiguator exactly as printed in the chunk. Letter suffixes (`A`, `B`, `C`, `Q`, `R`) and Roman-numeral disambiguators are part of the id. Lacuna markers inside a name (`[...]`, `Name[...]`, `[Name]`, `Se[...]kare`, `Nen?[...]`) are preserved verbatim. Compound disambiguators like `Iuhetibu B Fendy`, `Haankhef C Ikherneferet`, `Sobkhotep D Miu`, `Sobkhotep E Djadja` preserve the full printed form as `dh_id`. Within-chunk duplicate `dh_id`s are an extraction bug — flag any in your final report.

- **`name`** — same string as `dh_id` for this source.

- **`alt_names`** — list of variant name strings D&H records inline in the current entry's own prose (e.g. `"Also known as …"`). `[]` when no inline variant is named.

- **`roles`** — list of role-code tokens from the parenthetical after the name. Split on `;` and trim whitespace. Preserve every token verbatim, including trailing hedge modifiers (`?` etc.) and spelled-out role phrases. Never expand or decode a code; Phase A owns the role-code glossary. Spelled-out long-form role phrases are preserved as a **single verbatim token** inside the `roles` list — do not split them on spaces. This chunk uses several long-form role tokens (same treatment as `King of Hittites` / `Mistress of All Women` in earlier chunks): `Governor of El-Kab`, `Overseer of the Fields`, `Chief Scribe of the Vizier`, `Elder of the Portal`, `High Steward`, `Attendant of Dog-Keepers`, `Townsman`, `Royal Representative`, `RO`. Codes observed on prior chunks include: `K`, `KD`, `KDB`, `KM`, `KW`, `KGW`, `GW`, `KSis`, `KSon`, `KSonB`, `EKSon`, `EKSonB`, `HPH`, `HPM`, `SPP`, `HPA`, `GWA`, `Ador`, `GM`, `MULE`, `MoH`, `Genmo`, `Exec`, `ExecH2L`, `L2L`, `M2L`, `GBW`, `Fanbearer`, `Nomarch`, `Viz`, `PH`, `GS`, `GF`, `UWC`, `King of Hittites`, `King of Mitanni`, `Mistress of All Women`, plus hedged forms like `KW?`. Entries with an empty parenthetical or no parenthetical at all (e.g. an entry whose header is just `**Name**` followed by prose) get `roles: []`. List any novel role-code tokens in your final report.

- **`sex`** — derive from the role-code parenthetical first, using D&H's legend. The role-code-first rule (new in this prompt) makes the 3-agent vote independently-derivable rather than dependent on typography that may have been synthesised during OCR post-processing:
  - **Female-indicating codes** (any one present → `"female"`): `KW`, `KGW`, `GW`, `GBW`, `KD`, `KDB`, `KM`, `KSis`, `UWC`, `M2L`, `L2L`, `GS`, `GM`, `GWA`, `Ador`, `PH`, `MULE`, `RO`, `Mistress of All Women`, and any `X?` / `X!` hedged variant of the above (e.g. `KW?`).
  - **Male-indicating codes** (any one present → `"male"`): `K`, `KSon`, `KSonB`, `1KSonB`, `EKSon`, `EKSonB`, `KSonN`, `1KSon`, `GF`, `HPH`, `HPM`, `HPA`, `SPP`, `Exec`, `ExecH2L`, `Genmo`, `1Genmo`, `Gen`, `MoH`, `Viz`, `Nomarch`, `Fanbearer`, `Troop Commander`, `Viceroy`, `King of Hittites`, `King of Mitanni`, `Overseer of Treasurers`, `Adjutant of the Chariotry`, `Overseer of the Fields`, `Chief Scribe of the Vizier`, `Elder of the Portal`, `High Steward`, `Attendant of Dog-Keepers`, `Townsman`, `Royal Representative`, `Governor of El-Kab`.
  - **Role-less entries or ambiguous-role entries**: derive from prose-kinship verbs in the current entry's notes. Female: `"wife of"`, `"daughter of"`, `"mother of"`, `"sister of"`, `"niece of"`, `"granddaughter of"`, `"grandmother of"`, `"half-sister of"`, and pronouns `she`/`her`/`hers`. Male: `"husband of"`, `"son of"`, `"father of"`, `"brother of"`, `"nephew of"`, `"grandson of"`, `"grandfather of"`, `"son-in-law of"`, `"step-father of"`, and pronouns `he`/`his`/`him`. If both role-code and prose point to the same answer: emit it. If they disagree: emit the prose-kinship answer and flag the row in your final report as an ambiguity.
  - **Typography (`***Name***` vs `**Name**`) is the tiebreaker only** when both role-code and prose signals are absent or ambiguous. For this chunk's OCR specifically, typography was restored post-hoc by the main-session OCR pipeline from the same role-code + prose signals the agents are deriving from, so it is not an independent signal — use it only as a last-resort tiebreaker.

- **`spouse_names`** — list of spouse names from `"wife of X"`, `"husband of Y"`, `"married Z"`, `"consort of W"` phrases in the current entry's own prose. Hedges preserved verbatim inside the string (e.g. `"NAME (probable)"`, `"NAME (possibly)"`, `"NAME or NAME2 (possible)"`, `"either NAME or NAME2"` — the latter two are common in this chunk because D&H often gives multiple candidate husbands for a possible queen). Empty list when the prose names no specific spouse; **when D&H's prose names the spouse as "an unknown king" or otherwise unresolvable, emit `[]`**. Do NOT conflate parent cross-references (`"daughter of"`, `"son of"`, `"mother of"`) with spouses.

- **`father_name`** / **`mother_name`** — single string from `"son of X"`, `"daughter of Y"`, `"father of Z"`, `"mother NAME"` prose in the current entry itself. `null` when the prose either doesn't name the parent at all OR names the parent only as anonymous/unresolvable (e.g. `"an unknown king"`, `"a king whose prenomen included the syllable 'hotep'"`). Hedges on a **named** parent (`"probably"`, `"possibly"`, `"possible"`, `"probable"`) preserved verbatim inside the string.

- **`children_names`** — list of children named in the current entry's own prose. Do NOT do cross-entry inference for this chunk: if the prose of the current entry does not name a child, the list is empty even when another entry's prose names the current entry as a parent. Hedges preserved verbatim as on the other kinship fields.

- **`dynasty`** — integer `13` for every row in this chunk. D&H groups the entire 13th Dynasty under this sub-section.

- **`sub_period`** — string, exactly `"Kings and Commoners"` on every row.

- **`unplaced`** — `true` for entries appearing under the `### Unplaced` sub-heading at the end of the chunk. `false` for every entry appearing above that heading.

- **`notes`** — the full prose paragraph for the entry, verbatim, single-line-joined. Preserve museum locations (Cairo Museum / CM, British Museum, Metropolitan Museum, Louvre, Würzburg, Vatican, Vienna, Basel, Tukh, Kerma, Boston, Bologna, Rio de Janeiro, etc.), named papyri (`Papyrus Bulaq 18`, `Juridical Stela from Karnak`, `Kahun papyrus`, `Turin Canon`), tomb IDs (`tomb of Reniseneb B`, `tomb 9 at El-Kab`), inscription locations (`Wadi Hammamat`, `Wadi el-Hol`, `Wadi el-Hudi`, `Philae`, `Sehel`, `Karnak`, `Abydos`, `Koptos`), and D&H's hedges (`probable`, `probably`, `possible`, `possibly`, `perhaps`, `conceivably`). Trim leading / trailing whitespace. Do NOT summarise, editorialise, or add scope commentary.

   **Cross-reference stub entries.** When an entry's prose body is a single short pointer phrase (e.g. `See previous section.`, `See the following chapter.`, or similar phrasings referring the reader to another location for the full Brief Life), preserve the pointer phrase verbatim as the `notes` value — it IS the notes body for this row, not a marker to skip. The stub's kinship fields (`spouse_names`, `father_name`, `mother_name`, `children_names`) are `null` / `[]` because the stub's own prose does not repeat the kinship clauses; those clauses live in the full-Brief-Life row located in the other sub-section that the pointer references. The composite `(dh_id, sub_period)` key handles the two rows independently — downstream Phase A unions them.

- **`source_citation`** — fixed literal `{"pdf_pages": "98-103", "edition": "Thames & Hudson 2004 hardback"}` on every row.

## Abstract parsing rules (no per-row answer enumeration)

- **Non-regnal vs regnal names.** A name with a trailing single-letter capital suffix (`A`, `B`, `C`, `Q`, `R`) is D&H's per-family-tree disambiguator for a non-regnal individual. A name with a Roman-numeral suffix (`I`, `II`, `III`, `IV`, ..., or BOLD CAPITALS form like `SOBKHOTEP IV`) is the regnal form of a pharaoh's name and appears in the Brief Lives only as a cross-reference in other entries' prose — not its own Brief Lives entry. Emit rows for letter-suffixed individuals; do NOT emit rows for Roman-numeral kings referenced in prose.
- **Compound name-with-epithet forms.** Several `dh_id`s carry compound forms where D&H appends an epithet or second name: `Iuhetibu B Fendy`, `Haankhef C Ikherneferet`, `Sobkhotep D Miu`, `Sobkhotep E Djadja`, `Seneb[henas A]` (the latter with bracketed lacuna inside the name). Preserve the compound form verbatim as the `dh_id`.
- **Lacuna-prefixed entries.** `[...]13A`, `[...]13B`, `[...]13C`, `[...]13D`, `[...]13E`, `[...]djeb` (Unplaced) preserve brackets and ellipsis verbatim.
- **Question-mark hedge inside a name.** `Nen?[...]` uses `?` as a transcription hedge on the first character. Preserve verbatim as `Nen?[...]`.
- **Spelled-out long-form role phrases** (several per chunk): preserve as single verbatim tokens inside `roles` — do not split on spaces. See the `roles` semantics block above for the list.
- **Cross-section stub entries** (pointer-phrase-only prose). Emit one row whose `notes` is the pointer phrase verbatim (e.g. `"See previous section."`). Derive `dh_id`, `name`, `roles`, and `sex` from the entry's bold-name + parenthetical per the standard rules. Kinship fields (`spouse_names`, `father_name`, `mother_name`, `children_names`) are `[]` / `null` because the stub's own prose does not repeat kinship clauses; those clauses live on the full-Brief-Life row in the other sub-section the pointer references. `unplaced` follows the entry's position in the chunk (under `### Unplaced` → `true`; above that heading → `false`).
- **Hedged attributions.** Role-code hedges (`?`) and prose hedges (`possible`, `possibly`, `probable`, `probably`, `perhaps`, `conceivably`) preserved verbatim — on roles inside the parenthetical, hedges attach to the code token; on relationships inside the prose, hedges attach to the name string.
- **Multiple candidate husbands**. Several entries give disjunctive hedges like `"wife of either X or Y"` or `"probable wife of X, Y or Z"` (e.g. Iy, Inni, Nubkhaes A). Emit each candidate as a separate string in `spouse_names`, carrying D&H's hedge on each: e.g. `["X (either)", "Y (either)"]` for a two-candidate disjunction, or `["X (probable)", "Y (probable)", "Z (probable)"]` for a three-candidate probable. The "either" / "probable" / "possible" modifier applies to each element in the disjunction.

## Sort order

Alphabetical by `dh_id`, case-insensitive, within each `unplaced` bin. The merge step handles final sort; you may emit rows in reading order.

## Expected row count

**108 rows** — 91 placed + 17 unplaced. If your row count differs from 108, re-read the chunk and count bold entry heads per page. Agents should NOT invent rows to meet an expected count — if the count looks anomalous, flag it in your final report.

## Output

Write the JSONL. In your final response, report:
1. Total row count and the placed/unplaced split.
2. Any within-chunk duplicate `dh_id`s (extraction bug if present).
3. Any novel role-code tokens preserved verbatim (tokens not in the prior-chunk list above).
4. Any rows where role-code sex disagreed with prose-kinship sex (flag for main-session review).
5. Any rows where you had to use typography as a last-resort tiebreaker (should be zero or very few on this chunk if the role-code-first rule was applied cleanly).
6. Anything else anomalous in the OCR.

Under 150 words.
