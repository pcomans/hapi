# Revise priors: Baud #178 hedge-typing scope decision

- **Date**: 2026-05-03 (unix 1777791674)
- **Agent**: parent (Claude Opus 4.7)
- **Triggered by**: Starting issue #178 (Baud 1999 OK Royal Family, Tier 2, 4 P1)

## Scope

Implementing the schema-audit fix for Baud 1999. Strict-all-4-P1 per the established #176/#177 policy. Family 1 (joint-entry / collective-monument / lost-name typed flags + pm_refs/monuments list-promotion) is straightforward — same shape as PM #169 / HKW #188 / Ryholt #189.

**Family 2 is the open question.** The audit recommends promoting `father_name: str | None` → `father: {name: str, confidence: enum{attested, probable, reconstructed, contested}, baud_id: str | None} | None` (and same for `mother`, `spouse_names` items, `children_names` items). Affects ~62 father + 14 mother + 78 spouse + 61 children rows = **~215 row-fields** restructured.

## Assumption suspected

Whether to type the hedge-and-cross-ref encoding (Shape E + Shape H + Shape I item 1) at the **dict-shape** level, or stay with **scalar names + companion `*_baud_id` fields + scalar hedges in `notes_from_baud`**.

## Evidence

The audit cites `feedback_schema_p1_merge_blockers.md` ("All P1 findings are merge-blockers. No 'unless negotiated' / 'deferred to follow-up PR' escape.") and lists Shape E, Shape H, Shape I as P1 contributors. Strict reading: all of Family 2 lands in this PR.

Concrete data from current `reconciled.jsonl`:
- 62 `father_name` values containing hedge tokens like `"X (probable)"`, `"X (per Baud)"`, `"X (?)"`, `"[X]"`
- 14 `mother_name` similar
- ~22 `spouse_names` items + ~20 `children_names` items with hedges
- ~20 rows embed `[N]` cross-references in name strings (`"Snḏm-jb Jntj [215]"`)

**Corpus convention check** (every other authority source for comparison):
- PM Theban: `occupant_name: str` (scalar). `co_occupants` is list-of-dict but `name` inside is scalar string — no per-name hedge typing.
- D&H queens: `father_name: str | None`, `spouse_names: list[str]` — scalar strings, no hedge typing.
- Leprohon: name lists are typed `[{transliteration, anglicised, source_note, ...}]` — already structured per-name.
- Beckerath: scalar name fields.
- Kitchen TIPE: scalar name fields.
- Ryholt SIP: scalar name fields.
- HKW 2006: scalar name fields (with `alt_names: list[str]` after #176).

So promoting Baud's parent fields to typed dicts would diverge from 6/8 corpus sources. Only Leprohon already uses dict-shape (because Leprohon's source distinguishes 8 name-types per king).

## Decision needed from user

**Two questions in priority order.**

1. **Family-2 scope: how deep to type the hedge encoding?**
   - (a) **Strict full restructure**: `father` / `mother` / `spouse` / `children` all become `list[{name, confidence, baud_id}]` dicts (or scalar dict for father/mother). ~215 row-fields restructured. Diverges from 6/8 corpus sources. Cleanest semantics; biggest migration.
   - (b) **Companion-field minimal**: keep scalar `father_name`, `mother_name`, `spouse_names`, `children_names` strings. Add typed `father_baud_id`, `mother_baud_id`, `spouse_baud_ids: list[str | None]`, `children_baud_ids: list[str | None]` companion fields (lift the `[N]` cross-references). Add `father_confidence: enum`, etc., as separate scalar enums. NO restructure of the name fields themselves; hedges stay in strings.
   - (c) **Defer Family 2 entirely**: ship Family 1 (joint-entry / collective-monument / lost-name / pm_refs / monuments list-promotion) in this PR. Open follow-up issue with explicit P1-carry-forward for Family 2. Same exception class as the original strict-policy escape clause we said NO to. **Per `feedback_schema_p1_merge_blockers.md` this is the wrong move; offered for completeness.**

2. **Monuments list shape (within Family 1):**
   - (x) `monuments: list[str]` — simple list of monument descriptions; lose per-document localisation (different sites for documents 1 / 2 of `baud-22`).
   - (y) `monuments: list[{document_id, monument, localisation}]` — structured per-document; captures per-document site. ~50 rows restructured. Cleanest; bigger migration.

## Recommendation

**My answers if forced to choose alone:**

- **Q1: Option (b)** — companion-field minimal. Keeps Baud's scalar name shape consistent with corpus convention; adds typed cross-refs and confidence enums as separate fields (same Rule-3 enforcement direction as Family 1 typed flags). Avoids the "Baud is special" divergence that Phase-A consumers will trip over. Only Leprohon's typed-name-dicts pattern would justify (a), and that's because Leprohon's source structurally distinguishes 8 name-types per king (Baud doesn't).

- **Q2: Option (y)** — structured monuments list. The per-document localisation IS load-bearing for chunks like `baud-22` (Saqqara vs Heliopolis); flattening loses information.

But the user gets to decide both. Q1 in particular touches ~215 row-fields and the answer determines whether this PR is ~600 or ~900+ lines.

## Resolution paths

- **Dismiss** (proceed with my recommended (b) + (y)): `rm .claude/revise-priors/1777791674-baud-178-hedge-typing-scope.md`
- **Resolve** (user picks (a) or (c) and any rule amendment lands first): edit any policy/scope docs as needed, then move marker to `resolved/`
