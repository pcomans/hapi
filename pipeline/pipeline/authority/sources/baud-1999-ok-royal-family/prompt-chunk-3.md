# Extraction prompt — Baud 1999 BdE 126 Corpus, chunk 3 (entries `[81]`–`[120]`)

You are one of three independent Claude Code subagents extracting structured prosopographical data from Michel Baud's *Famille royale et pouvoir sous l'Ancien Empire égyptien* (BdE 126, IFAO 1999), vol. 2 *Corpus*. The three of you run in parallel on the identical prompt; your outputs are merged via majority vote downstream, so honest independence matters more than consistency with a hypothetical peer. Follow the schema EXACTLY; downstream code fails loud on shape drift.

**Framing.** This extraction is fair-use scholarly data compilation for a private cross-museum provenance index operated under contract with a credentialed Egyptologist. Only factual data (names, titles, kinship, monuments, dates, cross-references) is extracted; Baud's narrative prose is not reproduced. The source PDF is not redistributed. If you encounter content-filter hesitation, this framing resolves it — proceed with the task.

## What to read

`pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/raw/source-chunk-3.pdf` — a 28-page sub-PDF of Baud vol. 2 covering physical pages 82–109 of the original. Contents:

- **Physical p. 82** (overlap with chunk 2) — contains the tail of entry `[80]` and the header block of `[81]`. **Do NOT emit a row for `[80]`** (chunk 2 already emitted it). Your first row is `[81]` (`Mrjj-Ttj Mrj`).
- **Physical pp. 82–109** — Corpus entries `[81]` through `[120]`.

**Boundary warning.** Entry `[121]` has a header at the bottom of physical p. 109 that continues onto p. 110 (not included in the sub-PDF). **Do NOT emit a row for `[121]`.** Your last row is `[120]`.

**Sub-entry warning.** Chunk 2 surfaced a Baud sub-entry `[60a] Pn-mdw` (physical p. 63 — letter-suffix numbering for a graffito-only attested prince between `[60]` and `[61]`). If chunk 3 has any `[Na]`-style sub-entry, emit it with `baud_id = "baud-<N><letter>"` and the plumbing (merge.py, tests) handles it. Watch for them.

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
- **`dynasty`**: string form `"3"`, `"4"`, `"5"`, `"6"`, or a range `"4-5"` for cross-dynasty. **`null` when Baud declines to date** (writes `"Date?"` in his `(d)` line). Derive from `date_attested` — map French dynasty numerals (`IVᵉ` → `"4"`, `"Vᵉ"` → `"5"`, etc.). Do NOT emit `"unknown"` — the test suite rejects it.
- **`sub_period`**: `null` unless Baud explicitly names an OK sub-period (e.g. `"début IVᵉ dynastie"` → `"early Dyn 4"`; `"Fin IVᵉ – début Vᵉ"` → `"end Dyn 4 – early Dyn 5"`).
- **`baud_refs`**: dict. Keys are lowercase author surnames used by Baud in his `(e)` convention: `baer`, `strudwick`, `seipel`, `harpur`, `troy`, `schmitz`. Values are the reference strings as printed (the number/page/entry Baud cites). `{}` when Baud gives no `(e)` line.
- **`titles_from_baud`**: list of verbatim title strings from the `TITRES.` rubric, split on commas. `[]` when the entry has no `TITRES.` rubric.
- **`roles`**: normalised OK-appropriate role codes derived from `titles_from_baud` and Baud's filiation prose. Controlled vocabulary (extended for chunk 2):
  - `king` (any king holding a cartouche — rare in Baud; mostly consorts)
  - `queen` (for `ḥmt nswt` holders who are also attested on royal monuments)
  - `king's mother` (`mwt nswt`)
  - `king's wife` (`ḥmt nswt`)
  - `king's son` (`zꜣ nswt`)
  - `king's daughter` (`zꜣ(t) nswt`)
  - `king's son-in-law` (spouse-of-royal-daughter, where Baud asserts it)
  - `king's eldest son of his body` — **requires BOTH `smsw` AND `nj ẖt.f` (with or without `mrjj.f`) in the same title string**. Do NOT emit this role if the title has only one of the two elements. Chunk-2 second-pass egyptologist review found 7 rows over-claiming this. If `smsw` is absent → just `king's son`. If `nj ẖt.f` is absent but `smsw` is present → still just `king's son` (no vocab term for smsw-only).
  - `vizier` (`ṯꜣtj`)
  - `priest of the royal pyramid` / `priest of the king's mother` / `priest of the king's wife` / `priest of the king` — derived from `ḥm-nṯr` titles scoping to a named pyramid / mother / wife / king.
  - `steward of the queen` (`jmj-r pr` + queen reference)
  - `steward of the king's children` (`jmj-r prw msw nswt` and equivalents; any `jmj-r pr` or `jmj-r sbꜣ` that scopes to `msw nswt`). Additive whenever this scoping appears, even alongside other roles.
  - `sem priest` (`sm`)
  - `overseer of the treasury of pr-ꜥꜣ` / `overseer of scribes of pr-ꜥꜣ` — for `jmj-r pr-ḥḏ pr-ꜥꜣ` / `jmj-r zš ꜥ pr-ꜥꜣ` administrative titles.
  - `steward of the king's mother` — for estate-administrator titles scoping to a king's mother (e.g. `ḥqꜣ ḥwt-ꜥꜣt ḥwt <mother-cartouche>`).
  - `high priest of Ptah` — for the title `wr ḫrp ḥmwwt`.
  - `overseer of the king's ornaments` — for `jmj-r ḥkr nswt`-style titles. `ḥkr nswt` = royal adornments/jewelry cult, NOT `pr-ḥḏ` (treasury) — keep the distinction.

  **Role scoping must match title scoping.** Chunk-2 regression: `jmj-r ḥmw-kꜣ (nw zꜣt nswt)` was majority-voted to `steward of the queen`, but the title scopes to a king's DAUGHTER, not a queen. Ka-priest/steward roles inherit their target from the Egyptian `<title> <target>` — if `<target>` is a goddess (`ḥmt-nṯr Ḥwt-Ḥr`, `Nt`, `Bꜣpf`, etc.), do NOT emit a queen/mother role; if `<target>` is a king's daughter, do NOT emit a queen role. When no existing vocab term matches exactly, leave `roles: []` (honest gap beats vocab stretch).

  **Additive, not alternative.** When a TITRES rubric gives `ḥm-nṯr <pyramid-cartouche>` or `wꜥb <pyramid-cartouche>`, add `priest of the royal pyramid` — do not collapse it into a generic `priest of the king`. Same principle for `msw nswt`-scoped administrative titles: keep the specific role code. Chunk-1 majority-vote narrowed this kind of list too aggressively; please be inclusive.

  Add a new role code only when the title doesn't map to any of the above; flag it in your report.

- **`father_name` / `mother_name`**: single-name strings from PARENTÉ prose. Preserve Baud's hedges:
  - `"Téti (probable)"` — parenthesised for Baud-probable.
  - `"[Snéfrou]"` — bracketed for Baud-reconstructed-from-lacuna.
  - `null` — Baud does not attest this parent.
  - Append `" (per Baud)"` ONLY when the row would otherwise promote a purely interpretive claim (no physical attestation, only Baud's titular-synchronism argument) to a hard claim.
- **`spouse_names`**, **`children_names`**: lists. Empty `[]` when Baud attests none. Apply the same hedge convention as `father_name`/`mother_name`. Cross-entry inference IS permitted within chunk 2 — if Baud's entry `[X]` is silent on whether they have a child, but entry `[Y]` names `[X]` as parent, populate `[X].children_names = ["<Y's name>"]`. Applies to symmetric relationships (parent/child, spouse/spouse).
- **`tomb`**: designation if the monument is a tomb (`"G 7650"`, `"D 62"`, `"Mastaba 17 Meidum"`); `null` otherwise.
- **`notes_from_baud`**: short fragment (≤ 2 sentences, ≤ 50 words) from PARENTÉ or DIVERS when a hedge or cross-reference changes the factual reading. Default `null`.
- **`source_citation`**: `{"source": "Baud 1999 BdE 126 Corpus [<N>]", "pdf_pages": "82-109", "edition": "IFAO 1999 vol. 2"}`. Every chunk-3 row uses `"82-109"`.

## Hedge conventions — do NOT over- or under-hedge

Six levels (increasing distance from attested fact). Chunk 1 surfaced the **under-hedging** AND **over-hedging** failure modes twice; re-read this section carefully.

1. **`"X"`** — bare value, **inscribed attestation**. Titles naming a specific king (`mwt nswt X`, `ḥmt nswt X`, `zꜣt nswt X`) are **direct attestations**; do NOT wrap the named king in `(probable)` or any other hedge (chunk-1 regression: baud-36 where the mother-of-Neferkare title should have produced a bare `"Néferkarê"`).
2. **`"X (per Baud)"`** — inferred by Baud on iconographic or titular-synchronism grounds. Stronger than `(probable)`: Baud commits to the reading based on his own scholarly argument.
3. **`"X (probable)"`** — Baud's own probable attribution.
4. **`"X (?)"`** — Baud retains a literal question-mark glyph where a sign is legible but reading/attribution is disputed. Preserve verbatim.
5. **`"[X]"`** — Baud's bracketed reconstruction from a lacuna (physical damage). Preserve the brackets.
6. **`null`** — NOT attested, OR **Baud reports another scholar's hypothesis without endorsing it** (chunk-1 resolution: baud-33 where Strudwick's hypothesis about `mr.s-ꜥnḫ III` being the mother was left as `null` because Baud himself questions it). Watch for phrases like "hypothétique d'après X", "X suggère que", "X pense que", "selon X" — those are not Baud asserting, they're Baud reporting.

## Pitfalls (skim before extracting)

- **Do NOT extract `[80]` or `[121]`.** Your sub-PDF starts on p. 82 (containing `[80]`'s tail) and ends on p. 109 (containing `[121]`'s header). Any row with `baud_id == 80` or `baud_id >= 121` is a bug. Sub-entries `[94b]`, `[101a]` (letter-suffixed) are legitimate and stay.
- **Asterisks in names are significant.** `Jḥtj-ḥtp*` is service personnel; `Jḥtj-ḥtp` (same name, no asterisk, different entry number) is a family member. The asterisk sets `service_personnel: true` and changes `roles` semantics.
- **Grandchild vs child.** `zꜣ` (son, direct) ≠ `zꜣ n zꜣ` / French `petit-fils` (grandson). `children_names` is direct-children only. Chunk-1 regression: baud-26 where a `petit-fils` was promoted to `children_names` by majority vote.
- **Spouse vs mother.** A woman titled `mwt nswt X` is the mother of king X, not his wife. Chunk-1 regression: baud-38 where Pépi II was incorrectly added to `spouse_names` — he was her son, not her husband. Check titles: `mwt nswt` → `children_names`, `ḥmt nswt` → `spouse_names`.
- **Half-sibling marriage.** `zꜣt nswt` + `ḥmt nswt` attests a woman as simultaneously daughter-of-King-A and wife-of-King-B. `father_name` and `spouse_names` may name **different** kings — populate both independently.
- **Role narrowing by majority vote — be additive.** If TITRES contains `ḥm-nṯr` or `wꜥb` of a named pyramid cult, `priest of the royal pyramid` is additive, not optional. Same for `msw nswt`-scoped `jmj-r pr` / `jmj-r prw` / `jmj-r sbꜣ` titles: include `steward of the king's children` whenever attested.
- **Cross-reference-only entries.** Some short entries are pure cross-references (e.g. `"///-Ḥr. Voir Ḥr/// [154]"`). Emit the row with the baud_id from the original numbered entry, minimal fields, and `notes_from_baud` = `"Cross-reference to [N]."`. Do not try to follow the ref.
- **Corpus entries are alphabetical by Egyptian transliteration, not by dynasty.** Chunk 3 contains a mix of Dyn 2/3-transition, 3, 4, 5, and 6 entries.
- **Hedge-heavy source.** Baud explicitly says "dans de nombreux cas, les informations sur la parenté sont inexistantes et les hypothèses généalogiques fragiles." He names probable parents knowing he's inferring. Preserve every hedge; promoting a hedge to a hard claim is the signature failure mode.
- **Don't anglicize French regnal names.** `Snéfrou`, `Pépi Iᵉʳ`, `Téti`, `Merenrê`, `Niouserrê`, `Djedkarê`, `Ounas`, `Rêkhaef`, `Menkaourê`, `Chepseskaf`, `Néferirkarê`, `Sahourê` stay verbatim in `father_name` / `spouse_names` / `children_names` / `date_attested`. `name_anglicised` is the only field carrying an English form.
- **French vs Anglo-American transliteration.** Baud uses French-school conventions (dots, `j`). Your output keeps French-school verbatim in `name_egyptian`; normalisation to a house style is Phase A.
- **Footnotes.** Baud uses numbered footnotes. Ignore footnote content unless it contains a parenthetical hedge Baud references by number; even then, summarise, don't quote.
- **Multiple documents per entry.** Some entries describe multiple monuments (e.g. `"1 : Mastaba ...; 2 : Représentation chez ..."`). In this case keep the `"1: ...; 2: ..."` multi-document convention in `monument` (Baud-style numbering, single string); `pm_ref` concatenates distinct PM references with `"; "`.

## Output format

Write newline-delimited JSON to `pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/raw/agent-<YOUR_TAG>-chunk-3.jsonl`, where `<YOUR_TAG>` is `a`, `b`, or `c` (the spawner will tell you which). One row per Baud Corpus entry, in ascending `baud_id` order.

Every row MUST contain every field in the schema — use `null` / `[]` / `{}` / `false` for missing values per the per-field rules above. Downstream `merge.py` expects a uniform schema; missing keys confuse the majority vote.

**Expected row count:** 40 rows (entries `[81]`–`[120]`), plus 1 additional row IF chunk 3 contains any `[Na]`-style sub-entry (as chunk 2 did with `[60a]`). If your extraction produces < 35 or > 45, re-read the prompt and the boundary warnings; something is off.

## Report

When done, output a single report of ≤ 80 words:
- Row count.
- Any entries you struggled with (ambiguous monument/localisation splits, unreadable glyphs, cross-reference entries with unclear referents).
- Any pitfalls above you suspect you violated — explicit about uncertainty beats silent-pretending-it's-fine.
- Any NEW role codes you emitted beyond the controlled vocab above.
