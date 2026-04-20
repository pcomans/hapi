# Extraction prompt — Leprohon 2013 chunk 6 (Chapter V Middle Kingdom tail — Dyn 13a + 14 + 14a)

Pass this to **three** independent Claude Code subagents in parallel. Each agent writes to `agent-{a,b,c}-dyn13a-14.jsonl`.

---

You are extracting structured king data from Leprohon, Ronald J. (2013) *The Great Name: Ancient Egyptian Royal Titulary*, SBL WAW 33.

**Input:** `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/chunk-p93-p101-pypdf.md` — physical pp. 93–101 = printed 72–80. Contains Leprohon's late-MK Ramesside-added sub-dynasties **Dynasty 13a**, **Dynasty 14**, and **Dynasty 14a**.

**Output:** `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/agent-{a|b|c}-dyn13a-14.jsonl`

## Prerequisite reading

Read prompts for chunks 1–5 first (`prompt.md`, `prompt-old-kingdom.md`, `prompt-fip.md`, `prompt-mk.md`, `prompt-dyn13.md`) for schema, hazard catalogue, and all rules previously established. This prompt adds only what's specific to chunk 6.

## Chunk-6 specifics

### Dynasty labels, chapter, IDs

All rows: `chapter: "Middle Kingdom"` (Leprohon places all three sub-dynasties in chapter V, NOT in chapter VI SIP).

- **Dyn 13a:** `dynasty_number: 13`, `dynasty_label: "Dynasty 13a"`, IDs `leprohon-13a.NN`. Sequence resets at 1 (not continued from Dyn 13's tail — Dyn 13a is a separately-numbered Ramesside-list sub-section, unlike the Dyn 11b continuation convention).
- **Dyn 14:** `dynasty_number: 14`, `dynasty_label: "Dynasty 14"`, IDs `leprohon-14.NN`. Numbering resets at 1.
- **Dyn 14a:** `dynasty_number: 14`, `dynasty_label: "Dynasty 14a"`, IDs `leprohon-14a.NN`. Numbering resets at 1.

All rows: `stage_suffix: null` (no multi-stage kings in this chunk).

### Ramesside-only tagging

Apply the canonical tag (`"Ramesside-attested only — no contemporary attestation per Leprohon's headword asterisk."`) to the first populated name-entry's `source_note` on every row whose HEADWORD carries a trailing `*`. The per-entry asterisks (on individual name-rows rather than the headword) stay in their originating name-type list with a per-entry source_note flagging later-attestation provenance — same policy as chunks 4 and 5.

Dyn 13a as a whole is a Ramesside-list sub-section but Leprohon still uses `*` marking selectively per headword; do not assume all Dyn 13a kings carry the tag — check each headword.

### Non-standard Dyn 13a headwords (entries 5, 6, 7)

Three Dyn 13a entries have atypical headwords:

- `5. HORUS MERYTAWY` — a king attested only by a Horus name; no standard SMALLCAP king name.
- `6. TWO LADIES USERKHAU` — a king attested only by a Nebty/Two-Ladies name.
- `7. SEKHAENPTAH` — standard SMALLCAP.

For entries 5 and 6, the `display_name` should preserve Leprohon's full headword verbatim (title-cased): `"Horus Merytawy"`, `"Two Ladies Userkhau"`. The king has no separate SMALLCAP name — the Horus/Nebty designation IS the display_name.

The corresponding name-row under these entries will be the ONLY name-type attested (e.g. entry 5 will have populated `horus_names` and empty everything else).

### Stub entries for destroyed / missing names

Dyn 14 has stub entries where the king's name is lost (e.g. `14. NAME LOST`, `15. /// -DJEFARE`, `16. /// WEBENRE II`, `49. ONE NAME LOST`). Handle per chunk-5 convention:
- If the headword is a pure descriptor phrase like `NAME LOST` / `ONE NAME LOST`, Title-Case the phrase for `display_name`, emit all empty name-lists.
- If the headword has partial name with `///` fragmentary-reading markers, preserve the `///` verbatim in `display_name`.

### Expected row counts

- **Dyn 13a:** 7 rows (entries 1–7, contiguous)
- **Dyn 14:** 38 rows (entries 1–19 contiguous + 22–34 + 43–45 + 49–51; Leprohon skips 20–21, 35–42, 46–48 in his own numbering)
- **Dyn 14a:** 6 rows (entries 1–6, contiguous)

**Total: 51 rows.** If you come in significantly under 47 or over 55, re-scan for missed entries.

### Numbering gaps

Dyn 14 has numbering gaps (20–21, 35–42, 46–48 missing). These are Leprohon's own decision — he numbered what he included and left holes where unnumbered. Emit ONLY the entries that exist in the chunk file. Do not invent rows for the gaps.

### Per-dynasty sparse titularies

Dyn 13a, 14, 14a kings are mostly fragmentary: most have only Throne + Birth. `Horus: none attested` → empty `horus_names: []` etc. Same as chunk 5.

## Output ordering

Sort by (`dynasty_label`, `sequence_in_chapter_section` ascending). merge.py re-sorts, but consistency aids diff readability.

## Final response

Give a one-line summary: row count per (sub-)dynasty, highest footnote seen, Ramesside-only count per section, stub-row confirmations. Under 100 words.
