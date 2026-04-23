# Handoff — Phase 0 next steps after Leprohon completion

**Written 2026-04-23** by the agent who shipped Leprohon chunk 14 (PR #99, merged as `4b2c96c`). With chunk 14 landed, the **Leprohon 2013 chapters II–X transcription is substantively complete (395 rows across all 14 chunks)**. This handoff covers what's left for Phase-0 document ingestion, ordered by ease and Phase-A unblocking power.

For generic Phase-0 source onboarding, see `docs/playbook-phase-0-ocr-transcription.md`. For the older comprehensive scope plan, see `docs/handoff-phase-0-transcription.md` (now mostly outdated — most sources have landed). This handoff supersedes both where they disagree.

---

## State on `main` (verify first)

```bash
git checkout main && git pull
ls pipeline/pipeline/authority/sources/   # 14+ source dirs
cd pipeline && uv run pytest -q            # should be 977 passing
```

**Landed Phase-0 sources** (commits visible in `git log --oneline --grep='feat(' -- pipeline/pipeline/authority/sources/`):

- pharaoh.se (PR #25) — 381 rulers, full titulary, Beckerath-saturated citations
- iDAI.gazetteer (PR #6) — sites
- HKW Hornung-Krauss-Warburton (PR #5) — chronology
- Ryholt 1997 SIP (PR #34) — 157 rows Dyn 13–17 + Abydos Dynasty
- Kitchen 1996 TIPE (PR #36) — 60 rows Dyn 21–26 chronology
- Wikipedia-Ptolemaic (PR #19) — 24 rows
- Shaw OHAE 2000 (PR #32) — 13 chapter-banner period rows
- Baud 1999 *Famille royale* (PRs #41 + queens chunks) — OK royal family
- Porter-Moss Vol I.2 Theban royal tombs (PRs #69–73, KV1–KV62) — Valley of the Kings
- Dodson-Hilton 2004 Ch 1–4 (PRs #37–39, #76–79) — TIP queens + family-tree context
- **Leprohon 2013 chapters II–X (PRs #83–97, #99) — 395 rows, primary titulary authority**

**Dropped (verified redundant with pharaoh.se coverage):** Manetho Dyn 7 fragments (PR #75), Hölbl Argead bridge (PR #74), Beckerath 1999 *Handbuch* (audit 2026-04-19).

**Blocked on PDF acquisition:** Dreyer 1998 *Umm el-Qaab I* — the file currently at `proprietary/books/Dreyer 1998 - Umm el-Qaab I.pdf` is actually a Kahl 2003 review article, not the primary monograph. Out-of-print DAI publication; user has not located a copy. ~3 missing rulers (Iry-Hor, Ka, Scorpion I) — known authority gap.

---

## What's left, in priority order

### 1. Porter-Moss Vol I.1 — private TT tombs (HIGHEST PRIORITY)

**Why first:** Theban Tomb numbers (TT1–TT400+) appear *verbatim* in museum records — "from TT55, tomb of Ramose", "Theban Tomb 100, tomb of Rekhmire". This is one of the highest-precision matching sources in the entire corpus. The Met holds substantial Nina de Garis Davies facsimiles of canonical TT tombs; Brooklyn and Harvard hold fragments and squeeze material.

**Source:** `proprietary/books/Porter & Moss - PM I Theban Necropolis.pdf` (verify SHA matches what's pinned in `sources/porter-moss-theban/transcribe.md` — the I.2 work used the same volume).

**Scope:** Vol I.1 covers private (non-royal) TT tombs — TT1–TT400+, organised by location and date. Distinct from Vol I.2 (royal tombs, KV/QV) which has already landed under `sources/porter-moss-theban/`. Decide early whether this should be a sibling directory `sources/porter-moss-theban-private/` or absorbed into the existing `porter-moss-theban/` with a `tomb_type: "private" | "royal"` field. The existing directory's schema, prompt structure, and chunk pattern should be reused — read it first.

**Method:** same as PM I.2 — Claude Code subagent OCR (the printed PM volumes are NOT born-digital; the pypdf+MdC shortcut used for Leprohon and most modern academic books does NOT apply here). Per ADR-017: OCR → 3-agent extraction → merge → egyptologist review → fix_rows.

**Anticipated row count:** ~200–400 across all of TT1–TT400+. Will need multi-chunk PRs (~30–50 tombs per PR is the comfortable scale per the I.2 chunk-PR pattern).

**Phase-A unblock:** site/tomb authority for Theban necropolis private tombs. Without this, Met/Brooklyn/Harvard private-Theban material can't be resolved beyond "Thebes" generic.

### 2. Porter-Moss Vol III — Memphis (Giza/Saqqara/Abusir)

**Why second:** without this, Memphite provenances ("from Saqqara", "from the tomb of Ti at Saqqara") will systematically under-resolve below the level Met/Brooklyn/Harvard catalogues actually carry. The Memphite necropolis is one of the densest single-site corpora in the museum world.

**Source:** `proprietary/books/Porter & Moss - PM III Memphis.pdf`. Verify SHA and pin in the new source's README.

**Scope:** Vol III covers Giza, Saqqara, Abusir (Old Kingdom royal + private + Late Period reuse). Different volume editor (Málek's 1974–1981 revision, with ongoing Griffith Institute updates — record both the original 1934 PM team and Málek's revision date in `_source`).

**Method:** same as PM I.1 — OCR-required. Reuse the PM I.2 chunk schema. Different physical-page offset; re-verify per chunk.

**Anticipated row count:** ~400–800 across the whole Memphite necropolis. Multi-chunk; budget ~10–15 PRs.

**Phase-A unblock:** Memphite site authority. Critical for OK royal-mortuary attributions (Khufu's pyramid complex, Sahure's funerary temple, Userkaf's pyramid, the Abusir solar temples).

### 3. Dodson-Hilton Ch 5 — Late Period + Ptolemaic queens

**Why third:** lower per-row match rate than Ch 4 TIP (already landed), but Cleopatra VII alone has enough museum attestation to require proper queens resolution. Adds family-tree context that pharaoh.se / Wikipedia-Ptolemaic don't carry.

**Source:** `proprietary/books/Dodson & Hilton 2004 - Complete Royal Families.pdf` (already SHA-pinned in `sources/dodson-hilton-queens/transcribe.md`).

**Scope:** D&H Ch 5 *Late and Ptolemaic Periods*, 5 sub-sections:
- Final Renaissance = Dyn 26 Saite
- Persian Pharaohs = Dyns 27 / 31
- Last Egyptian Pharaohs = Dyns 28 / 29 / 30
- Macedon = Argead bridge (partial overlap with pharaoh.se)
- House of Ptolemy = Ptolemaic queens (partial overlap with Wikipedia-Ptolemaic + Leprohon chunk 14)

**Method:** follow `docs/handoff-dodson-hilton-next-chunk.md` — that handoff is still current for this source. Reuse `transcribe-extract-chunk-pdf.py`, the prompt structure, the composite `(dh_id, sub_period)` primary key, and the cross-section-duplicate handling pattern. The Leprohon chunk-14 work has zero schema impact on D&H.

**Anticipated row count:** ~60 rows. Probably 1–2 PRs.

**Phase-A unblock:** queens authority for Late Period (Nitocris I, Ankhnesneferibre, Shepenwepet) and Ptolemaic period (Arsinoe II, Berenice I–IV, Cleopatra I–VII). Note that Leprohon chunk 14 already covers the four Ptolemaic queen-consorts (Arsinoe II, Berenike II, Cleopatra I, Cleopatra II) at `leprohon-33.02a / 33.03a / 33.05a / 33.08a` with their titulary-relevant data; D&H adds genealogy + non-titular queens.

### 4. Predynastic / Dyn 0 (BLOCKED — needs PDF acquisition)

**Why blocked:** the file at `proprietary/books/Dreyer 1998 - Umm el-Qaab I.pdf` is mis-named — it's actually a 24-page **Jochem Kahl 2003** review article (*"Die frühen Schriftzeugnisse aus dem Grab U-j in Umm el-Qaab"*, *Chronique d'Égypte* 78, pp. 112–135), not the primary Dreyer monograph (DAI Archäologische Veröffentlichungen 86). User confirmed 2026-04-19 that the primary monograph is not available online; acquisition path unclear.

**Narrow gap:** pharaoh.se has 7 Predynastic kings (Seka, Khayu, Tiu, Tjesh, Neheb, Wenegbu, Mekh — Naqada-era obscure names) but is missing **Iry-Hor, Ka, Scorpion I** (the U-j-attested late-Predynastic / Dyn-0-frontier rulers). Narmer is already in pharaoh.se as First Dynasty.

**What you can do without the monograph:** the Kahl 2003 article (currently mislabelled in `proprietary/books/`) mentions all three by name on its PDF p. 5 (= published p. 116) but cites page numbers in Dreyer's book we don't have. So Kahl alone gives ~3 mentioned-but-uncited rows — not Phase-0 grade, would fail rule 1.

**Resolution path:**
1. User obtains the Dreyer 1998 monograph (DAI publication, out of print at most resellers — try DAI directly, or interlibrary loan).
2. Once obtained, transcribe the U-j ruler entries plus the Naqada IIIa/IIIb/IIIc seriation framework into `sources/predynastic-dyn0/reconciled.jsonl`.
3. Combine with Kaiser 1990 (*MDAIK* 46) for Stufe terminology and Hendrickx 2006 (in HKW Ch. 2) for Naqada I–III chronology.

**Until then:** Dyn 0 rulers remain an acknowledged authority gap. Document it in `dynasties.json` Phase A so the UI can flag pre-Narmer artifacts as "ruler authority pending."

---

## Cross-cutting deferred work (NOT blocking Phase-A start, but track)

These are issues that surfaced during chunks 1–14 of Leprohon and should be addressed at some point — but each is its own PR and none blocks the next-source ingestion.

### A. Human Egyptologist sign-off on Leprohon (ADR-017 step 6)

**Status:** NEVER DONE for any of the 14 chunks. The egyptologist-reviewer Claude subagent does NOT satisfy this — ADR-017 step 6 specifies a *credentialed* (i.e. real-human) Egyptologist walking a sample of rows against the PDF. Per the playbook's multi-chunk naming convention, the future review pass should be logged as `human-review-<YYYY-MM-DD>-<chunk>.md`.

**Suggested approach:** when a credentialed reviewer becomes available, sample ~20 rows per chunk (so ~280 rows total across all 14 chunks), spot-check transliteration / attestation / classification fidelity. The chunks most worth deep review are:

- Chunk 4 (MK proper) — Mentuhotep II's three titulary stages are the prototypical multi-stage emission case
- Chunk 8 (Dyn 18) — densest titulary per king (Thutmose III alone has dozens of attested prenomen variants); Akhenaten's a/b stages
- Chunk 14 (Macedonian + Ptolemaic) — the queen-consort sub-entry decision (see B below)

### B. Queen-consort schema overload — `stage_suffix` is doing two jobs

**Issue:** Leprohon chapter X uses the same `Na.` sub-headword convention for two different things: (1) titulary stages within a single king's reign (Mentuhotep II's a/b/c), and (2) queen-consort sub-entries within a Ptolemy's section (Arsinoe II at `2A.`, Berenike II at `3A.`, Cleopatra I at `5A.`, Cleopatra II at `8A.`). The chunk-14 extract reuses `stage_suffix: "a"` for both — structurally faithful to Leprohon's printed pattern but semantically overloaded.

**Documented in:** `pipeline/pipeline/authority/sources/leprohon-2013-titulary/README.md` (schema block, `stage_suffix` definition) and `transcribe.md` (chunk-14 log entry).

**Tracking:** test `test_chunk14_queen_consort_sub_entries_use_stage_suffix_a` locks the four affected rows.

**Proper fix:** add a `consort_of: str | None` field (or a `row_type: "king" | "consort" | "co_regent"` discriminator) to the row schema. Touches:
- `pipeline/pipeline/authority/sources/leprohon-2013-titulary/README.md` schema
- `fix_rows.py` to populate the new field on the 4 chunk-14 rows
- `tests/test_sources_leprohon_titulary.py` to assert the new field
- Likely a regenerate of `reconciled.jsonl` through `merge.py` + `fix_rows.py`

Defer until a consumer actually surfaces a problem — Phase-A `rulers.json` construction will reveal whether the overload causes real downstream issues.

### C. `notes` top-level field for row-level "absence" metadata

**Issue:** Several chunks emitted narrative text like "Two Ladies and Golden Horus names: none known" inside an individual name-list entry's `source_note`. The empty name-list itself is the canonical absence semantic, so the narrative is redundant — but it survived because there's no top-level `notes` field for row-level metadata. Gemini PR #99 flagged this; chunk-14 instances were stripped in `fix_rows.py`, but identical pattern exists on:

- `leprohon-27.02` (Cambyses, chunk 13 Late Period)
- `leprohon-29.02` (Hakor, chunk 13 Late Period)

**Proper fix:** either (a) sweep the 2 chunk-13 rows the same way (small, can be done now without the schema change), or (b) add a `notes: str | None` top-level field to the row schema and migrate. Option (a) is the minimum-scope fix.

### D. 308–306 BCE Interregnum — Phase-A curation question, not a Phase-0 gap

**Issue:** between Alexander IV's death (ca 310/309 BCE) and Ptolemy I's accession as King (305/304 BCE), Egypt had no titular pharaoh — Ptolemy I was ruling as *satrap* of the post-Alexander Diadochi partition. Some scholars list this as a brief "Interregnum" period.

**Not a source gap.** The primary facts — Alexander IV's death, Ptolemy's satrap-then-king progression, reign dates — are already in pharaoh.se as predecessor/successor chains + reign-date dicts, and in Hölbl's Appendix prose we decided not to transcribe (PR #74). Leprohon 2013 *itself* bridges the gap in chapter X: his chapter banners read `Macedonian Dynasty (332–305 BCE)` and `Ptolemaic Dynasty (305–30 BCE)`, treating the satrap years as the tail of the Macedonian Dynasty. Our chunk-14 extract picks up those exact dates.

**Resolution at Phase A** (when building `dynasties.json` / `periods.json`):
1. Follow Leprohon — no explicit Interregnum, Macedonian ends 305, Ptolemaic starts 305.
2. Follow Hölbl 2001 — explicit Macedonian 332–309, Interregnum 308–306, Ptolemaic 305–30.
3. Split Macedonian into two sub-periods (332–309 king-led, 308–306 satrap-only).

Either way: no new Phase-0 source is needed. **No museum record references "Interregnum" as a reign**, so Phase-A matching doesn't need an Interregnum pseudo-dynasty to resolve against — this is purely a dynasty-label classification choice.

### E. Cleopatra I anglicised gloss internal inconsistency (preserved as-is)

**Issue:** Leprohon's printed text at p. 181 has the transliteration `ḫkr(t).n ẖnmw` (with `k`) but his anglicised gloss reads `kheqer(et).en khnemu` (with `q`). This is Leprohon's own typesetting inconsistency — his anglicisation convention elsewhere consistently maps MdC `k` → English `k` and MdC `ḳ` → English `q`. The extract preserves both forms verbatim per source-fidelity. Egyptologist-reviewer 2026-04-21 flagged it as P2 ("either is defensible; leaving it is acceptable"). No action recommended unless Phase-A matching surfaces a specific problem.

---

## Workflow reminders for the next agent

The PR review workflow is documented in `CLAUDE.md` § "Pull request workflow". Key reminders that bit this session:

1. **Trigger Gemini Code Assist via `/gemini review` comment** for re-reviews on subsequent pushes (Gemini auto-fires on PR open). Check the quota before triggering — there's a daily limit and Gemini posts a quota-warning comment when exhausted. Codex is the fallback (`@codex review`) but has its own quota.
2. **`gh pr create` and other `gh` GraphQL calls fail in the sandbox** with `tls: failed to verify certificate: x509: OSStatus -26276` (macOS keychain TLS issue). Use `curl + gh auth token` for all PR-creation, comment-posting, review-fetching, and merge calls. The `feedback_curl_vs_gh_api_in_sandbox.md` memory has the canonical pattern.
3. **Push-time hooks:** every push that touches `docs/mvp-tasks.md` requires `TASK_LIST_UPDATED=1` env-var prefix. Every PR-comment that responds to a review batch requires `SCOPE_CHECKED=1` prefix (after running `scope-accountability-enforcer` once for the batch).
4. **`/watch-pr-reviews` skill** arms a Monitor for review notifications. Use it after pushing fixes — don't sit idle waiting.
5. **`scope-accountability-enforcer` subagent** before responding to a review batch. Particularly important when you're tempted to dismiss reviewer findings as "false positives" or "out of scope." It will challenge improper deferrals and confirm legitimate ones. Run it ONCE per batch, then prefix all `gh pr comment` calls in that batch with `SCOPE_CHECKED=1`.
6. **`fix_rows.py` is the durable correction layer.** Never patch `reconciled.jsonl` directly — `merge.py` rebuilds the file from agent outputs, so direct patches get blown away on re-merge. PR #97 learned this the hard way; chunk-14 inherited the cleanup.
7. **Self-merge clean PRs once CI is green** and at least one of {Gemini, Codex} has reviewed the current HEAD. Squash-merge via the GitHub API + delete the branch. Do not wait for the user.

---

## Suggested first step for the next session

```bash
git checkout main && git pull
cd pipeline && uv run pytest -q   # confirm 977 tests pass

# Read the relevant source's prior work before starting
ls pipeline/pipeline/authority/sources/porter-moss-theban/   # for PM I.1 sibling
cat pipeline/pipeline/authority/sources/porter-moss-theban/README.md
cat pipeline/pipeline/authority/sources/porter-moss-theban/transcribe.md

# Then ask the user which target they want next: PM I.1 vs PM III vs D&H Ch 5
```

Source priority (1 → 4) is the recommended order, but the user may have shifted priorities — confirm before committing to a direction.
