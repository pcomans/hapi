"""Apply reviewer spot corrections and derive computed fields.

Baud 1999 — Famille royale et pouvoir sous l'Ancien Empire égyptien.
Follows the Dodson-Hilton / Kitchen pattern:

1. Load `reconciled.jsonl` (written by `merge.py`).
2. Apply `SPOT_CORRECTIONS` — per-row field overrides identified by
   the LLM `egyptologist-reviewer` pass; each carries a scholar-
   legible rationale. Extended per chunk via
   `CHUNK<N>_CORRECTIONS` → concatenated into `SPOT_CORRECTIONS`.
3. Apply `REDIRECT_CORRECTIONS` — rewrite redirect-stub rows so
   every non-redirect factual field is nulled/emptied. This is
   deterministic so `merge.py` can leave those fields at whatever
   the agents produced.
4. Derive `dynasty_min` / `dynasty_max` from
   `datation_raw` + `king` via the French-date parser below.
5. Derive `king_father` from `father_name` against a known
   Old-Kingdom king authority list (inline in this module — short
   enough and immutable).
6. Rewrite `reconciled.jsonl` with `json.dumps(..., sort_keys=True)`
   for deterministic diffs.
7. Append (or idempotently refresh) an
   `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED` section to
   `merge-disagreements.txt`.

Idempotent: re-running overwrites the override-log section,
re-derives the derived fields from the current input rows, and
re-applies `SPOT_CORRECTIONS` from scratch. Never mutates the agent
raw files.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/baud-1999-ok-royal-family/fix_rows.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
RECONCILED = SOURCE_DIR / "reconciled.jsonl"
DIFF = SOURCE_DIR / "merge-disagreements.txt"

OVERRIDE_MARKER = "\n\n=== LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED ===\n"


# ---------------------------------------------------------------------------
# Known-king authority for `king_father` derivation.
# ---------------------------------------------------------------------------
# French spellings as Baud prints them. Hedge suffixes (`"Snéfrou (probable)"`)
# are stripped before lookup via `_strip_hedge`; the base spelling must match
# one of these strings exactly.
KNOWN_OK_KINGS: frozenset[str] = frozenset(
    {
        # Dyn 3
        "Djoser",
        "Sékhemkhet",
        "Khaba",
        "Houni",
        # Dyn 4
        "Snéfrou",
        "Khoufou",
        "Rêdjedef",
        "Rêkhaef",
        "Menkaourê",
        "Chepseskaf",
        # Dyn 5
        "Ouserkaf",
        "Sahourê",
        "Néferirkarê",
        "Chepseskarê",
        "Néferefrê",
        "Niouserrê",
        "Menkaouhor",
        "Djedkarê",
        "Ounas",
        # Dyn 6
        "Téti",
        "Ouserkarê",
        "Pépi Ier",
        "Pépi I",
        "Mérenrê",
        "Pépi II",
        "Nitocris",
    }
)


HEDGE_PARENS_RE = re.compile(r"\s*\([^)]*\)\s*$")


def _strip_hedge(name: str) -> str:
    """Strip a trailing parenthetical hedge: 'Snéfrou (probable)' → 'Snéfrou'."""
    return HEDGE_PARENS_RE.sub("", name).strip()


# ---------------------------------------------------------------------------
# French-date parser.
# ---------------------------------------------------------------------------
# Maps printed Roman-numeral-plus-ordinal (often with `e` or `^e` superscript)
# to an integer. Case-insensitive match on the base form.
ROMAN_DYN_RE = re.compile(
    r"(?P<r>III|IV|VI|V)(?:[eèE]?)\s*(?:dynastie|dyn\.?|dynastie\s*\??)?",
    re.IGNORECASE,
)
ROMAN_TO_INT: dict[str, int] = {"III": 3, "IV": 4, "V": 5, "VI": 6}

# King-name → dynasty lookup (Dyn 3 is too sparse in Baud's OK corpus to
# need many entries; extend as future chunks surface cases).
KING_TO_DYNASTY: dict[str, int] = {
    # Dyn 3
    "Djoser": 3,
    "Sékhemkhet": 3,
    "Khaba": 3,
    "Houni": 3,
    # Dyn 4
    "Snéfrou": 4,
    "Khoufou": 4,
    "Rêdjedef": 4,
    "Rêkhaef": 4,
    "Menkaourê": 4,
    "Chepseskaf": 4,
    # Dyn 5
    "Ouserkaf": 5,
    "Sahourê": 5,
    "Néferirkarê": 5,
    "Chepseskarê": 5,
    "Néferefrê": 5,
    "Niouserrê": 5,
    "Menkaouhor": 5,
    "Djedkarê": 5,
    "Ounas": 5,
    # Dyn 6
    "Téti": 6,
    "Ouserkarê": 6,
    "Pépi Ier": 6,
    "Pépi I": 6,
    "Mérenrê": 6,
    "Pépi II": 6,
    "Nitocris": 6,
}


def derive_dynasty_bounds(
    datation_raw: str | None, king: str | None
) -> tuple[int | None, int | None]:
    """Return `(dynasty_min, dynasty_max)` inferred from Baud's date fields.

    Strategy:
    1. Scan `datation_raw` for Roman-numeral dynasty tokens; every distinct
       match contributes its integer to the candidate set. Spanning
       connectives `-`, `–`, `à` widen the range naturally: the min is the
       smallest matched integer, the max the largest.
    2. If no dynasty token matched, fall back to `king` — strip its hedge
       and look up the base spelling in `KING_TO_DYNASTY`. A match on
       `king` sets both min and max to that dynasty.
    3. If both steps produced nothing, return `(None, None)`. Baud's
       `"Inconnue"` / `null` entries hit this path.

    Raises nothing — a row whose date is unparseable simply stays
    `(None, None)` and downstream queries treat it as "dynasty
    unspecified".
    """
    candidates: set[int] = set()
    if datation_raw:
        for match in ROMAN_DYN_RE.finditer(datation_raw):
            roman = match.group("r").upper()
            candidates.add(ROMAN_TO_INT[roman])

    if not candidates and king:
        base = _strip_hedge(king)
        # Try exact king match, then with trailing adverbs stripped
        # ("Rêkhaef au plus tard" → "Rêkhaef"; "Khoufou environ" → "Khoufou").
        for tail in (" au plus tard", " environ", " ou plus", " ou plus tôt"):
            if base.endswith(tail):
                base = base[: -len(tail)].strip()
        if base in KING_TO_DYNASTY:
            dyn = KING_TO_DYNASTY[base]
            return dyn, dyn

    if not candidates:
        return None, None
    return min(candidates), max(candidates)


def derive_king_father(father_name: str | None) -> str | None:
    """Return `father_name` verbatim if its base spelling is a known OK king;
    else `None`. Preserves hedges in the output (`"Snéfrou (probable)"` →
    returned as-is when `"Snéfrou"` is a known king).
    """
    if not father_name:
        return None
    base = _strip_hedge(father_name)
    if base in KNOWN_OK_KINGS:
        return father_name
    return None


# ---------------------------------------------------------------------------
# SPOT_CORRECTIONS — populated after the LLM egyptologist-reviewer pass.
# ---------------------------------------------------------------------------
# Each tuple is `(baud_id, field, new_value, rationale)`.
# Rationale must be scholar-legible (cite the Baud page or a cross-ref,
# not "LLM said so").
CHUNK1_CORRECTIONS: list[tuple[str, str, object, str]] = []

SPOT_CORRECTIONS: list[tuple[str, str, object, str]] = list(CHUNK1_CORRECTIONS)


# ---------------------------------------------------------------------------
# Redirect-row normalisation.
# ---------------------------------------------------------------------------
# A redirect row (`redirect_to` != None) must have every non-redirect
# factual field nulled/emptied regardless of what the agents produced.
NULLABLE_FIELDS: tuple[str, ...] = (
    "head_note",
    "king",
    "datation_raw",
    "dynasty_min",
    "dynasty_max",
    "father_name",
    "mother_name",
    "king_father",
    "sex",
    "notes",
)
EMPTY_LIST_FIELDS: tuple[str, ...] = (
    "monuments",
    "pm_refs",
    "publications",
    "titles",
    "spouse_names",
    "children_names",
)


def normalise_redirect_row(row: dict) -> dict:
    """Return `row` with non-redirect factual fields nulled/emptied if
    `redirect_to` is set. Non-redirect rows are returned unchanged."""
    if row.get("redirect_to") is None:
        return row
    out = dict(row)
    for field in NULLABLE_FIELDS:
        out[field] = None
    for field in EMPTY_LIST_FIELDS:
        out[field] = []
    out["asterisk"] = False
    return out


# ---------------------------------------------------------------------------
# Driver.
# ---------------------------------------------------------------------------
def apply_overrides(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """Return `(fixed_rows, override_log_lines)`.

    Applies, in order: SPOT_CORRECTIONS → redirect-row normalisation →
    derive `dynasty_min`/`dynasty_max` → derive `king_father`.
    """
    by_id = {r["baud_id"]: dict(r) for r in rows}
    log: list[str] = []

    for baud_id, field, new_value, rationale in SPOT_CORRECTIONS:
        if baud_id not in by_id:
            raise KeyError(
                f"SPOT_CORRECTIONS references unknown baud_id={baud_id!r}; "
                f"reconciled.jsonl must contain every targeted row."
            )
        old = by_id[baud_id].get(field)
        by_id[baud_id][field] = new_value
        log.append(
            f"{baud_id}.{field}: "
            f"{json.dumps(old, ensure_ascii=False)} → "
            f"{json.dumps(new_value, ensure_ascii=False)} "
            f"[{rationale}]"
        )

    for baud_id, row in list(by_id.items()):
        by_id[baud_id] = normalise_redirect_row(row)

    for baud_id, row in by_id.items():
        dyn_min, dyn_max = derive_dynasty_bounds(
            row.get("datation_raw"), row.get("king")
        )
        row["dynasty_min"] = dyn_min
        row["dynasty_max"] = dyn_max
        row["king_father"] = derive_king_father(row.get("father_name"))

    fixed = [by_id[bid] for bid in sorted(by_id.keys())]
    return fixed, log


def rewrite_override_section(existing: str, log: list[str]) -> str:
    """Split off any previous override section; append the fresh one."""
    head = existing.split(OVERRIDE_MARKER, 1)[0]
    if not log:
        return head  # No overrides this run; drop stale section.
    body = "\n".join(log)
    return f"{head}{OVERRIDE_MARKER}{body}\n"


def main() -> None:
    rows = [
        json.loads(line)
        for line in RECONCILED.read_text().splitlines()
        if line.strip()
    ]
    fixed, log = apply_overrides(rows)

    RECONCILED.write_text(
        "\n".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) for r in fixed
        )
        + "\n"
    )

    existing = DIFF.read_text() if DIFF.exists() else ""
    DIFF.write_text(rewrite_override_section(existing, log))

    print(f"Fixed {len(fixed)} rows.")
    print(f"Applied {len(log)} override(s) / derived-field updates.")
    print(f"Wrote {RECONCILED.name}, {DIFF.name}.")


if __name__ == "__main__":
    main()
