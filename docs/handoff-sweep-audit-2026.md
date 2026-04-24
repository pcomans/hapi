# Phase-0 Authority Sweep Audit - 2026-04-23

Retrospective sweep across all committed directories in `pipeline/pipeline/authority/sources/`.
Reviewer-set decisions: all book/transcription sources received code-reviewer and egyptologist-reviewer coverage; `pharaoh-se` and `wikipedia-ptolemaic` received both because ruler-attestation correctness matters; `idai-gazetteer` received code-reviewer only because it is a geographic gazetteer source.

**Scope decisions actioned after the sweep (same day):** `holbl-2001-argead` and `wikipedia-ptolemaic` were **dropped** rather than fixed. Hölbl's reconciled source was never on `main` (PR #74 was closed after egyptologist review confirmed pharaoh.se already covers the three Argead rulers with full Beckerath titulary); the sweep flagged it as P1 only because the stale directory remained on disk. Wikipedia-Ptolemaic's coverage is redundant with pharaoh.se + Leprohon Ch X chunk 14, so fixing the Rule-1 provenance gap (no committed URLs / revision IDs / raw snapshots) was not worth the effort. The 5 Ptolemaic queens unique to Wikipedia-Ptolemaic (Cleopatra III/V/VII, Berenice III/IV) are now a pending gap scheduled for D&H Ch 5 House-of-Ptolemy. See `docs/mvp-tasks.md` for the scope changes.

## Source Coverage

| Source | Reviewers | P1 | P2 | P3 | Key issues |
|---|---:|---:|---:|---:|---|
| `baud-1999-ok-royal-family` | code + egyptologist | 2 | 4 | 5 | Missed over-asserted eldest-son roles; `baud-126` child assigned to wrong mother; chunks 3-7 under-pinned; stale README/schema docs. |
| `dodson-hilton-queens` | code + egyptologist | 0 | 3 | 3 | `fix_rows.py` loses idempotent override audit trail; arbitrary correction fields can create schema keys; Founders dynasty refinement remains inconsistent. |
| `hkw-chronology-2006` | code + egyptologist | 0 | 5 | 3 | Original 203 rows lack value-pinning tests; orphan dynasty invariant incomplete; README still describes Scorpion I as Dyn-0; prenomen/source-scope drift. |
| ~~`holbl-2001-argead`~~ | code + egyptologist | 3 | 4 | 4 | **Dropped 2026-04-23** — pharaoh.se already covers the three Argead rulers with full Beckerath titulary; stale directory (never on `main` after PR #74 closed) deleted. |
| `idai-gazetteer` | code only | 0 | 3 | 0 | Retrieval date regenerated from wall clock; supplementary gazetteer bypass list not fully enforced; mapped fields have thin canary coverage. |
| `kitchen-tipe` | code + egyptologist | 1 | 5 | 3 | Source artifacts/OCR not committed; singleton rows admitted; row tests are selective; missing Smendes-in-N row; normalized date fields encode a printed contradiction. |
| `leprohon-2013-titulary` | code + egyptologist | 2 | 4 | 3 | `stage_suffix` conflates titulary stages with distinct queen-consorts; singleton rows admitted; Leprohon vs alias provenance mixed; row-level absence notes remain in name notes. |
| `pharaoh-se` | code + egyptologist | 3 | 3 | 3 | Name-card parser corrupts titulary fields; Roman reign dates are shifted/contradict page evidence; CE single-year dates mis-signed as BCE; missing pages only warn. |
| `porter-moss-theban-necropolis` | code + egyptologist | 0 | 4 | 3 | Chunk-1/2 tests are representative, not full value pins; stale chunk-7 prompt guidance conflicts with fixed data; QV unnumbered tomb scope and KV46 role fidelity. |
| `ryholt-1997-sip` | code + egyptologist | 1 | 4 | 5 | No-majority field votes choose arbitrary agent-order winner; singleton rows admitted; `15.3` has markup/lost clause; several tests use weak or tolerant assertions. |
| `shaw-ohae-2000` | code + egyptologist | 0 | 4 | 3 | Row citations omit pages supporting Naqada subperiods; ch. 10 note imports uncited subperiod dates; title/provenance normalization drift; partial value pinning. |
| ~~`wikipedia-ptolemaic`~~ | code + egyptologist | 1 | 6 | 4 | **Dropped 2026-04-23** — coverage redundant with pharaoh.se + Leprohon Ch X chunk 14; fixing the Rule-1 provenance gap wasn't worth the effort. 5 Ptolemaic queens unique to this source (Cleopatra III/V/VII, Berenice III/IV) scheduled for D&H Ch 5. |

## Cross-Cutting Patterns

1. **Rule 1 provenance gaps recur across source types.** Kitchen lacks committed/reproducible authority artifacts; Shaw and HKW have row facts or docs pointing to incomplete/incorrect source coverage. (Hölbl and Wikipedia-Ptolemaic were also flagged here; both dropped 2026-04-23.)

2. **Rule 3 deterministic enforcement is still uneven.** Multiple merge scripts admit singleton rows or no-majority field votes (`Kitchen`, `Leprohon`, `Ryholt`). Several correction policies remain documented in prose or prompt files rather than enforced by tests.

3. **Rule 5 value-pinning is the dominant test gap.** HKW, Baud, idai, Kitchen, pharaoh.se, PM, Shaw, and Ryholt all have shape/coverage tests that would miss concrete field drift.

4. **Prompt/README drift is common after reviewer fixes.** HKW still calls Scorpion I Dyn-0; PM chunk-7 prompt contains stale known-wrong answers; Baud, D&H, Kitchen, Shaw, and Leprohon have documentation that no longer matches committed data or review status.

5. **Schema fields are carrying overloaded or mixed semantics.** Leprohon `stage_suffix`, PM `occupant_role`, Shaw `source_note`, Kitchen `polity`, and Wikipedia no-reign/uncertainty rows need clearer structured distinctions before Phase-A reconciliation.

## Fix-Up PR Batching Plan

### Data Corrections

- Baud: fix `baud-29`, `baud-30`, `baud-57` eldest-son roles and `baud-126.children_names`.
- D&H: finish Founders dynasty convention/refinement and footnote-marker cleanup.
- Kitchen: decide/add Smendes-in-N; repair `21H.06` normalized chronology representation; clarify/cite polity imports.
- Leprohon: split queen-consort rows from same-king stage rows structurally.
- Pharaoh.se: repair parser-shifted name cards, Roman date shifts, CE single-year signing, and dropped `Kaisaros` attestations.
- Ryholt: fix `15.3` markup/lost clause and `14.32` missing anglicised prenomen.
- PM: decide QV § X.B scope; adjust KV46 role.
- ~~Wikipedia-Ptolemaic: correct Berenice III co-regency wording, Cleopatra V uncertainty, and Ptolemy VII no-reign modeling.~~ — obsolete; source dropped 2026-04-23.

### Test Additions

- Add full-row value fixtures for small sources first: Shaw, idai canaries, PM chunks 1-2. (Wikipedia-Ptolemaic and Hölbl were in the original small-source list; both dropped 2026-04-23.)
- Add targeted canaries for high-risk parser/correction cases: pharaoh.se name cards and Roman dates, Ryholt no-majority rows, Kitchen concurrency, HKW original table rows, Baud derived role-to-title rules.
- Replace tolerant tests and presence checks with exact values where the source is already fixed-size.

### Doc / Audit-Trail Additions

- Update stale README/prompt/transcribe files for Baud, D&H, HKW, Kitchen, PM, Shaw, and Leprohon.
- Preserve idempotent correction audit trails in D&H and ensure reviewer/restoration rationale points to notes lines where applicable.
- Separate source notes from extractor/editorial rationale where fields currently mix provenance and pipeline commentary.

### Source Re-Extraction / Reproducibility

- ~~Hölbl needs an explicit decision: restore the reconciled source and tests on `main`, or drop it from Phase-0 scope.~~ — **Decided 2026-04-23: dropped.** Directory deleted.
- Kitchen needs a committed permissible source artifact, transcription, or deterministic acquisition artifact sufficient for audit.
- ~~Wikipedia-Ptolemaic needs stable per-row URLs/revision IDs or archived snapshots plus tests requiring them.~~ — **Decided 2026-04-23: dropped.** Coverage redundant with pharaoh.se + Leprohon Ch X chunk 14.
- Pharaoh.se should fail on missing raw pages and re-run after parser fixes, then repin affected rows.

## Artifacts Produced

- 12 `code-review-sweep-2026.md` files, one per source.
- 11 `reviewer-notes-sweep-2026.md` files, excluding `idai-gazetteer` by design.
- This coordinator summary.
