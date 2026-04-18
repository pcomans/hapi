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
        None,
        "Baud's PARENTÉ for ꜥnḫ-m-ꜥ-Rꜥ (physical p. 423) reports Strudwick's "
        "hypothesis verbatim: 'la mère Mr.s-ꜥnḫ III [76] est hypothétique "
        "d'après Strudwick.' Baud himself is reporting another scholar's "
        "hypothesis, not asserting — 'hypothétique d'après Strudwick' is "
        "Strudwick's guess, and Baud's own commentary raises doubts ('est-ce "
        "l'appartenance à une autre branche par sa mère?'). Two reviewer "
        "passes conflicted on the right field value here: first pass wrote "
        "'(per Baud)' reading Baud as endorser, second pass pushed back "
        "noting Baud is questioning the hypothesis, not affirming it. "
        "Null is the reading most honest to the primary source — the "
        "mother-connection in the structured field is not attested by Baud "
        "himself; notes_from_baud already captures Strudwick's hypothesis "
        "verbatim for the reader's benefit.",
    ),
    (
        "baud-37",
        "name_anglicised",
        "Ankhesenmeryre I",
        "'Ankhesenmerire' directly transliterates the French-form Mrjj-Rꜥ; "
        "the conventional English form in modern Egyptological scholarship "
        "is 'Ankhesenmeryre' (Dodson-Hilton) or 'Ankhesenpepi' (Wikipedia, "
        "some museum catalogs, following the double-name attestation). "
        "Provisional pending Phase A reconciliation against pharaoh.se's "
        "Conventional English Display Form — if pharaoh.se canonicalises to "
        "'Ankhesenpepi I', the Phase A curation step will update the "
        "authority accordingly. 'Ankhesenmeryre' is the reviewer's "
        "recommended default until that reconciliation runs.",
    ),
    (
        "baud-38",
        "name_anglicised",
        "Ankhesenmeryre II",
        "Same provisional French-to-English choice as baud-37 — "
        "Ankhesenmerire → Ankhesenmeryre. Wikipedia's convention for this "
        "individual is 'Ankhesenpepi II'; either form is acceptable modern "
        "English-Egyptological usage. Preserves the naming-parallel with "
        "baud-37 (her predecessor of the same name). Phase A will "
        "reconcile the final form against pharaoh.se.",
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
        "to a chunk-2 prompt update for the vocab expansion. Same vocab "
        "gap applies to baud-10, baud-25, baud-34 — see README § 'Known "
        "gaps'.",
    ),
    (
        "baud-20",
        "roles",
        ["steward of the queen"],
        "2nd-pass egyptologist-reviewer correction. Baud's (b) monument "
        "block places Jmnj at queen Wḏbt-n.j's funerary complex, and his "
        "TITRES carry `jmꜣḫw ḫr ḥnwt.f` ('honored-by-his-mistress', where "
        "ḥnwt = mistress/queen) — together establishing queen-attached "
        "service personnel. Majority-vote left roles empty despite the "
        "attested queen-attachment. `steward of the queen` is in the "
        "seeded controlled vocabulary.",
    ),
    (
        "baud-36",
        "children_names",
        ["Néferkarê"],
        "2nd-pass egyptologist-reviewer correction. Baud's TITRES "
        "(physical p. 427) include `mwt nswt Ḏd-ꜥnḫ-Nfr-kꜣ-Rꜥ` — a "
        "cartouche-scoped 'mother of king Neferkare' title explicitly "
        "attested in the pyramid-mortuary-cult formula. The `(probable)` "
        "hedge on majority-voted `children_names` is wrong when the "
        "mother-of-Neferkare relation is attested in an own-titulary "
        "inscription, not inferred. Hedge removed per README § "
        "'Interpretive-facts caveat' — title-attested kinship is "
        "asserted bare.",
    ),
]


# Chunk-1 backfill: the `steward of the king's children` role
# (`jmj-r prw msw nswt` and equivalents) was surfaced by the PR #53 reviewer
# pass but deferred from chunk 1 because the controlled vocabulary had not
# yet accepted it. Chunk 2 adds the role to the vocab (`README.md` § Schema,
# `prompt-chunk-2.md`, `test_roles_vocabulary_is_bounded`), so chunk 1's
# four affected rows can be backfilled here in the chunk-2 PR. Kept in a
# separate list so the audit trail distinguishes reviewer-flagged
# chunk-1 errors (CHUNK1_CORRECTIONS) from vocab-expansion backfills.
CHUNK1_BACKFILL: list[tuple[str, str, object, str]] = [
    (
        "baud-10",
        "roles",
        ["steward of the king's children"],
        "TITRES includes `jmj-r pr ... nwt msw nswt` (steward of the "
        "king's children's house). Chunk 1 left roles empty pending vocab "
        "expansion; chunk 2 adds `steward of the king's children` to the "
        "controlled vocabulary.",
    ),
    (
        "baud-25",
        "roles",
        ["steward of the king's children"],
        "TITRES includes `jmj-r sbꜣ n msw nswt nw ẖt.f` (overseer of the "
        "door/schooling of the king's own-body children). `msw nswt`-scoped "
        "administrative title maps to `steward of the king's children` in "
        "the expanded vocab.",
    ),
    (
        "baud-34",
        "roles",
        ["steward of the king's children"],
        "TITRES includes `jmj-r prw msw nswt` (overseer of the houses of "
        "the king's children) — the canonical form of this role. Chunk 1 "
        "left roles empty pending vocab expansion.",
    ),
    (
        "baud-40",
        "roles",
        [
            "priest of the king",
            "priest of the royal pyramid",
            "steward of the king's children",
        ],
        "TITRES includes `jmj-r prw msw nswt (2)`. Chunk-1 correction "
        "already set roles to `[priest of the king, priest of the royal "
        "pyramid]`; chunk 2 appends `steward of the king's children` now "
        "that the vocab accepts it.",
    ),
]


# Chunk-2 corrections from the egyptologist-reviewer pass.
CHUNK2_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "baud-42",
        "roles",
        ["king's son"],
        "Baud's TITRES for Ḥꜣ-w(j)-kꜣ.j (physical p. 50) gives `[zꜣ nswt] "
        "nj ẖt.f mrr jt.f`. The `smsw` (eldest) glyph is absent; "
        "`mrr jt.f` / `nj ẖt.f` alone attest body-son, not eldest. The "
        "`king's eldest son of his body` vocab term specifically requires "
        "`smsw`. Removed; `king's son` remains as the bare direct attestation.",
    ),
    (
        "baud-43",
        "roles",
        ["priest of the king", "priest of the royal pyramid"],
        "Baud's TITRES for Wꜣš-Ptḥ (physical p. 50) gives `jmj-r ḥmw-kꜣ "
        "(nw zꜣt nswt...?)` — overseer of the ka-priests of a king's "
        "daughter (Ḥꜥ-mrr-Nbtj II per notes), NOT a queen. Majority-vote "
        "mapped this to `steward of the queen` which is semantically wrong "
        "(queen ≠ king's daughter). Dropped the role; the daughter-scoped "
        "administrative title has no clean vocab home and is preserved in "
        "`titles_from_baud`.",
    ),
    (
        "baud-55",
        "father_name",
        None,
        "Baud's PARENTÉ for Bꜣ-bꜣ.f II (physical p. 58–59) reports Reisner's "
        "hypothesis — 'Fils de Dwꜣ-n-Rꜥ selon Reisner … idée reprise "
        "hypothétiquement par PM 155 … Strudwick … ne remet pas vraiment "
        "en question l'hypothèse'. Baud himself does not endorse. Same "
        "pattern as chunk-1 baud-33 (Strudwick hypothesis): structured "
        "field is null, notes_from_baud already captures the hypothesis "
        "verbatim for readers.",
    ),
    (
        "baud-57",
        "roles",
        [
            "king's son",
            "king's eldest son of his body",
            "priest of the king",
            "priest of the royal pyramid",
        ],
        "Baud's TITRES for Bꜣ-kꜣ.j (physical p. 60–61) opens with "
        "`ḥm-nṯr Rꜥ-ḏd.f` — priest of the royal cult of Rêdjedef. Same "
        "additive-role pattern as chunk-1 baud-28 / baud-40: `ḥm-nṯr "
        "<royal-cartouche>` attests `priest of the royal pyramid`. "
        "Majority-vote omitted this role; the other three were preserved.",
    ),
    (
        "baud-62",
        "roles",
        ["overseer of the king's ornaments"],
        "Baud's TITRES for Pr-sn* (physical p. 64) are `jmj-r jzwj ḥkr "
        "nswt`, `jmj-r mrḫt ḥkr nswt`, `jmj-r ḥkr nswt`, `šḏ pr-ꜥꜣ`. "
        "`ḥkr nswt` is the king's ornaments/jewelry cult-institution, NOT "
        "the treasury (`pr-ḥḏ`). Majority-vote mapped to the treasury "
        "vocab term. Replaced with `overseer of the king's ornaments` "
        "(new vocab term added in this chunk). Baud explicitly notes "
        "(p. 447 n. 53) that `pr-ꜥꜣ` is associated with `šḏ`, not `ḥkr "
        "nswt` — so the three are three different institutions.",
    ),
    (
        "baud-64",
        "roles",
        ["steward of the king's mother"],
        "Baud's TITRES for Pḥ-r-nfr* (physical p. 66) includes `ḥqꜣ ḥwt-"
        "ꜥꜣt ḥwt Mr.s-ꜥnḫ` — ruler of the great estate of the domain of "
        "Meresankh (the king's mother per notes_from_baud). This is an "
        "estate administrator, not a priest. Majority-vote mis-coded as "
        "`priest of the king's mother`. Replaced with the new vocab term "
        "`steward of the king's mother` — parallel to `steward of the "
        "queen` and `steward of the king's children`.",
    ),
    (
        "baud-66",
        "spouse_names",
        ["Mrwt Zšzšt (?)"],
        "Baud's PARENTÉ for Ptḥ-m-hꜣt Ptḥj (physical p. 67) reads "
        "'Époux (?) de la fille royale Mrwt Zšzšt [82]' — the literal "
        "question mark is Baud's own hedge, not a transcription artifact. "
        "Majority-vote dropped it. Preserved per README hedge-level 4 "
        "(`X (?)` = legible sign, reading/attribution disputed).",
    ),
    (
        "baud-68",
        "roles",
        [
            "sem priest",
            "king's son-in-law",
            "priest of the king",
            "high priest of Ptah",
        ],
        "Baud's TITRES for Ptḥ-špss (physical p. 68–69) includes `wr ḫrp "
        "ḥmwwt` — the canonical title of the High Priest of Ptah at "
        "Memphis. This is Ptahshepses of Saqqara whose biography Baud "
        "cites (Urk. I 51–53). Majority-vote omitted the role; no "
        "existing vocab term covered it, so `high priest of Ptah` added "
        "to the controlled vocabulary in this chunk.",
    ),
    # Second-pass egyptologist-reviewer on PR #57 surfaced a systemic
    # over-extraction: seven rows carry `king's eldest son of his body`
    # when TITRES has either `smsw` or `nj ẖt.f` but not both. The vocab
    # term (per the chunk-2 baud-42 correction) specifically requires both
    # elements. Applying the same rule consistently — body-son without
    # smsw = `king's son` only; smsw without nj ẖt.f = `king's son` only.
    (
        "baud-41",
        "roles",
        ["king's son"],
        "PDF p. 432: TITRES `zꜣ nswt`, `zꜣ nswt smsw`, `tz nḫn(?)`. "
        "`smsw` present, `nj ẖt.f` absent — same rule as baud-42. Drop "
        "`king's eldest son of his body` (requires both elements).",
    ),
    (
        "baud-44",
        "roles",
        ["king's daughter"],
        "Wꜥtt-ḫt-ḥr Zšzšt (PDF p. 434) is a king's daughter (Téti) married "
        "to the vizier Mererouka, NOT to a king. Majority-vote added "
        "`king's wife` and `priest of the king's wife`, but her `ḥmt-nṯr "
        "Ḥwt-Ḥr` / `ḥmt-nṯr Nt` titles are priestess-of-GODDESS, not of a "
        "queen's cult — both roles are fabricated. Spouse Mrr-wj-kꜣj is "
        "a vizier, not a king. Dropped both.",
    ),
    (
        "baud-55",
        "roles",
        ["vizier", "king's son"],
        "PDF p. 442 TITRES: `zꜣ nswt`, `zꜣ nswt nj ẖt.f`, `smr wꜥtj n jt.f`. "
        "No `smsw` anywhere. Same rule as baud-42: drop `king's eldest son "
        "of his body`. (father_name correction already in this chunk.)",
    ),
    (
        "baud-60a",
        "father_name",
        None,
        "PDF p. 446 [60a] Pn-mdw has NO PARENTÉ section — Baud gives only "
        "DATATION (Pépi Iᵉʳ, based on the monument location in the "
        "complex) and a DIVERS name-reading caveat. Promoting a "
        "reign-date to a filiation claim is fabrication. The graffito's "
        "place of attestation is in notes; structured parent field is null.",
    ),
    (
        "baud-60a",
        "roles",
        ["king's son"],
        "PDF p. 446: only title is `zꜣ nswt smsw`. `smsw` present, "
        "`nj ẖt.f` absent — same rule as baud-42.",
    ),
    (
        "baud-67",
        "roles",
        ["vizier", "king's son", "king's son-in-law"],
        "Ptahshepses of Abusir, PDF p. 452. TITRES carries `zꜣ nswt nj "
        "ẖt.f` only; no `smsw`. Famously NOT born royal (married into "
        "the royal family via the king's daughter Ḥꜥ-mrr-Nbtj II). "
        "`king's eldest son of his body` unattested and historically wrong.",
    ),
    (
        "baud-71",
        "roles",
        ["king's son"],
        "PDF p. 457 TITRES: `zꜣ nswt`, `zꜣ nswt nj ẖt.f`, "
        "`zꜣ nsw[t] nj ẖt.f [mr]jj.f`. No `smsw`. Same rule as baud-42.",
    ),
    (
        "baud-73",
        "roles",
        ["king's son"],
        "PDF p. 458–459: TITRES `zꜣ nswt (2)`, `zꜣ nswt nj ẖt.f`; no "
        "`smsw`. Also not a direct royal son — Baud makes him son of the "
        "zꜣt nswt Sḏjt [222]. `king's eldest son of his body` doubly "
        "unattested.",
    ),
    (
        "baud-76",
        "spouse_names",
        ["Rêkhaef (?)"],
        "PDF p. 461 PARENTÉ: 'on a proposé Rêkhaef' — Baud reports the "
        "proposal without endorsing. `(probable)` overstates his hedge; "
        "`(?)` matches Baud's `on a proposé` more honestly (hedge-level 4 "
        "per README).",
    ),
    (
        "baud-79",
        "roles",
        ["king's son"],
        "PDF p. 464: TITRES `zꜣ nswt nj ẖt.f` only. No `smsw`. "
        "Attribution rests on onomastics + Giza-East locality, not on "
        "an eldest-son title. Same rule as baud-42.",
    ),
    # Gemini Code Assist PR #57 suggested adding a `steward of the king's
    # children` entry for baud-69 (`smsw pr n jrj-pꜥt`). The
    # scope-accountability-enforcer flagged it as a vocab-integrity stretch:
    # `jrj-pꜥt` is a court rank (hereditary prince/noble), not `msw nswt`
    # ("king's children"). The chunk-1 backfill pattern applies specifically
    # to `msw nswt`-scoped titles. baud-69's `roles: []` is the honest
    # mapping. Deferred.
]


# Chunk-3 corrections.
CHUNK3_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "baud-85",
        "children_names",
        ["Kꜣ.j-wꜥb (probable)"],
        "Baud writes 'si la reconstitution de Smith est exacte' — Kꜣ.j-wꜥb "
        "is Smith's reconstruction that Baud reports (not endorses). "
        "`(per Baud)` over-promoted; `(probable)` matches the actual hedge.",
    ),
    (
        "baud-86",
        "roles",
        ["king's daughter"],
        "TITRES has `ḥmt-nṯr Ḫwfw, ḥmt-nṯr Nt, ḥmt-nṯr Ḥwt-Ḥr` on a king's "
        "daughter — priestess of royal cult of Khoufou plus goddess-cults "
        "(Neith, Hathor). Majority-vote added `priest of the king` but the "
        "title is female royal-cult priestess, not service-personnel "
        "`priest of the king`. Role vocab intends the latter. Dropped.",
    ),
    (
        "baud-117",
        "roles",
        ["king's son", "vizier"],
        "Nfr-mꜣꜥt I's TITRES has `zꜣ nswt smsw` — `smsw` is present but "
        "`nj ẖt.f` is absent. Per the chunk-2 baud-42 rule (vocab term "
        "`king's eldest son of his body` requires BOTH elements), drop "
        "the role. `king's son` remains as the bare attestation; "
        "`vizier` from other titulary preserved.",
    ),
    (
        "baud-87",
        "father_name",
        "Ptḥ-špss (probable)",
        "Baud's PARENTÉ reports Schmitz's supposition: 'Schmitz … ont "
        "amené à supposer qu'il s'agit … d'une fille du couple Ptḥ-špss "
        "et Ḫꜥ-mrr-Nbtj'. `(per Baud)` over-promotes a reported "
        "hypothesis; `(probable)` matches Baud's stance.",
    ),
    (
        "baud-87",
        "mother_name",
        "Ḫꜥ-mrr-Nbtj (probable)",
        "Same Schmitz-supposition as baud-87 father_name. `(per Baud)` → "
        "`(probable)` for consistency with how Baud hedges.",
    ),
    (
        "baud-93",
        "roles",
        ["king's daughter"],
        "Same pattern as baud-86: TITRES has `ḥmt-nṯr Ḫwfw, ḥmt-nṯr "
        "Ḥwt-Ḥr, ḥkrt nswt` on a king's daughter — female royal-cult "
        "priestess plus goddess-cult. `priest of the king` is the "
        "service-personnel vocab; doesn't fit a female royal's own "
        "titulary. Dropped.",
    ),
    (
        "baud-94",
        "father_name",
        "Rêkhaef (probable)",
        "Baud's PARENTÉ says the Rêkhaef filiation 'est motivée par le "
        "secteur' but `on peut néanmoins en douter`. Baud reports the "
        "hypothesis and hedges it; `(per Baud)` over-promotes. "
        "`(probable)` is the most generous honest mapping.",
    ),
    (
        "baud-92",
        "roles",
        ["steward of the king's mother"],
        "Gemini PR #58 review. TITRES has `ḥm pr mwt nswt` (servant of "
        "the house of the king's mother) — administrative/domestic, not "
        "priestly. `priest of the king's mother` vocab requires "
        "`ḥm-nṯr mwt nswt X`; this row only has `ḥm pr`. Dropped. "
        "`steward of the king's mother` retained (from `ḥqꜣ n mwt nswt "
        "Nj-mꜣꜥt-Ḥp`, genuinely administrative).",
    ),
    (
        "baud-94b",
        "titles_from_baud",
        [],
        "Gemini PR #58 review. baud-94b has NO TITRES rubric — the "
        "extracted `[zꜣt nswt] (probablement)` was inferred from prose, "
        "not a verbatim TITRES line. Per schema, `titles_from_baud` is "
        "the verbatim TITRES rubric only. Empty list is honest; roles "
        "already empty (deferred earlier).",
    ),
    (
        "baud-97",
        "roles",
        ["priest of the king's mother", "priest of the royal pyramid"],
        "TITRES includes `jmj-r ḥst pr-ꜥꜣ` — overseer of the STOREROOM "
        "(`ḥst`) of the great-house, NOT the treasury (`pr-ḥḏ`). "
        "`overseer of the treasury of pr-ꜥꜣ` was mis-applied by "
        "majority-vote. Dropped (no clean vocab fit for storeroom); the "
        "priest-of-royal-cult roles from `ḥm-nṯr Šzp-jb-Rꜥ` etc. retained.",
    ),
]


# Aggregation: every chunk's corrections list AND every backfill list must
# appear here. `test_all_corrections_includes_every_chunk_list` asserts
# module-level `CHUNK*` list attributes are all present — dropping one
# silently destroys its audit trail and the test fails loud.
CHUNK4_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "baud-123",
        "spouse_names",
        ["Ouserkaf (probable)"],
        "Egyptologist-reviewer PR #59: p.493 Grdseloff's hypothesis, "
        "explicitly 'conjecturale'. Baud reports but does not assert. "
        "`(per Baud)` over-promotes; `(probable)` matches Baud's hedge.",
    ),
    (
        "baud-123",
        "children_names",
        ["Sahourê (probable)"],
        "Egyptologist-reviewer PR #59: p.494 multi-author hypothesis "
        "(Callender/Jánosi/Labrousse) Baud relays. Same pattern as spouse; "
        "`(per Baud)` → `(probable)`.",
    ),
    (
        "baud-126",
        "father_name",
        None,
        "Gemini PR #59: notes explicitly say Baud 'ne s'engage pas' on the "
        "filiation. Per hedge-level 6, `null` is the honest mapping when "
        "Baud reports a hypothesis without endorsing it.",
    ),
    (
        "baud-128",
        "roles",
        ["king's daughter"],
        "Egyptologist-reviewer PR #59: `ḥmt-nṯr Snfrw` on a king's daughter "
        "is royal-cult priestess titulary, not service-personnel `priest "
        "of the king`. Same pattern as chunk-3 baud-86/93; consistent "
        "resolution across chunks.",
    ),
    (
        "baud-133",
        "mother_name",
        "Nt [136] (probable)",
        "Egyptologist-reviewer PR #59: p.504 Seipel's localisation-based "
        "hypothesis Baud relays. `(per Baud)` → `(probable)`.",
    ),
    (
        "baud-136",
        "children_names",
        ["Merenrê II (probable)"],
        "Egyptologist-reviewer PR #59: pp.506-507 heavily hedged "
        "(Goedicke's proposal, 'sauf extraordinaire longévité... s'il "
        "s'agit de Nmtj-m-zꜣ.f'). `(per Baud)` → `(probable)`.",
    ),
    (
        "baud-137",
        "roles",
        ["king's son", "priest of the royal pyramid"],
        "Gemini PR #59: TITRES has `ḥm-nṯr ḫnt Ḫꜥ-Snfrw` — priest of "
        "Sneferu's pyramid (`Ḫꜥ-Snfrw` = pyramid cartouche). Adds "
        "`priest of the royal pyramid`. Drops spurious `overseer of "
        "scribes of pr-ꜥꜣ` (unattested — actual title is `zš ḫrjt-ꜥ "
        "nswt`, a different administrative office).",
    ),
    (
        "baud-143",
        "roles",
        ["king's son", "vizier"],
        "Gemini + egyptologist PR #59: `zꜣ nswt nj ẖt.f` and `smsw jzt` "
        "are SEPARATE titles. `smsw jzt` is a chamber-office title "
        "(`jzt` = office/chamber), NOT kinship. The `king's eldest son "
        "of his body` vocab term requires `smsw` AND `nj ẖt.f` in the "
        "SAME title string. Drop; `vizier` retained.",
    ),
    (
        "baud-151",
        "roles",
        ["king's son", "vizier"],
        "Egyptologist-reviewer PR #59: same pattern as baud-143. "
        "`zꜣ nswt nj ẖt.f` and `smsw jzt` present but not conjoined; "
        "`smsw` sits on the chamber title only. Drop `king's eldest son "
        "of his body`; `vizier` retained.",
    ),
    (
        "baud-155",
        "spouse_names",
        [],
        "Egyptologist-reviewer PR #59: the list item "
        "`Mr.s-ꜥnḫ II [75] (hypothèse controversée)` puts a French "
        "parenthetical-hedge inside the value, which breaks downstream "
        "Phase-A matching. Baud himself labels the marriage 'controversée'. "
        "Empty list is honest; notes_from_baud already captures the "
        "hypothesis verbatim.",
    ),
    (
        "baud-158",
        "roles",
        ["king's son"],
        "Gemini + egyptologist PR #59: Hordjedef's TITRES has only "
        "`zꜣ nswt nj ẖt.f` — `smsw` is not attested anywhere. First-born "
        "status is later-literary (Westcar Papyrus), not OK titular. "
        "Drop `king's eldest son of his body`.",
    ),
]


# Chunk-5 corrections from egyptologist + Gemini reviewer passes.
# Systemic pattern this chunk: female figures with `zꜣt nswt nt ẖt.f (smst)`
# were mechanically assigned `king's eldest son of his body` (male-coded
# vocab term). No equivalent female-coded role exists; dropping is the
# honest fix.
CHUNK5_CORRECTIONS: list[tuple[str, str, object, str]] = [
    (
        "baud-163",
        "roles",
        ["queen", "king's wife", "king's daughter"],
        "Egyptologist PR #60: TITRES has `ḥmt-nṯr Bꜣpf, Tꜣzp(t.f), "
        "Ḏḥwtj` — priesthoods of GODS only (Bapef, Tazepf, Thoth), NOT "
        "of queens. `priest of the king's wife` requires `ḥmt-nṯr <queen-"
        "cartouche>`; dropped.",
    ),
    (
        "baud-164",
        "roles",
        ["king's daughter"],
        "Egyptologist + Gemini PR #60: female figure (Ḥtp-ḥr.s). "
        "`king's eldest son of his body` is male-coded vocab — dropped. "
        "`priest of the king` also dropped: `ḥmt-nṯr Snfrw (?)` is her "
        "own female royal-cult priestess titulary, not service-personnel "
        "priesthood (same rule as chunks-3/4 baud-86/93/128).",
    ),
    (
        "baud-172",
        "roles",
        ["queen", "king's wife", "king's daughter"],
        "Egyptologist PR #60: Ḫꜥ-mrr-nbtj II is female — her `zꜣt nswt "
        "nt ẖt.f smst` is 'eldest daughter', not son. `king's eldest son "
        "of his body` male-coded; dropped.",
    ),
    (
        "baud-173",
        "roles",
        ["king's daughter"],
        "Egyptologist PR #60: `ḥkrt nswt wꜥtt` = 'sole royal ornament', "
        "an honorific/service designation on HERSELF, NOT an `jmj-r "
        "ḥkrwt` overseer role. Chunk-2 vocab intended the overseer "
        "pattern. Dropped; baud-167 (same title, no role) is the "
        "consistent precedent.",
    ),
    (
        "baud-187",
        "roles",
        ["queen", "king's mother", "king's wife"],
        "Egyptologist PR #60: Ḫnt-kꜣw.s II's only `ḥmt-nṯr` titles are "
        "of gods (Bapef, Tazepf, Thoth). `mrt Nfr-jr-kꜣ-Rꜥ rꜥ nb` is an "
        "epithet, not a priesthood. `priest of the king` dropped; her "
        "queen/mother/wife roles from the kinship titulary remain.",
    ),
    (
        "baud-188",
        "roles",
        ["king's daughter"],
        "Egyptologist + Gemini PR #60: female `zꜣt nswt nt ẖt.f`; no "
        "`smst` marker. `king's eldest son of his body` doubly wrong "
        "(male-coded vocab, no eldest marker). Dropped.",
    ),
    (
        "baud-189",
        "roles",
        ["king's daughter"],
        "Egyptologist PR #60: female `zꜣt nswt nt ẖt.f`; no eldest "
        "marker. Same rule violation as baud-188. `king's eldest son "
        "of his body` dropped.",
    ),
    (
        "baud-190",
        "roles",
        ["king's daughter"],
        "Egyptologist PR #60: female with `zꜣt nswt nt ẖt.f smst` — "
        "eldest daughter, not son. Male-coded vocab mis-applied. Dropped.",
    ),
    (
        "baud-191",
        "roles",
        ["king's son"],
        "Egyptologist + Gemini PR #60: Ḫntj-r-kꜣ.j's only title is "
        "`zꜣ nswt nj ẖ<t>.f` — no `smsw`. Rule-8 AND-test fails "
        "(requires BOTH smsw and nj ẖt.f). Dropped `king's eldest son "
        "of his body`; `king's son` retained.",
    ),
    (
        "baud-198",
        "roles",
        ["king's daughter"],
        "Egyptologist + Gemini PR #60: Ḥkrt-Nbtj, female, titles `zꜣt "
        "nswt nt ẖt.f (var. mrt.f)` — no eldest marker. Male-coded "
        "vocab wrong on two counts. Dropped.",
    ),
]


ALL_CORRECTIONS: list[list[tuple[str, str, object, str]]] = [
    CHUNK1_CORRECTIONS,
    CHUNK1_BACKFILL,
    CHUNK2_CORRECTIONS,
    CHUNK3_CORRECTIONS,
    CHUNK4_CORRECTIONS,
    CHUNK5_CORRECTIONS,
]

SPOT_CORRECTIONS: list[tuple[str, str, object, str]] = sum(ALL_CORRECTIONS, [])

# Guard against accidental `(baud_id, field)` duplicates across correction
# lists — a duplicate silently stomps the earlier value based on list
# order. Today `baud-40 / roles` is intentionally in both
# `CHUNK1_CORRECTIONS` and `CHUNK1_BACKFILL` (the backfill appends
# `steward of the king's children` to the chunk-1 corrected list); the
# `_ALLOWED_DUPLICATES` allowlist acknowledges this. Any other
# accidental duplicate fails loud.
_ALLOWED_DUPLICATES: frozenset[tuple[str, str]] = frozenset(
    {("baud-40", "roles")}
)
_seen: dict[tuple[str, str], int] = {}
for _baud_id, _field, _, _ in SPOT_CORRECTIONS:
    _key = (_baud_id, _field)
    _seen[_key] = _seen.get(_key, 0) + 1
    if _seen[_key] > 1 and _key not in _ALLOWED_DUPLICATES:
        raise ValueError(
            f"Duplicate SPOT_CORRECTIONS entry for {_key!r}; "
            f"later value silently overrides. Add to _ALLOWED_DUPLICATES "
            f"if intentional, or merge the two entries."
        )
del _seen, _baud_id, _field, _key


def main() -> None:
    rows = [json.loads(line) for line in RECONCILED.read_text().splitlines() if line.strip()]

    # Pass 1: deterministic transliteration normalization across every row.
    rows = [_normalise_transliteration(r) for r in rows]

    # Pass 2: LLM-reviewer spot corrections.
    #
    # The log must describe the *state* of reconciled.jsonl, not the *delta*
    # from the previous run. On a second run every `old_val == new_val`, so a
    # delta-style log would incorrectly report "no overrides applied" while
    # the file on disk reflects all the applied overrides. Instead: always
    # log every SPOT_CORRECTION entry, showing the rationale and the current
    # value. `applied_count` tracks how many rows actually changed this run
    # for the terminal "Applied N overrides" line (0 on a re-run is
    # correct — nothing changed — but the disk log still describes the
    # complete override set).
    override_log: list[str] = []
    applied_count = 0
    for baud_id, field, new_val, rationale in SPOT_CORRECTIONS:
        row = next((r for r in rows if r["baud_id"] == baud_id), None)
        if row is None:
            raise KeyError(f"No row with baud_id={baud_id!r}")
        old_val = row.get(field)
        if old_val != new_val:
            applied_count += 1
            override_log.append(
                f"- {baud_id}: {field} corrected ({rationale})\n"
                f"    was: {json.dumps(old_val, ensure_ascii=False)}\n"
                f"    now: {json.dumps(new_val, ensure_ascii=False)}"
            )
            row[field] = new_val
        else:
            # Row already reflects the override — still emit a log entry
            # so the on-disk audit trail describes the full committed
            # override set, not just this run's deltas.
            override_log.append(
                f"- {baud_id}: {field} corrected ({rationale})\n"
                f"    value: {json.dumps(new_val, ensure_ascii=False)}"
            )

    RECONCILED.write_text(
        "\n".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows
        )
        + "\n"
    )

    existing_diff = DIFF.read_text()
    marker = "LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED"
    # Strip the previous LLM-APPLIED OVERRIDES section in-place so the
    # rewritten section replaces (not duplicates) it. Use the bare marker
    # as the split point rather than `\n\n{marker}` — the latter would
    # silently fail to match and produce a duplicate section if the file
    # were ever manually edited to use a different whitespace separator.
    # The `rstrip()` handles trailing whitespace before the marker.
    idx = existing_diff.find(marker)
    if idx != -1:
        existing_diff = existing_diff[:idx].rstrip()
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

    print(f"Applied {applied_count} override(s) this run ({len(override_log)} total in log).")
    print(f"Updated {RECONCILED.relative_to(RECONCILED.parents[4])}")
    print(f"Updated {DIFF.relative_to(DIFF.parents[4])}")


if __name__ == "__main__":
    main()
