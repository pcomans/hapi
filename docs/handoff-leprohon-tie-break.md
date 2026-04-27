# Leprohon `_majority` tie-break enforcement — handoff

**Issue #128.** Resolves the silent-first-seen pick at 1/1/1 ties in `pipeline/pipeline/authority/sources/leprohon-2013-titulary/merge.py`. Per CLAUDE.md constitutional rule 6 ("Data is sacred"): a value chosen by silent first-seen at a tie is data with no provenance — slop. This PR replaces that with option (a) enforcement: every IDENTIFIER tie either has a cited override or fails loud.

## Pipeline

1. **Pre-merge MdC normalisation.** `_normalise_for_merge` applies the project's MdC → IFAO mapping (`A→ꜣ, a→ꜥ, H→ḥ, x→ḫ, X→ẖ, S→š, T→ṯ, D→ḏ, q→ḳ`) to the `transliteration` sub-field of every name-list entry BEFORE the per-field majority vote. Encoding-style differences (`HqA tAwy` MdC vs `ḥḳꜣ tꜣwy` canonical) collapse to one equivalence class pre-vote — eliminates 30+ of the 134 IDENTIFIER ties in the original audit.

2. **`_majority` tie classification + dispatch.** When the top two equivalence classes have equal count:
   - `TIE_BREAK_OVERRIDES.get((lid, field))` — explicit cited resolution → use it.
   - `_classify_tie(field, values)`:
     - `PROSE` (only `source_note` / `attested_in` differ) → `_resolve_prose_tie` deterministic shortest-wins. Source-faithful: shorter source_notes typically have less editorial scaffolding ("Per Leprohon fn. N:" prefixes, paraphrased glosses) and stay closer to Leprohon's own footnote text.
     - `IDENTIFIER` / `STRUCTURE` / `SCALAR` → **raise**. Data is sacred.

3. **`TIE_BREAK_OVERRIDES`** loaded from `tie-break-overrides.json` (sibling of `merge.py`). 48 entries, populated by the 2026-04-27 3-arbiter blind re-extraction sweep.

## How the 48 overrides were established (the 2026-04-27 sweep)

After pre-merge MdC normalisation, 48 ties remained across 10 chunks (32 IDENTIFIER + 8 STRUCTURE + 8 SCALAR). For each chunk:

1. Spawned 3 fresh general-purpose Claude Code subagents (tags d/e/f). Each got the chunk's extraction prompt + OCR markdown + the contested (lid, field) list with the original a/b/c values shown only as a post-hoc sanity check ("blind first").
2. Each arbiter independently re-extracted each contested field from the OCR.
3. Aggregation: per-tie 3-arbiter vote. ≥2/3 majority on the same canonicalised value → that's the override. 1/1/1 with 2/3 `matches_agent` agreement on which original agent was right → use that agent's value (the arbiters' detail differences were typically non-load-bearing source_note framing).

Total: 30 arbiter agents (3 × 10 chunks). 48 overrides resolved unanimously or by majority. Net: 0 escalations after `matches_agent` fallback.

### One mis-read caught manually

`leprohon-21.02 / source_citation`: all 3 arbiters voted `printed=137 / physical=158`. Re-verification against the OCR (`chunk-p157-p173-pypdf.md` line 95 carries the running header "138"; Smendes' headword at line 110 follows it) showed `printed=138 / physical=159` is correct. The override carries the corrected value; the obsolete `fix_rows.py` SPOT_CORRECTION on `source_citation.printed_page` was removed (one-shot full-citation override now does both fields together).

**Lesson:** 3 blind arbiters can share a common mis-read of the OCR. The cross-check against committed evidence (running headers) caught it. Not a methodology failure — the methodology produced a wrong answer, and the OCR-grounded re-verification corrected it.

## Cost / scale

- Pre-merge MdC pass: <10ms per merge run. No measurable runtime cost.
- 48 overrides × ~250 byte avg = ~12KB JSON file alongside merge.py.
- Merge time: unchanged (overrides are `dict.get` lookups).

## What changed in CLAUDE.md

- **Rule 2** (No defensive programming) extended with: "**No silent arbitrary picks.** At reconciliation time (merging across agents, deduplicating, voting), ambiguity must raise unless the resolution rule is documented as deterministic with a citation."
- **Rule 6** renamed from "Raw data is sacred" to **"Data is sacred"**, extended to cover reconciled artifacts: "A value chosen by silent first-seen-pick at a tie is no longer traceable to either the source or a documented rule — it is data with no provenance."

## Going forward

Every Phase-0 source's `merge.py` should adopt the same enforcement when its agent extraction encounters 1/1/1 ties:
1. Pre-merge canonicalisation passes (whatever the source's natural normalisation rules are) — collapse encoding-style ties before the vote.
2. `_majority` raises on uncovered IDENTIFIER ties, deterministic rule on prose-only ties.
3. Per-source `TIE_BREAK_OVERRIDES` table with cited rationales.

Baud, Kitchen, Ryholt, Dodson-Hilton, Hkw all currently use the silent first-seen idiom. Migrating each is its own PR; this PR is Leprohon-only.
