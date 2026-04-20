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

### Non-standard headwords with name-type labels inline

Some entries have headwords of the form `N. NAME_TYPE_LABEL NAME` where
the name-type label is fused into the identity string because Leprohon
only has that one name-type attested for this king (e.g. a king known
ONLY by his Horus name, ONLY by his Nebty name, ONLY by a Golden Horus
name — no standard SMALLCAP personal name). Rules:

- `display_name` preserves Leprohon's full headword verbatim (Title-Cased): `"Horus <Name>"`, `"Two Ladies <Name>"`, `"Golden Horus <Name>"`.
- `alt_display_names`: include the bare name without the name-type prefix (e.g. if display_name is `"Horus <Name>"`, add `"<Name>"` to alt_display_names) so downstream Phase-A museum-record matching has a matchable handle.
- Only the corresponding name-type list is populated; all other name-lists are empty for that row.

### Stub entries for destroyed / missing names

Two flavours of stub entries appear in this chunk, both preserving
Leprohon's sequence-numbering for entries whose name is unreadable in
his sources:

**Single-slot stub** — one numbered entry with a pure descriptor phrase
as headword (e.g. `N. NAME LOST`). Handle per chunk-5 convention:
Title-Case the phrase for `display_name`, emit all empty name-lists,
`sequence_in_chapter_section` is the single slot number.

**Multi-slot stub** — one entry header spans a range of sequence
numbers (e.g. `N1–N2. <COUNT_WORD> NAMES LOST` like `THREE NAMES LOST`
covering 3 slots, `FIVE NAMES LOST` covering 5 slots). Emit ONE row
per stub header (NOT one per covered slot). Set
`sequence_in_chapter_section` to the FIRST slot in the range;
`display_name` Title-Cases the descriptor phrase (`"Three Names Lost"`,
`"Five Names Lost"`); empty name-lists.

Headwords with partial name + `///` fragmentary-reading markers are
NOT stubs; they ARE real king entries with a partially-reconstructed
name — preserve the `///` verbatim in `display_name` and populate
whatever name-type rows Leprohon gives.

### Expected row counts

- **Dyn 13a:** 7 rows (entries 1–7, contiguous).
- **Dyn 14:** 40 rows — entries 1–19 (19 rows), 22–34 (13 rows), 43–45 (3 rows), multi-slot stub at slots 46–48 (1 row), 49–51 (3 rows), multi-slot stub at slots 52–56 (1 row). Leprohon's own numbering skips 20–21 and 35–42.
- **Dyn 14a:** 6 rows (entries 1–6, contiguous).

**Total: 53 rows.** If you come in significantly under 49 or over 57, re-scan for missed entries — in particular, DO NOT skip the multi-slot stub rows.

### Numbering gaps

Dyn 14 has numbering gaps (20–21, 35–42, 46–48 missing). These are Leprohon's own decision — he numbered what he included and left holes where unnumbered. Emit ONLY the entries that exist in the chunk file. Do not invent rows for the gaps.

### Per-dynasty sparse titularies

Dyn 13a, 14, 14a kings are mostly fragmentary: most have only Throne + Birth. `Horus: none attested` → empty `horus_names: []` etc. Same as chunk 5.

### Name-rows with no anglicised gloss / no translation

Some entries (particularly in Dyn 14a) give ONLY the transliteration,
with no parenthetical anglicised gloss and no English translation (e.g.
a `Birth:` row of the form `Birth: transliteration` on its own, no
`(gloss), translation` continuation). Emit `anglicised: null` and
`translation: null` for those rows — do NOT synthesize an anglicised
form from the transliteration, and do NOT copy the anglicised form into
the translation field. Constitutional rule 2 (no defensive programming):
an absent field is `null`, not a fabricated guess.

## Output ordering

Sort by (`dynasty_label`, `sequence_in_chapter_section` ascending). merge.py re-sorts, but consistency aids diff readability.

## Final response

Give a one-line summary: row count per (sub-)dynasty, highest footnote seen, Ramesside-only count per section, stub-row confirmations. Under 100 words.
