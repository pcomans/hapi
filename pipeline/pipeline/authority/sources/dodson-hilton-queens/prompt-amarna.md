# Extraction prompt for Dodson & Hilton Brief Lives — Amarna Interlude

Pass this to **three** independent Claude Code subagents in parallel. Each writes JSONL to a distinct filename; `merge.py` majority-votes across both chunk batches (Pre-Amarna `agent-{a,b,c}.jsonl` and Amarna `agent-{a,b,c}-amarna.jsonl`). The prompt is verbatim; the only per-agent substitution is the output-file suffix (`-a`, `-b`, `-c`).

---

You are extracting structured royal-family-member rows from OCR'd Brief Lives entries of Dodson & Hilton (2004) *The Complete Royal Families of Ancient Egypt*, 1st ed. hardback.

**Input**: one OCR chunk file at `<repo_root>/pipeline/pipeline/authority/sources/dodson-hilton-queens/raw/chunk-p142-p145.md`.

**Output**: write your JSONL to `<agent_dir>/agent-{a|b|c}-amarna.jsonl`, where `<agent_dir>` defaults to `<source_dir>/raw/` (gitignored via `raw/agent-*.jsonl`). One JSON object per line, no preamble, no code fences.

**Task**: every Brief Lives entry in the chunk gets one row. Entries begin with a bold name (sometimes bold-italic for female, bold-capital for king) followed by role codes in parentheses, then a 1–3 sentence prose paragraph.

## Schema

```json
{
  "dh_id": "Nefertiti",
  "name": "Nefertiti",
  "alt_names": ["Neferneferuaten-Nefertiti"],
  "roles": ["KGW", "L2L"],
  "sex": "female",
  "spouse_names": ["Akhenaten"],
  "father_name": null,
  "mother_name": null,
  "children_names": [],
  "dynasty": 18,
  "sub_period": "The Amarna Interlude",
  "unplaced": false,
  "notes": "Wife of Akhenaten; known from year 5 onwards as Neferneferuaten-Nefertiti. …",
  "source_citation": {"pdf_pages": "142-145", "edition": "Thames & Hudson 2004 hardback"}
}
```

## Field semantics

- **`dh_id`** — D&H's name-with-disambiguator exactly as printed: `Amenhotep E`, `Ankhesenpaaten`, `Iset C`, `Mutnodjmet A`, `Mutnodjmet Q`, `Tiye A`, `Ay A`, `Ay B`, `[...]18A–H`, `–18P`. Lacuna-prefixed names keep the square brackets and ellipsis. The short-dash lacuna form (`–18P`, `–18Q`) keeps the en-dash. `Q` suffixes are IDs, not throwaway markers. **`dh_id` is the primary key** — do not emit two rows with the same `dh_id`; emit the first and flag the duplicate in `notes`.
- **`name`** — same string as `dh_id` for this source. Separate field for cross-source schema parity.
- **`alt_names`** — list of variant name strings D&H record inline (e.g. `Ankhesenpaaten` is also known as `Ankhesenamun` per the prose — include both in `alt_names`; `Nefertiti` also known as `Neferneferuaten-Nefertiti`; `Tutankhuaten` also known as `TUTANKHATEN/AMUN` — split into `["TUTANKHATEN", "AMUN"]` if the prose renders them with a slash). Empty list when absent. Do NOT include the disambiguator letter in alt_names; it's already in `dh_id`.
- **`roles`** — list of role-code strings from the parenthetical after the name. Split on `;` with trailing whitespace trimmed. Known codes in this chunk include `K` (King, marked by BOLD CAPITALS entry rendering), `KSon`, `KSonN` (King's Son, Nurse or Natural?), `KD`, `KDB` (King's Daughter of his Body), `KGW`, `KW`, `GW`, `GBW` (Greatly Beloved Wife), `KSis`, `KM`, `L2L`, `M2L`, `MULE` (codes from D&H's legend — treat as literal strings), `KGD` (King's Great Daughter?), `Viz?`, `MoH` (Master of the Horse? or similar — literal), `GF` (Godfather? literal), `Genmo` (General?), `Exec`, `Gen`, `ChA`, `2PA`, `1PMut`, `Sister of KGW`, `Steward of Queen Tiye A/Tey`, `HPM`, `SPP`, `OPULE`, `EKSon`, `King of Mitanni`, `KM of KGW`. Preserve code strings verbatim even if you've never seen them before — D&H sometimes spells a role out instead of using an abbreviation. Do NOT attempt to expand codes to long-form — Phase A owns the code glossary.
- **`sex`** — `"male"` or `"female"`:
  - **male**: any role in `{K, KSon, KSonN, EKSon, HPM, SPP, OPULE, Gen, Genmo, Exec, "King of Mitanni", "2PA", "1PMut", "Steward of Queen Tiye A/Tey", "Viz?", "GF", "MoH"}`; BOLD upright entry rendering; the prose uses `"He"` / `"His"`.
  - **female**: any role beginning with `K` for a female-pattern code (`KD`, `KDB`, `KGD`, `KGW`, `KW`, `KM`, `KSis`) or in `{GW, GBW, L2L, M2L, MULE, ChA, "Sister of KGW"}`; BOLD ITALIC entry rendering; the prose uses `"She"` / `"Her"`.
  - Ambiguous short codes (`K`, `2PA`, `MoH`, `GF`) resolve to **male** when D&H renders the entry in BOLD upright and the prose uses masculine pronouns (typical for father-in-law / vizier / general codes), and **female** when BOLD ITALIC. Fall back to prose pronouns as the final tiebreaker.
  - The lacuna entries `[...]18A–H`, `[...]18K–N`, `–18P`, `–18Q` are explicitly typed as female daughters in the prose → `"female"`; `[...]18J` is a son → `"male"`.
- **`spouse_names`** — list of spouse names named in the prose. Phrases `"Wife of X"`, `"Husband of Y"` → `["X"]`, `["Y"]`. If the prose says `"possibly identical with Mutnodjmet A"`, that is NOT a spouse. If D&H says `"wife of Tutankhamun, later known as Ankhesenamun"`, emit `spouse_names: ["Tutankhamun"]` (and put the later-name in `alt_names`). Emit hedges verbatim (`"Ay (brief marriage)"`). Empty list when no spouse is named.
- **`father_name`** / **`mother_name`** — single strings from `"son of X"`, `"daughter of Y"`, `"mother Z"` constructions. Include hedges verbatim (`"Yuya (possibly)"`, `"Ay (probable)"`). `null` when D&H don't state the parent.
- **`children_names`** — list of children named in the prose. `"mother of Akhenaten"` → `["Akhenaten"]`. Multiple named children → list them all.
- **`dynasty`** — integer `18`. Entire chunk is chapter 3 / The Amarna Interlude / late Dyn 18.
- **`sub_period`** — string `"The Amarna Interlude"` for every row in this chunk.
- **`unplaced`** — The Amarna Brief Lives section has no explicit `Unplaced` sub-heading. The lacuna group at the end (`[...]18A–H`, `[...]18J`, `[...]18K–N`, `–18P`, `–18Q`) are tentative-identity entries that D&H place at the foot of the alphabetical run but do NOT label "Unplaced" in this chunk. Emit `unplaced: false` for every row unless you see an explicit `Unplaced` heading in the OCR.
- **`notes`** — the full prose paragraph verbatim, single-line-joined. Preserve museum catalogue numbers (`CM JE60670`, `KV55`, `TT255`, `TA2`), scholarly-hedge words (`probably`, `possibly`, `perhaps`), Mitanni names, and Berlin/Brooklyn/Louvre attributions as they appear. Trim leading/trailing whitespace. Do NOT summarise; do NOT editorialise.
- **`source_citation`** — `{"pdf_pages": "142-145", "edition": "Thames & Hudson 2004 hardback"}` on every row.

## Parsing hazards

- **`Ay A` vs `Ay B`**: Ay A = father of Nefertiti, later king. Ay B = nephew of Ay A, 2PA. Do not conflate.
- **`Mutnodjmet A` vs `Mutnodjmet Q`**: D&H explicitly discusses whether they are the same person. Emit both as separate rows per D&H's listing; put the hedged-identity note in both entries' `notes`.
- **`Nakhtmin A` vs `Nakhtmin B`**: A = father of Ay B (named on the statue of his son). B = probable son of Ay, Genmo/KSon/Exec. Distinct individuals.
- **`Ankhesenpaaten` later = Ankhesenamun**: same person, name change after husband Tutankhaten became Tutankhamun. Put `Ankhesenamun` in `alt_names`, keep `dh_id` as `Ankhesenpaaten` (D&H's primary entry name).
- **Kings appearing as Brief Lives entries**: `Amenhotep E` (= later **AMENHOTEP IV/AKHENATEN**), `Ay A` (later king Ay), `Horemheb` (later king), `Tutankhuaten` (= later **TUTANKHATEN/AMUN**). Emit each as a Brief Lives row with `sex: "male"`. Cross-reference to the later regnal name goes in `alt_names`.
- **Mitanni kings**: `Shuttarna II`, `Tushratta` are Mitanni, not Egyptian. D&H includes them for family-tree completeness (fathers-in-law of Amenhotep III and Akhenaten). Emit as rows with `dynasty: 18`, `sex: "male"`, role `["King of Mitanni"]`.
- **Still-born children `–18P` and `–18Q`**: both are daughters of Tutankhamun and Ankhesenamun. Distinct rows — D&H list them separately.
- **Lacuna group entries (`[...]18A–H`, etc.)**: each represents a *group* of daughters/sons from one tomb scene. Emit one row per D&H entry (5 rows total for the lacuna block: `[...]18A–H`, `[...]18J`, `[...]18K–N`, `–18P`, `–18Q`). Put the group scope in `notes`.
- **`Tey (KGW; KGW)`**: D&H writes the code `KGW` twice. Deduplicate to `["KGW"]`; the repetition in the book is a typo, not a distinct role assignment.
- **`Meryetaten-tasherit` and `Ankhesenpaaten-tasherit`**: the `-tasherit` suffix is part of the name (D&H convention for "the younger"). Keep in `dh_id`.
- **`Neferneferuaten-tasherit` and `Neferneferuaten`**: two different individuals. `Neferneferuaten-tasherit` is the fourth daughter of Akhenaten and Nefertiti. `Neferneferuaten` as a regnal name is cross-referenced in `Meryetaten`'s entry (Meryetaten became female king Neferneferuaten). No separate Brief Lives row for the regnal `Neferneferuaten` appears in this chunk.

## Sort order

Alphabetical by `dh_id`, case-insensitive. Lacuna-prefixed names (`[...]`, `–`) sort after all letter-prefixed names.

## Expected row count

~41 rows. If your row count is below 35 or above 50, re-read the chunk and count entries per page before writing. Per-page estimate from D&H's 3-column layout: p. 154 ≈ 12 entries; p. 155 ≈ 6 entries; p. 156 ≈ 9 entries; p. 157 ≈ 14 entries (incl. 5 lacuna entries).

## Output

Write the JSONL. In your final response, report: row count + anything anomalous (e.g. an entry that didn't fit the template, a role code you couldn't classify). Under 80 words.
