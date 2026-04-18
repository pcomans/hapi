# Handoff — Baud 1999 Old Kingdom royal family, chunk 2+

**Written 2026-04-17**, after chunk 1 merged at PR #53 and the post-chunk-1 handoff rewrite merged at PR #55. You are the agent starting chunk 2 (entries `[41]`–`[80]`) or any later chunk.

Baud is the OK prosopographic counterpart to D&H's NK/LP queen coverage — deeper per-entry (full titulary, monument list, scholarly refs) but narrower in scope. Expect denser extraction than D&H: each Baud entry has a header block (a–e) plus up to four prose rubrics (TITRES / DATATION / PARENTÉ / DIVERS). Per `docs/mvp-tasks.md`, Baud is required (not optional) because D&H's OK coverage is weaker.

Read `docs/playbook-phase-0-ocr-transcription.md` § "Multi-chunk source pattern" first. Dodson-Hilton (`sources/dodson-hilton-queens/`) and Baud chunk 1 (`sources/baud-1999-ok-royal-family/`) are the reference implementations. This handoff supersedes the playbook where they disagree.

---

## Source

Michel Baud, *Famille royale et pouvoir sous l'Ancien Empire égyptien*, Bibliothèque d'Étude 126, IFAO, Cairo, 1999. Two volumes; vol. 2 is the *Corpus* (282 entries alphabetical by Egyptian transliteration, spanning Dyns 3–6).

- **PDF:** `proprietary/books/Baud 1999 - Famille royale AE vol 2.pdf` (gitignored; 296 physical pages).
- **SHA-256:** `8768536a13fb5428d8ec7fbd96263d028aabb557a5411e7f796cad99ed6881cb` (pinned in the source `README.md` and `transcribe.md`).

---

## State

- ✅ **Chunk 1** (`[1]`–`[40]`, physical pp. 11–49) — merged PR #53. 40 rows, 10 `fix_rows.py` LLM-APPLIED OVERRIDES, 22 pytest functions / 65 asserts. Pipeline + web CI green.
- 🔜 **Chunks 2–7** — pending. ~40 entries per chunk, one PR each.
- Issue #54 tracks the same three bugs in D&H's merge/fix_rows scripts that chunk 1 fixed in the Baud clone. Not blocking; fix when D&H earlier-chapters chunks are touched.

### Chunk plan

| # | Entries | Status | Pages |
|---|---|---|---|
| 1 | `[1]`–`[40]` | ✅ PR #53 | physical pp. 11–49 (incl. Corpus intro pp. 11–16) |
| 2 | `[41]`–`[80]` | 🔜 **next** | physical pp. 49–~83 — **include p. 49** (boundary overlap; `[41]`'s headword starts at the bottom of p. 49) |
| 3 | `[81]`–`[120]` | pending | TBD |
| 4 | `[121]`–`[160]` | pending | TBD |
| 5 | `[161]`–`[200]` | pending | TBD |
| 6 | `[201]`–`[240]` | pending | TBD |
| 7 | `[241]`–`[282]` | pending | TBD |

**Density:** chunk 1 was 40 entries / 33 content pages = ~1.2 entries/content-page (pp. 11–16 are the Corpus intro, which chunk 1 alone bundles). Chunks 2+ plan on ~33–35 physical pages per 40 entries. Baud's entries grow longer in the Dyn-4/Dyn-6 dense sections; later chunks may drift higher.

---

## Scaffolding — extend, do not rebuild

`pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/` already exists on `main`. For chunk N, ADD these files:

- **`prompt-chunk-<N>.md`** — clone from `prompt-chunk-1.md`, update: entry-number boundaries, physical-page range, per-chunk hazards (the prior chunk's review cycle often flags new ones), expected-row-count sanity bound.
- **`raw/source-chunk-<N>.pdf`** — split with `pypdf` (same recipe as chunk 1). Gitignored.
- **`raw/agent-{a,b,c}-chunk-<N>.jsonl`** — 3 parallel `general-purpose` subagents Read the sub-PDF directly; no committed OCR. Gitignored.
- **`fix_rows.py`** — APPEND a new `CHUNK<N>_CORRECTIONS: list[tuple[str, str, object, str]]` constant alongside every existing chunk constant (do not edit prior lists). Chunk 2 replaces the current singleton `SPOT_CORRECTIONS: list[tuple[str, str, object, str]] = CHUNK1_CORRECTIONS` with the list-based aggregation:
  ```python
  ALL_CORRECTIONS = [CHUNK1_CORRECTIONS, CHUNK1_BACKFILL, CHUNK2_CORRECTIONS]
  SPOT_CORRECTIONS = sum(ALL_CORRECTIONS, [])
  ```
  If chunk 2 implements the `CHUNK1_BACKFILL` list from the decision checklist (see below), include it in `ALL_CORRECTIONS` alongside the per-chunk constants. Each later chunk appends its constant to `ALL_CORRECTIONS` (single-line edit). Dropping any constant from the list silently destroys its audit trail — a parallel test that iterates module-level `CHUNK*_CORRECTIONS` / `CHUNK*_BACKFILL` attributes and asserts each appears in `ALL_CORRECTIONS` catches the omission.
- **`tests/test_sources_baud_ok_royal_family.py`**:
  - ADD a new `CHUNK<N>_EXPECTED_ROWS = 40` module-level constant next to every existing chunk-count constant. Do NOT rename existing constants.
  - UPDATE `test_row_count` to the list form `assert len(_rows()) == sum([CHUNK1_EXPECTED_ROWS, CHUNK2_EXPECTED_ROWS, ...])`. Pair with an iteration-based omission-catch test for the same reason as `ALL_CORRECTIONS` above.
  - RENAME `test_baud_id_covers_1_to_40` → `test_baud_id_is_contiguous_to_running_total`, generalize the body to `range(1, running_total + 1)` where `running_total` is the sum of every `CHUNK*_EXPECTED_ROWS`.
  - ADD a flagship-row test asserting **every populated field** on the chunk's best-attested entry (rule 5 — mirror `test_ihetihotep_baud_3_full_populated_row` with every dict key asserted).
  - ADD one regression test per `CHUNK<N>_CORRECTIONS` entry asserting the post-override field value (pattern: `test_baud_26_grandchild_not_listed_as_child`).
- **`transcribe.md`** — clone the existing `### Chunk 1 — entries [1]–[40]` subsection under § Chunks as a template; update the four fields it uses (physical-page range, first entry + its start page, last entry + its end page, offset-drift notes). Keep the Pipeline section untouched.

Do NOT change:
- **`README.md` § Schema** — canonical. If the handoff ever drifts from the README, the README wins.
- **`merge.py`** — `_load_agent_chunks()` already globs `agent-{tag}-*.jsonl` and unions across chunks; just run it.

---

## Schema & vocabulary (canonical elsewhere)

Rule 4 (single source of truth). Do NOT paraphrase here:

- **Schema (fields, types, null/hedge conventions):** `pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/README.md` § Schema.
- **Roles controlled vocabulary:** the `allowed` set in `test_roles_vocabulary_is_bounded` inside `pipeline/tests/test_sources_baud_ok_royal_family.py`. Authoritative. Any new role added in chunk N must be added to the test AND the extraction prompt in the same commit.
- **Chunk-1 override rationale:** `fix_rows.py` `CHUNK1_CORRECTIONS` + `merge-disagreements.txt` § "LLM-APPLIED OVERRIDES".

### Hedge conventions (six levels, increasing distance from attested fact)

1. **`"X"`** — bare value, **inscribed attestation**. Titles naming a specific king are direct attestations; do NOT hedge-wrap the named king (chunk-1 regression: baud-36).
2. **`"X (per Baud)"`** — inferred by Baud on iconographic or titular-synchronism grounds. Stronger than `(probable)`: Baud commits to the reading based on his own scholarly argument.
3. **`"X (probable)"`** — Baud's own probable attribution.
4. **`"X (?)"`** — **Baud retains a literal question-mark glyph** where a sign is legible but reading/attribution is disputed. Preserve verbatim.
5. **`"[X]"`** — Baud's **bracketed reconstruction from a lacuna** (physical damage).
6. **`null`** — NOT attested, OR Baud reports another scholar's hypothesis without endorsing it (chunk-1 resolution: baud-33's Strudwick hypothesis).

### Transliteration normalization (deterministic)

`fix_rows.py`'s `_normalise_transliteration` rewrites PDF-text-layer fallback codepoints to canonical **Unicode-5.1 Egyptological** characters (U+A723 `ꜣ`, U+A725 `ꜥ`) used by TLA / pharaoh.se / Beckerath-2nd-ed errata / modern scholarship. These codepoints did not exist when Baud 1999 was typeset; the PDF emits `ˁ` / `ɛ` / `ɜ` fallbacks that `_TRANSLIT_NORMALIZE` maps:

- `ˁ` (U+02C1) → `ꜥ` (U+A725)
- `ɛ` (U+025B) → `ꜥ` (U+A725)
- `ɜ` (U+025C) → `ꜣ` (U+A723)

Tests enforce. Carry the normalizer unchanged into chunk N. The recursive walk (dict/list/str/scalar) handles any new schema field automatically. Sanity-check chunk N's reconciled JSONL character inventory before finalizing:

```python
from collections import Counter
from pathlib import Path
p = Path('pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/reconciled.jsonl')
chars = Counter(c for c in p.read_text() if ord(c) > 127)
for c in sorted(chars, key=ord):
    print(f'U+{ord(c):04X} {c!r} count={chars[c]}')
```

If an unknown fallback codepoint appears, add it to `_TRANSLIT_NORMALIZE` in the same commit.

---

## Pipeline (per ADR-017; all stages Claude Opus 4.7)

1. **Scope chunk boundaries.** Open the PDF at the expected physical-page start/end; confirm entry-number boundaries (first and last). Update `transcribe.md` § Chunks.
2. **Split the sub-PDF** with `pypdf`. Target ~1–2 MB.
3. **Three parallel `general-purpose` subagents** Read the sub-PDF directly — no committed OCR (Baud's prose is the playbook's unsafe-to-commit-verbatim category). Each writes `raw/agent-{a,b,c}-chunk-<N>.jsonl`.
4. **Deterministic merge** via `merge.py`. `_load_agent_chunks()` unions every `raw/agent-{tag}-*.jsonl` it finds, so `reconciled.jsonl`'s row count is *cumulative*: chunk 2 produces 80 rows (40 prior + 40 new), chunk 3 produces 120, etc. Sanity-check the new chunk added exactly 40 (or the expected chunk size) rather than the raw total. merge.py itself is unchanged from chunk 1.
5. **Transliteration normalization** fires automatically when `fix_rows.py` runs.
6. **`egyptologist-reviewer` subagent pass** on the reconciled JSONL + PDF; use chunk 1's review prompt as a template, updating the page range and chunk number.
7. **Apply reviewer corrections** via new `CHUNK<N>_CORRECTIONS` list; append to `ALL_CORRECTIONS`.
8. **Tests** — expand `test_sources_baud_ok_royal_family.py` per the checklist above.
9. **Commit, push, open PR.** Stage files explicitly by name; prefix push with `TASK_LIST_UPDATED=1` when `docs/mvp-tasks.md` is in the commit.
10. **Post-PR reviews:** Gemini Code Assist auto-reviews on PR open; `/gemini review` on subsequent pushes. Arm `/watch-pr-reviews` Monitor. Spawn `code-reviewer` + `egyptologist-reviewer` subagents in parallel. Invoke `scope-accountability-enforcer` once per review batch, then prefix every `gh pr comment` / `gh api /repos/.../comments/.../replies` with `SCOPE_CHECKED=1`.

---

## Chunk-2 decision checklist (from chunk-1 review cycle)

Resolve **before** chunk-2 extraction starts to minimize backfill:

- [ ] **Add `steward of the king's children` to the roles vocab** (the test's `allowed` set) and backfill chunk-1 rows baud-10, baud-25, baud-34, baud-40 via a `CHUNK1_BACKFILL` list in `fix_rows.py`. All four rows carry `jmj-r prw msw nswt` or equivalent in `titles_from_baud`. The egyptologist-reviewer on PR #53 second pass flagged this as affecting four rows; chunk 1 deferred. Technical debt accumulates linearly; backfill is cheap. (The English gloss parallels the existing `steward of the queen`.)
- [ ] **Monument list-or-string schema decision.** baud-22 has two monuments encoded as `"1: ...; 2: ..."` in a single string. If chunk 2 surfaces more multi-monument entries, decide whether to keep the micro-convention or migrate `monument: str` → `monuments: list[str]`. Either commits both chunks (backfill migration) or commits to the micro-convention permanently. Do NOT discover the answer mid-chunk.

Anticipated OK-role vocab additions (egyptologist-reviewer-predicted; add to vocab + test when first attested, don't pre-seed):
- `priest of the king's ka` (`ḥm-kꜣ nswt`)
- `overseer of works` (`jmj-r kꜣt`)
- `inspector of priests` (`sḥḏ ḥm(w)-nṯr`)

---

## Known traps (chunk-1 battle scars — every one earned)

1. **Do NOT re-run the 3-agent extraction after a prompt fix.** Use `fix_rows.py` surgical overrides. Playbook-level rule.
2. **Role narrowing by majority vote.** One agent proposes a richer `roles` list (e.g. `ḥm-nṯr Nfr-jr-kꜣ-Rꜥ` → add `priest of the royal pyramid`); two agents omit; majority strips. Chunk-1 examples: baud-28, baud-40. Chunk-N prompt should say: *"when TITRES contains `ḥm-nṯr` or `wꜥb` of a named pyramid cult, `priest of the royal pyramid` is additive, not optional"*.
3. **Hedge-level promotion AND under-hedging.** Two directions:
   - Over-hedging: `(probable)` where Baud is reporting another scholar without endorsing → should be `null`. Chunk-1: baud-33 Strudwick.
   - Under-hedging: inscribed filiational titles (`sꜣt nswt X`, `mwt nswt X`, `ḥmt nswt X`) are **direct attestations**, not probabilities — do NOT wrap in `(probable)`. Chunk-1: baud-36 Néferkarê.
4. **Grandchild vs child.** `sꜣ` (son, direct) ≠ `sꜣ n sꜣ` / French `petit-fils` (grandson). `children_names` is direct-children only. Chunk-1: baud-26.
5. **Spouse vs mother, and half-sibling marriage.**
   - Regent mother confused with wife: baud-38 had `"Pépi II (?)"` in `spouse_names` but he is her son. Title diagnoses: is the named king her husband or her child?
   - Half-sibling marriage: `sꜣt nswt` + `ḥmt nswt` attests a woman as simultaneously daughter-of-King-A and wife-of-King-B. `father_name` and `spouse_names` name *different* kings — populate both independently. Khufu's daughters who married Khafre: `father_name = "Khufu"` AND `spouse_names = ["Khafre"]`; do not leave one slot empty.
6. **Monument enumeration.** See chunk-2 decision checklist above.
7. **Cross-reference stub rows** (baud-9 in chunk 1) have all-null structured fields and a `notes_from_baud` describing the redirect. `test_dynasty_coverage_is_ok_only` allows `null` for these — preserve the pattern.
8. **Do NOT anglicize French regnal names in kinship fields.** `Snéfrou`, `Pépi Iᵉʳ`, `Téti`, `Merenrê`, `Niouserrê`, `Djedkarê`, `Ounas`, `Rêkhaef`, etc. stay verbatim in `father_name` / `spouse_names` / `children_names` / `date_attested`. Normalization against pharaoh.se is Phase A's job. `name_anglicised` is the only field carrying an English form.
9. **Physical PDF pages vs Baud's printed pages.** `source_citation.pdf_pages` records PDF-internal physical pages, NOT Baud's printed pages. Per ADR-017 § "Cite physical pages". Baud vol. 2 has continuous pagination with vol. 1 (printed pp. 395–675), so printed-to-physical drift is not cleanly computable — all the more reason to stick with physical.
10. **Agent JSONL + sub-PDF stay under `raw/` and are gitignored.** `tests/test_structure.py::test_no_tracked_files_under_raw_for_phase0_sources` fails CI if a non-`.gitkeep` file under `raw/` is committed.
11. **`.claude/agent-memory/` pollution.** `code-reviewer` / `egyptologist-reviewer` subagents write memory files there during a review cycle. These appear untracked. **Never `git add -A` / `git add .`** — always stage by name.
12. **Pre-push hook requires `TASK_LIST_UPDATED=1`** when `docs/mvp-tasks.md` is in the commit.
13. **Deterministic JSONL: `sort_keys=True`.** Both `merge.py` and `fix_rows.py` write `reconciled.jsonl` with `json.dumps(..., sort_keys=True)`. Without it, dict-iteration-order reshuffles produce spurious diffs on every re-run. Do not "simplify" this away.

---

## After chunk N merges

1. Log the human Egyptologist sign-off sample in `human-review-<YYYY-MM-DD>-chunk<N>.md` per ADR-017 step 6 (pending across all chunks until a credentialed Egyptologist signs off).
2. Update this handoff: chunk N's actual page range, row count, any new traps surfaced. Chunk N+1 inherits.
3. Start chunk N+1 in a fresh PR.

---

## Memory pointers

- User-feedback rules: `feedback_autonomy.md`, `feedback_branch_pr.md`, `feedback_push_after_commit.md`, `feedback_pr_review_replies.md`, `feedback_ci_failures.md`, `feedback_gemini_review.md`, `feedback_pr_reviewers.md`.
- Constitutional rules 1, 2, 4, 5, 6, 12 apply hardest — scholarly traceability, loud failures, single source of truth, value-assertion tests, raw data preservation, no-excusing-existing-violations.
- `/watch-pr-reviews` for review monitoring after each push.
