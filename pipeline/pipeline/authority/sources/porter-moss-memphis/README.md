# Porter & Moss — Topographical Bibliography Vol III (Memphis)

Authority extract of named tomb-owners and named pyramid-complexes in the Memphite necropolis (Abû Rawâsh, Gîza, Zâwyet el-ʿAryan, Abû Ghurâb, Abûsîr, Saqqâra, Dahshûr, Lisht, Mêdûm). Companion to `porter-moss-theban-necropolis/` for the Memphite half of the corpus.

Met / Brooklyn / Harvard Old-Kingdom material is overwhelmingly Memphite. iDAI.gazetteer is too coarse to resolve Memphite provenances at the cemetery-level granularity museum records demand (~6 rows for Memphis/Saqqara/Giza/Abusir combined). PM III closes the gap for tomb-owner attribution and cemetery-level sub-site classification.

## Citation

- **Vol III, Part 1: Abû Rawâsh to Abûsîr** — Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part I. Abû Rawâsh to Abûsîr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1974).
- **Vol III, Part 2: Ṣaqqâra to Dahshûr** — Porter, B. & Moss, R.L.B. *Topographical Bibliography ... Volume III: Memphis. Part 2. Ṣaqqâra to Dahshûr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1978 / 1981 fascicles).

PDFs held in `proprietary/books/` (gitignored, not committed):
- `Porter & Moss - PM III Memphis.pdf` (Vol III.1) — SHA-256 `4817c0e09d126f387ffdc6793517caa125946aca1b6f4a5736a8daf32e167e58`
- `Porter & Moss - PM III Part 2 Saqqara-Dahshur.pdf` (Vol III.2) — SHA-256 `dabb5c207642f1dd7a47de4f3db28f6c59d16ab3f0db8140c9672de3e7ed77df`

Both are the Griffith Institute's free-distribution scans (downloaded from `griffith.ox.ac.uk/topbib/pdf/`), which carry an embedded text layer used by this extraction in lieu of running OCR. See `transcribe.md` § "Method deviation".

## Scope

**In scope** — one row per named tomb / named pyramid-complex in the Memphite necropolis with a known occupant.

Initial chunk (this PR): the three Gîza pyramid complexes (Khufu, Khephren, Menkaureʿ) and their attested queens' subsidiary pyramids, physical pp.8–32 / printed pp.11–35 of PM III.1. Subsequent chunks land the Gîza Necropolis (G 1000–G 7000 cemeteries — Reisner-numbered family mastabas around the pyramids, including G 7000X Hetepheres I and the East Field royal-family cluster), the Saqqâra pyramid complexes of Userkaf / Sahurēʿ / Neferirkarēʿ / Niuserrēʿ / Unas / Teti / Pepi I / Pepi II (PM III.2), and the named Saqqâra Old-Kingdom mastabas. Abûsîr Dyn-V sun-temples and Mêdûm are stretch / deferred.

**Out of scope** (do NOT extract):
- Per-room descriptive prose: relief catalogs, scene-by-scene epigraphy, plate references, sub-corridor breakdowns. PM's expressive content is the iconographic description, which is copyrighted scholarly expression — see "Rights" below. The headword line per tomb (tomb identifier + occupant + role + cartouches + bibliographic refs in parens) is fact; the body description is expression.
- Plates, plans, figures, photographs.
- Museum-object catalogs (Cairo Mus. Ent. ##### lists, statue inventories). Object-to-tomb provenance reconciliation is a separate Phase-A consumer concern, not Phase-0 extraction.
- Indexes 1–5 (cross-reference tables at the end of each volume) — useful as a downstream join but extracted in their own follow-up chunk if at all.

## Rights

Per the playbook's derived-extract default (`docs/playbook-phase-0-ocr-transcription.md` § "Rights policy"):
- The PDFs are NOT redistributed through this repo. They live in `proprietary/books/` (gitignored).
- Only `reconciled.jsonl` (factual rows: tomb_id → occupant → role → cemetery → dynasty) is committed. The verbatim text-layer chunk (`raw/chunk-*.txt`) stays gitignored.
- US copyright after *Feist v. Rural* does not protect raw factual compilations; the project's working assumption is that the committed extract is a fact compilation, not a derivative of PM's protectable expression. The chosen scope (headwords only, no scene descriptions, no museum-object catalogs) keeps the extract on the safe side of that line.

**Source-specific licence note (overrides nothing, supplements the default).** The Griffith Institute distributes PM Vol III PDFs from `griffith.ox.ac.uk/topbib` under their own terms. The PDFs themselves stay un-redistributed regardless of the broader US/UK fact-compilation framing. PDF stays gitignored, extract is fact-only.

## Schema

One row per tomb / pyramid-complex. All fields except `tomb_id`, `memphite_area`, and `source_citation` are nullable (per CLAUDE.md rule 4 — sparse rows are valid).

The chunk-1 extract example below shows what a typical row looks like after PM-headword extraction. Two notes on Phase-0 vs Phase-A boundaries:

- **`dynasty`** IS extracted when PM prints it in the headword block. PM III opens each pyramid-complex / cemetery section with an explicit `Dyn. <Roman>` line (e.g. `Dyn. IV` for the Giza pyramid-complex sections of Khufu/Khephren/Menkaureʿ); when this line is present in the headword block for a row, extract it as a Roman→Arabic string (`"4"`). When PM gives no dynasty in the headword block, store `null`.
- **`date_bce_approx_start` / `date_bce_approx_end`** stay `null` at Phase 0 — BCE dates come from the king authority (pharaoh.se / Beckerath / HKW) at Phase A, not from PM headwords.

```json
{
  "tomb_id": "G1",
  "memphite_area": "Giza",
  "occupant_name": "Khufu",
  "occupant_alt_names": ["Cheops"],
  "occupant_role": "King",
  "tomb_aliases": ["Great Pyramid", "First Pyramid"],
  "co_occupants": [],
  "is_joint_burial": false,
  "dynasty": "4",
  "sub_period": null,
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": null,
  "discovery_year": null,
  "discoverer": null,
  "is_unfinished": false,
  "is_uninscribed": false,
  "is_usurped": false,
  "attribution_certainty": "attested",
  "shared_with_tombs": [],
  "notes_from_pm": "Lepsius, IV; Perring and Vyse, I of Giza; Reisner, G I; called Great or First Pyramid.",
  "source_citation": {"page": 13, "edition": "PM III.1 2nd ed. 1974", "section": "I"}
}
```

**Diacritic-stripping policy (`occupant_name` vs `notes_from_pm`).** Same convention as `porter-moss-theban-necropolis/`: `occupant_name` strips scholarly diacritics for Phase-A name-authority joining (`MENKAUREʿ` → `Menkaureʿ`, `SAHUREʿ` → `Sahureʿ`); `notes_from_pm` is verbatim-preserve against PM's printed text including dropped macrons / underdot letters / ayins that the text-layer OCR loses.

PM III text-layer noise classes (will accumulate across chunks):
- `Khufu` (clean), `Khephren` (clean), `Menkaurea` → `Menkaureʿ` (PM prints with terminal ayin)
- `aAnemHo`, `ParaaemHab` (raised-`a` digraphs in royal-name compounds where text layer mangles the ayin); preserve in `notes_from_pm`, normalise to ayin in `occupant_name`.
- `KHA(` for `Khaʿ` (Khaʿbekhnet-style cartouche-stub artifact, already seen in Theban chunk 9).

**Field semantics:**
- `tomb_id` — Reisner G-number for Giza pyramids and cemeteries (`G1`, `G1a`, `G1b`, `G1c`, `G2`, `G3`, `G3a`, `G3b`, `G3c`, `G7000X` for Hetepheres I, `G2000` for a Reisner cemetery). For Saqqara: Lepsius `LS<n>`, Mariette letters (`D<n>`, `C<n>`, `S<n>`). For sites without a numbered designation: `<PREFIX>-<TitleCaseDescriptor>` (e.g. `GIZA-SphinxTemple`, `SAQ-PyramidUnas`) following the Theban chunk-7 precedent. Reproduce letter suffixes verbatim.
- `memphite_area` — Coarse Memphite sub-area: `"Abu Rawash"`, `"Giza"`, `"Zawyet el-Aryan"`, `"Abu Ghurab"`, `"Abusir"`, `"Saqqara"`, `"Dahshur"`, `"Lisht"`, `"Meidum"`. Diacritics stripped from the field VALUE (downstream join-friendly); PM-faithful diacritic forms appear in `notes_from_pm` where applicable.
- `occupant_name` — Conventional English form drawn from PM's headword. PM uses `Cheops` interchangeably with `Khufu` in older prose; preserve PM's headword form (the conventional `Khufu` for the Pyramid-complex sections); cross-resolution to alternate forms via the name authority.
- `occupant_alt_names` — Alternate name forms of the SAME PERSON (prenomen / Greek form / throne-name vs birth-name). Tomb-nicknames belong in `tomb_aliases`, not here.
- `tomb_aliases` — Popular names of the *tomb itself* (e.g. `Great Pyramid` for G1, `Second Pyramid` for G2, `Third Pyramid` for G3, `Mastabat el-Fara'un` for the Shepseskaf tomb). Empty list when PM gives no popular tomb-name.
- `co_occupants` — Additional people buried in the same tomb (joint burials). Schema same as the Theban variant: `[{"name": str, "role": str, "alt_names": list[str]}]`. Empty list for the common single-occupant case.
- `is_joint_burial` — Boolean flag for coordinate burials where PM does NOT mark a principal occupant. Same semantics as Theban.
- `occupant_role` — Controlled vocabulary (same as Theban): `King`, `Queen`, `Royal Family`, `Vizier`, `Official`, `High Priest`, `Princess`, `Prince`, `Unknown`. Pyramids almost always `King`; subsidiary queen's pyramids `Queen` (or `Unknown` when anonymous).
- `dynasty` — Roman-numeral dynasty as a STRING (`"4"`, `"5"`, `"6"`, `"III"`, etc. — final form normalised to Arabic numerals). Null when PM does not state dynasty in the headword.
- `sub_period` — Optional finer chronological label. Null for most rows.
- `date_bce_approx_start` / `date_bce_approx_end` — Negative integers (BCE convention). Null until Phase-A king-authority cross-reference.
- `cemetery` — Reisner / Lepsius cemetery designation as a string, when PM places the tomb within a numbered cemetery (`"G 7000"`, `"G 2000"`, `"Junker Cemetery West"`). Null for stand-alone pyramid-complexes and for tombs not within a labelled cemetery.
- `discovery_year` / `discoverer` — Modern excavation history. Extracted only when present in the headword's parenthetical biblio refs.
- `is_unfinished` — `true` when PM headword carries the literal word `Unfinished`.
- `is_uninscribed` — `true` when PM headword carries `uninscribed` (issue #182 schema field, carried over from Theban).
- `is_usurped` — `true` when PM headword carries `usurp(ed|ation)` (issue #182).
- `attribution_certainty` — enum `{attested, probable, uncertain}`. Derived from PM hedge tokens (`Probably`, `(probably)`, `attributed to`, `tentatively`, `perhaps`, `possibly`, `uncertain`, `(?)`).
- `shared_with_tombs` — `See also Tomb N` cross-references. List of tomb_ids.
- `notes_from_pm` — Verbatim short prose from the headword line (PM's parenthetical refs, Lepsius/Perring/Reisner cross-numbering, descriptive marker like "Lower part unexcavated").
- `source_citation` — Per-row citation: PM's printed page number, edition string (`PM III.1 2nd ed. 1974` or `PM III.2 2nd ed. 1978`), section ID per PM's TOC.

## Pipeline

Per ADR-017 + the Phase-0 playbook (`docs/playbook-phase-0-ocr-transcription.md`):

1. **Text-layer extraction** (deviates from playbook step 3 — see `transcribe.md` § "Method deviation"). `pypdf` reads the verbatim text layer for the chunk's physical-page range into `raw/chunk-p<start>-p<end>.txt` (gitignored). No OCR subagent needed: PM III PDFs carry a publisher text layer (verified for PM III.1; PM III.2 to be confirmed at chunk 4+).
2. **Three parallel extraction subagents** read `raw/chunk-*.txt` and `prompt-chunk-*.md`, write `raw/agent-{a,b,c}-<chunk>.jsonl`.
3. **Deterministic merge** (`merge.py`) — majority-vote across the three agents per `(tomb_id, field)`. Outputs `reconciled.jsonl` and `merge-disagreements.txt`. `tie-break-overrides.json` resolves 1/1/1 ties with a printed-source citation.
4. **LLM reviewer pass** — `egyptologist-reviewer` subagent against the source PDF.
5. **Spot corrections** — `fix_rows.py` applies reviewer's corrections to `reconciled.jsonl`.
6. **Tests** — `pipeline/tests/test_sources_porter_moss_memphis.py`.
7. **Human Egyptologist sign-off** (ADR-017 step 6) — provisional until logged at `human-review-<YYYY-MM-DD>-<chunk>.md`.

## Multi-chunk plan

This source lands across multiple PRs (Theban precedent). Per the playbook § "Multi-chunk source pattern":

- **Chunk 1** ✅ PR #217: Gîza pyramid complexes — Khufu (G1), Khephren (G2), Menkaureʿ (G3) and their attested queens' subsidiary pyramids (G1a/b/c, G3a/b/c). Physical pp.8–32 / printed pp.11–35 of PM III.1 § I "PYRAMIDS". 10 rows. Establishes the `memphite_area="Giza"` vocabulary entry and Reisner G-number `tomb_id` convention.
- **Chunk 2** ✅ PR #219: Gîza Cemetery G 7000 East Field royal-family cluster (Hetepheres I G 7000X, Kawab + Hetepheres II G 7110+7120, etc.). PM III.1 § III "B. EAST FIELD", physical pp.176–187 / printed pp.179–190. 13 rows.
- **Chunk 3** ✅ PR #220: Gîza Central Field — LG 100 Khentkaus I + Saite (Dyn XXVI) intrusions (LG 81/83/84/97). PM III.1 § III "E. CENTRAL FIELD", physical pp.285–289 / printed pp.288–292. 5 rows.
- **Chunk 4** ✅ PR #222: Saqqâra § I. PYRAMIDS back half (sections F–K) — 5 Dyn V/VI royal kings (Unis, Pepy I, Isesi, Merenrʿ I, Pepy II) + 4 queens (anonymous Wife-of-Isesi, plus Pepy II's Neit / Iput II / Wezebten). PM III.2 § I, physical pp.61–72 / printed pp.421–432. 9 rows. First PM III.2 chunk; establishes `memphite_area="Saqqara"` and `SAQ-` descriptor-form tomb_ids.
- **Chunk 5** ✅ PR #223: Saqqâra § I. PYRAMIDS front half (sections A–E) — Teti (Dyn VI) + Iput + Khuit queens + Userkaf (Dyn V) + Neterikhet/Zoser (Dyn III Step Pyramid) + Sekhemkhet (Dyn III, unfinished) + anonymous 'Great Enclosure' (Probably Dyn III). PM III.2 § I, physical pp.33–57 / printed pp.393–417. 7 rows. First Dyn III rows in this source; first parenthetical-alias pattern (Neterikhet ↔ Zoser/Djoser); first Shape-3 anonymous structure where `dynasty: "3"` is from PM's own annotation rather than inherited from a king's complex.
- **Chunk 6** ✅ PR #225: Gîza § III.A West Field, Junker low-thousands cemeteries — G 1000 / G 1100 / G 1200 / G 1300 / G 1400 / G 1500 / G 1600 / G 1900. PM III.1 § III.A, physical pp.46–62 / printed pp.49–65. 54 rows (30 Shape-1 named primary + 24 Shape-2 bare-suffix). First West Field chunk; first Shape-3 compound twin-mastaba in the West Field (G 1452+1453 ZADUWAʿ); first underdot-Ḥ glyph normalisation for non-royal names (Meḥyt in G 1201).
- **Chunk 7** ✅ PR #226: Gîza § III.A West Field continuation — Cemetery G 2000 + Cemetery G 2100 + Mastaba G 2220. PM III.1 § III.A, physical pp.63–80 / printed pp.66–83. 46 rows (mix of Shape-1 named, Shape-2 bare-suffix, Shape-3 compound). Royal-family density: G 2100-I-annexe (Merib, King's son; recorded as `G2100a` in `tomb_id`), G 2101 Nensezerkai I (Princess, King's daughter). First chunk to handle **PM's duplicate `G 2156` Reisner-number assignment** — two distinct mastabas (Kanenesut II east of G 2155 + Redenes south of G 2220) share the same Reisner number per PM's "another G 2156" cross-reference; the second occurrence is renamed to `G2156b` via a chunk-7 pre-merge dedup pass with full audit trail in `transcribe.md`. Also introduces a one-time chunk-7 normalisation script (`normalize_chunk7.py`) that strips occupant-name prefixes from `notes_from_pm` to align with the chunks 1-6 convention.
- **Chunk 8** ✅ PR #227: Gîza § III.A West Field continuation — Cemetery en Echelon (G 2300 + G 2400 sub-clusters) + Cemetery G 2500. PM III.1 § III.A, physical pp.80–92 / printed pp.83–95. 33 rows (17 Shape-1 named + 16 Shape-2 bare-suffix). Senedjemib clan dominates the named cohort: G 2370 Senezemib Inti (Vizier under Isesi), G 2378 Senezemib Meḥi (Vizier under Unis), G 2381 Meryrēʿ-Meryptaḥʿankh Nekhebu (royal architect under Pepy I), G 2387 Pepy-Meryptaḥʿankh, G 2423 Meḥu (Judge, Prophet of Maʿet). First chunk to systematically apply the **"good name" alt-name idiom** (Egyptian *rn nfr*) for OK-official secondary names; first compound theophoric occupant_name with underdot-Ḥ on the *ptḥ* root (Meryptaḥʿankh); first headword-level joint-burial `<NAME> and wife <NAME>` (G 2415 Weri/Meti).
- **Chunk 9** ✅ PR #228: Gîza § III.A West Field continuation — CEMETERY G 3000 (Fisher's "Minor Cemetery", Penn Coxe Expedition 1915). PM III.1 § III.A, physical pp.92–96 / printed pp.95–99. 14 rows. Essentially a Dyn-VI assemblage. 8 tie-break-overrides on wife-clause role strings + Ḥathor underdot normalisation.
- **Chunk 10** ✅ PR #229: Gîza § III.A West Field continuation — JUNKER CEMETERY (WEST) (Junker Excavation, Akademie der Wissenschaften in Wien + Pelizaeus-Museum Hildesheim + University of Leipzig, 1926-7). PM III.1 § III.A, physical pp.97–105 / printed pp.100–108. 30 rows: 18 Shape-1 named-primary + 5 Shape-2 S-numbered (Steindorff) + 7 Shape-3 bracketed-Roman-regnal named (Sonb I, Khesef I/II, Khnemhotp II, Ptahshepses II, Meni I/II). First chunk to use the **JKR descriptor tomb_id convention** (parallel to chunk-4's SAQ) and the **Steindorff S-number form** (`S4040`, `S4399`, etc.). Cemetery field uses descriptor `"Junker West"` (parallel to chunk-3's `"Central Field"`). Highlights: JKR-SonbI (full name dwarf-vizier Sonb I, the largest chunk-10 block spanning 3+ pages of chapel decoration), JKR-Inpuhotp (Anubis-priest with Saḥurēʿ/Neuserrēʿ/Rēʿ triple-macron-Ē-plus-ayin compound), JKR-Ithu (3 co-occupants: parents Iaʿib + Khaut I + wife Intkaes). 10 tie-break-overrides resolve 1/1/1 ties on wife-clause role strings + ʾtw-aleph + multi-diacritic Re-compounds + Sentiotes I bracketed regnal.
- **Chunk 11** (this PR; halves 11a + 11b): Gîza § III.A West Field continuation — STEINDORFF CEMETERY (Steindorff Excavation, University of Leipzig + Pelizaeus Expedition 1903-7). PM III.1 § III.A, physical pp.105–114 / printed pp.108–117. 44 rows: 40 D-numbered tombs (D.I → D.221) + 4 STN- descriptor-form interstitial named tombs (Wemtetka, Ibir, Nu, Iri) without a D-number. First chunk to use the **D-number tomb_id convention** (Steindorff's own field numbering — explicitly NOT Mariette's Saqqâra D-prefix, a discovery from a `/revise-priors` pass that corrected the chunk-10 prompt's misattribution) and the **STN- descriptor form** (parallel to chunk-10's JKR-). Cemetery field uses descriptor `"Steindorff"` (parallel to chunk-3's `"Central Field"` and chunk-10's `"Junker West"`). Split into halves 11a (D.I → D.38 + 2 interstitials, 17 rows) and 11b (D.39/40 → D.221 + 2 interstitials, 27 rows) after the original full chunk failed across 6 subagent attempts (3 sonnet stalls + 3 opus socket errors). Highlights: D.117 WEHEMKA three-co-occupant block (father Iti + mother Zefatsen + wife Ḥetepibes called Ipi, with gendered Father/Mother/Wife roles), D.37 RAaHERKA Re-deity-compound + ḥ-root triple-diacritic `Rēʿḥerka` (combines macron-Ē + ayin + underdot-Ḥ), D.39/40 twin-number form, D.80/80 A twin-letter form with LG 22 cross-reference, STN-Iri+Sebani joint-named twin without a D-number. 14 tie-break-overrides resolve 1/1/1 ties on Shape-2 bare-numeric null notes, ellipsis-truncation notes, Shape-4 joint-twin notes, the three-co-occupant parent-pair-plus-wife block, `mitrt` typography, and controlled-vocab fallback for unknown joint-twin roles.
- **Chunk 12** ✅ PR #230: Saqqâra § I.L-N royal complexes — Shepseskaf (Dyn IV Mastabat el-Faraʿun), Userkareʿ Khenzer (Dyn XIII), anonymous Dyn XIII southern pyramid-enclosure. PM III.2 physical pp.73–76 / printed pp.433–436. 3 rows. Closes the back-half of PM III.2 § I PYRAMIDS that chunks 4 (sections F–K) and 5 (sections A–E) left open. First chunk to emit `dynasty: "13"` (Dyn XIII Second Intermediate Period).
- **Chunk 13** (this PR): Gîza § III.A West Field continuation — JUNKER CEMETERY (EAST) (Junker Excavation, same expedition as chunk-10 Junker West). PM III.1 § III.A, physical pp.115–118 / printed pp.118–121. 15 rows: 13 JKE- named-primary + 1 S-numbered (S 2411) + 1 anonymous JKE-AnonCompanion (PM `NAME UNKNOWN, Companion (smr N.N. of Junker)`). First chunk to use the **JKE- descriptor convention** (parallel to chunk-10's JKR-). Cemetery field uses descriptor `"Junker East"` (parallel to chunk-10's `"Junker West"`). Highlights: JKE-NiankhHathor (Prophetess of Ḥathor, double-diacritic `Niʿankh-Ḥathor`), JKE-Meruka (Elder of the Hall, Prophet of Khufu — largest Junker East block), JKE-Nikaukhnum+Neferesris (Shape-4 joint twin), JKE-User (Late Dyn V with Mother Henutsen co-occupant), JKE-AnonCompanion (Shape-5 anonymous smr-N.N. tomb). Clean merge: no 1/1/1 ties; CHUNK13_CORRECTIONS empty pending reviewer pass.
- **Chunk 14** (this PR; halves 14a + 14b): Gîza § III.A West Field continuation — CEMETERY G 4000 (Reisner Excavation, Harvard-Boston Expedition). PM III.1 § III.A, physical pp.119–138 / printed pp.122–141. 49 rows: ~32 Shape-1 named-primary + ~14 Shape-2 bare-numeric + 1 Shape-3 bracketed-Roman (G 4761 Nufer [I]) + 1 Shape-4 joint twin (G 4811 + 4812 ʿAnkhirptaḥ) + 1 Shape-5 anonymous (G 4860). Headlined by **G 4000 Ḥemyunu** — Khufu's Chief Justice and Vizier and chief architect of the Great Pyramid. Split into halves 14a (G 4000–G 4540, 25 rows) and 14b (G 4560–G 4860, 24 rows) preemptively (50+ tombs total) parallel to chunk-11 halving pattern. Highlights: G 4000 Ḥemyunu (`Vizier` role); G 4351 IMISETKAI (1st Int. Per. — first chunk to emit `dynasty: null` for outside-OK dating); G 4520 Khufu-ʿAnkh (hyphenated theophoric naming convention); four Ḥathor-Mistress-of-the-Sycamore wife clauses (G 4351, G 4561, G 4630, G 4710, G 4651); G 4761 Nufer [I] (3-co-occupant Probably-parent-pair-plus-wife parallel to chunk-11 D117). 12 tie-break-overrides; CHUNK14_CORRECTIONS empty pending reviewer pass.
- **Chunk 15** ✅ PR #234 (halves 15a + 15b): Gîza § III.A West Field continuation — CEMETERY EN ECHELON. SOUTH PART (Reisner + Junker Excavations; some tombs earlier by Schiaparelli / Steindorff). PM III.1 § III.A, physical pp.138–165 / printed pp.141–168. 32 rows: ~22 Shape-1 named-primary + ~6 Shape-2 bare-numeric + ~4 Shape-3 bracketed-Roman (3 Seshemnufer regnals at G 4940 / G 5080 / G 5170 + 2 Rēʿwer regnals at G 5270 / G 5470). Highlights: **G 5110 Duaenrēʿ** (Vizier of Menkaurēʿ, son of Khephren and Meresʿankh III); **G 5170 Seshemnufer [III]** (Chief Justice and Vizier under Isesi, son of the G 5080 Vizier; three-co-occupant parent-pair-plus-wife block parallel to chunk-11 D117); **G 5210 Khemtnu** (Steward of Kawaʿab + Ḥetepḥeres II + Meresʿankh III); **G 5550 Nufer good name Idu [I]** (Chief Justice and Vizier, Early Dyn. VI). Split into halves 15a (G 4911–G 5230, 16 rows) and 15b (G 5232–G 5560, 16 rows). 16 tie-break-overrides + 17 CHUNK15_CORRECTIONS entries (six rounds of Gemini review: dynasty backfills G 5190/G 5232/G 5290/G 5332/G 5350/G 5480/G 5482/G 5520, parent-extraction G 5110/G 5270/G 5280/G 5340/G 5550, diacritics, theophoric-ankh hyphenation). Follow-ups: #235 (IDU [II] unnumbered headword), #236 (ʿankh/ʿAnkh source-wide convention).
- **Chunk 16** (this PR): Gîza § III.A West Field — CEMETERY G 6000 (Hemiunu-adjacent; Reisner Excavation, Harvard-Boston Expedition). PM III.1 § III.A, physical pp.166–179 / printed pp.169–182. 8 rows: 3 Shape-1 named-primary (G 6010 Neferbauptaḥ, G 6020 Iymery, G 6040 Shepseskaf-ʿankh) + 1 Shape-3 bracketed-Roman (G 6030 It [I]) + 4 Shape-2 bare-numeric (G 6012, G 6014, G 6037, G 6042). **Three-generation family cluster**: G 6040 Shepseskaf-ʿankh (grandfather, Steward, Temp. Neferirkarēʿ) → G 6020 Iymery (father, Prophet of Khufu, Temp. Neuserrēʿ or later) → G 6010 Neferbauptaḥ (son, Steward of the Great Estate, Middle to end of Dyn. V); the Shape-3 G 6030 It [I] is linked into the same clan via wife Usertka (daughter of Shepseskaf-ʿankh). Clean merge: 4 cleanly-resolved 2/1 disagreements, no 1/1/1 ties → no tie-break-overrides. 3 CHUNK16_CORRECTIONS entries from Gemini round-1 review (G 6020 wife-clause `, etc.` marker + two source_citation page-offset corrections on G 6037 and G 6042 — the agent-majority voted off-by-N from the prompt's `printed = physical + 3` boundary rule).
- **Chunk 17+** (future PRs): Gîza West Field — remaining Cemetery G 7000 East Field officials not yet shipped by chunks 2/4 (the G 7100+ named OK clientele). Then § III.D QUARRY CEMETERY WEST OF SECOND PYRAMID + § III.E Central Field OK portion (chunk 3 already did the Saite intrusions).
- **Later** (future PRs): § II Saqqâra NECROPOLIS named OK mastabas (Ti, Mereruka, Kagemni, Ptahhotep, Akhethetep, Mehu). PM III.1 Zâwyet el-ʿAryan + Abû Ghurâb + Abûsîr pyramid complexes (stretch). Then Dahshûr / Lisht / Mêdûm if MVP scope demands.

Per-chunk prompt files: `prompt-chunk-<chunk>.md`. Per-chunk agent JSONLs: `raw/agent-{a,b,c}-<chunk>.jsonl`.

## Known gaps

- **King → BCE date lookup.** This source extracts the headword (occupant name); the BCE date fields stay null until the king authority (pharaoh.se / Beckerath / HKW) is reconciled in Phase A. Holding rows null is consistent with constitutional rule 4 (sparse rows are valid) and rule 7 (authority lookup, not hard-coded names in extracts).
- **Cartouches in the text layer render as garbage characters.** PM prints royal names with hieroglyphic cartouches inline; the text layer renders these as `(~~~ ::)`, `(•~~)`, etc. The conventional English name in titlecase before the cartouches is the extraction target. Don't try to recover the cartouches from the text layer.
- **PM-printed `Menkaurea` / `Sahurea` / `Neferirkarea` etc. with terminal raised-`a` ayin.** PM III's typesetting uses a raised-`a` glyph for terminal Egyptological ayin in royal names; the text layer renders this verbatim as a trailing `a`. `occupant_name` normalises to ayin `ʿ` (Egyptological convention); `notes_from_pm` preserves whatever the text layer outputs (with the egyptologist-reviewer pass restoring PM-faithful diacritics against the PDF page image).
