# Extraction prompt for Dodson & Hilton Brief Lives

Pass this to **three** independent Claude Code subagents in parallel. Each writes JSONL to a distinct filename; `merge.py` majority-votes. The prompt is verbatim; the only per-agent substitution is the output-file suffix (`-a`, `-b`, `-c`).

---

You are extracting structured royal-family-member rows from OCR'd Brief Lives entries of Dodson & Hilton (2004) *The Complete Royal Families of Ancient Egypt*, 1st ed. hardback.

**Input**: one OCR chunk file at `<repo_root>/pipeline/pipeline/authority/sources/dodson-hilton-queens/raw/chunk-p126-p130.md`.

**Output**: write your JSONL to `<agent_dir>/agent-{a|b|c}.jsonl`, where `<agent_dir>` defaults to `<source_dir>/raw/` (gitignored via `raw/agent-*.jsonl`). One JSON object per line, no preamble, no code fences.

**Task**: every Brief Lives entry in the chunk gets one row. Entries begin with a bold name (sometimes bold-italic for female, bold-capital for king) followed by role codes in parentheses, then a 1–3 sentence prose paragraph.

## Schema

```json
{
  "dh_id": "Mutemwia",
  "name": "Mutemwia",
  "alt_names": [],
  "roles": ["KGW", "KM"],
  "sex": "female",
  "spouse_names": ["Thutmose IV"],
  "father_name": null,
  "mother_name": null,
  "children_names": ["Amenhotep III"],
  "dynasty": 18,
  "sub_period": "The Power and the Glory",
  "unplaced": false,
  "notes": "Wife of Thutmose IV and mother of Amenhotep III; shown in the 'divine birth' scenes of her son in Luxor temple. A statue of her probably came from his mortuary temple, with a figure of her in a boat found adjacent to the granite sanctuary of the Karnak temple (British Museum); she is also represented with her son on the Colossi of Memnon and in the tomb of Heqareshu (TT226, now in the Luxor Museum).",
  "source_citation": {"pdf_pages": "126-130", "edition": "Thames & Hudson 2004 hardback"}
}
```

## Field semantics

- **`dh_id`** — D&H's name-with-disambiguator exactly as printed: `Ahmes B`, `Mutnefert A`, `Hatshepsut D`, `[...]pentepkau`. `Q` suffixes (for "Unplaced" entries) are IDs, not throwaway markers. Names without a disambiguator letter (`Mutemwia`, `Huy`, `Ipu B` wait — B *is* a disambiguator — `Tintamun`, `Menhet`, `Merti`, `Menwi`, `Webensenu`, `Siamun B`, `Wadjmose`) stay as-is. **`dh_id` is the primary key** — do not emit two rows with the same `dh_id`; emit the first and flag the duplicate in `notes`.
- **`name`** — same string as `dh_id` for this source. Separate field for cross-source schema parity.
- **`alt_names`** — list of variant name strings D&H record inline, usually hyphenated compounds: `Hatshepsut-Khnemetamun`, `Meryetre-Hatshepsut`, `Neferneferuaten-Nefertiti`. Empty list when absent. Do NOT include the disambiguator letter in alt_names; it's already in `dh_id`.
- **`roles`** — list of role-code strings from the parenthetical after the name. Split on `;` with trailing whitespace trimmed. Example: `"Ahmes B (KM; KGW; KSis)"` → `["KM", "KGW", "KSis"]`. Known codes in this chunk include `K` (King, marked by BOLD CAPITALS entry rendering), `KM`, `KW`, `KGW`, `GW`, `KSis`, `KD`, `KSon`, `EKSon`, `HPH`, `Ador`, `Nurse`, `Exec`, `SPP`, `Genmo`, `UWC`, `Overseer of Cattle`, `Captain of the Troops`, `Mayor of Thinis`. Preserve code strings verbatim even if you've never seen them before. Do NOT attempt to expand codes to long-form — Phase A owns the code glossary.
- **`sex`** — `"male"` or `"female"`:
  - **male**: any role in `{K, KSon, EKSon, HPH, Genmo, SPP, Exec, "Overseer of Cattle", "Captain of the Troops", "Mayor of Thinis"}`.
  - **female**: any role in `{KM, KW, KGW, GW, KSis, KD, "Nurse", Ador, UWC}`.
  - If a row has only ambiguous / unknown codes, infer from D&H's typography: BOLD italic = female; BOLD upright = male (king); plain bold + pronouns in prose (`"She"` / `"Her"` vs `"He"` / `"His"`) disambiguate the rest.
- **`spouse_names`** — list of spouse names named in the prose. Phrases `"Wife of X"`, `"Husband of Y"`, `"wife of Thutmose IV"` → `["Thutmose IV"]`. If the prose says `"probably a wife of"` or `"possibly a daughter of"`, preserve the hedge verbatim (`["Akhenaten (probable)"]`). If D&H mentions no spouse, emit `[]`.
- **`father_name`** / **`mother_name`** — single strings from `"son of X"`, `"daughter of Y"`, `"mother Z"`, `"her father X"` constructions. Include hedges verbatim: `"Ay (probable)"`, `"a king of the mid-18th Dynasty"`, `"unknown"` (actual word if D&H writes it that way). `null` when D&H don't state the parent.
- **`children_names`** — list of children named in the prose: `"mother of Amenhotep III"` → `["Amenhotep III"]`; `"Her children include A, B and C"` → `["A", "B", "C"]`. Do NOT guess children from cross-references ("Iset B is named on a statue of her grandmother Huy" ≠ Huy is a parent of Iset B — that's grandparent). Empty list if no children are stated in the entry's own prose.
- **`dynasty`** — integer `18`. This chunk's scope is entirely chapter 3 / The Power and Glory / pre-Amarna Dyn 18. If D&H explicitly places an entry in a different dynasty (e.g. "Wife of a king of the mid-18th Dynasty"), still emit `dynasty: 18`. Cross-dynasty entries will not appear in this chunk.
- **`sub_period`** — string `"The Power and the Glory"` for every row in this chunk.
- **`unplaced`** — `true` for rows under the `### Unplaced` section heading at the end of the chunk (printed p. 141; D&H flag these individuals as attested but not confidently placed in the family tree). `false` for all other rows. Note: not every Unplaced entry carries a `Q` suffix — names like `Henutiunu`, `Sithori`, `Tatau`, `Wiay A`, `Ti` all appear under the `Unplaced` heading without a `Q`. Use the section heading, not the disambiguator letter, to determine this flag.
- **`notes`** — the full prose paragraph verbatim, single-line-joined. Strip OCR artifacts like broken ligatures, but preserve museum catalogue numbers (`CM CG57006`, `BM EA43`, `TT226`, `KV43`), scholarly-hedge words (`probably`, `possibly`, `perhaps`), and footnote markers (`¹⁰²`) as they appear. Trim leading/trailing whitespace. Do NOT summarise; do NOT editorialise.
- **`source_citation`** — `{"pdf_pages": "126-130", "edition": "Thames & Hudson 2004 hardback"}` on every row.

## Parsing hazards

- **`Iset A` and `Iset B`** are distinct individuals — Iset A is mother of Thutmose III; Iset B is daughter of Thutmose III + Meryetre-Hatshepsut. Do not conflate.
- **`(See also Addenda p. 304)`** appearing after a name is a cross-reference marker; include it in `notes`.
- **`Unplaced`** is a section heading in D&H's text, not an individual. The entries under it use `Q`-suffix disambiguators. Emit each individual as a separate row; treat the heading as chunk-internal structure only.
- **BOLD CAPITALS like `AMENHOTEP II`** appearing mid-entry means D&H is cross-referencing the king. The king is not a Brief Lives entry of his own here — he's a reference target. If `AMENHOTEP II` appears as a standalone entry header (bold-capital name at column start with its own role-code parenthetical), emit it as a row with `sex: "male"`, dynasty 18. If it appears mid-prose as part of another entry, leave it as prose context (it'll end up in `notes`).
- **Dual entries for the same name**: e.g. `Amenhotep D (KSon) ... Amenmose (EKSon; Genmo)` — these are two distinct people with different dh_ids. Emit both.
- **`Amenemopet A` and `Amenemopet B`** are two separate Brief Lives entries on p. 137. Similarly `Amenhotep B`, `Amenhotep C`, `Amenhotep D`. Don't collapse.
- **Kings' Daughters reburied during the 21st Dynasty**: D&H repeats the phrase `"One of the group of princesses reburied during the 21st Dynasty on Sheikh Abd el-Qurna"` for multiple near-anonymous princesses (Pyihia, Henutiunu, Meryetptah A, Sithori, Tatau, Wiay A — at least). Each is a distinct entry; emit each as its own row with the repeated prose verbatim in `notes`.
- **Homonymous Thutmoses**: `Thutmose A` is a son of Amenhotep II (later king Thutmose IV). `Thutmose Q` (Unplaced) might be a Captain of the Troops. `**THUTMOSE IV**` or `**AMENHOTEP II**` appearing as a bold-capital entry is that king as a Brief Lives entry — give him his own row.
- **Lacunae** `[...]` in names: preserve verbatim as `"[...]pentepkau"`. These are genuine gaps in the attestation.

## Sort order

Alphabetical by `dh_id`, case-insensitive. `Q`-suffix entries ("Unplaced" block) sort after the main alphabetical run even when they share a letter prefix — emit them in a single trailing block. `[...]`-prefixed names (lacunae at the start) sort after all letter-prefixed names.

## Expected row count

50-60 rows. If your row count is below 40 or above 70, re-read the chunk and count entries per page before writing.

## Output

Write the JSONL. In your final response, report: row count + anything anomalous (e.g. an entry that didn't fit the template, a role code you couldn't classify). Under 80 words.
