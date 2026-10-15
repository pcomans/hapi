# Prompt audit, TLA link review protocol v2, round 1

Audited: `prompts/system-v2.txt`, `reviewer-v2.txt`, `reconciler-v2.txt`, the rendering code (`tla_link_review.py` `labelled`, `tla_record`, `compose`, `compose_reconciler`; `tla_links.py` `units`) and the rendered samples Ahmes, Iaret, Mereret, Minemaes.

Verdict: NOT fine to run as is. No template text leaks an answer, but there are two P1 rule gaps (tie rule, ending asymmetry) that make models improvise. There are also P2 proxies in the record format.

## Leakage in template text: clean

- No D&H name from the review set appears in any template. No TLA string, lemma id or translation is quoted in the templates. All examples are generic (`.t`, `.w`, `=`).
- The unit id and the D&H name are the only unit-specific text. The shuffle seed is `sha256(salt + dh_name)`, not the answer. `dh_target_ids` and `by_rule` are not rendered. Reconciler X/Y order is seeded the same way. Both are fine.
- Reconciler labels are the same C labels as the reviewers, so the quoted reasoning stays interpretable. Good.

## P1

1. **Tie rule is undefined and contradicts the binary definition.** (reviewer-v2 l.19, reconciler-v2 l.21.) "Same name" is defined as reading *exactly* the candidate's words, which is binary. The tie rule then asks for the candidate rendered "most exactly", which is graded, and nothing says how to grade. The samples show real ties:
   - Iaret: `Jꜣrt` and `Jꜥr.t` both satisfy the stated conventions, because ꜣ and ꜥ are each "a vowel or not at all".
   - Mereret: `Mrry`, `Mrrj` and `Mrry.t` are all candidates, and j and y are interchangeable under the conventions.

   A model must invent a tiebreak. Under rule 2 this is a silent arbitrary pick, and the reconciler only inherits it. Rewrite one of two ways:
   - Define the tiebreak deterministically: "fewest conventions applied; if still equal, answer `none`/`tie`".
   - Add an explicit tie outcome, e.g. `"choice": "tie"` with the tied labels listed, resolved by a documented code rule. A tie between two variant transliterations of one name is a legitimate state that the one-choice format cannot express.
2. **Endings are asymmetric and unspecified.** A modern spelling "may leave out a feminine t". Nothing says whether it may *add* one. The same applies to `.w`, `.y` and any other ending. Mereret has `Mrry` (no t), `Mrr` and `Mrr.w`, so the model must decide whether the record's extra t disqualifies them. Say it explicitly, e.g. "an ending the candidate has may be omitted in record 1 only if it is `.t`; record 1 may not add a consonant the candidate lacks". Say too whether "record 1 renders no word that the candidate lacks" covers endings. Today the answer depends on whether the model counts `.t` as a word.

## P2

3. **The "different words sharing consonants" clause is biased toward `none` and assumes information the record lacks.** (l.16.) "A noun against an adjective or verb of the same root" cannot be applied, because record 1 is only a spelling with no gloss. The model cannot know which word class D&H intend, so it will guess. The clause is one-sided: nothing balances it with "do not reject a candidate merely because a related word exists". Suggest: "If record 1 could render the candidate's words, and the only difference is a possible alternative reading, it is the same name unless the candidate's translation shows a different meaning." That gives the model something checkable.
4. **Bearer information is shown, then declared inadmissible.** `tla_record` prints translations verbatim. Iaret C2 shows `Iaret (a wife of Tuthmosis IV)`, and D&H's book is of royal families. The line "Who bore a name ... not evidence" cannot stop a model from using a gloss that says "royal wife" as a proxy for the answer. It will likely break the C1/C2 tie. Either strip bearer parentheticals from the displayed translations (`GLOSS` in `tla_links.py` already does this for matching; apply it in the render and note it in the prompt), or drop the "not evidence" sentence and accept the proxy. Do not do both halves.
5. **Lemma ids may be a notability proxy.** TLA id prefixes appear to correlate with lemma sets (the royal-woman candidates are 4xxxxx, ordinary names 7xxxxx). The ids do no work in the decision. Replace them in the render with the candidate label only, and keep the id in the stored record. Alternatively, show that ids carry no meaning. Note the shuffle hides order but not ids.
6. **"A candidate was found because some spelling of it shares consonants with record 1."** (l.4.) `candidate_pairs` also admits candidates on `raw_exact` and `committed_normalized` tiers, so this sentence is not true of every candidate. It also primes the model to treat every candidate as a probable false friend (a mild lean to `none`). Make it neutral: "Candidates were selected by spelling similarity; some may be the same name, none may be."
7. **Convention list is incomplete.** Nothing covers: doubled consonants versus single (Mrr vs Mer-er), whether the vowels D&H add must sit at ꜣ/ꜥ/weak positions only, or what to do with an unexplained record 1 consonant. Item 2's "record 1 may not add a consonant" covers the last.

## P3

8. The three examples in the "different words" clause (different god, noun vs adjective, feminine t) mirror the v1 failure modes. None names a data item, so this is not a leak, but it tells the reviewer what kind of trap this dataset contains and nudges toward `none`. Acceptable if item 3 is balanced.
9. Translation lines are inconsistent: some candidates show `en: ""`, and one (Mereret C8) has only `de:`. Cosmetic, but a model may read an empty or absent `en` as evidence. Render absent translations as `(none)` uniformly.
10. The "mixed lemma" claim in the template ("one or more lemmas with one transliteration") is fine, but no sample shows a multi-lemma candidate. Check one before the run.

## Reconciler framing

Neutral. Reviews are labelled X/Y in a seeded order, "either or both may be wrong" is balanced, and "a claim the records do not support counts for nothing" applies to both. Two points:
- The reviewers' `reasoning` carries any bearer-gloss reasoning forward (item 4), and the reconciler cannot see which review is Opus and which Sonnet, which is correct.
- It inherits the tie rule of item 1, so both fixes must be applied to `reviewer-v2.txt` and `reconciler-v2.txt` together. They duplicate the rules text, so a change in one and not the other creates a contradiction. Consider a single shared rules block.

## Internal contradictions found

- "Exactly" (binary) vs "most exactly" (graded): item 1.
- "May leave out a feminine t" vs silence on adding one, against "record 1 renders no word the candidate lacks": item 2.
- "Not evidence" for bearer vs a record that prints the bearer: item 4.
- On D&H fusing words: "every word rendered ... no word the candidate lacks" does not conflict, since the text says record 1 is "often written as one word". This is settled, provided the segmentation is judged on words and not on separators.
