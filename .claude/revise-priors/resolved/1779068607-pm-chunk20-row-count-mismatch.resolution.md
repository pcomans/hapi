# Resolution: PM III.2 chunk-20 prompt expected-count corrected

The marker (correctly) flagged that the prompt's `## Expected row count` section enumerated 8 named primaries but the chunk file actually contains 15–16 Shape-1 headwords across pp.148–164. Agent A extracted 15, agent B extracted 16, agent C extracted 8 (the C agent followed the prompt's explicit list).

## Decision

**Option (b): update the prompt's expected-count section.** Keep the chunk file as-is (phys pp.148–164, stopping just before the Mereruka mega-block on phys p.165). Bump the expected count from 8 (band 6–10) to 15 rows (band 12–18) and add a paragraph documenting the Drioton-1943 Dyn-VI mastaba cluster (Wernu, Khui, Thetut, Desi, Semdent, Meru Tetisonb, Gemniwser) that the original scan missed.

This honors Constitutional Rule 1 (scholar-grade source-traced): every PM-headworded named tomb in the printed page range gets a row, no silent drops.

The anonymous `TOMB WITH SEVERAL BURIAL CHAMBERS` (phys p.156) and `NAME LOST` (phys p.161) entries are deliberately excluded from chunk-20 scope and land in a follow-up chunk together with the Mereruka mega-block on phys p.165+ — documented in the prompt's new "Anonymous-row scope rule" section.

## What was changed

`pipeline/pipeline/authority/sources/porter-moss-memphis/prompt-chunk-20.md`:
- Replaced the 8-row expected-count paragraph with a 15-row paragraph naming the Drioton Dyn-VI cluster
- Added an "Anonymous-row scope rule" section pinning the deliberate exclusion of the two anonymous entries

The 3-agent vote stands: agents A (15) and B (16) form a 2/3 majority on the Drioton cluster extras; agent C (8) is out-voted on those rows. `merge.py` will route the 7 extras through majority-vote successfully.

Resolved 2026-05-18 by main agent under the user's standing `keep working until PM Vol III is 100% done` directive.
