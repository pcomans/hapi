# Kings resolved in their record's context (2026-10-17)

**Why.** The per-museum ruler test (`../ruler-per-museum-2026-10-17/`) found the Met's "Aya" records
linked to the Dynasty 13 king Merneferre Aya. The Met writes "Aya" for him and for the Dynasty 18 Ay,
whom the authority spells "Ay", so the name alone matched only the Dynasty 13 king. Kings were
matched on spelling alone; only royal women used the record's dynasty. The owner asked that king
matching use the record's dynasty and date (2026-10-17).

**The rule** (`pipeline/pipeline/authority/king_context.py`):
- The record's single dynasty decides. For a museum's reign field, which dates the object to the
  reign, a king of another dynasty is never linked.
- A title cue ("Scarab of King …") may postdate the king, so there the dynasty only chooses among
  kings of the name and never refuses the one king the name gives.
- Dates only break a tie between different, dated kings of the name.
- Without context, a name links only when one king has it (owner's choice).

**Why dates decide so little.** The museums' dates are not precise enough to refuse a link:
- 191 Met records of "reign of Ramesses IV" are Dynasty 20, as he is, but carry the single year
  1295 BCE;
- early chronologies differ by up to two centuries;
- 142 records have a date range that ends before it starts, and these are read as no date.

Most remaining ties are not between different kings. They are one king entered twice by different
king lists (Djoser as `beckerath-03.02` and `cluster-leprohon-leprohon-3.01`). Picking one entry by
its dates would be arbitrary, so these stay ambiguous until the authority merges them.

## Effect on the frozen inputs (`results/measure.json`, `scripts/measure.py`)

13 Met mention changes; no other museum changes.

| Change | Mentions | Reading |
|---|---|---|
| "Aya", Dynasty 18 reign field: link to the Dynasty 13 king removed | 7 | the wrong link the test found |
| "Teti", Dynasty 6: now King Teti, not Aha or Sekhemkhet | 3 | a correct link gained |
| "Amenhotep II" and "Ramesses IV" reign fields on Dynasty 19 records: link removed | 1 + 1 | the Met's reign and dynasty disagree |
| "Takeloth II", Dynasty 23: link removed | 1 | probably a correct link lost: his dynasty is disputed (22 in Kitchen, the only list that holds him; 23 in others) |

The Met's "Mentuhotep III" problem is untouched. Those records name a king of their own dynasty,
and only the dates could tell the kings apart, which they cannot be trusted to do.

**What is left ambiguous among the kings:** 59 mentions. 56 of them are one king entered twice
(Djoser 48, Shabaka 2, and single cases of Iuput II, Sobekhotep III, Xerxes I, Smendes I,
Menkheperre and Alexander the Great); 3 are different kings. Merging those duplicates in the
authority, with sources, is its own work item.

The Aya and Teti records are now tuned-on records: a later test of the Met counts them apart.
