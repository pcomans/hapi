# Authority sources — rationale

Why Hapi transcribes the specific scholarly works it does, and what each closes in the Egyptological authority landscape.

## The big picture

Hapi is a cross-museum Egyptian-artifact search index. Museums each store metadata in their own idiolect — the Met says "Thutmose III" where Brooklyn says "Menkheperre" where Harvard says "Mn-ḫpr-Rꜥ". To unify those into a single index that answers *"show me objects of Thutmose III"* we need an **authority layer**: a canonical ruler list, queen list, site list, etc., where every variant spelling maps to one ID.

## The hard constraint

Constitutional rule 1 (`CLAUDE.md`): *"Every authoritative fact must trace to a clear, documented, reproducibly-acquired source on disk. 'The model knows' is not a source."*

That rules out LLM-hallucinated authority data, uncited Wikipedia scrapes, and aggregator sites whose provenance can't be audited. It forces us to transcribe from specific scholarly editions, commit the reasoning, and trace every row back to a page number.

## Why multiple sources instead of one

No single source covers the whole authority. The Egyptological authority is necessarily stitched from specialist editions because each expert covers a specific domain (queens, SIP kings, TIP concurrency, OK prosopography, etc.). The "multi-source authority" isn't a limitation — it's the scholarly consensus method.

## Source-by-source rationale

### Pharaoh.se — primary pharaoh authority

**Fills:** baseline ruler list across all dynasties.

**Why this one, not others:** CC BY 4.0 (committable per ADR-012), expert-curated, derives from Beckerath 1999 (the standard reference). Replaced an earlier Wikidata-based approach which had persistent quality issues: 0% prenomen coverage, polluted with fictional characters, inconsistent structured data.

**Method:** Firecrawl scrape, not transcription (ADR-012, PR #25).

**Coverage:** Dyn 1 through Ptolemaic kings with full five-name titulary (Horus, Nebty, Golden Horus, Prenomen, Nomen).

**Gap it does NOT cover:** queens, princes, princesses, viziers, or any non-king member of the royal family. Also weak on Dyn 7 convention, the Argead bridge (Alexander → Ptolemy I), and some Dyn 0 / Predynastic rulers.

### HKW 2006 *Ancient Egyptian Chronology* (Hornung / Krauss / Warburton)

**Fills:** BCE-date chronology framework.

**Why this one:** the current scholarly-consensus chronology. Beckerath 1997 *Chronologie* is the alternative but is older and partially superseded.

**Method:** not transcribed by the pipeline — already available in structured form from a prior workstream.

**Coverage:** dynasty-level BCE ranges, Egyptian calendar mappings, Sothic-cycle anchors.

**Gap it does NOT cover:** ruler-level titulary or per-king reign details. Used for date-banner display and period faceting, not for ruler identification.

### Dodson & Hilton 2004 *The Complete Royal Families of Ancient Egypt*

**Fills:** NK through Late Period queens, princes, princesses, royal genealogies.

**Why this one:** the only single volume covering the full royal family across New Kingdom and Late Period with cross-referenced genealogies. Porter-Moss has objects by tomb; D&H has PEOPLE by family tree.

**Method:** multi-chunk 3-agent majority-vote extraction from Brief Lives prose. First ADR-017 invocation of the Gemini 3.1 Pro OCR amendment on the Ramesside chunk p126–p130 (Chapter 3 §"The Power and the Glory" Brief Lives sub-block) — Opus 4.6 issued a reasoned copyright refusal on the grounds that the 5-page-of-prose quantity exceeded fair-use excerpting. Gemini 3.1 Pro produced the OCR markdown; downstream 3-agent extraction + merge + reviewer pass stayed on Opus.

**Coverage:** Nefertiti, Nefertari, Tiye, Ahmose-Nefertari, Ankhesenamun, plus hundreds of minor royal-family members. Genealogical edges (parent-of, spouse-of) captured as structured fields.

**Gap it does NOT cover:** Old Kingdom royal family (D&H's OK chapter is explicitly thinner — that's Baud's job). Predynastic / Dyn 0.

### Baud 1999 *Famille royale et pouvoir sous l'Ancien Empire égyptien*

**Fills:** Old Kingdom prosopography.

**Why this one:** D&H's OK coverage is explicitly weaker (their book is primarily NK/LP). Baud's vol. 2 *Corpus* is the definitive OK authority — 282 numbered entries covering every attested OK royal family member plus service personnel attached to the royal household (priests of the king's mother, stewards of the queen, etc.).

**Method:** 7-chunk 3-agent majority-vote extraction, 289 rows (282 integer-numbered + 7 letter-suffix sub-entries). Ships with provisional partial sign-off (`human-review-2026-04-18-chunk*.md`) pending specialist pass. Largest single Phase-0 job because each Baud entry has (a)-(h) header fields plus up to 4 French prose rubrics — ~5× the per-person density of pharaoh.se.

**Coverage:** Queens like Khentkaus I/II, Iput I, Ankhesenmeryre I/II. Princes like Kawab (Khufu's eldest), Hordjedef, Rahotep. Vizier-sons-in-law. Service personnel attached to queens' cults.

**Gap it does NOT cover:** anything outside OK (Dyn 3-6). Uses French scholarly idiolect (e.g. `Snéfrou`, `Pépi Iᵉʳ`, `Rêkhaef`) that Phase-A normalization maps to English forms.

### Ryholt 1997 *The Political Situation in the Second Intermediate Period*

**Fills:** Dyn 13-17 kings plus the Abydos Dynasty.

**Why this one:** HKW gives Dyn 13-17 BCE dates but not full titulary or per-king attestations. Museums with SIP material (especially scarabs) need Ryholt's catalogue of Dyn 13-17 kings — including the Abydos Dynasty and the unattributed-king bucket — to resolve objects to specific rulers. The catalogue runs ~60-80 king entries; the `reconciled.jsonl` has more rows because many kings have multiple attestations captured as separate rows.

**Method:** Part VI Catalogue of Attestations + Chronological Tables (physical PDF pp. 336-416), 3-agent majority-vote extraction. Deterministic cross-reference between two Ryholt sections (catalogue + chronology).

**Coverage:** every known SIP king with five-name titulary where attested, nomenclature variants, attestation count, the seal-based dating that no other single source consolidates.

**Gap it does NOT cover:** non-royal SIP individuals. TIP (Kitchen's job).

### Kitchen 1996 *The Third Intermediate Period in Egypt* (3rd ed.)

**Fills:** TIP chronology including Dyn 21-25 and the parallel Tanite / Theban High-Priest-of-Amun lines.

**Why this one:** the standard TIP reference. Unique in modeling the Dyn 21 Tanite kings AND the Theban HPA rulers as CONCURRENT rather than sequential — they ruled different parts of Egypt simultaneously. No other source commits BCE ranges for the parallel rulers with Kitchen's precision.

**Method:** Part VI Tables 1, 3, 4 (physical PDF pp. 240-243), 3-agent extraction + `fix_rows.py` deterministic recomputation of `concurrent_with_kings` by interval overlap. The concurrency matrix is too mistake-prone for LLMs — computed from `start_bce` / `end_bce` pairs instead.

**Coverage:** Ramesses XI + full Dyn 21-25 + Dyn 26 parallel streams.

**Gap it does NOT cover:** later ethnological detail; post-1996 revisions (Aston 1989, Jansen-Winkeln *Inschriften der Spätzeit*) land as separate deltas, not bundled.

### Shaw 2000 *The Oxford History of Ancient Egypt*

**Fills:** period date-range banners.

**Why this one:** the widely-cited overview whose chapter banners give "Old Kingdom = Dyn 3-6 = 2686-2160 BCE" at the level of granularity museum UIs need for period facets / dropdowns.

**Method:** 13-row transcription of chapter banners (chapters 2-10, 12-15).

**Coverage:** period-to-BCE-range mapping. Predynastic sub-periods Naqada I (Amratian) and Naqada II (Gerzean) captured from Midant-Reynes' Ch. 3 chronology (pp. 42-43).

**Gap it does NOT cover:** narrowly-defined sub-periods like Amarna, Ramesside, Saite. Those need a different source in Phase A.

### Porter-Moss Vol I (Theban Necropolis) — PENDING

**Fills:** tomb index for KV (Kings' Valley), QV (Queens' Valley), TT (Theban Tombs 1-400+).

**Why this one:** the canonical tomb index, continuously updated by the Griffith Institute. When a museum says "from TT320" we need to know what TT320 is — which occupant, which location, which dynasty. PM is the authority.

**Method:** derived-extract of the tomb index table. Moss's descriptive prose (iconography, epigraphy) stays out of scope per the playbook's rights policy.

**Gap:** Theban only. Memphite material needs Vol III.

### Porter-Moss Vol III (Memphis — Giza / Saqqara / Abusir) — PENDING

**Fills:** Memphite tomb/site index.

**Why this one:** the Met, Brooklyn, and Harvard all hold substantial Memphite material. Without Vol III, the site authority systematically under-resolves Giza/Saqqara/Abusir provenances.

**Method:** same derived-extract pattern as Vol I.

### Manetho fragments — PENDING

**Fills:** Dyn 7 convention.

**Why this one:** Dyn 7 is Manetho's "ghost dynasty" — likely fictional but still used as a convention in museum catalogs. The preferred critical edition is Verbrugghe & Wickersham 1996 *Berossos and Manetho* (Michigan); Waddell 1940 Loeb is a commonly-cited alternative.

**Method:** derived-extract of the Dyn-7 kinglist from Africanus / Eusebius / Barbarus epitomators.

### Hölbl 2001 *A History of the Ptolemaic Empire* — PENDING

**Fills:** Argead bridge dynasty.

**Why this one:** Alexander III, Philip III Arrhidaeus, Alexander IV ruled Egypt 332-305 BCE — absent from both HKW and pharaoh.se. Museums with late-fourth-century BCE material need this bridge.

**Method:** transcribe the opening chronological table.

### Beckerath 1999 *Handbuch der ägyptischen Königsnamen*, 2nd ed. — PENDING

**Fills:** cross-reference fallback for pharaoh.se.

**Why this one:** pharaoh.se derives from Beckerath 1999. When pharaoh.se is ambiguous, silent, or where a curator wants to verify a titulary entry against the primary, Beckerath is the source. Any scholarly reviewer will expect this to be in the authority.

**Priority:** lower than the other pending sources if pharaoh.se proves sufficient. But land before Phase A completes.

## Why not an aggregator (Trismegistos, Wikidata, etc.)

A scholarly reviewer will ask: why not just pull from Trismegistos (TM) — the Leuven aggregator that already unifies Egyptian prosopography across sources?

- **Licensing.** TM's terms are not CC-BY-equivalent; bulk re-hosting in Hapi's authority requires a license review that pharaoh.se + the per-source transcriptions don't.
- **Scope mismatch.** TM is strongest on Graeco-Roman period papyrology and weaker on pharaonic-era royal families — the inverse of Hapi's primary coverage need.
- **Provenance density.** When TM aggregates from upstream sources, it collapses the per-source variant information that Hapi deliberately preserves. We want "D&H spells Nefertari X / Beckerath spells it Y / pharaoh.se Z" — TM gives you a single canonical form.
- **Wikidata** was tried and dropped (ADR-012). Persistent quality issues (fictional characters, 0% prenomen coverage, inconsistent structured data). Pharaoh.se replaced it.

This is "why not pull from one aggregator" — and the answer is that Hapi IS the aggregator we're building, explicitly from primary scholarly editions rather than from another aggregator's collapsed view.

## Out-of-scope acknowledgments

Sources a scholarly reviewer might expect but that are deliberately out of scope:

- **Ranke, *Die ägyptischen Personennamen* (PN I–III).** The standard non-royal personal-names reference. Out of scope because Hapi's authority is currently royal / attested-in-monuments only; non-royal individuals surface as museum-object owners but don't get authority IDs.
- **Leitz, *Lexikon der ägyptischen Götter und Götterbezeichnungen* (LGG).** Deity-authority reference. Deities appear in museum metadata (e.g. "figurine of Horus") but Hapi's current authority-layer scope is rulers, royal family, sites, and periods — not deities. If deity-authority becomes in-scope, LGG is the source.
- **Gauthier, *Le livre des rois d'Égypte*** (1907-1917). Earlier kinglist; Beckerath supersedes it.
- **von Beckerath, *Chronologie des pharaonischen Ägypten*** (1997). Alternative chronology to HKW 2006. HKW is the current consensus; Beckerath's chronology remains citable but is not the working framework.

## Principles that fall out

- **One source, one gap.** Each source has a single clear motivation. When coverage overlaps, we prefer the source that's more granular in its specialist area (Baud > D&H for OK royal family; Ryholt > HKW for SIP; Kitchen > HKW for TIP; pharaoh.se > Beckerath for the common case).
- **Per-source discipline, not multi-source-in-one-slot.** When revisions to a source land (Kitchen 2009 Broekman eds., Aston 1989 JEA 75, etc.), they become their own deltas, not amendments to an existing source's `reconciled.jsonl`. This preserves the audit trail — every row traces to one specific edition.
- **Provisional until signed off.** Every Phase-0 source is provisional at the chunk level until a human Egyptologist signs off (ADR-017 step 6). LLM-applied corrections are explicitly labelled `NOT HUMAN-VALIDATED` in `merge-disagreements.txt`.
- **Transcription method is part of the artifact.** Each source commits its `transcribe.md` describing how the extract was produced, which PDF pages were scoped, which prompts the 3-agent extraction used, and any fallback (Gemini 3.1 Pro per ADR-017 amendment when Opus refuses).

## Where this lives operationally

- Per-source README: `pipeline/pipeline/authority/sources/<source>/README.md` (schema + rights policy + sign-off status)
- Per-source transcription method: `pipeline/pipeline/authority/sources/<source>/transcribe.md`
- Per-source extract: `pipeline/pipeline/authority/sources/<source>/reconciled.jsonl`
- Per-chunk human-review logs: `<source_dir>/human-review-<YYYY-MM-DD>[-<chunk>].md`
- The full phase-0 protocol: `docs/playbook-phase-0-ocr-transcription.md`
- The architectural decision: `docs/adr/017-ocr-pipeline-for-scan-only-sources.md`
- Task / progress tracking: `docs/mvp-tasks.md` Milestone 3 § "Additional sources required before Phase A can start"
