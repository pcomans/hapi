# Extraction prompt — Leprohon 2013 chunk 11 (Chapter VIII TIP — Dyn 21 + 21a + 22 + 22a)

Pass this to **three** independent Claude Code subagents in parallel. Each agent writes to `agent-{a,b,c}-tip-early.jsonl`.

---

You are extracting structured king data from Leprohon, Ronald J. (2013) *The Great Name: Ancient Egyptian Royal Titulary*, SBL WAW 33.

**Input:** `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/chunk-p157-p173-pypdf.md` — physical pp. 157–173 = printed 136–152. Contains Leprohon's Chapter VIII Third Intermediate Period: **Dyn 21** (Tanite kings), **Dyn 21a** (Theban High Priests of Amun parallel line), **Dyn 22** (Bubastite Sheshonqs main line), **Dyn 22a** (collateral / second-tier).

**Output:** `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/agent-{a|b|c}-tip-early.jsonl`

## Prerequisite reading

Read prompts for chunks 1–10 first. Schema, hazard catalogue, and accumulated rules carry over. Chunk 11 introduces no new schema patterns.

## Chunk-11 specifics

### Dynasty labels, chapter, IDs

All rows: `chapter: "Third Intermediate Period"`. IDs and dynasty_label per sub-section:
- Dyn 21: `leprohon-21.NN`, `dynasty_number: 21`, `dynasty_label: "Dynasty 21"`.
- Dyn 21a (Theban HPA parallel line): `leprohon-21a.NN`, `dynasty_number: 21`, `dynasty_label: "Dynasty 21a"`.
- Dyn 22: `leprohon-22.NN`, `dynasty_number: 22`, `dynasty_label: "Dynasty 22"`.
- Dyn 22a: `leprohon-22a.NN`, `dynasty_number: 22`, `dynasty_label: "Dynasty 22a"`.

All rows: `stage_suffix: null`. Each sub-dynasty resets sequence at 1.

### Theban HPA parallel line (Dyn 21a)

The Theban High Priests of Amun who held quasi-royal status during the Tanite Dyn 21 period. Leprohon includes them as Dyn 21a per the established TIPE-scholar convention. Their titularies are typically simpler than full pharaohs — often just `Throne` + `Birth`. Treat as standard king entries; do not add any "HPA" qualifier to display_name unless Leprohon's headword does.

### Sheshonq density (Dyn 22)

Dyn 22 is the long Bubastite Sheshonq/Osorkon/Takeloth line — 28 expected entries with Roman-numeral disambiguators (Sheshonq I, II, III, IV, V, VI...; Osorkon I, II, III, IV; Takeloth I, II, III; Pami; etc.). Some entries may have multi-stage suffixes (Na/Nb) — apply chunk-4 MK-style if Leprohon's headword carries the suffix in the SMALLCAP form.

### Possible Greek aliases

Sheshonq / Shoshenq is variously printed by Leprohon. Watch for parenthesised Greek forms like `OSORKON (OSORTHON)` or similar; populate `alt_display_names` if present. Do NOT add Greek aliases not printed by Leprohon.

### Slashed homonyms

Some TIP kings have slashed-homonym headwords (e.g. `SHESHONQ I/SHOSHENQ I`-style). Apply the chunks 1-3 slash-homonym convention.

### Sparse titularies

TIP kings often have sparse titularies. `Horus: none attested` → empty `horus_names: []`. Same as chunks 5-10.

### No Ramesside-only tags

All TIP kings are contemporarily attested (this is post-Ramesside). Do NOT apply the Ramesside-only headword tag.

## Expected row counts

Per the post-Broekman renumbering Leprohon adopts (verified post-extraction):

- **Dyn 21:** 8 entries (Herihor, Smendes/Nesbanebdjed, Amenemnesut, Psusennes I, Amenemope, Osorkon the Elder, Siamun, Psusennes II).
- **Dyn 21a:** 3 entries (Theban HPA line: Pinodjem I, Menkheperre, Psusennes III).
- **Dyn 22:** 13 entries (Sheshonq I/IIa/IIb/IIc/III/IV/V, Osorkon I/II/IV, Takelot I/II, Pamiu — Broekman renumbering halves the older count).
- **Dyn 22a:** 1 entry (Harsiese).

**Total: 25 rows.** If you produce fewer than 23 or more than 27, re-scan for missed entries.

## Output ordering

Sort by (`dynasty_label`, `sequence_in_chapter_section`). merge.py re-sorts.

## Final response

One-line summary: row count per (sub-)dynasty, density notes for Dyn 22 Sheshonq line, any Greek aliases, slashed homonyms, multi-stage entries. Under 100 words.
