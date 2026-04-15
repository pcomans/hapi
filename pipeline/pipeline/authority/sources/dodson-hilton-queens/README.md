# Dodson & Hilton 2004 — *The Complete Royal Families of Ancient Egypt*

Source of truth for non-king Egyptian royal-family members — queens, king's mothers, king's sons, king's daughters, and the extended family trees pharaoh.se doesn't cover.

## Citation

Dodson, A. & Hilton, D. (2004) *The Complete Royal Families of Ancient Egypt*. London: Thames & Hudson. ISBN 0-500-05128-3 / 978-0500051283.

- **Edition used:** first edition, 2004 hardback.
- **Retrieved:** 2026-04-15 (local scan).
- **PDF SHA-256:** `e636c49f3d0b5b6c6ec072cc6e7af9d605caf52d438c55cd84da9de7b07008a0`.

## Scope — first PR (18th-Dynasty pre-Amarna only)

Chapter 3 *The New Kingdom*, section **"The Power and the Glory"** *Brief Lives* entries — printed pp. 137–141, physical PDF pp. 126–130. This is the first-half-of-Dyn-18 cohort (Ahmose I through Amenhotep III + Thutmose IV's royal ladies), ~55 named royal-family members.

Out of scope for this PR, landing in follow-up PRs:
- **"The Amarna Interlude"** Brief Lives (printed 142–157) — Akhenaten/Nefertiti/Tutankhamun household. Separate PR.
- **"The House of Ramesses" + "The Feud of the Ramessides" + "The Decline of the Ramessides"** Brief Lives (printed 158–194) — Dyn 19/20 prosopography. Separate PR.
- **Chapters 1, 2, 4, 5** (Early Dynastic / OK / MK / SIP / TIP / Late Period) — separate PRs; `sources/baud-1999-ok-royal-family/` is the preferred OK source and this book is known-weaker there.
- **Front-matter reference sections** ("The Pharaonic State" pp. 10–23, "The Royal Family" pp. 24–37, "Genealogical Groupings" pp. 38–42) are narrative exposition, not ruler-list data.
- **Genealogical chart figures** (visual diagrams on pp. 144–145 etc.) are not extracted as rows — the Brief Lives text entries contain the same parent/spouse/child relationships in prose form.
- **Illustration captions** describing photographs / reliefs — not royal-family rows.

**Expected row count (this PR):** ~50–60 rows. The handoff doc estimates ~30 rows for "MVP priority" queens; we include the full Brief Lives list for Power and Glory rather than cherry-pick because cherry-picking would require editorial judgement about which second-tier princesses "matter".

**Eventual full-scope row count across all PRs:** ~150–250.

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

- **`dh_id`** = Dodson & Hilton's name-with-disambiguator-letter exactly as they write it. The book uses single-letter suffixes (`A`, `B`, `C`, `D`, ...) to distinguish homonymous royals across generations (e.g. `Ahmes B` vs `Ahmes A`, `Mutnefert A`, `Nefertiry C`). `Q` suffix marks entries Dodson & Hilton flag as "*Unplaced*" — attested but not confidently placed in the family tree. Names without a disambiguator (e.g. `Mutemwia`, `Huy`) are unique in the Brief Lives and get no letter. **`dh_id` is the primary key** — duplicates fail loud in `merge.py`.
- **`name`** = same as `dh_id` for this source. Kept as a separate field for cross-source schema parity; future Phase A may normalise differently.
- **`alt_names`** = list of bracketed variant names Dodson & Hilton record inline (e.g. `Hatshepsut-Khnemetamun` for `Hatshepsut D`). Empty list when absent.
- **`roles`** = list of Dodson & Hilton's own role-code abbreviations from the parentheses after the name (e.g. `"(KM; KGW; KSis)"` → `["KM", "KGW", "KSis"]`). Extracted verbatim; Phase A expands the codes. Known codes in this scope: `KM` (King's Mother), `KW` (King's Wife), `KGW` (King's Great Wife), `GW` (Great Royal Wife), `KSis` (King's Sister), `KD` (King's Daughter), `KSon` (King's Son), `EKSon` (Eldest King's Son), `HPH` (High Priest of...?), `Ador` (Adorator of ...?), `Nurse` (Nurse), `Exec` (Executive of ...?), `SPP` (Sem Priest of Ptah), `Genmo` (General of ...?), `UWC` (?), `KSis` (King's Sister). The book's abbreviation key lives on pp. 24–37 (front matter); decoding is Phase A work.
- **`sex`** = `"male"` or `"female"`. Inferred from role codes (`K*Son` → male; `KW`, `GW`, `KD`, `KM`, `KSis` → female). For mixed-role entries that only carry male or only female codes, the inference is unambiguous. For ambiguous cases, follow D&H's own text (bold vs italic per their legend — males bold, females bold italic in the chart key on p. 145).
- **`spouse_names`** = list of spouses named in the prose (e.g. `"Wife of Thutmose IV"` → `["Thutmose IV"]`). Empty list when no spouse is named.
- **`father_name` / `mother_name`** = single names from "daughter of X", "son of Y", "mother Z" constructions in the prose. `null` when D&H don't state parentage. Preserve their hedges verbatim in the name string (e.g. `"Ay (probable)"`).
- **`children_names`** = list of named children mentioned in the prose (e.g. for Mutemwia: `["Amenhotep III"]`). Empty list when absent.
- **`dynasty`** = integer. Scope of this PR is Dyn 18 throughout.
- **`sub_period`** = D&H's own subsection title within the chapter. Scope of this PR: `"The Power and the Glory"` for all rows.
- **`unplaced`** = `true` if the entry sits under D&H's own `Unplaced` sub-section (printed p. 141 for this chunk), `false` otherwise. These are individuals D&H flag as attested but not confidently placed in the family tree — Phase A consumers may want to apply a lower confidence score. Not every Unplaced entry carries a `Q`-suffix disambiguator; the flag follows the section heading in the book, not the name suffix.
- **`notes`** = the full prose paragraph verbatim from D&H's entry. No editorial summarisation — scholarly argumentation is Kitchen's / D&H's, and normalising would strip the evidence a reader uses to judge the entry.
- **`source_citation.pdf_pages`** = the OCR chunk's physical-page range. Each row cites the chunk range; D&H's own printed page numbers appear in the OCR markdown so a reviewer can cross-reference trivially.

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
