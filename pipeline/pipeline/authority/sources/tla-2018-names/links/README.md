# Spelling links: Dodson & Hilton's women's names ↔ TLA personal-name lemmas (2026-10-15)

A link says that a D&H name and a TLA lemma are **one name**, so that the lemma's renderings
(its transliteration and translations, glosses removed) become further spellings of that name
for the royal-women resolver (`royal_women.build_index(..., linked_spellings=...)`). A link is
never a decision about a person: "Henttawy" would link to every D&H woman of that name, and
the resolver still chooses among them by the record's numeral, family and dynasty.

Code: `pipeline/pipeline/authority/tla_links.py` (candidates, linked spellings) and
`tla_link_review.py` (the model review). Tests: `pipeline/tests/test_tla_links.py`.

## Licence

The linked renderings are TLA data, CC BY-SA 4.0, with the attribution in `../README.md`.
They stay in this source's directory and are read from here; they are not copied into
Apache-licensed data.

## Candidates

`tla_links.candidate_pairs`: every (D&H name, TLA `person_name` lemma) whose spellings meet on
one of the resolver's tiers. A D&H name is a label with D&H's letter or numeral removed.

| Tier the pair first meets on | Pairs | Decided by |
|---|---|---|
| exact (`raw_exact`) | 34 | rule: the resolver already treats this tier as one name |
| claim-graph keys (`committed_normalized`) | 9 | rule, as above |
| weak-sign key only (`weak_sign_skeleton`) | 122 | model review (below) |

A weak-sign key that D&H spells differently for different women (`withheld_keys`: hntt,
nbt, nfr, tntmn) proposes no pair, since the key cannot tell those names apart.

## Review (Rule 13, Rule 14)

- **Prompts:** `prompts/system-v1.txt`, `reviewer-v1.txt`, `reconciler-v1.txt`. Each was
  leak-audited before any call (`prompt-audit.md`, three rounds; a test checks the SHA-256s).
  The D&H side of a prompt carries the name only, never the woman's kin, dynasty or letter.
- **Calls:** Claude Code headless on the subscription (`claude -p`, model alias `sonnet`,
  served `claude-sonnet-5-5`, effort high), with no tools. Every call is stored complete in
  `runs/<role>/` as its stream-json event log, with the command, the system prompt and the
  user content. A test re-checks each stored call: no API-key billing, the served model, no
  tools, no hook output, and a valid answer with stated reasoning.
- **Reviewers A and B** judged each of the 122 pairs independently. Their verdicts agreed on
  120. The reconciler, which saw both reviews under shuffled opaque labels, decided the 2 they
  disagreed on.
- **Reasoning captured:** every one of the 250 answers states its reasoning; 249 of the calls
  also hold the model's thinking block. Reviewer A's call on Seneb|706871 has none, and its
  answer's reasoning stands alone.
- **Two stored pairs decide nothing.** The run withheld hntt, nbt and nfr. The resolver's
  rule was later derived from the data (`different_spellings`) and also withholds tntmn
  (Tentamun / Tintamun). So the run's two pairs Tentamun|708230 and Tintamun|708230 are no
  longer candidates. Their calls stay on disk (Rule 13), and a test pins them as the only
  calls that are not current candidates.

## Result (`decisions.jsonl`)

| Basis | same_name | different_name |
|---|---|---|
| rule (exact or claim-graph keys) | 43 | — |
| reviewers agree | 70 | 50 |
| reconciler | — | 2 |

`decisions.jsonl` is rebuilt from the stored calls by
`uv run python -m pipeline.authority.tla_link_review decide`. A test checks that the rebuild
equals the committed file. The 113 `same_name` links give 110 women 304 further spellings.
They add no weak-sign collision and change no withheld key (tested).

## Limits

- **The reviewers judge spelling, not usage.** The prompt lets a modern spelling leave out
  an element-final t, so a masculine and a feminine form can be one name (Seneb and `Snb.t`).
  That is the key's own rule 3.
- **Lemmas are not one-to-one with names.** One D&H name can link to several lemmas of one
  name entered twice. Every one of their renderings becomes a spelling.
- **Royal-name (`kings_name`) lemmas are not linked here.** Linking them to the king graph is
  a later stage.
