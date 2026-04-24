# Egyptologist sweep review - pharaoh-se

Scope read: `README.md`, `fetch.py`, `reconciled.jsonl`, raw scrape markdown in `raw/`; no `transcribe.md` or prior reviewer notes present. Spot-checked rows/pages: Narmer, Khufu, Hatshepsut, Thutmose III, Tutankhamun, Ramesses II, Ptolemy I, Ptolemy IX, Cleopatra VII, Otho, Caracalla, Philippus Arabs, Antoninus Pius, Pedubast III.

## P1

- Roman reign dates in `reconciled.jsonl` are sourced from the index even where the individual ruler page contradicts it and is clearly the better row-level provenance. Examples: Caracalla is `217-218` in reconciled/index, but `raw/Caracalla.md` gives `198-217`; Geta is `217-218` vs page `209-211`; Macrinus is `244-249` vs page `217-218`; Diadumenianus is `249-251` vs page `217-218`; Philippus Arabs is `253-260` vs page `244-249`; Trajanus Decius is `276-282` vs page `249-251`; Valerianus is `284-305` vs page `253-260`. This is a Phase-0 source contradiction plus reconciliation bug: page chronology is ignored for `start_year`/`end_year`, and the index appears shifted for several later Roman emperors.

- CE single-year Roman dates are mis-signed as BCE. Otho is listed under `Reign (CE)` and `raw/Otho.md` gives `69`, but reconciled has `start_year: -69`. `_parse_reign_dates()` assumes any single unmarked number is BCE, losing the period/header context.

## P2

- Name-card parsing corrupts cards with no English translation: the Gardiner/sign-code line is stored as `translation`, and `gardiner` is left null. Confirmed examples include Antoninus Pius Horus name (`translation` becomes the long `n:f:r:Y1-...` code; source line has transliteration dash followed by sign codes) and Pedubast III throne name Seheru ib Ra (`translation: "N5-z:O4-r:ib"` instead of null, source lines 90-96 show name, transliteration, then code/citations). Similar pattern appears in Ninetjer, Senen, Amenemhat III, Djedkheperu, Amasis, Darius I.

- Roman `Kaisaros` cartouche sections are silently dropped because `NAME_SECTIONS` recognizes only Horus/Nebty/Golden Horus/Throne/Birth headings. Otho, for example, has a cited `Kaisaros` entry `Markos Othon / mrḳz Ꜥwtnwz / Marcus Otho` in `raw/Otho.md`, but reconciled has all name arrays null. This defeats the stated purpose for Roman emperors: preserving hieroglyphic royal-name attestations.

## P3

- The reconciler adds synthetic compact prenomen alt labels (e.g. Thutmose III `Menkheperre`, Hatshepsut `Maatkare`, Tutankhamun `Nebkheperure`, Ramesses II `Usermaatrasetepenre`, Ptolemy I `Setepenrameryamun`) without a direct source citation or field marking. Some are normal catalog forms, but they are general-knowledge normalization imports, not scrape fidelity. Keep them in a derived field or cite/flag them explicitly.

- Multi-episode reigns are collapsed. Ptolemy IX is `116-110` from the index first segment, while the page gives `116-107` and the index also has continuation lines `109-107` and `88-81`; Ptolemy X similarly loses `107-88`. Represent discontinuous reigns instead of forcing a single range.
