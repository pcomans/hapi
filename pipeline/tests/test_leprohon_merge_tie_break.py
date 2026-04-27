"""Unit tests for Leprohon merge.py's tie-break enforcement.

Covers (issue #128):
  * Pre-merge MdC → IFAO transliteration normalisation collapses
    encoding-style ties before the majority vote.
  * `_majority` raises on unresolved IDENTIFIER ties (no override,
    no clear majority) — option (a) enforcement, "data is sacred,
    fail loudly".
  * `TIE_BREAK_OVERRIDES` lookup resolves IDENTIFIER ties when an
    explicit override exists.
  * Prose-only ties (only `source_note` / `attested_in` differ) are
    resolved deterministically by `_resolve_prose_tie`.
  * Tie classification (IDENTIFIER / STRUCTURE / PROSE / SCALAR) is
    correct.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SOURCE_DIR = (
    Path(__file__).parent.parent
    / "pipeline" / "authority" / "sources" / "leprohon-2013-titulary"
)
MERGE_PY = SOURCE_DIR / "merge.py"


@pytest.fixture(scope="module")
def merge_module():
    spec = importlib.util.spec_from_file_location("leprohon_merge", MERGE_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# === Pre-merge translit normalisation ====================================

def test_normalise_translit_mdc_to_canonical(merge_module):
    """MdC capitals → canonical IFAO codepoints per transcribe.md."""
    n = merge_module._normalise_translit
    assert n("HqA tAwy") == "ḥḳꜣ tꜣwy"   # H→ḥ, q→ḳ, A→ꜣ, T→ṯ
    assert n("kAw nTrw") == "kꜣw nṯrw"   # plain `k` unchanged; A→ꜣ, T→ṯ
    assert n("xpr") == "ḫpr"             # x→ḫ
    assert n("XnSw") == "ẖnšw"           # X→ẖ, S→š


def test_normalise_translit_fallback_codepoints(merge_module):
    """ɜ/ɛ/ˁ codepoint fallbacks → canonical ꜣ/ꜥ."""
    n = merge_module._normalise_translit
    assert n("ɜsmsw") == "ꜣsmsw"
    assert n("ɛnh") == "ꜥnh"


def test_normalise_translit_passthrough_canonical(merge_module):
    """Already-canonical strings unchanged."""
    n = merge_module._normalise_translit
    assert n("ḥḳꜣ tꜣwy") == "ḥḳꜣ tꜣwy"


def test_normalise_for_merge_only_translit_subfield(merge_module):
    """MdC normalisation applies ONLY to the transliteration sub-field
    of name-list entries — NOT to source_note (which contains English
    prose with letters that look like MdC capitals like 'H' in 'Horus')
    and NOT to other top-level fields."""
    row = {
        "leprohon_id": "leprohon-X.01",
        "horus_names": [
            {
                "transliteration": "HqA tAwy",  # MdC → should normalise
                "anglicised": "heqa tawy",
                "translation": "Ruler of the Two Lands",
                "source_note": "Horus is the king of the Two Lands.",  # English; must NOT normalise
                "variant_index": 1,
                "is_variant": False,
                "attested_in": [],
            }
        ],
        "display_name": "Test king",
    }
    out = merge_module._normalise_for_merge(row)
    entry = out["horus_names"][0]
    assert entry["transliteration"] == "ḥḳꜣ tꜣwy"
    # Source note unchanged — would have become "ṯhe king" otherwise
    assert entry["source_note"] == "Horus is the king of the Two Lands."
    # Top-level field unchanged
    assert out["display_name"] == "Test king"


def test_normalise_for_merge_pure_function(merge_module):
    """Does not mutate input."""
    row = {"horus_names": [{"transliteration": "HqA"}]}
    original = {"horus_names": [{"transliteration": "HqA"}]}
    merge_module._normalise_for_merge(row)
    assert row == original


# === _majority — unanimous and clear majority ============================

def test_majority_unanimous_returns_value(merge_module):
    """All three agents agree → value, count = 3."""
    values = ["a", "a", "a"]
    chosen, count = merge_module._majority(values, lid="leprohon-X.01", field="display_name")
    assert chosen == "a"
    assert count == 3


def test_majority_clear_majority_returns_majority_value(merge_module):
    """Two agree, one differs → majority value, count = 2."""
    values = ["a", "a", "b"]
    chosen, count = merge_module._majority(values, lid="leprohon-X.01", field="display_name")
    assert chosen == "a"
    assert count == 2


# === _majority — tie with explicit override ==============================

def test_majority_tie_with_override_uses_override(merge_module):
    """1/1/1 IDENTIFIER tie with a TIE_BREAK_OVERRIDES entry → override value."""
    # Inject a temporary override.
    key = ("leprohon-test.99", "horus_names")
    merge_module.TIE_BREAK_OVERRIDES[key] = {
        "value": "RESOLVED",
        "rationale": "test",
    }
    try:
        values = [
            [{"transliteration": "x", "variant_index": 1, "is_variant": False,
              "anglicised": "x", "translation": "x", "source_note": None,
              "attested_in": []}],
            [{"transliteration": "y", "variant_index": 1, "is_variant": False,
              "anglicised": "y", "translation": "y", "source_note": None,
              "attested_in": []}],
            [{"transliteration": "z", "variant_index": 1, "is_variant": False,
              "anglicised": "z", "translation": "z", "source_note": None,
              "attested_in": []}],
        ]
        chosen, count = merge_module._majority(
            values, lid="leprohon-test.99", field="horus_names"
        )
        assert chosen == "RESOLVED"
    finally:
        del merge_module.TIE_BREAK_OVERRIDES[key]


# === _majority — tie raises on uncovered IDENTIFIER ======================

def test_majority_tie_uncovered_identifier_raises(merge_module):
    """1/1/1 IDENTIFIER tie with NO override → ValueError naming
    candidates and pointing at TIE_BREAK_OVERRIDES."""
    values = [
        [{"transliteration": "x", "variant_index": 1, "is_variant": False,
          "anglicised": "x", "translation": "x", "source_note": None,
          "attested_in": []}],
        [{"transliteration": "y", "variant_index": 1, "is_variant": False,
          "anglicised": "y", "translation": "y", "source_note": None,
          "attested_in": []}],
        [{"transliteration": "z", "variant_index": 1, "is_variant": False,
          "anglicised": "z", "translation": "z", "source_note": None,
          "attested_in": []}],
    ]
    with pytest.raises(ValueError) as exc:
        merge_module._majority(
            values, lid="leprohon-uncov.99", field="horus_names"
        )
    msg = str(exc.value)
    assert "Unresolved IDENTIFIER tie" in msg
    assert "leprohon-uncov.99" in msg
    assert "horus_names" in msg
    assert "TIE_BREAK_OVERRIDES" in msg


def test_majority_tie_uncovered_structure_raises(merge_module):
    """1/1/1 STRUCTURE tie (different list lengths) → ValueError."""
    values = [
        [{"transliteration": "x", "variant_index": 1, "is_variant": False,
          "anglicised": "x", "translation": "x", "source_note": None,
          "attested_in": []}],
        [
            {"transliteration": "x", "variant_index": 1, "is_variant": False,
             "anglicised": "x", "translation": "x", "source_note": None,
             "attested_in": []},
            {"transliteration": "y", "variant_index": 2, "is_variant": True,
             "anglicised": "y", "translation": "y", "source_note": None,
             "attested_in": []},
        ],
        [
            {"transliteration": "x", "variant_index": 1, "is_variant": False,
             "anglicised": "x", "translation": "x", "source_note": None,
             "attested_in": []},
            {"transliteration": "y", "variant_index": 2, "is_variant": True,
             "anglicised": "y", "translation": "y", "source_note": None,
             "attested_in": []},
            {"transliteration": "z", "variant_index": 3, "is_variant": True,
             "anglicised": "z", "translation": "z", "source_note": None,
             "attested_in": []},
        ],
    ]
    with pytest.raises(ValueError) as exc:
        merge_module._majority(
            values, lid="leprohon-struct.99", field="horus_names"
        )
    assert "Unresolved STRUCTURE tie" in str(exc.value)


# === _majority — prose tie resolved deterministically ====================

def test_majority_tie_prose_unions_attested_in(merge_module):
    """1/1/1 with only attested_in differing → all citations are
    UNIONED, not dropped. Earlier rule was shortest-wins on the full
    JSON, which silently discarded real provenance. Gemini PR #128
    round-1 P1 finding."""
    a = [{"transliteration": "x", "variant_index": 1, "is_variant": False,
          "anglicised": "x", "translation": "x", "source_note": None,
          "attested_in": ["Karnak Cachette"]}]
    b = [{"transliteration": "x", "variant_index": 1, "is_variant": False,
          "anglicised": "x", "translation": "x", "source_note": None,
          "attested_in": ["Turin 8,21"]}]
    c = [{"transliteration": "x", "variant_index": 1, "is_variant": False,
          "anglicised": "x", "translation": "x", "source_note": None,
          "attested_in": ["Abydos king-list"]}]
    chosen, _ = merge_module._majority(
        [a, b, c], lid="leprohon-att.99", field="horus_names"
    )
    # All three citations are present (order is deterministic but
    # implementation-dependent — assert as a set).
    assert set(chosen[0]["attested_in"]) == {
        "Karnak Cachette", "Turin 8,21", "Abydos king-list"
    }


def test_majority_tie_prose_unions_attested_in_dedup(merge_module):
    """If two agents share a citation, it's preserved once (deduplicated)."""
    a = [{"transliteration": "x", "variant_index": 1, "is_variant": False,
          "anglicised": "x", "translation": "x", "source_note": None,
          "attested_in": ["Karnak Cachette", "Turin 8,21"]}]
    b = [{"transliteration": "x", "variant_index": 1, "is_variant": False,
          "anglicised": "x", "translation": "x", "source_note": None,
          "attested_in": ["Karnak Cachette"]}]
    c = [{"transliteration": "x", "variant_index": 1, "is_variant": False,
          "anglicised": "x", "translation": "x", "source_note": None,
          "attested_in": ["Abydos king-list"]}]
    chosen, _ = merge_module._majority(
        [a, b, c], lid="leprohon-att.99", field="horus_names"
    )
    # Karnak Cachette appears once even though two agents emitted it.
    assert chosen[0]["attested_in"].count("Karnak Cachette") == 1
    assert set(chosen[0]["attested_in"]) == {
        "Karnak Cachette", "Turin 8,21", "Abydos king-list"
    }


def test_leprohon_21_02_source_citation_is_138_159(merge_module):
    """Invariant pin per code-reviewer round-1 P2-4.

    leprohon-21.02 (Smendes / Nesbanebdjed) had a 1/1/1 source_citation
    tie; agent A=printed-139, B=printed-138, C=(printed-137, physical-158).
    The OCR running header at chunk-p157-p173-pypdf.md line 95 ('138 THE
    GR EAT NAME') confirms Smendes' headword (line 110) is on printed
    138 / physical 159. Both the previous fix_rows SPOT_CORRECTION and
    the current TIE_BREAK_OVERRIDES entry agree on these values; this
    test pins them on the loaded reconciled.jsonl so a future
    re-extraction or re-aggregation can't drift back to one of the
    wrong agent values.
    """
    import json
    reconciled_path = SOURCE_DIR / "reconciled.jsonl"
    rows = [json.loads(line) for line in reconciled_path.read_text().splitlines() if line.strip()]
    smendes = [r for r in rows if r.get("leprohon_id") == "leprohon-21.02"]
    assert len(smendes) == 1
    citation = smendes[0]["source_citation"]
    assert citation["printed_page"] == 138
    assert citation["physical_pdf_page"] == 159
    assert citation["book"] == "Leprohon 2013"
    assert citation["edition"] == "SBL Writings from the Ancient World 33"


def test_majority_requires_lid_and_field(merge_module):
    """Constitutional rule 10: no backwards compatibility shim. The
    previous signature accepted Optional lid/field with a silent
    first-seen fallback for "legacy callers" — that path was the
    exact slop pattern this module exists to kill. Now keyword-only
    required."""
    import pytest as _pytest
    with _pytest.raises(TypeError):
        merge_module._majority(["a", "b", "c"])
    with _pytest.raises(TypeError):
        merge_module._majority(["a", "b", "c"], lid="x.01")
    with _pytest.raises(TypeError):
        merge_module._majority(["a", "b", "c"], field="display_name")


def test_majority_tie_prose_resolves_to_shortest(merge_module):
    """1/1/1 with only source_note differing → deterministic shortest-wins.
    Shorter source_notes are typically closer-to-source (less editorial
    scaffolding like 'Per Leprohon fn. N:' prefixes, fewer paraphrased
    interpretations). The 3-arbiter sweeps repeatedly identified
    'shortest = most verbatim' as the right disposition."""
    short = [{"transliteration": "x", "variant_index": 1, "is_variant": False,
              "anglicised": "x", "translation": "x",
              "source_note": "Gauthier 1907.", "attested_in": []}]
    medium = [{"transliteration": "x", "variant_index": 1, "is_variant": False,
               "anglicised": "x", "translation": "x",
               "source_note": "Per Leprohon fn. 5: Gauthier 1907.",
               "attested_in": []}]
    longest = [{"transliteration": "x", "variant_index": 1, "is_variant": False,
                "anglicised": "x", "translation": "x",
                "source_note": "Per Leprohon fn. 5: Gauthier 1907. Editorial paraphrase added by extraction agent.",
                "attested_in": []}]
    values = [short, medium, longest]
    chosen, _ = merge_module._majority(
        values, lid="leprohon-prose.99", field="horus_names"
    )
    assert chosen[0]["source_note"] == "Gauthier 1907."


def test_majority_tie_prose_deterministic_across_orderings(merge_module):
    """Same 3 values in different agent-order → same result (resolution
    is order-independent)."""
    a = [{"transliteration": "x", "variant_index": 1, "is_variant": False,
          "anglicised": "x", "translation": "x",
          "source_note": "AAAA", "attested_in": []}]
    b = [{"transliteration": "x", "variant_index": 1, "is_variant": False,
          "anglicised": "x", "translation": "x",
          "source_note": "BBBB", "attested_in": []}]
    c = [{"transliteration": "x", "variant_index": 1, "is_variant": False,
          "anglicised": "x", "translation": "x",
          "source_note": "CCCC", "attested_in": []}]
    r1, _ = merge_module._majority([a, b, c], lid="x.01", field="horus_names")
    r2, _ = merge_module._majority([c, b, a], lid="x.01", field="horus_names")
    r3, _ = merge_module._majority([b, a, c], lid="x.01", field="horus_names")
    assert r1 == r2 == r3
    # All same length → lex-smallest wins (deterministic).
    assert r1[0]["source_note"] == "AAAA"


# === _classify_tie =======================================================

def test_classify_identifier_tie_on_transliteration(merge_module):
    values = [
        [{"transliteration": "x", "variant_index": 1, "is_variant": False,
          "anglicised": "a", "translation": "t",
          "source_note": None, "attested_in": []}],
        [{"transliteration": "y", "variant_index": 1, "is_variant": False,
          "anglicised": "a", "translation": "t",
          "source_note": None, "attested_in": []}],
        [{"transliteration": "z", "variant_index": 1, "is_variant": False,
          "anglicised": "a", "translation": "t",
          "source_note": None, "attested_in": []}],
    ]
    assert merge_module._classify_tie("horus_names", values) == "IDENTIFIER"


def test_classify_prose_tie_on_source_note_only(merge_module):
    values = [
        [{"transliteration": "x", "variant_index": 1, "is_variant": False,
          "anglicised": "a", "translation": "t",
          "source_note": "p1", "attested_in": []}],
        [{"transliteration": "x", "variant_index": 1, "is_variant": False,
          "anglicised": "a", "translation": "t",
          "source_note": "p2", "attested_in": []}],
        [{"transliteration": "x", "variant_index": 1, "is_variant": False,
          "anglicised": "a", "translation": "t",
          "source_note": "p3", "attested_in": []}],
    ]
    assert merge_module._classify_tie("horus_names", values) == "PROSE"


def test_classify_structure_tie_on_different_lengths(merge_module):
    values = [
        [{"transliteration": "x", "variant_index": 1, "is_variant": False,
          "anglicised": "a", "translation": "t",
          "source_note": None, "attested_in": []}],
        [],
        [{"transliteration": "x", "variant_index": 1, "is_variant": False,
          "anglicised": "a", "translation": "t",
          "source_note": None, "attested_in": []}] * 2,
    ]
    assert merge_module._classify_tie("horus_names", values) == "STRUCTURE"


def test_classify_scalar_field_is_scalar(merge_module):
    """Non-name-list field is classified SCALAR (treated as IDENTIFIER
    for tie-handling — needs override, not deterministic resolution)."""
    values = ["a", "b", "c"]
    assert merge_module._classify_tie("display_name", values) == "SCALAR"


def test_classify_non_dict_entry_at_position_is_structure(merge_module):
    """If any agent emits a non-dict at a list position (e.g. a string
    instead of the schema's dict shape), treat as STRUCTURE — a real
    schema mismatch. Previous behaviour silently coerced to {},
    erasing the IDENTIFIER signal. Gemini round-1 finding on PR #128.
    """
    values = [
        [{"transliteration": "x", "anglicised": "x", "translation": "x",
          "variant_index": 1, "is_variant": False, "source_note": None,
          "attested_in": []}],
        ["string_instead_of_dict"],  # malformed entry
        [{"transliteration": "y", "anglicised": "y", "translation": "y",
          "variant_index": 1, "is_variant": False, "source_note": None,
          "attested_in": []}],
    ]
    assert merge_module._classify_tie("horus_names", values) == "STRUCTURE"


def test_classify_key_presence_diff_is_identifier(merge_module):
    """If agents disagree on whether a key is PRESENT (one emits
    transliteration, others don't), that's an IDENTIFIER diff — must
    not slip into PROSE. Previous behaviour only checked agreement on
    keys at-least-one agent emitted, missing presence/absence diffs.
    Gemini round-1 finding on PR #128.
    """
    values = [
        [{"transliteration": "x", "anglicised": "x", "translation": "x",
          "variant_index": 1, "is_variant": False, "source_note": None,
          "attested_in": []}],
        [{"anglicised": "x", "translation": "x",
          "variant_index": 1, "is_variant": False, "source_note": None,
          "attested_in": []}],  # transliteration ABSENT
        [{"anglicised": "x", "translation": "x",
          "variant_index": 1, "is_variant": False, "source_note": None,
          "attested_in": []}],  # transliteration ABSENT
    ]
    assert merge_module._classify_tie("horus_names", values) == "IDENTIFIER"


def test_classify_source_note_presence_diff_is_prose(merge_module):
    """Conversely: if agents disagree on whether source_note is
    present (some emit None, some omit the key entirely, some emit a
    string), that's still a PROSE diff (source_note isn't an
    IDENTIFIER sub-field), so it gets the deterministic shortest-wins
    treatment, not a raise."""
    values = [
        [{"transliteration": "x", "anglicised": "x", "translation": "x",
          "variant_index": 1, "is_variant": False, "source_note": "p1",
          "attested_in": []}],
        [{"transliteration": "x", "anglicised": "x", "translation": "x",
          "variant_index": 1, "is_variant": False, "source_note": None,
          "attested_in": []}],
        [{"transliteration": "x", "anglicised": "x", "translation": "x",
          "variant_index": 1, "is_variant": False,
          "attested_in": []}],  # source_note key ABSENT entirely
    ]
    assert merge_module._classify_tie("horus_names", values) == "PROSE"


# === SCALAR tie raises ===================================================

def test_majority_tie_scalar_raises(merge_module):
    """1/1/1 on a scalar field (display_name etc.) without override → ValueError.
    Scalar fields are load-bearing (Phase-A consumers match against display_name);
    silent first-seen-pick is unsafe."""
    values = ["A", "B", "C"]
    with pytest.raises(ValueError) as exc:
        merge_module._majority(
            values, lid="leprohon-scalar.99", field="display_name"
        )
    assert "Unresolved SCALAR tie" in str(exc.value)
