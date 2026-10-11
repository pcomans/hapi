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

Deterministic headline (no review yet): shared records on any two-museum shared node —
literal arm Met 27,330 / Brooklyn 2,894 / Harvard 534; authority arm Met 14,502 /
Brooklyn 1,156 / Harvard 8 (`results/real-run-report.json`).

## Review protocol (changes from the original)

- **Reviewer:** Claude Sonnet 5.5 through the Anthropic API, **one case per call**, with
  adaptive thinking (display `summarized`), effort `high`, and the `web_search_20260209` tool
  (`scripts/run_claude_review.py`). Two independent reviewers are two separate runs. One call
  per case keeps each decision's record separate; a whole-queue call with web search would
  exceed the context window.
- **No dated model snapshot.** Per the revised Constitutional Rule 13 (2026-10-11), an LLM call
  cannot be re-executed to reproduce a decision, with or without a dated model id. The record
  of each call is what is re-read: request parameters, system prompt, user content, every
  response round verbatim, the served model, the thinking, the web-search queries and results,
  token usage, and the validated decision.
- **No automatic fallback** to another model on a refusal: a refusal stops the run, so a
  case's reviewer can never change silently.
- **Fail loud:** an unparseable or schema-invalid answer, a wrong case ID or evidence hash, or
  a case decided without any web search stops the run after the record is written.
- **Prompt:** `prompts/stage-1-reviewer-v3.txt`, response schema
  `raw-response-contracts/stage-1-reviewer-case-v1.schema.json`. Leak-audited before use
  (Rule 14; `prompt-audit-2026-10-11.md`).
- **Every judgment rests on a cited source.** Whether the two sides' strings match or differ
  is never by itself a basis for a judgment, and general knowledge is not a source; what the
  case evidence records about the records counts only through a named artifact-evidence
  exception. The schema requires at least one institutional `http(s)` citation on every
  decision, including `insufficient_evidence`.
- **Each side shows up to 5 of its records** (`shown_records`): the museum's public record
  URL, taken from the frozen corpus's canonical `source_url`, and the full text of each field
  that holds a mention. They are chosen in an opaque seeded order over record IDs. The original
  registration showed only the mention strings. In the mini-pilot both reviewers then took a
  title-field "Horemheb" for "Stela of Lady Horemheb" (a private woman). The ledger record is
  "Fragment of a Statue of King Horemheb", so one reviewer answered `different_entity` on a
  real match. Adding the records changes no case membership, case ID or other evidence field
  (`results/real-review-population-digest.json`, `results/real-rerun-proof.json`).
- **Up to 99 web searches per case** (`max_uses`), so a case is never decided from general
  knowledge because a search cap ran out (the 5-search cap of the first pilot did).

## Known limitations (disclosed)

- **Search result text is not fully readable.** Anthropic's web search returns each result's
  page content encrypted. The record keeps the results exactly as returned — URL, title, page
  age, the encrypted content, and any passages the model quotes in its answer — so the URLs a
  decision rests on are inspectable, but not the full text the model read. Accepted by the
  project owner on 2026-10-11.
- **Search filtering output is encrypted too.** `web_search_20260209` filters results by
  running code server-side. The code is recorded in plain text (`code_executions`); its output
  is returned encrypted, like the page content.
- **The thinking is a summary.** Current Claude models return a summary of their reasoning,
  never the raw chain of thought, and adaptive thinking is optional: a simple case may carry
  no thinking at all.
- **Surface text correlates with case type.** An authority-only gain has no common literal
  string by construction, so a case whose two sides show the same string can only be a retained
  control or a literal-only loss. The reviewer can infer that partition from the evidence it is
  asked to judge; it cannot be removed. The prompt does not name arms or classes.
- **Sourcing burden is unequal in practice.** The prompt treats every case alike, but an
  institutional source for a variant spelling is harder to find than one for an identical
  string, so differing-string cases may draw more `insufficient_evidence`. Read the f counts
  with this in mind.
- **Field text helps some cases more than others.** A shown record's field text can carry
  context the bare mention lacks (both the "Hurbeit" and "Horbeit" records read
  "(Pharbaethos)"); this is the museums' own text and the reason the records are shown, but it
  helps differing-string cases more than identical ones.
- **Record pages may not open.** Whether a museum's page loads for the reviewer can vary by
  site. A record that cannot be opened may be used only through an artifact-evidence exception
  saying so, the same for every case.
- This measures the current resolver's potential on the frozen ledger, not deployed pipeline
  behaviour (#338).
