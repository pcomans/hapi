# Extraction prompt — Leprohon 2013 chunk 13 (Chapter IX Late Period — Dyn 26 + 27 + 28 + 29 + 30 + 31)

Pass this to **three** independent Claude Code subagents in parallel. Each agent writes to `agent-{a,b,c}-late-period.jsonl`.

---

You are extracting structured king data from Leprohon, Ronald J. (2013) *The Great Name: Ancient Egyptian Royal Titulary*, SBL WAW 33.

**Input:** `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/chunk-p185-p195-pypdf.md` — physical pp. 185–195 = printed 164–174. Contains Leprohon's Chapter IX Late Period: **Dyn 26** (Saite renaissance), **Dyn 27** (1st Persian), **Dyn 28** (Amyrtaios), **Dyn 29** (Mendesian), **Dyn 30** (Sebennytic), **Dyn 31** (2nd Persian).

**Output:** `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/agent-{a|b|c}-late-period.jsonl`

## Prerequisite reading

Read prompts for chunks 1–12 first. Schema, hazard catalogue, and accumulated rules carry over. Chunk 13 introduces no new schema patterns.

## Chunk-13 specifics

### Dynasty labels, chapter, IDs

All rows: `chapter: "Late Period"`, IDs `leprohon-26.NN` through `leprohon-31.NN`, `dynasty_label: "Dynasty 26"` through `"Dynasty 31"`. Sequence resets at 1 in each dynasty section.

All rows: `stage_suffix: null`. No multi-stage kings expected in LP (verify).

### Persian kings (Dyn 27 and Dyn 31)

The Achaemenid Persian rulers (Cambyses, Darius I, Xerxes I, Artaxerxes I, Darius II, Artaxerxes II — Dyn 27; Artaxerxes III, Arses, Darius III — Dyn 31) appear as pharaohs in Leprohon because they took Egyptian titularies during their rule of Egypt. Their `display_name` should preserve Leprohon's Egyptian-form headword (e.g. `KAMBYTHET` for Cambyses, `INTARYUSHA` for Darius). Standard Greek / Persian forms (`Cambyses`, `Darius I`, `Xerxes I`) go into `alt_display_names` only if Leprohon prints them in the headword parenthetical. Don't force Greek aliases that aren't in Leprohon — those land via fix_rows post-pass with explicit attribution.

### Greek aliases for Saite kings (Dyn 26)

Several Saite kings have prominent Greek/Manetho aliases (Psamtik = Psammeticus / Psammetichus, Necho = Nekau, Apries = Wahibre / Hophra biblical, Amasis = Ahmose II / Ahmosis). Populate `alt_display_names` only if Leprohon prints the alias parenthetical. Standard fix_rows attribution applies for Phase-A enrichment.

### Dyn 30 kings

Nectanebo I, Teos (Tachos), Nectanebo II. Standard convention.

### Sparse titularies + numbered name-types

Same conventions as chunks 5-12.

### No Ramesside-only tags

All Late Period kings are contemporarily attested. Do NOT apply the Ramesside-only tag.

## Expected row counts

Conservative estimates (verify against chunk file):

- **Dyn 26 (Saite):** ~7-9 entries.
- **Dyn 27 (1st Persian):** ~5-6 entries.
- **Dyn 28:** 1 entry (Amyrtaios).
- **Dyn 29:** ~4-5 entries.
- **Dyn 30:** ~3 entries (Nectanebo I, Teos, Nectanebo II).
- **Dyn 31 (2nd Persian):** ~3 entries.

**Total: ~23-27 rows.** If you produce fewer than 20 or more than 30, re-scan.

## Output ordering

Sort by (`dynasty_label`, `sequence_in_chapter_section`). merge.py re-sorts.

## Final response

One-line summary: row count per dynasty, density notes for Saite kings (Psamtik I, Amasis often have substantial titularies), Greek aliases populated. Under 100 words.
