"""Apply post-merge corrections to reconciled.jsonl.

Runs AFTER merge.py. Carries two classes of fix:

1. **Source-wide deterministic OCR substitutions** that should ideally happen
   pre-extraction at the `postprocess.py` layer but were not present when the
   chunk's raw text-layer was read. Currently: PM's Reisner-Roman-numeral
   tokens `G II` and `G III` render in the Griffith Institute text layer as
   Arabic `G 11` and `G 111` (the same OCR engine renders `G I` correctly,
   confirmed by the egyptologist-reviewer pass — chunk 1 PM III.1 review,
   2026-05-15). These appear in `notes_from_pm` cells where the source-faithful
   form is the Roman. Deterministic substring fix, longest-match first.

2. **Per-chunk reviewer-cited corrections** (`<CHUNK>_CORRECTIONS` dicts) for
   row-specific egyptologist findings beyond the source-wide substring rules.
   Currently empty for chunk 1 (clean review pass, 0 P1, 1 P2 already handled
   by the substring rule, 2 P3 nits).

Invocation:
    cd pipeline && uv run python pipeline/authority/sources/porter-moss-memphis/fix_rows.py

Idempotent: re-running on already-fixed reconciled.jsonl is a no-op (each
substitution's right-hand side does not contain the left-hand side).
"""

from __future__ import annotations

import json
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
RECONCILED = SOURCE_DIR / "reconciled.jsonl"
DIFF = SOURCE_DIR / "merge-disagreements.txt"

# Marker that delimits the auto-appended audit-trail section in
# `merge-disagreements.txt`. Re-running fix_rows.py strips any existing
# section that begins at this marker before re-appending, so the file
# remains byte-identical across consecutive runs (constitutional rule 2
# + playbook idempotence guard).
_AUDIT_MARKER = "\nLLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED\n"


# Source-wide OCR-drift fixes applied to `notes_from_pm`.
# Ordered LONGEST-MATCH FIRST so that `G 111` is rewritten before any
# overlapping `G 11` rule could fire on the same string.
_NOTES_OCR_FIXES: list[tuple[str, str]] = [
    ("Reisner, G 111-", "Reisner, G III-"),  # subsidiary-pyramid form first
    ("Reisner, G 111;", "Reisner, G III;"),
    ("Reisner, G 111.", "Reisner, G III."),
    ("Reisner, G 111", "Reisner, G III"),
    ("Reisner, G 11-", "Reisner, G II-"),
    ("Reisner, G 11;", "Reisner, G II;"),
    ("Reisner, G 11.", "Reisner, G II."),
    ("Reisner, G 11", "Reisner, G II"),
]


# Per-chunk reviewer-cited corrections.
# Format: `{(tomb_id, field): {"value": ..., "rationale": "..."}}`.
# `CHUNK<N>_CORRECTIONS` is per-chunk; a dict is empty when the
# egyptologist pass clears that chunk with no row-specific P1 findings
# (chunk 1 case).
CHUNK1_CORRECTIONS: dict[tuple[str, str], dict[str, object]] = {}

# Chunk-2 corrections from the egyptologist-reviewer pass on the printed PM
# III.1 source (2026-05-15). The pypdf text-layer renders `D` and `O`
# ambiguously in PM's all-caps headwords; pypdf chose `O` for the `D` in
# `IDU`. Two corrections needed:
#   1. `occupant_name`: "Iou" → "Idu"
#   2. `notes_from_pm`: rewrite the verbatim "IOU" token to "IDU" so the
#      stored headword form matches what PM prints (the OCR misread is
#      not PM-faithful).
CHUNK2_CORRECTIONS: dict[tuple[str, str], dict[str, object]] = {
    ("G7102", "occupant_name"): {
        "value": "Idu",
        "rationale": (
            "Egyptologist-reviewer pass against PM III.1 2nd ed. 1974 "
            "printed p.185: PM's all-caps headword unambiguously reads "
            "`G 7102. IDU`. pypdf text-layer misread D→O producing `IOU`, "
            "which all three extraction agents inherited and majority-voted. "
            "Corroborated by the already-correctly-OCR'd footnote on "
            "printed p.184 (`Textual evidence also permits Meryrēᶜnūfer "
            "Kar to be son of Idu (tomb G 7102)`) and by Simpson, *Mastabas "
            "of the Western Cemetery I* (1980)."
        ),
    },
}

# Chunk-3 corrections from the egyptologist-reviewer pass (PR #220 / PM
# III.1 printed pp.288-292). The Saite joint-burial rows (LG 83, LG 97)
# need typed roles for their co-occupants — PM explicitly types Queen
# Nekhtubasterau (LG 83) and pairs Harsiesi + Harwoz as both wnrw-priests
# (LG 97). Currently `co_occupants` is `list[str]` (names only) and the
# co-occupant's role is lost. Solution: a parallel `co_occupant_roles`
# field. Order-coupled with `co_occupants`. The schema addition matters
# for downstream Phase-A queen-of-Amasis queries, which must surface
# LG 83 as a Queen tomb even though its primary occupant is a Commander.
CHUNK3_CORRECTIONS: dict[tuple[str, str], dict[str, object]] = {
    ("LG83", "co_occupant_roles"): {
        "value": ["Queen"],
        "rationale": (
            "Egyptologist-reviewer pass against PM III.1 2nd ed. 1974 "
            "printed p.289: PM's joint-burial headword reads `LG 83. "
            "aAHMOSI Commander of the army, and his mother Queen "
            "NEKHTUBASTERAU (wife of Amasis). Dyn. XXVI.`. The secondary "
            "occupant carries an explicit `Queen <NAME>` token AND a "
            "`wife of <king>` parenthetical — both attributes that PM "
            "types as primary-source facts about her. Without a parallel "
            "`co_occupant_roles` list, this typed role is lost into "
            "prose, and Phase-A queries for 'queens of Amasis' will not "
            "surface LG 83. Adds `co_occupant_roles: [\"Queen\"]` so "
            "downstream enrichment can route Nekhtubasterau as a Queen "
            "without losing the joint-burial-with-son-ʿAhmosi context."
        ),
    },
    ("LG97", "co_occupant_roles"): {
        "value": ["Official"],
        "rationale": (
            "Egyptologist-reviewer pass against PM III.1 2nd ed. 1974 "
            "printed p.291: PM's joint-burial headword reads `LG 97. "
            "HARSIESI and HARWOZ both wnrw-priests. Dyn. XXVI.`. The "
            "`both <shared title>` phrasing types BOTH occupants with the "
            "same priestly role; the secondary (Harwoz) inherits the same "
            "`Official` role as the primary (Harsiesi). Parallel "
            "`co_occupant_roles` array preserves the symmetric typing."
        ),
    },
    ("LG97", "notes_from_pm"): {
        "value": "LG 97. HARSIESI and HARWOZ both wnrw-priests. Dyn. XXVI. Mother, Tentamūn.",
        "rationale": (
            "Egyptologist-reviewer pass F5 + Gemini PR #220 round-1 inline "
            "comment id=3253276720 (both reviewers converged on the same "
            "finding). PM III.1 2nd ed. 1974 printed p.291 prints the "
            "parental relation as `Mother, Tentamūn.` (with a trailing "
            "period and a macron over the `u`). Two issues with the "
            "majority-voted notes value: (1) pypdf rendered the macron-u "
            "as the digraph `ii`, producing `Tentamiin` (analogous OCR "
            "drift to chunks 1-2 raised-ayin `a` / `c` patterns); (2) "
            "the trailing period was dropped because pypdf concatenated "
            "the next sub-heading `Names and titles from ushabtis.` "
            "onto the same line as `Mother, Tentamūn`, and the agents "
            "(correctly) stopped extraction at the sub-heading boundary "
            "but lost the headword's terminal period. Restoration: "
            "`Tentamiin` → `Tentamūn` + trailing period."
        ),
    },
}

# Chunk-4 corrections from the egyptologist-reviewer pass (PR #222 / PM
# III.2 Saqqâra Dyn V/VI pyramids).
CHUNK4_CORRECTIONS: dict[tuple[str, str], dict[str, object]] = {
    ("SAQ-MerenreI", "occupant_name"): {
        "value": "Merenreʿ I",
        "rationale": (
            "Egyptologist-reviewer pass F1 against PM III.2 2nd ed. 1978/1981 "
            "printed p.425 (physical p.65): PM prints `MERENRĒʿ I` (macron-ē + "
            "raised-ayin). pypdf rendered the macron-ē-plus-raised-ayin glyph "
            "cluster as the 2-character sequence `£c`, where `£` represents "
            "the underlying `Ē` (or `É` with combining marks) and `c` "
            "represents the raised-ayin. The chunk-4 prompt's rule "
            "`£c → ʿ` correctly converts the raised-ayin glyph but DROPS the "
            "underlying vowel — producing the non-standard form `Merenrʿ I`. "
            "The conventional Egyptological transcription is `Merenreʿ I` "
            "(mer-en-Reʿ, \"Beloved of Re\") with the `e` vowel of the `Re` "
            "element preserved. Parallel to chunk-1's `Menkaureʿ` (PM "
            "`MENKAUREa` → drop the raised-`a` glyph, keep the `e` vowel that "
            "precedes it). Restoration: `Merenrʿ I` → `Merenreʿ I`. Egyptologist "
            "F1 finding."
        ),
    },
    ("SAQ-IputII", "source_citation"): {
        "value": {"page": 432, "edition": "PM III.2 2nd ed. 1978/1981", "section": "I"},
        "rationale": (
            "Gemini PR #222 round-1 caught a 2/1 majority that happened to be "
            "wrong: agents A and C reported `page: 431`, agent B reported "
            "`page: 432`. The IPUT II headword `PYRAMID-ENCLOSURE OF IPUT [II]¹` "
            "appears on physical p.72 of the chunk file. The PM III.2 printed-vs-"
            "physical offset is `printed = physical + 360`, so physical p.72 = "
            "printed p.432. Agent B's reported page (432) is correct; A and C "
            "are off by one (likely confused by the prior right-page running "
            "header `Pyramid-complex of Pepy II 431` on physical p.71). Override "
            "the majority with the cited correct page. The `SAQ-IputII|"
            "notes_from_pm` tie-break-overrides.json rationale already states "
            "`printed p.432 (physical p.72)`; this fix aligns source_citation "
            "with the documented page reference."
        ),
    },
}

# Chunk-5 corrections (PM III.2 § I.A–E Saqqâra front-half pyramid
# complexes: Teti+Iput-I+Khuit, Userkaf, Neterikhet/Zoser, Sekhemkhet,
# Great Enclosure). Findings from the printed-source egyptologist-reviewer
# pass against PM III.2 pp.393–417.
CHUNK5_CORRECTIONS: dict[tuple[str, str], dict[str, object]] = {
    ("SAQ-IputI", "occupant_name"): {
        "value": "Iput",
        "rationale": (
            "Egyptologist-reviewer printed-source pass against PM III.2 "
            "p.396: PM prints `PYRAMID-ENCLOSURE OF IPUT¹` (bare IPUT with "
            "footnote anchor `¹` keyed to `1 King's wife (of Teti), "
            "King's mother (of Pepy I).` at the bottom of the same page). "
            "The agents' converged extraction `Iput I` interpolates the "
            "regnal numeral `I` from Egyptological convention — but PM "
            "itself does NOT print `[I]` on this heading. Contrast with "
            "chunk-4's SAQ-IputII row where PM explicitly prints `IPUT "
            "[II]¹` with the bracket-regnal. The chunk-4 [II] bracket is "
            "PM's editorial regnal disambiguation; chunk-5's bare IPUT "
            "(without bracket) is PM's faithful headword form. Per rule 1 "
            "(work like a scholar — every fact traces to a documented "
            "source), `occupant_name` must match PM's printed form. The "
            "museum-side disambiguating form `Iput I` is preserved in "
            "`occupant_alt_names` for Phase-A matching coverage. "
            "Restoration: `Iput I` → `Iput`."
        ),
    },
    ("SAQ-IputI", "occupant_alt_names"): {
        "value": ["Iput I"],
        "rationale": (
            "Companion fix to the SAQ-IputI `occupant_name` correction. "
            "`Iput I` is the museum-conventional disambiguating form "
            "(distinguishing Teti's queen-consort from Pepy II's queen "
            "Iput II covered in chunk 4). Phase-A name-authority matching "
            "needs this alias because museum records will say `Iput I` "
            "even though PM's headword is bare `IPUT`. Egyptologist "
            "F1 finding."
        ),
    },
    ("SAQ-IputI", "notes_from_pm"): {
        "value": (
            "PYRAMID-ENCLOSURE OF IPUT. Dyn. VI. PYRAMID. "
            "¹ [King's daughter of his] body, King's wife (of Teti), "
            "King's mother (of Pepy I)."
        ),
        "rationale": (
            "Egyptologist-reviewer second-pass printed-source verification "
            "against PM III.2 p.396: the full footnote text is "
            "`¹ [King's daughter of his] body, King's wife (of Teti), "
            "King's mother (of Pepy I).` — three titles, with the first "
            "(`King's daughter of his body`, restoring the lost original "
            "title `sꜣt-nsw-n(t)-ẖt.f`) in editorial brackets per PM's "
            "convention for restored text. First-pass review F3 fix "
            "captured only the last two titles (`King's wife (of Teti), "
            "King's mother (of Pepy I).`) — a rule-1 fidelity loss that "
            "would lead Phase-A consumers to wrongly conclude PM prints "
            "only two titles. Second-pass fix restores PM's bracketed "
            "first clause. Verbatim form (no `(Footnote: ...)` editorial "
            "wrapper) per the README's `notes_from_pm` convention; the "
            "`¹` superscript marker is PM's own footnote-anchor character "
            "and stays as PM's contextual signal that this clause is "
            "footnote prose rather than the headline-block continuation."
        ),
    },
    ("SAQ-Khuit", "notes_from_pm"): {
        "value": (
            "PYRAMID-ENCLOSURE OF KHUIT. Dyn. VI. "
            "¹ King's wife (of Teti)."
        ),
        "rationale": (
            "Egyptologist-reviewer printed-source pass against PM III.2 "
            "p.397: PM prints `PYRAMID-ENCLOSURE OF KHUIT¹` with footnote "
            "anchor `¹` keyed to `¹ King's wife (of Teti).` at the bottom "
            "of the same page. Parallel to the SAQ-IputI fix above. The "
            "footnote text supports the `occupant_role: \"Queen\"` "
            "classification and Teti's spouse identification — both "
            "Phase-A-relevant facts that need a documented PM trace. "
            "Restoration: append PM's verbatim footnote text (with PM's "
            "own `¹` anchor) to the headword condensation, no "
            "editorial `(Footnote: ...)` wrapper. Egyptologist F3 finding."
        ),
    },
    ("SAQ-Neterikhet", "occupant_alt_names"): {
        "value": ["Zoser", "Djoser"],
        "rationale": (
            "Egyptologist-reviewer printed-source pass against PM III.2 "
            "p.399: PM prints `STEP PYRAMID ENCLOSURE OF NETERIKHET "
            "(Zoser)` — the parenthetical `Zoser` is PM's printed alias "
            "(post-OK reception of the king's birth-name). Modern museum "
            "records (Met, Brooklyn, Harvard, BM) overwhelmingly use the "
            "spelling `Djoser` rather than PM's `Zoser`. Adding `Djoser` "
            "as a second alt_name gives Phase-A name-authority matching "
            "the museum-conventional spelling without altering PM's "
            "printed primary form. Egyptologist F4 finding (P2)."
        ),
    },
}

# Chunk-6 corrections (PM III.1 § III.A West Field cemeteries G 1000–G
# 1900, Junker excavations). Findings from the printed-source
# egyptologist-reviewer pass against PM III.1 pp.49–65.
CHUNK6_CORRECTIONS: dict[tuple[str, str], dict[str, object]] = {
    ("G1607", "is_unfinished"): {
        "value": False,
        "rationale": (
            "Egyptologist-reviewer printed-source pass against PM III.1 "
            "p.65 (physical p.62): the `unfinished` token appears in PM's "
            "body prose `Rock-cut tomb, unfinished.` AFTER the headword "
            "block, not within the headword. The chunk-6 prompt's "
            "`is_unfinished` rule fires only on headword-block "
            "`unfinished` (parallel to chunk-5 SAQ-Sekhemkhet where PM's "
            "`STEP PYRAMID. Unfinished.` IS the sub-heading). Agent A's "
            "extraction over-fired the deriver on body content. "
            "Restoration: `is_unfinished: true` → `false`. Egyptologist "
            "F1 finding (P1)."
        ),
    },
    ("G1234", "occupant_name"): {
        "value": "ʿAnkh-haf",
        "rationale": (
            "Egyptologist-reviewer printed-source pass against PM III.1 "
            "p.60 (physical p.57): PM prints `aANKH-HAF` (raised-ayin + "
            "all-caps + hyphen). Agent normalisation to U+02BF on the "
            "leading ayin produced `ʿAnkh-Haf` with title-cased `Haf` "
            "post-hyphen — but the standard Egyptological + museum-"
            "conventional Anglicisation lowercases the post-hyphen "
            "element (`ʿAnkh-haf`). Boston/Met catalogues print "
            "`Ankh-haf` / `Ankhhaf`. Phase-A name-authority "
            "matching against museum records depends on the lowercase-"
            "haf form. Restoration: `ʿAnkh-Haf` → `ʿAnkh-haf`. Parallel "
            "to chunk-3 LG 84's `Wehebreʿ-emakhet` (lowercase post-"
            "hyphen for the `m-akhet` locative element). Egyptologist "
            "F2 finding (P1). (Note: this is NOT the Dyn-IV Khufu-half-"
            "brother ʿAnkh-haf — that one is at G 7510 East Field, "
            "future chunk; PM dates G 1234 as `Late Dyn. V or Dyn. VI`.)"
        ),
    },
    ("G1234", "occupant_alt_names"): {
        "value": ["Ankhhaf", "Ankh-haf"],
        "rationale": (
            "Egyptologist F2 finding (P1) — companion to the "
            "`occupant_name` correction. Phase-A name-authority matching "
            "against museum records needs both the dehyphenated form "
            "`Ankhhaf` and the non-ayin lower-cased form `Ankh-haf`, "
            "since museum catalogues use both interchangeably (Boston "
            "MFA, Brooklyn, Met) for any ʿAnkh-haf row. The `ʿAnkh-haf` "
            "U+02BF form stays as `occupant_name`; the ASCII alt forms "
            "fall in `occupant_alt_names`. Gemini PR #225 round-1 "
            "high-priority finding."
        ),
    },
    ("G1221", "attribution_certainty"): {
        "value": "uncertain",
        "rationale": (
            "Gemini PR #225 round-3 finding (medium): the prompt's "
            "attribution_certainty rule says `(?)` → `\"uncertain\"`, "
            "`Probably`/`Perhaps` → `\"probable\"`. PM's G 1221 headword "
            "carries BOTH hedges: `SHAD (?), Royal acquaintance. Probably "
            "Dyn. V.` — the `(?)` after the name is uncertainty about the "
            "NAME reading (occupant-identification level), and `Probably` "
            "before `Dyn. V` is uncertainty about the DATING. The agents "
            "majority-voted `probable` on attribution_certainty (2/1 on "
            "interpreting `Probably Dyn. V.` as the operative hedge), but "
            "the `(?)` after the name is the more conservative hedge for "
            "the occupant-identification axis that attribution_certainty "
            "measures. Per the prompt's literal rule, the conservative "
            "`(?)` should win. Restoration: `\"probable\"` → "
            "`\"uncertain\"`. The dating uncertainty (`Probably Dyn. V.`) "
            "remains documented in `notes_from_pm`."
        ),
    },
    ("G1221", "notes_from_pm"): {
        "value": "Royal acquaintance. Probably Dyn. V.",
        "rationale": (
            "Egyptologist-reviewer printed-source pass against PM III.1 "
            "p.59 (physical p.56): PM prints `G 1221. SHAD (?), Royal "
            "acquaintance. Probably Dyn. V.` with ONE `(?)` hedge. The "
            "pypdf text-layer extraction stuttered the hedge (chunk-6 "
            "text file line 432 reads `SHAD (?) (?)`). Per reviewer "
            "F3 finding (P1) the name and hedge are removed from "
            "`notes_from_pm` entirely — the name reading is already in "
            "`occupant_name: \"Shad\"` and the doubt is already captured "
            "in `attribution_certainty: \"uncertain\"` (per the prompt's "
            "`(?)` → `uncertain` rule; see the G1221 attribution_certainty "
            "entry above for the round-3 correction from `probable` to "
            "`uncertain`). Including a second copy in the notes risks "
            "downstream consumers double-counting the hedge. "
            "Restoration: drop the name + hedge from notes (matches "
            "reviewer's recommended form). Gemini PR #225 round-1 "
            "medium-priority finding aligned this fix with the "
            "reviewer's recommended form."
        ),
    },
    ("G1207", "occupant_role"): {
        "value": "Official",
        "rationale": (
            "Egyptologist-reviewer pass against PM III.1 p.58 (physical "
            "p.55): NUFER's title cluster is `Royal acquaintance (woman)` "
            "— a non-royal honorific (rḫt-nswt) attested for elite "
            "non-royals, NOT a royal-family descent indicator. The "
            "chunk-6 prompt's role-derivation rule mistakenly mapped "
            "`Royal acquaintance (woman)` to `Royal Family`; corrected "
            "to `Official` per the honorific's actual meaning. "
            "Egyptologist F5 finding (P2)."
        ),
    },
    ("G1227", "occupant_role"): {
        "value": "Official",
        "rationale": (
            "Egyptologist-reviewer pass against PM III.1 p.59 (physical "
            "p.56): SETHIHEKNET's title cluster `Royal acquaintance "
            "(woman)` is the same non-royal honorific as G1207's. Same "
            "correction. Egyptologist F5 finding (P2)."
        ),
    },
    ("G1020", "occupant_role"): {
        "value": "Official",
        "rationale": (
            "Egyptologist-reviewer pass against PM III.1 p.53 (physical "
            "p.50): MES-SA's headword carries a named occupant with no "
            "explicit title cluster (just dating `Late Dyn. IV or first "
            "half of Dyn. V.`). The chunk-6 prompt's role-derivation "
            "rule has no entry for `named occupant, no title` and "
            "defaulted to `Unknown` — but `Unknown` is reserved for "
            "Shape-2 bare-suffix headwords (no name AT ALL). A named "
            "Old-Kingdom non-royal mastaba occupant defaults to "
            "`Official` per Old-Kingdom Memphite necropolis "
            "demographics. Egyptologist F6 finding (P2)."
        ),
    },
    ("G1104", "occupant_role"): {
        "value": "Official",
        "rationale": (
            "Egyptologist-reviewer pass against PM III.1 p.55 (physical "
            "p.52): MES-SA's headword (different individual from G1020 "
            "MES-SA, same conventional name) is parallel to G1020 — "
            "named occupant, no title cluster, dating only. Default to "
            "`Official` per the same rule. Egyptologist F6 finding (P2)."
        ),
    },
    ("G1204", "occupant_role"): {
        "value": "Official",
        "rationale": (
            "Egyptologist-reviewer pass against PM III.1 p.57 (physical "
            "p.54): AKHTIHOTP's headword (Middle Dyn. V or later) "
            "carries a named occupant with no explicit title cluster. "
            "Default to `Official` per the same rule. Egyptologist F6 "
            "finding (P2)."
        ),
    },
    ("G1314", "occupant_name"): {
        "value": "Khaʿkareʿ",
        "rationale": (
            "Egyptologist F-P2-3 finding: PM III.1 p.61 (physical p.58) "
            "prints `G 1314. Second half of Dyn. V.` as a bare-suffix "
            "headword, but the body content on the next printed page "
            "(p.62 / physical p.59) identifies the tomb owner: "
            "`Architrave with figure of Khaʿkareʿ repeated nine times.` "
            "+ `Double-statue, Khaʿkareʿ, Hairdresser of the Great "
            "House`. The architrave + statue are inscribed-attestation "
            "identifications of the tomb owner — Phase-A consumers need "
            "this for museum-matching. The agents correctly applied the "
            "chunk-6 headword-only rule (occupant_name: null) which is "
            "strictly faithful but loses the body-attested name. "
            "Restoration recovers `Khaʿkareʿ` from the body. PM's "
            "raised-ayin clusters in `Khaakarea` normalise to U+02BF on "
            "both occurrences. Gemini PR #225 round-1 medium-priority "
            "finding aligned this fix with the reviewer's recommended "
            "recovery."
        ),
    },
    ("G1314", "occupant_role"): {
        "value": "Official",
        "rationale": (
            "Egyptologist F-P2-3 companion: PM's body-attested title "
            "cluster for Khaʿkareʿ on physical p.62 is `Hairdresser of "
            "the Great House` (jr-šn pr-ꜥꜣ) — a non-royal court-officer "
            "title. Maps to `Official` per the chunk-6 role-derivation "
            "rule. Updated from agents' bare-suffix-default `Unknown`."
        ),
    },
    ("G1314", "attribution_certainty"): {
        "value": "probable",
        "rationale": (
            "Egyptologist F-P2-3 companion: the body-attested "
            "identification (architrave + double-statue) is strong "
            "inscriptional evidence but it is NOT a PM-headword "
            "identification — PM prints a bare-suffix headword for "
            "G 1314. The body inscriptions are PM-published; the "
            "identification is well-supported but is one inferential "
            "step removed from a headword-level attribution. "
            "Conservatively rate as `probable` rather than `attested` "
            "(reserve `attested` for headword-attestation cases)."
        ),
    },
    ("G1314", "notes_from_pm"): {
        "value": (
            "Second half of Dyn. V. Architrave with figure of Khaʿkareʿ "
            "repeated nine times. Double-statue, Khaʿkareʿ, Hairdresser "
            "of the Great House."
        ),
        "rationale": (
            "Egyptologist F-P2-3 companion: extends the bare-suffix "
            "headword's `Second half of Dyn. V.` with the body-attested "
            "identifications (architrave inscription + double-statue "
            "label) per the reviewer's recommendation. Documents the "
            "trace from PM's body text for Phase-A consumers."
        ),
    },
}

# Per-chunk reviewer corrections for chunk 7 (Gîza West Field Cemetery
# G 2000 + G 2100 + Mastaba G 2220). Intentionally empty — chunk-7
# normalisation was handled by a separate one-time pre-merge script
# (`normalize_chunk7.py`) that stripped occupant-name prefixes from
# notes_from_pm. No reviewer-cited row-level corrections were required
# after that normalisation. Kept here as an empty placeholder per
# Gemini PR #228 round-2 medium for registry completeness.
CHUNK7_CORRECTIONS: dict[tuple[str, str], dict[str, object]] = {}


# Per-chunk reviewer corrections for chunk 8 (Gîza West Field Cemetery
# en Echelon G 2300 + G 2400 + Cemetery G 2500). Combined feedback from
# Gemini Code Assist PR #227 round 1 (3 medium) + egyptologist-reviewer
# (4 P1, 4 P2) + code-reviewer (3 P2, 2 P3) on commit ac9085fe.
CHUNK8_CORRECTIONS: dict[tuple[str, str], dict[str, object]] = {
    # Egyptologist P1-1: PM headword on G 2407 is bare-suffix, but the
    # body sub-heading immediately below the headword (line 435 of the
    # chunk file) reads "Statues. Late Dyn. V. Found in débris of shaft
    # D." Per chunk-6 G 1314 body-recovery precedent, body-attested
    # dating dating IS captured on dynasty; certainty stays uncertain.
    ("G2407", "dynasty"): {
        "value": "5",
        "rationale": (
            "Egyptologist PR #227 P1-1: G 2407 PM headword is bare-"
            "suffix `G 2407.`, but body sub-heading `Statues. Late "
            "Dyn. V.` on the next printed line documents tomb owner's "
            "Late Dyn. V dating. Per chunk-6 G 1314 precedent, body-"
            "attested dating recovered into `dynasty`."
        ),
    },
    ("G2407", "notes_from_pm"): {
        "value": "Late Dyn. V. Statues found in débris of shaft D.",
        "rationale": "Companion to dynasty fix: capture body-attested dating in notes.",
    },
    # Egyptologist P1-2: same body-recovery pattern for G 2501.
    ("G2501", "dynasty"): {
        "value": "6",
        "rationale": (
            "Egyptologist PR #227 P1-2: G 2501 PM headword is bare-"
            "suffix `G 2501.`, but body line reads `Head and legs of "
            "statuette, Dyn. VI, found in front of mastaba` (printed "
            "p.95). Body-attested Dyn. VI captured into `dynasty`."
        ),
    },
    ("G2501", "notes_from_pm"): {
        "value": "Dyn. VI. Statuette found in front of mastaba.",
        "rationale": "Companion to dynasty fix.",
    },
    # Egyptologist P2-4 + body-recovery consistency: G 2335 body reads
    # `wood, Dyn. V, from burial chamber of shaft A` — same recovery
    # pattern as G 2407/G 2501.
    ("G2335", "dynasty"): {
        "value": "5",
        "rationale": (
            "Egyptologist PR #227 P2-4: G 2335 body sub-heading "
            "`Male statuette ... wood, Dyn. V, from burial chamber of "
            "shaft A` body-attests Dyn. V. Burial-chamber context = "
            "strong attribution to tomb owner."
        ),
    },
    ("G2335", "notes_from_pm"): {
        "value": "Dyn. V. Wood statuettes from burial chamber of shaft A.",
        "rationale": "Companion to dynasty fix.",
    },
    # Egyptologist P2-4: G 2336 body has `Three female statuettes, wood,
    # Dyn. V-VI, from serdab` (line 38 of chunk file). Range tail rule
    # → Dyn. VI = "6". Also captures body-attested name Khuwiptah from
    # relief-fragment (line 37) per scope-accountability-enforcer
    # required action: body-prose attestation must be structurally
    # captured, not punted.
    ("G2336", "dynasty"): {
        "value": "6",
        "rationale": (
            "Egyptologist PR #227 P2-4: G 2336 body reads "
            "`Three female statuettes, wood, Dyn. V-VI, from serdab` "
            "(serdab = inner statue chamber → strong tomb-owner "
            "attribution). Range tail rule → `6`."
        ),
    },
    ("G2336", "occupant_name"): {
        "value": "Khuwiptah",
        "rationale": (
            "Scope-accountability-enforcer required action on PR #227 "
            "E-P2-3: G 2336 body line `Relief-fragment, Khuwiptah and "
            "text, in Boston Mus. 13.4344.` names Khuwiptah as the "
            "relief-attested occupant. Body-recovery follows chunk-6 "
            "G 1314 Khaʿkareʿ precedent (architrave-attested name "
            "promoted to occupant_name with attribution_certainty: "
            "uncertain since the relief-fragment context is weaker "
            "than the Khaʿkareʿ double-statue inscription). Theneny "
            "(false-door found BETWEEN G 2337 and G 2371 per PM "
            "explicit clause) is NOT this tomb's owner; mentioned in "
            "notes_from_pm only."
        ),
    },
    ("G2336", "occupant_role"): {
        "value": "Official",
        "rationale": "Khuwiptah body-recovery default role per chunk-6 G 1314 precedent.",
    },
    ("G2336", "notes_from_pm"): {
        "value": (
            "Relief-fragment with Khuwiptah and text. Three female "
            "statuettes, wood, Dyn. V-VI, from serdab. False-door of "
            "Theneny Inspector of ka-servants, etc., Dyn. VI, found "
            "between tombs G 2337 and G 2371."
        ),
        "rationale": "Body-prose recovery: Khuwiptah relief + Theneny adjacent false-door.",
    },
    # Egyptologist P1-3: Hathor → Ḥathor underdot in co_occupant_roles.
    # PM prints Ḥ with underdot at p.87 (G 2378) and p.94 (G 2430).
    ("G2378", "co_occupant_roles"): {
        "value": ["Wife, King's daughter of his body, Prophetess of Ḥathor"],
        "rationale": (
            "Egyptologist PR #227 P1-3: PM prints Hathor with underdot-"
            "Ḥ (cobra-house-of-Horus root); chunk-8 already preserves "
            "underdot on Meḥi, Meḥu, Maʿet, Meryptaḥʿankh — Hathor "
            "asymmetry was an oversight. Verified against PM PDF p.87."
        ),
    },
    ("G2430", "co_occupant_roles"): {
        "value": ["Wife, Prophetess of Ḥathor in all her places"],
        "rationale": (
            "Egyptologist PR #227 P1-3: same Ḥathor underdot fix "
            "(verified PM PDF p.94)."
        ),
    },
    # Gemini G2 + Egyptologist scope: wife clauses missing from
    # G2370/G2378/G2430 notes. Per chunk-8 design rule (transcribe.md
    # §"Wife-attestation in body prose preserved when adjacent to
    # headword"), wife clauses adjacent to the headword are preserved
    # verbatim — chunk-8 currently applies this rule via override on
    # G 2423 only. Generalize: apply consistently across G 2370,
    # G 2378, G 2430 where PM prints `Wife, <NAME> <Title cluster>`
    # immediately after the dating marker.
    ("G2370", "notes_from_pm"): {
        "value": (
            "Chief Justice and Vizier, King's architect and builder in "
            "the Two Houses, etc. Temp. Isesi. (Also owner of tomb LG "
            "10.) Wife, Thefi Royal acquaintance. Stone-built mastaba. "
            "LG 27."
        ),
        "rationale": (
            "Gemini PR #227 medium #2: chunk-8 design rule preserves "
            "wife-attestation clauses adjacent to headword (G 2423 "
            "precedent). G 2370's `Wife, Thefi Royal acquaintance.` "
            "clause restored to notes for cross-chunk consistency."
        ),
    },
    ("G2378", "notes_from_pm"): {
        "value": (
            "Chief Justice and Vizier, King's architect and builder in "
            "the Two Houses, etc. Temp. Unis. Parents, Senezemib Inti "
            "and Thefi (tomb G 2370). Wife, Khentkaus King's daughter "
            "of his body, Prophetess of Ḥathor. Stone-built mastaba. "
            "LG 26."
        ),
        "rationale": (
            "Gemini PR #227 medium #2: same wife-clause restoration "
            "(Khentkaus, King's daughter of his body)."
        ),
    },
    ("G2430", "notes_from_pm"): {
        "value": (
            "Overseer of tenants of the Great House, Director of the "
            "Palace, Secretary of his Lord, etc. Early Dyn. VI. Wife, "
            "Khaʿmerernebti Prophetess of Ḥathor in all her places, "
            "etc. Stone-built mastaba. LG 25."
        ),
        "rationale": (
            "Gemini PR #227 medium #2: same wife-clause restoration "
            "(Khaʿmerernebti, Prophetess of Ḥathor)."
        ),
    },
    # Egyptologist P2-1 + Gemini-aligned: add `Senedjemib` modern
    # spelling to occupant_alt_names for the two Senedjemib viziers.
    # Boston MFA / Met / current Egyptological lit predominantly use
    # the modern spelling; preserve PM-verbatim `Senezemib` in
    # occupant_name and add `Senedjemib` as a secondary alias alongside
    # the PM `good name` form.
    ("G2370", "occupant_alt_names"): {
        "value": ["Inti", "Senedjemib"],
        "rationale": (
            "Egyptologist PR #227 P2-1: Senedjemib is the modern "
            "spelling used by Boston MFA + Met catalogs + current "
            "Egyptological literature; preserve PM-verbatim `Senezemib`"
            " as primary, add `Senedjemib` as alias for cross-museum "
            "matching at Phase A. `Inti` (PM 'good name') stays."
        ),
    },
    ("G2378", "occupant_alt_names"): {
        "value": ["Meḥi", "Senedjemib"],
        "rationale": "Same Senedjemib modern-spelling alias as G 2370.",
    },
    # Gemini G3 + Code-reviewer P2-1 — underdot-Ḥ on occupant names
    # where the underlying Egyptian root carries underdot-Ḥ.
    ("G2352", "occupant_name"): {
        "value": "Ḥagi",
        "rationale": (
            "Gemini PR #227 medium #3: PM-verbatim transliteration "
            "Ḥagi (Egyptian root `ḥgy`); chunk-8 was inconsistent — "
            "Meḥu/Meḥi/Ptaḥ already underdot-Ḥ, but Hagi/Akhetmehu/"
            "Hetepniptah/ʿAnkhirptah missed it. Source-wide ḥ "
            "convention applied here for consistency."
        ),
    },
    ("G2375", "occupant_name"): {
        "value": "Akhetmeḥu",
        "rationale": (
            "Gemini PR #227 medium #3 + Code-reviewer PR #227 P2-1: "
            "underdot-ḥ on the *mḥw* root. Test docstring already "
            "wrote `Akhetmeḥu` — data corrected to match the docstring "
            "convention."
        ),
    },
    ("G2375a", "occupant_name"): {
        "value": "ʿAnkhirptaḥ",
        "rationale": (
            "Gemini PR #227 medium #3: underdot-ḥ on the *ptḥ* "
            "theophoric root (`ʿnḫ-ir-ptḥ` = 'Ptaḥ-makes-life'). "
            "Parallel to G 2381/G 2387 Meryptaḥʿankh."
        ),
    },
    ("G2430", "occupant_name"): {
        "value": "Ḥetepniptaḥ",
        "rationale": (
            "Gemini PR #227 medium #3: underdot-ḥ on BOTH the *ḥtp* "
            "root (initial) and *ptḥ* root (terminal) — `ḥtp-nî-ptḥ` "
            "= 'Ptaḥ-is-merciful-to-me'."
        ),
    },
}


# Per-chunk reviewer corrections for chunk 9 (Gîza West Field Cemetery
# G 3000, Fisher's "Minor Cemetery"). Gemini PR #228 round-1 medium #1
# flagged G 3086 RUZ row.
CHUNK9_CORRECTIONS: dict[tuple[str, str], dict[str, object]] = {
    ("G3086", "notes_from_pm"): {
        "value": (
            "Prophet of Khufu, Raʿzedef, and Khephren, waʿb-priest of "
            "the King's mother, Supervisor of the police, etc. Dyn. "
            "VI. Parents, Iymerery and Personet (tomb G 3098). Wife, "
            "Mest Royal acquaintance."
        ),
        "rationale": (
            "Gemini PR #228 medium #1: G 3086 RUZ headword notes — "
            "agents reached 2/1 majority on `waab-priest` (text-layer "
            "raw) so merge.py picked that form, but it violates the "
            "source-wide raised-`a` → U+02BF ayin normalisation "
            "convention applied uniformly across G 3008 / G 3093 / "
            "G 3098 waʿb-priest renderings (PM III.1 p.98). Reviewer "
            "correction: rewrite `waab-priest` → `waʿb-priest`."
        ),
    },
    ("G3086", "shared_with_tombs"): {
        "value": ["G3098"],
        "rationale": (
            "Gemini PR #228 medium #1 + code-reviewer PR #228 P1.2: "
            "G 3086 RUZ notes_from_pm contains the explicit cross-"
            "reference `Parents, Iymerery and Personet (tomb G 3098).` "
            "Per the chunk-9 prompt field-rule for `shared_with_tombs` "
            "(chunks 6–8 convention), an explicit cross-tomb reference "
            "is captured structurally. Ruz is the son of G 3098's "
            "primary occupant Iymerery — bidirectional family link "
            "(paired with the G3098 → G3086 entry below)."
        ),
    },
    ("G3098", "shared_with_tombs"): {
        "value": ["G3086"],
        "rationale": (
            "Code-reviewer PR #228 P1.2: G 3098 IYMERERY body contains "
            "the explicit cross-reference `Drum of deceased and wife, "
            "dedicated by son Ruz (tomb G 3086)` (PM III.1 printed "
            "p.99). Per the chunk-9 prompt field-rule for "
            "`shared_with_tombs`, an explicit cross-tomb reference is "
            "captured structurally. This is the reciprocal link to "
            "G 3086 → G 3098 (parent–son relationship). Agents A+C "
            "missed it; agent B captured it; A+C silently won "
            "majority — reviewer correction restores."
        ),
    },
    # Egyptologist F1 P1 finding: G 3097 occupant Neferhi must use
    # underdot-ḥ for chunk-internal consistency with G 3098 (b)
    # Neferḥetpes-Wer (same `nfr-ḥy/ḥtp` root family). PM III.1 p.99
    # uses underdot-Ḥ throughout this chunk on names with the ḥ
    # phoneme (Snefruḥotp, Ḥathor, Meḥu etc. — egyptologist
    # verified). Both G 3097 + G 3098(b) names share the same root,
    # so they must resolve to the same form. Selecting Neferḥi.
    ("G3097", "occupant_name"): {
        "value": "Neferḥi",
        "rationale": (
            "Egyptologist PR #228 F1 P1: intra-chunk inconsistency "
            "G 3097 `Neferhi` vs G 3098 `Neferḥetpes-Wer` for the "
            "same `nfr-ḥ` root family. PM III.1 p.99 typesetting "
            "uses underdot-Ḥ on this root. OCR strips diacritics in "
            "all-caps (PM prints `NEFERHI` and `NEFERHETPES-WER` in "
            "caps), so the text layer couldn't settle the question. "
            "Reviewer correction: Neferhi → Neferḥi for source-wide "
            "consistency."
        ),
    },
    # Egyptologist P3 nit: G 3035 wife title `mjtrt` (text-layer raw,
    # 2/1 agent majority) should normalise to `mitrt` matching the
    # G 3050 G3050|co_occupant_roles tie-break override convention.
    # PM publisher typography uses `i`/`j` interchangeably for the
    # *i* phoneme in OK female titles; `mitrt` is the form used in
    # G 3050 (PM III.1 p.98 verbatim), so chunk-9 normalises uniformly.
    ("G3035", "co_occupant_roles"): {
        "value": ["Wife, mitrt"],
        "rationale": (
            "Egyptologist PR #228 P3: G 3035 wife title `mjtrt` "
            "normalised to `mitrt` matching G 3050 (PM III.1 p.98) "
            "tie-break override. PM publisher typography variance "
            "between `mjtrt`/`mitrt` is OCR-level noise; standardise "
            "on `mitrt` for source-wide consistency."
        ),
    },
    ("G3035", "notes_from_pm"): {
        "value": "Judge and Scribe. Dyn. VI. Wife, Nefert mitrt.",
        "rationale": (
            "Egyptologist PR #228 P3: companion to the "
            "co_occupant_roles fix — notes_from_pm also normalised "
            "`mjtrt` → `mitrt`."
        ),
    },
}


# Per-chunk reviewer corrections for chunk 10 (Gîza West Field JUNKER
# CEMETERY (WEST) named-tomb cluster). Adds the JKR-Ithu co_occupants
# expansion to keep length-coupling with the 3-entry co_occupant_roles
# override; tie-break-overrides.json carries the structured tie
# resolutions but cannot extend a non-tied field, so fix_rows.py is
# the right channel for the co_occupants expansion (chunks 6/8/9
# precedent for body-recovery reviewer corrections).
CHUNK10_CORRECTIONS: dict[tuple[str, str], dict[str, object]] = {
    ("JKR-Ithu", "co_occupants"): {
        "value": ["Iaʿib", "Khaut I", "Intkaes"],
        "rationale": (
            "Chunk-10 reviewer pass: PM III.1 2nd ed. 1974 p.103 prints "
            "Ithu's headword block with THREE co-occupants — Parents "
            "(probably) Iaʿib (Scribe) + Khaut I (mitrt) + Wife Intkaes "
            "(mitrt). All three agents reduced co_occupants to only "
            "the wife (`[\"Intkaes\"]`); the tie-break-override on "
            "co_occupant_roles expanded to 3 entries (parents+wife). "
            "This correction keeps the length-coupling invariant "
            "satisfied by expanding co_occupants to match — paired "
            "with the tie-break override on JKR-Ithu|co_occupant_roles."
        ),
    },
    # Gemini PR #229 review-1 medium: mjtrt → mitrt normalisation in
    # JKR-Ankh notes (was `mjtrt`, but co_occupant_roles override
    # already standardised on `mitrt`; this aligns notes to match).
    ("JKR-Ankh", "notes_from_pm"): {
        "value": "ʾtw-official. Late Old Kingdom. Wife, Nefertka, mitrt.",
        "rationale": (
            "Gemini PR #229 review-1 medium: PM III.1 2nd ed. 1974 "
            "p.100 prints `mjtrt` in the typographic variant; "
            "chunk-9 G 3050 + chunk-10 JKR-Ankh|co_occupant_roles "
            "tie-break override standardise on `mitrt`. Notes string "
            "aligned for source-wide consistency."
        ),
    },
    # Gemini PR #229 review-1 medium: `Dyn VI.` missing period (should
    # be `Dyn. VI.`). 2/1 agent majority on the truncated form.
    ("JKR-KhesefI", "notes_from_pm"): {
        "value": "Recruit. Dyn. VI.",
        "rationale": (
            "Gemini PR #229 review-1 medium: PM III.1 2nd ed. 1974 "
            "p.106 prints `Dyn. VI.` (period before VI); 2/1 agent "
            "majority dropped the period. Restored."
        ),
    },
    # Gemini PR #229 review-1 medium: cross-ref to `Meni [I]` should
    # drop the brackets per the chunk-10 bracketed-regnal rule applied
    # to JKR-SonbI Sentiotes I + JKR-MeniI / JKR-MeniII tomb_ids.
    ("JKR-MeniII", "notes_from_pm"): {
        "value": (
            "Elder of the house. Late Dyn. VI. Possibly same as Meni I. "
            "Wife, Merutnes."
        ),
        "rationale": (
            "Gemini PR #229 review-1 medium: PM III.1 2nd ed. 1974 "
            "p.107 cross-reference `Meni [I]` — bracketed Roman "
            "regnal normalisation per chunk-10 prompt rule (drop "
            "brackets, append Roman with space). Consistent with "
            "JKR-SonbI's Sentiotes I treatment."
        ),
    },
    # Gemini PR #229 review-1 medium: Hathor → Ḥathor underdot
    # (chunk-8 PR #227 P1-3 + chunk-9 source-wide Ḥathor convention).
    ("JKR-Menib", "notes_from_pm"): {
        "value": "Prophetess of Ḥathor, etc. Late Old Kingdom.",
        "rationale": (
            "Gemini PR #229 review-1 medium: PM III.1 2nd ed. 1974 "
            "p.104 prints Ḥathor with underdot-Ḥ; agents' 2/1 majority "
            "dropped the diacritic. Restored per source-wide chunk-8 "
            "PR #227 P1-3 + chunk-9 G 3008/G 3093 conventions."
        ),
    },
    # Gemini PR #229 review-1 medium: mjtrt → mitrt in JKR-Nebtpezu
    # notes (same as JKR-Ankh fix).
    ("JKR-Nebtpezu", "notes_from_pm"): {
        "value": "mitrt (woman). Late Old Kingdom.",
        "rationale": (
            "Gemini PR #229 review-1 medium: PM III.1 2nd ed. 1974 "
            "p.104 prints `mjtrt` in typographic variant; chunk-9/10 "
            "convention standardises on `mitrt`. Aligned."
        ),
    },
    # Gemini PR #229 review-1 medium: JKR-Sinekhen co_occupants name
    # missing ayin (was `Maakherui`); notes_from_pm tie-break already
    # has `Maʿkherui`. Align co_occupants.
    ("JKR-Sinekhen", "co_occupants"): {
        "value": ["Maʿkherui"],
        "rationale": (
            "Gemini PR #229 review-1 medium: PM III.1 2nd ed. 1974 "
            "p.103 prints `Maʿkherui` with raised-ayin; agents' 2/1 "
            "majority left raw OCR `Maakherui`. notes_from_pm tie-"
            "break already restored the ayin; aligning co_occupants."
        ),
    },
    ("JKR-Sinekhen", "co_occupant_roles"): {
        "value": ["Wife, Female steward, etc."],
        "rationale": (
            "Gemini PR #229 review-2 high: add `Wife,` prefix per "
            "chunk-8/9/10 wife-clause convention (parallel to "
            "JKR-Ankh `Wife, mitrt`, chunk-9 G 3008 `Wife, Prophetess "
            "of Ḥathor...`)."
        ),
    },
    # Gemini PR #229 review-1 medium: JKR-Sinufer ʿAnkh-hathor wife
    # name missing underdot-Ḥ on `hathor` element. PM prints with
    # underdot; restore to `ʿAnkh-ḥathor`.
    ("JKR-Sinufer", "co_occupants"): {
        "value": ["ʿAnkh-ḥathor"],
        "rationale": (
            "Gemini PR #229 review-1 medium: wife's name `ʿAnkh-"
            "hathor` (=`ʿnḫ-ḥwt-ḥr` Egyptian `Hathor-lives`) carries "
            "the underdot-Ḥ on the *ḥwt-ḥr* root; PM III.1 prints "
            "this verbatim. Restored."
        ),
    },
    ("JKR-Sinufer", "co_occupant_roles"): {
        "value": ["Wife, Royal acquaintance"],
        "rationale": (
            "Gemini PR #229 review-2 high: add `Wife,` prefix per "
            "chunk-8/9/10 convention."
        ),
    },
    ("JKR-Sinufer", "notes_from_pm"): {
        "value": (
            "Inspector of tenants of the Great House, etc. Dyn. VI. "
            "Wife, ʿAnkh-ḥathor Royal acquaintance."
        ),
        "rationale": (
            "Gemini PR #229 review-1 medium: notes ḥathor underdot "
            "alignment with co_occupants fix."
        ),
    },
    # Gemini PR #229 review-2 HIGH: JKR-Inpuhotp 3-co-occupant bug.
    # notes_from_pm tie-break override already captures `Parents,
    # Ither ... and Sabt Royal acquaintance. Wife, Senezem.` but
    # co_occupants/co_occupant_roles reduced to 1 (wife only) and
    # role was incorrectly tagged `Royal acquaintance` (one of the
    # parents' role, not the wife's). Expand to 3 entries.
    ("JKR-Inpuhotp", "co_occupants"): {
        "value": ["Ither", "Sabt", "Senezem"],
        "rationale": (
            "Gemini PR #229 review-2 HIGH: PM III.1 2nd ed. 1974 "
            "p.106 (physical p.103) prints Inpuhotp's headword block "
            "with THREE co-occupants — Parents Ither (Prophet of "
            "Neuserrēʿ, etc.) and Sabt (Royal acquaintance), plus "
            "Wife Senezem. notes_from_pm tie-break override already "
            "captured the parents-and-wife clause verbatim; this "
            "correction expands co_occupants from 1 (wife only) to "
            "all 3 occupants in PM headword-block order. Parallel "
            "to JKR-Ithu chunk-10 reviewer fix."
        ),
    },
    ("JKR-Inpuhotp", "co_occupant_roles"): {
        "value": [
            "Parent, Prophet of Neuserrēʿ, etc.",
            "Parent, Royal acquaintance",
            "Wife",
        ],
        "rationale": (
            "Gemini PR #229 review-2 HIGH: paired with co_occupants "
            "expansion. PM prints Wife Senezem without a title "
            "cluster — use plain `Wife` per chunk-8 G 2415 + "
            "chunk-10 JKR-Iiu / JKR-MeniII precedent. Parents tagged "
            "`Parent, <title cluster>` per chunk-10 JKR-Ithu pattern."
        ),
    },
    # Gemini PR #229 review-2 high: JKR-SonbI co_occupant_roles add
    # `Wife,` prefix + restore Ḥathor underdot.
    ("JKR-SonbI", "co_occupant_roles"): {
        "value": ["Wife, Prophetess of Ḥathor and Neith, etc."],
        "rationale": (
            "Gemini PR #229 review-2 high: add `Wife,` prefix per "
            "chunk-8/9/10 wife-clause convention + restore Ḥathor "
            "underdot per chunk-8 PR #227 P1-3 source-wide rule."
        ),
    },
}


# Chunk-11 (Steindorff Cemetery D-numbered + STN- interstitials, halves 11a+11b).
# Round-1 Gemini fixes apply the project-wide Re-deity + ḥ-root diacritic
# conventions consistently to chunk-11 names that the agent-majority left
# under-normalised; also moves mitrt title out of co_occupants name field
# into co_occupant_roles per chunks 9/10 precedent.
CHUNK11_CORRECTIONS: dict[tuple[str, str], dict[str, object]] = {
    # D.9 RAaHOTP — Re-deity-compound theonymic name. Apply macron-Ē + ayin
    # + underdot-Ḥ per chunk-11 D37 precedent (`Rēʿḥerka`). Egyptian name
    # *rꜥ-ḥtp* (\"Re is content\") — Ra IS the deity here.
    ("D9", "occupant_name"): {
        "value": "Rēʿḥotp",
        "rationale": (
            "Gemini PR #231 round-1 medium: Re-deity-compound theonymic "
            "name requires source-wide macron-Ē + ayin + underdot-Ḥ per "
            "chunk-11 D37 `Rēʿḥerka` precedent and chunks 4/8/10 "
            "convention (Merenrēʿ I, Saḥurēʿ, Neuserrēʿ). Agent-majority "
            "wrote `Raʿḥotp` (ayin only, no macron). Fix to `Rēʿḥotp`."
        ),
    },
    # D.23 RAaSHEPSES — same Re-deity-compound rule. Stem `shepses` has no
    # ḥ-root, so no underdot here.
    ("D23", "occupant_name"): {
        "value": "Rēʿshepses",
        "rationale": (
            "Gemini PR #231 round-1 medium: Re-deity-compound theonymic "
            "name requires macron-Ē + ayin per chunks 4/8/10 convention "
            "and chunk-11 D37 `Rēʿḥerka` precedent. Agent-majority wrote "
            "`Raʿshepses` (ayin only, no macron). Fix to `Rēʿshepses`. No "
            "underdot-Ḥ since `shepses` has no ḥ-root."
        ),
    },
    # D.116 SESHEMU — agents put the wife title `mjtrt` inside the
    # co_occupants name field. Move to co_occupant_roles per chunks 9/10
    # `Wife, mitrt` convention. Also normalise mjtrt→mitrt in notes.
    ("D116", "co_occupants"): {
        "value": ["Nefert"],
        "rationale": (
            "Gemini PR #231 round-1 medium: Egyptian female title `mitrt` "
            "belongs in co_occupant_roles, not in the occupant-name field. "
            "Agent-majority emitted `[\"Nefert mjtrt\"]` mixing title into "
            "name. Per chunk-9 G 3050 + chunk-10 JKR-Ankh convention, name "
            "and title separate: co_occupants `[\"Nefert\"]`, "
            "co_occupant_roles `[\"Wife, mitrt\"]`."
        ),
    },
    ("D116", "co_occupant_roles"): {
        "value": ["Wife, mitrt"],
        "rationale": (
            "Gemini PR #231 round-1 medium: paired with D116 co_occupants "
            "correction. Per chunk-9 G 3050 + chunk-10 JKR-Ankh `Wife, "
            "mitrt` convention. Agent-majority emitted no role (length-"
            "coupled with the title-in-name miscapture)."
        ),
    },
    ("D116", "notes_from_pm"): {
        "value": "Overseer of the crew of rowers. Dyn. V-VI. Wife, Nefert mitrt.",
        "rationale": (
            "Gemini PR #231 round-1 medium: source-wide `mjtrt`→`mitrt` "
            "typography normalisation per chunk-9 G 3050 + G 3035 + "
            "chunk-10 JKR-Ankh `mitrt` convention. Agent-majority preserved "
            "PM-verbatim `mjtrt` in notes; fix to standardised `mitrt`."
        ),
    },
    # D.117 WEHEMKA notes_from_pm — agent-majority left `Hetepibes` without
    # underdot-Ḥ; the D117|co_occupants tie-break override already uses
    # `Ḥetepibes`. Apply the underdot consistently in notes too.
    ("D117", "notes_from_pm"): {
        "value": (
            "Scribe of the archives and of recruits, Steward, etc. Early "
            "Dyn. V. Parents, Iti Strong-of-voice of the archives, and "
            "Zefatsen Royal acquaintance. Wife, Ḥetepibes called Ipi "
            "Royal acquaintance."
        ),
        "rationale": (
            "Gemini PR #231 round-1 medium: underdot-Ḥ on the ḥ-root "
            "`Ḥetepibes` per the D117|co_occupants tie-break override "
            "convention. Agent-majority wrote `Hetepibes` without "
            "underdot, creating intra-row inconsistency with the "
            "co_occupants override that mandated underdot per source-"
            "wide ḥ-root convention (chunk-8 PR #227 P1-3 + chunk-9 "
            "G 3008 / G 3093 Ḥathor precedent)."
        ),
    },
    # D.203 NUFER+ITISEN joint twin notes_from_pm — agent-majority "TAw"
    # capitalisation does not match the D203|co_occupant_roles tie-break
    # override which uses "tAw" (PM's italic transliteration of Egyptian
    # *tꜣw* / sailor-crew).
    ("D203", "notes_from_pm"): {
        "value": (
            "Nufer Overseer of barbers, etc., and Itisen Overseer of the "
            "tAw of the Great Bark. Late Dyn. V or Dyn. VI."
        ),
        "rationale": (
            "Gemini PR #231 round-1 medium: `tAw` capitalisation must "
            "match the D203|co_occupant_roles tie-break override which "
            "selected lowercase-t form. Agent-majority wrote `TAw` (cap T) "
            "in notes; fix to `tAw` (lowercase t) for intra-row "
            "consistency."
        ),
    },
    # D.215 IMHOTEP — co_occupants wife name also needs source-wide
    # `Ḥathor` single-underdot normalisation per the D215|notes_from_pm
    # override fix (`Ḥatḥor` double-underdot → `Ḥathor` single-underdot).
    # Follows from the same rule Gemini flagged on the override; applies
    # rule consistently to all D215 fields.
    ("D215", "co_occupants"): {
        "value": ["ʿAnkh-Ḥathor"],
        "rationale": (
            "Gemini PR #231 round-1 medium (rule-consistency extension): "
            "the same `Ḥatḥor` → `Ḥathor` single-underdot fix Gemini "
            "flagged on D215|notes_from_pm override applies to "
            "co_occupants where the agent-majority `ʿAnkh-Ḥatḥor` carries "
            "the same double-underdot mistake. Per chunks 8/9 source-wide "
            "Ḥathor convention (single underdot on the initial ḥ, no "
            "underdot on the medial t)."
        ),
    },
    # D.215 co_occupant_roles — title `mitrt` is in notes_from_pm but missing
    # from the role field. Add per chunks 9/10 `Wife, mitrt` convention.
    ("D215", "co_occupant_roles"): {
        "value": ["Wife, mitrt"],
        "rationale": (
            "Gemini PR #231 round-2 medium: title `mitrt` is in "
            "notes_from_pm but the role field was just `[\"Wife\"]` "
            "(dropping the title). Per chunk-9 G 3050 + chunk-10 JKR-Ankh "
            "+ chunk-11 D116 `Wife, mitrt` convention, the title belongs in "
            "co_occupant_roles. Same rule that Gemini flagged on D116 "
            "applies here."
        ),
    },
    # D.39/40 ZASHA page number — agent-majority assigned page 109 because
    # the chunk-11b raw file's split point dropped the preceding
    # `=== PHYS PAGE 108 ===` marker, leaving D.39/40 without an immediate
    # page-marker antecedent; agents fell back to the misleading
    # `West Field 109` header preserved from the chunk-11 banner head.
    # PM III.1 2nd ed. 1974 places `D. 39/40` on physical p.108 = printed
    # p.111 (verified against the PDF: physical p.108 has `West Field 111`
    # running header followed by D.37, D.38, and D.39/40 headwords).
    ("D39", "source_citation"): {
        "value": {"edition": "PM III.1 2nd ed. 1974", "page": 111, "section": "III"},
        "rationale": (
            "Gemini PR #231 round-2 medium: page 109 → 111. Verified "
            "against PM III.1 2nd ed. 1974 PDF physical p.108 (running "
            "header `West Field 111`) which carries D.37 + D.38 + D.39/40 "
            "headwords. Agent error caused by chunk-11b split dropping the "
            "preceding `=== PHYS PAGE 108 ===` marker, leaving agents to "
            "fall back on the misleading `West Field 109` banner header."
        ),
    },
}


# Registry of all per-chunk correction dicts. New chunks add their
# `CHUNK<N>_CORRECTIONS` constant to THIS list (single source of truth);
# `main`'s correction loop iterates this list rather than hardcoding the
# tuple inline. Gemini PR #219 round-1 medium-priority finding.
_ALL_CHUNK_CORRECTIONS: list[dict[tuple[str, str], dict[str, object]]] = [
    CHUNK1_CORRECTIONS,
    CHUNK2_CORRECTIONS,
    CHUNK3_CORRECTIONS,
    CHUNK4_CORRECTIONS,
    CHUNK5_CORRECTIONS,
    CHUNK6_CORRECTIONS,
    CHUNK7_CORRECTIONS,
    CHUNK8_CORRECTIONS,
    CHUNK9_CORRECTIONS,
    CHUNK10_CORRECTIONS,
    CHUNK11_CORRECTIONS,
]

# Schema-uniformity backfill: every reconciled row carries
# `co_occupant_roles: list[str]` (default `[]` for single-occupant rows
# and rows whose co-occupants are not typed by PM). Rows in
# `CHUNK<N>_CORRECTIONS` that set this key override the default.
def _ensure_co_occupant_roles_default(row: dict) -> bool:
    """Backfill `co_occupant_roles: []` on rows that don't already have
    the field. Idempotent — re-running on a row that already has the
    field is a no-op. Returns True if the row was modified.
    """
    if "co_occupant_roles" not in row:
        row["co_occupant_roles"] = []
        return True
    return False


def _apply_chunk2_notes_ocr_fixes(notes: str | None, tid: str) -> str | None:
    """Per-row OCR fixes inside `notes_from_pm` that are scoped to a single
    chunk-2 row. Separate from the source-wide `_NOTES_OCR_FIXES` table
    because these substitutions are narrow enough that the global table
    would carry risk of misfiring on a future chunk.

    Currently: G7102 — rewrite the all-caps `IOU` (pypdf D→O misread) to
    `IDU` so the stored verbatim notes match what PM printed. The
    `notes_from_pm` stored form was `"IOU Tenant of the Pyramid of Pepy
    I, ..."`; rewrite the leading token only.
    """
    if notes is None:
        return None
    if tid == "G7102" and notes.startswith("IOU "):
        return "IDU " + notes[len("IOU "):]
    return notes


def _apply_ocr_fixes(notes: str | None) -> str | None:
    if notes is None:
        return None
    out = notes
    for src, dst in _NOTES_OCR_FIXES:
        out = out.replace(src, dst)
    return out


def main() -> None:
    rows = [json.loads(line) for line in RECONCILED.read_text(encoding="utf-8").splitlines() if line.strip()]

    ocr_applied: list[tuple[str, str]] = []
    overrides_applied: list[tuple[str, str, object, object]] = []

    for row in rows:
        tid = row["tomb_id"]
        # Schema-uniformity backfill: ensure every row carries
        # `co_occupant_roles: []` before the per-chunk correction loop runs
        # (so that `CHUNK3_CORRECTIONS`'s `co_occupant_roles` overrides
        # treat the default as `[]`, not as absent).
        _ensure_co_occupant_roles_default(row)

        original_notes = row.get("notes_from_pm")
        fixed_notes = _apply_ocr_fixes(original_notes)
        fixed_notes = _apply_chunk2_notes_ocr_fixes(fixed_notes, tid)
        if fixed_notes != original_notes:
            row["notes_from_pm"] = fixed_notes
            ocr_applied.append((tid, original_notes or ""))

        for corrections in _ALL_CHUNK_CORRECTIONS:
            for (override_tid, field), spec in corrections.items():
                if override_tid == tid:
                    previous = row.get(field)
                    # Skip no-op corrections (value already matches) so the audit
                    # trail in `merge-disagreements.txt` does not accrue
                    # misleading `X → X` entries on subsequent runs.
                    if previous == spec["value"]:
                        continue
                    row[field] = spec["value"]
                    overrides_applied.append((tid, field, previous, spec["value"]))

    RECONCILED.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows) + "\n",
        encoding="utf-8",
    )

    if ocr_applied or overrides_applied:
        existing = DIFF.read_text(encoding="utf-8") if DIFF.exists() else ""
        # Strip any prior auto-appended audit-trail section so the merge
        # diff stays byte-identical across consecutive `fix_rows.py` runs.
        marker_idx = existing.find(_AUDIT_MARKER)
        if marker_idx >= 0:
            existing = existing[:marker_idx]
        annotations: list[str] = []
        annotations.append(_AUDIT_MARKER)
        annotations.append("============================================\n")
        if ocr_applied:
            annotations.append("\nOCR-drift fixes (Roman-numeral restore in notes_from_pm):\n")
            for tid, original in ocr_applied:
                annotations.append(f"  {tid}: {original}\n")
        if overrides_applied:
            annotations.append("\nReviewer-cited row corrections:\n")
            for tid, field, before, after in overrides_applied:
                annotations.append(
                    f"  {tid}.{field}: {json.dumps(before, ensure_ascii=False)} "
                    f"→ {json.dumps(after, ensure_ascii=False)}\n"
                )
        DIFF.write_text(existing + "".join(annotations), encoding="utf-8")

    print(f"Rows: {len(rows)}")
    print(f"OCR-drift fixes applied: {len(ocr_applied)}")
    print(f"Reviewer corrections applied: {len(overrides_applied)}")


if __name__ == "__main__":
    main()
