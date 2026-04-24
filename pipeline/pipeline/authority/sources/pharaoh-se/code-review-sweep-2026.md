# Pharaoh.se Sweep Review - 2026

## P1 - Name-card parser shifts fields and corrupts committed titulary data

`fetch.py` assumes every name card is exactly `name`, `transliteration`, `translation`, then scans from the fourth content line for Gardiner/source fields (`fetch.py:308-327`). The raw source does not always follow that shape. In `raw/Ptolemy-V.md:93-104`, the throne name spans two lines (`Iwa en netjerwy` plus `merwy it...`), then transliteration, translation, Gardiner. The committed row at `reconciled.jsonl:333` stores the second name line as `transliteration`, the transliteration as `translation`, and the real translation in `sources`. The same row has the Golden Horus name shifted from `raw/Ptolemy-V.md:70-81`: `henmemet...` is incorrectly stored as transliteration.

The parser also treats the third content line as a translation even when the source has no translation. In `raw/Pedubast-III.md:48-60`, `N5-z:O4-r:ib` is the Gardiner code, but `reconciled.jsonl:379` stores it as `translation` with `gardiner: null`. A quick scan of the committed JSONL found 9 `translation` values that look like Gardiner strings, including Ninetjer, Senen, Amenemhat III, Darius I, Antoninus Pius, and Pedubast III, plus 57 first `sources` entries that look like Gardiner codes while `gardiner` is null.

This violates Rule 1 because fields no longer trace to the cited raw source semantics, Rule 3 because no deterministic check catches shifted columns, and Rule 5 because the value-pinning tests do not assert these affected rows. Fix by parsing cards from explicit source structure, accepting multi-line name fields, detecting absent translations before assignment, and adding regression assertions for Ptolemy V and Pedubast III.

## P2 - Missing page fetches only warn, then produce partial authority rows

After parsing raw/page markdowns, `main()` computes missing slugs but only prints a warning (`fetch.py:649-651`) before reconciling every index row (`fetch.py:653-654`). If Firecrawl omits pages or `raw/` is incomplete, `reconcile()` silently emits records with index-only fields and null titulary/predecessor/successor/chronologies. The row count still passes because it is driven by the index, and the current tests only assert that `raw/index.md` exists, not that every index slug has a corresponding raw page.

This is a Rule 2 loud-fail issue and a Rule 3 enforcement gap. Missing source pages should raise before writing `reconciled.jsonl`, and tests should assert the index slug set equals the raw page stem set.

## P3 - Integrity tests rely on coverage thresholds instead of per-row value pinning

`TestPharaohSeIntegrity` checks broad thresholds for prenomen/date/alt-label coverage (`test_authority.py:321-340`) and only pins one detailed ruler, Thutmose III (`test_authority.py:356-368`). `test_name_cards_have_required_fields` only asserts each card has a name or transliteration (`test_authority.py:377-393`), so field swaps like Ptolemy V and Pedubast III pass.

This falls short of Rule 5 for this authority source. Add focused canary rows covering multi-line titulary, no-translation Gardiner cards, ancient sources, Roman positive dates, and sparse rows; assert all populated fields for those rows, not only presence/coverage.
