# Extraction prompt for Dodson & Hilton Brief Lives — The Founders (Dyn 0–3)

Pass this to **three** independent Claude Code subagents in parallel. Each writes JSONL to a distinct filename (`agent-{a|b|c}-founders.jsonl`) under the agent directory (default `<source_dir>/raw/`). `merge.py` majority-votes across all chunk batches by `agent-{tag}-*.jsonl` glob.

---

You are extracting structured royal-family-member rows from OCR'd Brief Lives entries of Dodson & Hilton (2004) *The Complete Royal Families of Ancient Egypt*, 1st ed. hardback (Thames & Hudson).

## Inputs

One OCR chunk file covering D&H's chapter 1 "The Founders" Brief Lives sub-block (1st, 2nd and 3rd Dynasties — the Early Dynastic period):

1. `<repo_root>/pipeline/pipeline/authority/sources/dodson-hilton-queens/raw/chunk-p44-p45.md` — printed pp. 48–49, physical PDF pp. 44–45. Includes a trailing `### Unplaced` sub-block.

## Output

Write JSONL to `<agent_dir>/agent-{a|b|c}-founders.jsonl`, where `<agent_dir>` defaults to `<source_dir>/raw/` (gitignored via `raw/agent-*.jsonl`). One JSON object per line, no preamble, no code fences.

## Task

Every Brief Lives entry gets one row. Entries begin with a bold name (`**Name**` upright for males, `***Name***` italic for females — D&H's typographic convention for sex) followed by role codes in parentheses, then a 1–3 sentence prose paragraph. Read the chunk in order and preserve every entry. The chunk also contains a trailing `### Unplaced` sub-heading; rows beneath that heading take `unplaced: true`.

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
  "dynasty": 1,
  "sub_period": "The Founders",
  "unplaced": false,
  "notes": "<full prose paragraph verbatim>",
  "source_citation": {"pdf_pages": "44-45", "edition": "Thames & Hudson 2004 hardback"}
}
```

## Field semantics

- **`dh_id`** — D&H's bold name-with-disambiguator exactly as printed in the chunk. Letter suffixes (`A`, `B`, `C`) and numerical disambiguators are part of the id. Lacuna markers inside a name (`[...]1A`) preserved verbatim. Entries without any suffix keep the bare name (e.g. `Benerib`, `Herneith`).

- **`name`** — same string as `dh_id` for this source.

- **`alt_names`** — list of variant name strings D&H records inline in the current entry's own prose (e.g. `"Also known as …"`). `[]` when no inline variant is named.

- **`roles`** — list of role-code tokens from the parenthetical after the name. Split on `;` and trim whitespace. Preserve every token verbatim. This chunk uses several role codes that are new to the D&H corpus — preserve them as-is and list novel tokens in your final report. Codes observed on prior chunks include: `K`, `KD`, `KDB`, `KM`, `KW`, `KGW`, `GW`, `KSis`, `KSon`, `KSonB`, `EKSon`, `EKSonB`, `HPH`, `HPM`, `SPP`, `HPA`, `GWA`, `Ador`, `GM`, `GF`, `MULE`, `MoH`, `Genmo`, `Exec`, `ExecH2L`, `L2L`, `M2L`, `GBW`, `Fanbearer`, `Nomarch`, `Viz`, `PH`, `GS`, `UWC`, `RO`, `King of Hittites`, `King of Mitanni`, `Mistress of All Women`, plus hedged forms like `KW?`. Entries with an empty parenthetical or no parenthetical at all (e.g. an entry whose header is just `**Name**` followed by prose) get `roles: []`. List any novel role-code tokens in your final report.

- **`sex`** — derive from the role-code parenthetical first, using D&H's legend; role-code-first makes the 3-agent vote independently-derivable rather than dependent on typography that may have been synthesised during OCR post-processing on prior chunks (the Founders chunk specifically does NOT have synthesised typography — Gemini preserved D&H's bold-italic; so typography is also a reliable independent signal here):
  - **Female-indicating codes** (any one present → `"female"`): `KW`, `KGW`, `GW`, `GBW`, `KD`, `KDB`, `KM`, `KSis`, `UWC`, `M2L`, `L2L`, `GS`, `GM`, `GWA`, `Ador`, `PH`, `MULE`, `RO`, `CTL`, `FW`, `SH`, `SCH`, `ScH`, `Mistress of All Women`, and any `X?` / `X!` hedged variant.
  - **Male-indicating codes** (any one present → `"male"`): `K`, `KSon`, `KSonB`, `1KSonB`, `EKSon`, `EKSonB`, `KSonN`, `1KSon`, `GF`, `HPH`, `HPM`, `HPA`, `SPP`, `Exec`, `ExecH2L`, `Genmo`, `Gen`, `MoH`, `Viz`, `Nomarch`, `Fanbearer`, `King of Hittites`, `King of Mitanni`.
  - **Role-less entries or ambiguous-role entries**: derive from prose-kinship verbs in the current entry's notes. Female: `"wife of"`, `"daughter of"`, `"mother of"`, `"sister of"`, `"niece of"`, `"granddaughter of"`, `"grandmother of"`, pronouns `she`/`her`. Male: `"husband of"`, `"son of"`, `"father of"`, `"brother of"`, `"nephew of"`, `"grandson of"`, `"grandfather of"`, pronouns `he`/`his`.
  - **Typography (`***Name***` vs `**Name**`)** is also a reliable independent signal for this chunk (unlike Seizers / Kings and Commoners where typography was restored post-OCR) — use it as a confirmation. If role-code, prose-kinship, and typography all agree: emit the agreed answer. If they disagree: emit the prose-kinship answer and flag the row in your final report.

- **`spouse_names`** — list of spouse names from `"wife of X"`, `"husband of Y"`, `"probable wife of X"` phrases in the current entry's own prose. Hedges preserved verbatim inside the string (e.g. `"NAME (probable)"`, `"NAME (possibly)"`). Empty list when the prose names no specific spouse. Several entries in this chunk carry `"probable wife of"` / `"possible owner of"` style hedged prose — preserve the hedge.

- **`father_name`** / **`mother_name`** — single string from `"son of X"`, `"daughter of Y"`, `"father of Z"`, `"mother NAME"` prose in the current entry itself. `null` when the prose either doesn't name the parent at all OR names the parent only as anonymous. Hedges on a **named** parent preserved verbatim inside the string.

- **`children_names`** — list of children named in the current entry's own prose. Do NOT do cross-entry inference for this chunk: if the prose of the current entry does not name a child, the list is empty.

- **`dynasty`** — integer `1` for every row in this chunk. D&H's section title explicitly lists the 1st, 2nd AND 3rd Dynasties jointly under "The Founders"; per-row dynasty refinement is Phase-A work that reads `notes` cues (e.g. `Shepsetipet`'s notes explicitly say "2nd Dynasty"; `Redji`'s notes say "3rd Dynasty"). The extract keeps dynasty coarse and defers per-individual dynasty assignment.

- **`sub_period`** — string, exactly `"The Founders"` on every row.

- **`unplaced`** — `true` for entries appearing under the `### Unplaced` sub-heading. `false` for every entry appearing above that heading.

- **`notes`** — the full prose paragraph for the entry, verbatim, single-line-joined. Preserve museum locations (Cairo Museum, Louvre, Turin Museum, British Museum, etc.), tomb IDs (`tomb B14 at Umm el-Qaab`, `Saqqara S3507`, `Umm el-Qaab tomb Y`, `Helwan tomb 1241 H9`, `Saqqara tomb S2146E`, `tomb 175 H8 at Helwan`, `tomb 964 H8`, `K1 at Beit Khallaf`, etc.), named stelae (`stela (number 95)`, `stela (number 128)`, `stela (number 126)`, `stela (number 129)`), named royal monuments (`Cairo Annals Stone`, `Palermo Stone`, `Royal Tomb at Naqada`, `Step Pyramid`), and footnote markers (`[^60]`, `[^61]`, `[^62]` — preserve as-is). Trim leading / trailing whitespace.

- **`source_citation`** — fixed literal `{"pdf_pages": "44-45", "edition": "Thames & Hudson 2004 hardback"}` on every row.

## Abstract parsing rules

- **Non-regnal vs regnal names.** A name with a trailing letter or numerical suffix (e.g. `Meryetneith A`, `[...]1A`, `Neithhotep A` vs `Neithhotep B`) is D&H's per-family-tree disambiguator for a non-regnal individual. Bare names without suffix (e.g. `Benerib`, `Herneith`, `Semat`) are also non-regnal — D&H omits the suffix when the name is unique in the Brief Lives. Emit rows for every bold entry you see in the chunk; do NOT emit rows for regnal-name kings (`HOR-AHA`, `DJER`, `DEN`, `DJOSER`, etc.) that appear only as cross-references in prose.
- **Lacuna-bearing entry** `[...]1A` preserves brackets and `1A` suffix verbatim in `dh_id`.
- **Cross-reference stubs.** This chunk has no "See previous section" / "See next section" cross-references — every entry has its own verbatim prose.
- **Hedged attributions.** D&H's role-code hedges (`?`) and prose hedges (`probable`, `probably`, `possible`, `possibly`, `perhaps`) preserved verbatim on the fields where they appear.

## Sort order

Alphabetical by `dh_id`, case-insensitive, within each `unplaced` bin. The merge step handles final sort; you may emit rows in reading order.

## Expected row count

**26 rows** — 15 placed + 11 unplaced. If your row count differs from 26, re-read the chunk and count bold entry heads per page.

## Output

Write the JSONL. In your final response, report:
1. Total row count and the placed/unplaced split.
2. Any within-chunk duplicate `dh_id`s (extraction bug if present).
3. Any novel role-code tokens preserved verbatim (tokens not in the prior-chunk list above — particularly new tokens you see here like `CTL`, `FW`, `SH`, `SCH`, `ScH` which are Early-Dynastic-specific and likely decode to women's cult / priestess / lineage roles).
4. Any rows where role-code + prose-kinship + typography all agreed (for confirmation) or disagreed (for flag).
5. Anything else anomalous in the OCR.

Under 120 words.
