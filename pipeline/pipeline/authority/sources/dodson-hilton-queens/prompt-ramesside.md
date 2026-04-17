# Extraction prompt for Dodson & Hilton Brief Lives — Ramesside (chunk 3)

Pass this to **three** independent Claude Code subagents in parallel. Each writes JSONL to a distinct filename; `merge.py` majority-votes across all chunk batches (Power `agent-{a,b,c}-power.jsonl`, Amarna `agent-{a,b,c}-amarna.jsonl`, Ramesside `agent-{a,b,c}-ramesside.jsonl`). The prompt is verbatim; the only per-agent substitution is the agent tag in the output filename (`a`, `b`, or `c` in `agent-{tag}-ramesside.jsonl`).

---

You are extracting structured royal-family-member rows from OCR'd Brief Lives entries of Dodson & Hilton (2004) *The Complete Royal Families of Ancient Egypt*, 1st ed. hardback.

## Inputs

Three OCR chunk files covering the three Brief Lives sub-blocks of D&H's chapter 3 Ramesside material:

1. `<repo_root>/pipeline/pipeline/authority/sources/dodson-hilton-queens/raw/chunk-p157-p162.md` — The House of Ramesses Brief Lives (19th Dyn pt 1, printed pp. 170–175, physical pp. 157–162). ~120–130 entries expected.
2. `<repo_root>/pipeline/pipeline/authority/sources/dodson-hilton-queens/raw/chunk-p169-p170.md` — The Feud of the Ramessides Brief Lives (19th Dyn pt 2, printed pp. 182–183, physical pp. 169–170). ~10 entries expected.
3. `<repo_root>/pipeline/pipeline/authority/sources/dodson-hilton-queens/raw/chunk-p178-p180.md` — The Decline of the Ramessides Brief Lives + Unplaced (20th Dyn, printed pp. 192–194, physical pp. 178–180). ~35 entries expected (33 placed + 2 unplaced).

Read all three. Extract every Brief Lives entry across the three into one JSONL output.

## Output

Write JSONL to `<agent_dir>/agent-{a|b|c}-ramesside.jsonl`, where `<agent_dir>` defaults to `<source_dir>/raw/` (gitignored via `raw/agent-*.jsonl`). One JSON object per line, no preamble, no code fences.

## Task

Every Brief Lives entry across the three chunks gets one row. Entries begin with a bold name (`**Name**` upright for males, `***Name***` italic for females, `**NAME**` allcaps inline for regnal names) followed by role codes in parentheses, then a 1–3 sentence prose paragraph. Read the three chunk files in input order; preserve every entry.

## Schema

```json
{
  "dh_id": "Bintanath",
  "name": "Bintanath",
  "alt_names": [],
  "roles": ["KDB", "KGW", "L2L", "MULE"],
  "sex": "female",
  "spouse_names": ["Ramesses II"],
  "father_name": "Ramesses II",
  "mother_name": "Isetneferet A",
  "children_names": [],
  "dynasty": 19,
  "sub_period": "The House of Ramesses",
  "unplaced": false,
  "notes": "Eldest daughter of Ramesses II and Isetneferet A. Served as one of her father's Great Wives following her mother's death and was represented on a number of monuments throughout Ramesses II's reign. …",
  "source_citation": {"pdf_pages": "157-162", "edition": "Thames & Hudson 2004 hardback"}
}
```

## Field semantics

- **`dh_id`** — D&H's name-with-disambiguator exactly as printed: `Ramesses A`, `Ramesses B`, `Khaemwaset C`, `(Ramesses-)Meryastarte`, `[Set]emnakhte`, `[...]19A`, `–18P`-style en-dash lacunae, etc. Lacuna-prefixed names keep the square brackets and ellipsis. The short-dash lacuna form keeps the en-dash. `Q` suffixes are IDs, not throwaway markers.

  **Cross-section duplicate individuals.** D&H lists at least two individuals under two sub-sections each: `Takhat A` appears in *The House of Ramesses* Brief Lives as a *daughter of Ramesses II* (cross-reference stub ending `(see next section)`) and again in *The Feud of the Ramessides* Brief Lives as the *wife of Sety II* (full prose). `Isetneferet C` appears similarly. Emit TWO rows for each such individual, one per sub-section — the composite primary key is `(dh_id, sub_period)`, not `dh_id` alone. Each row carries its own verbatim `notes`, `roles`, `spouse_names`, and `father_name`/`mother_name` from that section's prose. Downstream Phase A will reconcile them to a single canonical individual.

  Flag any other cross-section duplicates you encounter in your final report so the main agent can cross-check against the PDF before merge.

- **`name`** — same string as `dh_id` for this source. Kept separate for cross-source schema parity.

- **`alt_names`** — list of variant name strings D&H records inline (e.g. `Amenemwia/Setemwia` → `dh_id: "Amenemwia/Setemwia"`, `alt_names: []` because the slash is part of D&H's own printing of the composite name; `Meryamun A` prose "Also known as **Ramesses-Meryamun**" → `alt_names: ["Ramesses-Meryamun"]` titlecase). Use **titlecase** for regnal-name alt_names; D&H's BOLD-CAPITALS rendering is typographic emphasis, not canonical spelling. Empty list when absent. Do NOT include the disambiguator letter in alt_names.

- **`roles`** — list of role-code strings from the parenthetical after the name. Split on `;` with trailing whitespace trimmed. Known codes in this chunk (non-exhaustive — D&H introduces several new codes in the Ramesside era):
  - Kinship codes from chunks 1 and 2: `K` (King, BOLD CAPITALS), `KSon`, `KSonB` (Son of his Body — explicit), `EKSon` (Eldest King's Son), `KD`, `KDB` (King's Daughter of his Body), `KGW`, `KW`, `GW`, `KM`, `KSis`, `M2L` (Mistress of the Two Lands), `L2L` (Lady of the Two Lands), `MULE` (code per D&H's own legend — preserve verbatim), `KSonN`.
  - Codes introduced or heavily-used in this chunk: `1KSonB` (First King's Son of his Body — D&H uses the leading digit for first-born), `GM` (God's Mother?), `MoH` (Master of Horse), `HPH` (High Priest of Heliopolis), `HPM` (High Priest of Memphis), `SPP` (Sem Priest of Ptah), `Exec` (Executive?), `ExecH2L` (Executive of the Two Lands?), `Genmo` (General), `Gen` (General — variant), `Viz` (Vizier), `ChA` (Chief of...?), `Fanbearer`, `Troop Commander`, `Viceroy`, `Overseer of Treasurers`, `King of Hittites`, `King of Mitanni`, `Adjutant of the Chariotry`, `GWA` (God's Wife of Amun), `Ador` (Adorer / Adoratrix), `GF` (Godfather?), `HPA` (High Priest of Amun), `Songstress of Pre`.
  - Preserve code strings verbatim even if you've never seen them before — D&H sometimes spells a role out (`King of Hittites`, `Fanbearer`) instead of using an abbreviation. Do NOT attempt to expand codes to long-form — Phase A owns the code glossary.
  - If a parenthetical repeats a code (e.g. the chunk-2 Tey precedent, `(KGW; KGW)`), deduplicate to a single occurrence — the book's repetition is a typo, not a distinct role.

- **`sex`** — `"male"` or `"female"`:
  - **male**: any role in `{K, KSon, KSonB, 1KSonB, EKSon, KSonN, HPH, HPM, SPP, Gen, Genmo, Exec, ExecH2L, MoH, Fanbearer, Viz, Viceroy, Overseer of Treasurers, Troop Commander, Adjutant of the Chariotry, HPA, "King of Hittites", "King of Mitanni", GF, "Sem Priest"-variants}`; BOLD upright entry rendering; the prose uses `"He"` / `"His"` / `"son of"` / `"father of"`.
  - **female**: any role beginning with `K` for a female-pattern code (`KD`, `KDB`, `KGD`, `KGW`, `KW`, `KM`, `KSis`, `GM`) or in `{GW, L2L, M2L, MULE, ChA, GWA, Ador, Songstress of Pre}`; BOLD ITALIC entry rendering; the prose uses `"She"` / `"Her"` / `"daughter of"` / `"mother of"`.
  - Ambiguous shared codes resolve by BOLD upright (male) vs BOLD ITALIC (female) typography in D&H's OCR, then by prose pronouns as tiebreaker.
  - Bold-capitals regnal-name entries (kings in the Brief Lives: `RAMESSES I`, `RAMESSES II`, `MERENPTAH`, `SETY II`, `AMENMESSE`, `SIPTAH`, `RAMESSES III`-`XI`, `TAUSRET`, `SETNAKHTE`) get `sex: "male"` unless BOLD ITALIC CAPITALS (Tausret as female king — follow D&H's chart-key convention).

- **`spouse_names`** — list of spouse names from `"Wife of X"`, `"Husband of Y"`, `"married Z"`, `"consort of W"`. Do NOT conflate cross-reference mentions (`"brother of"`, `"father-in-law of"`) with spouses. Include hedges verbatim (`"Ramesses II (probable)"`, `"Ay (perhaps, brief marriage)"`). Empty list when no spouse is named.

- **`father_name`** / **`mother_name`** — single strings from `"son of X"`, `"daughter of Y"`, `"mother Z"` / `"father W"` constructions. Include D&H's hedges verbatim. `null` when D&H doesn't state the parent. The many `"Son of Ramesses II and number N in the processions of sons"` entries get `father_name: "Ramesses II"` and `mother_name: null` unless the entry itself also names the mother.

- **`children_names`** — list of children named in this entry's own prose. The chunk-2 cross-entry-inference rule stays in effect: if a child's Brief Lives entry names Ramesses II as father and the mother's entry is silent, `Ramesses II.children_names` does NOT auto-acquire that child — but where a parent's entry explicitly lists children (e.g. `Nefertiry D Meryetmut`'s prose likely names her offspring), include them. Cross-entry inference is sanctioned for symmetry cases (e.g. if a Hittite princess's entry names her as daughter of Hattusilis III and Hattusilis III's own entry is silent, append the princess to `Hattusilis III.children_names` — analogous to the chunk-2 Shuttarna II → Gilukhipa precedent). Flag any cross-entry inferences you apply in your final report.

- **`dynasty`** — integer:
  - `19` for every row with `sub_period` in `{"The House of Ramesses", "The Feud of the Ramessides"}`.
  - `20` for every row with `sub_period == "The Decline of the Ramessides"`.
  - The Unplaced sub-block at the end of the Decline chunk is headed `"in 19th and 20th Dynasties"` — these entries straddle both; assign `dynasty: 20` as the section's primary dynasty unless D&H's prose for the individual row explicitly anchors her to the 19th (in which case use `19`).

- **`sub_period`** — string, exactly one of:
  - `"The House of Ramesses"` for every row from `chunk-p157-p162.md`.
  - `"The Feud of the Ramessides"` for every row from `chunk-p169-p170.md`.
  - `"The Decline of the Ramessides"` for every row from `chunk-p178-p180.md` (including the Unplaced sub-block).

- **`unplaced`** — `true` only for rows that appear under the `### Unplaced` sub-heading on printed p. 194 of the Decline chunk (at minimum: `Anuketemheb`, `Taiay`). All other Ramesside rows: `false`. D&H does not print an explicit "Unplaced" sub-heading in House of Ramesses or Feud Brief Lives for this chunk.

- **`notes`** — the full prose paragraph verbatim, single-line-joined. Preserve museum catalogue numbers (`CM CG42153`, `MMA 11.155.3`, `BM EA19`, `Ny Carlsberg 589`, `CM JE52577-8`), tomb IDs (`KV5`, `KV10`, `KV13`, `KV14`, `KV55`, `KV56`, `KV74`, `QV38`, `QV44`, `QV55`, `QV66`, `QV68`, `QV71`, `QV74`, `QV80`, `TT120`, `TT148`, `TT255`, `TT320`, `TT346`), city names (`Abu Simbel`, `Abydos`, `Medinet Habu`, `Gebel el-Silsila`, `Wadi el-Sebua`, `Bubastis`, `Saqqara`), footnote superscript markers (`119`, `120`, `121`, `122`, `123`, `124`, `125`, `126`, `127`, `128`, `129`, `130`, `131`, `132`, `133`, `134`, `135`, `136`), scholarly hedges (`probably`, `possibly`, `perhaps`, `seems to`, `remains doubtful`), and all named proper-noun attestation evidence. Trim leading/trailing whitespace. Do NOT summarise, editorialise, or add scope/meta commentary.

- **`source_citation`** — one of:
  - `{"pdf_pages": "157-162", "edition": "Thames & Hudson 2004 hardback"}` for House of Ramesses rows.
  - `{"pdf_pages": "169-170", "edition": "Thames & Hudson 2004 hardback"}` for Feud rows.
  - `{"pdf_pages": "178-180", "edition": "Thames & Hudson 2004 hardback"}` for Decline rows (including Unplaced).

## Parsing hazards (Ramesside)

- **The Ramesses letter-run.** ~15–20 distinct individuals named `Ramesses` across Dyn 19/20, mixing kings and king's-sons. Each has a letter suffix or compound-name form:
  - Kings: `RAMESSES I`, `RAMESSES II`, `RAMESSES III`, `RAMESSES IV`, `RAMESSES V`, `RAMESSES VI`, `RAMESSES VII`, `RAMESSES VIII`, `RAMESSES IX`, `RAMESSES X`, `RAMESSES XI`. These appear in BOLD CAPITALS and as prose references to the regnal names of letter-suffixed princes (`Amenhirkopshef C (…) later king as RAMESSES VI`).
  - Princes: `Ramesses A` (= later RAMESSES II, eldest son of Sety I), `Ramesses B` (son of Ramesses II and Isetneferet A, heir from year 25–50), `Ramesses C` — BEWARE: in House of Ramesses this is the grandson of Ramesses II; in Decline this is the son of Ramesses III (later RAMESSES IV). Different individuals; letter-suffix reuse across sub-sections is a feature of D&H's per-family-tree letter-scoping. Preserve each `Ramesses C` with its own `sub_period`.
  - Compound forms: `(Ramesses-)Meryastarte`, `(Ramesses-)Merymaat`, `(Ramesses-)Siptah A`, `(Ramesses-)Userkhepesh`, `Ramesses-Maatptah`, `Ramesses-Merenre`, `Ramesses-Meretmirre`, `Ramesses-meryamun-Nebweben`, `Ramesses-Meryset`, `Ramesses-Payotnetjer`, `Ramesses-Siatum`, `Ramesses-Sikhepri`, `Ramesses-Userpehty`.
  - **DO NOT MERGE ACROSS LETTERS.** Each letter suffix is a distinct individual. Cross-chunk re-use of a letter means two rows with the same `dh_id` but different `sub_period` (handled by the composite key).

- **Amenhirkhopshef / Amenhirkopshef / Amenhirwenemef cluster.** Multiple princes spanning Ramesses II, III, VI. D&H spellings: `Amenhirwenemef/Amenhirkopshef A` (eldest son of Ramesses II and Nefertiry D); `Amenhirkhopshef B` (eldest son of Ramesses III, EKSon); `Amenhirkopshef C` (son of Ramesses III, later RAMESSES VI); `Amenhirkopshef D` (son of Ramesses VI). Preserve D&H's spelling per entry — orthography drifts by individual. Role codes distinguish them too (`1KSonB; EKSon; Genmo` vs `EKSon; ExecH2L` vs `1KSon; MoH`). Phase A handles the museum-catalogue spelling drift (`Amunhirkhopshef`, `Amenherkhepshef`).

- **Khaemwaset cluster.** `Khaemwaset B` (uncle of Ramesses I — Fanbearer); `Khaemwaset C` (famous Sem-Priest of Ptah, son of Ramesses II and Isetneferet A — "first Egyptologist"); `Khaemwaset D` (son of Merenptah, in Feud); `Khaemwaset E` (son of Ramesses III, Sem-Priest of Ptah, echoes his grandfather's namesake). Four distinct people; preserve each with its own letter.

- **Setherkhepeshef / Sethirkopshef variants.** `Sethirkopshef A` is an alt-name-later-regnal-switch for Amenhirwenemef A (who changed his name early in Ramesses II's reign). `Sethirkopshef B` is son of Ramesses III, later RAMESSES VIII. Do NOT conflate.

- **Dyn 20 contested queens:**
  - `Tyti` (KD; KSis; KW; KM; GW) — D&H places her as possible wife of Ramesses X, NOT Ramesses III despite scholarly debate. Owner of tomb QV52. Her Brief Lives prose reflects D&H's authorial call.
  - `Takhat A` (Dyn 19, in Feud — wife of Sety II, mother of Amenmesse, daughter of Ramesses II) and `Takhat B` (Dyn 20, in Decline — King's Mother of Ramesses IX, buried KV10 annex). Two distinct women with letter suffixes. Takhat A has a cross-reference stub in the House of Ramesses Brief Lives (see below).
  - `Iset D Ta-Hemdjert` (principal wife of Ramesses III, mother of RAMESSES VI) — D&H gives her the compound name with `Ta-Hemdjert` epithet. Do NOT confuse with Dyn-19 `Isetneferet A` (Ramesses II's queen) or `Isetneferet B`/`C`/`D` (daughters / descendants).
  - `Tentopet` in the main narrative of the Feud pages is actually `(Dua)tentopet` in the Decline Brief Lives — wife of RAMESSES IV, in QV74. Prefix parenthesis is part of D&H's printing; keep as `dh_id: "(Dua)tentopet"`.
  - `Nubkhesbed` (KGW) wife of RAMESSES VI, mother of Iset E. Preserve as-is.
  - `Henttawy Q` (KD; KW; KM) — 21st-Dyn link, daughter of late Ramesside king, wife of PINUDJEM I. The `Q` suffix here is D&H's disambiguator (not an Unplaced flag — `Henttawy Q` is in the main Decline Brief Lives, not under Unplaced). Keep `unplaced: false`.

- **Tausret (BOLD ITALIC CAPITALS in D&H).** Her Brief Lives entry appears in the Feud sub-block. She is a queen-became-king; D&H's schema treats her as female. Preserve spelling verbatim — museum catalogues more commonly use `Tawosret` or `Twosret`, but `dh_id` is D&H's printing.

- **Hittite diplomatic princesses.** `Maathorneferure` (first Hittite princess, arrived year 34 of Ramesses II, daughter of Hattusilis III and Pudukhepa). Only ONE is given a Brief Lives entry under this name; a second unnamed Hittite princess appears in the narrative prose (pp. 166–167) but is not a Brief Lives entry — do NOT emit a row for her. `Pudukhepa` (wife of Hattusilis III) does get a Brief Lives entry in House of Ramesses.

- **Cross-section duplicates.** Known cases:
  - `Takhat A` — House of Ramesses stub (`Daughter of Ramesses II; number 14 on the Louvre ostrakon list. Probable wife of Sety II (see next section).`) + Feud full entry (`Wife of Sety II, mother of Amenmesse, and probable daughter of Ramesses II. …`). Two rows; composite key.
  - `Isetneferet C` — House of Ramesses stub (`Granddaughter of Ramesses II, daughter of Khaemwaset C and possibly wife of Merenptah (see next section).`) + Feud full entry (`Wife of Merenptah. Depicted on a statue usurped for her husband from Amenhotep III …`). Two rows; composite key.
  - Watch for additional cases (e.g. whether `Ramesses C` is duplicated across House + Decline — lettering suggests no, but verify from the OCR).
  - Flag every `dh_id` that appears in more than one `sub_period` across your output in your final report.

- **Letter-suffix collisions vs duplicates.** Within one `sub_period`, NEVER emit two rows with the same `dh_id` — that's an extraction bug. Across `sub_period`s, same `dh_id` is legitimate (see above). The composite key `(dh_id, sub_period)` must be unique.

- **`Amenemwia/Setemwia (KSonB)`** — slash is part of D&H's name-change shorthand (this prince changed his name). Keep `dh_id: "Amenemwia/Setemwia"` with `alt_names: []` — the compound is the D&H primary name. Different from the chunk-2 `TUTANKHATEN/AMUN` case, where the slash introduced a successive regnal name; here it introduces an earlier-vs-later personal-name change. Follow D&H's prose cue for how to emit `alt_names`.

- **Name-change slashes in regnal-name contexts.** When the prose says `"… and later became king as RAMESSES X"`, include `"Ramesses X"` (titlecase) in `alt_names`. Same pattern chunk 2 used for Amenhotep E → Akhenaten.

- **Foreign rulers listed as Brief Lives entries for family-tree completeness.** `Hattusilis III` (King of Hittites), `Pudukhepa` (wife of Hattusilis III), `Benanath` (Syrian ship's captain, father-in-law of Simentu). Emit as rows with `sub_period: "The House of Ramesses"` and `dynasty: 19`; `roles: ["King of Hittites"]` or the verbatim D&H role prose.

- **`[Set]emnakhte`, `[Mut]metennefer`, `[...]Jheb`, `[...]khesbed`, `[...]taweret`, `[...]19A`, `[...]19B`, `[...]19C`, `[R]uia`, `Nebet[...]hf[...]ja`, `Nebetj[...]Jt[...]ja`** — square-bracketed lacunae. Preserve brackets and ellipses exactly. Sort after letter-prefixed names within each `sub_period` (the merge-step sort key handles this).

## Sort order

Alphabetical by `dh_id`, case-insensitive. Lacuna-prefixed names (`[`, `–`) sort after letter-prefixed names within their bin. Unplaced entries sort after placed within their `sub_period`. `sub_period` is the final tiebreaker for cross-section duplicates — merge.py handles this, you just emit one row per entry in the order you read them.

## Expected row count

**~165–180 rows total**, split roughly: 120–130 House of Ramesses + ~10 Feud + ~35 Decline (33 placed + 2 unplaced). If your row count is below 140 or above 200, re-read the chunks and count entries per page before writing. Per-page estimate (3-column layout): p. 170 ≈ 20, p. 171 ≈ 17, p. 172 ≈ 23, p. 173 ≈ 19, p. 174 ≈ 21, p. 175 ≈ 23; p. 182 ≈ 6, p. 183 ≈ 4; p. 192 ≈ 11, p. 193 ≈ 11, p. 194 ≈ 13.

## Output

Write the JSONL. In your final response, report:
1. Total row count, split by `sub_period` (House / Feud / Decline) and with the Unplaced count broken out.
2. The list of `dh_id`s that appear in more than one `sub_period` in your output (the cross-section duplicates — expected: at least `Takhat A`, `Isetneferet C`; flag any additional ones for spot-checking).
3. Any `dh_id` where you applied cross-entry inference for `children_names` (per the chunk-2 sanctioned pattern).
4. Anything anomalous (role code you couldn't classify, entry that didn't fit the template, OCR artifact you couldn't resolve).

Under 120 words.
