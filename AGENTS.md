# Repository agent rules

## Fundamental inputs are hard blockers

Never substitute fixtures, synthetic data, scaffolding, proxy metrics, or partial
datasets when the user's requested conclusion depends on a missing fundamental
input.

If a required corpus, database, credential, source, environment, or other
fundamental input is unavailable:

1. Stop work that purports to answer or complete the blocked objective.
2. State precisely what is missing and why the objective cannot be completed
   without it.
3. Do not reframe preparatory work as execution, validation, evidence, or
   meaningful progress toward the requested conclusion.
4. Do not continue merely to produce a deliverable or appear complete.
5. Resume only when the missing input becomes available or the user explicitly
   changes the objective.

Passing tests on fixtures proves only fixture behavior. It must never be
presented as evidence about the unavailable real corpus.
