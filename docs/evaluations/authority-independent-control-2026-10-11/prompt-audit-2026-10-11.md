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
