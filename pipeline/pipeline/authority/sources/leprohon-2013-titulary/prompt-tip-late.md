# Extraction prompt — Leprohon 2013 chunk 12 (Chapter VIII TIP — Dyn 23 + 23a + 24 + 25)

Pass this to **three** independent Claude Code subagents in parallel. Each agent writes to `agent-{a,b,c}-tip-late.jsonl`.

---

You are extracting structured king data from Leprohon, Ronald J. (2013) *The Great Name: Ancient Egyptian Royal Titulary*, SBL WAW 33.

**Input:** `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/chunk-p174-p184-pypdf.md` — physical pp. 174–184 = printed 153–163. Contains Leprohon's Chapter VIII Third Intermediate Period (late section): **Dyn 23** (Tanite/Theban Dyn 23 split), **Dyn 23a** (additional Dyn 23 collateral), **Dyn 24** (Saite — Tefnakhte + Bakenrenef), **Dyn 25** (Nubian/Kushite — Piye, Shabaka, Shabataka, Taharqa, Tantamani).

**Output:** `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/agent-{a|b|c}-tip-late.jsonl`

## Prerequisite reading

Read prompts for chunks 1–11 first. Schema, hazard catalogue, and accumulated rules carry over. Chunk 12 introduces no new schema patterns.

## Chunk-12 specifics

### Dynasty labels, chapter, IDs

All rows: `chapter: "Third Intermediate Period"`. IDs and dynasty_label per sub-section:
- Dyn 23: `leprohon-23.NN`, `dynasty_number: 23`, `dynasty_label: "Dynasty 23"`.
- Dyn 23a: `leprohon-23a.NN`, `dynasty_number: 23`, `dynasty_label: "Dynasty 23a"`.
- Dyn 24: `leprohon-24.NN`, `dynasty_number: 24`, `dynasty_label: "Dynasty 24"`.
- Dyn 25: `leprohon-25.NN`, `dynasty_number: 25`, `dynasty_label: "Dynasty 25"`.

All rows: `stage_suffix: null`. Each sub-dynasty resets sequence at 1.

### No Ramesside-only tags

All TIP kings are contemporarily attested per Leprohon's prose preamble. Do NOT apply the Ramesside-only tag.

### Dyn 25 (Nubian) alt_display_names

Same general convention as prior chunks: populate `alt_display_names` only with forms Leprohon explicitly prints in the SMALLCAP headword (parenthesised Greek alias OR slash-separated homonym). Do NOT add scholarly / museum-standard aliases not printed by Leprohon — those land via fix_rows post-pass with explicit egyptologist-reviewer attribution.

### Sheshonq spelling alias for Dyn 23

If Dyn 23 contains any Sheshonq entries (Sheshonq VI / "Sheshonq VII" depending on numbering), apply the same `Shoshenq` alias convention as chunk 11.

### Sparse titularies + numbered name-types

Same conventions as chunks 5-11.

### Scope boundary at p. 184

Chunk 12 ends at physical p. 184. The next chapter (IX Late Period) starts at physical p. 185. STOP at the `Late Period` chapter header if visible at the bottom of p. 184.

## Expected row counts

Conservative estimates per Leprohon's actual numbering (verify against chunk file):

- **Dyn 23:** ~9 entries.
- **Dyn 23a:** ~5 entries.
- **Dyn 24:** ~2 entries (Tefnakhte, Bakenrenef).
- **Dyn 25:** ~7 entries (Kashta, Piye, Shabaka, Shabataka, Taharqa, Tantamani, plus possibly others).

**Total: ~23 rows.** If you produce fewer than 18 or more than 28, re-scan.

## Output ordering

Sort by (`dynasty_label`, `sequence_in_chapter_section`). merge.py re-sorts.

## Final response

One-line summary: row count per (sub-)dynasty, Greek aliases populated for Dyn 25, any Shoshenq aliases for Dyn 23, sparse-titulary observations. Under 100 words.
