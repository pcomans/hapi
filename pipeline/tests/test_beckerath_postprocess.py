"""Unit tests for Beckerath chronology chunk-file post-processing.

The post-processor restores persistent dynasty + section context across
page boundaries in the OCR markdown so the 3-subagent extraction step
doesn't silently lose `etwa` qualifiers (Dyn-4 case from PR #128 fix_rows
overrides 04.02–04.08) or mis-attribute short dynasties to the wrong
period (Dyn-24/25 → Spätzeit case from PR #128 fix_rows overrides 24.01,
24.02).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_PP_PATH = (
    Path(__file__).parent.parent
    / "pipeline"
    / "authority"
    / "sources"
    / "beckerath-1997-chronologie"
    / "postprocess.py"
)
_spec = importlib.util.spec_from_file_location("beckerath_postprocess", _PP_PATH)
pp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pp)


# === Heading recognisers ====================================================


def test_recognises_section_headings() -> None:
    assert pp._is_section_heading("### FRÜHZEIT") == "Frühzeit"
    assert pp._is_section_heading("### ALTES REICH") == "Altes Reich"
    assert pp._is_section_heading("### I. ZWISCHENZEIT") == "I. Zwischenzeit"
    assert pp._is_section_heading("### MITTLERES REICH") == "Mittleres Reich"
    assert pp._is_section_heading("### II. ZWISCHENZEIT") == "II. Zwischenzeit"
    assert pp._is_section_heading("### NEUES REICH") == "Neues Reich"
    assert pp._is_section_heading("### III. ZWISCHENZEIT") == "III. Zwischenzeit"
    assert pp._is_section_heading("### SPÄTZEIT") == "Spätzeit"
    assert (
        pp._is_section_heading("### VORGESCHICHTE (PRÄDYNASTISCHE ZEIT)")
        == "Vorgeschichte"
    )


def test_section_heading_returns_none_for_non_match() -> None:
    assert pp._is_section_heading("**4. Dynastie**") is None
    assert pp._is_section_heading("Senofru (Soris)\t2639/2589") is None
    assert pp._is_section_heading("## Book p187") is None


def test_recognises_bold_dynasty_heading() -> None:
    assert (
        pp._is_dynasty_heading("**4. Dynastie (etwa 2639/2589–2504/2454)**")
        == "4. Dynastie (etwa 2639/2589–2504/2454)"
    )
    assert (
        pp._is_dynasty_heading("**22. Dynastie (946/945–ca.735)**")
        == "22. Dynastie (946/945–ca.735)"
    )
    # Dyn 28-31 use the spelling drift `Dynaste` (no `i`).
    assert pp._is_dynasty_heading("**28. Dynaste**") == "28. Dynaste"
    # `0. Dynastie` with a tab/whitespace tail (chunk has it followed by date)
    # — we just need to match the `**...**` opening.
    assert (
        pp._is_dynasty_heading("**0. Dynastie**\tungefähr 150 Jahre")
        == "0. Dynastie"
    )


def test_recognises_compound_dynasty_heading() -> None:
    """`9./10. Dynastie (in Herakleopolis, etwa ...)` is NOT bolded in OCR."""
    assert (
        pp._is_dynasty_heading(
            "9./10. Dynastie (in Herakleopolis, etwa 2170/2120–2025/2020/2010) 18 Könige"
        )
        == "9./10. Dynastie (in Herakleopolis, etwa 2170/2120–2025/2020/2010) 18 Könige"
    )


def test_dynasty_heading_returns_none_for_non_match() -> None:
    assert pp._is_dynasty_heading("### FRÜHZEIT") is None
    assert pp._is_dynasty_heading("Senofru (Soris)\t2639/2589") is None
    assert pp._is_dynasty_heading("## Book p187") is None


def test_recognises_page_boundary() -> None:
    assert pp._is_page_boundary("## Book p187")
    assert pp._is_page_boundary("## Book p188")
    assert pp._is_page_boundary("## Book p194")
    assert not pp._is_page_boundary("**4. Dynastie**")
    assert not pp._is_page_boundary("### FRÜHZEIT")


# === process_chunk integration =============================================


def test_attaches_period_after_dynasty_heading() -> None:
    """Defeats the Dyn-24/25 → Spätzeit mis-attribution case."""
    md = (
        "### III. ZWISCHENZEIT\n"
        "\n"
        "**24. Dynastie (in Sais)**\n"
        "Fürst Tef-nachte\tum 740–719/17\n"
        "Bokchoris (Bak-en-rinef, Wah-ka-rê)\t719/717–714/712\n"
        "\n"
        "**25. Dynastie (Kuschiten)**\n"
        "Kaschta\tvor ca. 746\n"
    )
    out = pp.process_chunk(md)
    # Section heading appears before each dynasty heading; period comment
    # is emitted ON the line directly after each dynasty heading.
    assert "**24. Dynastie (in Sais)**\n<!-- period: III. Zwischenzeit -->" in out
    assert "**25. Dynastie (Kuschiten)**\n<!-- period: III. Zwischenzeit -->" in out


def test_section_change_resets_dynasty_context() -> None:
    """Section-heading boundary clears the carried dynasty context so a
    later page-break in the next section doesn't refresh stale dynasty info."""
    md = (
        "### I. ZWISCHENZEIT\n"
        "\n"
        "9./10. Dynastie (in Herakleopolis, etwa 2170/2120–2025/2020) 18 Könige\n"
        "\n"
        "### MITTLERES REICH\n"
        "\n"
        "## Book p189\n"
        "\n"
        "Some king row\t1995–1983\n"
    )
    out = pp.process_chunk(md)
    # No dynasty-context refresh after the page break — current_dynasty_heading
    # was reset by the MITTLERES REICH heading.
    assert "<!-- dynasty-context:" not in out


def test_refreshes_dynasty_context_after_page_break_inside_dynasty() -> None:
    """Defeats the Dyn-4 page-break-loses-`etwa` case (PR #128 overrides
    04.02–04.08)."""
    md = (
        "### ALTES REICH\n"
        "\n"
        "**4. Dynastie (etwa 2639/2589–2504/2454)**\n"
        "Senofru (Soris)\t2639/2589–2604/2554\n"
        "\n"
        "## Book p188\n"
        "\n"
        "Cheops (Chufu)\tetwa 2604/2554–2581/2531\n"
        "Djedefre\t2581/2531–2572/2522\n"
    )
    out = pp.process_chunk(md)
    # Refresh comments emitted directly after the page boundary because the
    # next line is a king-row, NOT a new heading.
    assert (
        "## Book p188\n"
        "<!-- dynasty-context: 4. Dynastie (etwa 2639/2589–2504/2454) -->\n"
        "<!-- period: Altes Reich -->"
    ) in out


def test_does_not_refresh_when_next_line_is_new_heading() -> None:
    """If the next non-empty line after a page break IS itself a section or
    dynasty heading, the agent gets fresh context from that heading; no
    duplicate comment refresh is needed."""
    md = (
        "**21. Dynastie (1070/1069–946/945)**\n"
        "Smendes\t1070/69–1044/43\n"
        "\n"
        "## Book p191\n"
        "\n"
        "**22. Dynastie (946/945–ca.735)**\n"
        "Schoschenq I.\t946/45–925/24\n"
    )
    out = pp.process_chunk(md)
    # No refresh between page boundary and the new dynasty heading.
    assert "## Book p191\n<!--" not in out
    assert "## Book p191\n\n**22. Dynastie" in out


def test_handles_predynastic_section_heading() -> None:
    """`### VORGESCHICHTE (PRÄDYNASTISCHE ZEIT)` maps to `Vorgeschichte`."""
    md = (
        "### VORGESCHICHTE (PRÄDYNASTISCHE ZEIT)\n"
        "\n"
        "**0. Dynastie**\tungefähr 150 Jahre\n"
    )
    out = pp.process_chunk(md)
    assert "**0. Dynastie**\tungefähr 150 Jahre\n<!-- period: Vorgeschichte -->" in out


def test_preserves_input_lines_verbatim() -> None:
    """Non-heading content (king rows, page breaks, blanks, decorative
    lines) must pass through unchanged. The post-processor only INJECTS
    annotations, never modifies existing content."""
    md = (
        "### FRÜHZEIT\n"
        "\n"
        "**1. Dynastie (etwa 3032/2982–2853/2803)**\n"
        "Menes (Hor Aha)\tetwa 3032/2982–3000/2950\n"
        "Iti (Heti ?)\t3000/2950–2999/2949\n"
        "\n"
        "Marathon: 7. Dynastie enthält „70 Tage\"\n"
    )
    out = pp.process_chunk(md)
    # Every original line still appears in the output.
    for original in md.splitlines():
        assert original in out


def test_idempotent_on_already_annotated_input() -> None:
    """Running the post-processor twice on its own output should be a no-op
    beyond stable annotation placement — the comments do NOT match the
    section/dynasty/page recognisers, so the second pass adds nothing new."""
    md = (
        "### ALTES REICH\n"
        "\n"
        "**4. Dynastie (etwa 2639/2589–2504/2454)**\n"
        "Senofru\t2639/2589–2604/2554\n"
        "\n"
        "## Book p188\n"
        "\n"
        "Cheops\tetwa 2604/2554–2581/2531\n"
    )
    once = pp.process_chunk(md)
    twice = pp.process_chunk(once)
    assert once == twice


def test_full_chunk_shape() -> None:
    """End-to-end: a representative chunk fragment exercising section
    transitions, dynasty headings, page breaks, and the carry rules."""
    md = (
        "## Book p187\n"
        "\n"
        "### FRÜHZEIT\n"
        "\n"
        "**1. Dynastie (etwa 3032/2982–2853/2803)**\n"
        "Menes (Hor Aha)\tetwa 3032/2982–3000/2950\n"
        "\n"
        "### ALTES REICH\n"
        "\n"
        "**4. Dynastie (etwa 2639/2589–2504/2454)**\n"
        "Senofru\t2639/2589–2604/2554\n"
        "\n"
        "## Book p188\n"
        "\n"
        "Cheops\tetwa 2604/2554–2581/2531\n"
        "\n"
        "**5. Dynastie (etwa 2504/2454–2347/2297)**\n"
        "Userkaf\t2504/2454–2496/2446\n"
    )
    out = pp.process_chunk(md)
    # First-page boundary at top has no dynasty context yet (Dyn 1 hasn't
    # been declared) so no refresh.
    assert (
        "## Book p187\n\n### FRÜHZEIT\n"
        in out
    ), "no refresh should be inserted before the section heading"
    # Period attached to Dyn 1 heading.
    assert (
        "**1. Dynastie (etwa 3032/2982–2853/2803)**\n<!-- period: Frühzeit -->" in out
    )
    # Section change to ALTES REICH resets dynasty context.
    assert "**4. Dynastie (etwa 2639/2589–2504/2454)**\n<!-- period: Altes Reich -->" in out
    # Page break inside Dyn 4 refreshes dynasty + period.
    assert (
        "## Book p188\n"
        "<!-- dynasty-context: 4. Dynastie (etwa 2639/2589–2504/2454) -->\n"
        "<!-- period: Altes Reich -->"
    ) in out
    # Period attached to Dyn 5 heading.
    assert "**5. Dynastie (etwa 2504/2454–2347/2297)**\n<!-- period: Altes Reich -->" in out


# === Real chunk smoke test =================================================


def test_real_chunk_p105_p109_no_regressions() -> None:
    """Smoke test: applying the post-processor to the real OCR chunk file
    must not delete or reorder existing content. Skipped when the chunk
    file is not present (gitignored, regenerable)."""
    chunk_path = (
        Path(__file__).parent.parent
        / "pipeline"
        / "authority"
        / "sources"
        / "beckerath-1997-chronologie"
        / "raw"
        / "chunk-p105-p109.md"
    )
    if not chunk_path.exists():
        import pytest

        pytest.skip("chunk file not present; run OCR step first")
    md = chunk_path.read_text()
    out = pp.process_chunk(md)
    # Every original line still appears in the output, in order.
    original_lines = md.splitlines()
    output_lines = out.splitlines()
    j = 0
    for line in original_lines:
        # Find the next occurrence of `line` in the output starting at j.
        try:
            j = output_lines.index(line, j) + 1
        except ValueError:
            raise AssertionError(
                f"original line lost or reordered in postprocessed output: {line!r}"
            )
    # The output is strictly larger or equal (annotations only added).
    assert len(output_lines) >= len(original_lines)
