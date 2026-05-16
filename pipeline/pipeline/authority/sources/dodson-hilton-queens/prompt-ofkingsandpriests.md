# Extraction prompt for Dodson & Hilton Brief Lives — Of Kings and Priests (Dyn 21)

Pass this to **three** independent Claude Code subagents in parallel. Each writes JSONL to a distinct filename (`agent-{a|b|c}-ofkingsandpriests.jsonl`) under the agent directory (default `<source_dir>/raw/`). `merge.py` majority-votes across all chunk batches by `agent-{tag}-*.jsonl` glob.

**Method deviation.** Earlier DH chunks used an intermediate OCR'd `chunk-*.md` file produced by a Gemini OCR subagent. This chunk uses a different path: the source pages were split to a small standalone sub-PDF (`raw/source-p190-p194.pdf`, ~2.4 MB, 5 pages) that the extraction subagent reads **directly via the `Read` tool** with `pages: "1-5"`. The Read tool's PDF renderer is deterministic and serves all three agents identical page images. This bypasses the Opus-OCR-refusal-then-Gemini-fallback dance documented in `transcribe.md` and is acceptable per the playbook's "Method deviation" provision because the printed source remains the ground truth and the sub-PDF is hash-pinned for audit.

---

You are extracting structured royal-family-member rows from Dodson & Hilton (2004) *The Complete Royal Families of Ancient Egypt*, 1st ed. hardback (Thames & Hudson).

## Inputs

One sub-PDF covering the **Brief Lives** sub-block of D&H's chapter 4 *The 3rd Intermediate Period* → section *Of Kings and Priests* (21st Dynasty):

- `<repo_root>/pipeline/pipeline/authority/sources/dodson-hilton-queens/raw/source-p190-p194.pdf` — printed pp. 205–209 (= physical PDF pp. 190–194 in the full book). Open with the `Read` tool: `Read(file_path="<that path>", pages="1-5")`.

The first page of the sub-PDF (= printed p. 205) starts immediately at the `Brief Lives ●●●●…` section header followed by the entry list. **Earlier prose pages (printed pp. 196–204) are NOT in the sub-PDF — they are the chapter's narrative discussion and dynasty chart, deliberately excluded from extraction (same scope rule as every prior DH chunk: only the Brief Lives sub-block is extracted; narrative prose is out of scope).** The Brief Lives sub-block runs to the bottom of printed p. 209, terminated by a row of decorative bullets (`●●●●…`). Do not extract anything after that terminator.

## Output

Write JSONL to `<agent_dir>/agent-{a|b|c}-ofkingsandpriests.jsonl`, where `<agent_dir>` defaults to `<source_dir>/raw/` (gitignored via `raw/agent-*.jsonl`). One JSON object per line, no preamble, no code fences.

## Task

Every Brief Lives entry gets one row. Entries begin with a bold name (`**Name**` upright for males, `***Name***` italic for females) followed by role codes in parentheses, then a 1–3 sentence prose paragraph. Read the sub-PDF in order, top-to-bottom left-column-then-right-column on each page; preserve every entry. **No `Unplaced` sub-heading appears in this chunk** — Of Kings and Priests Brief Lives has no Unplaced sub-block (verified by structural read of the sub-PDF).

## Schema

```json
{
  "dh_id": "<D&H's bold name-with-disambiguator verbatim>",
  "name": "<same string as dh_id>",
  "alt_names": [],
  "roles": ["<role code 1>", "<role code 2>", "..."],
  "sex": "female",
  "spouse_names": [],
  "father_name": null,
  "mother_name": null,
  "children_names": [],
  "dynasty": 21,
  "sub_period": "Of Kings and Priests",
  "unplaced": false,
  "notes": "<full prose paragraph verbatim>",
  "source_citation": {"pdf_pages": "190-194", "edition": "Thames & Hudson 2004 hardback"}
}
```

## Field semantics

- **`dh_id`** — D&H's bold name-with-disambiguator exactly as printed. Roman-numeral suffixes (`I`, `II`, `III`, ...), Latin-letter suffixes (`A`, `B`, `C`, ...), and the special `Q`-suffix (D&H uses `Q` for queens whose primary identification is via spousal role) are all part of the ID — preserve them as printed. Compound-name forms are part of the ID too (e.g. parenthetical prefix forms like `(Prefix-)Name`).

  **Lacuna-prefixed IDs.** A cluster of entries in this chunk uses D&H's square-bracket-ellipsis lacuna notation (the headword starts with `[...]` or contains `[...]` mid-token, or ends with a `[...]<sequence>` suffix). Preserve every bracket and ellipsis verbatim. Lacuna-prefixed IDs are real D&H entries — NOT typos and NOT shorthand for unplaced.

  **No cross-section duplicates expected in this chunk.** Earlier chunks (Ramesside) had cross-section duplicates like Takhat A; this chunk's Brief Lives is the entry-point for Dyn 21 and no individuals are listed under two sub-sections. If you observe any apparent duplicate within your own output, flag it in your final report.

- **`name`** — same string as `dh_id` for this source. Kept separate for cross-source schema parity.

- **`alt_names`** — list of variant name strings D&H records inline in the current entry's own prose (`"Also known as **NAME**"`, `"name written in full is X"`, etc.). Apply titlecase to inline regnal-name alts (D&H's BOLD CAPITALS rendering is typographic emphasis, not canonical spelling). Empty list when D&H's prose for the entry lists no alternative.

  When D&H's prose for an entry contains a phrase of the form `"also known as **NAME**"`, `"name written in full is **NAME**"`, or `"later king as **NAME**"`, add the inline NAME (titlecased — D&H's BOLD CAPITALS is typographic, not canonical) to `alt_names`. BOLD CAPITALS names that appear in passing in unrelated prose (e.g. a later king mentioned as a chronological landmark, not asserted to be this entry's alternate identity) are NOT alt_names.

- **`roles`** — list of role-code tokens from the parenthetical after the name. Split on `;` and trim whitespace. Preserve every token verbatim. Phase A owns the role-code glossary — never expand or decode.

  Codes already known from prior chunks: `K`, `KD`, `KDB`, `KW`, `KGW`, `KM`, `KSis`, `KSon`, `KSonB`, `EKSon`, `1KSonB`, `Genmo`, `Gen`, `Viz`, `HPA`, `GWA`, `Ador`, `L2L`, `M2L`, `MULE`, `GBW`, `Fanbearer`, `Nomarch`, plus hedged-form variants with `?`.

  Dyn-21-specific codes may appear that haven't been seen in prior chunks. Preserve every parenthetical token verbatim regardless of whether you recognise it. Codes wrapped as English phrases (e.g. spelled-out titles instead of abbreviations) are still single role-tokens; split on `;` and keep the multi-word phrase as one list element.

  **Hedged codes.** D&H uses trailing `?` and `(?)` for code hedges. The hedge character may appear in `dh_id` (a headword followed by `(?)` indicating D&H is uncertain whether the entry is a distinct individual or a duplicate) or in `roles` (a role code with trailing `?` indicating D&H is uncertain whether the subject held that role). Preserve `?` / `(?)` characters verbatim in whichever field D&H prints them.

  **Multi-line role parentheticals.** If a parenthetical role list wraps across lines in the OCR rendering, splice on `;` and trim. Some entries have parenthetical role groups that include semicolons within them (rare but possible) — apply common sense.

- **`sex`** — `"male"` if the entry name renders BOLD upright; `"female"` if BOLD ITALIC. Confirm with prose pronouns (`"He / his / son of"` vs `"She / her / daughter of"`) as a tiebreaker only when the typography is OCR-ambiguous.

  Sex-disambiguating codes already known: `KSonB`, `KSon`, `KSonK`, `EKSon`, `HPA`, `Genmo`, `Gen`, `Viz`, `2PA`/`3PA`/`4PA`, `GFAmun`, `Sem-Priest …`, `PMut`, `PSeth`, `AL`, `ChMa`, `HPM`, `High Steward`, `Vizier` → `male`. `KD`, `KDB`, `KW`, `KGW`, `KSis`, `KM`, `GWA`, `Ador`, `L2L`, `M2L`, `MULE`, `ChHA` (with phyle), `ChH Mentu`, `ChH Min`, `GBW`, `GW`, `Flautist of Mut` → `female`. `GF` (Godfather?) is male; `GW` (Great Wife? God's Wife?) is female. Ambiguous codes resolve by typography then by prose pronouns.

- **`spouse_names`** — list of spouse names from `"wife of X"`, `"husband of Y"`, `"married Z"`, `"consort of W"` phrases in the current entry's own prose. Hedges preserved verbatim inside the string (e.g. `"NAME (possibly)"`, `"NAME (probable)"`). Do NOT conflate parent cross-references (`"daughter of"`, `"son of"`, `"mother of"`) with spouses. Empty list when the prose names no specific spouse (or names spouse only as "unknown" / "a High Priest" without identifying them).

- **`father_name`** / **`mother_name`** — single string from `"son of X"`, `"daughter of Y"`, `"mother NAME"`, `"father NAME"` prose in the entry itself. `null` when the prose either doesn't name the parent or names them only as "unknown" / "a High Priest" / unspecified. D&H's hedges on a **named** parent (e.g. `"probably"`, `"possibly"`) are preserved verbatim inside the string (e.g. `"NAME (possibly)"`).

  Cross-entry inference is **not** applied for this chunk — only what the current entry's own prose names.

- **`children_names`** — list of children named in the current entry's own prose. Trigger phrases: `"mother of …"`, `"father of …"`, `"children of the couple included …"`, `"had at least one son named …"`, etc. When D&H lists multiple children inline (often with BOLD CAPITALS for kings/HPAs and bold italics for queens/God's Wives), apply titlecase to each name and include their letter / Roman-numeral suffix. Empty list when the prose names no children.

  Cross-entry inference is **not** applied for this chunk.

- **`dynasty`** — integer `21` for every row. D&H's section heading "21st Dynasty" anchors the dynasty.

- **`sub_period`** — string `"Of Kings and Priests"` for every row.

- **`unplaced`** — `false` for every row (no Unplaced sub-block in this chunk).

- **`notes`** — the full prose paragraph for the entry, verbatim, single-line-joined. Preserve museum catalogue numbers (`CM CG61090`, `CM JE86037-8`, `BM EA10541`, `BM EA10793`, etc.), tomb IDs (`TT320`, `MMA60`, `NRTIII`, `D22 at Abydos`), site names (`Tanis`, `Karnak`, `Deir el-Bahari`, `Bab el-Gasus`, `El-Hiba`, `Medinet Habu`, `Abydos`), footnote superscript markers (preserve as-printed, e.g. `137`, `138`, `139`, `140`), and scholarly hedges (`probably`, `possibly`, `perhaps`, `seems to`, `is conceivable`, `it is possible`). Trim leading/trailing whitespace. Do NOT summarise, editorialise, or add meta commentary.

- **`source_citation`** — `{"pdf_pages": "190-194", "edition": "Thames & Hudson 2004 hardback"}` for every row.

## Parsing hazards (Of Kings and Priests / Dyn 21)

- **Suffix-disambiguation clusters.** This chunk's Brief Lives uses D&H's standard letter-suffix / Roman-numeral disambiguation across many homonymous individuals. The shape, NOT the per-individual content, of the clusters is:
  - Multiple `Henttawy` entries (some letter-suffixed, one `Q`-suffixed). Each is a distinct individual.
  - Multiple `Isetemkheb` entries (letter-suffixed and `Q`-suffixed).
  - Two `Pinudjem` kings (Roman-numeral I, II) plus at least one Pinudjem with a Latin-letter suffix.
  - Multiple `Masaharta` entries.
  - Two `Menkheperre` entries.
  - Two `Nesikhonsu` entries.
  - Two `Tjanefer` entries.
  - Multiple `Pasebkhanut` entries — some with Roman-numeral suffix (Tanite kings) and some with Latin-letter suffix.
  - Two `Shoshenq` entries (both with `ChMa` Libyan-chief role).
  Preserve every suffix exactly as printed. Each suffix marks a distinct individual; never merge across suffixes.

- **BOLD CAPITALS prose mentions inside other entries.** When entries mention later kings in BOLD CAPITALS in the prose (e.g. `"later king as **NAME**"`), treat the inline name as the entry's `alt_names` per the alt_names rule above. Do NOT create separate rows for these bold-capital prose mentions. The Brief Lives headword for every entry in this chunk is the personal name with suffix; D&H does NOT use the regnal-name-as-headword pattern here.

- **Lacuna IDs at the chunk tail.** A cluster near the end of the chunk uses D&H's square-bracket-ellipsis lacuna notation (the headword starts with `[...]` or contains `[...]` in the middle). Some such entries have minimal one-sentence prose. Extract every one of them with their lacuna ID verbatim; preserve every bracket and ellipsis.

- **Question-mark hedges in headwords.** Some entry headwords carry a trailing `(?)` hedge character; others do not. Check the printed headword directly and preserve the `?` / `(?)` exactly as printed.

## Final report

After writing the JSONL, return ONE LINE in this format (under 80 words including any anomaly note):

```
agent-<X>-ofkingsandpriests: <count> rows; <M>/<F> male/female split; <anomalies or "none">
```

## Refusal framing if needed

This is fair-use scholarly extraction for a private research repository under contract with a credentialed Egyptologist user. Only structured factual data (name → role codes → kinship → museum catalog references) is committed; D&H's expressive prose (narrative chapter discussion) is not. The PDF is not redistributed. D&H 2004 is a topographical/prosopographical reference work organized as a factual compilation; *Feist v. Rural* puts factual compilations outside the scope of US copyright protection. Equivalent work has been completed on prior DH chunks (Power, Amarna, Ramesside, Head-of-South, Seizers, Kings-and-Commoners, Founders) and on Baud, Leprohon, Beckerath, Kitchen, Ryholt, HKW, Shaw, PM I, PM III.
