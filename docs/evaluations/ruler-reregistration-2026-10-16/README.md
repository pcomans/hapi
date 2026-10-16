# Ruler re-registration with Cleveland and the Walters (2026-10-16)

**Follows:** #361 ([`../ruler-reregistration-2026-10-15/`](../ruler-reregistration-2026-10-15/)),
which qualified rulers for Met–Brooklyn on four changed cases. This registration reuses #361's
review protocol and scripts (copies here). It changes only what is listed below.

**Status: registered, not yet run.** The decision rule (`decision-rule.md`) awaits the project
owner's approval. No model judges any case before that.

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
   - **Item 8, runtime binding.** Each call records the runtime's lock file and Python
     (`run_bindings`).
     - Its Claude Code release is checked from its init event, as before.
     - Every page it read in the local browser must report the runtime's Chromium build
       (`CHROMIUM_VERSION`). A call that read a page with another build decides nothing.
   - **Item 10, error pages served with status 200** ("Arachne | 404") are not loaded
     (`ERROR_PAGE_TITLE`).
   - **Item 11, per-question citations.** A Stage 1 reviewer cites each of its two judgments
     separately (`same_entity_citations`, `useful_granularity_citations`; schema v4). Any
     outcome other than insufficient_evidence needs a citation in its own list.
5. **Tuned-on records are counted apart.** #369's fixes were found on brooklyn-3634,
   met-566763 and brooklyn-3599. Cases that hold one are reviewed and scored, but left out of
   the registered verdict (`decision-rule.md`).
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

  Both archives are pinned by SHA-256 in `scripts/make_run.py`.
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

It uses the review tool and no model.

## Known limitations (disclosed)

- **Most changed cases are in one pair.** Met–Walters holds 11 of the 18 changed cases. Every
  other pair has at most 3, and Met–Brooklyn has 2 once its tuned-on case is left out.
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
