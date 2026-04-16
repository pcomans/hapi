# Egyptologist-reviewer notes — Ramesside chunk

Medium-confidence flags from the Ramesside-chunk review pass (2026-04-16).
High-confidence corrections are already applied via `RAMESSIDE_CORRECTIONS`
in `fix_rows.py`. Items here need a main-agent judgment call against the
source PDF before being either applied or dismissed.

## Row-level summary

- Ramesside row count in `reconciled.jsonl` is 170 (125 House + 10 Feud + 35 Decline), matching the prompt's expected range (~165–180).
- Cross-section duplicates `Takhat A` and `Isetneferet C` both have two rows with distinct `sub_period`; verbatim prose, roles, parentage, and spouse hedges differ as expected.
- Regnal-name `alt_names` titlecase convention consistently applied: `Amenhirkopshef C → "Ramesses VI"`, `Sethirkopshef B → "Ramesses VIII"`, `Messuy → "Amenmesse"`, `Paramessu → "Ramesses I"`, `Sety-Merenptah A → "Sety II"`, `Ramesses A → "Ramesses II"`, `Ramesses C (Decline) → "Ramesses IV"`. None missing.
- No meta-commentary or editorial tails in any `notes` field (chunk-1/chunk-2 drift pattern checked — clean).
- All `source_citation.pdf_pages` match the section (`157-162` / `169-170` / `178-180`). No drift.
- Hittite-princess coverage is correct: only `Maathorneferure` has a Brief Lives row; the second year-40 princess (narrative only) is absent as intended.
- `Tawosret` spelling matches D&H's printing (verified in OCR p.170).

## Medium-confidence flags

### 1. `Hori A.father_name` hedge ambiguity

- Current: `"father_name": "Khaemwaset C (probable)"` (hedge restored; see below).
- D&H p. 171: `"Probably a grandson of Ramesses II and son of Khaemwaset C."`
- Reading A: `"Probably"` scopes only to `"grandson of Ramesses II"`; the son-of-Khaemwaset-C is asserted.
- Reading B: `"Probably"` scopes to the entire coordinated phrase (grandson-and-son). English syntax doesn't force a choice, but coordinated nominal phrases without a comma typically share the modifier, and D&H uses the comma form elsewhere when narrowing scope.
- **Resolved (main agent, 2026-04-16):** Reading B is the safer interpretation. Corrected to `"Khaemwaset C (probable)"` via `RAMESSIDE_CORRECTIONS` in `fix_rows.py`, matching chunks-1-2 hedge-preservation convention (`"Yuya (probable)"` on Mutemwia, `"Ay (probable)"` on Nefertiti etc.). The paired Khaemwaset C cross-entry inference keeps `children_names = ["Hori A", ...]` unhedged per the README's hedge-handling rule (hedges live on the child-row's `father_name`, not on the parent's `children_names` list).

### 2. `Sethirkopshef B.roles` — `MH` vs `MoH`, trailing period

- Current: `"roles": ["KSon", "MH"]` — matches OCR verbatim (`(KSon; MH).`).
- D&H elsewhere uses `MoH` (`Master of Horse`) — e.g. `Amenhirkopshef C` has `(KSon; MoH)` on p. 192.
- **Resolved (main agent, 2026-04-16).** Re-read PDF p. 194 Sethirkopshef B: D&H literally prints `(KSon; MH).` — the `MH` is not an OCR drop of `MoH`. Per constitutional rule 6 (raw data sacred) and rule 1 (scholarly traceability), the extract preserves what D&H printed; Phase A's role-code glossary will decide whether `MH` is an intentional distinct abbreviation, a typo-for-`MoH`, or something else. **No fix_rows correction applied.** The trailing period inside the parenthetical is already correctly dropped during extraction.

### 3. `Hattusilis III.spouse_names` — scope of cross-entry inference

- Current: `"spouse_names": ["Pudukhepa"]` (majority-voted in; agent-c voted `[]`).
- D&H p. 171 for Hattusilis III: the entire entry is `"Father-in-law of Ramesses II."` — silent on spouse.
- D&H p. 171 for Pudukhepa: `"Wife of Hattusilis III; corresponded with Nefertiry D."` — explicitly names Hattusilis III as husband.
- The sanctioned cross-entry-inference rule in the README covers `children_names` only ("is allowed for `children_names` when D&H's prose in another Brief Lives entry establishes a child-of relationship"). Extending the rule to `spouse_names` is a policy expansion not explicitly documented in chunk-2.
- Recommendation: either (a) accept the inference and update the README to say the rule covers all symmetric-relationship fields, or (b) revert to `[]` and let Phase A rebuild spouse-of-wife from wife-of-husband. My read is (a) is the more useful outcome and matches what downstream consumers will want, but the policy change is worth documenting explicitly rather than leaving implicit.

### 4. `Tjia.father_name` — conflict with `Amenwahsu` prose

- Current: `"father_name": "Amenwahsu"` on `Tjia` (per agents a and b; c had null).
- D&H p. 170: `Amenwahsu` entry reads `"Father of Tjia; shown with him, Ramesses II, and Sety B on a block in Chicago."`
- D&H p. 175: `Tjia` entry reads `"Brother-in-law of Ramesses II. Shown along with his mother-in-law and wife on a block in Toronto. Buried with his wife in a tomb at Saqqara."` — silent on father, only mother-in-law/wife mentioned.
- The `Amenwahsu → Tjia` paternity is parent-stated in Amenwahsu's own entry; Tjia's entry is silent. This is the REVERSE of the sanctioned cross-entry-inference direction (chunk-2 sanctions *parent.children_names* acquiring from child's entry, not *child.father_name* acquiring from parent's entry). But the same symmetry argument applies.
- Current state is correct on Amenwahsu's side (already should have `Tjia` in children, verify) and arguably correct on Tjia's side too. Low-impact flag — mainly highlighting that the cross-entry-inference rule is being applied in both directions and the README only documents one.

### 5. `Khaemwaset C.children_names` — hedge propagation in the applied correction

The applied fix sets `children_names = ["Hori A", "Isetneferet C", "Ramesses C"]` as bare strings. Note that Hori A's child→parent assertion is hedged (`"Probably... son of Khaemwaset C"`) while Isetneferet C and Ramesses C are unhedged. The chunk-2 precedents (Shuttarna II → Gilukhipa, Tushratta → Tadukhipa) were all unhedged, so there is no chunk-2 answer for the "hedged child, silent parent" case. I chose the unhedged bare-string form to match the rest of the file's `children_names` convention (which does not carry hedges on the child names — hedges live on the parent-side `father_name`/`mother_name` fields on the child's own row). If the main agent prefers to push hedges into `children_names` as `"Hori A (probable)"`, that is a source-wide convention change and should be applied to all chunks.

### 6. `Ramesses C` cross-sub_period disambiguation for downstream consumers

The string `"Ramesses C"` now appears in `children_names` on two rows:
- `Khaemwaset C [The House of Ramesses].children_names → ["Hori A", "Isetneferet C", "Ramesses C"]` — referring to the Dyn-19 Ramesses C (grandson of Ramesses II).
- `Iset D Ta-Hemdjert [The Decline of the Ramessides].children_names → ["Amenhirkopshef C", "Ramesses C"]` — referring to the Dyn-20 Ramesses C (later RAMESSES IV).

The composite primary key `(dh_id, sub_period)` on the row side already distinguishes these. But bare-string `children_names` references can only be disambiguated by the parent row's own `sub_period`. Phase A consumers resolving these references must scope to the same `sub_period` when looking up the child's own row — a simple rule but worth making explicit in downstream code. Not a data bug; a Phase-A consumer contract note.

## Pre-commit diff attestation (Step 11.5 item 0)

Playbook Step 11.5 item 0 (baseline transcription diff) was run locally before this PR landed:

```
cd pipeline && uv run python pipeline/authority/sources/dodson-hilton-queens/diff_ramesside.py
# [The House of Ramesses]   matched=125 mismatches=0 unmatched=0 missing_in_recon=0
# [The Feud of Ramessides]  matched=10  mismatches=0 unmatched=0 missing_in_recon=0
# [The Decline of Ramessides] matched=35  mismatches=0 unmatched=0 missing_in_recon=0
# Ramesside totals across 3 sub-blocks: mismatches=0 unmatched=0 missing_in_recon=0
```

Clean run against all 170 Ramesside rows. The three OCR chunk files (`raw/chunk-p157-p162.md`, `raw/chunk-p169-p170.md`, `raw/chunk-p178-p180.md`) are gitignored per ADR-017 / `.gitignore:49` (OCR'd copyrighted prose must not leave the repo). The `diff_ramesside.py` script itself is committed so any reviewer who re-runs the OCR step locally from the SHA-pinned source PDF can re-verify the same clean run. This matches the playbook's pre-commit-gate model for gitignored-transcription sources (Step 11.5 § implementation-vehicle list).

## Out of scope for this pass

- `Amenemwia/Setemwia.alt_names = []` — per prompt's explicit instruction (slash is D&H's primary-name form, not a successive regnal change). Not a flag.
- `Merenptah A.alt_names = []` — OCR prose says only `"He later became king."` without the regnal name `MERENPTAH`. Can't cite what isn't printed. Not a flag; the Phase A layer will link Merenptah A to the pharaoh.se king `Merenptah`.
- `Takhat A` House-of-Ramesses stub `children_names = []` — correct; the stub is two sentences and names no children. The Feud row already has `["Amenmesse"]` from the full entry.
- Cross-section-duplicate row verification passed — both `Takhat A` and `Isetneferet C` double-rows differ in verbatim `notes`, `roles`, `spouse_names`, and parentage between their two sub-period keys, as expected from D&H's split.
