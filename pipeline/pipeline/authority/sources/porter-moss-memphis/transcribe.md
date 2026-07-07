# Transcription method — Porter & Moss Vol III (Memphis)

Operational notes for the Phase-0 pipeline. The protocol itself lives in `docs/playbook-phase-0-ocr-transcription.md`.

## Source

- **Vol III.1** *Memphis. Part I. Abû Rawâsh to Abûsîr*, 2nd ed., 1974, ed. Málek. PDF SHA-256 `27777b018b327ffd3e5a009cb02d00a8c4bc314a7bff7042af005231a58955ec`. **460 physical pages** (complete: printed pp.1–360 continuous). **Re-fetched 2026-07-04** from `topbib.griffith.ox.ac.uk/pdfs/pm3-1.pdf` to replace an earlier defective scan (SHA `4817c0e0…e167e58`, 349 pp.) that was missing printed pp.313–359 (all of Abûsîr). NB physical pagination differs from the old scan, so chunks 1–35 physical-page refs are relative to the old file; printed-page `source_citation` values remain canonical.
- **Vol III.2** *Memphis. Part 2. Ṣaqqâra to Dahshûr*, 2nd ed., 1978/1981 fascicles, ed. Málek. PDF SHA-256 `dabb5c207642f1dd7a47de4f3db28f6c59d16ab3f0db8140c9672de3e7ed77df`. To be exercised at chunk 4+ (Saqqara work).

Both PDFs sit at `proprietary/books/` (gitignored, submodule).

## Method deviation (vs playbook step 3)

PM III PDFs carry an embedded text layer (verified 2026-05-15 for PM III.1 — `pypdf.PdfReader` produces extractable prose for every physical page sampled). Per the playbook's "Method deviation" provision and the Theban precedent (`porter-moss-theban-necropolis/transcribe.md`), the OCR subagent step is replaced by deterministic `pypdf` text-layer extraction:

```python
import pypdf
r = pypdf.PdfReader("proprietary/books/Porter & Moss - PM III Memphis.pdf")
with open("pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-1-p8-p32.txt", "w") as f:
    for i in range(7, 32):  # physical pages 8–32, 0-indexed
        f.write(f"\n=== physical page {i+1} ===\n")
        f.write(r.pages[i].extract_text())
```

The text-layer output goes to `raw/chunk-<n>-p<start>-p<end>.txt` (gitignored under the `raw/chunk-*.txt` pattern; same posture as Theban chunk files).

## Page-offset map (PM III.1)

The front matter consumes physical pages 1–7 (cover, half-title, title, contents i–vii). PM's printed-page numbering then begins at printed `p.1` = physical p.8 (Abû Rawâsh I. Pyramid). The offset is **`physical = printed + 7`** for the body; verify per-chunk because PM III front-matter pagination may drift (the printed contents page itself is `p.vii` in Roman but lives at physical p.5, etc.).

Page anchors confirmed via text-layer header scan (2026-05-15):

| Printed | Physical | Section |
|---|---|---|
| 11 | 8  | Pyramid-field of Gîza — I. PYRAMIDS — A. PYRAMID-COMPLEX OF KHUFU |
| 19 | 17 | B. PYRAMID-COMPLEX OF KHEPHREN |
| 27 | 24 | C. PYRAMID-COMPLEX OF MENKAUREʿ |
| 35 | 32 | (Menkaureʿ tail) → § II. GREAT SPHINX AREA |
| 49 | 46 | § III. NECROPOLIS — A. WEST FIELD (Cemetery G 1000+) |

## Pipeline

1. `pypdf` text-layer extraction → `raw/chunk-<n>-p<start>-p<end>.txt`.
2. Three parallel extraction subagents (general-purpose) run against `prompt-chunk-<n>.md` + the text-layer chunk, write `raw/agent-{a,b,c}-<chunk>.jsonl`.
3. `merge.py` — deterministic majority-vote, `tie-break-overrides.json` resolves 1/1/1 ties with a printed-source citation. Outputs `reconciled.jsonl` + `merge-disagreements.txt`.
4. `egyptologist-reviewer` subagent pass against the printed PDF pages (`reviewer-notes-chunk<n>.md`).
5. `fix_rows.py` applies reviewer corrections + post-merge normalisations to `reconciled.jsonl`.
6. `pipeline/tests/test_sources_porter_moss_memphis.py`.

## Chunk 1 scope

Physical pp.8–32 / printed pp.11–35: the three Gîza pyramid complexes (Khufu G1, Khephren G2, Menkaureʿ G3) and their attested queens' subsidiary pyramids. Expected ~8–12 rows. Establishes the `memphite_area` vocabulary and the Reisner G-number `tomb_id` convention.

PM III text-layer noise classes will accumulate from chunk 1 onwards into `postprocess.py` and per-chunk `CHUNK<N>_CORRECTIONS` tables. The Theban-source `porter-moss-theban-necropolis/postprocess.py` template carries OCR-noise rules portable to PM III where the same Griffith-Institute scan generation produced the same artifacts.

## Chunk 2 scope

Physical pp.176–187 / printed pp.179–190: Gîza Cemetery G 7000 East Field — Khufu's royal-family mastaba cluster opening with G 7000X (Hetepheres I shaft tomb, Khufu's mother) and continuing through the twin mastabas of Kawab+Hetepheres II (G 7110+7120), Khufukhaef I+Nefertkau (G 7130+7140), the Dyn-VI priestly intrusions G 7101 (Meryreanufer) and G 7102 (Iou) tied to the Pyramid-of-Pepy-I establishment, and ending with G 7150 Khufukhaef II under Neuserre. 13 rows from § III. NECROPOLIS — B. EAST FIELD.

Chunk-2 design choices:
- Twin-mastaba compound headwords like `G 7110+7120` emit TWO rows (one per Reisner number) with `shared_with_tombs` cross-reference. The compound is treated as PM's section header, not a row identifier.
- Bare-headword shafts (`G 7112.`, `G 7142.`) emit `occupant_name: null`, `occupant_role: "Unknown"`, `attribution_certainty: "uncertain"` rows. This required diverging from the Theban-source `merge.SENTINEL_NULL_STRINGS` — removing `"unknown"` from that frozenset so `"Unknown"` survives as a controlled-vocab value rather than collapsing to `None`. (The Theban source has the same latent bug — its `merge.SENTINEL_NULL_STRINGS` still includes `"unknown"`, and it papers over the issue with per-row `fix_rows.py` overrides on the (small number of) cases that surface. The Memphis approach fixes it at the merge layer instead. Future merges may consider converging the two sources on the Memphis pattern; for now they intentionally diverge.)
- Cemetery designation `"G 7000"` (formerly `null` in chunk 1) introduced for the East Field mastabas. PM's `CEMETERY G 7000` banner on printed p.182 sets the designation for the entire B. EAST FIELD section.
- The G 7000X Hetepheres I headword opens with a `1/1/1` tie on `notes_from_pm` (three agents truncated the headword block at three different sentence boundaries). Resolved via `tie-break-overrides.json` with a printed-source citation (PM III.1 p.179).

Chunk file text-layer SHA-256 pin: `886973b5663e748f282bb6147cc36d88e98f1f7fb43cda8ab46304cebeb4aa69`.

## Chunk 3 scope

Physical pp.285–289 / printed pp.288–292: Gîza Central Field — LG 100 Khentkaus I (the "Sarcophagus-shaped Tomb", End of Dyn IV or early Dyn V queen-mother) closing § III. E. CENTRAL FIELD Old-Kingdom block, then the Saite (Dyn XXVI) LG-numbered cluster: LG 81 (bare-headword anonymous, OCR-drift `LG 8 I` form), LG 83 (joint burial — Commander ʿAhmosi + his mother Queen Nekhtubasterau, wife of Amasis), LG 84 (Pakap, good name Wehebreʿ-emakhet), LG 97 (joint burial — Harsiesi + Harwoz, both wnrw-priests). 5 rows total.

Chunk-3 design choices:
- First LG-prefix tomb_id rows (Lepsius "Grab" numbering). Extends `merge.AREA_ORDER` with `"LG": 1` (sorts after Reisner G but within the same Gîza memphite_area).
- First joint-burial rows: `co_occupants` non-empty + `is_joint_burial: true`. LG 83 and LG 97 establish the schema for shared-tomb cases.
- First `sub_period` non-null rows: Saite-era Dyn XXVI carries `sub_period: "Saite"`. Old Kingdom rows in this chunk (LG 100) keep `sub_period: null`.
- First `cemetery: "Central Field"` rows (chunk-1 was `null` for pyramid-complexes; chunk-2 was `"G 7000"` for East Field).
- New OCR-drift rule for Saite raised-ayin: pypdf renders PM's Late-Period raised-ayin glyph as a literal `c` (in contrast to the chunks 1-2 raised-`a` for Old Kingdom names). LG 84's `WEHEBREc-EMAKHET` → `Wehebreʿ-emakhet` after U+02BF normalisation. A 1/1/1 tie on the three agents' variants resolved via `tie-break-overrides.json` with a cited PM III.1 p.290 rationale.
- LG-number OCR drift: pypdf renders `LG 81` as `LG 8 I` (Arabic 1 → Roman I with inserted space). The chunk-3 prompt's normalisation rule re-reads the Roman-block as Arabic.
- Out-of-scope no-LG-number tombs (THAIHARPATA, PEDUBASTE, PTAHARDAIS): each Saite-era tomb without a Lepsius / Reisner / Mariette identifier. Deferred to a follow-up chunk with the descriptor-tomb-id scheme (e.g. `CF-Thaiharpata`).

Chunk file text-layer SHA-256 pin: `83c4c224ca022c9e62a5563d1535a35e7ff3240d80cab6b5769306678abda8e7`.

## Chunk 4 scope (FIRST PM III.2 chunk)

Physical pp.61–72 / printed pp.421–432 of PM III.2 (Saqqâra-Dahshûr): the back half of § I. PYRAMIDS at Saqqâra — the Dyn V/VI royal pyramid-complexes from F. Unis (Dyn V's last king) through K. Pepy II (Dyn VI's longest-reigning king), plus Pepy II's three queens' pyramid-enclosures (Neit, Iput II, Wezebten) and the anonymous Wife-of-Isesi queen-enclosure under H. 9 rows total: 5 kings + 4 queens.

Chunk-4 design choices:
- First chunk drawn from PM Vol III.2 (not III.1). Introduces `edition: "PM III.2 2nd ed. 1978/1981"` alongside chunks 1-3's `PM III.1 2nd ed. 1974`.
- First `memphite_area: "Saqqara"` rows (chunks 1-3 were all `Giza`).
- First `SAQ-`-prefix descriptor-form `tomb_id`s (machine-readable identifiers in `SAQ-<DescriptorName>` shape, e.g. `SAQ-Unis`, `SAQ-PepyII`, `SAQ-WifeOfIsesi`). Saqqâra pyramids lack a uniform Reisner-style or Lepsius-style numeric ID — the descriptor synthesises from the section's named royal occupant.
- `tomb_id` descriptors stay ASCII-only (no U+02BF ayin in identifiers — `SAQ-MerenreI`, NOT `SAQ-MerenrʿI`). The U+02BF ayin lives in `occupant_name` (`Merenrʿ I` per the 2/1 majority strict-rule normalisation; egyptologist-reviewer may post-process to the conventional `Merenreʿ I` form via fix_rows.py CHUNK4_CORRECTIONS).
- Extends `merge.AREA_ORDER` with `"SAQ": 2` (sorts after Reisner `G` and Lepsius `LG` numbered forms).
- New `pre_merge.py` mechanism for PM Memphis (cloned from D&H queens PR #218 precedent): `tomb_id_corrections-<chunk>.json` files apply OCR-drift tomb_id fixes BEFORE merge so a singleton-rejected mis-OCR'd row routes back into the canonical majority. Chunk-4 uses this for Agent B's `IPUT [II]¹` → `IPUT Il1` → `IPUT` mis-OCR and for Agent B's U+02BF-in-descriptor non-conformance on `MerenreI`.
- New `tomb_aliases` content: Saqqâra pyramids carry Arabic popular-names appended to their Lepsius identification line (e.g. Isesi's `Haram el-Shawwaf` — "the Sentinel Pyramid"). Extracted into `tomb_aliases` per the chunk-4 prompt's alias rule.
- Three new `tie-break-overrides.json` entries for chunk-4 1/1/1 ties on `notes_from_pm` (SAQ-IputII, SAQ-Neit, SAQ-MerenreI — agents disagreed on period-before-PYRAMID sentence-boundary preservation + raised-ayin normalisation).
- Out-of-scope `J. PYRAMID OF KAKAREʿ IBI` (Dyn VIII transitional king on printed p.426) — explicitly excluded from chunk 4 per the prompt's OUT-OF-SCOPE rule. Regression-pin in `test_chunk4_no_jay_kakare_ibi_row` guards against accidental inclusion.

Chunk file text-layer SHA-256 pin: `7c2a4a712c4419eb2b479c2f0e07a7ee350ad68989af2a08dbc17a16678916e3`.

## Chunk 5 scope (FRONT half of PM III.2 § I. PYRAMIDS)

Physical pp.33–57 / printed pp.393–417 of PM III.2 (Saqqâra-Dahshûr): the FRONT half of § I. PYRAMIDS at Saqqâra — sections A through E that chunk 4 left open. A. Teti (Dyn VI founder) + 2 queens (Iput, Khuit) + B. Userkaf (Dyn V founder) + C. Step Pyramid Enclosure of Neterikhet/Zoser (Dyn III) + D. Step Pyramid Enclosure of Sekhemkhet (Dyn III, unfinished) + E. anonymous 'Great Enclosure' (Probably Dyn III). 7 rows total: 4 kings + 2 queens + 1 unknown.

Chunk-5 design choices:
- Closes the front half of PM III.2 § I. PYRAMIDS pair-wise with chunk 4 (which did F-K). Combined chunks 4+5 give complete coverage of the Saqqâra royal-pyramid corpus excluding L–N (Shepseskaf Dyn IV, Userkareʿ Khenzer Dyn XIII, anonymous Dyn XIII — deferred to a follow-up chunk).
- First Dyn III rows in this source. Three rows carry `dynasty: "3"`: SAQ-Neterikhet (PM `Dyn. III`), SAQ-Sekhemkhet (PM `Dyn. III`), SAQ-GreatEnclosure (PM `Probably Dyn. III` → `dynasty: "3"` + `attribution_certainty: "uncertain"`).
- First Shape-3 anonymous row in PM Memphis: SAQ-GreatEnclosure has `occupant_name: null`, `occupant_role: "Unknown"`, `attribution_certainty: "uncertain"`. Distinct from chunk-4's `SAQ-WifeOfIsesi` (also `null` name but Shape-2 queen-enclosure under a known king's complex with role inferred as Queen). The Great Enclosure stands alone with no parent king's complex, hence `Unknown` role.
- First parenthetical-alias pattern: PM § I.C heads as `STEP PYRAMID ENCLOSURE OF NETERIKHET (Zoser)` — the parenthetical Zoser is captured in `occupant_alt_names`. Egyptologist-reviewer F4 finding added `Djoser` (museum-conventional spelling) as a second alt_name.
- First Step Pyramid sub-heading form (`STEP PYRAMID.` vs the `PYRAMID.` of chunks 1, 2, 4). Sections C and D use the Dyn III Step Pyramid heading variant; the chunk-5 prompt's Shape-1b rule handles both.
- First `is_unfinished: true` row in PM Memphis: SAQ-Sekhemkhet's `STEP PYRAMID. Unfinished.` sub-heading literally carries PM's `Unfinished` token.
- Egyptologist-reviewer printed-source pass against PM III.2 PDF surfaced three findings: (P1 F1) SAQ-IputI `occupant_name` corrected from interpolated `Iput I` to PM-faithful `Iput` with `Iput I` moved to `occupant_alt_names` — PM prints bare `IPUT¹` with footnote, NOT bracket-regnal like chunk-4's `IPUT [II]¹`; (P1 F3) SAQ-Khuit `notes_from_pm` extended to include the PM-printed footnote `King's wife (of Teti).` — the sole prosopographic justification for the Queen role classification; (P2 F4) SAQ-Neterikhet `occupant_alt_names` extended with `Djoser` for museum-Phase-A matching. All three captured in `fix_rows.py` `CHUNK5_CORRECTIONS`.
- The chunk-5 prompt is **self-contained** per the chunk-9 P1 #3 / chunk-11 PR-#196 precedent — full schema preamble inlined, no "re-read chunk N" cross-references.

Chunk file text-layer SHA-256 pin: `a30dfe883a9f31051cb20b19c0bdb6133b931cc02e98a283bae91c1cad0556a1`.

## Chunk 6 scope (FIRST PM III.1 § III.A West Field chunk)

Physical pp.46–62 / printed pp.49–65 of PM III.1: § III. NECROPOLIS — A. WEST FIELD opener and the Junker-excavated low-thousands cemeteries G 1000 / G 1100 / G 1200 / G 1300 / G 1400 / G 1500 / G 1600 / G 1900. 54 rows total: 30 Shape-1 named-primary rows + 24 Shape-2 bare-suffix (anonymous shaft) rows. Dense mix of Dyn IV-VI Old Kingdom officials.

Chunk-6 design choices:
- First chunk to open the West Field (chunks 1-3 covered § I PYRAMIDS Giza + § III.B East Field G 7000 + § III.E Central Field Saite; chunks 4-5 covered PM III.2 Saqqâra § I PYRAMIDS).
- Shape-2 bare-suffix rule formalised: PM rows like `G 1011. Dyn. V.` (dating only) and `G 1021.` (purely numeric stub) both emit one row with `occupant_name: null`, `occupant_role: "Unknown"`, `attribution_certainty: "uncertain"`. The dating marker, when present, goes to `dynasty`; the rest goes to `notes_from_pm`.
- First Shape-3 compound twin-mastaba in the West Field: `G 1452+1453. ZADUWAʿ` emits two rows (G1452 and G1453) sharing the compound's occupant-name token, each with `shared_with_tombs` cross-reference. Parallel to chunk-2's G 7110+7120 KAWAaB precedent.
- First underdot-Ḥ glyph normalisation for non-royal names: PM prints Meḥyt (the cobra-goddess of Thinis) with underdot-Ḥ in G 1201 WEPEMNEFERT's headword. pypdf renders the underdot glyph as mid-word uppercase `H` (`MeHyt`). Three-agent 1/1/1 tie resolved via `tie-break-overrides.json` with PM-faithful Egyptological normalisation. Parallel to chunk-3's LG 84 `Wehebreʿ-emakhet` raised-ayin normalisation.
- Egyptologist-reviewer printed-source pass against PM III.1 PDF surfaced 3 P1 findings + 3 P2 findings, all captured in `fix_rows.py` `CHUNK6_CORRECTIONS`:
  - (P1 F1) G 1607 Iʿan `is_unfinished: true` reverted to `false`: PM's `unfinished` token appears in body prose (`Rock-cut tomb, unfinished.`), NOT in the headword block. Agent A's deriver over-fired on body content.
  - (P1 F2) G 1234 occupant_name `ʿAnkh-Haf` → `ʿAnkh-haf`: museum-conventional lowercase-haf form (parallel to chunk-3 LG 84's `Wehebreʿ-emakhet` lowercase post-hyphen locative element). Critical for Phase-A matching against Boston/Met records.
  - (P1 F3) G 1221 SHAD notes_from_pm `Shad (?) (?)` → `Shad (?)`: pypdf text-layer stuttered the hedge token (line 432 of chunk-6 text file); PM prints `(?)` once.
  - (P2 F5) G 1207 NUFER + G 1227 SETHIHEKNET `occupant_role: Royal Family` → `Official`: `Royal acquaintance (woman)` (rḫt-nswt) is a non-royal honorific, not a royal-family descent indicator.
  - (P2 F6) G 1020 + G 1104 MES-SA + G 1204 AKHTIHOTP `occupant_role: Unknown` → `Official`: named occupants with no title cluster default to `Official` (the chunk-6 prompt's role-derivation rule had no `named-no-title` entry; Unknown is reserved for Shape-2 bare-suffix).
- New `tie-break-overrides.json` entries for chunk-6 1/1/1 ties: G1151 (KEDNUFER colon vs semicolon + ayin form), G1201 (Meḥyt underdot-Ḥ), G1221 (SHAD double-hedge stutter).
- Three 2/1 ties on notes_from_pm dropped to 0 disagreements after fix_rows reviewer corrections.

Chunk file text-layer SHA-256 pin: `de6da4216c0653448bf1cf06787cc736ce7d102eab85e88417bb6389865c1416`.

## Chunk 7 scope (West Field G 2000 + G 2100 + Mastaba G 2220)

Physical pp.63–80 / printed pp.66–83 of PM III.1: § III. NECROPOLIS — A. WEST FIELD continuation. Two cemetery banners + the eponymous Mastaba G 2220 cluster. 46 rows total: mix of Shape-1 named-primary, Shape-2 bare-suffix, Shape-3 compound-twin (G 2092+2093 NIMAʿETREʿ).

Chunk-7 design choices:
- **Duplicate `G 2156` disambiguation.** PM uses the Reisner number `G 2156` for TWO distinct mastabas — Kanenesut II (east of G 2155, p.79) and Redenes (south of G 2220, p.80). PM cross-references the second occurrence with `There is another G 2156 east of G 2155 (see p. 79).` All three extraction agents detected the duplicate and emitted two rows with the same `tomb_id`. A chunk-7 pre-merge dedup pass (`normalize_chunk7.py`) renames the second-occurrence row to `tomb_id: "G2156b"` (lowercase-letter suffix per the existing regex convention) while preserving the cross-reference in `notes_from_pm`. This is the first PM-source duplicate-Reisner-number case in this source; sets the convention for future cases.
- **G 2100-I-annexe → `tomb_id: "G2100a"`.** PM prints `G 2100-I-annexe.` for Merib's annexe to G 2100 (King's son of Khufu, Greatest of the seers in On). The "I-annexe" annotation is descriptor information not numeric, but the lowercase-letter suffix `a` per the existing tomb_id regex preserves the parent-G-2100 relationship while keeping the row distinct. The "I-annexe" detail itself lives verbatim in `notes_from_pm`.
- **`normalize_chunk7.py` script** strips occupant-name prefixes from `notes_from_pm` for Shape-1 named rows. The chunk-7 prompt's "verbatim from PM headword block" rule was interpreted by agents as "keep the name in notes", but the chunks 1-6 convention drops the name (lives in `occupant_name`). The normalisation aligns chunk 7 with the source-wide convention. Committed for reproducibility (rerun-on-fresh-extraction = same result).
- Three tie-break-overrides.json entries for chunk-7 1/1/1 ties: `G2100a|notes_from_pm` (raised-ayin normalisation in `Menkaureʿ`), `G2156b|notes_from_pm` (cross-reference clause preservation). The `G2001|notes_from_pm` tie originally added in this chunk was retired after the name-prefix normalisation collapsed it to a unanimous form.
- Compound twin `G 2092+2093` NIMAʿETREʿ produces two rows with `shared_with_tombs` cross-refs (parallel to chunks 2 + 6 precedents).

Chunk file text-layer SHA-256 pin: `c200f8771307e263e6b9c5d24ecf0788ca8ce3a173e7734ef9018f77c2cea7f4`.

## Chunk 8 scope (West Field G 2300 + G 2400 + G 2500)

Physical pp.80–92 / printed pp.83–95 of PM III.1: § III. NECROPOLIS — A. WEST FIELD continuation. Two PM banners — `CEMETERY EN ECHELON. NORTH PART WITH MASTABAS G 2300 AND 2400` (split internally by Reisner-number range into the G 2300 + G 2400 sub-clusters) + `CEMETERY G 2500`. 33 rows total: 17 Shape-1 named-primary + 16 Shape-2 bare-suffix; no Shape-3 compound twins in this chunk.

Chunk-8 design choices:
- **Chunk boundary trimmed at `CEMETERY G 3000`.** First-pass extraction covered phys pp.80–118 but PM's `CEMETERY G 3000` banner (Fisher Minor Cemetery, Penn Expedition; entirely distinct cluster) opens on phys p.92. The chunk file was re-cut to phys pp.80–92 with a `text.find('CEMETERY G 3000')` truncation, ensuring chunk 8 covers only the Reisner Cemetery en Echelon + Cemetery G 2500 material. The G 3000 cluster moves to a future chunk.
- **Cemetery field assigned by Reisner-number range, not banner wording.** The `CEMETERY EN ECHELON. NORTH PART WITH MASTABAS G 2300 AND 2400` PM banner spans two Reisner-number ranges (2300–2399 and 2400–2499). Per the chunk-8 prompt's cemetery field-rule, rows in the 2300 range carry `cemetery: "G 2300"`, rows in the 2400 range carry `cemetery: "G 2400"`. CEMETERY G 2500 contributes the single G 2501 row with `cemetery: "G 2500"`.
- **"good name" alt-name idiom standardisation.** Egyptian *rn nfr* "beautiful name" — the secondary personal name many OK officials used alongside their primary name. PM prints `<PRIMARY> good name <ALT>` in the headword. Chunk-8 codifies the convention: primary in `occupant_name`, alt in `occupant_alt_names` as a single entry. Three chunk-8 rows demonstrate the pattern (verify against PM PDF pp.85–87): G 2370 SENEZEMIB good name INTI, G 2378 SENEZEMIB good name MEḤI, G 2381 MERYRĒʿ-MERYPTAḤʿANKH good name NEKHEBU.
- **Compound theophoric occupant_name with underdot-Ḥ.** PM prints `MERYRE^a-MERYPTAH^aANKH` in caps with raised-ayin glyphs both pre-hyphen and intra-name. Normalised form `Meryreʿ-Meryptaḥʿankh` puts underdot-Ḥ on the *ptḥ* theophoric root (Egyptological convention) and preserves both ayins as U+02BF. Post-hyphen `Meryptaḥʿankh` keeps the capital `M` per the chunk-7 `Nefer-Maʿet` precedent for two-half compound names in caps. The same pattern applies to G 2387 `Pepy-Meryptaḥʿankh`.
- **Headword-level joint-burial declaration.** PM prints `G 2415. WERI and wife METI. Late Dyn. V.` — the `and wife` coordinate-name phrasing within the headword itself (not buried in body prose) triggers `is_joint_burial: true`. The wife is captured in `co_occupants` (`["Meti"]`) + `co_occupant_roles` (`["Wife"]`). The tie-break override on `notes_from_pm` selects the lowercase `and wife Meti.` form (continuation of dropped primary name, not sentence-start `And`).
- **Wife-attestation in body prose preserved when adjacent to headword.** G 2423 MEḤU's headword ends `... Prophet of Maʿet, etc. Dyn. V-VI.` and the next printed line is `Wife, Khenit / Stone-built mastaba.` The wife-attestation `Wife, Khenit.` appears in the body but immediately adjacent to the headword block, and the agents reasonably treated it as part of the headword. Tie-break override keeps the wife clause in `notes_from_pm` AND captures `Khenit` in `co_occupants` independently.
- **Bare-suffix letter-suffix rows.** G 2347a is the first chunk-8 letter-suffix-headword row where PM prints `G <NNNN>a.` on its own line with NO occupant name or dating marker. Per Shape-2 rule: `notes_from_pm: null` (selected via tie-break override). Distinct from chunk-7's G 2100a (annexe with full body content) and chunk-6's bare-suffix shafts (purely numeric).
- 6 tie-break-overrides.json entries for chunk-8 1/1/1 ties: `G2347a|notes_from_pm` (Shape-2 null), `G2381|notes_from_pm` (ayin + shaft-prefix drop), `G2381|occupant_name` (underdot-Ḥ + post-hyphen cap), `G2387|occupant_name` (same pattern), `G2415|notes_from_pm` (lowercase `and` continuation), `G2423|notes_from_pm` (ayin in Maʿet + wife clause).

Chunk file text-layer SHA-256 pin: `c71edc42bf958accf20228ed58242565086607e99474a8d2c8a41dc37e86f080`.

## Chunk 9 scope (West Field Cemetery G 3000, Fisher Minor Cemetery)

Physical pp.92–96 / printed pp.95–99 of PM III.1: § III. NECROPOLIS — A. WEST FIELD continuation. One PM banner — `CEMETERY G 3000` ('The Minor Cemetery'. Fisher Excavation. The Eckley B. Coxe Jr. Expedition of the University of Pennsylvania, 1915). 14 rows total: 13 Shape-1 named-primary + 1 Shape-2 bare-suffix (G 3015 dating-only headword); no Shape-3 compound twins.

Chunk-9 design choices:
- **Chunk boundary trimmed at `JUNKER CEMETERY (WEST)` banner.** The Junker / Steindorff cemeteries on physical pp.97+ use a fundamentally different identifier convention — tombs are PM-headworded by occupant NAME alone (no Reisner G-number), with occasional `S <NNNN>/<NNNN>` Steindorff-style numbers. That requires a new tomb_id convention (descriptor form like `JKR-Irty`) and a different prompt. Chunk 9 is therefore deliberately scoped to PM's G 3000 Reisner-numbered cluster only; the named-tomb clusters land in a future chunk.
- **Annexe-pair single-row rule** (distinct from chunk-7 G 2100-I-annexe split). G 3098 carries TWO occupants under one Reisner number: (a) IYMERERY waʿb-priest of the King's mother + wife Personet; (b) NEFERḤETPES-WER (woman) King's adorner in the north-east annexe, daughter of Duareʿ King's son. PM prints `G 3098 with annexe.` followed by inline (a)/(b) sub-blocks. Per the chunk-9 prompt rule, this emits ONE row with `tomb_id: G3098`; the annexe occupant is captured via `co_occupants` and the annexe-position phrase preserved in `notes_from_pm`. Distinct from chunk-7's `G 2100-I-annexe` where PM gives the annexe its own separately-headworded Roman-numeral-suffixed line → split into G2100a as a sub-row.
- **Wife-clause role string tie pattern.** Four of the chunk's 14 rows (G 3008 / G 3050 / G 3093 / G 3098) carry "Wife, <NAME> <Title cluster>" body-prose lines adjacent to the headword. All four wife-clause role strings triggered 1/1/1 ties across the three agents, on three orthogonal axes: (1) Ḥathor underdot-Ḥ vs plain Hathor (chunk-8 PR #227 P1-3 convention applied uniformly); (2) personal name in `co_occupants` field vs packed into `co_occupant_roles` string; (3) inclusion vs exclusion of body-mastaba-line trailer in `notes_from_pm`. 8 tie-break-overrides resolve these (4 rows × 2 fields each).
- **`waʿb-priest` title cluster ayin normalisation.** PM prints the *w3b*-priest title as `waab-priests` in the text layer (raised-`a` glyph rendered as plain `a`). Per source-wide raised-`a` → U+02BF ayin convention, normalise to `waʿb-priests`. Applied to G 3008 and G 3098 notes via tie-break override.
- 8 tie-break-overrides.json entries for chunk-9 1/1/1 ties: `G3008|notes_from_pm`, `G3008|co_occupant_roles`, `G3050|notes_from_pm`, `G3050|co_occupant_roles`, `G3093|notes_from_pm`, `G3093|co_occupant_roles`, `G3098|notes_from_pm`, `G3098|co_occupant_roles`.

Chunk file text-layer SHA-256 pin: `ac8d99495fa4475d2549154ba624bdaffdcc09b58251f9e2db34108eb1a2368d`.

## Chunk 10 scope (West Field JUNKER CEMETERY (WEST), Junker named-tomb cluster)

Physical pp.97–105 / printed pp.100–108 of PM III.1: § III. NECROPOLIS — A. WEST FIELD continuation. One PM banner — `JUNKER CEMETERY (WEST)` (Junker Excavation. Akademie der Wissenschaften in Wien + Pelizaeus-Museum Hildesheim + University of Leipzig Expedition, 1926-7). 30 rows total: 18 Shape-1 named-primary + 5 Shape-2 S-numbered (Steindorff form) + 7 Shape-3 bracketed-Roman-regnal named.

Chunk-10 design choices:
- **JKR descriptor tomb_id convention.** First chunk to use named-headword Junker tombs (no Reisner G-number). Synthesise `JKR-<TitleCaseAsciiName>` from PM's all-caps headword name token. Drop ayin/underdot from the tomb_id ASCII descriptor; they live in `occupant_name` only. Parallel to chunk-4's `SAQ-<KingName>` for Saqqâra royal pyramids without Reisner numbers.
- **Steindorff S-number form for bare-headword tombs.** PM prints `S <NUM>.` or `S <NUM1>/<NUM2>.` for Steindorff-excavated tombs without an attested occupant. Synthesise `tomb_id: S<NUM>` (first number only). Twin-numbered form preserves the second number in `tomb_aliases`. 5 S-numbered rows in chunk 10: S4040, S4233 (with `S 4283` alias), S4248 (with `S 4321`), S4399 (with `S 4507`), S4419.
- **Bracketed Roman regnal Shape-3.** PM disambiguates same-name individuals with bracketed Roman regnal (`[I]`, `[II]`, etc.). The chunk-10 prompt rule drops the brackets and appends the Roman to the name: `<Name> I` in `occupant_name` (space) and `JKR-<Name>I` in `tomb_id` (no space). 7 Shape-3 rows: SonbI, KhesefI, KhesefII, KhnemhotpII, PtahshepsesII, MeniI, MeniII.
- **Late Old Kingdom dating → Dyn VI.** Junker West tombs often carry `Late Old Kingdom.` rather than a specific dynasty number. Per chunk-10 prompt rule, Late OK → `dynasty: "6"` (terminal-Dyn-VI convention).
- **Cemetery descriptor `"Junker West"`.** Parallel to chunk-3's `"Central Field"` descriptor — Junker West has no Reisner G-NNNN identifier so the cemetery field uses a stable descriptor name.
- **SONB I single-row rule.** The largest chunk-10 headword block (PM `SONB [I` "full name") spans 3+ printed pages with elaborate chapel-decoration sub-features (Doorway, Offering-table, False-door panels (a)–(h), Pillars, Serdab, etc.). Per the chunk-10 prompt rule, this is ONE row — sub-features are dropped. Wife Sentiotes I (bracketed Roman regnal on co-occupant name) preserved in `co_occupants` + role string; Ḥathor underdot applied per chunk-8/9 convention.
- **JKR-Ithu three-co-occupant block.** PM's Ithu headword block names parents (probably) Iaʿib (Scribe) + Khaut I (mitrt) + wife Intkaes (mitrt). All three captured as `co_occupants`; the chunk-10 tie-break overrides + fix_rows correction maintain length-coupling with the 3-entry `co_occupant_roles`.
- **JKR-Inpuhotp multi-diacritic Re-compound.** PM's Inpuhotp (Anubis-priest) headword carries Saḥurēʿ + Neuserrēʿ + Rēʿ three Re-deity-compound royal names. Synthesised note preserves macron-Ē + ayin everywhere, plus underdot-Ḥ on the *sḥ* root of Saḥurēʿ.
- 10 tie-break-overrides.json entries for chunk-10 1/1/1 ties: `JKR-Ankh|co_occupant_roles`, `JKR-Irty|co_occupant_roles`, `JKR-Ithu|co_occupant_roles`, `JKR-Ithu|notes_from_pm`, `JKR-Iiu|co_occupant_roles`, `JKR-Iiu|notes_from_pm`, `JKR-MeniII|co_occupant_roles`, `JKR-Inpuhotp|notes_from_pm`, `JKR-Sinekhen|notes_from_pm`, `JKR-SonbI|notes_from_pm`. Plus 14 row-level reviewer corrections in `fix_rows.py` `CHUNK10_CORRECTIONS` covering: the JKR-Ithu co_occupants 3-entry expansion (length-coupling with the tie-break role override); the JKR-Inpuhotp 3-co-occupant bug fix (parents Ither + Sabt + wife Senezem); and Gemini PR #229 round-1 medium/high consistency fixes (mjtrt→mitrt normalisation, Ḥathor / ʿAnkh-ḥathor underdot restoration, bracket-regnal drop on cross-references, missing-period restoration, Maʿkherui ayin alignment, `Wife,` prefix consistency on SonbI / Sinekhen / Sinufer co_occupant_roles).

Chunk file text-layer SHA-256 pin: `d8f9807ac323cc0b8dfb2fb98d4223f82fee9d4936506005ec50ee40ba53610a`.

## Chunk 12 scope (Saqqâra § I.L-N royal complexes)

Physical pp.73–76 / printed pp.433–436 of PM III.2: § I. PYRAMIDS sections L, M, N. 3 rows: SAQ-Shepseskaf + SAQ-UserkareKhenzer + SAQ-DynXIIIAnon. Closes the back-half of PM III.2 § I that chunks 4 (F–K) and 5 (A–E) left open.

Chunk-12 design choices:
- **First chunk to emit `dynasty: "13"`** — Dyn XIII (Second Intermediate Period) for Userkareʿ Khenzer + the anonymous southern Dyn-XIII pyramid-enclosure. Distinct from chunk-5's anonymous Dyn-III Great Enclosure.
- **Mastabat el-Faraʿun alias normalisation.** PM prints `Mastabet Faraʿun` (typographic variant); chunk-12 normalises to the canonical `Mastabat el-Faraʿun` transliteration form used in museum catalogs and modern Egyptological literature (tie-break override on `SAQ-Shepseskaf|tomb_aliases`).
- **Userkareʿ Khenzer ayin.** PM prints `USERKARE< KHENZER` (text-layer renders raised-ayin glyph as `<`); normalise to `Userkareʿ Khenzer` per source-wide raised-ayin → U+02BF convention.
- **Anonymous Dyn XIII section N** descriptor synthesised as `SAQ-DynXIIIAnon` (PM gives no qualifying adjective in the headword block). Parallel to chunk-5's `SAQ-GreatEnclosure` anonymous-structure descriptor.
- **Lepsius Roman numerals without LG-number.** PM cites the Lepsius monument-list Roman numerals (`Lepsius, XLIII`, `Lepsius, XLIV`, `Lepsius, XLVI`) for these royal complexes but without modern LG Grab-numbers. Per chunk-12 prompt rule, keep these in `notes_from_pm` verbatim (not as `tomb_aliases` entries; those reserve for clean LG numbers).
- 1 tie-break-overrides.json entry for chunk-12 1/1/1 tie: `SAQ-Shepseskaf|tomb_aliases`.

Chunk file text-layer SHA-256 pin: `b790446628175210e0eb115ba2e51ecf19983465ce9b266b21a4fe8369ca8b57`.

## Chunk 11 scope (West Field STEINDORFF CEMETERY, halves 11a + 11b)

Physical pp.105–114 / printed pp.108–117 of PM III.1: § III. NECROPOLIS — A. WEST FIELD continuation, STEINDORFF CEMETERY banner (Steindorff Excavation, University of Leipzig + Pelizaeus Expedition 1903-7). 44 rows: 40 D-numbered tombs (Steindorff's own field numbering) + 4 STN- descriptor-form interstitial named tombs (Wemtetka, Ibir, Nu, Iri) without a D-number.

**Split into halves 11a + 11b** after the original full chunk-11 extraction failed across 6 subagent attempts (3 sonnet stalls + 3 opus socket errors). 11a covers D.I → D.38 + STN-Wemtetka + STN-Ibir (17 rows, physical pp.105–108); 11b covers D.39/40 → D.221 + STN-Nu + STN-Iri (27 rows, physical pp.108–114). Each half ran its own 3-agent extraction + merge cycle; tie-break-overrides and CHUNK11_CORRECTIONS accept both halves.

Chunk-11 design choices:
- **NEW D-number tomb_id convention** (`D1`, `D4`, `D15B`, `D39`, `D80`, ...). PM's `D. <NUM>` is Steindorff's own field numbering for the Leipzig+Pelizaeus excavation, NOT Mariette's Saqqâra D-prefix. This was a `/revise-priors` discovery — chunk-10's prompt had wrongly classified D-numbers as Mariette cross-references; the revise-priors marker file forced a prompt revision before extraction.
- **STN- descriptor form** for interstitial named tombs without a D-number (parallel to chunk-10's JKR- and chunk-4's SAQ- conventions): `STN-Wemtetka`, `STN-Ibir`, `STN-Nu`, `STN-Iri`. Only 4 interstitials in this chunk.
- **Cemetery descriptor `"Steindorff"`** (parallel to chunk-3's `"Central Field"` and chunk-10's `"Junker West"`). Single banner covers all 44 rows.
- **D.I (Roman one) normalised to D1 (Arabic).** Per chunk-11 prompt rule for the rare Roman-one opening form.
- **D.39/40 twin-number form.** Headword `D. 39/40.` emits ONE row with `tomb_id: D39` + `tomb_aliases: ["D 40"]` (PM-verbatim with space).
- **D.80/80 A twin-letter form.** Headword `D. 80/80 A.` emits ONE row with `tomb_id: D80` + `tomb_aliases: ["D 80A", "LG 22"]` (the Lepsius cross-reference lands as a separate alias).
- **D.15 ellipsis name truncation.** PM `D. 15. KHUFU . . ., King's waʿb-priest.` (private person, not the king). The chunk-11 prompt rule captures `Khufu` as occupant_name and notes the truncation. Same pattern applies to STN-Ibir.
- **D.37 RAaHERKA triple-diacritic.** Re-deity-compound (macron-Ē + ayin per chunks 4/8/10) + ḥ-root middle element (underdot-Ḥ per chunks 8/9). Canonical egyptological form `Rēʿḥerka`.
- **D.117 WEHEMKA three-co-occupant block.** Largest chunk-11 co-occupant cluster: father Iti + mother Zefatsen + wife Ḥetepibes called Ipi. Gendered Father/Mother/Wife role-prefixes preserved from PM's per-parent title clusters.
- **Joint-named twin headwords (Shape 4).** D.4 (Washptah + Khenu), D.32 (Memi + Neferḥerenptaḥ), D.203 (Nufer + Itisen), STN-Iri (Iri + Sebani). All emit ONE row with `is_joint_burial: true`.
- **D.207 TY (also Q Q) OCR drift.** The `Q Q` is pypdf's rendering of PM's two hieroglyphic alt-name signs (not text-layer-resolvable). Kept verbatim in notes_from_pm with `Ty` title-cased for readability.
- 14 tie-break-overrides.json entries for chunk-11 1/1/1 ties: `D1|notes_from_pm`, `D4|notes_from_pm`, `D15|notes_from_pm`, `D32|notes_from_pm`, `D37|occupant_name`, `STN-Ibir|notes_from_pm`, `STN-Wemtetka|notes_from_pm`, `D117|co_occupants`, `D117|co_occupant_roles`, `D203|co_occupant_roles`, `D207|notes_from_pm`, `D215|notes_from_pm`, `STN-Iri|co_occupant_roles`, `STN-Nu|notes_from_pm`. `CHUNK11_CORRECTIONS` starts empty; egyptologist-reviewer adds entries on the review pass.

Chunk-11a file text-layer SHA-256 pin: derived from `chunk-11-p105-p114-steindorff.txt` (full Steindorff extract) split at line 109 (D.38/D.39/40 boundary).
