---
name: Document-only sourcing rule for factual fields in extraction prompts
description: Flag Phase-0 prompts that don't require world-knowledge be off-limits for factual fields. Prevents agents from filling null gold-values with training-data inferences (venue/date type errors).
metadata:
  type: feedback
---

When auditing a new `prompt-chunk-*.md`, check that the prompt explicitly forbids the agent from filling **factual** fields (filiation, dates, monuments, titles, cross-references, regnal years, dynasty bracketing, PM references) from world knowledge when the source PDF is silent. If the rule is missing or only present in soft form ("do not invent values"), recommend adding a load-bearing **document-only sourcing rule** near the top of the prompt.

**Recommended phrasing** (adapt to the source's vocabulary):

> **Every factual value you emit must appear literally in the chunk PDF, or follow a direct mechanical reading of something the PDF says** (e.g., a French dynasty numeral that Baud prints, a name verbatim from a header, a title from a `TITRES.` rubric).
>
> **World knowledge is OFF-LIMITS** for these field categories: filiation, dates, monuments, titles, cross-references, regnal years, dynasty assignment, PM/site references. If you happen to know — from training data or other Egyptological sources — that a queen is the wife of king X, or that a monument is in cemetery Y, but the PDF does not literally state it, the value is `null`.
>
> Rule of thumb: if you cannot point to the exact span on a specific page that contains the value (or that obviously implies it via the source's own documented conventions), leave the field null / `[]` / `{}` per its schema type.

**Scope carve-out.** The rule applies to FACTUAL fields. It does NOT apply to convention-based anglicisation fields (`name_anglicised` and equivalents) where the field's purpose is to hold a standard English form even when the source itself prints only French / German / transliteration. State the carve-out explicitly in the prompt; do not leave it implicit.

## Why

**Mechanism evidence (NIPS-1989 hill-climb, May 2026).** On a single English-academic-paper extraction (ExtractBench task `academic/research/NIPS-1989-handwritten-digit-recognition`), Haiku × 1 agent with the default ExtractBench-style prompt scored 0.714 (5/7 deterministic-scoreable fields). The two failing fields were both world-knowledge fill-ins: `venue: "NIPS 1989"` and `publication_date: "1989"` where the gold strictly wanted `null` (the paper itself doesn't print those facts in its title page). Adding the document-only sourcing rule moved Haiku × 1 to 0.952 (3-rep mean, 1 slip), and Sonnet × 1 with the same rule hit 1.000 (3/3). The 3-agent voting setup at default-prompt could not catch this class of error because all 3 agents made the same world-knowledge inference.

**Phase-0 spot-check evidence (Baud chunk 1).** A one-shot re-extraction of Baud chunk 1 with the blanket strict rule produced 40 rows. Comparison against the shipped `reconciled.jsonl` (entries 1–40) showed:
- **7 `name_anglicised` values present in production, absent under the strict rule** (`Iput I`, `Ankhhaf`, `Ankhesenmeryre I/II`, `Ihetihotep`, etc.). Grep of the chunk-1 PDF text layer confirmed none of those forms appear in Baud — Baud writes pure French throughout (`Pépi Iᵉʳ`, `Khoufou`, `Snéfrou`). The production values were filled in from training-data knowledge of conventional anglicisations.
- **No factual disagreements traceable to the strict rule.** Filiation, dates, dynasties, titles, monuments matched. The strict rule didn't expose any factual hallucination in chunk 1's production output (which suggests either Baud chunk 1 was already factually clean, OR the strict rule's protection would activate only on chunks where production HAD a factual hallucination — neither directly demonstrated).

The Baud spot-check is the source of the scope carve-out: suppressing `name_anglicised` removed values that downstream search consumers actually use, and that any reviewing Egyptologist would have signed off on. So the recommendation is **scope to factual fields, exempt convention-based anglicisation**.

## What's NOT demonstrated (be honest in your audit)

- The rule has not been shown to expose a specific factual hallucination in any shipped Phase-0 source. The case for it is mechanistic (NIPS-1989 result + plausibility argument), not empirical-on-Egyptological-data.
- Multi-chunk effect untested. The rule has only been run on Baud chunk 1.
- Effect on dense per-row catalog shapes (Leprohon Ch X, PM TT-decades) untested.

Treat the rule as a default-on recommendation for NEW prompt drafts. Existing per-source prompts are pinned to their shipped `reconciled.jsonl` and the egyptologist sign-off they received; do not retroactively modify them just to add this rule.

## How to apply

In your audit report, if the prompt lacks an explicit document-only sourcing rule for factual fields, raise a **P2 finding** (not P1 — the rule is recommended-default, not required-by-CLAUDE.md-rule-3-yet) titled "Document-only sourcing rule missing" with:
- Quote the prompt's existing world-knowledge guidance if any (most prompts say "do not invent" — note that this is too soft).
- Suggest the load-bearing phrasing above, adapted to the source's vocabulary.
- Suggest the `name_anglicised` carve-out if the source has such a field.
- Link this memo so the prompt author understands the evidence and limits.
