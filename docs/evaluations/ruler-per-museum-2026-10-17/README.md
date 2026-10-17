# Per-museum ruler test (2026-10-17)

**Status: approved, not yet run.** The project owner approved the decision rule
(`decision-rule.md`) on 2026-10-17, before any model judged any case.

## Question

For each museum: are its links to the authority's rulers right, and which rulers does it name
that the authority misses?

The earlier ruler tests (#337, #361, the 2026-10-16 re-registration) compared museum pairs against
plain-text matching, and only judged the cases where the two disagreed. Most pairs had too few
such cases to decide anything. The owner asked instead for each museum to be judged against the
authority directly (2026-10-17). Every link and every miss of every museum is reviewed; nothing is
sampled.

## What is reviewed

From the production link step's run on the frozen inputs (`results/run-manifest.json`), ruler
mentions only:

| Museum | Links (distinct text → ruler) | Their records | Misses (distinct texts) | Their records |
|---|---|---|---|---|
| Met | 107 | 8,869 | 99 | 319 |
| Brooklyn | 16 | 24 | 25 | 33 |
| Harvard | 3 | 3 | 0 | 0 |
| Cleveland | 13 | 76 | 3 | 3 |
| Walters | 35 | 62 | 34 | 49 |
| **Total** | **174** | | **161** | |

- **A link** is a mention text and the one ruler the authority resolved it to. The question: is
  that ruler the one the records name?
- **A miss** is a mention text the authority left unmatched, or ambiguous between several rulers.
  The question: do the records name one specific ruler with it, and which? A mention the
  extractor itself reads as a list, a range or a doubt is not a single ruler and is not reviewed.
- **20 decoys** among the link cases: a real link shown with a wrong ruler, another of the same
  name and a different regnal number (`build_queue.decoy_target`). The reviewers are not told
  decoys exist. If the review fails to reject more than 1 in 5 of them, the result is
  inconclusive. The decoys test that reviewers reject a wrong ruler of the same name; they do
  not test subtler errors (`decision-rule.md`). Four of them show Ramesses XI, and none shows a
  royal woman (whose labels carry no regnal number); neither is visible within one call.
- **Named rulers of misses are not reconciled.** Only whether a text names one ruler is
  reconciled. When both reviewers find one, the fix list gives both names as written.

Each case shows what reviewers need and nothing that hints at the answer: the museum, the mention
text, every distinct text of the fields that hold it with its record count and up to five record
URLs, and for a link the ruler's label and authority metadata. Case IDs and order are opaque.

## The rule

`decision-rule.md`, in short: any wrong link **fails** a museum; otherwise it **passes**. Links
the reviewers could not settle either way are reported and decide nothing, and misses never fail a
museum; they are the fix list.

## Protocol

As the 2026-10-16 registration: each case is one call of headless Claude Code (Claude Sonnet 5.5,
effort high, on the subscription), two independent reviewers, and a reconciler where they
disagree. Reviewers read pages with `open_page` in a real browser and cite only pages of the
citable sources that they opened and that loaded. Every call is stored complete and re-validated
from its events. Changes from that registration:

- **#384 fixed.** The runner starts one virtual display for the whole run and stops it when the
  run ends (also on SIGTERM), instead of one per call that outlived the call. A call in which
  every page open returned an error read nothing; it is no decision and is retried.
- **The Claude Code release is called by its installed path**, with auto-update off, so an update
  mid-run cannot change it (the 2026-10-16 run's case-021).
- **What happens when a call gives no answer is fixed in advance** (`decision-rule.md`, "Calls
  that give no answer"). A case with no valid answer in three tries is settled as unconfirmed,
  and the run goes on. A call that stopped the run can be set aside only through the committed
  ledger `set-asides.json`, never by moving files. The 2026-10-16 README asked for both.
- **The scorer and the decision rule are bound** by the population digest, like every file the
  review runs on, so neither can change after the cases are built.
- **New prompts** for the two questions (`prompts/*-v1.txt`), audited for answer leakage
  (`prompt-audit-2026-10-17.md`).

Before the run, `scripts/preflight_page_check.py` opens every record page the cases show (a sample
of 60 of the Met's), with the review's browser tool and no model. The run starts only once every
one has loaded (`results/preflight-page-check.json`).

## Frozen inputs

The 2026-10-16 registration's archives (#337's corpus of 2026-08-27; Cleveland's and the Walters'
raw tables as ingested on 2026-10-16), run through today's main by `scripts/make_run.py` twice,
under different hash seeds, with identical output. The queues are built by
`scripts/build_queue.py`; `results/review-population-digest.json` binds them, the answer key and
every file the review runs on.
