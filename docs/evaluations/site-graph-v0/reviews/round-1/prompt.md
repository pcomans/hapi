Review Hapi GitHub issue #327 at exact commit 36c23e7424f3deb901cc86a5019b408d3951c208 in the current worktree. This is a read-only code review: do not edit files or memory.

Read AGENTS.md, CLAUDE.md, GitHub issue https://github.com/pcomans/hapi/issues/327, and the diff from base 97f2e610974f0e89b9c03d409b230dff89edbb1f. Review every new file under docs/evaluations/site-graph-v0/.

The issue must preregister the real-corpus site-graph evaluation before authority changes. Review for correctness, simplicity, deterministic enforcement, incomplete or self-confirming metrics, denominator drift, broad-to-specific inflation, museum imbalance, missing real-input validation, checksum/reproducibility holes, tests that could pass without proving required values, unsupported claims from provisional silver, and scope violations. Narrower nodes must not mechanically earn improvement credit. New links and reassignments must remain separate. Museums can have different data ceilings.

Return an actual review, not a summary. For every finding give severity P0/P1/P2/P3, exact file and line, why it violates the issue or repository rules, and a concrete fix. Explicitly state the reviewed commit SHA. Finish with APPROVE only if there are no P0/P1/P2 findings; otherwise finish with REQUEST_CHANGES.
