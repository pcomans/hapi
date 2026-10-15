# Weak-sign key hill-climb — protocol v2 (committed before any v2 measurement)

## Why v2

A first climb (v1, commit 4f22bd9, 2026-10-15) was reviewed and found unsound:
- **It loosened its own metric.** After iteration 1 it stopped counting ḥ/h, ẖ/ḫ and q/k as
  strong merges. q/k hid the cost of a rule already in the key.
- **It counted merges only within a split.** That misses most name pairs.
- **It accepted a bug fix as a climb step.**
- **It shipped a trigger character (ʿ) that the data never contains.**
- **It looked at its TLA test split twice.**

v1's results were withdrawn (removed in the next commit). The bugs it uncovered were fixed
outside any climb, before v2's baseline:
- Unicode composition.
- Digraph units, so that Menkauhor's k + h is not the ḫ of Menkheperre.

The egyptologist review's P1 was fixed the same way: a key shared by different names
(`DIFFERENT_NAMES`) never resolves.

## Disclosure

- **The candidates came from inspecting v1's train misses.** The four candidates below were
  identified from v1's TLA train-split misses, so they are not independent of the TLA train
  data.
- **The TLA test split is spent.** v1 scored it for two keys. Its v2 figure is reported but is
  no held-out estimate.
- **The held-out check for v2** is the king spellings of the committed claim graph (below),
  which neither climb read.

## Ground truth

`pipeline/pipeline/authority/sources/tla-2018-names/reconciled.jsonl` (CC BY-SA 4.0). A
lemma's *renderings* are its transliteration and each translation value with any gloss
(text from the first "(", ";" or ",") removed. A bracketed value is a description and is
skipped. All renderings of one lemma are one name in several conventions.

A lemma's *name* is its strict transliteration: lowercased, composed (NFC), with the
separators . - = ⸗ ~ ʾ, spaces, brackets and the marks of i̯/u̯ removed. Two lemmas with one
name are one name entered twice.

## Split

By SHA-256 of `"weak-sign-hillclimb-v2/" + name` modulo 10: train 0–5, validation 6–7, test
8–9. Splitting by name keeps a name's duplicate lemmas in one split.

## Metrics (`measure.py`)

1. **Recall** (per split): of the pairs of renderings within one lemma that both have a key,
   the share whose keys are equal.
2. **Coverage** (per split): of all renderings, the share that have a key.
3. **Strong merges** (whole set, every rendering):
   - Group every rendering of every lemma by its key.
   - A key is a strong merge if the names of the lemmas in its group have more than one
     *strong skeleton*.
   - The strong skeleton is the name with its final t dropped and ꜣ, j, y, w, i, ꞽ removed.
     Every other sign is kept as itself: ꜥ, q, ḳ, ḥ, ẖ, ḫ, ṯ, ḏ, z, š.
   - The count is the number of names in such groups (strict). A *fold-aware* count, which
     also treats ḥ = h and ẖ = ḫ as the committed fold does, is reported beside it but
     decides nothing.

## Acceptance (applied in code)

A candidate is accepted if and only if, against the current accepted key, all of these hold:
- train recall rises;
- validation recall does not fall;
- train and validation coverage do not fall;
- strict strong merges do not rise.

Candidates are tried in the order below, each against the key accepted so far, and each once.

## Candidates (fixed)

1. **C1:** in an Egyptological transliteration, j is always the weak sign. The trigger is a
   sign that only transliterations use: ꜣ, ꜥ, ꞽ, =, ⸗, or the inverted breve of i̯ (U+032F).
2. **C2:** z is written s.
3. **C3:** ṯ is written t.
4. **C4:** remove the existing rule that c and q are k.

## Held-out check (scored once, at the end, for the v2 baseline and the v2 final key)

- **Data:** the committed claim graph's identity clusters
  (`web-claimgraph/data/claim-graph.json`), five sources' display names for one king. Each
  name has its regnal numeral and a trailing parenthetical removed.
- **Recall:** pairs of display names within one cluster, both keyed, with equal keys.
- **Merges:** the keys shared by display names of different clusters are listed, not scored.
  Homonymous kings, such as Amenhotep I and II, share names by nature.

## Frozen inputs

- `normalize_frozen.py` is a copy of `pipeline/pipeline/authority/claimgraph/normalize.py`
  at this commit. Key snapshots are measured with it, not with the live normalizer.
- `keys/v2-*.py` are the keys as measured.
