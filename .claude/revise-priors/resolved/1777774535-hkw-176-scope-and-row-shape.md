# Revise priors: HKW #176 scope + row-shape decision

- **Date**: 2026-05-03 (unix 1777774535)
- **Agent**: parent (Claude Opus 4.7) — first real use of the revise-priors skill
- **Triggered by**: starting work on issue #176 (HKW 2006 schema audit, Tier 2, 6 P1)

## Scope

Implementing the schema-audit fix for `pipeline/pipeline/authority/sources/hkw-chronology-2006/`. The audit found 6 P1, all in one source (issue #176, [docs/schema-audit-2026-05-findings.md](../../../docs/schema-audit-2026-05-findings.md)). HKW currently has no `merge.py` or `fix_rows.py` — single-transcriber extract. Building both as part of the fix.

## Assumption suspected (#1) — that all 6 P1 must land in this PR

The audit doc + `feedback_schema_p1_merge_blockers.md` say "All P1 findings are merge-blockers. No 'unless negotiated' / 'deferred to follow-up PR' escape." But I was about to scope down to ~3 P1 (Shapes A, B, J-subset) and defer Shape C (load-bearing facts in `note` field — 5 categories of structured facts including coregencies, rival-claimants, alt-reading qualifiers, per-bound `ca.` qualifiers, transcription-correction provenance) and the rest of Shape J (typed flags for `is_coregency`/`coregency_with`, `is_rival_claimant`, `dynasty_branch`, `null_dates_reason`).

That's exactly the slip-workaround the revise-priors skill exists to prevent. Either the rule is "all P1 in one PR" (in which case this is a much bigger PR than the previous Tier 1 fixes), or the rule is "P1 can be split across PRs if scope warrants" (in which case `feedback_schema_p1_merge_blockers.md` needs an exception clause documented).

## Assumption suspected (#2) — `rulers: list[{...}]` is the right row-shape for category-3 multi-ruler entries

5 HKW rows pack multiple rulers into one chronological slot (e.g. `Sobekhotep VIII, Nebiriau, Rahotep, Sobekemzaf I & II, Bebiankh` — 6 SIP-era kings under one date range because HKW doesn't know the order). Two structural options for the fix:

- **(a) `rulers: list[{name, prenomen, alternative_reading, alt_names}]`** — one row per HKW chronological slot; each compound row carries N ruler entries. Preserves HKW's "we don't know the order" semantic. Phase-A consumers must learn to iterate `rulers[]` to get per-person matches against pharaoh.se / Beckerath / Leprohon.

- **(b) Split to one row per person** — synthesize 4–6 separate rows from each compound HKW entry. Matches every other authority source's per-person convention (PM, D&H, Leprohon, Beckerath, Ryholt, Baud, Kitchen, Shaw, iDAI, pharaoh.se). But: produces N rows with IDENTICAL date ranges, which Phase-A might mis-interpret as coregents (instead of HKW's actual "we don't know which order" hedge).

I'd recommend (a) because option (b) loses the chronological-aggregate semantic, but (a) diverges from corpus convention — every Phase-A consumer must remember HKW is special.

## Evidence

- `docs/schema-audit-2026-05-findings.md` — the audit doc, lists all 6 P1 across Shapes A/B/C/E/G/I/J.
- `pipeline/pipeline/authority/sources/hkw-chronology-2006/reconciled.jsonl` — 207 rows; 12 rows pack multiple names into `display`; 5 of those are genuinely multi-ruler (cat 3); 7 are name-variant-of-same-person (cat 1+2).
- HKW PDF p.493 (verified): `Smenkhkare'/Nefernefruaten` slash-row gets ONE prenomen `'Ankhkheprure'` and ONE date range — HKW itself unifies them as one chronological slot with name-uncertainty hedge.
- HKW PDF p.492 (verified): `Amenhotep IV/Akhenaten` is one person (name change after Year 5).
- HKW PDF p.488 (visible in extract): `Swadjtu, Ined, Hori, Dedumose` is a single chronological slot covering 4 SIP-era short-reigning kings.

## Decision needed from user

**Two questions, in priority order.**

1. **P1-deferral policy for HKW.** Three options:
   - (a) Strict: do all 6 P1 in this PR. Estimated PR size: ~600+ lines diff (new `fix_rows.py` ~300 lines, schema migrations on 207 rows including 12 restructures, ~10 new tests, README rewrite, prompt-rule additions for future re-extraction).
   - (b) Phased: ship Shapes A + B + J-subset (`is_multi_ruler_entry`, `name_uncertain`) in this PR; open follow-up issues for Shape C (note field migration) and rest of Shape J (`is_coregency`/`is_rival_claimant`/`dynasty_branch`/`null_dates_reason`). Documented as explicit-policy exception for HKW given the source has no prior extraction infrastructure.
   - (c) Phased + amend `feedback_schema_p1_merge_blockers.md` to allow phased P1 fixes when a single source has 5+ P1 findings.

2. **Row-shape for category-3 multi-ruler entries.** Two options:
   - (a) `rulers: list[{...}]` — preserve HKW's chronological-aggregate semantic, diverge from corpus convention.
   - (b) Split to one row per person — match corpus convention, lose HKW's grouping signal.

## Recommendation

**My answers if forced to choose alone:**
- Q1: **Option (b)** — phased. Without amending `feedback_schema_p1_merge_blockers.md`, just open follow-up issues with explicit P1-status carry-forward and a tracking comment. The MVP P1 set is exactly the 3 "data is genuinely wrong on disk right now" findings; Shape C's `note`-field facts are accurate-but-untyped, which is bad but not actively-shipping-bad-data.
- Q2: **Option (a)** — `rulers: list[{...}]`. The compound rows ARE chronological aggregates per HKW's own table layout; splitting loses that signal. README documents the divergence + Phase-A consumer note.

But the user gets to decide both. The divergence on Q2 in particular is bad to have hidden — it'll surprise Phase-A engineers later.

## Resolution paths

- **Dismiss** (proceed with my recommended (b) + (a)): `rm .claude/revise-priors/1777774535-hkw-176-scope-and-row-shape.md`
- **Resolve** (amend my plan in code/docs first): edit `feedback_schema_p1_merge_blockers.md` and/or this issue's scope, then `mv .claude/revise-priors/1777774535-hkw-176-scope-and-row-shape.md .claude/revise-priors/resolved/`

(Note: the `rm` form is the intended cheap-dismiss path. The `mv` form is for the case where the user actually changes priors in the codebase first — e.g. if they pick Q1(a) strict and want to do all 6 P1 here, no rule amendment needed; if they amend `feedback_schema_p1_merge_blockers.md` to allow phased fixes, that change goes in first then the marker moves to resolved.)
