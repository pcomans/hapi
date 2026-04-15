# Extraction prompt for Claude Code subagents

Pass this to **three** independent Claude Code subagents in parallel (general-purpose, or any agent with Read/Write tools). Each agent writes its JSONL output to a distinct filename. The three outputs are then merged by `merge.py` via majority vote (see `transcribe.md`).

The prompt below is verbatim; the only per-agent substitution is the output-file suffix (`-a`, `-b`, `-c`).

---

You are extracting structured king data from OCR'd pages of Ryholt 1997, *The Political Situation in Egypt During the Second Intermediate Period*.

**Input**: 17 OCR chunk files at `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/ryholt-1997-sip/raw/chunk-p*.md`. Each file covers a physical-PDF-page range declared in an HTML comment at the top and in the filename (`chunk-pNNN-pMMM.md`).

**Output**: write your final JSONL to `/tmp/claude-501/ryholt/agent-{a|b|c}.jsonl`. One JSON object per line, no trailing newline required, no preamble, no code fences.

**Task**: walk every chunk. Find every king entry — each one begins with a line like `Appellation: NAME File X/Y` (sometimes bolded as `**Appellation: NAME** File X/Y`). For each king, emit one row with the following schema:

```json
{
  "ryholt_id": "13.17",
  "dynasty": 13,
  "sequence_in_dynasty": 17,
  "sequence_suffix": null,
  "nomen": "Khendjer",
  "prenomen": "Woserkare",
  "horus_name_transliterated": "mnḫ-...",
  "nebty_name_transliterated": null,
  "golden_horus_name_transliterated": "ꜥnḫ-nṯrw",
  "prenomen_transliterated": "sḫm-rꜥ-ḫw-tꜣwy",
  "nomen_transliterated": "sbk-ḥtp",
  "date_bce_start": -1764,
  "date_bce_end": -1759,
  "polity": "Memphite",
  "concurrent_with": [],
  "source_citation": {"pdf_pages": "336-340", "edition": "CNI Publications 20, Museum Tusculanum Press, 1997"}
}
```

**Field semantics**:
- `ryholt_id` = `"{dynasty}.{sequence}{optional-suffix}"` from Ryholt's `File X/Y` label.
- `dynasty` = integer 13-17, or null for `File N/...` unattributed entries.
- `sequence_in_dynasty` = the Y in `File X/Y`.
- `sequence_suffix` = letter suffix (`"a"`, `"b"`) or null.
- `nomen` = anglicised nomen from the Chronological Tables (Tables 94-98); fall back to the Appellation if not in a Chron Table.
- `prenomen` = anglicised prenomen from the Chron Tables; null if Ryholt doesn't give one.
- `horus_name_transliterated` / `nebty_ / golden_horus_ / prenomen_ / nomen_transliterated` = verbatim from the H / D / G / P / N lines in Ryholt's File entry. Strip surrounding markdown emphasis (`*...*`). A bare `-` means "not known" → null. Strip trailing `with filiation to his father ..., Amenemhet IV` clauses from `nomen_transliterated`.
- `date_bce_start` / `date_bce_end` = negative integers for BCE, from the Chronological Tables. Null if Ryholt gives no absolute date.
- `polity` by dynasty: 13 → `"Memphite"`, 14 → `"Avaris"`, 15 → `"Avaris (Hyksos)"`, 16 → `"Theban"`, 17 → `"Theban"`, unattributed → null.
- `concurrent_with` by dynasty: 13 → `["14"]`, 14 → `["13", "15"]`, 15 → `["16", "17", "Abydos"]`, 16 → `["15", "17"]`, 17 → `["15", "16"]`, unattributed → `[]`.
- `source_citation.pdf_pages` = the chunk's physical-page range (e.g. `chunk-p336-p340.md` → `"336-340"`). NOT Ryholt's own printed-page numbers.

**Critical matching rule**: cross-reference each king with the Chronological Tables (Tables 94, 95, 96, 97, 98), found in `chunk-p411-p415.md`. Match by **anglicised nomen string** from the Appellation, not by sequence index. Ryholt's File numbering can disagree with his Chronological-Table sequence — e.g. File 17/9 is Kamose, and File 17/a (letter-only suffix) is Nebmaatre, who isn't in the Chron Table proper. Look up each king by his Appellation in the Chron Tables; if no match, leave `prenomen` and date fields null and populate `nomen` from the Appellation.

**Format notes in the OCR**:
- Bolded `**Appellation: NAME** File X/Y` headers alongside plain ones.
- File suffixes may be numeric (`17/9`), letter-only (`17/a`), or combined (`13/21a`).
- H/D/G/P/N lines sometimes italicised (`H: *mnḫ-[...]*`), sometimes plain.
- `-` on an H/D/G/P/N line → null.
- `Appellation: -` with no name → **skip**, do not emit a row.
- Chron Table lacuna markers (italic narrative rows like `*Eight kings lost in the Turin King-list*`) → skip.
- `(H:) Sewesekhtawy` in a Chron Table means the Horus name substitutes for an unknown nomen; record the anglicised value in `nomen`.
- Two Chron Table layouts: 5-column `| No | Nomen | Prenomen | Date | Date |` (Dyns 13/14/16/17) and 4-column `| Nomen | Prenomen | Date | Date |` (Dyn 15). Parse both.

**Sort order**: by dynasty (ascending) then sequence. Unattributed (`dynasty: null`) last.

**Expected row count**: ~150 (our first run produced 157 identical rows across three agents).

**Output**: final JSONL at the designated path. In your response message, give a one-line summary stating how many rows you wrote plus anything anomalous. Under 80 words.
