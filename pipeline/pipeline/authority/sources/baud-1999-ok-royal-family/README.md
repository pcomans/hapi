# Baud 1999 — Old Kingdom royal family

## Citation

Michel Baud, *Famille royale et pouvoir sous l'Ancien Empire égyptien*,
2 vols, Bibliothèque d'Étude 126/1 and 126/2, Institut français
d'archéologie orientale (IFAO), Le Caire, 1999.
ISBN 2-7247-0248-4 (édition complète), 2-7247-0249-2 (vol. 1),
2-7247-0250-6 (vol. 2). ISSN 0259-3823.

Local PDFs (gitignored, under `proprietary/books/`):

- Vol. 1 (BdE 126/1): `Baud 1999 - Famille royale AE vol 1.pdf`
  SHA-256 `7913623545deb56697506c703f261445d3c029a8f0712474796629670d2f302a`
- Vol. 2 (BdE 126/2): `Baud 1999 - Famille royale AE vol 2.pdf`
  SHA-256 `8768536a13fb5428d8ec7fbd96263d028aabb557a5411e7f796cad99ed6881cb`

## Scope

**In scope.** The 282-entry prosopographical *Corpus* of vol. 2 (printed
pp. 395–627, physical vol.2 pp. 19–244). Each entry is a numbered
`[N]` record collecting the titles, monuments, dating, parentage, and
discussion of one named or anonymous Old-Kingdom individual
attested with a royal-kinship title (*mwt nswt*, *ḥmt nswt*,
*zꜣ(t) nswt*) or with a function title that attaches them to the
royal family (e.g. "prêtre de la mère royale"). Cross-reference
stubs (e.g. `[9] Jj-[ḥr?]-nfr. Voir à Nfrt-kꜣw II [132]`) are included
as redirect rows.

**Out of scope.**

- Vol. 1 in its entirety. It is Baud's narrative / analytical chapters
  (dating methods, kinship terminology, status markers, etc.) — prose,
  not a prosopographical list. Per the playbook's rights policy we do
  not transcribe narrative chapters.
- The *Corpus* header material on vol.2 pp. 395–398 (Baud's own
  explanation of the *a*–*h* rubric scheme and transcription
  conventions). Prose, reproducible from the scan.
- Vol.2 Appendices A, B, C (vol.2 pp. 245–250 / printed pp. 628–632):
  - Appendice A "Références erronées ou non confirmées" — Baud's own
    list of *rejected* attributions. Explicitly excluded from the
    authority because Baud is telling us these entries should not be
    used.
  - Appendice B — a prose discussion of the family of Nbt and Ḫwj at
    Abydos, with hypothetical genealogies only (fig. 48). The primary
    individuals (ʿnḫ.s-n-Mrjj-Rʿ I [37]/II [38], Ḫwj, Nbt, Ḏʿw, etc.)
    are already in the main *Corpus*; the appendix's genealogical
    speculation belongs in downstream curation, not this authority.
  - Appendice C "Documents postérieurs à l'Ancien Empire, de tradition"
    (Bꜣw.f-Rʿ, Nt-jḳrt) — post-Old-Kingdom traditions, outside this
    authority's period scope.
- Vol.2 Index (printed pp. 633+) and list of tableaux / figures.

**Rights policy — facts-only extraction.** Baud's prose is
copyrighted. Per ADR-017 and the Phase-0 playbook's rights policy,
the *Corpus* is prose-heavy and we do NOT commit OCR'd prose
transcriptions (`raw/chunk-*.md`) for this source. Instead the three
independent extraction subagents read the PDF directly via the
Claude Code `Read` tool (page-range calls against the SHA-pinned
`proprietary/books/` PDF), and each writes structured JSONL to
`raw/agent-{a,b,c}-<chunk>.jsonl`. Only the per-row structured
*facts* (ID, name in transliteration, monument, dynasty, titles,
parentage) survive into committed `reconciled.jsonl`. Baud's
argumentative prose stays in Baud; the derived-extract basis is
restricted to non-copyrightable facts and short quoted snippets in
the `notes` field kept under the fair-use threshold.

## Schema (per row)

All fields are optional except `baud_id` and `source_citation`.
Sentinel-null strings (`"none"`, `"-"`, `"—"`, `"n/a"`) normalise to
`null` at merge time; bracketed lacuna markers (e.g. `[ḥr?]`,
`[...]`) are preserved verbatim. French hedges
(*peut-être*, *probablement*, *sans doute*, *fin IV^e – début V^e
dynastie?*) are preserved verbatim in `datation_raw` and `notes`;
they are **never** promoted to hard claims.

| Field             | Type                  | Semantics                                                                                                                                                            |
|-------------------|-----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `baud_id`         | `str`                 | The bracketed corpus number Baud prints at the head of each entry. Zero-padded to 3 digits (e.g. `"007"`, `"017"`, `"282"`) for deterministic sort and easy lookup.  |
| `name`            | `str`                 | Baud's own Egyptological transliteration of the head-word (`Jḥtj-ḥtp`, `Jpwt Ire`, `[...]-Ḥr`). Verbatim. Special-character diacritics (ꜣ ꜥ ḥ ḫ ẖ š ṯ ḏ) preserved.    |
| `head_note`       | `str | null`          | The italic descriptor printed to the right of the headword when present (e.g. *"graffito de la pyramide de Néferirkaré"*, *"Nom perdu, fils de Pépi II, ..."*). Verbatim French. `null` when Baud prints none (typical for a plain-name headword). |
| `asterisk`        | `bool`                | `true` if Baud prints `*` after the headword (marks a person *rattaché* to the royal family — intendant, priest, spouse of zꜣt nswt — rather than a parenté-royale member by title). See vol.2 p. 395 header note.  |
| `redirect_to`     | `str | null`          | For stub entries (`[9] Jj-[ḥr?]-nfr. Voir à Nfrt-kꜣw II [132]`) the target `baud_id` (zero-padded, e.g. `"132"`). Otherwise `null`. On a redirect row every other factual field is `null`. |
| `monuments`       | `list[str]`           | Monument or document list Baud prints in the entry header block (mastaba numbers, tomb numbers, stela, statue, graffito — each as one string). `[]` if none.       |
| `pm_refs`         | `list[str]`           | Porter-Moss references as printed (`"PM 214"`, `"PM 200-201"`, `"PM III2 339"`). Raw string list; no normalisation.                                                  |
| `publications`    | `list[str]`           | Additional publication citations printed in the header (Borchardt, Hassan, etc.). Raw string list.                                                                   |
| `king`            | `str | null`          | The reign Baud prints as the entry's principal date on a line of its own in the header (e.g. `"Néferirkaré"`, `"Khoufou environ"`, `"Snéfrou"`, `"Rêkhaef au plus tard"`). Verbatim French with Baud's hedges. `null` if absent.  |
| `datation_raw`    | `str | null`          | The verbatim French date/dynasty phrase as printed in the header block below `king` (e.g. `"Ve dynastie"`, `"Fin IVe – début Ve dynastie?"`, `"Milieu de la IVe dynastie"`). `null` when the header carries only a `king` line. This is the hedge-preserving field; `dynasty_min`/`dynasty_max` below are derived, not primary. |
| `dynasty_min`     | `int | null`          | Earliest plausible dynasty integer derived from `datation_raw` + `king`. `null` when Baud's date is "Inconnue" or not dynasty-resolvable. See `§ Derived fields` below for the rule. |
| `dynasty_max`     | `int | null`          | Latest plausible dynasty integer. Equals `dynasty_min` for an unhedged single-dynasty date; differs when Baud spans a boundary (`"Fin IVe – début Ve dynastie"` → min=4, max=5). |
| `titles`          | `list[str]`           | The TITRES line, split on Baud's commas. Each title is verbatim Egyptological transliteration (`"zꜣt nswt"`, `"rḫ nswt"`, `"zꜣ nswt nj ẖt.f smsw"`, `"ḥmt nswt"`). `[]` if no TITRES section is printed. Parenthetical disambiguators Baud prints verbatim (`"shd zwnw (aîné, Jr-n-Jḥtj)"`) stay in the string. |
| `father_name`     | `str | null`          | Father's name from PARENTÉ, verbatim transliteration, with Baud's hedges preserved in parentheses (e.g. `"Snéfrou (probable)"`, `"Khoufou"`). `null` if Baud writes "Inconnue" or if PARENTÉ is absent. |
| `mother_name`     | `str | null`          | Mother's name, same conventions.                                                                                                                                     |
| `king_father`     | `str | null`          | A duplicate of `father_name` *only* when the father is himself a king. Helps downstream filtering; derived from `father_name` in `fix_rows.py`.                      |
| `spouse_names`    | `list[str]`           | Spouse(s) from PARENTÉ (wife / husband), transliteration with Baud's hedges preserved. `[]` if none stated.                                                          |
| `children_names`  | `list[str]`           | Children from PARENTÉ, transliteration, hedges preserved.                                                                                                            |
| `sex`             | `"male" | "female" | null` | Derived from the primary title at extraction time (zꜣ nswt → male; zꜣt nswt / ḥmt nswt / mwt nswt / ḥkrt nswt → female). `null` when no sex-bearing title is attested. |
| `notes`           | `str | null`          | A short factual paraphrase (≤ 2 sentences, English) of Baud's DATATION / DIVERS prose — identity-disambiguating details only, no argumentative sprawl. `null` when the prose adds nothing beyond the structured fields. |
| `sub_period`      | `str`                 | Always `"Old Kingdom (Dynasties 3-6)"` for this source. Kept as a field for schema parity with Dodson-Hilton's cross-period queens list.                             |
| `source_citation` | `dict`                | `{"edition": "IFAO BdE 126/2 1999", "pdf_pages": "19-<N>"}` — physical vol.2 pages of this row's entry. `pdf_pages` is one integer or hyphenated range.               |

### Derived fields

`dynasty_min` / `dynasty_max` / `king_father` are computed from the
primary fields by `fix_rows.py`, not extracted by the agents.
Extraction agents leave those three fields set to `null`. The rule
for `dynasty_min`/`dynasty_max` is: parse `datation_raw` + `king`
with a small French-date grammar (see `fix_rows.py` for the exact
mapping `"IIIe"→3`, `"IVe"→4`, `"Ve"→5`, `"VIe"→6`, spanning
hyphens and `à` connectives widen the range, `"Inconnue"` / `null`
→ both `null`). Dynasty integers come only from this derivation;
no LLM extraction of dynasty.

## Schema rationale vs. Dodson-Hilton

Baud's schema diverges from Dodson-Hilton in three places:

1. **Transliteration over anglicisation.** Baud works in
   Egyptological transliteration; D&H anglicises. Keeping Baud's
   spelling as the authority `name` preserves his scholarly
   identifier. Downstream consumers can cross-reference via
   `pm_refs` / `monuments` / authority-linking tables.
2. **`datation_raw` + derived `dynasty_min`/`dynasty_max` in place
   of D&H's integer `dynasty`.** Baud's dates are frequently hedged
   ("fin Ve dynastie?", "Khoufou environ"); a single integer would
   hide that.
3. **`redirect_to` for cross-reference stubs.** D&H doesn't have this
   pattern; Baud's corpus does (entries like `[9]`, `[132]`, etc.).
   A `redirect_to` row is a first-class row with the headword and
   target; downstream consumers can collapse or follow.

## Multi-chunk source

Per-chunk files use the `-<suffix>` convention documented in
`docs/playbook-phase-0-ocr-transcription.md § "Multi-chunk source
pattern"`:

- `prompt.md` — the first chunk's prompt (pages 19–40 of vol.2,
  entries `[1]`–`[~25]`, sub-period label `"Old Kingdom (Dynasties
  3-6)"`).
- `prompt-<suffix>.md` — subsequent chunk prompts.
- `raw/agent-{a,b,c}-<suffix>.jsonl` — per-agent extractions for one
  chunk.

This PR lands chunk 1 only. Remaining chunks 2–N (~257 entries on
~205 physical pages) are scheduled via
`docs/handoff-baud-next-chunk.md` and land in follow-up PRs.

## Known gaps

- Vol.2 Appendices A/B/C are out of scope by design — see Scope.
- Egyptological transliteration as extracted is the *character* form
  Baud prints; combining diacritics are preserved as NFC.
- Baud's own parenthetical references (`voir infra`, `§ divers`,
  `cf. chap. 2, p. 174-175`) are dropped from `notes`; they are
  navigation aids inside vol.1, not extractable facts.
- Footnote numerals (Baud prints superscript `^10` etc.) are dropped
  from `notes`; Baud's footnotes themselves are out-of-scope narrative.

## Provisional status

The extracted rows are **provisional** until a human Egyptologist
signs off per ADR-017 step 6 / playbook Step 12. The LLM
`egyptologist-reviewer` pass does NOT satisfy that requirement. Per
playbook Step 11.5, the residual human surface is limited to (a) any
row that fails an automated check, (b) a ~3-row random
transcription-vs-PDF fidelity sample, (c) any new category the LLM
reviewer flags. The `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED`
section of `merge-disagreements.txt` reflects the current state.

## Current state: scaffolding only

This PR lands the source-directory scaffolding (schema,
extraction prompt, merge script, derived-field deriver, handoff
doc, unit tests). **No `reconciled.jsonl` yet.** Chunk 1
extraction (vol.2 pp. 19–40, entries `[1]`–`[~25]`) is the next
agent's task — see `docs/handoff-baud-next-chunk.md`. Follow-up
chunks 2–7 are scheduled there.
