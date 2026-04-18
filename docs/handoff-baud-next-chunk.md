# Handoff — Baud 1999 Old Kingdom royal family, chunk 2+

**Written 2026-04-17.** Picks up after chunk 1 merged at PR #53 (commit `00c95cb`). Pick this up when the user asks to start chunk 2 (entries `[41]`–`[80]`) or any later chunk of the Baud 1999 Old-Kingdom prosopography transcription.

Baud is the OK prosopographic counterpart to D&H's NK/LP queen coverage — deeper per-entry (full titulary, monument list, scholarly refs) but narrower in scope (OK only). Expect denser extraction than D&H: each Baud entry has a header block (a–e) plus up to four prose rubrics (TITRES / DATATION / PARENTÉ / DIVERS), vs D&H's compact Brief Lives paragraph. Per `docs/mvp-tasks.md`: "without it, OK queen/consort coverage will be thin while NK/LP is dense, producing an uneven authority. Required, not optional." D&H covers the earlier chapters too, but D&H's OK coverage is explicitly flagged as weaker; Baud is the preferred OK source.

Read `docs/playbook-phase-0-ocr-transcription.md` § "Multi-chunk source pattern" first. Dodson-Hilton (`sources/dodson-hilton-queens/`) and Baud chunk 1 (`sources/baud-1999-ok-royal-family/`) are the reference implementations. This handoff supersedes the playbook where they disagree.

---

## Source

**Citation.** Michel Baud, *Famille royale et pouvoir sous l'Ancien Empire égyptien*, Bibliothèque d'Étude 126, Institut Français d'Archéologie Orientale, Cairo, 1999. Two volumes. Vol. 1 is analytical (out of scope). Vol. 2 is the *Corpus* — 282 numbered entries `[1]`–`[282]`, alphabetical by Egyptian transliteration (not by dynasty).

**PDF.** `proprietary/books/Baud 1999 - Famille royale AE vol 2.pdf` (gitignored). SHA-256 `8768536a13fb5428d8ec7fbd96263d028aabb557a5411e7f796cad99ed6881cb`, pinned in `pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/README.md` and `transcribe.md`. 296 physical pages.

---

## State as of 2026-04-18

- ✅ **Chunk 1** (`[1]`–`[40]`, physical pp. 11–49) — 40 rows merged in PR #53. 22 pytest test functions (65 asserts). 10 `fix_rows.py` LLM-APPLIED OVERRIDES (8 first-pass + 2 second-pass egyptologist-reviewer corrections) logged under `NOT HUMAN-VALIDATED`. Pipeline CI + web CI green on merge.
- 🔜 **Chunks 2–7** — pending. Chunk size remains ~40 entries per chunk (7 PRs total).
- **Related cleanup tracked elsewhere:** Issue #54 — the `sources/dodson-hilton-queens/` merge.py + fix_rows.py carry the same three bugs fixed in chunk 1 (normalization bypass, idempotence, per-row field set). Not blocking any Baud chunk; fix when D&H earlier-chapters chunks are touched.

---

## Chunk plan

| Chunk | Entries | Status | Tentative pages |
|---|---|---|---|
| 1 | `[1]`–`[40]` | ✅ merged (PR #53) | physical pp. 11–49 (incl. Corpus methodological intro pp. 11–16) |
| 2 | `[41]`–`[80]` | 🔜 next | physical pp. 49–~83 (scope at start; entry `[41]`'s headword starts at the bottom of p. 49 and continues onto p. 50 — **include p. 49** in the chunk-2 sub-PDF so extractors see the `[41]` headword even though chunk 1 also covered p. 49. One-page boundary overlap is the standard multi-chunk extraction convention) |
| 3 | `[81]`–`[120]` | pending | TBD |
| 4 | `[121]`–`[160]` | pending | TBD |
| 5 | `[161]`–`[200]` | pending | TBD |
| 6 | `[201]`–`[240]` | pending | TBD |
| 7 | `[241]`–`[282]` | pending | TBD |

**Density observed in chunk 1:** 40 entries across physical pp. 11–49 = 39 physical pages, but 6 of those are the Corpus methodological intro (pp. 11–16) that chunk 1 alone bundles. The actual entry density is ~40 entries / 33 content pages ≈ 1.2 entries per content page. **Chunks 2+ plan on ~33–35 physical pages per 40 entries** (no intro overhead). Verify density stays consistent when scoping — Baud's entries grow longer in the Dyn-4 and Dyn-6 dense sections, so later chunks may drift to 40+ pages.

Ship one chunk per PR. Do NOT bundle.

---

## Scaffolding — extend, do not rebuild

`pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/` already exists on `main`. For the next chunk, ADD these files alongside the existing ones:

- `prompt-chunk-<N>.md` — clone from `prompt-chunk-1.md`, update:
  - entry-number boundaries (`[41]`–`[80]` for chunk 2)
  - physical-page range
  - per-chunk hazards (the prior chunk's review cycle often flags new ones)
  - expected-row-count sanity bound
- `raw/source-chunk-<N>.pdf` — split with `pypdf`, gitignored under `raw/*`
- `raw/agent-{a,b,c}-chunk-<N>.jsonl` — 3 parallel extractions, gitignored
- `fix_rows.py` — APPEND a new `CHUNK<N>_CORRECTIONS: list[tuple[str, str, object, str]] = [...]` constant alongside every existing chunk constant (do not edit prior lists). Chunk 2 replaces the current singleton (`SPOT_CORRECTIONS: list[tuple[str, str, object, str]] = CHUNK1_CORRECTIONS`) with a list-based aggregation to keep later chunks maintainable:
  ```python
  ALL_CORRECTIONS = [CHUNK1_CORRECTIONS, CHUNK2_CORRECTIONS]
  SPOT_CORRECTIONS = sum(ALL_CORRECTIONS, [])  # flatten
  ```
  Each subsequent chunk appends its constant to `ALL_CORRECTIONS` (single-line edit). Dropping any chunk from the list silently destroys its audit trail; a test that iterates module-level `CHUNK*_CORRECTIONS` attributes and asserts each is present in `ALL_CORRECTIONS` catches the omission.
- `tests/test_sources_baud_ok_royal_family.py`:
  - ADD a new `CHUNK<N>_EXPECTED_ROWS = 40` module-level constant next to every existing chunk-count constant. Do NOT rename the existing chunk constants.
  - UPDATE `test_row_count` to the list-based aggregation `assert len(_rows()) == sum([CHUNK1_EXPECTED_ROWS, CHUNK2_EXPECTED_ROWS, ...])` — same maintainability reason as the `fix_rows.py` pattern. Chunk 3 appends `CHUNK3_EXPECTED_ROWS` to the list, etc. A parallel omission-catch test (iterate `CHUNK*_EXPECTED_ROWS` module attributes and assert each is summed) prevents silently dropped counts.
  - RENAME `test_baud_id_covers_1_to_40` → `test_baud_id_is_contiguous_to_running_total` and generalize its body to `range(1, running_total + 1)` where `running_total` is the sum of every `CHUNK<N>_EXPECTED_ROWS`.
  - ADD a new flagship-row test asserting **every populated field** on the chunk's best-attested entry (rule 5 — follow the pattern of `test_ihetihotep_baud_3_full_populated_row` with every dict key asserted, not a 5-field smoke test).
  - ADD a regression test per `CHUNK<N>_CORRECTIONS` entry that asserts the post-override field value (same pattern as `test_baud_26_grandchild_not_listed_as_child`).

Do NOT change:
- `README.md` schema section — it's stable and drives the test suite. (The chunk-1 additions of `baud_refs`, `service_personnel`, `monument`/`localisation`/`pm_ref` splits are the schema.)
- `merge.py` — `_load_agent_chunks()` already globs `agent-{tag}-*.jsonl` and unions across chunks. Running merge.py after chunk 2's agents finish Just Works.
- `transcribe.md` — clone the existing `### Chunk 1 — entries [1]–[40]` subsection under § Chunks as a template, updating the four fields it uses: physical-page range, first entry + its start page, last entry + its end page, and offset-drift notes. Keep the Pipeline section untouched.

---

## Schema & vocabulary (canonical elsewhere)

Rule-4 discipline: every fact lives in one place. This handoff does NOT duplicate the schema or the role vocabulary. Read these once and refer back, don't paraphrase here:

- **Schema (fields, types, null/hedge conventions):** `pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/README.md` § Schema. Canonical — if the README and this handoff ever drift, the README wins.
- **Roles controlled vocabulary:** enforced by `test_roles_vocabulary_is_bounded` in `pipeline/tests/test_sources_baud_ok_royal_family.py`. The test's `allowed` set is the authoritative enumeration. If chunk 2 adds new roles, update both the test and the extraction prompt in the same commit.
- **Chunk-1 override rationale + scholarly provenance:** `pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/fix_rows.py` `CHUNK1_CORRECTIONS` list + `merge-disagreements.txt` § "LLM-APPLIED OVERRIDES".

### Steward-of-the-king's-children vocab gap (chunk-2 decision)

Chunk 1's baud-10, baud-25, baud-34, baud-40 all carry `jmj-r prw msw nswt` ("overseer of the houses of the royal children") or equivalent in `titles_from_baud` but have no matching role code in the chunk-1 seeded vocab. The PR-53 egyptologist-reviewer second pass flagged this as affecting four rows; chunk 1 deferred the fix.

**Strongly recommended for chunk 2:** (a) add `steward of the king's children` to the controlled vocab (the test's `allowed` set) in the same commit as the prompt update, (b) apply it to attested chunk-2 rows, and (c) add a `CHUNK1_BACKFILL` list in `fix_rows.py` that applies the role to baud-10/25/34/40. Carrying the four-row under-coverage forward into chunks 2–7 accumulates technical debt; the backfill is cheap and scholarly-defensible. Both adding the vocab AND documenting the backfill under README § "Known gaps" is the right move — not either/or.

The English gloss `steward of the king's children` parallels the existing `steward of the queen` ("`jmj-r pr` + queen-name" pattern); internally consistent. Most Anglophone literature (Strudwick, Jones) would render `jmj-r pr(w)` as "overseer of the house(s)"; the "steward" variant is this authority's house style.

### Additional OK-role vocab additions chunks 2–7 are likely to surface

Egyptologist-reviewer-anticipated (not attested in chunk 1, but OK-ubiquitous):

- `priest of the king's ka` (`ḥm-kꜣ nswt`) — distinct from `priest of the king`; household/mortuary role often held by non-royal dependents.
- `overseer of works` (`jmj-r kꜣt`) — OK-central for royal sons / viziers.
- `inspector of priests` (`sḥḏ ḥm(w)-nṯr`) — second-tier cult role.

Add to vocab + test when first attested; don't pre-seed.

### Hedge conventions (Baud-specific)

Six levels, in increasing distance from attested fact:

- `"X"` — bare value, **inscribed attestation** (e.g. title `mwt nswt Nfr-kꜣ-Rꜥ` → `children_names = ["Néferkarê"]`). Titles naming a specific king are direct attestations; do NOT hedge-wrap the named king. chunk-1 regression: baud-36.
- `"X (per Baud)"` — field value inferred by Baud on iconographic or titular-synchronism grounds (not direct inscribed attestation). Stronger than `(probable)`: Baud commits to the reading based on his own scholarly argument.
- `"X (probable)"` — Baud's own probable attribution (plausible, well-supported, but not inscribed).
- `"X (?)"` — **Baud retains a literal question-mark glyph** where a sign is legible but the reading/attribution is disputed. Distinct from `(probable)` (Baud-endorsed) and `[X]` (lacuna). Preserve Baud's `(?)` verbatim in the value string; do not promote to `(probable)` or demote to `null`. Chunk 1 saw this pattern in PARENTÉ rubrics flagged "peu sûr" / "lecture incertaine".
- `"[X]"` — Baud's **bracketed reconstruction from a lacuna** (the sign itself is physically damaged or missing).
- `null` — NOT attested by Baud at all, OR Baud reports another scholar's hypothesis without endorsing it. Chunk 1 resolved baud-33's Strudwick hypothesis to `null` after two reviewer passes conflicted (first pass: `(per Baud)`, second pass: Baud is reporting Strudwick's guess, not asserting).

### Transliteration normalization (deterministic)

`fix_rows.py`'s `_normalise_transliteration` rewrites the PDF-text-layer fallback codepoints to the canonical **Unicode-5.1 Egyptological** characters (U+A723 `ꜣ` aleph, U+A725 `ꜥ` ayin) used by TLA, pharaoh.se, Beckerath 2nd-ed errata, and current scholarship. These codepoints did not exist when Baud 1999 was typeset (pre-Unicode-5.1 / 2008), so Baud's printed form uses different glyphs and the PDF text layer extracts them as `ˁ` / `ɛ` / `ɜ` fallbacks:

- `ˁ` (U+02C1 MODIFIER LETTER REVERSED GLOTTAL STOP) → `ꜥ` (U+A725)
- `ɛ` (U+025B LATIN SMALL LETTER OPEN E) → `ꜥ` (U+A725)
- `ɜ` (U+025C LATIN SMALL LETTER REVERSED OPEN E) → `ꜣ` (U+A723)

Tests `test_name_egyptian_uses_canonical_translit` + `test_titles_from_baud_uses_canonical_translit` enforce. Carry the normalizer unchanged into chunk 2. Re-check the character inventory of the new chunk's `reconciled.jsonl` before finalizing — new OCR fallbacks do occasionally appear. Quick recipe:

```python
from collections import Counter
from pathlib import Path
p = Path('pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/reconciled.jsonl')
chars = Counter(c for c in p.read_text() if ord(c) > 127)
for c in sorted(chars, key=ord):
    print(f'U+{ord(c):04X} {c!r} count={chars[c]}')
```

If an unknown codepoint appears, add it to `_TRANSLIT_NORMALIZE` in the same commit as the chunk-2 extraction lands.

---

## Pipeline

Per ADR-017 + playbook. All stages on Claude Opus 4.7.

1. **Scope chunk boundaries.** Open the PDF at the expected physical-page start/end and confirm entry-number boundaries. Update `transcribe.md` § Chunks.
2. **Split the sub-PDF** with `pypdf` (same command as chunk 1's scaffolding scripts). 1.77 MB is a reasonable size target; 40 pages is well under the 100 MB Read-tool limit.
3. **Three parallel `general-purpose` subagents** Read the sub-PDF directly. No committed OCR — Baud's prose is the playbook's unsafe-to-commit-verbatim category. Each writes `raw/agent-{a,b,c}-chunk-<N>.jsonl`.
4. **Deterministic merge** via `merge.py`. Expect 40 rows with every row having every schema field. No changes to `merge.py` should be necessary.
5. **`fix_rows.py` transliteration normalization** fires automatically on the new chunk's rows.
6. **`egyptologist-reviewer` subagent pass** on the reconciled + PDF. Feed it the chunk-1 reviewer prompt as a template — update the chunk number and page range.
7. **Apply reviewer corrections** via new `CHUNK<N>_CORRECTIONS` list.
8. **Tests** — expand `test_sources_baud_ok_royal_family.py`. Add ≥ 1 flagship-row assertion with every populated field (rule 5). Add ≥ 1 regression test per `fix_rows.py` override.
9. **Commit, push, open PR.** Stage files explicitly by name (never `git add -A`). Prefix push with `TASK_LIST_UPDATED=1` when `docs/mvp-tasks.md` is in the commit.
10. **Post-PR reviews:** Gemini Code Assist auto-reviews on PR open; post `/gemini review` on subsequent pushes. Arm `/watch-pr-reviews` Monitor. Spawn `code-reviewer` + `egyptologist-reviewer` subagents. Prefix every `gh pr comment` / `gh api /repos/.../comments/.../replies` with `SCOPE_CHECKED=1` after invoking `scope-accountability-enforcer` once per review batch.

---

## Known traps (chunk 1 battle scars)

1. **Do NOT re-run the 3-agent extraction after a prompt fix.** Covered in the playbook. Use `fix_rows.py` surgical overrides.
2. **Role narrowing by majority vote.** When one agent proposes a richer `roles` list from a pyramid-cult title (e.g. `ḥm-nṯr Nfr-jr-kꜣ-Rꜥ` → add `priest of the royal pyramid`) and two agents omit it, the majority strips it. Chunk 1 hit this at baud-28 and baud-40. **Chunk 2 prompt should add: "when TITRES contains `ḥm-nṯr` or `wꜥb` of a named pyramid cult, `priest of the royal pyramid` is additive, not optional."**
3. **Hedge-level promotion AND under-hedging.** Two directions of failure:
   - Over-hedging: `(probable)` where Baud actually reports another scholar's hypothesis without endorsing → should be `null`. Chunk-1 example: baud-33's Strudwick hypothesis.
   - Under-hedging: **inscribed filiational titles are direct attestations, NOT probabilities.** If a title reads `sꜣt nswt Khufu` / `mwt nswt Neferkare` / `ḥmt nswt Pepi`, the named king's filiation is attested — do NOT wrap in `(probable)`. Chunk-1 example: baud-36's Néferkarê, initially hedged as `"Néferkarê (probable)"` by majority-vote, reviewer-corrected to bare `"Néferkarê"`.
4. **Grandchild vs child.** baud-26's Sꜥnḫ-n-Ptḥ was promoted to `children_names` but is a `petit-fils` (grandchild). `children_names` is direct-children only. OK filiation language distinguishes `sꜣ` (son, direct) from `sꜣ n sꜣ` / French `petit-fils` (grandson).
5. **Spouse vs mother, and half-sibling marriage.** Two related OK-specific pitfalls:
   - Regent mother confused with wife. baud-38 had `"Pépi II (?)"` in `spouse_names` but he is her son (she was regent). Distinction: is the named king her husband (spouse) or her child (regent)? Titles give the answer.
   - **Half-sibling marriage and generational collapse.** A woman titled `sꜣt nswt` + `ḥmt nswt` is simultaneously daughter-of-King-A and wife-of-King-B (her brother/half-brother). `father_name` and `spouse_names` name *different* kings — populate both independently. Khufu's daughters who married Khafre have `father_name = "Khufu"` AND `spouse_names = ["Khafre"]`; do NOT leave one slot empty under the assumption a royal woman can only have a king in one role.
6. **Monument enumeration.** baud-22 has two monuments numbered "1:" / "2:" in Baud's header. The current schema carries them in a single string field with `"1: ...; 2: ..."` micro-convention. A schema evolution to `monuments: list[str]` is a reasonable chunk-2 planning question — decide BEFORE chunk-2 extraction starts to minimize backfill complexity.
7. **Cross-reference stub rows** (baud-9 in chunk 1) have all-null structured fields and a `notes_from_baud` describing the redirect. The `test_dynasty_coverage_is_ok_only` test now accepts `null` for these — preserve the pattern.
8. **Do not anglicize French regnal names in kinship fields.** `Snéfrou`, `Pépi Iᵉʳ`, `Téti`, `Merenrê`, `Niouserrê`, `Djedkarê`, `Ounas`, `Rêkhaef`, etc. stay verbatim in `father_name` / `spouse_names` / `children_names` / `date_attested`. Normalization against pharaoh.se's Conventional English Display Form is Phase A's job, not chunk extraction's. `name_anglicised` is the only field that carries an English form.
9. **Physical PDF pages vs Baud's printed pages.** `source_citation.pdf_pages` records PDF-internal physical pages (chunk 1: `"11-49"`), NOT Baud's printed pages (chunk 1 would be `"395-432"` printed). Per ADR-017 § "Cite physical pages, not printed pages" — physical page numbers are reproducible across any copy of the PDF; printed pages drift from physical pages at multi-volume boundaries. Baud vol. 2 has continuous pagination with vol. 1 (printed pp. 395–675), so printed-to-physical drift is not cleanly computable — another reason to stick with physical.
10. **Agent JSONL + sub-PDF stay under `raw/` and are gitignored.** `tests/test_structure.py::test_no_tracked_files_under_raw_for_phase0_sources` fails CI if any non-`.gitkeep` file under `raw/` is committed.
11. **`.claude/agent-memory/` pollution.** Running `code-reviewer` / `egyptologist-reviewer` subagents writes memory files under `.claude/agent-memory/`. These appear as untracked files after a review cycle. They are NOT project files. Always stage explicitly by filename (`git add <specific paths>`), NEVER `git add -A` or `git add .`.
12. **Pre-push hook requires `TASK_LIST_UPDATED=1`** when `docs/mvp-tasks.md` is in the commit.
13. **Deterministic JSONL: `sort_keys=True`.** `merge.py` and `fix_rows.py` both write `reconciled.jsonl` with `json.dumps(..., sort_keys=True)`. Without sorted keys, Python's dict iteration order makes the file re-shuffle on every re-run even when values are identical — spurious diffs pollute the PR and review. Per playbook step 10; don't "simplify" this away.
14. **Transliteration normalizer covers new field shapes recursively.** `_normalise_transliteration` walks `dict` / `list` / `str` / scalar recursively, so new schema fields in chunk 2 are handled automatically. Spot-check: after chunk-2's first merge, run the character-inventory recipe above against `reconciled.jsonl` and confirm no fallback codepoints (U+02C1, U+025B, U+025C) survived the normalizer pass.

---

## After chunk N merges

1. Log the human Egyptologist sign-off sample in `human-review-<YYYY-MM-DD>-chunk<N>.md` per ADR-017 step 6.
2. Update this handoff doc with chunk N's actual page range, row count, and any new traps surfaced. Future chunks inherit those refinements.
3. Start chunk N+1 in a fresh PR.

---

## Memory pointers

- User feedback rules relevant to this work: `feedback_autonomy.md`, `feedback_branch_pr.md`, `feedback_push_after_commit.md`, `feedback_pr_review_replies.md`, `feedback_ci_failures.md`, `feedback_gemini_review.md`, `feedback_pr_reviewers.md`.
- Constitutional rules 1, 2, 5, 6, 12 are the ones this work stresses hardest — scholarly traceability, loud failures, value-assertion tests, raw data preservation, no-excusing-existing-violations.
- `/watch-pr-reviews` skill for review monitoring after each push.
