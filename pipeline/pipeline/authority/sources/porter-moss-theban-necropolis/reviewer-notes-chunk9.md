# Reviewer notes — chunk 9 (PM I.1 § I, TT1–TT10 Deir el-Medina core)

This file commits the egyptologist-reviewer subagent's printed-source review notes for chunk 9 (PR #196). The notes are the audit-trail anchor that `CHUNK9_CORRECTIONS` rationales in `fix_rows.py` reference when they cite "egyptologist printed-source review". Per `feedback_fix_rows_unattributed_restoration.md` and CLAUDE.md rule 1, every correction inserting characters absent from the raw text-layer dump must trace to a committed scholarly review — this file is that anchor for the chunk-9 corrections.

Two passes ran:

- **First pass** (post-merge, pre-`CHUNK9_CORRECTIONS`): 6 P2 findings → applied via `CHUNK9_CORRECTIONS` (TT2 attribution_certainty override, TT3/TT4/TT5/TT6/TT9 notes_from_pm corrections). Reviewer pinned the fix-direction for each P2.
- **Second pass** (post-`CHUNK9_CORRECTIONS`, on the committed `reconciled.jsonl`): 2 P2 follow-up findings → applied (TT4 rationale softened, TT10 Turin Mus. 1559 cross-ref restored).

Source for both passes: `/Users/philipp/code/hapi/proprietary/books/Porter & Moss - PM I Theban Necropolis.pdf` (SHA-256 `1d98326920f18faa25c3273c0c3b1b38dbc9fe18faeae07fa89f873a47a75455`). Page offset: physical = printed + 18.

---

## Pass 1 — Findings against the post-merge state

Yellow. All 10 TT1-TT10 rows are structurally correct (page numbers, edition, section, joint-burial classifications, controlled-vocab roles, PM-I.1 noise residuals in `occupant_name`, `.).` → `.)` punctuation fix, `shared_with_tombs` parsing for TT3/TT4/TT7). The `occupant_name` matchable field is clean across all 10 rows — no wrong-person risk.

### TT2 — Khaʿbekhnet — P2 (`attribution_certainty` misfire on a non-primary hedge)
- PM p.6: "2. KHAʿBEKHNET …, Servant in the Place of Truth. Temp. Ramesses II. (L. D. Text, No. 107.) Parents, Sennezem (tomb 1) and Iyneferti. Wives, Saḥte … and (probably) Esi …"
- Issue: row carries `attribution_certainty="probable"` because the Tier-3 deriver fired on the literal token `(probably)` in `notes_from_pm`. PM's `(probably)` here qualifies the identification of the *second wife* Esi, NOT Khaʿbekhnet's primary attribution — Khaʿbekhnet himself is fully attested.
- Fix applied: `DERIVER_OVERRIDES` mechanism in `fix_rows.py` pins TT2 `attribution_certainty="attested"` post-derivation with cited rationale. The verbatim `(probably)` token stays in `notes_from_pm`.

### TT3 — Peshedu — P2 (false underdots in two names within the parents/wife clause)
- PM p.9: "3. PESHEDU …, Servant in the Place of Truth on the west of Thebes. (Also owner of tomb 326.) Ramesside. Deir el-Medina. Parents, Menna … and Huy …. Wife, Nezemtbehdet …"
- Issue: row notes had `Ḥuy` and `Nezemtbeḥdet` with underdots; PM p.9 prints `Huy` and `Nezemtbehdet` with plain h, no underdot.
- Fix applied via `CHUNK9_CORRECTIONS`: drop both false underdots.

### TT4 — Ḳen — P2 (false underdot in `Ḥenutmeḥyt`; macron-loss inconsistency)
- PM p.11: "4. ḲEN …, Chiseller of Amūn in the Place of Truth. (Perhaps also owner of tomb 337.) Temp. Ramesses II. Deir el-Medina. (L. D. Text, No. 106.) Parents, Thonūfer …, Chiseller of Amūn in the Khenu, and Maʿetnefert …. Wives, Nefertere … and Ḥenutmehyt …"
- Issue 1: row notes had `Ḥenutmeḥyt` with two underdots; PM p.11 prints only the leading capital-Ḥ underdot, the medial `h` carries no underdot (egyptologist verified directly against multiple body-text positions on p.11 — see Pass 2 findings for the rationale-softening note).
- Issue 2: row notes had `Amun` (×2) and `Thonufer` without macrons; PM prints `Amūn` and `Thonūfer` with macron-u. The earlier `tie-break-overrides.json` TT4 entry argued "macrons dropped per project-wide convention" — empirically wrong vs the chunk-3/7 macron-preserve precedent.
- Fix applied via `CHUNK9_CORRECTIONS`: drop medial Ḥenutmehyt underdot, restore Amūn (×2) and Thonūfer macrons.

### TT5 — Neferʿabet — P2 (false underdot in `Mahi`)
- PM p.12: "5. NEFERʿABET …, Servant in the Place of Truth on the west of Thebes. Ramesside. Deir el-Medina. Parents, Neferronpet … and Mahi … (name on stela in Brit. Mus. 150, see infra, p. 14). Wife, Taēsi …"
- Issue 1: row notes had `Maḥi`; PM prints `Mahi` (plain h).
- Issue 2: row notes had `Taesi`; PM prints `Taēsi` with macron-e.
- Fix applied via `CHUNK9_CORRECTIONS`: drop Mahi underdot, restore Taēsi macron.

### TT6 — Neferhotep + son Nebnufer — P2 (macron loss; otherwise OK)
- PM p.14: "6. NEFERḤŌTEP … and son NEBNŪFER …, Foremen in the Place of Truth. Temp. Ḥaremḥab to Ramesses II. Deir el-Medina. (L. D. Text, No. 101.) Wife (of Neferḥōtep), Iymau …; (of Nebnūfer), Iy …"
- Joint-burial classification: hierarchical (`X and son Y` — Neferhotep leads, Nebnufer in `co_occupants`). `is_joint_burial=false`. Verified correct.
- Issue: row notes had `Neferḥotep` and `Nebnufer` without macron-ō / macron-ū; PM prints both with macrons.
- Fix applied via `CHUNK9_CORRECTIONS`: restore both macrons. The strip-Ḥ rule applies to `occupant_name` only; `notes_from_pm` is verbatim-preserve so both Ḥ underdots and macrons stay.

### TT9 — Amenmose — P2 (false underdot on `Tent-hōm`)
- PM p.18: "9. AMENMOSI …, Servant in the Place of Truth, Charmer of scorpions. Ramesside. Deir el-Medina. Wife, Tent-hōm …"
- Issue: row notes had `Tent-ḥōm` (underdot-ḥ + macron-o); PM prints `Tent-hōm` (plain h, macron-o).
- Fix applied via `CHUNK9_CORRECTIONS`: drop the false underdot, preserve the macron-o.

---

## Pass 2 — Findings against the post-`CHUNK9_CORRECTIONS` state

Net: ship it. Two P2 follow-ups, both applied.

### TT4 — `Ḥenutmehyt` rationale overclaim — P2 (rationale-text only)
- PM p.11 prints the queen's name in multiple body positions ((2), (5), (7)) — comparison with clearly-underdotted instances on the same page (`Ḥaremḥab`, `Amenemḥab`) supports reading the medial as plain `h` in PM's typesetting of this entry.
- BUT the standard scholarly form is `Ḥnwt-mḥyt` ("Mistress of fish") — Ranke PN, LÄ, and TLA all print medial `-mḥ-`. PM's typesetting may simply have lost the medial underdot in this entry's text-layer setting.
- The `notes_from_pm` field is verbatim-preserve "against PM's printed text", not against the canonical scholarly form. The committed value is therefore correct under the field's stated policy — but the rationale's flat claim "PM prints only the LEADING capital-Ḥ underdot" undersells the ambiguity.
- Fix applied: softened the `CHUNK9_CORRECTIONS` rationale to acknowledge the diacritic-distribution call and cite the body-text positions as the corroborating evidence. No data change.

### TT10 — `(name from offering-table of Penbuy, in Turin Mus. 1559)` dropped from notes — P2
- PM p.19 prints, between the two clauses already captured: `Father (of Penbuy), Iri … (name from offering-table of Penbuy, in Turin Mus. 1559).`
- The pre-Pass-2 committed `notes_from_pm` carried `Father (of Penbuy), Iri.` and skipped the Turin Mus. catalog cross-ref entirely — same R5/R9/R10 systemic-clause-loss pattern flagged in chunks 3/7 (cf. KV45's `Cairo Mus. Ent. 47032` restoration).
- The Turin Mus. 1559 reference is exactly the catalogable fact the schema is meant to retain (object-level cross-reference downstream Phase-A consumers will want for direct Turin-data joins).
- Fix applied: restored to `notes_from_pm` via `CHUNK9_CORRECTIONS` TT10 update.

---

## Page-citation verification (Pass 1)

All 10 page numbers verified directly against the PDF:

| tomb_id | printed page | physical page | headword |
|---|---|---|---|
| TT1 | 1 | 19 | `1. SENNEZEM …, Servant in the Place of Truth.` |
| TT2 | 6 | 24 | `2. KHAʿBEKHNET …, Servant in the Place of Truth.` |
| TT3 | 9 | 27 | `3. PESHEDU …, Servant in the Place of Truth on the west of Thebes.` |
| TT4 | 11 | 29 | `4. ḲEN …, Chiseller of Amūn in the Place of Truth.` |
| TT5 | 12 | 30 | `5. NEFERʿABET …, Servant in the Place of Truth on the west of Thebes.` |
| TT6 | 14 | 32 | `6. NEFERḤŌTEP … and son NEBNŪFER …, Foremen in the Place of Truth.` |
| TT7 | 15 | 33 | `7. RAʿMOSI …, Scribe in the Place of Truth.` |
| TT8 | 16 | 34 | `8. KHAʿ …, Chief in the Great Place.` |
| TT9 | 18 | 36 | `9. AMENMOSI …, Servant in the Place of Truth, Charmer of scorpions.` |
| TT10 | 19 | 37 | `10. PENBUY … and KASA …, Servants in the Place of Truth.` |

Boundary marker TT11 verified at physical p.39 (= printed p.21) — out of chunk-9 scope and shifts theban_area to Draʿ Abû el-Nagaʿ.

---

## Joint-burial classifications (Pass 1)

- **TT6 (NEFERḤŌTEP and son NEBNŪFER)**: PM's `… and son …` is hierarchically subordinated. Row has `is_joint_burial=false`, `co_occupants=[{name: "Nebnufer", role: "Official"}]`. Correct per the schema rule (`X and son Y` → hierarchical, X is the syntactic head).
- **TT10 (PENBUY and KASA, Servants in the Place of Truth)**: PM uses bare conjunction with plural role-clause; no syntactic primacy. Row has `is_joint_burial=true`, `co_occupants=[{name: "Kasa", role: "Official"}]`. Correct per the schema rule (`X and Y, plural-role` → coordinate).

The other 8 TT1–TT10 rows are single-occupant.

---

## P3 confirmations (Pass 2)

- `Maʿetnefert` (TT4 parent name) preserved verbatim — PM p.11 prints with plain ayin + plain e/n (no macron, no underdot). No action.
- `Sennezem` (TT1) verbatim against PM p.1 — modern scholarship uses `Sennedjem`. Phase-A alias coverage concern: when this row is propagated to a person/ruler authority, `Sennedjem` should be added as an alt-name. Out of chunk-9 scope.
- `Bukhaʿnef` (TT10 wife of Kasa) — PM p.19 prints the ayin. Verified.
- `co_occupants[0].name="Nebnufer"` strip-form on TT6 is the right call (matchable field, parallel to `occupant_name`); the PM-printed `Nebnūfer` lives in `notes_from_pm` for traceability.

---

## Methodology observations

- The `DERIVER_OVERRIDES` mechanism (typed table that pins a deriver's regex output for cases where PM's hedge token applies to a secondary clause) is well-designed: it preserves the deterministic-derivation default while allowing per-row escape with cited rationale. Mirrors the SPOT_CORRECTIONS shape, which keeps the audit-trail uniform. Reuse for any future rule-vs-evidence conflicts.
- The `CHUNK9_CORRECTIONS` rationales cite chunk-3/chunk-7 macron-preserve precedents explicitly. This kind of cross-chunk-precedent citation is exactly what makes the audit trail useful when a future sweep tries to harmonise verbatim policies across volumes (PM I.1 vs PM I.2 typesetting differs subtly — chunk 9 is the first PM I.1 chunk).
- The empirical correction of the earlier `tie-break-overrides.json` TT4 entry's wrong claim ("macrons dropped per project-wide convention" → false vs chunk-3/7 precedent) is the right kind of self-correction; the new `CHUNK9_CORRECTIONS` entry supersedes it cleanly with the citation.

---

## Verdict (passes 1 + 2)

Both passes: ship it. All P2 findings applied (6 from Pass 1 via `CHUNK9_CORRECTIONS` + 1 via `DERIVER_OVERRIDES`; 2 from Pass 2 — TT4 rationale soften + TT10 Turin Mus. cross-ref restoration — applied via `CHUNK9_CORRECTIONS` rationale text + value update).

---

## Pass 3 — Findings against the post-Pass-2 state

Fresh-eyes re-reading. Two passes already verified pages 1, 6, 9, 11, 12, 14, 15, 16, 18, 19; the third pass turns up 4 substantive findings the earlier passes missed.

### TT9 — `occupant_name` should be `Amenmosi` not `Amenmose` — P1 (merge-blocker)

PM I.1 p.18 prints `9. AMENMOSI`. The pre-Pass-3 row carried `occupant_name="Amenmose"` — silent Anglicization to a more common modern spelling. This is a rule-1 (work-like-a-scholar) provenance violation in the matchable name field. Cross-volume corroboration: chunk-7's `DAN-AhmosiHenutempet` / `DAN-AhmosiSonOfSeqenenre` rows preserve PM's `-osi` ending verbatim — it is PM's volume-wide editorial convention, not a typesetting accident.

**Fix applied via CHUNK9_CORRECTIONS:** `TT9.occupant_name = "Amenmosi"`.

### TT7 — `occupant_name` should be `Raʿmosi` not `Raʿmose` — P1 (merge-blocker)

PM I.1 p.15 prints `7. RAʿMOSI`. Same `-osi` → `-ose` Anglicization as TT9, but compounded by **wrong-person collision risk**: `Raʿmose` is the name of the famous Vizier of Amenhotep IV in TT55 — a completely different historical person from this Deir el-Medina scribe. PM itself reserves `RAʿMOSI` for the TT7 scribe and uses `RAʿMOSE` (plain `e`) for the TT55 vizier; preserving PM's distinction in `occupant_name` is exactly what the matchable-field convention is for.

**Fix applied via CHUNK9_CORRECTIONS:** `TT7.occupant_name = "Raʿmosi"`.

### TT1 — missing object-cite parenthetical for the BRUYÈRE 1927 fragment — P2

PM I.1 p.1 prints `Father, Khaʿbekhnet [cartouche] (name on fragment, BRUYÈRE, Rapport (1927), fig. 34 [4]).` The pre-Pass-3 row dropped the entire parenthetical. Same systemic R5/R9/R10 clause-loss pattern as TT10's Turin Mus. 1559 restoration: object-level provenance cross-references are exactly the catalogable facts the schema is meant to retain.

**Fix applied via CHUNK9_CORRECTIONS:** TT1 `notes_from_pm` updated to `"Servant in the Place of Truth. Dyn. XIX. Father, Khaʿbekhnet (name on fragment, BRUYÈRE, Rapport (1927), fig. 34 [4]). Wife, Iyneferti."`.

### TT5 — missing Brit. Mus. 150 stela object-cite — P2

PM I.1 p.12 prints `Parents, Neferronpet ... and Mahi ... (name on stela in Brit. Mus. 150, see infra, p. 14).` The pre-Pass-3 row dropped the entire parenthetical. Notably, the Pass-1 reviewer note quotes this exact PM clause when describing TT5's headword (line 35) — the reviewer saw the clause but the correction was never written. Brit. Mus. 150 is a major British Museum object — exactly the catalog-level cross-reference Hapi needs for cross-museum reunification of Deir el-Medina material.

**Fix applied via CHUNK9_CORRECTIONS:** TT5 `notes_from_pm` extended to `"Servant in the Place of Truth on the west of Thebes. Ramesside. Parents, Neferronpet and Mahi (name on stela in Brit. Mus. 150, see infra, p. 14). Wife, Taēsi."`.

## Pass 3 — P3 confirmations (no action needed)

- TT1 `Sennezem` vs modern `Sennedjem`: row correctly preserves PM verbatim. Phase-A authority alias coverage concern, out of chunk-9 scope.
- TT2 `(see supra, p. 5)` cross-ref: dropped from notes; within-volume back-reference (to TT1 Esi-as-wife mention), not a museum-object cite. Defensible as out of scope.
- `occupant_role="Official"` for all 10 rows: verified — workmen, scribes, foremen, chief, chiseller all flatten to `"Official"` per the prompt's controlled-vocab rule. TT8 `Chief in the Great Place` is the head artisan, NOT a priest; `"High Priest"` would be wrong.
- `is_joint_burial` and `co_occupants` for TT6 (hierarchical) vs TT10 (coordinate): re-confirmed.
- `shared_with_tombs` for TT3 / TT4 / TT7: re-confirmed; no other TT1-TT10 row has a missed cross-reference.
- `source_citation.page` spot-checked on TT1, TT4, TT8, TT10: all correct.
- `DERIVER_OVERRIDES` mechanism on TT2: re-confirmed (`(probably)` qualifies wife Esi, not Khaʿbekhnet).
- Diacritic spot-check across all 10 rows: all macrons, underdots, ayin preserved correctly post-Pass-2.

## Verdict (Pass 3)

After applying the 4 Pass-3 fixes (2 P1 + 2 P2), **ship it.** The matchable-name field on TT7 and TT9 now traces to PM verbatim; the object-cite parentheticals on TT1 and TT5 close the systemic clause-loss gap that Pass 2 first surfaced on TT10.
