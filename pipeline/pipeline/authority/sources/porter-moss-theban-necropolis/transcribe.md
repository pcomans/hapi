# Transcription method — Porter-Moss Vol I (Theban Necropolis)

Per ADR-017 + the Phase-0 playbook (`docs/playbook-phase-0-ocr-transcription.md`), with a documented method deviation: **no OCR step**.

## Source

Two PDFs, both Griffith Institute free-distribution scans (downloaded from `griffith.ox.ac.uk/topbib/pdf/`):

| Volume | File in `proprietary/books/` | SHA-256 |
|---|---|---|
| PM I.1 (Private Tombs) | `Porter & Moss - PM I Theban Necropolis.pdf` | `1d98326920f18faa25c3273c0c3b1b38dbc9fe18faeae07fa89f873a47a75455` |
| PM I.2 (Royal Tombs and Smaller Cemeteries) | `Porter & Moss - PM I.2 Royal Tombs and Smaller Cemeteries.pdf` | `bd79be57b1180ea8766d0f8195a35d99dd02bfd986c0caf4f0026e568b209a42` |

The two volumes share a continuous printed page numbering — PM I.1 ends at p.493, PM I.2 begins at p.495. References to "printed p.N" disambiguate by volume only when N is in the overlap (which it isn't — the volumes are sequential).

## Method deviation: text-layer extraction replaces OCR subagent

**ADR-017 specifies an OCR subagent for scan-only sources.** The PM I.2 PDF distributed by the Griffith Institute carries a publisher text layer — the scan was OCRed at the source. Verified by `pypdf.PdfReader(...).pages[n].extract_text()` returning the printed prose verbatim (with the typical post-1960s lithographic-OCR noise — see "Known text-layer noise" below). **The OCR subagent step is therefore unnecessary** and would only re-OCR the same scan worse than Griffith already did.

The substitute step is deterministic text-layer extraction:

```bash
cd pipeline && uv run python -c "
import pypdf
r = pypdf.PdfReader('proprietary/books/Porter & Moss - PM I.2 Royal Tombs and Smaller Cemeteries.pdf')
text = ''.join(p.extract_text() + chr(12) for p in r.pages[36:60])  # physical p.37-60
open('pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/chunk-p37-p60.txt', 'w').write(text)
"
```

This file is gitignored (`raw/*` per the repo-root `.gitignore`) — same rule as OCR chunks. It contains verbatim copyrighted prose; same redistribution constraint as an OCR transcript.

After the text-layer dump lands, run `postprocess.py` against each chunk file in place — it normalises the publisher OCR's reproducible glyph-class noise into canonical Unicode (`J:I`/`I:I`/`I;I`/`l:I`/`I:J` → `Ḥ`; `<` adjacent to a letter → `ʿ`; whitelisted Egyptian-name `c` → `ʿ` for tokens like `Smenkhkarec`/`Rec`/`Takhact`; `[Ist ed.` → `[1st ed.`; king-name-anchored Roman numerals `Ill`/`Il`/`11` → `III`/`II`) so the 3-agent extraction sees the same canonical form across runs instead of diverging on glyph readings. The fixup table is documented in `postprocess.py`'s module docstring; tests in `pipeline/tests/test_porter_moss_postprocess.py` lock the per-rule behaviour and the bidirectional digit hazard (catalog numbers like `5I109` and years like `I922` must NOT be rewritten).

```bash
cd pipeline && uv run python pipeline/authority/sources/porter-moss-theban-necropolis/postprocess.py \
    --input pipeline/authority/sources/porter-moss-theban-necropolis/raw/chunk-p89-p106.txt
```

The postprocessor is idempotent (every rule's RHS does not contain its LHS); re-running on its own output is a no-op.

**Downstream stages are unchanged from the playbook:** three parallel extraction subagents read the postprocessed `raw/chunk-*.txt` and produce JSONL; `merge.py` majority-votes; `fix_rows.py` applies LLM-reviewer corrections; tests assert specific values.

The Dodson-Hilton precedent (PR #38, main-session OCR for chunk 2 after subagent OCR refused on chunk 1) covers the more general principle: when the playbook's default OCR-subagent path is unnecessary, document the deviation in `transcribe.md` and proceed with the substitute. The Dodson-Hilton case substituted main-session OCR for subagent OCR; this case substitutes deterministic text-layer extraction for any OCR at all.

## Chunks

Multi-chunk source. Each chunk is its own PR; this file's "Chunks" section is updated as chunks land.

| Chunk | Section | Printed pages | Physical pages | Status | PR |
|---|---|---|---|---|---|
| 1 | KV1–KV10 (PM I.2 § I.A) | p.495–518 | p.37–60 | landed | #66 |
| 2 | KV11–KV20 (PM I.2 § I.A) | p.518–548 | p.60–90 | landed | #68 |
| 3 | KV22–KV46 (PM I.2 § I.A, sparse) | p.547–564 | p.89–106 | landed | #69 |
| 4 | KV47–KV57 (PM I.2 § I.A, sparse) | p.564–569 | p.106–111 | landed | #70 |
| 5 | KV62 Tutʿankhamun (PM I.2 § I.A, headword only) | p.569–570 | p.111–112 | landed | #71 |
| 6 | KV63–KV65 sweep / § I.A closure (no rows) | p.586–592 | p.128–134 | landed | #?? |
| 7 | PM I.2 §§ II + III.A/C/D — South-West Valleys + Dra' Abu el-Naga (Antef Cemetery Dyn XI + Ahmose-Nefertari + Seventeenth Dynasty Cemetery BURIALS) | p.590–606 | p.132–148 | landed | #100 |
| 8 | PM I.2 § X.A Valley of the Queens — 20 numbered QV tombs (QV33–QV75 sparse) | p.751–768 | p.292–313 | landed | #?? |
| 9 | PM I.1 § I "Numbered Tombs" — TT1–TT10 Deir el-Medina core (10 rows) | p.1–19 | p.19–37 | landed | #196 |
| 10 | PM I.1 § I "Numbered Tombs" — TT11–TT20 Dra' Abu el-Naga (10 rows) | p.21–37 | p.39–55 | landed | #198 |
| 11 | PM I.1 § I "Numbered Tombs" — TT21–TT30 (heterogeneous: Sh. ʿAbd el-Qurna / Dra' Abu el-Naga / ʿAsâsîf, 10 rows) | p.35–46 | p.53–68 | landed | #199 |
| 12 | PM I.1 § I "Numbered Tombs" — TT31–TT40 (heterogeneous: Sh. ʿAbd el-Qurna / Khokha / ʿAsâsîf / Dra' Abu el-Naga / Qurnet Muraʿi, 10 rows) | p.47–78 | p.65–96 | landed | #200 |
| 13 | PM I.1 § I "Numbered Tombs" — TT41–TT50 (heterogeneous: Sh. ʿAbd el-Qurna / Khokha, 10 rows) | p.78–95 | p.96–115 | landed | #202 |
| 14 | PM I.1 § I "Numbered Tombs" — TT51–TT60 (homogeneous: Sh. ʿAbd el-Qurna, 10 rows; first PM-I.1 anonymous-occupant headword TT58, two Vizier rows TT55+TT60) | p.97–121 | p.115–141 | landed | #204 |
| 15 | PM I.1 § I "Numbered Tombs" — TT61–TT70 (homogeneous: Sh. ʿAbd el-Qurna, 10 rows; second anonymous-occupant variant TT70, bracketed-fragment headword TT68, two Vizier rows TT61+TT66, one High Priest TT67) | p.123–139 | p.141–160 | landed | #205 |
| 16 | PM I.1 § I "Numbered Tombs" — TT71–TT80 (homogeneous: Sh. ʿAbd el-Qurna, 10 rows; one High Priest TT72, one usurpation TT77, d-bar TT80 Ḏhutnūfer, alt-name TT79 Menkheper/Menkheperraʿsonb, primary-attribution-hedge TT73 → uncertain) | p.139–157 | p.157–177 | landed | #207 |
| 17 | PM I.1 § I "Numbered Tombs" — TT81–TT90 (homogeneous: Sh. ʿAbd el-Qurna, 10 rows; one Vizier TT83 ʿAmethu/ʿAhmosi, one High Priest TT86 Menkheperraʿsonb shared with TT112, one partly-usurped TT84 Amunezeḥ→Mery, alt-names TT85+TT88+TT83, third within-source NEBAMŪN collision TT90 after TT17/TT65) | p.159–183 | p.177–201 | landed | #208 |
| 18 | PM I.1 § I "Numbered Tombs" — TT91–TT100 (homogeneous: Sh. ʿAbd el-Qurna, 10 rows; anonymous TT91 — third such variant after chunk-14 TT58 + chunk-15 TT70; Vizier TT100 Rekhmirēʿ; two High Priests TT95+TT97 First prophets of Amūn; TT95 Mery is the USURPER of TT84 — chunk-17 cross-ref captured via verbatim parenthetical + DERIVER_OVERRIDE on is_usurped; within-chunk Sennufer name collision TT96+TT99) | p.185–215 | p.203–233 | landed | #210 |
| 19 | PM I.1 § I "Numbered Tombs" — TT101–TT110 (homogeneous: Sh. ʿAbd el-Qurna, 10 rows; two Vizier rows TT103 Dagi + TT106 Paser — both "Governor of the town and Vizier"; bracketed-fragment headword TT104 `[Hutnufer]` (PM `[H]utnufer` with bracket-fragment + plain-H per strip-Ḥ-from-tomb_id rule) with cross-tomb-ref `shared_with_tombs: ["TT80"]` from PM `(See tomb 80.)`; d-bar TT110 `Ḏhout`; regnal-date hedge TT108 `Temp. Tuthmosis IV(?)` → attribution_certainty="attested" via DERIVER_OVERRIDE; parent-identification hedge TT110 `Pesediri(?)` → attribution_certainty="attested" via DERIVER_OVERRIDE) | p.214–227 | p.232–246 | landed | #263 |
| 20 | PM I.1 § I "Numbered Tombs" — TT111–TT120 (homogeneous: Sh. ʿAbd el-Qurna, 10 rows; **4 anonymous rows** TT114/115/116/119 — highest density of anonymous-occupant headwords in any single decade so far; TT112 Menkheperraʿsonb usurped by ʿAshefytemweset with `shared_with_tombs: ["TT86"]` cross-ref to chunk-17 TT86; TT117 Dyn. XI tomb re-used by Zemutefʿankh in Dyn. XXI-XXII; TT120 ʿAnen `occupant_alt_names: ["Mahu"]` from Gardiner & Weigall Cat. external-catalogue label; regnal-date hedges TT116 + TT118 `Temp. Amenophis III(?)` → attribution_certainty="attested" via DERIVER_OVERRIDE) | p.229–235 | p.247–253 | landed | #264 |
| 21 | PM I.1 § I "Numbered Tombs" — TT121–TT130 (homogeneous: Sh. ʿAbd el-Qurna, 10 rows; 9 Official + 1 anonymous TT129 "Name lost"; **first chunk-21 joint burial** TT122 `[Amen]ḥotp` + Amenemḥet — "both Overseers of the magazine of Amūn" — is_joint_burial=true with co_occupants=["Amenemḥet"] + parents Wazmosi/Tetisonb noted; TT127 Senemiʿoḥ usurped in Ramesside times (deriver fires is_usurped=true); TT128 PATHENFY "Mayor of Edfu, Mayor of the City"; TT130 MAY Harbour-master Tuthmosis III(?); 4 regnal-date hedges TT121/126/127/130 `(?)` on regnal date → attribution_certainty="attested" via DERIVER_OVERRIDE) | p.235–246 | p.253–264 | landed | #265 |
| 22 | PM I.1 § I "Numbered Tombs" — TT131–TT140 (10 rows; **first heterogeneous sub-site chunk since chunk-13**: TT131–TT139 Sh. ʿAbd el-Qurna + TT140 Dra' Abu el-Naga; 9 Official + 1 anonymous TT136 "Royal scribe ... of the Lord of the Two Lands"; TT131 AMENUSER or User with shared_with_tombs=["TT61"] (PM `(See tomb 6z.)` decoded as TT61 not TT62 — bidirectional cross-reference with TT61 Vizier User, both Temp. Tuthmosis III; same Egyptological person); TT134 1st-edition cross-numbering note `(1st ed. 135)`; TT140 Ḥefia OCR-damaged alt-name (`~EFIA` reading flagged for egyptologist verification); 9 CHUNK22_CORRECTIONS for OCR-decode + diacritic restorations; 7 tie-break overrides; 1 DERIVER_OVERRIDE) | p.245–254 | p.263–272 | landed | #266 |
| 23 | PM I.1 § I "Numbered Tombs" — TT141–TT150 (10 rows; **all Dra' Abu el-Naga** — first homogeneous-DAN decade since chunk-10's TT11–TT20; 8 Official + 2 anonymous TT143 "Name lost" + TT147 anonymous "Head of the masters of ceremonies(?)"; TT150 USERḤET unfinished is_unfinished=true; TT142 + TT143 tomb-numbers absent from OCR (assigned via page-273 running header `Tombs I4I, r42, and I43`); TT146 OCR `q.6.` decoded as 146; 3 CHUNK23_CORRECTIONS (TT141 wʿab-priest ayin + TT143/TT147 occupant_role); 7 tie-break overrides on Amūn macron splits; 5 DERIVER_OVERRIDES on regnal-date hedges) | p.254–262 | p.272–280 | landed | #267 |
| 24 | PM I.1 § I "Numbered Tombs" — TT151–TT160 (10 rows; **all Dra' Abu el-Naga** — second consecutive homogeneous-DAN decade; 7 Official + 1 High Priest TT157 NEBWENENEF "First prophet of Amūn temp. Ramesses II" + 2 anonymous TT152/TT153 "Name lost"; TT151 ḤETY unfinished is_unfinished=true; TT152 usurpation `Usurped in Ramesside times(?)` → is_usurped=true via deriver; TT155 [ANTEF] bracket-fragment; TT156 PENNESUTTAUI Ḥ-residual cluster; TT159 RAʿY/Raʿya ayin handling; 3 CHUNK24_CORRECTIONS + 3 tie-break overrides + 4 DERIVER_OVERRIDES regnal-date hedges) | p.261–275 | p.279–293 | landed | #268 |
| 25 | PM I.1 § I "Numbered Tombs" — TT161–TT170 (10 rows; 9 Dra' Abu el-Naga + 1 Sh. ʿAbd el-Qurna TT170 NEBMEHY(T); 9 Official + 1 anonymous TT167 unfinished+name-lost; TT162 KENAMUN (cone-attribution; A's Ḳenamun overruled 2/1 by B+C plain-K); TT162+TT163 inaccessible state-marker; chunk-file initially missed TT161 headword on p.292 — re-extracted with extended boundary; 1 CHUNK25_CORRECTIONS + 0 tie-break overrides + 3 DERIVER_OVERRIDES regnal-date hedges) | p.274–279 | p.292–297 | landed | #269 |
| 26 | PM I.1 § I "Numbered Tombs" — TT171–TT180 (10 rows; **first Khôkha-dominated decade** — 1 Sh. ʿAbd el-Qurna TT171 + 9 Khôkha TT172–TT180 (Khôkha sub-site not used since chunk-13); 7 Official + 3 anonymous TT171/TT175/TT180 "Name lost"/"No name"; TT177+TT180 unfinished; TT176 [Amen]userhet bracket-fragment; TT178 NEFERRONPET called KENRO alt-name; TT180 "Accessible from tomb 179" architectural access relation preserved verbatim (NOT shared_with_tombs); 3 CHUNK26_CORRECTIONS + 0 tie-break overrides + 3 DERIVER_OVERRIDES regnal-date hedges) | p.279–287 | p.297–305 | landed | #270 |
| 27 | PM I.1 § I "Numbered Tombs" — TT181–TT190 (10 rows; 8 Khôkha + 2 ʿAsâsîf TT189/TT190; all Official; **second coordinate-joint-burial in PM I.1** — TT181 NEBAMUN + IPUKY both sculptors temp. Amenophis III to IV (after TT122 [Amen]ḥotp + Amenemḥet chunk-21); TT190 ESBANEBDED Saite tomb usurped from Ramesside — Esbanebded is USURPER not victim, is_usurped=False via DERIVER_OVERRIDE per TT95/Mery precedent; TT189 NEKHT-ḎHOUT d-bar (3-way 1/1/1 tie resolved by PDF p.295 cite); chunk-file initially started at p.305 missing TT181 headword on p.304 — re-extracted with extended boundary; prompt initially claimed TT191 absent in PM (incorrect — TT191 IS present as boundary marker); 5 CHUNK27_CORRECTIONS + 4 tie-break overrides + 2 DERIVER_OVERRIDES) | p.286–298 | p.304–316 | in-progress | (this PR) |

The physical-to-printed offset for PM I.2 is **+458** (printed = physical + 458 / physical = printed − 458). Verified at chunk-1's first and last printed pages, at chunk-2 boundaries, and at chunk-3 boundaries — no part-boundary drift within the KV1–KV46 span. Foldout plates (Plan II at the start of § I; the shared plan p.528 for KV11–KV14 Finds; the plan p.548 for KV20/22/23/38; the plan p.552 for KV34/35/42) and figure pages occupy intervening physical pages; the chunk ranges each cross a floor-plan page but the offset is stable across KV headwords.

Absence patterns within PM I.2 § I.A:
- **KV21** is absent — the list jumps from KV20 to KV22 (chunk-2 boundary).
- **KV24–KV33** are absent — the list jumps from KV23 to KV34 (chunk-3 boundary). These numbers are assigned to real tombs by modern surveys but were not catalogued as inscribed royal tombs in the 1964 PM I.2 edition.
- **KV37, KV40, KV41, KV44** are absent from chunk 3's range.
- **KV49–KV54, KV58–KV61** are absent from chunk 4's range (PM jumps 48 → 55 and 57 → 62).
- **KV63–KV65** are absent from PM I.2 1964 entirely (chunk 6 sweep). KV63 was discovered 2005, KV64 in 2011, KV65 in 2019 — all post-date PM I.2's 2nd edition. PM I.2 § I.A ends with KV62; the volume immediately continues with § I.B "Finds from the Valley of the Kings" (physical p.128 / printed 586), § I.C "Rest-houses and Shrines" (printed 588), § I.D "Graffiti" (printed 590), then § II "South-West Valleys" (printed 592). Those sections are a separate concern from the tomb-row extractor and land as later chunks if at all.

**PM I.2 § I.A KV tomb-row coverage is now complete**: chunks 1–5 delivered 37 rows covering KV1–KV62 (with the absences enumerated above). Chunk 6 formally closes the KV series — no rows added, just this documentation + roadmap update.

Chunk 2's file is `raw/chunk-p60-p90.txt` (31 physical pages) — includes p.60 to capture KV11's headword at the tail and extends through p.90 so the agents can see the `Tombs 20, 22, 23, 38` plan marking the KV20 / KV22 boundary. Chunk 3's file is `raw/chunk-p89-p106.txt` (18 physical pages) — includes p.89 to capture KV22's headword at the tail (KV20's body is out of scope) and extends through p.106 so the agents can see the KV47 heading as a boundary marker closing KV46.

**Chunk 7 — descriptor tomb_id convention.** Chunk 7 is the first chunk to extract from PM sections that do NOT use numbered tombs. § II South-West Valleys, § III Dra' Abu el-Naga (and later chunks will extend to § IV 'Asasif, § V Deir el-Bahri, § VII Sheikh Abd el-Qurna, § VIII Ramesseum, § IX Deir el-Medina, § XI Medinet Habu) each announce tombs by an occupant-name headword rather than a KV-style number. `tomb_id` uses `<PREFIX>-<TitleCaseDescriptor>` — `SWV-HatshepsutSouth`, `DAN-KamoseWadjkheperre`, `DAN-AntefSehertaui` — where the prefix is the valley code (`SWV` = South-West Valleys, `DAN` = Dra' Abu el-Naga; new prefixes added per section as chunks 8+ land). The descriptor is PM-faithful: preserve PM's letter choices (`Ahmosi` not `Ahmose`, `Mentuhotp` not `Mentuhotep`) with diacritics stripped and prenomen appended only for disambiguation. Chunk-7 extraction had three agents split on the `Ahmose/Ahmosi`, `Mentuhotep/Mentuhotp`, and `SebkemsafII/-SekhemreShedtaui/-IISekhemreShedtaui` canonical forms — the prompt has been updated to pin the PM-faithful variants, and a one-off `normalize_chunk7_ids.py` reconciled the first-pass agent output before `merge.py`. Future chunks using the descriptor form inherit the PM-faithful rule from `prompt-chunk-7-*.md`. The chunk-7 file is `raw/chunk-p132-p148.txt` (17 physical pages) — starts at p.132 (§ II.A's first page in § II SOUTH-WEST VALLEYS header at bottom) and extends through p.148 so agents see the `E. PETRIE EXCAVATIONS.` header at physical p.148 as a boundary marker that closes § III.D's BURIALS. Sub-sections in scope: II.A / II.B / III.A / III.C / III.D. Sections EXPLICITLY out of chunk-7 scope: § II.C (graffiti — not tombs), § III.B (Entrance to Valley of the Kings — rock-stelae + graffiti only), § III.E and later (excavator-organised find reports with minimal named-tomb headwords — land as a separate chunk if at all).

**Chunk 9 — PM I.1 § I "Numbered Tombs" TT1–TT10 (Deir el-Medina core).** First chunk drawn from PM I.1 (Private Tombs); chunks 1–8 all came from PM I.2. PM I.1's printed-page offset is **+18** (printed = physical − 18), distinct from PM I.2's +458 — verified at TT1 = printed p.1 = physical p.19. 10 rows TT1–TT10, every TT number in that decade is present (no gaps in the listing — unlike KV / QV which have many absences). All 10 rows share `theban_area="Deir el-Medina"` (Deir el-Medina workmen's tombs — Servants in the Place of Truth, Foremen, Chiseller, Scribe, Chief in the Great Place); all 10 rows assigned `occupant_role="Official"` (the controlled-vocab flattening of these specific titles, with the verbatim title preserved in `notes_from_pm`). Two joint-burial headwords: TT6 `NEFERḤŌTEP and son NEBNŪFER, Foremen…` (hierarchical — `is_joint_burial=false`, Nebnufer in `co_occupants`) and TT10 `PENBUY and KASA, Servants in the Place of Truth` (coordinate — `is_joint_burial=true`, Kasa in `co_occupants`). Three `shared_with_tombs` cross-references parsed from PM's `(Also owner of tomb N.)` / `(Perhaps also owner of tomb N.)` / `(also owner of tombs N and M)` headword phrasings: TT3→TT326, TT4→TT337 (hedged), TT7→TT212+TT250.

PM I.1 surfaced four new text-layer noise classes that PM I.2 did not: (1) `J.I` for capital underdot-Ḥ (single observed site `NEFERJ.IOTEP` in TT6 — added to `postprocess.py` Phase-1 substitution table alongside the existing five Ḥ-substitutes); (2) `( <space-cartouche>` for ayin at name end (TT8 `KHA( ~` → `Khaʿ`); (3) `I>.` for capital underdot-Ḳ (TT4 `I>.EN` → `Ḳen`); (4) `RAcMosi` for `Raʿmose` (whitelisted token-trailing `c` for ayin pattern). Patterns 2/3/4 are context-dependent and handled by prompt-level guidance + `CHUNK9_CORRECTIONS` rather than `postprocess.py` substitutions, since open-paren and `I>.` and trailing-c collide with non-ayin content elsewhere in the chunk text.

**Chunk 10 (TT11–TT20)** surfaced four additional PM-I.1 noise classes, all observed once each in the chunk file and all handled at prompt + `CHUNK10_CORRECTIONS` level (none promoted to `postprocess.py` for the same context-collision reason as chunk 9): (5) **tomb-number-position digit/letter substitution** — `12•` for `12` (bullet for period at TT12 headword), `zo.` for `20` (z→2, o→0 at TT20 headword) — the publisher OCR confuses Arabic digits with letters in headword position; the prompt's column-zero positional rule disambiguates; (6) **`<DIGIT>;I` cluster** for capital underdot-Ḥ (`Ḥ`) inside an all-caps name token (TT14 `1;I UY` → `ḤUY`); a Ḥ-residual variant beyond the chunk-9 `J.I` pattern; (7) **`:[>` cluster** for capital underdot-Ḍ (`Ḍ`) at the start of an all-caps name token (TT11 `:[>ḤOUT` → `ḌHOUT`); analogous to chunk-9's `I>.` for underdot-Ḳ; (8) **mid-dot/bullet for trailing apostrophe** in the recurring sub-site declaration `Dra' Abû el-Naga'.` (rendered `Dra· Abu el-Naga·.` / `Dra· Abu el-Naga•.`); the canonical `theban_area="Dra' Abu el-Naga"` (chunk-7 convention) absorbs the variation. None of these patterns recurred at multiple call sites in chunk 10, so no postprocess promotion was justified — collision risk with non-tomb-headword content (e.g. the `12•` pattern would over-fire on body-prose decimal numbers, the `:[>` pattern on bracketed citations) is too high.

Chunk 10 also surfaced two **text-layer name-glyph misreads** beyond the postprocessable noise classes: the `n` → `m` ligature error in two wife-name positions (TT16 `Ternūte` extracted as `Termite`, TT17 wife fragment `Ta . . . nūfer` extracted as `Ta . . . mūfer`). These are not postprocessable (no unambiguous bigram signature; both halves of the substitution are valid English-word fragments) and were caught by the egyptologist printed-source review, which ships PDF-cited `CHUNK10_CORRECTIONS` entries restoring PM's printed values. The same OCR class is documented in chunk-9 as the `Tent-ḥōm` macron-position misread; in chunk 10 it crossed into a name-character class for the first time.

Chunk 9 also surfaced one Tier-3-deriver edge case: PM I.1 TT2's headword reads `... Wives, Saḥte and (probably) Esi.` — the `(probably)` qualifies the second wife's identification, NOT Khaʿbekhnet's primary attribution. The context-free `_detect_attribution_certainty` regex fires on any `(probably)` in `notes_from_pm`, so it incorrectly derives `attribution_certainty="probable"` for TT2. Resolved by adding a per-row `DERIVER_OVERRIDES` mechanism in `fix_rows.py` that runs AFTER the regex pass and pins TT2 back to `"attested"` with a citing rationale. The override mechanism is scoped to the single TT2 case and explicitly documented as "for secondary-clause hedges that PM does not apply to the primary occupant"; later chunks may extend the list as similar cases surface.

CHUNK9_CORRECTIONS applies 9 egyptologist printed-source corrections per the chunk-9 reviewer pass: (a) the `.).` → `.)` redundant-double-period strip on TT2/TT6/TT7/TT8/TT10 (merge majority stitched a paragraph break with an extra period that PM does not print); (b) drop false underdots inserted by extraction agents on `Ḥuy`/`Nezemtbeḥdet` (TT3), `Ḥenutmeḥyt` medial (TT4), `Maḥi` (TT5), `Tent-ḥōm` (TT9); (c) restore macrons that agents stripped against the chunk-3/7 macron-preserve precedent — `Amūn`+`Thonūfer` (TT4), `Neferḥōtep`+`Nebnūfer` (TT6), `Taēsi` (TT5), `Irnūfer` (TT10).

**Chunk 13 (TT41–TT50, 10 rows)** is the second decade where all rows fall into just two sub-sites: 7 in `Sh. ʿAbd el-Qurna` (TT41–46, TT50) and 3 in `Khokha` (TT47–49). One usurpation (TT45 — Ḏhout original, Ḏḥutemḥab usurper); two `called <ALT>` alt-name patterns (TT41 Amenemōpet/Ipy, TT48 Amenemḥet/Surero); one tomb-state marker (TT47 `(Inaccessible.)`); one within-decade NAME collision (TT49 and TT50 both `Neferhotep` — distinct individuals, distinct fields). Chunk 13 extends the d-bar `Ḏ` (U+1E0E) convention for the Thoth/Djehuty d-emphatic to PM I.1 TT45 `Ḏhout` (matches the chunk-12 PR #200 TT32 `Ḏhutmosi` precedent + the chunk-7 / chunk-8 / PR #151 d-bar precedent across PM I.2 — the consistency check confirmed by direct PDF visual on physical p.103 headword `ḎḤOUT`). CHUNK13_CORRECTIONS layers 4 egyptologist-cited PDF-verified corrections: TT41 `Amenemopet` → `Amenemōpet` (capital macron-Ō drop, same OCR class as chunk-11 TT29 / chunk-12 TT33+TT34+TT39); plus 3 spurious-double-period strips on TT41/TT47/TT49 `notes_from_pm` (the `.).` → `.)` class that went 2/1 the wrong way at reconciliation rather than 1/1/1 — chunk 13 is the first chunk where the wrong form had a real majority instead of just an OCR-noise tie). DERIVER_OVERRIDES adds 4 chunk-13 entries for `attribution_certainty` regnal-/usurper-clause hedges (TT41, TT43, TT45, TT46) — same chunk-9 TT2 + chunk-10 cluster + chunk-11 TT22 precedent that the deriver's context-free `(?)` regex over-fires on regnal-date hedges that don't qualify the primary occupant's identification.

**Chunk 13 process note: page-marker omission.** The chunk-13 extraction script initially wrote `raw/chunk-p96-p115.txt` separating pages with bare form-feed `\f` characters but WITHOUT the `===== PHYSICAL PAGE N (PRINTED PAGE M) =====` markers used by chunks 9–12. The 3 extraction agents had to derive `source_citation.page` from running-headers (`Tomb N`, `Tombs N and M`); 2 of 3 agents converged on the correct page numbers but agent A drifted on 5 of 10 rows (TT41–44 and TT46), pulling the page from a stale running-header read. The merge majority vote rescued the page numbers (B and C correct on all rows), so the on-disk reconciled.jsonl is unaffected; but the failure mode was a near-miss for a rule-2 silent-failure regression. Fix going forward: the extraction snippet (re-run for this PR after the agents completed, idempotent; this version of the file IS what's on disk now and is byte-equivalent to what the prompt's `===== PHYSICAL PAGE` rule expected) writes the page markers explicitly. Future chunks must use this snippet shape; the prompt's `===== PHYSICAL PAGE` rule is the authoritative source-page convention.

**Chunk 14 (TT51–TT60, 10 rows)** is the first PM-I.1 decade where every row falls into a single sub-site (`Sh. ʿAbd el-Qurna`, all 10 rows). New patterns: (a) **first PM-I.1 anonymous-occupant headword** (TT58 `58. Name unknown, ... Usurped by AMENḤOTP and his son AMENEMONET, Dyn. XX.`) — `occupant_name=null`, `occupant_role="Unknown"` per the chunk-8 KV12/KV39/KV56/QV36/QV40/QV73/QV75 precedent; the OCR substitutes `s8` for `58` in the tomb-number position so the anonymous shape stayed below the agents' headword regex initially (had to widen the pre-extraction scan); (b) **two Vizier rows** TT55 `Raʿmosi` ("'Stuart's Tomb'", Governor of the town and Vizier, Temp. Amenophis IV) and TT60 `Antefoḳer` (Governor of the town and Vizier) — Vizier-precedence rule applied per chunk-11 TT29; (c) **TT60 mother as hierarchical co-occupant** (`<NAME-A>, ..., and mother, SENT, Prophetess of Ḥatḥor.`) — first PM-I.1 hierarchical pattern outside the chunk-9 TT6 `<NAME-A> and son <NAME-B>` shape; mother in `co_occupants[]` with role `Official`, `is_joint_burial=false`. CHUNK14_CORRECTIONS layers 6 PDF-cited corrections: 4 capital-macron restorations on `occupant_name` (TT51 `Userhet` → `Userhēt`, TT53 `Amenemhet` → `Amenemhēt`, TT56 `Userhet` → `Userhēt`, TT57 `Khaʿemhet` → `Khaʿemhēt` — all the same `-emḤĒt` capital-macron-drop class as chunk-12 TT34 `MENTUEMḤĒT`), 1 macron restoration on `notes_from_pm` (TT58 `Amenemonet` → `Amenemōnet` per the chunk-11 TT29 `Amenemōpet` precedent), and 1 controlled-vocab pairing fix (TT58 `occupant_role` `null` → `"Unknown"` enforcing the chunk-8 null-name pairing invariant). Tracking issue #203 opened to audit chunk-13 TT47 (likely same `Userhet` → `Userhēt` correction). 5 tie-break overrides on chunk-14 (all cosmetic `notes_from_pm` punctuation/diacritic ties). DERIVER_OVERRIDES adds 2 entries for TT52/TT54 regnal-date `(?)` hedges per the established occupant-vs-regnal certainty distinction.

**Chunk 8 — PM I.2 § X.A Valley of the Queens numbered tombs.** Returns to the numbered-tomb form (`QV<n>`, matching chunk 1's KV pattern). 20 rows extracted from printed pp.751-768 / physical pp.292-313: QV{33, 36, 38, 40, 42, 43, 44, 46, 47, 51, 52, 53, 55, 60, 66, 68, 71, 73, 74, 75}. Chunk-8 file `raw/chunk-p292-p314.txt` extends through physical p.314 so agents see `XI. MEDYNET HABU` / `TOMBS INSIDE ENCLOSURE. DYN. XXII-XXVI.` as a boundary marker closing § X.A. Explicitly out of scope: § X.B (Unnumbered tombs and pits — find-level inventory), § X.C (Finds), § X.D (Graffiti), § XI Medinet Habu (future chunk). QV1–QV32 never catalogued in the 1964 edition; QV34/35/37/39/41/45/48-50/54/56-59/61-65/67/69/70/72/76-80 absent from § X.A. Agent A initially under-counted (missed QV60, emitting 19 rows) but agents B and C caught it via the explicit headword at p.761 and the plate caption `QUEENS' TOMBS, 60, 66, 68, 71, 73-5` at p.760 — merge retained the 20-row shape. Fix_rows.py CHUNK8_CORRECTIONS applies `occupant_role="Unknown"` on 4 null-name headwords (QV36 'A PRINCESS, no name', QV40 'A QUEEN, cartouche blank', QV73 'A PRINCESS, no name, Dyn. XX', QV75 'A QUEEN, no name') per the prompt rule that null names carry Unknown role — the KV12/KV39/KV56 precedent.

## Extraction prompt design rationale

PM headwords are short and structured — the FIRST line of each tomb's section carries the tomb number, the conventional-English occupant name in titlecase, the cartouches (which render as garbage), parenthetical bibliographic / classical-traveller cross-references, and a `Plan, p. N` marker. The body is multi-page descriptive prose detailing every wall, corridor, side-room, and ceiling — emphatically out of scope per the rights policy.

The extraction prompt at `prompt.md` instructs the agents to:
- Find each tomb's section by the regex pattern `^[0-9]+\.\s+[A-Z]` at line start.
- Extract only the headword line (the first paragraph after the tomb-number heading).
- Drop everything from "Corridor", "Hall", "Room", "Side-room", "Approach", "Pillars", "Ceiling", "Sarcophagus" headers onward.
- Preserve the literal `Unfinished` flag and `See also Tomb N` cross-references when present.
- Emit `null` for any field absent from the headword (do not infer from body prose).

This keeps the extract on the safe side of the fact / expression line for copyright purposes AND keeps each agent's output narrow enough to majority-vote consistently.

## Known text-layer noise

Predictable artifacts in the Griffith text layer that the extraction prompt must call out (and `fix_rows.py` may need to clean up):

- **`pi.` for `pl.`** (plate references). Example: `LEFEBURE, pi. xii` should be `pl. xii`. Doesn't reach our structured fields (sits in dropped body prose).
- **`1` for `l`** in word interiors (`pis.` for `pls.`, `Muh1k` for `Muluk`, `MoLLER` for `MOLLER`). Same: typically in dropped prose.
- **`BuRTON` capitalisation** (small caps in original render as `B`+`u`+`RTON` from the text layer). Doesn't affect our extract.
- **Cartouche garbage**: PM prints the royal cartouches inline (e.g. `(o│|║) (∘|)│`); the text layer outputs combinations like `(~~~ ::) ( e~ f ~g ffi_ j j gJ` or `(•~~)`. The titlecase English name BEFORE the cartouches is the canonical handle. Drop the cartouche garbage entirely. Phase A re-acquires the cartouches from a typed king authority (pharaoh.se / Beckerath).
- **`Re c` for `Reʿ`** (Egyptological ayin rendered as a separated `c`). When this appears in a king-name (e.g. `Khepermaʿtreʿ Ramesses VI` → text layer: `Khepermac trec`), normalise via `fix_rows.py`'s `_WORD_LEVEL_FIXES`-style table. Same template as Baud's `_WORD_LEVEL_FIXES` for the `ꜥd-mr → ꜥḏ-mr` case.
- **`sox` for `501`, `sos` for `505`** etc. (page numbers in running headers OCRed as letter forms). The structured `source_citation.page` is parsed from the start-of-tomb context, not from running headers, so this typically doesn't bite. Cross-check during reviewer pass.
- **Printed-page numbers in the running header sometimes float off-line** (lithographic margin drift). When `prompt.md` asks the agent to attribute a tomb to a page, the agent should use the `Plan, p. N` reference inside the tomb's headword OR the running-header page number from the first body page after the tomb number, not the running header on the tomb-number line itself.

### Bigram-uniqueness audit for new postprocess substrings

When `postprocess.py` adds a new context-free substring substitution in `_SUBSTRING_FIXES`, the new substring's left-hand side must not appear in normal English prose anywhere in the source or future source PDFs. The rule's docstring claims "verified by grep over raw/chunk-*.txt", but the `raw/*.txt` files are gitignored (CLAUDE.md rule 1, rights policy) so a CI test can't enforce the claim. The audit is therefore a **manual grep procedure** every time a new substring is added:

```bash
# From the repo root, verify the bigram (or substring) does not appear
# anywhere in any raw chunk text file. The grep should print no hits;
# any hit is a potential false-positive site that must be inspected
# before adding the rule.
cd pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/
grep -E '<NEW-SUBSTRING-PATTERN>' raw/chunk-*.txt
```

Examples of past audits:
- `J.I` (added in chunk-9 PR for capital underdot-Ḥ in the PM-I.1 text-layer): single hit `NEFERJ.IOTEP` in `raw/chunk-p18-p40.txt` (TT6's headword); no other occurrences across all chunks. The bigram-uniqueness claim holds.
- `J:I`, `I:I`, `I;I`, `l:I`, `I:J` (the original five Ḥ-substitutes from chunks 1-3): all verified by the same grep procedure when added.

The `tests/test_porter_moss_postprocess.py::test_capital_h_underdot_j_period_i_does_not_misfire_on_synthetic_text` covers the substitution-shape invariant against synthetic fixtures (sentence-end author initials, lowercase-`l` Pushkin Mus. citations, lowercase-`j` Egyptian-suffix transliteration). The test does NOT exercise the `raw/` files. The structural limit is documented in CLAUDE.md rule 9 (generated-file convention) and rule 1 (rights policy). When a new substitution rule is added, run the manual grep AND extend the synthetic-fixture test to cover any new collision shapes.

## Reproducibility

To re-extract the chunk-1 text layer:
```bash
cd pipeline && uv run python -c "
import pypdf
r = pypdf.PdfReader('proprietary/books/Porter & Moss - PM I.2 Royal Tombs and Smaller Cemeteries.pdf')
text = ''.join(p.extract_text() + chr(12) for p in r.pages[36:60])
open('pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/chunk-p37-p60.txt', 'w').write(text)
"
```

Form-feed (`chr(12)` = `\f`) separates per-page output so the extraction agent can recover physical-page boundaries when assigning `source_citation.page`. The PDF SHA pinned above + `pypdf` version (`pyproject.toml`) are sufficient to re-derive the byte-identical chunk text.

## Provisional-status disclaimer

Per ADR-017 step 6: `reconciled.jsonl` is **provisional** until human Egyptologist sign-off. The LLM `egyptologist-reviewer` subagent does NOT satisfy this — it is "LLM checking an LLM" per ADR-017's own framing. Human review logged at `human-review-<YYYY-MM-DD>-<chunk>.md` per chunk; un-reviewed chunks remain provisional even after the LLM review pass.
