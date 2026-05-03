# Baud 1999 — *Famille royale et pouvoir sous l'Ancien Empire égyptien*

Source of truth for Old-Kingdom royal-family members — queens, king's mothers, king's sons, king's daughters, and the service personnel attached to the royal household. The OK analogue of Dodson-Hilton, required because D&H's OK coverage is explicitly flagged as weaker (`docs/mvp-tasks.md`).

## Citation

Baud, M. (1999) *Famille royale et pouvoir sous l'Ancien Empire égyptien*. Bibliothèque d'Étude 126. Cairo: Institut Français d'Archéologie Orientale. Two volumes. ISBN 2-7247-0250-6 (vol. 2).

- **Edition used:** first edition, 1999, vol. 2 *Corpus*.
- **Retrieved:** local scan, 2026-04-14.
- **PDF SHA-256 (vol. 2):** `8768536a13fb5428d8ec7fbd96263d028aabb557a5411e7f796cad99ed6881cb`.
- **On-disk path (gitignored):** `proprietary/books/Baud 1999 - Famille royale AE vol 2.pdf` (vol. 1 lives next to it under the parallel name).

## Scope

Vol. 2 *Corpus* entries `[1]`–`[282]`, a prosopography of attested Old Kingdom royal-family members and service personnel. Entries are alphabetical by Egyptian transliteration (not by dynasty). Vol. 1 (analytical narrative chapters) and vol. 2 appendices are out of scope.

Landed across multiple PRs, one chunk per PR, ~40 entries per chunk:

| PR | Entries | Physical pp. (vol. 2) | Rows |
|----|---|---|---|
| #53 (merged) | `[1]`–`[40]` | 11–49 | 40 |
| #57 (this PR) | `[41]`–`[80]` + `[60a]` | 49–82 | 41 |
| future | `[81]`–`[120]` | 82–109 (est.) | ~40 |
| future | `[121]`–`[160]` | TBD | ~40 |
| future | `[161]`–`[200]` | TBD | ~40 |
| future | `[201]`–`[240]` | TBD | ~40 |
| future | `[241]`–`[282]` | TBD | ~42 |

**Out of scope** (will not be extracted in any chunk):

- **Vol. 1** — analytical narrative chapters (datation systems, titulary theory, queens' statuses). Interpretive synthesis, not prosopographical data.
- **Vol. 2 appendix A** (p. 628+) — cross-references Baud himself flags as erroneous or too uncertain; he explicitly excludes them from the main Corpus and we follow suit.
- **Vol. 2 appendices B, C** — indices; recomputable from the structured data.
- **The full DATATION / PARENTÉ / DIVERS prose paragraphs.** Per the playbook's rights policy, Baud's prosopographical paragraphs are the unsafe-to-commit category. Only short attested-fact fragments land in `notes_from_baud`; the full scholarly prose (often 300+ French words per entry) stays in the book.

## Schema

One row per numbered Baud Corpus entry:

```json
{
  "baud_id": "baud-3",
  "name_egyptian": "Jḥtj-ḥtp",
  "name_anglicised": "Ihetihotep",
  "service_personnel": false,
  "monument": "Mastaba G 7650",
  "localisation": "nécropole orientale de Gîza",
  "pm_ref": "PM 200-201",
  "date_attested": "Rêkhaef au plus tard",
  "dynasty": "4",
  "sub_period": null,
  "baud_refs": {"baer": "7", "schmitz": "121-122 (356)", "harpur": "10"},
  "titles_from_baud": ["/// n jmꜣt (?)", "ꜥd-mr wḥꜥw", "ḥm [bꜣw] Nḫn", "ḥm-nṯr Ḫwfw", "ḥrp ꜥḥ", "smr", "smr wꜥtj"],
  "roles": ["king's son-in-law"],
  "father_name": null,
  "mother_name": null,
  "spouse_names": ["Mrt-jt.s"],
  "children_names": [],
  "tomb": "G 7650",
  "notes_from_baud": "Époux de la fille royale Mrt-jt.s [86].",
  "source_citation": {"source": "Baud 1999 BdE 126 Corpus [3]", "pdf_pages": "11-49", "edition": "IFAO 1999 vol. 2"}
}
```

The JSON example uses the canonical IFAO Egyptological codepoints (`ꜣ` U+A723 for aleph, `ꜥ` U+A725 for ayin) — post-normalization form matching `reconciled.jsonl`. The extraction agents sometimes emit fallback codepoints (`ɜ`, `ˁ`, `ɛ`) that `fix_rows.py`'s deterministic transliteration pass replaces; the test suite asserts no fallbacks survive.

Field-by-field:

- **`baud_id`** = `"baud-<N>"` where `<N>` is Baud's own 1–282 Corpus entry number. Flat namespace, no sub-section scoping — unlike D&H's per-sub-section letter suffixes. `baud_id` is the sole primary key; merge.py fails loud on duplicates.
- **`name_egyptian`** = transliteration headword exactly as printed. Preserves diacritics (ꜣ ꜥ ḥ ḫ ẖ š ṯ ḏ) and dots/hyphens verbatim — morpheme-boundary conventions (e.g. `mw.t-nsw`, `Jḥtj-ḥtp`) are load-bearing for later reconciliation against pharaoh.se and Beckerath. Normalisation to a single house style happens in Phase A, not here.
- **`name_anglicised`** = conventional English form (e.g. "Hetepheres", "Khufu", "Ihetihotep") if Baud gives one or if one is obvious to a specialist; `null` otherwise. Phase A will reconcile against pharaoh.se's Conventional English Display Form.
- **`service_personnel`** = `true` for headwords ending in `*` (asterisk marks attached personnel rather than family members per Corpus intro item `a`). `false` otherwise. This flag changes the semantics of `roles`: for service personnel, roles describe their function in the royal household; for family members, roles are kinship terms.
- **`monument`** = the first line of the `(b)` header block — tomb designation, statue origin, stela, etc. (e.g. `"Mastaba G 7650"`, `"Statue découverte dans le temple bas..."`, `"Tombe rupestre n° 4 au nord du Sphinx"`).
- **`localisation`** = the site portion of the `(b)` line (e.g. `"Giza"`, `"Saqqara"`, `"Dahchour"`). Split from `monument` whenever Baud gives both. `null` when only a collection/museum reference is given.
- **`pm_ref`** = Porter-Moss reference exactly as printed (`(c)` line). Includes volume and page reference (`"PM 339"`, `"PM III 200-201"`). `null` when absent.
- **`date_attested`** = Baud's dating under the header `(d)` — verbatim. Ranges from tight (`"Pépi II"`) to hedged (`"Snéfrou (?)"`) to dynasty-span (`"Fin IVᵉ - début Vᵉ dynastie"`).
- **`dynasty`** = string: `"3"`, `"4"`, `"5"`, `"6"`, or a range `"4-5"` for cross-dynasty attestations, or `"unknown"` when Baud declines to date. Derived from `date_attested` during extraction.
- **`sub_period`** = OK sub-period label (e.g. `"early Dyn 4"`, `"end Dyn 4 – early Dyn 5"`) only when Baud attests it explicitly. `null` otherwise.
- **`baud_refs`** = dict of cross-references Baud gives under header `(e)` to prior prosopographical literature: Baer (*Rank and Title*), Strudwick (*Administration*), Seipel (*Königinnen*), Harpur (*Decoration*), Troy (*Queenship*), Schmitz (*Königssohn*). Keys are lowercase author names, values are the page/entry reference as printed. Empty dict `{}` when Baud gives none.
- **`titles_from_baud`** = verbatim title list from the `TITRES` rubric (f), as a list. Load-bearing for reconciliation; preserve dots, hyphens, glyph choices. Baud sometimes writes hedges inline (`zɜ nswt (?)`); those survive in the strings.
- **`roles`** = structured list of normalised OK-appropriate role codes derived from `titles_from_baud` and Baud's filiation prose. Controlled vocabulary for this source — canonical list in `test_roles_vocabulary_is_bounded` in `pipeline/tests/test_sources_baud_ok_royal_family.py`; extended per chunk as new titulary patterns are encountered. Phase A expands to canonical titulary codes.
- **`father_name` / `mother_name`** = single names from Baud's PARENTÉ prose. `null` when Baud attests none. Baud's own hedges are preserved verbatim inside the string using the playbook convention: `"Téti (probable)"` for parenthesised-probable, `"[Snéfrou]"` for bracketed-reconstructed, `null` for "unattested per Baud". Baud's scholarly judgments — attributions he asserts on iconographic or titular inference — are marked with a trailing `" (per Baud)"` annotation only when the row would otherwise promote an interpretive claim to a hard one.
- **`spouse_names`** = list of spouse names from Baud's PARENTÉ prose. `[]` when none.
- **`children_names`** = list of child names from Baud's PARENTÉ prose. `[]` when none. Cross-entry inference IS permitted (same rule as Dodson-Hilton): if Baud's entry is silent but another Corpus entry names this person as a parent, populate the link. Bracketed references like `[86]` survive as part of the name string only if Baud's prose gives no other form of the name.
- **`tomb`** = tomb designation (`"G 7650"`, `"D 62"`, `"Mastaba 17 Meidum"`) when the `(b)` block identifies one. `null` when the monument isn't a tomb or when Baud gives no tomb designation. Cross-references to Porter-Moss land in `pm_ref`, not here.
- **`notes_from_baud`** = short prose fragment (≤ 2 sentences, ≤ 50 words) from Baud's PARENTÉ or DIVERS prose when the hedge or cross-reference changes the factual reading but doesn't fit the structured fields. Default is `null`. **Do not reproduce full paragraphs** — per the playbook's rights policy Baud's paragraphs are the unsafe-to-commit category; this field carries only the fragment a reviewer needs to understand why a hedge is in `father_name` / `mother_name` or why `roles` includes a tentative code.
- **`source_citation`** = dict with `source` (`"Baud 1999 BdE 126 Corpus [N]"` format), `pdf_pages` (physical-page range of the chunk sub-PDF, per ADR-017), `edition` (`"IFAO 1999 vol. 2"`).

## Role-derivation conventions

`roles` codes are derived from `titles_from_baud` plus Baud's filiation prose. Two derivations are stricter than the prosopographic literature's looser convention; this section records them so downstream consumers know what they're getting and can fall back to `titles_from_baud` when the loose form is wanted.

**`king's eldest son of his body` — single-string conjunction.** OK Egyptian distinguishes three formulae:

- `zꜣ nswt smsw` — "king's eldest son" (an ordinal claim, attested as a Rangtitel for *Titularprinzen* per Schmitz 1976).
- `zꜣ nswt nj ẖt.f` — "king's son of his body" (an attestation of biological direct kinship, distinguishing from titular sons).
- `zꜣ nswt smsw nj ẖt.f` (or its variants `zꜣ nswt nj ẖt.f smsw`, `… mrjj.f`, etc.) — "king's eldest son of his body", the *conjoined* form.

The `roles` vocab term `king's eldest son of his body` corresponds **only** to the conjoined form, attested as a single composite title string in `titles_from_baud`. **Two separate titles each carrying one marker do not satisfy it** — even when the same row also separately attests `zꜣ nswt nj ẖt.f` and `zꜣ nswt smsw`.

This is stricter than the loose prosopographic convention, which often treats co-attestation across a titulary as evidence for the conjoined claim (Schmitz, Strudwick, and Baud himself all do this analytically in vol. 1). The strict reading is a deliberate project-internal choice: it keeps `roles` mechanically derivable from a deterministic test (`test_eldest_son_role_requires_smsw_and_nj_khet_f_in_same_title` in the test suite, which iterates every row and fails loud on violations), and it keeps the `roles` controlled vocabulary unambiguous about *what kind of attestation* it represents.

**Matching consequence.** A row whose holder is catalogued by a downstream museum as "king's eldest son of his body of King X" but whose Baud titulary lists `smsw` and `nj ẖt.f` only as separate titles will *not* carry the `roles` term. The `titles_from_baud` field still contains both Egyptian titles verbatim, so a Phase-A matcher that wants the looser reading can recover it from there. Curators reading an empty `roles` field should consult `titles_from_baud` before concluding "Baud doesn't attest the kinship at all."

The conjunction rule is enforced both at correction time (in `fix_rows.py` chunk-2/4/5/7 + sweep-2026 rationales) and at test time (the universal invariant test).

## Issue #178 schema additions (2026-05-02 audit-fix)

The schema-audit fix added the following typed fields. Every row carries every field after `fix_rows.py` runs (closure-tested by `test_178_every_row_has_every_new_field`):

- `is_joint_entry: bool` — True for the rare headword that catalogues two persons under one number (Shape J). As of the 2026-05-02 audit, exactly one row qualifies: `baud-209` ("Snj* et Zzj*"). The two service-personnel names live in `co_holders: list[{name, service_personnel}]` so consumers don't have to parse the headword. Authoritative count is `test_178_joint_persons_canonical_set`.
- `entry_kind: str` — typed enum `{"person", "joint_persons", "collective_monument", "attribution_pending"}`. Replaces the convention of inferring kind from `is_collective_monument` (since dropped) and from "is the headword 'Nom perdu'?" (now a `name_status` flag).
- `name_status: str` — typed enum `{"attested", "lost", "tentative", "anonymous"}`. `lost` = Baud's headword "Nom perdu" / "Nom(s) perdu(s)" — name once attested but damaged. `anonymous` = Baud's headword "Anonyme" / "anonyme" or unnamed queens cited only by relation — name never inscribed. The lost/anonymous distinction is load-bearing; consumers must not collapse them. `tentative` = Baud explicitly hedges the headword reading (e.g. "Nom perdu, dit «Ptḥ-mr-zt.f»"). Authoritative counts: `test_178_lost_name_canonical_set` (13 rows), `test_178_anonymous_canonical_set` (8 rows), `test_178_tentative_canonical_set` (3 rows).
- `candidate_baud_ids: list[str]` — for `attribution_pending` rows, the list of plausible baud_ids the row might equal. As of the 2026-05-02 audit, exactly one row: `baud-39` (= `["baud-36", "baud-37", "baud-38"]`, per Baud's "Iʳᵉ, II, ou autre" headword + DIVERS option (c)). Authoritative count is `test_178_attribution_pending_canonical_set`.
- `pm_refs: list[str]` — split from `pm_ref` on `;` and ` et ` separators. Baud's French convention elides the "PM" prefix on `et`-continuation tokens (`PM 407 et 414` ≡ `[PM 407, PM 414]`); the elided prefix is restored in the typed list.
- `monuments: list[{document_id, monument, localisation}]` — structured per-document split of Baud's `1: ...; 2: ...` numbered-document enumeration. Single-monument rows produce a 1-entry list with `document_id=1`. Per-document `localisation` defaults to the row's single `localisation`, but is overridden by the per-doc `à <Place>` extractor when Baud's prose distinguishes per-document sites (e.g. baud-22 doc 2 = Héliopolis vs row-level Saqqara, baud-85 doc 3 = Byblos). The extractor only catches the `à <Place>` preposition with a clause-terminus lookahead; Baud's other locality prepositions (`de`, `dans`, `du temple ... de`) fall back to the row-level value, so phase-A site reconciliation still has work to do for full per-document coverage.
- `father_baud_id`, `mother_baud_id: str | None` — typed cross-reference companion to `father_name`/`mother_name`. Populated when Baud's name string ends in `[N]` (e.g. `"Pépi I [37]"` → `baud_id = "baud-37"`).
- `father_confidence`, `mother_confidence: str | None` — enum `{None, "attested", "probable", "per_baud", "uncertain"}`. Derived from the hedge token in the name string (`(probable)`, `(per Baud)`, `(?)`). The hedge token is **kept** in the name string so the field remains re-derivable and conventional readers see the source's wording.
- `spouse_baud_ids`, `children_baud_ids: list[str | None]` — list-parallels to `spouse_names`/`children_names`. Element `i` is the resolved baud_id for `spouse_names[i]` (None if no `[N]` cross-reference is present in the name string).

The companion-field design (`<field>_confidence` enum + raw-name preservation) is preferred over restructuring the name field into a dict because it matches the Phase-0 corpus convention of preserving Baud's verbatim wording for hedge audit trails.

## Rights

IFAO, 1999, in copyright. Per ADR-017 and the Phase-0 playbook's rights policy, this extract contains only **factual data** — names, kinship relations, Baud's verbatim title lists, monument/tomb/PM references, attested dynasty or reign dates, and (optionally) short hedge fragments from Baud's prose. The source PDF is not committed (lives in `proprietary/books/`, gitignored). Per-agent extraction JSONL under `raw/` is gitignored. **No verbatim OCR of Baud's prose is committed** — prosopographical paragraphs are explicitly the unsafe-to-commit category per the playbook, so extractors Read the sub-PDF directly and write only structured JSONL. `notes_from_baud` carries at most a 2-sentence fragment when a hedge is load-bearing.

**Interpretive-facts caveat.** Baud's attributions are *scholarly judgments* woven in with factual headwords. When a filiation or role depends on Baud's inference rather than an inscribed attestation, the field carries the hedge convention (`"X (probable)"`, `"[X]"`, `" (per Baud)"`) so Phase A can distinguish attested-in-the-source from asserted-by-Baud. The playbook's § "Interpretive facts are still facts, but cite them as such" applies.

## Method

Per ADR-017: extractors Read the sub-PDF directly (no committed OCR) → 3 parallel extraction subagents on Claude Opus 4.7 → deterministic majority-vote merge → egyptologist-reviewer LLM pass → `fix_rows.py` for deterministic post-processing and spot corrections. See `transcribe.md` for the chunk-specific pipeline.

**Review.** The `egyptologist-reviewer` Claude Code subagent has walked the reconciled chunk-1 extract against the source PDF. Flagged corrections are applied via `fix_rows.py` and logged in `merge-disagreements.txt` under `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED`. **A human Egyptologist sign-off has NOT been performed** — the extract is provisional until that happens (ADR-017 step 6).

## Known gaps / Phase A notes

- **Role-code vocabulary.** The `roles` vocabulary is seeded from chunk 1 and will grow across chunks as Baud's Corpus surfaces new titles. Phase A authors the canonical expansion table. Specific chunk-1 gaps flagged by the reviewer passes and deferred to the chunk-2 prompt update:
  - **`steward of the king's children`** (for `jmj-r prw msw nswt` / `jmj-r pr jnꜥwt nwt msw nswt` / similar). Affects baud-10, baud-25, baud-34, baud-40 — each has an administrative king's-children-household title that doesn't map cleanly to the current vocab. baud-40's override already pins `priest of the royal pyramid` + `priest of the king`; the king's-children-steward role remains unrepresented. When the vocab is expanded in chunk 2, a `fix_rows.py` backfill over these four rows is the cleanest way to populate them.
- **Transliteration normalisation.** Baud uses the French Egyptological school's conventions (dot for suffix, `j` vs `i` for iod, morpheme-boundary marking). `name_egyptian` preserves his form verbatim; Phase A normalises across sources.
- **Overlap with D&H earlier chapters.** D&H's Chapters 1–2 also cover OK queens; both are extracted, and Phase A reconciles by name + parent + spouse triangulation. D&H disambiguator letters are NOT the same as Baud's numeric IDs.
- **Porter-Moss III cross-reference.** Tomb designations (`G xxxx`, `D xx`) are preserved verbatim. Resolution to canonical PM III site entries happens in Phase A after `sources/porter-moss-memphis/` lands.
- **Appendix A rejection.** Baud himself flags appendix A (p. 628) as containing erroneous or uncertain attributions. We do not extract it; any cross-reference in a main-Corpus entry that points to `[appendix A]` is preserved verbatim in `notes_from_baud` when present.
