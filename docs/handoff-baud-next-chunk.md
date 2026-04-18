# Handoff — Baud 1999 Old Kingdom royal family, chunk 2+

**Written 2026-04-18.** Picks up after chunk 1 merged at PR #53 (commit `00c95cb`). Pick this up when the user asks to start chunk 2 (entries `[41]`–`[80]`) or any later chunk of the Baud 1999 Old-Kingdom prosopography transcription.

Baud is the OK analogue of Dodson-Hilton. Per `docs/mvp-tasks.md`: "without it, OK queen/consort coverage will be thin while NK/LP is dense, producing an uneven authority. Required, not optional." D&H covers the earlier chapters too, but D&H's OK coverage is explicitly flagged as weaker; Baud is the preferred OK source.

Read `docs/playbook-phase-0-ocr-transcription.md` § "Multi-chunk source pattern" first. Dodson-Hilton (`sources/dodson-hilton-queens/`) and Baud chunk 1 (`sources/baud-1999-ok-royal-family/`) are the reference implementations. This handoff supersedes the playbook where they disagree.

---

## Source

**Citation.** Michel Baud, *Famille royale et pouvoir sous l'Ancien Empire égyptien*, Bibliothèque d'Étude 126, Institut Français d'Archéologie Orientale, Cairo, 1999. Two volumes. Vol. 1 is analytical (out of scope). Vol. 2 is the *Corpus* — 282 numbered entries `[1]`–`[282]`, alphabetical by Egyptian transliteration (not by dynasty).

**PDF.** `proprietary/books/Baud 1999 - Famille royale AE vol 2.pdf` (gitignored). SHA-256 `8768536a13fb5428d8ec7fbd96263d028aabb557a5411e7f796cad99ed6881cb`, pinned in `pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/README.md` and `transcribe.md`. 296 physical pages.

---

## State as of 2026-04-18

- ✅ **Chunk 1** (`[1]`–`[40]`, physical pp. 11–49) — 40 rows merged in PR #53. 22 pytest assertions. 10 `fix_rows.py` LLM-APPLIED OVERRIDES (8 first-pass + 2 second-pass egyptologist-reviewer corrections) logged under `NOT HUMAN-VALIDATED`. Pipeline CI + web CI green on merge.
- 🔜 **Chunks 2–7** — pending. Chunk size remains ~40 entries per chunk (7 PRs total).
- **Related cleanup tracked elsewhere:** Issue #54 — the `sources/dodson-hilton-queens/` merge.py + fix_rows.py carry the same three bugs fixed in chunk 1 (normalization bypass, idempotence, per-row field set). Not blocking any Baud chunk; fix when D&H earlier-chapters chunks are touched.

---

## Chunk plan

| Chunk | Entries | Status | Tentative pages |
|---|---|---|---|
| 1 | `[1]`–`[40]` | ✅ merged (PR #53) | physical pp. 11–49 |
| 2 | `[41]`–`[80]` | 🔜 next | physical pp. 49–~90 (scope at start) |
| 3 | `[81]`–`[120]` | pending | TBD |
| 4 | `[121]`–`[160]` | pending | TBD |
| 5 | `[161]`–`[200]` | pending | TBD |
| 6 | `[201]`–`[240]` | pending | TBD |
| 7 | `[241]`–`[282]` | pending | TBD |

**Density observed in chunk 1:** ~1 entry per printed page average, so ~40 entries = ~40 physical pages per chunk. Verify density stays consistent when scoping chunk 2; Baud's entries grow longer in the Dyn-4 and Dyn-6 dense sections.

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
- `fix_rows.py` — APPEND `CHUNK<N>_CORRECTIONS: list[tuple[str, str, object, str]] = [...]` and concatenate into `SPOT_CORRECTIONS`. Do not edit chunk 1's corrections.
- `tests/test_sources_baud_ok_royal_family.py` — bump `CHUNK1_EXPECTED_ROWS` (rename to running-total) and `test_baud_id_covers_1_to_40` accordingly; add flagship-row tests for the chunk's best-attested entry; add regression tests for every new `fix_rows.py` override.

Do NOT change:
- `README.md` schema section — it's stable and drives the test suite. (The chunk-1 additions of `baud_refs`, `service_personnel`, `monument`/`localisation`/`pm_ref` splits are the schema.)
- `merge.py` — `_load_agent_chunks()` already globs `agent-{tag}-*.jsonl` and unions across chunks. Running merge.py after chunk 2's agents finish Just Works.
- `transcribe.md` — add a chunk-2 subsection under § Chunks; keep the Pipeline section untouched.

---

## Schema (stable — do not change)

See `pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/README.md` § Schema. Summary of fields:

- `baud_id` (`"baud-N"`, flat numeric)
- `name_egyptian` (verbatim transliteration, dots/hyphens preserved)
- `name_anglicised` (conventional English form where one exists, null otherwise)
- `service_personnel` (bool, from `*` suffix on headword — stripped from name)
- `monument` / `localisation` / `pm_ref` (three separate fields from Baud's header block `(b)` and `(c)`)
- `date_attested` (Baud's `(d)` line verbatim)
- `dynasty` (`"3"`..`"6"`, or range like `"4-5"`, or null for cross-ref stubs)
- `sub_period` (explicit sub-period string or null)
- `baud_refs` (dict of lowercase author → printed reference string from Baud's `(e)` line: baer / strudwick / seipel / harpur / troy / schmitz)
- `titles_from_baud` (verbatim list from TITRES rubric)
- `roles` (controlled vocabulary — see below)
- `father_name` / `mother_name` / `spouse_names` / `children_names` (hedge-preserving)
- `tomb` (tomb designation or null)
- `notes_from_baud` (≤ 2-sentence fragment, null by default — NOT full paragraphs per rights policy)
- `source_citation` (dict with `source` / `pdf_pages` / `edition`)

### Roles controlled vocabulary

Chunk-1-seeded (enforced by `test_roles_vocabulary_is_bounded`):
```
king, queen, king's mother, king's wife, king's son, king's daughter,
king's son-in-law, king's eldest son of his body, vizier,
priest of the royal pyramid, priest of the king's mother,
priest of the king's wife, priest of the king, steward of the queen,
sem priest, overseer of the treasury of pr-ꜥꜣ,
overseer of scribes of pr-ꜥꜣ
```

**Known gap:** `steward of the king's children` (for `jmj-r prw msw nswt` / `jmj-r pr jnꜥwt nwt msw nswt`). Chunk 1's baud-10/25/34/40 all have an admin king's-children-household title that doesn't map. **Chunk 2 SHOULD either add this role to the vocab and backfill the four chunk-1 rows via a new `CHUNK1_BACKFILL` list in `fix_rows.py`, or document the continued deferral in README § "Known gaps".** Either is acceptable; not both.

### Hedge conventions (Baud-specific)

- `"X (probable)"` — Baud's own probable attribution.
- `"[X]"` — Baud's bracketed reconstruction from a lacuna.
- `"X (per Baud)"` — field value asserted by Baud's scholarly judgment (iconography / titular synchronism), not physical attestation.
- `null` — NOT attested by Baud, or Baud reports another scholar's hypothesis without endorsing it. (Chunk 1 resolved baud-33's Strudwick hypothesis to `null`; two reviewer passes conflicted before settling there.)

### Transliteration normalization (deterministic)

`fix_rows.py`'s `_normalise_transliteration` rewrites the PDF-text-layer fallback codepoints to canonical IFAO:
- `ˁ` (U+02C1) → `ꜥ` (U+A725)
- `ɛ` (U+025B) → `ꜥ` (U+A725)
- `ɜ` (U+025C) → `ꜣ` (U+A723)

Tests `test_name_egyptian_uses_canonical_translit` + `test_titles_from_baud_uses_canonical_translit` enforce. Carry this unchanged into chunk 2 — no new codepoints observed in chunk 1, but re-check the character inventory of the new chunk's `reconciled.jsonl` before finalizing (the inventory script is in the PR-53 history if needed).

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
3. **Hedge-level promotion.** `(probable)` vs `(per Baud)` vs `null` depend on whether Baud is asserting, judging, or reporting another scholar. Baud-33 had three options and two reviewers disagreed. The resolution was `null` (source reports Strudwick, does not endorse). Preserve this nuance in chunk 2's prompt.
4. **Grandchild vs child.** baud-26's Sꜥnḫ-n-Ptḥ was promoted to `children_names` but is a `petit-fils` (grandchild). `children_names` is direct-children only.
5. **Spouse vs mother.** baud-38 had "Pépi II (?)" in `spouse_names` but he is her son. Mother-of-king regent roles get confused with wife-of-king roles. Both roles are legitimate; the distinction is "is the king her husband (spouse) or her child (regent)?" — titles give the answer.
6. **Monument enumeration.** baud-22 has two monuments numbered "1:" / "2:" in Baud's header. The current schema carries them in a single string field with `"1: ...; 2: ..."` micro-convention. A schema evolution to `monuments: list[str]` is a reasonable chunk-2 planning question — decide once, touch all chunks (would require a backfill).
7. **Cross-reference stub rows** (baud-9 in chunk 1) have all-null structured fields and a `notes_from_baud` describing the redirect. The `test_dynasty_coverage_is_ok_only` test now accepts `null` for these — preserve the pattern.
8. **Agent JSONL files stay under `raw/` and are gitignored.** `tests/test_structure.py::test_no_tracked_files_under_raw_for_phase0_sources` will fail CI if a non-`.gitkeep` file under `raw/` is committed. Stage by filename, never `git add -A`.
9. **Pre-push hook requires `TASK_LIST_UPDATED=1`** when `docs/mvp-tasks.md` is in the commit.

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
