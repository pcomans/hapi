# Retrospective Code Review — PR #102 (Ch 2 Hendrickx Dyn-0 rows)

Reviewer: code-reviewer subagent, 2026-04-23. Merge commit `c157092`. Review
scope is the 4 new `reconciled.jsonl` rows, the `test_authority.py` updates,
and the README changes.

## Findings

### P1 — Hand-extraction audit trail is thinner than the constitutional rule 1 bar

The 4 Dyn-0 rows were hand-extracted directly from `raw/chunk-ch2-p55-p93.txt`
(pypdf text layer) without going through the 3-subagent extraction pipeline
that chunks 7+8 used. Rule 1 says every authoritative fact must trace to "a
clear, documented, reproducibly-acquired source on disk." The `note` fields
cite Hendrickx pp. 88/89/91/92 explicitly and that is genuinely load-bearing
(good), **but** the README says only "hand-extracted from Hendrickx's
narrative prose and Tables II.1.6 and II.1.7" — it does not name the
extractor (Claude? which session?), the method (how were p.88/89/91/92 chosen
out of the 55-93 range?), or whether an egyptologist-reviewer ran. Compare
`feedback_fix_rows_unattributed_restoration.md` in the code-reviewer memory:
corrections inserting characters absent from the raw text layer need a cited
verifier. These 4 rows don't insert characters — they insert 4 whole rows —
and the bar should be *higher*, not lower.

**Fix:** add a short `transcribe-ch2.md` (or append a section to README)
naming: (a) which agent/session produced the rows, (b) the decision path for
which pages to cite, (c) confirmation that the pypdf text layer was the
only source (no paraphrase from memory / model prior), (d) whether an
egyptologist-reviewer signed off. This is a one-time housekeeping fix; do not
block future Ch-2 expansions on it but do it before any further hand-extract
chunks land.

### P2 — `alternative_reading: "Sekhen"` for Ka is under-sourced for rule 1

The row's own note says: *"Alternative reading 'Sekhen' is the traditional
alternative cartouche reading, widely attested in Egyptological literature
**though Hendrickx does not use it in his own tables**."* That's a field
value sourced to general Egyptological knowledge, not to the committed raw
file. Rule 1 explicitly rejects "the model knows" as a source. Two clean
fixes: (a) drop `alternative_reading` to `null` for Ka and move "Sekhen" into
`note` as "traditionally also read Sekhen (not used by Hendrickx)", or
(b) cite a specific page in Hendrickx Ch 2 where he acknowledges the reading
(p.89 tables mention it? verify). Option (a) is the conservative choice and
keeps the field semantically tight: `alternative_reading` = "reading the
source itself offers," not "reading Egyptology offers."

### P2 — Dyn-0 parent_period is structurally inconsistent with the rest of the file

Every other dynasty row in `reconciled.jsonl` has a non-null `parent_period`.
Dyn-0's `null` is justified in the note ("sits at the Predynastic / Early
Dynastic boundary") and the test asserts it explicitly — that's fine as data,
but it means `test_dynasty_parent_period_references_exist` silently allows
orphan dynasties. Either (a) add a `"Predynastic"` period row citing
Hendrickx Table II.1.7 so Dyn-0 has a parent, or (b) tighten the test to
whitelist Dyn-0 as the sole allowed orphan. Current state: a future dynasty
row that forgets `parent_period` will pass tests. Rule 3 (deterministic
enforcement over convention) prefers (b) as a minimum; (a) is scholarly
cleaner if Hendrickx supports it.

### P3 — `test_dyn0_rulers_present` conflates existence with content

The test asserts `set(dyn0_rulers) == {"Iry-Hor", "Ka", "Scorpion I"}` and
then loops asserting dates-null / page-range / approximate / "Hendrickx" in
note. Fine, but it does *not* assert the specific page numbers (88/89/91),
the greek_form being null, the prenomen being null, or the exact dynasty
number. Rule 5: "every fixture test class must assert all mappable fields."
The 4 new rows populate ~10 fields each and the tests assert 4-5. Add
per-ruler explicit-page assertions (`assert dyn0_rulers["Iry-Hor"]["page"]
== 89`) so a typo in a page number is caught.

### P3 — `test_page_numbers_in_range` 55-93 is a wide net

The valid-page set `range(55, 94)` covers 39 pages but only 4 pages are
actually cited (88/89/91 and the dynasty row's 88). A typo turning `89` into
`79` would pass. Tighten to the cited-pages set, or add an explicit "every
Ch-2 row cites one of {88, 89, 91, 92}" assertion. Low priority because the
pages are also asserted implicitly by the per-ruler tests, but the wide
range invites future drift as more Ch-2 chunks land.

### P3 — README "Ch 2 Hendrickx" section and row count drift risk

README says "207 rows total" as plain prose; the test asserts 207. Two
sources of truth for the same number (rule 4). Either drop the number from
the README or have the test read it from the README. Low priority — the
count is also obvious from `wc -l` — but worth noting.

## Summary

The scholarly work is solid: per-row page cites, honest notes about
ambiguous tomb-row placement for Ka, and explicit flagging of the
`alternative_reading` provenance issue in Ka's own note (which is how I
caught it). The gaps are audit-trail (P1) and one field-sourcing slip (P2);
the rest is test tightening. No merge regret — these are all fixable in a
follow-up PR.

File reviewed: `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/hkw-chronology-2006/reconciled.jsonl`
Tests: `/Users/philipp/code/hapi/pipeline/tests/test_authority.py`
README: `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/hkw-chronology-2006/README.md`
