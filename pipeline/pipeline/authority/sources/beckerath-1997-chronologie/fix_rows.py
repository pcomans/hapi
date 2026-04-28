"""Apply egyptologist-reviewer-identified corrections to reconciled.jsonl.

Run AFTER merge.py to layer scholarly corrections on top of the 3-subagent
majority vote. Every correction is recorded in merge-disagreements.txt under
the `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED` section so the audit trail
is preserved.

Source of corrections: egyptologist-reviewer Claude Code subagent pass against
pre-rendered single-book-page JPEG scans (scan-NNN-{left,right}.jpg) of
Beckerath 1997 Anhang A + Supplement zu A.

Run:
    cd pipeline && uv run python pipeline/authority/sources/beckerath-1997-chronologie/fix_rows.py
"""

from __future__ import annotations

import json
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
RECONCILED = SOURCE_DIR / "reconciled.jsonl"
DIFF = SOURCE_DIR / "merge-disagreements.txt"


# beckerath_id → dict of fields to override.
# Only fields listed here are changed; all others are preserved verbatim.
# Every entry is backed by a specific scan reference documented in the
# LLM-APPLIED OVERRIDES section appended to merge-disagreements.txt.
#
# History note (2026-04-28 OCR redo). The previous OCR pipeline fed
# double-page-spread JPEGs to a single subagent, which produced a class of
# column-drift errors at the page fold (most visibly: row 11.03 An-jotef III
# had its parenthetical spliced with fragments from book p189). The
# split-single-book-page OCR now feeds each book page as its own JPEG,
# eliminating the cross-fold drift mechanism. As a result, ~10 overrides that
# this branch previously carried became redundant (merge now produces the
# correct values directly) or actively harmful (the old overrides forced the
# previous OCR's misread values onto rows the new OCR reads correctly).
# Every surviving override here was re-verified against the printed PDF
# (scan-NNN-{left,right}.jpg renders) on 2026-04-28.
OVERRIDES: dict[str, dict] = {

    # ── Dyn 3 brace bracket (scan-105-right) ──────────────────────────────
    # Beckerath prints a brace `}` spanning Hor Cha-bai / Sôuphis,Mesochris /
    # Ahu with the shared range 2663/2613–2639/2589. The agents now extract
    # the dates correctly (the bracket-propagation cue is a visual `}` glyph
    # the OCR doesn't preserve, but the merge majority pulls the bracket-end
    # date through). The remaining override is the cross-row editorial note
    # tying the three rows together for downstream readers; the field
    # contract reads canonical `name` plus `beckerath_id` in parentheses.
    "03.04": {
        "editorial_notes": "shared bracket range with Sôuphis (03.05) and Ahu (03.06) (scan-105-right)",
    },
    "03.05": {
        "editorial_notes": "shared bracket range with Hor Cha-bai (03.04) and Ahu (03.06) (scan-105-right)",
    },
    "03.06": {
        "editorial_notes": "shared bracket range with Hor Cha-bai (03.04) and Sôuphis (03.05) (scan-105-right)",
    },

    # ── Dyn 15 Hyksos brace bracket (scan-106-right) ──────────────────────
    # Beckerath prints a brace spanning Bêôn / Apachnas / Chajan with the
    # shared range 1648/1645–1590/1587. The merge propagated the dates onto
    # 15.03 Apachnas (the brace's vertical centre) but left 15.02 Bêôn and
    # 15.04 Chajan with null dates because the OCR markdown lacks the brace
    # glyph. Overrides fill in the bracket dates on Bêôn and Chajan to match
    # what Beckerath prints. Salitis (15.01) sits OUTSIDE the bracket and
    # has no individual date — leave it null.
    "15.02": {
        "start_bce_high": -1648,
        "start_bce_low": -1645,
        "end_bce_high": -1590,
        "end_bce_low": -1587,
        "start_approximate": False,
        "end_approximate": False,
        "editorial_notes": "shared brace bracket with Apachnas (15.03) and Chajan (15.04) (scan-106-right)",
    },
    "15.04": {
        "start_bce_high": -1648,
        "start_bce_low": -1645,
        "end_bce_high": -1590,
        "end_bce_low": -1587,
        "start_approximate": False,
        "end_approximate": False,
        "editorial_notes": "shared brace bracket with Bêôn (15.02) and Apachnas (15.03) (scan-106-right)",
    },

    # ── 31.04 Chabbasch (scan-108-left): name + titulary kind ─────────────
    # Beckerath prints `Chababasch (Senen-sotep-en-ptah)` under the
    # `Ägypt. Gegenkönig:` sub-block at the foot of Dyn 31. The merge
    # produces:
    #   name = "Chababasch (Senen-sotep-en-ptah)"  (parens included)
    #   egyptian_titulary = "Senen-sotep-en-ptah"
    #   egyptian_titulary_kind = "nomen"
    # The unusual sub-block typography confused the agents' name-vs-titulary
    # split — every other Greek-Egyptian row has the parenthetical content
    # extracted into titulary alone. Strip the parens from name; the
    # `-sotep-en-ptah` suffix is prenomen morphology throughout Beckerath
    # (Schoschenq, Si-amun, etc.), so kind="prenomen".
    "31.04": {
        "name": "Chababasch",
        "egyptian_titulary_kind": "prenomen",
    },

    # ── 17.01 Dyn-17 marker row: heading-level `etwa` propagates ──────────
    # Beckerath's heading reads `17. Dynastie (in Theben, etwa 1645–1550)
    # 15 (?) Könige`. The `etwa` qualifier propagates to BOTH endpoints
    # (matching Dyn 1, Dyn 2, Dyn 4-6 etwa-headings); the merge majority
    # set start_approximate=True correctly but flagged end_approximate=False
    # because 1550 reads as a bare number to the agents. The 15 (?) hedge
    # in the regnal-count tail also implies end-uncertainty. Force True.
    "17.01": {
        "end_approximate": True,
    },

    # ── 19.08 Kgin. Te-wosret name split (scan-107-right) ─────────────────
    # Beckerath chains her on Si-ptah's row as `und Kgin. Te-wosret
    # (Thuoris)`. The Co-regent queen rule (prompt.md) splits this into a
    # separate row with `name="Kgin. <queen-name>"` and the parenthetical
    # `(Thuoris)` extracted into egyptian_titulary. The merge's titulary
    # extraction worked (`Thuoris`, kind=`nomen`) but name retained the
    # paren content (`Kgin. Te-wosret (Thuoris)`); strip the redundant
    # parenthetical from name to match the rule's name format.
    "19.08": {
        "name": "Kgin. Te-wosret",
    },

    # ── 21.02 Amen-em-nisu name/titulary split (scan-107-right) ───────────
    # Beckerath prints `Amen-em-nisu (Nephercheres)` in the Übersicht. The
    # standard Greek-alias-in-parens pattern (matching Schoschenq I.
    # `(Sesonchis)`, etc.) puts the alias in egyptian_titulary with
    # kind=`nomen`. The agents folded the parenthetical into name; split
    # to match the canonical pattern.
    "21.02": {
        "name": "Amen-em-nisu",
        "egyptian_titulary": "Nephercheres",
        "egyptian_titulary_kind": "nomen",
    },
}


# ── Systematic spelling fix: Schoscheng → Schoschenq ─────────────────────
# Beckerath consistently writes "Schoschenq" (with q-descender) in Anhang A
# and Supplement zu A (verified against scan-107 right-half + scan-108
# right-half). OCR systematically misread q→g on every Schoschenq row,
# including the prenomen Eigenname-half "Schoschenq mer-amun" form.
# Apply via string-replace on `name` and `prenomen` fields wherever
# "Schoscheng" appears.
SCHOSCHENG_TO_SCHOSCHENQ_FIELDS = (
    "name",
    "prenomen",
    "egyptian_titulary",
    "notes_from_beckerath",
)


# Human-readable rationale for the audit log (one entry per override key).
OVERRIDE_LOG: dict[str, str] = {
    "03.04": (
        "03.04 Hor Cha-bai: brace bracket on scan-105-right spans rows "
        "03.04 / 03.05 / 03.06 with shared range 2663/2613–2639/2589. "
        "Merge majority extracts the dates correctly; this override adds "
        "the cross-row editorial_notes tying the three bracketed rows "
        "together. [P2]"
    ),
    "03.05": (
        "03.05 Sôuphis, Mesochris: same brace bracket as 03.04. Merge "
        "produces the correct dates; this override adds the cross-row "
        "editorial_notes. [P2]"
    ),
    "03.06": (
        "03.06 Ahu (Huni, Aches): same brace bracket as 03.04. Merge "
        "produces the correct dates; this override adds the cross-row "
        "editorial_notes. [P2]"
    ),
    "15.02": (
        "15.02 Bêôn: scan-106-right brace bracket spans Bêôn / Apachnas / "
        "Chajan with shared range 1648/1645–1590/1587. The merge majority "
        "propagated the dates onto Apachnas (brace centre) but left Bêôn "
        "with null dates. Override fills in the bracket dates to match the "
        "printed PDF. [P1]"
    ),
    "15.04": (
        "15.04 Chajan (Iannas, Se'user-en-rê): same brace bracket as 15.02. "
        "Merge majority left Chajan with null dates; override fills in the "
        "bracket dates. (Replaces a pre-OCR-redo override that erroneously "
        "set Chajan's end to Apophis's dates -1549/-1546; the previous "
        "override was based on a misreading of the brace span.) [P1]"
    ),
    "31.04": (
        "31.04 Chababasch: scan-108-left prints `Chababasch "
        "(Senen-sotep-en-ptah)` under the `Ägypt. Gegenkönig:` sub-block. "
        "The agents folded the parenthetical into name; standard pattern "
        "elsewhere strips it. Also corrects kind to prenomen — the suffix "
        "`-sotep-en-X` is throne-name morphology throughout Beckerath. [P2]"
    ),
    "17.01": (
        "17.01 Dyn 17 marker row: heading-level `etwa` qualifier in `17. "
        "Dynastie (in Theben, etwa 1645–1550) 15 (?) Könige` propagates to "
        "BOTH endpoints (matching Dyn 1, Dyn 2, Dyn 4-6 etwa-headings). "
        "Merge set start_approximate=True but end_approximate=False because "
        "1550 reads as bare numeric to agents; force end_approximate=True "
        "to match Beckerath's heading semantics. [P2]"
    ),
    "19.08": (
        "19.08 Kgin. Te-wosret: Co-regent queen rule prescribes "
        "`name=\"Kgin. <queen-name>\"` (no parenthetical) with the "
        "parenthetical content moved to egyptian_titulary. Agents extract "
        "titulary correctly (`Thuoris`, kind=nomen) but kept the paren in "
        "name; this override strips the redundant `(Thuoris)` from name. "
        "[P2]"
    ),
    "21.02": (
        "21.02 Amen-em-nisu: standard Greek-alias-in-parens pattern "
        "(matching Schoschenq I. `(Sesonchis)`) puts the alias in "
        "egyptian_titulary with kind=nomen. Agents folded `(Nephercheres)` "
        "into name with titulary=null; this override splits name and "
        "titulary to match the canonical pattern. [P2]"
    ),
}


def _apply_schoschenq_spelling_fix(rows: list[dict]) -> list[str]:
    """Replace 'Schoscheng' → 'Schoschenq' on `name` and `prenomen` fields.

    Beckerath consistently writes Schoschenq (with q-descender). OCR misread
    q→g on every occurrence; the systematic correction is applied here as
    a final pass after OVERRIDES.

    Returns a list of audit-log entries naming each row that was rewritten.
    """
    fixed: list[str] = []
    for row in rows:
        for field in SCHOSCHENG_TO_SCHOSCHENQ_FIELDS:
            v = row.get(field)
            if isinstance(v, str) and "Schoscheng" in v:
                row[field] = v.replace("Schoscheng", "Schoschenq")
                fixed.append(
                    f"{row['beckerath_id']} {row.get('name', '?')}: "
                    f"{field}: {v!r} → {row[field]!r} "
                    f"(Schoscheng→Schoschenq systematic OCR fix). [P2]"
                )
    return fixed


def main() -> None:
    rows = [json.loads(line) for line in RECONCILED.read_text().splitlines() if line.strip()]

    # Validate every beckerath_id in OVERRIDES is present BEFORE mutating.
    found_ids = {r["beckerath_id"] for r in rows}
    for bid in OVERRIDES:
        if bid not in found_ids:
            raise KeyError(f"No row with beckerath_id {bid!r} in {RECONCILED}")

    applied: list[str] = []
    actually_mutated_count = 0

    for row in rows:
        bid = row["beckerath_id"]
        if bid not in OVERRIDES:
            continue
        fields = OVERRIDES[bid]
        for field, new_val in fields.items():
            old_val = row.get(field)
            if old_val == new_val:
                continue
            row[field] = new_val
            actually_mutated_count += 1
        # `applied` documents what corrections this script DEFINES — it is
        # the committed audit trail, not a per-run mutation log. Always
        # record every OVERRIDE that exists, even on idempotent re-runs
        # where no field actually changed; otherwise the audit log
        # silently shrinks across runs and loses provenance.
        applied.append(OVERRIDE_LOG[bid])

    # Systematic spelling fix runs after OVERRIDES so individual overrides
    # (e.g. on a Schoschenq row's prenomen) win first, then any remaining
    # "Schoscheng" → "Schoschenq" rewrites land. The schoschenq helper
    # already filters to "actually-mutated" entries (it only appends when
    # `Schoscheng` was found and replaced), so its return is naturally
    # empty on re-runs — that's the correct behaviour for a string-replace
    # pass, and is documented in the helper's docstring.
    applied.extend(_apply_schoschenq_spelling_fix(rows))

    # Ensure every row carries an editorial_notes key (default None).
    # merge.py only emits keys present in ≥1 agent payload, and the agents
    # do not produce this field — fix_rows.py is the introduction point.
    # Set explicitly so the JSONL has a uniform schema, sort_keys lines up,
    # and downstream consumers can rely on the field's presence.
    for row in rows:
        row.setdefault("editorial_notes", None)

    RECONCILED.write_text(
        "\n".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows
        )
        + "\n"
    )

    existing_diff = DIFF.read_text()
    marker = "## LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED"
    if marker in existing_diff:
        # Whitespace-tolerant: split on the marker itself and trim trailing
        # blank lines. Was previously sensitive to exactly two preceding
        # newlines, which would silently double-write the override block if
        # the file had been hand-edited or if a prior run produced different
        # spacing (Gemini PR #113).
        head, _, _ = existing_diff.partition(marker)
        existing_diff = head.rstrip()

    # NOTE: parenthesise "=" * N explicitly. Python's implicit string-literal
    # concatenation rule means an unparenthesised `"=" * N` next to other
    # string literals binds the multiplication to the WHOLE adjacent-literal
    # concatenation, producing N copies of the entire string. (Discovered
    # 2026-04-25 when fix_rows.py spuriously wrote 43 sections to merge-
    # disagreements.txt.)
    divider = "=" * (len(marker) - 3)
    audit_lines = "\n".join(f"- {line}" for line in applied)
    appended = (
        f"{existing_diff.rstrip()}\n\n"
        f"{marker}\n"
        f"{divider}\n"
        "Corrections applied by fix_rows.py AFTER the 3-subagent majority-vote\n"
        "merge. Source: egyptologist-reviewer Claude Code subagent pass against\n"
        "pre-rendered single-book-page JPEG scans (scan-NNN-{left,right}.jpg)\n"
        "of Beckerath 1997 Anhang A + Supplement zu A. No human scholar has\n"
        "signed off on this extract — per ADR-017 step 6, the extract is\n"
        "provisional.\n\n"
        "Severity tags: P1 = corrects a clearly-wrong value (merge-blocker);\n"
        "P2 = style / audit context only.\n\n"
        f"{audit_lines}\n"
    )
    DIFF.write_text(appended)

    print(
        f"Applied {len(applied)} override(s) across {len(OVERRIDES)} row(s); "
        f"{actually_mutated_count} field-value mutation(s) on this run."
    )
    print(f"Updated {RECONCILED.relative_to(RECONCILED.parents[4])}")
    print(f"Updated {DIFF.relative_to(DIFF.parents[4])}")


if __name__ == "__main__":
    main()
