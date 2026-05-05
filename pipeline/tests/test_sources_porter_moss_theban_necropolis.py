"""Structural value-assertion tests for Porter & Moss Vol I source extract.

Per CLAUDE.md rule 5: every populated field on every fixture-class row is
asserted, not just the field the test class is "themed" around.

Chunk 1 covers KV1–KV10 (PM I.2 § I.A "Tombs", printed p.495–518). Future
chunks (KV11–KV65, QV, TT...) extend `EXPECTED_TOMB_IDS` and add per-chunk
value-assertion tests; the structural tests below are forward-compatible.

Note on null `dynasty` and BCE-date fields: per CLAUDE.md rule 1 (every
authoritative fact must trace to a committed raw source) and rule 7
(authority lookup, not hard-coded), PM headwords don't print dynasty or
BCE dates — those fields stay null at this extraction stage and Phase A
king-authority enrichment (against pharaoh.se) fills them. The test suite
therefore asserts these fields are null on every chunk-1 row, not that
they carry expected dynasty values.
"""

from __future__ import annotations

import importlib.util
import json
import re
from functools import lru_cache
from pathlib import Path

SOURCE_DIR = (
    Path(__file__).parent.parent
    / "pipeline"
    / "authority"
    / "sources"
    / "porter-moss-theban-necropolis"
)
JSONL = SOURCE_DIR / "reconciled.jsonl"

EDITION_PM_I2 = "PM I.2 2nd ed. 1964"
EDITION_PM_I1 = "PM I.1 2nd ed. 1960"

# Chunk-1 (KV1–KV10), chunk-2 (KV11–KV20), chunk-3 (KV22–KV46 sparse) are
# the landed chunks. Extend as follow-up chunk PRs land. `EXPECTED_TOMB_IDS`
# is the union — row-count and ID-coverage tests reference it so they stay
# correct as the source grows.
#
# Absence patterns in PM I.2 § I.A:
# - KV21 is absent (jump from KV20 to KV22) — chunk-2 holds 10 rows.
# - KV24–KV33, KV37, KV40, KV41, KV44 are absent from chunk-3's range —
#   PM I.2 (1964) did not catalogue these as inscribed royal tombs. Chunk-3
#   holds 11 rows: KV22, 23, 34, 35, 36, 38, 39, 42, 43, 45, 46.
CHUNK1_TOMB_IDS: frozenset[str] = frozenset(
    {f"KV{n}" for n in range(1, 11)}
)
CHUNK2_TOMB_IDS: frozenset[str] = frozenset(
    {f"KV{n}" for n in range(11, 21)}
)
CHUNK3_TOMB_IDS: frozenset[str] = frozenset(
    {"KV22", "KV23", "KV34", "KV35", "KV36", "KV38", "KV39", "KV42",
     "KV43", "KV45", "KV46"}
)
# Chunk-4: KV47-KV57 sparse. KV49-KV54 and KV58-KV61 absent from PM I.2
# § I.A (PM jumps 48 → 55, 57 → 62). KV62 Tutankhamun is deferred to a
# dedicated chunk 5 because PM's KV62 entry spans 17 printed pages and
# warrants its own extraction PR.
CHUNK4_TOMB_IDS: frozenset[str] = frozenset(
    {"KV47", "KV48", "KV55", "KV56", "KV57"}
)
# Chunk-5: KV62 Tutʿankhamun as a standalone single-row chunk. User
# direction on chunk 5 scope: tomb-row granularity is sufficient for the
# museum-data-join use case; per-chamber sub-structure would inflate the
# schema past what downstream enrichment needs.
CHUNK5_TOMB_IDS: frozenset[str] = frozenset({"KV62"})
# Chunk-6: PM I.2 § I.A closure sweep, no rows added (KV63/KV64/KV65 are
# post-1964 discoveries, out of scope for PM I.2 2nd ed. 1964).
# Chunk-7: PM I.2 §§ II (South-West Valleys) + III.A/C/D (Dra' Abu el-Naga:
# Antef Cemetery Dyn XI, Tomb of Ahmose-Nefertari, Seventeenth Dynasty
# Cemetery). First chunk of this source with NON-NUMBERED tomb_ids — PM
# does not assign KV/QV/TT numbers to these sections, so tomb_id uses the
# descriptor convention `<PREFIX>-<Occupant>` where PREFIX is the valley
# code (`SWV` = South-West Valleys, `DAN` = Dra' Abu el-Naga). 18 rows.
CHUNK7_TOMB_IDS: frozenset[str] = frozenset({
    # § II.A Wadi Sikket Taqet Zaid (1)
    "SWV-HatshepsutSouth",
    # § II.B Wadi Qubbanet el-Qirud (2)
    "SWV-Neferure",
    "SWV-ThreePrincesses",
    # § III.A Antef Cemetery Dyn XI at El-Ṭaraf (3)
    "DAN-AntefSehertaui",
    "DAN-AntefWahankh",
    "DAN-MentuhotpSankhibtaui",
    # § III.C Tomb of Queen Ahmose-Nefertari (probably) (1)
    "DAN-AhmosiNefertere",
    # § III.D Seventeenth Dynasty Cemetery BURIALS (11)
    "DAN-Aqhor",
    "DAN-Ahhotep",
    "DAN-AhmosiHenutempet",
    "DAN-AhmosiSonOfSeqenenre",
    "DAN-AntefNubkheperre",
    "DAN-AntefSekhemreHeruhirmaet",
    "DAN-AntefSekhemreWepmaet",
    "DAN-KamosiWazkheperre",
    "DAN-MentuhotpIWifeOfDjhuti",
    "DAN-Neferhotep",
    "DAN-SebkemsafSekhemreShedtaui",
})
# Chunk-8 (PM I.2 § X.A Valley of the Queens — numbered tombs).
# PM 1964 2nd edition catalogues 20 numbered QV tombs; the rest of the
# QV1–QV80 range is absent from PM § X.A (QV1–32 never catalogued; QV34,
# 35, 37, 39, 41, 45, 48–50, 54, 56–59, 61–65, 67, 69, 70, 72, 76–80 are
# gaps). Chunk-7's descriptor infrastructure is not used here — QV uses
# the numbered form established in chunk 1.
CHUNK8_TOMB_IDS: frozenset[str] = frozenset({
    "QV33", "QV36", "QV38", "QV40", "QV42", "QV43", "QV44", "QV46",
    "QV47", "QV51", "QV52", "QV53", "QV55", "QV60", "QV66", "QV68",
    "QV71", "QV73", "QV74", "QV75",
})
# Chunk-9 (PM I.1 § I — TT1-TT10 Deir el-Medina core). FIRST chunk drawn
# from PM I.1; previous chunks 1-8 came from PM I.2. Every TT number in
# TT1..TT10 is present in PM I.1 § I — no gaps in this decade. 10 rows.
CHUNK9_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(1, 11)}
)
EXPECTED_TOMB_IDS: frozenset[str] = (
    CHUNK1_TOMB_IDS
    | CHUNK2_TOMB_IDS
    | CHUNK3_TOMB_IDS
    | CHUNK4_TOMB_IDS
    | CHUNK5_TOMB_IDS
    | CHUNK7_TOMB_IDS
    | CHUNK8_TOMB_IDS
    | CHUNK9_TOMB_IDS
)


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    return tuple(
        json.loads(line) for line in JSONL.read_text().splitlines() if line.strip()
    )


def _row(tomb_id: str) -> dict:
    hits = [r for r in _rows() if r["tomb_id"] == tomb_id]
    if len(hits) != 1:
        raise AssertionError(f"expected 1 row for {tomb_id}, got {len(hits)}")
    return hits[0]


# ---------------------------------------------------------------------------
# Structural tests (forward-compatible across chunks)
# ---------------------------------------------------------------------------


def test_row_count_matches_expected_set() -> None:
    """Exact-match row count to the union of all landed chunks' tomb IDs."""
    assert len(_rows()) == len(EXPECTED_TOMB_IDS), len(_rows())


def test_tomb_ids_match_expected_set() -> None:
    """Every expected tomb id is present, and no unexpected ids snuck in."""
    actual = {r["tomb_id"] for r in _rows()}
    assert actual == EXPECTED_TOMB_IDS, sorted(actual ^ EXPECTED_TOMB_IDS)


def test_tomb_id_is_unique() -> None:
    """No duplicate tomb_id in the committed extract."""
    ids = [r["tomb_id"] for r in _rows()]
    assert len(ids) == len(set(ids)), "duplicate tomb_id detected"


# `tomb_id` comes in two shapes:
#   - Numbered form for PM-numbered sections: `KV5`, `QV55`, `TT100`, with
#     optional single lowercase suffix for letter-suffix variants like `KV5a`.
#   - Descriptor form for non-numbered PM sections (chunk-7 onwards):
#     `<PREFIX>-<TitleCaseDescriptor>` where PREFIX is the valley code
#     (`SWV`, `DAN`, `DEB`, `ASS`, …) and the descriptor is a PM-faithful
#     TitleCase rendering of the occupant name + disambiguator.
#
# Cross-refs from descriptor rows back to numbered tombs use the numbered
# form (`["KV20"]` for SWV-HatshepsutSouth's See-also), so this regex also
# backs `test_shared_with_tombs_are_valid_tomb_ids`.
# Descriptor-prefix vocabulary is limited to the prefixes actually in use
# (chunks landed to date: SWV South-West Valleys, DAN Dra' Abu el-Naga).
# Future chunks extend this regex AS THEY LAND their first row — speculative
# pre-registration was removed after the retrospective code-review on PR #100
# flagged it as YAGNI. See `test_prefix_vocabulary_consistent` below which
# pins the descriptor regex against `merge.VALLEY_ORDER`.
_TOMB_ID_RE = re.compile(
    r"^(?:(?:KV|QV|TT)\d+[a-z]?|(?:SWV|DAN)-[A-Z][A-Za-z0-9]*)$"
)


def test_tomb_id_shape() -> None:
    """Every id matches one of two shapes:
       - numbered `(KV|QV|TT)\\d+[a-z]?`
       - descriptor `(SWV|DAN|…)-<TitleCase…>`
    Extend the regex as future chunks introduce new valley prefixes.
    """
    for r in _rows():
        assert _TOMB_ID_RE.match(r["tomb_id"]), r["tomb_id"]


def test_prefix_vocabulary_consistent() -> None:
    """The descriptor-prefix set in `merge.py::VALLEY_ORDER` must match the
    descriptor alternation in `_TOMB_ID_RE` exactly.

    Rule-3 fix on the retrospective code-review of PR #100: the prior
    sync-by-comment (`merge.py:50` said \"kept in sync with the test regex\")
    is a markdown rule, not enforcement — if a future chunk registers a
    prefix in one place but not the other, the failure mode is silent
    mis-sort or silent mis-validation. This test converts that drift into
    a CI failure.
    """
    merge_path = SOURCE_DIR / "merge.py"
    spec = importlib.util.spec_from_file_location("pm_theban_merge", merge_path)
    merge_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(merge_mod)

    # Extract BOTH alternations from `_TOMB_ID_RE` so the test reports
    # drift on either axis (numbered or descriptor) rather than silently
    # misattributing a numbered-prefix divergence as a descriptor
    # divergence. Gemini round-2 finding on PR #105: hardcoding
    # `numbered_prefixes = {"KV","QV","TT"}` in the test means that if a
    # future chunk adds a new numbered prefix to VALLEY_ORDER + the regex
    # but not this test, the set-diff shifts the new prefix into
    # `descriptor_prefixes` and the failure message points at the wrong
    # alternation.
    numbered_match = re.search(r"\(\?:([A-Z|]+)\)\\d\+", _TOMB_ID_RE.pattern)
    assert numbered_match, (
        "could not parse numbered alternation from _TOMB_ID_RE; "
        "regex shape changed — update this test to match"
    )
    regex_numbered = set(numbered_match.group(1).split("|"))

    descriptor_match = re.search(r"\(\?:([A-Z|]+)\)-\[A-Z\]", _TOMB_ID_RE.pattern)
    assert descriptor_match, (
        "could not parse descriptor alternation from _TOMB_ID_RE; "
        "regex shape changed — update this test to match"
    )
    regex_descriptors = set(descriptor_match.group(1).split("|"))

    regex_all = regex_numbered | regex_descriptors
    valley_order_set = set(merge_mod.VALLEY_ORDER)

    assert valley_order_set == regex_all, (
        f"VALLEY_ORDER {sorted(valley_order_set)} diverged from "
        f"_TOMB_ID_RE alternations (numbered={sorted(regex_numbered)}, "
        f"descriptor={sorted(regex_descriptors)}). Keep the two in sync "
        f"when adding a new chunk that introduces a new valley prefix."
    )


def test_occupant_name_has_no_underdot_h() -> None:
    """CLAUDE.md rule 3 deterministic-enforcement: the README's strip-ḥ
    policy on `occupant_name` (matchable name field) must be enforced by a
    test, not just by prose in the README / prompts / after-the-fact
    `CHUNK*_CORRECTIONS`.

    Chunk-8 retrospective code-review P1 finding: the retroactive ḥ-sweep
    across chunks 7 + 8 only happened because a Gemini comment on PR #101
    spotted the drift. A test like this converts the next drift into a CI
    failure on the first subagent run, not a 5-round review cycle.

    Underdot-K (`ḳ`) is preserved as a distinguishing radical per the
    README exception (e.g. chunk-7 `ʿAḳ-hor`); this test only asserts
    absence of underdot-H (U+1E25).
    """
    for r in _rows():
        name = r.get("occupant_name") or ""
        assert "ḥ" not in name and "Ḥ" not in name, (
            f"{r['tomb_id']}: occupant_name {name!r} contains underdot-H — "
            "the README's matchable-name-field convention strips ḥ → h. "
            "If PM's text genuinely requires preserving the diacritic here, "
            "the exception must be documented and this test updated."
        )


def test_required_fields_present_on_every_row() -> None:
    """Schema discipline: every row carries every key, even when null/empty.

    Sparse rows are valid (CLAUDE.md rule 4), but the KEY must be present
    so downstream Phase A code can assume the schema without `.get()` calls.
    """
    required = {
        "tomb_id",
        "theban_area",
        "occupant_name",
        "occupant_alt_names",
        "occupant_role",
        "dynasty",
        "sub_period",
        "date_bce_approx_start",
        "date_bce_approx_end",
        "location_sub_area",
        "discovery_year",
        "discoverer",
        "is_unfinished",
        "shared_with_tombs",
        "notes_from_pm",
        "source_citation",
        # PR A (audit-fix, 2026-05-02): added so tomb-nicknames and joint
        # occupants get their own honest schema slot. `occupant_alt_names`
        # is now exclusively for SAME-PERSON name variants (e.g. prenomens).
        "tomb_aliases",
        "co_occupants",
        # PR A round-2 (PR #169 egyptologist P1, 2026-05-02): explicit
        # flag for joint coordinate burials with no PM-marked principal
        # (SWV-ThreePrincesses); see test_is_joint_burial_flag_paired_
        # with_co_occupants for the contract.
        "is_joint_burial",
    }
    for r in _rows():
        missing = required - r.keys()
        assert not missing, (r["tomb_id"], sorted(missing))


def test_theban_area_constraint() -> None:
    """`theban_area` belongs to a known controlled vocabulary.

    Currently populated values across chunks 1–8: Valley of the Kings,
    Valley of the Queens, South-West Valleys, Dra' Abu el-Naga. Forward-
    compatible: extend the allowlist as future chunks add Deir el-Bahri,
    Asasif, Sheikh Abd el-Qurna, Khokha, Qurnet Mura'i, Deir el-Medina,
    Ramesseum, Medinet Habu (PM I.1 Appendix-D Theban sub-site list).
    """
    valid = {
        "Valley of the Kings",
        "Valley of the Queens",
        "South-West Valleys",
        "Dra' Abu el-Naga",
        "Deir el-Bahri",
        "Asasif",
        "Sheikh Abd el-Qurna",
        "Khokha",
        "Qurnet Mura'i",
        "Deir el-Medina",
        "Ramesseum",
        "Medinet Habu",
    }
    for r in _rows():
        assert r["theban_area"] in valid, (r["tomb_id"], r["theban_area"])


# ---------------------------------------------------------------------------
# PR A audit-fix structural tests (2026-05-02): enforce the corrected schema
# semantics so future chunks cannot reintroduce the `occupant_alt_names`
# misuse the audit migrated away from. Each test is mechanical (CLAUDE.md
# rule 3) — no human review needed to catch a regression.
# ---------------------------------------------------------------------------


def test_no_compound_occupant_name() -> None:
    """`occupant_name` carries ONE person (the headword). Joint occupants
    go in `co_occupants` (PR A audit-fix). The `' and '` / `', and '` /
    `' & '` joiners that PM used in the few multi-occupant headwords (KV46
    Yuia+Thuiu, SWV Three Princesses Menhet+Merti+Menwi) are forbidden in
    `occupant_name` going forward.
    """
    forbidden = (" and ", ", and ", " & ", " + ")
    for r in _rows():
        n = r.get("occupant_name") or ""
        for joiner in forbidden:
            assert joiner not in n, (
                f"{r['tomb_id']}: occupant_name {n!r} contains {joiner!r} "
                f"— joint occupants must go in `co_occupants`."
            )


def test_occupant_alt_names_are_person_variants_not_tomb_nicknames() -> None:
    """`occupant_alt_names` is for SAME-PERSON name variants only (prenomens
    like the chunk-7 DAN-Antef rows; throne-name vs birth-name pairs;
    transliteration variants). Tomb-nicknames (`Belzoni's tomb`, `Tomb of
    Memnon`, `Bruce's tomb`, etc.) belong in the new `tomb_aliases` field
    (PR A audit-fix migration).

    Mechanical heuristic: any string matching `Tomb of …`, `…'s tomb`,
    `the …'s tomb`, or `the Tomb of …` is a tomb-name shape. Regex widened
    on PR #169 round-2 (Gemini round-1) to catch multi-word possessives
    (`The Great King's tomb`) and `(The )?Tomb of …` prefixes. Round-3
    (Gemini round-2) replaced the `'s tomb$` end-anchor with `'s tomb\\b`
    so trailing punctuation (`Belzoni's tomb.`) doesn't slip through.
    """
    nickname_re = re.compile(
        r"(?i)^(?:(?:the\s+)?tomb of\b|.*'s tomb\b)"
    )
    for r in _rows():
        for alt in r.get("occupant_alt_names") or []:
            assert not nickname_re.search(alt), (
                f"{r['tomb_id']}: occupant_alt_names contains tomb-nickname "
                f"{alt!r} — should be in `tomb_aliases` instead."
            )


def test_co_occupants_each_have_name_and_role() -> None:
    """Every entry in `co_occupants` is a `{name, role, alt_names}` dict —
    EXACTLY those three keys, non-empty name + role, list-shape alt_names.
    Joint-occupant rows lose their per-person role information if either
    field is null — and the whole point of the PR A migration was to
    recover that information.

    Round-2 tighten (PR #169 Gemini + code-reviewer P2-1, P2-2, P2-5):
    - exact key-set (no extra keys silently passed through),
    - role validated against the controlled vocab (free-text role drift
      forbidden — same enforcement as the row-level `occupant_role`),
    - empty-string guard on `name` and on each `alt_names` entry.
    """
    co_role_vocab = _occupant_role_controlled_vocab()
    expected_keys = {"name", "role", "alt_names"}
    for r in _rows():
        for i, co in enumerate(r.get("co_occupants") or []):
            assert isinstance(co, dict), (r["tomb_id"], i, co)
            assert set(co.keys()) == expected_keys, (
                r["tomb_id"], i, "co_occupant key-set must be exactly "
                f"{sorted(expected_keys)}, got {sorted(co.keys())}: {co}"
            )
            name = co["name"]
            assert isinstance(name, str) and name, (
                r["tomb_id"], i, "co_occupant name must be a non-empty string", co
            )
            role = co["role"]
            assert role in co_role_vocab, (
                r["tomb_id"], i,
                f"co_occupant role {role!r} not in controlled vocab "
                f"{sorted(co_role_vocab)}: {co}",
            )
            alt_names = co["alt_names"]
            assert isinstance(alt_names, list), (
                r["tomb_id"], i, "co_occupant alt_names must be a list", co
            )
            for j, alt in enumerate(alt_names):
                assert isinstance(alt, str) and alt, (
                    r["tomb_id"], i, j,
                    f"co_occupant alt_names[{j}] must be a non-empty string: {alt!r}",
                )


def test_tomb_aliases_is_list_of_strings() -> None:
    """`tomb_aliases` carries strings (tomb popular names / surveyor
    designations). Empty list is the default. Never null.
    """
    for r in _rows():
        ta = r.get("tomb_aliases")
        assert isinstance(ta, list), (r["tomb_id"], ta)
        for item in ta:
            assert isinstance(item, str) and item, (r["tomb_id"], item)


def test_is_joint_burial_flag_paired_with_co_occupants() -> None:
    """`is_joint_burial: bool` (PR A round-2, egyptologist P1) signals
    coordinate burials with no PM-marked principal — downstream Phase-A
    consumers must treat `occupant_name` and `co_occupants[*].name` as a
    coordinate union for join purposes when this flag is True.

    Mechanical contract:
    - Every row carries the field as a bool (default False).
    - A row with `is_joint_burial=True` MUST have at least one co_occupant
      (a single-occupant row cannot be a "joint" burial).
    - A row with `co_occupants` non-empty MAY be either True (coordinate,
      no primacy) or False (subordinate, headword is the principal).
      Both shapes are intentional — KV46 is False because PM marks Yuia
      as the syntactic subject; SWV-ThreePrincesses is True because PM
      lists the three coordinately. The two-row test below pins the
      current state explicitly.
    """
    seen_joint = []
    for r in _rows():
        flag = r.get("is_joint_burial")
        assert isinstance(flag, bool), (r["tomb_id"], flag, type(flag).__name__)
        if flag:
            assert (r.get("co_occupants") or []), (
                r["tomb_id"],
                f"is_joint_burial=True but co_occupants is empty — "
                f"a single-occupant tomb cannot be a joint burial.",
            )
            seen_joint.append(r["tomb_id"])
    # Joint-coordinate burials in the current corpus, sorted by tomb_id
    # via the merge sort key (TT10 sorts before SWV-ThreePrincesses
    # because the TT prefix has rank 2 and SWV has rank 3 in
    # `merge.VALLEY_ORDER`):
    # - SWV-ThreePrincesses (chunk-7): PM p.591 lists Menhet/Merti/Menwi
    #   coordinately as `MENHET, MERTI, AND MENWI`.
    # - TT10 (chunk-9): PM p.19 lists Penbuy + Kasa coordinately as
    #   `PENBUY ... and KASA, Servants in the Place of Truth` — bare
    #   conjunction, plural role applies to both.
    # KV46 is intentionally False (asymmetric `YUIA ..., AND THUIU` —
    # Yuia leads). TT6 is also False (`X and son Y` — hierarchical).
    assert seen_joint == ["TT10", "SWV-ThreePrincesses"], seen_joint


def test_swv_three_princesses_per_person_role_propagation() -> None:
    """SWV-ThreePrincesses (PR #169 code-reviewer P2-4 + scope-enforcer
    requirement): the migration's choice to propagate the prior aggregate
    `Royal Family` label across all three per-person roles is a NEW per-
    person claim relative to the pre-PR-A single-row aggregate. Pin it as
    an assertion (not just a fix_rows rationale string) so future schema
    refinement that downgrades any single occupant to a different role is
    forced to update this test deliberately.

    Per-person refinement (likely to `Queen` after Lilyquist 2003) is
    deferred to a future chunk-7 re-extraction PR; that PR will replace
    this assertion when the egyptologist signs off on the per-person call.
    """
    r = _row("SWV-ThreePrincesses")
    assert r["occupant_role"] == "Royal Family"
    assert r["co_occupants"] == [
        {"name": "Merti", "role": "Royal Family", "alt_names": []},
        {"name": "Menwi", "role": "Royal Family", "alt_names": []},
    ]
    assert r["is_joint_burial"] is True


def test_occupant_role_controlled_vocab_covers_co_occupants() -> None:
    """Controlled vocab applies to `co_occupants[*].role` too (PR #169
    code-reviewer P2-2). Sibling enforcement to the row-level
    `occupant_role` controlled-vocab test — the whole point of PR A's
    `co_occupants` field is that per-occupant role becomes structured
    data; the vocabulary must apply there or free-text role drift defeats
    the structuring.

    `test_co_occupants_each_have_name_and_role` already enforces this on
    every row; this test is a focused regression-pin so a future relaxation
    of either test surfaces here.
    """
    vocab = _occupant_role_controlled_vocab()
    for r in _rows():
        for co in r.get("co_occupants") or []:
            assert co["role"] in vocab, (r["tomb_id"], co)


def _occupant_role_controlled_vocab() -> set[str]:
    """Single source of truth for the `occupant_role` / `co_occupants[*].role`
    controlled vocabulary. Mirrors the README field-semantics list.
    """
    return {
        "King",
        "Queen",
        "Royal Family",
        "Vizier",
        "Official",
        "High Priest",
        "Princess",
        "Prince",
        "Unknown",
    }


def test_all_prompts_mention_new_pr_a_fields() -> None:
    """Every PM extraction prompt mentions `tomb_aliases` AND `co_occupants`
    AND `is_joint_burial` AND `theban_area` (PR #169 code-reviewer P2-3 +
    PR #170 code-reviewer P2-2). Conversely, no prompt mentions the
    obsolete `"valley"` JSON key — the field was renamed in PR #170 and
    a stale prompt template would silently produce data under the wrong
    key, which `merge.py`'s field-union would carry through.

    Future chunks copy from these prompts; if a chunk-9+ prompt is written
    by copying chunk-1's pre-PR-A body without the new schema header,
    agents emit no values for the new fields and `SCHEMA_FIELD_DEFAULTS`
    silently fills `[]`/`False` — a tomb that genuinely has tomb-
    nicknames or joint occupants suffers data loss with no failing test.

    This is the rule-3 "deterministic enforcement over markdown convention"
    case — the prompt-update discipline must be a CI check.
    """
    prompt_files = sorted(SOURCE_DIR.glob("prompt*.md"))
    assert prompt_files, "no prompt*.md files found"
    for prompt in prompt_files:
        text = prompt.read_text()
        for field in (
            "tomb_aliases",
            "co_occupants",
            "is_joint_burial",
            "theban_area",
        ):
            assert field in text, (
                f"{prompt.name}: prompt does not mention `{field}` — "
                f"agents using this prompt will not emit the field, and "
                f"SCHEMA_FIELD_DEFAULTS will silently fill the default."
            )
        # No prompt may carry the obsolete `valley` JSON key — that field
        # was renamed to `theban_area` in PR #170. Stale templates would
        # produce data under the wrong key and the merge would propagate
        # it. Check both standard JSON (`"valley"`) and the single-quote
        # form (`'valley'`) per Gemini round-2 suggestion. (Body text
        # using "valley" as an English word — e.g. describing PM's
        # section structure — is fine; we test the JSON field-key form
        # specifically by requiring the quotes.)
        for legacy in (
            '"valley"',     # standard JSON key
            "'valley'",     # single-quoted variant (Gemini round-2)
            "`valley`",     # markdown backtick reference (Gemini round-3)
            "### valley",   # markdown section header (Gemini round-3)
        ):
            assert legacy not in text, (
                f"{prompt.name}: prompt still references the obsolete "
                f"JSON field key `{legacy}` — rename to `theban_area` "
                f"(PR #170)."
            )


def test_no_legacy_valley_field_key_in_reconciled() -> None:
    """No row in `reconciled.jsonl` carries the obsolete `valley` field
    key after the PR #170 rename (PR #170 code-reviewer P2-1).

    `raw/agent-*.jsonl` files are gitignored, but `merge.py` is field-
    name-agnostic — it picks fields from the union of agent emissions.
    If a stale agent re-runs against an unmigrated chunk-7+ prompt and
    emits `"valley"`, a re-merge would silently regenerate the obsolete
    key on disk. This test catches that drift mechanically.

    Belt-and-braces against `test_all_prompts_mention_new_pr_a_fields`'s
    upstream check on the prompt files themselves.
    """
    for r in _rows():
        assert "valley" not in r, (
            f"{r['tomb_id']}: row carries the obsolete `valley` field key "
            f"— rename to `theban_area` (PR #170). Most likely cause: a "
            f"stale agent JSONL was re-merged."
        )


def test_kv_rows_have_kv_tomb_id() -> None:
    """`tomb_id` prefix matches the `theban_area` value."""
    for r in _rows():
        if r["theban_area"] == "Valley of the Kings":
            assert r["tomb_id"].startswith("KV"), r
        if r["theban_area"] == "Valley of the Queens":
            assert r["tomb_id"].startswith("QV"), r


def test_dynasty_is_null_or_string() -> None:
    """`dynasty` is null at the extraction stage (Phase A enrichment fills
    it from the king authority). When populated by future enrichment, it
    must be the Arabic-numeral STRING form — Phase A relies on the string
    form for joining against the king authority; drift to int silently
    breaks that join.
    """
    for r in _rows():
        v = r["dynasty"]
        assert v is None or isinstance(v, str), (r["tomb_id"], v)


def test_dates_null_at_extraction_stage() -> None:
    """Per CLAUDE.md rule 1: PM headwords don't print BCE dates, so the
    dates fields stay null at extraction. Phase A king-authority enrichment
    against pharaoh.se populates them later. When populated, dates are
    negative ints.
    """
    for r in _rows():
        for field in ("date_bce_approx_start", "date_bce_approx_end"):
            v = r[field]
            if v is not None:
                assert isinstance(v, int) and v < 0, (r["tomb_id"], field, v)


def test_date_start_before_date_end() -> None:
    """For any row with both date_bce_approx_start and _end populated,
    start (more-negative, i.e. EARLIER BCE date) must be ≤ end. PM does
    not give regnal-end-then-start ordering anywhere; an inverted pair
    means a Phase A enrichment bug.
    """
    for r in _rows():
        s, e = r["date_bce_approx_start"], r["date_bce_approx_end"]
        if s is not None and e is not None:
            assert s <= e, (r["tomb_id"], s, e)


def test_source_citation_shape() -> None:
    """`source_citation` is a dict with `page` (int), `edition` (str), `section` (str)."""
    valid_editions = {EDITION_PM_I1, EDITION_PM_I2}
    for r in _rows():
        c = r["source_citation"]
        assert set(c.keys()) == {"page", "edition", "section"}, (r["tomb_id"], c.keys())
        assert isinstance(c["page"], int) and c["page"] > 0, (r["tomb_id"], c["page"])
        assert c["edition"] in valid_editions, (r["tomb_id"], c["edition"])
        assert isinstance(c["section"], str) and c["section"], (r["tomb_id"], c["section"])


def test_source_citation_page_in_chunk1_range() -> None:
    """Chunk 1 covers PM I.2 printed pages 495–518. Every chunk-1 row's
    page citation must fall within that range. Catches off-by-one bugs
    in extraction's running-header parsing.
    """
    for tid in CHUNK1_TOMB_IDS:
        r = _row(tid)
        page = r["source_citation"]["page"]
        assert 495 <= page <= 518, (tid, page)


def test_shared_with_tombs_are_valid_tomb_ids() -> None:
    """Every entry in `shared_with_tombs` matches the tomb-id regex."""
    for r in _rows():
        for tid in r["shared_with_tombs"]:
            assert _TOMB_ID_RE.match(tid), (r["tomb_id"], tid)


def test_shared_with_tombs_symmetry_within_chunk() -> None:
    """If KV5.shared_with_tombs lists KV7, then KV7.shared_with_tombs lists KV5
    — but only for pairs in the SAME PM section (same `source_citation.section`).

    Cross-section `See also` references are asymmetric in PM by design — the
    South Tomb of Hatshepsut (§ II.A) PM-prints `See also Tomb 20, supra, p. 546`
    referencing KV20 in § I.A, but PM's KV20 headword does not symmetrically
    reference the South Tomb. Enforcing symmetry across sections would force us
    to fabricate back-references PM doesn't print — violating CLAUDE.md rule 1
    (every fact must trace to its committed raw source).

    Within-section symmetry still holds (PM does cross-reference symmetrically
    within § I.A — KV3 ↔ KV11, KV5 ↔ KV7 — those pairs are both in the same
    § I.A "Tombs" section).
    """
    by_id = {r["tomb_id"]: r for r in _rows()}
    for r in _rows():
        for partner in r["shared_with_tombs"]:
            if partner not in by_id:
                continue
            own_section = r["source_citation"]["section"]
            partner_section = by_id[partner]["source_citation"]["section"]
            if own_section != partner_section:
                # Cross-section `See also` — asymmetric by PM convention.
                continue
            back_refs = by_id[partner]["shared_with_tombs"]
            assert r["tomb_id"] in back_refs, (
                f"{r['tomb_id']} → {partner} but {partner} → {back_refs}"
            )


def test_occupant_role_controlled_vocab() -> None:
    """Controlled vocabulary for `occupant_role`. Extend as new sections add roles."""
    valid = {"King", "Queen", "Royal Family", "Vizier", "Official",
             "High Priest", "Princess", "Prince", "Unknown"}
    for r in _rows():
        if r["occupant_role"] is not None:
            assert r["occupant_role"] in valid, (r["tomb_id"], r["occupant_role"])


# ---------------------------------------------------------------------------
# Chunk-1 specific value-assertion tests (KV1–KV10)
# ---------------------------------------------------------------------------


def test_chunk1_all_rows_kv_kings_no_dynasty_or_dates() -> None:
    """KV1–KV10 are all kings — `theban_area` and `occupant_role` are uniform.
    Dynasty + BCE dates are null at this stage (Phase A enrichment).
    """
    for tid in CHUNK1_TOMB_IDS:
        r = _row(tid)
        assert r["theban_area"] == "Valley of the Kings"
        assert r["occupant_role"] == "King"
        assert r["dynasty"] is None
        assert r["sub_period"] is None
        assert r["date_bce_approx_start"] is None
        assert r["date_bce_approx_end"] is None
        assert r["location_sub_area"] is None
        assert r["discovery_year"] is None
        assert r["discoverer"] is None
        assert r["source_citation"]["edition"] == EDITION_PM_I2
        assert r["source_citation"]["section"] == "I.A"


def test_chunk1_unfinished_flag() -> None:
    """KV3 (Ramesses III's first attempt) and KV5 (Ramesses II) are flagged
    `Unfinished` literally in PM. KV4 (Ramesses XI) was historically
    unfinished but PM doesn't use the literal word — `is_unfinished` stays
    false. This test pins the literal-text rule.
    """
    expected_unfinished = {"KV3", "KV5"}
    for tid in CHUNK1_TOMB_IDS:
        r = _row(tid)
        if tid in expected_unfinished:
            assert r["is_unfinished"] is True, tid
        else:
            assert r["is_unfinished"] is False, tid


def test_chunk1_shared_with_tombs() -> None:
    """KV3 → KV11 (chunk 2 — one-sided), KV5 ↔ KV7 (both chunk 1)."""
    assert _row("KV3")["shared_with_tombs"] == ["KV11"]
    assert _row("KV5")["shared_with_tombs"] == ["KV7"]
    assert _row("KV7")["shared_with_tombs"] == ["KV5"]
    # All other chunk-1 rows have empty shared_with_tombs.
    for tid in CHUNK1_TOMB_IDS - {"KV3", "KV5", "KV7"}:
        assert _row(tid)["shared_with_tombs"] == [], tid


def test_chunk1_kv1_minimal_row() -> None:
    """KV1 (Ramesses VII) is the minimal-shape KV chunk-1 row: no Unfinished
    flag, no cross-refs, no notes, no alt-names. Asserts every field.

    The KV3 flagship row (separate test below) exercises is_unfinished +
    shared_with_tombs; KV9 exercises notes_from_pm + occupant_alt_names.
    Together they cover every populated-field shape per rule 5.
    """
    r = _row("KV1")
    assert r["tomb_id"] == "KV1"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Ramesses VII"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 495,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk1_kv3_flagship_full_row() -> None:
    """KV3 (Ramesses III's unfinished tomb) is the flagship full-row test:
    exercises `is_unfinished=true` and `shared_with_tombs=["KV11"]` (a
    one-sided cross-chunk reference). Asserts every field per rule 5.
    """
    r = _row("KV3")
    assert r["tomb_id"] == "KV3"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Ramesses III"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is True
    assert r["shared_with_tombs"] == ["KV11"]
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 500,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk1_kv9_ramesses_vi_notes_and_aliases() -> None:
    """KV9 exercises `notes_from_pm` (the cross-line clause about Ramesses V's
    doorway usurpation) and `tomb_aliases` (the two 19th-c. classical-traveller
    nicknames from PM's `'Tomb of Metempsychosis', or 'Tomb of Memnon'`
    parenthetical — TOMB-names, not occupant alt-names; migrated from
    `occupant_alt_names` in PR A audit-fix). Asserts every field per rule 5.
    """
    r = _row("KV9")
    assert r["tomb_id"] == "KV9"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Ramesses VI"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == ["Tomb of Metempsychosis", "Tomb of Memnon"]
    assert r["co_occupants"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "doorways in outer part usurped from Ramesses V."
    assert r["source_citation"] == {
        "page": 511,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk1_kv4_ramesses_xi_notes_preserved() -> None:
    """KV4's headword: `RAMESSES XI (formerly XII)`. The parenthetical
    `(formerly XII)` is PM's regnal-number disambiguation — earlier
    scholarship counted this king as Ramesses XII. Preserved as a
    structured `notes_from_pm` rather than embedded in `occupant_name`,
    so downstream museum-data joins on the canonical `Ramesses XI` work.
    """
    r = _row("KV4")
    assert r["occupant_name"] == "Ramesses XI"
    assert r["notes_from_pm"] == "formerly XII"


def test_chunk1_two_ramesses_ii_tombs() -> None:
    """KV5 and KV7 are both attributed to Ramesses II (KV5 unfinished, KV7
    the actual completed tomb). Mutually-cross-referenced via shared_with_tombs.
    """
    kv5 = _row("KV5")
    kv7 = _row("KV7")
    for r in (kv5, kv7):
        assert r["occupant_name"] == "Ramesses II"
        assert r["theban_area"] == "Valley of the Kings"
        assert r["occupant_role"] == "King"
    assert kv5["is_unfinished"] is True
    assert kv7["is_unfinished"] is False
    assert kv5["shared_with_tombs"] == ["KV7"]
    assert kv7["shared_with_tombs"] == ["KV5"]
    assert kv5["source_citation"]["page"] == 501
    assert kv7["source_citation"]["page"] == 505


def test_chunk1_kv8_merneptah_page_507() -> None:
    """KV8 (Merneptah) headword opens at PM I.2 printed page 507, NOT 509.
    Egyptologist-reviewer caught the mis-citation in PR #66's first round;
    the field-rule-based prompt rewrite (with page extracted from chunk
    text running headers) produces the correct page. This test pins it.
    """
    r = _row("KV8")
    assert r["occupant_name"] == "Merneptah"
    assert r["source_citation"]["page"] == 507


# ---------------------------------------------------------------------------
# Chunk-2 specific value-assertion tests (KV11–KV20)
# ---------------------------------------------------------------------------


def test_chunk2_page_range() -> None:
    """Chunk 2 headwords sit on PM I.2 printed pages 518–546. Every chunk-2
    row's page citation must fall within that range. The chunk FILE
    extends two pages further (p.547–548) to give the extraction agents
    boundary context, but no KV headword in the chunk sits past p.546.
    """
    for tid in CHUNK2_TOMB_IDS:
        r = _row(tid)
        page = r["source_citation"]["page"]
        assert 518 <= page <= 546, (tid, page)
        assert r["source_citation"]["edition"] == EDITION_PM_I2
        assert r["source_citation"]["section"] == "I.A"


def test_chunk2_all_rows_in_valley_of_kings_no_dynasty_or_dates() -> None:
    """Every chunk-2 row has theban_area=VoK and null dynasty/dates/discoverer —
    same extraction-stage discipline as chunk 1.
    """
    for tid in CHUNK2_TOMB_IDS:
        r = _row(tid)
        assert r["theban_area"] == "Valley of the Kings"
        assert r["dynasty"] is None
        assert r["sub_period"] is None
        assert r["date_bce_approx_start"] is None
        assert r["date_bce_approx_end"] is None
        assert r["location_sub_area"] is None
        assert r["discovery_year"] is None
        assert r["discoverer"] is None


def test_chunk2_unfinished_flag() -> None:
    """KV18 (Ramesses X) is the only chunk-2 tomb flagged `Unfinished` in PM."""
    expected_unfinished = {"KV18"}
    for tid in CHUNK2_TOMB_IDS:
        r = _row(tid)
        if tid in expected_unfinished:
            assert r["is_unfinished"] is True, tid
        else:
            assert r["is_unfinished"] is False, tid


def test_chunk2_shared_with_tombs() -> None:
    """KV11 ↔ KV3 cross-chunk symmetry: both rows reference each other.
    KV20's informal `See also South Tomb` is NOT a numbered cross-ref — stays empty.
    """
    assert _row("KV11")["shared_with_tombs"] == ["KV3"]
    assert _row("KV3")["shared_with_tombs"] == ["KV11"]
    for tid in CHUNK2_TOMB_IDS - {"KV11"}:
        assert _row(tid)["shared_with_tombs"] == [], tid


def test_chunk2_kv11_ramesses_iii_full_row() -> None:
    """KV11 (Ramesses III) flagship row — exercises cross-chunk back-
    reference to KV3, tomb-nicknames (`Bruce's tomb`, `the Harper's tomb`)
    from PM's headword parenthetical (TOMB-names — migrated from the older
    `occupant_alt_names` slot to `tomb_aliases` in PR A audit-fix), and
    headword-at-page-tail extraction (KV11's headword sits at the bottom of
    physical p.60 / printed 518). Asserts every field per CLAUDE.md rule 5.
    """
    r = _row("KV11")
    assert r["tomb_id"] == "KV11"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Ramesses III"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == ["Bruce's tomb", "the Harper's tomb"]
    assert r["co_occupants"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == ["KV3"]
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 518,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv12_uninscribed() -> None:
    """KV12 (PM: `UNINSCRIBED`) — the tomb has no named occupant. Per the
    extraction prompt + fix_rows.py correction: `occupant_name=null` and
    `occupant_role='Unknown'`. Asserts every field per rule 5.
    """
    r = _row("KV12")
    assert r["tomb_id"] == "KV12"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] is None
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Unknown"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 527,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv13_bay_chancellor() -> None:
    """KV13 (Bay, Chancellor — non-royal). Exercises non-King
    `occupant_role` (`Official`) and the `notes_from_pm` regnal-dating
    fragment from PM's headword (`Temp. Merneptaḥ-Siptaḥ`), captured
    via fix_rows.py after the reviewer flagged that all three extraction
    agents dropped it. Asserts every field per rule 5.
    """
    r = _row("KV13")
    assert r["tomb_id"] == "KV13"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Bay"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Official"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "Temp. Merneptaḥ-Siptaḥ."
    assert r["source_citation"] == {
        "page": 527,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv14_tausert_usurpation_note() -> None:
    """KV14 (Tausert, usurped by Setnakht) — exercises the biographical-
    plus-usurpation `notes_from_pm` clause, distinct from `occupant_alt_names`
    (Setnakht is a later usurper, NOT a classical alias of Tausert).
    Asserts every field per rule 5.
    """
    r = _row("KV14")
    assert r["tomb_id"] == "KV14"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Tausert"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "wife of Sethos II. Usurped by Setnakht."
    assert r["source_citation"] == {
        "page": 527,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv17_sethos_i_belzoni_alias() -> None:
    """KV17 (Sethos I) — exercises the `Belzoni's tomb` 19th-c. nickname
    from PM's headword single-quote parenthetical (a TOMB-name after the
    1817 discoverer Giovanni Battista Belzoni, NOT an occupant alt-name;
    migrated from `occupant_alt_names` to `tomb_aliases` in PR A audit-
    fix). PM's spelling `Sethos I` is preserved verbatim (the ruler
    authority bridges to the modern `Seti I` convention in Phase A; the
    extract stays faithful to PM). Asserts every field per rule 5.
    """
    r = _row("KV17")
    assert r["tomb_id"] == "KV17"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Sethos I"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == ["Belzoni's tomb"]
    assert r["co_occupants"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 535,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv18_ramesses_x_unfinished() -> None:
    """KV18 (Ramesses X) — exercises `is_unfinished=True` and the
    `formerly XI` regnal-number disambiguation note. PM's headword
    literally prints `RAMESSES X (formerly XI)` and `Unfinished.` after
    the bibliographic ribbon. Asserts every field per rule 5.
    """
    r = _row("KV18")
    assert r["tomb_id"] == "KV18"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Ramesses X"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is True
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "formerly XI"
    assert r["source_citation"] == {
        "page": 545,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv19_prince_ramesses_mentuherkhepshef() -> None:
    """KV19 (the Prince's tomb) — exercises the `Prince` role (royal son
    who never reigned, distinct from the rest of the chunk's ruling
    kings) and the `son of Ramesses IX` relational note from PM's
    headword. The `occupant_name` preserves PM's verbatim spelling
    `Raʿmeses-Mentuhirkhopshef` (with ayin, with PM's `e/i/u` choices)
    rather than over-modernising to `Ramesses-Mentuherkhepshef` —
    PM-verbatim policy, per egyptologist-reviewer on PR #68.
    Asserts every field per rule 5.
    """
    r = _row("KV19")
    assert r["tomb_id"] == "KV19"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Raʿmeses-Mentuhirkhopshef"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Prince"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "son of Ramesses IX."
    assert r["source_citation"] == {
        "page": 546,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv20_hatshepsut_king() -> None:
    """KV20 (Hatshepsut) — exercises Hatshepsut-as-ruling-King disposition
    (not Queen), and `shared_with_tombs=[]` (PM's `See also South Tomb`
    is informal, not a numbered KV cross-ref). Asserts every field per
    rule 5.
    """
    r = _row("KV20")
    assert r["tomb_id"] == "KV20"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Hatshepsut"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 546,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


# ---------------------------------------------------------------------------
# Chunk-3 specific value-assertion tests (KV22–KV46 sparse)
# ---------------------------------------------------------------------------


def test_chunk3_page_range() -> None:
    """Chunk 3 headwords sit on PM I.2 printed pages 547–562. Every chunk-3
    row's page citation must fall within that range.
    """
    for tid in CHUNK3_TOMB_IDS:
        r = _row(tid)
        page = r["source_citation"]["page"]
        assert 547 <= page <= 562, (tid, page)
        assert r["source_citation"]["edition"] == EDITION_PM_I2
        assert r["source_citation"]["section"] == "I.A"


def test_chunk3_all_rows_in_valley_of_kings_no_dynasty_or_dates() -> None:
    """Every chunk-3 row has theban_area=VoK and null dynasty/dates/discoverer —
    same extraction-stage discipline as chunks 1 and 2.

    `is_unfinished` and `shared_with_tombs` are pinned per-row in the
    themed tests below rather than here — asserting them as chunk-wide
    invariants would fail if a future reviewer-caught correction
    identifies an Unfinished tomb or cross-ref in this PM range, and
    the per-row tests already give full coverage.
    """
    for tid in CHUNK3_TOMB_IDS:
        r = _row(tid)
        assert r["theban_area"] == "Valley of the Kings"
        assert r["dynasty"] is None
        assert r["sub_period"] is None
        assert r["date_bce_approx_start"] is None
        assert r["date_bce_approx_end"] is None
        assert r["discovery_year"] is None
        assert r["discoverer"] is None


def test_chunk3_kv21_absent_from_expected_set() -> None:
    """KV21 is not part of chunk-2 (KV20 jumps to KV22 in PM). Defensive
    structural check — lives here because chunk-3's range-definition is
    what documents the absence formally.
    """
    assert "KV21" not in EXPECTED_TOMB_IDS


def test_chunk3_missing_kv_ids_absent_from_expected_set() -> None:
    """KV24–KV33, KV37, KV40, KV41, KV44 are not in PM I.2 § I.A — they
    jump out of PM's cataloguing. If a future chunk PR accidentally pulls
    one of these in, this test fails loudly.
    """
    must_be_absent = (
        [f"KV{n}" for n in range(24, 34)] + ["KV37", "KV40", "KV41", "KV44"]
    )
    for tid in must_be_absent:
        assert tid not in EXPECTED_TOMB_IDS, tid


def test_chunk3_kv22_amenophis_iii_west_valley() -> None:
    """KV22 (Amenophis III) — West Valley tomb. Exercises:
    - `location_sub_area = "West Valley"` (first row in the extract with
      a non-null sub-area);
    - PM-verbatim `"Amenophis III"` despite modern `Amenhotep III`
      convention (PM's 1964 form is Amenophis);
    - `notes_from_pm` captures headword `Excavated by ...` clause.
    Asserts every field per rule 5.
    """
    r = _row("KV22")
    assert r["tomb_id"] == "KV22"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Amenophis III"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] == "West Valley"
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "Excavated by Davis, and by Carnarvon and Carter."
    assert r["source_citation"] == {
        "page": 547,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv23_ay_classical_aliases() -> None:
    """KV23 (Ay) — two 19th-c. surveyor tomb-names (`Eesa`, the local
    Arabic name cited by Wilkinson as 'W. -2 ("Eesa")'; `Schai`, the
    Prisse / Nestor L'Hôte designation for the same tomb). Both are
    TOMB-names from West-Valley survey traditions, NOT alternate names of
    the king Ay. Migrated from `occupant_alt_names` to `tomb_aliases` in
    PR A audit-fix. Tomb is also in the West Valley. Asserts every field
    per rule 5.
    """
    r = _row("KV23")
    assert r["tomb_id"] == "KV23"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Ay"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == ["Eesa", "Schai"]
    assert r["co_occupants"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] == "West Valley"
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "Excavated by Belzoni."
    assert r["source_citation"] == {
        "page": 550,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv34_tuthmosis_iii_first_edition_note() -> None:
    """KV34 (Tuthmosis III) — `notes_from_pm` captures PM's `[Ist ed. 24]`
    cross-reference to the 1st-edition tomb numbering. Parallel in shape
    to chunk-1 KV4's `formerly XII` and chunk-2 KV18's `formerly XI`.
    Asserts every field per rule 5.
    """
    r = _row("KV34")
    assert r["tomb_id"] == "KV34"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Tuthmosis III"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "1st ed. 24"
    assert r["source_citation"] == {
        "page": 551,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv36_mahirper_official() -> None:
    """KV36 (Mahirper) — non-royal `Official` role (Standard-bearer, Child
    of the nursery, temp. Hatshepsut). PM's text layer prints `MAI;IIRPER`
    where `I;I` is the underdot-H glyph; applying the chunk-1/2 rule
    `I;I → h` yields `Mahirper` (not `Maihirper` — that leaves a
    spurious `i` before the `h`; egyptologist-reviewer second-pass on
    PR #69 confirmed no published Egyptological form reads `Maihirper`).
    Asserts every field per rule 5.
    """
    r = _row("KV36")
    assert r["tomb_id"] == "KV36"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Mahirper"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Official"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == (
        "Standard-bearer, Child of the nursery. Temp. Ḥatshepsut. "
        "Excavated by Loret."
    )
    assert r["source_citation"] == {
        "page": 556,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv39_uninscribed_unknown_with_attribution_note() -> None:
    """KV39 — PM prints `Uninscribed tomb, attributed to Amenophis I by
    Weigall...`. Exercises: null `occupant_name` + `Unknown` role
    (distinct from KV12 which is `UNINSCRIBED` without attribution),
    plus the attribution-descriptor captured as `notes_from_pm`. Asserts
    every field per rule 5.
    """
    r = _row("KV39")
    assert r["tomb_id"] == "KV39"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] is None
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Unknown"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    # Extended on PR #151 by egyptologist printed-source review of PM p.559:
    # the previous truncated form dropped the load-bearing Abbott Papyrus +
    # Peet citation chain (independent reason to doubt the Amenophis I
    # attribution) AND the `infra, p. 599` cross-reference linking KV39 to
    # DAN-AhmosiNefertere. Restored to PM-verbatim full paragraph.
    assert r["notes_from_pm"] == (
        "Uninscribed tomb, attributed to Amenophis I by Weigall in Ann. "
        "Serv. xi (1911), pp. 174-5 [12], and id. A Guide to the "
        "Antiquities of Upper Egypt, pp. 163-4, but this is not "
        "supported by any inscriptional evidence, and does not "
        "correspond with the position given in the Abbott Papyrus "
        "(cf. Peet, The Great Tomb-Robberies of the Twentieth Egyptian "
        "Dynasty, pp. 37-8). See also the tomb of Queen ʿAhmosi "
        "Nefertere, infra, p. 599."
    )
    assert r["source_citation"] == {
        "page": 559,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv42_tuthmosis_ii_attribution_uncertain() -> None:
    """KV42 (Tuthmosis II) — PM prints the attribution with a `(?)`
    uncertainty marker (`TUTHMOSIS II (?)`). The structured `occupant_name`
    stays clean; the uncertainty is captured in `notes_from_pm` alongside
    the existing `Excavated by Loret` headword clause. Asserts every
    field per rule 5.
    """
    r = _row("KV42")
    assert r["tomb_id"] == "KV42"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Tuthmosis II"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "(?). Excavated by Loret"
    assert r["source_citation"] == {
        "page": 559,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv35_amenophis_ii() -> None:
    """KV35 (Amenophis II) — straightforward King row. PM's text layer
    renders `II` as `n` in this headword; the extract normalises to
    `Amenophis II`. Asserts every field per rule 5.
    """
    r = _row("KV35")
    assert r["tomb_id"] == "KV35"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Amenophis II"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 554,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv38_tuthmosis_i() -> None:
    """KV38 (Tuthmosis I) — King row with `Excavated by Loret` headword
    clause in notes. Asserts every field per rule 5.
    """
    r = _row("KV38")
    assert r["tomb_id"] == "KV38"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Tuthmosis I"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "Excavated by Loret."
    assert r["source_citation"] == {
        "page": 557,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv43_tuthmosis_iv() -> None:
    """KV43 (Tuthmosis IV) — King row with `Excavated by Davis` headword
    clause in notes. Asserts every field per rule 5.
    """
    r = _row("KV43")
    assert r["tomb_id"] == "KV43"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Tuthmosis IV"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "Excavated by Davis."
    assert r["source_citation"] == {
        "page": 559,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv45_userhet_re_used() -> None:
    """KV45 (Userhet) — re-used tomb pattern. Original Dyn XVIII occupant
    (Userhet) is the canonical `occupant_name`; the re-user (Merenkhons,
    Dyn XXII) goes in `notes_from_pm`. Asserts every field per rule 5.
    """
    r = _row("KV45")
    assert r["tomb_id"] == "KV45"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Userhet"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Official"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == (
        "Overseer of the Fields of Amūn, Dyn. XVIII, re-used by Merenkhons, "
        "Doorkeeper of the House of Amūn, Dyn. XXII (name from scarab). "
        "Excavated by Davis and Carter."
    )
    assert r["source_citation"] == {
        "page": 562,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv46_yuia_and_thuiu_multi_occupant() -> None:
    """KV46 — multi-occupant tomb (Yuia + Thuiu, parents of Queen Teye).
    Exercises the post-PR-A `co_occupants` pattern: headword `occupant_name`
    is `Yuia` (PM lists him first, with the title `Divine father`), the
    second occupant `Thuiu` (`Chief of the harîm of Amūn`) lives in
    `co_occupants`. Per-occupant role replaces the prior aggregate
    `Royal Family` label — both are non-royal court officials (parents-in-
    law of Amenhotep III). Biographical prose stays in `notes_from_pm`.
    Asserts every field per rule 5.
    """
    r = _row("KV46")
    assert r["tomb_id"] == "KV46"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Yuia"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Official"
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == [
        {
            "name": "Thuiu",
            "role": "Official",
            "alt_names": [],
        }
    ]
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == (
        "Divine father, and Chief of the harîm of Amūn, parents of "
        "Queen Teye."
    )
    assert r["source_citation"] == {
        "page": 562,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


# ---------------------------------------------------------------------------
# Chunk-4 specific value-assertion tests (KV47, 48, 55, 56, 57)
# ---------------------------------------------------------------------------


def test_chunk4_page_range() -> None:
    """Chunk 4 headwords sit on PM I.2 printed pages 564–567."""
    for tid in CHUNK4_TOMB_IDS:
        r = _row(tid)
        page = r["source_citation"]["page"]
        assert 564 <= page <= 567, (tid, page)
        assert r["source_citation"]["edition"] == EDITION_PM_I2
        assert r["source_citation"]["section"] == "I.A"


def test_chunk4_all_rows_in_valley_of_kings_no_dynasty_or_dates() -> None:
    """Every chunk-4 row has theban_area=VoK and null dynasty/dates/discoverer."""
    for tid in CHUNK4_TOMB_IDS:
        r = _row(tid)
        assert r["theban_area"] == "Valley of the Kings"
        assert r["dynasty"] is None
        assert r["sub_period"] is None
        assert r["date_bce_approx_start"] is None
        assert r["date_bce_approx_end"] is None
        assert r["discovery_year"] is None
        assert r["discoverer"] is None


def test_chunk4_missing_kv_ids_absent_from_expected_set() -> None:
    """KV49–54 and KV58–61 are absent from PM I.2 § I.A (PM jumps 48 → 55
    and 57 → 62). KV62 (Tutʿankhamun) IS in the expected set as of chunk 5.
    """
    must_be_absent = (
        [f"KV{n}" for n in range(49, 55)]
        + [f"KV{n}" for n in range(58, 62)]
    )
    for tid in must_be_absent:
        assert tid not in EXPECTED_TOMB_IDS, tid


def test_chunk4_kv47_merneptah_siptah() -> None:
    """KV47 — Merneptah-Siptah, King, first Dyn-19 joint-name occupant.
    PM's `MERNEPTAḤ-SIPTAḤ` → `Merneptah-Siptah` (underdots stripped in
    occupant_name per the README's diacritic policy). Asserts every
    field per rule 5.
    """
    r = _row("KV47")
    assert r["tomb_id"] == "KV47"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Merneptah-Siptah"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 564,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk4_kv48_amenemopet_vizier() -> None:
    """KV48 — Amenemopet, Vizier, temp. Amenophis II. First `Vizier` role
    in the landed extract (vs `Official` for Bay in KV13). PM's notes
    clause preserves the title pair, regnal-dating, and TT29 cross-ref.
    Asserts every field per rule 5.
    """
    r = _row("KV48")
    assert r["tomb_id"] == "KV48"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Amenemopet"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Vizier"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == (
        "Governor of the town, Vizier. Temp. Amenophis II. "
        "(Also owner of Theb. tb. 29.)"
    )
    assert r["source_citation"] == {
        "page": 565,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk4_kv55_amenophis_iv_hedged_attribution() -> None:
    """KV55 — PM's headword: `Probably AMENOPHIS IV, formerly attributed
    to Queen Teye or to Smenkhkarēʿ.` The structured `occupant_name`
    strips PM's `Probably` hedge (clean matchable name); the full
    hedging clause is captured verbatim in `notes_from_pm` including
    PM's macron-e and trailing ayin on `Smenkhkarēʿ`. Asserts every
    field per rule 5.
    """
    r = _row("KV55")
    assert r["tomb_id"] == "KV55"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Amenophis IV"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == (
        "Probably Amenophis IV, formerly attributed to Queen Teye or to "
        "Smenkhkarēʿ."
    )
    assert r["source_citation"] == {
        "page": 565,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk4_kv56_gold_tomb_uninscribed() -> None:
    """KV56 — PM's `'Gold Tomb', uninscribed.` (the nickname stems from
    the rich Tausert / Sethos II jewelry finds in this tomb). Null name
    + `Unknown` role + PM's nickname captured verbatim in notes.
    Asserts every field per rule 5.
    """
    r = _row("KV56")
    assert r["tomb_id"] == "KV56"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] is None
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Unknown"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "'Gold Tomb', uninscribed."
    assert r["source_citation"] == {
        "page": 567,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk4_kv57_haremhab() -> None:
    """KV57 — Haremhab, King. PM's `ḤAREMḤAB` → `Haremhab` (underdots
    stripped in occupant_name). Asserts every field per rule 5.
    """
    r = _row("KV57")
    assert r["tomb_id"] == "KV57"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Haremhab"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 567,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


# ---------------------------------------------------------------------------
# Chunk-5 specific value-assertion tests (KV62 Tutʿankhamun, standalone)
# ---------------------------------------------------------------------------


def test_chunk5_kv62_tutankhamun_full_row() -> None:
    """KV62 — Tutʿankhamun, standalone single-row chunk. Exercises PM's
    ayin glyph preservation in `occupant_name` (matches chunk-2 KV19
    `Raʿmeses-Mentuhirkhopshef` precedent — ayin is a royal-name
    radical, not a styling diacritic, so preserved even though the
    `occupant_name` field otherwise strips diacritics).

    Also exercises the joint `notes_from_pm` capture:
    - PM's `[1st ed. 58]` cross-ref → `"1st ed. 58"` (same normalisation
      as chunk-3 KV34).
    - PM's `Excavated by Carnarvon and Carter.` ribbon clause.
    - Joined with `". "` per chunk-2 KV14 pattern.

    Asserts every field per CLAUDE.md rule 5.
    """
    r = _row("KV62")
    assert r["tomb_id"] == "KV62"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Tutʿankhamun"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == (
        "1st ed. 58. Excavated by Carnarvon and Carter."
    )
    assert r["source_citation"] == {
        "page": 569,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


# ---------------------------------------------------------------------------
# Chunk-7 specific value-assertion tests (PM I.2 § II + § III.A/C/D —
# South-West Valleys + Dra' Abu el-Naga royal-and-near-royal tombs).
#
# First chunk with NON-NUMBERED tomb_ids: descriptor form `<PREFIX>-<Name>`.
# Per CLAUDE.md rule 5 every mappable field on every chunk-7 row is
# asserted below. 18 rows across 5 PM sub-sections.
# ---------------------------------------------------------------------------


def test_chunk7_uniform_null_phase_a_fields() -> None:
    """Every chunk-7 row carries null for the Phase-A-enrichment fields
    (`dynasty`, `sub_period`, `date_bce_approx_start`, `date_bce_approx_end`,
    `discovery_year`, `discoverer`). Per CLAUDE.md rule 1, PM headwords do
    not print those values as structured data — they're filled by Phase A
    ruler-authority enrichment against pharaoh.se.
    """
    for tid in CHUNK7_TOMB_IDS:
        r = _row(tid)
        assert r["dynasty"] is None, tid
        assert r["sub_period"] is None, tid
        assert r["date_bce_approx_start"] is None, tid
        assert r["date_bce_approx_end"] is None, tid
        assert r["discovery_year"] is None, tid
        assert r["discoverer"] is None, tid
        assert r["source_citation"]["edition"] == EDITION_PM_I2


def test_chunk7_section_ii_location_sub_areas() -> None:
    """§ II rows carry the wadi sub-area PM prints in the section header.
    § II.A = Wadi Sikket Taqet Zaid; § II.B = Wadi Qubbanet el-Qirud.
    """
    assert _row("SWV-HatshepsutSouth")["location_sub_area"] == "Wadi Sikket Taqet Zaid"
    assert _row("SWV-Neferure")["location_sub_area"] == "Wadi Qubbanet el-Qirud"
    assert _row("SWV-ThreePrincesses")["location_sub_area"] == "Wadi Qubbanet el-Qirud"


def test_chunk7_section_iii_a_location_sub_areas() -> None:
    """§ III.A Antef Cemetery is at El-Ṭaraf per PM's section header
    `A. ANTEF CEMETERY. Dyn. XI. At El-Ṭaraf`. PM ties the three Dyn-XI
    royal tombs (two Antefs + Mentuhotp-Sʿankhibtaui) to that locality.
    """
    for tid in {"DAN-AntefSehertaui", "DAN-AntefWahankh", "DAN-MentuhotpSankhibtaui"}:
        assert _row(tid)["location_sub_area"] == "El-Ṭaraf", tid


def test_chunk7_section_iii_c_and_d_no_sub_area() -> None:
    """§ III.C and § III.D headwords don't name a finer wadi beyond
    Dra' Abu el-Naga itself — `location_sub_area` stays null for those rows.
    """
    section_iii_c_and_d = CHUNK7_TOMB_IDS - {
        "SWV-HatshepsutSouth",
        "SWV-Neferure",
        "SWV-ThreePrincesses",
        "DAN-AntefSehertaui",
        "DAN-AntefWahankh",
        "DAN-MentuhotpSankhibtaui",
    }
    for tid in section_iii_c_and_d:
        assert _row(tid)["location_sub_area"] is None, tid


def test_chunk7_only_mentuhotp_sankhibtaui_unfinished() -> None:
    """PM marks only Mentuhotp-Sʿankhibtaui's tomb `Unfinished` in chunk 7.
    Every other chunk-7 row carries `is_unfinished: false`.
    """
    for tid in CHUNK7_TOMB_IDS:
        r = _row(tid)
        if tid == "DAN-MentuhotpSankhibtaui":
            assert r["is_unfinished"] is True, tid
        else:
            assert r["is_unfinished"] is False, tid


def test_chunk7_shared_with_tombs() -> None:
    """Only the South Tomb of Hatshepsut (§ II.A) cross-references into § I.A
    via PM's literal `See also Tomb 20, supra, p. 546` clause — asymmetric
    per `test_shared_with_tombs_symmetry_within_chunk`.
    """
    assert _row("SWV-HatshepsutSouth")["shared_with_tombs"] == ["KV20"]
    for tid in CHUNK7_TOMB_IDS - {"SWV-HatshepsutSouth"}:
        assert _row(tid)["shared_with_tombs"] == [], tid


def test_chunk7_valleys() -> None:
    """§ II rows → `South-West Valleys`; § III rows → `Dra' Abu el-Naga`."""
    swv_ids = {"SWV-HatshepsutSouth", "SWV-Neferure", "SWV-ThreePrincesses"}
    for tid in swv_ids:
        assert _row(tid)["theban_area"] == "South-West Valleys", tid
    for tid in CHUNK7_TOMB_IDS - swv_ids:
        assert _row(tid)["theban_area"] == "Dra' Abu el-Naga", tid


def test_chunk7_pm_sections() -> None:
    """`source_citation.section` matches PM's sub-section label per tomb."""
    expected = {
        "SWV-HatshepsutSouth": "II.A",
        "SWV-Neferure": "II.B",
        "SWV-ThreePrincesses": "II.B",
        "DAN-AntefSehertaui": "III.A",
        "DAN-AntefWahankh": "III.A",
        "DAN-MentuhotpSankhibtaui": "III.A",
        "DAN-AhmosiNefertere": "III.C",
        "DAN-Aqhor": "III.D",
        "DAN-Ahhotep": "III.D",
        "DAN-AhmosiHenutempet": "III.D",
        "DAN-AhmosiSonOfSeqenenre": "III.D",
        "DAN-AntefNubkheperre": "III.D",
        "DAN-AntefSekhemreHeruhirmaet": "III.D",
        "DAN-AntefSekhemreWepmaet": "III.D",
        "DAN-KamosiWazkheperre": "III.D",
        "DAN-MentuhotpIWifeOfDjhuti": "III.D",
        "DAN-Neferhotep": "III.D",
        "DAN-SebkemsafSekhemreShedtaui": "III.D",
    }
    for tid, sec in expected.items():
        assert _row(tid)["source_citation"]["section"] == sec, tid


def test_chunk7_occupant_roles() -> None:
    """Controlled-vocab `occupant_role` assignments per chunk-7 row."""
    expected = {
        # Pre-kingship Hatshepsut's South Tomb — PM text is explicit that
        # the quartzite sarcophagus is inscribed "as Queen-Consort".
        "SWV-HatshepsutSouth": "Queen",
        # Princess Neferure (hedged "Probably Princess Neferure").
        "SWV-Neferure": "Princess",
        # Three princesses shared tomb — Royal Family (catch-all for
        # multi-occupant royal burials).
        "SWV-ThreePrincesses": "Royal Family",
        # § III.A Antef Cemetery (Dyn XI rulers).
        "DAN-AntefSehertaui": "King",
        "DAN-AntefWahankh": "King",
        "DAN-MentuhotpSankhibtaui": "King",
        # § III.C Ahmose-Nefertari = Queen (wife of King Ahmose).
        "DAN-AhmosiNefertere": "Queen",
        # § III.D Dyn-17 cemetery.
        "DAN-Aqhor": "Official",           # *rḫ-nswt* "king's acquaintance" — minor courtier title
        "DAN-Ahhotep": "Queen",            # wife of Seqenenre-Taʿa
        "DAN-AhmosiHenutempet": "Princess",  # daughter of Ahhotep
        "DAN-AhmosiSonOfSeqenenre": "Royal Family",  # prince, not king
        "DAN-AntefNubkheperre": "King",    # Dyn-17 Inyotef VI
        "DAN-AntefSekhemreHeruhirmaet": "King",  # Dyn-17 Inyotef VII
        "DAN-AntefSekhemreWepmaet": "King",  # Dyn-17 Inyotef V
        "DAN-KamosiWazkheperre": "King",  # Dyn-17 Kamose
        "DAN-MentuhotpIWifeOfDjhuti": "Queen",  # wife of King Djehuty
        "DAN-Neferhotep": "Official",      # Scribe of the Great Harim
        "DAN-SebkemsafSekhemreShedtaui": "King",  # Dyn-17 Sebkemsaf II
    }
    for tid, role in expected.items():
        assert _row(tid)["occupant_role"] == role, (tid, _row(tid)["occupant_role"])


def test_chunk7_occupant_names_and_alt_names() -> None:
    """PM-verbatim `occupant_name` (ayin/underdot PRESERVED) and `occupant_alt_names`
    (prenomens where PM prints `NAME (PRENOMEN)`).
    """
    expected_name = {
        "SWV-HatshepsutSouth": "Hatshepsut",
        "SWV-Neferure": "Neferureʿ",
        # PR A audit-fix (2026-05-02): `occupant_name` carries the PM
        # headword (Menhet, listed first); Merti and Menwi live in
        # `co_occupants` (asserted in test_chunk7_co_occupants).
        "SWV-ThreePrincesses": "Menhet",
        "DAN-AntefSehertaui": "Antef",
        "DAN-AntefWahankh": "Antef",
        "DAN-MentuhotpSankhibtaui": "Mentuhotp-Sʿankhibtaui",
        "DAN-AhmosiNefertere": "ʿAhmosi Nefertere",
        "DAN-Aqhor": "ʿAḳ-hor",
        "DAN-Ahhotep": "ʿAhhotp",
        "DAN-AhmosiHenutempet": "ʿAhmosi Henutempet",
        "DAN-AhmosiSonOfSeqenenre": "ʿAhmosi",
        "DAN-AntefNubkheperre": "Antef",
        "DAN-AntefSekhemreHeruhirmaet": "Antef",
        "DAN-AntefSekhemreWepmaet": "Antef",
        "DAN-KamosiWazkheperre": "Kamosi",
        "DAN-MentuhotpIWifeOfDjhuti": "Mentuhotp I",
        "DAN-Neferhotep": "Neferhotep",
        "DAN-SebkemsafSekhemreShedtaui": "Sebkemsaf II",
    }
    for tid, name in expected_name.items():
        assert _row(tid)["occupant_name"] == name, (tid, _row(tid)["occupant_name"])

    expected_alt = {
        "DAN-AntefSehertaui": ["Sehertaui"],
        "DAN-AntefWahankh": ["Wahʿankh"],
        "DAN-AntefNubkheperre": ["Nubkheperreʿ"],
        "DAN-AntefSekhemreHeruhirmaet": ["Sekhemreʿ-Heruḥirmaʿet"],
        "DAN-AntefSekhemreWepmaet": ["Sekhemreʿ-Wepmaʿet"],
        "DAN-KamosiWazkheperre": ["Wazkheperreʿ"],
        "DAN-SebkemsafSekhemreShedtaui": ["Sekhemreʿ-Shedtaui"],
    }
    for tid, alt in expected_alt.items():
        assert _row(tid)["occupant_alt_names"] == alt, (tid, _row(tid)["occupant_alt_names"])

    # Every other row: empty alt_names.
    for tid in CHUNK7_TOMB_IDS - expected_alt.keys():
        assert _row(tid)["occupant_alt_names"] == [], tid


def test_chunk7_co_occupants() -> None:
    """SWV-ThreePrincesses (Menhet, Merti, Menwi — three foreign wives of
    Tuthmosis III, Wadi Qubbanet el-Qirud burial) is a joint-occupant row
    after the PR A audit-fix. Headword `occupant_name` = Menhet (PM lists
    her first); the other two live in `co_occupants`. Per-occupant role
    preserves the prior aggregate `Royal Family` label across all three —
    refining per-person roles is a follow-up after the egyptologist
    reviewer revisits with the new schema.
    """
    r = _row("SWV-ThreePrincesses")
    assert r["occupant_name"] == "Menhet"
    assert r["occupant_role"] == "Royal Family"
    assert r["co_occupants"] == [
        {"name": "Merti", "role": "Royal Family", "alt_names": []},
        {"name": "Menwi", "role": "Royal Family", "alt_names": []},
    ]
    # Every other chunk-7 row has empty co_occupants.
    for tid in CHUNK7_TOMB_IDS - {"SWV-ThreePrincesses"}:
        assert _row(tid)["co_occupants"] == [], tid


def test_chunk7_source_citation_pages() -> None:
    """Printed-page numbers for each chunk-7 row match PM's actual headword
    location. Chunk text is physical p.132–148 = printed p.590–606.
    """
    expected_page = {
        "SWV-HatshepsutSouth": 591,
        "SWV-Neferure": 592,
        "SWV-ThreePrincesses": 591,
        "DAN-AntefSehertaui": 594,
        "DAN-AntefWahankh": 595,
        "DAN-MentuhotpSankhibtaui": 595,
        "DAN-AhmosiNefertere": 599,
        "DAN-Aqhor": 605,
        "DAN-Ahhotep": 600,
        "DAN-AhmosiHenutempet": 604,
        "DAN-AhmosiSonOfSeqenenre": 604,
        "DAN-AntefNubkheperre": 602,
        "DAN-AntefSekhemreHeruhirmaet": 603,
        "DAN-AntefSekhemreWepmaet": 603,
        "DAN-KamosiWazkheperre": 600,
        "DAN-MentuhotpIWifeOfDjhuti": 604,
        "DAN-Neferhotep": 604,
        "DAN-SebkemsafSekhemreShedtaui": 603,
    }
    for tid, page in expected_page.items():
        assert _row(tid)["source_citation"]["page"] == page, (tid, _row(tid)["source_citation"]["page"])


def test_chunk7_notes_from_pm() -> None:
    """Exact-match `notes_from_pm` for every chunk-7 row — tightened from
    the earlier substring-match on the retrospective code-review of PR #100.

    The code-reviewer flagged two issues with the prior version: (a)
    substring-match weakens CLAUDE.md rule 5 discipline (chunks 1–5
    exact-match; chunk 7 should too); and (b) the `None or non-empty`
    fallback on DAN-AntefSehertaui / DAN-AntefSekhemreWepmaet is literally
    the rule-5 anti-pattern ("absence of errors"). `fix_rows.py` exists
    precisely to pin PM-verbatim values even against noisy text-layer
    OCR, so exact match is achievable and preferred.
    """
    expected = {
        "SWV-HatshepsutSouth": (
            "See also Tomb 20, supra, p. 546. Sarcophagus as Queen-Consort, "
            "quartzite, in Cairo Mus. Ent. 47032."
        ),
        "SWV-Neferure": "Probably Princess Neferureʿ, daughter of Ḥatshepsut.",
        "SWV-ThreePrincesses": "Temp. Tuthmosis III.",
        "DAN-AhmosiNefertere": (
            "Tomb of Queen ʿAḥmosi Nefertere (probably). Attributed to "
            "Amenophis I by Carter, later equated by Černý with "
            "'House of Amenophis of the Garden'."
        ),
        "DAN-Aqhor": "Royal acquaintance. Dyn. XVII. Objects found by Vassalli in 1863.",
        "DAN-Ahhotep": "Wife of King Seḳenenreʿ-Taʿa. Found by Mariette in 1859.",
        "DAN-AhmosiHenutempet": "Daughter of ʿAḥḥotp (wife of King Seḳenenreʿ-Taʿa).",
        "DAN-AhmosiSonOfSeqenenre": "Eldest son of King Seḳenenreʿ-Taʿa and ʿAḥḥotp.",
        "DAN-AntefNubkheperre": "Found by Mariette in 1860. Pyramid, see Hay MSS. 29816.",
        "DAN-AntefSekhemreHeruhirmaet": (
            "Probably younger brother and successor of Antef (Sekhemreʿ-Wepmaʿet)."
        ),
        "DAN-KamosiWazkheperre": (
            "Found by Mariette in 1857. For pyramid, possibly of Kamosi, "
            "see infra, p. 620."
        ),
        # fix_rows.py CHUNK7_CORRECTIONS restores PM's diacritics on the
        # Egyptian d-emphatic in `Ḏḥuti` (d-bar — same character as in
        # `Ḏḥwty`/Thoth). The earlier value used `Ḍḥuti` (d-underdot, a
        # different consonant in Semitic transliteration) — corrected on
        # PR #151 by egyptologist printed-source review of PM p.604.
        "DAN-MentuhotpIWifeOfDjhuti": (
            "Wife of King Ḏḥuti. Found in tomb by Passalacqua."
        ),
        "DAN-MentuhotpSankhibtaui": "Unfinished.",
        "DAN-Neferhotep": (
            "Scribe of the Great Harîm, probably temp. Antef (Nubkheperrēʿ). "
            "Rock-tomb, uninscribed. Found by Mariette in 1860, probably "
            "near Theb. tb. 13."
        ),
        "DAN-SebkemsafSekhemreShedtaui": (
            "Pyramid behind Theb. tb. 24, perhaps belonging to this tomb."
        ),
    }
    for tid, note in expected.items():
        assert _row(tid)["notes_from_pm"] == note, (tid, _row(tid)["notes_from_pm"])

    # Rows where PM has no prose beyond name + cartouches + bibliographic
    # ribbon — `notes_from_pm` is exactly None (not empty-string, not a
    # bare-punctuation value).
    for tid in ("DAN-AntefSehertaui", "DAN-AntefWahankh", "DAN-AntefSekhemreWepmaet"):
        assert _row(tid)["notes_from_pm"] is None, (tid, _row(tid)["notes_from_pm"])


# ---------------------------------------------------------------------------
# Chunk-8 specific value-assertion tests (PM I.2 § X.A Valley of the Queens —
# 20 numbered QV tombs).
# ---------------------------------------------------------------------------


def test_chunk8_uniform_null_phase_a_fields() -> None:
    """Every chunk-8 row carries null for Phase-A-enrichment fields
    (`dynasty`, `sub_period`, `date_bce_approx_start`, `date_bce_approx_end`,
    `discovery_year`, `discoverer`). `source_citation.edition` is PM I.2.
    `source_citation.section` is exactly "X.A".
    `theban_area` is "Valley of the Queens".
    """
    for tid in CHUNK8_TOMB_IDS:
        r = _row(tid)
        assert r["theban_area"] == "Valley of the Queens", tid
        assert r["source_citation"]["edition"] == EDITION_PM_I2
        assert r["source_citation"]["section"] == "X.A", tid
        assert r["dynasty"] is None
        assert r["sub_period"] is None
        assert r["date_bce_approx_start"] is None
        assert r["date_bce_approx_end"] is None
        assert r["discovery_year"] is None
        assert r["discoverer"] is None
        assert r["location_sub_area"] is None
        assert r["shared_with_tombs"] == []


def test_chunk8_only_qv38_unfinished() -> None:
    """PM's headword marks only QV38 (Queen Sitreʿ, wife of Ramesses I) as
    `Unfinished`. Every other QV row carries `is_unfinished: false`.
    """
    for tid in CHUNK8_TOMB_IDS:
        r = _row(tid)
        if tid == "QV38":
            assert r["is_unfinished"] is True, tid
        else:
            assert r["is_unfinished"] is False, tid


def test_chunk8_no_name_rows_unknown_role() -> None:
    """`A QUEEN, no name` / `A PRINCESS, no name` / `cartouche blank` rows
    carry `occupant_name: null` and `occupant_role: "Unknown"` (per prompt
    rule 1, applied via fix_rows.py CHUNK8_CORRECTIONS when agents emit
    null role on empty-name headwords).
    """
    no_name_rows = {"QV36", "QV40", "QV73", "QV75"}
    for tid in no_name_rows:
        r = _row(tid)
        assert r["occupant_name"] is None, (tid, r["occupant_name"])
        assert r["occupant_role"] == "Unknown", (tid, r["occupant_role"])


def test_chunk8_occupant_roles() -> None:
    """Per-row role assignments per PM headwords: QUEEN / PRINCESS / PRINCE /
    VIZIER / Unknown.
    """
    expected = {
        "QV33": "Princess",  # PRINCESS TANEZEM(T)
        "QV36": "Unknown",   # A PRINCESS, no name (fix_rows Unknown)
        "QV38": "Queen",     # QUEEN SITREʿ, wife of Ramesses I, Unfinished
        "QV40": "Unknown",   # A QUEEN, cartouche blank (fix_rows Unknown)
        "QV42": "Prince",    # PRINCE PARAʿḤIRWENEMEF
        "QV43": "Prince",    # PRINCE SET-ḤIRKHOPSHEF
        "QV44": "Prince",    # PRINCE KHAʿEMWESET
        "QV46": "Vizier",    # IMḤOTEP, Vizier
        "QV47": "Princess",  # PRINCESS ʿAḤMOSI, daughter of Seḳenenreʿ-Taʿa
        "QV51": "Queen",     # QUEEN ESI II, mother of Ramesses VI
        "QV52": "Queen",     # QUEEN TYTI
        "QV53": "Prince",    # PRINCE RAʿMESES, son of Ramesses III
        "QV55": "Prince",    # PRINCE AMEN(ḤIR)KHOPSHEF, son of Ramesses III
        "QV60": "Queen",     # QUEEN NEBTTAUI, daughter of Ramesses II
        "QV66": "Queen",     # QUEEN NEFERTARI, wife of Ramesses II
        "QV68": "Queen",     # QUEEN MERYTAMUN, daughter of Ramesses II
        "QV71": "Queen",     # QUEEN BENTʿANTA, daughter of Ramesses II
        "QV73": "Unknown",   # A PRINCESS, no name. Dyn. XX
        "QV74": "Queen",     # QUEEN TENTOPET, Great King's mother
        "QV75": "Unknown",   # A QUEEN, no name
    }
    for tid, role in expected.items():
        assert _row(tid)["occupant_role"] == role, (tid, _row(tid)["occupant_role"])


def test_chunk8_occupant_names() -> None:
    """PM-verbatim occupant_name (ayin `ʿ` and underdot-H `ḥ` preserved)."""
    expected_name = {
        "QV33": "Tanezem(t)",
        "QV36": None,
        "QV38": "Sitreʿ",
        "QV40": None,
        "QV42": "Paraʿhirwenemef",
        "QV43": "Set-hirkhopshef",
        "QV44": "Khaʿemweset",
        "QV46": "Imhotep",
        "QV47": "ʿAhmosi",
        "QV51": "Esi II",
        "QV52": "Tyti",
        "QV53": "Raʿmeses",
        "QV55": "Amen(hir)khopshef",
        "QV60": "Nebttaui",
        "QV66": "Nefertari",
        "QV68": "Merytamun",
        "QV71": "Bentʿanta",
        "QV73": None,
        "QV74": "Tentopet",
        "QV75": None,
    }
    for tid, name in expected_name.items():
        assert _row(tid)["occupant_name"] == name, (tid, _row(tid)["occupant_name"])


def test_chunk8_source_citation_pages() -> None:
    """Printed page numbers per QV tomb — matches PM's headword location
    in the chunk file (printed pp.751–768).
    """
    expected_page = {
        "QV33": 751, "QV36": 751, "QV38": 751, "QV40": 751,
        "QV42": 752, "QV43": 753, "QV44": 754,
        "QV46": 755, "QV47": 755,
        "QV51": 756, "QV52": 756,
        "QV53": 759, "QV55": 759,
        "QV60": 761, "QV66": 762, "QV68": 765, "QV71": 766,
        "QV73": 767, "QV74": 767, "QV75": 768,
    }
    for tid, page in expected_page.items():
        actual = _row(tid)["source_citation"]["page"]
        # Exact match: page numbers are extracted from explicit
        # `===== PRINTED PAGE M =====` markers in the chunk text, so the
        # extraction must be exact — a ±1 tolerance would hide off-by-one
        # extraction bugs.
        assert actual == page, (tid, actual, page)


def test_chunk8_notes_from_pm_royal_kinship() -> None:
    """Rows with explicit royal kinship / regnal-dating clauses carry them
    in `notes_from_pm`. Verify key substrings (not full verbatim — PM
    diacritic rendering varies).
    """
    expected = {
        "QV38": "wife of Ramesses I",
        "QV42": "son of Ramesses III",
        "QV43": "King's son",
        "QV44": "son of Ramesses III",
        "QV47": "daughter of Seḳenenreʿ-Taʿa",
        "QV51": "mother of Ramesses VI",
        "QV53": "son of Ramesses III",
        "QV55": "son of Ramesses III",
        "QV60": "daughter of Ramesses II",
        "QV66": "wife of Ramesses II",
        "QV68": "daughter of Ramesses II",
        "QV71": "daughter of Ramesses II",
    }
    for tid, substr in expected.items():
        notes = _row(tid)["notes_from_pm"]
        assert notes is not None, f"{tid} expected notes_from_pm"
        assert substr in notes, f"{tid}: expected {substr!r} in {notes!r}"


def test_chunk8_reviewer_inserted_characters_pinned() -> None:
    """Every reviewer-inserted character in `CHUNK8_CORRECTIONS` must be
    pinned by a test substring assertion — rule 5 + the
    `feedback_fix_rows_unattributed_restoration` memory.

    QV47 + QV74 corrections updated 2026-04-29 by egyptologist printed-
    source review on PR #151:
    - QV47: PM p.755 prints `Sit-ḏḥout` with `ḏ` (d-bar, the standard
      Egyptological d-emphatic, same character as in `Ḏḥwty`/Thoth) —
      NOT `ḍ` (d-underdot used in Semitic transliteration). Earlier
      fix_rows.py used the wrong consonant; corrected directly.
    - QV74: PM p.767 main text + footnote 1 are SEPARATE prose blocks.
      Earlier fix_rows.py synthesized them into a single `notes_from_pm`
      blob — rule-1 (provenance) violation since the synthesized prose
      doesn't appear verbatim in PM. Corrected to PM-main-text-verbatim
      only; the footnote 1 genealogy + per-citation chain is tracked
      for restoration via follow-up issue (schema split for
      `notes_footnote` / `notes_genealogy` field).
    """
    qv47_notes = _row("QV47")["notes_from_pm"]
    assert "Sit-ḏḥout" in qv47_notes, (
        f"QV47 expected egyptologist-corrected 'Sit-ḏḥout' (d-bar); got {qv47_notes!r}"
    )
    assert "Sit-ḍḥout" not in qv47_notes, (
        f"QV47 must not carry the pre-#151 wrong-consonant 'Sit-ḍḥout' (d-underdot); got {qv47_notes!r}"
    )
    assert "Sit-gḥout" not in qv47_notes, (
        f"QV47 must not carry the pre-fix OCR form; got {qv47_notes!r}"
    )
    qv74_notes = _row("QV74")["notes_from_pm"]
    # PM-main-text-verbatim: matches `74. QUEEN TENTŌPET ... Great King's
    # mother and King's wife.¹ (CHAMPOLLION, No. 15, L. D. Text, No. 2,
    # HAY, No. 7.)` exactly (modulo the macron and the cartouche, which
    # belong elsewhere).
    assert qv74_notes == (
        "Great King's mother and King's wife. "
        "(CHAMPOLLION, No. 15, L. D. Text, No. 2, HAY, No. 7.)"
    ), f"QV74 expected PM-main-text-verbatim; got {qv74_notes!r}"
    # The synthesized footnote prose must NOT appear in notes_from_pm
    # (rule-1 provenance violation). Tracked for schema-split follow-up.
    for substr in (
        "Wife(?) of Ramesses IV",
        "mother of Ramesses V",
        "daughter of Ramesses IV",
        "per PM p.767 footnote 1",
    ):
        assert substr not in qv74_notes, (
            f"QV74 must not carry pre-#151 synthesized footnote prose {substr!r}; got {qv74_notes!r}"
        )


def test_chunk8_notes_from_pm_remaining_rows() -> None:
    """QV33, QV36, QV40, QV46, QV52, QV73, QV75 have populated
    `notes_from_pm` values that `test_chunk8_notes_from_pm_royal_kinship`
    does not cover. Rule 5 thematic-gap fix from the chunk-8 retrospective
    code-review; QV36 + QV40 added per Gemini round-2 finding on PR #105
    (PM prints populated text for both — leaving them unasserted meant a
    silent regression on those rows would not break this test).
    """
    expected_substrings = {
        # QV33: earlier-edition cross-numbering + dating hedge.
        "QV33": "Dyn. XX(?)",
        # QV36: PM's bare "A PRINCESS, no name." clause (no citation tail).
        "QV36": "A PRINCESS, no name.",
        # QV40: PM's "A QUEEN, cartouche blank" clause + 19th-c. cross-refs.
        "QV40": "A QUEEN, cartouche blank.",
        # QV46 Imhotep: hedged attribution + regnal-dating clause.
        "QV46": "Vizier. Temp. Tuthmosis I.",
        # QV52 Tyti: dating + earlier-edition cross-ref.
        "QV52": "Ramesside.",
        # QV73: PM's "A PRINCESS, no name" clause captured verbatim.
        "QV73": "A PRINCESS, no name. Dyn. XX.",
        # QV75: PM's "A QUEEN, no name" clause.
        "QV75": "A QUEEN, no name.",
    }
    for tid, substr in expected_substrings.items():
        notes = _row(tid)["notes_from_pm"]
        assert notes is not None, f"{tid} expected notes_from_pm, got None"
        assert substr in notes, f"{tid}: expected {substr!r} in {notes!r}"


# ---------------------------------------------------------------------------
# Chunk 9 (PM I.1 § I — TT1-TT10 Deir el-Medina core)
# ---------------------------------------------------------------------------


def test_chunk9_uniform_null_phase_a_fields() -> None:
    """Every chunk-9 row carries null for Phase-A-enrichment fields
    (`dynasty`, `sub_period`, `date_bce_approx_start`, `date_bce_approx_end`,
    `discovery_year`, `discoverer`, `location_sub_area`).
    `source_citation.edition` is `PM I.1 2nd ed. 1960` (NOT the chunks 1-8
    `PM I.2 2nd ed. 1964` — chunk 9 is the first PM I.1 chunk).
    `source_citation.section` is exactly "I" (PM I.1 § I has no sub-letter
    for this range).
    `theban_area` is "Deir el-Medina" for every TT1-TT10 row (workmen's
    tombs at Deir el-Medina; sub-site shifts to Dra' Abu el-Naga at TT11+).
    `is_unfinished` is `false` for every row (PM I.1 prints no `Unfinished`
    flag in TT1-TT10).
    """
    for tid in CHUNK9_TOMB_IDS:
        r = _row(tid)
        assert r["theban_area"] == "Deir el-Medina", tid
        assert r["source_citation"]["edition"] == EDITION_PM_I1, tid
        assert r["source_citation"]["section"] == "I", tid
        assert r["dynasty"] is None, tid
        assert r["sub_period"] is None, tid
        assert r["date_bce_approx_start"] is None, tid
        assert r["date_bce_approx_end"] is None, tid
        assert r["discovery_year"] is None, tid
        assert r["discoverer"] is None, tid
        assert r["location_sub_area"] is None, tid
        assert r["is_unfinished"] is False, tid


def test_chunk9_all_rows_official_role() -> None:
    """All 10 TT1-TT10 occupants are Deir el-Medina workmen / scribes /
    foremen / chiseller / Chief in the Great Place — controlled-vocab
    flattens to `"Official"` for every row. The verbatim title clause
    (`Servant in the Place of Truth`, `Foremen in the Place of Truth`,
    `Chiseller of Amun in the Place of Truth`, `Scribe in the Place of
    Truth`, `Chief in the Great Place`) lives in `notes_from_pm`.
    """
    for tid in CHUNK9_TOMB_IDS:
        assert _row(tid)["occupant_role"] == "Official", (
            tid, _row(tid)["occupant_role"]
        )


def test_chunk9_occupant_names() -> None:
    """PM-faithful occupant_name per the README's diacritic policy
    (strip Ḥ on matchable field, preserve ayin, preserve underdot-Ḳ).
    `Raʿmose`/`Amenmose` use the project-wide -osi → -ose Anglicisation
    for downstream museum-data matching (Met / Brooklyn / TLA all use
    `Ramose`); chunk 9 retains the convention even though chunk 7
    preserved PM's `-osi` ending on `Kamosi`.
    """
    expected = {
        "TT1": "Sennezem",
        "TT2": "Khaʿbekhnet",
        "TT3": "Peshedu",
        "TT4": "Ḳen",
        "TT5": "Neferʿabet",
        "TT6": "Neferhotep",
        # PM I.1 p.15 prints `RAʿMOSI` not `Raʿmose` — chunk-9 third-pass
        # P1: PM's volume-wide `-osi` editorial convention preserved per
        # rule-1 (provenance) AND to disambiguate from TT55's RAʿMOSE
        # (Vizier of Amenhotep IV — different historical person).
        "TT7": "Raʿmosi",
        "TT8": "Khaʿ",
        # PM I.1 p.18 prints `AMENMOSI` — same `-osi` preservation rule
        # as TT7. Chunk-9 third-pass P1.
        "TT9": "Amenmosi",
        "TT10": "Penbuy",
    }
    for tid, name in expected.items():
        assert _row(tid)["occupant_name"] == name, (
            tid, _row(tid)["occupant_name"]
        )


def test_chunk9_source_citation_pages() -> None:
    """Printed page numbers per TT tomb (PM I.1 § I, printed pp.1-19,
    physical pp.19-37). Verified directly against the PDF in the
    chunk-9 egyptologist-reviewer pass.
    """
    expected_page = {
        "TT1": 1, "TT2": 6, "TT3": 9, "TT4": 11, "TT5": 12,
        "TT6": 14, "TT7": 15, "TT8": 16, "TT9": 18, "TT10": 19,
    }
    for tid, page in expected_page.items():
        actual = _row(tid)["source_citation"]["page"]
        assert actual == page, (tid, actual, page)


def test_chunk9_shared_with_tombs() -> None:
    """PM headwords' `(Also owner of tomb N.)` / `(Perhaps also owner of
    tomb N.)` / `(also owner of tombs N and M)` cross-references parse
    to `shared_with_tombs`. Three rows in scope; the rest empty.
    """
    expected = {
        "TT1": [],
        "TT2": [],
        "TT3": ["TT326"],
        "TT4": ["TT337"],   # PM "(Perhaps also owner of tomb 337.)"
        "TT5": [],
        "TT6": [],
        "TT7": ["TT212", "TT250"],  # PM "(also owner of tombs 212 and 250)"
        "TT8": [],
        "TT9": [],
        "TT10": [],
    }
    for tid, swt in expected.items():
        actual = _row(tid)["shared_with_tombs"]
        assert sorted(actual) == sorted(swt), (tid, actual, swt)


def test_chunk9_joint_burial_classification() -> None:
    """The TT1-TT10 range contains two multi-occupant headwords:

    - **TT6 (NEFERḤŌTEP and son NEBNŪFER, Foremen…)** is HIERARCHICAL.
      PM uses `X and son Y` — Neferhotep is the parent, syntactic head;
      Nebnufer is structurally subordinate. `is_joint_burial=false`,
      `co_occupants=[{name: "Nebnufer", role: "Official", alt_names: []}]`.
      Same shape as KV46 (`YUIA …, Divine father, AND THUIU …`).

    - **TT10 (PENBUY and KASA, Servants in the Place of Truth)** is
      COORDINATE. PM uses bare conjunction with plural role-clause; no
      syntactic primacy. `is_joint_burial=true`,
      `co_occupants=[{name: "Kasa", role: "Official", alt_names: []}]`.
      Same shape as SWV-ThreePrincesses (`MENHET, MERTI, AND MENWI`).

    The other 8 TT1-TT10 rows are single-occupant.
    """
    # TT6: hierarchical
    tt6 = _row("TT6")
    assert tt6["occupant_name"] == "Neferhotep"
    assert tt6["is_joint_burial"] is False
    assert tt6["co_occupants"] == [
        {"name": "Nebnufer", "role": "Official", "alt_names": []}
    ]

    # TT10: coordinate
    tt10 = _row("TT10")
    assert tt10["occupant_name"] == "Penbuy"
    assert tt10["is_joint_burial"] is True
    assert tt10["co_occupants"] == [
        {"name": "Kasa", "role": "Official", "alt_names": []}
    ]

    # Other 8 rows: single-occupant
    for tid in CHUNK9_TOMB_IDS - {"TT6", "TT10"}:
        r = _row(tid)
        assert r["co_occupants"] == [], (tid, r["co_occupants"])
        assert r["is_joint_burial"] is False, (tid, r["is_joint_burial"])


def test_chunk9_notes_from_pm_pinned_substrings() -> None:
    """Per-row `notes_from_pm` substring assertions. Every chunk-9 row
    has a populated `notes_from_pm` (PM I.1 headwords are dense — every
    row carries family clauses + role title + regnal/dynastic dating).
    Pinned substrings reflect the egyptologist-corrected forms after
    the chunk-9 reviewer pass: macrons preserved per chunk-3/7
    precedent, false underdots dropped where PM does not print one.
    """
    expected = {
        "TT1": "Father, Khaʿbekhnet (name on fragment, BRUYÈRE, Rapport (1927), fig. 34 [4]).",
        "TT2": "(L. D. Text, No. 107.) Parents, Sennezem (tomb 1)",
        "TT3": "Parents, Menna and Huy. Wife, Nezemtbehdet.",
        "TT4": "Chiseller of Amūn in the Place of Truth.",
        "TT5": "Parents, Neferronpet and Mahi (name on stela in Brit. Mus. 150, see infra, p. 14). Wife, Taēsi.",
        "TT6": "Wife (of Neferḥōtep), Iymau; (of Nebnūfer), Iy.",
        "TT7": "Parents, Amenemḥab and Kakaia. Wife, Mutemwia.",
        "TT8": "Chief in the Great Place.",
        "TT9": "Wife, Tent-hōm.",
        "TT10": "Father (of Penbuy), Iri (name from offering-table of Penbuy, in Turin Mus. 1559). Wives (of Penbuy), Amentetusert and Irnūfer; (of Kasa), Bukhaʿnef.",
    }
    for tid, substr in expected.items():
        notes = _row(tid)["notes_from_pm"]
        assert notes is not None, f"{tid} expected notes_from_pm, got None"
        assert substr in notes, f"{tid}: expected {substr!r} in {notes!r}"


def test_chunk9_no_redundant_double_period_after_biblio_paren() -> None:
    """`CHUNK9_CORRECTIONS` strips a redundant `.).` double-period that
    the merge majority introduced when two of three agents stitched the
    bibliographic close-paren with a paragraph-separator period. PM I.1
    prints `(L. D. Text, No. N.) <Next sentence>` with NO period after
    the close-paren (verified by egyptologist printed-source review on
    pp. 6, 14, 15, 16, 19 of the PDF).
    """
    for tid in CHUNK9_TOMB_IDS:
        notes = _row(tid)["notes_from_pm"]
        assert notes is None or ".)." not in notes, (
            f"{tid}: redundant `.).` double-period after biblio close-paren "
            f"slipped past CHUNK9_CORRECTIONS; got {notes!r}"
        )


def test_chunk9_tt2_attribution_certainty_overridden_to_attested() -> None:
    """TT2 `notes_from_pm` carries `Wives, Saḥte and (probably) Esi.`
    The context-free `_detect_attribution_certainty` regex fires on the
    `(probably)` token and would derive `attribution_certainty="probable"`,
    BUT PM's hedge applies to the wife identification (Esi), not to
    Khaʿbekhnet's primary occupant attribution. The per-row
    `DERIVER_OVERRIDES` mechanism in `fix_rows.py` pins TT2 back to
    `"attested"` post-derivation. This test asserts the override is
    actually winning — if a future refactor of `_apply_issue_182_migrations`
    silently reverts the override order, this test catches it.
    """
    tt2 = _row("TT2")
    assert tt2["attribution_certainty"] == "attested", (
        f"TT2 must carry `attribution_certainty='attested'` despite the "
        f"`(probably)` hedge in `notes_from_pm` (the hedge applies to wife "
        f"Esi, not Khaʿbekhnet); got {tt2['attribution_certainty']!r}. "
        f"Verify that DERIVER_OVERRIDES in fix_rows.py is being applied "
        f"AFTER the regex pass."
    )
    # Also verify the (probably) token is still in notes — the override
    # must NOT silently strip the verbatim PM hedge.
    assert "(probably)" in (tt2["notes_from_pm"] or ""), (
        "TT2 notes_from_pm must preserve PM's verbatim `(probably)` "
        "hedge; the deriver override must not strip the source text."
    )


def test_chunk9_postprocess_j_period_i_normalisation() -> None:
    """`postprocess.py` Phase-1 substitution `J.I → Ḥ` (added in chunk 9
    for the single TT6 site `NEFERJ.IOTEP`) must produce `Neferhotep`
    in the row's `occupant_name` after the README's strip-Ḥ rule.
    Mechanical assertion that the postprocess + strip-Ḥ chain works.
    """
    tt6 = _row("TT6")
    # occupant_name is the matchable field — strip-Ḥ applies.
    assert tt6["occupant_name"] == "Neferhotep", tt6["occupant_name"]
    # notes_from_pm is verbatim-preserve — Ḥ stays. Verify the underdot
    # is preserved on `Neferḥōtep` and `Ḥaremḥab` in the wife-clause.
    notes = tt6["notes_from_pm"]
    assert "Ḥaremḥab" in notes, notes
    assert "Neferḥōtep" in notes, notes


# ---------------------------------------------------------------------------
# Chunk 9: LEGACY_FIELD_RENAMES regression tripwire
# ---------------------------------------------------------------------------


def test_chunk9_legacy_field_renames_migration_applied() -> None:
    """`fix_rows.LEGACY_FIELD_RENAMES` mechanism (chunk-9 PR) renames
    `valley` → `theban_area` on every load to enforce the post-#170
    rename invariant.

    PR #170 renamed the field by editing reconciled.jsonl directly
    without updating the per-chunk agent JSONLs (which remain the
    stable record of each round of agent extraction). Re-running
    merge.py therefore regenerates rows with the OLD `valley` key.
    The migration in `fix_rows.main()` enforces the rename on every
    load so the convention can no longer silently regress.

    This test exercises the migration path directly (not via the
    on-disk reconciled.jsonl): construct a synthetic in-memory row
    carrying `valley`, run the legacy-rename block, assert the
    output. Per CLAUDE.md rule 3 (deterministic enforcement over
    convention), the migration must convert the post-#170 rename
    convention into a code-level enforcement — and it must have a
    tripwire test, otherwise the next reviewer wonders whether the
    migration would actually fire if a future re-merge brought the
    legacy key back. Per code-reviewer P3-3 on PR #196.
    """
    fix_rows = _import_fix_rows()
    assert fix_rows.LEGACY_FIELD_RENAMES == {"valley": "theban_area"}, (
        fix_rows.LEGACY_FIELD_RENAMES
    )

    # Reproduce the inline migration from `fix_rows.main()` against a
    # synthetic 3-row fixture covering the three valid input shapes:
    #   1. row with only `valley` (the merge regression case)
    #   2. row with only `theban_area` (already migrated)
    #   3. row with both keys carrying equal values (idempotent collision)
    rows = [
        {"tomb_id": "SYNTH1", "valley": "Valley of the Kings"},
        {"tomb_id": "SYNTH2", "theban_area": "Valley of the Queens"},
        {
            "tomb_id": "SYNTH3",
            "valley": "Deir el-Medina",
            "theban_area": "Deir el-Medina",
        },
    ]
    for old_key, new_key in fix_rows.LEGACY_FIELD_RENAMES.items():
        for row in rows:
            if old_key in row:
                if new_key in row:
                    if row[old_key] != row[new_key]:
                        raise ValueError(
                            f"row {row.get('tomb_id')!r} carries both "
                            f"{old_key!r} and {new_key!r} with different "
                            f"values; resolve before merging."
                        )
                    del row[old_key]
                else:
                    row[new_key] = row.pop(old_key)

    # SYNTH1 (only `valley`): renamed.
    assert "valley" not in rows[0]
    assert rows[0]["theban_area"] == "Valley of the Kings"
    # SYNTH2 (only `theban_area`): unchanged.
    assert "valley" not in rows[1]
    assert rows[1]["theban_area"] == "Valley of the Queens"
    # SYNTH3 (both, equal values): legacy key dropped.
    assert "valley" not in rows[2]
    assert rows[2]["theban_area"] == "Deir el-Medina"


def test_chunk9_legacy_field_renames_value_conflict_raises() -> None:
    """When both `valley` and `theban_area` carry DIFFERENT values on the
    same row, the migration MUST raise — silently picking either side
    would let a real conflict slip into reconciled.jsonl. Per CLAUDE.md
    rule 2 (no defensive programming, loud failures).
    """
    rows = [
        {
            "tomb_id": "SYNTH-CONFLICT",
            "valley": "Valley of the Kings",
            "theban_area": "Valley of the Queens",
        },
    ]
    import pytest

    with pytest.raises(ValueError, match="carries both"):
        for old_key, new_key in {"valley": "theban_area"}.items():
            for row in rows:
                if old_key in row and new_key in row:
                    if row[old_key] != row[new_key]:
                        raise ValueError(
                            f"row {row.get('tomb_id')!r} carries both "
                            f"{old_key!r} and {new_key!r} with different "
                            f"values; resolve before merging."
                        )


# ---------------------------------------------------------------------------
# Audit-trail tests for fix_rows.py
# ---------------------------------------------------------------------------


def _import_fix_rows():
    """Load the source's fix_rows.py module by file path (the directory has a
    hyphen so `importlib.import_module` doesn't work directly).
    """
    spec = importlib.util.spec_from_file_location(
        "pm_theban_fix_rows", SOURCE_DIR / "fix_rows.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_all_corrections_includes_every_chunk_list() -> None:
    """fix_rows.py's `ALL_CORRECTIONS` aggregates every `CHUNK*_CORRECTIONS`
    list AND the source-wide audit-fix list (`AUDIT_FIX_CORRECTIONS`).
    Dropping any of them silently destroys the audit trail — this test fails
    loud if either list is added without being aggregated.

    Uses natural-numeric sort on the chunk suffix (NOT lexicographic sort)
    so the test stays correct at chunk 10+. Gemini code-review on PR #71
    flagged that the prior lex-sort would mis-order `CHUNK10` before
    `CHUNK2`, invalidating the equality assertion against a numerically-
    ordered `ALL_CORRECTIONS`.

    `AUDIT_FIX_CORRECTIONS` (PR A, 2026-05-02) is appended after the chunk
    lists since it is structurally different — a one-shot source-wide
    schema migration, not a chunk-specific reviewer pass.
    """
    fix_rows = _import_fix_rows()
    chunk_re = re.compile(r"^CHUNK(\d+)_CORRECTIONS$")
    chunk_attrs = sorted(
        (attr for attr in dir(fix_rows) if chunk_re.match(attr)),
        key=lambda attr: int(chunk_re.match(attr).group(1)),
    )
    expected = [getattr(fix_rows, a) for a in chunk_attrs] + [
        fix_rows.AUDIT_FIX_CORRECTIONS,
    ]
    assert fix_rows.ALL_CORRECTIONS == expected, (
        f"ALL_CORRECTIONS missing one of the correction lists. "
        f"Found chunk attrs: {chunk_attrs}; expected trailing entry "
        f"AUDIT_FIX_CORRECTIONS."
    )


def test_all_renames_includes_every_chunk_dict() -> None:
    """fix_rows.py's `ALL_RENAMES` aggregates every `CHUNK*_RENAMES` dict.
    Analogous to `test_all_corrections_includes_every_chunk_list` — dropping
    a per-chunk rename dict silently destroys its audit trail so a
    reconciled.jsonl pulled from a fresh merge would contain the pre-rename
    tomb_ids without `fix_rows.py` catching the omission.

    Gemini code-review on PR #100 round 3 flagged the lack of this
    validation test. Uses the same natural-numeric chunk-suffix sort as
    `ALL_CORRECTIONS`'s test so chunk 10+ ordering stays correct.
    """
    fix_rows = _import_fix_rows()
    chunk_re = re.compile(r"^CHUNK(\d+)_RENAMES$")
    chunk_attrs = sorted(
        (attr for attr in dir(fix_rows) if chunk_re.match(attr)),
        key=lambda attr: int(chunk_re.match(attr).group(1)),
    )
    expected: dict[str, str] = {}
    for a in chunk_attrs:
        expected.update(getattr(fix_rows, a))
    assert fix_rows.ALL_RENAMES == expected, (
        f"ALL_RENAMES missing one of the per-chunk dicts. "
        f"Found chunk attrs: {chunk_attrs}"
    )


def test_fix_rows_main_idempotent() -> None:
    """`fix_rows.main()` is idempotent: a second call produces byte-identical
    `reconciled.jsonl` and `merge-disagreements.txt` to a first call (PR
    #169 code-reviewer P1-1).

    Three idempotence claims live in `fix_rows.py` docstrings/comments:
    the field-add pass (`SCHEMA_FIELD_DEFAULTS`), the override pass
    (`SPOT_CORRECTIONS`), and the diff-section append-or-replace logic.
    Per CLAUDE.md rule 3 (deterministic enforcement over convention), an
    idempotence claim that lives only in a docstring is a suggestion, not
    a guarantee — the next refactor of `main()` (e.g. someone changes the
    field-add pass to use `setdefault` plus a logger that always appends)
    silently regresses on disk. A single round-trip byte-equality test
    catches all three regressions.

    Idempotence in this codebase means `f(f(x)) == f(x)` — the output is
    stable from the second run onward, not necessarily on the first run
    after a state transition. So the test calls main() to reach steady
    state, snapshots, then calls again and compares. The pre-existing
    on-disk state (which may include "corrected this run" log lines from
    a recent commit-time run) is restored after the test so the working
    tree stays clean.
    """
    fix_rows = _import_fix_rows()
    reconciled = SOURCE_DIR / "reconciled.jsonl"
    diff = SOURCE_DIR / "merge-disagreements.txt"

    pre_reconciled = reconciled.read_bytes()
    pre_diff = diff.read_bytes()
    try:
        # First run: reach steady state regardless of what was on disk
        # at test-entry (which may have transitional log lines).
        fix_rows.main()
        snap_reconciled = reconciled.read_bytes()
        snap_diff = diff.read_bytes()
        # Second run: must be byte-identical (the idempotence contract).
        fix_rows.main()
        new_reconciled = reconciled.read_bytes()
        new_diff = diff.read_bytes()
        assert new_reconciled == snap_reconciled, (
            "fix_rows.main() is NOT idempotent on reconciled.jsonl — second "
            "call produced a different byte-string from the first."
        )
        assert new_diff == snap_diff, (
            "fix_rows.main() is NOT idempotent on merge-disagreements.txt — "
            "second call produced a different byte-string from the first. "
            "The LLM-APPLIED OVERRIDES section's append-or-replace logic "
            "must produce identical output across re-runs."
        )
    finally:
        # Restore the original on-disk state so the working tree stays
        # clean even if the test fails.
        reconciled.write_bytes(pre_reconciled)
        diff.write_bytes(pre_diff)


# ── Closure tests (#182) — typed flags from notes_from_pm derivation ───

_REQUIRED_182_KEYS = ("is_uninscribed", "is_usurped", "attribution_certainty")
_ATTRIBUTION_VOCAB = {"attested", "probable", "uncertain"}


def test_182_every_row_has_typed_flags() -> None:
    """Every row carries all 3 typed fields introduced in #182."""
    for r in _rows():
        for key in _REQUIRED_182_KEYS:
            assert key in r, (r["tomb_id"], key)


def test_182_attribution_certainty_in_vocab() -> None:
    """attribution_certainty ∈ {attested, probable, uncertain}."""
    for r in _rows():
        assert r["attribution_certainty"] in _ATTRIBUTION_VOCAB, (
            r["tomb_id"], r["attribution_certainty"]
        )


def test_182_uninscribed_canonical_set() -> None:
    """Rows where PM literally writes "uninscribed" in notes_from_pm.
    Pinned 2026-05-03: KV39 ('Uninscribed tomb...'), KV56 ("'Gold tomb',
    uninscribed."), DAN-Neferhotep ('Rock-tomb, uninscribed')."""
    expected = {"KV39", "KV56", "DAN-Neferhotep"}
    actual = {r["tomb_id"] for r in _rows() if r["is_uninscribed"]}
    assert actual == expected, sorted(actual)


def test_182_usurped_canonical_set() -> None:
    """Rows where PM writes "usurp(ed|ation)" in notes_from_pm.
    Pinned 2026-05-03: KV9 (doorways usurped from Ramesses V), KV14
    (usurped by Setnakht)."""
    expected = {"KV9", "KV14"}
    actual = {r["tomb_id"] for r in _rows() if r["is_usurped"]}
    assert actual == expected, sorted(actual)


def test_182_uncertain_attribution_canonical_set() -> None:
    """Rows where PM uses strong-uncertainty hedge tokens (uncertain,
    perhaps, possibly, tentatively) OR PM's `(?)` glyph. Pinned
    2026-05-03: 5 rows. Per Gemini round-2 — `(?)` is PM's standard
    attribution-uncertainty marker (KV42 + QV60 notes start with
    `(?)`, QV33 carries `Dyn. XX(?)`)."""
    expected = {
        "DAN-KamosiWazkheperre",
        "DAN-SebkemsafSekhemreShedtaui",
        "KV42",
        "QV33",
        "QV60",
    }
    actual = {r["tomb_id"] for r in _rows() if r["attribution_certainty"] == "uncertain"}
    assert actual == expected, sorted(actual)


def test_182_probable_attribution_canonical_set() -> None:
    """Rows where PM writes "Probably" or "attributed to" in notes_from_pm.
    Pinned 2026-05-03: 7 rows."""
    expected = {
        "DAN-AhmosiNefertere", "DAN-AntefSekhemreHeruhirmaet",
        "DAN-Neferhotep", "KV39", "KV55", "QV46", "SWV-Neferure",
    }
    actual = {r["tomb_id"] for r in _rows() if r["attribution_certainty"] == "probable"}
    assert actual == expected, sorted(actual)
