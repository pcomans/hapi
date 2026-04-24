# Reviewer notes — sweep 2026 (PM I.2 current source)

Scope read: `README.md`, `transcribe.md`, `reconciled.jsonl`, `reviewer-notes-chunk7.md`, `reviewer-notes-chunk8.md`, `code-review-chunk7.md`, `code-review-chunk8.md`, and raw text-layer chunks. Spot-checked against the PM I.2 PDF text/pages for KV1, KV13, KV14, KV22, KV46, KV55, KV62, SWV-HatshepsutSouth, SWV-ThreePrincesses, DAN-KamosiWazkheperre, DAN-MentuhotpIWifeOfDjhuti, DAN-Aqhor, QV38, QV47, QV74, QV75, and QV § X.B. I did not duplicate the already-filed chunk-7/chunk-8 findings except where the current `reconciled.jsonl` still raises a distinct issue.

## P1

None found in the current 75-row file. Previously flagged P1/P2 chunk-7 and chunk-8 issues appear applied: `DAN-Aqhor` is now `ʿAḳ-hor`/`Official`, `DAN-AhmosiNefertere` has the Carter/Černý attribution note, `DAN-MentuhotpIWifeOfDjhuti` restores `Ḍḥuti`, QV38 has `is_unfinished=true`, QV47 has `Sit-ḍḥout`, and QV74 has the footnoted kinship data.

## P2

- **QV § X.B scope contradiction / missed unnumbered tombs.** README chunk 8 says § X.B "Unnumbered tombs and pits" is out of scope as find-level inventory, but PM p.769 includes tomb-level headwords: "QUEEN MUT..." west of Tomb 66, "PRINCESS NEFERḤET..." probably south-east of Tomb 75, and "TOMB OF PRINCESSES, temp. Amenophis III. Position unknown." These are not merely object-list rows; at least Queen Mut/Tuy and the Tomb of Princesses are named tomb/group-tomb entries in a tomb section. Either add descriptor-id rows or narrow the README scope to "numbered QV tombs only" so the omission is intentional and auditable.

- **KV46 overstates royal-family status.** PM p.562 prints "Yuia ... Divine father, and Thuiu ..., Chief of the harim of Amun, parents of Queen Teye." The row has `occupant_role: "Royal Family"`. PM gives court titles and a relationship to a queen, not membership in the royal family. Suggested: use `Official` (or split if the schema ever supports per-occupant roles). This is source-fidelity, not general-knowledge enrichment.

## P3

- **QV74 `notes_from_pm` mixes PM wording with editorial prose.** PM p.767 footnote prints the three claims as bibliographic sentences ("Wife (?)...", "Mother...", "Daughter..."). Current notes compress them and add "(per PM p.767 footnote 1)", which is useful provenance but not PM wording despite README's "notes_from_pm is verbatim-preserve" policy. Either rename/loosen the field semantics or make QV74 a closer PM-fragment paraphrase without editorial citation text.

- **Known-current nonblocking checks.** KV13 Bay as `Official`, KV14 Tausert with Setnakht usurpation in notes, KV22/KV23 West Valley, KV55 hedged Amenophis IV, KV62 Carter/Carnarvon, SWV-HatshepsutSouth as queen-consort, and QV38/QV47/QV75 all match the cited PM headwords well enough for this extract's conventions.
