# Ruler escalation queue — audit and work-off (2026-10-12)

**Result.** After the queue was worked off (ADR-020 amendment 2026-10-12), ambiguous ruler
mentions on the #337 ledger fell from **689 to 62**: 627 now resolve to one king, no mention
that resolved before resolves to a different king, none became ambiguous. Approved links
354 → 429; parked pairs 974 → 890. An Egyptologist review of every merge found no false
merge (`results/merge-review.md`). Details in [After the work-off](#after-the-work-off);
the audit below is the state before (commit a4ab486).

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

## After the work-off

The matcher and reviewer changes are ADR-020 amendment 2026-10-12, items 1–5. The graph was
rebuilt with DeepSeek V4.1 Flash via the Vercel gateway (`build_graph --provider vercel
--fresh`, ~1,230 reviewer calls). The code-review fixes that followed are deterministic
guards over the stored verdicts, applied by rebuilding from the verdict cache with no model
call. `scripts/measure_rebuild.py` ran the #337 resolver over the same frozen ledger against
the graph on main (9402974) and the rebuilt one. Output: `results/rebuild.json`, with every
merged cluster, the edges that join it, and every link main approved that is no longer
approved.

| | Before | After |
|---|---|---|
| Approved links | 354 | 429 |
| Parked pairs | 974 | 890 |
| Identity clusters | 160 | 190 |
| Ambiguous ruler mentions | 689 | 62 |
| Resolved ruler mentions | 8,279 | 8,906 |
| Resolved mentions moved to a different king | — | 0 |

Newly resolved: Psusennes I 309, Amenhotep II 129, Thutmose IV 62, Apries 41, Ramesses III
40, Thutmose II 29, Necho II 5, Userkaf 4, Kashta 3, Osorkon II 2, and one each for Intef II,
Intef III and Rudamun.

Still ambiguous (62): Djoser 48. Beckerath's record has no Horus name, so only the
king-name route applies, and it needs both reign windows overlapping; Leprohon gives none
and pharaoh.se is 28 years off. The rest: Teti / Aha / Sekhemkhet 4, Shabaka 2 (a reused
throne name, Neferkare, held by the homonym guard), Amenhotep I/II/III 2, and one each for
Xerxes I, Iuput II, Smendes I, Sobekhotep III, Menkheperre / Necho I, and Aha / Djet / Iti /
Ity.

Links main approved that are no longer approved (4, all escalated, in the queue):
Senakhtenre (Leprohon 17.26 and pharaoh.se against Ryholt 17.7 "Siamun (?)") and Seqenenre
Tao (Leprohon 17.27 and pharaoh.se against Ryholt 17.8; the sources print different Horus
names). The Egyptologist judged all four the same king and the escalations defensible.

**Review.** The `egyptologist-reviewer` checked all 58 merged clusters of the graph before the guards (51 remain, each a subset of a reviewed one):
no false merge (`results/merge-review.md`). It raised two P1s, fixed here: the reviewer
*rejected* Senakhtenre on Ryholt's uncertain "Siamun (?)", so a rejection touching a reading
its source flags uncertain is now escalated (item 5); and `name_dynasty` edges joining
records that both carry throne names (Beckerath's German transcriptions the normaliser does
not equate) are now described correctly in the ADR.

The `code-reviewer` then found the king-name route enforced only by the prompt: the stored
run approved Radjedef, Userkare, Shepseskaf, Sahure and others with a missing or
non-overlapping reign window. Now enforced in code (item 1): both windows known, overlapping
by at least half the shorter, same regnal number; 7 approvals were downgraded. Also fixed:
a listed reused throne name shared in full stays trapped beside an unlisted compound
(Shabaka); a later Horus name needs no conflicting regnal number; regnal numbers are read
from Leprohon's "(I)" and "III (a)" forms; a clash with a rival of unknown dynasty stays
escalated; and a `name_only` pair is escalated ahead of the verdict cache (a cached verdict
from an earlier basis had approved one). Every link approved now was among those the
Egyptologist reviewed. Excluding Dyn 21–24 from the king-name basis was measured and not
adopted: 374 ambiguous mentions instead of 62 (`results/alternative-exclude-dyn-21-24/`).
The window rule does not cover the case it was meant for: Beckerath's and pharaoh.se's
"Shoshenq IV" are different kings with overlapping dates and the same numeral, so for a
record without a throne name there the reviewer is the only defence. The project owner
accepted that risk on 2026-10-12 (ADR item 1).

**A discarded first rebuild.** The first reviewer policy (audit rounds 1–3) applied the
reign-window and regnal-numeral checks meant for the king-name route to every pair. The
model then escalated 97 throne-name links it approves on main (Khafre, Senwosret I–III,
Amenhotep III, Ramesses V–XI …) because chronologies differ by decades or a window was
missing. That run is kept in `results/discarded-round-3/` (graph, full reviewer run, and its
measurement, which lists the 97 links). The policy was split into three explicit routes,
re-audited (rounds 4–5, `prompt-audit-2026-10-12.md`) and the graph rebuilt. During that
rebuild one call timed out three times and the run stopped, as designed; the timed-out
attempts are in `results/aborted-attempts-2026-10-12.jsonl`, and the run was resumed from
the verdict cache.

**Follow-ups (not in this change).** Beckerath, Kitchen, Leprohon and pharaoh.se print "(?)" readings
without a typed flag, so item 5 covers Ryholt only until the flag is added upstream (#352). The
normaliser keys "mery ib ra" and "Mer ib Ra" differently, which leaves Meryibre Khety
`name_only` (#353). pharaoh.se's Ptolemy V row is column-shifted (#354), and its
Qemau-Siharnedjheritef carries the alt label "Amenemhat VI" (Ryholt 13.8; #355).
`regnal_number_of` reads only a trailing numeral, so an epithet ordinal ("Soter II") can
stand in for the king's number (#356; no current pair affected). Queens have no authority
entries.

## Reproduce

The graph is replayed, not re-reviewed: `web-claimgraph/data/claim-graph.reviewer-run.jsonl`
holds every reviewer interaction, and `test_committed_decisions_follow_from_the_run_and_the_current_matcher`
re-derives every committed decision from it with the current matcher and guards (Rule 13).
The 13 paid verdicts on pairs the final matcher calls `name_only` (so never reviewer-decided)
are kept in `results/superseded-by-name-only.jsonl`.

```bash
pipeline/.venv/bin/python docs/evaluations/ruler-escalation-queue/scripts/audit_escalations.py \
  --ledger <#337 run>/mentions.ndjson.gz --extraction-manifest <#337 run>/extraction-manifest.json \
  --graph web-claimgraph/data/claim-graph.json \
  --out docs/evaluations/ruler-escalation-queue/results/escalation-queue.json

git show 9402974:web-claimgraph/data/claim-graph.json > before-graph.json
pipeline/.venv/bin/python docs/evaluations/ruler-escalation-queue/scripts/measure_rebuild.py \
  --ledger <#337 run>/mentions.ndjson.gz --extraction-manifest <#337 run>/extraction-manifest.json \
  --before-graph before-graph.json --after-graph web-claimgraph/data/claim-graph.json \
  --out docs/evaluations/ruler-escalation-queue/results/rebuild.json
```

`results/escalation-queue.json` now describes the rebuilt graph (890 pairs, 62 ambiguous
mentions; it adds the park reasons `king_name_route` and `uncertain_reading`); the 974-pair audit above is that file
at a4ab486.
