# Dodson & Hilton 2004 — *The Complete Royal Families of Ancient Egypt*

Source of truth for non-king Egyptian royal-family members — queens, king's mothers, king's sons, king's daughters, and the extended family trees pharaoh.se doesn't cover.

## Citation

Dodson, A. & Hilton, D. (2004) *The Complete Royal Families of Ancient Egypt*. London: Thames & Hudson. ISBN 0-500-05128-3 / 978-0500051283.

- **Edition used:** first edition, 2004 hardback.
- **Retrieved:** 2026-04-15 (local scan).
- **PDF SHA-256:** `e636c49f3d0b5b6c6ec072cc6e7af9d605caf52d438c55cd84da9de7b07008a0`.

## Scope — current state

Brief Lives prosopographical sub-blocks from chapters 2 and 3. Extraction from the narrative chapter prose (Historical Background, The Royal Family, End of the Amarna Dynasty, etc.) is intentionally out of scope — only the prosopographical Brief Lives bullet-style entries are transcribed.

| PR | Section | Printed pp. | PDF-viewer pp. | Rows |
|----|---|---|---|---|
| #37 (merged) | Ch 3 *The Power and the Glory* — Brief Lives (Dyn 18 pre-Amarna) | 137–141 | 126–130 | 59 (47 placed + 12 Unplaced) |
| #38 (merged) | Ch 3 *The Amarna Interlude* — Brief Lives (Dyn 18 late) | 154–157 | 142–145 | 41 (36 named + 5 lacuna-group) |
| (merged) | Ch 3 *The House of Ramesses* — Brief Lives (Dyn 19 pt 1) | 170–175 | 157–162 | 125 |
| (merged) | Ch 3 *The Feud of the Ramessides* — Brief Lives (Dyn 19 pt 2) | 182–183 | 169–170 | 10 |
| (merged) | Ch 3 *The Decline of the Ramessides* — Brief Lives + Unplaced (Dyn 20) | 192–194 | 178–180 | 35 (33 placed + 2 Unplaced) |
| this PR | Ch 2 *The Head of the South* — Brief Lives + Unplaced (Dyn 11 transition) | 88–89 | 81–82 | 13 (12 placed + 1 Unplaced) |

Combined `reconciled.jsonl` 283 rows (Ch 3 New Kingdom: 59 Power + 41 Amarna + 125 House + 10 Feud + 35 Decline = 270; Ch 2: 13 Head of South).

Out of scope for this PR, landing in follow-up PRs:
- **Chapters 1, 2, 4, 5** (Early Dynastic / OK / MK / SIP / TIP / Late Period) — separate PRs; `sources/baud-1999-ok-royal-family/` is the preferred OK source and this book is known-weaker there.
- **Front-matter reference sections** ("The Pharaonic State" pp. 10–23, "The Royal Family" pp. 24–37, "Genealogical Groupings" pp. 38–42) are narrative exposition, not ruler-list data.
- **Chapter 3 narrative prose** (Historical Background, The Royal Family, End of the Amarna Dynasty — printed pp. 142–153 and equivalent for the other sections) is not extracted; only the Brief Lives sub-blocks are.
- **Genealogical chart figures** (visual diagrams on pp. 144–145 etc.) are not extracted as rows — the Brief Lives text entries contain the same parent/spouse/child relationships in prose form.
- **Illustration captions** describing photographs / reliefs — not royal-family rows.

**Eventual full-scope row count across all PRs:** ~300–400 once the earlier chapters (1 / 2 / 4 / 5) are transcribed; the Ramesside pass alone is larger than chunks 1 + 2 combined because Ramesses II's ~100 children produce the densest prosopographical sub-block in the book.

## Schema

One row per named royal-family member (queen, king's mother, king's wife, king's son, king's daughter, prince, princess, or otherwise flagged royal consort / relation):

```json
{
  "dh_id": "Mutemwia",
  "name": "Mutemwia",
  "alt_names": [],
  "roles": ["KGW", "KM"],
  "sex": "female",
  "spouse_names": ["Thutmose IV"],
  "father_name": null,
  "mother_name": null,
  "children_names": ["Amenhotep III"],
  "dynasty": 18,
  "sub_period": "The Power and the Glory",
  "unplaced": false,
  "notes": "Wife of Thutmose IV and mother of Amenhotep III; shown in the 'divine birth' scenes of her son in Luxor temple. A statue of her probably came from his mortuary temple, with a figure of her in a boat found adjacent to the granite sanctuary of the Karnak temple (British Museum); she is also represented with her son on the Colossi of Memnon and in the tomb of Heqareshu (TT226, now in the Luxor Museum).",
  "source_citation": {"pdf_pages": "126-130", "edition": "Thames & Hudson 2004 hardback"}
}
```

- **`dh_id`** = Dodson & Hilton's name-with-disambiguator-letter exactly as they write it. The book uses single-letter suffixes (`A`, `B`, `C`, `D`, ...) to distinguish homonymous royals across generations (e.g. `Ahmes B` vs `Ahmes A`, `Mutnefert A`, `Nefertiry C`). `Q` is another D&H disambiguating suffix (like `A`, `B`, `C`) that tends to appear on entries in D&H's *Unplaced* sub-section — but `unplaced` status is determined from the section heading/context, not the suffix. Some `Q`-suffixed entries (e.g. `Henttawy Q`) appear in the main alphabetical Brief Lives and are NOT unplaced. Names without a disambiguator (e.g. `Mutemwia`, `Huy`) are unique in the Brief Lives and get no letter. **`(dh_id, sub_period)` is the primary key** — duplicates on the composite key fail loud in `merge.py`. `dh_id` alone is NOT unique across the full reconciled file; two distinct phenomena can produce the same `dh_id` under two `sub_period`s (see below), both handled by the composite key.

  **Why `dh_id` alone isn't unique (two phenomena, both introduced in the Ramesside chunk):**

  1. **Cross-section duplicate of the same individual.** D&H writes a cross-reference stub under one sub-section and the full Brief Life under another sub-section. The two rows refer to the *same* person but carry different prose, different role codes, and different family-context fields (daughter-of vs wife-of, for instance). Known cases: `Takhat A` appears in *The House of Ramesses* (as *daughter of Ramesses II*, stub ending `(see next section)`) AND in *The Feud of the Ramessides* (as *wife of Sety II, mother of Amenmesse*, full prose). `Isetneferet C` similarly appears in *House* as the granddaughter-of-Ramesses-II stub and in *Feud* as the wife-of-Merenptah full entry. Both rows are emitted (rather than collapsed) so every fact D&H asserts traces to its source sub-section; Phase A reconciles them to one canonical individual downstream.

  2. **Letter-suffix reuse across sub-sections for *different* individuals.** D&H re-scopes the single-letter disambiguator per sub-section's family tree rather than using one global namespace across the book. Known case: `Ramesses C` in *The House of Ramesses* is a Dyn-19 prince (grandson of Ramesses II, son of Khaemwaset C; Memphis dedicator); `Ramesses C` in *The Decline of the Ramessides* is a different Dyn-20 prince (son of Ramesses III and Iset D Ta-Hemdjert, who became King Ramesses IV). NOT the same person — both rows are genuinely distinct individuals that happen to share the D&H letter.

  Per advisor guidance and constitutional rule 1 (work like a scholar / no invented unique keys), each Brief Lives entry is emitted as its own row with its sub-section's verbatim data; the composite `(dh_id, sub_period)` key is correct for both phenomena.
- **`name`** = same as `dh_id` for this source. Kept as a separate field for cross-source schema parity; future Phase A may normalise differently.
- **`alt_names`** = list of bracketed variant names Dodson & Hilton record inline (e.g. `Hatshepsut-Khnemetamun` for `Hatshepsut D`). Empty list when absent.
- **`roles`** = list of Dodson & Hilton's own role-code abbreviations from the parentheses after the name (e.g. `"(KM; KGW; KSis)"` → `["KM", "KGW", "KSis"]`). Extracted verbatim; Phase A expands the codes. Codes seen across all three chunks: `KM` (King's Mother), `KW` (King's Wife), `KGW` (King's Great Wife), `GW` (Great Royal Wife), `KSis` (King's Sister), `KD` (King's Daughter), `KDB` (King's Daughter of his Body), `KSon` (King's Son), `KSonB` (King's Son of his Body — explicit), `KSonK`, `KSonN`, `EKSon` (Eldest King's Son), `EKSonB`, `1KSon`, `1KSonB` (First King's Son of his Body — leading-digit form), `1Genmo`, `HPH` (High Priest of Heliopolis), `HPM` (High Priest of Memphis), `HPA` (High Priest of Amun), `Ador` (Adoratrix), `Nurse`, `Exec` (Executive), `ExecH2L` (Executive of the Two Lands), `SPP` (Sem Priest of Ptah), `Genmo` (General), `Gen`, `UWC`, `L2L` (Lady of the Two Lands), `M2L` (Mistress of the Two Lands), `MULE` (D&H's legend code), `MH`, `MoH` (Master of Horse), `GM` (God's Mother), `GWA` (God's Wife of Amun), `GBW` (Greatly Beloved Wife), `ChA`, `2PA`, `1PMut`, `GF`, `Viz` (Vizier), `King of Mitanni`, `King of Hittites`, `Fanbearer`, `Overseer of Treasurers`, `Troop Commander`, `Viceroy`, `Adjutant of the Chariotry`, `Songstress of Pre`, `Sister of KGW`, `Steward of Queen Tiye A/Tey`. Head-of-South chunk adds: `PH` (Priestess of Hathor — the Mentuhotep-II-era Deir el-Bahari mortuary-chapel wives carry it; Phase-A decoding), `GS` (on Tem, wife of Mentuhotep II), `Nomarch` (non-royal provincial governor — on Inyotef A only), and the hedged-role form `KW?` (on possible-wife entries Kawit and Kemsit where D&H writes `(PH; KW?)` — the `?` is preserved as part of the code string). The book's abbreviation key lives on pp. 24–37 (front matter); decoding is Phase A work.
- **`sex`** = `"male"` or `"female"`. Inferred from role codes (`K*Son` → male; `KW`, `GW`, `KD`, `KM`, `KSis` → female). For mixed-role entries that only carry male or only female codes, the inference is unambiguous. For ambiguous cases, follow D&H's own text (bold vs italic per their legend — males bold, females bold italic in the chart key on p. 145).
- **`spouse_names`** = list of spouses named in the prose (e.g. `"Wife of Thutmose IV"` → `["Thutmose IV"]`). Empty list when no spouse is named.
- **`father_name` / `mother_name`** = single names from "daughter of X", "son of Y", "mother Z" constructions in the prose. `null` when D&H don't state parentage. Preserve their hedges verbatim in the name string (e.g. `"Ay (probable)"`).
- **`children_names`** = list of named children mentioned in the prose of this entry (e.g. for Mutemwia: `["Amenhotep III"]`). Empty list when the entry's own prose names no children.

  **Extraction rule — cross-entry inference is allowed** for symmetric relationship fields (`children_names`, `spouse_names`, and the `father_name`/`mother_name` reverse) when D&H's prose in *another* Brief Lives entry establishes a kinship relationship that this entry is silent on. The egyptologist-reviewer pass on PR #38 first sanctioned the rule for `children_names`; chunk 3's review extended it to `spouse_names` (e.g. `Hattusilis III.spouse_names = ["Pudukhepa"]` where his own entry reads only "Father-in-law of Ramesses II." and Pudukhepa's entry names him explicitly). The generalized principle: a silent entry inherits a kinship claim that the *other* entry in the symmetric pair states verbatim.

  Concrete cross-entry inference cases in the Amarna chunk (exhaustive for that chunk):
  - `Shuttarna II.children_names = ["Gilukhipa"]` — Shuttarna II's own entry reads "Father-in-law of Amenhotep III." (p. 156), naming no children. Inferred from Gilukhipa's entry: "Wife of Amenhotep III and daughter of Shuttarna II of Mitanni."
  - `Tushratta.children_names = ["Tadukhipa"]` — Tushratta's own entry reads "Possible father-in-law of Akhenaten." (p. 157), naming no children. Inferred from Tadukhipa's entry: "daughter of Tushratta, king of Mitanni."

  Concrete cross-entry inference cases added in the Ramesside chunk (illustrative, not exhaustive):
  - `Hattusilis III.spouse_names = ["Pudukhepa"]` and `Hattusilis III.children_names = ["Maathorneferure"]` — his own entry reads only "Father-in-law of Ramesses II." (p. 170); Pudukhepa's and Maathorneferure's entries each name him.
  - `Khaemwaset C.children_names = ["Hori A", "Isetneferet C", "Ramesses C"]` — applied via `fix_rows.py` on review; the three children's own entries each explicitly name him as father (Hori A: "probably a grandson of Ramesses II and son of Khaemwaset C"; Isetneferet C: "daughter of Khaemwaset C"; Ramesses C House: "Grandson of Ramesses II. Dedicator at Memphis of a statue of his father, Khaemwaset C").
  - `Iset D Ta-Hemdjert.children_names = ["Amenhirkopshef C", "Ramesses C"]` — applied via `fix_rows.py` on review; own entry names only her granddaughter, but both sons' entries explicitly state "Son of Ramesses III and Iset D".

  All *other* parent/child relationships in the Amarna and Ramesside chunks are stated verbatim in the parent's own entry (e.g. Yuya's and Tjuiu's entries both directly name Tiye A as daughter; Nakhtmin A's and Mutemnub's entries both directly name Ay B as son) and are therefore NOT cross-entry inferences.

  **Hedge handling on inferred values.** The Shuttarna II / Tushratta / Hattusilis III cases all involve unhedged child/spouse references in the other entry. When the other entry's statement is hedged (e.g. Hori A's "probably... son of Khaemwaset C"), the inferred `children_names` entry is the bare name; hedges live on the parent-side `father_name`/`mother_name` fields on the child's own row, not on `children_names` lists. This matches the chunk-2 precedent and keeps the lists parseable.

  Rationale for adopting rather than excluding the rule: D&H's alphabetical-by-individual layout occasionally states the relationship on only one side of a pair, and dropping the cross-inference would produce asymmetric family trees where one entry knows a relationship and its symmetric counterpart does not. Downstream Phase A consumers can rebuild symmetric trees either way; populating both sides in the extract avoids requiring a post-processing "invert relationships" pass. Cross-entry inferences remain traceable because each inferred kinship is independently attested in the counterparty's verbatim `notes`.
- **`dynasty`** = integer. `18` for Pre-Amarna and Amarna chunks; `19` for House-of-Ramesses and Feud chunks; `20` for Decline-of-Ramessides (including its Unplaced sub-block, whose heading is `"in 19th and 20th Dynasties"` but whose primary dynasty is 20 unless individual row prose anchors it to 19); `11` for Head-of-South rows (the 11th Dynasty transition at the 1IP/MK boundary — D&H groups the entire dynasty under this sub-section).
- **`sub_period`** = D&H's own subsection title within the chapter, exactly one of: `"The Power and the Glory"` (Pre-Amarna, pp. 137–141), `"The Amarna Interlude"` (pp. 154–157), `"The House of Ramesses"` (pp. 170–175), `"The Feud of the Ramessides"` (pp. 182–183), `"The Decline of the Ramessides"` (pp. 192–194 including Unplaced sub-block), `"The Head of the South"` (pp. 88–89 including Unplaced sub-block).
- **`unplaced`** = `true` if the entry sits under D&H's own `Unplaced` sub-section (printed p. 141 for the Pre-Amarna chunk; printed p. 194 for the Decline chunk; printed p. 89 for the Head-of-South chunk — a single entry `Neferkayet`). All other rows: `false`. These are individuals D&H flag as attested but not confidently placed in the family tree — Phase A consumers may want to apply a lower confidence score. Not every Unplaced entry carries a `Q`-suffix disambiguator; the flag follows the section heading in the book, not the name suffix. Conversely, a `Q`-suffixed `dh_id` is not automatically `unplaced: true` — e.g. `Henttawy Q` in the Decline Brief Lives is in the main placed alphabetical run despite the `Q`.
- **`notes`** = the full prose paragraph verbatim from D&H's entry. No editorial summarisation — scholarly argumentation is Kitchen's / D&H's, and normalising would strip the evidence a reader uses to judge the entry.
- **`source_citation.pdf_pages`** = the **PDF-viewer page range** of the OCR chunk that produced this row — i.e., the page numbers a reader sees when opening the raw PDF in a viewer, counting from the first rendered page (`"126-130"` for Power-and-Glory rows, `"142-145"` for Amarna-Interlude rows). These differ from the book's **printed page numbers** (Power 137–141, Amarna 154–157) by the frontmatter offset (~11 pages). Each row cites the chunk range, not a single page; D&H's own printed page numbers appear in the OCR markdown so a reviewer can cross-reference to a specific printed page within the chunk trivially.

## Rights

Thames & Hudson, 2004, in copyright. This extract contains only **factual data** — names, kinship relations (spouse, parent, child), royal titles extracted verbatim from D&H's own abbreviation set, dynasty numbers, and one paragraph of their prose quoted verbatim as `notes` per entry. The book's extensive illustrations, genealogical chart diagrams, narrative chapter prose, and scholarly argumentation chapters are **not** reproduced. Per ADR-017, the source PDF is not committed; per-page OCR markdown in `raw/` is gitignored (`raw/*` pattern).

**Verbatim-quotation caveat:** the `notes` field reproduces D&H's Brief-Lives paragraphs (typically 30–80 words per entry) verbatim. Facts (names, kinships, monument references) are not copyrightable; D&H's specific phrasing of the narrative interpretation around those facts is. If this repo ever goes public, the `notes` field should either be summarised, dropped, or re-sourced — see the `.gitignore` comment on `proprietary/`.

## Method

Per ADR-017 (Claude Code subagent OCR → 3 parallel extraction subagents → deterministic merge → egyptologist-reviewer LLM pass → `fix_rows.py` for deterministic post-processing and spot corrections). See `transcribe.md` for the specifics.

### ADR-017 deviation

**OCR step on this chunk was performed by Google Gemini 3.1 Pro, not Claude Opus 4.6.** Claude Opus 4.6 refused the OCR pass on reasoned copyright-scope grounds (see `transcribe.md` § "Model deviation" for the refusal transcript and rationale). This deviation is permitted under ADR-017 § "Amendment 2026-04-15: external-model fallback for copyright-refusal" and comes with constraints:

- The Gemini prompt is committed verbatim at `transcribe-gemini-prompt.md` for reproducibility.
- The Gemini model version (`Gemini 3.1 Pro`, web UI, 2026-04-15) is pinned.
- Every downstream stage (3-subagent extraction, merge, reviewer pass, `fix_rows.py`) continues to run on Claude Opus 4.6 — only the OCR step uses Gemini.
- Follow-up Dodson-Hilton chunks (Amarna, Ramesside) must re-attempt Opus OCR first before escalating to Gemini; this is a per-chunk deviation, not a source-level blanket fallback.

A scholarly reviewer checking the provenance chain for any row in `reconciled.jsonl` should open `transcribe.md` and `transcribe-gemini-prompt.md` in addition to the ADR and the source PDF.

The 158 MB source PDF exceeds the 100 MB limit of the `Read` tool that OCR subagents use, so the book is first split into small per-chunk sub-PDFs under `raw/source-pNNN-pMMM.pdf` via `pypdf`. Subagents Read the small sub-PDFs. The split-PDF step is a mechanical `uv run --with pypdf` invocation; see `transcribe.md` for the exact command.

**Review.** The `egyptologist-reviewer` Claude Code subagent has walked the reconciled extract against the source PDF. Flagged corrections are applied via `fix_rows.py` and logged in `merge-disagreements.txt` under `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED`. **A human Egyptologist sign-off has NOT been performed** — the extract is provisional until that happens (ADR-017 step 6).

## Known gaps / Phase A notes

- **Abbreviation-code glossary not included.** D&H's role-code legend (front matter pp. 24–37) is not extracted as part of this PR. Phase A must expand `KM`, `KGW`, `KSis`, `SPP`, `Ador`, `Genmo`, `HPH`, `Exec`, `UWC`, etc., by reading the front-matter glossary and authoring `pipeline/pipeline/authority/codes/dodson-hilton-roles.json`. Until then, the `roles` field is a bag of D&H's own shorthand.
- **Disambiguator-letter stability is scoped to D&H.** `Ahmes B` is D&H's assignment — other sources (Baud 1999, Beckerath 1999) may use different letters or none. Cross-source deduplication happens in Phase A via name + parent + spouse triangulation, not by matching disambiguator letters.
- **`Unplaced` bucket.** D&H list some individuals whose family placement is uncertain in a dedicated `Unplaced` sub-block at the end of each Brief Lives section. Their entries carry `Q` suffix in `dh_id` (e.g. `Amenemhat Q`, `Henut Q`, `Thutmose Q`). These rows are real but Phase A flags them for reduced confidence.
- **`Addenda` (p. 304) is out of scope.** D&H's Addenda section corrects their own Brief Lives post-publication. Those corrections land in a follow-up revisions-only PR similar to how Kitchen 2009 supersedes Kitchen 1996.
- **Homonyms across chapters.** A `Thutmose` in the Brief Lives of Chapter 3 may collide semantically with one in Chapter 4 (different dynasty). Because `dh_id` scopes to D&H's book-wide disambiguator letters, the collision is prevented within the source itself — but cross-chapter `dh_id` uniqueness holds only if later PRs preserve the letters faithfully.
- **Mother vs Nurse.** D&H use the code `Nurse` for royal nannies who were not the biological mother. Don't collapse to `mother_name`. Ipu B's prose `"Mother of Sitiah"` really is biological parentage — the prose overrides role code; cross-check in Phase A.
- **Kings listed in the Brief Lives.** D&H include some kings (e.g. `AMENHOTEP II`, `AMENHOTEP III`, `THUTMOSE IV`) in the Brief Lives bold-capitalised because they are referenced as children / fathers of the main queens. These rows get `sex: "male"` and a role that contains `K` (or similar) — Phase A may dedupe against pharaoh.se rather than treat them as separate records.
