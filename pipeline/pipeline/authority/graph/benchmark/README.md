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

All LLM numbers are from the **de-leaked, precision-first prompt** (no source ids,
no named answer pairs, opaque shuffled labels — constitutional rule 14). Earlier
"0.92/0.98" figures were measured on a *leaky* prompt and are discarded as invalid.

| Matcher (Leprohon×Beckerath) | aligned | Pairwise P | Pairwise R | F1 | false merges |
|---|---|---|---|---|---|
| Exact (deterministic) | 336 | **1.00** | 0.33 | 0.50 | 0 |
| LLM name-only, unguarded | 296 | 0.98 | 0.89 | 0.93 | 1 |
| **LLM name-only + guard** | 296 | **1.00** | **0.89** | **0.94** | **0** |
| LLM rich-context + guard | 296 | **1.00** | **0.89** | **0.94** | 0 |

**Headline: precision 1.00 / recall 0.89** (LLM + cannot-link guard, Wikidata
silver, aligned set) — zero measurable false merges at 0.89 recall, with
escalation doing the precision work (the "missing > false" profile, ADR-020 §6).
The table is identical for name-only and rich context **because the silver set
only covers well-known rulers** (see the rich-context note below).

Two findings worth recording:
- **The prompt leak was *hurting* precision.** The leaky-prompt id-tell caused
  false merges where dynasty-sequence aligned but the rulers differ; the
  de-leaked precision-first prompt is *more* precise (0.92 → 0.98 unguarded), and
  the guard takes it to 1.00. Recall (47 TP / 6 FN) was never affected by the leak.
- **Rich context helps — where the name doesn't already suffice — but the silver
  benchmark is blind to it.** On the aligned set the numbers are identical, but
  that set is the ~296 *famous* rulers, for whom the display name is already a key
  into the model's parametric knowledge (it knows Amenhotep III = Amenophis III,
  the reign, the prenomen, from training). Reading the persisted reasoning, rich
  context made **15 extra correct matches on obscure rulers** by using the
  structured evidence — e.g. *Nakhthorhebyt → Nektanebôs* disambiguated among
  three near-identical late-period kings **by reign dates**, and *Sheshonq IIa →
  Schoschenq II.* matched **by prenomen** ("Heqa-kheper-re"). Those rulers don't
  align to Wikidata, so they never count as true positives — the benchmark
  structurally undersells context. **Rich context is a kept option (not retired),
  recommended where the model's parametric knowledge is weak (obscure rulers);
  name-only remains the default for cost on famous-heavy sets.** Properly
  measuring the gain needs a gold set that includes obscure rulers (ADR-020 Tier 3).

The exact matcher is precision-perfect but misses every cross-language pair
(Khufu/Cheops, Amenhotep I/Amenophis I., …); the LLM nearly triples recall
(0.33 → 0.89).

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

Resolution is `poc.resolve_matches` — order-independent (no incumbent, no
re-prompt; Constitutional rule 2) and precision-first (ADR-020 §6):

- **Hard cannot-link guard** (`matcher/constraints.cannot_link` + `_guarded_union`):
  refuses any union placing two cannot-link rulers in one component (checked across
  all members, so a single bad edge can't metastasize). Hard rules: disjoint reign
  Time-Spans, and same-source-distinct rows (exempting phase-suffix siblings and
  documentary `same_person_as` links).
- **Uniqueness escalation (Fix 1):** if two DISTINCT rulers from one source both
  claim a single target (and aren't the same person), ALL the clashing edges
  escalate — set-based, so it's order-independent and never auto-keeps an
  incumbent. (Catches the Ninetjer/Nebre → Kaiëchós error.)
- **Regnal-mismatch escalation (Fix 2):** a regnal-number difference escalates
  rather than hard-blocking — sources number the same name differently
  (Ahmose III = Amosis II = Amasis, shared throne name Khnemibre), so a hard block
  would *false-reject* true matches.

Result above: precision **0.98 → 1.00** at zero measurable recall cost; the
held-apart / clashing / regnal cases become explicit human escalations rather than
silent accepts or rejects. (Ground-truthed via web research — see the matcher
discussion; only 1 of 3 flagged "failures" was a real model error, and it was a
uniqueness clash.)
