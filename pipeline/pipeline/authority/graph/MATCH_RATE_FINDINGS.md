# Cross-source match-rate findings (Leprohon × Beckerath)

> **⚠️ Not reproducible from this branch.** Every number below comes from a *live*
> LLM run. To keep this POC PR slim, the multi-hundred-KB run artifacts
> (`match_rate_result.json`, the per-pick clean-edge dumps, `benchmark_results.json`)
> are **not committed**, so these figures are **directional, not branch-verifiable**
> — do not cite them as established results. Reproduce with
> `cd pipeline && uv run python run_match_rate.py` (constraint-narrow + LLM pick)
> and `run_benchmark.py` (silver scoring); a live run now persists the *full*
> per-candidate interaction (prompt + raw response + model snapshot) to
> `reviewer_outputs/<run_id>.jsonl` (Rules 1 & 13), which is what a committed run
> must include before any of these numbers become authority-grade.

Constraint-narrowed + LLM-pick matching between the two POC sources, run via
`pipeline/run_match_rate.py`.

## Headline

| Metric | Constraint-narrow + LLM | + escalation | Exact name match |
|---|---|---|---|
| **Beckerath coverage** | **88.0%** (146/166) | **87.3%** (145/166) | ~6% |
| Leprohon match rate | 39.5% (156/395) | 39.0% (154/395) | ~6% |
| Escalated to human | 0 | **5** | — |
| API errors | 0 | 0 | — |

**The meaningful number is ~88%** — of Beckerath's 166 rulers, ~146 found a
Leprohon counterpart. The 39.5% Leprohon figure is low for a structural reason,
not a matcher failure: **Leprohon lists ~2.4× more rulers** (395 vs 166), so
~230 Leprohon entries (anti-kings, ephemeral SIP/TIP/Ptolemaic-detail rulers)
have no Beckerath counterpart at all. Against the exact-name baseline (~6%),
constraint-narrow + LLM is a **~14× lift**.

**With escalation enabled** (added after the first run), coverage barely moves
(88.0% → 87.3%, −0.7pp) while **5 genuinely-contested identities correctly route
to the human queue instead of being auto-resolved**: Aha (the Aha/Menes/Narmer
"who is Menes" problem), Sekhemib (Sekhemib/Peribsen), Sanakht (uncertain
placement, possibly = Nebka), and Neferneferuaten + Smenkhkare (the Amarna
succession). The model's escalation choices map precisely onto real
Egyptological controversies — escalation removes over-confident resolution of
disputed identities at negligible cost to coverage.

## Method (why not edit distance / token overlap)

ADR-009 forbids surface-string acceptance: edit distance and token overlap are
*anti-correlated* with identity for Egyptian royal names. The regnal numeral
discriminates identity but is a tiny surface difference (Thutmose III vs IV =
distance 1, different kings); the stem transliteration preserves identity but
varies wildly (Thutmose/Tuthmosis, Amenhotep/Amenophis). So this never scores
names — it **constraint-narrows by shared dynasty** (the only structured signal
both sources carry; Leprohon dates no reigns) and the **LLM picks the match from
the narrowed set** (ADR-018 § Implications for matching). 395 pick calls, one per
Leprohon ruler in a shared dynasty.

## Quality signals (good)

- Matched across **naming traditions, not just spelling**: Manetho's Greek names
  ↔ archaeological Egyptian (Den == Usaphais, Adjib == Miëbis, Qaa == Biëneches).
- **Phase-splits handled many-to-one** (9 Beckerath rulers matched by >1 Leprohon
  row): Mentuhotep II (a/b/c) → one; Amenemhat I (a/b) → one; Thutmose III (a/b)
  → one. Exactly the ADR's intra-source aliasing.
- The **20 unmatched Beckerath (12%) are mostly genuine gaps**, not misses:
  Manetho-only names with no clean archaeological counterpart (Iti, Ita,
  Thamphthis, Salitis, Apachnas) and the famously-unresolved Libyan-period
  Dynasty 22/23 numbering (Osorkon III/IV, Takelot III, Petubastis I, Rud-amun).

## Honest caveats

1. **This is recall/coverage, not validated precision.** No gold-standard match
   set exists, so not all 156 matches are certified correct. Dynasty 1 and 18
   spot-checks are strong, but a labeled set is needed for a precision claim.
2. **Escalation is now enabled and confirmed live.** The first run lacked an
   `escalate` path and resolved contested identities as confident matches; the
   `escalate` option (see `constraint_narrowed.py`) was added and the full run
   re-done. Confirmed against the real API: the pick escalates exactly the 5
   genuinely-contested identities listed above (and, on the Dynasty-18 sample,
   Neferneferuaten + Smenkhkare). The wiring is also covered offline by
   `test_contested_identity_is_escalated_not_matched`. These numbers are still
   recall/coverage, not precision-validated — but the disputed cases are no
   longer silently resolved.

## Precision / recall vs Wikidata (silver standard, ADR-020)

Measured against the Wikidata QID crosswalk (silver, not gold), **de-leaked
precision-first prompt** (rule 14). See [`benchmark/README.md`](./benchmark/README.md)
for the full table; headline (LB, aligned set):

| Matcher | aligned | pairwise P | pairwise R | F1 | false merges |
|---|---|---|---|---|---|
| Exact (deterministic) | 336 | **1.00** | 0.33 | 0.50 | 0 |
| LLM name-only + cannot-link guard | 296 | **1.00** | **0.89** | **0.94** | 0 |

The "~88% coverage" headline above was an upper bound; **measured recall against
the silver key is 0.89 at precision 1.00** (zero false merges after the guard),
with escalation doing the precision work (ADR-020 §6, missing > false). Earlier
"0.92/0.98" figures were leaky-prompt artifacts and are discarded. **Rich context
helps on obscure rulers** (e.g. disambiguating late-period kings by reign dates /
prenomen) but the Wikidata silver set only covers famous rulers — where the name
already suffices — so the benchmark can't see the gain; it is a kept option, not
retired (see [`benchmark/README.md`](./benchmark/README.md)). Only the alignable subset is scored (≈296–336 of
~620); Wikidata is silver, so these are directional, not authority-grade (ADR-020).

## Bottom line

Measured against Wikidata silver (de-leaked, precision-first prompt), the LLM
matcher + cannot-link guard reaches **precision 1.00 / recall 0.89** on the
aligned set — vindicating the ADRs' thesis that surface-string metrics are the
wrong tool. **"~88% coverage" is an upper bound, not recall** (ADR-020:
never report coverage as recall); the trustworthy figure is the silver-measured
recall above. These are silver, not authority-grade — the escalation path
(missing > false) plus a committed gold set (ADR-020 Tier 3, incl. obscure
rulers) are needed before treating clusters as authority data.
