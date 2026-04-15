# Human Egyptologist sign-off — Dodson-Hilton Amarna Interlude chunk

Per ADR-017 step 6 ("Human review — required, not yet performed"), a
human reviewer walked a sample of rows against the source PDF
(pp. 154–157, physical pp. 142–145) on **2026-04-15**.

This is the **first** human sign-off on any Dodson-Hilton chunk; PR #37
(Pre-Amarna Power-and-Glory Brief Lives, 59 rows) remains provisional
until a separate human review is logged for it.

## Reviewer

Philipp Comans (project owner / transcriber).

## Rows reviewed

Seven high-leverage rows across the 41-row Amarna chunk:

| # | Row(s) | D&H p. | Scope of review |
|---|---|---|---|
| Q1 | `Tutankhuaten` | 157 | `alt_names` slash-expansion (`TUTANKHATEN/AMUN` → `["Tutankhaten", "Tutankhamun"]`) |
| Q2 | `Kiya` | 155 | hedge transitivity on `father_name: "Tushratta (conceivably)"` |
| Q3 | `Meryetaten` | 155 | `alt_names: ["Neferneferuaten"]` (identifying her with the female regnal name) |
| Q4 | `Mutnodjmet A` / `Mutnodjmet Q` | 155–156 | two-row vs one-row for D&H's "perhaps identical" pair |
| Q5 | `Nefertiti` | 156 | `children_names: []` (parent→child denormalization question) — **deferred**; see below |
| Q6 | `Ankhesenpaaten` | 154 | listing Ay in `spouse_names` with `(perhaps, brief marriage)` hedge |
| Q7 | `[...]18A–H`, `[...]18J`, `[...]18K–N`, `–18P`, `–18Q` | 157 | one-row-per-D&H-group-entry granularity |

The remaining 34 Amarna rows were NOT individually reviewed by the human
pass — the seven sampled rows were chosen to cover the extraction calls
most likely to be contested (regnal-name identity claims,
perhaps-identical pairs, hedge preservation, lacuna granularity).

## Verdict per reviewed row

| # | Verdict | Notes |
|---|---|---|
| Q1 | ✅ Correct | Slash-expansion `TUTANKHATEN/AMUN` → `["Tutankhaten", "Tutankhamun"]` confirmed. |
| Q2 | ✅ Hedging preserved correctly | Transitive `(conceivably)` on `father_name` is the right call — if Kiya ≠ Tadukhipa, Tushratta ≠ her father, so the hedge genuinely attaches to both claims. |
| Q3 | ✅ Accept | Meryetaten-as-Neferneferuaten is a reasonably well-established identification; `alt_names: ["Neferneferuaten"]` is appropriate for authority-layer dedup. |
| Q4 | ✅ Two rows correct | External cross-check with Gemini confirms scholarly literature has not settled the Mutnodjmet A = Mutnodjmet Q identity; keep them as separate-but-flagged-identical rows. |
| Q5 | ⏭️ Deferred | Open architectural question on parent→child denormalization. Current extract keeps `children_names` empty for Nefertiti (mirrored by the 6 daughters each listing her as `mother_name`). Decision to be made at Phase A authority curation, not blocking on this PR. |
| Q6 | ✅ Decision stands | Listing Ay as `spouse_names` entry with `(perhaps, brief marriage)` parenthetical hedge is faithful to D&H's `"perhaps indicating"` language. |
| Q7 | ✅ One row per D&H group entry | Exploding `[...]18A–H` into 8 individual rows would fabricate precision that the lacuna markers explicitly deny; keeping the D&H grouping is the right call. Dropping them entirely was floated as an alternative but is a downstream-filtering decision, not an extraction call. |

## Consequence

Six of the seven reviewed rows are sign-off accepted. The `reconciled.jsonl`
values for those six are validated against D&H's prose by a human with
sufficient context to judge the extraction calls. **They should no longer
be marked provisional for Phase A authority curation purposes** (the
remaining 34 un-sampled rows remain provisional at the chunk level).

Q5 is a source-wide architectural question on `children_names` semantics
(discussed below). It is not a row-level error; it is a design decision
deferred to the Phase A authority-curation phase. Flagging here so it
is not forgotten.

## Deferred item — Q5 detail

Reviewer's instinct: avoid denormalization where possible. If a child
has its own Brief Lives entry, the child-row's `father_name` /
`mother_name` is the single source of truth; the parent-row's
`children_names` would just duplicate that. Potentially drop
`children_names` entirely and make the parent→child direction a
downstream-derived view.

Options (not resolved in this review):

**A.** Drop `children_names` across the board. Parent→child relations
live only in child rows' `father_name` / `mother_name`. Extract is
cleanest; Phase A authority curation reconstructs the parent→child
view by scanning all rows.

**B.** Keep current mixed pattern: populate `children_names` when D&H's
own entry names children in prose (Mutemwia → `["Amenhotep III"]`,
Yuya → `["Tiye A"]`, etc.), *plus* a small handful of cross-entry
inferences (Shuttarna II → `["Gilukhipa"]`, Tushratta →
`["Tadukhipa"]`) documented in the source README. This is what PR
#38 ships.

**C.** Keep `children_names` only when D&H's own entry names children
in prose; no cross-entry inference. The re-run experiment in PR #38
accidentally produced this pattern (when agents followed the prompt
text literally); it was reverted only because OTHER hedges were lost
in the same re-run, not because `children_names` changes were wrong.

Recommendation deferred to the Phase A authority-curation phase. That
phase will need to make this call consistently across all Phase 0
sources (pharaoh.se, HKW, Dodson-Hilton, Baud 1999, etc.), and the
decision logic is the same everywhere. Making it source-by-source would
create drift.
