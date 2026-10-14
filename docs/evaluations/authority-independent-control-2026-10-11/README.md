# Authority-independent control — re-registration (2026-10-11)

**Issue:** [#337](https://github.com/pcomans/hapi/issues/337) · **Supersedes for new work:**
[`../authority-independent-control-2026-09-13/`](../authority-independent-control-2026-09-13/),
which stays frozen as the original registration and is not edited.

## Why re-register

The original registration froze the claim graph as it was on 2026-09-13. Issue #342 has since
rebuilt it (ambiguous ruler mentions on the same ledger: 5,037 → 689). Testing the frozen graph
would mostly re-measure gaps that are already fixed, so the project owner chose to re-register
against the current graph (2026-10-11). The original's exploratory 2026-09-14 outputs were
invalid and are not used. The decision rule (`decision-rule.md`) was chosen and committed
after those outputs existed, so it is disclosed as a **prospective decision rule**, not a
pristine pre-registration.

## What is frozen

- **Base commit** `1d35337ff5b5185f1c620d04d58ede939b27f5af`, with the resolver inputs pinned
  by SHA-256 in `scripts/compare_arms.py` (`CURRENT_INPUTS`): the post-#342 claim graph, the
  normalizer, the linkability resolver, the iDAI and Porter–Moss sources.
- **The same corpus and mention ledger** as the original (148,871 mentions; ledger SHA-256s
  identical to the 2026-09-13 run).
- **Two independent runs** of both arms and the review queue: every registered output
  byte-identical (`results/real-rerun-proof.json`).
- **The review population:** 98 cases (15 authority-only gains, 33 literal-only losses,
  50 retained controls), 108 Stage 1 review units (`results/real-review-population-digest.json`).
- **The decision rule:** `decision-rule.md`, approved before any model judged any case.

Deterministic headline (before review): shared records on any two-museum shared node —
literal arm Met 27,330 / Brooklyn 2,894 / Harvard 534; authority arm Met 14,502 /
Brooklyn 1,156 / Harvard 8 (`results/real-run-report.json`).

## Result (2026-10-14, protocol v10): CONTINUE, sites only, all three museum pairs

`results/real-adjudicated-score.json`, from `decision-rule.md` applied in code:

| Step | Numbers | Outcome |
|---|---|---|
| Calibration | 3 of 50 retained controls uncertain or wrong (6%, limit 20%) | passed |
| Safety | b = 0 of 13 authority gains labelled a/b/c | passed |
| Utility | scopes below | 3 qualify |

| Scope | a | b | c | d | e | f | Qualifies |
|---|---|---|---|---|---|---|---|
| site, Met–Brooklyn | 9 | 0 | 0 | 10 | 10 | 1 | yes (a + e = 19 > d = 10) |
| site, Met–Harvard | 1 | 0 | 0 | 1 | 3 | 0 | yes (4 > 1) |
| site, Brooklyn–Harvard | 1 | 0 | 0 | 1 | 2 | 0 | yes (3 > 1) |
| ruler, Met–Brooklyn | 2 | 0 | 0 | 5 | 1 | 1 | no (3 < 5) |

Reading it:
- **Every judgment rests on pages the reviewer actually read.** The agents opened pages in a
  real browser, and only a page the call itself opened, that loaded, and that belongs to a
  citable source counts as a citation. Museum record pages loaded 802 of 802 times in Stage 1
  and 397 of 398 in Stage 2 (3 and 1 of them only when read again in Browserbase after the
  local browser timed out); the iDAI gazetteer records the Stage 2 site cases ask about
  loaded 112 of 112 times. Every class's loaded rate for citable pages is within 5 points of
  its entity type's rate in both stages (largest gap: ruler authority gains in Stage 2, 4.7
  points below; `results/real-page-load-gate.json`, the Rule 14 gate. It was measured before
  any result was read and passed; the committed file is its recomputation under the rules
  tightened on review, see "Reconciliation, Stage 2 and scoring"). All 346 deciding reviewer calls loaded at least one page.
- **What the Stage 2 citations rest on:** 385 cite the case's own museum records, 105 the
  target's iDAI gazetteer record, 65 an independent source (Pleiades 37, the Griffith
  Institute 12, UCL's Digital Egypt 4, and others).
- **One false merge is scored as uncertain.** Case-067 (ruler, Met–Brooklyn, an authority
  gain): both Stage 1 reviewers found the two sides are different rulers, and Stage 2 found
  the target is not their identity. Granularity has nothing to judge for two different
  entities, so it was settled as `insufficient_evidence`, and the frozen classifier
  (`classify_case`, which `decision-rule.md` names) checks uncertainty first and requires
  `useful` for b: the case is labelled f, not b. The label is left as frozen. **Counted as
  b, the verdict is unchanged:** b = 1 is under 2 and is 1 of 13 gains (8%, limit 10%); it
  makes the ruler Met–Brooklyn scope unsafe, which does not qualify anyway. The other f
  (case-011, a site gain) is a real ambiguity: the Brooklyn records give only a hedged
  "Qurnah", the Met records "Sheikh Abd el-Qurna" (a specific hill), and Polz's encyclopedia
  entry, which both reviewers opened, shows "Qurna" has named the hill, the necropolis area
  around the Sety I temple and the modern village.
- **The authority arm still loses correct matches.** 17 literal-only losses were correct,
  useful connections plain text makes (d), against 16 that were wrong or not useful (e).
  For sites in all three museum pairs, the gains plus the bad links it removes outweigh the
  good links it loses; for rulers they do not (5 lost against 3).
- **The Harvard pairs qualify narrowly** (Met–Harvard 5 changed cases, Brooklyn–Harvard 4),
  so treat them as weak. Both moved from v4 on one judgment each: the plain-text "Fayum" link
  (case-094, Met–Harvard; case-012, Brooklyn–Harvard), which both reviewers now judged the
  same place but too broad to be useful, citing Pleiades' entry for the Fayum as a whole
  region of many sites (in v4 they had judged it useful). That makes those two losses e, not
  d, and is what lets Brooklyn–Harvard qualify.
- **One control is unstable across runs.** Case-088 (a site control, Met–Brooklyn) was
  "useful but wrong identity" in v3, "same, useful, exact target" in v4, and is now
  uncertain: the two Stage 2 reviewers disagreed, and the reconciler found that Brooklyn's
  "Leontopolis" records mix two Delta sites (one reads "Leontopolis (Tell el Muqdam)", others
  Tell el-Yahudiya, the target), so the museum-side evidence does not denote exactly the
  target. This is a mixed-evidence case, not a reviewer error.
- The counts are a finite census of the selected review population, not a sample estimate.

Review: Stage 1, 108 units, two reviewers agreeing on both questions in 107 (1 reconciled
with a cited override); Stage 2, 65 proposed targets, agreeing in 62 (3 reconciled). Every
reviewer and reconciler call was valid on its first attempt; no call hit a session limit, and
no `open_page` call failed. In the deciding reviewer calls, Browserbase served 13 Stage 1 and
7 Stage 2 page opens (15 loaded): 14 for the sources routed there, 6 read again after the local
browser failed (4 museum record pages that timed out locally, all loaded; an IFAO page and an
MFA Boston page that failed in both). The gate result counts these retries by class and host. All calls ran through
Claude Code (Claude Sonnet 5.5) on the subscription; the records are private
(`dropbox/hapi-337-review-v10-2026-10-14/`), bound by the hashes in the score.

**Superseded runs** (all on the same frozen population: the 108 Stage 1 units and the private
answer key are byte-identical in every run). Each was stopped or superseded for a defect in
how pages were read or which sources counted, never for its result; the records of v5 to v9
were never read beyond the page-load counts.
- **v3** (2026-10-12): pages read with Claude Code's WebFetch, which the Met and Brooklyn sites
  refuse, so most judgments rested on search summaries or the case's own field text. Same
  verdict and primary counts as v4; private (`dropbox/hapi-337-review-2026-10-11/`).
- **v4** (2026-10-13): pages read in a headless browser, any loaded page citable. CONTINUE,
  site Met–Brooklyn and Met–Harvard; a 13, b 0, c 0, d 19, e 14, f 2; calibration 2 of 50. Its
  score is in the Git history of `results/real-adjudicated-score.json`.
- **v5**: only listed scholarly sources citable, headful browser. Stage 1 failed the page-load
  gate (Trismegistos and UCL's Digital Egypt walled).
- **v6**: Browserbase for Digital Egypt and PCMA, Trismegistos excluded. Stopped when a
  reviewer miscopied the evidence hash three times on one unit.
- **v7**: the hash left out of the model input. Passed the gate, but `open_page` timed out on
  every iDAI gazetteer place page, the record each Stage 2 case asks about.
- **v8**: that fixed. Stopped when a reviewer cited a UCLA Encyclopedia of Egyptology article
  in three attempts, which the allowlist's path did not cover.
- **v9**: all of eScholarship citable. Stage 1 failed the page-load gate (site authority gains
  7.3 points below the site rate), mostly from `open_page` errors on Heidelberg pages.

## Review protocol

Every role (Stage 1 and Stage 2 reviewer and reconciler) answers **one case per call** through
headless Claude Code (`scripts/run_harness_review.py --role ...`; shared rules in
`scripts/review_protocol.py`). The Anthropic API credit ran out during the mini-pilot, and on
the project owner's decision every scored call runs on the Claude Code subscription.

- **Call setup.** Claude Sonnet 5.5 (`--model sonnet`, served model checked as
  `claude-sonnet-5-5`), effort `high`, the review system prompt
  (`launcher-instructions/review-system-v4.txt`), exactly two tools: WebSearch, to find pages,
  and `open_page`, to read them, served by the one MCP server (`scripts/open_page_server.py`),
  no API key (auth checked as the subscription), each case in a fresh empty directory. The
  driver refuses any other setup. Two independent reviewers are two separate runs. User-level plugins and a SessionStart hook still load; every stored call is checked to
  have had no hook output.
- **The record** of each call is its full stream-json event log, with the exact command,
  system prompt and user content, and the SHA-256 of the runner and the browser server that
  made it (`run_bindings`; a stored call made by other files is refused). Per Constitutional
  Rule 13 (revised 2026-10-11) an LLM call
  cannot be re-executed to reproduce a decision; the record is what is re-read, and every
  validation is re-derived from the stored events.
- **Runtime.** The runner and the browser server run from `runtime/.venv`, synced from
  `runtime/uv.lock`: the pipeline's dependencies plus `mcp` 2.3.0, the MCP SDK (with
  `playwright` 1.58.0, `pypdf` 6.10.2 and `jsonschema` 4.26.0). That lock is kept here, not in
  `pipeline/`, because the site-graph-v0 pre-registration pins `pipeline/uv.lock` byte for
  byte. The browser runs headful on a virtual display, so the system needs `xvfb-run`
  (Debian package `xvfb`) and Chromium's libraries. To run again: `uv sync --locked
  --all-groups --project runtime`, `runtime/.venv/bin/python -m playwright install chromium`,
  then run `scripts/run_harness_review.py` with `runtime/.venv/bin/python` (the browser server
  starts with the same interpreter under `xvfb-run`), with `BROWSERBASE_API_KEY` in the
  environment (the browser server reads it there; it is never on the recorded command). The
  superseded v4 run used `pipeline/.venv` synced from the same lock.
- **Pages are read in a real browser** (protocol v4, 2026-10-13; headful from v5).
  `open_page` loads a URL in Chromium, headful on a virtual display, and returns the HTTP
  status of the final document, the final URL, the title, whether it loaded and the visible
  text (up to 40,000 characters); a PDF is read with pypdf. All of it is stored in the call's
  event log. It paces opens to one every 2 seconds per host, also across parallel calls (a
  Browserbase re-read of a page that failed locally follows at once), and
  refuses blocked domains, before and after redirects. The validator re-derives `loaded` from
  the stored status, title and text: status 200, text to read, and no wall title (Vercel and
  Cloudflare checkpoints, Anubis's "Oh noes!", a captcha page). Claude Code's WebFetch, used in the v3 run,
  is a plain HTTP request: the Met and Brooklyn collection sites put a JavaScript "Security
  Checkpoint" (Vercel) in front of every page, which answered 69% of Met and 96% of Brooklyn
  fetches with HTTP 429, whatever the user agent; a real browser passes it. A headless one is
  still refused by the Anubis and Cloudflare walls in front of Pleiades, UNESCO, the Theban
  Mapping Project and others (3 of 58 walled pages of the v4 run loaded headless, 36 headful).
  Still walled even headful: UCL's Digital Egypt and Trismegistos (Cloudflare). The browser
  does not disguise itself to get past a wall a site puts up against automated readers.
- **Pages that never finish loading** (protocol v8, 2026-10-14). `open_page` waits for the
  HTML to be parsed, then up to 15 seconds for the `load` event, and records whether it fired
  (`load_event`). Until v7 it waited for `load` itself, which the iDAI gazetteer's place pages
  never reach (an analytics script, piwik.dainst.org, never arrives, although the record has
  rendered within seconds): in the v7 run all 337 opens of those pages, the record each
  Stage 2 case asks about, timed out. v7 passed its page-load gate, because the failure hit
  every class alike; it was superseded before any result was read (records private and unread,
  `dropbox/hapi-337-review-v7-2026-10-14/`), and the gate now also reports opens by citation
  role, where a target record that will not load shows.
- **Pages that navigate on** (protocol v10, 2026-10-14). Heidelberg's Propylaeum pages move on
  right after their HTML is parsed (an Anubis challenge passing, a redirect to the PDF), and
  reading the title at that moment raised, so every such open failed with a tool error; these
  were counted as a wall until v9. A title read now survives one such navigation, and a PDF
  reached that way is read as a PDF; the page text is still read without that guard, and a
  page that navigates again after it raises. Parallel first opens no longer each launch a
  browser.
- **Browserbase for the sources that need it** (protocol v6, 2026-10-13). The v5 run's
  Stage 1 failed its pre-registered page-load gate before any result was read: in site
  authority-gain units, opens of citable sources loaded 9.7 points below the site rate,
  because Trismegistos (34 failed opens) and UCL's Digital Egypt (14) refused the agents'
  browser. A Browserbase cloud browser session read 5 of 5 Digital Egypt pages and the PCMA
  page our browser could not; it did not help with Heidelberg's Propylaeum (Anubis) or IFAO
  (HTTP 503 on every page). On the project owner's choice, Browserbase is used only for the
  sources that need it: those marked `"browser": "browserbase"` in `citable-sources.json`
  (Digital Egypt, PCMA) go there directly, and from v10 any other page that does not load in
  the local browser (an error, a wall, an empty page; not a 404 or 410) is read again there,
  the page record keeping why the local read failed (`local_failure`; lost if the re-read
  itself raises, see the limitations). Each such page is read
  in its own session, one at a time per call, released when read; its ID is in the page
  record, for the session's replay on Browserbase. Trismegistos sells full access by institutional
  subscription and blocked this project's IP after the v5 run's attempts, so it was moved to
  the excluded sources before the v6 run, until access is agreed with KU Leuven. The v5
  records stay private and unread (`dropbox/hapi-337-review-v5-2026-10-13/`).
- **Prompts.** Per-case prompts and schemas: `prompts/stage-1-reviewer-v6.txt`,
  `stage-1-reconciler-v6.txt`, `stage-2-reviewer-v6.txt`, `stage-2-reconciler-v6.txt`;
  `raw-response-contracts/*-case-v3.schema.json`. All leak-audited before use (Rule 14;
  `prompt-audit-2026-10-11.md`, rounds 14–20, whose audited SHA-256s of the prompts, the
  system prompt, the citable-source list and the browser tool are checked by a test).
- **Only scholarly sources are citable** (protocol v5, 2026-10-13). On the project owner's
  doubt that generic web pages are a scholarly basis, a citation must be a page of a source
  in `citable-sources.json`: museum collections, scholarly gazetteers, Egyptological research
  projects, scholarly publications, institutional open archives (for published work) and
  heritage authorities, matched by host and, for a source inside a broad host (UCL's Digital
  Egypt), by path. Until v8 the UCLA Encyclopedia of Egyptology was matched by the path
  `escholarship.org/uc/nelc_uee`, which is only its table of contents (its articles live at
  `/uc/item/<id>` and `/content/qt<id>/`); in the v8 run a reviewer cited a UEE article in
  three attempts on one unit, which stops the run, and from v9, on the project owner's
  decision, all of eScholarship (UC's open archive) is citable, as HAL is. The list states its criteria, names
  each institution, and lists excluded examples with reasons (Wikipedia, Britannica, GeoNames,
  pharaoh.se, private sites, self-upload sites, library authority files, and, from v6,
  Trismegistos). It was drawn up after
  the v4 run, informed by the hosts its reviewers opened, vetted by the egyptologist-reviewer
  agent and committed before any model ran on it; the composed model input lists it. Any
  other page may help a reviewer find sources but is never a citation. Each source has a role
  for reporting: `case_input` (the case's own museums, which show what the evidence says),
  `target_record` (iDAI, the source of the Stage 2 site targets, which shows what the target
  is) or `independent`; `results/real-page-load-gate.json` counts citations by role. The
  standard print references for ruler identity (Beckerath, Leprohon, Hornung et al.) have no
  openable page, so ruler judgments rest on museum records and open sources only.
- **A citation is a page the call opened and that loaded.** Nothing else is a source: not a
  search result, not a URL the case shows, not a page a review cites, not general knowledge
  (project owner, 2026-10-13: "a citation that can't access the data is not a citation").
  The validator matches every citation (host without `www.`, path and query; scheme and a
  trailing slash ignored) against the call's own loaded `open_page` results, under the
  requested or final URL (a redirect's requested URL reaches the page the call read), and both
  the cited URL and the final URL must belong to a citable source. A call citing anything
  else fails and is retried. Whether the two sides' strings match or differ is never
  by itself a basis for a judgment, and the case's field text is never a basis on its own.
  Every outcome other than `insufficient_evidence` needs at least one citation;
  `insufficient_evidence` may cite nothing only when no citable page loaded. No citation may point at a
  blocked domain.
- **Each side shows up to 5 of its records** (`shown_records`): the museum's public record
  URL, taken from the frozen corpus's canonical `source_url`, and the full text of each field
  that holds a mention, chosen in an opaque seeded order over record IDs. The original
  registration showed only the mention strings. In the mini-pilot both reviewers then took a
  title-field "Horemheb" for "Stela of Lady Horemheb" (a private woman). The ledger record is
  "Fragment of a Statue of King Horemheb", so one reviewer answered `different_entity` on a
  real match. Adding the records changes no case membership, case ID or other evidence field.
- **The model never sees the evidence hash** (protocol v7, 2026-10-14). A case's
  `evidence_sha256` binds it to the frozen population in the records, queues and score; it is
  left out of the model input, and an answer echoes only the case ID. In the v6 run reviewer
  A failed one unit three times only by miscopying the 64-character hash (a trailing "dd"
  written as "d"), which the retry cap turns into a stop; on the project owner's decision the
  v6 run was stopped there (its Stage 1 records stay private and unread,
  `dropbox/hapi-337-review-v6-2026-10-14/`) and the whole review re-run under v7.
- **Pages are checked before a run** (from v10). `scripts/preflight_page_check.py` opens,
  with the current `open_page` and no model, every citable page that failed to load in earlier
  runs' records and up to 3 per host that loaded (the iDAI gazetteer's 183 failed place pages
  sampled to 20). Run over the v5 to v9 records, with the v10 tool, on 2026-10-14
  (`results/preflight-page-check.json`, schema /1, which does not yet record the hashes of the
  tool, list and script that made it, as the script now does; it was first run before the v10 run, when Browserbase
  refused sessions for lack of credit, and re-run in full after the v10 run): of 184 pages, 132
  loaded (11 UCL Digital Egypt pages in Browserbase, 3 UNESCO pages only on the Browserbase
  re-read), 34 do not exist (HTTP 404), and 18 did not load: PCMA 7 (a CAPTCHA, in Browserbase
  too), IFAO 3 (HTTP 503), the iDAI gazetteer's search and `http://` pages 2 ("Application
  Blocked"), 2 Griffith Institute PDFs (whole Topographical Bibliography volumes, not fetched
  within 45 seconds) and a Heidelberg PDF link with a `#page=` fragment (timeout), an eScholarship item page (HTTP 202 with no text; its PDF loads), and 2 pages on
  a retired iDAI host name.
- **Fail loud.** Billed auth, another tool or MCP server, hook output, or another served
  model stops the run, and such a case is not resumed automatically. An answer rejected for
  its format (not JSON, schema-invalid, miscopied case ID, a reconciler resolving
  other than the disputed questions), an answer citing a page the call did not open or a
  non-citable source, or a
  call whose search results, opened pages or citations touched Wikidata or GitHub (Claude
  Code's search cannot exclude them), is retried, up to 3 such calls per case.
- **One call is one review.** Every deciding reviewer call must be its own Claude Code
  session (its init event's `session_id`); a stored call copied under both labels, or under
  two cases, fails loud rather than counting as agreement.
- **Attempts.** Every call is kept as `<case>.attempt-<n>.json` and never overwritten. The
  answer is the JSON object that ends the final message; a note on its own line before it is
  kept, not parsed. When a later rule changes a stored call's verdict, the call is re-checked
  from its saved events, with no new model call, and the re-check is kept as a new attempt
  naming its source call (its events must equal the source's). A case's decision is its one
  valid call.
- **Session limits.** A Claude Code session limit stops the run, which resumes after the
  reset. A call in which the session limit refused any tool call is a session-limit stop too,
  not a decision, because its research was cut short for a reason unrelated to the case
  (added 2026-10-12 during the superseded v3 run, where it voided two calls; no run since hit a
  session limit).

Pilot runtimes, not used for any scored call (removed; see the Git history of this
directory): the Anthropic API reviewer (`run_claude_review.py`, web search and web fetch with
`blocked_domains`), used until the credit ran out; and a DeepSeek V4 Pro / V4.1 Flash trial
through the Vercel AI Gateway (`run_gateway_review.py`), rejected because 4 of 5 calls ended
with the model's tool call emitted as text.

## Reconciliation, Stage 2 and scoring (2026-10-12)

The whole-queue reconciler and Stage 2 of the original design were replaced by the same
per-case pattern.

1. **Stage 1 consensus.** A question both reviewers answer identically is settled by that
   agreement. Each case with a disputed question goes to the reconciler, which sees the case,
   both reviews under opaque labels in a seeded-hash order, and the disputed questions, and
   must settle each one with at least one cited source (`prepare-reconciliation`). The
   consensus (`freeze-consensus`) is written once and accepted only if it is exactly what the
   protocol rebuilds from the stored records: every attempt is re-checked from its saved
   events, each case must have exactly one valid call per role, and each record must have
   been composed from the current prompt, schema and case.
   The override must cite at least one page the reconciler itself opened; a reconciler that
   answers `insufficient_evidence` because no page loaded may cite nothing, and that
   resolution is labelled `reconciler_insufficient_evidence_without_source`, not a cited
   override.
2. **Stage 2 release.** `build_review_queue.py release-stage-2` releases the 65 proposed-target
   cases only after verifying the frozen Stage 1 consensus, and binds its hash. The scorer
   rebuilds the release from the digest-bound custodian and requires the reviewed queue to be
   exactly it, so no target label or metadata can change after release.
3. **Stage 2** runs the same way: two independent reviewers, then the reconciler on
   disagreements, then a frozen consensus.
4. **Scoring.** `score_review.py` verifies both consensus files against the records, checks
   every protocol file against the population digest (from 2026-10-14 also the browser tool,
   the citable-source list and the page-load gate), recomputes the page-load gate from the same
   records and refuses to score if it failed (the score names the gate result's hash), labels
   each case, and applies `decision-rule.md` in code (`decision_rule`). The last two checks
   were added after the v10 run, on Codex review; the v10 records were rescored with them, with
   the same result, from a population rebuilt byte-identical to the one v10 ran on. Two rules
   were corrected at the same time: the gate now fails a class whose calls opened no citable
   page (none in v10), and the validator requires a citation only when a citable page loaded,
   not any page, as the prompts say (no v10 call was rejected under the old rule: every call
   was valid on its first attempt). Later in the same review, two more: the gate counts a
   citable page as loaded only if the page it ended on is citable too (one v10 Stage 2 page
   redirected off the list; the Stage 2 site gaps moved from 0.38 and −0.11 to −0.29 and 0.08
   points), and a call whose process exited unsuccessfully, or whose stream does not end in a
   successful result, decides nothing (all 350 v10 calls exited 0 with a successful result).
   And then: an answer that cites nothing without having tried to open a citable page is
   rejected as unresearched (a URL `open_page` refuses, not http(s), is no attempt, and the
   gate does not count one; every v10 call tried at least one, and no v10 answer cites
   nothing), and the scorer accepts only the
   committed population digest, not one supplied beside the queues.

The population digest was rebuilt for these files: the Stage 1 queue and the private answer
key are byte-identical to the ones the Stage 1 reviewers ran on; the Stage 2 custodian
changed only in its prompt and schema hashes. `review-artifact.schema.json` (the original
whole-queue artifact schema) is no longer used, but the frozen Stage 1 queue binds its hash,
so it stays.

## Known limitations (disclosed)

- **Thinking summaries.** Calls run with `--thinking-display summarized`, so a call's
  thinking is stored as Claude Code's summary of it. 348 of the 350 deciding records of the v10
  run carry one; the other 2 have no thinking block at all (the model answered without
  thinking). The superseded v3 run had no thinking text, because the flag was found only after
  it was scored.
- **Pages are recorded as the text the model read.** `open_page` returns the page's visible
  text (capped at 40,000 characters), stored verbatim in the event log; it is the live page
  on the day of the call, not the frozen corpus snapshot. Search results are recorded as
  titles and URLs.
- **`loaded` recognises the walls it has met by their titles** (Vercel's "Security
  Checkpoint", Cloudflare's "Just a moment", Anubis's "Making sure you're not a bot" and "Oh
  noes!", "Captcha Verification Needed"). A wall with another title and status 200 would count
  as loaded, and could then be cited; the validator admits a citation only of a page so
  loaded. So would an error page served with status 200: the pre-flight check's
  `arachne.dainst.org/place/2042876` ends on "Arachne | 404" with status 200 and counts as
  loaded, and `dainst.org` is citable. No v10 call opened it.
- **Surface text correlates with case type.** An authority-only gain has no common literal
  string by construction, so a case whose two sides show the same string can only be a retained
  control or a literal-only loss. The reviewer can infer that partition from the evidence it is
  asked to judge; it cannot be removed. The prompts do not name arms or classes.
- **Sourcing burden is unequal in practice.** The prompts treat every case alike, but an
  institutional source for a variant spelling is harder to find than one for an identical
  string, so differing-string cases may draw more `insufficient_evidence`. Read the f counts
  with this in mind.
- **Trismegistos is not citable** (from v6). It requires a subscription and blocked this
  project's IP, so differing-string site cases have one alias-bearing source fewer (Pleiades,
  iDAI and the Thesaurus Linguae Aegyptiae remain). The gate result reports citations by
  source per class, so a shortfall shows. An access request to KU Leuven is pending.
- **A record that will not load forces `insufficient_evidence`.** There is no fallback to the
  case's field text. This is class-neutral only if the loaded rate is, so the `open_page`
  loaded rate per museum and per case class is measured against the private answer key, in
  aggregate, after the Stage 1 reviewers and before any result is read (Rule 14 gate, audit
  round 12).
- **Some listed sources stay unreadable, and one is broader than its purpose.** PCMA (Polish
  Centre of Mediterranean Archaeology) shows a CAPTCHA to the local browser and to Browserbase
  alike, and IFAO's archaeology pages answer HTTP 503 to every browser (its BEO database
  pages load); the browser does not solve CAPTCHAs or disguise itself. In v10 they account for 3 and 1 failed opens. All of eScholarship is
  citable (from v9) so that UEE articles are, which also admits UC working papers and theses
  that the `open_repository` criterion excludes; the gate result lists every cited source,
  and v10 cites eScholarship twice.
- **Field text helps some cases more than others.** A shown record's field text can carry
  context the bare mention lacks (both the "Hurbeit" and "Horbeit" records read
  "(Pharbaethos)"); this is the museums' own text and the reason the records are shown, but it
  helps differing-string cases more than identical ones.
- **Stage 2 targets recur.** Some proposed targets appear in several cases, and the class is
  the same within each recurring target (one site target recurs only in authority-only gains,
  others only in controls). No reviewer sees this, since each case is a separate call, but a
  reviewer's knowledge of one recurring target is confounded with class when reading results.
- **Released ruler targets omit builder internals.** Claim-statement IDs and a label count
  are dropped from a target's metadata at release (`UNRELEASED_TARGET_METADATA`); they are no
  evidence a reviewer can check.
- **`open_page` defects found after the v10 run**, fixed only in the next registration (#358;
  the stored calls are bound to the browser tool's hash, so changing it voids them). None changed
  a v10 call: no v10 `open_page` call failed, every Browserbase re-read that failed returned
  a page record, and no call opened a local host (7). (1) When the Browserbase re-read itself raises, the error drops the
  local failure reason. (2) The page text is read without the navigation guard the title has
  (above). (3) A page whose `load` never fires waits 15 seconds twice. (4) A PDF records
  `load_event` true although none was measured. (5) A Browserbase session is not released if
  connecting to it fails. (6) The Browserbase re-read is not paced. (7) `open_page` will open
  a loopback, link-local or private-network URL the model gives it (it blocks only listed
  domains), so a page or search result could point it at a service on the review host. No
  stored v10 call, reviewer or reconciler, deciding or not, asked `open_page` for or ended on
  a loopback, link-local, private or internal host (the gate result's
  `local_host_opens_in_any_stored_call`, empty in both stages). Not recorded, and so not
  checked: the requests a loaded page makes itself, and a public name resolving to a private
  address. (8) A call is bound to the runner's and browser tool's source, not to the
  dependencies that ran them (`runtime/uv.lock`, the Chromium build). The served model and the
  Claude Code release are checked per call from its stored init event (`claude-sonnet-5-5`,
  2.1.299; all 350 v10 calls). No call records the lock: the lock in force at run time is
  shown by its last change (0196e45, 2026-10-13, before the v10 run) and by the test that pins
  its hash and the Playwright, MCP and pypdf versions. The local Chromium is the build
  `playwright install chromium` fetches for Playwright 1.58.0; the browser of a Browserbase
  session is neither recorded nor pinned. (9) The rule that a call whose process exited
  unsuccessfully decides nothing is checked when stored calls are read (`decided_record`), but
  the runner, hash-bound, accepts a call through `validate` alone; in a later run such a call
  would be stored as decided and then stop the run at consensus, loudly.
- **A different-entity pair cannot be labelled b** (case-067 above). The classifier fix belongs
  to the next registration (#358).
- This measures the current resolver's potential on the frozen ledger, not deployed pipeline
  behaviour (#338).
