# Extraction prompt — Porter & Moss Vol I.2 (Theban Necropolis), Chunk 7

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/chunk-p132-p148.txt` and produce a JSONL file with one structured row per named royal tomb / near-royal tomb in §§ II and III.A / III.C / III.D of PM I.2. The other two agents see the same prompt and same chunk; `merge.py` majority-votes.

This is the first chunk of this source that covers sections **without numbered tomb-id conventions** (no KV/QV/TT numbers). The schema is unchanged; `tomb_id` becomes a descriptor-based stable identifier per the rules below.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** this prompt gives extraction RULES and normalisation conventions — it does NOT hand you per-tomb answers. Every field value must trace to something in the chunk file. The only things the prompt may validly hint: structural facts about the section (page range, scope, absent numbers); text-layer noise signatures; vocabulary constraints.

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume I, Part 2: Royal Tombs and Smaller Cemeteries.* 2nd edition, Oxford 1964.
- Sections in scope:
  - **§ II. SOUTH-WEST VALLEYS** (printed p.590–594; physical p.132–136)
    - § II.A Wadi Sikket Taqet Zaid
    - § II.B Wadi Qubbanet el-Qirud (Valley of the Tombs of the Monkeys)
    - (§ II.C Graffiti — out of scope, NOT a tomb)
  - **§ III. DRA' ABU EL-NAGA' with EL-TARAF** (printed p.594–606 within this chunk; physical p.136–148):
    - § III.A Antef Cemetery, Dyn. XI (printed p.599 ≈ physical p.141)
    - (§ III.B Entrance to Valley of the Kings — printed p.599 — OUT OF SCOPE: rock-stelae + graffiti, no tomb headwords)
    - § III.C Tomb of Queen ʿAhmosi Nefertere (probably) (printed p.600)
    - § III.D Seventeenth Dynasty Cemetery — BURIALS sub-block (printed p.600–605)
  - § III.E onwards (Petrie Excavations, Gauthier-Chassinat, Northampton, Philadelphia, Carnarvon-Carter, Passalacqua, Position unknown, Finds) — **OUT OF SCOPE for chunk 7**; they are excavator-organised find-reports, not named-royal-tomb headwords. Defer to a later chunk.

- Printed page range in scope: **p.590–605** (physical p.132–147).
- The chunk file extends through physical p.148 (printed p.606) for boundary context only; do NOT extract rows from content that begins at or after `E. PETRIE EXCAVATIONS.` (printed p.606 header).
- Offset: printed = physical + 458.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF (see `transcribe.md` § "Method deviation").

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-a-chunk7.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-b-chunk7.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-c-chunk7.jsonl`

One JSON object per line. Sort rows by `(valley, section, tomb_id)` alphabetically. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## How to identify a "tomb row" in this chunk

PM's non-numbered sections organise named tombs via a hierarchy of sub-headers:

- A **section-level sub-header** like `A. WADI SIKKET TAQET ZAID`, `A. ANTEF CEMETERY. Dyn. XI. At El-Ṭaraf`, `C. TOMB OF QUEEN ʿAḤMOSI NEFERTERE (probably)`, `D. SEVENTEENTH DYNASTY CEMETERY`. These are the PM-section letters under `II. SOUTH-WEST VALLEYS` and `III. DRA' ABU EL-NAGA'`.
- **Named-tomb entries** within a section, written as a bold all-caps headword that names an occupant and is followed by a bibliographic/excavator ribbon and then finds. Examples:
  - `SOUTH TOMB OF ḤATSHEPSUT. See also Tomb 20, supra, p. 546.` — a single named tomb.
  - `TOMB OF THREE PRINCESSES, MENḤET ..., MENUI..., MERTI ...` — a single tomb with multiple occupants.
  - `TOMB, PROBABLY PRINCESS NEFERURĒʿ ..., daughter of Ḥatshepsut.` — a single hedged-attribution tomb.
  - `KAMOSI (WAZKHEPERRE<) [cartouches] Found by Mariette in 1857.` — a § III.D BURIAL headword; the all-caps name + prenomen-in-parentheses is the PM-canonical Dyn-17 royal burial format.
  - `ʿAḤḤOTP (...)`, `ANTEF (NUBKHEPERRE<)`, `ANTEF (SEKHEMRE<-WEPMA<ET)`, `QUEEN MENTUḤOTP I (...)`, `ʿAḤMOSI, eldest son of King Seḳenenreʿ-Taʿa ...`, `ʿAḤHOR ...` — all are § III.D BURIALS headwords.
- For the **Antef Cemetery (Dyn XI)** in § III.A: the section begins with general prose + Petrie-tomb references (Petrie Qurneh tombs 1–28); the Dyn-XI ruler-tombs are marked by all-caps headwords `ANTEF (SEHERTAUI)`, `ANTEF (WAḤʿANKH)`, and possibly a third Antef further on. Look only at the all-caps ruler headwords — the mid-section `Various` prose listing non-royal Dyn-XI finds is NOT a tomb row.

**Do NOT emit rows for:**
- Section-level sub-header lines like `A. WADI SIKKET TAQET ZAID`, `D. SEVENTEENTH DYNASTY CEMETERY` (these are organising headers, not tombs).
- `TOMBS OF THE MONKEYS. Late Period.` — this is an *animal-mummy* site at the mouth of the valley, not a human burial; skip.
- `FINDS`, `PETRIE EXCAVATIONS`, `NORTH OF ROAD TO THE VALLEY OF THE KINGS` — find-list or excavator-organisation sub-headers.
- Individual post-headword object entries (e.g. "Throwstick of Thuiu, son of Sekenenre", "Axe-head with two baboons"), unless the object's owner gets their own all-caps headword.
- Graffiti lists (§ II.C and any § III graffiti summaries).

**Ownership ambiguity:** if an object or coffin is described as "of X, son of King Y", that is a find within another tomb, not a distinct tomb row. A tomb row requires an all-caps PM headword that announces an occupant-tomb.

## Expected row count

Approximate bounds (not a guarantee — the real answer comes from the chunk text):
- § II.A: ~1 row (South Tomb of Hatshepsut).
- § II.B: ~2 rows (Tomb of Three Princesses + Tomb probably of Princess Neferure).
- § III.A: ~2–3 rows (Antef I / Antef II / possibly Antef III).
- § III.C: ~1 row (Tomb of Queen Ahmose-Nefertari).
- § III.D BURIALS: ~6–9 rows (Kamose + Ahhotep + Antef-Nubkheperre + Antef-Sekhemre + Queen Mentuhotep I + Ahmose-son-of-Seqenenre + Ahhor + possibly others).

Expected total: **12–18 rows**. If your count falls outside 10–22, double-check you haven't emitted find-entries as rows or merged tombs that should be distinct.

## Schema (per row)

Every row MUST have these keys; use `null` (not omitted, not empty string) for unknown values.

```json
{
  "tomb_id": "...",
  "valley": "...",
  "occupant_name": "...",
  "occupant_alt_names": [...],
  "occupant_role": "...",
  "dynasty": null,
  "sub_period": null,
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "location_sub_area": null,
  "discovery_year": null,
  "discoverer": null,
  "is_unfinished": true|false,
  "shared_with_tombs": [...],
  "notes_from_pm": "..." | null,
  "source_citation": {"page": <int>, "edition": "PM I.2 2nd ed. 1964", "section": "II.A" | "II.B" | "III.A" | "III.C" | "III.D"}
}
```

## `tomb_id` — descriptor-based convention (NEW for this chunk)

Non-numbered tombs have no KV/QV/TT prefix. Use this convention:

```
<VALLEY-PREFIX>-<OCCUPANT-DESCRIPTOR>[-<DISAMBIG>]
```

Where **VALLEY-PREFIX** is:
- `SWV` = South-West Valleys (§ II)
- `DAN` = Dra' Abu el-Naga (§ III)

And **OCCUPANT-DESCRIPTOR** is a compact identifier:
- For § II.A South Tomb of Hatshepsut: `HatshepsutSouth` → `tomb_id: "SWV-HatshepsutSouth"`
- For § II.B Tomb of Three Princesses: `ThreePrincesses` → `tomb_id: "SWV-ThreePrincesses"`
- For § II.B Tomb probably of Princess Neferure: `Neferure` → `tomb_id: "SWV-Neferure"`
- For § III.A Dyn-11 Antefs: use prenomen as disambiguator — `AntefSehertaui`, `AntefWahankh`, `AntefNakhtnebtepnefer` (if present) → `DAN-AntefSehertaui`, `DAN-AntefWahankh`, etc.
- For § III.C Queen Ahmose-Nefertari: `AhmosiNefertere` → `DAN-AhmosiNefertere` (PM prints `ʿAḤMOSI NEFERTERE` — keep the `-osi` / `-ere` letter choices per the PM-faithful rule below).
- For § III.D Dyn-17 Cemetery: same prenomen disambiguator, PM-faithful spelling — `KamosiWazkheperre`, `Ahhotep`, `AntefNubkheperre`, `AntefSekhemreWepmaet`, `MentuhotpIWifeOfDjhuti`, `AhmosiSonOfSeqenenre`, `Aqhor` (PM prints `ʿAḲ-ḤOR`, not `ʿAḥḥor`) → e.g. `tomb_id: "DAN-KamosiWazkheperre"`.

**Normalisation rules for the descriptor token (after the hyphen):**
- TitleCase, no spaces, no diacritics, no cartouche garbage.
- **Keep PM's letter choice** (don't anglicise): preserve `-osi` / `-otp` / etc. as PM prints them. So `ʿAḤMOSI` → `Ahmosi` (not `Ahmose`); `MENTUḤOTP` → `Mentuhotp` (not `Mentuhotep`); `ʿAḤḤOTP` → `Ahhotep`; `SEBEKEMSAF` → `Sebkemsaf`.
- Ayin `ʿ` / `<` → drop (not `c`). So `ʿAḤMOSI` → `Ahmosi`; `WAḤʿANKH` → `Wahankh`.
- Underdot-H / h-with-dot-below (`ḥ` / text-layer `I:I`, `I;I`, `I}`) → `h`. So `ḤATSHEPSUT` → `Hatshepsut`, `MENTUḤOTP` → `Mentuhotp`.
- Macron, underdot-k (`ḳ`) → strip diacritic, keep base letter (`ḳ` → `k`).
- Where two rows would otherwise collide (two "Antef"s, two "Mentuhotp"s), disambiguate by **PM-printed prenomen** appended in TitleCase (no space). **Prenomen-only disambiguator (no regnal numeral).** Follow the Antef pattern: `AntefSehertaui`, `AntefWahankh`, `AntefNubkheperre`, `AntefSekhemreWepmaet`. Apply the same to Sebkemsaf II → `SebkemsafSekhemreShedtaui` (not `SebkemsafII` and not `SebkemsafIISekhemreShedtaui`).
- Where there is NO prenomen in PM's headword but a genealogical qualifier is (e.g. `ʿAḤMOSI, eldest son of Seqenenre-Taʿa`), use `AhmosiSonOfSeqenenre`. Keep the `Ahmosi` / `Mentuhotp` spelling rule above.

`tomb_id` must be stable — downstream Phase-A enrichment will key on it. Test the three agents' outputs against each other: if you and another agent disagree on a disambiguator, the merge defaults to the majority vote per `(valley, occupant_name)` pair.

**Single-multi-occupant tombs:** `Tomb of Three Princesses, Menhet, Menui, Merti` is ONE tomb with three occupants. Emit ONE row with `occupant_name: "Menhet, Menui, and Merti"` (comma-joined, PM's order, `and` before the last), `occupant_role: "Royal Family"`, and `notes_from_pm` preserving any PM qualifier ("wives of Tuthmosis III" etc.).

## `valley`

- `"South-West Valleys"` for § II.A, § II.B rows.
- `"Dra' Abu el-Naga"` for § III.A, § III.C, § III.D rows. Use ASCII apostrophe (not Unicode ʻ) per the chunk-1 convention.

## `occupant_name`

**PM-verbatim, conventional-English form, titlecase, ayin PRESERVED as `ʿ` where PM prints it** in the actual occupant name (e.g. `ʿAhhotep`, `ʿAhmose`, `ʿAhmose-Nefertari`). This is the `occupant_name` convention from the chunk-5 Tutʿankhamun precedent — ayin is kept in `occupant_name`, stripped only in `tomb_id`.

Text-layer noise to normalise (not PM's scholarly choice):
- Underdot-H (`ḥ`) renders variably: `I:I`, `I;I`, `I}` → `ḥ` (Unicode underdot-H) in `occupant_name` per `notes_from_pm` policy, but strip to `h` in `tomb_id` per above.
- Regnal Roman numerals: count capital-I glyphs even if rendered as `Il` / `I Il` / `Ill`.
- Cartouches → drop entirely.
- Ayin rendered as `<`, `c` in the text layer → `ʿ` in `occupant_name` when PM's actual print shows ayin (the `<` rendering is typical of scholarly ayin).

If PM's headword has a **hedge** (`TOMB, PROBABLY PRINCESS NEFERURE` / `(probably)`): extract the name clean (`Neferure`), keep the hedge clause in `notes_from_pm` (`"Probably Princess Neferureʿ, daughter of Ḥatshepsut."`).

For the **three-princesses shared tomb**: `occupant_name: "Menhet, Menui, and Merti"` (PM's three occupants joined). Preserve PM's spellings; ayin if PM prints it.

## `occupant_alt_names`

A list of alternative names PM gives in the headword block — prenomens, classical aliases in parentheses, secondary personal names. Empty list `[]` when absent.

For Dyn-17 cemetery ruler headwords of form `NAME (PRENOMEN)`: put the prenomen in `occupant_alt_names` (e.g. `["Wadjkheperreʿ"]` for Kamose, `["Nubkheperreʿ"]` for Antef-Nubkheperre, `["Seḳenenreʿ Taʿa"]` for headwords that name a ruler by double-prenomen, etc.). Preserve scholarly diacritics.

## `occupant_role`

Controlled vocabulary: `"King"`, `"Queen"`, `"Royal Family"`, `"Vizier"`, `"Official"`, `"High Priest"`, `"Princess"`, `"Prince"`, `"Unknown"`.

- Kamose, Antef-Nubkheperre, Antef-Sekhemre-Wepmaet → `"King"` (§ III.D lists Dyn-17 kings).
- Antef-Sehertaui, Antef-Wahankh, Antef-Nakhtnebtepnefer (§ III.A Antef Cemetery Dyn XI) → `"King"` (all three Inyotefs were Dyn-11 rulers).
- ʿAhhotep, Queen Mentuhotep I (wife of Djehuty), Queen Ahmose-Nefertari → `"Queen"`.
- South Tomb of Hatshepsut → `"Queen"` (PM's Hatshepsut here is pre-kingship Hatshepsut as Queen-Consort of Thutmose II; the sarcophagus is labelled "as Queen-Consort". But PM's headword prints no role. **Defer to the headword**: if PM's prose inside the headword block explicitly flags Queen-Consort context, role = `"Queen"`; if silent, default to `"King"` per rule 4 below).
- Tomb of Three Princesses (Menhet et al.) → `"Royal Family"` (multiple princesses, `"Royal Family"` is the catch-all).
- Tomb probably of Princess Neferure → `"Princess"`.
- ʿAhmose son of Seqenenre, ʿAhhor → `"Royal Family"` (princes not of kingly status).

Assignment rules (apply per row):
1. If `occupant_name` is null or unknown: role `"Unknown"`.
2. If the headword explicitly names a role (`Queen`, `Princess`, `Prince`, `Vizier`, `daughter of <King>`, `wife of <King>`, `son of King <X>`): use that role.
3. If the headword gives cartouches (prenomen) AND no non-royal qualifier: role `"King"`.
4. Otherwise default: `"Royal Family"` for § II / § III (these are royal-precinct tombs).

## `dynasty`, `sub_period`, `date_bce_approx_start`, `date_bce_approx_end`

**All `null`** at this extraction stage. Phase A ruler-authority enrichment fills these. Do NOT supply from outside knowledge (rule 7).

## `location_sub_area`

Set to the specific wadi / sub-area phrase PM uses when that phrase is a named wadi:
- § II.A rows: `"Wadi Sikket Taqet Zaid"`.
- § II.B rows: `"Wadi Qubbanet el-Qirud"`.
- § III.A rows: `"El-Ṭaraf"` (PM's Dyn-XI Antef Cemetery is located at El-Taraf per the `A. ANTEF CEMETERY. Dyn. XI. At El-Ṭaraf` header).
- § III.C rows: `null` (no finer wadi PM names).
- § III.D rows: `null` (PM's Dyn-17 cemetery is the whole of Dra' Abu el-Naga; no finer wadi).

Apply the text-layer-noise normalisation to the sub-area string (drop cartouche garbage; underdot-T `ṭ` → `ṭ` or text-layer `ţ` / `t` — preserve the scholarly character if PM prints it; `El-Ṭaraf` is the PM form).

## `discovery_year`, `discoverer`

`null` for all rows. `Excavated by X in YEAR` / `Found by X in YEAR` / `Discovered by X` clauses go in `notes_from_pm`, not in these structured fields. This mirrors the chunk-1–6 convention.

## `is_unfinished`

`true` iff the literal word `Unfinished` (capital-U) appears in the headword block. Otherwise `false`. None of the chunk-7 tombs are expected to be flagged `Unfinished`.

## `shared_with_tombs`

List of cross-referenced tomb IDs pulled from `See also Tomb N` / `See also KV<N>` phrases in the headword block. Use the chunk-file convention: KV tombs → `KV<N>`.

The chunk-7 concrete case: **South Tomb of Hatshepsut** headword says `See also Tomb 20, supra, p. 546.` → `shared_with_tombs: ["KV20"]` (KV20 is Hatshepsut's Valley of the Kings tomb, our chunk-3 row).

## `notes_from_pm`

Verbatim short prose fragments from the headword block that don't fit any structured field. Preserve PM's diacritics (ayin `ʿ`, underdot-H `ḥ`, underdot-T `ṭ`). Capture:

- Attribution hedges: `Probably Princess Neferureʿ, daughter of Ḥatshepsut.` / `(probably)`.
- Discovery / excavator clauses: `Found by Mariette in 1857.`, `Discovered by Carter in 1917.`
- Dating / dynastic clauses: `Dyn. XVII.`, `Temp. Sekenenreʿ-Taʿa.` (regnal-dating phrase).
- Genealogical qualifiers for non-royal occupants: `eldest son of King Seḳenenreʿ-Taʿa and ʿAḥḥotp`, `wife of King Djehuti`, `Royal acquaintance`.
- Monument type clauses: `Pyramid, Dyn. XVII.` when PM ties a pyramid to the burial.
- Cross-referencing phrases: `See also Tomb 20, supra, p. 546.` (captured here AND parsed into `shared_with_tombs`).

Join distinct clauses with `". "` (chunk-1..6 convention). `null` when the headword has nothing beyond name + cartouches + bibliographic ribbon.

## `source_citation`

Object with three fixed keys:
- `"edition"`: exactly `"PM I.2 2nd ed. 1964"`.
- `"section"`: one of `"II.A"`, `"II.B"`, `"III.A"`, `"III.C"`, `"III.D"` — the PM sub-section the headword sits in.
- `"page"`: the printed page number on which the tomb's headword line begins. **Extract from the chunk text** — the page-separator markers `===== PHYSICAL PAGE N (PRINTED PAGE M) =====` in the chunk file give you the printed number directly. Do NOT supply from memory.

## Structural gotchas to watch

- **§ III.A Antef Cemetery:** PM's section starts with general Petrie-tomb prose (Qurneh tombs 1–28, mostly non-royal Dyn-XI/XII dependents); the actual Dyn-XI *ruler* tombs are announced by all-caps `ANTEF (PRENOMEN)` headwords further into the section. Do not emit a row for the general prose; only for the all-caps ruler headwords.
- **§ III.D BURIALS sub-block:** this is the big one. Every all-caps royal or royal-family headword in the BURIALS prose is a tomb row. Watch for ~7-9 headwords in this sub-block (Kamose, Ahhotep, Antef-Nubkheperre, Antef-Sekhemre-Wepmaet, Queen Mentuhotep wife of Djehuti, Ahmose son of Seqenenre, Ahhor, and potentially Seqenenre-Taʿa himself). Chunk-1 found ~6-8; do not truncate if you see more.
- **§ III.C "TOMB OF QUEEN ʿAHMOSI NEFERTERE (probably)":** the parenthetical `(probably)` is PM's own hedge on the attribution. Keep it in `notes_from_pm`, emit `occupant_name: "ʿAḥmosi Nefertere"` (PM-verbatim form with PM's ayin + underdot-H + `-osi` / `-ere` letter choices preserved).
- **Boundary at physical p.148 / printed p.606:** STOP emitting rows before `E. PETRIE EXCAVATIONS.` (physical p.148 begins the out-of-scope excavator-organised find-report block). The chunk file extends through p.148 only so you can see the boundary; do NOT extract Petrie Excavation rows.
- **`Tomb 20` reference** in the South Tomb of Hatshepsut headword is **KV20** (our chunk-3 row), not a Dra' Abu el-Naga tomb. → `shared_with_tombs: ["KV20"]`.

## Pitfall summary (read LAST before running)

1. **~12–18 rows expected**; stay within 10–22 or you've mis-identified headwords.
2. **tomb_id uses descriptor-based IDs** (`SWV-*`, `DAN-*`), no KV/QV/TT prefix (none of these tombs have PM tomb-numbers).
3. **Skip § III.B** (Entrance to Valley of the Kings — rock-stelae + graffiti only, no tombs).
4. **Skip § III.E onwards** (Petrie Excavations and later) — out of chunk-7 scope.
5. **Skip `TOMBS OF THE MONKEYS`** (animal-mummy site, not a human tomb).
6. **Skip sub-headers and excavator-organisation headers** (`D. SEVENTEENTH DYNASTY CEMETERY`, `NORTH OF ROAD TO THE VALLEY OF THE KINGS`, `FINDS`, `BURIALS`) — none of those are tomb rows.
7. **Three Princesses tomb → ONE row** with comma-joined occupant_name.
8. **PM verbatim spelling** — don't modernise `ʿAhmosi` to `Ahmose`, don't change PM's `Neferereʿ`.
9. **Dynasty / BCE / discoverer / discovery_year / sub_period all null** — do not supply from memory.
10. **`source_citation.page` from the chunk text** (use the `===== PRINTED PAGE M =====` markers), not memory.

## Report back

After writing the JSONL, output a one-paragraph report with:
- Row count and the PM sub-section distribution.
- Any row where you're unsure about a field, naming the field and your best-guess value.
- Any unexpected text-layer noise this prompt doesn't flag.

Stay under 150 words.
