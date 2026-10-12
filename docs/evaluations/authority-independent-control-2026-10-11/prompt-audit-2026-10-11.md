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
