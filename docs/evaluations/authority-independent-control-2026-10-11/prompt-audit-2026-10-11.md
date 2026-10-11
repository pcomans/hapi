# Stage 1 reviewer prompt — leak audits (Rule 14), 2026-10-11

Audited by the `prompt-auditor` agent against the exact composed requests (system prompt,
parameters, user content for three real cases) before any model judged a case.

| Round | Prompt state | Verdict | Findings acted on |
|---|---|---|---|
| 1 | first v3 draft | PASS (no P0/P1) | P2-b "Treat insufficient evidence conservatively" biases against cases whose two sides use different strings; P2-c v3 had dropped the guard against consulting the evaluation's own materials; P3-a "any experimental arm or class" named the concept |
| 2 | P2-b/P2-c/P3-a fixed | PASS | P2-d the new sentence warned only against `different_entity`/`insufficient_evidence` (a soft push toward `same_entity`); P3-d it covered only the first question |
| 3 | neutral wording | PASS (no P0/P1/P2) | none |

Accepted residuals (disclosed in `README.md`): surface text correlates with case type and
cannot be removed (P2-a); JSON keys are printed sorted, so `brooklyn` precedes `met`
(P3-b, cosmetic); extractor-internal role names appear in the evidence (P3-c, shared by both
arms). The project owner approved the final wording on 2026-10-11.
