# Weak-sign key: hill-climb on the TLA names (2026-10-15)

The royal-women resolver's third tier (`pipeline/pipeline/authority/weak_sign_skeleton.py`)
matches spellings of one name across conventions. This climb tuned it against an independent
ground truth, the Thesaurus Linguae Aegyptiae's personal and royal names
(`sources/tla-2018-names/`, CC BY-SA 4.0). In that set each lemma's transliteration and its
German and English renderings are one name in several conventions
(`Jꜥḥ-ms.w-nfr.t-jr.j` / Ahmes-Nefertari / Ahmose-Nofretari). No museum record was read: the
ruler evaluation that will use the key (#361) reads Met, Brooklyn and Harvard records, and the
TLA is none of them.

## Protocol (fixed before the first iteration)

- **Split.** By a hash of the TLA id (`measure.py`): train 60%, validation 20%, test 20%.
  Rules were chosen by looking at train misses only. Validation was a check. Test was scored
  once, at the end, for the starting and the final key.
- **Metrics.**
  - *Recall:* of the pairs of renderings within one lemma that both have a key, the share
    whose keys meet.
  - *Strong merges:* names (distinct transliterations) that share a key with a name differing
    in a strong consonant. The weak signs ꜣ ꜥ j y w, the vowels and a final t don't count,
    since the key drops them by design.
- **Acceptance.** A change must:
  - be a documented rendering convention, never a fix for one name;
  - raise train recall;
  - not raise strong merges on train or validation;
  - not lower validation recall.
- **Not in reach by design:** Greek forms (Sesostris, Cheops, Thutmosis), which are other
  names, and renderings that add a second name (Djedkare-*Isesi*).

**Metric correction, before iteration 1 was accepted.** Iteration 1's new strong merges were
ẖ against ḫ. English writes both "kh", and the committed fold already merges them, so the
strict metric could not tell a fold from a bug. From then on, strong merges ignore the
consonant pairs English renderings never distinguish (ḥ/h, ẖ/ḫ, q/k). This was applied to every
iteration, including the baseline, and is the only change to the metric.

## Iterations

Train / validation; strong merges count names.

| # | Change | Recall train | Recall val | Strong train | Strong val | Decision |
|---|---|---|---|---|---|---|
| 0 | Starting key (review fixes, 8c1cca9) | 79.34% | 81.60% | 9 | 0 | baseline |
| 1 | Compose Unicode (NFC) before the fold: a capital H̱ has no precomposed form, so it read as h | 81.67% | 83.13% | 6 | 0 | **accepted** |
| 2 | In a transliteration (a sign only transliterations have, or = ⸗), j is always the weak sign: ṯ and ḏ are letters of their own there | 87.13% | 88.96% | 6 | 0 | **accepted** |
| 3 | z as s (TLA `Z-n-wsr.t` Senwosret) | 88.43% | 90.02% | 34 | 7 | rejected: merges distinct names (Semen / Sa-Amun, Seneb / Zenebet) |
| 4 | ṯ (tj) as t (TLA `Mnṯ.w-ḥtp.w` Mentuhotep) | 88.86% | 89.42% | 14 | 0 | rejected: merges distinct names (sṯf / stf) |

**Stopped there.** The remaining train misses are Greek forms, double names, German ḥ/ḫ
renderings ("Iach-mesu"), gemination ("Ramses"/"Ramesses") and German "th" for t. None of
these is a convention the key could adopt without merging names it now keeps apart. "th" is t
+ h in Hathor and Sithathor.

## Result (test split, scored once)

| Key | Recall | Strong merges |
|---|---|---|
| Starting (iteration 0) | 78.59% (481 / 612) | 2 names |
| Final (iteration 2) | **86.44%** (529 / 612) | 2 names |

- The gain carries over: +7.8 points on train, +7.4 on validation, +7.8 on test.
- The two names still merged on test (`njkꜣwḥrw`, `njẖrt` → nkhr) are the fold's k + ḥ
  against ẖ, which no letter rule separates.
- The D&H collision table and every royal-women test are unchanged by both accepted
  iterations: D&H's labels are English, and the accepted rules change transliterations.

## Files

- `measure.py`: the split and both metrics.
- `keys/iteration-*.py`: each key as measured; `iteration-2.py` is the committed key's code.
- `results/`: each iteration's train and validation figures and the test scores, with the
  strong-merge groups.
