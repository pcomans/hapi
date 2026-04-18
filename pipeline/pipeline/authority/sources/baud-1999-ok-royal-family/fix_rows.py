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
    # Gemini Code Assist PR #57 suggested adding a `steward of the king's
    # children` entry for baud-69 (`smsw pr n jrj-pꜥt`). The
    # scope-accountability-enforcer review flagged this as a vocab-
    # integrity stretch: `jrj-pꜥt` is a court rank (hereditary
    # prince/noble), not `msw nswt` ("king's children"). The chunk-1
    # backfill pattern applies specifically to `msw nswt`-scoped titles;
    # extending it to `jrj-pꜥt` would conflate distinct title elements.
    # baud-69's `roles: []` is the honest mapping — `smsw pr` is an
    # administrative-household title with no clean vocab home, and
    # `jrj-pꜥt` scoping deserves its own vocab term when a future chunk
    # attests it more broadly. Deferred.
]


# Aggregation: every chunk's corrections list AND every backfill list must
# appear here. `test_all_corrections_includes_every_chunk_list` asserts
# module-level `CHUNK*` list attributes are all present — dropping one
# silently destroys its audit trail and the test fails loud.
ALL_CORRECTIONS: list[list[tuple[str, str, object, str]]] = [
    CHUNK1_CORRECTIONS,
    CHUNK1_BACKFILL,
    CHUNK2_CORRECTIONS,
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
