# Rule 14 audit: #361 Stage 2 royal-woman target rendering (2026-10-15)

Scope: the new Stage 2 proposed-target shape for Dodson & Hilton (D&H) royal women
(`compare_arms.py` `load_current_resolvers`, released by `build_review_queue.py`
`released_stage_2_case`), checked against the unchanged v6 Stage 2 reviewer prompt. The
released sample inspected has Nefertiti, Maatkare A (3 cases), Tiye A and two king targets.
The private museum text was not available, so any check that needs it is listed under
"Checks left to the parent".

Verdict: fine to run. There is no P1. Two P2 fixes are recommended (drop `pdf_pages`; decide
on `labels`). The unchanged prompt needs no edit, and adding the explanation of the D&H
letter is optional.

## 1. Leakage

No field of a royal-woman target reveals the answer or the case class.

- Every field is a property of the authority record (`woman.*`). None is derived from the
  museum evidence or from whether the case is a control or an authority gain. Cases in both
  classes render the same shape, and the same target renders identically across cases
  (Maatkare A x3).
- `target_id` "dodson_hilton:…" and `source` only name the authority. They are the same
  class as the king `cluster-beckerath-…` id, which v10 already accepted. P3: `target_id`
  adds nothing beyond `source`. Leave it for parity with the king shape.
- The D&H letter in "Maatkare A" is the authority's own label. It says which authority
  entry is proposed, not whether the museum denotes her. It is a legitimate part of the
  proposal (see section 3).
- `family_names` is the closest thing to a leak. The resolver chose this target partly
  because the record's own kings and dynasty fit it (`resolve_royal_woman(...,
  record_king_ids, record_dynasty)`). So where a museum record also names "Pinudjem I",
  the target's `family_names` will echo that other mention. This is not a class proxy:
  controls and gains pass through the same resolver. It is authority metadata a scholar
  would want to compare with the record, and it is no more an answer than a king
  cluster's dynasty. It does make the resolver's cue visible, which nudges toward
  exact_identity when the echo is present. Kept (P3, below).
- P2: `source_citations[].pdf_pages` ("142-145", "190-194"). These are page numbers of the
  project's local PDF, not of the printed book. The book cannot be opened (it is not in
  `citable-sources.json`; `not_citable_but_standard` lists the print references). The
  numbers are unusable evidence and invite a search for a scan. Archive.org is excluded, so
  it is harmless as a citation, but it is noise and hints at a repository artifact.
  Rewrite: release only `edition` and `source`, and drop `pdf_pages` via
  `UNRELEASED_TARGET_METADATA` or a per-representation filter in `released_stage_2_case`.
  Alternatively replace it with a book-page range if one is available.

## 2. Asymmetry versus king targets

King targets show `member_ids` and `source_ids` (3 sources, corroboration visible). Royal
women show one source, a print book, with `dynasties`, `family_names` and `labels`.

- The direction of the bias is not clear-cut and is probably small. The king shape signals
  triple corroboration, which is a stronger "authority agrees" cue than a single book. The
  royal-woman shape signals the opposite (single source, unopenable), and the reviewer is
  told to treat target metadata as case evidence only. The likely effect is more
  `insufficient_evidence` for queens, not more exact_identity. That is not an answer leak.
  It does raise the f (uncertain) count, which the decision rule caps at one third of a
  scope's changed cases, so expect it and report it. P3.
- P2: `labels` lists the bare spelling ("Maatkare") next to "Maatkare A". Kings render no
  alias list. For a case whose museum string is the bare "Maatkare", `labels` tells the
  reviewer that the authority registers this exact spelling as the proposed woman's name.
  That is the resolver's own matching rule and is not evidence of identity. It also
  advertises that the bare name is ambiguous, which is the useful half. Either drop
  `labels` for parity with kings (`label` is kept), or keep it and rely on the prompt's
  "match or differ is never, by itself, a basis". Recommendation: drop it. The
  disambiguation need is met by `family_names` and `dynasties`.
- `entity_type: "ruler"` for queens is the schema value; fine. The `dynasties` and
  `family_names` values give the reviewer the authority's own disambiguators to compare
  against museum records, so they favour correct different_identity calls when two
  same-name women exist (Maatkare A and B). Keep them.

## 3. Prompt coherence with a print-book authority

The unchanged text reads coherently.

- "its label and the metadata of its authority record" matches both shapes.
- "The case's structural facts (…the target's label and metadata)… are case evidence, not
  sources" already covers the case where D&H cannot be opened. The reviewer must settle
  identity from museum records and other citable pages. Kings are in the same position
  (Beckerath and Leprohon are not citable), so there is no new rule.
- "A source can show only what it documents, at the granularity it documents it" does not
  conflict with the D&H letter. If a museum page says only "Maatkare", it does not settle
  which woman of that name is meant, and the correct outcome is insufficient_evidence.
- No change is required. The letter explanation is optional: the existing
  "match or differ is never, by itself, a basis" and "same entity under a different
  spelling… is exact identity" already prevent the failure mode (treating the missing "A"
  as a difference). Adding a sentence such as "A trailing capital letter in a label
  separates women of the same name in the authority's own scheme; it is not part of the
  ancient name" is rule-based and leak-free. But editing v6 voids the "unchanged v10
  prompts" claim and forces a new prompt version, hash and re-audit. Recommendation: do not
  edit; record in the README that the letter is covered by the existing rules.

## Findings

- P1: none.
- P2: (a) drop `source_citations[].pdf_pages` from the released royal-woman target;
  (b) drop `labels` for royal women, or document why it is kept.
- P3: (a) `family_names` echoes the resolver's context cue, which is accepted as legitimate
  authority metadata; (b) expect more insufficient_evidence for queens; (c) `target_id`
  adds nothing beyond `source`; (d) optional prompt sentence on the letter, not
  recommended because it breaks prompt reuse.

## Checks left to the parent (the private text was unavailable)

1. In the released queue, confirm no museum field_text contains a D&H page number or the
   string "Dodson" (a `grep -c` on the released JSON).
2. If P2(a)/(b) are applied, rebuild the released queue and confirm the `forbidden`
   recursion in `released_stage_2_queue` and the scorer's rebuild-equality check still pass.
   The queue hash changes, so re-pin it before any model call.
