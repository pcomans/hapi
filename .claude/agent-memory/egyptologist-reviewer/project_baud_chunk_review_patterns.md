---
name: Baud 1999 chunk-review recurring patterns
description: Recurring failure modes and judgment calls seen in Baud 1999 corpus chunk extraction that reviewers should watch for across future chunks
type: project
---

For Baud 1999 *Famille royale* Corpus chunk reviews, these patterns recurred across chunks 1-3 and are worth pre-loading when reviewing chunks 4-7:

**Why:** First-pass LLM extraction systematically under- and over-hedges Baud's prosopographical claims, systematically drops controlled-vocabulary roles when the title is unusual, and often conflates children_names from cross-referenced tombs with true children.

**How to apply:**

1. **`(per Baud)` vs `(probable)` distinction is subtle and LLMs collapse it.** Baud frequently *reports* Strudwick's / Schmitz's / Seipel's hypotheses with his own question mark attached. That is NOT `(per Baud)` — it's `(probable)` at most, or `null` + hypothesis in `notes_from_baud`. `(per Baud)` is reserved for cases where Baud himself asserts an inference on iconographic or titular grounds. Override #4 (baud-33) promoted a Strudwick hypothesis that Baud was questioning to "per Baud" — wrong direction. Chunk-3 example: baud-87 father "Ptḥ-špss (per Baud)" is actually Schmitz's proposal that Baud reports.

2. **Inscribed titles are attestations, not probabilities.** If a queen's title list contains `mwt nswt Ḏd-ꜥnḫ-Nfr-kꜣ-Rꜥ`, that's an attested filiation to Neferkare — not `"Néferkarê (probable)"`. Look for hedge-markers on attested inscribed titular claims; strip them. (baud-36 pattern.)

3. **Service-personnel `roles: []` is almost always a miss.** When `service_personnel: true` and the title list contains named-royal elements (`wꜥb mwt-nswt`, `jmj-r pr-šnꜥ` attached to a named queen's complex, `ḥm-nṯr Ḫwfw`), the controlled vocab usually has a role for it. `[]` is valid only when the titles are pure administrative with no royal-cult or household-service marker. (baud-20 pattern.)

4. **Ḥm-nṯr / wꜥb of named king or pyramid → `priest of the royal pyramid`.** Apply consistently. Agents tend to drop this when the title is embedded in a longer list.

5. **`jmj-r prw msw nswt` / `jmj-r sbꜣ n msw nswt` = "steward of the king's children".** Chunk-2 seeded into vocab. Chunk 3 uses it correctly (baud-95, baud-103).

6. **French-form regnal names in kinship fields will need Phase-A reconciliation.** `Rêkhaef`, `Snéfrou`, `Pépi Iᵉʳ`, `Téti`, `Merenrê`, `Niouserrê`, `Djedkarê`, `Ounas` all live in `father_name`/`spouse_names`/`children_names`/`date_attested`. Don't "fix" these during chunk extraction — normalization is Phase A's job against pharaoh.se.

7. **Override rationales should not overstate certainty.** Anglicisation corrections have multiple live conventions. Log anglicisation fixes as "provisional pending pharaoh.se reconciliation".

8. **"king's eldest son of his body" systemic mis-assignment.** Vocab term requires BOTH `smsw` (eldest) AND `nj ẖt.f` (of his body) in the title list. Extraction agents frequently assign the role when only one marker is present. Audit every row carrying the role. Chunk 3: baud-117 correctly dropped (smsw only). But baud-114 retained it based on `zꜣ nswt smsw nj ẖt.f` — correct. baud-104 has `zꜣ nswt nj ẖt.f smsw` and `zꜣ nswt smsw` AND `zꜣ nswt nj ẖt.f smsw` — correct.

9. **Reign-date is not father_name.** A monument dated to a king's reign does NOT imply a father-son filiation. Do not promote dating evidence to kinship in the structured field.

10. **Priestess of a goddess ≠ priest of the king's wife.** `ḥmt-nṯr Ḥwt-Ḥr` / `ḥmt-nṯr Nt` are priestesses of Hathor / Neith (goddesses). They do not justify `priest of the king's wife` in roles.

11. **`priest of the king` vocab is being over-triggered by `ḥm-nṯr <kingname>` alone.** Watch for queens/princesses with `ḥmt-nṯr Ḫwfw` being assigned `priest of the king` — this is a priestess-of-the-royal-cult title, functionally distinct from service-personnel `priest of the king`. Chunk 3 examples: baud-86, baud-93 both have `priest of the king` role attached to a king's-daughter with `ḥmt-nṯr Ḫwfw`. Reviewer should decide whether this is correctly mapped or whether priestly-royal-cult titles on family members should NOT promote to service-personnel-style role.

12. **children_names should not include subjects of a son's tomb where the entry is the parent represented there.** Conversely, cross-references where entry X is shown "chez son fils Y" means Y is a child of X — that IS valid back-inference. E.g., baud-85 correctly lists Kꜣ.j-wꜥb via doc. 2. But "(per Baud)" there overstates — Baud says "si la reconstitution de Smith est exacte" = hypothesis, → `(probable)` not `(per Baud)`.

13. **Meretites I anglicisation.** Baud's `Mrt-jt.s Iʳᵉ` is the well-known "Meritites I" of Khufu. Both "Meritites" and "Meretites" are live conventions; museum catalogues (Met, Boston MFA) prefer "Meritites". Provisional anglicisation should use whichever form pharaoh.se adopts; flag for Phase-A reconciliation.

14. **`smsw jzt` is NOT the `smsw` of `king's eldest son of his body`.** `smsw jzt` = "eldest of the chamber/staff", an administrative office; `zꜣ nswt smsw` = "eldest king's son", a kinship marker. Rule-8's AND-test must check for `smsw` *adjacent to* or conjoined with `zꜣ nswt` / `nj ẖt.f` in the SAME title, not both markers scattered across a title list. Chunk-4 misses: baud-143, baud-151, baud-158. Correct retentions: baud-133, baud-134, baud-157 (all have `zꜣ nswt smsw nj ẖt.f` as a single title).

15. **Hordjedef / Ḥr-ḏd.f "king's eldest son" is traditional, not titular.** Baud records only `zꜣ nswt nj ẖt.f` for him, no `smsw`. Tradition knows him as Khufu's firstborn sage; that is LITERARY/later-reception evidence, not Old Kingdom titulary. Do not auto-promote the eldest-son role for him regardless of reputation. Same caution applies to other famous figures with modern "firstborn" reputations.

16. **Parenthetical caveats in structured list values break downstream matching.** E.g., baud-155 `spouse_names: ["Mr.s-ꜥnḫ II [75] (hypothèse controversée)"]`. Structured-list caveats must use the controlled `(probable)` / `(per Baud)` suffix ONLY, or null + note. Free-form French parentheticals in value strings will not match Phase-A reconciliation.
