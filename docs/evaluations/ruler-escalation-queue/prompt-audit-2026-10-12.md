# Reviewer policy change — leak audits (Rule 14), 2026-10-12

The claim-graph reviewer's `SYSTEM_PROMPT` (`pipeline/pipeline/authority/claimgraph/reviewer.py`)
gained the approval routes of the ADR-020 amendment 2026-10-12. Audited by the
`prompt-auditor` agent on five exactly composed requests (system + user): Psusennes I
(Kitchen, no titulary) vs pharaoh.se, Amenophis II (Beckerath) vs Amenhotep II
(pharaoh.se), Ramesses III, Userkaf, Apries (Beckerath vs Kitchen).

| Round | Verdict | Findings acted on |
|---|---|---|
| 1 | **FAIL** (P2 ×2) | The new route made dynasty and regnal numerals load-bearing, with "consistent reign dates" undefined; "forms that cannot be compared" let any differently transliterated pair fall through to the name-and-dynasty route. Auditor's rewrites applied; transliteration differences declared not to be incomparability; the code comment now records that the policy is deliberately route-shaped |
| 2 | **FAIL** (P2 ×2) | "substantially overlap" vs "partial → ESCALATE" contradicted itself (nearly every cross-source pair overlaps partially); "a numeral in one record only … REJECT" contradicted "numerals are convention-relative". Auditor's rewrites applied verbatim |
| 3 | **PASS** (no P0/P1/P2) | none |
| 4 | **FAIL** (P2 ×2) | Run on the full candidate set, the round-3 text escalated 94 throne-name pairs the main-branch prompt approved (non-overlapping or unknown windows) and 3 more over differing numerals, because the window and numeral conditions had been written for the king-name-only route. The revision split the policy into three routes. Round 4 found: route (1) contradicted the "Prenomen reuse … weigh reign window" bullet, and "non-overlapping" was unbounded; route (1) as drafted could approve a reused throne name across distinct same-dynasty kings (consistent dynasty and conflicting titulary undefined, window and numeral signals neutralised). Applied: route (1) requires the same dynasty (or one a different convention places adjacent) and no field pointing to a different king; windows bounded to an offset of a few decades; numerals that distinguish two kings sharing a throne name and windows separated by more than a chronology offset are reasons to escalate; the reuse bullet weighs birth name, Horus name, dynasty and any window gap beyond a chronology offset; route (2) gained the consistent-dynasty and no-conflicting-field conditions; the numerals/dynasty bullet now says "weak as sole evidence" and defers to routes (1) and (3). Two deviations from the auditor's rewrite were judged in round 5 |
| 5 | **PASS** (no P0/P1/P2) | none. Twelve real composed requests (throne-name pairs with a ~37-year window offset and with differing numerals, Greek vs Egyptian birth names, no-titulary Kitchen records, reused-throne-name pairs across dynasties, an early-dynastic Horus pair) were read against the policy; none is pushed to a wrong answer. Deviations accepted: an extra throne-name variant or epithet does not point to a different king; a Greek vs Egyptian rendering of a birth name is not a different name |

No leak in any round: no king, spelling or listed homonym is named, and the user prompt
still carries no stage-1 basis or shared key (both pinned by existing tests in
`pipeline/tests/test_claimgraph_matcher.py`). Accepted P3s: a pair corroborated by a later
Horus name plus the king name has no reign-window check (by design, ADR amendment); regnal
numerals are parsed from display names, which is noisy. Round-5 accepted P3s: route (1) gives
no criterion for when a numeral difference is "only by numbering scheme" (agreement of throne,
Horus and birth names is what a careful model uses); a pair whose only shared field is the
throne name, with an unknown window and no birth name on one side, would be approved (rare in
the loaded sources); the Greek-vs-Egyptian and throne-name-variant allowances rest on the
model's Egyptological knowledge; route (2) says "consistent dynasty" without defining it for a
Dynasty "0" vs 1 Horus pair.

Audited `SYSTEM_PROMPT` SHA-256 (UTF-8): `6dbd56fc9556dc969fa6d50f47569fc8e5c553b911b28ce4a59a35dc5f98f9fe`
(computed by the caller; the auditor had no shell and did not recompute it)
