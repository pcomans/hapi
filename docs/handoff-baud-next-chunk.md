# Handoff — Baud 1999 Old Kingdom royal family (next chunk)

**Written 2026-04-17.** Pick this up when the user asks to start or continue the Baud 1999 Old-Kingdom prosopography transcription.

Baud is the OK analogue of Dodson-Hilton. Per `docs/mvp-tasks.md`: "without it, OK queen/consort coverage will be thin while NK/LP is dense, producing an uneven authority. Required, not optional." D&H covers the earlier chapters too, but D&H's OK coverage is explicitly flagged as weaker; Baud is the preferred OK source.

For generic Phase-0 source onboarding, read `docs/playbook-phase-0-ocr-transcription.md` first. This handoff supersedes the playbook where they disagree. The multi-chunk source pattern in the playbook (§ "Multi-chunk source pattern") is the model to follow — Dodson-Hilton is the reference implementation and has its own handoff at `docs/handoff-dodson-hilton-next-chunk.md`.

---

## Source

**Citation.** Michel Baud, *Famille royale et pouvoir sous l'Ancien Empire égyptien*, Bibliothèque d'Étude 126, Institut Français d'Archéologie Orientale, Cairo, 1999. Two volumes. Vol. 1 is the analytical study (narrative, out of scope). Vol. 2 is the *Corpus* — 282 numbered prosopographical entries `[1]`–`[282]` spanning Dyns 3–6, alphabetical by Egyptian transliteration (not by dynasty).

**PDF location (once acquired).** `proprietary/books/Baud 1999 - Famille royale et pouvoir sous l'Ancien Empire égyptien vol 2.pdf`. Gitignored. SHA-256 pinned in `README.md` and `transcribe.md` once the file is on disk.

**Rights posture.** Follows the playbook's derived-extract default: PDF never committed, only `reconciled.jsonl` (facts) and, if useful, a tabular transcription at source-dir root lands in git. Facts are the prosopographical headwords, attested dates, attested filiation, attested titles. Baud's narrative commentary on attributions and skepticism stays in the book — but note his attributions are *scholarly judgments*, not bare facts (see § "Interpretive-facts caveat" below).

---

## Scope: the *Corpus* only

- **In scope:** vol. 2 *Corpus* entries `[1]`–`[282]`, printed pp. 395–627 (approximate — verify in the PDF). Each entry is a compact prosopographical record with headword (Egyptian + translation), titulary, filiation, attested dates/reigns, titles, and bibliographic references.
- **Out of scope:** vol. 1 (narrative analytical chapters), vol. 2 appendices A/B/C. Per the playbook's rights policy, narrative commentary is not extracted. Baud's own author-flagged rejection of appendix A is noted in his introduction — confirm during scoping, don't extract it regardless.

---

## Chunk plan (~7 PRs)

282 entries alphabetical by transliteration → chunk into ~40-entry blocks by entry number. That gives seven roughly-equal-sized PRs:

| Chunk | Entries | Tentative row count |
|---|---|---|
| 1 | `[1]`–`[40]` | ~40 |
| 2 | `[41]`–`[80]` | ~40 |
| 3 | `[81]`–`[120]` | ~40 |
| 4 | `[121]`–`[160]` | ~40 |
| 5 | `[161]`–`[200]` | ~40 |
| 6 | `[201]`–`[240]` | ~40 |
| 7 | `[241]`–`[282]` | ~42 |

Refine the entry-to-page mapping during chunk 1 scoping (the entries-per-page distribution isn't uniform, so some chunks may span more or fewer physical pages). Ship one chunk per PR. Do NOT bundle chunks — the D&H PR sizing (59–170 rows per chunk) is the comfortable review surface.

---

## Scaffolding state

**No Baud scaffolding exists on `main`.** A previous session had a `sources/baud-1999-ok-royal-family/` directory staged but not committed; those stashes were dropped in the 2026-04-17 session. Nothing to rebase off. Start fresh from the playbook's Step 1.

`proprietary/books/Baud 1999 ...pdf` may or may not be present on the user's machine. Confirm `ls proprietary/books/` and ask if it's missing — without the PDF no transcription is possible.

---

## Schema

Baud's per-entry data maps to a JSONL row with at least:

- `baud_id` — string `"baud-1"`, `"baud-2"`, etc. (Baud's own entry number from the *Corpus*).
- `name_egyptian` — transliteration headword as printed (preserve diacritics: ꜣ ꜥ ḥ ḫ ẖ š ṯ ḏ).
- `name_anglicised` — conventional English form where Baud gives one; null otherwise. Phase A will reconcile against pharaoh.se's Conventional English Display Form.
- `dynasty` — string like `"4"`, `"5"`, `"6"`, `"3-4"` for cross-dynasty attestations, or `"unknown"`.
- `sub_period` — OK sub-period if Baud attests it (e.g. "early Dyn 4"), else null.
- `roles` — structured list. OK-appropriate role vocabulary includes `king`, `queen`, `king's mother`, `king's wife`, `king's son`, `king's daughter`, `vizier`, `king's eldest son of his body`. Use Baud's exact title list in `titles_from_baud` as the raw source.
- `titles_from_baud` — verbatim title list from Baud's entry (raw cells of the prosopography, not interpretive).
- `father_name` / `mother_name` / `spouse_names` / `children_names` — relationship strings. **Attribute scholarly judgments** — Baud sometimes states a filiation Baud himself is not certain of. When the hedge is in Baud's prose, use the playbook's hedge convention: parenthesised for probable, square-bracketed for reconstructed, sentinel-null for "unattested per Baud."
- `tomb` — tomb designation (`G xxxx`, `D xx`, etc.) if attested. Cross-references to Porter-Moss III will be resolved in Phase A.
- `source_citation` — `"Baud 1999 BdE 126 Corpus [N]"` format.
- `source_pdf_pages` — physical-page range citation per ADR-017.
- `notes_from_baud` — short prose hedges / cross-entry references that change the factual reading but don't fit the structured fields. Same sentence-budget rule as Dodson-Hilton.

Define the full schema in `prompt-chunk-1.md` before extraction; refine across chunks as Baud's coverage surfaces edge cases.

---

## Interpretive-facts caveat (per the playbook)

Per `docs/playbook-phase-0-ocr-transcription.md` § "Interpretive facts are still facts, but cite them as such": Baud's attributions are not bare givens. When extracted facts depend on Baud's judgment (e.g., "probable mother of X", tomb assignments that Baud reconstructs from fragmentary evidence), the extracted field must either carry the hedge or cite `source_note: "per Baud 1999 §N"` so Phase A can distinguish attested-in-the-source from asserted-by-Baud.

The three-agent extraction prompt should explicitly include a "preserve Baud's hedges" rule in its pitfalls block — same pattern as Dodson-Hilton's hedge-preservation rule in `raw/prompt-ramesside.md`.

---

## Step-by-step plan (chunk 1)

Follow the playbook's Step 1–11 for Phase-0 sources. Baud-specific deviations:

1. **Scope the sub-PDF for chunk 1 (entries `[1]`–`[40]`).** Find the page range in vol. 2 that covers those entries. Re-verify at both ends of the chunk per the playbook's page-offset warning.
2. **OCR via a Claude Code subagent** on Claude Opus 4.7 (the current-good OCR model on this project — Dodson-Hilton's `transcribe.md` records its use on 2026-04-16 chunks). If Opus refuses on French scholarly prose, reframe the prompt (fair-use extraction for a private research repo). If that also fails, escalate to Gemini per ADR-017 amendment — but Baud's French prose should not hit the same content-filter that Dodson-Hilton's Brief Lives did, since it's scholarly prosopography not royal-children narrative.
3. **Three parallel extraction subagents** with the Baud-specific `prompt-chunk-1.md`. Each writes `raw/agent-{a,b,c}-chunk-1.jsonl`. Expected row count: ~40 (range 35–45 is a sanity-check bound).
4. **Deterministic merge** via `merge.py` adapted from Ryholt or Kitchen. Primary key: `baud_id`. **Use a single key, not composite — Baud's entry-number scheme doesn't reuse labels across sub-sections (he has a flat numeric list, unlike D&H's sub-section-scoped letter suffixes).**
5. **LLM reviewer pass** via `egyptologist-reviewer` subagent, targeting Baud-specific risks:
   - Did the extraction drop Baud's hedges? (Baud is especially hedge-heavy — OK prosopography is sparsely attested.)
   - Did the extraction promote a scholarly judgment to a hard claim?
   - Are tomb designations correctly preserved (G xxxx for Giza, D xx for Saqqara mastabas, etc.)?
   - Do the relationships respect D&H's earlier-chapter conventions where they overlap? (Baud and D&H-chapter-1 will overlap on named OK queens; the reviewer should flag discrepancies but not auto-reconcile.)
6. **`fix_rows.py`** for spot corrections + deterministic recomputation where needed. No BCE-date arithmetic for Baud (unlike Kitchen) — OK dates are relative dynasty/reign positions, not absolute years.
7. **Tests** at `pipeline/tests/test_sources_baud_ok_royal_family.py` per rule 5: row count exact match for chunk, ID uniqueness, ID shape, citation completeness, one fully-populated flagship row (pick a well-attested OK queen — Hetepheres I is the canonical choice), edge-case regression tests for Baud's hedges, polity/dynasty constraint matrix.
8. **Step 11.5 risk-driven checks** per the playbook: after chunk 1 establishes the extract shape, encode the reviewer-flagged failure-mode categories as deterministic checks in `diff_chunk1.py` so chunks 2–7 inherit them.

---

## Known traps (learned on other sources — will likely apply to Baud too)

1. **Do NOT re-run the 3-agent extraction after a prompt fix.** Re-running loses quality on fields the prompt never targeted. Use `fix_rows.py` surgical overrides instead. See D&H PR #38 for the concrete regression.
2. **Scan-order anomalies shift the physical-to-printed offset mid-chunk.** Verify at both ends of every chunk; document the drift path in `transcribe.md`. IFAO PDFs are more likely to have fold-outs than Thames-and-Hudson because of the larger scholarly-apparatus footprint.
3. **Agent JSONL files stay under `raw/` and are gitignored.** The `tests/test_structure.py::test_no_tracked_files_under_raw_for_phase0_sources` test (landed in PR #47) will fail CI if any non-`.gitkeep` file under `raw/` is committed. Stage by filename, never `git add -A`.
4. **Pre-push hook requires `TASK_LIST_UPDATED=1`** when `docs/mvp-tasks.md` is in the commit. Prefix with it or the hook blocks.
5. **Baud's transliteration convention.** Both the French and Anglo-American schools use the same diacritic character set (ꜣ ꜥ ḥ ḫ ẖ š ṯ ḏ) — there is no character-set difference to normalise. The real distinctions are conventions like the dot-for-suffix (Baud writes `mw.t-nsw`, some Anglo-American treatments elide the dot), `j` vs `i` for the iod glyph, and morpheme-boundary marking. The extraction prompt must instruct agents to preserve Baud's printed form verbatim — dots, hyphens, glyph choices are load-bearing for later reconciliation against pharaoh.se and Beckerath. Normalisation to a single house style happens in Phase A, not extraction.

---

## After chunk 1 merges

1. Log the human Egyptologist sign-off sample in `human-review-<YYYY-MM-DD>-chunk1.md` per ADR-017 step 6. Baud's hedges make this chunk's human-review value high — sample at least 5 rows including 2 with Baud-hedged filiation.
2. Update this handoff doc with chunk 1's actual page range, any schema refinements, and any Baud-specific pitfalls surfaced. Future chunks inherit those refinements.
3. Start chunk 2 (`[41]`–`[80]`) in a fresh PR.

---

## Memory pointers

- User feedback rules relevant to this work: `feedback_autonomy.md`, `feedback_branch_pr.md`, `feedback_push_after_commit.md`, `feedback_pr_review_replies.md`, `feedback_ci_failures.md`, `feedback_gemini_review.md`, `feedback_pr_reviewers.md`. Read before starting.
- Constitutional rules 1, 5, 6, 12 are the ones this work stresses hardest — scholarly traceability, value-assertion tests, raw data preservation, no-excusing-existing-violations.
- The `/watch-pr-reviews` skill (`.claude/skills/watch-pr-reviews/`) is the standard PR-review watch pattern; use it on every push.
