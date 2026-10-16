# Rule 14 audit: ruler re-registration v7 prompts and model input (2026-10-16)

Scope: the three v7 changes against the v6 prompts audited in #337 rounds 14-20, #361 and
`../ruler-reregistration-2026-10-15/prompt-audit-2026-10-15.md`: (1) `record_texts` replaces
`shown_records` (builder: `record_texts`, `surface_groups`, `released_stage_2_case`);
(2) per-question Stage 1 citations (`stage-1-reviewer-case-v4.schema.json`); (3) Cleveland
and the Walters in `citable-sources.json`, plus `purl.thewalters.org`. Inspected: the four v7
prompts against their v6 versions, the six composed sample requests (units 032, 066, 070;
cases 004, 006, 029), the private answer key for those samples, the builder, and
`review_protocol.py` (`CITATION_KEYS`, `citation_lists`, `reconciliation_queue`).

Limit: this session had no shell, so I could not compute any statistic over the full 99-unit /
82-case private population. The population-wide correlation checks are listed under "Checks
left to the parent" and are the one thing standing between this verdict and a clean "fine".

Verdict: fine to run on prompt text and design. No P1. One P2 (population-wide proxy check
must be run before the models run; unbounded prompt size). Four P3s.

## 1. `record_texts`, `record_count`, entry order, example URLs: class or answer proxy?

By design, none of these derives from the arm, class, target or answer.

- Entry order is `sha256(OPAQUE_ORDER_SEED | "record-text" | hash(fields))`, and the example URL
  pick/order is `sha256(seed | "example-record" | artifact_id)`. The seed is a constant string
  that does not mention a class. Neither record IDs, counts nor arm order them. The URL cap
  (5 per text) is a constant. Good.
- `record_count` per text partitions counts already shown: in all three samples the entries'
  `record_count` values sum to the existing `distinct_record_count`
  (032 Walters 1+5=6; 066 Met 1+1+10=12; 070 Met 2+1=3). The v6 prompt already disclosed
  `distinct_record_count`, `mention_count` and `exact_mention_variants`. So the new information
  is the full field text and its partition, not a new count.
- The number of entries is a function of how many distinct full texts exist. That is a property
  of the museum data, the same for every class, and bounded by how many variants the museum
  has. Whether it correlates with class in this population (e.g. authority-only gains arising
  where a side has varied spellings) cannot be seen from six samples. The six samples show no
  pattern: the authority-only gain (066) has 3 and 1 entries, the retained control (070) has 1
  and 2, the literal-only loss (032) has 1 and 2. The signal that does separate classes in the
  samples is the mention-string match/differ ("Seti II" vs "Sety II" in 066/case-004; equal
  strings in 032 and 070), and that was already visible in v6 through
  `exact_mention_variants` and `representative_exact_mention`. The prompt neutralises it
  ("match or differ is never, by itself, a basis"). Not new.
- Example URLs: Met IDs and Walters/Cleveland accession numbers are museum-native and carry no
  cross-side correspondence (the two sides' numbering schemes are independent). They were
  shown in v6 too. Not new.

## 2. New identifiers encoding the correspondence?

No. Every added string is a museum field text, a count, or a museum record URL. The Stage 2
target block is unchanged in kind (`cluster-beckerath-*`, `dodson_hilton:*`, member/source ids
as accepted in v10 and the 2026-10-15 audit). `evidence_sha256` is a hash of evidence, not
of the target. `purl.thewalters.org` in the citable list appears in every request regardless
of the case, so it carries no case information; it is needed so a Walters record URL in the
case can actually be cited.

## 3. Coherence of the per-question citation wording

Coherent end to end.

- Reviewer prompt: "for each question separately ... (same_entity_citations,
  useful_granularity_citations). Any outcome other than insufficient_evidence needs at least one
  citation in its own list. For an insufficient_evidence answer, list the loaded citable pages
  you read for that question, if any; ... otherwise an empty list." This matches the v4
  schema (`minItems: 1` only when the question's outcome is not insufficient_evidence; empty
  allowed otherwise) and the key names in `CITATION_KEYS["1"]`.
- Reconciler: `reconciliation_queue` renders each review with `same_entity`,
  `useful_granularity`, `reasoning` and both `*_citations` keys. The v7 reconciler prompt says
  "Each review gives its outcomes, its reasoning and each question's citations", which matches.
  The reconciler's own output stays a single `citations` list per resolution (v3 schema), and its
  prompt still says so ("For each disputed question give the outcome, a concise rationale, and
  the URLs"). No contradiction.
- Stage 2 prompts keep one `citations` list; "Each review gives its outcome, reasoning and
  citations" is unchanged and still true.
- The reconciler is shown citations for undisputed questions too. That was true of the single
  list before; it is not a leak.

## 4. Contradictions introduced by the v7 edits

None found. Checked: "up to five of those records" now applies per text, so a side may show
more than five URLs, and the prompt says exactly that ("each with ... example_record_urls");
"Do not treat a field_text as describing a record until you have opened a record that carries
it" is satisfiable, since each listed URL is a record carrying that text by construction; "the
field texts, record counts and URLs under record_texts are case evidence, not sources" is
consistent with the "record page ... once opened is a source" rule. No leftover `shown_records`
string in any v7 prompt (grep).

## Findings

- P1: none.
- P2-a: unbounded input size. `record_texts` has no cap on the number of entries (only 5 URLs
  per entry). A side with many distinct field texts (long free-text fields, several field paths
  joined into one text) can yield a large block. That is not a leak, but entry count then
  becomes visible case size, and a very large block risks truncation or very long contexts that
  differ across cases. Confirm the maximum before running (see check 2).
- P2-b: the population-wide proxy check (below, check 1) is not yet done; I could not do it.
- P3-a: Stage 2 echo. Now every distinct text is shown, so case-006's Met title
  "daughter of Painedjem I" appears next to the D&H target `family_names: ["Pinudjem I"]`. This is
  genuine record text and genuine authority metadata, the same echo class the 2026-10-15 audit
  accepted (the resolver chose the target using the record's context). It is stronger now
  because the cap no longer hides such records. Not a class proxy if controls and gains pass
  through the same resolver; expect it to push toward exact_identity for those cases.
- P3-b: `record_count` summing to `distinct_record_count` is redundant. Harmless.
- P3-c: Walters/Cleveland field texts carry their own dates and dynasties ("ca. 1200 BCE (New
  Kingdom, Dynasty 19, reign of Sety II)"). This is the museum's own field text, the intended
  evidence, so it is not a leak. Be aware it is richer than v6's for those museums.
- P3-d: the Stage 2 `target_id` and `source_ids` accepted earlier still show the authority
  cluster id; unchanged.

## Checks left to the parent

1. Over all 99 Stage 1 units and 82 Stage 2 cases, join the released queue to the private
   answer key and tabulate by class (authority-only gain / literal-only loss / retained control):
   number of `record_texts` entries per side, `max record_count`, whether any side's entries
   sum above 5 URLs, and number of distinct field paths per entry. Fail if any of these
   separates a class better than the existing `distinct_record_count` / `exact_mention_variants`
   already do, or if any value is constant within a class and different across classes.
2. Report the maximum entry count and total input size of any single released case, and
   confirm it fits the context with the schema and the citable list.
3. Confirm the released queue and the Stage 2 queue contain no field absent from the six
   samples (the forbidden-key and identifier scans in `released_stage_2_queue` and the
   leak digest should still be 0), and that the scorer's rebuild-equality check passes with the
   new `record_texts`.
4. Hash the seven audited files after any edit, and append the "Audited prompt bytes" table.

## Follow-up checks (2026-10-16, by the parent)

On the registered population: 99 Stage 1 units, from `scripts/class_proxy_check.py`
(`results/class-proxy-check.json`). A unit is labelled by every class of the cases whose nodes it
reviews.

- **Item 1 (class proxies, P2-b): none found.** Every new visible feature overlaps across the
  classes. Each value is min / median / max per side:

  | Class | Sides | Entries | Largest record_count | URLs | Field paths per entry |
  |---|---|---|---|---|---|
  | authority-only gain | 26 | 1 / 1 / 6 | 1 / 2 / 431 | 1 / 2 / 14 | 1 / 1 / 2 |
  | literal-only loss | 10 | 1 / 1 / 20 | 1 / 1 / 5 | 1 / 1 / 27 | 1 / 1 / 1 |
  | retained control | 162 | 1 / 1.5 / 9 | 1 / 2 / 2749 | 1 / 3 / 25 | 1 / 1 / 3 |

  The losses' small largest-count follows from their small `distinct_record_count`. v6 already
  showed that, so it is not new information.
- **Item 2 (size, P2-a).** The most entries on one side is 20, and the largest Stage 1 unit is
  6,158 characters of case JSON. There is no truncation risk, so no cap on entries is added.
- **Item 3.** The builder's blinding scan is 0: forbidden keys 0, private identifiers
  0 (`results/real-review-population-digest.json`, `executable_check_counts`). The Stage 2
  release is rebuilt and compared by the scorer (`verify_stage_2_release`), as in #361.
- **P3-a (family-name echo).** Kept, as in the 2026-10-15 audit, and disclosed in the README.

## Delta audit (2026-10-16, stage-1 reviewer citation sentence)

Change: in `stage-1-reviewer-v7.txt` the insufficient_evidence citation clause now reads "list
the loaded citable pages you read for that question. If any citable page you opened loaded,
every list must name at least one; give an empty list only if no citable page you opened
loaded." It replaces the "...if any; if no citable page loaded, give an empty list" wording.

- **Leak: none.** The sentence is a generic format rule. It names no case value, id, class or
  count.
- **Coherence with `review_protocol.validate`: yes.** The validator rejects any empty list when
  some opened page loaded with both requested and final URL citable ("cites nothing although a
  citable page it opened loaded"). The new sentence states that rule, with the same
  definition of a usable page as earlier in the prompt (loaded, citable final_url). The old
  wording ("if any") contradicted the validator and would have caused retries on exactly the
  uncertain answers, which is an output-selection bias; the edit removes it.
- **Coherence with schema v4: consistent, not identical.** The schema requires `minItems: 1`
  only for a non-insufficient outcome and cannot know which pages loaded. The prompt is
  stricter than the schema because the validator is, and a schema-valid empty list can still be
  rejected. This is the intended layering.
- **Pressure to cite an irrelevant page: small P3.** The first sentence says "pages you read
  for that question" while the second says every list needs one if any citable page loaded, so
  a reviewer whose only loaded page concerns the other question must still list it. The
  consequence is cosmetic: an insufficient_evidence answer is not a basis, and the citations
  are not scored as support. The same validator rule applied to the single list in #337/#361.
  Optional tightening, which I do not recommend because it would change the hashed bytes
  again: "the loaded citable pages you read, even if they did not settle it".
- **P3: unstated second validator rule.** The validator also rejects an empty list when the
  reviewer never tried a citable page ("cites nothing without having tried a citable page").
  The prompt asks for research but never states this. It is rule-based and leak-free, and the
  opens are mandated by the research sentences, so no edit is needed.
- **Hash:** the v7 reviewer prompt bytes changed; the "Audited prompt bytes" table must be
  generated after this edit. No other prompt changed, and the reconciler prompts are
  unaffected (their own single `citations` list is unchanged).

Verdict for the delta: fine to run, no P1.

## Audited prompt bytes

What the model reads in this registration, as audited above and in the delta audit:
- the four v7 prompts (#361's v6 with the record-text description, the per-question citation
  instruction and its validator-aligned sentence);
- the unchanged system prompt;
- the citable-source list (Cleveland and the Walters as case museums);
- the browser server, whose `open_page` description is #361's (tested);
- the Stage 1 reviewer schema v4.

| File | SHA-256 |
|---|---|
| `stage-1-reviewer-v7.txt` | `c97e14ba4c13b2063483f0c9dc722cfc06ea1d0fb3223ab0fbd6b2474ef7b277` |
| `stage-1-reconciler-v7.txt` | `5deb06f3e6092a8b3b7e484978e862babe22f2b3f929a5730958034899bbe736` |
| `stage-2-reviewer-v7.txt` | `1d6963146df04ace27102c3f7d90036f15004c984adcab2bf4aeb7996d654438` |
| `stage-2-reconciler-v7.txt` | `9e086d2ff7e3bb6972fb85864dbfdf460b3d3778af62c9d7eba7306e3a64ab04` |
| `review-system-v4.txt` | `290ab72e433d8cbbd167d4f906e874fee1d6994c38201bfe10d01e7cd3116451` |
| `citable-sources.json` | `4bd37e0670ecbeccd441b22e311a69e09cfe2925617a8fc1e00272396a4721d5` |
| `open_page_server.py` | `2ce814c976a3eaee31bf07614e6c82a65c8beb21453cc39b2bcc42e182264244` |
| `stage-1-reviewer-case-v4.schema.json` | `0b94e388454cd8c56506aac4e9c2cb856471c9813ef103da59cedb97904490be` |
