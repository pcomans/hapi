# Handoff — Phase 0 Source 3 (Kitchen 1996 TIPE)

**You are the agent tackling Phase 0 Source 3.** The generic 11-source plan lives at `docs/handoff-phase-0-transcription.md`; **this doc is the focused next-step hand-off** with everything you need to go from a fresh session to a merged PR. It supersedes the generic doc for this one source where they disagree.

## Where the project is

- **Source 1 (Shaw 2000 OHAE period banners)** — merged as PR #32. 13 rows. Simple `.txt`-plus-PDF extraction; no OCR pipeline needed.
- **Source 2 (Ryholt 1997 SIP)** — merged as PR #34. 157 rows. First source to use the ADR-017 OCR pipeline (Claude Code subagents + 3-subagent extraction + deterministic merge). **Read `pipeline/pipeline/authority/sources/ryholt-1997-sip/` end-to-end first — it is your reference implementation.**
- Everything the OCR pipeline needed (deps, `.gitignore`, ADR) is already committed. You do not need to re-design any of it.

## Your task: Source 3

**Citation.** Kitchen, K. A. (1996) *The Third Intermediate Period in Egypt (1100–650 BC)*, 3rd ed. with new preface. Warminster: Aris & Phillips. ISBN 978-0856682988.

**Source PDF.** `proprietary/books/Kitchen 1996 - Third Intermediate Period 3rd ed.pdf` (not committed). Pin its SHA-256 in your README.

**Target directory.** `pipeline/pipeline/authority/sources/kitchen-tipe/`.

**Scope.** The **Summary Chronological Table** at the front of the book (approximately pp. xxix–xxxviii in the 3rd edition) and any ruler-list appendices. One row per ruler across the Third Intermediate Period (Dynasties 21–25, plus parallel Tanite / Theban / Leontopolite lines).

**Out of scope for this PR.** Kitchen's **2009** revisions (Broekman/Demarée/Kaper eds.) are Source 10 in the generic handoff and land in a *separate* PR as a revisions-only delta overlaying this source. Do NOT merge the two. Put a note in the README's "Known gaps / Phase A notes" that Kitchen 2009 exists and will supersede some values.

**Expected row count.** ~40–50 rulers across Dyns 21–25.

**Schema** — see the generic handoff doc at `docs/handoff-phase-0-transcription.md` Source 3 entry for the authoritative field list. Summary:

```json
{
  "kitchen_id": "22.03",
  "dynasty": 22,
  "sequence_in_dynasty": 3,
  "name": "Osorkon I",
  "prenomen": "Sekhemkheperre Setepenre",
  "start_bce": -924,
  "end_bce": -889,
  "length_of_reign_years": 35,
  "approximate": false,
  "polity": "Tanis",
  "concurrent_with_kings": [],
  "notes_from_kitchen": "",
  "source_citation": {"pdf_pages": "NNN-MMM", "edition": "Aris & Phillips 3rd ed. 1996"}
}
```

**Important deviations from the generic handoff for this source specifically:**

- `source_citation.pdf_pages` is a **physical-PDF-page range string** (e.g. `"35-39"`), not a single printed-page integer. This is ADR-017 canonical; the generic handoff doc still shows the older per-page integer style. Use physical pages.
- `dynasty`: integer 21–25. If Kitchen tags a king as Leontopolite / Theban / Tanite separately within a dynasty, capture that in `polity`, not by splitting `dynasty`.

## Pipeline — how to execute

Follow **ADR-017** step by step (`docs/adr/017-ocr-pipeline-for-scan-only-sources.md`). The canonical reference implementation is Ryholt; copy its structure.

**Step-by-step:**

1. **Branch off main:** `git checkout main && git pull && git checkout -b feat/source-kitchen-tipe`.
2. **Scaffold the source dir:** `pipeline/pipeline/authority/sources/kitchen-tipe/` with `README.md`, `transcribe.md`, `prompt.md`, `merge.py`. Copy the Ryholt files and tailor them; do not reinvent the structure. Keep the empty `raw/` with its `.gitignore`-covered contents.
3. **OCR pass — Claude Code subagents.** For each 5-physical-page chunk of the target range, spawn a general-purpose subagent with the ADR-017-style prompt (use Ryholt's `transcribe.md` "Bulk OCR (Claude Code subagents)" block as the template). Subagents use the `Read` tool on the source PDF with `pages:"NNN-MMM"` and write per-chunk markdown to `raw/chunk-pNNN-pMMM.md`. These chunks are gitignored — do not commit them.
4. **Identify the target physical page range.** The printed pp. xxix–xxxviii range lives somewhere in the PDF's front matter. Rather than resolving the offset, do a quick Read on ~10 pages at a time to locate the Summary Chronological Table by eye, then chunk that range. Also check for a back-matter ruler-list appendix. Err on the side of over-inclusion; chunks are cheap.
5. **Structured extraction — three parallel subagents.** Write a Kitchen-specific `prompt.md` (mirror Ryholt's). Spawn three `general-purpose` Claude Code subagents with that prompt in parallel, each writing to `<agent_dir>/agent-{a|b|c}.jsonl` under `/tmp/claude-501/kitchen/` (or any dir; make it configurable via your `merge.py --agent-dir`).
6. **Merge.** Copy Ryholt's `merge.py` verbatim (it's almost entirely source-agnostic) and adjust only the `_sort_key` if Kitchen's ID scheme differs. Preserve the sentinel normalisation, duplicate detection, and all field-level majority-vote machinery. Output: `reconciled.jsonl` + `merge-disagreements.txt`.
7. **LLM review pass.** Invoke the `egyptologist-reviewer` Claude Code subagent and point it at `merge-disagreements.txt` + the source PDF. Apply flagged corrections via a committed override script (inline `fix_rows.py` or similar). Record every override in `merge-disagreements.txt` under the `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED` section. **Be honest in the label: this is not human review.**
8. **Tests.** `pipeline/tests/test_sources_kitchen_tipe.py`, ~10 value-assertion tests per rule 5. Assert every populated field on at least one fully-filled ruler row (the Ryholt file `pipeline/tests/test_sources_ryholt_sip.py` is the template). Include a regression test for anything surprising the reviewer pass caught.
9. **Update `docs/mvp-tasks.md`** — strike through the Kitchen TIPE bullet, add the row count and PR number.
10. **Commit, push, open PR.** Title: `feat: transcribe Kitchen 1996 TIPE → sources/kitchen-tipe`. Body follows the Ryholt PR (#34) as a template — include rights verification, known gaps, test plan. Request Copilot review. Run `code-reviewer` and `egyptologist-reviewer` subagents in parallel per the feedback memory. **Invoke the `scope-accountability-enforcer` once before replying to any batch of review comments**, then post replies individually with `SCOPE_CHECKED=1 gh api ...`.

## Things to watch out for (hard-learned on Ryholt)

Read **`docs/harness.md` → "Lessons from Phase 0 transcription"** before starting. In particular:

- **Do not commit `raw/chunk-*.md`.** They contain Kitchen's prose verbatim and would redistribute copyrighted material. `.gitignore` already excludes them.
- **Cite physical pages, not printed pages.** Scholarly books have mid-book offset shifts; don't waste effort resolving them. `source_citation.pdf_pages` is the chunk range.
- **Never claim "human review" when only an LLM has looked.** Label your overrides section `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED`. A real Egyptologist's sign-off pass is separate future work.
- **Never run `git filter-repo` on the whole repo** — it rewrites `main`'s SHAs and orphans your branch. If a scrub is needed, scope it to the feature branch.
- **Duplicate IDs fail loud** in `merge.py`'s `_load()` — don't silence that check.
- **Sentinel strings** (`"none"`, `"-"`, `"unknown"`) are normalised to `null` at vote time. Don't remove that normaliser.
- **OCR subagent refusal risk.** Claude Opus 4.6 declined bulk transcription on Ryholt once; framing as "fair-use scholarly extraction for a private research repository" resolved it. If your OCR subagent refuses on Kitchen, reframe rather than swap to an external API. ADR-017 is explicit that Gemini/Mistral/Flash are out.

## Kitchen-specific hazards (guessed from the source)

These are predictions — verify during the OCR pass and correct this doc via a follow-up if wrong:

- **Parallel-line dates.** TIP chronology has simultaneous Tanite and Theban lines; a king at `22.03` may overlap in time with a king at `23.01`. Capture via `polity` and `concurrent_with_kings` (which takes either king names or Kitchen IDs — pick one and document it in the README).
- **Kitchen uses hedged dates frequently** ("c.924"). Capture the hedge via `approximate: true` on those rows; leave the BCE integer as-is.
- **Co-regencies** may be encoded as two separate rulers or one ruler with a note. Follow Kitchen's own framing; let Phase A reconcile.
- **Dynasty 21 High Priests of Amun at Thebes** are separately numbered by Kitchen (Herihor, Pinedjem I, etc.) and may sit outside the main Dyn-21 Tanite line. Likely a separate sub-list; treat as a distinct `polity: "Theban (HPA)"` or similar and document.

## Done criteria

- `reconciled.jsonl` committed, ~40–50 rows, every row has a valid `pdf_pages` range.
- `merge-disagreements.txt` committed with the LLM-overrides section.
- `README.md`, `transcribe.md`, `prompt.md`, `merge.py` present and internally consistent.
- Tests pass (`cd pipeline && uv run pytest`). Add structural row-level tests in `pipeline/tests/test_sources_kitchen_tipe.py`.
- `docs/mvp-tasks.md` Kitchen TIPE bullet struck through with row count + PR link.
- PR opened, Copilot + code-reviewer + egyptologist-reviewer consulted, all comments responded to, CI green, merged.

## Next

Source 4 = Dodson & Hilton 2004, *The Complete Royal Families*. Queens and royal-family members. Similar OCR pipeline, expected ~150–250 rows.
