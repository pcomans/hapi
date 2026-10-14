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

## v4 prompt bytes (the superseded v4 run)

The v4 prompts that ran in the superseded v4 run, by SHA-256.

| Prompt | SHA-256 |
|---|---|
| `stage-1-reviewer-v4.txt` | `8c6a3d8dd4154203f493d1f9d00beaec23126a33aeeefb1f14b671cfbcbd2c2b` |
| `stage-1-reconciler-v4.txt` | `52ad6e48acf6b54214d2c3dfd72bb4e8bcd29515ce1363a054cd7859215a58e4` |
| `stage-2-reviewer-v4.txt` | `723a242914ecd6aeaf28d1f25efe74b5858ecff9d54dbc8cc72f2b3c1118b9ab` |
| `stage-2-reconciler-v4.txt` | `e6cd8dfb1aa7e4d5d733e239915f19bd5bd726f2c6df26a440fcd6fda9c2ec8d` |

## Rounds 14–15: v5, citable sources only (2026-10-13)

The project owner doubted that generic web pages are a scholarly basis for these judgments,
so v5 adds a committed allowlist of citable sources (`citable-sources.json`, vetted by the
egyptologist-reviewer agent), rendered into the composed user content after the role
prompt; replaces "Prefer official museum, iDAI, ... institutional sources" with the
allowlist rule; adds a sentence on coarse sources (the Egyptologist found UNESCO properties
and Pleiades places lump whole areas); and runs the browser headful and reads PDFs (tool
description changed). Audited on freshly composed requests (Stage 1 units 001 and 002,
Stage 2 cases 001 and 003, a reconciler request per stage with placeholder v5 reviews), the
system prompt `review-system-v4.txt` and the rendered tool description. The auditor's reports
are kept verbatim in `prompt-audit-reports-2026-10-13.md` (rounds 12–15).

| Round | Prompt state | Verdict | Findings acted on |
|---|---|---|---|
| 14 | first v5 drafts | allowlist block PASS (constant across cases; roles not rendered); all four prompts **FAIL** (P2) | P2 the coarse-source sentence cautioned only against concluding identity, a one-sided push that weighs on differing-string cases (which depend on alias-bearing gazetteers); the auditor's symmetric replacement applied verbatim. P3 applied: "loaded citable pages"; a source must have its final_url on the list (also enforced in code); "a record page of a listed museum"; system-prompt wording aligned. P3 checked: Stage 2 target `representation` is fixed by entity type and uniform across classes; ruler `source_ids` differ in 2 of 11 cases, one per class. Measured residual, not a prompt effect: rulers have no openable authority, so the page-load gate is stratified by entity type × class (rule committed before the run) and citations are reported by role. |
| 15 | round-14 fixes | **PASS** all four and the system prompt (no P0/P1/P2) | none |

Post-audit edits (the auditor's own round-15 P3 wording; identical for every case, names no
outcome): the prompts' citation sentence ends "by the URL you opened or its final_url, both
of which must belong to a citable source;", and the tool description says "Only a page with
loaded: true whose final_url belongs to a citable source may be cited."

## v5 audited bytes (the superseded v5 run)

The files of the v5 run, which stopped at its Stage 1 page-load gate, by SHA-256.

| File | SHA-256 |
|---|---|
| `stage-1-reviewer-v5.txt` | `000f60be5d3e64f739c5833c870a39309b3414125d02c4438a677d6c543cc1f8` |
| `stage-1-reconciler-v5.txt` | `ddc64e48f04c37c1c8f0173466f037bee055e3fdc4e7437349ed91ffb1f2d181` |
| `stage-2-reviewer-v5.txt` | `1e560d70a2046856f7b6eae01fb1b2fa784af4fe528f8a7e06f661824c65c198` |
| `stage-2-reconciler-v5.txt` | `7f1edf2b81d5443a03ecf4a9fa77cee579bdcba26d383e523e37388535fee9a8` |
| `review-system-v4.txt` | `290ab72e433d8cbbd167d4f906e874fee1d6994c38201bfe10d01e7cd3116451` |
| `citable-sources.json` | `8c0ad623c3e7ea395e675da022af30fcccaccf20cc32b8cb5729eab384e134da` |
| `open_page_server.py` | `1cf83e6530142e706329ec3ac86a01e627bf266b6d0b9377c916f92fa6be3115` |

## Round 16: v6, Trismegistos excluded, Browserbase routing (2026-10-13)

The v5 run's Stage 1 failed its page-load gate before any result was read (README). For v6,
Trismegistos was moved to the excluded sources (subscription; it blocked this project's IP),
and two sources a local browser cannot open (UCL Digital Egypt, PCMA) are read in a
Browserbase cloud browser. Model-visible changes: the citable block lost the Trismegistos
line; the tool description carries the round-15 wording; tool results gain `browser` and,
for Browserbase, an opaque session ID. Prompts and system prompt are byte-identical to
round 15.

| Round | State | Verdict | Findings acted on |
|---|---|---|---|
| 16 | v6 | **PASS** (no P0/P1/P2) | Trismegistos removal is a measured residual, not a prompt bias (fewer citable alias sources for differing-string site cases): the gate now reports citations by source per class. P3: opens are reported by browser, so a Browserbase effect is not read as a class effect. |

## v6 audited bytes (the stopped v6 run)

The files of the v6 run, stopped at a hash-copy failure in Stage 1, by SHA-256.

| File | SHA-256 |
|---|---|
| `stage-1-reviewer-v5.txt` | `000f60be5d3e64f739c5833c870a39309b3414125d02c4438a677d6c543cc1f8` |
| `stage-1-reconciler-v5.txt` | `ddc64e48f04c37c1c8f0173466f037bee055e3fdc4e7437349ed91ffb1f2d181` |
| `stage-2-reviewer-v5.txt` | `1e560d70a2046856f7b6eae01fb1b2fa784af4fe528f8a7e06f661824c65c198` |
| `stage-2-reconciler-v5.txt` | `7f1edf2b81d5443a03ecf4a9fa77cee579bdcba26d383e523e37388535fee9a8` |
| `review-system-v4.txt` | `290ab72e433d8cbbd167d4f906e874fee1d6994c38201bfe10d01e7cd3116451` |
| `citable-sources.json` | `62e59f2b1f5574bf6f1c88aeda117f7719044cf2686e359f5aa64ca97c8fd0cd` |
| `open_page_server.py` | `7bb3c9c888375d694d581bf95220e8f9369eda9d2e140d9fb70504cd06fd7643` |

## Round 17: v7, no evidence hash in the model input (2026-10-14)

In the v6 run reviewer A failed one unit three times only by miscopying the 64-character
evidence hash. The model input no longer contains `evidence_sha256` (`without_hashes`), the
response schemas (`*-case-v3`) no longer ask for it, and the prompts (`*-v6`) say "Copy the
case ID exactly." instead of "Copy the case ID and evidence hash exactly." That sentence is
the only difference from the v5 prompt files (which already carry the round-15 post-audit
wording on final URLs).

| Round | State | Verdict | Findings acted on |
|---|---|---|---|
| 17 | v7 | **PASS** (no P0/P1/P2) | none (P3: noted that the v5 files include the round-15 post-audit wording) |

## v7 audited bytes (the v7 run, superseded)

The files of the v7 run, superseded because its browser tool timed out on every iDAI
gazetteer place page, by SHA-256.

| File | SHA-256 |
|---|---|
| `stage-1-reviewer-v6.txt` | `e3d3b169a90ab33a2a36d0d7d22f229c469b1735c95c0e57ceafce2036fe1c7f` |
| `stage-1-reconciler-v6.txt` | `8190916efafc4b916409694462762a81e5baff63aec6c18e0d3f1357c594f21e` |
| `stage-2-reviewer-v6.txt` | `98a36059e79fb554c2218c42e08626e12d4f62b0ead6bd56c3be51abbdb3bdc4` |
| `stage-2-reconciler-v6.txt` | `d3a8ed2d74bf75796d8bc693c2f100280bad9e61b64d61c2900f16c8aff651bd` |
| `review-system-v4.txt` | `290ab72e433d8cbbd167d4f906e874fee1d6994c38201bfe10d01e7cd3116451` |
| `citable-sources.json` | `62e59f2b1f5574bf6f1c88aeda117f7719044cf2686e359f5aa64ca97c8fd0cd` |
| `open_page_server.py` | `7bb3c9c888375d694d581bf95220e8f9369eda9d2e140d9fb70504cd06fd7643` |

## Round 18: v8, pages whose `load` event never fires (2026-10-14)

In the v7 run every open of an iDAI gazetteer place page (the record each Stage 2 case asks
about) timed out: `open_page` waited for the `load` event, which an analytics script on those
pages (piwik.dainst.org) keeps from ever firing, although the record renders within seconds.
`open_page` now waits for `domcontentloaded`, then up to 15 seconds for `load`, and reports
`load_event`. Its tool description gained one clause about `load_event`; the prompts, system
prompt and citable-source list are unchanged.

| Round | State | Verdict | Findings acted on |
|---|---|---|---|
| 18 | v8 | **PASS** (no P0/P1/P2) | none (P3: tool errors echo the host and URL, as in v7) |

## v8 audited bytes (the stopped v8 run)

The files of the v8 run, stopped in Stage 1 when a reviewer cited a UEE article three times
(the eScholarship entry covered only the encyclopedia's table of contents), by SHA-256.

| File | SHA-256 |
|---|---|
| `stage-1-reviewer-v6.txt` | `e3d3b169a90ab33a2a36d0d7d22f229c469b1735c95c0e57ceafce2036fe1c7f` |
| `stage-1-reconciler-v6.txt` | `8190916efafc4b916409694462762a81e5baff63aec6c18e0d3f1357c594f21e` |
| `stage-2-reviewer-v6.txt` | `98a36059e79fb554c2218c42e08626e12d4f62b0ead6bd56c3be51abbdb3bdc4` |
| `stage-2-reconciler-v6.txt` | `d3a8ed2d74bf75796d8bc693c2f100280bad9e61b64d61c2900f16c8aff651bd` |
| `review-system-v4.txt` | `290ab72e433d8cbbd167d4f906e874fee1d6994c38201bfe10d01e7cd3116451` |
| `citable-sources.json` | `62e59f2b1f5574bf6f1c88aeda117f7719044cf2686e359f5aa64ca97c8fd0cd` |
| `open_page_server.py` | `c6665190c0ea78de7f755d37d5f8d33354c0880ee30aa3b4579a921f09c9d6ff` |

## Round 19: v9, all of eScholarship citable (2026-10-14)

The eScholarship entry's path prefix (`/uc/nelc_uee`) covered only the UCLA Encyclopedia of
Egyptology's table of contents: its articles live at `/uc/item/<id>` and `/content/qt<id>/`.
In the v8 run a reviewer cited a UEE article PDF in three attempts on one unit, which stops the
run. On the project owner's decision the entry is now all of escholarship.org, category
`open_repository` (as HAL). Nothing else in the model input changed.

| Round | State | Verdict | Findings acted on |
|---|---|---|---|
| 19 | v9 | **PASS** (no P0/P1/P2) | none (P3: non-UEE eScholarship working papers are now citable by domain) |

## Audited prompt bytes

The v9 prompts (`*-v6.txt`), system prompt, citable-source list and browser tool (whose
description is model input) that run, by SHA-256 (a test checks these against the files).

| File | SHA-256 |
|---|---|
| `stage-1-reviewer-v6.txt` | `e3d3b169a90ab33a2a36d0d7d22f229c469b1735c95c0e57ceafce2036fe1c7f` |
| `stage-1-reconciler-v6.txt` | `8190916efafc4b916409694462762a81e5baff63aec6c18e0d3f1357c594f21e` |
| `stage-2-reviewer-v6.txt` | `98a36059e79fb554c2218c42e08626e12d4f62b0ead6bd56c3be51abbdb3bdc4` |
| `stage-2-reconciler-v6.txt` | `d3a8ed2d74bf75796d8bc693c2f100280bad9e61b64d61c2900f16c8aff651bd` |
| `review-system-v4.txt` | `290ab72e433d8cbbd167d4f906e874fee1d6994c38201bfe10d01e7cd3116451` |
| `citable-sources.json` | `0fb13c7940a91b62aa50b8734682d921e222618dd43979aa582354f56552e3a7` |
| `open_page_server.py` | `c6665190c0ea78de7f755d37d5f8d33354c0880ee30aa3b4579a921f09c9d6ff` |
