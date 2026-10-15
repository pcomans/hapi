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
   was no cue. Each mention also carries its record's dynasty, as the canonical record gives
   it. The span after a cue is v10's: a quote before the name stays in it
   ('"Nefertity'), and the mention reader refuses it, which is a missed link and never the
   kings (a first draft stripped the quote, and the resolver then read the name as uncued; code
   review).

   `scripts/ledger_diff.py` compares this ledger with v10's on the frozen corpus
   (`results/ledger-diff.json`, tested):
   - 93 new mentions, each after a royal-woman cue;
   - none of v10's lost or changed (148,871 → 148,964);
   - none of the 239 royal-woman-cued mentions is one the resolver would not read as cued.

   The extractor still reads no authority file. A test checks that its cues match the
   resolver's on a fixed list of cue phrases.
3. **The authority arm** (`scripts/compare_arms.py`, `RulerAuthority`):
   - **A mention after a royal-woman cue** resolves among the royal women and the female
     rulers (`royal_women.resolve_royal_woman`), never among the other kings. Its context is
     the record's own kings (what the record's uncued ruler mentions resolve to) and the
     record's dynasty (`royal_women.single_dynasty`).
   - **Every other ruler mention** resolves among the kings by v10's method, on the current
     claim graph (item 7).
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
7. **The king data is today's, not v10's.** v10 froze the claim graph at 1d35337. Since then:
   - #357 merged duplicate king entries from the ruler escalation queue;
   - #362 changed only how `run_linkability.py` finds its repository.

   Both are in `CURRENT_INPUTS`. The kings' method is unchanged; their data is not (see the
   Result).

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
- **The mention ledger:** 148,964 mentions, gzip SHA-256 `98ec263a0aa2…`.
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
- **A node is judged from at most five records per side** (v10's protocol: the prompts, v10's
  audited bytes, state the cap).
  - Reviewers see every surface string of a side, with its count, field paths and roles
    (`exact_mention_variants`); only each record's own context is capped. On the Met side the
    four changed nodes hold 27, 31, 2 and 31 records.
  - What the cap can hide is a homonym: one of the shown strings naming a different ruler in a
    record the reviewers do not see.
  - The decision rule counts cases, one label per node, so the verdict rests on judged nodes.
    The score's record figures count every record on those nodes, so they measure node
    membership, not record-by-record judgments. The score says so beside them
    (`record_figures_note`; Codex review of #368).
  - Showing every record would change the audited prompts, so it is left to the next
    registration (#358).
- **v10's other limitations stand where not fixed above**, and the next registration inherits
  them (#358):
  - the five-record cap per side (above);
  - one citation list for both Stage 1 questions;
  - thinking stored as Claude Code's summary;
  - walls recognised by their titles;
  - a call bound to the runner's and tool's source, not to their dependencies;
  - surface text correlating with case type;
  - an unequal sourcing burden.

## Result (2026-10-15): CONTINUE, rulers Met–Brooklyn

`results/real-adjudicated-score.json`, from `decision-rule.md` applied in code:

| Step | Numbers | Outcome |
|---|---|---|
| Calibration | 0 of 15 retained controls uncertain or wrong (limit 20%) | passed |
| Safety | b = 0 of 2 authority gains | passed |
| Utility | ruler, Met–Brooklyn: a 2, b 0, c 0, d 1, e 1, f 0 (a + e = 3 > d = 1; 4 decided) | qualifies |

**The four changed cases** (case and Stage 1 unit IDs as in the private records):
- **Two gains (a).** The authority links two spellings of one king that plain text keeps apart:
  - case-010, unit-016: the Met's "Haremhab" with Brooklyn's "Horemheb";
  - case-013, unit-005: the Met's "Niuserre" with Brooklyn's "Ni-user-re".

  Stage 2 found the proposed king the exact identity in both. Both were v10's a's too (case-069
  and case-062).
- **A false link removed (e)**, case-016, unit-008: plain text's "Ahmose" node. It is v10's e,
  unchanged (case-008, the same literal node).
  - The Met side is mostly "reign of Ahmose" (the king) but includes "Hatshepsut's Mother, Queen
    Ahmose" (met-566763). Brooklyn's side is "Queen Ahmose, Mother of Hatshepsut". The reviewers
    found the node joins different entities.
  - **The authority also missed a real queen-to-queen link here.** Both "Queen Ahmose" records
    are queen-cued, but "Ahmose" meets D&H's "Ahmes" only on the weak-sign key. Its
    three-consonant key needs a named family king, and neither record gives one as a ruler
    mention: the Met's reign field is unparsed, and Brooklyn's "Mother of Hatshepsut" is no cue.
    Both stay unconfirmed.
  - **The verdict hangs on this case.** Read as a loss (d), the scope would not qualify (a + e
    = 2 against d = 2).
- **A correct link lost (d)**, case-009, unit-021: Queen Neferu.
  - The Met's Queen Neferu records (her tomb at Deir el-Bahri) and Brooklyn's "Sunk Relief of
    Queen Neferu" are one queen.
  - The Met records resolve to Neferu II through their king, Mentuhotep II. Brooklyn's record
    gives no king and a dynasty the resolver does not read ("second part of Dynasty 11"), so it
    stays ambiguous among the Neferus.
  - This is the gap found after the population was built and left unfixed (limitations). It was
    v10's case-095, also d.

**Against #337 v10's rulers, case by case** (Met–Brooklyn; v10: a 2, d 5, e 1, f 1). The literal
node IDs are stable on the frozen corpus, so the cases can be followed:
- **v10's two a's are a again**, and its e (Ahmose) is e again.
- **Four of v10's five d's are no longer losses**; this run reviewed them as retained controls,
  each judged correct.
  - Nefertiti (v10 case-020) and Tiye (case-083) now link through the royal women
    (`dodson_hilton:Nefertiti`, `dodson_hilton:Tiye A`).
  - Apries (case-096) and Userkaf (case-098) now link among the kings through #357's merges.
    On v10's claim graph each name is ambiguous between two duplicate entries
    (`cluster-beckerath-26.04` / `kitchen-26.04`; `leprohon-leprohon-5.01` /
    `pharaoh_se-Userkaf`). On today's graph each resolves to one cluster.
- **The fifth d, Neferu, is d again.**
- **v10's f is gone.** It was case-067, Brooklyn's "Shabty of Queen Maatkare" merged with
  Hatshepsut, a false merge that this registration's rule labels b. This run sends the
  queen-cued Maatkare to `dodson_hilton:Maatkare A`, which Stage 2 judged the exact identity
  (control case-011).
- **The result:** rulers in Met–Brooklyn, which did not qualify in v10 (and were unsafe under
  this registration's rule), now qualify.

**What the controls judge.** "0 of 15 controls uncertain or wrong" judges each control's authority
node (`classify_case`).
- Two controls' literal nodes were judged wrong: plain text's "Maatkare" joins the 21st-dynasty
  God's Wife with Hatshepsut (Maatkare is her throne name).
  - In unit-003 (Met–Brooklyn, case-011) the reviewers agreed on "different entities, too
    broad".
  - In unit-014 (Met–Harvard, case-004) the reconciler settled it the same way.
- In both, the authority's node (Maatkare A) was judged exact.
- In useful nodes over the whole population, the authority has 17 against the literal arm's 14
  (+3): +2 in Met–Brooklyn and +1 in Met–Harvard, where no case changed
  (`adjudicated_arm_outcomes`).

**Caveat.** This is a small census of the selected population (4 changed cases, 15 controls),
not a sample estimate, and it carries the weight of four cases. Its margin is narrow and rests on
both changes since v10:
- **The royal women alone** (Nefertiti, Tiye, Maatkare) would leave d = 3 (Neferu, Apries,
  Userkaf) against a + e = 3, which does not qualify.
- **The king merges alone** would leave v10's Maatkare false merge, a b under this rule, which
  makes the scope unsafe.
- **Read the Ahmose case as a loss**, and the scope does not qualify either.

**Review.** All calls ran on Claude Code (Claude Sonnet 5.5), on the subscription.
- **Stage 1:** 21 units; the two reviewers agreed on both questions in 20. The reconciler
  settled unit-014 with two cited overrides.
- **Stage 2:** 17 proposed targets, 5 of them royal women; the reviewers agreed on all.
- **Calls:** every call valid on its first attempt but one. Reviewer A's first Stage 2 call on
  case-011 (Maatkare A) opened a blocked domain (Wikidata), which fails a call, and the case was
  asked again.
- **Pages:** in the deciding calls every citable page opened loaded, locally or in Browserbase
  (gate deviations 0.0 in every class, `results/real-page-load-gate.json`). No page needed a
  Browserbase re-read after a local failure, and one Met page was read before its load event
  fired.
- **Records:** private, in `dropbox/hapi-361-review-2026-10-15/`, bound by
  `results/real-review-records.json`: 43 Stage 1 and 35 Stage 2 stored calls. The reason is
  #337's: they carry museum text verbatim.
