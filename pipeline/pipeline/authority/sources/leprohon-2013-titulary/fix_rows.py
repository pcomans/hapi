"""Apply post-merge corrections to Leprohon's reconciled.jsonl.

Two classes of correction (per the Phase-0 playbook):

1. **Spot corrections** — specific rows the `egyptologist-reviewer` subagent
   flagged against the PDF. Hard-coded in `EARLY_DYNASTIC_CORRECTIONS` as
   `(leprohon_id, json_path, new_value, rationale)` tuples. Every rationale
   is scholar-legible — "book p. X shows Y, not Z" rather than "LLM said so".

2. **Deterministic recomputation** — fields that are a pure function of
   other extracted fields. Leprohon's schema does NOT currently have such
   fields (unlike Kitchen's `concurrent_with_kings`, which derives from
   BCE date intervals); the `variant_index` is extractor-driven, not a
   post-merge derivation. This section is empty for now and reserved for
   future chunks (e.g. a cross-source `pharaoh_se_join_key` if Phase A
   demands one).

`json_path` is a dotted-path string used by `_set_by_path` to address
nested dict/list entries. Examples:
  - `"display_name"` — set top-level scalar.
  - `"horus_names.0.translation"` — set the translation of the first
    `horus_names` entry.
  - `"later_cartouche_names.2.attested_in"` — set the attested_in list
    of the third later_cartouche_names entry.

Every applied correction is appended to `merge-disagreements.txt` under
the heading `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED`. Re-running
`fix_rows.py` is idempotent — the log section is replaced in place, not
duplicated.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/leprohon-2013-titulary/fix_rows.py

Outputs:
    reconciled.jsonl                 (rewritten in place with corrections)
    merge-disagreements.txt          (override-log section appended/replaced)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
RECONCILED = SOURCE_DIR / "reconciled.jsonl"
DIFF = SOURCE_DIR / "merge-disagreements.txt"

OVERRIDE_HEADER = "=== LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED ===\n"


# Per-chunk correction lists. Concatenated into SPOT_CORRECTIONS below.
#
# Format: (leprohon_id, json_path, new_value, rationale)

EARLY_DYNASTIC_CORRECTIONS: list[tuple[str, str, object, str]] = [
    # Egyptologist-reviewer 2026-04-20: page range transcription error in
    # agent-merged source_note. Leprohon p. 22 fn. 12 opens with "Gauthier
    # 1907, 1–3, 17–19" — pypdf extracted this correctly; OCR misread "1–3"
    # as "4–5" and the merge majority-voted for OCR. Restore the pypdf form.
    (
        "leprohon-0.03",
        "horus_names.0.source_note",
        (
            "Gauthier 1907, 1–3, 17–19; von Beckerath 1999, 36–37. "
            "Narmer is possibly the King Menes—Egyptian mni (meni), "
            '"The established one"—of tradition, although some scholars '
            "equate the Horus Aha with Menes. See, lately, the discussion "
            "in Raffaele 2003, 106–7."
        ),
        "Leprohon p. 22 fn. 12 opens with 'Gauthier 1907, 1–3, 17–19'; OCR "
        "misread as '4–5', pypdf had it correctly. Egyptologist-reviewer "
        "2026-04-20 confirmed against the PDF.",
    ),
    # NOTE: the original egyptologist-reviewer 2026-04-20 pass flagged
    # leprohon-1.06 Semerkhet's Horus transliteration `smr ẖt` as wanting
    # `smr ḫt` instead. That correction was WRONG and has been removed
    # after user-directed re-verification (2026-04-20):
    #
    # 1. The publisher's embedded PDF text layer for Leprohon p. 26 is
    #    `smr Xt` (capital X). In Manuel de Codage, `X` → ẖ (h-with-line-
    #    below, "body"); `x` → ḫ (h-with-breve-below, "thing"). pypdf
    #    read the text layer faithfully and the MdC normalizer applied
    #    the correct `X → ẖ` mapping.
    # 2. The reviewer argued `kh` in the anglicised gloss `(semer khet)`
    #    implied ḫ — but `kh` is an anglicisation of BOTH ẖ and ḫ, so
    #    the gloss alone doesn't disambiguate.
    # 3. Semantic check: ẖt = "body", ḫt = "thing / matter". Leprohon's
    #    own translation reads "Friend of the (divine) body (i.e., the
    #    Ennead)" — "body" maps to ẖt, confirming pypdf.
    # 4. Visual inspection of the rendered PDF page 26 (user request,
    #    2026-04-20) confirms the glyph is h-with-line-below (ẖ), not
    #    h-with-breve (ḫ). The reviewer misread the rendered diacritic.
    #
    # Lesson recorded in user feedback memory: don't silently apply
    # reviewer corrections that contradict deterministic pipeline output
    # plus the source's own translation. Over-trusting a single reviewer
    # verdict against corroborating evidence produced a regression here.
    # Future MdC `X` vs `x` disagreements: verify text layer + gloss +
    # translation semantics BEFORE overriding pypdf.
    # Egyptologist-reviewer 2026-04-20: the extractors included the
    # translation's leading "Seth, " in the anglicised column. Leprohon
    # p. 29 prints only `(per(u) ib.sen)` in the parenthetical gloss; the
    # "Seth," prefix belongs to the translation column.
    (
        "leprohon-2.07",
        "seth_names.0.anglicised",
        "per(u) ib.sen",
        "Leprohon p. 29: parenthetical gloss is '(per(u) ib.sen)' only. The "
        "'Seth,' prefix the agents concatenated belongs to the translation "
        "column ('Seth, (for whom ?) their will has come forth'), not the "
        "anglicised field. Egyptologist-reviewer 2026-04-20 high-confidence.",
    ),
    # Egyptologist-reviewer 2026-04-20: translator-glosses (fn. 60) from
    # the *translation* column leaked into source_note. "Horus and Seth."
    # is fn. 60 glossing the "two powers" in the translation — not a
    # scholarly source-note.
    (
        "leprohon-2.01",
        "horus_names.0.source_note",
        "Gauthier 1907, 37; von Beckerath 1999, 42–43.",
        "Trim trailing 'Horus and Seth.' — fn. 60 is a translator-gloss on "
        "'two powers', not scholarly commentary. Belongs dropped per schema "
        "'source_note = non-attestation scholarly commentary'.",
    ),
    # Egyptologist-reviewer 2026-04-20: same pattern as 2.01 — chained
    # translator-glosses from fns. 81 and 82 leaked into source_note.
    (
        "leprohon-2.08",
        "horus_names.1.source_note",
        (
            "Horus/Seth 2 form: the king reconciled the Seth and Horus "
            "traditions; the serekh is topped by BOTH Horus and Seth "
            "animals. See the accompanying Two Ladies entries which "
            "repeat this dual form."
        ),
        "Trim trailing 'Horus and Seth; both animals appear on the top of "
        "the serekh. Horus and Seth again.' — these are fns. 81 and 82 "
        "glossing 'two powerful ones' and 'two lords' in the translation, "
        "not source-notes.",
    ),
    (
        "leprohon-2.08",
        "nebty_names.0.source_note",
        (
            "Horus/Seth 2 form: the king reconciled the Seth and Horus "
            "traditions; the serekh is topped by BOTH Horus and Seth "
            "animals. See the accompanying Two Ladies entries which "
            "repeat this dual form. If the two signs nbwy in the last "
            "phrase were placed in honorific transposition, this part "
            "of the name might read ḥtp nbwy im.f, \"The two lords "
            "within him are satisfied.\""
        ),
        "Keep the honorific-transposition footnote (fn. 83 — scholarly "
        "note on the name's meaning) but remove the duplicated dual-form "
        "description if it's chained in. Minimal rewrite to lock the canonical form.",
    ),
]

SPOT_CORRECTIONS: list[tuple[str, str, object, str]] = [
    *EARLY_DYNASTIC_CORRECTIONS,
]


# Deterministic post-pass: the 3-agent extraction prompt told agents to flag
# OCR-vs-pypdf transliteration disagreements via a debug string appended to
# `source_note`. Majority vote propagated that debug string into the merged
# output for ~10 rows. The egyptologist-reviewer 2026-04-20 flagged this as
# schema-level debug-string leakage; we strip it deterministically across
# every name-entry `source_note` before spot corrections run.
OCR_PYPDF_DEBUG_RE = re.compile(
    r"\s*(?:^|\. )?OCR vs pypdf (?:transliteration )?disagreement:.*?$",
    flags=re.DOTALL,
)


def _strip_ocr_pypdf_debug(text: str | None) -> str | None:
    if not text:
        return text
    cleaned = OCR_PYPDF_DEBUG_RE.sub("", text).strip()
    return cleaned if cleaned else None


def _set_by_path(row: dict, path: str, value: object) -> None:
    """Set a nested field in a row by dotted-path string.

    Numeric path segments index into lists; non-numeric segments key into
    dicts. Raises KeyError / IndexError on unreachable paths — we do NOT
    silently succeed on a typo'd path because that would hide broken
    corrections.
    """
    parts = path.split(".")
    *parents, leaf = parts
    cursor: object = row
    for part in parents:
        if part.isdigit():
            assert isinstance(cursor, list), (
                f"path {path!r}: expected list at segment {part!r}, got {type(cursor).__name__}"
            )
            cursor = cursor[int(part)]
        else:
            assert isinstance(cursor, dict), (
                f"path {path!r}: expected dict at segment {part!r}, got {type(cursor).__name__}"
            )
            cursor = cursor[part]
    if leaf.isdigit():
        assert isinstance(cursor, list)
        cursor[int(leaf)] = value
    else:
        assert isinstance(cursor, dict)
        cursor[leaf] = value


NAME_LIST_FIELDS = (
    "horus_names",
    "nebty_names",
    "golden_horus_names",
    "throne_names",
    "birth_names",
    "later_cartouche_names",
    "later_horus_names",
    "seth_names",
)


def strip_debug_leakage(rows: list[dict]) -> list[str]:
    """Walk every name-entry in every row and strip the OCR-vs-pypdf debug
    string from `source_note`. Returns log lines describing each strip.

    Runs BEFORE spot corrections so that the spot corrections operate on
    already-cleaned text (simplifying their rationale descriptions).
    """
    log_lines: list[str] = []
    for row in rows:
        lid = row["leprohon_id"]
        for field in NAME_LIST_FIELDS:
            for idx, entry in enumerate(row.get(field, [])):
                before = entry.get("source_note")
                after = _strip_ocr_pypdf_debug(before)
                if after != before:
                    entry["source_note"] = after
                    log_lines.append(
                        f"  {lid} / {field}.{idx}.source_note:\n"
                        f"    stripped OCR-vs-pypdf debug tail\n"
                        f"    before: {json.dumps(before, ensure_ascii=False)}\n"
                        f"    after:  {json.dumps(after, ensure_ascii=False)}"
                    )
    return log_lines


def apply_corrections() -> list[str]:
    """Apply deterministic debug-string strip + every SPOT_CORRECTIONS entry
    to reconciled.jsonl in place.

    Returns a list of human-readable log lines describing each applied
    correction, for appending to merge-disagreements.txt.
    """
    rows = [json.loads(line) for line in RECONCILED.read_text().splitlines() if line.strip()]
    log_lines: list[str] = []

    # Deterministic pass first — strips debug-string leakage uniformly so that
    # any spot corrections that follow operate on clean text.
    log_lines.extend(strip_debug_leakage(rows))

    by_id = {r["leprohon_id"]: r for r in rows}
    for lid, path, new_value, rationale in SPOT_CORRECTIONS:
        if lid not in by_id:
            raise KeyError(f"SPOT_CORRECTIONS references unknown leprohon_id: {lid!r}")
        row = by_id[lid]
        _set_by_path(row, path, new_value)
        log_lines.append(
            f"  {lid} / {path}:\n"
            f"    new value: {json.dumps(new_value, ensure_ascii=False, sort_keys=True)}\n"
            f"    rationale: {rationale}"
        )
    RECONCILED.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows)
        + "\n"
    )
    return log_lines


def update_diff_log(log_lines: list[str]) -> None:
    """Append / replace the override-log section in merge-disagreements.txt."""
    existing = DIFF.read_text() if DIFF.exists() else ""
    if OVERRIDE_HEADER in existing:
        body_before = existing.split(OVERRIDE_HEADER, 1)[0]
    else:
        body_before = existing
    if not body_before.endswith("\n"):
        body_before += "\n"
    new_body = body_before + "\n" + OVERRIDE_HEADER
    if log_lines:
        new_body += "\n".join(log_lines) + "\n"
    else:
        new_body += "(no overrides applied)\n"
    DIFF.write_text(new_body)


def main() -> None:
    log_lines = apply_corrections()
    update_diff_log(log_lines)
    print(f"Applied {len(log_lines)} SPOT_CORRECTIONS.")


if __name__ == "__main__":
    main()
