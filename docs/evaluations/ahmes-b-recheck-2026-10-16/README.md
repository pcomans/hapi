# A check of the one unreviewed Met–Brooklyn ruler link (2026-10-16)

**Result: the review found the link right, with moderate confidence.** In Met–Brooklyn, the
pipeline's ruler connections are #361's reviewed population plus one shared target #369 added:
Dodson & Hilton's Ahmes B (#376). Ahmes B joins three records, met-566763, met-547683 and
brooklyn-3634.
- **Stage 1.** Reviewed with #361's protocol, both reviewers found the three records to be one
  woman.
- **Stage 2.** The reconciler decided she is Ahmes B, a cited override of one reviewer's
  "insufficient evidence". No page any call could open shows Dodson & Hilton's own "Ahmes B"
  entry, so the identity rests on the target's family names (wife of Thutmose I, mother of
  Hatshepsut). Those fit only one Ahmose the reviewers found.

**This is a check, not evidence.** #369's fix was found on these records, which were #361's
deciding case-016. So this check says the link is correct, but it does not count toward the
scope's qualification, which rests on #361's review (owner, 2026-10-16). A next registration
must still flag these records as tuned-on (#358).

## What was reviewed

The case was built by `scripts/build_queues.py` with #361's case-building helpers
(`arm_node`, `review_unit_evidence`, `released_stage_2_case`), on the pipeline's links from the
frozen corpus (run `f13f590d…`, #376's). Its checks:
- a target-name guard on Stage 1, and the prompt auditor's reading of both queues;
- #361's Stage 2 forbidden-key scan;
- #361's `verify_consensus` on the Stage 1 consensus before Stage 2 is released.

The last two were added after the run, at review. For the run itself, `verify` proves the order:
the reviewed Stage 2 queue embeds the frozen Stage 1 consensus's hash, and it is exactly the
queue released from it. #361's Stage 1 blinding check is not run.

- **Stage 1** shows the three records' titles and links, with no target. The case ID is opaque,
  and the builder refuses a Stage 1 queue that contains the target's ID or name.
- **Stage 2** shows Ahmes B as #361 showed a royal woman: label, dynasty 18, family names
  (Thutmose I, Hatshepsut), and the source.
- The prompt auditor checked the case for answer leakage (Rule 14). It caught a case ID that
  named the target, which was then made opaque. The prompts, runner and model
  (`claude-sonnet-5-5`, on the subscription harness) are #361's, unchanged.

## Outcome (`results/check.json`)

| Stage | Question | Reviewer A | Reviewer B | Decided |
|---|---|---|---|---|
| 1 | Same entity? | same | same | same entity (agreement) |
| 1 | Useful granularity? | useful | useful | useful (agreement) |
| 2 | Is it Ahmes B? | insufficient evidence | exact identity | exact identity (the reconciler's cited override) |

- **Reviewer A** found the records to be Queen Ahmose, chief wife of Thutmose I and mother of
  Hatshepsut. It held back only because no citable page shows Dodson & Hilton's own "Ahmes B"
  entry: the book is print-only, a limit #361 disclosed for every royal-woman target.
- **The reconciler** cited the three museum pages and the Theban Mapping Project.
  - The only other royal Ahmose it found, Princess Ahmose (a daughter of Seqenenre Tao, QV 47),
    is not linked to Thutmose I or Hatshepsut. So the target's family fits only Hatshepsut's
    mother.
  - It rated its confidence as moderate, for the same print-only reason.

Every call's full record (command, prompt, event log and answer) is kept privately, as #361's
are, in `dropbox/hapi-ahmes-b-recheck-2026-10-16/`, for #361's reason: they quote museum text
verbatim. Their SHA-256 hashes are in `results/check.json` (Rule 13).

With the private records, `scripts/build_queues.py verify` (with the private dir, the frozen
corpus and #361's two queues) checks everything `check.json` publishes:
- the two template queues are #361's own, by the hashes #361 committed for them;
- `check.json` covers both stages, and both consensus files rebuild from the stored calls
  (#361's `verify_consensus`);
- every hash matches;
- the outcomes and resolutions (method, reviewer outcomes, citations) are the consensus's;
- the target, run and records are the private binding's, and the reviewed Stage 1 queue and
  that binding are exactly what the script builds from the frozen corpus (`--archive`);
- the reviewed Stage 2 queue binds the frozen Stage 1 queue and consensus, and is their release.

It passed on 2026-10-16.
