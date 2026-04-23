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

**Downstream stages are unchanged from the playbook:** three parallel extraction subagents read `raw/chunk-*.txt` and produce JSONL; `merge.py` majority-votes; `fix_rows.py` applies LLM-reviewer corrections; tests assert specific values.

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
| 8 | PM I.2 § X.A Valley of the Queens — 20 numbered QV tombs (QV33–QV75 sparse) | p.751–768 | p.292–313 | in-progress | (this PR) |

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
