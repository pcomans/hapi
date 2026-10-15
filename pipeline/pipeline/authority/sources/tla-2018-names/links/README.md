# Spelling links: Dodson & Hilton's women's names ↔ TLA personal-name lemmas (protocol v2.1, 2026-10-15)

A link says that a D&H name and one or more TLA lemmas are **one name**. The lemmas'
renderings (transliteration and translations, glosses removed) then become further spellings
of that name for the royal-women resolver (`royal_women.build_index(..., linked_spellings=...)`).

A link is never a decision about a person:
- "Henttawy" would link to every D&H woman of that name;
- the resolver still chooses among them by the record's numeral, family and dynasty.

Code:
- `pipeline/pipeline/authority/tla_links.py`: candidates, units, linked spellings.
- `tla_link_review.py`: the model review.

Tests: `pipeline/tests/test_tla_links.py`.

## Licence

This directory is Adapted Material of the TLA lemma list, shared under CC BY-SA 4.0 with the
attribution in `../README.md` (and the repository's `NOTICE`). That covers:
- the stored model calls, which quote TLA rows;
- the decisions;
- the prompts.

The linked renderings are read from here and are not copied into Apache-licensed data.

## Candidates and units

- **Candidates.** `tla_links.candidate_pairs`: every (D&H name, TLA `person_name` lemma) whose
  spellings meet on one of the resolver's tiers, 163 in all. A D&H name is a label with D&H's
  letter or numeral removed.
  - A lemma's spellings are read once, by `spellings_of`, for the candidates, the linked
    spellings and the prompt alike. Descriptions in parentheses and comma tails go; a second
    spelling after ";" counts.
  - A broken-off lemma ("Jpw-...") is no candidate.
- **Withheld keys.** A weak-sign key that D&H spells differently for different women
  (`withheld_keys`: hntt, nbt, nfr, tntmn) proposes nothing.
- **Units.** `tla_links.units` groups the candidates by D&H name. Within a name, lemmas of one
  strict transliteration (`strict_name`) are one TLA name: 97 D&H names.
  - **By rule (32).** The exact or claim-graph keys find exactly one TLA name, which is
    linked: the resolver already treats those tiers as one name.
  - **Reviewed (65).** The rule finds no TLA name, or more than one (Iaret, Ti), and the
    candidates go to review: 107 TLA names in all.

## Review (Rule 13, Rule 14)

**Prompts** (`prompts/`, one shared rules block):
- The D&H name is shown with its candidates under opaque labels, in an order seeded by the
  name. The prompt shows no lemma ids and no descriptions such as "(a wife of Tuthmosis IV)".
- The rule compares words, not consonant skeletons. Consonant conventions are stated; a
  feminine ending t may be omitted; nothing else may be added or dropped; different words that
  share consonants are different names.
- The answer is the set of every candidate that is the same name, possibly empty.
- Audited in two rounds before any call. The auditor's full reports are
  `prompt-audit-v2-round1.md` and `prompt-audit-v2-round2.md`; the summary and SHA-256s, which
  a test checks, are in `prompt-audit-v2.md`.

**Calls:**
- Claude Code headless on the subscription (`claude -p`, no API key), effort high, no tools,
  slash commands off.
- Reviewer A is claude-sonnet-5-5. Reviewer B and the reconciler are claude-opus-5-5, so the
  two reviewers are different models.
- Every call is stored complete in `runs/<role>/`: stream-json events, command, system prompt,
  user content.
- A decision is re-derived from the stored event log (`validate`), and the `result` stored
  beside it must agree.
- A test re-checks every call: no API-key billing, only the role's model in the init event,
  every assistant message and the usage, no tools, no hook output.

**Hidden context.** Claude Code adds about 585 tokens of its own context to every headless
call. A probe measured it: 602 input tokens for a 15-token prompt, with slash commands on or
off. The probe's event logs are in `probe-hidden-context/`, and a test reads the figure. No subscription-auth flag
removes it (`--bare` requires an API key), so it is not in the stored input. That is a limit
of harness runs, accepted as the #337 evaluation's harness reviews were: the record is the
stored event log with the exact command, system prompt and user content (project owner's
decision, 2026-10-15).

**Khnemet re-asked.** The first candidate reader cut "Chnum(?)-anchu" to "Chnum", which
proposed lemma 705752 to Khnemet. With one reader, it is no candidate, so Khnemet's prompt
changed. Its two stored calls moved to `withdrawn-v2.1-khnemet-candidate/`, and A and B were
asked again. It is the only unit whose prompt changed (checked).

**Result of the review:**
- A and B agreed on 59 of the 65 units. The reconciler, which saw both reviews under shuffled
  opaque labels, decided the other 6: Meryetneith, Minemaes, Nubemhat, Nubemiunu, Reniseneb,
  Werenro.
- Every answer states its reasoning. A thinking block is present in 49 of A's 65 answering
  calls, 55 of B's 65 and all 6 of the reconciler's: thinking is adaptive.
- One call failed format and was retried: A on Meketaten, with no JSON object in the answer.

## Expert calls (`runs/expert/`)

Three units are decided by one stored expert call each: claude-opus-5-5, headless, no tools,
recorded like the reviewer calls. Its answer decides the unit, whatever it is, and the model
decision is kept beside it (`model_basis`, `model_tla_ids`).

**Which units.** They were fixed before the calls (`EXPERT_UNITS`):
- **Neferuni and Meryetyotes.** These are the unstable units. `unstable_units` finds units on
  which one reviewer's valid answers differ between this run and its earlier run, the withdrawn
  v2.0 B, read by today's parser. Agreement on such a unit is luck, not consensus, so `decide`
  refuses an unstable unit that is not an expert unit. Exactly these two are unstable. On every
  other unit, B answered the same in both runs (tested).
- **Minemaes.** The egyptologist review of this PR (a Claude Code subagent) judged the
  reconciler's link to `Mnw-ms.w` wrong. Its argument: D&H write the preposition m as "em" and
  ꜣ + =s as "aes", so "Min-em-aes" would be a Min-em-… name.
  - Its transcript holds session-private context and is not committed. So it selected the unit
    but decides nothing.

**What the expert sees** (`prompts/expert-v1.txt`, audited in two rounds):
- the unit as the reviewers saw it;
- how D&H write every other name decided by rule or by agreement, including the names decided
  to have no TLA name, as evidence of their conventions.

It does not see this unit's decision, the reviewers' split, or why the unit was sent.

**What it answered:**

| D&H name | Model decision | Expert | Expert's stated reasoning, in short |
|---|---|---|---|
| Meryetyotes | agreement: `Mr.t-jtj=s`, `Mr.yt-jtj=s` | both | one name in two orthographies; D&H write Mr.t as "Meryet" (Meryetamun) |
| Minemaes | reconciler: `Mnw-ms.w` | `Mnw-ms.w` | Min + ms.w, as in Ahmes; "not certain: the 'ae' is unusual" |
| Neferuni | agreement: `Nfr.w-Nj.t` | `Nfr.w-Nj.t` | Neferu + Ni(t), with the feminine t dropped as in Dedetanuq; "with some uncertainty, since D&H might be expected to print 'Neith' in full" |

**The expert and the egyptologist review disagree** on Minemaes and Neferuni.
- Both are model readings of a D&H spelling, and the expert states its uncertainty.
- Under the rule fixed before the calls, the expert's stored answer decides.
- The resolver reads these spellings only for a mention after a royal-woman cue (Queen,
  Princess, King's Daughter …). A Min-mesu or Neferu-Neith is therefore reached only when a
  record calls her a royal woman, and the record's family and dynasty still have to confirm
  which woman.

## Result (`decisions.jsonl`)

| Basis | no TLA name | one TLA name | two TLA names |
|---|---|---|---|
| rule | — | 32 | — |
| reviewers agree | 15 | 40 | 2 |
| reconciler | 3 | 2 | — |
| expert | — | 2 | 1 |

- **Two names.** The decisions on two TLA names are Iaret (`Jꜥr.t`, `Jꜣrt`), Ti (`Tj`, `Ty`)
  and Meryetyotes (`Mr.t-jtj=s`, `Mr.yt-jtj=s`, by the expert): one name in two TLA
  orthographies. This is the documented policy: every candidate that is the same name is
  linked.
- **Rebuilt from the calls.** `decisions.jsonl` is rebuilt from the stored calls by
  `uv run python -m pipeline.authority.tla_link_review decide`, and a test checks that the
  rebuild equals the committed file.
- **Effect on the resolver.** The links give 121 women 263 further spellings.
  - They add no weak-sign collision and change no withheld key (tested).
  - The new exact and claim-graph keys are shared only by women of one D&H name, as their D&H
    labels already are, with one exception: the claim-graph key `tj` now reaches Ti and
    Tia C/Q. A mention keyed `tj` is left ambiguous among them, not resolved (tested).

## Withdrawn runs (kept, deciding nothing)

- `v1-withdrawn/`: protocol v1, a consonant-procedure review of single pairs. It linked names
  that differ; see its README.
- `withdrawn-v2.0-strict-parser/`: the v2.0 runs of reviewer B and the reconciler.
  - v2.0's parser rejected answers in a closing code fence, and the reconciler fenced six of
    six attempts on one unit.
  - Re-reading those attempts under a looser parser would have changed two of B's answers
    after they were seen, so B and the reconciler were run afresh under v2.1.
  - A's calls read the same under both parsers.
  - During that run the retry cap was raised from 3 to 6 (and set back to 3 for v2.1), so
    some of its reconciler units hold up to six attempts.
  - Read by v2.1's parser, the fresh B run answers every unit as the withdrawn one first did,
    except Neferuni and Meryetyotes. Those are the unstable units above.
- `withdrawn-v2.1-khnemet-candidate/`: Khnemet's first A and B calls, asked with the stray
  candidate (above).

## Limits

- **A model judgment.** The review judges which words a modern spelling renders. D&H give no
  transliteration, so the decision rests on the model reading the D&H spelling, checked
  against the TLA's transliteration and translations. The egyptologist review of this PR
  checks the linked names.
- **Sampling variance.** Reviewer B answered two units differently on different runs. Those
  units are decided by the expert, but a unit can be unstable without our having sampled it
  twice.
- **Missed links.** The egyptologist review found two misses, which cost recall only: Sitre /
  `Zꜣ.t-Rꜥw` and Bakmut / `Bꜣk.t-Mw.t`. The candidate keys did not propose them (z/s and the
  feminine t).
- **Royal-name lemmas are not linked here.** Linking the `kings_name` lemmas to the king graph
  is a later stage.
