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
POWER_CORRECTIONS: list[tuple[str, str, str, object, str]] = [
    (
        "Tiaa A",
        "The Power and the Glory",
        "notes",
        "Wife of Amenhotep II and mother of Thutmose IV. A number of "
        "monuments were created for her by the latter at Giza, Thebes "
        "and the Fayoum, including a number of usurpations of material "
        "belonging to Meryetre-Hatshepsut. She was buried in tomb KV32, "
        "where many fragments of her funerary equipment have been found; "
        "some material was washed by floodwater into the adjacent tomb "
        "KV47, where it was for a long time thought to belong to a "
        "like-named mother of Siptah.",
        'Gemini OCR dropped the article "a" in "including a number of '
        'usurpations" and left a stray colon after "including". The PDF '
        "(p. 140 col 2, Tiaa A entry) reads with the article; `notes` "
        "is a verbatim-quotation field so the reviewer's correction is "
        "applied rather than preserving the OCR artifact.",
    ),
]


AMARNA_CORRECTIONS: list[tuple[str, str, str, object, str]] = [
    (
        "[...]18A–H",
        "The Amarna Interlude",
        "notes",
        "Daughters of Amenhotep III, shown in the tomb of Kheruef "
        "(TT192; see p. 30); some may be identical with named "
        "daughters.",
        "Majority-voted notes retained an editorial tail ('Group entry "
        "covering multiple daughters.') added by agent-a that is not in "
        "D&H's prose on p. 157. `notes` is a verbatim-quotation field; "
        "the tail is stripped.",
    ),
    (
        "[...]18K–N",
        "The Amarna Interlude",
        "notes",
        "Daughters of Anen; depicted with their siblings in tomb TT120.",
        "Majority-voted notes retained the same 'Group entry covering "
        "multiple daughters.' editorial tail added by agent-a. Stripped "
        "for verbatim fidelity to D&H p. 157.",
    ),
    (
        "Tey",
        "The Amarna Interlude",
        "notes",
        "Wife of Ay A and 'nurse' (= stepmother?) of Nefertiti; shown "
        "with her husband in his tomb at Amarna and later became his "
        "queen. As such, she is depicted with Ay in his royal tomb in "
        "the Valley of the Kings (WV23) and in the rock-chapel of Min "
        "at Akhmim. If she were the mother of Nakhtmin B, she will also "
        "have held the title of Adorer of Min.",
        "Majority-voted notes retained agent-a's editorial tail 'D&H "
        "writes the role code KGW twice in the parenthetical; treated "
        "as a single role per extraction rules.' That is meta-commentary "
        "about the extraction, not D&H prose. Stripped. The KGW "
        "deduplication itself is correct (see roles field).",
    ),
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


SPOT_CORRECTIONS: list[tuple[str, str, str, object, str]] = (
    POWER_CORRECTIONS + AMARNA_CORRECTIONS + RAMESSIDE_CORRECTIONS
)


def main() -> None:
    rows = [json.loads(line) for line in RECONCILED.read_text().splitlines() if line.strip()]

    override_log: list[str] = []
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
        if old_val == new_val:
            continue
        override_log.append(
            f"- {dh_id} [{sub_period}]: {field} corrected ({rationale})\n"
            f"    was: {json.dumps(old_val, ensure_ascii=False)}\n"
            f"    now: {json.dumps(new_val, ensure_ascii=False)}"
        )
        row[field] = new_val

    RECONCILED.write_text(
        "\n".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows
        )
        + "\n"
    )

    existing_diff = DIFF.read_text()
    marker = "LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED"
    if marker in existing_diff:
        head, _, _ = existing_diff.partition(f"\n\n{marker}")
        existing_diff = head
    body = (
        "\n".join(override_log)
        if override_log
        else "- No overrides applied. The reviewer pass produced no "
        "actionable corrections on `reconciled.jsonl` for this chunk."
    )
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

    print(f"Applied {len(override_log)} override(s).")
    print(f"Updated {RECONCILED.relative_to(RECONCILED.parents[4])}")
    print(f"Updated {DIFF.relative_to(DIFF.parents[4])}")


if __name__ == "__main__":
    main()
