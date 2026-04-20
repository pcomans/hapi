# Extraction prompt — Leprohon 2013 chunk 9 (Chapter VII NK Dynasty 19 + Horemheb scope-recovery)

Pass this to **three** independent Claude Code subagents in parallel. Each agent writes to `agent-{a,b,c}-dyn19.jsonl`.

---

You are extracting structured king data from Leprohon, Ronald J. (2013) *The Great Name: Ancient Egyptian Royal Titulary*, SBL WAW 33.

**Input:** `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/chunk-p128-p146-pypdf.md` — physical pp. 128–146 = printed 107–125. Contains Leprohon's Chapter VII NK **Dynasty 19** (the Ramesside founders + early Ramessides), including Tausret on physical p. 146.

**Scope boundary at p. 146:** physical p. 146 contains the END of Tausret (Dyn 19 entry 8) at the top, then the `Dynasty 20 (1185-1070 B.C.E.)` header mid-page. **EXTRACT Tausret's complete entry from p. 146** and **STOP at the `Dynasty 20` header**. Do NOT emit any Dyn 20 / Sethnakht rows from this chunk; those land in chunk 10.

**Output:** `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/agent-{a|b|c}-dyn19.jsonl`

## Prerequisite reading

Read prompts for chunks 1–8 first. Schema, hazard catalogue, and accumulated rules carry over. Chunk 9 introduces no new schema patterns.

## Scope-recovery: Horemheb

Physical p. 128 contains BOTH the tail of Dyn 18 (Horemheb is Leprohon's Dyn 18 entry 15, immediately following Ay) AND the opening of Dyn 19. Chunk 8 (PR #91) erroneously stopped at "Ay" without extracting Horemheb — the chunk-8 prompt assumed Dyn 18 had 14 entries when it actually has 15.

**Recovery rule:** extract Horemheb's complete entry as the FIRST row in your output, with:
- `leprohon_id: "leprohon-18.15"` (Dyn 18 entry 15, NOT Dyn 19)
- `dynasty_number: 18`
- `dynasty_label: "Dynasty 18"`
- `chapter: "New Kingdom"`
- `sequence_in_chapter_section: 15`
- `stage_suffix: null`
- Complete titulary as Leprohon prints it (Horus, Two Ladies, Golden Horus, Throne, Birth, plus epithets-added blocks).

This row recovers the chunk-8 scope miss (cf. chunk-2's Seneferka recovery from chunk 1 — same pattern).

## Chunk-9 specifics

### Dynasty 19 entries

After the Horemheb recovery row, START extracting Dyn 19 from the `Dynasty 19 (1293–1185 B.C.E.)` header. All Dyn 19 rows: `chapter: "New Kingdom"`, `dynasty_number: 19`, `dynasty_label: "Dynasty 19"`. IDs `leprohon-19.NN`. Sequence resets to 1 (Ramesses I).

### Slashed-headword homonyms in Dyn 19

Watch for slash-homonyms in the SMALLCAP headwords. For example, the entry that appears as `MERENPTAH/MERNEPTAH` should follow the chunks 1-3 slash-homonym convention: `display_name` preserves the slash; `alt_display_names` lists each form individually (split on `/`, strip whitespace).

### Ramesses II density

Ramesses II is one of the densest entries in the book (long reign, many monuments). Expect a substantial number of name-variants per name-type. Same per-variant emission convention as Thutmose III in chunk 8.

### Per-stage / Epithets-added blocks

Several Dyn 19 kings (especially Ramesses II, possibly Sety I) have `Epithets added to the Throne name:` / `Epithets added to the Birth name:` blocks (same convention as chunk 8). Emit each epithet as a separate variant entry in the corresponding name-type list with `is_variant: true` and a source_note flagging the epithet-addition status. Apply lowercase MdC normalization to transliteration fields (the upstream transcribe_chunk.py regex doesn't normalize unlabeled epithet rows — fix_rows.py post-pass catches them).

### Sety I / Sety II / Ramesses II Greek aliases

Possible Greek aliases (Sethos, Ramses → Ramesses, etc.) printed in headword parentheticals. Populate `alt_display_names` if Leprohon prints them; otherwise leave empty.

## Expected row count

- **Horemheb scope-recovery:** 1 row (Dyn 18.15).
- **Dyn 19:** Leprohon numbers entries 1–8 in this section (verify against the chunk file). The 8 numbered entries include the founder, the early Ramessides, and the queen-regent who closes the dynasty.

**Total: ≈ 9 rows** (1 Horemheb scope-recovery + 8 Dyn 19). If you produce fewer than 8 or more than 11, re-scan for missed entries or stages.

## Output ordering

Sort by (`dynasty_number`, `sequence_in_chapter_section`). merge.py re-sorts. Horemheb (Dyn 18.15) comes BEFORE all Dyn 19 entries.

## Final response

One-line summary: total row count, Horemheb scope-recovery confirmation, Dyn 19 king count + names, density notes for Ramesses II, any Greek aliases, slashed-homonym findings. Under 100 words.
