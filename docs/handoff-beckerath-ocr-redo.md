# Beckerath 1997 OCR redo — handoff

**TL;DR.** Issue #131 (Beckerath transcribe-stage post-processor) shipped in PR #138. The follow-up re-extraction work on branch `feat/beckerath-reextraction` (commit `8883501d`) cut manual `fix_rows.py` overrides from 25 to 9 — but spot-checking row 11.03 An-jotef III against the printed PDF revealed a **column-drift class of OCR error** that the post-processor + 3-agent merge cannot detect. The OCR step needs to be re-done with column-drift-resistant settings before the re-extraction PR can land. This handoff scopes that work.

## Context (what's already done)

- **PR #138 merged** (commit `a4bed05a`) — `postprocess.py` injects `<!-- period: ... -->` and `<!-- dynasty-context: ... -->` annotations into the chunk file to refresh dynasty + section context across page boundaries. Period is derived from a canonical Beckerath dynasty→period mapping (`DYNASTY_PERIOD` 0..31), robust against OCR section-heading omissions.
- **Branch `feat/beckerath-reextraction` (commit `8883501d`)** — re-extraction of `chunk-p105-p109.md` against the post-processed input by 3 fresh agents. New prompt rules added: Co-regent queen rule (Nofret-ete, Te-wosret get their own rows), OCR-duplicate detection (Dyn-27 Dareios II twice → emit once). 1161 pipeline tests pass on the branch.
- **`fix_rows.py` cleanup** — overrides pruned 25 → 9. The 16 redundant ones were verified at the agent level (≥2/3 agents now emit the correct value unaided).
- **Human Egyptologist verification** (project lead, 2026-04-28) confirmed three values against the printed PDF:
  - `19.05` Amen-mes-su Thronname = `Men-mi-rê sotep-en-rê` ✓
  - `19.06` Sethós II Thronname = `User-chepru-rê mer-amun` ✓
  - `11.03` An-jotef III Horus name = `Hor[-nacht] Neb-tep-nofer` (corrected from OCR-corrupt `Hor Men-cheper nach) Nub`)

## The blocker

The 11.03 An-jotef III spot-check exposed a **column-drift OCR error**: the chunk's value `Hor Men-cheper nach) Nub` is not a random OCR misread. The substituted fragments are Egyptian-name fragments from OTHER rows on the same physical PDF page:

- `Men-cheper` and `Men-cheperre` appear as Amenemnes IV's prenomen and as Tuthmosis III's prenomen on **book p189** (right half of physical PDF scan-106).
- `Nub` appears in `Nub-kau-rê`, Amenemnes II's prenomen, also on book p189.

So the OCR step's reading order slipped at An-jotef III's row (book p188, left half of scan-106) and pulled fragments from the opposite-page Dyn 12 column into An-jotef III's parenthetical, with stray punctuation as the splice seam. **The 3-agent merge cannot detect this** — all 3 agents read the same garbled markdown; they all dutifully output the same wrong value; the majority vote sees unanimity and is happy. The disagreement log is structurally blind to silent unanimity on a wrong value.

11.03 is unlikely to be the only column-drift case. The chunk has ~172 rows with Egyptian-glyph parentheticals; the OCR pass is the same model on all of them; any row near a dense double-page-spread fold is at risk. Without a fresh OCR pass with column-drift-resistant settings, shipping the re-extraction PR as-is would freeze in unknown drift cases as "verified data".

## What you (the next agent) should do

### 1. Re-OCR the chunk with column-drift-resistant settings

The current OCR setup (per `pipeline/pipeline/authority/sources/beckerath-1997-chronologie/transcribe.md`):

- One Claude Code general-purpose subagent (sonnet model)
- Reads pre-rendered JPEGs of the **double-page-spread** scans at `$TMPDIR/beckerath_scan/scan-105.jpg` … `scan-109.jpg` (regenerable via `pdftoppm -r 100 -f 105 -l 109 "<pdf-path>" <out-prefix> -jpeg`)
- Writes Markdown chunk file at `raw/chunk-p105-p109.md`

The double-page-spread layout is the root cause. The OCR subagent has to maintain reading order across two facing book pages, and at the page fold its reading order can slip — splicing fragments from one page's column into the other.

**Fix options (pick one or combine):**

1. **Split the JPEGs to single book pages** before OCR. Use `convert` (ImageMagick) or `pdftoppm` with crop options to cut each scan-NNN.jpg into scan-NNN-left.jpg + scan-NNN-right.jpg. Then OCR each half separately, with explicit "this is one book page only; do NOT pull text from beyond the right margin" prompt instruction. The chunk file's existing `## Book pNNN` boundary annotations match this naturally.

2. **Tighten the OCR subagent prompt** with explicit column-drift defenses: "Each book page is a single column. Egyptian-name parentheticals belong to the king on the SAME LINE; never pull fragments from below the dynasty boundary or from the opposite book page. If a parenthetical's content is ambiguous due to layout density, prefer to leave it incomplete (`(?)`) rather than substitute from a nearby row."

3. **Use a different OCR pipeline** (e.g. Gemini 3.1 Pro vision per ADR-017 amendment 2026-04-15 tier 4, or a layout-aware OCR like Tesseract with `--psm 4` single-column mode). Document the new tier choice in `transcribe.md`.

Recommended: combine (1) and (2). (1) eliminates the cross-page-fold drift mechanism entirely; (2) backstops against intra-page drift.

### 2. Re-run the 3-agent extraction on the new chunk

After OCR, the 3-agent extraction step is the same pattern as before (3 parallel general-purpose subagents reading `prompt.md` + the new chunk; output to `raw/agent-{a,b,c}.jsonl`). The current prompt.md (on this branch) already includes the Co-regent queen rule and OCR-duplicate detection — keep those.

Run merge.py, then fix_rows.py.

### 3. Verify against the row-overlap structural test

After re-merge, scan `egyptian_titulary` across all 172 rows for substring overlap with non-adjacent rows on the same physical PDF page. A row whose Egyptian-name parenthetical contains a fragment that appears verbatim in another row's parenthetical (and they're not historically related kings — e.g. not all the `Men-cheper-rê` occurrences which ARE expected) is a column-drift candidate.

Implementation hint:

```python
# pseudo-code
for row in rows:
    titulary = row["egyptian_titulary"] or ""
    for fragment in titulary.split():
        if len(fragment) < 4: continue
        for other in rows:
            if other["beckerath_id"] == row["beckerath_id"]: continue
            if abs(other["dynasty"] - row["dynasty"]) > 1: continue
            other_titulary = other["egyptian_titulary"] or ""
            if fragment in other_titulary:
                print(f"OVERLAP: {row['beckerath_id']} ↔ {other['beckerath_id']}: {fragment!r}")
```

False positives are fine (some fragments DO recur legitimately, e.g. `Re` / `User` / `mer-amun` are common across many king names). The test is a discovery aid, not a fail-on-overlap gate. Spot-check each flagged candidate against the printed PDF.

### 4. Spot-check every Dyn 11 row + adjacent dynasties

Even if the OCR re-do produces clean output, manually verify rows on book p188 (Dyn 11 cluster) and book p189 (Dyn 12 cluster) against the printed PDF. The fold between p188/p189 is the most-fragile zone in the entire chunk because it lands inside Dyn 11.

Specifically verify:
- 11.01–11.06 (An-jotef I/II/III, Men-hotpe II/III/IV)
- 12.01–12.07 (Amenemnes I-IV, Sesostris I-III, Sobeknofru)

The PDF is at `proprietary/books/Beckerath 1997 - Chronologie des pharaonischen Aegypten.pdf`. The project lead is the human Egyptologist for sign-off — ask concrete questions one at a time, like "What does Beckerath print as the parenthetical content for An-jotef II.?".

### 5. Update fix_rows.py + open the PR

After OCR + re-extraction + verification:
- Drop any `fix_rows.py` overrides whose values now match the freshly-extracted data unaided (those become redundant once the OCR is clean).
- Keep overrides for any remaining true-OCR-error cases.
- Update the audit log entries in `OVERRIDE_LOG` to reflect the new provenance.
- Open the PR; reference issue #131 and PR #138; document the OCR-redo methodology in `transcribe.md`.

## Out of scope

- **Don't migrate other sources** in this PR. The column-drift class likely affects Porter-Moss (#132) and Ryholt (#133) too, but each has its own physical PDF and its own OCR pipeline; per-source PRs.
- **Don't change `merge.py` semantics.** PR #128's tie-break enforcement holds. The fix is in the OCR layer, upstream.
- **Don't change `postprocess.py` semantics.** PR #138's structural-context refresh is correct and orthogonal to the column-drift problem.
- **Don't try to fix column drift in the agents.** They can't detect what they can't see; the OCR has to give them clean input. Detection invariants in tests are fine; agent-side detection isn't.

## Risk: what NOT to do

- **Don't ship the existing `feat/beckerath-reextraction` branch as-is.** It contains undetected column-drift values that haven't been spot-checked. The 9 fix_rows overrides target the cases I happened to find; they're not exhaustive. Marking the data "validated" without a clean OCR pass is a constitutional rule 6 violation ("data is sacred").
- **Don't delete the existing branch.** The post-processed chunk + new prompt rules + 3-agent re-extraction work are all valuable artifacts. The branch state shows what `fix_rows.py` looks like AFTER the post-processor's improvements but BEFORE OCR clean-up; that's a useful intermediate snapshot for the next agent comparing methodology rounds.
- **Don't blindly apply the existing 9 overrides on top of new OCR.** Re-evaluate each one against the freshly-extracted data. Some may now be obviated by clean OCR; some may need different correction values; some may need to be expanded if new column-drift cases surface.

## Acceptance criteria

- [ ] OCR step re-run with split-page or column-drift-defended prompt; document new tier in `transcribe.md`.
- [ ] 3-agent extraction re-run on the new chunk; merge.py runs green.
- [ ] Cross-row Egyptian-fragment overlap audit run; all flagged candidates spot-checked or explicitly accepted as legitimate cross-king fragments.
- [ ] Dyn 11 + Dyn 12 cluster verified against printed PDF for any residual column-drift.
- [ ] `fix_rows.py` updated; only OCR-error overrides remain (no leftover post-processor-redundant entries).
- [ ] PR description summarizes: count of overrides before/after, list of human-verified rows, list of OCR-redo methodology changes.
- [ ] All pipeline tests pass; egyptologist-reviewer + code-reviewer pass; Gemini review on the PR HEAD clean.

## References

- PR #130 — https://github.com/pcomans/hapi/pull/130 (Leprohon prototype this work mirrors)
- PR #138 — https://github.com/pcomans/hapi/pull/138 (Beckerath post-processor; the structural-loss fix layer)
- Branch `feat/beckerath-reextraction` (commit `8883501d`) — current WIP state
- Issue #131 — top-level Beckerath issue this work is closing
- Issue #137 — meta tracking issue for cross-source rollout
- ADR-017 — Phase-0 transcription protocol + OCR escalation tiers
- `docs/playbook-phase-0-ocr-transcription.md` — multi-chunk OCR pattern (pre-dating this work)
- The PDF — `proprietary/books/Beckerath 1997 - Chronologie des pharaonischen Aegypten.pdf` (gitignored; SHA-256 pinned in `transcribe.md`)
