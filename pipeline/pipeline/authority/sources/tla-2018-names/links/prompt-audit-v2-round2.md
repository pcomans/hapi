# Prompt audit, TLA link review protocol v2, round 2

Audited: `prompts/{system,rules,reviewer,reconciler}-v2.txt`, `tla_link_review.py` (`spellings`, `compose`, `validate`, `disputed`, `compose_reconciler`, `decide`), samples in `v2-samples-r2/` (Iaret, Mereret, Neferhotep, Iaret-reconciler).

Verdict: fine to run after one wording fix (P1 below, a one-line edit). Round-1 P1.1, P2.3-P2.7, P3.8-P3.10 are resolved.

## Leakage: clean

- No D&H name, TLA string, lemma id or translation appears in the templates. The "different word that happens to share consonants" example is generic.
- Lemma ids and subtype are gone from the render. Candidate order and labels are shuffled by a seed from the D&H name. `dh_target_ids` is not rendered.
- Bearer descriptions are mostly gone: `DESCRIPTION` strips parentheticals and comma tails. The Iaret sample no longer carries "wife of Tuthmosis IV".
- Reconciler: X/Y are shuffled, the framing is symmetric, and reviewer reasoning is quoted under the same C labels. In the sample, the dispute is {C1} against {} and the wording is neutral.

## P1

1. **Rule 4 (rules-v2 l.7) contradicts rule 2 (l.5).** L.7 says record 1 "may not ... leave out any other consonant the candidate has". L.5 says ꜣ, ꜥ, j, y and w may be rendered "not at all". Read literally, l.7 forbids omitting the ꜣ/ꜥ/j/y/w that l.5 permits omitting, because those are "other" than the feminine t. Models will resolve this differently. It matters for Iaret (ꜣ/ꜥ), Ahmes (ꜥ) and any j/y/w unit. Rewrite: "apart from what the lines above allow, record 1 may not render a consonant the candidate lacks, nor leave out a consonant the candidate has; the one further omission allowed is a feminine ending t."

## P2

2. **Bearer residue and untested regex.** `DESCRIPTION = \s*\([^)]*\)|,.*$` does not handle nested parentheses (leaves a stray `)`). It also misses descriptions that follow `;`, " - " or a plain space without a comma, such as "Name Tochter des X", and leaves a ";" second spelling in place. Add a committed test over all candidate lemmas of the 65 review units. It should fail on any rendered value containing a parenthesis, a bracket, more than two whitespace-separated tokens, or a lowercase German or English word from a small stoplist (Tochter, Frau, Sohn, wife, daughter, king, queen). Per rule 3 this should be a test, not a convention. Keep "Who bore a name is not evidence"; it is harmless now.
3. **Downstream code is stale for multi-choice.** `tla_links.linked_spellings` (l.186-187) still raises "linked to more than one TLA name" if a decision's `tla_ids` span more than one strict name, and it reads the old `tla_name` shape. `decide` now emits `tla_names` and several names per D&H name (as the design intends). The first legitimately multi-orthography decision will raise there. Update that consumer and its tests, and decide explicitly whether a D&H name may resolve to several TLA names. The raise is the guard against the v1 Min/Amun failure, so replace it with a deliberate check, not a deletion.
4. **Ordering and grading drift.** "Several candidates can be the same name in different orthographies" is the only licence for multi-choice, and the rules give no criterion for when two candidates are one name beyond "record 1 can be read as" each. Two candidates that both pass the conventions are therefore both correct by definition (Iaret C1/C2, Mereret C1/C5). That is consistent and deterministic, so it is fine, but record this in the README as the documented policy.

## P3

5. Reconciler line 1 says reviewers "listed different candidates"; when one listed none (Iaret sample) that is slightly off. Suggest "gave different answers".
6. `validate`: `set(choices)` raises TypeError if the model returns an unhashable item (a nested list). The `map(str, ...)` check runs first, but `set(choices)` is evaluated after it and still crashes. Treat as a failure, not a crash.
7. The duplicated identical lemma lines (Neferhotep C2, Lemma 1 and 2) are correct but mean "two lemmas, same spelling". Harmless.
8. The "translations show which words it is made of" clause is weakened now that descriptions are removed. Many translations are bare spellings ("Merery"), so the clause only helps hyphenated ones. Acceptable; the model falls back on the transliteration.

## Items checked and clean

- Endings: only the feminine t may be omitted, and extra consonants are barred. Mereret's t-less candidates (Mrry, Mrr, Mrr.w) are correctly excluded, and C2 `Mrry.t` is the only reading that fits. That is the rule's effect, not a hint.
- Fused D&H words: "often written as one word" together with "in the same order" does not conflict.
- Equal sets between A and B count as agreement; empty sets are valid and distinct from a failure.
