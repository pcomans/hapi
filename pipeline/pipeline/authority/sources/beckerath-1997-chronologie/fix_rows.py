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
    # Cross-row editorial_notes always reference sister rows by their
    # canonical `name` field plus `beckerath_id` in parentheses (per
    # README field contract) so a downstream consumer can grep-resolve
    # without name-form fuzziness.
    "03.04": {
        "editorial_notes": "shared bracket range with Sôuphis (03.05) and Ahu (03.06) (scan-105 right-half)",
    },
    "03.05": {
        # Agents emit no dates because the bracket-propagation cue is a
        # visual `}` glyph the OCR doesn't preserve. Inherit from 03.04 per
        # the brace bracket Beckerath prints over the three rows.
        "start_bce_high": -2663,
        "start_bce_low": -2613,
        "end_bce_high": -2639,
        "end_bce_low": -2589,
        "editorial_notes": "shared bracket range with Hor Cha-bai (03.04) and Ahu (03.06) (scan-105 right-half)",
    },
    "03.06": {
        "start_bce_high": -2663,
        "start_bce_low": -2613,
        "end_bce_high": -2639,
        "end_bce_low": -2589,
        "editorial_notes": "shared bracket range with Hor Cha-bai (03.04) and Sôuphis (03.05) (scan-105 right-half)",
    },

    # ── Dyn 4 etwa propagation (rows 04.02–04.08): NOW REDUNDANT after
    #    PR #138 (postprocess.py emits <!-- dynasty-context: ... -->
    #    refresh after each page break inside a dynasty's span). The
    #    Beckerath re-extraction against the post-processed chunk now
    #    propagates `etwa` correctly across the book p187/p188 break;
    #    all 7 overrides removed.

    # ── Dyn 5 and 6: approximate flags — confirmation entry only.
    # Beckerath's Dyn 5 heading reads "5. Dynastie (etwa 2504/2454–2347/2297)";
    # Dyn 6 heading reads "6. Dynastie (etwa 2347/2297–2216/2166)". The
    # majority vote always set start_approximate=true / end_approximate=true
    # correctly (no page break disrupts attention within these dynasties).
    # No override needed.

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

    # ── 18.05 Kgin. Hat-schepsut — OCR-corrupt end date + editorial residue
    # Two corrections merged into one entry (Gemini PR #117 caught the
    # duplicate-key data-loss bug):
    # 1) (PR #113) Scan-107 shows "Kgin. Hat-schepsut (Maat-ka-rê)
    #    1479/73–1458". Same "341/837" garble maps to the bare endpoint
    #    "1458". The start 1479/73 is already correct in the merge
    #    (start_high=-1479, start_low=-1473). Override end dates;
    #    end_approximate = false.
    # 2) (#115 egyptologist sweep) The earlier "start 1479/73" string in
    #    notes_from_beckerath was editorial residue (Beckerath does not
    #    annotate her accession date in Anhang A). Stripped to null per
    #    rule 1 — notes must contain only verbatim Beckerath text.
    "18.05": {
        "end_bce_high": -1458,
        "end_bce_low": -1458,
        "end_approximate": False,
        "notes_from_beckerath": None,
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

    # ── 19.05 Amen-mes-su / 19.06 Sethós II Supplement-zu-A splice ────────
    # The Supplement zu A's `Mit ein glatt:` / `Mi ein glatt:` OCR garbles
    # break the `<King>:` label that anchors prenomen/nomen pairs to the
    # right king. After re-extraction (PR #138 post-processor), 3-agent vote
    # STILL splices Amen-mes-su's prenomen with Sethós II's, and Sethós II's
    # with Merenptah's. The splice is baked into the OCR markdown and a
    # post-processor on top of OCR can't fix it; needs explicit override
    # backed by scan-108-right verification.
    "19.05": {
        "prenomen": "Men-mi-rê sotep-en-rê",
        "notes_from_beckerath": "Antritt 3.5.1203",
    },
    "19.06": {
        "prenomen": "User-chepru-rê mer-amun",
        "notes_from_beckerath": "Antritt 12.1200/1199",
    },

    # ── 24.01 / 24.02 Tef-nachte / Bokchoris period: NOW REDUNDANT after
    #    PR #138 (postprocess.py emits `<!-- period: III. Zwischenzeit -->`
    #    directly after the Dyn-24 / Dyn-25 headings, derived from the
    #    canonical Beckerath dynasty→period mapping in DYNASTY_PERIOD).
    #    Overrides removed.

    # ── 27.03 Xerxes I. dates: NOW REDUNDANT after re-extraction; the
    #    new majority emits the correct end_bce_low=-464 directly. Override
    #    removed.

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
    # 31.04 Chabbasch — two corrections merged into one entry (Gemini PR
    # #117 caught the duplicate-key data-loss bug):
    # 1) (Gemini PR #113) OCR "Chadabasch" / "Sanm-sotep-en-ptah". Beckerath
    #    gives `Chabbasch (Senem-sotep-en-ptah)`. Both name and titulary
    #    corrected.
    # 2) (#115 egyptologist sweep) The titulary `Senem-sotep-en-ptah` was
    #    tagged kind="nomen" by the earlier correction, but the
    #    `-sotep-en-X` suffix is prenomen morphology throughout Beckerath.
    #    Corrected kind to "prenomen".
    "31.04": {
        "name": "Chabbasch",
        "egyptian_titulary": "Senem-sotep-en-ptah",
        "egyptian_titulary_kind": "prenomen",
    },

    # ── Editorial-prose stripping in notes_from_beckerath (rule 1):
    #    NOW REDUNDANT for 09.01 / 11.01 / 27.05. Re-extraction against
    #    the post-processed chunk now emits clean Beckerath-verbatim notes
    #    (`in Herakleopolis; 18 Könige`, `in Theben`, `Perser`) without
    #    the agent-editorial prose contamination. Overrides removed.

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

    # ── Egyptologist post-merge sweep findings (issue #115, 2026-04-25) ───
    #
    # Methodology blind-spot: the disagreement-log review is structurally
    # unable to catch cases where all three agents AGREED on a wrong or
    # incomplete value. The compound-titulary truncation pattern
    # (Beckerath prints `Name (nomen, prenomen)`, agents disagree which
    # half to extract, majority selects one) recurs across the corpus and
    # is not visible in merge-disagreements.txt.

    # ── 29.02 Achoris compound titulary: NOW REDUNDANT. Re-extraction
    #    against the post-processed chunk now emits the full
    #    `Hagor, Chnem-maat-rê` compound (kind=mixed) directly. Override
    #    removed.

    # ── 06.05 Pepy II compound titulary: NOW REDUNDANT. Re-extraction
    #    emits kind=mixed directly. Override removed.

    # ── 19.07 Si-ptah Anfangsname annotation. The Supplement zu A indented
    #    `anfang Sich-ka-rê sotep-en-rê` annotation is a beginning-of-reign
    #    throne-name variant Beckerath prints as a per-row note. Re-extraction
    #    captures `Antritt 10.1194/93` cleanly but does not yet pull in the
    #    indented Anfangsname annotation; appended here.
    "19.07": {
        "notes_from_beckerath": (
            "Antritt 10.1194/93; Anfangsname Sich-ka-rê sotep-en-rê; "
            "Spätname Ach-en-rê sotep-en-rê"
        ),
    },

    # ── 11.03 An-jotef III Horus name — full OCR garble (human-verified)
    # The OCR rendered the parenthetical as `(Hor Men-cheper nach) Nub`
    # — that's three substantive corruptions, not just a stray paren:
    #   `Men-cheper` should be `[-nacht]` (editorial-bracketed restoration)
    #   `nach`       should be `Neb`
    #   `Nub`        should be `tep-nofer`
    # Beckerath 1997 Chronologie prints
    #   `An-jotef III. (Hor[-nacht] Neb-tep-nofer)`
    # Human-verified against the printed PDF by the project lead 2026-04-28.
    "11.03": {
        "egyptian_titulary": "Hor[-nacht] Neb-tep-nofer",
    },

    # 21.02 Amen-em-nisu — wrong egyptian_titulary_kind. The value
    # "Nephercheres" is the Greek rendering of Neferkare — a prenomen
    # (throne name), not a nomen. Beckerath uses Nephercheres in the
    # Übersicht parenthetical as the Greek-form throne name.
    "21.02": {
        "egyptian_titulary_kind": "prenomen",
    },

    # ── 19.08 Kgin. Te-wosret: NOW REDUNDANT. Re-extraction (with the new
    #    co-regent-queen prompt rule) emits Te-wosret as a full row with
    #    name=`Kgin. Te-wosret`, egyptian_titulary=`Thuoris`, prenomen=
    #    `Sit-rê sotep-en-muat`, notes=`Mitregentin von Si-ptah`. The old
    #    override (which nulled notes and added an English editorial cross-
    #    reference) would now NULL OUT the correct Beckerath-derived
    #    `Mitregentin von Si-ptah` annotation. Override removed.
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
        "03.04/03.05/03.06; agents extract dates on 03.04 correctly but "
        "the bracket span itself is invisible in the OCR markdown. Cross-row "
        "audit note added in editorial_notes. [P2]"
    ),
    "03.05": (
        "03.05 Sôuphis: same brace bracket as 03.04. Agents emit no dates "
        "(the bracket-propagation cue is a visual `}` glyph the OCR doesn't "
        "preserve); inherit dates from 03.04 per Beckerath's printed bracket. "
        "Scan-context note added in editorial_notes. [P1+P2]"
    ),
    "03.06": (
        "03.06 Ahu: same brace bracket as 03.04. Inherit dates from 03.04 "
        "per the printed bracket; scan-context note added in editorial_notes. "
        "[P1+P2]"
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
        "18.05 Kgin. Hat-schepsut: TWO corrections merged. (1) scan-107 "
        "left shows '1479/73–1458'; '341/837' garble maps to bare 1458; "
        "end_high=-1458, end_low=-1458, end_approximate=false. (2) The "
        "earlier 'start 1479/73' note was editorial residue (Beckerath "
        "does not annotate her accession date in Anhang A); stripped to "
        "null per rule 1. [P1+P1, both Gemini PR #117-flagged dup-key]"
    ),
    "15.04": (
        "15.04 Chajan: scan-106 left-half shows '1590/87–1549/1546'; "
        "end_bce_high was OCR-corrupted to -1149 (flagged by Agent A); "
        "corrected to -1549. end_bce_low=-1546 already correct in merge. [P1]"
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
        "31.04 Chabbasch: TWO corrections merged. (1) OCR rendered name "
        "as 'Chadabasch' and titulary 'Sanm-sotep-en-ptah'; scan-108 "
        "right shows 'Chabbasch (Senem-sotep-en-ptah)' — name + titulary "
        "corrected. (2) The earlier correction tagged kind='nomen' but "
        "the `-sotep-en-X` suffix is prenomen morphology — kind corrected "
        "to 'prenomen'. [P1+P2, both Gemini PR #117-flagged dup-key]"
    ),
    "18.10": (
        "18.10 Akhenaten: OCR dropped the 'r' between 'u' and 'ê' in "
        "the prenomen → 'Nefer-chepruê wa-en-rê'; scan-107 left shows "
        "'Nefer-cheprurê wa-en-rê'. Discovered during 18.11–18.14 spot- "
        "verify (code-reviewer P2.3). Corrected. [P1 — typo]"
    ),
    "19.05": (
        "19.05 Amen-mes-su Thronname: Supplement zu A on scan-108 right "
        "reads 'Men-mi-rê sotep-en-rê, Ra-mes-su hotep-er-maat'. The OCR "
        "garbles the `Amen-mes-su:` label as `Mit ein glatt:`, which breaks "
        "the king-to-prenomen anchor. Even after the post-processor (PR #138) "
        "and the new co-regent / OCR-duplicate prompt rules, all 3 agents "
        "splice Amen-mes-su's prenomen with the next king's row. Override "
        "to scan-verified Thronname `Men-mi-rê sotep-en-rê`. Human-verified "
        "against the 1997 Chronologie printed PDF by the project lead "
        "2026-04-28; overrides this entry's prior 'LLM-applied' status to "
        "human-confirmed-against-source. [P1]"
    ),
    "19.06": (
        "19.06 Sethós II Thronname: same `Mit ein glatt:` / `Mi ein glatt:` "
        "OCR-label garble shape as 19.05. After re-extraction the merge "
        "still produces `Ba-en-rê-meri-netjeru` (Merenptah's prenomen) for "
        "Sethós II. Override to scan-verified `User-chepru-rê mer-amun`. "
        "Human-verified against the 1997 Chronologie printed PDF by the "
        "project lead 2026-04-28; the 1999 Handbuch's `User-chepru-rê "
        "sotep-en-rê` reading is a later edition divergence, not a 1997 "
        "transcription error. [P1]"
    ),
    "17.01": (
        "17.01 17. Dynastie: scan-106 right shows '17. Dynastie (in Theben, "
        "etwa 1645–1550) 13 (?) Könige'. OCR inserted phantom '1539/' from "
        "the Dyn-15 Hyksos line above ('1648/1645–1539/1536'); merge stored "
        "end_bce_high=-1539 (wrong, phantom) and end_bce_low=-1550. "
        "Corrected to end_bce_high=end_bce_low=-1550 (single endpoint). "
        "Surfaced by codex review (P2 inversion → P1 OCR-bleed). [P1]"
    ),
    "19.07": (
        "19.07 Si-ptah Anfangsname: re-extraction emits 'Antritt 10.1194/93' "
        "cleanly but does not capture the indented 'anfang Sich-ka-rê "
        "sotep-en-rê' annotation from Supplement zu A. Override appends the "
        "Anfangsname annotation to notes_from_beckerath. The earlier 'und "
        "Kgin. Te-wosret (Thuoris)' inclusion is dropped because Te-wosret "
        "now extracts as her own row 19.08 under the Co-regent queen rule. [P2]"
    ),
    "21.02": (
        "21.02 Amen-em-nisu: egyptian_titulary_kind was 'nomen' for the "
        "value 'Nephercheres'. Nephercheres is the Greek rendering of "
        "Neferkare — a prenomen (throne name), not a nomen. Corrected to "
        "kind='prenomen'. [P2]"
    ),
    "11.03": (
        "11.03 An-jotef III: chunk OCR fully garbled the Horus name. "
        "Beckerath 1997 Chronologie prints "
        "`An-jotef III. (Hor[-nacht] Neb-tep-nofer)`. The OCR rendered "
        "this as `(Hor Men-cheper nach) Nub` — three substantive "
        "corruptions, not just a stray paren. Human-verified against "
        "the printed PDF by the project lead 2026-04-28. Override sets "
        "the verbatim Beckerath form. [P1]"
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
