# PM III chunk 6 (G 1000–G 1900 West Field) — Egyptological review

Source verified: PM III.1 2nd ed. (Málek, 1974), printed pp. 52–65 (physical pp. 49–62).

---

## P1 — merge-blockers

### P1-1. G 1607 `is_unfinished: true` is wrong (printed p. 65)

PM's headword block for G 1607 is `I‘AN, Overseer of the House of weaving women, etc. Possibly late Dyn. IV.` — there is **no `unfinished` token in the headword cluster**. The `unfinished` qualifier appears later in body prose: "Rock-cut tomb, unfinished." The chunk-6 prompt's literal-`Unfinished`-token rule fires only on the headword block; this row triggered the flag on body prose. Compare row G 1452+1453 (`Mastaba with rubble core encased in brick walls` — same body-prose register, correctly NOT flagged). Wrong-data risk into Phase-A: a downstream consumer filtering "completed tombs" will lose Iʿan, whose chapel is unfinished but whose burial/statuary record is substantive. Revert to `false`.

### P1-2. G 1234 occupant_name `ʿAnkh-Haf` should be `ʿAnkh-haf` (printed p. 60)

PM prints `‘ANKH-HAF` in small caps; the Anglicising convention used elsewhere in this same chunk is lowercase-after-hyphen (cf. G 1227 `Sethiheknet` not `Sethi-Heknet`; G 1225 `Nefertyabt`; chunk-5 conventions). This is **the famous ʿAnkh-haf** (vizier under Khafre, MFA 27.442 reserve head — one of the most-catalogued Old Kingdom officials in Western collections, present in Boston/Brooklyn/Met cross-references). Capitalised `Haf` will miss museum-catalog matches that overwhelmingly print `Ankh-haf` / `Ankhhaf` / `ʿnḫ-ḥʾf`. Wrong-person matching risk is concrete. Normalise to `ʿAnkh-haf` and add aliases `["Ankhhaf", "Ankh-haf"]` to `occupant_alt_names`.

### P1-3. G 1221 `notes_from_pm` contains OCR-artifact stutter (printed p. 59)

Row 42 notes_from_pm: `"Shad (?) (?), Royal acquaintance. Probably Dyn. V."` — PM prints `SHAD (?)` once, followed by the hieroglyph block, then `Royal acquaintance.` The agents pulled `(?)` twice. Rule-1 / rule-6 (reconciled data is sacred): a value not in the source. Fix: `"Royal acquaintance. Probably Dyn. V."` — leave the headword `(?)` reflected only in `attribution_certainty: probable`, which is already correctly set.

---

## P2 — same-cycle preferred

### P2-1. G 1207 Nufer (woman) classified `Royal Family` (printed p. 58)

PM: `NUFER, Royal acquaintance (woman). Temp. Khufu or later.` `Royal acquaintance` (*rḫt-nswt*) is an **honorific court title held by non-royal women**, not membership in the royal family. The same misclassification did NOT propagate to G 1205 Khufunakht (`Royal acquaintance`, correctly `Official`) — so this is an inconsistent application of the role-derivation rule, not a systemic prompt error. Compare also G 1227 Sethiheknet (row 46), same title, also wrongly tagged `Royal Family`. Both should be `Official`. Recommend filing as a tracked sweep item if not fixed this PR.

### P2-2. G 1020 / G 1104 Mes-Sa, G 1204 Akhtihotp — `occupant_role: "Unknown"` despite named occupant

PM's printed headword for all three: just `MES-SA. Late Dyn. IV...` / `MES-SA. Late Dyn. V.` / `AKHTIHOTP. Middle Dyn. V or later.` — **no title cluster at all**. Per the prompt convention (a named occupant with no titles defaults to `Official`, not `Unknown`), these three need to be `Official`. `Unknown` is reserved for unnamed occupants (cf. correctly-tagged G 1011, G 1021 with no name AND no title). Same downstream-matching cost as P1-2: the Berkeley Hetepi/Renpetnefert statues (G 1020) are Berkeley-catalog-attested.

### P2-3. G 1314 `dynasty: "5"` but occupant_name null — KhaʿkareʿKHA‘KARE‘ architrave is the *identifier* of the tomb owner

PM p. 61: `G 1314. Second half of Dyn. V. Architrave with figure of Kha‘kare‘ repeated nine times.` The architrave names Khaʿkareʿ (continued on p. 62: `Double-statue, Kha‘kare‘, Hairdresser of the Great House...`). Row 53 has `occupant_name: null` — the name and title are on the next printed page, which the chunker presumably split mid-entry. Recover: `occupant_name: "Khaʿkareʿ"`, `occupant_role: "Official"`, notes from p. 62 prose.

---

## P3 — nits

- Row 33 G 1201 `Meḥyt` underdot-Ḥ: matches PM's printed `Meḥyt` (visible page 57). Correctly preserved.
- Raised-ayin glyph normalisation to U+02BF is correct in every spot-check (Shepseskafʿankh, Niʿankhmin, Kaemʿah, ʿAnkh-Haf, Zaduwaʿ, Iʿan). No issues.
- Cemetery banners: G 1000 (p. 52), G 1100 (p. 55), G 1200 (p. 56 bottom / p. 57 first row), G 1300 (p. 61), G 1400 (p. 64), G 1500 (p. 64 bottom), G 1600 (p. 65), G 1900 (p. 65) — all 54 rows assigned correctly.
- G 1452+1453 compound twin-row emission (rows 56-57, `shared_with_tombs` cross-refs) matches PM's compound headword `G 1452+1453. ZADUWA‘...` on p. 64. Correct.

---

## Verdict: FIX-AND-SHIP

3 P1s (1 wrong-data flag + 1 wrong-person-risk anglicisation + 1 reconciled-data fabrication) must land in this PR. P2 fixes preferred same-cycle but tractable as follow-up.
