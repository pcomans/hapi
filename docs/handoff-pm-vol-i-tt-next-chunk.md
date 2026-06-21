# Handoff — Porter-Moss Vol I.1 next chunk (private TT tombs)

**Written 2026-05-02** by the agent that scoped chunk 9 (TT1–TT10) after PR #167 closed (Roman-period chronology deferral). Phase-0 priority queue (per session 2026-05-02): **PM Vol I TT first** (egyptologist-flagged highest-precision matching source in the corpus — TT numbers appear verbatim in museum records: "from TT55", "Theban Tomb 55, tomb of Ramose"), then PM Vol III Memphis, then D&H Ch 4 TIP, then D&H Ch 5 LP+Ptolemaic.

Pick this up when the user asks to continue PM I.1 transcription or process Phase-0 priority queue. For generic Phase-0 source onboarding see `docs/playbook-phase-0-ocr-transcription.md`. This handoff **supersedes** the playbook where they disagree — chunks 1–8 already established a multi-chunk PM extraction pattern under `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/`; chunk 9 is the first chunk on a new volume (PM I.1 *Private Tombs* vs the prior chunks' PM I.2 *Royal Tombs and Smaller Cemeteries*).

---

## Current state on `main` (verify before starting)

- **Source dir:** `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/`
- **Landed chunks (75 rows total, all from PM I.2):**
  - Chunks 1–5 — KV1–KV62 (PM I.2 § I.A). 37 rows. PRs #66 / #68 / #69 / #70 / #71.
  - Chunk 6 — KV63–KV65 sweep / § I.A closure. 0 rows. Roadmap-only.
  - Chunk 7 — PM I.2 §§ II + III.A/C/D South-West Valleys + Dra' Abu el-Naga (Antef Cemetery + Ahmose-Nefertari + Seventeenth Dynasty Cemetery BURIALS). 18 rows. PR #100. Introduced `<PREFIX>-<TitleCaseDescriptor>` tomb_id convention for non-numbered sections.
  - Chunk 8 — PM I.2 § X.A Valley of the Queens, 20 numbered QV tombs. 20 rows. PR #101.
- **Volume offsets:**
  - PM I.2: printed = physical + 458. (Used for all chunks 1–8.)
  - **PM I.1: printed = physical − 18** (printed 1 = physical 19). NEW for chunk 9. Verify on first and last chunk-9 page before extracting.
- **Source PDFs** (both gitignored under `proprietary/books/`):
  - PM I.1 Private Tombs: `Porter & Moss - PM I Theban Necropolis.pdf` (520 physical pages, SHA-256 `1d98326920f18faa25c3273c0c3b1b38dbc9fe18faeae07fa89f873a47a75455`).
  - PM I.2 Royal Tombs and Smaller Cemeteries: `Porter & Moss - PM I.2 Royal Tombs and Smaller Cemeteries.pdf` (SHA-256 `bd79be57b1180ea8766d0f8195a35d99dd02bfd986c0caf4f0026e568b209a42`).

---

## Target for chunk 9: TT1–TT10 (Deir el-Medina early Ramesside core)

**Scope:** First 10 numbered Theban Tombs in PM I.1 § I "Numbered Tombs". This chunk validates the pipeline on the new volume + the new section-shape (private rather than royal tombs) before scaling to TT11–TT400+ in subsequent chunks.

| Anchor | Physical pp. | Printed pp. | Notes |
|---|---|---|---|
| Section header `I. NUMBERED TOMBS` | 19 (top) | 1 | Confirmed in pdftotext probe. |
| TT1 SENNEZEM | 19 | 1 | Servant in the Place of Truth. Dyn. XIX. Deir el-Medina. |
| TT2 KHA'BEKHNET | 24 | 6 | Servant in the Place of Truth. Temp. Ramesses II. Deir el-Medina. |
| TT3 PESHEDU | 26 | 8 | Servant in the Place of Truth on the west of Thebes. Ramesside. Deir el-Medina. |
| TT4 KEN | 26 | 8 | Chiseller of Amūn in the Place of Truth. Temp. Ramesses II. Deir el-Medina. |
| TT5 (verify name in extraction) | ~28 | ~10 | First-pass regex skipped — confirm headword via direct extraction, not the ad-hoc locator below. |
| TT6 NEFERHOTEP + NEBNUFER (joint) | 32 | 14 | Foremen in the Place of Truth. Temp. ... Joint occupants — likely needs the chunk-7 KV46 / chunk-8 multi-occupant pattern (`occupant_alt_names`, role `Royal Family` for KV46; for TT6 the role is `Foremen` shared, not "Royal Family"). |
| TT7 (verify) | ~33 | ~15 | Ditto. |
| TT8 KHA' | 34 | 16 | Chief in the Great Place. Temp. Amenophis II, Tuthmosis IV. Deir el-Medina. |
| TT9 (verify) | ~35 | ~17 | Ditto. |
| TT10 PENBUY + KASA (joint) | 37 | 19 | Servants in the Place of Truth. Temp. ... Joint occupants — same multi-occupant pattern as TT6. |
| TT11 ḌḤOUT (next chunk's first row, **boundary marker**) | 39 | 21 | Overseer of the treasury, Overseer of works. Temp. Ḥatshepsut. **Stop here in chunk 9.** |

**Chunk-9 raw file:** `raw/chunk-p19-p39.txt` (21 physical pages — TT1 through TT11's headword line, where TT11 acts as the boundary marker exactly as KV47 closed chunk-3 and `XI. MEDYNET HABU` closed chunk-8). Extract with the same pypdf one-shot used for chunks 1–8 (see `transcribe.md` § "Method deviation"); apply `postprocess.py` afterwards (idempotent). The raw file is gitignored, same as prior chunks.

**Expected row count:** 10 rows. Two of them (TT6, TT10) carry joint occupants — keep as one row with `occupant_alt_names` populated, mirroring chunk-3 KV46 (Yuia + Thuiu, role `Royal Family`).

---

## Schema decisions blocking chunk 9

The KV/QV chunks used `valley: "Valley of the Kings"` / `valley: "Valley of the Queens"`. **Private TT tombs are not in a single "valley"** — they're scattered across seven Theban sub-sites (Deir el-Medina, Sheikh 'Abd el-Qurna, Dra' Abu el-Naga', Khokha, 'Asasif, Deir el-Bahari, Qurnet Mura'i). PM I.1 Appendix D "Classification of tombs according to site" (printed p.477) is the canonical site list — use those exact strings.

**Two options. Pick one in the chunk-9 prompt + prompt-rationale doc:**

1. **Repurpose `valley` for the Theban sub-site string.** Cleanest from a column-stability standpoint. The semantic name `valley` becomes loose for non-valley sub-sites (Deir el-Medina is a village, Sheikh 'Abd el-Qurna a hill, etc.) but the column already carried different values for SWV/DAN in chunk 7. Continuation of chunk-7 precedent.
2. **Add a new column `theban_subsite`** alongside `valley`. Clean naming but forks the schema across volumes; KV/QV rows would need null-fill. Costs one schema-fork ADR.

Recommendation: **Option 1** — repurpose `valley`. It avoids a schema fork mid-source and keeps chunk-9 a same-shape extension of chunks 7/8. Document in the chunk-9 prompt that for PM I.1 § I numbered tombs, `valley` carries the PM Appendix-D sub-site string (e.g., `"Deir el-Medina"`).

**Edition citation:** previous chunks use `"edition": "PM I.2 2nd ed. 1964"`. Chunk 9 (and all PM I.1 work) uses `"edition": "PM I.1 2nd ed. 1960"`. The schema's `source_citation.edition` field already supports this verbatim; just change the string in the prompt.

---

## Step-by-step plan for chunk 9

### 1. Verify the offset

Re-confirm `printed = physical − 18` at both ends of the chunk (TT1 at physical 19 = printed 1; TT11 at physical 39 = printed 21). Chunk-3 saw the offset stable across the KV1–KV46 range; chunk-9 should be similarly stable across the 21-page span, but PM I.1 may have foldout plates or figure pages that drift the offset by +1 each. **Check.**

### 2. Extract the raw text layer

```bash
cd pipeline && uv run python -c "
import pypdf
r = pypdf.PdfReader('proprietary/books/Porter & Moss - PM I Theban Necropolis.pdf')
text = ''.join(p.extract_text() + chr(12) for p in r.pages[18:39])  # physical p.19-39 (0-indexed 18-38)
open('pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/chunk-p19-p39.txt', 'w').write(text)
"
```

The raw file is gitignored. Form-feed (`\f`) separates physical-page boundaries.

### 3. Run `postprocess.py`

```bash
cd pipeline && uv run python pipeline/authority/sources/porter-moss-theban-necropolis/postprocess.py \
    --input pipeline/authority/sources/porter-moss-theban-necropolis/raw/chunk-p19-p39.txt
```

Idempotent. Confirms canonical glyph-class normalisation before the 3-agent extraction sees the file.

### 4. Write `prompt-chunk-9-tt1-tt10.md`

Copy `prompt-chunk-8-qv.md` as the closest structural template (numbered-tomb form + sub-area classification). Adjust:

- Section header: PM I.1 § I "Numbered Tombs" (replaces I.2 § X.A "Valley of the Queens").
- Edition string: `"PM I.1 2nd ed. 1960"`.
- Offset note: physical → printed offset is **−458** for I.2 vs **+18** for I.1 (a sign flip — the extraction prompt must internalise this so agents emit `source_citation.page` correctly).
- `valley` values: enumerate the seven Theban sub-sites from Appendix D. PM I.1 chunk-9 candidates appear to be mostly **Deir el-Medina** (TT1, TT2, TT3, TT4, TT8, TT10) but check each tomb's headword.
- Joint-occupant pattern: TT6 (Neferhotep + Nebnufer, both Foremen in the Place of Truth) and TT10 (Penbuy + Kasa, both Servants in the Place of Truth). One row per tomb; `occupant_name` carries the first occupant; `occupant_alt_names` carries the second. Role applies to both ("Foremen", "Servants" — keep PM's plural form).
- TT-specific role vocabulary: PM I.1 private tombs span a much wider role set than the royal KV/QV chunks. Expect: Servant in the Place of Truth, Chiseller of Amūn, Foreman, Chief, Head of brazier-bearers, King's son, Mayor in the Southern City, Prophet, Scribe, Steward, First prophet, Royal butler, Royal scribe, Officer, Vizier, Chief steward of the divine adoratress, Overseer of the treasury, Overseer of works, etc. Preserve PM's exact title verbatim — this is the museum-record-matching surface (museum descriptions often quote PM's title verbatim for TT-attributed objects).
- False-positive watch: scene-item numbers `(1)`, `(2)`, `(15)`, `(16)`, etc. inside body prose. PM I.1 entries are denser than I.2 — TT1 alone has scenes (5)–(25)+ before the first body sub-header (`Burial Chambers of Sennezem`). The headword block is just the first paragraph; everything inside parenthesised scene markers is body prose, NOT new tombs.

### 5. Spawn three parallel extraction subagents

Use `prompt-chunk-9-tt1-tt10.md`. Each agent writes to `raw/agent-{a,b,c}-chunk9.jsonl`. Standard chunk-7 / chunk-8 invocation pattern.

### 6. Run `merge.py`

`merge.py` reads the three agent outputs, majority-votes per field, emits a `merged.jsonl`, and a `merge-disagreements.txt` for the egyptologist-reviewer to resolve.

### 7. Spawn `egyptologist-reviewer`

Standard reviewer protocol per `feedback_pr_reviewers.md` and `feedback_reviewer_subagents_no_bash.md`: point reviewer at a worktree, they write to `/tmp/claude/eg-review-pr-N-chunk9.md`, parent agent posts inline comments via `gh`. PDF preflight per `feedback_pdf_preflight.md` is **already passed** for this chunk — `Porter & Moss - PM I Theban Necropolis.pdf` is on disk.

The reviewer should specifically check:
- TT1 SENNEZEM canonical English form (PM uses 'Sennezem', not 'Sennedjem'; ADR-016 display-name discipline says preserve PM-verbatim, then Phase-A normalises against Leprohon if there's a king involved — but TT1 is a private servant, no king-name overlap).
- TT5, TT7, TT9 names — these were not captured by the ad-hoc locator regex in this handoff. Verify by direct page extraction; do not infer from sequence.
- Joint-occupant rows (TT6, TT10) carry both names, plural role.
- `valley` field carries PM Appendix-D sub-site strings, not "Valley of the Kings"-style values.

### 8. Apply `fix_rows.py` CHUNK9_CORRECTIONS

Standard fix_rows pattern. Limit to corrections the reviewer cited; per `feedback_reviewer_vs_deterministic_output.md`, do not blindly accept reviewer corrections that contradict the source — verify against the chunk file first.

### 9. Tests

Follow chunks 7/8 testing pattern (deterministic invariants + per-row value pinning). Specifically:
- `test_chunk9_tt_count` — exactly 10 rows.
- `test_chunk9_tomb_id_format` — every row matches `r"^TT\d+$"` with N in 1..10.
- `test_chunk9_valley_in_appendix_d` — every `valley` string is in the PM I.1 Appendix-D sub-site list.
- `test_chunk9_joint_occupants` — TT6 and TT10 have non-null `occupant_alt_names`.
- Per-row pinning for at least the 4 confirmed-by-locator rows (TT1, TT2, TT8, plus one of TT3/TT4/TT6/TT10): `occupant_name`, `occupant_role`, `dynasty` (Roman, e.g. `XIX`), `valley`.

### 10. README + transcribe.md

Update `README.md` for the volume cross-over (chunks 1–8 covered I.2; chunk 9+ covers I.1; both share the same `reconciled.jsonl`). Add the chunk-9 row to the `transcribe.md` "Chunks" section.

### 11. Commit, branch, push, PR

Standard protocol. PR title: `feat(porter-moss): PM I.1 chunk 9 — TT1–TT10 Deir el-Medina core (10 rows)`. Reviewer flow per CLAUDE.md (Gemini auto-fire + watch-pr-reviews + code-reviewer + egyptologist-reviewer in parallel + scope-accountability-enforcer).

---

## Subsequent chunks (10+) — provisional plan

Once chunk 9 lands and validates the new schema for TT private tombs, subsequent chunks follow numbered-tomb decades:

| Chunk | Range | Notes |
|---|---|---|
| 10 | TT11–TT20 | Includes TT15 Tetiky (King's son, Mayor; Early Dyn XVIII), TT17 Nebamun (Scribe + physician). Mixed Sheikh 'Abd el-Qurna + Dra' Abu el-Naga' + Deir el-Medina. |
| 11 | TT21–TT40 | Includes TT22 Waḥ (Royal butler), TT24 Nebamun (Steward of royal wife Nebtu, Temp. Tuthmosis III), TT29 Amenemopet/Pairi (Vizier). |
| 12+ | TT41+ ... TT100 ... TT200 ... TT400+ | Many chunks. Egyptologist canonical anchors per § 3.1: TT100 Rekhmire, TT52 Nakht, TT69 Menna, TT96 Sennefer, TT55 Ramose, TT57 Userhat, TT93 Kenamun. These are the highest-MVP-value rows. |

**Per the playbook:** each chunk = its own PR. Don't bundle. Anticipated total: ~40 chunks for TT1–TT400+.

**§ II "Tombs without official numbers"** (PM I.1 printed pp.447–462) — cataloguing tombs known by descriptor only ('a' through 'uu' in 1st ed., several rediscovered and renumbered). Lower MVP-match-value than numbered TTs since museum records use TT-numbers; treat as the LAST chunk in the PM I.1 series, or defer. Decide when chunk 30+ is in flight.

**Mortuary-temple sections / appendixes** in PM I.1 — out of scope per the original transcribe.md "lower object-attribution density per MVP-match-value analysis" rationale (mirroring the deferred PM I.2 §§ IV/V/VII/VIII/IX/XI mortuary-temple sections). Re-evaluate post-MVP.

---

## Things to NOT do

- **Don't** try to use the chunk-7 descriptor `<PREFIX>-<TitleCaseDescriptor>` convention for TT tombs. PM I.1's numbered tombs use the same numbered form as KV/QV. Stick with `TT<N>`.
- **Don't** infer TT5 / TT7 / TT9 occupant names from sequence or from external sources — extract from the PDF directly.
- **Don't** scope chunk 9 to more than 10 tombs. Pipeline-validation chunk; bigger chunks come after the schema settles.
- **Don't** include scene-prose `(1)–(25)+` body content in `notes_from_pm`. Those are per-scene descriptions inside body prose and are explicitly out of scope per the rights policy and the `prompt.md` "drop everything from `Corridor`, `Hall`, etc. headers onward" rule.
- **Don't** edit `reconciled.jsonl` directly — per `feedback_never_edit_reconciled_jsonl.md`, corrections go through `fix_rows.py`'s CHUNK9_CORRECTIONS.

---

## Open question for the user

Before chunk 10+ ships in volume, decide: should `valley` be **renamed** to `theban_area` (or similar) at the schema level to reflect that PM I.1 uses sub-site classification, not valley-name classification? This is a one-off rename; chunks 1–8 already carry strings that aren't strictly "valleys" (chunk-7 SWV/DAN are valley-codes, chunk-8 QV is a valley but the tomb-cluster name overlaps the valley name).

Option (a): rename `valley` → `theban_area` everywhere; one-time migration on the existing 75 rows.
Option (b): keep `valley` as the column name, document the loose semantic in the README, accept the looseness.

The chunk-9 prompt should pick option (b) by default to avoid blocking on a rename ADR; flag to the user when the chunk-9 PR opens.
