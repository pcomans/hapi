"""Apply deterministic normalization + LLM-reviewer corrections to reconciled.jsonl.

Run AFTER merge.py. Mirrors Dodson-Hilton's pattern — idempotent re-runs,
append-only LLM-APPLIED OVERRIDES section in merge-disagreements.txt,
every override recorded with rationale.

Two passes:

1. **Deterministic transliteration normalization** (`_normalise_transliteration`).
   The three extraction agents rendered the Egyptological ayin and aleph
   characters inconsistently — the PDF's text layer hands out `ˁ` (U+02C1)
   / `ɛ` (U+025B) / `ɜ` (U+025C) as fallbacks, but the canonical IFAO /
   pharaoh.se / Beckerath convention is `ꜥ` (U+A725) and `ꜣ` (U+A723).
   Majority-vote on majority-fallback selected the wrong codepoints; a
   deterministic post-pass restores the canonical form across every
   string-valued field recursively. Parallels Kitchen's
   `concurrent_with_kings` recomputation: "interval overlap is a pure
   function of already-extracted fields, don't trust the LLMs on it."

2. **LLM-reviewer spot corrections** — populated after the
   egyptologist-reviewer subagent pass (empty list until then). Baud-specific
   risks: dropped hedges (Baud is especially hedge-heavy; OK prosopography
   is sparsely attested), scholarly judgment promoted to hard claim,
   missing `service_personnel: true` for asterisk-marked headwords.

Run:
    cd pipeline && uv run python pipeline/authority/sources/baud-1999-ok-royal-family/fix_rows.py

Idempotent: re-running replaces (not duplicates) the LLM-APPLIED OVERRIDES
section in merge-disagreements.txt. `merge-disagreements.txt` reflects the
PRE-normalization per-agent diff — it is the merge's audit trail of how
the three LLMs disagreed, and should not be regenerated post-normalization.
"""

from __future__ import annotations

import json
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
RECONCILED = SOURCE_DIR / "reconciled.jsonl"
DIFF = SOURCE_DIR / "merge-disagreements.txt"


# Egyptological-transliteration normalization table.
# Keys are the codepoints various extraction agents emit as fallbacks for
# ayin and aleph; values are the canonical IFAO / pharaoh.se codepoints.
# `str.translate()` applies this across every string in every row.
#
# `ˁ` (U+02C1 MODIFIER LETTER REVERSED GLOTTAL STOP) → `ꜥ` (U+A725 ayin)
# `ɛ` (U+025B LATIN SMALL LETTER OPEN E)             → `ꜥ` (U+A725 ayin)
# `ɜ` (U+025C LATIN SMALL LETTER REVERSED OPEN E)    → `ꜣ` (U+A723 aleph)
#
# The target codepoints are the characters the extraction prompt specifies
# ("ꜣ ꜥ ḥ ḫ ẖ š ṯ ḏ"). Agent B used them correctly; agents A and C used
# fallback codepoints that majority-vote then selected.
_TRANSLIT_NORMALIZE = {
    0x02C1: 0xA725,  # ˁ → ꜥ
    0x025B: 0xA725,  # ɛ → ꜥ
    0x025C: 0xA723,  # ɜ → ꜣ
}


def _normalise_transliteration(obj: object) -> object:
    """Recursively apply the transliteration normalization to every string
    value in the row. Preserves structure (dict/list/scalar) and non-string
    leaves (int, bool, None) unchanged.
    """
    if isinstance(obj, str):
        return obj.translate(_TRANSLIT_NORMALIZE)
    if isinstance(obj, list):
        return [_normalise_transliteration(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _normalise_transliteration(v) for k, v in obj.items()}
    return obj


# Chunk-1 corrections identified by the egyptologist-reviewer subagent pass.
# Each entry: (baud_id, field, new_value, rationale).
# Corrections are applied AFTER transliteration normalization, so
# `new_value` strings MUST already use the canonical ꜥ / ꜣ codepoints
# (not the fallback ˁ / ɛ / ɜ that the merged rows carried pre-normalization).
CHUNK1_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "baud-22",
        "monument",
        "1: Stèles-bornes, remployées, complexe funéraire de Djoser; "
        "2: Représentée dans le temple de Djoser à Héliopolis",
        "Baud's header for Jnt-kꜣ.s (printed p. 415) enumerates two documents: "
        "(1) the Saqqara stèles-bornes and (2) a representation in Djoser's "
        "Heliopolis temple. Majority-vote dropped document 2, losing the "
        "Heliopolis provenance that Phase A site-reconciliation will want. "
        "Restored with the '1:' / '2:' numbering Baud uses.",
    ),
    (
        "baud-26",
        "children_names",
        [],
        "Baud's DIVERS + figure 34 (physical p. 418–419) make clear that "
        "Sꜥnḫ-n-Ptḥ is Jḫj's grandchild (petit-fils), not child. "
        "Baud's own prose: '(b) Sꜥnḫ-n-Ptḥ, son petit-fils' — an unnamed "
        "son-generation sits between them. `children_names` is scoped to "
        "direct children per README; the grandchild is already correctly "
        "captured in `notes_from_baud`. No fabrication of the intermediate "
        "'X' son — Baud himself leaves it unnamed.",
    ),
    (
        "baud-28",
        "roles",
        ["priest of the king's mother", "priest of the royal pyramid"],
        "Baud's TITRES (physical p. 420) lists wꜥb Bꜣ-Nfr-jr-kꜣ-Rꜥ as the "
        "first title — 'priest of Neferirkare's pyramid'. The controlled "
        "vocab includes `priest of the royal pyramid` for exactly this "
        "ḥm-nṯr/wꜥb-of-named-pyramid pattern. Agent A proposed the richer "
        "list and was majority-voted down; the title is unambiguous and "
        "derives directly from titles_from_baud per README rules.",
    ),
    (
        "baud-33",
        "mother_name",
        "Mr.s-ꜥnḫ III (per Baud)",
        "Baud's PARENTÉ for ꜥnḫ-m-ꜥ-Rꜥ (physical p. 423) introduces the "
        "mother through Hassan → Strudwick's titular-synchronism argument, "
        "with Baud explicitly flagging it as inferential: 'est-ce "
        "l'appartenance à une autre branche par sa mère?' This is a "
        "scholarly-judgment attribution, not an attested filiation; the "
        "`(probable)` hedge understates it. Per README § 'Interpretive-"
        "facts caveat', `(per Baud)` distinguishes asserted-by-Baud from "
        "attested-in-source.",
    ),
    (
        "baud-37",
        "name_anglicised",
        "Ankhesenmeryre I",
        "'Ankhesenmerire' transliterates the French-form Mrjj-Rꜥ directly; "
        "the conventional English form used in modern Egyptological "
        "scholarship (Dodson-Hilton, pharaoh.se) is 'Ankhesenmeryre' "
        "(with -y- in the Meryre component). Phase A reconciliation against "
        "pharaoh.se's Conventional English Display Form expects this form.",
    ),
    (
        "baud-38",
        "name_anglicised",
        "Ankhesenmeryre II",
        "Same French-to-conventional-English fix as baud-37 — "
        "Ankhesenmerire → Ankhesenmeryre. Preserves the homonymy with "
        "baud-37 (her predecessor of the same name) under the "
        "standard English convention.",
    ),
    (
        "baud-38",
        "spouse_names",
        ["Pépi Iᵉʳ"],
        "ꜥnḫ.s-n-Mrjj-Rꜥ II was the mother of Pépi II, not a wife — "
        "Baud's titles list (physical p. 428) gives her ḥmt nswt Mn-nfr-"
        "Mrjj-Rꜥ (wife of Pépi Iᵉʳ's pyramid) and mwt nswt Mn-ꜥnḫ-Nfr-"
        "kꜣ-Rꜥ (mother of Pépi II's pyramid). The 'Pépi II (?)' entry in "
        "spouse_names is a confusion with her regent role for her son. "
        "children_names already correctly contains Pépi II.",
    ),
    (
        "baud-40",
        "roles",
        ["priest of the king", "priest of the royal pyramid"],
        "Baud's TITRES (physical p. 432) lists three ḥm-nṯr royal-cult "
        "titles (ḥm-nṯr Ḫwfw, ḥm-nṯr Sꜣḥw-Rꜥ, ḥm-nṯr Nfr-jr-kꜣ-Rꜥ) — each "
        "maps to `priest of the royal pyramid` in the controlled vocab. "
        "Agent A proposed the richer list; majority-vote narrowed to the "
        "generic `priest of the king` only. DIVERS rubric also highlights "
        "prêtrises + intendance. `jmj-r prw msw nswt` (steward of the "
        "king's children's houses) is an additional role attested here "
        "but not yet in the seeded controlled vocabulary; it is deferred "
        "to a chunk-2 prompt update for the vocab expansion.",
    ),
]


SPOT_CORRECTIONS: list[tuple[str, str, object, str]] = CHUNK1_CORRECTIONS


def main() -> None:
    rows = [json.loads(line) for line in RECONCILED.read_text().splitlines() if line.strip()]

    # Pass 1: deterministic transliteration normalization across every row.
    rows = [_normalise_transliteration(r) for r in rows]

    # Pass 2: LLM-reviewer spot corrections.
    override_log: list[str] = []
    for baud_id, field, new_val, rationale in SPOT_CORRECTIONS:
        row = next((r for r in rows if r["baud_id"] == baud_id), None)
        if row is None:
            raise KeyError(f"No row with baud_id={baud_id!r}")
        old_val = row.get(field)
        if old_val == new_val:
            continue
        override_log.append(
            f"- {baud_id}: {field} corrected ({rationale})\n"
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
