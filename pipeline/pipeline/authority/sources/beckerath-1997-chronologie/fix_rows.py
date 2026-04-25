"""Apply egyptologist-reviewer-identified corrections to reconciled.jsonl.

Run AFTER merge.py to layer scholarly corrections on top of the 3-subagent
majority vote. Every correction is recorded in merge-disagreements.txt under
the `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED` section so the audit trail
is preserved.

Source of corrections: egyptologist-reviewer Claude Code subagent pass against
the pre-rendered JPEG scans (scan-105.jpg through scan-109.jpg) of Beckerath
1997 Anhang A + Supplement zu A.

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
OVERRIDES: dict[str, dict] = {

    # ── Dyn 3: brace bracket (scan-105 right-half) ────────────────────────
    # Beckerath prints a bracket spanning Hor Cha-bai / Sôuphis,Mesochris /
    # Ahu with the shared range 2663/2613–2639/2589. The majority vote left
    # notes_from_beckerath null on 03.04 because agents B and C missed the
    # bracket (the dates themselves were correctly picked up by the 2v1 vote).
    # Adding the audit note; dates already correct so no date override needed.
    "03.04": {
        "notes_from_beckerath": "shared bracket range with Sôuphis,Mesochris and Ahu (scan-105)",
    },
    "03.05": {
        "notes_from_beckerath": "shared bracket range with Hor Cha-bai and Ahu (scan-105)",
    },
    "03.06": {
        "notes_from_beckerath": "shared bracket range with Hor Cha-bai and Sôuphis,Mesochris (scan-105)",
    },

    # ── Dyn 4: approximate flags (scan-105 right-half) ────────────────────
    # Beckerath's heading reads "4. Dynastie (etwa 2639/2589–2504/2454)".
    # The "etwa" propagates to all individual rows per the extraction rules.
    # Agent C voted false for both flags on all Dyn 4 rows; the 2v1 majority
    # correctly set Senofru (04.01) true/true, but 04.02 through 04.08 were
    # tipped false by Agent C on end_approximate, and false on start_approximate
    # for 04.03–04.08 (Agent B voted true but C and the merge logic diverged).
    # All Dyn 4 rows must have start_approximate=true, end_approximate=true.
    "04.02": {
        "start_approximate": True,
        "end_approximate": True,
    },
    "04.03": {
        "start_approximate": True,
        "end_approximate": True,
    },
    "04.04": {
        "start_approximate": True,
        "end_approximate": True,
    },
    "04.05": {
        "start_approximate": True,
        "end_approximate": True,
    },
    "04.06": {
        "start_approximate": True,
        "end_approximate": True,
    },
    "04.07": {
        "start_approximate": True,
        "end_approximate": True,
    },
    "04.08": {
        "start_approximate": True,
        "end_approximate": True,
    },

    # ── Dyn 5 and 6: approximate flags (scan-106 left-half) ───────────────
    # Beckerath's Dyn 5 heading reads "5. Dynastie (etwa 2504/2454–2347/2297)";
    # Dyn 6 heading reads "6. Dynastie (etwa 2347/2297–2216/2166)".
    # Agent C voted false on all, tipping no overrides in Dyn 5/6 but the
    # disagreement log confirms every 05.xx and 06.xx row had a 2v1 majority
    # (A+B true, C false). The majority vote picked true correctly for
    # 05.01–05.09 and 06.01–06.07. These are CONFIRMED CORRECT — no override.
    # (Included here as explicit confirmation audit entry only.)

    # ── 18.02 Amenophis I. — critical identity error (scan-107 left-half) ─
    # The merge produced name="An-jotef I." with egyptian_titulary="Hor
    # Neb-cheper-rê" for the second Dyn 18 king. This is wrong. Scan-107
    # left-half clearly shows: after Amosis (Neb-pehti-rê) 1550–1525 comes
    # "Amenophis I. (Djeser-ka-rê) 1525–1504". Agent A self-flagged this as
    # an OCR anomaly. The correct entry is Amenophis I., prenomen Djeser-ka-rê.
    # Note: "Hor Neb-cheper-rê" is the Horus name of Seqenenre/Antef VII
    # (Dyn 17), not Amenophis I. The merge produced a garbled splice.
    "18.02": {
        "name": "Amenophis I.",
        "egyptian_titulary": "Djeser-ka-rê",
        "egyptian_titulary_kind": "prenomen",
        "start_bce_high": -1525,
        "start_bce_low": -1525,
        "end_bce_high": -1504,
        "end_bce_low": -1504,
        "start_approximate": False,
        "end_approximate": False,
        "notes_from_beckerath": None,
    },

    # ── 18.04 Tuthmosis II. — OCR-corrupt end date (scan-107 left-half) ───
    # Scan-107 shows "Tuthmosis II. (A-cheper-en-rê) 14.8.1473–1458".
    # The "341/837" OCR garble corresponds to the bare endpoint "1458"
    # (no slash pair, single date). Override end dates and clear the
    # OCR-corrupt note; flag `end_approximate: false` (bare numeral).
    "18.04": {
        "end_bce_high": -1458,
        "end_bce_low": -1458,
        "end_approximate": False,
        "notes_from_beckerath": "Antritt 14.8.1473",
    },

    # ── 18.05 Kgin. Hat-schepsut — OCR-corrupt end date (scan-107 left) ───
    # Scan-107 shows "Kgin. Hat-schepsut (Maat-ka-rê) 1479/73–1458".
    # Same "341/837" garble maps to the bare endpoint "1458". The start
    # 1479/73 is already correct in the merge (start_high=-1479,
    # start_low=-1473). Override end dates; end_approximate = false.
    "18.05": {
        "end_bce_high": -1458,
        "end_bce_low": -1458,
        "end_approximate": False,
        "notes_from_beckerath": "start 1479/73",
    },

    # ── 15.04 Chajan — inverted end date (scan-106 left-half) ─────────────
    # Scan-106 shows "Chajan 1590/87–1549/1546". The merge correctly set
    # start_high=-1590, start_low=-1587, end_low=-1546. But end_high was
    # OCR-corrupted to -1149 (agent A flagged). Correct value is -1549.
    "15.04": {
        "end_bce_high": -1549,
        "end_bce_low": -1546,
        "end_approximate": False,
        "notes_from_beckerath": None,
    },

    # ── 19.05 Amen-mes-su — garbled prenomen and notes (scan-108 right) ───
    # Supplement zu A (scan-108 right) shows:
    #   "Amen-mes-su: Men-mi-rê sotep-en-rê, Ra-mes-su hotep-er-maat"
    # The Thronname (prenomen) is "Men-mi-rê sotep-en-rê"; the Eigenname
    # (nomen) is "Ra-mes-su hotep-er-maat". The merge erroneously set
    # prenomen="Amen-mes-su mer-amun" (which is the Eigenname form, not the
    # Thronname). Also strip the OCR-artifact "Mit ein glatt" note.
    "19.05": {
        "prenomen": "Men-mi-rê sotep-en-rê",
        "notes_from_beckerath": "Antritt 3.5.1203",
    },

    # ── 19.06 Sethós II. — wrong prenomen and garbled notes (scan-108 right)
    # Supplement zu A (scan-108 right) shows:
    #   "Sethós II.: User-chepru-rê mer-amun, Ra-mes-su Amen-hir-chepeschef"
    # The Thronname (prenomen) is "User-chepru-rê mer-amun"; the Eigenname
    # is "Ra-mes-su Amen-hir-chepeschef". The merge set prenomen=
    # "Ba-en-rê-meri-netjeru" which is Merenptah's prenomen — a clear splice
    # error. Also strip the OCR-artifact "Mi ein glatt" note.
    "19.06": {
        "prenomen": "User-chepru-rê mer-amun",
        "notes_from_beckerath": "Antritt 12.1200/1199",
    },

    # ── 24.01 Fürst Tef-nachte — wrong period (scan-108 left-half) ─────────
    # Scan-108 left shows the SPÄTZEIT heading appears above Dyn 26 (664–525),
    # not above Dyn 24. Dynasties 24 and 25 sit under the III. ZWISCHENZEIT
    # heading. The merge picked "Spätzeit" (2 of 3 agents: A+C) but the scan
    # contradicts this. Correct period is "III. Zwischenzeit".
    "24.01": {
        "period": "III. Zwischenzeit",
    },

    # ── 24.02 Bokchoris — wrong period (scan-108 left-half) ─────────────────
    # Same III. ZWISCHENZEIT heading applies to Bokchoris (Dyn 24 second king).
    "24.02": {
        "period": "III. Zwischenzeit",
    },

    # ── 27.03 Xerxes I. — inverted end dates (scan-108 left-half) ───────────
    # Scan-108 shows "Xerxes I. 486/85–465/64". The merge set
    # end_bce_high=-465 and end_bce_low=-484 — the low is wrong (should be
    # -464, and is inverted relative to high). Correct: end_high=-465,
    # end_low=-464.
    "27.03": {
        "end_bce_high": -465,
        "end_bce_low": -464,
    },
}


# Human-readable rationale for the audit log (one entry per override key).
OVERRIDE_LOG: dict[str, str] = {
    "03.04": (
        "03.04 Hor Cha-bai: brace bracket on scan-105 right-half spans rows "
        "03.04/03.05/03.06; majority vote left notes_from_beckerath null "
        "because agents B+C missed the bracket; dates already correct; audit "
        "note added. [P2]"
    ),
    "03.05": (
        "03.05 Sôuphis,Mesochris: same brace bracket as 03.04; notes added. [P2]"
    ),
    "03.06": (
        "03.06 Ahu (Huni,Aches): same brace bracket as 03.04; notes added. [P2]"
    ),
    "04.02": (
        "04.02 Cheops: Dyn-4 heading on scan-105 right-half reads "
        "'etwa 2639/2589–2504/2454'; 'etwa' propagates to all Dyn-4 rows; "
        "Agent C voted false on both flags, tipping merge; corrected to "
        "start_approximate=true, end_approximate=true. [P1]"
    ),
    "04.03": (
        "04.03 Djedefre: same Dyn-4 'etwa' propagation; corrected to "
        "start_approximate=true, end_approximate=true. [P1]"
    ),
    "04.04": (
        "04.04 Chephren: same Dyn-4 'etwa' propagation; corrected. [P1]"
    ),
    "04.05": (
        "04.05 Bikheris: same Dyn-4 'etwa' propagation; corrected. [P1]"
    ),
    "04.06": (
        "04.06 Mykerinos: same Dyn-4 'etwa' propagation; corrected. [P1]"
    ),
    "04.07": (
        "04.07 Schepseskaf: same Dyn-4 'etwa' propagation; corrected. [P1]"
    ),
    "04.08": (
        "04.08 Thamphthis: same Dyn-4 'etwa' propagation; corrected. [P1]"
    ),
    "18.02": (
        "18.02 IDENTITY ERROR — merge produced name='An-jotef I.' with "
        "egyptian_titulary='Hor Neb-cheper-rê'; scan-107 left-half clearly "
        "shows the Dyn-18 second king is 'Amenophis I. (Djeser-ka-rê) "
        "1525–1504'. Agent A self-flagged 'OCR anomaly: name An-jotef I. "
        "appears in Dyn 18 context'. 'Hor Neb-cheper-rê' is the Horus name "
        "of a Dyn-17 Antef, not Amenophis I. Full override: name, titulary, "
        "titulary_kind, dates. [P1 CRITICAL]"
    ),
    "18.04": (
        "18.04 Tuthmosis II.: scan-107 left-half shows '14.8.1473–1458'; "
        "the '341/837' OCR garble maps to bare endpoint 1458; "
        "end_bce_high=-1458, end_bce_low=-1458, end_approximate=false. "
        "Notes cleaned: 'Antritt 14.8.1473'. [P1]"
    ),
    "18.05": (
        "18.05 Kgin. Hat-schepsut: scan-107 left-half shows '1479/73–1458'; "
        "same '341/837' garble; end_bce_high=-1458, end_bce_low=-1458, "
        "end_approximate=false. [P1]"
    ),
    "15.04": (
        "15.04 Chajan: scan-106 left-half shows '1590/87–1549/1546'; "
        "end_bce_high was OCR-corrupted to -1149 (flagged by Agent A); "
        "corrected to -1549. end_bce_low=-1546 already correct in merge. [P1]"
    ),
    "19.05": (
        "19.05 Amen-mes-su: Supplement zu A on scan-108 right reads "
        "'Men-mi-rê sotep-en-rê, Ra-mes-su hotep-er-maat'; Thronname "
        "(prenomen) is 'Men-mi-rê sotep-en-rê', not 'Amen-mes-su mer-amun' "
        "(which is the Eigenname). Prenomen corrected. OCR-artifact 'Mit ein "
        "glatt' note stripped; Antritt date preserved. [P1]"
    ),
    "19.06": (
        "19.06 Sethós II.: Supplement zu A on scan-108 right reads "
        "'User-chepru-rê mer-amun, Ra-mes-su Amen-hir-chepeschef'; Thronname "
        "is 'User-chepru-rê mer-amun'. Merge had 'Ba-en-rê-meri-netjeru' "
        "which is Merenptah's prenomen — a splice error. Corrected. OCR- "
        "artifact 'Mi ein glatt' note stripped. [P1]"
    ),
    "24.01": (
        "24.01 Fürst Tef-nachte: scan-108 left-half shows SPÄTZEIT heading "
        "above Dyn 26 (664–525); Dyn 24 and 25 fall under III. ZWISCHENZEIT. "
        "Merge picked 'Spätzeit' (A+C 2v1) but scan contradicts it. "
        "Corrected to 'III. Zwischenzeit'. [P1]"
    ),
    "24.02": (
        "24.02 Bokchoris: same III. ZWISCHENZEIT heading applies; corrected "
        "from 'Spätzeit'. [P1]"
    ),
    "27.03": (
        "27.03 Xerxes I.: scan-108 left-half shows '486/85–465/64'; merge "
        "set end_bce_low=-484 (wrong — appears to be a carry-over of "
        "start_bce_low); correct end_bce_low=-464. [P1]"
    ),
}


def main() -> None:
    rows = [json.loads(line) for line in RECONCILED.read_text().splitlines() if line.strip()]

    applied: list[str] = []

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
        applied.append(OVERRIDE_LOG[bid])

    # Validate every beckerath_id in OVERRIDES was found.
    found_ids = {r["beckerath_id"] for r in rows}
    for bid in OVERRIDES:
        if bid not in found_ids:
            raise KeyError(f"No row with beckerath_id {bid!r} in {RECONCILED}")

    RECONCILED.write_text(
        "\n".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows
        )
        + "\n"
    )

    existing_diff = DIFF.read_text()
    marker = "## LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED"
    if marker in existing_diff:
        head, _, _ = existing_diff.partition(f"\n\n{marker}")
        existing_diff = head

    appended = (
        f"{existing_diff.rstrip()}\n\n"
        f"{marker}\n"
        "=" * (len(marker) - 3) + "\n"
        "Corrections applied by fix_rows.py AFTER the 3-subagent majority-vote\n"
        "merge. Source: egyptologist-reviewer Claude Code subagent pass against\n"
        "pre-rendered JPEG scans (scan-105.jpg–scan-109.jpg) of Beckerath 1997\n"
        "Anhang A + Supplement zu A. No human scholar has signed off on this\n"
        "extract — per ADR-017 step 6, the extract is provisional.\n\n"
        "Severity tags: P1 = corrects a clearly-wrong value (merge-blocker);\n"
        "P2 = style / audit context only.\n\n"
        + "\n".join(f"- {line}" for line in applied) + "\n"
    )
    DIFF.write_text(appended)

    print(f"Applied {len(applied)} override(s) across {len(OVERRIDES)} row(s).")
    print(f"Updated {RECONCILED.relative_to(RECONCILED.parents[4])}")
    print(f"Updated {DIFF.relative_to(DIFF.parents[4])}")


if __name__ == "__main__":
    main()
