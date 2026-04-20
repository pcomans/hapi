# Extraction prompt — Leprohon 2013 chunk 8 (Chapter VII New Kingdom — Dynasty 18)

Pass this to **three** independent Claude Code subagents in parallel. Each agent writes to `agent-{a,b,c}-dyn18.jsonl`.

---

You are extracting structured king data from Leprohon, Ronald J. (2013) *The Great Name: Ancient Egyptian Royal Titulary*, SBL WAW 33.

**Input:** `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/chunk-p114-p128-pypdf.md` — physical pp. 114–128 = printed 93–107. Contains all of **Dynasty 18** from Leprohon's chapter VII New Kingdom.

**Scope boundary:** physical p. 128 is SHARED with chunk 9. The page contains the END of Ay's entry (his Birth name spills over from p. 127) AND the OPENING of Dynasty 19 (Horemheb is Leprohon's Dyn 19 entry 1). **EXTRACT Ay's complete entry** including the Birth name from p. 128, then **STOP at the `Dynasty 19` header**. Do NOT emit any Dyn 19 / Horemheb rows from this chunk; those land in chunk 9.

**Output:** `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/agent-{a|b|c}-dyn18.jsonl`

## Prerequisite reading

Read prompts for chunks 1–7 first. The schema, hazard catalogue, and accumulated rules carry over. Chunk 8 introduces ONE new pattern (NK inline-stage convention for Akhenaten); everything else is preservation of established conventions.

## Chunk-8 specifics

### Dynasty label, chapter, IDs

All rows: `chapter: "New Kingdom"`, `dynasty_number: 18`, `dynasty_label: "Dynasty 18"`. IDs `leprohon-18.NN[stage_suffix?]` where the optional stage_suffix applies to multi-stage kings (see below).

### Multi-stage kings — TWO conventions

Leprohon uses two different typographic conventions for multi-stage king entries within Dyn 18:

**(A) MK-style separately-numbered stages** (same as chunk 4 Mentuhotep II 5a/5b/5c, Amenemhat I 1a/1b): the headword itself includes the stage suffix, e.g. `5a. THUTMOSE III (a)` and `5b. THUTMOSE III (b)`. Emit ONE row per stage suffix; `sequence_in_chapter_section: 5`, `stage_suffix: "a"` or `"b"`; `display_name` preserves the verbatim stage marker `"Thutmose III (a)"`.

**(B) NK inline-stage convention** (new in chunk 8 — Akhenaten): the headword is a SINGLE numbered entry like `10. AMENHOTEP IV/AKHENATEN`, but the body contains internal stage markers `a. Regnal Years 1 to 5` and `b. Regnal Years 5 to 17` (or similar period descriptors) BEFORE the name-rows of each stage's titulary. Emit ONE row per inline stage as if it were the (A) convention:
- Row 1: `leprohon_id: "leprohon-18.10a"`, `sequence_in_chapter_section: 10`, `stage_suffix: "a"`, `display_name: "Amenhotep IV (Regnal Years 1 to 5)"` (or whatever Leprohon prints for the early-reign king-name).
- Row 2: `leprohon_id: "leprohon-18.10b"`, `sequence_in_chapter_section: 10`, `stage_suffix: "b"`, `display_name: "Akhenaten (Regnal Years 5 to 17)"`.

Both rows carry their own full cross-name-type titulary (Horus, Two Ladies, etc.) — same row-per-stage rationale as MK convention. Add a canonical marker on the FIRST populated name-entry's `source_note` of stage (a) only:
```
"Leprohon prints this king as a single numbered entry with internal `a./b.` sub-section markers labelling successive titulary stages (Amenhotep IV's pre-name-change Regnal Years 1-5; Akhenaten's post-name-change Regnal Years 5-17). Each stage is emitted as its own row to preserve cross-name-type correlation, matching the MK separately-numbered-stages convention."
```

### Numbering note: Ahmose (II)

Leprohon's first Dyn 18 entry is `1. AHMOSE (II)` — the `(II)` is a Roman-numeral disambiguator distinguishing the Dyn 18 founder from Dyn 17 entry 26 `Senakhtenre Ahmose (I)` (which landed in chunk 7). Preserve verbatim in `display_name`: `"Ahmose (II)"`.

### Greek aliases for Dyn 18 kings

Several Dyn 18 kings have Greek aliases that Leprohon prints in the SMALLCAP headword parenthetical (`AMENHOTEP III (AMENOPHIS III)`-style if present). Preserve the primary Egyptian form in `display_name`; populate `alt_display_names` with the Greek form. Watch for: Amenophis variants on Amenhotep I/II/III/IV, Thutmosis on Thutmose I-IV, etc. — only emit when Leprohon actually prints the parenthesised Greek form.

### Per-king titulary density

Dyn 18 kings have the densest per-king titularies in the book — especially Thutmose III (entries 5a/5b have many Horus/Throne variants), Hatshepsut, Amenhotep III, and Akhenaten. Preserve every variant Leprohon lists. Use `variant_index: 1, 2, 3, ...` for multiple entries within a single name-type list, with `is_variant: false` for the first and `true` for subsequent.

### Numbered name-types (`Horus 1`, `Horus 2`, etc.)

Many Dyn 18 entries have explicit `Horus 1:`, `Horus 2:`, `Horus 3:` numbering, plus `Two Ladies 1/2/3`, `Golden Horus 1/2/3`, etc. Same convention as chunks 1-3: emit each as a separate entry in the same name-type list, with `variant_index` matching Leprohon's numbering.

### Provenance markers within name-rows

Some Dyn 18 entries (especially Amenhotep III) include provenance/location markers BEFORE name-rows, e.g. `Southern Colossus of Memnon, Western Thebes`, `Granite sphinx, Temple of Mut, Karnak`, `Luxor Temple`, `White faience lid, Karnak`. These are organisational markers grouping name-rows by where they're attested. Treat them as context only — do NOT emit them as their own rows; the name-rows that follow inherit them as `attested_in` provenance (append to the entry's `attested_in` list).

### Epithets-added blocks

Amenhotep III (and possibly others) have a list of "Epithets added to the Throne name:" / "Epithets added to the Birth name:" containing additional epithet phrases. Treat each epithet as a variant entry in the corresponding name-type list with `is_variant: true` and a source_note flagging the "epithet addition" status.

### Expected row count

- **Dyn 18:** Leprohon numbers entries 1–14, with two of those carrying multi-stage suffixes (one MK-style separately-numbered Na/Nb pair + one NK inline-stage entry that emits as two rows). Total expected ≈ 16 rows. If you produce fewer than 14 or more than 18, re-scan for missed stages.

(Note: Horemheb is placed in Dyn 19 per Leprohon's editorial scheme — he will appear in a later chunk, not this one.)

## Final response

Give a one-line summary: total row count, stage breakdown for Thutmose III and Akhenaten, highest footnote seen, alt_display_names confirmations for Greek aliases, any titulary-density edge cases. Under 100 words.
