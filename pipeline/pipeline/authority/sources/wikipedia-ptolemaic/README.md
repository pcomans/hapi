# Wikipedia — Ptolemaic Rulers

Source: English Wikipedia articles on individual Ptolemaic pharaohs and
queens regnant, accessed April 2026. Cross-referenced against
Encyclopaedia Britannica and UCL Digital Egypt for date consistency.

## Why a separate source

The HKW chronological table (section IV.2) ends at Alexander the Great
(332 BCE). The Ptolemaic dynasty (305–30 BCE) is not covered in that
volume. This source fills the gap using Wikipedia's well-sourced king
list, which itself draws primarily from von Beckerath (1999) and
Dodson & Hilton (2004).

## Layout

```
pipeline/pipeline/authority/sources/wikipedia-ptolemaic/
  README.md        — this file
  reconciled.jsonl — transcription of record
```

## Coverage

24 rows: 1 period entry + 15 rulers (Ptolemy I through XV) + 8 queens
(Arsinoe II, Cleopatra I Syra, Cleopatra V Tryphaena, Cleopatra II,
III, VII, Berenice III, IV).

## Schema

Uses the same schema as the HKW source for cross-source compatibility.
The `page` field is `null` for all rows since there is no PDF source.
The `dynasty` field is `null` for all rulers — the Ptolemaic period is
not a numbered Egyptian dynasty.

Prenomen (Egyptian throne names) were extracted from individual
Wikipedia pharaoh articles where available. Late Ptolemies (XI, XIII,
XIV) and all queens lack attested prenomen on Wikipedia; these are
recorded as `prenomen: null`.

## Design decisions

- **One row per ruler** for interrupted reigns (Ptolemy VI, VIII, IX,
  XII). The `start_bce`/`end_bce` span the full period; gaps are
  documented in the `note` field. Museums attribute artifacts to
  "Ptolemy IX", not "Ptolemy IX first reign".
- **Ptolemy VII included** with null dates and a note. He never
  formally reigned but his name appears in a royal cartouche on a
  Temple of Edfu relief, so artifacts could bear his name.
- **Queens regnant included.** Cleopatra II, III, VII and Berenice III,
  IV all held pharaonic authority and may appear in museum catalogs.
- **Cleopatra VII listed before Ptolemy XIII–XV** since she was the
  senior pharaoh throughout; the numbered Ptolemies were her junior
  co-regents.
