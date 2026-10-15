# Protocol v1 (withdrawn, 2026-10-15)

Kept for the record (Rule 13); it decides nothing.

- **What it was.** Each (D&H name, TLA lemma) pair meeting only on the weak-sign key went to
  two reviewers (both claude-sonnet-5-5), with a reconciler (sonnet) on disagreements. The
  prompt was a sign-by-sign consonant procedure, audited in three rounds
  (`prompt-audit.md`). 250 calls are stored in `runs/`; their decisions are in
  `decisions.jsonl`.
- **Why it was withdrawn.** The local code review read the linked lemmas. Of the 70 weak-tier
  `same_name` links, about a dozen joined different names:
  - one D&H name linked to both a Min- and an Amun- name;
  - a D&H name linked to four distinct `Nfr-` names;
  - a name linked to `Mttj`.

  Cause:
  - **A skeleton test.** The procedure was in effect the weak-sign key with ordering, so it
    could not tell different words with the same consonants apart.
  - **An incoherent clause.** Its "elements differ in number" rule contradicted true pairs
    (D&H fuse words), so the reviewers set it aside.
  - **Not independent.** Both reviewers were the same model, so 120 of 122 agreements
    measured self-consistency.
- **What replaced it.** Protocol v2 (`../`):
  - one unit per D&H name, its candidate TLA names under shuffled opaque labels;
  - a word-level rule;
  - reviewers on two different models.
