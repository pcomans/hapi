---
name: project-pm-memphis-abusir
description: PM III.1 Memphis Phase-0 source; chunk-36 (Abûsîr, ABU- rows 850-877) review state and the prompt-induced diacritic regression found there
metadata:
  type: project
---

Porter & Moss III.1 Memphis authority source lives at `pipeline/pipeline/authority/sources/porter-moss-memphis/`. reconciled.jsonl accumulates chunks (chunks 1–35 signed off = 849 rows; chunk-36 Abûsîr = the 28 `ABU-` rows, lines 850–877). fix_rows.py holds per-chunk CHUNK<N>_CORRECTIONS.

**Chunk-36 review (2026-07-04) found a prompt-induced diacritic regression** that future chunk reviews on this source must watch for:
- **Ayin codepoint drift.** prompt-chunk-36.md line 96 says "Use ayin U+02BF (ꜥ …)" but the glyph it pastes is actually U+A725 (ꜥ, Egyptological ain), NOT U+02BF (ʿ, modifier letter left half ring). Agents copied the glyph → all 28 ABU rows use U+A725 while the entire source-wide convention (303 lines) uses U+02BF. A single authority file with two ayin codepoints breaks the enrich-stage string matching that is Hapi's whole point. Fix: normalise ABU ayins to U+02BF.
- **Macron dropped on Rēʿ-names.** Established chunks write Saḥurēʿ / Neuserrēʿ / Neferirkarēʿ / Menkaurēʿ / Rēʿ WITH macron (109 lines carry ē). ABU rows wrote plain Saḥureꜥ / Neuserreꜥ / Neferirkareꜥ. PM does print the macron (confirmed on rendered p.345). Same wrong-matching risk.

**Why:** these are Rule-4 / cross-museum-matching defects, merge-blocker class, not cosmetic — same king spelled two ways in one file.
**How to apply:** when reviewing any new chunk of this source, grep the new rows' ayin codepoint against the source-wide one, and check Rēʿ-name macrons against prior chunks, before signing off. See [[feedback-pm-headword-typography]] for the scope heuristic used in the same review.
