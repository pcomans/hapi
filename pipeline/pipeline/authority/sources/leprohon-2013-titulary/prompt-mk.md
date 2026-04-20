# Extraction prompt — Leprohon 2013 chunk 4 (Chapter V Middle Kingdom — Dyn 11b + Dyn 12)

Pass this to **three** independent Claude Code subagents in parallel. Each agent writes its JSONL output to a distinct filename (`agent-{a,b,c}-mk.jsonl` per the multi-chunk pattern). The three outputs are then merged by `merge.py` via majority vote.

---

You are extracting structured king data from the pypdf+MdC-normalised text of Leprohon, Ronald J. (2013) *The Great Name: Ancient Egyptian Royal Titulary*, SBL Writings from the Ancient World 33. Ed. Denise M. Doxey.

**Input:** the deterministic pypdf+MdC chunk file at

`/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/chunk-p75-p81-pypdf.md`

This chunk covers physical PDF pages 75–81 = printed pages 54–60. It contains the opening of Chapter V Middle Kingdom: **Dynasty 11b** (late Eleventh Dynasty — Mentuhotep II, III, IV) and **Dynasty 12** (Amenemhat I-IV, Senwosret I-III, Queen Sobekneferu). The chunk file's last page (physical 81 / printed 60) ALSO contains the opening prose of Dynasty 13, which is OUT OF SCOPE for this chunk — stop at the `Dynasty 13 (1782–1650 B.C.E.)` header and do not emit any Dyn 13 rows.

**Output:** write your final JSONL to

`/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/agent-{a|b|c}-mk.jsonl`

One JSON object per line. No preamble, no code fences, no trailing newline required.

## Prerequisite reading

Read the chunk-1 prompt `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/prompt.md`, chunk-2 prompt `prompt-old-kingdom.md`, and chunk-3 prompt `prompt-fip.md` first. The schema, field semantics, and hazard catalogue carry over; chunk-4 adds ONE new top-level field and changes how a few specific name-row layouts are handled.

## New schema field: `stage_suffix`

Chunk 4 introduces a new top-level field to represent Leprohon's **titulary-stage** numbering. Several Middle Kingdom kings reformed their titulary mid-reign and Leprohon marks the successive titularies with letter-suffixed headwords: `5a. MENTUHOTEP II (a)`, `5b. MENTUHOTEP II (b)`, `5c. MENTUHOTEP II (c)` for Mentuhotep II's three reform stages; `1a. AMENEMHAT I (a)`, `1b. AMENEMHAT I (b)` for Amenemhat I's pre-/post-Itj-tawy-move reforms.

Schema:

- `stage_suffix: str | None`. Single lowercase letter `"a"`, `"b"`, `"c"` when the headword carries the suffix; `null` when the king has a single unified titulary.
- `leprohon_id`: format `leprohon-{dyn_group}.{NN}{stage_suffix}`. Examples: `leprohon-11b.05a`, `leprohon-11b.05b`, `leprohon-11b.05c`, `leprohon-11b.06`, `leprohon-11b.07`, `leprohon-12.01a`, `leprohon-12.01b`, `leprohon-12.02`, ..., `leprohon-12.08`.
- `sequence_in_chapter_section: int` — just the NUMERIC part (e.g. `5`, `1`, `10`). The letter lives in `stage_suffix`, not in the sequence number.
- `display_name`: include the parenthesised stage marker verbatim. `"Mentuhotep II (a)"`, `"Mentuhotep II (b)"`, `"Mentuhotep II (c)"`, `"Amenemhat I (a)"`, `"Amenemhat I (b)"`. Downstream consumers recognise the three Mentuhotep II rows refer to the same king by the `"Mentuhotep II "` display-name prefix.
- Emit ONE row per stage, each with its own full cross-name-type titulary. Do NOT collapse stages into `is_variant` entries within a single name-list — that would lose the cross-name-type correlation ("in stage b, Throne is `nb ḥpt rꜥ` AND Nebty is `nṯri-ḥḏt`").
- The first name entry's `source_note` (on stage a only, i.e. on `leprohon-11b.05a` Mentuhotep II stage a and `leprohon-12.01a` Amenemhat I stage a) should carry a canonical marker:
  ```
  "Leprohon distinguishes this king's successive titulary-stages by letter suffixes (5a/5b/5c for Mentuhotep II's three reforms; 1a/1b for Amenemhat I's pre-/post-Itj-tawy-move). Each stage is emitted as its own row to preserve cross-name-type correlation."
  ```
  Append it AFTER any existing footnote content. Stages b/c inherit the knowledge from stage a's source_note — their own source_notes carry only stage-specific content (e.g. footnote 28 for Amenemhat I stage b documents the Itj-tawy move rationale).

## Dyn 11b sequence — continuation from Dyn 11a, NOT reset

Normally each dynasty section restarts numbering at 1 (as in chunks 1/2/3). Dyn 11b is **the exception**: Leprohon continues the numbering from Dyn 11a's tail. Dyn 11a had 4 entries (Mentuhotep I = 1, Intef I/II/III = 2/3/4 per chunk 3). Dyn 11b starts at entry **5**, not 1.

- Mentuhotep II → entries `5a`, `5b`, `5c` (3 rows)
- Mentuhotep III → entry `6` (1 row)
- Mentuhotep IV → entry `7` (1 row)

Total Dyn 11b: 5 rows.

Dyn 12 resets normally to 1 (Amenemhat I = 1a/1b, Senwosret I = 2, etc.).

## Dyn 11b / Dyn 12 king density

Expected counts — verify against the chunk file:

- **Dyn 11b: 5 rows** (Mentuhotep II stages a/b/c + Mentuhotep III + Mentuhotep IV)
- **Dyn 12: 9 rows** (Amenemhat I stages a/b + Senwosret I + Amenemhat II + Senwosret II + Senwosret III + Amenemhat III + Amenemhat IV + Queen Sobekneferu)

**Total: 14 rows.** If you produce fewer than 12 or more than 16, re-read the chunk file and re-scan for missed entries / mis-parsed headers.

## MK-specific name-type conventions

1. **Numbered variants within a name-type list** — Middle Kingdom kings have name-types with variants (`Horus 1`, `Horus 2`, `Golden Horus 1`, `Golden Horus 2`, `Throne 1`, `Throne 2`, etc.) within a single stage. Example: Mentuhotep III stage has `Golden Horus 1: ḥtp(w)` AND `Golden Horus 2: sḫm`; `Throne 1: sꜥnḫ kꜣ rꜥ` AND `Throne 2: snfr kꜣ rꜥ*`. Emit these as separate entries in the same name-list with `variant_index: 1, 2, ...` and `is_variant` tracking position, same convention as chunks 1-3.

2. **Asterisked name entries inside Throne/Birth lists** — Leprohon uses `*` trailing a specific name-row to mark Ramesside-list-only attestation for THAT name entry specifically (e.g. Mentuhotep III `Throne 2: snfr kꜣ rꜥ (senefer ka ra),* The one whom the ka of Re has made perfect` — fn. 17 notes this is from the Karnak List). In chunks 1-3 this signal went to `later_cartouche_names` or `later_horus_names`. For MK throne/birth variants marked this way, KEEP the entry in its original name-type list (Throne/Birth/etc.) but append to its `source_note`:
   ```
   "This specific name-entry is Ramesside-list-attested only per Leprohon's trailing asterisk — the king himself is contemporarily attested."
   ```
   Do NOT move the entry to `later_cartouche_names`/`later_horus_names`, and do NOT tag the king-level row as Ramesside-only.

3. **Birth name with `sꜣ rꜥ` prefix** — MK Birth names often start with `sꜣ rꜥ` ("son of Re") in the transliteration (`Birth: sꜣ rꜥ mnṯw ḥtp(.w)`). Preserve the full transliteration verbatim — do NOT strip the `sꜣ rꜥ` prefix.

4. **Contemporary-attestation default** — Leprohon's Dyn 11b opening prose says: "The royal names from this period are mostly well attested in contemporary records. There will, therefore, be no need to indicate the provenance of the name." Meaning: no kings in Dyn 11b are Ramesside-only. Same policy for Dyn 12. Do NOT append the Ramesside-only tag to any king in this chunk. (Individual name-entries marked with `*` — see rule 2 — are the only exception, and that tagging is at the entry level, not the king level.)

5. **Descriptive footnote chains** — MK kings have long footnote chains with provenance, attestations, and scholarly discussion. The `attested_in` field remains primary-attestation-only (Turin / Abydos / Saqqara king-list numbers when present, which is rare for MK since MK kings are mostly attested on contemporary monuments). `source_note` gets the scholarly chain, trimmed to non-attestation content.

## Dyn 12 BCE-range in dynasty label

Dyn 12 header reads `Dynasty 12 (1991–1782 B.C.E.)`. As with prior chunks: do NOT include the BCE range in `dynasty_label` — just `"Dynasty 12"`. BCE ranges live in a separate chronology authority.

## Output ordering

Sort the emitted rows in your output file by the merge.py sort key order:
1. `leprohon-11b.05a`, `11b.05b`, `11b.05c`, `11b.06`, `11b.07`
2. `leprohon-12.01a`, `12.01b`, `12.02`, `12.03`, `12.04`, `12.05`, `12.06`, `12.07`, `12.08`

`merge.py` re-sorts anyway, but consistent ordering aids disagreement-diff readability.

## Final response

In your final response message, give a one-line summary: row count per (sub-)dynasty with stages breakdown (e.g. `"11b:5 (5a/5b/5c/6/7), 12:9 (1a/1b/2-8)"`), highest footnote number seen, any transliteration-vs-anglicised disagreements or MdC edge cases you flagged, and confirmation that stages a/b/c rows carry their own full titulary (not collapsed to variants). Under 100 words.
