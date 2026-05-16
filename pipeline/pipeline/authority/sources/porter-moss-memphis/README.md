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

- **Chunk 1** (this PR): Gîza pyramid complexes — Khufu (G1), Khephren (G2), Menkaureʿ (G3) and their attested queens' subsidiary pyramids (G1a/b/c, G3a/b/c). Physical pp.8–32 / printed pp.11–35 of PM III.1 § I "PYRAMIDS". Establishes the `memphite_area="Giza"` vocabulary entry and Reisner G-number `tomb_id` convention.
- **Chunk 2** (future PR): Gîza Sphinx-area structures + LG 100 Khentkaus I tomb. PM III.1 § II + § "FROM GIZA TO ZÂWYET EL-ʿARYAN".
- **Chunk 3+** (future PRs): Gîza Necropolis cemeteries — § III West Field (G 1000s, G 2000s, G 4000s, G 6000s, Junker / Steindorff cemeteries), § III East Field (G 7000 with Hetepheres I G 7000X, Hetepheres II, Meresankh III, Kawab, Hardjedef — Khufu's family cluster), § III Central Field, § III Menkaureʿ Cemetery. Each Reisner cemetery group likely a sub-chunk.
- **Later** (future PRs): PM III.1 Zâwyet el-ʿAryan + Abû Ghurâb + Abûsîr pyramid complexes. Then PM III.2 Saqqâra pyramid complexes (Userkaf, Sahurēʿ, Neferirkarēʿ, Niuserrēʿ, Unas, Teti, Pepi I, Pepi II) + Saqqâra mastabas. Then Dahshûr / Lisht / Mêdûm if MVP scope demands.

Per-chunk prompt files: `prompt-chunk-<chunk>.md`. Per-chunk agent JSONLs: `raw/agent-{a,b,c}-<chunk>.jsonl`.

## Known gaps

- **King → BCE date lookup.** This source extracts the headword (occupant name); the BCE date fields stay null until the king authority (pharaoh.se / Beckerath / HKW) is reconciled in Phase A. Holding rows null is consistent with constitutional rule 4 (sparse rows are valid) and rule 7 (authority lookup, not hard-coded names in extracts).
- **Cartouches in the text layer render as garbage characters.** PM prints royal names with hieroglyphic cartouches inline; the text layer renders these as `(~~~ ::)`, `(•~~)`, etc. The conventional English name in titlecase before the cartouches is the extraction target. Don't try to recover the cartouches from the text layer.
- **PM-printed `Menkaurea` / `Sahurea` / `Neferirkarea` etc. with terminal raised-`a` ayin.** PM III's typesetting uses a raised-`a` glyph for terminal Egyptological ayin in royal names; the text layer renders this verbatim as a trailing `a`. `occupant_name` normalises to ayin `ʿ` (Egyptological convention); `notes_from_pm` preserves whatever the text layer outputs (with the egyptologist-reviewer pass restoring PM-faithful diacritics against the PDF page image).
