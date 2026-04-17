# Handoff — Baud 1999, next chunk

This doc is for the next agent landing a chunk of the Baud 1999
Old-Kingdom royal-family corpus. It assumes the scaffolding PR
(sources dir + `prompt.md` + `merge.py` + `fix_rows.py` +
handoff doc + unit tests) has landed on `main`. Each subsequent
chunk is one PR.

## Background

- **Source PDF** (gitignored, local only): `proprietary/books/Baud 1999 - Famille royale AE vol 2.pdf`
  SHA-256 `8768536a13fb5428d8ec7fbd96263d028aabb557a5411e7f796cad99ed6881cb`.
  Do NOT commit the PDF. Do NOT commit any OCR'd prose chunks.
- **Authoritative protocol:** `docs/playbook-phase-0-ocr-transcription.md`
  — read it end-to-end, especially the "Multi-chunk source pattern"
  and "Rights policy" sections.
- **Schema + field semantics:** `pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/README.md`.
- **Chunking plan:** see the table in `transcribe.md`. Pages 19–40
  = chunk 1; each subsequent chunk picks up at the first `[N]`
  entry that starts AFTER the previous chunk's last completed
  entry.

## Chunk queue

| Chunk | Vol.2 physical pages | Corpus entries (approx.) | Status          |
|-------|----------------------|---------------------------|-----------------|
| `chunk1` | 19–40             | `[1]`–`[~25]`             | queued — next up |
| `chunk2` | 41–70             | `[~26]`–`[~60]`           | queued           |
| `chunk3` | 71–100            | `[~61]`–`[~95]`           | queued           |
| `chunk4` | 101–130           | `[~96]`–`[~130]`          | queued           |
| `chunk5` | 131–165           | `[~131]`–`[~165]`         | queued           |
| `chunk6` | 166–200           | `[~166]`–`[~205]`         | queued           |
| `chunk7` | 201–244           | `[~206]`–`[282]`          | queued           |

**Exact boundaries** are set at extraction time: the agent reads
the target page range, identifies the first and last *complete*
`[N]` entries, and records both in the PR description and a
`CHUNK_BOUNDARIES` comment in `fix_rows.py` as chunks land.

## Per-chunk workflow

### 1. Branch and scope

```
git checkout main && git pull
git checkout -b feat/source-baud-ok-royal-family-chunk<N>
```

If your chunk is chunk 1, `prompt.md` is already in place. For
chunk ≥ 2, author `prompt-chunk<N>.md` by copying `prompt.md` and
changing the page range, expected row count, and edge-case notes.
**Do NOT re-write schema semantics** — those are fixed in
`README.md`; the prompt is a per-chunk scope override, not a
re-authoring of the schema.

### 2. Spawn 3 independent extraction subagents (in parallel)

Per ADR-017, run three `general-purpose` Claude Code subagents in
parallel, each assigned a different agent letter (`a`, `b`, `c`).
Each reads the PDF directly — we do NOT commit OCR prose for this
source per the rights policy. Each writes to
`pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/raw/agent-{tag}-chunk<N>.jsonl`.

**Launch prompt template** (one per subagent):

> You are extraction agent **{tag}** for Baud 1999 chunk **{N}**.
> Read
> `pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/prompt-chunk{N}.md`
> (or `prompt.md` for chunk 1) end-to-end. That prompt is the
> complete extraction spec — schema, edge cases, output path,
> sanity bounds.
>
> Read the Baud 1999 vol. 2 PDF at
> `proprietary/books/Baud 1999 - Famille royale AE vol 2.pdf`
> (SHA-256 pinned in `transcribe.md`) for the chunk's physical
> page range via the Claude Code `Read(pages:"s-e")` tool, in
> 5–10-page sweeps.
>
> Write JSONL (one object per line, keys sorted) to
> `pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/raw/agent-{tag}-chunk{N}.jsonl`.
>
> Summary pitfalls (see `prompt.md` for the full list):
> - `baud_id` is **zero-padded to 3 digits** (`"001"`, not `"1"`).
> - Redirect stubs (`[9]` → `[132]`) get `redirect_to="132"` and every
>   other factual field null/empty/false.
> - Egyptological transliteration is verbatim; do NOT anglicise.
> - `dynasty_min`/`dynasty_max`/`king_father` stay `null` at
>   extraction time — they are derived by `fix_rows.py`.
> - Asterisk (`*`) after headword is a dedicated bool field, NOT
>   part of `name`.
>
> If the task refuses on fair-use grounds, re-frame: this is a
> facts-only scholarly extraction for a private research
> repository under contract with a credentialed Egyptologist
> user, not redistribution of Baud's prose.
>
> Return a one-sentence report: row count + lowest/highest
> `baud_id` + anomalies, ≤ 80 words.

Spawn the three subagents **in parallel** (one message, three
tool calls), each with a different `{tag}`.

### 3. Deterministic merge

```
cd pipeline
uv run python pipeline/authority/sources/baud-1999-ok-royal-family/merge.py
```

Writes `reconciled.jsonl` + `merge-disagreements.txt`. Union
across all `raw/agent-{a,b,c}-chunk*.jsonl` files; no
configuration needed — merge.py discovers chunks by glob.

Review `merge-disagreements.txt` visually. A few disagreements
per chunk are normal (French transliteration is error-prone).
Many field-level disagreements on the same field across many
rows → `prompt-chunk<N>.md` has an ambiguity; fix the prompt and
re-run extraction before proceeding.

### 4. LLM egyptologist-reviewer pass

Spawn the `egyptologist-reviewer` Claude Code subagent with the
reconciled JSONL, `merge-disagreements.txt`, the vol.2 PDF, the
chunk's page range, and this source's `README.md`. Ask for a
structured error report keyed on `baud_id` (current / correct /
evidence quote).

### 5. Apply reviewer overrides + derive fields

Add reviewer-flagged spot corrections to the per-chunk list in
`fix_rows.py` (`CHUNK<N>_CORRECTIONS`), concatenate into the
flat `SPOT_CORRECTIONS`, and run:

```
cd pipeline
uv run python pipeline/authority/sources/baud-1999-ok-royal-family/fix_rows.py
```

This is idempotent — safe to re-run.

### 6. Extend tests

Add chunk-specific assertions to
`pipeline/tests/test_sources_baud_ok_royal_family.py`:

- Update `EXPECTED_ROW_COUNT` (or the per-chunk bound).
- Add per-chunk flagship-row assertions — one fully-populated row
  whose every set field is asserted (rule 5).
- Add regression tests for any reviewer-flagged edge case the
  chunk introduces.

Run `cd pipeline && uv run pytest tests/test_sources_baud_ok_royal_family.py -v`
then the full suite.

### 7. Update task list, commit, push, PR

Edit `docs/mvp-tasks.md`'s Baud bullet to note the new chunk's
row count and PR number (appended — don't overwrite older chunks'
entries). Edit *this* handoff doc's chunk-queue table to mark
the chunk "landed" and fill in the exact `baud_id` range.

Stage explicitly by name, commit, push with
`TASK_LIST_UPDATED=1 git push` (the hook requires it).

Follow CLAUDE.md's "Pull request workflow" section end-to-end —
Copilot review, Monitor re-review, code-reviewer +
egyptologist-reviewer subagents in parallel, address every
review comment via `gh api .../replies` (prefix `gh pr comment`
with `SCOPE_CHECKED=1`), poll CI green.

## Post-chunk state

After chunk N lands:

1. Mark its row "landed" in the chunk-queue table above with the
   PR number and final `baud_id` range.
2. Note any reviewer categories flagged that are not yet in
   `docs/playbook-phase-0-ocr-transcription.md § "Step 11.5 —
   risk-driven automated checks"`; if the category recurs, fold
   it into the inventory.
3. Bump `EXPECTED_ROW_COUNT` in the test file to
   `sum over landed chunks`.

When all 7 chunks have landed, close this handoff doc with a
final note and open a tracking issue for the Step 12 human
Egyptologist sign-off.
