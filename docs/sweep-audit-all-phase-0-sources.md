# Sweep audit — all Phase-0 authority sources

**Purpose.** Retrospectively run `code-reviewer` and `egyptologist-reviewer` subagents across every committed Phase-0 authority source. Motivated by the session-2026-04-23 retrospective audit which revealed that the `feedback_pr_reviewers.md` policy ("run code-reviewer AND egyptologist-reviewer on every PR") was **only enforced by memory, not by a hook** — so earlier PRs shipped with Gemini coverage alone. The PM Theban / HKW retrospective found a P1 data error (Scorpion I dynasty attribution) plus rule-3 / rule-5 gaps. Other sources likely have similar hidden issues.

**This document is a spawn prompt for a coordinator agent.** The coordinator reads this file and executes it; it does not do the reviewing itself. The actual reviewing is done by `code-reviewer` / `egyptologist-reviewer` subagents spawned from the coordinator.

## Scope

In scope: every directory under `pipeline/pipeline/authority/sources/`. At the time of writing:

- `baud-1999-ok-royal-family` — OK royal family (Baud 1999)
- `dodson-hilton-queens` — Chs 1–4 Brief Lives (D&H 2004); Ch 5 pending
- `hkw-chronology-2006` — HKW chronology table IV.2 + Ch 2 Hendrickx Dyn-0 addendum
- `holbl-2001-argead` — Argead bridge (Hölbl 2001) — may be dropped/partial per project memory
- `idai-gazetteer` — DAI Gazetteer sites
- `kitchen-tipe` — Kitchen 1996 TIP chronology
- `leprohon-2013-titulary` — Leprohon 2013 full titulary (14 chunks)
- `pharaoh-se` — pharaoh.se web scrape (381 rulers)
- `porter-moss-theban-necropolis` — PM I.2 Theban Necropolis (just audited in session-2026-04-23; include for completeness and because new chunks 7+8 landed)
- `ryholt-1997-sip` — Ryholt 1997 SIP chronology
- `shaw-ohae-2000` — Shaw OHAE chapter banners (13 period rows)
- `wikipedia-ptolemaic` — Wikipedia-Ptolemaic cross-reference

Out of scope (not Phase-0 source directories): anything in `pipeline/pipeline/authority/` outside `sources/`, and the test-fixture trees.

## Coordinator execution plan

You are the **sweep-coordinator agent**. Execute these steps in order.

### Step 1: enumerate

```bash
cd /Users/philipp/code/hapi
ls pipeline/pipeline/authority/sources/ | sort > /tmp/sweep-sources.txt
cat /tmp/sweep-sources.txt
```

Confirm against the scope list above. If the filesystem has new directories not in this doc, include them. If any listed directory is missing, note it and continue.

### Step 2: choose reviewer set per source

Not every source needs both reviewers:

| Source type | code-reviewer | egyptologist-reviewer |
|---|---|---|
| Book-transcription source (Baud, D&H, HKW, Kitchen, Leprohon, PM Theban, Ryholt, Shaw, Hölbl) | YES | YES |
| Web-scrape source (pharaoh-se, wikipedia-ptolemaic) | YES | YES (for ruler-attestation correctness) |
| Gazetteer / non-scholarly data (idai-gazetteer) | YES | NO (geographic data; egyptologist adds little) |

For each source, record the decision in a one-line comment in the coordination log.

### Step 3: spawn reviewers in parallel batches

**Do NOT spawn all ~20 subagents at once.** Cost + harness load risk. Batch by ~4 subagents in parallel, waiting for each batch before launching the next. Use the Agent tool with `run_in_background: true`.

For each source, the reviewer briefs look like this.

#### Code-reviewer brief template

```
Retrospective code review of source `pipeline/pipeline/authority/sources/<SOURCE>/` at
/Users/philipp/code/hapi. The source was merged in a prior PR without running a
code-reviewer subagent during the cycle (policy from feedback_pr_reviewers.md was
memory-only, not enforced by a hook — fixed in session-2026-04-23).

Read the full source directory: README.md, prompt.md (and any prompt-<chunk>.md),
transcribe.md if present, merge.py and fix_rows.py if present, reconciled.jsonl,
and all committed reviewer-notes / code-review files from prior cycles.

Then read the test file(s) at pipeline/tests/test_sources_<source>.py (or the
relevant class in tests/test_authority.py).

Review for CLAUDE.md compliance — especially:

- **Rule 1 (scholar):** every authoritative fact in reconciled.jsonl traces to a
  cited source page. Spot-check 5–10 random rows' `note` / `source_citation`
  fields. Call out any row whose fact is not cited or whose cite is wrong.
- **Rule 2 (no defensive programming):** merge.py / fix_rows.py should loud-fail
  on malformed inputs, not silently skip.
- **Rule 3 (deterministic enforcement):** rules that could be tests should be
  tests. Specifically: strip-ḥ policies, format conventions (tomb_id shape,
  prefix vocabularies), sort-order invariants. Flag anything enforced only by
  README prose / prompt markdown / after-the-fact CHUNK*_CORRECTIONS.
- **Rule 5 (tests assert values, not absence of errors):** for every populated
  field on every row, a test should pin its value. Flag substring-match,
  `None-or-non-empty`, try/except-pass, or `assert not raises` patterns.
- **Rule 12 (no defensive grandfather clauses):** if the source has a
  "chunks 1-5 did X because Y but chunks 6+ do Z" comment that excuses current
  code from a rule, flag it as a rule-12 violation.

Also check:
- Whether `fix_rows.py` has any reviewer-inserted characters not covered by the
  `feedback_fix_rows_unattributed_restoration` memory (rationale must name the
  reviewer-notes file line).
- Whether per-row tests cover every populated field per rule 5, or only a
  themed subset.
- Whether the source is a multi-chunk source and whether ALL_CORRECTIONS /
  ALL_RENAMES aggregation is validated by a test.

Write findings to `pipeline/pipeline/authority/sources/<SOURCE>/code-review-sweep-2026.md`
with P1 / P2 / P3 severities. Under 700 words. Don't spawn subagents, don't
run merge.py or fix_rows.py, don't open a PR.
```

#### Egyptologist-reviewer brief template

```
Retrospective scholarly review of source `pipeline/pipeline/authority/sources/<SOURCE>/`
at /Users/philipp/code/hapi. The source was merged in a prior PR without running
the egyptologist-reviewer subagent during the cycle (policy from
feedback_pr_reviewers.md was memory-only, not enforced by a hook — fixed in
session-2026-04-23).

Read the full source README.md, transcribe.md (if present), reconciled.jsonl,
and any prior reviewer-notes-*.md files.

Spot-check at least 10 rows against the cited source PDF (in proprietary/books/
or referenced in README). Verify:

1. **Identification correctness:** does the row's `display` / `occupant_name`
   match what the source actually prints? Any OCR misreads, transliteration
   drift, or wrong-ruler-attribution bugs?
2. **Field values:** dynasty numbers, regnal-year dates, tomb IDs, Naqada
   phases, prenomens — all traceable to the cited page?
3. **Provenance fidelity:** any `alternative_reading` / `note` content that
   was imported from general Egyptological knowledge rather than the cited
   source? (Like the Ka "Sekhen" provenance-leak flagged in the HKW Ch 2
   retrospective.)
4. **Scope faithfulness:** is the row's scope consistent with what the source
   actually says? E.g. if Hendrickx reserves Dyn-0 for cemetery-B rulers,
   rows claiming Dyn-0 should only be cemetery-B rulers.
5. **Cross-source sanity:** if this source claims something that another
   Phase-0 source contradicts (e.g., a reign-length different from HKW /
   Leprohon), flag the discrepancy for Phase-A reconciliation.

Write findings to `pipeline/pipeline/authority/sources/<SOURCE>/reviewer-notes-sweep-2026.md`
with P1 / P2 / P3 severities. Under 700 words. Don't spawn subagents, don't
open a PR.
```

### Step 4: collate findings

After all reviewers complete, read every `code-review-sweep-2026.md` and
`reviewer-notes-sweep-2026.md` file they produced. Write a coordinator summary
at `docs/handoff-sweep-audit-2026.md` containing:

- Per-source findings table: source | P1 count | P2 count | P3 count | key issues
- Cross-cutting patterns: any rule (e.g. rule 3 deterministic enforcement)
  that multiple sources violate in similar ways
- Fix-up PR batching plan: group findings by whether they need (a) data
  corrections, (b) test additions, (c) doc/audit-trail additions, (d)
  source re-extractions

### Step 5: report to user

Output a concise summary (~300 words) to the user and stop. The actual fix-up
PRs are the user's decision and a separate session's work.

## Guardrails

- **Do NOT commit or push anything.** The coordinator and every reviewer
  subagent are READ-ONLY on git.
- **Do NOT open PRs.** Any fix-up work follows the user's triage.
- **Do NOT modify reconciled.jsonl.** Only write `code-review-sweep-2026.md`
  and `reviewer-notes-sweep-2026.md` per source plus the single `docs/handoff-sweep-audit-2026.md`.
- **Skip sources that already have recent reviewer files.** `porter-moss-theban-necropolis`
  has `code-review-chunk7.md` / `code-review-chunk8.md` / `reviewer-notes-chunk7.md`
  / `reviewer-notes-chunk8.md` from the 2026-04-23 session. The sweep reviewer
  should still run on it to cover the full source (the prior reviews were
  per-chunk, not source-wide), but the per-chunk files should be cross-referenced
  in the sweep review to avoid duplicate findings.
- **Rate limit:** ~4 subagents in parallel max. Pause between batches until the
  prior batch completes. A full sweep of ~12 sources × 2 reviewers = ~24 subagent
  runs, so expect 6–8 batches across the sweep.

## Success criteria

- Every in-scope source has a `code-review-sweep-2026.md` file.
- Every book-transcription source has a `reviewer-notes-sweep-2026.md` file.
- `docs/handoff-sweep-audit-2026.md` exists and summarises cross-cutting patterns.
- The coordinator's final report to the user identifies the top 3–5 P1 findings
  across the corpus.
