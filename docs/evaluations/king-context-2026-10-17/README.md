# Kings resolved in their record's context (2026-10-17)

**Why.** The per-museum ruler test (`../ruler-per-museum-2026-10-17/`) found the Met's "Aya" records
linked to the Dynasty 13 king Merneferre Aya. The Met writes "Aya" for him and for the Dynasty 18 Ay,
whom the authority spells "Ay", so the name alone matched only the Dynasty 13 king. Kings were
matched on spelling alone; only royal women used the record's dynasty. The owner asked that king
matching use the record's dynasty and date (2026-10-17).

## The rule (`pipeline/pipeline/authority/king_context.py`)

1. **The record's dynasty chooses among kings of one name.** Dynasty 6 picks King Teti over Aha
   and Sekhemkhet, whom other king lists also call Teti.
2. **A king clashes with a record only when the dynasty and the date both disagree.** The
   record's single dynasty is not one the king lists give the king, *and* the record's date range
   lies more than 50 years outside his reign. Either alone is not enough (owner's choice,
   2026-10-17, after the code and Egyptology reviews):
   - **A dynasty number depends on the chronology a museum follows.** The Met puts Takeloth II in
     Aston's Theban Dynasty 23. Of the authority's four entries for him, Beckerath's, Leprohon's
     and Kitchen's say 22 and pharaoh.se's says 23. They were never merged, and the Met's spelling
     reaches only Kitchen's.
   - **Museum dates are loose.** 191 Met records of "reign of Ramesses IV" carry the single year
     1295 BCE.
3. **A museum's reign field drops a clashing king.** It dates the object to the reign.
4. **A title cue never drops a king for clashing.** Objects can postdate the king they name: scarabs
   bearing Thutmose III's name were made for centuries. The exception is a king the same record's
   reign field dropped: the record has said the object is not of his reign.
5. **Otherwise the name alone decides.** Without context, a name links only when one king has it
   (owner's choice).

A record date range that ends before it starts (a Met "664–380 B.C." stored as 664–712 BCE) is the
museum's error and is read as no date.

## Effect on the frozen inputs (`results/measure.json`, `scripts/measure.py`)

The same mentions and records as the per-museum test's frozen run. 12 Met mentions change; no other
museum changes. By record link:

| Change | Records | Reading |
|---|---|---|
| "Aya" → the Dynasty 13 king: link removed | 7 (met-550059, -550075, -557077, -557785, -557786, -557787, -567754) | all Dynasty 18 records, c. 1327 BCE. They include the three the per-museum test's reviewers opened and found to be Ay; none of the three they found to be Merneferre Aya is removed. On met-557077 the title's "Aya" goes with the reign field's (rule 4). |
| "Teti" → King Teti (Dynasty 6): link gained | 2 (met-543897, -543922) | the name was ambiguous between three kings |
| "Amenhotep II": link removed | 1 (met-549239) | the record's dynasty field says 19 and its date 1279 BCE, about 120 years after his reign. Both disagree with the reign field. |

- **One more mention changes but stays unlinked.** The Met's "pontificate of Menkheperre" on a
  Dynasty 21 record no longer has Necho I among its candidates (#338's re-run proof, below).
- **Met–Walters stays qualified.** met-549239 is one of the Met records in the 2026-10-16
  re-registration's Met–Walters and Met–Cleveland *retained controls* for Amenhotep II (case-070,
  case-032). The other records of those controls keep the link. The changed cases that decided the
  qualification are untouched.
- **The Mentuhotep III problem is untouched.** The Met's "Mentuhotep III" on records of Nebhepetre
  Mentuhotep II is a king of the record's own dynasty and period. This rule cannot catch it.

**Tuned-on records.** These records are now tuned on, and a later test of the Met counts them apart:
- the seven Aya records;
- the two Teti records;
- met-549239.

## What is still unlinked among the kings

59 king mentions stay ambiguous:
- **56 have candidates that share a label** (Djoser 48, Shabaka 2, and one each of Iuput II,
  Sobekhotep III, Xerxes I, Smendes I, Menkheperre and Alexander the Great). These are mostly one
  king entered by two king lists, but not always. The two Menkheperre entries are the High Priest
  of Amun (Leprohon 21a.02, Kitchen 21H.07). pharaoh.se's Shoshenq VI is not Kitchen's (Egyptology
  review). So merging them needs each identity checked against sources, not their labels.
- **3 have candidates that are all labelled apart.**

## Other code

- **The #338 promotion proof** (`../authority-bridge-338/`) now passes each record's dates. Both
  its scripts were re-run with this code (`rerun-after-king-context/`), and a test holds them to
  the previous re-run:
  - only the ruler figures this measurement reports changed;
  - every other figure, sites and tombs included, is the same;
  - every changed ruler mention is #369's or this rule's.

  The re-run also corrects a stale label that #383 left behind: the qualified ruler scope is
  credited to the 2026-10-16 re-registration, not #361.
- **#369's measurement script** (`../resolver-gaps-369/scripts/measure_resolver_change.py`)
  calls the resolver as it was then, so it no longer runs on this tree. Its committed result
  records that code; its tests read the result, not the script.
