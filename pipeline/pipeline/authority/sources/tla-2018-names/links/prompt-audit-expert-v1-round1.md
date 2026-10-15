# Prompt audit: expert-v1 (round 1)

Scope: `prompts/expert-v1.txt` + `rules-v2.txt` + `system-v2.txt`, `compose_expert` / `compose` / `labelled` / `spellings` / `model_decision` in `tla_link_review.py`, and the three rendered samples (Meryetyotes, Neferuni, Minemaes).

## Verdict

Fine to run: no P1. Two P2 fixes are recommended first (they affect validity of the evidence, not answer leakage). The rest is P3.

## 1. Leakage

Not found.

- No line in the block equals any candidate transliteration of any of the three units. Checked: Mr.yt-jtj=s and Mr.t-jtj=s; Nfr-wn.t, Nfr-nw-j, Nfr-jwn.w and Nfr.w-Nj.t; Mnw-ms.w and Jmn-ms.w. None appears as another name's link.
- The unit's own model decision, the reviewers' split, and the egyptologist's objection are not in the prompt. `compose_expert` passes only `conventions`. `reviews=""` stays empty. The stored `model_basis` and `model_tla_ids` are never rendered.
- The shuffled labels are seeded by dh_name (fine), and the unit_id is only the D&H name.
- Sub-word overlap exists but is the intended "convention evidence", not an answer proxy. Examples: Inyotef `jtj=f` and Intkaes `kꜣ=s` for Meryetyotes; Meryetneith `Nj.t` and Neferu `Nfr.w` for Neferuni's C4; Mr.yt vs Mr.t lines for Meryetyotes. Those lines do come close to settling each unit. That is acceptable only if the lines are trustworthy (P2-a).
- Block identity: it is the same for every unit except for the self-exclusion. Nothing signals which units were sent to the expert.

## P2

**a. Contested/unchecked decisions presented as "decided ... evidence".** `model_decision` includes `reconciler`-basis units, the same mechanism the code-side egyptologist found wrong for Minemaes. The block does not separate rule/agreement-decided lines from reconciler-decided ones, and its Mr.t / Mr.yt lines are exactly the ambiguity Meryetyotes turns on. If reviewers picked Mr.t vs Mr.yt arbitrarily for Meryetamun, Meryetptah, Meryetaten and others, the "convention" is manufactured from the same reviewers' picks (circular, correlated with the split). Fix: build the block only from `basis in {"rule", "agreement"}` units, drop `reconciler`-basis lines, and record the cutoff in the audit trail. Also state in the wording that these are earlier link decisions, not ground truth.

**b. Block contradicts rules-v2 and the template invites it to override them.** Pudukhepa: Ptḫp has d for t, which rules-v2 line 7 forbids (a consonant the candidate lacks). The expert is told to use the block as evidence of D&H conventions, so it may import "d can render t". Also `Werenro: Wr=n-rʾ.y` uses a sign (ʾ) that rules-v2 does not define. Fix: add to the template "the rules above decide sameness; the lines show only how D&H write words", and drop or flag the lines that violate the rules.

**c. Bias toward linking.** `if options:` omits every unit decided "none", so every line shown is a positive link. The header says "the TLA transliteration of the same name". Together they imply that every D&H name has a counterpart, and the reasoning slot ("which conventions bear on it") asks for a pattern match per candidate. Fix: either include a few none-decided names (with "no TLA name") or say that some names have no TLA counterpart. Reword the reasoning slot to "and whether any convention above argues against it".

**d. Tuned examples hint at why the units were chosen.** "a word, a preposition, an ending or a god's name" mirrors the contested features (m/ms, the t ending/=s, Neith). Fix: use the neutral "how they write names" and drop the parenthetical list.

## P3

- "they say nothing about record 1's name itself" vs "use as evidence ... which conventions bear on it": mildly incoherent. Suggested replacement: "they show how D&H write names; they do not say which candidate, if any, is record 1's name".
- Formatting inconsistency: `Nefertiry Meryetmut: Nfr.t-jr.j mr.yt-Mw.t` (space, lowercase m). Normalise or drop the line.
- Multi-link lines ("or") are fine and consistent with "several candidates".

## 3. Contradictions with rules-v2

Only the Pudukhepa/ʾ cases above (P2-b). Otherwise the template matches rules-v2 ("same name" as in rules; "list every candidate ... or none"). Line 9 of rules-v2 ("who bore a name is not evidence") is unaffected: the block gives names and spellings only, not bearers.

## Suggested minimal edit

1. Block filter: rule/agreement-decided units only.
2. Header: "Earlier link decisions for other names, as Dodson & Hilton print them. They show how D&H write names; the rules above alone decide whether a candidate is record 1's name."
3. Reasoning slot: "...whether record 1 can be read as exactly those words, and whether any D&H convention above supports or argues against it".
