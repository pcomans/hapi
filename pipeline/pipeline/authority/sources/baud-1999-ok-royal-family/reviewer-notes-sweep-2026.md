# Sweep review notes - 2026 retrospective

Reviewer: egyptologist-reviewer subagent. Scope read: `README.md`, `transcribe.md`, full `reconciled.jsonl`; no prior `reviewer-notes-*.md` files were present. Source checked against local `proprietary/books/Baud 1999 - Famille royale AE vol 2.pdf`. Spot-checked entries include [41], [42], [43], [45], [120], [121], [123], [126], [127], [200], [241], [245], [276], [282], plus surrounding context.

## P1

- `baud-126` misassigns a child to the wrong mother. The row for Nfr-kꜣw.s Jkw has `children_names: ["Mrwt", "Kꜣ.j-ḥtp (per Baud)"]`. Baud's genealogy on vol. 2 pp. 496-498, fig. 40 separates Mḥw's two wives: Nbt is mother of `[aîné?]` and Kꜣ.j-ḥtp, while Nfr-kꜣw.s Jkw is mother of `[aîné]` and Mrwt. Remove Kꜣ.j-ḥtp from `baud-126.children_names`; if captured elsewhere, he belongs under Nbt, not Nfr-kꜣw.s.

## P2

- `baud-43` overstates role coding. Baud's titles for Wꜣš-Ptḥ are ka-priest oversight for the royal daughter/queen Ḥꜥ-mrr-Nbtj II plus `ḥm-nṯr Ptḥ`, `ḥm-nṯr Ḫwfw`, `ḥm-nṯr Zkr`, etc. The row's `roles: ["priest of the king", "priest of the royal pyramid"]` imports "royal pyramid" without a corresponding pyramid-estate title in the entry. This should be narrowed to service/priestly attachment to Ḥꜥ-mrr-Nbtj II and individual deity/king cult titles as Baud gives them.

- Several anonymous/uncertain entries promote inferred social identity into normalized roles without preserving the same uncertainty in the role field. Examples: `baud-265` notes "probablement reine et mère du roi" but has empty roles, while `baud-276` gives only `king's wife` although Baud's discussion explicitly frames the evidence as queen-wife and royal-mother ideology. Conversely `baud-257`, `baud-258`, and `baud-268` set spouse/queen roles from debated anonymous monuments. These may be acceptable as structured Baud judgments, but the rows need a consistent convention: either role hedges/notes carry `per Baud` consistently, or the role field should stay title-only for anonymous complexes.

## P3

- `baud-41` preserves the probable father/mother in structured fields, but `notes_from_baud` states "fils de Téti, frère de Pépi Iᵉʳ" without repeating Baud's "sans doute". This is minor because `father_name` and `mother_name` are hedged, but the prose note can mislead downstream review.

- Mixed-language notes reduce provenance fidelity and make later review harder. Examples seen in checked rows: `baud-230` ("Stadelmann and Strudwick dispute..."), `baud-234` ("Schmitz classes him..."), `baud-235` ("Represented censing..."), `baud-251` ("Perhaps identical..."). Not a factual error, but this source otherwise uses French paraphrase keyed to Baud; normalize these notes for consistency.

- `README.md` is stale relative to the data. It still describes a seven-PR chunk plan with only early chunks landed, while `reconciled.jsonl` now has 289 rows covering [1]-[282] plus lettered entries. This is a scope/provenance documentation issue, not a row error.

No OCR-driven headword errors were confirmed in the sampled rows; apparent `pdftotext` noise such as `Nfrt-pbt` for [127] was not used as evidence against the JSON.
