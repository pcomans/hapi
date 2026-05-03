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
    # Cross-row references in `editorial_notes` use the canonical `name`
    # field plus `beckerath_id` in parentheses, so downstream consumers
    # can grep-resolve sister rows without name-form fuzziness. For rows
    # whose canonical name is itself compound (e.g. 03.05 `Sôuphis,
    # Mesochris`, 03.06 `Ahu (Huni, Aches)`), the FULL compound goes in
    # the cross-reference text — not the bare leading form.
    "03.04": {
        "editorial_notes": "shared bracket range with Sôuphis, Mesochris (03.05) and Ahu (Huni, Aches) (03.06) (scan-105-right)",
    },
    "03.05": {
        "editorial_notes": "shared bracket range with Hor Cha-bai (03.04) and Ahu (Huni, Aches) (03.06) (scan-105-right)",
    },
    "03.06": {
        "editorial_notes": "shared bracket range with Hor Cha-bai (03.04) and Sôuphis, Mesochris (03.05) (scan-105-right)",
    },

    # ── Dyn 15 Hyksos brace bracket (scan-106-right) ──────────────────────
    # Beckerath prints a brace spanning Bêôn / Apachnas / Chajan with the
    # shared range 1648/1645–1590/1587. The merge propagated the dates onto
    # 15.03 Apachnas (the brace's vertical centre) but left 15.02 Bêôn and
    # 15.04 Chajan with null dates because the OCR markdown lacks the brace
    # glyph. Overrides fill in the bracket dates on Bêôn and Chajan, plus a
    # cross-row editorial_notes entry on Apachnas tying all three rows
    # together (mirrors the Dyn 3 pattern). Salitis (15.01) sits OUTSIDE
    # the bracket and has no individual date — leave it null.
    "15.02": {
        "start_bce_high": -1648,
        "start_bce_low": -1645,
        "end_bce_high": -1590,
        "end_bce_low": -1587,
        "start_approximate": False,
        "end_approximate": False,
        "editorial_notes": "shared brace bracket with Apachnas (Pachnan) (15.03) and Chajan (15.04) (scan-106-right)",
    },
    "15.03": {
        "editorial_notes": "shared brace bracket with Bêôn (Bnón) (15.02) and Chajan (15.04) (scan-106-right)",
    },
    "15.04": {
        "start_bce_high": -1648,
        "start_bce_low": -1645,
        "end_bce_high": -1590,
        "end_bce_low": -1587,
        "start_approximate": False,
        "end_approximate": False,
        # The merge produced a partial titulary extraction —
        # name=`Chajan (Iannas, Se'user-en-rê)` with titulary=`Se'user-en-rê`
        # — splitting only the prenomen half and leaving the compound in
        # name. That's an inconsistent state (compound duplicated across
        # name + titulary). Realign to the kind="mixed" split pattern that
        # the merge produces directly for 26.04 Apries `(Wah-ib-rê,
        # Haa-ib-rê)` and that this PR's 06.04 override applies to
        # `(Methusuphis, Mer-en-rê)`: name=just-the-king, titulary=full
        # compound, kind=mixed. (Round-6 Gemini PR #139 finding.)
        "name": "Chajan",
        "egyptian_titulary": "Iannas, Se'user-en-rê",
        "egyptian_titulary_kind": "mixed",
        "editorial_notes": "shared brace bracket with Bêôn (Bnón) (15.02) and Apachnas (Pachnan) (15.03) (scan-106-right)",
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
        # Beckerath's Anhang A prints `Senen-sotep-en-ptah` (with `sotep`);
        # his own *Handbuch der ägyptischen Königsnamen* (1999), p. 270,
        # gives this king's prenomen as `Senen-setep-en-ptah` (with `setep`).
        # Faithful transcription is correct per the source-fidelity rule, but
        # flag the divergence here so downstream curators don't assume it's
        # an OCR error. Egyptologist-reviewer call.
        "editorial_notes": (
            "Anhang A prints `Senen-sotep-en-ptah`; HdÄK p.270 gives "
            "`Senen-setep-en-ptah` — typographic inconsistency within "
            "Beckerath's own corpus, transcribed verbatim per source-"
            "fidelity rule"
        ),
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

    # ── 19.08 Kgin.Te-wosret name split (scan-107-right) ──────────────────
    # Beckerath chains her on Si-ptah's row as `und Kgin.Te-wosret
    # (Thuoris)` (no space after Kgin., per the standardisation below).
    # The Co-regent queen rule (prompt.md) splits this into a separate row
    # with `name="Kgin.<queen-name>"` and the parenthetical `(Thuoris)`
    # extracted into egyptian_titulary. The merge's titulary extraction
    # worked (`Thuoris`, kind=`nomen`) but name retained the paren content
    # (`Kgin. Te-wosret (Thuoris)`); strip the redundant parenthetical AND
    # the post-`Kgin.` space.
    "19.08": {
        "name": "Kgin.Te-wosret",
    },

    # ── Greek-alias-in-parens split (Old Kingdom + Dyn 21) ───────────────
    # Beckerath consistently uses `<EgyptianName> (<GreekAlias>)` for kings
    # whose Greek/Manethonic alias is a single non-compound form (Sesonchis,
    # Onnos, Othoês, etc.). The canonical extraction pattern — matching
    # Schoschenq I. `(Sesonchis)` → name=`Schoschenq I.`, titulary=`Sesonchis`,
    # kind=`nomen` — splits these into a king-form `name` and an alias
    # `egyptian_titulary`. The agents/merge correctly split the Dyn 22
    # Schoschenq + Osorkon rows but left ~17 Old-Kingdom and Dyn 21 rows
    # with the parenthetical folded into name (titulary=null), because in
    # those rows the agent majority disagreed about how to handle the alias.
    # Apply the canonical split uniformly so downstream consumers see one
    # consistent name/titulary contract.
    #
    # Discriminator: a SINGLE non-compound Greek-alias goes in titulary
    # with kind=`nomen` (`Onnos`, `Soris`, etc.). COMPOUND comma-separated
    # parentheticals get one of two treatments:
    # - When the compound is two name-form variants of a single concept
    #   (e.g. `Sôuphis, Mesochris` on 03.05 — two Greek transcriptions of
    #   the same king; `Huni, Aches` on 03.06 — Egyptian + Greek nomen
    #   variants), keep the compound INLINE in name with titulary=null.
    # - When the compound is a Greek-alias + Egyptian-prenomen pair
    #   (e.g. `(Iannas, Se'user-en-rê)` on 15.04, `(Methusuphis, Mer-en-rê)`
    #   on 06.04, `(Wah-ib-rê, Haa-ib-rê)` on 26.04), split: name=just-
    #   the-king, titulary=full compound, kind=`mixed` (the test
    #   `test_compound_titulary_implies_mixed_kind` enforces this when
    #   titulary contains a comma).
    "02.06": {
        "name": "Nefer-ka-rê",
        "egyptian_titulary": "Nephercheres",
        "egyptian_titulary_kind": "nomen",
    },
    "02.07": {
        "name": "Nefer-ka-sokar",
        "egyptian_titulary": "Sesochris",
        "egyptian_titulary_kind": "nomen",
    },
    "04.01": {
        "name": "Senofru",
        "egyptian_titulary": "Soris",
        "egyptian_titulary_kind": "nomen",
    },
    "04.07": {
        "name": "Schepses-kaf",
        "egyptian_titulary": "Seberchéres",
        "egyptian_titulary_kind": "nomen",
    },
    "05.01": {
        "name": "User-kaf",
        "egyptian_titulary": "Userchéres",
        "egyptian_titulary_kind": "nomen",
    },
    "05.02": {
        "name": "Sahu-rê",
        "egyptian_titulary": "Sephres",
        "egyptian_titulary_kind": "nomen",
    },
    "05.03": {
        "name": "Nefer-ir-ka-rê Kakai",
        "egyptian_titulary": "Nephercheres",
        "egyptian_titulary_kind": "nomen",
    },
    "05.04": {
        "name": "Schepses-ka-rê",
        "egyptian_titulary": "Sisires",
        "egyptian_titulary_kind": "nomen",
    },
    "05.05": {
        "name": "Neferef-rê Isi",
        "egyptian_titulary": "Cheres",
        "egyptian_titulary_kind": "nomen",
    },
    "05.06": {
        "name": "Ni-user-rê Ini",
        "egyptian_titulary": "Rathores",
        "egyptian_titulary_kind": "nomen",
    },
    "05.07": {
        "name": "Men-kaw-hor",
        "egyptian_titulary": "Mencheres",
        "egyptian_titulary_kind": "nomen",
    },
    "05.08": {
        "name": "Djed-ka-re Isesi",
        "egyptian_titulary": "Tancheres",
        "egyptian_titulary_kind": "nomen",
    },
    "05.09": {
        "name": "Unas",
        "egyptian_titulary": "Onnos",
        "egyptian_titulary_kind": "nomen",
    },
    "06.01": {
        "name": "Teti",
        "egyptian_titulary": "Othoês",
        "egyptian_titulary_kind": "nomen",
    },
    "06.06": {
        "name": "Nemti-em-saf II.",
        "egyptian_titulary": "Menthesuphis",
        "egyptian_titulary_kind": "nomen",
    },
    "21.02": {
        "name": "Amen-em-nisu",
        "egyptian_titulary": "Nephercheres",
        "egyptian_titulary_kind": "nomen",
    },
    "21.04": {
        "name": "Amen-em-opet",
        "egyptian_titulary": "Amenophthis",
        "egyptian_titulary_kind": "nomen",
    },
    "21.05": {
        "name": "Osochor",
        "egyptian_titulary": "Osorkon",
        "egyptian_titulary_kind": "nomen",
    },

    # ── Dyn 29-30 Greek-alias + Egyptian-prenomen pair split (scan-108-left) ─
    # Beckerath book p192 prints these four Late Period rows with the SAME
    # typography as the verified-precedent 15.04 Chajan / 26.04 Apries / 06.04
    # Nemti-em-saf I.: `<Greek-name> (<Egyptian-nomen>, <Egyptian-prenomen>)`.
    # The 3-agent merge produces an inconsistent half-split state — `name`
    # carries the full compound while `egyptian_titulary` holds only the
    # prenomen with `egyptian_titulary_kind="prenomen"`. That breaks downstream
    # alias matching: searching for `Necht-nebef` against egyptian_titulary
    # would NOT find Nektanebês because titulary holds only `Cheper-ka-rê`.
    #
    # Apply the canonical split (name=bare Greek lemma; titulary=full inner
    # compound; kind="mixed") matching 15.04. Egyptologist printed-source
    # review on PR #146 verified the discriminator applies to all four rows
    # against PDF p108-left. Tracking issue #147; landed in this PR.
    #
    # 29.03 Psamuthis is preceded by `Gegenkönig` in print; that prefix stays
    # in `notes_from_beckerath` (already set by the 3-agent merge); only the
    # name-vs-titulary split is the editorial pass here.
    "29.03": {
        "name": "Psamuthis",
        "egyptian_titulary": "Pe-sche[re-n-]mut, User-rê",
        "egyptian_titulary_kind": "mixed",
    },
    "30.01": {
        "name": "Nektanebês",
        "egyptian_titulary": "Necht-nebef, Cheper-ka-rê",
        "egyptian_titulary_kind": "mixed",
    },
    "30.02": {
        "name": "Teôs",
        "egyptian_titulary": "Djed-hor, Iri-maat-en-rê",
        "egyptian_titulary_kind": "mixed",
    },
    "30.03": {
        "name": "Nektanebôs",
        "egyptian_titulary": "Necht-har-ehbojet, Senedjem-ib-rê",
        "egyptian_titulary_kind": "mixed",
    },

    # ── #150 — Late Period adjacent-row half-split sweep (scan-108-left) ──
    # Egyptologist printed-source review on PR #148 surfaced 4 rows on
    # Beckerath book p192 adjacent to the Dyn 29-30 cohort that exhibit
    # a half-split state. Verified against the printed Beckerath PDF
    # (PDF p108 = book p192) on PR closing #150.
    #
    # NB: linguistic semantics in this cohort are MIXED — the discriminator's
    # structural shape (single alias → `nomen` split; alias-pair → `mixed`
    # split) is language-agnostic and applies regardless of which side is
    # which:
    #   - Old Kingdom cohort (`Senofru (Soris)` etc.): name = Egyptian,
    #     parenthetical = Greek alias.
    #   - 28.01 / 26.05 / 29.02 (this PR): INVERSE-direction —
    #     name = Greek/Manethonic display form, parenthetical = Egyptian
    #     birth name (sometimes + Egyptian prenomen).
    #   - 26.02 Nekaw: SAME-direction as the Old Kingdom cohort —
    #     name = Egyptian birth name, parenthetical = Greek transcriptions
    #     `Nekôs/Nechaô` + Egyptian prenomen `Uhem-ib-rê`. Beckerath uses
    #     the Egyptian display form for Nekaw specifically; the Greek
    #     forms are alternative transcriptions in the parenthetical.
    # The discriminator doesn't care which side is which — it pivots only
    # on the parenthetical's internal structure (single alias vs alias-pair).
    #
    # - 28.01 Amyrtaios: print is `Amyrtaios (Amen-ir-di-su)` — single
    #   Egyptian nomen in parens (Amyrtaios is the Greek/Manethonic form).
    #   Apply the SINGLE-alias rule structurally (same shape as the Old
    #   Kingdom cohort, semantics inverted): name=Greek display lemma,
    #   titulary=Egyptian nomen, kind=`nomen`.
    # - 26.02 Nekaw: print is `Nekaw (Nekôs/Nechaô, Uhem-ib-rê)` — TWO
    #   Greek alternatives separated by `/` (Manetho's Νεχώς vs
    #   Herodotus's Νεκώς — alternative transcriptions of the same
    #   Greek form), then Egyptian prenomen `Uhem-ib-rê` after a comma.
    #   `Nekaw` itself is Egyptian. Apply 15.04-style mixed split:
    #   name=bare Egyptian display lemma, titulary=full inner compound
    #   including the Greek slash-compound + Egyptian prenomen, kind=`mixed`.
    # - 26.05 Amosis II: print is `Amosis II. (Amasis, Chnem-ib-rê)` —
    #   Greek/Manethonic-alias + Egyptian-prenomen pair. Apply 15.04-style
    #   mixed split: name=`Amosis II.`, titulary=`Amasis, Chnem-ib-rê`,
    #   kind=`mixed`.
    # - 29.02 Achoris: print is `Achoris (Hagor, Chnem-maat-rê)` —
    #   Egyptian-nomen `Hagor` (Beckerath's rendering of Egyptian Ḥgr,
    #   the king's actual birth name) + Egyptian-prenomen pair, with
    #   `Achoris` as the Greek/Manethonic display form. Apply 15.04-style
    #   mixed split: name=`Achoris`, titulary=`Hagor, Chnem-maat-rê`,
    #   kind=`mixed`.
    "28.01": {
        "name": "Amyrtaios",
        "egyptian_titulary": "Amen-ir-di-su",
        "egyptian_titulary_kind": "nomen",
    },
    "26.02": {
        "name": "Nekaw",
        "egyptian_titulary": "Nekôs/Nechaô, Uhem-ib-rê",
        "egyptian_titulary_kind": "mixed",
    },
    "26.05": {
        "name": "Amosis II.",
        "egyptian_titulary": "Amasis, Chnem-ib-rê",
        "egyptian_titulary_kind": "mixed",
    },
    "29.02": {
        "name": "Achoris",
        "egyptian_titulary": "Hagor, Chnem-maat-rê",
        "egyptian_titulary_kind": "mixed",
    },

    # ── 06.04 Nemti-em-saf I. titulary OCR drift (scan-106-left) ──────────
    # PDF book p188 prints `Nemti-em-saf I. (Methusuphis, Mer-en-rê)`.
    # The OCR pass transcribed `Mer-en-ptah` — almost certainly an LLM
    # autocomplete-from-training-data substitution (Merenptah/Mer-en-ptah
    # is a famous Dyn 19 king, more familiar than the Dyn 6 king's
    # Mer-en-rê prenomen). Detected by egyptologist diff against the
    # printed PDF post-merge, 2026-04-28.
    "06.04": {
        "egyptian_titulary": "Methusuphis, Mer-en-rê",
    },

    # ── Schoschenq IIIa. existence-hedge parens (scan-107-right) ─────────
    # Beckerath prints `(Schoschenq IIIa.)` in parentheses — typographic
    # hedge for "this king's existence/identity is uncertain". The agents
    # dropped the parens. Restore them in name to preserve the hedge.
    "22.07": {
        "name": "(Schoschenq IIIa.)",
        "editorial_notes": "Beckerath parenthesises the name as an existence-hedge marker (scan-107-right)",
    },

    # ── 22.06 Schoschenq III. notes verbatim hedge ───────────────────────
    # PDF prints `ca. 837–798 (785 ?)`. The merge paraphrased this as
    # `notes_from_beckerath = "alternative end 785"` which loses the `?`
    # hedge token and Beckerath's parenthesised form. Restore verbatim.
    "22.06": {
        "notes_from_beckerath": "(785 ?)",
    },

    # ── 18.04 Tuthmosis II. accession-prefix scoping ──────────────────────
    # PDF prints `Frühj.(?) 1492–1479` — `Frühj.(?)` qualifies the start
    # date only. Notes_from_beckerath stored just `"Frühj.(?) 1492"` which
    # is technically correct but ambiguous about scope. Match the
    # `Antritt 22.3.1504` pattern used on 18.03 Tuthmosis I.
    "18.04": {
        "notes_from_beckerath": "Antritt Frühj.(?) 1492",
    },

    # ── 25.02 Pije slash semantics (alias-coverage editorial note) ────────
    # PDF prints `Pije (User-maat-re/Senefer-rê)`. The slash separates two
    # prenomens used in succession or as alternates. The merge stored both
    # in egyptian_titulary as a single string; downstream alias-matching
    # needs to split on the slash. Flag in editorial_notes so consumers
    # know the slash is meaningful.
    "25.02": {
        "editorial_notes": "egyptian_titulary contains TWO prenomens separated by `/` (User-maat-re; Senefer-rê) — Beckerath records two alternative throne-name forms",
    },

    # ── 19.07 Si-ptah Anfangsname/Spätname editorial note ─────────────────
    # PDF prints two prenomens for Si-ptah: `anfangs Secha-en-rê mer-amun,
    # später Ach-en-rê sotep-en-rê`. The merge stored the whole
    # German-prefixed string in `prenomen`. That's faithful but breaks
    # alias-matching because consumers searching for `Secha-en-rê` or
    # `Ach-en-rê` won't pattern-match the prefixed string. Flag in
    # editorial_notes the early-vs-late distinction so downstream split
    # logic can handle it.
    "19.07": {
        "editorial_notes": "prenomen contains TWO throne names with German anfangs/später prefixes (Anfangsname Secha-en-rê mer-amun; Spätname Ach-en-rê sotep-en-rê) — split on `, später ` for alias-matching",
    },

    # ── Kgin. spacing standardisation ─────────────────────────────────────
    # Beckerath consistently prints `Kgin.` with NO space before the queen's
    # name (verified `Kgin.Hat-schepsut`, `Kgin.Nofret-ete`, `Kgin.Te-wosret`
    # on scan-106-right and scan-107-left). The agents extracted some rows
    # with a space and others without. Standardise to no-space across all
    # five queen rows so downstream string matching is uniform.
    # 18.05 already extracts as `Kgin.Hat-schepsut` (no space) — no override
    # needed there.
    "06.07": {
        "name": "Kgin.Nitokris",
    },
    "12.08": {
        "name": "Kgin.Nefru-sobek",
    },
    "18.11": {
        "name": "Kgin.Nofret-ete",
    },
    # 19.08 Te-wosret is already standardised above — `name="Kgin.Te-wosret"`
    # — so no separate entry here.
}


# ── Systematic spelling tripwire: Schoscheng → Schoschenq ────────────────
# Defense-in-depth tripwire retained as a no-op against the post-OCR-redo
# reconciled.jsonl. Beckerath consistently writes "Schoschenq" (with
# q-descender) in Anhang A and Supplement zu A (verified scan-107-right +
# scan-108-right). The previous double-page-spread OCR systematically
# misread q→g on every Schoschenq row; the split-single-book-page OCR no
# longer produces the misread, so this string-replace currently rewrites
# zero rows. Kept anyway because (a) it's idempotent and free, and (b) the
# matching test `test_schoschenq_spelling_systematic` asserts the invariant
# directly — if a future re-OCR regresses on the q-descender, this pass
# silently corrects it AND the test traces what was rewritten via the
# returned audit-log entries.
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
        "editorial_notes. Note: name is `Ahu (Huni, Aches)` with the "
        "compound parenthetical kept inline (vs. the Greek-alias-strip "
        "rule applied to single-alias rows below) — `Huni, Aches` is a "
        "comma-compound mixed-titulary form that belongs in name, not a "
        "single Greek alias to extract into titulary. [P2]"
    ),
    "15.02": (
        "15.02 Bêôn: scan-106-right brace bracket spans Bêôn / Apachnas / "
        "Chajan with shared range 1648/1645–1590/1587. The merge majority "
        "propagated the dates onto Apachnas (brace centre) but left Bêôn "
        "with null dates. Override fills in the bracket dates to match the "
        "printed PDF. [P1]"
    ),
    "15.03": (
        "15.03 Apachnas: same brace bracket as 15.02. Merge produces the "
        "correct dates; this override adds the cross-row editorial_notes "
        "tying the three bracketed rows together (mirrors Dyn 3 pattern "
        "on 03.04 / 03.05 / 03.06). [P2]"
    ),
    "15.04": (
        "15.04 Chajan: same brace bracket as 15.02 — fills in the bracket "
        "dates the merge missed. ALSO realigns the compound titulary "
        "extraction: the merge produced an inconsistent state with "
        "name=`Chajan (Iannas, Se'user-en-rê)` AND titulary=`Se'user-en-rê` "
        "(half-compound duplicated across name + titulary). Override sets "
        "name=`Chajan`, titulary=`Iannas, Se'user-en-rê`, kind=`mixed` to "
        "match the 26.04 Apries / 06.04 Nemti-em-saf I. mixed-split pattern. "
        "(Replaces a pre-OCR-redo override that erroneously set Chajan's "
        "end to Apophis's dates -1549/-1546; the previous override was "
        "based on a misreading of the brace span.) [P1]"
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
        "21.02 Amen-em-nisu: Greek-alias-in-parens split — See _GREEK_ALIAS_NOTE. [P1]"
    ),
    # Greek-alias-in-parens split rule applied uniformly across the
    # canonical Old-Kingdom + Dyn 21 rows where Beckerath uses
    # `<EgyptianName> (<single Greek alias>)`.  All entries below share
    # the same rationale; collapse to a single shared note rather than
    # repeating per-row.
    "02.06": "02.06 Nefer-ka-rê: Greek-alias-in-parens split (Nephercheres → titulary/nomen). See _GREEK_ALIAS_NOTE. [P1]",
    "02.07": "02.07 Nefer-ka-sokar: Greek-alias-in-parens split (Sesochris → titulary/nomen). See _GREEK_ALIAS_NOTE. [P1]",
    "04.01": "04.01 Senofru: Greek-alias-in-parens split (Soris → titulary/nomen). See _GREEK_ALIAS_NOTE. [P1]",
    "04.07": "04.07 Schepses-kaf: Greek-alias-in-parens split (Seberchéres → titulary/nomen). See _GREEK_ALIAS_NOTE. [P1]",
    "05.01": "05.01 User-kaf: Greek-alias-in-parens split (Userchéres → titulary/nomen). See _GREEK_ALIAS_NOTE. [P1]",
    "05.02": "05.02 Sahu-rê: Greek-alias-in-parens split (Sephres → titulary/nomen). See _GREEK_ALIAS_NOTE. [P1]",
    "05.03": "05.03 Nefer-ir-ka-rê Kakai: Greek-alias-in-parens split (Nephercheres → titulary/nomen). See _GREEK_ALIAS_NOTE. [P1]",
    "05.04": "05.04 Schepses-ka-rê: Greek-alias-in-parens split (Sisires → titulary/nomen). See _GREEK_ALIAS_NOTE. [P1]",
    "05.05": "05.05 Neferef-rê Isi: Greek-alias-in-parens split (Cheres → titulary/nomen). See _GREEK_ALIAS_NOTE. [P1]",
    "05.06": "05.06 Ni-user-rê Ini: Greek-alias-in-parens split (Rathores → titulary/nomen). See _GREEK_ALIAS_NOTE. [P1]",
    "05.07": "05.07 Men-kaw-hor: Greek-alias-in-parens split (Mencheres → titulary/nomen). See _GREEK_ALIAS_NOTE. [P1]",
    "05.08": "05.08 Djed-ka-re Isesi: Greek-alias-in-parens split (Tancheres → titulary/nomen). See _GREEK_ALIAS_NOTE. [P1]",
    "05.09": "05.09 Unas: Greek-alias-in-parens split (Onnos → titulary/nomen). See _GREEK_ALIAS_NOTE. [P1]",
    "06.01": "06.01 Teti: Greek-alias-in-parens split (Othoês → titulary/nomen). See _GREEK_ALIAS_NOTE. [P1]",
    "06.06": "06.06 Nemti-em-saf II.: Greek-alias-in-parens split (Menthesuphis → titulary/nomen). See _GREEK_ALIAS_NOTE. [P1]",
    "21.04": "21.04 Amen-em-opet: Greek-alias-in-parens split (Amenophthis → titulary/nomen). See _GREEK_ALIAS_NOTE. [P1]",
    "21.05": "21.05 Osochor: Greek-alias-in-parens split (Osorkon → titulary/nomen). See _GREEK_ALIAS_NOTE. [P1]",
    "29.03": (
        "29.03 Psamuthis: Greek-alias + Egyptian-prenomen pair split (issue "
        "#147). Beckerath p192 (scan-108-left) prints `Gegenkönig Psamuthis "
        "(Pe-sche[re-n-]mut, User-rê)` — Pe-sche[re-n-]mut is the Egyptian "
        "nomen, User-rê the prenomen. The merge produced the half-split "
        "state name=full compound, egyptian_titulary=`User-rê` only, "
        "kind=`prenomen`. Realign to the kind=`mixed` pattern matching the "
        "15.04 Chajan / 26.04 Apries / 06.04 Nemti-em-saf I. precedent: "
        "name=`Psamuthis`, titulary=`Pe-sche[re-n-]mut, User-rê`, kind="
        "`mixed`. Egyptologist printed-source review on PR #146 verified "
        "the discriminator applies. [P1]"
    ),
    "30.01": (
        "30.01 Nektanebês: Greek-alias + Egyptian-prenomen pair split (issue "
        "#147). Beckerath p192 (scan-108-left) prints `Nektanebês "
        "(Necht-nebef, Cheper-ka-rê)` — Necht-nebef is the Egyptian nomen, "
        "Cheper-ka-rê the prenomen. The merge produced the half-split state "
        "name=full compound, egyptian_titulary=`Cheper-ka-rê` only, "
        "kind=`prenomen`. Realign to kind=`mixed` per the 15.04 precedent: "
        "name=`Nektanebês`, titulary=`Necht-nebef, Cheper-ka-rê`, kind="
        "`mixed`. Egyptologist printed-source review on PR #146 verified "
        "the discriminator applies. [P1]"
    ),
    "30.02": (
        "30.02 Teôs: Greek-alias + Egyptian-prenomen pair split (issue "
        "#147). Beckerath p192 (scan-108-left) prints `Teôs (Djed-hor, "
        "Iri-maat-en-rê)` — Djed-hor is the Egyptian nomen, Iri-maat-en-rê "
        "the prenomen. The merge produced the half-split state name=full "
        "compound, egyptian_titulary=`Iri-maat-en-rê` only, kind=`prenomen`. "
        "Realign to kind=`mixed` per the 15.04 precedent: name=`Teôs`, "
        "titulary=`Djed-hor, Iri-maat-en-rê`, kind=`mixed`. Egyptologist "
        "printed-source review on PR #146 verified the discriminator "
        "applies. [P1]"
    ),
    "30.03": (
        "30.03 Nektanebôs: Greek-alias + Egyptian-prenomen pair split "
        "(issue #147). Beckerath p192 (scan-108-left) prints `Nektanebôs "
        "(Necht-har-ehbojet, Senedjem-ib-rê)` — Necht-har-ehbojet is the "
        "Egyptian nomen, Senedjem-ib-rê the prenomen. The merge produced "
        "the half-split state name=full compound, egyptian_titulary="
        "`Senedjem-ib-rê` only, kind=`prenomen`. Realign to kind=`mixed` "
        "per the 15.04 precedent: name=`Nektanebôs`, titulary="
        "`Necht-har-ehbojet, Senedjem-ib-rê`, kind=`mixed`. Egyptologist "
        "printed-source review on PR #146 verified the discriminator "
        "applies. [P1]"
    ),
    "28.01": (
        "28.01 Amyrtaios: Egyptian-nomen-in-parens single-alias split "
        "(issue #150). Beckerath p192 (scan-108-left) prints `Amyrtaios "
        "(Amen-ir-di-su)` — single Egyptian nomen in parens (Amyrtaios "
        "is the Greek/Manethonic display form). Inverse-direction of the "
        "Old Kingdom + Dyn 21 single-alias cohort (`Senofru (Soris)` "
        "etc.) where the parenthetical is Greek and the king-name is "
        "Egyptian; here it's flipped, but the structural shape (single "
        "alias → `nomen` split) still applies. Pre-#150 state had "
        "name=full compound + duplicated titulary=`Amen-ir-di-su` — "
        "inconsistent. Realign to the single-alias canonical: name="
        "`Amyrtaios`, titulary=`Amen-ir-di-su`, kind=`nomen`. Egyptologist "
        "printed-source review on PR #148 retro flagged this row; PR "
        "closing #150 verified directly against book p192. [P1]"
    ),
    "26.02": (
        "26.02 Nekaw: Greek/Greek + Egyptian-prenomen split (issue "
        "#150). Beckerath p192 (scan-108-left) prints `Nekaw "
        "(Nekôs/Nechaô, Uhem-ib-rê)` — TWO Greek alternatives separated "
        "by `/` (Manetho's Νεχώς vs Herodotus's Νεκώς, two transcriptions "
        "of the same Greek form) followed by the Egyptian prenomen "
        "`Uhem-ib-rê` after a comma. `Nekaw` itself is Egyptian (the "
        "king's birth name). Apply 15.04-style mixed split: name=`Nekaw`, "
        "titulary=`Nekôs/Nechaô, Uhem-ib-rê` (preserving the Greek slash-"
        "compound + Egyptian prenomen verbatim), kind=`mixed`. PR closing "
        "#150 verified against book p192. [P1]"
    ),
    "26.05": (
        "26.05 Amosis II: Greek-alias + Egyptian-prenomen pair split "
        "(issue #150). Beckerath p192 (scan-108-left) prints `Amosis "
        "II. (Amasis, Chnem-ib-rê)` — Amasis is the Greek/Manethonic "
        "alias, Chnem-ib-rê the Egyptian prenomen. Pre-#150 state had "
        "name=`Amosis II. (Amasis)` + titulary=`Chnem-ib-rê` only — "
        "half-split. Realign to kind=`mixed` per the 15.04 precedent: "
        "name=`Amosis II.`, titulary=`Amasis, Chnem-ib-rê`, kind=`mixed`. "
        "PR closing #150 verified against book p192. [P1]"
    ),
    "29.02": (
        "29.02 Achoris: Egyptian-nomen + Egyptian-prenomen pair split "
        "(issue #150). Beckerath p192 (scan-108-left) prints `Achoris "
        "(Hagor, Chnem-maat-rê)` — Hagor is Beckerath's rendering of the "
        "Egyptian nomen Ḥgr (the king's actual birth name; `Achoris` is "
        "the Greek/Manethonic display form), Chnem-maat-rê the Egyptian "
        "prenomen. Pre-#150 state had name=`Achoris (Hagor)` + titulary="
        "`Chnem-maat-rê` only — half-split. Realign to kind=`mixed` per "
        "the 15.04 precedent: name=`Achoris`, titulary=`Hagor, Chnem-"
        "maat-rê`, kind=`mixed`. PR closing #150 verified against book "
        "p192. [P1]"
    ),
    "06.04": (
        "06.04 Nemti-em-saf I.: scan-106-left prints `(Methusuphis, "
        "Mer-en-rê)` but the OCR pass emitted `Mer-en-ptah` — an LLM "
        "autocomplete substitution to the more familiar Dyn-19 king "
        "Merenptah. Override restores the verbatim printed `Mer-en-rê`. "
        "Detected by egyptologist diff against printed PDF, 2026-04-28. "
        "[P1]"
    ),

    "22.07": (
        "22.07 (Schoschenq IIIa.): scan-107-right prints the name in "
        "parentheses — Beckerath's typographic existence-hedge for an "
        "uncertain king. Agents dropped the parens; restore them in name "
        "to preserve the hedge. Editorial_notes flags the convention. "
        "[P2]"
    ),
    "22.06": (
        "22.06 Schoschenq III.: scan-107-right prints `ca. 837–798 (785 ?)` "
        "— the trailing `(785 ?)` is Beckerath's verbatim alternative-end "
        "hedge with a load-bearing `?`. Merge paraphrased to "
        "`alternative end 785` which lost the `?`; restore verbatim. [P2]"
    ),
    "18.04": (
        "18.04 Tuthmosis II.: scan-106-right prints `Frühj.(?) 1492–1479` — "
        "the `Frühj.(?)` accession-prefix qualifies the START date only. "
        "Notes_from_beckerath stored `Frühj.(?) 1492` which is technically "
        "correct but ambiguous; rewrite to `Antritt Frühj.(?) 1492` to "
        "match the `Antritt 22.3.1504` pattern used on 18.03 Tuthmosis I. "
        "[P2]"
    ),
    "25.02": (
        "25.02 Pije: scan-107-right prints `Pije (User-maat-re/Senefer-rê)` "
        "— two prenomens separated by `/` (alternates or successive). "
        "Editorial_notes flags the slash semantics so downstream alias-"
        "matching can split for lookup. [P2]"
    ),
    "19.07": (
        "19.07 Si-ptah: scan-107-right prints `anfangs Secha-en-rê "
        "mer-amun, später Ach-en-rê sotep-en-rê` — two prenomens with "
        "German anfangs/später prefixes (Anfangsname / Spätname). "
        "Editorial_notes flags the early-vs-late distinction so downstream "
        "alias-matching can split on `, später ` for lookup. [P2]"
    ),
    "06.07": "06.07 Kgin.Nitokris: scan-106-left prints `Kgin.Nitokris`. See _KGIN_NOTE. [P2]",
    "12.08": "12.08 Kgin.Nefru-sobek: scan-106-right prints `Kgin.Nefru-sobek`. See _KGIN_NOTE. [P2]",
    "18.11": "18.11 Kgin.Nofret-ete: scan-107-left prints `Kgin.Nofret-ete`. See _KGIN_NOTE. [P2]",
}

# Shared rationale strings — collapsed via constants so the OVERRIDE_LOG
# entries above stay scannable. (Audit log writer expands them inline.)
_KGIN_NOTE = (
    "Beckerath prints the queen-honorific abbreviation `Kgin.` with NO "
    "space before the queen's name (verified `Kgin.Hat-schepsut` on "
    "scan-106-right, `Kgin.Nofret-ete` and `Kgin.Te-wosret` on "
    "scan-107-left, `Kgin.Nitokris` on scan-106-left, `Kgin.Nefru-sobek` "
    "on scan-106-right). The agents extracted some rows with a space and "
    "others without; this override standardises to no-space across all "
    "five queen rows (06.07 / 12.08 / 18.05 / 18.11 / 19.08) so downstream "
    "string matching is uniform. (18.05 already extracts as "
    "`Kgin.Hat-schepsut`; 19.08 strip is folded into the existing "
    "Te-wosret name override above.)"
)
_GREEK_ALIAS_NOTE = (
    "Beckerath consistently uses `<EgyptianName> (<single Greek alias>)` "
    "for these kings. Canonical extraction (matching the Schoschenq I. "
    "(Sesonchis) precedent on 22.01) puts the alias in egyptian_titulary "
    "with kind=nomen. The agents/merge correctly split the Dyn 22 "
    "Schoschenq + Osorkon rows but left the Old Kingdom and Dyn 21 rows "
    "with the alias folded into name (titulary=null). These overrides "
    "apply the canonical split uniformly so downstream consumers see one "
    "consistent name/titulary contract. Discriminator: this rule applies "
    "to SINGLE non-compound aliases only; compound parentheticals with "
    "internal commas where the compound is two name-form variants of a "
    "single concept (e.g. 03.05 `Sôuphis, Mesochris`, 03.06 `Ahu (Huni, "
    "Aches)`) are kept inline in name. Compounds that are Greek-alias + "
    "Egyptian-prenomen pairs (e.g. 15.04 `Iannas, Se'user-en-rê`, 06.04 "
    "`Methusuphis, Mer-en-rê`, 26.04 `Wah-ib-rê, Haa-ib-rê`) split with "
    "kind=mixed instead — see the discriminator on the OVERRIDES dict."
)


# === Issue #179 schema-audit additions =======================================
#
# Strict-all-2-P1 per #176/#177/#178 policy. Replaces scalar
# `egyptian_titulary` + `egyptian_titulary_kind` with
# `egyptian_titularies: list[{name, kind, when}]`; promotes paren
# birth-name variants to `name_variants: list[str]`; adds typed flags
# for dynasty markers, anti-kings, and existence uncertainty.

import copy
import re

SCHEMA_FIELD_DEFAULTS_179: dict[str, object] = {
    "egyptian_titularies": [],   # list[{name, kind, when}] replaces scalar
    "name_variants": [],         # list[str] from `(...)` in `name`
    "is_dynasty_marker": False,  # row catalogues a dynasty header, not a king
    "is_anti_king": False,       # Beckerath's Gegenkönig + parens-wrapped
    "existence_uncertain": False,  # `(?)` / `„...“` quotes / `? <name>` markers
}

# Rows whose `name` is a dynasty header ("0. Dynastie", "13. Dynastie", etc.)
# rather than a person. Mechanically detected by the `\d+\. Dynastie` pattern.
_DYNASTY_MARKER_RE = re.compile(r"^\d+(?:\./\d+)?\.\s+Dynastie$")

# Rows where Beckerath flags the king as anti-king (Gegenkönig) via the
# `Gegenkönig` token in notes_from_beckerath. The negative lookahead `(?!e)`
# excludes the plural `Gegenkönige` ("had anti-kings besides him") which
# appears on 11.07 Ment-hotpe IV — he is the legitimate king, not an
# anti-king. Per egyptologist + code-reviewer P1.
_ANTI_KING_NOTE_RE = re.compile(r"\bGegenkönig\b(?!e)", re.IGNORECASE)

# Existence-uncertainty markers Beckerath uses on the `name` field:
#   - bare-paren wrapping ("(Schoschenq IIIa.)")
#   - trailing "(?)" ("„Psammûs“ (?)")
#   - leading "? " ("? „Hu-djefa“")
#   - German quotation marks "„...“" alone (treated as flagged-uncertain)
_BARE_PAREN_NAME_RE = re.compile(r"^\(.+\)$")
_LEADING_QUESTION_RE = re.compile(r"^\?\s+")
_TRAILING_PAREN_QUESTION_RE = re.compile(r"\(\?\)\s*$")
_GERMAN_QUOTES_RE = re.compile(r"„.+“")

# Paren extraction for `name_variants`: strict — only matches when the
# paren immediately follows a non-space char and contains a name-like
# token (no digit-only ordinals like "I.", "II."). 22.07 "(Schoschenq
# IIIa.)" is a bare-paren name handled by uncertainty detection above,
# not a variant.
_NAME_VARIANT_PAREN_RE = re.compile(r"\s*\(([^()]+?)\)")
# Inside the paren, split on `,` to capture multi-variant cases like
# 19.01 "Ramses (Ra-mes-su, griech. Ramessês) I." → variants
# ["Ra-mes-su", "griech. Ramessês"].
_VARIANT_SPLIT_RE = re.compile(r"\s*,\s*")
# 03.02 Djoser is the lone "mixed" row whose two halves are nomen +
# horus_name (not nomen + prenomen). The `mixed` enum collapses 3+
# distinct compound shapes per the audit; this is the only one that
# isn't nomen+prenomen, so it gets a per-row override rather than a
# heuristic. Egyptologist verifiable: PDF p. 51, "Hor Netri-chet" is
# the Horus name "ḥr nṯrj-ẖt".
_MIXED_TITULARY_OVERRIDES: dict[str, list[dict]] = {
    "03.02": [
        {"name": "Tosorthros", "kind": "nomen", "when": None},
        {"name": "Hor Netri-chet", "kind": "horus_name", "when": None},
    ],
}

# 19.07 Si-ptah's `prenomen` packs two temporal throne-names. Convert
# to two list entries with `when` populated.
_PRENOMEN_TEMPORAL_OVERRIDES: dict[str, list[dict]] = {
    "19.07": [
        {"name": "Secha-en-rê mer-amun", "kind": "prenomen", "when": "anfangs"},
        {"name": "Ach-en-rê sotep-en-rê", "kind": "prenomen", "when": "später"},
    ],
}


def _split_titulary(value: str | None, kind: str | None, bid: str = "?") -> list[dict]:
    """Convert legacy scalar `egyptian_titulary` + `kind` to the typed
    list shape. Handles slash-separated alternatives (within a kind) and
    `mixed`-kind comma-separated nomen+prenomen pairs. `bid` (the
    beckerath_id) is included in error messages for debugging.
    """
    if not value:
        return []
    if kind == "mixed":
        # `<nomen>, <prenomen>` (default for mixed). 03.02 is overridden
        # at the call site for the rare nomen+horus_name shape.
        parts = [p.strip() for p in value.split(",") if p.strip()]
        if len(parts) != 2:
            raise ValueError(
                f"mixed titulary {value!r} for {bid!r} did not split "
                f"cleanly into two parts (got {parts!r}); add explicit "
                f"override or adjust splitter"
            )
        nomen_str, prenomen_str = parts
        out: list[dict] = []
        for n in nomen_str.split("/"):
            out.append({"name": n.strip(), "kind": "nomen", "when": None})
        for p in prenomen_str.split("/"):
            out.append({"name": p.strip(), "kind": "prenomen", "when": None})
        return out
    # Single-kind value — slash splits to alternatives.
    return [
        {"name": piece.strip(), "kind": kind, "when": None}
        for piece in value.split("/")
        if piece.strip()
    ]


def _extract_name_variants(name: str) -> tuple[str, list[str]]:
    """Strip parens content from `name`, return (canonical_name, variants).
    Bare-paren names (`"(Schoschenq IIIa.)"`) are left untouched — they
    are uncertainty markers, handled separately. `(?)` uncertainty
    markers are stripped from the canonical name without becoming
    variants (handled by `_detect_existence_uncertain` instead).

    Handles multi-paren names (`"Name (var1) (var2)"`) by extracting
    every paren group's content into variants and stripping all of them
    from the canonical name. The current Beckerath corpus has no
    multi-paren names but the extractor is structured to handle them
    silently if a future re-extraction surfaces one. Per Gemini round-3.
    """
    if _BARE_PAREN_NAME_RE.match(name):
        return name, []
    # First strip uncertainty `(?)` so it doesn't pollute name_variants.
    canonical = _TRAILING_PAREN_QUESTION_RE.sub("", name).strip()
    matches = list(_NAME_VARIANT_PAREN_RE.finditer(canonical))
    if not matches:
        return canonical, []
    variants: list[str] = []
    for m in matches:
        inner = m.group(1)
        variants.extend(
            v.strip() for v in _VARIANT_SPLIT_RE.split(inner) if v.strip()
        )
    canonical = _NAME_VARIANT_PAREN_RE.sub("", canonical).strip()
    canonical = re.sub(r"\s+", " ", canonical)
    return canonical, variants


def _detect_existence_uncertain(name: str) -> bool:
    return bool(
        _BARE_PAREN_NAME_RE.match(name)
        or _LEADING_QUESTION_RE.match(name)
        or _TRAILING_PAREN_QUESTION_RE.search(name)
        or _GERMAN_QUOTES_RE.search(name)
    )


def _detect_anti_king(name: str, notes: str | None) -> bool:
    """Anti-king detection — only via explicit `Gegenkönig` (NOT plural
    `Gegenkönige`) in notes_from_beckerath. Parens-wrapped names like
    22.07 `(Schoschenq IIIa.)` are existence-uncertainty markers, not
    anti-king markers — the audit explicitly puts 22.07 in
    `existence_uncertain`, not in is_anti_king. Per egyptologist P1-3."""
    return bool(notes and _ANTI_KING_NOTE_RE.search(notes))


def _backfill_179_schema(rows: list[dict]) -> list[str]:
    log: list[str] = []
    for row in rows:
        added = []
        for f, default in SCHEMA_FIELD_DEFAULTS_179.items():
            if f not in row:
                row[f] = copy.deepcopy(default)
                added.append(f)
        if added:
            log.append(f"  {row['beckerath_id']}: backfilled {sorted(added)!r}")
    return log


def _apply_179_migrations(rows: list[dict]) -> list[str]:
    log: list[str] = []
    for row in rows:
        bid = row["beckerath_id"]
        name = row.get("name") or ""

        # is_dynasty_marker
        new_dyn = bool(_DYNASTY_MARKER_RE.match(name))
        if row["is_dynasty_marker"] != new_dyn:
            row["is_dynasty_marker"] = new_dyn
            log.append(f"  {bid}: is_dynasty_marker → {new_dyn}")

        # is_anti_king
        new_anti = _detect_anti_king(name, row.get("notes_from_beckerath"))
        if row["is_anti_king"] != new_anti:
            row["is_anti_king"] = new_anti
            log.append(f"  {bid}: is_anti_king → {new_anti}")

        # existence_uncertain
        new_unc = _detect_existence_uncertain(name)
        if row["existence_uncertain"] != new_unc:
            row["existence_uncertain"] = new_unc
            log.append(f"  {bid}: existence_uncertain → {new_unc}")

        # name_variants — promote `(...)` content. IDEMPOTENT GUARD:
        # only run the extractor when the name still has parens. Once
        # name_variants is populated and the parens are stripped from
        # name, subsequent runs see no parens and would otherwise wipe
        # the typed variants. Per code-reviewer P1-1.
        if "(" in name and ")" in name:
            new_name, variants = _extract_name_variants(name)
            if row["name_variants"] != variants:
                row["name_variants"] = variants
                log.append(f"  {bid}: name_variants → {variants!r}")
            if new_name != name:
                row["name"] = new_name
                log.append(f"  {bid}: name → {new_name!r}")

        # egyptian_titularies — list-promote scalar pair, with overrides
        if bid in _MIXED_TITULARY_OVERRIDES:
            new_tit = _MIXED_TITULARY_OVERRIDES[bid]
        elif bid in _PRENOMEN_TEMPORAL_OVERRIDES:
            # 19.07 — prenomen field carries the temporal pair; the
            # scalar egyptian_titulary stays empty.
            new_tit = _PRENOMEN_TEMPORAL_OVERRIDES[bid]
        else:
            new_tit = _split_titulary(
                row.get("egyptian_titulary"),
                row.get("egyptian_titulary_kind"),
                bid,
            )
        if row["egyptian_titularies"] != new_tit:
            row["egyptian_titularies"] = new_tit
            log.append(f"  {bid}: egyptian_titularies → {len(new_tit)} entries")

    return log


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
    # Validate OVERRIDE_LOG covers every OVERRIDES key before the mutation
    # loop runs the lookup. This catches the "added an OVERRIDES entry,
    # forgot the matching OVERRIDE_LOG rationale" mistake at startup with
    # a clear error, rather than letting OVERRIDE_LOG[bid] raise KeyError
    # mid-mutation on an arbitrary row. Per constitutional rule 2 (loud
    # failures), the validation raises rather than silently fallback to
    # a "rationale missing" placeholder.
    missing_log = sorted(set(OVERRIDES) - set(OVERRIDE_LOG))
    stale_log = sorted(set(OVERRIDE_LOG) - set(OVERRIDES))
    if missing_log or stale_log:
        raise KeyError(
            "OVERRIDE_LOG mismatch: "
            f"missing entries for {missing_log}; "
            f"stale entries (no matching OVERRIDES key) for {stale_log}. "
            "Every key in OVERRIDES must have a matching OVERRIDE_LOG "
            "entry, and vice versa, so the audit trail stays complete and "
            "rationale dictionary doesn't accumulate dead entries."
        )

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
        # silently shrinks across runs and loses provenance. Expand the
        # `See _GREEK_ALIAS_NOTE.` shorthand inline so the audit log is
        # self-contained for readers who only have merge-disagreements.txt.
        rationale = OVERRIDE_LOG[bid]
        rationale = rationale.replace("See _GREEK_ALIAS_NOTE.", _GREEK_ALIAS_NOTE)
        rationale = rationale.replace("See _KGIN_NOTE.", _KGIN_NOTE)
        applied.append(rationale)

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

    # Issue #179 schema-audit pass: typed flags + list-promote scalar pair.
    # The legacy `egyptian_titulary` + `_kind` scalars are KEPT alongside
    # the new `egyptian_titularies` list — they are the read-side source-
    # of-truth that the schema-audit pass derives from, so dropping them
    # would make subsequent fix_rows.py runs read None and silently
    # destroy the typed data. The README marks them as derivative
    # ingest artifacts; consumers must use `egyptian_titularies`.
    schema_log = _backfill_179_schema(rows)
    schema_log += _apply_179_migrations(rows)
    if schema_log:
        applied.extend(schema_log)

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
