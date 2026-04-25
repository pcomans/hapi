---
name: Beckerath 1997 Chronologie — README/transcribe.md pre-ingest review
description: P1/P2 findings from the schema and scope review of the Beckerath 1997 source before OCR ingest begins
type: project
---

Pre-ingest review of `pipeline/pipeline/authority/sources/beckerath-1997-chronologie/` conducted 2026-04-25.

**Why:** README and transcribe.md had schema design issues that would propagate through the entire three-subagent extraction if not fixed first.

**P1 findings (must fix before ingest):**

1. `horus_name` field label is wrong — Beckerath's parentheticals are heterogeneous (Horus names in Dyn 1, Eigenname/nomen in Dyn 4, prenomens in Dyn 18, mixed in Dyn 19). Rename to `egyptian_titulary` or add a `parenthetical_kind` tag.
2. `15V` prefix misidentifies Beckerath's Dyn 16 — his heading reads `16. Dynastie (Hyksos-Vasallen, gleichzeitig mit Dynastie 15)`. Correct `dynasty` integer is 16.
3. `24S` prefix references a non-existent sub-line — Dyn 24 in Anhang A has only two rows (Tef-nachte + Bokchoris), no separate Sais branch.
4. Dyn 21 `21H` HPA stream overstated — Beckerath gives only 2 HPA names in a tail paragraph of Supplement zu A (PDF p.109), not a parallel column. Don't import Kitchen's fuller list under Beckerath IDs.
5. Mixed-certainty date encoding rules missing: `ca. 837–798 (785?)`, `vor ca. 746` (null start), day/month-prefixed dates (`31.5.1279`), `Herbst 1337–1333`, `664–ca.655` (per-endpoint certainty differs). All unaddressed by schema as written.
6. PDF page range ambiguous at p.109 — Anhang B starts on the *right half* of PDF p.109; transcribers must be told to stop at the fold, not at the start of that page.

**P2 findings:**

- Period enum `Vorgeschichte` truncates Beckerath's full heading `VORGESCHICHTE (PRÄDYNASTISCHE ZEIT)` — document the truncation.
- Dyn 0 has no numeric BCE endpoints (`ungefähr 150 Jahre`) — schema needs explicit null-start rule.
- Dyn 2 `Gegenkönig` entry (composite annotation, PDF p.105) needs explicit extraction rule (1 row vs 2 rows vs notes-only).

**Verified correct:** "332 BCE" stop, nine-period inventory, Anhang B/C exclusion, four-field high/low schema shape, methodology overall.

**How to apply:** When reviewing subsequent Beckerath extraction chunks, watch especially for agents putting prenomens or nomens into the `horus_name` field (the most common semantic disagreement expected), and for slash-date mis-splits on the mixed-certainty rows above.
