# Prompt audit, protocol v2 (Rule 14), 2026-10-15

`prompts/system-v2.txt`, `rules-v2.txt`, `reviewer-v2.txt` and `reconciler-v2.txt`, and the
code that renders them (`tla_link_review.py`: `labelled`, `spellings`, `compose`,
`compose_reconciler`), were audited by the prompt-auditor agent before any v2 call. Its full
reports are committed: `prompt-audit-v2-round1.md` and `prompt-audit-v2-round2.md`.

1. **Round 1: not fine to run.** No leak in the templates, but:
   - P1: a "most exactly" tie rule with no tiebreak;
   - P1: endings asymmetric (only a dropped t was ruled on);
   - P2: bearer descriptions and lemma ids in the rendered records could proxy the answer;
   - P2: framing that primed "none", and conventions that did not cover extra or missing consonants.

   Fixed: the answer is the set of every candidate that is the same name (no tiebreak);
   descriptions and ids are not rendered; one shared rules block.
2. **Round 2: fine to run after one wording fix.**
   - P1: the ending rule read as forbidding the weak-consonant omissions the line above
     allows. It was replaced with the auditor's wording verbatim.
   - P3: the reconciler's opening sentence was reworded as the auditor suggested.
   - A test now checks every rendered candidate spelling for leftover descriptions.

Final SHA-256s (checked by `pipeline/tests/test_tla_links.py`):

- `system-v2.txt`: `e5b702fbad5ee31c14d4025068c1ad0c80f882029952a2045273ee26e675d82a`
- `rules-v2.txt`: `bfb07dfec7556fdee6361a167eefe5f2200ed4c9e31b76158e4b26748982d97c`
- `reviewer-v2.txt`: `01508d0dd415949bdf5413c418d57b2b7b74c9cedecefbe8c2cb6e54818e5534`
- `reconciler-v2.txt`: `8a3edabf73bf6895d1a9bcafb3ecb8eebce4d8dccd7ba9124f9df57455add82f`
