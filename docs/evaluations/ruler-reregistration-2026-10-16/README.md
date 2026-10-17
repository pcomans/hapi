# Ruler re-registration with Cleveland and the Walters (2026-10-16)

**Follows:** #361 ([`../ruler-reregistration-2026-10-15/`](../ruler-reregistration-2026-10-15/)),
which qualified rulers for Met–Brooklyn on four changed cases. This registration reuses #361's
review protocol and scripts (copies here). It changes only what is listed below.

**Status: run and scored, 2026-10-17: CONTINUE, rulers Met–Walters** (Result, below). The
project owner approved the decision rule (`decision-rule.md`) on 2026-10-16, before any model
judged any case.

## Question

Does the authority layer link museum records on rulers better than plain text? The judge is
#361's two-stage review and its decision rule, on a bigger population. Cleveland (#380) and the
Walters (#381) were added because #361's population was too small. The resolver was tuned on
neither museum's spellings.

## What changed from #361

1. **The population comes from production.**
   - #361 compared two arms computed by its own scripts (`compare_arms.py`, `extract_mentions.py`).
   - This registration reads both modes of the pipeline's authority-links step
     (`pipeline.enrich.link_files.write_run`, #338), the code that runs in production.
   - `scripts/make_run.py` runs that step twice on the frozen inputs, in two interpreters with
     different hash seeds, and requires identical output (`results/run-manifest.json`).
2. **Five museums, ten pairs.** The population definition is #361's (`derive_candidates`): for
   each pair, every shared ruler target of either mode that is
   - an authority-only gain,
   - a literal-only loss,
   - or a retained control.

   Every case is reviewed; nothing is sampled.
3. **#358's five-record cap is lifted.** Each museum side now shows every distinct text of the
   fields that hold its mentions (`record_texts`). Each text comes with its number of records
   and up to five of those records' URLs, chosen in a seeded order.
   - A homonym can no longer hide in a record no reviewer sees.
   - At most 20 distinct texts fall on one side.
   - The prompts say so (v7, prompt audit `prompt-audit-2026-10-16.md`).
4. **#358's other open items:**
   - **Item 8, runtime binding.** Each call records the runtime's lock file (`run_bindings`).
     - Its Claude Code release is checked from its init event, as before.
     - Every page it read in the local browser must report the runtime's Chromium build
       (`CHROMIUM_VERSION`). A call that read a page with another build decides nothing.
   - **Item 10, error pages served with status 200** ("Arachne | 404") are not loaded
     (`ERROR_PAGE_TITLE`, in `page_loaded`). The validator re-derives `loaded` with it. The
     browser tool uses the same test, so such a page is read again in Browserbase, like any page
     that does not load locally.
   - **Item 11, per-question citations.** A Stage 1 reviewer cites each of its two judgments
     separately (`same_entity_citations`, `useful_granularity_citations`; schema v4).
     - Any outcome other than insufficient_evidence needs a citation in its own list.
     - If any citable page the call opened loaded, every list must name one. The validator has
       required that since #337, and the v7 prompt now says so. Otherwise the validator would
       reject, and the runner re-draw, an answer the prompt allowed (local code review).
5. **Tuned-on records are counted apart.** #369's fixes were found on brooklyn-3634,
   met-566763 and brooklyn-3599. Cases that hold one are reviewed and scored, but left out of
   the registered verdict (`decision-rule.md`).
   - For the same reason, no scope starts qualified. #361's Met–Brooklyn result hung on a case
     the resolver was later tuned on. After this registration, the qualified ruler scopes are
     the ones it qualifies.
   - `QUALIFIED_SCOPES` in `pipeline/enrich/authority_links.py` kept #361's Met–Brooklyn until
     this result was applied, on purpose: `authority_links.py` is one of the files the frozen
     resolver versions digest, so editing it before the run would have voided the frozen run.
     The result's PR set the ruler scopes to this registration's (a test binds them).
6. **Citable sources.** Cleveland and the Walters, already citable, are now case museums, and the
   Walters' permanent-link host is added (`citable-sources.json`).
7. **New seeds** for the opaque orders, the reconciliation order and the preflight sample.

The system prompt is #361's bytes. The four prompts change only as items 3 and 4 need.

## What is frozen

- **Inputs:**
  - #337's corpus archive (`hapi-museum-corpus-2026-08-27`, the Met, Brooklyn and Harvard);
  - `hapi-added-museums-2026-10-16`, Cleveland's and the Walters' raw tables as ingested into
    Neon on 2026-10-16. Each table reproduces the `raw_sha256` of its committed profile
    (`docs/museum-sources/<museum>-profile/profile.json`).

  Both archives are pinned by SHA-256 in `scripts/make_run.py`. The second is written by
  `scripts/dump_added_museums.py`, the same bytes from the same tables, and kept in the
  project's private store (`dropbox/hapi-added-museums-2026-10-16/`). Both museums' data is CC0.
- **The run is bound to the archives.** The queue builder re-derives the run's input digest from
  them, and recounts the run's transitions, before it builds anything.
- **The code** is main at the merge of #381 plus this directory. The run's manifest records
  both modes' resolver versions, which digest every code and data file they read. The queue
  builder refuses to build unless this tree's code gives the same versions.
- **The review population** (`results/real-review-population-digest.json`), rulers only:

  | Pair | Authority-only gains | Literal-only losses | Retained controls |
  |---|---|---|---|
  | Met–Brooklyn | 2 | 1 | 12 |
  | Met–Harvard | 0 | 0 | 2 |
  | Brooklyn–Harvard | 0 | 0 | 2 |
  | Met–Cleveland | 2 | 0 | 11 |
  | Brooklyn–Cleveland | 0 | 0 | 5 |
  | Harvard–Cleveland | 0 | 0 | 1 |
  | Met–Walters | 7 | 4 | 22 |
  | Brooklyn–Walters | 1 | 0 | 6 |
  | Harvard–Walters | 0 | 0 | 2 |
  | Cleveland–Walters | 1 | 0 | 6 |

  That is 87 cases, 99 Stage 1 review units and 82 Stage 2 targets.
  - Two cases hold tuned-on records, both Met–Brooklyn: the Neferu loss and the Ahmes B control.
  - Only Met–Walters has enough changed cases for the rule to decide it.

## Review protocol

As #361. Each case gets:
- one call per reviewer through headless Claude Code (Claude Sonnet 5.5, effort high, on the
  subscription);
- two independent reviewers, and a reconciler where they disagree;
- pages read with `open_page` in a real browser, with Browserbase for the marked sources and as
  the fallback.

Only pages of citable sources that the call opened and that loaded count as citations. Every
call is stored complete and re-validated from its events.

Before the run, the preflight check (`scripts/preflight_page_check.py`) opens:
- the citable pages earlier runs tried;
- every Cleveland and Walters record page the queue shows;
- a sample of the other museums' record pages.

It uses the review tool and no model. Met–Walters, the one scope the rule can decide, depends
on the Walters' record pages, which sit behind Cloudflare. So the run starts only once every
Cleveland and Walters record page the queue shows has loaded in the preflight
(`results/preflight-page-check.json`, tested).

## Known limitations (disclosed)

- **Most changed cases are in one pair.** Met–Walters holds 11 of the 18 changed cases. Every
  other pair has at most 3, and Met–Brooklyn has 2 once its tuned-on case is left out, so it
  cannot qualify here and ends unevaluated.
- **The extractor reads hyphenated pairs of rulers as one name** ("Psametik I-Necho II",
  docs/museum-sources/walters.md).
  - In the authority mode no ruler matches such a name, so it is a missed link, never a wrong one.
  - The literal mode links it by its text.
  - It is left as it is, so the Walters stays untuned.
- **Royal women rest on a print book reviewers cannot open** (#361's limitation, unchanged).
- **A royal woman's family names can echo the record text.** A queen is picked partly because the
  record's kings are her family. Her Stage 2 target shows those family names, and with every
  distinct record text now shown, the record that names them is always visible beside her
  ("daughter of Painedjem I" next to `family_names: ["Pinudjem I"]`). This may push toward
  exact_identity. Controls and gains go through the same resolver (prompt audit, P3-a).
- **Hidden harness context.** Accepted as in #337 and #361.
- **Thinking is stored as Claude Code's summary.**
- **Walls are recognised by their titles.**
- **Surface text correlates with case type, and the sourcing burden is unequal** (#337 and
  #361, unchanged).

## Result (2026-10-17): CONTINUE, rulers Met–Walters

`results/real-adjudicated-score.json`, from `decision-rule.md` applied in code, on the 85 cases
that hold no tuned-on record:

| Step | Numbers | Outcome |
|---|---|---|
| Calibration | 1 of 68 retained controls uncertain or wrong (limit 20%) | passed |
| Safety | b = 0 of 13 authority gains | passed |
| Utility | ruler, Met–Walters: a 7, b 0, c 0, d 2, e 2, f 0 (a + e = 9 > d = 2; 11 decided) | qualifies |

Every other pair has at most 2 changed cases, too few to decide (`scope_dispositions`):

| Pair | a | d | e | Outcome |
|---|---|---|---|---|
| Met–Walters | 7 | 2 | 2 | qualified |
| Met–Brooklyn | 2 | 0 | 0 | unevaluated |
| Met–Cleveland | 2 | 0 | 0 | unevaluated |
| Brooklyn–Walters | 1 | 0 | 0 | unevaluated |
| Cleveland–Walters | 1 | 0 | 0 | unevaluated |
| the other five | 0 | 0 | 0 | unevaluated |

So `QUALIFIED_SCOPES["ruler"]` is Met–Walters alone. Met–Brooklyn, which #361 qualified, is
unevaluated.

**Met–Walters' eleven changed cases** (case IDs as in the private records):
- **Seven gains, all a.** The authority links the Walters' spellings to the Met's kings, and
  Stage 2 found each proposed king the exact identity:
  - Senusret I, II and III (`cluster-beckerath-12.02`, `-12.04`, `-12.05`; case-057, case-010,
    case-059), from the Walters' "Sesostris";
  - Amenhotep I (`-18.02`, case-087), from "Amenophis I";
  - Seti I and II (`-19.02`, `-19.06`; case-025, case-004), from "Sety";
  - Psamtik I (`-26.01`, case-076), from "Psammetichus I".
- **Two correct links lost (d).** Plain text joins "Ptolemy II Philadelphos" (case-002) and
  "Ptolemy III Euergetes I" (case-075) across the two museums; the authority gives them no
  shared target.
- **Two false links removed (e).** Plain text joins the title cues "a King Holding" (case-020)
  and "the King Slaying" (case-047), which name no ruler. The reviewers found each node joins
  different entities.

**The other changed cases** are all a: Met–Brooklyn case-019 and case-069; Met–Cleveland
case-039 and case-065; Brooklyn–Walters case-063; Cleveland–Walters case-086.

**Tuned-on cases** (sensitivity, decides nothing). The two cases left out are Met–Brooklyn's
Ahmes B control (judged correct) and its Neferu loss (case-038, judged d, as in #361). With them,
the rule gives the same verdict and adds Met–Brooklyn (a 2 against d 1, 3 decided):
`decision_rule_including_tuned_on_cases`.

**The calibration miss** is case-060, Met–Walters' Pepi II control (`cluster-beckerath-06.05`).
Stage 1 found too little evidence that the two sides are one king; Stage 2 judged the target
exact.

**Arm outcomes** (`adjudicated_arm_outcomes`, all 87 cases): the authority has 81 useful nodes
against the literal arm's 68.

### The run

- **Calls.** Stage 1: 198 reviewer calls plus one retry (reviewer B's first answer on
  review-unit-019 cited a non-citable page), and 5 reconciled. Stage 2: 164
  reviewer calls, 1 reconciled. Records are private, in
  `dropbox/hapi-ruler-reregistration-2026-10-16/review-run/`, and bound by
  `results/real-review-records.json`. The reason is #337's: they carry museum text verbatim.
- **Pages.** The page-load gate passed (`results/real-page-load-gate.json`): citable pages
  loaded at most 1.51 points from the overall rate in every class (limit 5).

### Two incidents, and a deviation from the registration

Both incidents hit Stage 2's one reconciled case, case-021 (Met–Walters, a retained control,
judged correct). Three reconciler calls were made on it. All three are kept and hashed in
`results/real-review-records.json`. Only the third sits in `stage-2/reconciler/`, so it is the
only one the scorer counts as a decision.

1. **Claude Code updated itself** from 2.1.299 to 2.1.302 between the Stage 2 reviewers and the
   reconciler.
   - The reconciler's first call ran on 2.1.302, and the validator rejected it
     (`stage-2/reconciler-rejected-runtime/`). A rejected call has no decision.
   - That call was also hit by incident 2: every page it tried to open failed.
   - The runner does not resume a stopped case. The owner chose to redo the call on the pinned
     2.1.299, which was still installed, with auto-update off.
2. **The browser's virtual displays leaked.** Each call starts its browser under `xvfb-run`,
   and the Xvfb it starts outlived the call.
   - By the reconciler's redo, 1,738 leaked displays had filled the container's process limit
     (2,048). They had piled up from every browser run in this container since 2026-10-13, this
     review's 371 calls among them. Chromium could then not start threads, and every page open
     failed.
   - **The second reconciler call** opened none of its 10 pages and answered
     insufficient_evidence. The frozen validator accepted it: with no page loaded, the prompt
     makes insufficient_evidence the only valid answer.
   - **The deviation.** Under the frozen runner, that answer was the reconciler's decision.
     Claude (the agent running the review) set it aside on 2026-10-17, after its answer was
     printed, and moved it to `stage-2/reconciler-rejected-browser/`. Claude then closed the
     orphaned displays and made a third call, under the owner's instruction to redo the call;
     the owner was not asked about this second set-aside.
     - The line drawn was "no page loaded". A call that loads nothing can only answer
       insufficient_evidence, so the line does not depend on what it answered.
   - **The third call** loaded 4 of 4 pages and decided exact_identity, agreeing with Stage 2
     reviewer B.
   - **Calls the leak hit and that were kept.** Stage 2 reviewer A's own call on case-021
     loaded 1 of 20 pages and answered insufficient_evidence. That split is why the case went
     to the reconciler. It loaded a page, so the line above does not reach it, and it stands as
     the protocol made it. Two other Stage 2 calls lost one page each (reviewer A on case-010
     and case-013: 5 of 6 and 3 of 4 loaded); both agreed with reviewer B. No Stage 1 call
     was hit.

**The deviation does not change the result.** Had the second call's answer stood, case-021
would be a calibration miss:
- calibration would be 2 of 68 (limit 20%);
- Met–Walters' a 7, d 2, e 2 is untouched, so the verdict and every scope's outcome stay the
  same (tested);
- the Stage 2 page-load gate would still pass, with the authority class's deviation at 3.17
  points instead of 1.51 (limit 5), and one deciding call without a loaded page.

The runner is frozen with this registration. A later protocol must stop the display with the
call, and record set-asides in a committed list the scorer reads, not in directory names.

### Reproducing the run

The frozen run and queues are rebuilt on the tree this registration was approved on, main at
#382's merge (68ecbc3). This result's PR edits `QUALIFIED_SCOPES` in `authority_links.py`, a
file the resolver versions digest, so on later trees the queue builder refuses the frozen run.
