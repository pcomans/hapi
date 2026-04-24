# Retrospective scholarly review — `baud-1999-ok-royal-family` (sweep, 2026-04-24)

Source reviewed by `egyptologist-reviewer` subagent as part of the Phase-0
sweep audit (see `docs/handoff-sweep-audit-2026.md`). The source was merged
without an egyptologist-reviewer pass during its PR cycle.

Spot-checked 15 rows against Baud 1999 BdE 126 vol. 2 Corpus (PDF not
accessed in-session; verified via citation text in `reconciled.jsonl`,
`README.md`, `transcribe.md`, and external scholarly corroboration: Schmitz
1976, Troy 1986, Digital Giza, Dodson & Hilton 2004). No prior
`reviewer-notes-*.md` files exist in the source directory.

Note on provenance: the subagent returned findings inline (its own
system-reminder forbade writing `.md` analysis files); the coordinator
persisted the text to this file verbatim per the sweep-doc deliverable spec.

## P1 — correctness bugs (must fix before Phase A)

**baud-17 (Jpwt Iʳᵉ / Iput I) — `father_name: "Téti (probable)"` conflates spouse with father.** The same row has `spouse_names: ["Téti"]`. Baud's note is verbatim "Épouse de Téti et mère de Pépi Iᵉʳ; la filiation royale par rapport à Téti est débattue." Baud is citing the Schmitz-vs-Seipel dispute over whether Iput was of *royal* descent, with Seipel hypothesising a Teti filiation (implying brother-sister marriage). Standard prosopography (Dodson & Hilton; the Nile Scribes / Kanawati reassessment) makes her a daughter of Unas. By baking `"Téti (probable)"` into `father_name` the extractor has promoted one side of a debated reading to a structured fact while simultaneously making her both Teti's wife and his daughter. At minimum the hedge needs strengthening; more defensibly, `father_name` should be `null` with the debate summarised in `notes_from_baud`. This is exactly the "scholarly judgment promoted to a hard claim" failure mode the transcribe.md step 6 warned about.

**baud-36 (ꜥnḫ.s-n-Ppjj III / Ankhesenpepi III) — `father_name: null` drops Baud's own attribution.** Baud's entry on Ankhesenpepi III (reinforced by the South Saqqara Stone, which Baud & Dobrev later co-published) identifies her as daughter of Merenre I and wife of Pepi II. The row captures her as Pepi II's wife but leaves `father_name` null despite Baud giving the filiation. Likely a miss rather than a misread; verify against the source PDF and populate.

**baud-44 (Wꜥtt-ḫt-ḥr Zšzšt / Watetkhethor "Seshseshet") — `father_name: null` but notes identify her as a daughter of Teti.** The row's `notes_from_baud` reads "Épouse du vizir Mrr-wj-kꜣj [83]... fille de Téti. Elle est l'une des quatre Zšzšt filles de ce roi." Yet `father_name` is `null`. Populate with `"Téti"` (not probable — Baud states it).

## P2 — structural / scope issues

**baud-39 — `roles: ["king's mother", "king's wife"]` on an explicitly ambiguous record.** The `name_egyptian` is literally `"ꜥnḫ.s-n-Mrjj-Rꜥ (var. -Ppjj) Iʳᵉ, II, ou autre (attribution incertaine)"` and the note says "Attribution incertaine entre ꜥnḫ.s-n-Mrjj-Rꜥ Iʳᵉ et II." Committing hard `roles` on a row Baud treats as a disambiguation placeholder will feed downstream enrichment a phantom queen. Consider a `roles: []` + detailed note, or a boolean `is_disambiguation_stub`.

**baud-9 — cross-reference stub with `roles: []`, all fields null but `service_personnel: false`.** Row is just "Voir à Nfrt-kꜣw II [132]". Baud uses these as index pointers, not persons. Downstream a row with only a name + null everything is likely to pollute searches. Flag as a separate `row_type` or drop in Phase A.

**Role-vocabulary drift between chunks 1 and 2.** README already notes the `steward of the king's children` gap for baud-10/25/34/40. Chunk 2 adds `overseer of the king's ornaments` (baud-62) and `high priest of Ptah` (baud-68) without the README being updated. The vocabulary list is growing organically; without a canonical table, role-based queries will miss rows.

**baud-53 Wḏbt-n(.j) — `roles: ["king's wife", "queen"]` — is "queen" a role Baud uses?** Spot-check: most queens in chunk 1 get `"king's wife"` but not `"queen"`; chunks 2 introduces `"queen"` sporadically (baud-59, 63, 75, 78). Inconsistency suggests post-merge drift, not a Baud signal.

## P3 — minor issues

**baud-53 titles_from_baud contains duplicate entries** (`jrjt-pꜥt`, `ḥmt nswt (var. mrt.f)` appear twice). Likely a merge artifact; merge.py should dedupe within a row.

**Transliteration fallback codepoint surfaces in transcribe.md example** (`[40] ɛnḫ-Špss-kɜ.f*` uses `ɛ` and `ɜ`). README claims fix_rows.py normalises these out; transcribe.md itself should be updated to the canonical ꜥ/ꜣ form so it doesn't seed future prompts with bad glyphs.

**PM III reference style drift.** Chunk 1 uses `"PM 134-135"` (bare numbers); chunk 2 mixes `"PM IV, p. 91"` (baud-58) and `"PM V, p. 72"` (baud-11). README says "exactly as printed" — leave as-is but flag for Phase A normalisation.

**`pm_ref: "PM 339"`** (baud-1) with no volume prefix is ambiguous — PM III is implicit for Giza but not machine-derivable. Phase A needs the implicit-volume resolution table.

## Methodology observations

- Scope faithfulness is good — no row crosses Baud's explicit appendix-A exclusion.
- Hedge preservation is mostly honoured (`(probable)`, `(?)`, bracketed reconstructions survive) but `father_name` shows systematic bugs where the extractor conflated Baud's prose. Recommend Phase A audit specifically of `father_name` / `mother_name` against notes prose.
- Provenance-leak risk (the HKW "Sekhen" problem) is low here because Baud's prose is quoted French, not interpretive smoothing — but the Iput I case shows the same pattern can arise through ambiguous French syntax.
- No human Egyptologist sign-off per README line 99 — everything above is provisional pending that pass.

## Sources consulted

- Digital Giza — Meresankh III (G 7530-7540): http://giza.fas.harvard.edu/ancientpeople/236/full/
- Iput I — Wikipedia
- Ankhesenpepi — Wikipedia
- Ankhhaf — Wikipedia
- Returning an Old Kingdom Queen to History — Nile Scribes
- Digital Giza — Famille royale et pouvoir sous l'Ancien Empire égyptien: http://giza.fas.harvard.edu/pubdocs/554/full/
