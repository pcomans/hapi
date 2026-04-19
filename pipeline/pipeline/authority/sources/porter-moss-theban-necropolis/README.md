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

**Field semantics:**
- `tomb_id` — `KV<n>`, `QV<n>`, `TT<n>`. Letter-suffix variants (`KV5a`) are reproduced verbatim.
- `valley` — Coarse sub-area: `"Valley of the Kings"`, `"Valley of the Queens"`, `"Dra' Abu el-Naga"`, `"Deir el-Bahri"`, `"Asasif"`, `"Sheikh Abd el-Qurna"`, `"Khokha"`, `"Qurnet Mura'i"`, `"Deir el-Medina"`, `"Ramesseum"`, `"Medinet Habu"`. The valley a tomb belongs to is structural in PM (each numbered tomb sits within a section / sub-section).
- `occupant_name` — Conventional English form of the king's / queen's / official's name. Drawn verbatim from PM's headword (e.g. `Sethos I`, `Ramesses IV`, `Tut'ankhamun`). PM uses `Sethos` not `Seti`; preserved as-is, the name authority handles cross-resolution to `Seti I`.
- `occupant_alt_names` — Other names PM prints in the headword block, typically as a `('Tomb of X', or 'Tomb of Y'. ...)` parenthetical with classical-period aliases inside the quotes. KV9's `Memnon` (PM headword: `'Tomb of Memnon'`) is the chunk-1 example. The alias is captured even though the surface form is `Tomb of Memnon` — the alias attaches to the occupant per the museum-catalog convention "from the Tomb of Memnon" = "from KV9". Empty list `[]` when PM gives no parenthetical alt-name.
- `occupant_role` — Controlled vocabulary: `King`, `Queen`, `Royal Family`, `Vizier`, `Official`, `High Priest`, `Princess`, `Prince`, `Unknown`. KV almost always `King`, QV almost always `Queen`/`Princess`, TT mostly `Vizier` / `Official` / `High Priest`. PM does not always state the role bare; controlled-vocab assignment is a Phase A enrichment in advisory mode.
- `dynasty` — Roman-numeral dynasty as a STRING (`"18"`, `"19"`, `"20"`, `"XVIII"` etc. — final form normalised to Arabic numerals). PM does not always state dynasty in the headword; this is filled by reference to the king authority (pharaoh.se, Beckerath) downstream.
- `sub_period` — Optional finer chronological label (`"First Intermediate Period"`, `"Amarna"`, `"Saite"`). Null for most rows.
- `date_bce_approx_start` / `date_bce_approx_end` — Negative integers (BCE convention). Drawn from king-authority dates downstream, not from PM's text. Null until the cross-reference is wired.
- `location_sub_area` — Sub-region within the valley (e.g. `"East Valley"` for KV62 Tutankhamun). PM I.1 Appendix D gives this for TT; for KV the section header is the source.
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
- **Chunk 3 (this PR)**: `KV22–KV46` from PM I.2 § I.A, physical p.89–106. 11 rows: {KV22, KV23, KV34, KV35, KV36, KV38, KV39, KV42, KV43, KV45, KV46}. **KV24–KV33, KV37, KV40, KV41, KV44 are absent from PM I.2** — PM's 1964 edition did not catalogue these numbers as inscribed royal tombs (they correspond to uninscribed pits or post-1964 discoveries). Chunk 3 introduces three new row shapes: `West Valley` `location_sub_area` (KV22, KV23), the multi-occupant pattern (KV46 Yuia and Thuiu), and the re-used-tomb pattern (KV45 Userhet re-used by Merenkhons).
- **Future chunks** (each its own PR):
  - `KV47–KV65` and adjacent sparse ranges — one or two chunks across PM I.2 § I.A for the remaining numbered KV tombs. Note that KV62 Tutankhamun is a large standalone section that warrants its own chunk.
  - PM I.2 § I.B "Finds", § I.C "Rest-houses", § I.D "Graffiti" — one chunk if KV-related, else dropped.
  - PM I.2 § II–IX (South-West Valleys, Dra' Abu el-Naga, Asasif, Deir el-Bahri, Sheikh Abd el-Qurna, Ramesseum, Deir el-Medina) — chunked by section.
  - PM I.2 § X "Valley of the Queens" (QV1–QV80).
  - PM I.2 § XI "Medinet Habu", § XII "Objects from Thebes".
  - PM I.1 numbered tombs TT1–TT400+ — many chunks.

Per-chunk prompt files: `prompt.md` (chunk 1), `prompt-<chunk>.md` (chunks 2+). Per-chunk agent JSONLs: `raw/agent-{a,b,c}.jsonl` (chunk 1), `raw/agent-{a,b,c}-<chunk>.jsonl` (chunks 2+).

## Known gaps

- **King → BCE date lookup.** This source extracts the headword (occupant name); the BCE date fields stay null until the king authority (pharaoh.se) is reconciled in Phase A. Holding rows null is consistent with constitutional rule 4 (sparse rows are valid) and rule 7 (authority lookup, not hard-coded names in extracts).
- **Cartouches in the text layer render as garbage characters.** PM prints royal names with hieroglyphic cartouches inline; the text layer renders these as `(~~~ ::)`, `(•~~)`, etc. The conventional English name in titlecase before the cartouches is the extraction target. Don't try to recover the cartouches from the text layer — they're better-served by a future Beckerath/pharaoh.se cross-reference.
- **OCR-typo class fixed by `fix_rows.py`.** PM's text layer has predictable typos: `pi.` for `pl.` (plate), `1` for `l`, `BuRTON` capitalisation, `c` for `ʿ` (Egyptological ayin). Most of these don't reach the structured fields (they sit in the dropped body prose), but where they do (e.g. `Re c` instead of `Reʿ` in a king-name like `Khepermaʿtreʿ Ramesses VI`), `fix_rows.py` applies the same `_WORD_LEVEL_FIXES`-style normalisation as Baud's `fix_rows.py` template.
