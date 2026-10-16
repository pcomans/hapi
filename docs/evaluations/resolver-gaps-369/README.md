# #369: the resolver gaps the #361 ruler re-registration found

#361 (`../ruler-reregistration-2026-10-15/`) found three gaps and left them unfixed, so that
the authority was not tuned on the cases it was judging. This change fixes them on `main`. The
#361 result does not move, because #361's comparison runs on its frozen `BASE_COMMIT` tree.

## The fixes

1. **A phase of one dynasty is read as that dynasty** (`royal_women.single_dynasty`). For
   example "second part of Dynasty 11", "mid-Dynasty 18" and "Dynasty 12, early-mid". The forms
   accepted are those found in every dynasty value of the 2026-08-27 corpus. Ranges, doubts,
   styles, approximations and named periods still give no dynasty.
2. **A bracketed numeral can be a source's own count** (`graph_kings`). The rule applies when
   the same king also bears the name under a different plain numeral. Leprohon's
   "Ahmose (II)" for the Dynasty 18 founder is the only such label in the graph, and it no
   longer matches a mention's "Ahmose II".
   - Such a mention, which usually means Amasis, now stays unmatched. No claim-graph label
     calls Amasis "Ahmose II": pharaoh.se's alt_labels do, but the graph does not take alt
     labels.
3. **A king named as the queen's relative in her own field counts as named by the record**
   (`royal_women.stated_kin_names`, used by `resolve_ruler_mention`). Examples are "Queen
   Ahmose, Mother of Hatshepsut" and "Hatshepsut's Mother, Queen Ahmose".

## What it changes

`results/resolver-change.json` was made by `scripts/measure_resolver_change.py`. It ran on the
frozen corpus archive and #361's mention ledger, using the base tree and the working tree with
all three fixes in force together.

| Inputs compared | Changed |
|---|---|
| Distinct dynasty values | 45 of 696, covering 217 records. Each went from no dynasty to one dynasty; no value is read differently. |
| Distinct single-identity ruler mention texts, resolved among the kings | 0 of 232 |
| Dodson & Hilton family names, resolved among the kings | 0 of 102 |
| Royal-woman-cued single-identity ruler mentions | 2 of 194 |

## Tuned on #361's deciding case (disclosed)

The two changed cued mentions are Brooklyn 3634 and Met 566763. These are the two "Queen
Ahmose" records, and they now resolve to Dodson & Hilton's Ahmes B through Hatshepsut.

They belong to #361's Ahmose e. #361's README says its verdict hangs on that case. The rule is
general, but in this corpus its only effect is on that evaluated case. **The next registration
on Met–Brooklyn must flag both records as tuned-on, or leave them out.** Counting the resulting
queen-to-queen link as a gain would score the fix on the case it was found from.

The Brooklyn Neferu record ("second part of Dynasty 11"), #361's one d, is unchanged. Neferu I
and II are both of Dynasty 11, and nothing on disk dates a woman within a dynasty, so the record
stays ambiguous.

## Known limits

- **A stated relative counts only if the king authority resolves the name.** The claim graph has
  no "Tao I", "Tao II" or "Taa II". So Queen Inhapi's stated relatives add nothing, and neither
  do Dodson & Hilton's own "Taa II" family links.
- **Some phrasings are not read.** "Great Royal Wife of X", "wife and sister of X", "wife of King
  X", "Mother of X, Queen Y" and a relative's name followed by a bracket are all left unread.
  These forms only ever lose a match; they never make a wrong one.
- **The older resolver keeps the bug.** The linkability script's own resolver
  (`run_linkability.py`, hash-pinned by earlier evaluations) does not have rule 2.
