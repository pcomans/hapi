"""Tests for Baud 1999 — Famille royale et pouvoir sous l'Ancien Empire.

Per rule 5 these tests assert specific values, not absence of errors.
At this stage the source directory is scaffolding-only — no
`reconciled.jsonl` yet because chunk 1 extraction awaits a Claude
Code session with Task-tool access to spawn the three independent
extraction subagents per ADR-017 (see `docs/handoff-baud-next-chunk.md`).

What these tests DO cover:

1. **Scaffolding files exist** — README, transcribe.md, prompt.md,
   merge.py, fix_rows.py, raw/.gitkeep. Absence of any of these
   means the scaffolding PR regressed.
2. **`merge.py` invariants** — `_load` raises on malformed or
   duplicate `baud_id`; `_load_agent_chunks` raises on cross-chunk
   duplicates; `_majority` and `_normalise_value` behave per their
   docstrings; `SENTINEL_NULL_STRINGS` includes the French
   `"inconnue"` / `"inconnu"`.
3. **`fix_rows.py` derived-field logic** — the French-date
   parser maps Roman dynasty tokens correctly, falls back to the
   king-name lookup, preserves hedges on `king_father`, and the
   redirect-row normaliser nulls every non-redirect field.
4. **`apply_overrides` end-to-end** — feed a small fixture of
   representative rows (redirect stub, flagship, Inconnue parent,
   multi-dynasty hedged date) and assert every expected derivation.

When chunk 1 `reconciled.jsonl` lands, this file gains:

- `test_row_count_exact` — pin the chunk-1 row count.
- `test_baud_id_shape_regex` — every `baud_id` matches `^\\d{3}$`.
- `test_baud_id_uniqueness` — no duplicates.
- `test_every_row_has_source_citation` with the pinned edition
  string.
- A per-row flagship test (e.g. `test_entry_003_jhtj_htp_full_fields`)
  asserting every populated field on `[3]`.
- Edge-case regressions (redirect stub `[9]`, asterisk rows `[4]`
  `[5]` `[7]` `[10]` `[11]`, `[1]` headword-with-lacuna,
  `[17]` multi-page sprawl).

These will be added by the chunk-1-extraction PR, not this scaffolding PR.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

SOURCE_DIR = (
    Path(__file__).parent.parent
    / "pipeline"
    / "authority"
    / "sources"
    / "baud-1999-ok-royal-family"
)

# ---------------------------------------------------------------------------
# 1. Scaffolding files.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename",
    [
        "README.md",
        "transcribe.md",
        "prompt.md",
        "merge.py",
        "fix_rows.py",
        "raw/.gitkeep",
    ],
)
def test_scaffolding_file_exists(filename: str) -> None:
    path = SOURCE_DIR / filename
    assert path.exists(), f"Expected scaffolding file missing: {path}"


def test_readme_pins_pdf_sha256() -> None:
    readme = (SOURCE_DIR / "README.md").read_text()
    # Vol.2 is the corpus source; its SHA must be pinned for reproducibility.
    assert (
        "8768536a13fb5428d8ec7fbd96263d028aabb557a5411e7f796cad99ed6881cb"
        in readme
    ), "Vol.2 PDF SHA-256 not pinned in README (breaks reproducibility per rule 1)."


def test_transcribe_pins_pdf_sha256() -> None:
    transcribe = (SOURCE_DIR / "transcribe.md").read_text()
    assert (
        "8768536a13fb5428d8ec7fbd96263d028aabb557a5411e7f796cad99ed6881cb"
        in transcribe
    ), "Vol.2 PDF SHA-256 not pinned in transcribe.md."


# ---------------------------------------------------------------------------
# 2. merge.py invariants.
# ---------------------------------------------------------------------------


def _import_merge_module():
    """Import merge.py as a module without executing its `if __name__=='__main__'`."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "baud_merge", SOURCE_DIR / "merge.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_merge_sentinel_null_strings_include_french() -> None:
    merge = _import_merge_module()
    # Standard set
    for s in ("none", "-", "—", "n/a", "na", "unknown"):
        assert s in merge.SENTINEL_NULL_STRINGS
    # French extension — Baud uses these verbatim in PARENTÉ for "no data"
    for s in ("inconnue", "inconnu"):
        assert s in merge.SENTINEL_NULL_STRINGS


def test_merge_normalise_value_maps_french_inconnue_to_none() -> None:
    merge = _import_merge_module()
    assert merge._normalise_value("Inconnue") is None
    assert merge._normalise_value("inconnu") is None
    # Case insensitive, whitespace-stripped
    assert merge._normalise_value("  INCONNUE  ") is None


def test_merge_normalise_value_preserves_hedged_strings() -> None:
    merge = _import_merge_module()
    # Hedged names are positive authorial assertions, must survive
    assert merge._normalise_value("Snéfrou (probable)") == "Snéfrou (probable)"
    assert merge._normalise_value("[ḥr?]") == "[ḥr?]"
    assert merge._normalise_value("") == ""  # empty string is not sentinel


def test_merge_majority_picks_agreed_value() -> None:
    merge = _import_merge_module()
    chosen, count = merge._majority(["A", "A", "B"])
    assert chosen == "A"
    assert count == 2


def test_merge_majority_normalises_french_inconnue_before_vote() -> None:
    merge = _import_merge_module()
    # Two agents said "Inconnue", one said null → null wins with 3 votes
    chosen, count = merge._majority(["Inconnue", "inconnu", None])
    assert chosen is None
    assert count == 3


def test_merge_load_raises_on_malformed_baud_id(tmp_path: Path) -> None:
    merge = _import_merge_module()
    bad = tmp_path / "agent-a-chunk1.jsonl"
    bad.write_text('{"baud_id": "1"}\n')  # should be "001"
    with pytest.raises(ValueError, match="Malformed baud_id"):
        merge._load(bad)


def test_merge_load_raises_on_intra_file_duplicate(tmp_path: Path) -> None:
    merge = _import_merge_module()
    bad = tmp_path / "agent-a-chunk1.jsonl"
    bad.write_text(
        '{"baud_id": "001", "name": "X"}\n'
        '{"baud_id": "001", "name": "Y"}\n'
    )
    with pytest.raises(ValueError, match="Duplicate baud_id"):
        merge._load(bad)


def test_merge_load_agent_chunks_raises_on_cross_chunk_duplicate(
    tmp_path: Path,
) -> None:
    merge = _import_merge_module()
    (tmp_path / "agent-a-chunk1.jsonl").write_text('{"baud_id": "001"}\n')
    (tmp_path / "agent-a-chunk2.jsonl").write_text('{"baud_id": "001"}\n')
    with pytest.raises(ValueError, match="Duplicate baud_id.*across chunk files"):
        merge._load_agent_chunks(tmp_path, "a")


def test_merge_load_agent_chunks_unions_rows(tmp_path: Path) -> None:
    merge = _import_merge_module()
    (tmp_path / "agent-a-chunk1.jsonl").write_text(
        '{"baud_id": "001", "name": "A"}\n'
        '{"baud_id": "002", "name": "B"}\n'
    )
    (tmp_path / "agent-a-chunk2.jsonl").write_text(
        '{"baud_id": "026", "name": "Z"}\n'
    )
    rows = merge._load_agent_chunks(tmp_path, "a")
    assert set(rows.keys()) == {"001", "002", "026"}
    assert rows["026"]["name"] == "Z"


def test_merge_sort_key_is_numeric_order_of_zero_padded_id() -> None:
    merge = _import_merge_module()
    # Zero-padded 3-digit IDs sort lexicographically in numeric order
    ids = ["003", "017", "282", "001", "100"]
    assert sorted(ids, key=merge._sort_key) == ["001", "003", "017", "100", "282"]


# ---------------------------------------------------------------------------
# 3. fix_rows.py derived-field logic.
# ---------------------------------------------------------------------------


def _import_fix_rows_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "baud_fix_rows", SOURCE_DIR / "fix_rows.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_derive_dynasty_bounds_explicit_roman_single() -> None:
    fr = _import_fix_rows_module()
    assert fr.derive_dynasty_bounds("IVe dynastie", None) == (4, 4)
    assert fr.derive_dynasty_bounds("Ve dynastie", None) == (5, 5)
    assert fr.derive_dynasty_bounds("VIe dynastie", None) == (6, 6)
    assert fr.derive_dynasty_bounds("IIIe dynastie", None) == (3, 3)


def test_derive_dynasty_bounds_spanning_range() -> None:
    fr = _import_fix_rows_module()
    # "Fin IVe – début Ve dynastie?" — Baud's canonical spanning-hedge form
    assert fr.derive_dynasty_bounds("Fin IVe – début Ve dynastie?", None) == (4, 5)
    # "Fin Ve – début VIe"
    assert fr.derive_dynasty_bounds("Fin Ve – début VIe dynastie", None) == (5, 6)


def test_derive_dynasty_bounds_falls_back_to_king() -> None:
    fr = _import_fix_rows_module()
    # datation_raw absent → use king
    assert fr.derive_dynasty_bounds(None, "Snéfrou") == (4, 4)
    assert fr.derive_dynasty_bounds(None, "Pépi Ier") == (6, 6)
    assert fr.derive_dynasty_bounds(None, "Djedkarê") == (5, 5)


def test_derive_dynasty_bounds_strips_king_hedge_suffixes() -> None:
    fr = _import_fix_rows_module()
    assert fr.derive_dynasty_bounds(None, "Rêkhaef au plus tard") == (4, 4)
    assert fr.derive_dynasty_bounds(None, "Khoufou environ") == (4, 4)
    assert fr.derive_dynasty_bounds(None, "Pépi Ier (ou plus)") == (6, 6)


def test_derive_dynasty_bounds_returns_nulls_when_unparseable() -> None:
    fr = _import_fix_rows_module()
    assert fr.derive_dynasty_bounds(None, None) == (None, None)
    assert fr.derive_dynasty_bounds("", "") == (None, None)
    # Unknown king name
    assert fr.derive_dynasty_bounds(None, "SomeUnknownKing") == (None, None)


def test_derive_king_father_matches_known_king_with_hedge() -> None:
    fr = _import_fix_rows_module()
    # Hedged names survive verbatim in the returned value
    assert fr.derive_king_father("Snéfrou (probable)") == "Snéfrou (probable)"
    assert fr.derive_king_father("Khoufou") == "Khoufou"


def test_derive_king_father_returns_none_for_non_king() -> None:
    fr = _import_fix_rows_module()
    # A non-king father (typical OK commoner) returns None
    assert fr.derive_king_father("Wnj") is None
    assert fr.derive_king_father("Jj-mrjj (probable)") is None
    assert fr.derive_king_father(None) is None
    assert fr.derive_king_father("") is None


def test_normalise_redirect_row_nulls_non_redirect_fields() -> None:
    fr = _import_fix_rows_module()
    stub = {
        "baud_id": "009",
        "name": "Jj-[ḥr?]-nfr",
        "redirect_to": "132",
        # Suppose an agent wrongly populated some factual fields:
        "monuments": ["should be dropped"],
        "pm_refs": ["PM 999"],
        "publications": ["stale"],
        "king": "stale",
        "datation_raw": "stale",
        "dynasty_min": 5,
        "dynasty_max": 5,
        "titles": ["stale"],
        "father_name": "stale",
        "mother_name": "stale",
        "king_father": "stale",
        "spouse_names": ["stale"],
        "children_names": ["stale"],
        "sex": "male",
        "notes": "stale",
        "head_note": "stale",
        "asterisk": True,
        "sub_period": "Old Kingdom (Dynasties 3-6)",
        "source_citation": {"edition": "IFAO BdE 126/2 1999", "pdf_pages": "20-20"},
    }
    out = fr.normalise_redirect_row(stub)
    assert out["redirect_to"] == "132"
    assert out["baud_id"] == "009"
    assert out["name"] == "Jj-[ḥr?]-nfr"
    # sub_period and source_citation are meta-fields, not factual — preserved
    assert out["sub_period"] == "Old Kingdom (Dynasties 3-6)"
    assert out["source_citation"]["edition"] == "IFAO BdE 126/2 1999"
    # asterisk must flip to false on redirects (Baud doesn't mark them)
    assert out["asterisk"] is False
    # Every nullable factual field → null
    for field in (
        "head_note",
        "king",
        "datation_raw",
        "dynasty_min",
        "dynasty_max",
        "father_name",
        "mother_name",
        "king_father",
        "sex",
        "notes",
    ):
        assert out[field] is None, f"Redirect row leaked value in {field}"
    # Every list-typed factual field → empty
    for field in (
        "monuments",
        "pm_refs",
        "publications",
        "titles",
        "spouse_names",
        "children_names",
    ):
        assert out[field] == [], f"Redirect row leaked value in {field}"


def test_normalise_redirect_row_leaves_non_redirect_unchanged() -> None:
    fr = _import_fix_rows_module()
    row = {
        "baud_id": "003",
        "name": "Jḥtj-ḥtp",
        "redirect_to": None,
        "monuments": ["Mastaba G 7650 dans la nécropole orientale de Gîza"],
        "titles": ["rḫ nswt", "ḥm-nṯr Ḫwfw"],
    }
    out = fr.normalise_redirect_row(row)
    assert out == row


def test_apply_overrides_derives_dynasty_and_king_father() -> None:
    fr = _import_fix_rows_module()
    rows = [
        {
            "baud_id": "003",
            "name": "Jḥtj-ḥtp",
            "redirect_to": None,
            "head_note": None,
            "asterisk": False,
            "monuments": ["Mastaba G 7650"],
            "pm_refs": ["PM 200-201"],
            "publications": [],
            "king": "Rêkhaef au plus tard",
            "datation_raw": None,
            "dynasty_min": None,
            "dynasty_max": None,
            "titles": ["ḥm-nṯr Ḫwfw"],
            "father_name": "Snéfrou (probable)",
            "mother_name": None,
            "king_father": None,
            "spouse_names": ["Mrt-jt.s [86]"],
            "children_names": [],
            "sex": "male",
            "notes": None,
            "sub_period": "Old Kingdom (Dynasties 3-6)",
            "source_citation": {
                "edition": "IFAO BdE 126/2 1999",
                "pdf_pages": "20-20",
            },
        },
        {
            "baud_id": "009",
            "name": "Jj-[ḥr?]-nfr",
            "redirect_to": "132",
            "head_note": None,
            "asterisk": False,
            "monuments": [],
            "pm_refs": [],
            "publications": [],
            "king": None,
            "datation_raw": None,
            "dynasty_min": None,
            "dynasty_max": None,
            "titles": [],
            "father_name": None,
            "mother_name": None,
            "king_father": None,
            "spouse_names": [],
            "children_names": [],
            "sex": None,
            "notes": None,
            "sub_period": "Old Kingdom (Dynasties 3-6)",
            "source_citation": {
                "edition": "IFAO BdE 126/2 1999",
                "pdf_pages": "21-21",
            },
        },
        {
            "baud_id": "002",
            "name": "Jḥ-Rꜥ",
            "redirect_to": None,
            "head_note": None,
            "asterisk": False,
            "monuments": ["Tombe rupestre n° 4 au nord du Sphinx, Gîza"],
            "pm_refs": ["PM 214"],
            "publications": [],
            "king": None,
            "datation_raw": "Fin IVe – début Ve dynastie?",
            "dynasty_min": None,
            "dynasty_max": None,
            "titles": ["zꜣ nswt nj ẖt.f smsw mrjj.f"],
            "father_name": None,
            "mother_name": None,
            "king_father": None,
            "spouse_names": [],
            "children_names": [],
            "sex": "male",
            "notes": None,
            "sub_period": "Old Kingdom (Dynasties 3-6)",
            "source_citation": {
                "edition": "IFAO BdE 126/2 1999",
                "pdf_pages": "19-19",
            },
        },
    ]
    fixed, log = fr.apply_overrides(rows)

    # Rows come back sorted by baud_id
    assert [r["baud_id"] for r in fixed] == ["002", "003", "009"]

    row_002 = fixed[0]
    # Spanning hedge → (4, 5); king_father null (no father)
    assert row_002["dynasty_min"] == 4
    assert row_002["dynasty_max"] == 5
    assert row_002["king_father"] is None

    row_003 = fixed[1]
    # King fallback with "au plus tard" hedge stripped → (4, 4)
    assert row_003["dynasty_min"] == 4
    assert row_003["dynasty_max"] == 4
    # father_name = "Snéfrou (probable)"; Snéfrou is a known OK king → king_father preserved with hedge
    assert row_003["king_father"] == "Snéfrou (probable)"

    row_009 = fixed[2]
    # Redirect stub → factual fields nulled; derived fields re-derive as null from null inputs
    assert row_009["redirect_to"] == "132"
    assert row_009["dynasty_min"] is None
    assert row_009["dynasty_max"] is None
    assert row_009["king_father"] is None
    assert row_009["titles"] == []

    # No SPOT_CORRECTIONS registered in scaffolding → log is empty
    assert log == []


def test_apply_overrides_raises_on_unknown_spot_correction_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fr = _import_fix_rows_module()
    monkeypatch.setattr(
        fr,
        "SPOT_CORRECTIONS",
        [("999", "name", "X", "hypothetical test override")],
    )
    rows = [
        {
            "baud_id": "001",
            "name": "A",
            "redirect_to": None,
            "datation_raw": None,
            "king": None,
            "father_name": None,
        }
    ]
    with pytest.raises(KeyError, match="unknown baud_id"):
        fr.apply_overrides(rows)


def test_rewrite_override_section_is_idempotent() -> None:
    fr = _import_fix_rows_module()
    base = "No field-level disagreements.\n"
    log = ["001.name: \"A\" → \"B\" [rationale]"]
    first = fr.rewrite_override_section(base, log)
    second = fr.rewrite_override_section(first, log)
    # Section must not duplicate on re-run
    assert first == second
    # Marker appears exactly once
    assert first.count(fr.OVERRIDE_MARKER) == 1


def test_rewrite_override_section_drops_stale_section_when_log_empty() -> None:
    fr = _import_fix_rows_module()
    existing_with_section = (
        "No field-level disagreements.\n"
        + fr.OVERRIDE_MARKER
        + "stale override line\n"
    )
    cleared = fr.rewrite_override_section(existing_with_section, [])
    assert fr.OVERRIDE_MARKER not in cleared
    assert "stale override line" not in cleared
    assert cleared == "No field-level disagreements.\n"


# ---------------------------------------------------------------------------
# 4. Invariants on known facts shipped in the scaffolding.
# ---------------------------------------------------------------------------


def test_known_ok_kings_include_all_six_dynasty_last_kings() -> None:
    fr = _import_fix_rows_module()
    for king in ("Houni", "Chepseskaf", "Ounas", "Pépi II"):
        assert king in fr.KNOWN_OK_KINGS, (
            f"{king} missing from KNOWN_OK_KINGS — would prevent king_father "
            f"derivation for their descendants."
        )


def test_roman_dyn_tokens_map_to_correct_integers() -> None:
    fr = _import_fix_rows_module()
    assert fr.ROMAN_TO_INT == {"III": 3, "IV": 4, "V": 5, "VI": 6}


def test_prompt_md_names_flagship_row_three_for_tests() -> None:
    """The prompt's flagship-row mention and the test file's flagship-row
    test must stay aligned: if the prompt says `[3] Jḥtj-ḥtp` is the
    flagship, the test file's future `test_entry_003_jhtj_htp_full_fields`
    must exist (or this guard flags the drift).

    Scaffolding-only form: assert the prompt names `[3] Jḥtj-ḥtp` as
    the flagship. The full-field test is added by the chunk-1
    extraction PR alongside `reconciled.jsonl`.
    """
    prompt = (SOURCE_DIR / "prompt.md").read_text()
    assert "[3] Jḥtj-ḥtp" in prompt, (
        "Flagship row reference drifted — update prompt.md or update the "
        "expected flagship ID in this test."
    )


def test_baud_id_pattern_is_three_digit_zero_padded() -> None:
    merge = _import_merge_module()
    # The regex compiled in merge.py
    p = merge.BAUD_ID_PATTERN
    assert p.match("001")
    assert p.match("017")
    assert p.match("282")
    assert not p.match("1")
    assert not p.match("0001")
    assert not p.match("17")
    assert not p.match("abc")
