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
    assert pp._is_section_heading("### FRÜHZEIT") == (True, "Frühzeit")
    assert pp._is_section_heading("### ALTES REICH") == (True, "Altes Reich")
    assert pp._is_section_heading("### I. ZWISCHENZEIT") == (True, "I. Zwischenzeit")
    assert pp._is_section_heading("### MITTLERES REICH") == (True, "Mittleres Reich")
    assert pp._is_section_heading("### II. ZWISCHENZEIT") == (True, "II. Zwischenzeit")
    assert pp._is_section_heading("### NEUES REICH") == (True, "Neues Reich")
    assert pp._is_section_heading("### III. ZWISCHENZEIT") == (True, "III. Zwischenzeit")
    assert pp._is_section_heading("### SPÄTZEIT") == (True, "Spätzeit")
    assert pp._is_section_heading("### VORGESCHICHTE (PRÄDYNASTISCHE ZEIT)") == (
        True,
        "Vorgeschichte",
    )


def test_section_heading_returns_false_for_non_match() -> None:
    assert pp._is_section_heading("**4. Dynastie**") == (False, None)
    assert pp._is_section_heading("Senofru (Soris)\t2639/2589") == (False, None)
    assert pp._is_section_heading("## Book p187") == (False, None)


def test_section_heading_unknown_returns_true_with_none_name() -> None:
    """`### Supplement zu A` is a `### ...` heading but not one of the eight
    canonical period names. Must classify as heading-but-unknown so the
    process_chunk loop resets state instead of leaking the previous section."""
    assert pp._is_section_heading("### Supplement zu A") == (True, None)
    assert pp._is_section_heading("### Some Other Heading") == (True, None)


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
    # — capture the trailing date too so the dynasty-context comment
    # preserves Beckerath's full heading line.
    assert (
        pp._is_dynasty_heading("**0. Dynastie**\tungefähr 150 Jahre")
        == "0. Dynastie\tungefähr 150 Jahre"
    )


def test_dynasty_heading_with_parenthetical_outside_bold() -> None:
    """Defensive: capture the parenthetical qualifier even if a future OCR
    variant emits `**N. Dynastie** (etwa ...)` with the parenthetical OUTSIDE
    the bold markers. Without group 2 capture the `etwa` qualifier would be
    lost from the dynasty-context refresh."""
    assert (
        pp._is_dynasty_heading("**4. Dynastie** (etwa 2639/2589–2504/2454)")
        == "4. Dynastie (etwa 2639/2589–2504/2454)"
    )


def test_recognises_compound_dynasty_heading() -> None:
    """`9./10. Dynastie (in Herakleopolis, etwa ...)` is NOT bolded in OCR."""
    assert (
        pp._is_dynasty_heading(
            "9./10. Dynastie (in Herakleopolis, etwa 2170/2120–2025/2020/2010) 18 Könige"
        )
        == "9./10. Dynastie (in Herakleopolis, etwa 2170/2120–2025/2020/2010) 18 Könige"
    )


def test_recognises_bold_variant_of_compound_dynasty_heading() -> None:
    """Defensive: a future OCR run may emit the compound heading with `**`
    wrapping (`**9./10. Dynastie (...)**`). The bold markers must be
    stripped from the captured inner text."""
    assert (
        pp._is_dynasty_heading(
            "**9./10. Dynastie (in Herakleopolis, etwa 2170/2120–2025/2020) 18 Könige**"
        )
        == "9./10. Dynastie (in Herakleopolis, etwa 2170/2120–2025/2020) 18 Könige"
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


def test_period_derived_from_dynasty_number_not_from_ocr_section_heading() -> None:
    """REGRESSION (egyptologist-reviewer PR #138). The OCR-step output for
    chunk-p105-p109.md does NOT capture `### II. ZWISCHENZEIT` between
    Dyn 12 and Dyn 13. If the post-processor derived period from the OCR
    section heading state, Dyn 13–17 would silently get the prior heading's
    period (`Mittleres Reich`) — wrong by one whole epoch. The fix derives
    period from the canonical Beckerath dynasty→period mapping so the
    annotation is correct even when OCR drops a heading.

    Structure here mirrors the actual chunk's Dyn-12 → Dyn-13 transition
    with no intervening II. ZWISCHENZEIT heading."""
    md = (
        "### MITTLERES REICH\n"
        "\n"
        "**12. Dynastie (1976–1794/93)**\n"
        "Amenemnes I.\t1976–1947\n"
        "\n"
        "**13. Dynastie (1794/93–1648/1645)**\n"
        "(60 (?) Könige (zeitw. 6 Könige)\n"
        "\n"
        "**15. Dynastie (Hyksos, 1648/1645–1539/1536)**\n"
        "Salitis (Bnôn)\t1648/1645–1590/1587\n"
        "\n"
        "**17. Dynastie (in Theben, etwa 1645–1539/1550)** (?) Könige\n"
    )
    out = pp.process_chunk(md)
    # Dyn 12 gets Mittleres Reich (correct).
    assert "**12. Dynastie (1976–1794/93)**\n<!-- period: Mittleres Reich -->" in out
    # Dyn 13 gets II. Zwischenzeit DESPITE the missing OCR heading.
    assert (
        "**13. Dynastie (1794/93–1648/1645)**\n<!-- period: II. Zwischenzeit -->"
        in out
    )
    assert "**15. Dynastie (Hyksos, 1648/1645–1539/1536)**\n<!-- period: II. Zwischenzeit -->" in out
    # Dyn 17 also gets II. Zwischenzeit (still SIP).
    assert "**17. Dynastie (in Theben, etwa 1645–1539/1550)** (?) Könige\n<!-- period: II. Zwischenzeit -->" in out


def test_canonical_dynasty_period_mapping_covers_dyn_0_through_31() -> None:
    """Sanity: every Beckerath dynasty number (0..31) has a canonical period
    in `DYNASTY_PERIOD`. Adding a new dynasty without a period would silently
    emit no `<!-- period: ... -->` annotation."""
    for n in range(0, 32):
        assert n in pp.DYNASTY_PERIOD, f"missing canonical period for Dyn {n}"
    # Spot-checks against the schema's eight-period vocabulary.
    assert pp.DYNASTY_PERIOD[0] == "Vorgeschichte"
    assert pp.DYNASTY_PERIOD[1] == "Frühzeit"
    assert pp.DYNASTY_PERIOD[8] == "Altes Reich"
    assert pp.DYNASTY_PERIOD[10] == "I. Zwischenzeit"
    assert pp.DYNASTY_PERIOD[12] == "Mittleres Reich"
    assert pp.DYNASTY_PERIOD[13] == "II. Zwischenzeit"
    assert pp.DYNASTY_PERIOD[20] == "Neues Reich"
    assert pp.DYNASTY_PERIOD[25] == "III. Zwischenzeit"
    assert pp.DYNASTY_PERIOD[31] == "Spätzeit"


def test_dynasty_number_extractor_handles_all_heading_shapes() -> None:
    assert pp._dynasty_number("4. Dynastie (etwa 2639/2589–2504/2454)") == 4
    assert pp._dynasty_number("28. Dynaste") == 28
    assert pp._dynasty_number("0. Dynastie") == 0
    # Compound `9./10.` resolves to 9 (the leading number); the period is the
    # same for both halves of a Beckerath compound dynasty heading.
    assert pp._dynasty_number("9./10. Dynastie (in Herakleopolis, ...)") == 9
    assert pp._dynasty_number("not a dynasty heading") is None


def test_supplement_zu_a_does_not_inherit_spaetzeit_period() -> None:
    """REGRESSION (Gemini PR #138 + code-reviewer). Beckerath's Anhang A
    ends with `### SPÄTZEIT` (Dyn 26-31). The Supplement zu A is introduced
    by `### Supplement zu A` and contains supplementary titulary entries
    for Dyn 19-23 — those entries are Neues Reich (19/20) or III. Zwischenzeit
    (21/22/23), NOT Spätzeit. The supplement's `### ...` heading must reset
    the section state so the supplement's `**19. Dynastie**` etc. headings
    don't get a `<!-- period: Spätzeit -->` annotation leaked from the
    preceding `### SPÄTZEIT` block."""
    md = (
        "### SPÄTZEIT\n"
        "\n"
        "**31. Dynaste (Perserherrschaft, 342–332)**\n"
        "Artaxerxes III. Ochos\t342–338\n"
        "\n"
        "## Book p193\n"
        "\n"
        "### Supplement zu A\n"
        "\n"
        "Die vollständigen Namen.\n"
        "\n"
        "**19. Dynastie**\n"
        "Ramses I.:\tMen-pehti-rê, Ra-mes-su\n"
        "\n"
        "**20. Dynastie**\n"
        "Seth-nachte:\tUser-chau-rê sotep-en-rê\n"
    )
    out = pp.process_chunk(md)
    # The two supplement dynasty headings must NOT carry a `<!-- period: ... -->`
    # comment; current_section is None after the unrecognised supplement
    # heading reset state.
    assert "**19. Dynastie**\n<!-- period:" not in out
    assert "**20. Dynastie**\n<!-- period:" not in out
    # The `### Supplement zu A` heading is still preserved verbatim in output.
    assert "### Supplement zu A" in out
    # The dynasty-context refresh after the page break must not leak
    # `Spätzeit` either — `### Supplement zu A` follows the page break
    # immediately, so the look-ahead suppresses the refresh.
    assert "## Book p193\n<!--" not in out


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


# === Whole-chunk integration test (synthetic, mirrors real chunk shape) =====


def test_full_chunk_with_supplement_zu_a_integration() -> None:
    """Whole-chunk integration test: a synthetic mini-chunk that exercises
    every transition the real `chunk-p105-p109.md` does — section headings,
    bolded dynasty headings, page boundaries, mid-dynasty page break, and
    the trailing `### Supplement zu A` non-period section. This replaces
    the always-skipping real-file smoke test (the OCR chunk is gitignored
    and regenerable; the synthetic fixture is committed and runs in CI).

    Asserts:
    - Period annotations on every `**N. Dynastie ...**` in Anhang A
    - Page-break inside Dyn-4 refreshes dynasty + period
    - Page-break BEFORE a section/dynasty heading does NOT refresh
    - Supplement zu A resets state — its dynasty headings get NO period leak
    - Every original line preserved in order (no loss/reorder)
    """
    md = (
        "## Book p187\n"
        "\n"
        "### A. CHRONOLOGISCHE ÜBERSICHT ÜBER DIE GESCHICHTE ALTÄGYPTENS\n"
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
        "### III. ZWISCHENZEIT\n"
        "\n"
        "**24. Dynastie (in Sais)**\n"
        "Fürst Tef-nachte\tum 740–719/17\n"
        "\n"
        "### SPÄTZEIT\n"
        "\n"
        "**26. Dynastie (664–525)**\n"
        "Psamtik I.\t664–610\n"
        "\n"
        "## Book p193\n"
        "\n"
        "### Supplement zu A\n"
        "\n"
        "Die vollständigen Namen.\n"
        "\n"
        "**19. Dynastie**\n"
        "Ramses I.:\tMen-pehti-rê, Ra-mes-su\n"
    )
    out = pp.process_chunk(md)

    # Anhang A dynasty headings get period attached.
    assert (
        "**1. Dynastie (etwa 3032/2982–2853/2803)**\n<!-- period: Frühzeit -->"
        in out
    )
    assert (
        "**4. Dynastie (etwa 2639/2589–2504/2454)**\n<!-- period: Altes Reich -->"
        in out
    )
    assert (
        "**24. Dynastie (in Sais)**\n<!-- period: III. Zwischenzeit -->" in out
    )
    assert "**26. Dynastie (664–525)**\n<!-- period: Spätzeit -->" in out

    # Page-break inside Dyn-4 refreshes dynasty + period.
    assert (
        "## Book p188\n"
        "<!-- dynasty-context: 4. Dynastie (etwa 2639/2589–2504/2454) -->\n"
        "<!-- period: Altes Reich -->"
    ) in out

    # Page-break before `### Supplement zu A` does NOT refresh (next non-blank
    # line is a section heading).
    assert "## Book p193\n<!--" not in out

    # Supplement's dynasty heading does NOT get a Spätzeit period leak.
    assert "**19. Dynastie**\n<!-- period:" not in out

    # Every original line preserved in order.
    original_lines = md.splitlines()
    output_lines = out.splitlines()
    j = 0
    for line in original_lines:
        try:
            j = output_lines.index(line, j) + 1
        except ValueError as exc:
            raise AssertionError(
                f"original line lost or reordered: {line!r}"
            ) from exc
