# Transcription method — Porter & Moss Vol III (Memphis)

Operational notes for the Phase-0 pipeline. The protocol itself lives in `docs/playbook-phase-0-ocr-transcription.md`.

## Source

- **Vol III.1** *Memphis. Part I. Abû Rawâsh to Abûsîr*, 2nd ed., 1974, ed. Málek. PDF SHA-256 `4817c0e09d126f387ffdc6793517caa125946aca1b6f4a5736a8daf32e167e58`. 349 physical pages, ~50 pages front matter (Roman) + 366 pages body + 30 plates + indexes.
- **Vol III.2** *Memphis. Part 2. Ṣaqqâra to Dahshûr*, 2nd ed., 1978/1981 fascicles, ed. Málek. PDF SHA-256 `dabb5c207642f1dd7a47de4f3db28f6c59d16ab3f0db8140c9672de3e7ed77df`. To be exercised at chunk 4+ (Saqqara work).

Both PDFs sit at `proprietary/books/` (gitignored, submodule).

## Method deviation (vs playbook step 3)

PM III PDFs carry an embedded text layer (verified 2026-05-15 for PM III.1 — `pypdf.PdfReader` produces extractable prose for every physical page sampled). Per the playbook's "Method deviation" provision and the Theban precedent (`porter-moss-theban-necropolis/transcribe.md`), the OCR subagent step is replaced by deterministic `pypdf` text-layer extraction:

```python
import pypdf
r = pypdf.PdfReader("proprietary/books/Porter & Moss - PM III Memphis.pdf")
with open("pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-1-p8-p32.txt", "w") as f:
    for i in range(7, 32):  # physical pages 8–32, 0-indexed
        f.write(f"\n=== physical page {i+1} ===\n")
        f.write(r.pages[i].extract_text())
```

The text-layer output goes to `raw/chunk-<n>-p<start>-p<end>.txt` (gitignored under the `raw/chunk-*.txt` pattern; same posture as Theban chunk files).

## Page-offset map (PM III.1)

The front matter consumes physical pages 1–7 (cover, half-title, title, contents i–vii). PM's printed-page numbering then begins at printed `p.1` = physical p.8 (Abû Rawâsh I. Pyramid). The offset is **`physical = printed + 7`** for the body; verify per-chunk because PM III front-matter pagination may drift (the printed contents page itself is `p.vii` in Roman but lives at physical p.5, etc.).

Page anchors confirmed via text-layer header scan (2026-05-15):

| Printed | Physical | Section |
|---|---|---|
| 11 | 8  | Pyramid-field of Gîza — I. PYRAMIDS — A. PYRAMID-COMPLEX OF KHUFU |
| 19 | 17 | B. PYRAMID-COMPLEX OF KHEPHREN |
| 27 | 24 | C. PYRAMID-COMPLEX OF MENKAUREʿ |
| 35 | 32 | (Menkaureʿ tail) → § II. GREAT SPHINX AREA |
| 49 | 46 | § III. NECROPOLIS — A. WEST FIELD (Cemetery G 1000+) |

## Pipeline

1. `pypdf` text-layer extraction → `raw/chunk-<n>-p<start>-p<end>.txt`.
2. Three parallel extraction subagents (general-purpose) run against `prompt-chunk-<n>.md` + the text-layer chunk, write `raw/agent-{a,b,c}-<chunk>.jsonl`.
3. `merge.py` — deterministic majority-vote, `tie-break-overrides.json` resolves 1/1/1 ties with a printed-source citation. Outputs `reconciled.jsonl` + `merge-disagreements.txt`.
4. `egyptologist-reviewer` subagent pass against the printed PDF pages (`reviewer-notes-chunk<n>.md`).
5. `fix_rows.py` applies reviewer corrections + post-merge normalisations to `reconciled.jsonl`.
6. `pipeline/tests/test_sources_porter_moss_memphis.py`.

## Chunk 1 scope

Physical pp.8–32 / printed pp.11–35: the three Gîza pyramid complexes (Khufu G1, Khephren G2, Menkaureʿ G3) and their attested queens' subsidiary pyramids. Expected ~8–12 rows. Establishes the `memphite_area` vocabulary and the Reisner G-number `tomb_id` convention.

PM III text-layer noise classes will accumulate from chunk 1 onwards into `postprocess.py` and per-chunk `CHUNK<N>_CORRECTIONS` tables. The Theban-source `porter-moss-theban-necropolis/postprocess.py` template carries OCR-noise rules portable to PM III where the same Griffith-Institute scan generation produced the same artifacts.
