# Leprohon 2013 transcription — method

Per ADR-017 and `docs/playbook-phase-0-ocr-transcription.md`. Multi-chunk source; this file is authoritative across every chunk. Per-chunk OCR / extraction details are logged in the chunk table at the bottom.

## Source

- **Book:** Leprohon, Ronald J. (2013) *The Great Name: Ancient Egyptian Royal Titulary*, ed. Denise M. Doxey. SBL Writings from the Ancient World 33. Atlanta: SBL. ISBN 978-1-58983-735-5.
- **PDF path:** `proprietary/books/Leprohon 2013 - The Great Name.pdf` (gitignored).
- **PDF SHA-256:** `0a59c2763002c76fc7a17b4ff9f9e093f3dc1c887a537f75761de9fdf0ff3f5c`
- **Page count:** 280 pages (physical PDF).
- **Running-header format:** Odd pages: right-aligned SMALLCAP chapter title (`EARLY DYNASTIC PERIOD`), right-aligned printed page number. Even pages: left-aligned printed page number, centre-aligned SMALLCAP `THE GREAT NAME`. Footer carries the EBSCO Publishing watermark (`EBSCO Publishing : eBook Collection (EBSCOhost)`) — not transcribed, not extracted.
- **Physical-to-printed offset:** +21 for chunk 1 (verified printed p. 21 = physical p. 42 at the chapter-II headword, and printed p. 29 = physical p. 50 at the Khasekhemwy tail). Re-verify at each chunk's first and last pages per the multi-chunk-pattern gotcha; may drift at part boundaries (chapter-I/II boundary, chapter VIII/IX boundary are likely drift points).

## Pipeline

For each chunk:

### 1. Text-layer extraction — deterministic `transcribe_chunk.py`

**Method deviation from the playbook default** (supersedes ADR-017 step 1 for this source specifically): Leprohon's PDF is born-digital InDesign (File Type: InDesign in the copyright-page metadata, 280 pages, 2013 SBL WAW 33 publication), so the embedded text layer IS the publisher's typed Unicode, not a scan that needs OCR. Run `transcribe_chunk.py` to pull the text layer via `pypdf` and apply a Manuel de Codage → Egyptological-Unicode normalization on transliteration tokens (identified structurally: between a name-type label `Horus:` / `Two Ladies:` / etc. and the parenthetical anglicised gloss that follows). MdC map: `A→ꜣ, a→ꜥ, H→ḥ, x→ḫ, X→ẖ, S→š, T→ṯ, D→ḏ, q→ḳ`. The script is deterministic, reproducible, and reads directly from the publisher's text layer — an OCR vision model on top of that layer would be a strictly lossier detour (observed on chunk 1: OCR subagent misread `ḥꜣty` as `hꜣty`, losing the h-with-dot-below that the publisher's text layer carried correctly).

**Page-level post-processing (added in PR for #128 follow-up).** The pypdf text-layer flatten loses page-boundary, footnote-attribution, and watermark structural metadata. `transcribe_chunk.py`'s `_process_page` rebuilds it before the agent extraction step:

- **EBSCO watermark stripped.** Three trailing lines per page (`EBSCO Publishing : eBook Collection ...` / `AN: 663423 ; ...` / `Account: s8329666`) removed at the page-block level.
- **Running headers stripped.** Bare page-number lines, bare roman-chapter lines, and the running-header shapes `<NN> THE GR EAT NAME` (even pages) and ` SECO ND INTERMEDIATE PERIOD  <NN>` (odd pages) removed when they appear at the top of a page. The chapter-opening smallcap title (e.g. `s Econ D i nt Erm EDiat E PErio D`) is NOT stripped — it's content that signals chapter context to the extraction agents.
- **Footnote block detection + merging.** The trailing block of `\d+. <body>` lines on each page is identified by walking backwards from the last `\d+. ` start through the longest contiguous decrementing-by-1 run, gated by a prose safeguard (at least one merged candidate must contain a year, scholarly author, or `see`/`cf.`/`ibid` token; pure-headword pages have no such tokens and are correctly rejected). Each footnote's multi-line body (pypdf split it on InDesign line breaks like `Von Be\nckerath 1999, 116–17.`) is merged into a single string, emitted as `<fn id="N">body</fn>` after a `<!-- footnotes -->` separator at the bottom of the page block.
- **Footnote-anchor wrapping.** Inline footnote-superscript digits in body text are wrapped as `<sup data-fn="N">N</sup>` in four positional patterns: standalone-digit lines (`27`), end-of-line digits glued to the preceding text (`gods26`, `wAst).17`), continuation lines starting `<digit><space><word>` (`1 has been revised...`, `2 In the south...`), and mid-line anchors after sentence-end punctuation (`. 16 King`, `, 14 Ryholt`). Wrapping is gated on the digit value matching a footnote number on the same page, so dynasty numbers and 4-digit years pass through unchanged.
- **Split-number footnote pre-pass** (three observed shapes): `34\n. Turi\n` → `34. Turin`; `56.\n The na` → `56. The name`; `12\n2. Ibid\n., 106-7.` → `122. Ibid., 106-7.` (the 3-digit shape is restricted to merged values 100-250 to avoid false-positives where a body anchor `42` precedes a king-headword `1.`). En-dash + `\d+\.\s` continuations (`KRI IV, 31:1–\n13.`) are excluded from being misread as fn 13.
- **Footnote-number cap of 3 digits.** `_FOOTNOTE_START_RE = ^(\d{1,3})\.\s` excludes 4-digit years inside footnote bodies (e.g., `1985. The reading Renefer/Reneferef...` inside fn 55) from being mis-detected as footnote starts.

The deterministic-with-tests post-processing is what makes the 3-agent extraction protocol reliable for this source: agents read a structured page block where every footnote-number `N` in the body has a corresponding `<fn id="N">` body element, instead of inferring footnote attribution from typesetting cues that pypdf has flattened away.

Written to `raw/chunk-pNN-pMM-pypdf.md`. Not committed (Layer-2 rights policy).

**Chunk 1 only — parallel OCR cross-validation**: chunk 1 additionally runs an OCR Claude Code subagent to produce `raw/chunk-p42-p50-ocr.md` as an independent cross-reference. The purpose is to validate the pypdf+MdC output against a second pipeline, not to provide ongoing redundancy. Validation outcome: pypdf+MdC was strictly more accurate on transliteration content; OCR was cleaner on structural markdown (italics, page delimiters, footnote grouping). The deterministic cleanup rules in `transcribe_chunk.py` close most of the structural gap; the residual gap is absorbed by the 3-agent extraction majority vote downstream.

**Chunks 2+ — pypdf-only**: no OCR subagent step. `transcribe_chunk.py` is the sole transcription vehicle. Cost savings: one fewer subagent invocation per chunk (removes content-filter-refusal risk per the D&H chunk-1 precedent), fully reproducible from the SHA-pinned PDF.

### Escalation path (fallback tiers if `transcribe_chunk.py` fails)

Only escalate if the pypdf text layer for a specific chunk shows systemic quirks a regex-level normalizer cannot fix (e.g. a chapter typeset with a different font-mapping, an embedded scan for a figure the text layer can't reproduce, text-layer corruption). For Leprohon as currently scoped, no such chunks are expected — the book is a single-format SBL publication. Document any escalation in the § "Chunk log" row for that chunk.

- **Tier 2 — main-session Opus 4.6 OCR**: the main session reads the PDF pages and writes the markdown transcription itself. Used if the pypdf text layer is corrupt for a chunk.
- **Tier 3 — OCR subagent on Claude Opus 4.6** (playbook default, now demoted): only if tiers 1 and 2 fail. Apply the playbook's fair-use-scholarly-extraction refusal-framing paragraph. Preserves Egyptological diacritics + italic conventions in the output markdown.
- **Tier 4 — Gemini 3.1 Pro** (ADR-017 amendment 2026-04-15): only if tiers 1, 2, 3 all refuse. Commit the Gemini prompt at `transcribe-gemini-prompt.md`; pin the Gemini model version; keep every downstream stage (extraction, merge, review, fix_rows) on Opus 4.6.

### 2. Three parallel extraction subagents

Three general-purpose subagents, each reading `prompt.md` (chunk 1) / `prompt-<chunk>.md` (later chunks) and the chunk's OCR markdown. Each writes JSONL to `raw/agent-{a,b,c}.jsonl` (chunk 1) or `raw/agent-{a,b,c}-<chunk>.jsonl` (later chunks).

### 3. Deterministic merge

```bash
cd pipeline && uv run python pipeline/authority/sources/leprohon-2013-titulary/merge.py
```

Reads every `agent-{a,b,c}(-*).jsonl` file under `raw/`, unions the rows across chunks (cross-chunk ID collisions raise), majority-votes per field per row, and writes:

- `reconciled.jsonl` — the union-across-chunks majority-voted result, sorted by `(dynasty_number, sequence_in_chapter_section)`.
- `merge-disagreements.txt` — every non-unanimous row-field for audit.

### 4. LLM egyptologist review

Spawn `egyptologist-reviewer` Claude Code subagent with:

- Path to `reconciled.jsonl`.
- Path to `merge-disagreements.txt`.
- Path to the source PDF + the target physical-page range.
- Path to `README.md` (for schema context).

Asked to return a structured error report: `leprohon_id` / field / current / correct / evidence quote from the PDF.

### 5. Apply overrides via `fix_rows.py`

`SPOT_CORRECTIONS` list of `(leprohon_id, field, new_value, rationale)` tuples. Every correction appended to `merge-disagreements.txt` under `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED`. Idempotent on re-run.

Multi-chunk sources split `SPOT_CORRECTIONS` into per-chunk lists (`EARLY_DYNASTIC_CORRECTIONS`, `OLD_KINGDOM_CORRECTIONS`, ...) when the flat list passes ~10 entries.

### 6. Tests

`pipeline/tests/test_sources_leprohon_titulary.py` asserts exact values on every populated field of a flagship row + row-count invariants + ID uniqueness + ID regex + citation completeness + schema edge cases (Peribsen seth_names, Khasekhemwy horus_names-plus-seth_names, slash-display-name splitting, later_cartouche attestation, multi-variant Horus/Two-Ladies entries, etc.).

### 7. Human Egyptologist sign-off (ADR-017 step 6)

Deferred. When performed, log as `human-review-<YYYY-MM-DD>-<chunk>.md` per the playbook's multi-chunk naming convention.

## Chunk log

### Chunk 1 — Early Dynastic Period

- **Physical PDF pages:** 42–50 (9 pages).
- **Printed pages:** 21–29 (chapter II).
- **Physical-to-printed offset at chunk start / end:** +21 / +21. No drift.
- **Expected row count:** 27 kings. Dyn 0: 12 entries (Iry-Hor, Ka, Narmer, Scorpion, Crocodile, Hedju-Hor, Ny-<Hor>, Haty-Hor, Horwy, Ny-Neith, Horus "A", Horus "Pe"). Dyn 1: 7 entries (Aha, Djer, Djet/Wadjet, Den, Adjib, Semerkhet, Qa'a). Dyn 2: 8 entries (Hetepsekhemwy, Nebre, Ninetjer, Weneg, Sened, Sekhemib, Peribsen, Khasekhem/Khasekhemwy).
- **Known flagship rows for tests:** Den (Dyn 1, full titulary including throne + multi-form later cartouche), Khasekhem/Khasekhemwy (Dyn 2, slashed homonym + horus/seth dual classification + multi-form Horus and Two-Ladies), Peribsen (Dyn 2, Seth name replacing Horus).
- **OCR tier used:** TBD (fill after chunk 1 OCR step runs).
- **OCR output:** `raw/chunk-p42-p50.md` (gitignored).
- **Extraction output:** `raw/agent-{a,b,c}.jsonl` (gitignored).
- **Merge output:** `reconciled.jsonl`, `merge-disagreements.txt` (committed).
- **Reviewer log:** TBD.

### Chunk 2 — Chapter III Old Kingdom (+ recovered p. 30 from chunk 1)

- **Physical PDF pages:** 51–69 (19 pages).
- **Printed pages:** 30–48.
- **Physical-to-printed offset at chunk start / end:** +21 / +21. No drift.
- **Scope recovery:** chunk 1 misread the chapter-II boundary as ending at printed p. 29 and silently omitted 3 rows on printed p. 30 (`9. SENEFERKA` + Dyn-2a `1. NEFERKASOKAR` + `2. "HUDJEFA" (I)`). Chunk 2 picks them up as the first 3 emitted rows (`leprohon-2.09`, `leprohon-2a.01`, `leprohon-2a.02`), each tagged `chapter: "Early Dynastic Period"` to reflect their structural home.
- **Row count:** 60 rows. Per-dynasty: 2:1, 2a:2, 3:5, 3a:4, 4:7, 5:9, 6:7, 8:17, 8a:8.
- **Schema addition:** sub-dynasty suffix in `leprohon_id` (e.g. `leprohon-2a.01`, `leprohon-3a.03`, `leprohon-8a.08`) for Leprohon's distinctly-typeset Dyn-Na sub-sections. `dynasty_number` stays the integer parent (`2`, `3`, `8`); `dynasty_label` carries the full label (`"Dynasty 2a"`, `"Dynasty 3a"`, `"Dynasty 8a"`). `merge.py` `_sort_key` and the test-file regex both extended.
- **Dyn 8a is contemporarily attested, NOT Ramesside-only.** Chunk-2 prompt conflated Dyn 8a's framing with Dyn 2a's and incorrectly told the extractors to tag Dyn 8a as Ramesside-only. All three agents correctly ignored the wrong instruction per constitutional rule 1 (`work like a scholar` — prefer primary source over task framing). Leprohon's section header reads `Dynasty 8a – attested names` (p. 47) and the preface (p. 44) states these are `eight rulers who are attested contemporaneously`. Test `test_dyn_8a_is_contemporarily_attested_not_ramesside_only` locks this in.
- **OCR tier used:** tier 1 (pypdf+MdC only; no OCR subagent per the policy established in PR #83 for chunks 2+). Single-method input — the 3-agent extraction majority vote is the redundancy layer. No OCR-vs-pypdf disagreements logged this chunk.
- **Known flagship rows for tests:** Seneferka (2.09, recovered from chunk-1 omission), Khufu (4.02, Greek-alias `Cheops` in alt_display_names), Queen Neith-Iqeret (6.07, with `Nitocris` alt), Iytjenu (8a.08, last Dyn-8a contemporaneous entry).
- **Extraction output:** `raw/agent-{a,b,c}-old-kingdom.jsonl` (gitignored).
- **Merge output:** combined into `reconciled.jsonl` (87 rows total: 27 chunk-1 + 60 chunk-2), `merge-disagreements.txt` (committed).
- **Reviewer log:** no egyptologist-reviewer pass run for chunk 2 standalone — chunk-1 reviewer pass already covered the schema and found the relevant classes of extractor drift; chunk-2 data was spot-checked in-session for Ramesside-only tag correctness and Dyn-8a non-tagging. Full human Egyptologist sign-off remains deferred (ADR-017 step 6).

### Chunk 14 — Chapter X Macedonian and Ptolemaic Dynasties

- **Physical PDF pages:** 196–209 (14 pages).
- **Printed pages:** 175–188.
- **Physical-to-printed offset at chunk start / end:** +21 / +21. No drift.
- **Row count:** 24 rows. Per-dynasty: Macedonian (Dyn 32) 3 rows; Ptolemaic (Dyn 33) 21 rows = 17 numbered slots (Ptolemies I-XII at slots 1-11+13, Berenike at slot 12, Cleopatra VII at slot 14, Ptolemies XIII-XV at slots 15-17) + 4 queen-consort sub-entries at Leprohon's printed `2A. ARSINOE II / 3A. BERENIKE II / 5A. CLEOPATRA I / 8A. CLEOPATRA II` sub-headwords.
- **Schema additions:** `dynasty_number` extended to 32 (Macedonian) and 33 (Ptolemaic). pharaoh.se itself uses `dynasty_number: null` for both — the README's "consistent with pharaoh.se" rationale is a Leprohon-local extrapolation, not a literal alignment. The schema doesn't constrain the integer, so 32/33 was the natural extension of the per-chunk numbering pattern.
- **Stage_suffix semantic overload (RESOLVED 2026-04-24):** Leprohon's printed `Na.` sub-headword convention is reused in chapter X for queen-consorts (Arsinoe II, Berenike II, Cleopatra I, Cleopatra II) — distinct persons, not titulary stages of the preceding king. Chunk-14 emitted these as separate rows with `stage_suffix: "a"`, originally mirroring the literal headword pattern with only a `source_note` to flag the consort-queen semantics. Egyptologist-reviewer 2026-04-21 flagged this as P1 (one typed field encoding two unrelated concepts — rule-4 violation). The 2026-04-23 sweep audit resurfaced it; a 2026-04-24 schema PR introduced `printed_under: <leprohon_id> | null` as the typed discriminator. `stage_suffix` now encodes the suffix letter only (both stages and Chapter-X consorts have it); `printed_under` is null for the 9 stage rows and non-null for the 4 consort rows. The field was named `printed_under` rather than `consort_of` after 2026-04-24 egyptologist-reviewer verification found that 3 of the 4 Chapter-X placements are book-layout decisions without Leprohon prose attribution (only Cleopatra I → Ptolemy V has an explicit Leprohon scholarly claim via footnote 39) — naming it `printed_under` keeps the data honest about what Leprohon actually asserts. Tests: `test_printed_under_field_present_on_every_row`, `test_printed_under_points_at_valid_leprohon_id`, `test_printed_under_only_in_chapter_x`, `test_four_known_printed_under_pairs_resolve`, `test_same_king_stages_have_null_printed_under`.
- **Multi-stage titularies: zero in this chunk.** The chunk-14 prompt anticipated multi-stage rows for Alexander the Great and Ptolemy IV (based on "Original titulary" headings), but verified against the chunk file there are NO paired "Later titulary" / "Second titulary" headings — only "Original titulary" + "Additional names" patterns. All three agents converged on this independently. "Additional names" become variants within their parent name list per chunk-1 conventions.
- **Empty-titulary rows:** Ptolemy VII (slot 7), Ptolemy XI (slot 11), Ptolemy XIII (slot 15), Ptolemy XIV (slot 16) have all empty name lists per Leprohon's explicit "No royal titulary is attested in hieroglyphs" notes. Test `test_chunk14_ptolemaic_kings_with_no_attested_titulary_have_empty_name_lists` locks the invariant.
- **Slashed homonym `Alexander II/IV`:** Leprohon's chapter preamble (p. 175) names king 3 "Alexander II"; his SMALLCAP headword (p. 176) reads `3. ALEXANDER II/IV`. Per chunk-1 slashed-homonym convention, both forms populate `alt_display_names`. The `test_slashed_display_names_have_alt_forms` test was extended with Exception 3 to handle the shared-prefix-with-bare-roman-numeral pattern (`Alexander II/IV` → `["Alexander II", "Alexander IV"]`, not the literal slash-split `["Alexander II", "IV"]`).
- **Berenike (slot 12) needs disambiguation:** Leprohon prints only the bare headword `BERENIKE` (no roman numeral). She is Berenike III in standard Ptolemaic-history numbering (daughter of Ptolemy IX). fix_rows.py adds `["Berenike III"]` to her `alt_display_names` for Phase-A museum matching.
- **Title-case test extended for English particles:** `Alexander the Great` introduces a lowercase English particle `the` after the first space-delimited token. The `test_headword_display_names_are_title_cased` test was extended with Exception 8 to allow {`the`, `of`, `and`} after the first token.
- **OCR tier used:** tier 1 (pypdf+MdC only).
- **pypdf text-layer corruption (P0/P1 fix applied):** Cleopatra I's Horus name segment about Khnum: pypdf's text-layer extracted `Xqr(t).n Xnmw` which our MdC normalisation turned into `ẖḳr(t).n ẖnmw`. The egyptologist-reviewer 2026-04-21 flagged this against the PDF visual; the user supplied a screenshot of p. 181 confirming Leprohon's printed text reads `ḫkr(t).n ẖnmw` (the text layer mis-encoded `ḫ` → `X` and `k` → `q`; the second token Khnum is fine). fix_rows.py applies the correction. Note that this is a TWO-character substitution — uncommon, but worth flagging as the largest text-layer disagreement found in 14 chunks. A future deferred human-Egyptologist sign-off should re-walk every transliteration to catch any further single-character corruptions.
- **Anglicised/transliteration internal divergence:** Leprohon's printed anglicised gloss for the same Cleopatra I Khnum-token reads `kheqer(et).en khnemu` with `q`, even though his transliteration says `ḫkr` with `k`. This is an internal Leprohon typesetting inconsistency that we preserve verbatim — agents extracted the gloss as printed.
- **Pre-existing fix_rows gap closed:** PR #97 patched the three Dyn-23 Sheshonq aliases (`leprohon-23.03 / 23.07 / 23.09` → `Shoshenq VI / VIa / VII`) directly into `reconciled.jsonl` without adding entries to `fix_rows.py`. That made the aliases survive only as long as nobody re-merged. The chunk-14 re-merge correctly blew them away because the agent files don't carry them. fix_rows.py now carries the corrections so they're durable across all future re-merges.
- **Chunk file:** `raw/chunk-p196-p209-pypdf.md` (gitignored).
- **Extraction output:** `raw/agent-{a,b,c}-macedonian-ptolemaic.jsonl` (gitignored). All three agents converged on 24 rows.
- **Merge output:** combined into `reconciled.jsonl` (395 rows total: 371 from chunks 1-13 + 24 chunk-14), `merge-disagreements.txt` (committed). Disagreements are mostly minor `source_note` prose drift and queen-consort sub-entry routing details; no factual disagreements survived majority vote.
- **Reviewer log:** egyptologist-reviewer 2026-04-21 — verified queen-consort sub-headwords printed as `2A. / 3A. / 5A. / 8A.`; verified `3. ALEXANDER II/IV` headword; verified zero "Later titulary" headers; verified empty-titulary kings; spot-checked transliterations for Ptolemy I Soter / XII Auletes / Cleopatra VII Horus 1 / Alexander the Great Horus 1 — all match PDF. Flagged the Cleopatra I `ḫkr` vs `ẖḳr` text-layer corruption (applied via fix_rows). Full human Egyptologist sign-off remains deferred (ADR-017 step 6).
