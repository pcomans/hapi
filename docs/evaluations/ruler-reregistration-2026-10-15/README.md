# Ruler re-registration with royal women (2026-10-15)

**Issue:** [#361](https://github.com/pcomans/hapi/issues/361) · **Follows:** the #337
re-registration ([`../authority-independent-control-2026-10-11/`](../authority-independent-control-2026-10-11/),
protocol v10). This registration reuses that protocol and its scripts (frozen copies here), and
changes only what is listed below.

## Question

#337 v10 found that rulers do not qualify (Met–Brooklyn: a 2, d 5, e 1, f 1). Most of the lost
ruler links were queens: a queen-cued name went to the kings, where no king matched, or where a
king of her name did. Since then, the authority has gained the royal women:
- Dodson & Hilton's women, with the female rulers (#360, #363);
- a weak-sign spelling key (#365);
- spelling links to the Thesaurus Linguae Aegyptiae's names (#366).

The question is the same as #337's, for rulers only: does the authority arm link museum records
on rulers usefully where plain text does not, without false merges, judged by v10's review
protocol and decision rule?

## What changed from #337 v10

1. **Rulers only.** Sites and tombs are unchanged since v10, which decided them; here they
   abstain (`not_in_this_registration`).
2. **The extractor's cues** (`scripts/extract_mentions.py`). The royal-woman cues the resolver
   knows (`royal_women.ROYAL_WOMAN_CUE_BEFORE`) are now extraction cues, longest first:
   - Queen Mother;
   - King's (Great) Wife, King's Mother, King's Daughter;
   - Great Royal Wife;
   - God's Wife (of Amun);
   - Divine Adoratrice (of Amun);
   - Princess.

   Before, "mother" and "wife" were stop words after a bare "queen" or "king", and "princess"
   was no cue. An opening quote after a cue is not part of the name (`'The King's Wife
   "Nefertity"'`). Each mention also carries its record's dynasty, as the canonical record
   gives it. The span after a cue is v10's: a quote before the name stays in it
   ('"Nefertity'), and the mention reader refuses it, which is a missed link and never the
   kings (a first draft stripped the quote, and the resolver then read the name as uncued; code
   review).

   `scripts/ledger_diff.py` compares this ledger with v10's on the frozen corpus
   (`results/ledger-diff.json`, tested):
   - 93 new mentions, each after a royal-woman cue;
   - none of v10's lost or changed (148,871 → 148,964);
   - none of the 238 royal-woman-cued mentions is one the resolver would not read as cued.

   The extractor still reads no authority file. A test checks that its cues match the
   resolver's on a fixed list of cue phrases.
3. **The authority arm** (`scripts/compare_arms.py`, `RulerAuthority`):
   - **A mention after a royal-woman cue** resolves among the royal women and the female
     rulers (`royal_women.resolve_royal_woman`), never among the other kings. Its context is
     the record's own kings (what the record's uncued ruler mentions resolve to) and the
     record's dynasty (`royal_women.single_dynasty`).
   - **Every other ruler mention** resolves among the kings exactly as in v10.
   - **The royal women are:**
     - Dodson & Hilton's women (#360, #363), resolved through the claim-graph kings
       (`pipeline.authority.graph_kings`, #367);
     - the female rulers;
     - their spellings widened by the weak-sign key (#365) and the TLA links (#366).
   - **A royal woman is a target `dodson_hilton:<D&H id>`.** A woman who reigned is her king
     cluster, as before.
4. **#358's fixes**, which could not change v10's hash-bound tool:
   - `open_page`:
     1. a failed Browserbase re-read keeps the local failure;
     2. the page text, not only the title, survives a navigation, now up to three;
     3. no dead first wait for the load event;
     4. a PDF's `load_event` is `null` (not measured), and the gate counts only a measured
        false;
     5. a Browserbase session is released whatever fails;
     6. the re-read is paced per host;
     7. a loopback, link-local or private-network host is refused, by name or by what the
        name resolves to when it is checked. A redirect onto one has already been fetched when
        it is found, so only its result is withheld; DNS rebinding between the check and the
        browser's own lookup is not covered;
     10. a blocked domain with a trailing dot is blocked.
   - (9) A call whose process exited unsuccessfully decides nothing. The rule lives in
     `validate`, which the runner, a resume's re-check, `decided_record` and the gate all read.
   - The labels (`decision-rule.md`): a case whose sides Stage 1 finds to be different
     entities is a wrong link (b, e, or a wrong control) before anything is uncertain.
   - Each fix has a test.
5. **A royal woman's Stage 2 target** shows her D&H label, source, dynasties and family names.
   It does not show her other spellings or the local PDF's pages (prompt audit,
   `prompt-audit-2026-10-15.md`).
6. **New seeds** for the opaque orders, the reconciliation order and the preflight sample.

The four prompts, the system prompt and the citable-source list are v10's bytes, unchanged. The
`open_page` tool description the model reads is v10's too (tested).

## What is frozen

- **Base commit** `9fa4953` (main after #367). Twelve resolver inputs are pinned by SHA-256 in
  `scripts/compare_arms.py` (`CURRENT_INPUTS`):
  - the claim graph, the normalizer and the linkability resolver;
  - `graph_kings`, `royal_women`, `weak_sign_skeleton` and `tla_links`;
  - D&H's rows, same-woman decisions and female rulers;
  - the TLA names and link decisions.
- **The corpus** is #337's (`hapi-museum-corpus-2026-08-27`, the same archive SHA-256).
- **The mention ledger:** 148,964 mentions, gzip SHA-256 `9bdd60c4…`.
- **Two independent complete runs** are byte-identical in all 15 registered files
  (`results/real-rerun-proof.json`).
- **The review population** (`results/real-review-population-digest.json`), rulers only:

  | Pair | Authority-only gains | Literal-only losses | Retained controls |
  |---|---|---|---|
  | Met–Brooklyn | 2 | 2 | 11 |
  | Met–Harvard | 0 | 0 | 2 |
  | Brooklyn–Harvard | 0 | 0 | 2 |

  That is 19 cases and 21 Stage 1 review units. Stage 2 has 17 proposed targets, 5 of them
  royal women. Every retained control is reviewed: there are fewer than the 9:10 control ratio
  asks for.
- **The decision rule** (`decision-rule.md`): v10's, approved by the project owner on
  2026-10-15 before any model judged any case.

Deterministic headline (rulers, before review): 13 shared nodes on any two-museum shared node
in each arm. Shared records: literal Met 1,981 / Brooklyn 19 / Harvard 2; authority Met
1,955 / Brooklyn 19 / Harvard 2 (`results/real-run-report.json`).

## Review protocol

As #337 v10 (its README, "Review protocol" and "Reconciliation, Stage 2 and scoring"), with the
fixes above:
- one case per call through headless Claude Code (Claude Sonnet 5.5, effort high, the
  subscription);
- two independent reviewers, and a reconciler on disagreements;
- pages read with `open_page` in a real browser, Browserbase for the marked sources and as the
  fallback;
- only pages of citable sources that the call opened and that loaded are citations;
- every call stored complete and re-validated from its events.

Before the run, the preflight check (`scripts/preflight_page_check.py`) opened the citable pages
earlier runs had tried, with the fixed tool and no model (`results/preflight-page-check.json`).

## Known limitations (disclosed)

- **Found after the population was built, and left unfixed** (project owner, 2026-10-15:
  fixing them now would tune the authority on these cases):
  - **A dynasty phrased "second part of Dynasty 11" is not read as a single dynasty**
    (`royal_women.SINGLE_DYNASTY` knows early, late, middle and mid). Brooklyn's "Sunk Relief
    of Queen Neferu" gives only that, so her mention stays ambiguous among the Neferus, and the
    literal "Neferu" link to the Met's Queen Neferu records is an authority loss.
  - **The king graph resolves "Ahmose II" to Ahmose I** (Dynasty 18); Ahmose II is Amasis
    (Dynasty 26). Bare "Ahmose" stays unmatched.
- **A small population.** Four changed cases, all Met–Brooklyn. The decision rule needs at
  least three decided cases in a scope.
- **Royal women rest on a book the reviewers cannot open.** Dodson & Hilton is print-only, so
  a queen's Stage 2 target can be confirmed only from the museums' records and open sources,
  which may draw more `insufficient_evidence` (prompt audit, P3). Read the f counts with this in
  mind.
- **The target's family names are the resolver's cue.** A royal woman is picked partly because
  the record's kings are her family, and her target shows those family names, which may nudge
  a reviewer toward exact identity. Controls and gains go through the same resolver (prompt
  audit, P3).
- **Hidden harness context.** Claude Code adds its own fixed context to every headless call,
  which cannot be stored under subscription auth. It is accepted as in #337 (project owner,
  2026-10-15; measured in `pipeline/pipeline/authority/sources/tla-2018-names/links/probe-hidden-context/`).
- **v10's other limitations stand where not fixed above**, and the next registration inherits
  them (#358):
  - one citation list for both Stage 1 questions;
  - thinking stored as Claude Code's summary;
  - walls recognised by their titles;
  - a call bound to the runner's and tool's source, not to their dependencies;
  - surface text correlating with case type;
  - an unequal sourcing burden.

## Results

Pending: the review run follows this registration.
