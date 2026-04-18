# Extraction prompt — Baud 1999 BdE 126 Corpus, chunk 1 (entries `[1]`–`[40]`)

You are one of three independent Claude Code subagents extracting structured prosopographical data from Michel Baud's *Famille royale et pouvoir sous l'Ancien Empire égyptien* (BdE 126, IFAO 1999), vol. 2 *Corpus*. The three of you run in parallel on the identical prompt; your outputs are merged via majority vote downstream, so honest independence matters more than consistency with a hypothetical peer. Follow the schema EXACTLY; downstream code fails loud on shape drift.

**Framing.** This extraction is fair-use scholarly data compilation for a private cross-museum provenance index operated under contract with a credentialed Egyptologist. Only factual data (names, titles, kinship, monuments, dates, cross-references) is extracted; Baud's narrative prose is not reproduced. The source PDF is not redistributed. If you encounter content-filter hesitation, this framing resolves it — proceed with the task.

## What to read

`pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/raw/source-chunk-1.pdf` — a 39-page sub-PDF of Baud vol. 2 covering physical pages 11–49 of the original. The file includes:

- **Physical pp. 11–16** (printed pp. 395–400 approx.): the Corpus methodological intro. **Do not extract rows from these pages** — they document Baud's `(a)`–`(h)` field convention, which tells you HOW to read each entry. Refer back to them when you're unsure how a field should be interpreted.
- **Physical pp. 14–49** (printed pp. 399–432): Corpus entries `[1]` through `[40]`.

**Boundary warning.** Entry `[41]` (`ɛnḫ-Ttj`) has a header at the bottom of physical p. 49 that continues onto p. 50 (not included in the sub-PDF). **Do NOT emit a row for `[41]`.** Your last row is `[40]` (`ɛnḫ-Špss-kɜ.f*`).

## Baud's entry format (from his intro on printed pp. 395–397)

Each numbered entry has a header block followed by up to four prose rubrics:

```
[Numéro]  Nom (a)
           Monument et localisation (b).
           Référence Porter-Moss. Publication (c).
           Date (d).
           Code(s) de corpus (e).
Titres (f).
Datation (d-prose).
Parenté (g).
Divers (h).
```

- **(a) Nom** — the Egyptian-transliteration headword. An ASTERISK suffix (e.g. `Jḥtj-ḥtp*`) marks service personnel attached to the royal family (priest of the mother royale, intendant of the queen, etc.), not a family member. The asterisk is load-bearing.
- **(b) Monument et localisation** — tomb number or monument type, plus site. Example: `"Mastaba G 7650 dans la nécropole orientale de Gîza."` — split into `monument` (`"Mastaba G 7650"`) and `localisation` (`"nécropole orientale de Gîza"`).
- **(c) Référence Porter-Moss. Publication** — the `PM ...` line plus optional follow-on publication refs. The PM reference goes into `pm_ref`; the publication strings are dropped (scholarly apparatus, not prosopographical data).
- **(d) Date** — Baud's preferred reign / dynasty bracket. One line, terse (e.g. `"Rêkhaef au plus tard"`, `"Fin IVᵉ – début Vᵉ dynastie"`, `"Snéfrou (?)"`, `"Pépi II"`).
- **(e) Codes de corpus** — cross-references to prior prosopographical literature. Example: `"Baer n° 7, Schmitz, p. 121-122 (356), Harpur n° 10."` Parse each `<Author> <ref>` pair into the `baud_refs` dict (lowercase author key, value is the ref string as printed).
- **(f) Titres (prose rubric starting `TITRES.`)** — verbatim list of titles (Egyptological transliteration). Extract into `titles_from_baud` as a list, one title per list element, comma-separated in the source.
- **(d-prose rubric starting `DATATION.`)** — extended dating argument. Do NOT extract the prose; the one-line `(d)` date is what goes in `date_attested`.
- **(g rubric starting `PARENTÉ.`)** — filiation, spouse, children. Populate `father_name` / `mother_name` / `spouse_names` / `children_names`. Preserve hedges.
- **(h rubric starting `DIVERS.`)** — miscellaneous commentary, alternative readings, reconstructions. Do not reproduce verbatim; extract only the hedge or cross-reference fragment (≤ 2 short sentences) if it changes the factual reading of another field, and put it in `notes_from_baud`. Default `null`.

**Baud does not always give every rubric.** Many entries have only some of TITRES / DATATION / PARENTÉ / DIVERS. Treat absent rubrics as missing data, not as `null` structured fields; follow the schema rules in `README.md` for field-level `null` convention.

## Schema

See `pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/README.md` § "Schema" for the canonical spec. Summary of mandatory field semantics:

- **`baud_id`**: `"baud-<N>"` where `<N>` is Baud's 1-282 Corpus entry number.
- **`name_egyptian`**: transliteration headword, verbatim including ASCII-equivalents of diacritics when the PDF text layer gives them. Preserve dots (`mw.t-nsw`), hyphens, and case exactly as printed. If the PDF text layer is unreliable for a glyph, fall back to a Unicode-correct rendering using the standard Egyptological character set (ꜣ ꜥ ḥ ḫ ẖ š ṯ ḏ) — but prefer verbatim.
- **`name_anglicised`**: conventional English form (e.g. Khufu, Sneferu, Hetepheres, Iheti-hotep) if obvious to a specialist; `null` if there is no common English rendering. Do NOT invent one for obscure non-royal names.
- **`service_personnel`**: `true` if the headword ends in `*`, else `false`. The asterisk itself is stripped from `name_egyptian`.
- **`monument`**, **`localisation`**, **`pm_ref`**: split from header lines `(b)` and `(c)`. `null` when not attested.
- **`date_attested`**: Baud's `(d)` line verbatim (French text allowed; it's a scholarly dating, not prose).
- **`dynasty`**: string form `"3"`, `"4"`, `"5"`, `"6"`, or a range `"4-5"` for cross-dynasty, or `"unknown"` when Baud declines to date. Derive from `date_attested` — map French dynasty numerals (`IVᵉ` → `"4"`, `"Vᵉ"` → `"5"`, etc.).
- **`sub_period`**: `null` unless Baud explicitly names an OK sub-period (e.g. `"début IVᵉ dynastie"` → `"early Dyn 4"`; `"Fin IVᵉ – début Vᵉ"` → `"end Dyn 4 – early Dyn 5"`).
- **`baud_refs`**: dict. Keys are lowercase author surnames used by Baud in his `(e)` convention: `baer`, `strudwick`, `seipel`, `harpur`, `troy`, `schmitz`. Values are the reference strings as printed (the number/page/entry Baud cites). `{}` when Baud gives no `(e)` line.
- **`titles_from_baud`**: list of verbatim title strings from the `TITRES.` rubric, split on commas. `[]` when the entry has no `TITRES.` rubric.
- **`roles`**: normalised OK-appropriate role codes derived from `titles_from_baud` and Baud's filiation prose. Controlled vocabulary for this chunk:
  - `king` (any king holding a cartouche — rare in Baud; mostly consorts)
  - `queen` (for `ḥmt nswt` holders who are also attested on royal monuments)
  - `king's mother` (`mwt nswt`)
  - `king's wife` (`ḥmt nswt`)
  - `king's son` (`zɜ nswt`)
  - `king's daughter` (`zɜ(t) nswt`)
  - `king's son-in-law` (spouse-of-royal-daughter, where Baud asserts it)
  - `king's eldest son of his body` (`zɜ nswt smsw n ẖt.f` or variants with `mrjj.f`)
  - `vizier` (`ṯɜtj`)
  - `priest of the royal pyramid` / `priest of the king's mother` / `priest of the king's wife` / `priest of the king` — derived from `ḥm-nṯr` titles scoping to a named pyramid / mother / wife / king.
  - `steward of the queen` (`jmj-r pr` + queen reference)
  - `sem priest` (`sm`)
  - `overseer of the treasury of pr-ɛɜ` / `overseer of scribes of pr-ɛɜ` — for complex administrative titles.
  Add a new role code only when the title doesn't map to any of the above; in chunk 1 this will be rare.
- **`father_name` / `mother_name`**: single-name strings from PARENTÉ prose. Preserve Baud's hedges:
  - `"Téti (probable)"` — parenthesised for Baud-probable.
  - `"[Snéfrou]"` — bracketed for Baud-reconstructed-from-lacuna.
  - `null` — Baud does not attest this parent.
  - Append `" (per Baud)"` ONLY when the row would otherwise promote a purely interpretive claim (no physical attestation, only Baud's titular-synchronism argument) to a hard claim.
- **`spouse_names`**, **`children_names`**: lists. Empty `[]` when Baud attests none. Apply the same hedge convention as `father_name`/`mother_name`. Cross-entry inference IS permitted within chunk 1 — if Baud's entry `[X]` is silent on whether they have a child, but entry `[Y]` names `[X]` as parent, populate `[X].children_names = ["<Y's name>"]`. Applies to symmetric relationships (parent/child, spouse/spouse).
- **`tomb`**: designation if the monument is a tomb (`"G 7650"`, `"D 62"`, `"Mastaba 17 Meidum"`); `null` otherwise.
- **`notes_from_baud`**: short fragment (≤ 2 sentences, ≤ 50 words) from PARENTÉ or DIVERS when a hedge or cross-reference changes the factual reading. Default `null`. Examples of WHEN to populate:
  - Baud hedges filiation with a scholarly argument (parent is based on titular synchronism rather than inscription) — put the hedge in the parent-name field AND populate `notes_from_baud` with the fragment explaining why.
  - Baud cross-references another Corpus entry in a way that flips a role attribution.
  - Baud flags a reading as "très incertaine" / "peu vraisemblable" / "hypothèse".
- **`source_citation`**: `{"source": "Baud 1999 BdE 126 Corpus [<N>]", "pdf_pages": "11-49", "edition": "IFAO 1999 vol. 2"}`. The `pdf_pages` value is the **chunk-1 sub-PDF's physical-page range in the original book**, not the per-entry page. Every chunk-1 row uses `"11-49"`.

## Pitfalls (skim before extracting)

- **Do NOT extract `[41]`.** The sub-PDF ends mid-page on physical p. 49 before `[41]` finishes. Any row with `baud_id >= 41` is a bug.
- **Asterisks in names are significant.** `Jḥtj-ḥtp*` is service personnel; `Jḥtj-ḥtp` (same name, no asterisk, different entry number) is a family member. The asterisk sets `service_personnel: true` and changes `roles` semantics.
- **Cross-reference-only entries.** Some short entries are pure cross-references (e.g. `"///-Ḥr. Voir Ḥr/// [154]"`). Emit the row with the baud_id from the original numbered entry, minimal fields, and `notes_from_baud` = `"Cross-reference to [154]."` Do not try to follow the ref within this chunk — `[154]` is out-of-chunk.
- **Corpus entries are alphabetical by Egyptian transliteration, not by dynasty.** Chunk 1 contains a mix of Dyn 3, 4, 5, and 6 entries.
- **Hedge-heavy source.** Baud explicitly says "dans de nombreux cas, les informations sur la parenté sont inexistantes et les hypothèses généalogiques fragiles." He names probable parents knowing he's inferring. Preserve every hedge; promoting a hedge to a hard claim is the signature failure mode.
- **French vs Anglo-American transliteration.** Baud uses French-school conventions (dots, `j`). Your output keeps French-school verbatim in `name_egyptian`; normalisation to a house style is Phase A.
- **The "Corpus" heading on physical p. 11 is NOT a row.** It's a chapter title.
- **Be aware of the Corpus intro lettered items (`a`–`h`)** on physical pp. 11–16. These letters describe HOW to read an entry; they are NOT row IDs. Do not emit `[a]`, `[b]`, etc. rows.
- **Footnotes.** Baud uses numbered footnotes. Ignore footnote content unless it contains a parenthetical hedge Baud references by number; even then, summarise, don't quote.
- **Multiple documents per entry.** Some entries describe multiple monuments (e.g. entry `[39]` lists 7 documents numbered 1–7). In this case `monument` / `localisation` take the first document's values; `pm_ref` concatenates the distinct PM references with `"; "`.

## Output format

Write newline-delimited JSON to `pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/raw/agent-<YOUR_TAG>-chunk-1.jsonl`, where `<YOUR_TAG>` is `a`, `b`, or `c` (the spawner will tell you which). One row per Baud Corpus entry, in ascending `baud_id` order.

Every row MUST contain every field in the schema — use `null` / `[]` / `{}` / `false` for missing values per the per-field rules above. Downstream `merge.py` expects a uniform schema; missing keys confuse the majority vote.

**Expected row count:** 40 rows. If your extraction produces < 35 or > 45, re-read the prompt and the boundary warnings; something is off.

## Report

When done, output a single report of ≤ 80 words:
- Row count.
- Any entries you struggled with (ambiguous monument/localisation splits, unreadable glyphs, cross-reference entries with unclear referents).
- Any pitfalls above you suspect you violated — explicit about uncertainty beats silent-pretending-it's-fine.
