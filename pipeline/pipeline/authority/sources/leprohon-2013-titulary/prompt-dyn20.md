# Extraction prompt — Leprohon 2013 chunk 10 (Chapter VII NK Dynasty 20)

Pass this to **three** independent Claude Code subagents in parallel. Each agent writes to `agent-{a,b,c}-dyn20.jsonl`.

---

You are extracting structured king data from Leprohon, Ronald J. (2013) *The Great Name: Ancient Egyptian Royal Titulary*, SBL WAW 33.

**Input:** `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/chunk-p146-p156-pypdf.md` — physical pp. 146–156 = printed 125–135. Contains Leprohon's Chapter VII NK **Dynasty 20** (Sethnakht + Ramesses III through Ramesses XI).

**Scope boundary at p. 146:** physical p. 146 contains the END of Tausret (Dyn 19 entry 8 — already extracted in chunk 9). **START at the `Dynasty 20 (1185-1070 B.C.E.)` header.** Do NOT re-emit Tausret.

**Output:** `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/agent-{a|b|c}-dyn20.jsonl`

## Prerequisite reading

Read prompts for chunks 1–9 first. Schema, hazard catalogue, and accumulated rules carry over. Chunk 10 introduces no new schema patterns.

## Chunk-10 specifics

### Dynasty label, chapter, IDs

All rows: `chapter: "New Kingdom"`, `dynasty_number: 20`, `dynasty_label: "Dynasty 20"`. IDs `leprohon-20.NN`. Sequence resets to 1 (Sethnakht).

### Per-king titulary density

Ramesses III (Dyn 20 entry 2) is comparable to Ramesses II in density — long reign, many monuments, many name variants per name-type. Ramesses IV-XI are progressively shorter reigns with sparser titularies. Apply the per-variant emission convention (`variant_index: 1, 2, 3, ...`) per the chunks 8-9 lesson.

### Epithets-added blocks

Ramesside-tradition epithets-added blocks are common throughout Dyn 20. Treat each epithet as a variant entry in the corresponding name-type list with `is_variant: true` and a source_note flagging the epithet-addition status. Apply lowercase MdC normalization to transliteration fields (the upstream transcribe_chunk.py regex doesn't normalize unlabeled epithet rows; the fix_rows.py post-pass safety net catches them).

### Numbered name-types

Dyn 20 entries use `Horus 1`, `Horus 2`, `Two Ladies 1`, `Two Ladies 2`, `Golden Horus 1`, `Golden Horus 2`, etc. Same convention as chunks 1-9.

### Sparse titularies

Some later Dyn 20 kings (Ramesses VIII, X) have sparser titularies. `Horus: none attested` → empty `horus_names: []`. Same as chunks 5-9.

### No Ramesside-only tags expected

Per Leprohon's prose preamble for Dyn 20, all 10 kings are contemporarily attested (this is THE Ramesside line). Do NOT apply the Ramesside-only tag to any Dyn 20 row.

### Greek aliases

Possible Greek aliases (Sethnakht → ?, Ramses → Ramesses) printed in headword parentheticals. Populate `alt_display_names` only if Leprohon prints them; otherwise leave empty.

## Expected row count

- **Dyn 20:** 10 numbered entries (Sethnakht, Ramesses III, Ramesses IV, Ramesses V, Ramesses VI, Ramesses VII, Ramesses VIII, Ramesses IX, Ramesses X, Ramesses XI). Verify against the chunk file.

**Total: 10 rows.** If you produce fewer than 8 or more than 12, re-scan.

## Output ordering

Sort by `sequence_in_chapter_section`. merge.py re-sorts.

## Final response

One-line summary: total row count, density notes for Ramesses III, any Greek aliases or slashed-homonyms, epithet-block extraction status. Under 100 words.
