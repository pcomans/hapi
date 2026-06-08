# Matcher benchmark — precision / recall vs Wikidata (silver)

Measures the cross-source ruler matcher against a **Wikidata silver standard**
(ADR-020). Reproduce with **no API calls** — matcher outputs are read from disk
(Constitutional rule 13: never re-run an LLM step to score a past decision):

```bash
cd pipeline && uv run python run_benchmark.py   # writes benchmark_results.json
```

## Results

Graded against Wikidata QIDs, **end-to-end** (escalations/misses count against
recall), on the subset of rulers that align to a QID.

| Matcher | aligned | Pairwise P | Pairwise R | F1 | B-cubed F1 | false merges | missed |
|---|---|---|---|---|---|---|---|
| Exact (deterministic) | 336 | **1.00** | 0.33 | 0.50 | 0.91 | 0 | 63 |
| LLM (Leprohon×Beckerath) | 296 | 0.92 | 0.89 | 0.90 | 0.98 | 4 | 6 |
| **LLM + cannot-link guard** | 296 | **0.98** | **0.89** | **0.93** | 0.99 | 1 | 6 |

**Headline (LLM + guard): precision ≈ 0.98, recall ≈ 0.89.** The cannot-link
guard (regnal-numeral mismatch, same-source-distinct rows, disjoint reign spans
— see `matcher/constraints.py` + `poc.guarded_same_entity_clusters`) lifts
precision **0.92 → 0.98 at zero recall cost**, holding apart 5 contradictory
merges (Menkheperre/Pinudjem, Iuput I/Auput II, …). The one remaining false merge
(Aper-anati/Bêôn) has no structured discriminator — that needs bidirectional
agreement (advisor Priority 3) or post-cluster escalation (Priority 4).

The LLM nearly triples recall over exact name matching (0.33 → 0.89) at a small
precision cost:
- **4 false merges** (over-merges): Nebre/Ninetjer, Iuput I/II, Auput II./Iuput I,
  Aper-anati/Bêôn.
- **6 missed** links (+ 5 escalations also counted as misses, end-to-end) hold
  recall at 0.89 — mostly Libyan-period spelling variants Wikidata also splits.

The exact matcher is the precision ceiling (1.00, zero false merges) but misses
every cross-language pair (Khufu/Cheops, Amenhotep I/Amenophis I., …).

## Method

1. **Answer key** — the 518 entities with `P39 = Q37110` (position held = pharaoh),
   with en/de labels + aliases, cached on disk (`wikidata_pharaohs.json`).
2. **Align** each source row to a QID via Wikidata's *own* curated aliases
   (normalized name; parenthetical-strip fallback for phase rows). Same QID ⇒ same
   entity. Alignment uses Wikidata's curation, **not** our matcher (fair test).
3. **Gold = closed-world equivalence classes** over the aligned universe (group by
   QID). Within the universe every pair is decided; unaligned rows are excluded.
4. **Compare** the matcher's predicted clusters (connected components over
   `hapi:same_entity_as`) to the gold classes → **pairwise** TP/FP/FN and
   **B-cubed** P/R (which penalises over- and under-merge).

## Honest qualifiers

- **Silver, not gold.** Wikidata isn't independent of the same scholarly sources
  and is weakest on contested identities — directional, not authority-grade. A
  committed adjudicated gold set (ADR-020 Tier 3) would firm these up.
- **Alignable subset only** — ~296–336 of ~620 rows align; the rest (spelling gaps
  like "Sheshonq"/"Schoschenq", obscure Manetho-only names) drop from the
  denominator.
- **Leprohon×Beckerath only.** The 3-way (Kitchen) LLM run isn't scored here
  because its edges weren't persisted at the time. `persist.py` /
  `threeway_edges.json` now fix that, so the next 3-way run is disk-evaluable
  without re-spending.

## Precision guard (implemented)

The contradictory-merge guard ADR-020 § Consequences called for is implemented:
deterministic **cannot-link constraints** (`matcher/constraints.py`) +
**guarded clustering** (`poc.guarded_same_entity_clusters`) that refuses any union
placing two cannot-link rulers in one component (checked across all members, so a
single bad edge can't metastasize). Rules: regnal-numeral mismatch (a structured
discriminator, not an edit-distance — ADR-009-safe), disjoint reign Time-Spans,
and same-source-distinct rows (exempting phase-suffix siblings and documentary
`same_person_as` links). Result above: 0.92 → 0.98 precision, zero recall cost.
Held-apart conflicts are the natural input to the escalation path (advisor P4).
