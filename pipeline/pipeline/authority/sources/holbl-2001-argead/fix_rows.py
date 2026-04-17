"""Apply LLM-reviewer-identified corrections to reconciled.jsonl.

Run AFTER merge.py to layer scholarly corrections on top of the 3-subagent
majority vote. Every correction is recorded in merge-disagreements.txt
under the `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED` section so the audit
trail is preserved.

Hölbl's Argead extract is 3 rows; no deterministic-recomputation fields
(no concurrency, no interval arithmetic). The corrections here are all
spot corrections from the LLM reviewer pass, focused on `notes_from_holbl`
where the three-extractor majority vote picked a version containing
interpolation / editorial insertion not attested in Hölbl's rubric block:

- `argead.01` — the majority-vote `notes_from_holbl` appended "in Babylon"
  to "Died 10 June 323"; Hölbl's rubric writes only "10 June 323: Death of
  Alexander" (the Babylon setting is the scholarly consensus but is NOT
  stated in this table cell). Corrected to match the rubric-cell content.
- `argead.03` — the majority-vote `notes_from_holbl` contained the
  editorial insertion "(316, per Hölbl — reflecting a BCE sequencing issue
  in the appendix)". This parenthetical is extractor commentary, not a
  Hölbl fact; the appendix places Arsinoe II's birth at 316, not Alexander
  IV's birth. Alexander IV was born in 323 (posthumous to Alexander the
  Great's June 323 death). Corrected to a Hölbl-faithful note without the
  editorial.

Run:
    cd pipeline && uv run python pipeline/authority/sources/holbl-2001-argead/fix_rows.py
"""

from __future__ import annotations

import json
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
RECONCILED = SOURCE_DIR / "reconciled.jsonl"
DIFF = SOURCE_DIR / "merge-disagreements.txt"


# Spot corrections identified by the main-session self-review pass.
# (NOT the egyptologist-reviewer Claude Code subagent — that subagent was
# not invoked on this source; the harness exposed no Task/Agent tool, so
# review happened in the main session alongside extraction. See
# transcribe.md § "Model deviation" for the full disclosure.)
# Each entry: (holbl_id, field, new_value, rationale).
SPOT_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "argead.01",
        "notes_from_holbl",
        (
            "Invaded Egypt towards the end of 332 and acceded as pharaoh at "
            "the end of 332. Beginning of 331: foundation of Alexandria and "
            "expedition to the Ammoneion (Siwa), whose royal oracle "
            "legitimised him as pharaoh and confirmed his view of himself as "
            "son of Zeus-Ammon. Departed Egypt spring 331. Died 10 June 323."
        ),
        "The majority-vote text appended 'in Babylon' to 'Died 10 June 323'; "
        "Hölbl's appendix rubric-cell states only '10 June 323: Death of "
        "Alexander'. The Babylon setting is consensus scholarship but is not "
        "attested in this specific table cell. Corrected to rubric-faithful text.",
    ),
    (
        "argead.03",
        "notes_from_holbl",
        (
            "Posthumous son of Alexander the Great and Roxane; nominal joint "
            "king with Philip III Arrhidaios from birth, then sole nominal "
            "king after Philip III's murder in 317. Remained in Kassandros' "
            "custody under the Autumn 311 peace treaty between Ptolemy, "
            "Kassandros, Lysimachos and Antigonos. Murdered 310/309 by "
            "Kassandros. Ptolemy as Satrap of Egypt throughout this reign."
        ),
        "The majority-vote text contained the editorial parenthetical "
        "'(316, per Hölbl — reflecting a BCE sequencing issue in the "
        "appendix)' which is extractor commentary, not a Hölbl fact — "
        "Hölbl's '316' entry in the appendix refers to the birth of Arsinoe "
        "II, not Alexander IV. Alexander IV was born in 323 (posthumous to "
        "Alexander the Great's June 323 death). Corrected to a rubric-"
        "faithful note.",
    ),
]


def main() -> None:
    rows = [json.loads(line) for line in RECONCILED.read_text().splitlines() if line.strip()]

    applied_this_run = 0
    # Stable audit log derived from SPOT_CORRECTIONS, independent of whether
    # this run actually changed anything. Re-running fix_rows.py on an
    # already-corrected reconciled.jsonl keeps the audit section intact.
    stable_log: list[str] = []

    for hid, field, new_val, rationale in SPOT_CORRECTIONS:
        row = next((r for r in rows if r["holbl_id"] == hid), None)
        if row is None:
            raise KeyError(f"No row with holbl_id {hid!r}")
        old_val = row.get(field)
        stable_log.append(
            f"{hid}: {field} target → {json.dumps(new_val, ensure_ascii=False)} "
            f"({rationale})"
        )
        if old_val == new_val:
            continue
        applied_this_run += 1
        row[field] = new_val

    RECONCILED.write_text(
        "\n".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows
        )
        + "\n"
    )

    existing_diff = DIFF.read_text()
    # Guard against double-append if the script is re-run.
    marker = "LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED"
    if marker in existing_diff:
        head, _, _ = existing_diff.partition(f"\n\n{marker}")
        existing_diff = head
    appended = (
        f"{existing_diff.rstrip()}\n\n"
        f"{marker}\n"
        + "=" * len(marker) + "\n"
        "Corrections applied by fix_rows.py AFTER the 3-extractor majority-\n"
        "vote merge. Source of each correction: the main-session self-\n"
        "review pass against Hölbl's printed appendix rubric-block (NOT\n"
        "the egyptologist-reviewer Claude Code subagent — that subagent\n"
        "was not invoked on this source; the harness exposed no Task/Agent\n"
        "tool, so review happened in the main session alongside extraction).\n"
        "No human scholar has signed off on this extract yet — per ADR-017\n"
        "step 6, the extract is provisional until that happens.\n\n"
        "The log below is derived deterministically from SPOT_CORRECTIONS\n"
        "in fix_rows.py; it describes the TARGET value fix_rows.py enforces\n"
        "on each row and the rationale. It is re-emitted on every run so\n"
        "the audit trail survives a re-run that finds everything already\n"
        "correct (old_val == new_val).\n\n"
        + "\n".join(f"- {line}" for line in stable_log) + "\n"
    )
    DIFF.write_text(appended)

    print(f"Applied {applied_this_run} override(s) this run "
          f"({len(stable_log)} spot-correction(s) total in SPOT_CORRECTIONS).")
    print(f"Updated {RECONCILED.relative_to(RECONCILED.parents[4])}")
    print(f"Updated {DIFF.relative_to(DIFF.parents[4])}")


if __name__ == "__main__":
    main()
