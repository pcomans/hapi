# Extraction prompt — Porter & Moss Vol III.1 (Memphis), Chunk 17b

> **Chunk 17b (second half of CEMETERY G 7000 East Field remainder)** — picks up where chunk 17a leaves off at G 7540. PM III.1 physical pp.197–211 / printed pp.200–214. The chunk closes out the G 7000 East Field MVP coverage; chunk 18 will pick up at PM § III.C CEMETERY G I S (physical p.213). Highlights include the King's-son cluster (G 7660 KAEMSEKHEM, G 7760 MINZEDEF, G 7810 ZATY) + a Shape-4 joint twin Iynefer-and-wife-Nefertkau at G 7820 + the prophetess HEPENNEBTI at G 7815 + the dense terminal cluster G 7820 onwards with multiple Shape-1 named-primary rows. Parallel structure to chunk 17a; same Shape taxonomy. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-17b-p197-p211-g7000-east-remainder-b.txt` and produce a JSONL file with one structured row per **PM-headworded Reisner-numbered mastaba** in the G 7550→G 7948 range. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** field-extraction RULES only; no per-row answers.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (tomb identifier → occupant name → role → cemetery) is committed; PM's expressive prose is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside US copyright. Chunks 1–16 + chunk 17a have already shipped or are in-flight (see `reconciled.jsonl`).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part I. Abû Rawâsh to Abûsîr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1974).
- Section: **PYRAMID-FIELD OF GÎZA — III. NECROPOLIS — B. EAST FIELD** terminal portion, `CEMETERY G 7000` (Reisner Excavation, Harvard-Boston Expedition).
- PM III.1 offset for this chunk: **printed = physical + 3**.
- The chunk file covers physical pp.197–211 / printed pp.200–214.
- **Top boundary:** the chunk file opens at physical p.197 with `G 7550. DUAENHOR`. Chunk 17a covers G 7152→G 7540 (physical pp.188–196).
- **Bottom boundary:** the chunk file ends at physical p.211. Chunk 18 will pick up at physical p.213 with `C. CEMETERY G I S` banner.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk17b.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk17b.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk17b.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Schema (per row — 23 keys)

Identical to chunk-17a. See prompt-chunk-17a.md for the full schema block.

## How to identify a row

Identical Shape taxonomy to chunk-17a (Shape 1 named-primary, Shape 2 bare-numeric, Shape 3 bracketed-Roman, Shape 4 joint-twin `G xxxx+yyyy`, Shape 5 range/anonymous). See prompt-chunk-17a.md for the full Shape rules.

Critical Shape 4 rule (chunks 14 G 4811 lesson): joint-named twins `G xxxx+yyyy` are multiple TOMB NUMBERS, not multiple OCCUPANTS. Emit ONE row with `tomb_id: G<xxxx>`, `tomb_aliases: ["G <yyyy>"]`, `is_joint_burial: false`.

Chunk-17b-specific Shape 4 wrinkle: `G 7820. IYNEFER . . . and wife NEFERTKAU.` Per PM convention this IS a joint burial of multiple occupants (Iynefer and his wife Nefertkau share the same tomb shaft). For THIS row type, `is_joint_burial: true`, `occupant_name: "Iynefer"`, `co_occupants: ["Nefertkau"]`, `co_occupant_roles: ["Wife"]`. Distinct from the `G xxxx+yyyy` Reisner-number twin pattern. Per chunk-14 G 4811 lesson, multiple-TOMB-NUMBERS = is_joint_burial false, multiple-OCCUPANTS = is_joint_burial true.

**ROW-EMITTING vs OUT-OF-SCOPE.** Emit one row per:
- Each Shape-1, 2, 3, 4, 5 headword line in the page range G 7550→G 7948.

Do NOT emit rows for:
- Out-of-range headwords (G 7540 and below = chunk-17a territory).
- Body-prose object mentions without their own `G <NUM>.` headword line.
- Chapel sub-features, museum-citation lines, publication references.

**Headword block ends** at the first sub-feature heading or museum-citation token (see chunk-17a Shape-block rules).

## Expected row count

Pre-extraction structural scan: ~15 Shape-1 named-primary (G 7550 DUAENHOR, G 7650 AKHTIHOTP, G 7660 KAEMSEKHEM, G 7711a KHNEMZEDEF — letter-suffix tomb, G 7721 KAKHERPTAH, G 7760 MINZEDEF, G 7810 ZATY, G 7814 KAaAPER, G 7815 HEPENNEBTI, G 7821 NEFERSESHEMPTAH, G 7822 MESU, G 7836 NEBTYHERKAUS, G 7851 WERMERU, G 7946 NEFU, G 7948 RAaKHAaEFaANKH) + ~1 Shape-4 actual joint-occupant burial (G 7820 IYNEFER and wife NEFERTKAU) + ~1 Shape-4 `+`-joint-twin (G 7837+7843 aANKHMAaREa) + ~14 Shape-2 bare-numeric. **Total expected: ~25–32 rows (acceptable band 22–36).**

## PM III.1 text-layer noise (chunk-17b-relevant)

Same noise classes as chunk-17a. Key examples for this chunk:
- `aANKH-HAF` analogues: `aANKHMAaREa` → `ʿAnkh-maʿrēʿ` (Re-deity compound trailing, double ayin, macron-Ē on -rēʿ).
- `KAaAPER` → `Kaʿaper` (ayin only).
- `RAaKHAaEFaANKH` → `Raʿkhaʿef-ʿankh` (theophoric-ankh hyphenation per chunks 8/14/15 convention: `Khufu-ʿAnkh`, `Khufudinef-ʿankh`). NB: OCR `RAa` (uppercase R + uppercase A + raised-a) yields `Raʿ` only — no macron-ē. The macron-Ē applies to `REa` (uppercase R + uppercase E + raised-a) OCR forms (cf. `DUAENREa` → `Duaenrēʿ`, `MENKAUREa` → `Menkaurēʿ`); `RAa` and `REa` are distinct OCR signatures.
- `NEBTYHERKAUS` → `Nebtyḥerkaus` (ḥ-root *ḥr*).
- `HEPENNEBTI` → `Ḥepennebti` (ḥ-root *ḥp*).
- `AKHTIHOTP` → `Akhtiḥotp` (ḥ-root *ḥtp*).
- `KAKHERPTAH` → `Kakherptaḥ` (ḥ-root *ptḥ* trailing).
- `NEFERSESHEMPTAH` → `Neferseshemptaḥ` (ḥ-root *ptḥ* trailing).
- `WERMERU` → `Wermeru` (no ḥ, no ayin — clean).
- `KHNEMZEDEF` → `Khnemzedef`.
- `MINZEDEF` → `Minzedef`.
- `MESU` → `Mesu`.
- `NEFU` → `Nefu`.

**Letter-suffix tomb IDs.** PM `G 7711a.` → `tomb_id: G7711a` (lowercase letter suffix preserved, no space). Parallel to chunks 11 D80A / D75a precedents.

**"Wife, <NAME> <title>" body-prose preservation.** Per chunks 9-16 convention. Capture verbatim in `co_occupants` + `co_occupant_roles` with `, etc.` markers preserved.

**Royal-family occupant_role mapping.** Same as chunk-17a: `King's son [of his body]` → `Prince`. `King's daughter` → `Princess`. `Prophetess of <X>` (e.g., HEPENNEBTI Prophetess of Hathor and Neith) → `Official` per source-wide pattern.

## Field-by-field rules

Identical to chunk-17a. See prompt-chunk-17a.md for the full field-by-field block. Key reminders:
- `tomb_id`: `G<NUM>` (drop space). For letter-suffix: `G<NUM><letter>` (lowercase letter, no space).
- `cemetery`: `"G 7000"` for every chunk-17b row.
- `is_joint_burial`: `false` for `+`-joint-twin Reisner numbers; `true` only for true multi-occupant burials (G 7820 Iynefer + wife Nefertkau).
- `source_citation.page`: `printed = physical + 3` boundary rule. Chunk-17b page boundaries: physical p.197 = printed p.200, ..., physical p.211 = printed p.214.

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk17b: <count> rows; <shape1>/<shape2>/<shape3>/<shape4>/<shape5> split; <anomalies or "none">
```

Where shape1 = G-named primary, shape2 = G-bare-numeric, shape3 = bracketed-Roman, shape4 = joint-twin (`+` or `and wife`), shape5 = range/anonymous. Under 100 words.
