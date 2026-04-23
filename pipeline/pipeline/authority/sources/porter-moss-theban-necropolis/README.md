# Porter & Moss — Topographical Bibliography Vol I (Theban Necropolis)

Authority extract of named tombs in the Theban necropolis: occupant, dynasty, valley sub-area. Source for tomb-attributed provenances at Thebes (KV / QV / TT / Dra' Abu el-Naga / Deir el-Bahri / Asasif / Sheikh Abd el-Qurna / etc.).

## Citation

- **Vol I, Part 1: Private Tombs** — Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume I: The Theban Necropolis. Part 1: Private Tombs.* 2nd edition, revised and augmented. Oxford: Griffith Institute, Ashmolean Museum (1960; re-issued 1970).
- **Vol I, Part 2: Royal Tombs and Smaller Cemeteries** — Porter, B. & Moss, R.L.B. *Topographical Bibliography ... Volume I: The Theban Necropolis. Part 2: Royal Tombs and Smaller Cemeteries.* 2nd edition, revised and augmented. Oxford: Clarendon Press (1964).

PDFs held in `proprietary/books/` (gitignored, not committed):
- `Porter & Moss - PM I Theban Necropolis.pdf` (PM I.1) — SHA-256 `1d98326920f18faa25c3273c0c3b1b38dbc9fe18faeae07fa89f873a47a75455`
- `Porter & Moss - PM I.2 Royal Tombs and Smaller Cemeteries.pdf` (PM I.2) — SHA-256 `bd79be57b1180ea8766d0f8195a35d99dd02bfd986c0caf4f0026e568b209a42`

Both are the Griffith Institute's free-distribution scans (downloaded from `griffith.ox.ac.uk/topbib/pdf/`), which carry an embedded text layer used by this extraction in lieu of running OCR. See `transcribe.md` § "Method deviation".

## Scope

**In scope** — one row per named tomb in the Theban necropolis with a known occupant. Initial chunk: KV1–KV10 (PM I.2 § I.A "Tombs", printed p.495–518 / physical p.37–60). Subsequent chunks land KV11–KV65, the South-West Valleys, Dra' Abu el-Naga / Asasif / Deir el-Bahri / Sheikh Abd el-Qurna / Ramesseum / Deir el-Medina / Qurnet Mura'i / Medinet Habu sections from PM I.2, and the numbered TT tombs from PM I.1.

**Out of scope** (do NOT extract):
- Per-room descriptive prose: scene catalogs, wall-by-wall epigraphy, plate references, pillar/corridor breakdowns. PM's expressive content is the iconographic description, which is copyrighted scholarly expression — see "Rights" below. The headword line per tomb (tomb number + occupant + cartouches + bibliographic refs in parens + "Plan, p. X") is fact, the body description is expression.
- Plates, plans, figures.
- Indexes 1–5 (cross-reference tables) — useful as a downstream join but extracted in their own follow-up chunk if at all.

## Rights

Per the playbook's derived-extract default (`docs/playbook-phase-0-ocr-transcription.md` § "Rights policy"):
- The PDFs are NOT redistributed through this repo. They live in `proprietary/books/` (gitignored).
- Only `reconciled.jsonl` (factual rows: tomb_id → occupant → dynasty → location) is committed. The verbatim text-layer chunk (`raw/chunk-*.txt`) stays gitignored under the same rule that gitignores OCR chunks for other Phase-0 sources.
- US copyright after *Feist v. Rural* does not protect raw factual compilations; the project's working assumption is that the committed extract is a fact compilation, not a derivative of PM's protectable expression. The chosen scope (headwords only, no scene descriptions) keeps the extract on the safe side of that line.

**Source-specific licence note (overrides nothing, supplements the default).** The Griffith Institute distributes PM Vol I PDFs from `griffith.ox.ac.uk/topbib` under their own terms. The handoff at `docs/handoff-phase-0-transcription.md` § "Source 5" calls this out as "critical" — the PDFs themselves stay un-redistributed regardless of the broader US/UK fact-compilation framing. This README, the handoff, and the playbook all converge on the same operational rule: PDF stays gitignored, extract is fact-only.

## Schema

One row per tomb. All fields except `tomb_id`, `valley`, and `source_citation` are nullable (per CLAUDE.md rule 4 — sparse rows are valid).

The chunk-1 extract example below shows what a typical KV row looks like AFTER PM-headword extraction but BEFORE Phase A king-authority enrichment fills `dynasty` and BCE dates. Per CLAUDE.md rule 7 and rule 1, those fields stay null at this stage — they don't appear in PM headwords and we don't supply them from "what the model knows" or from a hardcoded prompt table. The fields are reserved in the schema so the Phase A enrichment writes to a known shape.

```json
{
  "tomb_id": "KV9",
  "valley": "Valley of the Kings",
  "occupant_name": "Ramesses VI",
  "occupant_alt_names": ["Memnon"],
  "occupant_role": "King",
  "dynasty": null,
  "sub_period": null,
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "location_sub_area": null,
  "discovery_year": null,
  "discoverer": null,
  "is_unfinished": false,
  "shared_with_tombs": [],
  "notes_from_pm": "doorways in outer part usurped from Ramesses V",
  "source_citation": {"page": 511, "edition": "PM I.2 2nd ed. 1964", "section": "I.A"}
}
```

**Diacritic-stripping policy (`occupant_name` vs `notes_from_pm`).** PM's typesetting uses scholarly diacritics (underdot-H `ḥ`, ayin `ʿ`, macron `ē`/`ō`, etc.) but the Griffith Institute's PDF text layer OCRs most of these imperfectly — `ḥ` renders as `I:I` / `I;I`, `ʿ` often renders as `c` or gets dropped, macrons typically get dropped entirely. The reference for "what PM actually prints" is the PDF page image, verified via the egyptologist-reviewer pre-merge pass; the text layer is the reproducible extraction substrate but is NOT the source of truth for diacritics.

The extract applies TWO different conventions depending on the field:
- `occupant_name` is the matchable name field used for Phase-A ruler-authority joining. It strips scholarly diacritics (`MERNEPTAḤ-SIPTAḤ` → `Merneptah-Siptah`, `MAIḤIRPER` → `Mahirper`, `ḤAREMḤAB` → `Haremhab`). Exceptions (preserved as distinguishing radicals): **ayin** `ʿ` in royal names (e.g. `RAʿMESES-MENTUHIRKHOPSHEF` keeps its ayin → `Raʿmeses-Mentuhirkhopshef`), and **underdot-K** `ḳ` where it distinguishes Semitic /q/ from plain Egyptian /k/ (e.g. chunk-7's `ʿAḲ-ḤOR` on DAN-Aqhor → `ʿAḳ-hor` retains the ḳ while stripping the ḥ; PM-printed `Seḳenenreʿ` similarly retains its ḳ). Only underdot-H is stripped in `occupant_name`; ayin and underdot-K are preserved.
- `notes_from_pm` is verbatim-preserve against PM's printed text. Capture PM's wording as-printed including diacritics even when the text-layer OCR has dropped them. Example from chunk 4: KV55's hedge clause in PM ends `...Smenkhkarēʿ.` with macron-e + ayin + closing period; the OCR text layer reads `Smenkhkarec.`; `fix_rows.py` restores the `ēʿ` against the egyptologist-reviewer pass.

This split lets downstream joins against pharaoh.se / Beckerath work on a normalised key while preserving PM's scholarly text for display and citation.

**Field semantics:**
- `tomb_id` — `KV<n>`, `QV<n>`, `TT<n>`. Letter-suffix variants (`KV5a`) are reproduced verbatim.
- `valley` — Coarse sub-area: `"Valley of the Kings"`, `"Valley of the Queens"`, `"Dra' Abu el-Naga"`, `"Deir el-Bahri"`, `"Asasif"`, `"Sheikh Abd el-Qurna"`, `"Khokha"`, `"Qurnet Mura'i"`, `"Deir el-Medina"`, `"Ramesseum"`, `"Medinet Habu"`. The valley a tomb belongs to is structural in PM (each numbered tomb sits within a section / sub-section).
- `occupant_name` — Conventional English form of the king's / queen's / official's name. Drawn verbatim from PM's headword (e.g. `Sethos I`, `Ramesses IV`, `Tut'ankhamun`). PM uses `Sethos` not `Seti`; preserved as-is, the name authority handles cross-resolution to `Seti I`.
- `occupant_alt_names` — Other names PM prints in the headword block, typically as a `('Tomb of X', or 'Tomb of Y'. ...)` parenthetical with classical-period aliases inside the quotes. KV9's `Memnon` (PM headword: `'Tomb of Memnon'`) is the chunk-1 example. The alias is captured even though the surface form is `Tomb of Memnon` — the alias attaches to the occupant per the museum-catalog convention "from the Tomb of Memnon" = "from KV9". Empty list `[]` when PM gives no parenthetical alt-name.
- `occupant_role` — Controlled vocabulary: `King`, `Queen`, `Royal Family`, `Vizier`, `Official`, `High Priest`, `Princess`, `Prince`, `Unknown`. KV almost always `King`, QV almost always `Queen`/`Princess`, TT mostly `Vizier` / `Official` / `High Priest`. PM does not always state the role bare; controlled-vocab assignment is a Phase A enrichment in advisory mode.
- `dynasty` — Roman-numeral dynasty as a STRING (`"18"`, `"19"`, `"20"`, `"XVIII"` etc. — final form normalised to Arabic numerals). PM does not always state dynasty in the headword; this is filled by reference to the king authority (pharaoh.se, Beckerath) downstream.
- `sub_period` — Optional finer chronological label (`"First Intermediate Period"`, `"Amarna"`, `"Saite"`). Null for most rows.
- `date_bce_approx_start` / `date_bce_approx_end` — Negative integers (BCE convention). Drawn from king-authority dates downstream, not from PM's text. Null until the cross-reference is wired.
- `location_sub_area` — Sub-region within the valley when PM's headword explicitly flags one (e.g. `"West Valley"` for KV22 Amenophis III and KV23 Ay, which PM marks with a `West Valley.` flag in the headword parenthetical). Null when PM doesn't flag a sub-area (KV62 Tutʿankhamun is in the East Valley but PM does not use a `East Valley.` flag — emit null rather than infer). PM I.1 Appendix D gives this for TT; for KV the section header is the source.
- `discovery_year` / `discoverer` — Modern excavation history. PM mentions both in body prose; extracted only when present in the headword's parenthetical biblio refs (rare).
- `is_unfinished` — `true` when PM headword carries the literal word `Unfinished` (KV3, KV5 do).
- `shared_with_tombs` — When PM's headword has `See also Tomb N`, list the cross-referenced tombs here (KV3 → `["KV11"]`, KV5 → `["KV7"]`, KV11 → `["KV3"]`).
- `notes_from_pm` — Verbatim short prose fragments from the headword line that don't fit a structured field (e.g. classical-traveller cross-refs `(Descr. Ant. 1st tomb west, ...)`).
- `source_citation` — Per-row citation: PM's printed page number for that tomb's headword, edition string, section ID per PM's TOC (`I.A`, `I.B`, `III.A`, etc.).

## Pipeline

Per ADR-017 + the Phase-0 playbook (`docs/playbook-phase-0-ocr-transcription.md`):

1. **Text-layer extraction** (deviates from playbook step 3 — see `transcribe.md` § "Method deviation"). `pypdf` reads the verbatim text layer for the chunk's physical-page range into `raw/chunk-p<start>-p<end>.txt` (gitignored). No OCR subagent is needed for any source whose PDF carries a publisher text layer.
2. **Three parallel extraction subagents** read `raw/chunk-*.txt` and `prompt.md`, write `raw/agent-{a,b,c}-<chunk>.jsonl` (per the multi-chunk pattern in the playbook).
3. **Deterministic merge** (`merge.py`) — majority-vote across the three agents per `(tomb_id, field)`. Outputs `reconciled.jsonl` and `merge-disagreements.txt`.
4. **LLM reviewer pass** — `egyptologist-reviewer` subagent against the source PDF.
5. **Spot corrections** — `fix_rows.py` applies reviewer's corrections to `reconciled.jsonl` and appends an `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED` section to `merge-disagreements.txt`.
6. **Tests** — `pipeline/tests/test_sources_porter_moss_theban_necropolis.py`.
7. **Human Egyptologist sign-off** (ADR-017 step 6) — provisional until logged at `human-review-<YYYY-MM-DD>-<chunk>.md`.

## Multi-chunk plan

This source lands across multiple PRs (Dodson-Hilton pattern). Per the playbook § "Multi-chunk source pattern":
- **Chunk 1** (PR #66): `KV1–KV10` from PM I.2 § I.A. 10 rows, physical p.37–60.
- **Chunk 2** (PR #68): `KV11–KV20` from PM I.2 § I.A. 10 rows, physical p.60–90. Note: **KV21 is absent from this PM section** — the list jumps from KV20 to KV22, so chunk 2 holds exactly 10 rows despite the "KV11–KV20" range label.
- **Chunk 3** (PR #69): `KV22–KV46` from PM I.2 § I.A, physical p.89–106. 11 rows: {KV22, KV23, KV34, KV35, KV36, KV38, KV39, KV42, KV43, KV45, KV46}. **KV24–KV33, KV37, KV40, KV41, KV44 are absent from PM I.2** — PM's 1964 edition did not catalogue these as inscribed royal tombs. Introduced three row shapes: `West Valley` `location_sub_area` (KV22, KV23), multi-occupant (KV46 Yuia and Thuiu), re-used-tomb (KV45 Userhet re-used by Merenkhons).
- **Chunk 4** (PR #70): `KV47–KV57` from PM I.2 § I.A, physical p.106–111. 5 rows: {KV47, KV48, KV55, KV56, KV57}. **KV49–KV54 and KV58–KV61 are absent from PM I.2**. Introduced hedged-attribution (KV55 `Probably Amenophis IV, formerly attributed to Queen Teye or to Smenkhkarēʿ.`) and the first `Vizier` role (KV48 Amenemopet). KV56 `'Gold Tomb', uninscribed.` — another null-name + `Unknown` row.
- **Chunk 5** (PR #71): `KV62 Tutʿankhamun` as a **standalone single-row** chunk. Per user direction: tomb-row granularity is sufficient for the museum-data-join use case. PM's KV62 body spans physical p.112–128 but is out of scope; the chunk-5 file is trimmed to physical p.111–112 (headword block only). Preserves PM's ayin in `occupant_name` (`Tutʿankhamun`, Unicode half-ring). Captures `1st ed. 58` cross-reference + `Excavated by Carnarvon and Carter.` clause in `notes_from_pm`. All 3 subagents unanimous; zero `CHUNK5_CORRECTIONS` needed.
- **Chunk 6**: **§ I.A closure sweep, no rows added.** Verified against PM I.2 p.569–594 that **KV63, KV64, KV65 are not catalogued in the 1964 2nd edition** — the volume transitions from KV62's body (ending ~p.586) directly to § I.B "Finds from the Valley of the Kings" (p.586 tail), § I.C "Rest-houses and Shrines" (p.588), § I.D "Graffiti" (p.590), then § II "South-West Valleys" (p.592). KV63 was discovered 2005, KV64 in 2011, KV65 in 2019 — all post-1964 and out of scope for this source. This PR formally closes PM I.2 § I.A with a documentation entry; the 37-row KV corpus from chunks 1–5 is the complete PM I.2 § I.A tomb-row coverage.
- **Chunk 7** (PR #100): PM I.2 §§ II + III.A/C/D — **first chunk with non-numbered tombs, introduces the descriptor-id convention.** 18 rows across 5 sub-sections:
  - § II.A (1): `SWV-HatshepsutSouth` — Hatshepsut's South Tomb (Queen-Consort, before accession).
  - § II.B (2): `SWV-ThreePrincesses` (Menhet, Merti, and Menwi — three wives of Thutmose III), `SWV-Neferure` (hedged: "Probably Princess Neferure, daughter of Hatshepsut").
  - § III.A Antef Cemetery Dyn XI at El-Ṭaraf (3): `DAN-AntefSehertaui` (Inyotef I), `DAN-AntefWahankh` (Inyotef II), `DAN-MentuhotpSankhibtaui` (Intef III successor, Unfinished).
  - § III.C (1): `DAN-AhmosiNefertari` — Tomb of Queen Ahmose-Nefertari (probably), attributed to Amenophis I by Carter.
  - § III.D Seventeenth Dynasty Cemetery BURIALS (11): Kamose, Ahhotep, Antef (Nubkheperre / Sekhemre-Wepmaet / Sekhemre-Heruhirmaet = Inyotef VI/V/VII), Sebkemsaf II, Queen Mentuhotp I (wife of Djehuti), Ahmose son of Seqenenre, Ahmose Henutempet (princess), Ahhor, and Neferhotep (Scribe of the Great Harim — only non-royal Dyn-17 headword, role `"Official"`).
  Skipped within chunk-7 range: § II.C Graffiti (not tombs), § III.B Entrance to Valley of the Kings (rock-stelae + graffiti only), § III.E onwards (excavator-organised find reports with few named-tomb headwords — deferred).
  Descriptor-id convention: `<PREFIX>-<TitleCaseDescriptor>` where prefix is the valley code (`SWV`/`DAN` introduced here; `DEB`/`ASS`/`SAQN`/`RAM` registered in `merge.py` and test regex for future chunks). Descriptor is PM-faithful: `Ahmosi` not `Ahmose`, `Mentuhotp` not `Mentuhotep`; prenomen-only disambiguation (no regnal numeral) following the Antef pattern. `merge.py` and `test_tomb_id_shape` both accept the descriptor form alongside the numbered form.
- **Chunk 8 (this PR)**: PM I.2 § X.A Valley of the Queens — **20 numbered QV tombs**, numbered-form schema (no descriptor-id work). QV{33, 36, 38, 40, 42, 43, 44, 46, 47, 51, 52, 53, 55, 60, 66, 68, 71, 73, 74, 75}. Absent from PM: QV1–QV32 (never catalogued), QV34/35/37/39/41/45/48–50/54/56–59/61–65/67/69/70/72/76–80 (gaps within the numbered range). Role distribution: 7 Queens (QV38/51/52/60/66/68/71/74), 5 Princes (QV42/43/44/53/55), 2 Princesses (QV33/47), 1 Vizier (QV46 Imḥotep, Dyn XVIII intruder), 4 Unknown (QV36/40/73/75 — "no name" / "cartouche blank" headwords with role set by `CHUNK8_CORRECTIONS`). `is_unfinished=true` only on QV38 (Queen Sitreʿ, wife of Ramesses I). Agent A emitted 19 rows (missed QV60); agents B + C caught it via PM's explicit headword at p.761 + plate caption `QUEENS' TOMBS, 60, 66, 68, 71, 73-5` at p.760; merge retained the 20-row shape. Egyptologist-reviewer pass on `reviewer-notes-chunk8.md`: QV38 `is_unfinished` flag verified correct post-merge; QV47 `Sit-gḥout` OCR misread corrected to PM-faithful `Sit-dḥout`; QV74 Tentopet filiation footnote (hedged wife/mother/daughter of Ramesses IV/V) restored to `notes_from_pm`. Skipped within chunk-8 range: § X.B Unnumbered tombs and pits (find-level inventory), § X.C Finds, § X.D Graffiti.
- **Future chunks** (each its own PR):
  - PM I.2 § I.B "Finds from the Valley of the Kings" — mostly object lists already redundant with museum APIs, likely skipped.
  - PM I.2 § I.C "Rest-houses and Shrines" — workmen's villages, non-KV structures; schema fit uncertain.
  - PM I.2 § I.D "Graffiti" — graffiti numbering, out of scope for tomb-row.
  - PM I.2 § III.E–III.L (Petrie, Gauthier-Chassinat, Northampton, Philadelphia, Carnarvon-Carter, Passalacqua excavations at Dra' Abu el-Naga) — sparse named-tomb headwords (Tomb 41 Antef Dyn XII, Tombs Beneath Temple of Nebwenenef, Tombs in El-Mandara). Cherry-pick the royal-and-near-royal entries if any; may produce 5–10 additional rows or be skipped.
  - PM I.2 §§ IV–IX 'Asasif / Deir el-Bahri / Valleys south of Deir el-Bahri / Sheikh Abd el-Qurna / Ramesseum / Deir el-Medina — named-royal-tomb entries only (Deir el-Bahri Royal Cache, Deir el-Medina Saite Princesses tombs, etc.). CG/JE-keyed individual priest burials (§ V Dyn-21 priests of Amun, Dyn-22-26 priests of Monthu) are OUT OF SCOPE — the tomb-row schema doesn't fit shaft/mummy-number burial clusters. Chunks will be explicitly scoped to only the named-royal-tomb subset in each section.
  - PM I.2 § XI "Medinet Habu" — Mortuary Chapels I–VII Dyn XX–XXIV have a clear headword format, possibly 7 rows; § XI's temple-area burials and Palace-City may require schema assessment.
  - PM I.2 § XII "Objects from Thebes" — museum-object catalog, out of scope.
  - PM I.1 numbered Theban Tombs `TT1`–`TT400+` (many chunks, likely keyed by numbered-tomb decades). PM I.1 offset: physical = printed + 18 (verified at TT1 = physical p.19 = printed p.1).

Per-chunk prompt files: `prompt.md` (chunk 1), `prompt-<chunk>.md` (chunks 2+). Per-chunk agent JSONLs: `raw/agent-{a,b,c}.jsonl` (chunk 1), `raw/agent-{a,b,c}-<chunk>.jsonl` (chunks 2+).

## Known gaps

- **King → BCE date lookup.** This source extracts the headword (occupant name); the BCE date fields stay null until the king authority (pharaoh.se) is reconciled in Phase A. Holding rows null is consistent with constitutional rule 4 (sparse rows are valid) and rule 7 (authority lookup, not hard-coded names in extracts).
- **Cartouches in the text layer render as garbage characters.** PM prints royal names with hieroglyphic cartouches inline; the text layer renders these as `(~~~ ::)`, `(•~~)`, etc. The conventional English name in titlecase before the cartouches is the extraction target. Don't try to recover the cartouches from the text layer — they're better-served by a future Beckerath/pharaoh.se cross-reference.
- **OCR-typo class fixed by `fix_rows.py`.** PM's text layer has predictable typos: `pi.` for `pl.` (plate), `1` for `l`, `BuRTON` capitalisation, `c` for `ʿ` (Egyptological ayin). Most of these don't reach the structured fields (they sit in the dropped body prose), but where they do (e.g. `Re c` instead of `Reʿ` in a king-name like `Khepermaʿtreʿ Ramesses VI`), `fix_rows.py` applies the same `_WORD_LEVEL_FIXES`-style normalisation as Baud's `fix_rows.py` template.
