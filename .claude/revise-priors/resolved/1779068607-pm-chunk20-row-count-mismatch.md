# Revise priors: PM chunk 20 prompt expects 8 rows but file contains ~16 Shape-1 headwords

- **Date**: 2026-05-18T01:43:27Z
- **Agent**: general-purpose (PM Memphis chunk-20 extraction subagent B)
- **Triggered by**: extraction task for `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-20-p148-p164-teti-pyramid-opener.txt` using prompt at `pipeline/pipeline/authority/sources/porter-moss-memphis/prompt-chunk-20.md`

## Scope

I am one of three parallel subagents (A/B/C) running the Phase-0 extraction protocol on **chunk 20** of Porter & Moss Vol III.2 (Memphis). The chunk covers § II.B AROUND TETI PYRAMID — NORTH OF THE PYRAMID, physical pp.148–164 / printed pp.508–524. Output is later majority-voted by `merge.py`.

## Assumption suspected

The prompt's `## Expected row count` section states:

> Pre-extraction structural scan: 7 Shape-1 descriptor-named primary tombs (INTI, KHENTKA IKHEKHI, NEFERSESHEMREʿ SHESHI, ʿANKHMAʿḤOR SESI, UZAḤATETI NEFERSESHEMPTAḤ SHESHI, PTAḤSHEPSES, MERERI) + 1 Shape-1 LS-headword (LS 10 KAGEMNI MEMI). **Total expected: 8 rows (acceptable band 6–10).**

The chunk file actually contains roughly **16–17** Shape-1 / Shape-1b / Shape-1-LS headwords across pp.148–164. The 8-row count is load-bearing because the band-guard (6–10) tells each subagent to re-read on overshoot, and `merge.py` may fail or silently drop rows if the three agents disagree on which extras are in scope.

## Evidence

Reading the chunk file line by line, the **explicitly-listed-in-prompt** headwords are present as expected:

- INTI — phys p.148, line 12
- KHENTKA IKHEKHI — phys p.148, line 20
- NEFERSESHEMREʿ SHESHI — phys p.151, line 168
- ʿANKHMAʿḤOR SESI — phys p.152, line 194 (`CANKHMACI;IOR ... SESI`)
- UZAḤATETI NEFERSESHEMPTAḤ SHESHI — phys p.155, line 330
- PTAḤSHEPSES — phys p.158, line 450
- MERERI — phys p.158, line 466
- LS 10. KAGEMNI MEMI — phys p.161, line 586

But the file **also** contains the following Shape-1 named-headword rows in the same page range that the prompt does NOT list and the band-cap (10) excludes:

- GEMNI USER — phys p.157, line 431: `GEM NI USER 2} 1 r = , Royal chamberlain, Scribe. ISt Int. Period.`
- WERNU — phys p.159, line 497: `WERNU ~:a;;. Tenant of the Pyramid of Teti, Lector-priest of the mit-bark of Horns and the dJt-bark of Horns, etc. Middle Dyn. VI or later.`
- KHUI — phys p.159, line 514: `KHUI ® }Q, Tenant of the Pyramid of Teti, Prophet of the Pyramid of Pepy I, Overseer of Upper Egypt, etc. Middle Dyn. VI or later.`
- THETUT — phys p.159, line 525: `THETUT = ::Jt, King's [secretary] of all secret commands of the frontier-posts, etc. Dyn. VI.`
- DESI — phys p.160, line 535: `DESI =~~.Noble of the King, Companion of the house. Dyn. VI.`
- MERU TETISONB — phys p.160, line 545: `MERU \-=-_} TETISONB 8) ~J (also MERYRECSONB ... and PEPYSONB ...), Overseer of commissions of tenants of the Pyramid of Teti, ...`
- SEMDENT — phys p.160, line 562: `SEMDENT -R -;:, Prophet of the Pyramid of Teti, etc. Dyn. VI.`
- NAME LOST — phys p.161, line 578: `NAME LosT, Royal chamberlain of the Great House, etc. Dyn. VI.`

There is **also** an unnamed group tomb at phys p.156, line 392: `ToMB WITH SEVERAL BuRIAL CHAMBERS. Ist Int. Period. ... Excavated by Lepsius in I843·` containing burial chambers of Reʿy, Ḥarshefḥotp, Ipiʿankhu, Khuit-khentekhtai, and an unnamed Berlin-burial Gemni. This block has no PM-headword CAPS name (the heading is a descriptive Shape-3-like grouping), so it's unclear whether it should emit a row at all under chunk-20's rules.

All eight additional headwords have the same syntactic shape as the listed ones (CAPS NAME + hieroglyph noise + comma-separated title cluster + `Dyn. VI` / `Temp. <King>` / `Middle Dyn. VI or later` dating + period). They are NOT sub-features (no Room/Façade/(N)-numbered scene prefixes), they are NOT museum-citation lines, and they are NOT wife/parents clauses. The "NAME LOST" entry is independent evidence that the prompt author did not anticipate everything in the page range — the prompt's field rules explicitly say `occupant_name: null` is "only for explicitly anonymous tombs (none expected in this chunk)."

CLAUDE.md rule 2 ("no silent arbitrary picks") forbids me from silently emitting 8 (fabricating scope by dropping 8+ real headwords) or silently emitting 16+ (blowing past the band-cap that the other two agents may use as a sanity check). Rule 6 (sacred reconciled data) reinforces this: a reconciled artifact built on a count-mismatch across the three agents has no provenance.

## Decision needed from user

Which is the correct interpretation?

1. **The chunk file was sliced too wide.** The prompt's expected-8 list and the cemetery-banner narrative (`§ II.B AROUND TETI PYRAMID — NORTH OF THE PYRAMID`) suggest chunk 20 was meant to stop at PTAḤSHEPSES or MERERI (phys p.158). The extra headwords (WERNU through NAME LOST, plus GEMNI USER and the unnamed Lepsius tomb) likely belong in chunk 21 or a separate sub-chunk for the SAAD/DRIOTON 1943-excavated tombs (which form a distinct cluster). Fix: re-slice the chunk file to stop at the appropriate boundary; the three agents re-run on the narrower file.
2. **The prompt author miscounted.** The chunk file is correctly sliced (it explicitly stops just before the Mereruka mega-block per the prompt header), and the prompt's "expected 8" listing was a non-exhaustive structural-scan undercount. Fix: update the prompt's Expected row count section to enumerate all ~16 headwords (or simply bump the band to e.g. 14–18), then the three agents re-run.

## Recommendation

If forced to choose without further information, I lean toward **option 2** (prompt undercount), because:

- The chunk header explicitly anchors the end-boundary at "stops just BEFORE the Mereruka mega-block (phys p.165+)" — that's a content-driven boundary, not a count-driven one.
- The additional headwords (WERNU, KHUI, THETUT, DESI, MERU TETISONB, SEMDENT, NAME LOST) all come from the SAAD/DRIOTON 1943 Ann. Serv. xliii cluster, which is topographically continuous with the AROUND TETI PYRAMID — NORTH OF THE PYRAMID material; splitting them off would create a chunk that's about excavator rather than location.
- GEMNI USER on p.157 sits between UZAḤATETI's burial chamber and PTAḤSHEPSES — it's clearly inside the Teti Pyramid cemetery cluster.

However, I want the user to confirm before any of the three agents commits its output, because the wrong choice causes either fabricated rows (option-1 outcome if we pick 2) or silently-dropped real tombs (option-2 outcome if we pick 1).

A secondary question the user should resolve: how to treat the unnamed `ToMB WITH SEVERAL BuRIAL CHAMBERS` (p.156). Options: (a) emit a single row with `occupant_name: null` and `co_occupants` listing Reʿy / Ḥarshefḥotp / Ipiʿankhu / Khuit-khentekhtai / Gemni; (b) skip it as not-a-named-tomb; (c) emit one row per named coffin occupant (against the chunk's Shape-1 rules but matches the data). I suspect (b) is intended (no CAPS-name headword line) but the prompt doesn't say.
