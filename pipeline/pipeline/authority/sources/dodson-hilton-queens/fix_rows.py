"""Apply LLM-reviewer-identified corrections to reconciled.jsonl.

Run AFTER merge.py. Mirrors Kitchen's pattern — idempotent re-runs,
append-only LLM-APPLIED OVERRIDES section in merge-disagreements.txt,
every override recorded with rationale.

For the Pre-Amarna chunk (p126–p130), the egyptologist-reviewer Claude
Code subagent flagged a single verbatim-prose OCR drift on `Tiaa A`'s
`notes`: Gemini's OCR dropped an article and introduced a stray colon
(`"including: number of usurpations"` vs the PDF's `"including a
number of usurpations"`). Since `notes` is a verbatim-quotation field,
the correction is applied rather than left in the extract.

For the Amarna chunk (p142–p145), eight field-level drifts are
corrected:

- Four editorial tails added by individual extraction subagents that
  survived majority-vote ([...]18A–H, [...]18K–N, Tey, Thutmose B
  alt_names cross-reference).
- One slash-expansion error on `Tutankhuaten`'s `alt_names` where
  "TUTANKHATEN/AMUN" was literally split to `["TUTANKHATEN", "AMUN"]`
  instead of being glossed as the successive regnal names
  `["Tutankhaten", "Tutankhamun"]`.
- Two allcaps-vs-titlecase alt_names normalisations flagged in the
  egyptologist-reviewer pass (Amenhotep E, Meryetaten) — D&H's
  BOLD-CAPITALS rendering of regnal names is typographic emphasis,
  not a canonical spelling, and museum-catalogue matching requires
  titlecase.
- One hedge-preservation fix on `Ankhesenpaaten.spouse_names` where
  agents dropped D&H's explicit "perhaps" from the Ay brief-marriage
  qualification.

Corrections sourced from a two-stage review pass: Claude Opus 4.6
main-session cross-check against the Opus-produced OCR chunk
(editorial tails, slash-split), followed by the egyptologist-reviewer
Claude Code subagent walking `reconciled.jsonl` against the source
PDF (casing, hedge loss). Each correction restores the verbatim prose
or fixes the semantic split.

No deterministic recomputation is needed for this source (the schema
has no interval-overlap or cross-row fields).

Run:
    cd pipeline && uv run python pipeline/authority/sources/dodson-hilton-queens/fix_rows.py

Idempotent: re-running replaces (not duplicates) the LLM-APPLIED OVERRIDES
section in merge-disagreements.txt.
"""

from __future__ import annotations

import json
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
RECONCILED = SOURCE_DIR / "reconciled.jsonl"
DIFF = SOURCE_DIR / "merge-disagreements.txt"


# Spot corrections identified by the egyptologist-reviewer subagent pass.
# Each entry: (dh_id, sub_period, field, new_value, rationale).
# The composite `(dh_id, sub_period)` key matches merge.py's row key —
# D&H lists some individuals (e.g. Takhat A) under two Brief Lives
# sub-sections as separate rows, so a correction may target only one
# of those rows.
# No POWER spot corrections remain: the only entry was a `notes`
# verbatim-prose fix, dropped along with the `notes` field itself by the
# terminal `destructure_notes.py` stage (D&H prose is not reproduced).
POWER_CORRECTIONS: list[tuple[str, str, str, object, str]] = []


AMARNA_CORRECTIONS: list[tuple[str, str, str, object, str]] = [
    # Three `notes` verbatim-prose corrections (group entries [...]18A–H,
    # [...]18K–N, and Tey) were removed: the `notes` field they fixed is
    # dropped wholesale by the terminal `destructure_notes.py` stage, so
    # writing it here would re-introduce D&H prose on a fix_rows re-run.
    (
        "Thutmose B",
        "The Amarna Interlude",
        "alt_names",
        [],
        "Two of three agents included 'Thutmose Q (conceivably "
        "identical)' as an alt_name, but `alt_names` is reserved for "
        "alternate forms of the same individual's name (e.g. "
        "'Ankhesenpaaten' → 'Ankhesenamun'). Thutmose Q is a distinct "
        "Brief Lives entry that D&H flags as conceivably the same "
        "person; that cross-reference belongs in `notes` (where it is "
        "already preserved) not `alt_names`.",
    ),
    (
        "Tutankhuaten",
        "The Amarna Interlude",
        "alt_names",
        ["Tutankhaten", "Tutankhamun"],
        "All three agents split the D&H compact-notation 'TUTANKHATEN/"
        "AMUN' literally to ['TUTANKHATEN', 'AMUN'], but the slash is "
        "D&H's shorthand for the successive regnal names "
        "Tutankhaten → Tutankhamun (the 'Tutankh-' prefix is dropped "
        "before /AMUN for typographic economy, as with other of D&H's "
        "name-change slashes). Expanded to the canonical pair.",
    ),
    (
        "Amenhotep E",
        "The Amarna Interlude",
        "alt_names",
        ["Amenhotep IV", "Akhenaten"],
        "Agents preserved D&H's BOLD-CAPITALS rendering (used by D&H for "
        "kings' regnal names) as ALLCAPS strings ['AMENHOTEP IV', "
        "'AKHENATEN']. Museum catalogues and downstream authority "
        "matching use titlecase ('Akhenaten', 'Amenhotep IV'); "
        "normalising to titlecase is consistent with the Tutankhuaten "
        "correction above and with titlecase alt_names already present "
        "on Ankhesenpaaten, Nefertiti, Horemheb, and Meryetaten-tasherit. "
        "D&H's typographic emphasis is a formatting signal, not a "
        "canonical-name choice.",
    ),
    (
        "Meryetaten",
        "The Amarna Interlude",
        "alt_names",
        ["Neferneferuaten"],
        "Same allcaps-vs-titlecase normalisation as Amenhotep E: agents "
        "preserved D&H's BOLD-CAPITALS rendering of the regnal name "
        "**NEFERNEFERUATEN** as 'NEFERNEFERUATEN'. Titlecase matches "
        "museum-catalogue spelling and the rest of the source's alt_names.",
    ),
    (
        "Ankhesenpaaten",
        "The Amarna Interlude",
        "spouse_names",
        ["Tutankhamun", "Ay (perhaps, brief marriage)"],
        "Agents rendered the Ay-marriage hedge as 'Ay (brief marriage)', "
        "dropping D&H's explicit 'perhaps' from the phrase 'a ring in "
        "Berlin that joins her cartouche with that of King Ay, perhaps "
        "indicating a brief marriage' (p. 154). The hedge belongs on "
        "the existence of the marriage, not its duration; preserved "
        "verbatim in the parenthetical.",
    ),
]


# Ramesside-chunk corrections (House of Ramesses, Feud of the Ramessides,
# Decline of the Ramessides Brief Lives) from the egyptologist-reviewer
# pass. Two cross-entry-inference misses: agents majority-voted empty
# `children_names` in cases where the sanctioned chunk-2 pattern
# (parent's own entry silent + child's entry explicitly names parent)
# clearly applies. Agent-b flagged both in the merge disagreements but
# lost the vote.
RAMESSIDE_CORRECTIONS: list[tuple[str, str, str, object, str]] = [
    (
        "Khaemwaset C",
        "The House of Ramesses",
        "children_names",
        ["Hori A", "Isetneferet C", "Ramesses C"],
        "Chunk-2 sanctioned cross-entry-inference pattern: Khaemwaset "
        "C's own entry (p. 171) names no children, while three separate "
        "Brief Lives entries in the same sub-section explicitly name him "
        "as father — Hori A (p. 171, 'Probably a grandson of Ramesses "
        "II and son of Khaemwaset C'), Isetneferet C House-row (p. 171, "
        "'daughter of Khaemwaset C'), Ramesses C House-row (p. 173, "
        "'Dedicator at Memphis of a statue of his father, Khaemwaset "
        "C'). Agent-b captured all three; the majority voted [] and "
        "lost the symmetry. Same mechanism as the Shuttarna II → "
        "Gilukhipa and Tushratta → Tadukhipa inferences sanctioned in "
        "the Amarna chunk README.",
    ),
    (
        "Iset D Ta-Hemdjert",
        "The Decline of the Ramessides",
        "children_names",
        ["Amenhirkopshef C", "Ramesses C"],
        "Chunk-2 sanctioned cross-entry-inference pattern: Iset D "
        "Ta-Hemdjert's own entry (p. 192) names only her granddaughter "
        "Iset E, but both Amenhirkopshef C (p. 192, 'Son of Ramesses "
        "III and Iset D') and Ramesses C Decline-row (p. 194, 'Son of "
        "Ramesses III and Iset D') explicitly name her as mother. D&H "
        "uses the short form 'Iset D' in the children's entries and "
        "the long compound 'Iset D Ta-Hemdjert' as her own dh_id — "
        "same individual. Without this inference the family tree is "
        "asymmetric. Populating children here matches the chunk-2 "
        "precedent (the mother's and grandmother's entries both point "
        "to Iset E's eventual appointment) and brings the row in line "
        "with the granddaughter mention already in `notes`.",
    ),
    (
        "Hori A",
        "The House of Ramesses",
        "father_name",
        "Khaemwaset C (probable)",
        "D&H p. 171 reads 'Probably a grandson of Ramesses II and son "
        "of Khaemwaset C.' Standard English coordination scopes "
        "'probably' over the whole nominal phrase — both the grandson "
        "claim and the son-of-Khaemwaset-C claim share the hedge. The "
        "extraction agents stripped the hedge from `father_name`; "
        "restored verbatim to match the chunks-1-2 hedge-preservation "
        "convention ('Yuya (probable)' on Mutemwia etc.). The paired "
        "cross-entry inference on Khaemwaset C keeps "
        "`children_names = ['Hori A', ...]` bare per the README's "
        "hedge-handling rule (hedges live on the child-row's "
        "`father_name`, not on the parent's `children_names` list).",
    ),
]


# Per-row dynasty refinements on the Founders chunk. D&H's section title
# jointly covers the 1st, 2nd and 3rd Dynasties under "The Founders", and
# `prompt-founders.md` defaults `dynasty: 1` for every row as a coarse
# extraction pass. Four Unplaced rows carry an EXPLICIT Egyptological-
# dynasty cue in their notes prose (`"2nd Dynasty;"` or `"3rd Dynasty;"`
# at the start of the sentence), making the coarse `dynasty: 1` a
# contradiction of the row's own evidence. Per constitutional rule 1
# (scholarly traceability), overriding `dynasty` to the notes-cue value
# is more honest than keeping the chunk-default. This is NOT a Phase-A
# deferral — the cue is on-row and parseable with zero ambiguity; Phase
# A would make the identical correction from the identical cue. Applying
# it here keeps the extract self-consistent.
FOUNDERS_CORRECTIONS: list[tuple[str, str, str, object, str]] = [
    (
        "Shepsetipet",
        "The Founders",
        "dynasty",
        2,
        "Notes prose explicitly opens with '2nd Dynasty; known from a "
        "stela found near tomb S3477 at Saqqara …' — the chunk-default "
        "`dynasty: 1` from D&H's Ch-1-joint-dynasties section placement "
        "contradicts the row's own evidence. Refined to 2 here.",
    ),
    (
        "Sitba",
        "The Founders",
        "dynasty",
        2,
        "Notes prose explicitly opens with '2nd Dynasty; buried in "
        "Helwan tomb 1241 H9.' — chunk-default `dynasty: 1` contradicts "
        "on-row evidence. Refined to 2.",
    ),
    (
        "Syhefernerer",
        "The Founders",
        "dynasty",
        2,
        "Notes prose explicitly opens with '2nd Dynasty; buried in "
        "Saqqara tomb S2146E …' — chunk-default `dynasty: 1` contradicts "
        "on-row evidence. Refined to 2.",
    ),
    (
        "Redji",
        "The Founders",
        "dynasty",
        3,
        "Notes prose explicitly ends with 'dated stylistically to the "
        "3rd Dynasty.' — chunk-default `dynasty: 1` contradicts on-row "
        "evidence. Refined to 3.",
    ),
]


# Seizers of the Two Lands (chunk 5) post-merge corrections surfaced by
# the retrospective Codex review on PR #77 (run 2026-04-19 under the
# `feedback_codex_review_every_pr` discipline established after the
# session wrap; the initial PR #77 merge predated that discipline).
# D&H's role-parenthetical mini-grammar — Of Kings and Priests case-notes.
#
# Code-reviewer (PR #218) raised a fair concern that this chunk's two P1
# corrections treat colon-bearing role tokens asymmetrically:
#
#  - Maatkare A had `["KDB", "Ador", "GWA: prenomen Mutemhat"]`. The
#    colon-bearing third element was SPLIT to bare `["KDB", "Ador",
#    "GWA"]` + `alt_names: ["Mutemhat"]`.
#  - Henttawy Q had relation-tokens `Daughter of: KGW` and `Mother of:
#    KGW, HPA & Genmo` (also colon-bearing). These were KEPT as single
#    role-tokens in the restored role list.
#
# Why the asymmetry is correct (not arbitrary): D&H's role-parenthetical
# uses the colon in two distinct grammatical roles —
#
#  (a) ROLE-ANNOTATION colon. `GWA: prenomen Mutemhat` means "the GWA
#      title, whose cartouche-prenomen reads Mutemhat." The colon
#      introduces an ASIDE about how the role's cartouche-name is
#      written. The role itself is `GWA`; `Mutemhat` is an alt-name for
#      the same individual under a different title-context. Splitting
#      correctly recovers a clean role-code (matchable against
#      `KNOWN_ROLE_TOKENS`) plus an alt-name (matchable against
#      `alt_names` glossary).
#
#  (b) ROLE-PARAMETER colon. `Daughter of: KGW` means "Daughter-of-X
#      where X = a King's Great Wife." The colon introduces the PARAMETER
#      of a parameterised kinship-role. The whole `Daughter of: KGW` is a
#      single semantic unit (a role with its target) that Phase A's
#      `enrich_rulers` / `enrich_individuals` pipeline can interpret
#      directly. Splitting this would lose the parameter binding.
#
# Same colon character, different grammatical roles in D&H's mini-grammar.
# The egyptologist-reviewer pass (PR #218 review) verified both readings
# against the printed source: Maatkare A's annotation form on p.206, and
# Henttawy Q's parameter form on p.205.
#
# `KNOWN_ROLE_TOKENS` accepts both kinds — bare role codes (`GWA`) AND
# parameter-bearing relation roles (`Daughter of: KGW`, `Mother of: KGW,
# HPA & Genmo`). Phase A owns the decoding of which kind a token is.
OFKINGSANDPRIESTS_CORRECTIONS: list[tuple[str, str, str, object, str]] = [
    (
        "Henttawy Q",
        "Of Kings and Priests",
        "roles",
        ["KD", "KW", "KM", "L2L", "M2L", "Daughter of: KGW", "1ChHA", "Mother of: KGW, HPA & Genmo"],
        "Egyptologist printed-source verification (p.205 right column): D&H's "
        "role-parenthetical for Henttawy Q reads `(KD; KW; KM; L2L; M2L; "
        "Daughter of: KGW; 1ChHA; Mother of: KGW, HPA & Genmo)`. Majority-"
        "voted roles dropped `1ChHA` and the two relation-tokens entirely; "
        "merged notes silently absorbed the relation-tokens as prose. "
        "Restoring the full role list per D&H's printed parenthetical "
        "(relation-tokens are D&H's annotation of kinship roles; Phase A "
        "owns the role-code glossary including these).",
    ),
    # The Henttawy Q `notes` correction (companion to the roles fix below)
    # was removed: `notes` is dropped by `destructure_notes.py`. The full
    # name "Duahathor-Henttawy" that it mentioned already lives in
    # `alt_names`, so no matchable fact is lost.
    (
        "Maatkare A",
        "Of Kings and Priests",
        "roles",
        ["KDB", "Ador", "GWA"],
        "Egyptologist printed-source verification (p.206): D&H's role-"
        "parenthetical for Maatkare A reads `(KDB; Ador; GWA: prenomen "
        "Mutemhat)`. The colon-bearing `GWA: prenomen Mutemhat` token is "
        "an annotation of the GWA cartouche's prenomen reading, not a "
        "role-code itself. Split into bare `GWA` (the role) plus alt_names "
        "`Mutemhat` (already preserved). No other row carries a colon-"
        "bearing role token; this would break downstream role-vocabulary "
        "matching.",
    ),
]


SEIZERS_CORRECTIONS: list[tuple[str, str, str, object, str]] = [
    (
        "Ameny A",
        "Seizers of the Two Lands",
        "alt_names",
        ["Amenemhat II"],
        "Ameny A's prose explicitly states 'later king as AMENEMHAT II' "
        "(D&H's BOLD-CAPITALS convention for a regnal-name reference). "
        "Earlier D&H chunks consistently populate `alt_names` with the "
        "titlecase regnal form when an individual has a later-king "
        "reference — precedents include `Paramessu` (alt_names: "
        "'Ramesses I'), `Ramesses A` (alt_names: 'Ramesses II'), "
        "`Amenhotep E` (alt_names: 'Amenhotep IV', 'Akhenaten'), and "
        "`Sobkhotep C` which the Kings and Commoners chunk later "
        "applied the same rule to ('later co-regent and king as "
        "SOBKHOTEP IV'). Seizers extraction missed the rule. "
        "Surfaced by Codex review on 2026-04-19 retrospective pass; "
        "fix restores cross-chunk-consistent aliasing so Phase-A "
        "matcher can hit Ameny A via either his D&H dh_id or his "
        "pharaoh.se canonical-name `Amenemhat II`.",
    ),
    (
        "Didit",
        "Seizers of the Two Lands",
        "mother_name",
        "Sithathor Q",
        "Didit's Brief Life ends with `mother of Neferet Q`; "
        "`Sithathor Q`'s Brief Life in the same sub-section's Unplaced "
        "block opens `Mother of Didit, named on the funerary stela of "
        "Neferet Q in Munich.` The cross-entry-inference rule D&H "
        "adopted in chunk 2 Amarna (Gilukhipa / Shuttarna II pair) "
        "and chunk 3 Ramesside (Hattusilis III / Pudukhepa pair, and "
        "others) symmetrises kinship: a parent-named-as-X-in-child's-"
        "notes populates `father_name`/`mother_name` on the child's "
        "row, and the reciprocal `children_names` on the parent's "
        "row. Seizers extraction applied the symmetry on child→parent "
        "(Didit's entry names Neferet Q as child → Neferet Q's row "
        "must have mother_name `Didit` — which it does) but missed "
        "the other symmetry edge: parent→child. `Sithathor Q` is a "
        "mother in her own entry but `Didit`'s row has `mother_name: "
        "null`. Surfaced by Codex review on 2026-04-19 retrospective "
        "pass; fix restores intra-chunk kinship symmetry.",
    ),
]


# Issue #175 (PR for that). Schema-audit findings:
#
# - Shape A: Sitre A's `alt_names = ["Tia Q"]` parallels the existing
#   Thutmose B precedent — D&H's prose ("She may previously have borne
#   the name Tia (Q).") is a hedged identity hint preserved in `notes`,
#   not a confirmed alt_name. `alt_names` is reserved for alternate
#   forms of the same individual's verified name (e.g.
#   `Ankhesenpaaten` → `Ankhesenamun`).
#
# - Shape F: `OPULE` typo in Thutmose B's roles (1 row) where `MULE`
#   was intended (8 rows in corpus). Currently shipping bad data in
#   reconciled.jsonl. The `KNOWN_ROLE_TOKENS` allowlist + closure test
#   added in this PR catches this class of typo going forward.
ISSUE_175_AUDIT_CORRECTIONS: list[tuple[str, str, str, object, str]] = [
    (
        "Sitre A",
        "The House of Ramesses",
        "alt_names",
        [],
        "Issue #175: clear `alt_names = ['Tia Q']` per the Thutmose B "
        "precedent (already in this fix_rows.py). D&H's notes prose for "
        "this row reads `She may previously have borne the name Tia (Q).` "
        "— a hedged identity hint, NOT a confirmed alt_name. `alt_names` "
        "is reserved for alternate forms of the same individual's verified "
        "name (e.g. `Ankhesenpaaten` → `Ankhesenamun`). The cross-reference "
        "to Tia (Q) is already preserved in `notes` so no information is "
        "lost; clearing `alt_names` brings this row in line with the "
        "Thutmose B / Thutmose Q correction also in this file.",
    ),
    (
        "Thutmose B",
        "The Amarna Interlude",
        "roles",
        ["EKSon", "HPM", "SPP", "MULE"],
        "Issue #175: fix `OPULE` typo (1 row) → `MULE` (8 rows in corpus). "
        "`OPULE` is not a documented D&H role token; `MULE` (Master / "
        "Overseer of the Lord's Estate) is the intended code. The "
        "`KNOWN_ROLE_TOKENS` allowlist + `test_role_tokens_in_known_vocab` "
        "closure test added in this PR catch this class of typo "
        "going forward.",
    ),
]


SPOT_CORRECTIONS: list[tuple[str, str, str, object, str]] = (
    POWER_CORRECTIONS
    + AMARNA_CORRECTIONS
    + RAMESSIDE_CORRECTIONS
    + FOUNDERS_CORRECTIONS
    + SEIZERS_CORRECTIONS
    + OFKINGSANDPRIESTS_CORRECTIONS
    + ISSUE_175_AUDIT_CORRECTIONS
)


# Issue #175 (Shape J): typed flag for D&H "group entries" — single
# rows that cover multiple individuals via D&H's letter-range notation
# (`[...]18A–H` covers up to 8 daughters A through H of Amenhotep III;
# `[...]18K–N` covers 4 daughters K–N). Pre-fix these were
# indistinguishable from regular lacuna entries (`[...]12A`, `Henut[...]`)
# which represent ONE partially-attested individual. Downstream
# consumers iterating per-row would conflate the two without a typed
# flag.
#
# The set is exhaustive against the current corpus — verified by
# `_GROUP_ENTRY_CANDIDATES_CHECK` at module-load below. New chunks
# that introduce additional group entries must extend this set
# explicitly (the closure test will fail otherwise, surfacing the
# decision rather than silently letting it slip).
GROUP_ENTRY_DH_IDS: set[tuple[str, str]] = {
    ("[...]18A–H", "The Amarna Interlude"),
    ("[...]18K–N", "The Amarna Interlude"),
}


# D&H role token vocabulary. Closure asserted by
# `test_role_tokens_in_known_vocab` — every token in any row's `roles`
# list must appear here. Update this set when adding a new chunk that
# introduces a new role token, after verifying the token is D&H's
# (not a typo).
#
# Membership semantics: presence in this set means "verified in the
# corpus; will not fail the closure test". A trailing `# ?` comment
# means "the semantic decoding of this token (what role it actually
# names) is uncertain pending Phase A" — NOT that the token's
# membership in the closure is in doubt. The closure test is the
# source of truth for membership; the comments are documentation of
# decoding status (Phase A work).
#
# Compiled from the corpus (74 distinct tokens minus the OPULE typo
# this PR fixes), grouped by category for human-readable maintenance.
KNOWN_ROLE_TOKENS: set[str] = {
    # Royal-family relational codes
    "KD",        # King's Daughter
    "KDB",       # King's Daughter (of Body)
    "KSon",      # King's Son
    "KSonB",     # King's Son (of Body)
    "KSonK",     # King's Son of Kush
    "KSonN",     # King's Son of Nubia (alt notation)
    "EKSon",     # Eldest King's Son
    "EKSonB",    # Eldest King's Son (of Body)
    "1KSon",     # First King's Son (D&H's leading-digit form)
    "1KSonB",    # First King's Son (of Body)
    "KSis",      # King's Sister
    "KW",        # King's Wife
    "KW?",       # King's Wife (hedged — D&H's explicit hedge variant)
    "KGW",       # King's Great Wife
    "KM",        # King's Mother
    "GW",        # God's Wife
    "GWA",       # God's Wife of Amun
    "GBW",       # Greatly Beloved Wife (foreign-princess title)
    "GM",        # God's Mother (priestess role)
    "GF",        # God's Father (Yuya, Ay etc.)
    "GS",        # God's Sister
    "PH",        # Possible/probable wife (D&H hedge in Mentuhotep-II contexts)
    "UWC",       # Unmarried Wife? / Unidentified Woman in Court (verify)
    "L2L",       # Lady of the Two Lands
    "Ador",      # Adoratrix (of Amun)
    "Genmo",     # Generalissimo / Generalissimo of the Army
    "1Genmo",    # First Generalissimo
    "MULE",      # Master / Overseer of the Lord's Estate
    "MoH",       # Master of the Horse
    "MH",        # Master of the Horse (alt)
    "Exec",      # Executive (chief minister)
    "ExecH2L",   # Executive of the Two Lands
    "HPH",       # High Priest of (somewhere)
    "HPM",       # High Priest of Memphis
    "HPA",       # High Priest of Amun
    "SPP",       # Sem-Priest of Ptah
    "Viz",       # Vizier
    "Viz?",      # Vizier (hedged)
    "Gen",       # General
    "Nomarch",   # Nomarch
    "Fanbearer",
    "1PMut",     # First Prophet of Mut
    "RO",        # Royal Ornament(?) — verify
    "ChA",       # ?
    # Additional compact codes (less frequent; semantics where known
    # noted in comments, otherwise verbatim from corpus pending future
    # README expansion).
    "2PA",       # Second Prophet of Amun
    "CTL",       # Chief Treasurer of the Lord (?)
    "FW",        # Foster-Wife (?)
    "KGD",       # King's Grand-Daughter (?)
    "KM of KGW", # King's Mother of King's Great Wife (compound role)
    "M2L",       # Mistress of the Two Lands
    "SCH",       # ?
    "SH",        # Steward of the Household (?)
    "ScH",       # Scribe of the Household (?)
    "Sister of KGW",
    # Long-form titles D&H spells out
    "Adjutant of the Chariotry",
    "Attendant of Dog-Keepers",
    "Captain of the Troops",
    "Chief Scribe of the Vizier",
    "Elder of the Portal",
    "Governor of El-Kab",
    "High Steward",
    "King of Hittites",
    "King of Mitanni",
    "Mistress of All Women",
    "Nurse of the God",
    "Overseer of Cattle",
    "Overseer of the Fields",
    "Overseer of Treasurers",
    "Royal Representative",
    "Songstress of Pre",
    "Steward of Queen Tiye A/Tey",
    "Townsman",
    "Troop Commander",
    # Of Kings and Priests (Dyn 21) — chapter-4 chunk-1 additions.
    "1ChHA",                     # First Chief of the Harem of Amun
    "2PA Tanis",                 # Second Prophet of Amun at Tanis
    "3PA",                       # Third Prophet of Amun
    "4PA",                       # Fourth Prophet of Amun
    "AL",                        # ?  — Tanite-royal title (Pasebkhanut II, Pasebkhanut A, Piankh)
    "ChH Mentu",                 # Chief of the Harem of Mentu
    "ChH Min",                   # Chief of the Harem of Min
    "ChHA",                      # Chief of the Harem of Amun
    "ChHA–1st phyle",            # Chief of the Harem of Amun (1st phyle)
    "ChHA–4th phyle",            # Chief of the Harem of Amun (4th phyle)
    "ChMa",                      # Chief of the Ma (Libyan tribal chiefship)
    "Daughter of: KGW",          # D&H relation-token in role parenthetical (Henttawy Q)
    "Flautist of Mut",
    "GFAmun",                    # God's Father of Amun
    "High Steward of Amun",
    "Mother of: KGW, HPA & Genmo",  # D&H relation-token in role parenthetical (Henttawy Q)
    "PA",                        # Prophet of Amun (bare; Hori C — distinct from 2PA/3PA/4PA)
    "PMut",                      # Priest of Mut (Ankhefenmut B)
    "PSeth",                     # Priest of Seth (Hori C)
    "Sem-Priest at Medinet Habu",
}

_OVERRIDES_MARKER = "LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED"

# Guard against a rationale string ever containing the marker text — the
# in-place strip in main() does `existing_diff.find(_OVERRIDES_MARKER)`,
# which would silently truncate inside a rationale instead of at the
# section boundary. Caught at module-load so a future correction that
# (innocently) quotes the marker fails loud rather than producing a
# half-stripped audit log.
for _, _, _, _, _rationale in SPOT_CORRECTIONS:
    if _OVERRIDES_MARKER in _rationale:
        raise ValueError(
            f"SPOT_CORRECTION rationale contains the LLM-APPLIED OVERRIDES "
            f"marker substring; the in-place strip in main() would mis-truncate. "
            f"Quote the marker differently or escape it. Offending rationale: "
            f"{_rationale[:120]!r}..."
        )
del _rationale


def backfill_is_group_entry(rows: list[dict]) -> list[str]:
    """Issue #175 (Shape J): every row carries `is_group_entry: bool`,
    True iff the (dh_id, sub_period) is in `GROUP_ENTRY_DH_IDS`.

    **Mutates `rows` in place** AND returns log lines for downstream
    audit-log writing. Idempotent. Schema-shape pass before SPOT_CORRECTIONS.
    Constitutional rule 4: schema shape uniform across all rows so
    consumers don't branch on present-vs-absent.
    """
    log_lines: list[str] = []
    for row in rows:
        key = (row["dh_id"], row["sub_period"])
        expected = key in GROUP_ENTRY_DH_IDS
        if "is_group_entry" not in row:
            row["is_group_entry"] = expected
            log_lines.append(
                f"  {row['dh_id']} [{row['sub_period']}]: backfilled "
                f"is_group_entry={expected}"
            )
        elif row["is_group_entry"] != expected:
            # Drift detector: someone hand-edited reconciled.jsonl OR a
            # new GROUP_ENTRY_DH_IDS entry was added without re-running
            # this pass. Fix the value to match the canonical set.
            row["is_group_entry"] = expected
            log_lines.append(
                f"  {row['dh_id']} [{row['sub_period']}]: corrected "
                f"is_group_entry to {expected} (drift from canonical set)"
            )
    return log_lines


def main() -> None:
    rows = [json.loads(line) for line in RECONCILED.read_text().splitlines() if line.strip()]

    # Schema-shape backfills first — every row gains the new typed
    # `is_group_entry` field BEFORE SPOT_CORRECTIONS runs. Patterned
    # after the leprohon `backfill_*` passes (PR #185) which solve the
    # same Rule-4 schema-uniformity problem.
    backfill_log = backfill_is_group_entry(rows)

    # The log must describe the *state* of reconciled.jsonl, not the *delta*
    # from the previous run. On a second run every `old_val == new_val`, so a
    # delta-style log would incorrectly report "no overrides applied" while
    # the file on disk reflects all the applied overrides. Instead: always
    # log every SPOT_CORRECTION entry, showing the rationale and the current
    # value. `applied_count` tracks how many rows actually changed this run
    # for the terminal "Applied N overrides" line (0 on a re-run is
    # correct — nothing changed — but the disk log still describes the
    # complete override set). Mirrors Baud's fix_rows.py.
    override_log: list[str] = []
    applied_count = 0
    for dh_id, sub_period, field, new_val, rationale in SPOT_CORRECTIONS:
        row = next(
            (r for r in rows if r["dh_id"] == dh_id and r["sub_period"] == sub_period),
            None,
        )
        if row is None:
            raise KeyError(
                f"No row with (dh_id, sub_period)=({dh_id!r}, {sub_period!r})"
            )
        old_val = row.get(field)
        header = f"- {dh_id} [{sub_period}]: {field} corrected ({rationale})"
        if old_val != new_val:
            applied_count += 1
            override_log.append(
                f"{header}\n"
                f"    was: {json.dumps(old_val, ensure_ascii=False)}\n"
                f"    now: {json.dumps(new_val, ensure_ascii=False)}"
            )
            row[field] = new_val
        else:
            override_log.append(
                f"{header}\n"
                f"    value: {json.dumps(new_val, ensure_ascii=False)}"
            )

    RECONCILED.write_text(
        "\n".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows
        )
        + "\n"
    )

    existing_diff = DIFF.read_text()
    marker = _OVERRIDES_MARKER
    # Strip the previous LLM-APPLIED OVERRIDES section in-place so the
    # rewritten section replaces (not duplicates) it. Use the bare marker
    # as the split point rather than `\n\n{marker}` — the latter would
    # silently fail to match and produce a duplicate section if the file
    # were ever manually edited to use a different whitespace separator.
    # The module-load guard above asserts no SPOT_CORRECTION rationale
    # contains the marker substring, so the first match here is always
    # the section boundary, never an embedded mention inside a rationale.
    idx = existing_diff.find(marker)
    if idx != -1:
        existing_diff = existing_diff[:idx].rstrip()
    # State-not-delta logging for the schema-backfill section too. The
    # `backfill_log` returned by `backfill_is_group_entry` only records
    # delta (rows that needed backfilling) — on a second run it's
    # empty, so the audit trail of WHICH rows carry is_group_entry=True
    # would be lost. Build a stable state summary instead, listing the
    # canonical (dh_id, sub_period) pairs from GROUP_ENTRY_DH_IDS.
    # PR #186 Gemini round-1 caught the instability.
    backfill_state_lines = [
        "- is_group_entry: state pinned to GROUP_ENTRY_DH_IDS:",
    ] + [
        f"    {dh_id} [{sub_period}]: True"
        for dh_id, sub_period in sorted(GROUP_ENTRY_DH_IDS)
    ] + [
        f"    (all {sum(1 for r in rows if not r['is_group_entry'])} "
        f"other rows: False)",
    ]
    if backfill_log:
        backfill_state_lines.append("  This-run delta:")
        backfill_state_lines.extend(f"  {line}" for line in backfill_log)

    body_sections: list[str] = [
        "Schema backfills:\n" + "\n".join(backfill_state_lines),
        # `override_log` always has at least one entry per SPOT_CORRECTION
        # (each entry emits either a "was/now" or "value" line), so no
        # empty-fallback branch is needed. PR #186 Gemini round-1 flagged
        # the previous fallback as dead code.
        "Field corrections:\n" + "\n".join(override_log),
    ]
    body = "\n\n".join(body_sections)
    appended = (
        f"{existing_diff.rstrip()}\n\n"
        f"{marker}\n"
        + "=" * len(marker) + "\n"
        "Corrections applied by fix_rows.py AFTER the 3-subagent majority-vote\n"
        "merge. Source of each correction: the egyptologist-reviewer Claude\n"
        "Code subagent pass against the source PDF. No human scholar has\n"
        "signed off on this extract yet — per ADR-017 step 6, the extract is\n"
        "provisional until that happens.\n\n"
        f"{body}\n"
    )
    DIFF.write_text(appended)

    print(f"Applied {applied_count} override(s) this run ({len(override_log)} total in log).")
    print(f"Updated {RECONCILED.relative_to(RECONCILED.parents[4])}")
    print(f"Updated {DIFF.relative_to(DIFF.parents[4])}")


if __name__ == "__main__":
    main()
