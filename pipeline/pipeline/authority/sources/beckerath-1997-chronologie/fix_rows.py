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

    # ── Akhenaten prenomen OCR typo (scan-107 left-half) ──────────────────
    # Beckerath: "Amenophis IV. Ach-en-aten (Nefer-cheprurê wa-en-rê)".
    # OCR dropped the `r` between `u` and `ê` → `Nefer-chepruê`.
    "18.10": {
        "egyptian_titulary": "Nefer-cheprurê wa-en-rê",
    },

    # ── Gemini Code Assist (PR #113, 2026-04-25) — scan-verified ─────────
    # 26.02 Necho II prenomen: OCR splice from Psamtik II's adjacent line.
    # Beckerath p.193 gives Wahem-ib-rê (Wḥm-ib-rꜥ).
    "26.02": {
        "egyptian_titulary": "Wahem-ib-rê",
    },
    # 26.04 Apries: extra `i` in second titulary. Should be Haa-ib-rê.
    "26.04": {
        "egyptian_titulary": "Wah-ib-rê, Haa-ib-rê",
    },
    # 31.02 Arses: OCR "Artges" (mis-OCR of "Arses"; Beckerath gives the
    # Greek form as Egyptian rendering since no Egyptian titulary attested).
    "31.02": {
        "egyptian_titulary": "Arses",
    },
    # 31.04 Chabbasch: OCR "Chadabasch" / "Sanm-sotep-en-ptah". Beckerath
    # gives `Chabbasch (Senem-sotep-en-ptah)`.
    "31.04": {
        "name": "Chabbasch",
        "egyptian_titulary": "Senem-sotep-en-ptah",
    },

    # ── Editorial-prose stripping in notes_from_beckerath (rule 1) ───────
    # The notes_from_beckerath field schema is "free-text annotations
    # Beckerath himself adds in the table cell". LLM extractors had inserted
    # editorial commentary like "end date not given" / "combined Dyn 9/10"
    # / "supplement notes:" — those are agent meta-prose, not Beckerath
    # text. Strip them; preserve Beckerath's actual annotations.
    "09.01": {
        "notes_from_beckerath": "in Herakleopolis; 18 Könige",
    },
    "11.01": {
        "notes_from_beckerath": "in Theben",
    },
    "19.07": {
        "notes_from_beckerath": (
            "Antritt 10.1194/93; und Kgin. Te-wosret (Thuoris); "
            "anfang Sich-ka-rê sotep-en-rê; später Ach-en-rê sotep-en-rê"
        ),
    },
    "27.05": {
        "notes_from_beckerath": "Perser",
    },

    # ── Dyn 17 OCR bleed (scan-106 right-half, codex review PR #113) ──────
    # Beckerath's Dyn 17 heading reads "17. Dynastie (in Theben, etwa
    # 1645–1550) 13 (?) Könige (siehe S. 124)" — a single 1550 endpoint,
    # no slash. OCR transcribed "1645-1539/1550", bleeding "1539" from the
    # adjacent Dyn 15 Hyksos line ("1648/1645-1539/1536"). The merge stored
    # end_bce_high=-1539 + end_bce_low=-1550 — both wrong (1539 is a
    # phantom; the correct value is a single -1550). Codex P2 surfaced the
    # high<=low inversion, which prompted re-verification against the scan.
    "17.01": {
        "end_bce_high": -1550,
        "end_bce_low": -1550,
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
    # ── Gemini Code Assist review pass (2026-04-25, PR #113) ──────────────
    "26.02": (
        "26.02 Necho II: OCR rendered titulary as 'Nefer-ib-rê' (which is "
        "Psamtik II's prenomen on the next line); scan-108 left shows "
        "Necho II's titulary is 'Wahem-ib-rê' (Wḥm-ib-rꜥ). Gemini Code "
        "Assist flagged the splice. Corrected. [P1]"
    ),
    "26.04": (
        "26.04 Apries: OCR rendered second titulary as 'Haai-ib-rê' (extra "
        "'i'); scan-108 left shows 'Haa-ib-rê' (Ḥꜥꜥ-ib-rꜥ). Gemini Code "
        "Assist flagged. Corrected. [P2]"
    ),
    "31.02": (
        "31.02 Arses: OCR rendered Egyptian titulary as 'Artges' (mis- "
        "OCR of 'Arses' / no separate Egyptian form); scan-108 right shows "
        "'Arses (Arses)'. Gemini flagged. Corrected to 'Arses'. [P1]"
    ),
    "31.04": (
        "31.04 Chabbasch: OCR rendered name as 'Chadabasch' and titulary "
        "'Sanm-sotep-en-ptah'; scan-108 right shows 'Chabbasch "
        "(Senem-sotep-en-ptah)'. Gemini flagged. Both corrected. [P1]"
    ),
    "18.10": (
        "18.10 Akhenaten: OCR dropped the 'r' between 'u' and 'ê' in "
        "the prenomen → 'Nefer-chepruê wa-en-rê'; scan-107 left shows "
        "'Nefer-cheprurê wa-en-rê'. Discovered during 18.11–18.14 spot- "
        "verify (code-reviewer P2.3). Corrected. [P1 — typo]"
    ),
    "09.01": (
        "09.01 9./10. Dynastie: notes_from_beckerath contained agent "
        "editorial 'combined Dyn 9/10'. Beckerath's actual cell text is "
        "'(in Herakleopolis, etwa 2170/2120-2025/2020) 18 Könige'. "
        "Stripped editorial; kept Beckerath text. [P1 — rule 1]"
    ),
    "11.01": (
        "11.01 An-jotef I. Dyn 11: notes_from_beckerath contained agent "
        "editorial 'end date not given'. Stripped; kept 'in Theben' "
        "(Beckerath's parenthetical placement annotation). [P1 — rule 1]"
    ),
    "19.07": (
        "19.07 Si-ptah: notes_from_beckerath had an agent prefix "
        "'supplement notes:'. Stripped the prefix; preserved the "
        "Beckerath/Supplement-zu-A content. [P1 — rule 1]"
    ),
    "27.05": (
        "27.05 Xerxes II.: notes_from_beckerath contained agent editorial "
        "'end date not given in source'. Stripped; kept 'Perser' "
        "(Beckerath's annotation). [P1 — rule 1]"
    ),
    "17.01": (
        "17.01 17. Dynastie: scan-106 right shows '17. Dynastie (in Theben, "
        "etwa 1645–1550) 13 (?) Könige'. OCR inserted phantom '1539/' from "
        "the Dyn-15 Hyksos line above ('1648/1645–1539/1536'); merge stored "
        "end_bce_high=-1539 (wrong, phantom) and end_bce_low=-1550. "
        "Corrected to end_bce_high=end_bce_low=-1550 (single endpoint). "
        "Surfaced by codex review (P2 inversion → P1 OCR-bleed). [P1]"
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
        "pre-rendered JPEG scans (scan-105.jpg–scan-109.jpg) of Beckerath 1997\n"
        "Anhang A + Supplement zu A. No human scholar has signed off on this\n"
        "extract — per ADR-017 step 6, the extract is provisional.\n\n"
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
