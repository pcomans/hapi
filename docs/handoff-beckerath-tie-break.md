# Beckerath 1997 — merge-stage tie-break propagation — handoff

**TL;DR.** PR #128 (`feat(leprohon): enforce tie-break; kill silent first-seen at 1/1/1`) fixed a constitutional-rule-2 violation in `leprohon-2013-titulary/merge.py` where `Counter.most_common(1)[0]` silently picked the first-seen value on a 1/1/1 three-way tie. The same bug exists in 6 of 7 source merge.py files; **Beckerath is the highest-priority next target** (issue #144) because it's the foundational chronology table that downstream sources (Leprohon, Kitchen, Baud) join against, so any silent tie-break here propagates across the authority layer. The Beckerath transcribe-stage postprocessor already shipped (issue #131 closed via PR #138/#139); this handoff covers the merge-stage cleanup.

## What's already done

- **PR #128** (commit on `1de7adaf` lineage, merged) — the canonical tie-break fix on Leprohon's `merge.py`: introduces `_classify_tie`, `_resolve_prose_tie`, and an external `tie-break-overrides.json` keyed by `id|field`. Identifier-bearing 1/1/1 ties RAISE without a covering override; prose ties (notes/citations) resolve via documented deterministic policy. **Read this PR + `docs/handoff-leprohon-tie-break.md` first** — your task is to apply the same pattern to Beckerath.
- **PR #138/#139** (Beckerath OCR redo + postprocessor) — closed issue #131. Beckerath's chunk text and reconciled.jsonl are clean as of those merges; you are NOT regenerating from raw OCR, only re-running the merge step against existing `agent-*.jsonl` files in `raw/`.
- **PR #140/#141** (Porter-Moss postprocessor + printed-source corrections) — adds the `feedback_egyptologist_diff_requires_printed_source.md` memory rule (see "Reviewer pass" below). Beckerath's PDF is already on disk at `proprietary/books/Beckerath 1997 - Chronologie des pharaonischen Aegypten.pdf` (verified earlier), so the gating egyptologist diff against printed source CAN run cleanly.

## The blocker (next agent's problem)

`pipeline/pipeline/authority/sources/beckerath-1997-chronologie/merge.py` line 115 carries the same buggy pattern:

```python
counts = Counter(key(v) for v in normalised)
top_key, top_count = counts.most_common(1)[0]   # ← silent first-seen on tie
```

On a 1/1/1 three-way tie, `most_common(1)[0]` returns whichever value `Counter` happened to hash first. The order depends on `dict` insertion order, which depends on agent order, which depends on file iteration order (`os.listdir`), which is not stable across machines or Python invocations. The reconciled value for that field has no provenance to genuine multi-agent agreement, real majority, or explicit override — per constitutional rule 6, that is **slop**, not authority data.

The 1/1/1 case is the textbook failure. The 1/1 case (one agent dropped a field, the other two split) is the same shape — `most_common(1)[0]` picks one silently.

## What you (the next agent) should do

### 1. Read the canonical fix first

- `pipeline/pipeline/authority/sources/leprohon-2013-titulary/merge.py` — the implementation pattern.
- `pipeline/pipeline/authority/sources/leprohon-2013-titulary/tie-break-overrides.json` — the override-table format.
- `docs/handoff-leprohon-tie-break.md` — the design doc for that work; documents WHY the pattern is shaped the way it is (e.g., `id|field` keying, the IDENTIFIER-vs-PROSE classification).
- PR #128 — the commit that introduced the pattern. Cross-reference its CI artifacts to see what test surface was added.

The Leprohon design separates two tie classes:

- **IDENTIFIER ties** (anything that disambiguates a row — name, dynasty, sequence, etc.). RAISE on tie unless an explicit `tie-break-overrides.json` entry exists. The override entry carries the chosen value AND a documented rationale (citation to the printed source or to a reviewer's note).
- **PROSE ties** (free-text fields like `notes_*` and bibliographic citations). Resolve deterministically via `_resolve_prose_tie` — e.g., longest-string-wins or sorted-first if equal length. Document the rule in code so it's not "first-seen" by accident.

### 2. Adapt the pattern to Beckerath's field set

Beckerath's row schema differs from Leprohon's. Read `pipeline/types/canonical.py` for the fields Beckerath emits. The likely classification:

- **IDENTIFIER fields** (raise on uncovered tie): `birth_name`, `prenomen`, `horus_name`, `nebty_name`, `golden_name`, `dynasty`, `sub_line`, `sequence_in_dynasty`, `start_year_bce`, `end_year_bce`, `period`.
- **PROSE fields** (deterministic policy): `notes_from_beckerath`, `attested_in`, any free-text bibliographic citation lists.

Confirm against the actual canonical model before locking the classification.

### 3. Pre-merge MdC normalisation

Before the tie-break enforcer raises, **add or reuse pre-merge normalisation** that collapses spurious ties (e.g., the same Manuel-de-Codage glyph encoded two ways by two different agents). The Leprohon design uses a `_normalise_value` step that runs BEFORE the per-field counter; spurious ties never reach `_classify_tie` because the normalised values match. Without this step, the override table inflates with entries like "agent A wrote `mn-ḫpr-rꜥ`, agent B wrote `mn-xpr-r<` — same glyph, different encoding".

Beckerath specifically: agents can disagree on `etwa`/`ca.`/`approximately` qualifiers in dynasty headings (the postprocessor PR #138 already restored these but the agent prompts may still vary). Normalise these to a canonical form (`approximate=True/False` boolean field, or a fixed `"etwa "` prefix) BEFORE the tie-break enforcer sees them.

### 4. Re-run merge against existing agent JSONL

Beckerath has 6 chunks of agent extraction already on disk (gitignored, regenerable from the PDF if needed). Re-run merge.py against the existing JSONL — do NOT re-run agents unless you also need to re-postprocess raw chunks. The new merge.py's tie-break enforcer will RAISE on every uncovered identifier tie. Each raise is a row × field that the prior `most_common(1)[0]` was silently first-seen-picking.

For each raise, choose ONE:

- **Add a `tie-break-overrides.json` entry** with the chosen value and a citation. Cite the printed PM page when the printed source is the truth-source (Beckerath's case: cite his printed Anhang A page).
- **If the tie is a real ambiguity in PM**, record both values in `attested_in` or a hedged form per Beckerath's own typography conventions; the reviewer pass on PR #115 (closed) is a precedent for this.
- **If the tie is a genuine disagreement at the agent level (e.g., one agent over-extracted)**, fix the prompt so all three agents emit the same value. This is the cleanest fix because it eliminates the tie at the source.

### 5. Gating reviewer pass — egyptologist diff against printed PM

Per `feedback_egyptologist_diff_requires_printed_source.md` (memory note, saved 2026-04-29 after PR #140's near-miss):

- **Verify the PDF is on disk** at `proprietary/books/Beckerath 1997 - Chronologie des pharaonischen Aegypten.pdf` BEFORE running the egyptologist diff. (Currently it IS — `ls -la "proprietary/books/"` should confirm.)
- If the PDF is absent, **STOP and `AskUserQuestion`** — do NOT degrade to OLD-vs-NEW-only review. The OLD-vs-NEW pass is structurally insufficient per ADR-017 (it cannot detect unanimous-but-wrong values; only a printed-source cross-check can).

Spawn the `egyptologist-reviewer` subagent with the printed PM Beckerath PDF as the truth-source. Cross-check 15-20 reconciled rows against the printed Anhang A. The Beckerath PR #139 lesson: a Mer-en-rê → Mer-en-ptah autocomplete regression slipped through the 3-agent merge but was caught by the egyptologist diff against print.

### 6. Audit `fix_rows.py` post-merge

After the tie-break enforcer + new overrides are in place, audit Beckerath's existing `fix_rows.py` entries:

- Drop entries that the new merge resolution path now produces correctly without override (constitutional rule 6 audit).
- Keep entries that override a 2/3 majority for an explicit egyptologist-flagged correction (these are not tie-break-related).

### 7. Open the PR

Per project conventions:

- Branch + PR (never push to main).
- Trigger Gemini review on PR open; address feedback per `feedback_pr_reviewers.md`.
- `scope-accountability-enforcer` audit before each Gemini-reply batch.
- `/watch-pr-reviews` monitor armed; do NOT treat timeout as acceptance.
- Before merging: ensure CI green AND egyptologist-reviewer printed-source pass complete (NOT degraded). Self-merge if both green per `feedback_self_merge_clean_prs.md`.

## Acceptance criteria

- [ ] `Counter.most_common(1)[0]` removed from `beckerath-1997-chronologie/merge.py`.
- [ ] Tie-break enforcer raises loudly on uncovered identifier tie with row + field + per-agent values.
- [ ] All raises addressed via `tie-break-overrides.json` entries (each carrying a citation) OR via prompt clarifications that eliminate the tie at the source.
- [ ] Pre-merge normalisation collapses spurious ties (e.g., MdC encoding variance, `etwa`/`ca.` qualifier variance).
- [ ] Reconciled.jsonl regenerated; egyptologist-reviewer diff against the printed Beckerath PDF on a 15-20 row sample, with the printed source on disk (NOT a degraded OLD-vs-NEW pass).
- [ ] `fix_rows.py` post-merge audit: drop redundant entries, document why each surviving entry is still load-bearing.
- [ ] All pipeline tests pass; tests assert specific values per CLAUDE.md rule 5.
- [ ] PR carries Gemini review on its current HEAD; CI green; per-source comment in #144 closes the issue.

## Out of scope for this PR

- The other 5 sources (Porter-Moss #145, Ryholt #133, Baud #134, Dodson-Hilton #135, Kitchen #136). Each has its own per-source issue with the same checklist; they land independently after this Beckerath PR ships.
- Issue #142 (`merge-disagreements.txt` field-ordering determinism). Different concern (audit-log churn, not data correctness). Could be bundled if the merge.py changes naturally touch the relevant code path; otherwise defer.
- The Beckerath transcribe-stage postprocessor (already shipped via PR #138/#139, issue #131 closed).

## Risk: what NOT to do

- **Do NOT degrade the egyptologist diff to OLD-vs-NEW-only** if you cannot find the PDF. Stop and `AskUserQuestion`. This is the lesson from PR #140 — see `feedback_egyptologist_diff_requires_printed_source.md`.
- **Do NOT remove `Counter.most_common(1)[0]` without replacing it with a unanimity / real-majority / raise-on-tie path.** A bare deletion that just defaults to the first agent is the same bug under a different name.
- **Do NOT silently coerce ties via `sorted()` or alphabetical-first or "agent A wins"**. Constitutional rule 2 enumerates all of these as slop. Either RAISE, or have a documented deterministic rule cited in code, or have a `tie-break-overrides.json` entry.
- **Do NOT bundle other sources' tie-break work into this PR.** Each per-source PR lands independently; they share a pattern but not a diff.
- **Do NOT skip the `fix_rows.py` audit.** The new merge resolution may obviate some existing overrides; the audit is required to keep `fix_rows.py` minimal and traceable per rule 6.

## References

- **PR #128** — `feat(leprohon): enforce tie-break; kill silent first-seen at 1/1/1`. The canonical fix to mirror.
- **`docs/handoff-leprohon-tie-break.md`** — design doc for PR #128. Read this before implementing.
- **CLAUDE.md constitutional rule 2** — the bar this work must meet. Verbatim: "`Counter.most_common(1)[0]` on a tie, 'first agent wins', or anything that depends on agent order / file iteration order / hash randomisation is a silent failure that produces non-reproducible output."
- **CLAUDE.md constitutional rule 6** — reconciled data is sacred; values must trace to multi-agent agreement, real majority, or explicit cited override.
- **Issue #144** — this work's tracker.
- **Issue #143 (closed-not-planned)** — meta-tracker for the cross-source rollout, consolidated into per-source issues #133/#134/#135/#136/#144/#145.
- **`feedback_egyptologist_diff_requires_printed_source.md`** — gating reviewer policy (saved after PR #140's near-miss).
- **PR #115 (closed)** — Beckerath egyptologist post-merge sweep findings (2 P1 + 3 P2). Provides per-row examples of where Beckerath's reconciled.jsonl had subtle issues that the egyptologist caught — useful priors for what to look for during the printed-source diff this round.
- **`pipeline/pipeline/authority/sources/beckerath-1997-chronologie/merge.py`** — the file to edit.
- **`pipeline/pipeline/authority/sources/beckerath-1997-chronologie/raw/agent-*.jsonl`** (gitignored) — existing agent extractions to re-merge.

## After this: the remaining 5 sources

Once Beckerath's tie-break PR ships, the cross-source rollout queue is:

1. **Porter-Moss I.2** (#145) — recently regenerated; PDF on disk; agents can re-merge against existing JSONL.
2. **Kitchen-TIPE** (#136) — bundle with that issue's existing concurrent_with_kings + hedge-fold work.
3. **Ryholt SIP** (#133) — has *partial* tie-break code; the new fix needs to fully replace `Counter.most_common(1)[0]`, not coexist.
4. **Baud OK Royal Family** (#134).
5. **Dodson-Hilton Queens** (#135) — bundle the additional D&H bugs from #54.

Each per-source issue carries its own checklist; they share the Leprohon pattern but not a diff. The handoff for the next source after this one belongs in its own `docs/handoff-<source>-tie-break.md`.
