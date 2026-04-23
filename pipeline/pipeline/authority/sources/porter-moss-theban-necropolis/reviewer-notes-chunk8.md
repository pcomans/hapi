# Reviewer notes — chunk 8 (PM I.2 § X.A, QV numbered tombs, pp. 751–769)

## Summary

**Yellow-green.** The 20-row set matches PM § X.A's numbered-tomb headwords exactly (QV 33, 36, 38, 40, 42–44, 46, 47, 51–53, 55, 60, 66, 68, 71, 73, 74, 75) — no missed headwords, no false inclusions, no § X.B / X.C / X.D / XI material leaked in. Headword spelling (ayin `ʿ` and underdot `ḥ`) is faithful to PM and roles are all in-vocab. The remaining issues are P2/P3 hedge- and scope-preservation slips in `notes_from_pm` plus one P1 role error (QV38 lost `Unfinished`).

## Per-row findings

### QV33 — Tanezem(t) — P2/P3
- PM p.751: "PRINCESS TANEZEM(T) [cart.]. Dyn. XX (?). Buried."
- `is_unfinished=false`, role=`Princess`, date hedge `Dyn. XX(?)` preserved in notes — correct.
- **P3**: PM places the hedge on the dynasty only ("Dyn. XX (?)"). Row collapses "Dyn. XX(?). Buried." — fine. No change.

### QV36 — no-name princess — OK (post-fix)
- PM p.751: "A PRINCESS, no name." `occupant_name=null`, role=`Unknown` (per CHUNK8_CORRECTIONS). Correct.

### QV38 — Sitreʿ — **P1 investigated: FALSE ALARM (no fix needed)**

**Post-review verification:** direct inspection of `reconciled.jsonl` on commit `a317dc5` shows `QV38.is_unfinished=true`. The flag is correctly set by the 3-subagent majority vote (agents B + C captured the `Unfinished` literal; agent A's 19-row output missed QV60 entirely and may have been the snapshot the reviewer inspected). `test_chunk8_only_qv38_unfinished` pins the True value. **No `CHUNK8_CORRECTIONS` entry needed** — fix_rows.py would be a no-op. The reviewer's P1 claim was based on a pre-merge snapshot.

Original reviewer note (kept verbatim for audit):
- PM p.751: "QUEEN SITRĒʿ [cart.], wife of Ramesses I. **Unfinished.**"
- Row has `is_unfinished=false`. The Unfinished headword is the one case prompted for; it was **dropped**. Set `is_unfinished=true`. `notes_from_pm` currently reads "wife of Ramesses I. Unfinished. (…)" — the note kept the word but the boolean flag didn't fire. **P1 — fix.**
- Minor: PM headword is "SITRĒʿ" (macron-e). Row uses `Sitreʿ` without macron. Consistent with the corpus-wide decision to drop vowel macrons; leave as-is unless this changes globally. **P3.**

### QV40 — no-name queen — OK (post-fix)
- PM p.751: "A QUEEN, cartouche blank." role=`Unknown` per fix. Correct.

### QV42 — Paraʿḥirwenemef — OK
- PM p.752: "PRINCE PARAʿḤIRWENEMEF…, Charioteer of the stable of the Great House, son of Ramesses III."
- Role `Prince`, notes verbatim — good.

### QV43 — Set-ḥirkhopshef — OK
- PM p.753: "PRINCE SET-ḤIRKHOPSHEF…, King's son, Hereditary prince of the royal children of his Majesty, Charioteer of the Great Stable, &c., son of Ramesses III."
- Matches. `ḥ` preserved.

### QV44 — Khaʿemweset — OK (with caveat)
- PM p.754: "PRINCE KHAʿEMWĒSET, sem-priest of Ptaḥ, son of Ramesses III."
- Row: `Khaʿemweset` (no macron), notes verbatim — good. **P3** macron issue as with Sitreʿ.

### QV46 — Imḥotep — OK
- PM p.755: "IMḤOTEP … (probably), Vizier. Temp. Tuthmosis I."
- Role `Vizier`, hedge `(probably)` preserved, "Temp. Tuthmosis I." preserved. Good.

### QV47 — ʿAḥmosi — **P2**
- PM p.755: "PRINCESS ʿAḤMOSI…, daughter of Seḳenenreʿ-Taʿa and Sit-**dhout**…"
- Row: `Sit-**gḥout**`. PM prints Sit-**dḥout** (d with underdot, not g). Appears to be an OCR misread of "dḥ" as "gḥ". **P2 — fix to `Sit-ḍḥout`.**

### QV51 — Esi II — **P2**
- PM p.756: "QUEEN ĒSI II [cart.], mother of Ramesses VI, daughter of Ḥubalzanet … (i.e. **Ḥemzert**)."
- Row name: `Esi II` (dropped macron — P3, consistent with project convention).
- Row notes: "(i.e. **Ḥemzert**)" — **correct**. Good.
- The PM footnote on p.756 clarifies "Wife of Ramesses III, see Černý…" attaching to Tyti below; not about Esi II — don't merge. OK.

### QV52 — Tyti — OK
- PM p.756: "QUEEN TYTI [cart.], Ramesside."
- Role `Queen`, `notes_from_pm` = "Ramesside." + citation. Good. The p.756 footnote ("Wife of Ramesses III … Daughter of Esi-Ḥemzert") is secondary filiation PM itself hedges — not in row, acceptable omission. **P3 optional**: could append "(wife of Ramesses III, daughter of Esi-Ḥemzert — per footnote)" but PM relegated it to a footnote, so leaving it out is defensible.

### QV53 — Raʿmeses — OK
- PM p.759: "PRINCE RAʿMESES…, son of Ramesses III." Matches row.

### QV55 — Amen(ḥir)khopshef — OK
- PM p.759: "PRINCE AMEN(ḤIR)KHOPSHEF…, Royal scribe, Overseer of horses, son of Ramesses III."
- Row name `Amen(ḥir)khopshef` — parenthetical preserved, correct. Notes verbatim. Good.

### QV60 — Nebttaui — OK (late add)
- PM p.761: "QUEEN NEBTTAUI … daughter of Ramesses II."
- Row matches. Good that merge recovered it from B/C.

### QV66 — Nefertari — OK
- PM p.762: "QUEEN NEFERTARI…, wife of Ramesses II." Matches.

### QV68 — Merytamun — OK
- PM p.765: "QUEEN MERYTAMŪN …, daughter of Ramesses II." Matches (macron dropped — P3 project convention).

### QV71 — Bentʿanta — OK
- PM p.766: "QUEEN BENTʿANTA …, daughter of Ramesses II." Matches.

### QV73 — no-name princess — OK (post-fix)
- PM p.767: "A PRINCESS, no name. Dyn. XX." role=`Unknown`, notes preserve "Dyn. XX." Correct.

### QV74 — Tentopet — **P2**
- PM p.767: "QUEEN TENTŌPET …, Great King's mother and King's wife.¹"
- Row notes: "Great King's mother and King's wife." — correct.
- **P2**: PM's footnote 1 on p.767 carries three filiation facts PM flags as hedged: "Wife (?) of Ramesses IV" (Gauthier), "Mother of Ramesses V" (Černý), "Daughter of Ramesses IV" (Seele). These are the kind of kinship hedges the prompt asks to preserve. Current row has none of it. Either append a compact hedge like "wife(?) of Ramesses IV; mother of Ramesses V (per footnote)" or leave out — I'd nudge toward appending, since it's the only kinship info PM gives. **P2, optional.**

### QV75 — no-name queen — OK (post-fix)
- PM p.768: "A QUEEN, no name." role=`Unknown`. Correct.

## Missed-row findings

None. All 20 § X.A headwords on pp. 751–768 are present. PM p.769–770 begins § X.B "Unnumbered Tombs and Pits" (Queen Mut…, ʿAhmosi son of Nebsu, Princess Neferḥēt, the Amenophis III princesses cache, etc.) — correctly excluded from this chunk.

## False-inclusion findings

None. No § X.B, § X.C (Finds, pp. 770–771), § X.D (Graffiti, p. 771), or § XI (Medinet Habu, p. 771+) content has leaked into the QV-prefixed rows.

## Priority recap

- **P1 (investigated, NO FIX NEEDED):** QV38 `is_unfinished` is already `true` post-merge — the reviewer's snapshot was pre-merge. See QV38 entry above.
- **P2 (should fix):** QV47 `Sit-gḥout` → `Sit-ḍḥout`; QV74 consider adding footnoted kinship hedge.
- **P3 (style/optional):** Macron-long-vowel dropped across the set (Sitreʿ, Khaʿemweset, Ēsi, Merytamūn, Tentōpet) — a project-wide policy call, not a chunk-8 defect.
