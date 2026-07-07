# Extraction prompt — Porter & Moss Vol III.1, Chunk 36

> **Thirty-sixth chunk — first PM III.1 chunk since the Gîza work (chunks 1–3, 6–19).** **PYRAMID-FIELD OF ABÛSÎR** — the complete Abûsîr section: § I Sun-temple, § II Pyramids (A–D), § III Necropolis (A–C), § IV Miscellaneous. PM III.1 2nd ed. 1974 (ed. Málek), printed pp.324–350. Per the 2026-05-19 all-dynastic scope expansion (mvp-tasks.md item 3), Abûsîr is in scope; the README's older "stretch/deferred" note for Abûsîr is superseded. This prompt is **self-contained**.
>
> **Source-file note:** the PM III.1 PDF was re-fetched 2026-07-04 (complete 460-page Griffith Institute scan, SHA `27777b0…955ec`) because the prior scan was missing exactly these pages. Its text layer is a noisy OCR layer (see Diacritics/OCR section) — read carefully.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-36-p351-p378-abusir.txt` (PDF physical pp.351–378 = printed pp.324–351). Each physical page is delimited by a `===== PDF physical page N =====` marker and PM's own printed page number appears in the running head line (e.g. `Pyramid-field of Abu~zr 325`).

**Source:** PM III.1 2nd ed. 1974, ed. Málek. **Output:** one JSONL line per row, `json.dumps(..., sort_keys=True, ensure_ascii=False)`, sorted by `tomb_id`. Write to ONE of `raw/agent-{a,b,c}-chunk36.jsonl`.

## Scope

The Abûsîr section, in PM's printed order:
- **§ I. SUN-TEMPLE** (printed 324) — one royal cult structure.
- **§ II. PYRAMIDS** (printed 326) — lettered royal pyramid-complexes **A**, **B**, **C**, **D** (Dyn V). Each opens with a `PYRAMID-COMPLEX OF <KING>` (or `PYRAMID ATTRIBUTED TO <KING>`) banner.
- **§ III. NECROPOLIS** (printed 340) — private mastabas/tombs, sub-banner **A** (Cemeteries north-east & east of the Neuserreʿ pyramid, itself grouped as *Large Dynasty V Mastabas* / *Dynasty VI and First Intermediate Period Tombs* / *Middle Kingdom Tombs* / *Late Burials*), **B** (Cemetery over the mortuary temple of Neferirkareʿ), **C** (Tombs in the plain south-east of the pyramids).
- **§ IV. MISCELLANEOUS** (printed 349) — see EXCLUSIONS.

You will discover the specific rulers, occupant names, tomb numbers, and exact row count by reading the chunk. The outline above is for scope-coverage confirmation, **not** a per-row answer key — do not fill in names or values from your own knowledge of Abûsîr (Constitutional Rule 1).

**Stop boundary:** the section ends at the `FROM ABÛSÎR TO SAQQÂRA` banner (printed 351, the last physical page in the file). Emit **no** rows from that banner or anything after it.

## How to identify a row

**Shape 1 — Sun-temple (royal).** The `§ I` all-caps `SUN-TEMPLE OF <KING>` banner is a named royal cult structure. Emit ONE row: `occupant_role: "King"`, `attribution_certainty: "attested"`, dynasty per the `Dyn. <Roman>` on the banner line.

**Shape 2 — Royal pyramid-complex main pyramid.** Each `§ II` lettered section (`PYRAMID-COMPLEX OF <KING>` / `PYRAMID ATTRIBUTED TO <KING>`) attributes to the named KING (`occupant_role: "King"`). Emit ONE row per lettered complex, anchored on the main pyramid. If PM hedges the attribution (`attributed to`, `Probably`, `(?)`) → `attribution_certainty: "probable"`. If PM marks the pyramid `Unfinished` → `is_unfinished: true`. Dynasty per the `Dyn. <Roman>` on the banner.

**Shape 3 — Private mastaba / tomb (§ III).** Each all-caps occupant headword under § III is a private tomb. `occupant_role` from PM's title clause (controlled vocab below). Dynasty per the sub-group the headword sits under (*Large Dynasty V* → `"5"`; *Dynasty VI and First Intermediate Period* → `"6"` when PM says Dyn VI, else `null` when PM says only "First Intermediate Period"; *Middle Kingdom* → the Dyn PM prints, else `null` with `sub_period: "Middle Kingdom"`; *Late Burials* → the Dyn PM prints, e.g. Saïte/Ptolemaic). Many § III tombs carry an excavator tomb-number — a `mR <n>` (Schäfer Middle-Kingdom number) or `Sp <n>` (Late-burial number); put that verbatim string in `tomb_aliases`, anchor `tomb_id` on the occupant name.

**Shape 4 — Joint / shared burial.** Where PM gives one tomb with several named occupants (e.g. a mastaba shared by a husband + wife, a collective "children of X" burial, or one excavator-number housing several named coffins): emit ONE row for the tomb, principal occupant in `occupant_name`, the rest in `co_occupants` (`[{"name","role","alt_names"}]`) with parallel `co_occupant_roles`. Set `is_joint_burial: true` only when PM marks no principal occupant (coordinate burial); a husband's mastaba with wife/children stays `is_joint_burial: false` with the husband as principal. A wife named only as "wife of <headword>" inside the headword's own entry folds into that row as a `co_occupant`, not a separate row.

## EXCLUSIONS — emit no row for any of these

Per the source-wide headwords-only policy (PM's descriptive/​object content is out of scope):
- **Sub-architecture of a pyramid/temple:** `SUBSIDIARY PYRAMID`, `UPPER TEMPLE`, `LOWER TEMPLE`, `MORTUARY TEMPLE`, `VALLEY TEMPLE`, `CAUSEWAY`, `SUN-BARK`, `BURIAL CHAMBER`, `SANCTUARY OF <deity>` (a New-Kingdom cult installation inside a Dyn-V temple is not a tomb), and their `Statues` / `Reliefs` / `Blocks` / `Finds` sub-dumps.
- **Object / find catalogues:** any `Statues.`, `Reliefs`, `Blocks, etc.`, `Finds`, `Sealings`, `Papyri`, `Fragments` sub-block listing museum inventory numbers. These are museum objects, not tomb-owners — even when a personal name appears in them.
- **Persons appearing only as finds:** a queen/king/official named only via a statuette, sealing, cylinder-seal, stela, graffito, or dedication (e.g. a queen attested by a statuette inside a king's complex, or a votive-stela dedicator) is NOT a tomb headword — exclude. A row requires the person's own all-caps tomb/structure headword.
- **§ IV. MISCELLANEOUS wholesale** (printed 349–350): PM flags it "Some possibly from North Saqqâra." It is a loose-object catalogue (statues, false-doors, stelae, blocks) — emit no rows, even for named individuals in it.
- **Anonymous / uninscribed fragments:** a bare excavator number with no legible owner name (e.g. an anonymous coffin) — no row.
- **Loose blocks / slabs / offering-fragments** not tied to a named tomb structure.

## tomb_id convention — NEW prefix `ABU-`

`ABU-<DescriptorName>`, mirroring `DAH-` (Dahshûr, chunk 33) and `SAQ-` (Saqqâra). Descriptor is **TitleCase ASCII with Egyptological diacritics stripped** (ayin/macron/underdot removed for the key — same convention as chunks 22/25/26/28–33).

Rules (not per-row answers):
- **Sun-temple** → anchor on the king + structure type so it never collides with that king's pyramid elsewhere in the source: `ABU-SunTemple<King>`.
- **Pyramid-complex** → anchor on the king's conventional English name: `ABU-<King>` (preserve a Roman ordinal if PM uses one; drop internal hyphens/diacritics).
- **Private mastaba** → TitleCase the occupant's primary (bold) name: `ABU-<Name>`. For a `called` / `good name` alias, anchor on the primary name, not the alias.
- **Homonym discipline** — two headwords sharing a name MUST get distinct ids: append that occurrence's PM excavator number (`ABU-<Name>mR<N>`) or a Roman ordinal PM itself assigns to the name. Before finalising each id, scan your other rows for a name collision — do NOT assume there is exactly one such collision, or none.
- Existing `reconciled.jsonl` (849 rows, chunks 1–35) uses G / LG / SAQ* / MAR / DAH / etc.; the new `ABU-` prefix collides with none. If a § I `ABU-SunTemple<King>` id or a § II `ABU-<King>` id happens to match an existing `SAQ-<King>` pyramid id for the same king (a king with monuments at both sites), that is expected — the site prefix keeps them distinct; verify against `reconciled.jsonl` rather than renaming.

## Schema (23 keys, identical to chunks 20–35)

```json
{
  "tomb_id": "ABU-<DescriptorName>",
  "memphite_area": "Abusir",
  "occupant_name": "..." | null,
  "occupant_alt_names": [],
  "tomb_aliases": [],
  "co_occupants": [],
  "co_occupant_roles": [],
  "is_joint_burial": false,
  "occupant_role": "King" | "Queen" | "Prince" | "Princess" | "Vizier" | "High Priest" | "Official" | "Royal Family" | "Unknown",
  "dynasty": "5" | "6" | "12" | null,
  "sub_period": null | "First Intermediate Period" | "Middle Kingdom" | "Late Period" | "Ptolemaic",
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "Pyramid-field of Abusir" | "North-East and East of Pyramid of Neuserre" | "Over Mortuary Temple of Neferirkare" | "Plain South-East of Pyramids",
  "discovery_year": null,
  "discoverer": null,
  "is_unfinished": false,
  "is_uninscribed": false,
  "is_usurped": false,
  "attribution_certainty": "attested" | "probable" | "uncertain",
  "shared_with_tombs": [],
  "notes_from_pm": "..." | null,
  "source_citation": {"page": <int>, "edition": "PM III.1 2nd ed. 1974", "section": "I" | "II" | "III" | "IV"}
}
```

**Field-rule notes:**
- `memphite_area`: NEW VALUE `"Abusir"` for every row this chunk.
- `cemetery`: for the 5 royal rows (§ I sun-temple + § II pyramid-complexes) use `"Pyramid-field of Abusir"`. For § III private tombs use the sub-banner descriptor: III.A → `"North-East and East of Pyramid of Neuserre"`, III.B → `"Over Mortuary Temple of Neferirkare"`, III.C → `"Plain South-East of Pyramids"`.
- `source_citation.section`: `"I"` for the sun-temple, `"II"` for the pyramid-complexes, `"III"` for necropolis tombs, `"IV"` only if (against the exclusion rule) something in § IV were emitted — it should not be. `page` is PM's **printed** page (from the running head), an integer.
- `dynasty`: Roman → Arabic-decimal STRING (`"5"`, `"6"`, `"12"`). `null` when PM gives no dynasty (e.g. a pure "First Intermediate Period" or undated tomb) — use `sub_period` to carry the period label in that case.
- `date_bce_approx_start` / `date_bce_approx_end`: always `null` (BCE dates come from the king authority at Phase A).
- `attribution_certainty`: `attested` = PM names the owner without hedge; `probable` = PM hedges (`attributed to`, `Probably`, `(?)`, `perhaps`); `uncertain` = stronger hedge or owner-identity effectively unknown.
- `notes_from_pm`: short PM-faithful headword prose — the title/role clause, dating clause, Lepsius "Pyramid" number, excavator (Borchardt/Ricke/Schäfer) attribution, and any condition note (`Unfinished`). **Drop** the museum-object bibliography dumps, cartouche glyph-noise, and plate lists. One or two sentences max.

## Diacritics / OCR normalisation (this scan is noisy)

The text layer is OCR with consistent artifacts — normalise in `occupant_name` / `occupant_alt_names` / `notes_from_pm`, but never invent:
- **Ayin (ʿ)** renders as `<` or a raised `c` — a royal or personal name printed `…RE<` / `…REc` / `…<name` normalises to the ayin form (`…Reʿ`, `ʿ…`). Use ayin **U+02BF** (`ʿ`, MODIFIER LETTER LEFT HALF RING) — the source-wide convention — NOT an apostrophe and NOT U+A725 (`ꜥ`, EGYPTOLOGICAL AIN). Those two glyphs look near-identical; emit U+02BF only.
- **Underdot-Ḥ (ḥ)** renders as `l).` / `I;I` / `!t` / `l;t` (e.g. the graffito name `I;Iareml).ab` → `Ḥaremḥab`).
- **Macron ē/ū** — PM prints them on royal Rēʿ-names; preserve where legible, else the plain vowel.
- **Cartouche glyphs** render as junk (`~A·`, `⊙`, boxes) — ignore; take the transliterated Latin-caps name.
- `$` in headers is the `ûsî` artifact (`ABU$IR` = Abûsîr) — header noise, not part of any name.
- `tomb_id` descriptors are ASCII-only — strip ALL of the above (ayin, macrons, underdots) to the nearest plain ASCII letter.

## Calibration self-check (not a hard rule)

Structural expectation from PM's § I–III layout:
- § I: 1 sun-temple row.
- § II: 4 pyramid-complex rows (one per lettered A–D section; a subsidiary pyramid is NOT its own row).
- § III: the bulk — the Large-Dyn-V mastabas + the Dyn-VI/FIP tombs + the Middle-Kingdom `mR`-numbered tombs + the Late `Sp`-numbered burials.

Total lands in the **≈ 26–34 row** range. If your count falls far outside that, re-read: check you haven't (a) minted rows for subsidiary pyramids / temples / find-catalogues / § IV, (b) split a husband+wife or a multi-coffin excavator-number into separate rows instead of one joint row, or (c) missed a named mastaba headword by mistaking it for a find-block.

## Constitutional Rules (binding)

- **Rule 1 (scholar-grade, source-traced):** every field value traces verbatim to text in `raw/chunk-36-p351-p378-abusir.txt`. Do NOT synthesise names, filiations, dates, titles, or monuments from training knowledge of Abûsîr. If the OCR is ambiguous, prefer a conservative `null` over a guess.
- **Rule 2 (no silent picks):** on genuine ambiguity (OCR glyph you can't resolve; body prose that might disambiguate but isn't in the headword), leave the field `null` — the three-agent merge will surface it.

## Stop criterion

Emit one row per row-emitting headword (Shapes 1–4) in scope. Sort by `tomb_id`. Verify each row has all 23 keys (use `null`/`[]`, never omit), `dynasty` is a STRING or null, `memphite_area` is `"Abusir"`, `source_citation.page` is an integer printed page.
