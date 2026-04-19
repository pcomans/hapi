# MVP Task List

Tasks to reach MVP (PRD Milestones 1–5). Each task is scoped for a single agent session. Tasks are ordered by dependency — later tasks depend on earlier ones.

The guiding principle: **one museum end-to-end before adding complexity.** The Met is the vertical slice that validates the entire pipeline. Brooklyn and Harvard stress-test normalization. Authority data is built from real ingested data, not guesses.

Phase-0-source handoffs live at `docs/handoff-<source>-*.md` (e.g. `docs/handoff-dodson-hilton-next-chunk.md`, `docs/handoff-phase-0-transcription.md`) and persist across sessions. Ad-hoc session handoffs may also be written at `docs/handoff-session-*.md` when a session ends with significant transient state; these are deleted by the next session that consumes them.

## Milestone 1: Met Vertical Slice

Take the Met from raw API to search results on screen. This validates the entire stack — schema, ingest, mapper, search index, web — before adding other museums.

### ~~1.1 Alembic migration for initial schema~~ ✅

Migration `744ef0c92771_initial_schema.py` created and applied. All tables exist in `catalog` schema: `artifacts`, `raw_met`, `raw_brooklyn`, `raw_harvard`, `fuzzy_match_reviews`.

### ~~1.2 Met fixtures~~ ✅

6 real Met API responses saved to `tests/fixtures/met/`: `rich_object.json` (Thutmose III statuette), `sparse_object.json` (Fishtail Knife), `ambiguous_provenance.json` ("Said to be from" geography), `coregency_reign.json` (Queen Tiye ring, reign spans Amenhotep III to Akhenaten), `no_image.json` (Wedge, no image), `multiline_medium.json` (Oblique Lyre, medium with `\r\n` delimiters).

### ~~1.3 Met mapper + tests~~ ✅

`pipeline/assets/normalize/met.py` implements `MapperProtocol`. Handles: reign extraction ("reign of X" → ruler name), structured geography → origin_site_raw, geographyType → origin_certainty, medium parsing (comma, semicolon, and `\r\n` delimiters), Wikidata ID extraction. 6 fixture files in `tests/fixtures/met/`, 57 tests in `tests/test_mappers/test_met.py`, all passing.

### ~~1.4 Met ingest asset~~ ✅

`pipeline/assets/ingest/met.py` — Dagster asset with concurrent fetching (20 workers via ThreadPoolExecutor). Per-batch commits (250 objects/batch). Handles 404s for deleted objects. ~28k objects ingested in ~20 minutes.

### ~~1.5 Dagster definitions wiring (Met)~~ ✅

`pipeline/definitions.py` registers `raw_met`, `normalize_met`, `sync_search` assets with `DatabaseResource`. Added `[tool.dagster] module_name` to `pyproject.toml`. Dagster dev runs on port 3001 (Next.js uses 3000).

### ~~1.6 Typesense sync asset~~ ✅

`pipeline/assets/index/sync_search.py` — drops and recreates the Typesense collection, syncs all canonical artifacts with faceted fields for museum, period, dynasty, ruler, site, object type.

### ~~1.7 Drizzle setup + schema introspection~~ ✅

`drizzle-orm`, `drizzle-kit`, `postgres` installed. Schema introspected to `src/lib/db/schema.ts`. Drizzle client at `src/lib/db/index.ts`.

### ~~1.8 Search API route + Typesense client~~ ✅

`web/src/lib/search/index.ts` (Typesense client, server-side). `web/src/app/api/search/route.ts` (Next.js API route proxying to Typesense with filter support).

### ~~1.9 License-aware image component~~ ✅

`web/src/components/artifact-image.tsx` — embeds CC0 directly, embeds with attribution for CC-BY variants, shows placeholder with link-out for restricted/unknown. 8 component tests passing (Vitest + React Testing Library).

### ~~1.10 Search landing page (`/`)~~ ✅

Search bar, faceted filters (sidebar), artifact cards in grid layout, pagination. Suggested searches (Karnak, Thutmose III, etc.) shown on empty state. Server-rendered.

### ~~1.11 First full pipeline run~~ ✅

Full pipeline materialized via Dagster: `raw_met` → `normalize_met` → `sync_search`. 27,969 Met objects ingested, normalized, and indexed in Typesense. Search returns Met artifacts on localhost:3000.

## Milestone 2: Harvard + Brooklyn

Add the other two museums to stress-test normalization across different data shapes. The pipeline, search index, and web already work from Milestone 1. Harvard first — Brooklyn's old API was retired but an undocumented replacement was found (see `docs/museum-sources/brooklyn.md`).

### ~~2.1 Harvard fixtures + mapper + tests~~ ✅

4 real Harvard API responses saved to `tests/fixtures/harvard/`. `pipeline/assets/normalize/harvard.py` implements `MapperProtocol`. Handles period/dynasty splitting ("Late Period, Dynasty 26"), multiline medium with `\r\n` delimiters, places array filtering for "Creation Place", date 0→null. 74 tests in `tests/test_mappers/test_harvard.py`, all passing. PR #7.

### ~~2.2 Harvard ingest asset~~ ✅

`pipeline/assets/ingest/harvard.py` — Dagster asset that paginates Harvard API (`culture=Egyptian`, 100/page, ~8 pages for 722 objects). Stores raw JSON in `raw_harvard` table with upsert. Requires `HARVARD_ART_MUSEUMS_API_KEY` env var. PR #7.

### ~~2.3 Register Harvard in Dagster~~ ✅

`pipeline/definitions.py` updated with `raw_harvard` and `normalize_harvard` assets. `sync_search` deps updated to include `normalize_harvard`. Both museums appear in Dagster asset graph. 28,691 total indexed artifacts (27,969 Met + 722 Harvard). PR #7.

### ~~2.4 Brooklyn API exploration~~ ✅

Old REST API (`/api/v2`) is retired. Undocumented replacement discovered via browser network inspection: public search API at `search.brooklynmuseum.org/api/search` (no auth, CORS `*`, max page size 50) plus RSC detail pages for full Sanity CMS object data. 8,832 objects in "Egyptian, Classical, Ancient Near Eastern Art" department. Full documentation in `docs/museum-sources/brooklyn.md`. PR #8.

### ~~2.5 Brooklyn fixtures + mapper + tests~~ ✅

5 real Brooklyn Museum fixtures (merged search API + RSC detail data) in `tests/fixtures/brooklyn/`: rich object (Isis Nursing Horus, 4035), dynasty typo (Head of Akhenaten, 60260), non-Egyptian culture (Cypriot Juglet, 3198), sparse/no-image (Model of Hoe, 123351), uncertain provenance (Funerary Cone, 118436). `BrooklynMapper` implements `MapperProtocol` with multi-material medium parsing, geography type → origin_certainty mapping, dimensions whitespace cleanup, thumbnail URL construction. 100 tests in `tests/test_mappers/test_brooklyn.py`, all passing. PR #9.

### ~~2.6 Brooklyn ingest asset~~ ✅

`pipeline/assets/ingest/brooklyn.py` — two-phase Dagster asset: (1) paginate search API via `requests` (no bot protection), (2) fetch RSC detail pages via Playwright headless browser (bypasses Vercel Security Checkpoint by establishing browser context first, then using `page.evaluate(fetch(...))` for RSC payloads in batches of 20). Merges both sources into `raw_brooklyn` table. Errors accumulated and logged per-object, not silently swallowed. No API key needed. Requires `uv run playwright install chromium`. PR #9.

### ~~2.7 Register Brooklyn in Dagster~~ ✅

`pipeline/definitions.py` updated with `raw_brooklyn` and `normalize_brooklyn` assets. `sync_search` deps updated to include `normalize_brooklyn`. All three museums appear in Dagster asset graph. 250 tests passing (all mappers + structural tests). PR #9.

### ~~2.8 Schema adjustments~~ ✅

Added `provenance` text column to canonical artifacts — available from Brooklyn (925 records, 10.5%) and Harvard (151 records, 21%), not Met. `inscribed` (Brooklyn-only, sparse) deferred. Full stack: SQLAlchemy model → Pydantic model → Alembic migration `3a1c350217d9` → Drizzle introspection → mapper updates for Brooklyn and Harvard → test assertions. Also added Brooklyn culture filter (`is_egyptian`) to exclude ~1,278 non-Egyptian objects (Greek, Roman, Cypriot, etc.) during normalization, expanded geography type mapping (11 types), and hardened null geo entry handling. 7,554 Brooklyn artifacts normalized. PR #10.

## Milestone 3: Authority Data + Enrichment

Authority files are built from real data ingested in Milestones 1–2. The detailed operational plan is in [normalization-plan.md](normalization-plan.md). Architectural decisions are in [ADR-012](adr/012-authoritative-sources.md) (sources), [ADR-013](adr/013-structured-dating-fields.md) (structured dating), [ADR-014](adr/014-exclude-non-ancient-records.md) (exclusion list), [ADR-015](adr/015-findspot-and-production-place.md) (findspot vs production), and [ADR-016](adr/016-royal-display-name-anglicized-nomen.md) (Conventional English Display Form).

The work is sequential by authority — dynasties first as the smallest, most constrained vocabulary, then periods, then rulers, then sites. Each tier validates the authority/enrich pattern before the next one starts.

### ~~3.1 Phase 0: Source acquisition~~ ✅

Acquire raw reference data per ADR-012 into `pipeline/pipeline/authority/sources/`. The operational protocol lives in [`docs/playbook-phase-0-ocr-transcription.md`](playbook-phase-0-ocr-transcription.md) — most recent iteration adds **Step 11.5 risk-driven automated checks** (PR #41) so reviewer-flagged failure-mode categories become deterministic checks in each source's diff script rather than per-row human to-dos. These can run in parallel:

- ~~Hornung/Krauss/Warburton (2006) chronology table~~ ✅ — 203-row transcription in `authority/sources/hkw-chronology-2006/reconciled.jsonl` (Early Dynastic → Alexander). PR #18.
- ~~Wikipedia Ptolemaic dynasty~~ ✅ — 24-row source in `authority/sources/wikipedia-ptolemaic/reconciled.jsonl` (Ptolemy I–XV + 8 queens, 305–30 BCE). Fills gap left by HKW. PR #19.
- ~~Wikidata pharaohs SPARQL dump~~ — **Dropped and replaced by pharaoh.se.** Wikidata had persistent quality issues (fictional characters, non-pharaohs, 0% prenomen coverage). Pharaoh.se (CC BY 4.0, expert-curated, full five-name titulary sourced from Beckerath) landed in `authority/sources/pharaoh-se/reconciled.jsonl`. See ADR-012 for the decision record. PR #21 / superseding PR.
- ~~Trismegistos Geo TM Places~~ — **Dropped.** Papyrological bias: pharaonic sites subsumed under coarse toponyms (e.g., Deir el-Bahari, Valley of the Kings, Medinet Habu all lumped into TM Geo 1341). Replaced by iDAI.gazetteer (see below). PR #22 closed.
- ~~Theban Mapping Project~~ — **Dropped.** Site offline (403/503), no API, ARCE copyright. See `docs/site-authority-research.md`.
- ~~iDAI.gazetteer site authority (CC BY 4.0)~~ ✅ — REST API at `gazetteer.dainst.org`. 2,061 fetched, 984 after archaeological-site/area/landform filter. 29/30 canary sites confirmed. `pipeline/pipeline/authority/sources/idai-gazetteer/reconciled.jsonl`. PR #27.

**Additional sources required before Phase A can start.** Per constitutional rule 1 ("work like a scholar"), every fact in the authority layer must trace to a committed raw source. HKW + pharaoh.se + iDAI.gazetteer + Wikipedia-Ptolemaic cover most structured data but leave concrete gaps: queens, KV/QV/TT tomb occupants, Memphite site granularity, OK royal-family prosopography, sub-period boundaries, SIP/TIP concurrency, Dyn 0 ruler list, Dyn 7 convention, the Argead bridge. The following sources close those gaps. Each becomes its own subdirectory under `pipeline/pipeline/authority/sources/` with a `README.md` documenting method, a fetch/transcription script where applicable, a raw artifact (PDF page, scraped HTML, or CSV), and a `reconciled.jsonl`.

Cross-source rationale ("why these sources, not others") lives in `docs/authority-sources-rationale.md` — per-source "what gap each closes", why-this-edition justifications, aggregator alternatives considered and rejected, out-of-scope acknowledgments.

- **Dodson & Hilton royal families (NK–LP queens)** → `sources/dodson-hilton-queens/reconciled.jsonl`. Transcribe the Brief Lives prosopographical entries from *The Complete Royal Families of Ancient Egypt* (Dodson & Hilton, Thames & Hudson, 2004). Covers queens, princes, princesses, and royal genealogies not in pharaoh.se. Primary fix for the missing-queens gap from the New Kingdom onward (Nefertiti, Nefertari, Tiye, Ahmose-Nefertari, Ankhesenamun, etc.). Landed as a series of per-section PRs rather than one mega-PR:
  - ✅ **Dyn 18 "Power and the Glory"** (printed pp. 137–141) — 59 rows (47 main + 12 Unplaced). Pre-Amarna 18th Dynasty queens, king's mothers, king's sons and daughters; includes Ahmes B, Hatshepsut D (as queen), Iset A, Mutemwia, Tiaa A, Meryetre-Hatshepsut. PR #37.
  - ✅ **"The Amarna Interlude"** (printed pp. 154–157 — Brief Lives sub-block only; narrative chapter prose pp. 142–153 is out of scope) — 41 rows (36 named + 5 lacuna-group; no Unplaced sub-block). Nefertiti, Kiya, Meryetaten, Ankhesenpaaten/Ankhesenamun, Tutankhuaten, Ay A, Horemheb, Tiye A, Tey, Yuya, Tjuiu. PR #38.
  - ✅ **"The House of Ramesses" + "Feud of the Ramessides" + "Decline of the Ramessides"** (printed pp. 170–175, 182–183, 192–194 — the three Brief Lives sub-blocks only; Dyn-19/20 narrative chapter prose is out of scope) — 170 rows (125 House + 10 Feud + 33 placed Decline + 2 Unplaced Decline). Dyn 19/20 prosopography: Ramesses II's ~100 children (the densest sub-block in the book), Nefertiry D Meryetmut, Isetneferet A, Maathorneferure (first Hittite-princess diplomatic marriage), Tawosret, Iset D Ta-Hemdjert, Nubkhesbed, Tyti, Pentaweret. This PR also introduces the composite `(dh_id, sub_period)` primary key in `merge.py` and `fix_rows.py` — D&H both lists Takhat A and Isetneferet C under two sub-sections each (same individual, two entries with distinct prose/roles), and reuses labels such as Ramesses C for different individuals across sub-periods; the composite key preserves both types of row.
  - 🔜 **Earlier chapters** (Chapter 1 Early Dynastic / OK, Chapter 2 1IP/MK/2IP, Chapter 4 3IP, Chapter 5 Late Period / Ptolemaic) — separate PRs; OK coverage is known-weaker here so `sources/baud-1999-ok-royal-family/` is the preferred OK source.
- **Baud 1999 Old Kingdom royal family** → `sources/baud-1999-ok-royal-family/reconciled.jsonl`. Transcribe the prosopographical *Corpus* (vol. 2) from *Famille royale et pouvoir sous l'Ancien Empire égyptien* (Baud, BdE 126, IFAO 1999). Vol. 1 narrative and vol. 2 appendices A/B/C are out of scope. This is the OK analogue of Dodson-Hilton — without it, OK queen/consort coverage will be thin while NK/LP is dense, producing an uneven authority. Required, not optional. Multi-chunk (~7 PRs keyed by Baud's own numbered entries `[1]`–`[282]`); see `docs/handoff-baud-next-chunk.md` for the chunk plan, schema, and Baud-specific reviewer risks (hedge preservation, transliteration-verbatim).
  - ✅ **Chunk 1** — entries `[1]`–`[40]`, physical pp. 11–49 of vol. 2 — 40 rows. Covers Dyn 3–6 entries alphabetically from `///-Ḥr [1]` through `ꜥnḫ-Špss-kꜣ.f [40]`. Flagship queens `Jnt-kꜣ.s [22]`, `Ankhesenmeryre I [37]`, `Ankhesenmeryre II [38]`. PR #53.
  - ✅ **Chunk 2** — entries `[41]`–`[80]` + Baud's sub-entry `[60a] Pn-mdw`, physical pp. 49–82 — 41 rows. Flagship: `Ptḥ-špss [68]` (High Priest of Ptah under Niouserrê); `Mrr-wj-kꜣ.j [83]`'s son `Mrjj-Ttj [81]` boundary-skipped to chunk 3. PR #57.
  - ✅ **Chunk 3** — entries `[81]`–`[120]` + sub-entries `[94b]` Nj-ꜥnḫ-Ḥwt-Ḥr and `[101a]` N(j)-s(w)-jr(w), physical pp. 82–109 — 42 rows. Includes baud-98 Nj-mꜣꜥt-Ḥp I (Dyn 2/3 transition) and Mrjj-Ttj's father Mrr-wj-kꜣ.j [83]. PR #58.
  - ✅ **Chunk 4** — entries `[121]`–`[160]` + sub-entries `[126a]`, `[133b]`, `[139a]`, physical pp. 109–141 — 43 rows. PR #59.
  - ✅ **Chunk 5** — entries `[161]`–`[200]`, physical pp. 142–179 — 40 rows (no sub-entries). Includes Khentkaus I [186] and Niouserrê [187]. PR #60.
  - ✅ **Chunk 6** — entries `[201]`–`[240]` + sub-entry `[206a]`, physical pp. 179–213 — 41 rows. PR #61.
  - ✅ **Chunk 7** — entries `[241]`–`[282]`, physical pp. 214–244 — 42 rows (no sub-entries). Final chunk. Total corpus 289 rows. PR #62.
  - 🟡 **Partial human review sign-off** (PR #63) — 21 of 289 rows verified at citation-fidelity layer (one flagship + one random-drift + all 7 sub-entries per chunk). Scholarly judgment fields on all rows remain provisional pending a specialist / credentialed-Egyptologist pass. Logs in `sources/baud-1999-ok-royal-family/human-review-2026-04-18-chunk<N>.md`. Sign-off surfaced translit drift (`ꜥd-mr → ꜥḏ-mr` 18 instances; `tꜣtj → ṯꜣtj` 11 instances in the vizier compound) fixed in the same PR via `_WORD_LEVEL_FIXES` in `fix_rows.py`.
  - 🔜 **Follow-up: Phase-A handling of Baud structural oddities.** Three patterns identified during PR #63 verification that Phase-A name reconciliation needs to special-case:
    - **Lacuna names** (e.g. `baud-206a` `name_egyptian = "Sꜥnḫ-///"`): Phase A should treat the literal `///` lacuna marker as "unnamed / partially-attested" rather than a matchable transliteration. Needs a `name_attested: boolean` or `name_has_lacuna: boolean` flag at reconciliation time; row still contributes monument/site/role data but is excluded from name-based cross-source joins.
    - **Nom perdu entries** (e.g. `baud-282` `name_egyptian = "Nom perdu, fils de Pépi II, représenté dans le temple funéraire de ce roi"`): descriptive French prose stored as `name_egyptian` because the actual Egyptian name is lost. KEEP in the authority (useful for site/date/role statistics), but Phase A should set `name_attested: false` to exclude from cross-source name-matching. Same flag as the lacuna case.
    - **Name collisions across distinct individuals** (e.g. `baud-143` vs `baud-144` both `Rꜥ-ḥtp` at Meidoum vs Gîza; `baud-231` vs `baud-232` both `Kꜣ.j-pw-Ptḥ`; several `Nj-mꜣꜥt-Ḥp` homonyms). Phase A person-authority matching across Baud / Dodson-Hilton / Porter-Moss must disambiguate by `monument` + `date_attested` + `pm_ref`, not by `name_egyptian` alone.
  - 🔜 **Follow-up: joint-entry [209] split or joint-flag.** `baud-209` is a single row for TWO attested individuals (`Snj*` and `Zzj*`, husband + wife buried together). Their individual title lists are mashed together in `titles_from_baud`. Phase A should either (a) split into two rows with `joint_source_entry: "baud-209"` flag, or (b) keep as one row with a `joint_entry: true` flag and a sub-structure separating per-person titles. Deferred because splitting means inventing IDs Baud did not author.
  - ✅ **Follow-up: translit drift sweep across all Phase-0 sources** — audited 2026-04-19, no action needed for Dodson-Hilton / Kitchen / Ryholt. Findings: Dodson-Hilton and Kitchen contain zero Egyptological transliteration characters in their reconciled extracts (D&H uses English royal-family prose; Kitchen uses English prenomens), so Baud's `_WORD_LEVEL_FIXES` template has nothing to match. Ryholt does carry transliterated king names but (a) no fallback ayin/aleph codepoints (ˁ/ɛ/ɜ) are present — the chunk-1 character-level remap isn't needed, and (b) no `ꜥd-mr` / `tꜣtj` / `zꜣb tꜣtj` occurrences — those are administrative titles, and Ryholt's schema only carries king names. The Baud-specific drifts were Baud-specific.
    - 🔜 **Separate follow-up (scholarly, not substring-sweep): Ryholt yod convention audit.** Ryholt's `*_transliterated` fields are internally inconsistent — 83 plain `i` vs 10 Leiden `ỉ` for the Egyptological yod (e.g. `ḥtp-ỉb-rꜥ` vs `sꜥnḫ-ib-tꜣwy`). Also one nomen appears as both `ini` and `i-n=i`. Deferred because: (a) pharaoh.se reconciliation in Phase A normalises to pharaoh.se's convention regardless; (b) the primary pharaoh.se match key is the conventional English name (`Sobekhotep I`), not the transliteration; (c) resolving requires an egyptologist-reviewer pass on each `i` position (yod vs plain vowel), not a mechanical substring fix.
- 🟡 **Porter-Moss Vol I (Theban Necropolis — KV/QV/TT tombs)** → `sources/porter-moss-theban-necropolis/reconciled.jsonl`. Transcribe the tomb index with occupant, dynasty, and location for KV1–KV65, selected QV, and TT1–TT400. Scope is Theban only — Memphite material needs Vol III (next task). Follows the default derived-extract path per the playbook's "Rights policy" section: PDFs stay in `proprietary/books/`, only the reconciled structured extraction is committed. Moss's tomb *descriptions* (iconography, epigraphy prose) are deliberately out of scope. Under the project's working posture, tomb-number and occupant data are extracted as facts rather than expressive content; the source `README.md` records the derived-extract basis AND the Griffith Institute licence terms under which the scans are used.
  - ✅ **Chunk 1: KV1–KV10** (PM I.2 § I.A "Tombs", printed p.495–518). 10 rows in `reconciled.jsonl`. **Method note:** PM PDFs from the Griffith Institute carry a publisher text layer; OCR subagent step (per ADR-017) is replaced by deterministic `pypdf` text-layer extraction. Documented in `sources/porter-moss-theban-necropolis/transcribe.md` § "Method deviation". PR #66.
  - ✅ **Chunk 2: KV11–KV20** (PM I.2 § I.A, printed p.518–546). 10 rows. Exercises several new row shapes vs chunk 1: KV12 uninscribed (`occupant_name=null`, `occupant_role="Unknown"`), KV13 Bay the Chancellor (non-royal `Official` role + regnal-dating note `Temp. Merneptah-Siptah`), KV14 Tausert usurped by Setnakht, KV17 Sethos I with `Belzoni's tomb` classical alias, KV18 Ramesses X unfinished + `formerly XI`, KV19 Raʿmeses-Mentuhirkhopshef as `Prince` (royal son, never reigned), KV20 Hatshepsut ruling-as-King. Closes the cross-chunk KV3↔KV11 symmetry gap from chunk 1. **Note:** KV21 is absent from PM I.2 § I.A — the list jumps from KV20 to KV22, so chunk 2 holds 10 rows despite the "KV11–KV20" label. PR #68.
  - ✅ **Chunk 3: KV22–KV46** (PM I.2 § I.A, printed p.547–562). 11 rows over a sparse range: {KV22, KV23, KV34, KV35, KV36, KV38, KV39, KV42, KV43, KV45, KV46}. **KV24–KV33, KV37, KV40, KV41, KV44 are absent from PM I.2** — PM's 1964 edition did not catalogue these as inscribed royal tombs. Three new row shapes: `location_sub_area = "West Valley"` (KV22 Amenophis III, KV23 Ay), multi-occupant (KV46 Yuia and Thuiu, parents of Queen Teye, role `Royal Family`), re-used (KV45 Userhet Dyn XVIII re-used by Merenkhons Dyn XXII). KV39 is the first `Uninscribed tomb` row with an explicit modern attribution (Weigall 1911 → Amenophis I) captured in `notes_from_pm`; KV42 preserves PM's `(?)` attribution-uncertainty marker as a notes clause. PR #69.
  - 🟡 **Chunk 4 in progress (this PR): KV47–KV57** (PM I.2 § I.A, printed p.564–568). 5 rows: {KV47, KV48, KV55, KV56, KV57}. **KV49–KV54 and KV58–KV61 are absent from PM I.2 § I.A** — PM jumps 48 → 55 and 57 → 62. Introduces attribution-hedging patterns PM uses in this range: KV55 PM's headword is `Probably AMENOPHIS IV, formerly attributed to Queen Teye or to Smenkhkare<` — the structured `occupant_name` strips the `Probably` / `formerly attributed to` hedges (extract = `Amenophis IV`) while the full PM hedge is recorded in `notes_from_pm`. KV56 is PM's `'Gold Tomb', uninscribed.` — another `occupant_name=null` + `occupant_role="Unknown"` row with PM's nickname captured in notes. KV47 Merneptah-Siptah, KV48 Amenemopet (Vizier, temp. Amenophis II — first `Vizier` role in the chunks), KV57 Haremhab round out the chunk.
  - 🔜 **Chunk 5: KV62 Tutankhamun (standalone)** (PM I.2 § I.A, printed p.569–586 / physical p.111–128). **KV62 is transcribed as its own chunk** because PM's entry spans roughly 17 printed pages — more than 3× the size of chunk 4 — with an unusually dense bibliographic ribbon (DAVIS; CARTER and MACE; CARTER alone; BURTON photographs; etc.) and a headword-block that merits precise handling (`'Tomb of the Pharaoh', discovered by Carter and Carnarvon 1922` phrasing, the shared `Workmen's Rest-houses` / `Graffiti` sub-sections that follow). Scope for the chunk-5 PR: one row for KV62 with full PM-verbatim name (`Tut'ankhamun` — PM uses the apostrophe form, not `Tutankhamun`), occupant_alt_names from any quoted nicknames, `notes_from_pm` capturing the discovery + intact-burial phrasing PM prints in the headword, and `source_citation.page` pinned to KV62's first printed page. The Workmen's Rest-houses and Graffiti sub-sections that appear before the next section boundary are NOT individual KV rows — they're sub-section prose attached to § I.A and are out of scope for the tomb-row extraction (may land as their own notes in a later sites-authority pass).
  - 🔜 **Chunk 6: KV63–KV65** (remaining numbered KV tombs in PM I.2 § I.A, if any are catalogued). Small sweep chunk. If PM I.2 1964 does not list KV63+ (post-1964 discoveries), this chunk is empty and the KV series closes at chunk 5.
  - 🔜 **Later chunks** (each its own PR): the South-West Valleys / Dra' Abu el-Naga / Asasif / Deir el-Bahri / Sheikh Abd el-Qurna / Khokha / Qurnet Mura'i / Deir el-Medina / Ramesseum / Medinet Habu sections from PM I.2 (valleys use non-KV ID schemes — `DAN`, `DEM` etc. TBD when first valley lands). Then `QV1`–`QV80` from PM I.2 § X (Valley of the Queens). Then `TT1`–`TT400+` from PM I.1 (many chunks, likely keyed by numbered-tomb decades).
  - 🔜 **Follow-up: `modern_attribution` schema field (cross-source).** PM's headwords reflect ~1960s scholarship (PM I.2 is Moss & Burney's 1964 2nd ed.) and are preserved verbatim per the derived-extract posture. For example, KV5 is attributed to Ramesses II in PM but was re-identified as the tomb of the *sons* of Ramesses II by Weeks' Theban Mapping Project (1995 rediscovery, formally published Weeks 2000 *KV 5: A Preliminary Report*, ARCE). A schema-wide `modern_attribution` field (or similar) should carry the modern scholarly correction alongside the source-verbatim value. Also affects any other period-snapshot source (Baud 1999 (Old Kingdom), D&H, future PM chunks) where modern re-identification diverges from the source's headword. **Resolve via new ADR** before the §3.3 schema-migrations step — shape parallels ADR-015 (findspot vs production) / ADR-016 (display-name discipline) in that it defines a canonical structural column on a core entity. Direct schema edits without an ADR would bypass the repo's decision-discipline pattern.
- **Porter-Moss Vol III (Memphis — Giza/Saqqara/Abusir)** → `sources/porter-moss-memphis/reconciled.jsonl`. Transcribe the site/tomb index from PM III (Málek's revision, 1974–1981, with ongoing Griffith Institute updates). Met/Brooklyn/Harvard hold substantial Memphite material; without this the site authority will systematically under-resolve Giza/Saqqara/Abusir provenances. Same derived-extract basis and same Griffith Institute licence recording requirement as Vol I — record both in the source README. Moss's tomb descriptions are out of scope, same as Vol I.
- ~~**Shaw OHAE period chapter date-ranges**~~ ✅ — 13-row transcription of the dated-period chapter banners (chapters 2–10 and 12–15) in `sources/shaw-ohae-2000/reconciled.jsonl`. Sub-periods Naqada I (Amratian) and Naqada II (Gerzean) are captured on the chapter 3 row from Midant-Reynes' opening chronology section (pp. 42-43); all other rows have `sub_periods: []` because their chapter openings do not state BCE sub-period boundaries. Amarna/Ramesside/Saite narrowly-defined spans must come from a different source in Phase A. PR #32.
- ~~**Ryholt 1997 SIP political tables**~~ ✅ — 157-row extraction of Ryholt's Part VI Catalogue of Attestations + Chronological Tables (physical PDF pp. 336–416) in `sources/ryholt-1997-sip/reconciled.jsonl`. Every king in Dynasties 13–17 plus the Abydos Dynasty and unattributed bucket, with five-name titulary, anglicised nomen/prenomen from Chronological Tables, BCE dates, polity per dynasty, and `pdf_pages` range citation. Pipeline: Claude Code subagent OCR → three parallel Claude Code subagent extractors → deterministic majority-vote merge → LLM-reviewer pass → human sign-off (pending). Per ADR-017. PR #34.
- ~~**Kitchen TIPE 1996 (Part VI Tables 1, 3, 4)**~~ ✅ — 60-row transcription of Kitchen's Preferred-Dates chronology (physical PDF pp. 240–243) in `sources/kitchen-tipe/reconciled.jsonl`. Covers Ramesses XI + the 21st-Dyn Tanite and Theban-HPA parallel lines, all of Dyns 22 and 23 (including Harsiese A as a Theban co-regent), the 24th + Early-Saite + Proto-Saite streams, the 25th Nubian dynasty, and the 26th Dynasty (captured verbatim from Table 4 even though it is beyond TIP proper). Schema carries `kitchen_id`, anglicised name, prenomen, `start_bce` / `end_bce` / `length_of_reign_years`, `approximate` flag for `c.`/`?`/`??` hedges, `polity`, Dyn-21 Tanite↔HPA `concurrent_with_kings` (computed deterministically by interval overlap, not LLM-guessed), and `notes_from_kitchen`. Pipeline: Claude Code subagent OCR → three parallel Claude Code subagent extractors → deterministic majority-vote merge → `fix_rows.py` for concurrency recomputation and egyptologist-reviewer spot corrections → human sign-off (pending). Per ADR-017. **Post-1996 revisions (Kitchen 2009 Broekman/Demarée/Kaper eds., Aston 1989 *JEA* 75, Jansen-Winkeln *Inschriften der Spätzeit*) land in separate PRs as revisions-only deltas** — the original "multi-source in one slot" framing has been superseded by the per-source Phase 0 discipline.
- **Manetho fragments for Dynasty 7** → `sources/manetho-fragments/reconciled.jsonl`. Source for the scholarly convention of "Dynasty 7" as Manetho's ghost dynasty. Preferred edition: Verbrugghe & Wickersham 1996 *Berossos and Manetho* (Michigan) — the modern critical edition a referee will expect. Waddell 1940 Loeb is a commonly-cited alternative. Follows the derived-extract path per the playbook's "Rights policy" section: PDF (once acquired) stays in `proprietary/books/`, only structured extraction JSONL of the fragment-attested Dyn-7 kinglist is committed. Record the edition used and derived-extract basis in the source `README.md`. (Previously this bullet required per-edition copyright verification as a precondition; that requirement is now subsumed by the playbook's derived-extract default. What lands in `reconciled.jsonl` is the epitomator-attributed figures — dynasty number, ruler count, regnal totals cited by Africanus / Eusebius / Barbarus — with names normalised to the authority's transliteration scheme; neither Verbrugghe & Wickersham 1996 nor Waddell 1940 is preserved verbatim, so the translators' English rendering never reaches the committed extract. The source `README.md` must still pin which critical edition was consulted.)
- **Hölbl Argead bridge (Alexander → Ptolemy I)** → `sources/holbl-2001-argead/reconciled.jsonl`. Transcribe the opening chronological table of *A History of the Ptolemaic Empire* (Hölbl, 2001) for Alexander III, Philip III Arrhidaeus, Alexander IV — the 332–305 BCE bridge dynasty absent from HKW and pharaoh.se.
- **Dreyer + Kaiser + Hendrickx for Predynastic / Dyn 0** → `sources/predynastic-dyn0/reconciled.jsonl`. HKW Ch. 2 gives the seriation framework but not the ruler list. Combine: **Dreyer 1998** *Umm el-Qaab I* (AV 86, DAI) for the Dyn 0 / Abydos U-j rulers (Iry-Hor, Ka, Narmer — critical, without Dreyer the Dyn 0 authority is wrong); **Kaiser 1990** (*MDAIK* 46) for Stufe terminology; **Hendrickx 2006** in HKW Ch. 2 or *The Relative Chronology of the Naqada Culture* for Naqada I–III chronology.
- **Beckerath 1999 Handbuch (cross-reference / fallback)** → `sources/beckerath-1999-hak/reconciled.jsonl`. Transcribe from *Handbuch der ägyptischen Königsnamen*, 2nd ed. (Beckerath, MÄS 49, 1999). pharaoh.se derives from it, so this is a fallback for rulers where pharaoh.se is ambiguous, silent, or where a curator wants to verify a titulary entry against the primary. Expected by any scholarly reviewer. Can be lower priority if pharaoh.se proves sufficient, but land it before Phase A completes.

Before these sources land, Phase A curation cannot begin. Each task is a separate PR — do NOT bundle. Transcription method must be documented (book, edition, page range, whether OCR/scraped/manually typed, any normalisation applied).

**Roman-period deferral** — per the Egyptological review, a Roman-period authority is acceptable to defer to post-beta, but the UI must flag Roman-period artifacts as "period authority pending" rather than silently show no period. When Roman chronology is added, the source will be Bagnall & Rathbone 2004 *Egypt from Alexander to the Early Christians* (Getty) and/or Bagnall *Egypt in Late Antiquity* (Princeton 1993).

### 3.2 Phase A: Authority curation

Hand-curate the four authority files in dependency order. Each file has the mandatory `_source` block (ADR-012), uses the structured shapes defined in ADRs 013 and 016, and seeds its `aliases` array from the most-frequent distinct raw values in `catalog.artifacts`.

1. **`dynasties.json`** — Dynasties 0–31 + Ptolemaic. Each entry: `id`, `display`, `dates`, `parent_period`, `polity` (for concurrent Intermediate-Period dynasties — 13th, 14th, 15th, 16th, 17th in different regions), `concurrent_with`, `aliases`
2. **`periods.json`** — Predynastic through Ptolemaic. Sub-periods (Amarna, Ramesside, Saite) are their own entries with `parent_id`. Sub-period replaces parent when raw text resolves more specifically
3. **`rulers.json`** — Per ADR-016: canonical `display` (Conventional English Display Form), structured `titulary` object with all five name parts, flat `aliases` for the matcher. Coverage priority: New Kingdom and Late Period
4. **`sites.json`** — Hierarchical structure (`egypt > upper_egypt > thebes > deir_el_bahri > tt_358`), ~100 most-referenced sites + KV/TT tombs

**Deferred schema decision: BCE chronology convention.** Each Phase-0 source currently carries BCE dates in its own convention and they do not agree. Pharaoh.se derives primarily from Beckerath 1997 (*Chronologie des pharaonischen Ägypten*, MÄS 46); Kitchen 1996 (*TIPE* 3rd ed.) differs; Hornung/Krauss/Warburton 2006 (*Ancient Egyptian Chronology*, HdO) differs from both. `rulers.json` (and any authority that stores canonical BCE dates) must pick a single convention as the canonical `date_bce_*` and either discard or preserve-as-alt the others. Surfaced by the 2026-04-19 pharaoh.se pressure-test audit (90% name match against Kitchen; dynasty-boundary shifts typically ≤10y, but per-ruler reign-length debates — Takelot II/III, Dyn-22/23 co-regencies, Osorkon II — push individual ruler start/end dates up to ~40y apart between conventions). **Resolve via new ADR** (parallel in shape to ADR-013 / ADR-016 on other canonical-structure questions — ADR-013 itself is scoped to artifact-level dating qualifier/certainty/relation and should not be stretched to cover which chronology is canonical on the ruler authority) before the §3.3 schema-migrations step — without it, `rulers.json` cannot take shape.

Per constitutional rule 3 (deterministic enforcement), add structural tests in `pipeline/tests/test_structure.py` that load every authority file and assert:

- Every authority file has a non-empty `_source` block and the `raw_file` it references exists on disk (ADR-012)
- Every entry in `rulers.json` has its `display` value present in the `nomen` titulary list (ADR-016)
- `pipeline/pipeline/assets/normalize/exclusions.py` exists, exports `is_in_scope`, and is imported by every normalize asset (ADR-014)

### 3.3 Schema migrations

Several schema changes are required before the enrich phase can land. Each follows rule 1: SQLAlchemy → Pydantic → Alembic → Drizzle introspect → commit together.

- Add `Qualifier`, `Certainty`, `Relation` enums to `pipeline/types/sources.py` (ADR-013)
- Add structured dating columns: `dynasty_ids`, `dynasty_qualifier`, `dynasty_certainty`, `dynasty_relation`, and the `period_*` equivalents (ADR-013)
- Replace `origin_site_id`, `origin_site_display_name`, `origin_certainty` with `production_site_id`, `production_site_certainty`, `findspot_site_id`, `findspot_site_certainty` (ADR-015)
- Add `pipeline/pipeline/assets/normalize/exclusions.py` exporting `is_in_scope(raw)` and wire it into every normalize asset (ADR-014)
- **Pending ADR (see §3.2 deferred schema decision):** canonical BCE chronology convention for the ruler authority — blocks the `rulers.json` shape and the `enrich_rulers` column choices.
- **Pending ADR (see §3.1 PM Theban chunk-1 follow-up):** `modern_attribution` (or equivalent) structural field to carry post-source scholarly re-attributions alongside PM-verbatim / Baud-verbatim / D&H-verbatim values — blocks any cross-source site/ruler enrichment that consumes period-snapshot authorities.

### 3.4 Phase B: Enrich assets

One Dagster asset per authority in `pipeline/pipeline/assets/enrich/`, in the same order as Phase A. Each reads `catalog.artifacts`, deterministically matches the raw text against the authority's `aliases` (exact match, case-insensitive, whitespace-normalized), and writes resolved IDs back to the same row. Anything that doesn't match exactly goes to the review queue (ADR-009). `sync_search` gains all four as upstream deps.

- `enrich_dynasties` → populates `dynasty_ids`, `dynasty_qualifier`, `dynasty_certainty`, `dynasty_relation`
- `enrich_periods` → populates `period_ids`, `period_qualifier`, `period_certainty`, `period_relation`
- `enrich_rulers` → populates `ruler_ids` (list, for joint reigns); also regex-scans `date_display` for "reign of X" patterns since Brooklyn and Harvard mappers leave `ruler_display_name` empty
- `enrich_sites` → populates `production_site_id`, `findspot_site_id`, `tomb_temple_id`, `excavation_id` (`KV\d+`, `TT\d+`, `MMA\d+` regex against the known monuments list)

### 3.5 Review queue triage asset

Create `pipeline/assets/quality/review_queue_triage.py` — Dagster asset that processes pending fuzzy match reviews using an LLM (Haiku). Per ADR-009: fetch artifact + authority entry, ask LLM if the match is correct, write APPROVED/REJECTED/UNCERTAIN status. Approved variants get added to authority files.

### 3.6 Dagster asset checks

Implement `@asset_check` decorators per ADR-010 Layer 1: ingest completeness (record count vs API total), normalization validity (date ranges, enum values), authority coverage (unmatched value frequency), cross-museum site consistency. Emit coverage metrics as asset metadata.

### 3.7 LLM data audit asset

Create `pipeline/assets/quality/llm_audit.py` — Dagster asset that samples records and uses Haiku for semantic audit, batch anomaly detection, and authority variant suggestions per ADR-010 Layer 2.

## Milestone 4: Full Web UX

Remaining pages beyond the search landing page. The search page already works from Milestone 1.

### 4.1 Artifact detail page (`/artifact/[id]`)

Build the detail page: full artifact info, image (license-aware), link back to source museum, match explanation for provenance data. Related candidates section deferred to Milestone 6.

### 4.2 Site page (`/site/[id]`)

Build the site page: all artifacts from an origin site across all museums, with the site hierarchy visible (e.g., "Valley of the Kings > Western Thebes > Thebes"). Filters for narrowing within the site's artifacts.

### 4.3 Museum page (`/museum/[id]`)

Build the museum browsing page: a museum's Egyptian holdings with Egyptology-native filters (dynasty, ruler, site of origin, object type) that the museum's own site may not offer.

### 4.4 Visual regression and E2E tests

Set up Playwright for deterministic E2E tests: search returns results, filters work, detail pages load, license rendering is correct (DOM assertions for img vs link based on license). Add `toHaveScreenshot()` visual regression at desktop + mobile viewports.

## Milestone 5: Beta Launch

### 5.1 Production deployment

Deploy pipeline (Dagster), web (Next.js), Postgres, and Typesense. Configure production environment variables, database credentials, API keys. Set up the `catalog` and `web` Postgres schemas.

### 5.2 Full pipeline run + coverage stats

Execute full pipeline against live museum APIs: ingest all three museums, normalize, enrich, sync to Typesense. Record coverage stats: total artifacts, % with mapped ruler, % with mapped site, % with image.

### 5.3 Basic analytics

Add lightweight analytics to measure engagement: page views, search queries, filter usage. Keep it minimal — no user tracking beyond aggregate counts.

## Milestone 6 (optional): Map View + Companion Pieces

Valuable but not required for a useful beta (PRD Milestone 5).

### 6.1 Map view (`/map`)

Geographic visualization showing which museums hold artifacts from a given site. Click a site marker to see counts by museum and drill into specific objects. Use Leaflet or MapLibre.

### 6.2 Related candidates logic

Implement companion piece matching per ADR-008 confidence tiers: Tier A (shared excavation/tomb/temple ID), Tier B (same site + overlapping dates + related type), Tier C (same broad region). Display with clear labels — never imply certainty the data doesn't support.

### 6.3 Related candidates on artifact detail page

Add the related candidates section to `/artifact/[id]` using the matching logic from 6.2. Show Tier A/B/C results with clear confidence labels and match explanations.
