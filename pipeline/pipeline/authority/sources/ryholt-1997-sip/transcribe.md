# Transcription method — Ryholt 1997

Reproducible protocol per ADR-017 (Claude Code subagent OCR, followed by three-subagent structured extraction and deterministic majority-vote merge).

## Inputs

1. `proprietary/books/Ryholt 1997 - Political Situation SIP.pdf` — full scanned book (466 pages, 37 MB). Not committed to the public repo.
2. Printed pages **333–411**: File 1 / Catalogue of Attestations (pp. 333–407) + Chronological Tables (pp. 408–411).

## Pipeline

Per ADR-017: Claude Code subagent OCR of physical-page chunks, followed by a three-subagent structured extraction and a deterministic majority-vote merge. The OCR runs under the existing Claude Code subscription (same trust boundary as any other Claude Code tool use) — no new external vendor and no per-page OCR billing.

### Bulk OCR (Claude Code subagents)

For each 5-physical-page chunk, spawn a Claude Code general-purpose subagent. The subagent uses the `Read` tool to open the source PDF at the chunk's physical-page range (1-indexed, max 20 pages per Read call) and transcribes each page as Markdown with the ADR-017 rules:

- Preserve Egyptological transliteration exactly (ꜣ ꜥ ḥ ḫ ẖ š ṯ ḏ); refuse ASCII substitutions.
- Preserve roman numerals and bibliographic references.
- Preserve the book's own running-header page-numbers inline.
- Preserve the two-column layout by emitting column 1 then column 2.
- Preserve underlined text with `<u>…</u>`.

Each chunk is written to `raw/chunk-pNNN-pMMM.md` on local disk. **These files are not committed** — they contain Ryholt's prose and must stay local per ADR-017.

### Review (LLM, then human — honestly labelled)

Per ADR-017 step 6:

- **LLM review (done on this source):** after the 3-subagent merge, the `egyptologist-reviewer` Claude Code subagent walks every entry in `merge-disagreements.txt`, cross-checks against the PDF, and flags rows where the majority vote is wrong. The main agent applies those corrections to `reconciled.jsonl` via a small override (committed). Every override is recorded in `merge-disagreements.txt` under the `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED` section. **This is an LLM checking an LLM.** Better than unreviewed merge output, but it is not scholarly validation.
- **Human review (required, NOT yet done on this source):** an actual Egyptologist reads a sample of king rows against Ryholt's printed PDF and signs off. Until that happens, the Ryholt extract is **provisional** for downstream consumers.

### JSONL derivation — three-subagent extraction + deterministic merge

The Ryholt catalogue has enough structural variety (bold vs plain Appellation headers, letter-only file suffixes like `17/a`, two different Chronological-Table layouts, lacuna markers, Roman-numeral disambiguators like `Sewadjkare (I)`) that a regex parser quickly accumulates bugs — e.g. a version that couldn't match `File 17/a` silently attributed Nebmaatre's titulary to Kamose (File 17/9). Instead, we extract via three independent Claude Code subagents and merge by majority vote.

**Step 1 — run three independent extractors in parallel.** From Claude Code, spawn three general-purpose subagents with identical prompts (the prompt is committed to `prompt.md` in this directory). Each subagent reads every `raw/chunk-p*.md` file and writes JSONL to a distinct file under the merge agent-directory (default `/tmp/claude-501/ryholt/`, overridable via `--agent-dir` / `RYHOLT_AGENT_DIR`):

- Agent A → `<agent_dir>/agent-a.jsonl`
- Agent B → `<agent_dir>/agent-b.jsonl`
- Agent C → `<agent_dir>/agent-c.jsonl`

**Step 2 — deterministic merge.**

```
cd pipeline && uv run python pipeline/authority/sources/ryholt-1997-sip/merge.py
```

`merge.py` groups rows by `ryholt_id`, takes a per-field majority vote across the three agents, writes `reconciled.jsonl`, and writes `merge-disagreements.txt` (committed) with every row whose fields didn't fully agree. The merge is pure Python with no LLM calls; re-running it on the same three inputs produces byte-identical output. Reviewers auditing the source can read the disagreements file to see every non-unanimous decision, and the LLM-applied overrides section at the bottom.

**Audit trail**:
- PDF (SHA-256 pinned in README; not committed) → `raw/chunk-p*.md` (Claude Code subagent OCR; not committed, per-transcriber regenerable)
- `raw/chunk-p*.md` → three per-extraction-agent JSONLs (Claude Code subagents, non-deterministic, ephemeral — not committed)
- three per-agent JSONLs → `reconciled.jsonl` (deterministic merge, committed)
- `merge-disagreements.txt` (committed) lists every field where extraction agents disagreed plus the majority-vote resolution

## The prompt

Both models receive an identical prompt that:

- Names the book, so the model has context
- Enumerates the Egyptological Unicode character set (`ꜣ ꜥ ḥ ḫ ẖ š ṯ ḏ`) and explicitly forbids ASCII substitutions (`3` for ꜣ, `c` for ꜥ, `h` for ḥ/ḫ)
- Demands Markdown output preserving the two-column layout and HTML `<u>…</u>` for underlined primary attestation locations
- Forbids any preamble or closing remarks

The prompt is the load-bearing part of the pipeline — a generic "transcribe this PDF" prompt produces worse diacritic output. See the "Bulk OCR (Claude Code subagents)" section above for the rules that every OCR-subagent prompt enforces.

## Known model biases (from the p. 336 benchmark)

- Claude Opus 4.6 has been observed to conflate `ḥ` and `ḫ` in Horus names (`mnḫ` → `mnḥ`) on early single-subagent tests; the diacritic prompt significantly reduces this.
- Proper-noun diacritics on French/Arabic transliterations (e.g. `Fûad` vs `Fūad`) and some roman-numeral references in bibliographies (e.g. `PM II²`) can drift between extractions. These fields do not flow into `reconciled.jsonl` so the drift has no authority-layer impact; it is noted here for curators who read the raw chunks.
- All tested subagent runs are reliable on `ꜣ ꜥ nṯ` once the prompt is enforced.

## PDF page ↔ printed page mapping

Per ADR-017 ("Why physical pages, not printed pages"), we cite by physical page number rather than resolving the book's own page numbering, because Ryholt's PDF has a Part-heading break at printed p. 408 that drops a blank and shifts the physical→printed offset from +4 to +3. For reference:

- In File 1 (printed pp. 333–407, ~Part VI): physical page N = printed page N + 3 (i.e. 0-indexed `reader.pages[N + 2]` for printed N). Verified at printed p. 336 / physical 340.
- In Chronological Tables (printed pp. 408–411): the offset is +2 (one page smaller). Verified at printed p. 408 / physical 410.

Citations in `reconciled.jsonl` use the physical-page range of the OCR chunk the row came from, so no offset arithmetic is needed to verify a row.

## Structure of File 1 entries

Every king entry follows the same template (see README for the full list):

```
Appellation: <Anglicised name>         File <dyn>/<seq>
H: <horus name>                        ← transliterated; dash if unknown
D: <nebty name>
G: <golden Horus name>
P: <prenomen>
N: <nomen> [with filiation to his father X]
Turin King-list, <col>/<row>: <...>    ← optional, if attested
Attestations:
  1) <findspot>, <object-type>.
     <current location>.
     Bibl.: <citations>.
  …
Remarks: <optional narrative>
Notes:
  1. …
  2. …
```

The JSONL parser (added when Phase 2 lands) uses this template to extract structured fields. Non-canonical entries — kings Ryholt lists in the "Unattributed" bucket at the end — require manual schema handling and are flagged in README known-gaps.

## Chronological Tables (pp. 408–411)

These pages summarise Ryholt's reconstructed parallel-dynasty chronology. They populate the `polity` and `concurrent_with` fields on every king entry. Extraction is done by table transcription from the OCR markdown, cross-referenced against the per-king entries in File 1 for consistency.

## PDF hash pinning

Source PDF SHA-256: `078c0d92bc3310c1044d4b736db6a8af9c309ef6839bd9e96b6864d200bbc972`. A reviewer re-running the pipeline against a PDF with a different hash should not expect byte-for-byte output reproduction; model outputs are stochastic, and the committed `reconciled.jsonl` is the source of truth.

## Verification

`pipeline/tests/test_sources_ryholt_sip.py` (added in Phase 2) will assert specific field values for 3+ sampled rows and enforce the rule-5 "all populated fields" contract.
