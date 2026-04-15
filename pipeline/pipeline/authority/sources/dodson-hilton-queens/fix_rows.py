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
# Each entry: (dh_id, field, new_value, rationale).
SPOT_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "Tiaa A",
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
    # --- Amarna chunk (p142–p145) ---
    (
        "[...]18A–H",
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
        "notes",
        "Daughters of Anen; depicted with their siblings in tomb TT120.",
        "Majority-voted notes retained the same 'Group entry covering "
        "multiple daughters.' editorial tail added by agent-a. Stripped "
        "for verbatim fidelity to D&H p. 157.",
    ),
    (
        "Tey",
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
        "alt_names",
        ["Neferneferuaten"],
        "Same allcaps-vs-titlecase normalisation as Amenhotep E: agents "
        "preserved D&H's BOLD-CAPITALS rendering of the regnal name "
        "**NEFERNEFERUATEN** as 'NEFERNEFERUATEN'. Titlecase matches "
        "museum-catalogue spelling and the rest of the source's alt_names.",
    ),
    (
        "Ankhesenpaaten",
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


def main() -> None:
    rows = [json.loads(line) for line in RECONCILED.read_text().splitlines() if line.strip()]

    override_log: list[str] = []
    for dh_id, field, new_val, rationale in SPOT_CORRECTIONS:
        row = next((r for r in rows if r["dh_id"] == dh_id), None)
        if row is None:
            raise KeyError(f"No row with dh_id {dh_id!r}")
        old_val = row.get(field)
        if old_val == new_val:
            continue
        override_log.append(
            f"- {dh_id}: {field} corrected ({rationale})\n"
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
