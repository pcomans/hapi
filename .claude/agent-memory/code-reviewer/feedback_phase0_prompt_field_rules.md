---
name: Phase-0 prompts must be field-rule-based, not per-row answer tables
description: Recurring rule 1/7 failure mode across Phase-0 extraction prompts (Porter-Moss, Dodson-Hilton, Leprohon)
type: feedback
---

When reviewing a Phase-0 source's extraction prompt (`prompt.md` or `prompt-<chunk>.md`), the prompt MUST state field-extraction rules, not pre-specify per-row answers. A prompt that lists "for KV11 emit `["Bruce's tomb", ...]`; for KV17 emit `["Belzoni's tomb"]`; for everyone else emit `[]`" is an answer table — the 3-agent majority vote then becomes theater (agents transcribe the prompt back; `merge-disagreements.txt` shows zero disagreements not because extraction converged but because the prompt already contains the answer).

Signals of this failure mode:
- Per-tomb / per-ID tables enumerating expected field values.
- "Expected value per row" paragraphs under a field rule.
- "Known uncertainties" / "Pitfall summary" sections that name specific tomb_ids with their expected values (narrower regression of the same violation; seen on PR #70 chunk-4 after chunk-1/chunk-2 cleanup). Even one or two per-tomb callouts in a prose section leak into the agent jsonl — check `raw/agent-{a,b,c}-chunk<N>.jsonl` for `notes_from_pm` strings that quote the prompt verbatim.
- "Headword patterns to watch for" bullet lists that pair a specific sequence number with its expected `display_name` / `alt_display_names` tuple — seen on PR #88 Leprohon chunk-5 (`prompt-dyn13.md:94` hands agents `18. SEB / SAB (?) → display_name: "Seb/Sab (?)", alt_display_names: ["Seb", "Sab"]`). Any line of the form `N. HEADWORD → field: "value"` is the violation.
- Stub-row JSON templates with concrete field values (PR #88 `prompt-dyn13.md:67` put `"display_name": "one name lost"` inside the literal row spec rather than describing how to derive the value).
- `merge-disagreements.txt` with zero disagreements on a chunk with ≥10 rows.
- Pitfall summaries that re-state answers as numbered rules.

**Why:** constitutional rule 1 (facts trace to a raw source, not to the prompt) and rule 7 (authority-lookup, not hardcoded domain values). PR #66 (Porter-Moss chunk 1) was flagged for this; PR #68 (chunk 2) regressed; PR #70 (chunk 4) regressed again in narrower form — 2 of 5 rows got per-tomb callouts in "Known uncertainties" + pitfall summary, and the agents transcribed the prompt's KV55 quote back verbatim. PR #88 (Leprohon chunk 5) reproduced the pattern in the headword-pattern bullet list + stub template. Fix is always to rewrite field-by-field rules describing how to *detect* the shape in the text (what constitutes a classical alias; how to distinguish a usurpation note from an alt-name; how to detect a trailing `(?)` on a slash-headword), mirroring the corrected chunk-1 prompt style. The abstract rules (`Probably <NAME>` handling, nickname-only headword handling) are usually already present at the top of the prompt; deleting the per-tomb "uncertainty" callouts is a mechanical, safe edit.

**How to apply:** on any Phase-0 PR review, skim the extraction prompt first. Tables keyed by `tomb_id` / `kitchen_id` / `dh_id` / `baud_id` / `leprohon_id`-sequence-number containing expected values are almost always the violation. ALSO check "Known uncertainties" / "Pitfall summary" / "Headword patterns to watch for" prose sections for entry-specific callouts — the narrower form is still rule 1. Stub-row JSON templates should describe the *shape* ("emit a row with all name-lists empty") not the *values* ("emit `display_name: "one name lost"`"). Flag as blocking.
