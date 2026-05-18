# Extraction prompt — Porter & Moss Vol III.2 (Saqqâra-Dahshûr), Chunk 20

> **Twentieth chunk drawn from PM Vol III** — Ṣaqqâra § II.B AROUND TETI PYRAMID opener / NORTH OF THE PYRAMID sub-section. PM III.2 physical pp.148–164 / printed pp.508–524. Named Old Kingdom mastabas of Teti's vizier-clientele (Khentka Ikhekhi, Neferseshemreʿ Sheshi, ʿAnkhmaʿḥor Sesi, Uzaḥateti Neferseshemptaḥ Sheshi, Ptaḥshepses, Mereri, LS 10 Kagemni Memi) plus one Shape-1 daughter-of-Teti named tomb (Inti). The chunk file deliberately stops just BEFORE the Mereruka mega-block (phys p.165+) which gets its own chunk. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-20-p148-p164-teti-pyramid-opener.txt` and produce a JSONL file with one structured row per **PM-headworded named tomb** in the chunk's page range. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** field-extraction RULES only; no per-row answers.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data is committed; PM's expressive prose is dropped. The PDF is not redistributed. Chunks 1–19 have already shipped.

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part 2.* 2nd edition, 1978/1981 fascicles, ed. Málek.
- Section covered: **§ II.B AROUND TETI PYRAMID — NORTH OF THE PYRAMID** sub-section (pp.508–524).
- PM III.2 offset: **printed = physical + 360**.
- Chunk file: physical pp.148–164 / printed pp.508–524.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk20.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk20.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk20.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. `json.dumps(..., sort_keys=True, ensure_ascii=False)`.

## Schema (per row — 23 keys)

```json
{
  "tomb_id": "TPC-<Name>" | "LS<N>",
  "memphite_area": "Saqqara",
  "occupant_name": "..." | null,
  "occupant_alt_names": [],
  "tomb_aliases": [],
  "co_occupants": [],
  "co_occupant_roles": [],
  "is_joint_burial": false,
  "occupant_role": "King" | "Queen" | "Prince" | "Princess" | "Vizier" | "High Priest" | "Official" | "Royal Family" | "Unknown",
  "dynasty": "5" | "6" | null,
  "sub_period": null,
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "Teti Pyramid Cemetery",
  "discovery_year": null,
  "discoverer": null,
  "is_unfinished": false,
  "is_uninscribed": false,
  "is_usurped": false,
  "attribution_certainty": "attested" | "probable" | "uncertain",
  "shared_with_tombs": [],
  "notes_from_pm": "..." | null,
  "source_citation": {"page": <int>, "edition": "PM III.2 2nd ed. 1978/1981", "section": "II"}
}
```

## tomb_id convention

**`TPC-<TitleCaseName>` for named-headword tombs WITHOUT an LS number** (descriptor convention parallel to chunks 10/13/19's `JKR-`/`JKE-`/`EF-`). `TPC` stands for "Teti Pyramid Cemetery". Descriptor is ASCII-only — drop ayin/underdot/macron from descriptor (apply them in occupant_name only). For PM's compound-headword `<NAME1> <NAME2>` (where NAME2 is the "good name" alt), use NAME1 only in the descriptor.

**`LS<N>` for LS-numbered tombs** (drop space from PM's `LS <N>`). Parallel to chunks 3/18/19's `LG<N>` convention. `LS` stands for "Lepsius Saqqara" — Lepsius's monument-list numbers used in the Teti pyramid area.

## Cemetery field assignment

All chunk-20 rows are within the **§ II.B AROUND TETI PYRAMID** banner. The cemetery field value is `"Teti Pyramid Cemetery"` (descriptor form parallel to chunks 3/10/11's `"Central Field"` / `"Junker West"` / `"Steindorff"`).

## How to identify a row

**Shape 1 — Named-primary descriptor headword.** Line `<NAME IN CAPS> <hieroglyphic glyph noise> <Title cluster>. <Dating>.` (no preceding `LS <N>.` prefix). For these, synthesise `tomb_id: TPC-<TitleCaseName>` from the leading all-caps name token. Title-case the name with diacritics applied in `occupant_name`. Examples expected in this chunk file include: KHENTKA IKHEKHI, NEFERSESHEMREʿ SHESHI, ʿANKHMAʿḤOR SESI, UZAḤATETI NEFERSESHEMPTAḤ SHESHI, PTAḤSHEPSES, MERERI, INTI.

**Shape 1 — Named LS-headword.** Line `LS <N>. <NAME IN CAPS> <hieroglyphic> <Title cluster>. <Dating>.` — same shape as chunks 3/18/19's LG form. `tomb_id: LS<N>`. Examples expected: LS 10 KAGEMNI MEMI.

**Shape 1b — "good name" alt-name idiom.** PM prints `<PRIMARY> <hieroglyphs> <ALT> <hieroglyphs>, <Title cluster>.` to encode the *rn nfr* "beautiful name" idiom. Per chunks-8/19 convention, primary name goes in `occupant_name`, alt name as a single entry in `occupant_alt_names`. Example expected: KAGEMNI MEMI → `occupant_name: "Kagemni"`, `occupant_alt_names: ["Memi", "Gemni"]` (PM's `(also GEMNI)` parenthetical adds the second alt). KHENTKA IKHEKHI → `occupant_name: "Khentka"`, `occupant_alt_names: ["Ikhekhi"]`.

**ROW-EMITTING vs OUT-OF-SCOPE.** Emit one row per:
- Each Shape-1 / Shape-1b named-primary descriptor headword in this page range.
- Each Shape-1 LS-headword in this page range.

Do NOT emit rows for:
- Sub-rooms (Room I., Room V., Outer Hall., Inner Corridor., Burial chamber., Façade., False-door., Doorway., (1)/(2)/(3) numbered scenes, etc.).
- Body-prose object mentions, museum-citation lines, publication references.
- Wife / parents / co-occupant clauses — these are captured via `co_occupants` on the parent row.
- Plan / Map / Synopsis references.
- The "(a) LATE DYNASTY VI AND 1ST INT. PERIOD" sub-period banner.

**Headword block ends** at the first sub-feature heading (`Room I.`, `Façade.`, `(1)`, `False-door.`, `Burial chamber.`, etc.) or museum-citation line.

## Expected row count

Pre-extraction structural scan: the chunk's printed-page range covers the Drioton 1943 publication cluster of small Dyn-VI mastabas of Teti's priestly clientele (Wernu, Khui, Thetut, Desi, Semdent, Meru Tetisonb, Gemniwser) PLUS the headline vizier-clientele tombs (Khentka Ikhekhi, Neferseshemreʿ Sheshi, ʿAnkhmaʿḥor Sesi, Uzaḥateti Neferseshemptaḥ Sheshi, Ptaḥshepses, Mereri) PLUS the daughter-of-Teti tomb (Inti) PLUS the LS 10 Kagemni Memi flagship. **Total expected: 15 rows (acceptable band 12–18).** If your count is below 12, re-scan: small Dyn-VI mastabas on printed pp.519–522 are easy to miss because their headword title clusters are short (`Wernu, Tenant of the Pyramid of Teti, etc.`). If your count is above 18, you've likely emitted sub-features or anonymous "TOMB WITH SEVERAL BURIAL CHAMBERS" / "NAME LOST" rows out of scope.

## Anonymous-row scope rule

The chunk file contains at least two PM-headworded anonymous entries that are EXCLUDED from this chunk: a `TOMB WITH SEVERAL BURIAL CHAMBERS` style entry and a `NAME LOST` entry. These would be Shape-5 anonymous in the chunk-19 sense, but chunk 20 deliberately omits them to keep scope tight on named primary headwords. They land in a follow-up chunk together with the Mereruka mega-block on phys p.165+.

## PM III.2 text-layer noise (chunk-20-relevant)

**Raised-ayin in occupant names.** PM uses raised-`a` / raised-`c` / `<` / `>` glyphs to encode the Egyptian ayin (the laryngeal consonant). pypdf renders these inconsistently: `MERYRE<` for `Meryreʿ`, `Cankhmachor` for `ʿankhmaʿḥor` (note also that pypdf swaps `c` for opening `ʿ` at the start of some names). Normalize all of these to `ʿ` (U+02BF) in `occupant_name`. tomb_id descriptor is ASCII-only — drop the ayin entirely (e.g., `TPC-AnkhmaHor`, NOT `TPC-ʿankhmaʿḤor`).

**Leading-ayin name.** PM's `CANKHMACI;IOR` text-layer noise resolves as `ʿAnkhmaʿḥor` (raised-ayin both leading and after `Ma`). The TPC descriptor drops both, yielding `TPC-AnkhmaHor`.

**Underdot-Ḥ glyph.** Apply on ḥ-root names per source-wide convention:
- HATHOR → Ḥathor (with underdot)
- ʿANKHMAʿḤOR → ʿAnkhmaʿḥor (the Horus-name compound carries underdot on the `mḥ` root)
- UZAḤATETI → Uzaḥateti (`zḥ` root, the "Sun-temple" theophoric Re-compound)
- NEFERSESHEMPTAḤ → Neferseshemptaḥ (`ptḥ` theophoric, terminal underdot)
- PTAḤSHEPSES → Ptaḥshepses (`ptḥ` theophoric)
- KHENTKA → Khentka (no ḥ)
- IKHEKHI → Ikhekhi (no ḥ)
- NEFERSESHEMREʿ → Neferseshemreʿ (Re-compound, no ḥ)
- SHESHI → Sheshi (no ḥ)
- KAGEMNI → Kagemni (no ḥ)
- MEMI → Memi (no ḥ)
- GEMNI → Gemni (no ḥ)
- MERERI → Mereri (no ḥ)
- INTI → Inti (no ḥ)

**Macron-Ē on Re-deity-compound names.** PM uses raised-ayin AND macron-Ē when an Egyptian theophoric name compounds with Re (the sun-god). `NEFERSESHEMRE<` → `Neferseshemreʿ` (macron + ayin). OCR vowel rule: `REa` / `RE<` → `Rēʿ` (macron); `RAa` / `RA<` → `Raʿ` (no macron).

**OCR drift on Old Kingdom raised-ayin.** Where PM uses raised-`c` for the Late-Period ayin (chunks 3 / 12 convention), the OK chunks use raised-`a` (chunks 2/8/10 convention). Chunk-20 follows the OK convention.

**"Wife, <NAME>" body-prose preservation.** Per chunks 9–19 convention — capture wife in `co_occupants` + her title cluster in `co_occupant_roles` (`"Wife, <title>"` form). Preserve `, etc.` markers. Example expected: KAGEMNI MEMI → wife Nebty-nubkhet Seshseshet (`co_occupants: ["Nebty-nubkhet Seshseshet"]`, `co_occupant_roles: ["Wife, King's daughter of his body"]`).

**"Parents, <NAME> and <NAME>" / father / mother clauses.** Similar to wife — capture in `co_occupants` + role string with `Father, ...` / `Mother, ...` / `Probably parents, ...` prefixes. Use PM-faithful order.

## Field-by-field rules

- **`tomb_id`** — `TPC-<TitleCaseName>` for descriptor named-primary (ASCII, no diacritics); `LS<N>` (drop space) for LS-numbered.
- **`memphite_area`** — Always `"Saqqara"`.
- **`occupant_name`** — Title-cased with diacritics applied. `null` only for explicitly anonymous tombs (none expected in this chunk).
- **`occupant_alt_names`** — `[ "<AltName>" ]` for the "good name" idiom (the secondary personal name); also includes `(also <NAME>)` parenthetical alternates. PM-faithful order if multiple.
- **`tomb_aliases`** — Empty.
- **`co_occupants`** — Wife, parents per body-prose clauses. PM-faithful order. Apply diacritics.
- **`co_occupant_roles`** — Length-coupled. `"Wife, <title>"`, `"Father, <title>"`, `"Mother, <title>"`, `"Probably parents, ..."`, etc.
- **`is_joint_burial`** — `false` for all chunk-20 rows (no joint-named twins expected).
- **`occupant_role`** — Controlled vocab. `"Vizier"` for Chief Justice and Vizier / Real Chief Justice and Vizier. `"Princess"` for King's daughter of his body (e.g., INTI). `"High Priest"` for Greatest of the ḥm-nṯr / Greatest of the craftsmen (wr-ḫrp-ḥmwt = High Priest of Ptaḥ at Memphis) — none expected in this chunk. `"Prophet of <X>"` alone or `Inspector of prophets` alone is NOT `High Priest` — generic priestly title → `"Official"`. `Count` + `Overseer of ...` + `Inspector of prophets of the Pyramid of Teti` → `"Official"`. Most named tombs in this chunk → either `"Vizier"` (for Chief Justice and Vizier) or `"Official"` (for everything else non-royal).
- **`dynasty`** — Roman→Arabic. `Temp. Teti` → `"6"` (Teti is Dyn VI founder). `Temp. Pepy I` → `"6"`. `Early Dyn. VI` → `"6"`. `Middle Dyn. VI or later` → `"6"`. `Dyn. V` → `"5"`. `Late Dyn. VI and 1st Int. Period` → `"6"` (Dyn-VI tail; 1st Int. Period is sub_period if needed but stays null per source-wide convention for non-Saite chunks).
- **`sub_period`** / **`date_bce_*`** — `null`.
- **`cemetery`** — Always `"Teti Pyramid Cemetery"`.
- **`discovery_year`** / **`discoverer`** — `null`.
- **`is_unfinished`** / **`is_uninscribed`** / **`is_usurped`** — `false` unless PM HEADWORD literally contains the token.
- **`attribution_certainty`** — `"attested"` for clean Shape-1 / Shape-1b named-primary. `"uncertain"` only for anonymous (no anonymous rows expected in this chunk).
- **`shared_with_tombs`** — Empty.
- **`notes_from_pm`** — Headword block prose (title cluster + dating + parents/wife clauses + immediate-position clause like `South-east of tomb of Khentka Ikhekhi.`). Drop occupant name, hieroglyphic-noise glyphs, `Map LII.` / `Plan LIII.` cartographic references, sub-feature headings, museum-citation lines. Preserve `Temp. <King>.` and `(probably <X>)` parentheticals. For the "good name" idiom, drop the alt-name from notes (it lives in occupant_alt_names).
- **`source_citation`** — `{"page": <printed page>, "edition": "PM III.2 2nd ed. 1978/1981", "section": "II"}`. Page boundary rule: printed = physical + 360. Use the printed page where the HEADWORD opens.

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk20: <count> rows; <shape1>/<shape1b>/<shape1ls> split; <anomalies or "none">
```

Where shape1 = pure named-primary descriptor (no alt-name idiom), shape1b = "good name" alt-name idiom rows, shape1ls = LS-headword rows. Under 100 words.
