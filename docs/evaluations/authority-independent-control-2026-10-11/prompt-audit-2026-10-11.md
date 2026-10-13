# Stage 1 reviewer prompt — leak audits (Rule 14), 2026-10-11

Audited by the `prompt-auditor` agent against the exact composed requests (system prompt,
parameters, user content for three real cases) before any model judged a case.

| Round | Prompt state | Verdict | Findings acted on |
|---|---|---|---|
| 1 | first v3 draft | PASS (no P0/P1) | P2-b "Treat insufficient evidence conservatively" biases against cases whose two sides use different strings; P2-c v3 had dropped the guard against consulting the evaluation's own materials; P3-a "any experimental arm or class" named the concept |
| 2 | P2-b/P2-c/P3-a fixed | PASS | P2-d the new sentence warned only against `different_entity`/`insufficient_evidence` (a soft push toward `same_entity`); P3-d it covered only the first question |
| 3 | neutral wording | PASS (no P0/P1/P2) | none |
| 4 | sourcing tightened after the first pilot (5-search cap exhausted; decisions from general knowledge) | **FAIL** (P2) | P2 "rest on an institutional source you cite or on the case evidence itself" let identical-string cases be settled from the strings while differing-string cases fell to `insufficient_evidence`, reintroducing string-match bias; P3 two different `insufficient_evidence` triggers |
| 5 | auditor's round-4 rewrite applied verbatim; single `insufficient_evidence` trigger; schema requires ≥1 `https` citation on every decision | PASS (no P0/P1/P2) | none |

Accepted residuals (disclosed in `README.md`): surface text correlates with case type and
cannot be removed (P2-a); JSON keys are printed sorted, so `brooklyn` precedes `met`
(P3-b, cosmetic); extractor-internal role names appear in the evidence (P3-c, shared by both
arms). The project owner approved the final wording on 2026-10-11.

Round 5 notes (P3):
sourcing is symmetric in the prompt, but a citation for a variant spelling is harder to find
than one for an identical string, so differing-string cases may draw more
`insufficient_evidence` (disclosed in `README.md`); "Judge this case only from its own
evidence" sits beside the web-research instruction (the system prompt permits search, so the
meaning is clear); the always-cite rule could invite a loosely related URL and nothing checks
that a URL is institutional — the pressure is equal for every case; "relied on" vs
"consulted" wording drift. The project owner approved the round-5 wording on 2026-10-11.

Post-audit cosmetic edits (2026-10-11, no re-audit; the project owner judged cosmetic
wording changes not to need one): "Judge this case only from its own evidence" → "Judge this
case on its own" (removes the tension with the web-research instruction), and the citation
sentence unified to "the institutional URLs you relied on. Always cite at least one, including
when you answer insufficient_evidence (then cite the sources you consulted)". Neither edit
names an outcome, arm, class or selection, or changes what any case type must provide.

Post-audit schema edit (2026-10-11, after the first mini-pilot attempt): the `citations`
pattern was widened from `^https://` to `^https?://`, because a reviewer cited the Perseus
Digital Library (Tufts), which serves `http://` only. The prompt asks for institutional URLs
and never named a scheme; the change is identical for every case and names no outcome.

## Rounds 6–8: shown records (2026-10-11)

The mini-pilot showed that the mention string alone can send a reviewer to the wrong record
(see `README.md`), so each side's evidence block gained `shown_records` (up to 5 records:
public URL and full field text, chosen in an opaque seeded order). This changed the case
evidence, so it was re-audited on freshly composed requests (cases 001, 014, 028).

| Round | Prompt state | Verdict | Findings acted on |
|---|---|---|---|
| 6 | `shown_records` added; "a museum's own record page is an institutional source you may cite" | **FAIL** (P2) | P2 the sourcing rule did not say whether field text and URLs are case evidence or sources; auditor's replacement applied; P3 "up to five" did not say the five are an arbitrary subset |
| 7 | round-6 replacement + "Do not rely on field_text without opening its record" | **FAIL** (P2) | P2 that sentence contradicted the artifact-evidence exception when a record page cannot be opened; fallback wording applied (field text usable only through an exception stating the record could not be opened); P3 "only a pointer" clause removed |
| 8 | fallback wording | PASS (no P0/P1/P2) | none |

Not applied: an optional round-6 suggestion that sameness "needs a source that connects"
the two sides. It would add an evidence bar likely to hit identical-string and
variant-spelling cases at different rates; the auditor agreed in round 7. Round 8 P3 notes:
field text gives some differing-string cases disambiguating context (e.g. both Hurbeit and
Horbeit records read "(Pharbaethos)") — real source text, disclosed in `README.md`; whether
a museum page opens may vary by museum site, which the fallback treats identically for
every case (noise, not class-linked bias).

## Round 9: web fetch (2026-10-11)

The project owner added `web_fetch_20260209` so the reviewer can open the shown record URLs.
Prompt changes: "public web search and web fetch" (system prompt); "Open these records with
web fetch" and "public web research (web search and web fetch)" (role prompt). Both web tools
block `wikidata.org`.

| Round | Prompt state | Verdict | Findings acted on |
|---|---|---|---|
| 9 | web fetch added | PASS on text; P2 gate | P2 gate: brooklynmuseum.org refuses fetches (HTTP 429), so a class that involves Brooklyn more often would get a weaker evidence path. Checked against the private answer key: a Brooklyn side appears in 14/15 authority-only gains (93%), 29/33 literal-only losses (88%) and 47/50 retained controls (94%), and always on the same side within a pair — class-neutral, so the gate passes and it is disclosed as a limitation. P3 the repository rule was convention only: `github.com` and `raw.githubusercontent.com` added to `blocked_domains` on both tools (the repository is public); the change only enforces an existing rule and is identical for every case, so it was not re-audited. Per-URL fetch outcomes are recorded (`web_fetches`). |

## Rounds 10–11: per-case reconciler and Stage 2 prompts (2026-10-12)

New prompts `stage-1-reconciler-v3.txt`, `stage-2-reviewer-v3.txt` and
`stage-2-reconciler-v3.txt`, audited on the exact composed requests: the three real Stage 1
reconciliation requests (units 023, 090, 092), three real Stage 2 requests (one ruler, two
sites) and a Stage 2 reconciler request with placeholder reviews (no Stage 2 review existed).
Class balance was checked against the private answer key (aggregate counts only).

| Round | Prompt state | Verdict | Findings acted on |
|---|---|---|---|
| 10 | first drafts | Stage 1 reconciler PASS; both Stage 2 prompts **FAIL** (P2) | P2 the exact-identity guidance listed only relations that are *not* exact identity. That one-sided push weighs on differing-string cases (where alias recognition decides) more than on identical-string ones; the auditor's symmetric definition was applied verbatim. P3 claim-statement IDs and a label count in a ruler target's metadata are builder internals, not checkable evidence (and the IDs invite searches for this repository); release now drops them. P3 the Stage 1 reconciler did not say agreed questions are settled; a sentence was added |
| 11 | round-10 fixes applied | **PASS** all three (no P0/P1/P2) | none |

Accepted residual (P3, disclosed in `README.md`): some Stage 2 targets recur across cases and
the class is uniform within each recurring target. No single request can see this (each case
is a separate call); it matters only when reading results, because a reviewer's knowledge of
one recurring target is confounded with class.

## v3 prompt bytes (the superseded 2026-10-12 run)

The v3 prompts that ran in the superseded run, by SHA-256. The Stage 1 reviewer
prompt is the round-9 text plus the post-audit cosmetic edits above, which the project owner
waived from re-audit; the other three are the round-11 text. The Stage 1 reviewer was audited
on requests composed for the API runtime; the harness runtime sends the same user content
(`compose_user_content`) and system prompt, without the API tool parameters. The
`prompt-auditor` runs were Claude Code subagents of the working session; their reports are
summarised in this file, not stored verbatim.

| Prompt | SHA-256 |
|---|---|
| `stage-1-reviewer-v3.txt` | `e9eda8a3b4a010f90c6206ae4a0476bdefbce38c7f6100c64104eab749c54bf3` |
| `stage-1-reconciler-v3.txt` | `91c4c701f5d4d5a213592a10abda4726db90619cb31637ac0c38ec0c57a7a1e2` |
| `stage-2-reviewer-v3.txt` | `e50e33ba0c0f1cf51c75674c2aafe88c8b2dd15ecb3ebb87dbfbd18e20c295a0` |
| `stage-2-reconciler-v3.txt` | `a8fafe930b5ab6fbdd280f6734354f8adb132bf00936d0b52c95a2313a3c3055` |

## Rounds 12–13: v4 prompts, opened pages only (2026-10-13)

In the v3 run the agents read pages with Claude Code's WebFetch, which cannot pass the
JavaScript "Security Checkpoint" (Vercel) in front of the Met and Brooklyn collection sites:
69% of Met and 96% of Brooklyn fetches got HTTP 429, so most judgments about those records
rested on search summaries or on the field text the case supplies. The project owner ruled
that a citation the agent could not access is not a citation. v4 replaces WebFetch with
`open_page` (`scripts/open_page_server.py`, a headless Chromium that passes the checkpoint),
counts as a citation only a page the call itself opened and that loaded, and removes the
artifact-evidence exception route and its schema field (`raw-response-contracts/*-case-v2`).
Audited on freshly composed requests (Stage 1 units 001 and 002, Stage 2 cases 001 and 003,
reconciler requests for Stage 1 unit 023 and Stage 2 case 001), with the system prompt
(`review-system-v3.txt`) and the rendered tool description.

| Round | Prompt state | Verdict | Findings acted on |
|---|---|---|---|
| 12 | first v4 drafts | PASS on leakage; **P2** in all four | P2 "Always cite at least one" beside "cite only pages that loaded" left no honest answer when no page loads, pushing toward a non-loaded citation; fixed with the auditor's wording (an outcome other than `insufficient_evidence` needs ≥1 citation; `insufficient_evidence` may cite nothing if no page loaded) and conditional `minItems` in the schemas; an uncited reconciler `insufficient_evidence` is labelled `reconciler_insufficient_evidence_without_source` in the consensus, not a cited override. P3 applied: cite by opened or final URL; "institutional source" restored; an error or checkpoint page is not a source. |
| 13 | round-12 fixes | **PASS** all four (no P0/P1/P2) | none |

Post-audit edit (no re-audit; identical for every case, names no outcome): the tool
description's `loaded` now reads "true only if status is 200 and the page is not a bot
checkpoint", matching the code (round-13 P3). Carried residual: builder-internal Stage 2
target metadata (`representation`), accepted in rounds 10–11. Gate (round-12 P3, Rule 14
round-9 check): the `open_page` loaded rate per museum and per case class is measured
against the private answer key, in aggregate, after the Stage 1 reviewers and before any
result is read; without the exception route an unloadable record forces
`insufficient_evidence`, which is class-neutral only if the loaded rate is.

## Audited prompt bytes

The v4 prompts that run, by SHA-256 (a test checks these against the files).

| Prompt | SHA-256 |
|---|---|
| `stage-1-reviewer-v4.txt` | `8c6a3d8dd4154203f493d1f9d00beaec23126a33aeeefb1f14b671cfbcbd2c2b` |
| `stage-1-reconciler-v4.txt` | `52ad6e48acf6b54214d2c3dfd72bb4e8bcd29515ce1363a054cd7859215a58e4` |
| `stage-2-reviewer-v4.txt` | `723a242914ecd6aeaf28d1f25efe74b5858ecff9d54dbc8cc72f2b3c1118b9ab` |
| `stage-2-reconciler-v4.txt` | `e6cd8dfb1aa7e4d5d733e239915f19bd5bd726f2c6df26a440fcd6fda9c2ec8d` |
