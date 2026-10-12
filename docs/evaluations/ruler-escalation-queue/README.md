# Ruler escalation queue — audit (2026-10-12)

**Why:** the #337 re-registration lost correct ruler matches that plain text makes (Apries,
Userkaf), because the claim graph keeps one king's records from different sources apart.
This audit measures why: every pair the matcher parked as "escalated", the evidence the
pair carries, and the museum mentions each parked pair leaves ambiguous.

`scripts/audit_escalations.py` recomputes the candidates and uniqueness-clash groups with
the committed matcher (they must equal the committed graph's escalations) and runs the #337
ruler resolver over the frozen #337 mention ledger against the committed graph. No model
call. Output: `results/escalation-queue.json` (authority pairs and aggregate counts only).

## The queue: 974 parked pairs, against 354 approved links

| Why parked | Pairs | What happened |
|---|---|---|
| `name_only` | 735 | No throne or Horus name in common; escalated by policy, never reviewed |
| `uniqueness_clash` | 116 | Reviewer approved; overridden because a record also matched a second record of the other source |
| `homonym_list` | 77 | Reviewer approved; overridden because a shared throne-name key is on the reused-name list |
| `reviewer_escalated` | 46 | The reviewer itself declined |

Why so many are `name_only`: 302 of the 1,159 ruler records carry no throne name and no
Horus name at all (Kitchen 34 of 60, Beckerath 67 of 166, Leprohon 80 of 395, pharaoh.se
85 of 381, Ryholt 36 of 157), so throne-name corroboration is impossible for them; and a
Horus-name match counts only in Dynasties 0–3.

## What it costs the museum side

All 689 ambiguous ruler mentions on the #337 ledger (of 11,555), by the targets they are
ambiguous between and why those targets are kept apart:

| Targets | Mentions | Parked as |
|---|---|---|
| Psusennes I | 309 | name_only |
| Amenophis II. / Amenhotep II | 129 | uniqueness_clash |
| Thutmose IV | 62 | homonym_list |
| Djoser / Netjerikhet/Djoser | 48 | name_only |
| Apries | 41 | name_only |
| Ramesses III | 40 | name_only |
| Tuthmosis II. / Thutmose II | 29 | uniqueness_clash |
| Nekau II / Necho II | 5 | name_only |
| Userkaf | 4 | name_only |
| Teti / Aha / Sekhemkhet | 4 | name_only |
| Kashta | 3 | name_only |
| Shabaka | 2 | homonym_list |
| Osorkon II | 2 | name_only, uniqueness_clash |
| Amenophis I. / Amenophis III. / Amenhotep II | 2 | name_only |
| Iuput II | 1 | name_only |
| Sobekhotep III | 1 | homonym_list |
| Xerxes I | 1 | name_only |
| Intef III | 1 | name_only |
| Intef II | 1 | name_only |
| Aha / Iti / Djet / Ity | 1 | none |
| Smendes I | 1 | name_only |
| Menkheperre / Necho I | 1 | name_only |
| Rudamun | 1 | homonym_list, name_only |

Root causes in the largest groups:
- **Psusennes I, Apries, Necho II, Kashta** (358 mentions): Kitchen's rows carry no throne
  name, so they can only ever be `name_only`.
- **Amenhotep II, Thutmose II** (158): pharaoh.se lists Amenhotep II's variant throne name
  Aakheperuenre. Its skeleton key drops the plural `w` and becomes `khprnr`, which is
  Thutmose II's Aakheperenre, so pharaoh.se's Amenhotep II "matches" two Beckerath kings
  and both approvals are overridden as a clash.
- **Thutmose IV** (62): both records share the full throne name Menkheperure and the Horus
  name Kanakht-tutkhau, but the skeleton `mnkhprr` collides with Thutmose III's listed
  Menkheperre, and the pair is overridden.
- **Ramesses III, Userkaf** (44): the full Horus names match (Kanakht-aanesyt; Irimaat),
  but a Horus name only counts in Dynasties 0–3, and the throne names differ in romanization
  (`weser` vs `user`; `mry` vs `mri`).
- **Djoser** (48): Beckerath's row has no titulary; Leprohon's has only the Horus name.

## Reproduce

```bash
pipeline/.venv/bin/python docs/evaluations/ruler-escalation-queue/scripts/audit_escalations.py \
  --ledger <#337 run>/mentions.ndjson.gz --extraction-manifest <#337 run>/extraction-manifest.json \
  --graph web-claimgraph/data/claim-graph.json \
  --out docs/evaluations/ruler-escalation-queue/results/escalation-queue.json
```
