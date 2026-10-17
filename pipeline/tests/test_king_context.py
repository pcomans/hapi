"""A king mention in its record's context (`pipeline.authority.king_context`)."""

from __future__ import annotations

from pipeline.authority import king_context as kc
from pipeline.enrich import authority_links as al


class Kings:
    """name → candidate ids; id → (dynasties, reign)."""

    NAMES = {"Aya": ["aya-13"], "Ahmose": ["ahmose-18", "ahmose-26"], "Amenemhat": ["amenemhat-12a", "amenemhat-12b"],
             "Djoser": ["djoser-3"], "Nobody": [], "Undated": ["undated-x", "ahmose-18"],
             "Shabaka": ["shabaka-a", "shabaka-b"], "Sobekhotep": ["sobekhotep-a", "sobekhotep-undated"]}
    LABELS = {"amenemhat-12a": "Amenemhat I", "amenemhat-12b": "Amenemhat II", "shabaka-a": "Shabaka",
              "shabaka-b": "Shabaka", "sobekhotep-a": "Sobekhotep III", "sobekhotep-undated": "Sobekhotep IV"}
    KINGS = {"aya-13": ((13,), (-1701, -1661)), "ahmose-18": ((18,), (-1550, -1525)),
             "ahmose-26": ((26,), (-570, -526)), "amenemhat-12a": ((12,), (-1976, -1947)),
             "amenemhat-12b": ((12,), (-1843, -1798)), "djoser-3": ((3,), None), "undated-x": ((), None),
             "shabaka-a": ((25,), (-722, -707)), "shabaka-b": ((25,), (-721, -707)),
             "sobekhotep-a": ((13,), (-1725, -1722)), "sobekhotep-undated": ((13,), None)}

    def resolve(self, name: str) -> dict:
        found = self.NAMES[name]
        status = "resolved" if len(found) == 1 else "ambiguous" if found else "unmatched"
        return {"status": status, "target_ids": list(found), "resolution_method": "raw_exact" if found else None}

    def dynasties(self, target_id: str) -> tuple[int, ...]:
        return self.KINGS[target_id][0]

    def reign(self, target_id: str) -> tuple[int, int] | None:
        return self.KINGS[target_id][1]

    def label(self, target_id: str) -> str:
        return self.LABELS.get(target_id, target_id)


KINGS = Kings()


def resolve(name: str, *, dynasty=None, dates=None, strict: bool) -> tuple:
    found = kc.resolve_in_context(KINGS, name, record_dynasty=dynasty, record_dates=dates, strict=strict)
    return found["status"], found["target_ids"], found["context_rule"]


def test_a_reign_field_of_another_dynasty_never_links_the_one_king_of_that_name() -> None:
    # The Met's Dynasty 18 "reign of Aya" records: the only "Aya" is the Dynasty 13 king.
    assert resolve("Aya", dynasty=18, dates=(-1327, -1323), strict=True) == ("unmatched", [], "record_context_conflict")
    assert resolve("Aya", dynasty=13, dates=(-1700, -1676), strict=True) == ("resolved", ["aya-13"], "record_context")
    # A date alone never refuses: museum date fields are not precise enough.
    assert resolve("Aya", dates=(-1327, -1323), strict=True) == ("resolved", ["aya-13"], None)


def test_a_title_cue_may_name_an_earlier_king_so_context_never_refuses_its_one_candidate() -> None:
    # A Dynasty 26 scarab "of King Aya" still names the one Aya: objects can postdate the king.
    assert resolve("Aya", dynasty=26, dates=(-664, -525), strict=False) == ("resolved", ["aya-13"], None)


def test_the_records_dynasty_chooses_among_kings_of_one_name() -> None:
    assert resolve("Ahmose", dynasty=18, strict=True) == ("resolved", ["ahmose-18"], "record_context")
    assert resolve("Ahmose", dynasty=26, strict=False) == ("resolved", ["ahmose-26"], "record_context")
    assert resolve("Ahmose", dynasty=12, strict=True) == ("unmatched", [], "record_context_conflict")
    # A title cue of a third dynasty fits neither, refuses neither: still ambiguous.
    assert resolve("Ahmose", dynasty=12, strict=False) == ("ambiguous", ["ahmose-18", "ahmose-26"], None)


def test_dates_choose_within_one_dynasty_and_a_wide_range_chooses_nothing() -> None:
    assert resolve("Amenemhat", dynasty=12, dates=(-1960, -1950), strict=True) == (
        "resolved", ["amenemhat-12a"], "record_date")
    # Without a dynasty, dates choose among the kings of the name.
    assert resolve("Ahmose", dates=(-560, -540), strict=True) == ("resolved", ["ahmose-26"], "record_date")
    assert resolve("Amenemhat", dynasty=12, dates=(-1981, -1802), strict=True) == (
        "ambiguous", ["amenemhat-12a", "amenemhat-12b"], None)


def test_the_slack_is_fifty_years_each_side() -> None:
    assert kc.DATE_SLACK_YEARS == 50
    # Aya's reign ends 1661 BCE: a record of 1611 BCE still fits, one of 1610 does not.
    assert kc.date_fits(KINGS, "aya-13", (-1611, -1611)) is True
    assert kc.date_fits(KINGS, "aya-13", (-1610, -1600)) is False
    assert kc.date_fits(KINGS, "aya-13", (-1751, -1751)) is True
    assert kc.date_fits(KINGS, "aya-13", (-1800, -1752)) is False
    assert kc.date_fits(KINGS, "djoser-3", (-2700, -2600)) is False  # no reign dates


def test_a_dynasty_conflict_is_not_outweighed_by_a_date() -> None:
    assert kc.dynasty_fit(KINGS, "aya-13", 18) is False
    assert resolve("Aya", dynasty=18, dates=(-1700, -1690), strict=True) == ("unmatched", [], "record_context_conflict")


def test_dates_never_choose_between_two_entries_of_one_king_or_against_an_undated_one() -> None:
    # Two king lists' "Shabaka": one king entered twice; dates must not pick one entry.
    assert resolve("Shabaka", dynasty=25, dates=(-720, -710), strict=True) == (
        "ambiguous", ["shabaka-a", "shabaka-b"], None)
    # A candidate without reign dates cannot be compared, so no date decides.
    assert resolve("Sobekhotep", dynasty=13, dates=(-1725, -1722), strict=True) == (
        "ambiguous", ["sobekhotep-a", "sobekhotep-undated"], None)


def test_dates_never_favour_a_candidate_whose_dynasty_conflicts() -> None:
    # A title cue of Dynasty 12 fits neither Ahmose; its dates point at one, which is not taken.
    assert resolve("Ahmose", dynasty=12, dates=(-560, -540), strict=False) == ("ambiguous", ["ahmose-18", "ahmose-26"], None)


def test_without_context_a_name_links_only_when_one_king_has_it() -> None:
    assert resolve("Djoser", strict=True) == ("resolved", ["djoser-3"], None)
    assert resolve("Ahmose", strict=True) == ("ambiguous", ["ahmose-18", "ahmose-26"], None)
    assert resolve("Nobody", dynasty=18, strict=True) == ("unmatched", [], None)


def test_a_candidate_the_king_lists_do_not_date_keeps_the_choice_open() -> None:
    # "undated-x" has no dynasty or reign: the record's Dynasty 18 confirms ahmose-18 but cannot
    # rule the other out, so the name stays ambiguous between them.
    assert resolve("Undated", dynasty=18, strict=True) == ("ambiguous", ["undated-x", "ahmose-18"], None)
    assert kc.dynasty_fit(KINGS, "undated-x", 18) is None


def test_the_resolution_says_what_context_it_read() -> None:
    found = kc.resolve_in_context(KINGS, "Ahmose", record_dynasty=18, record_dates=(-1550, -1530), strict=True)
    assert found["context"] == {"record_dynasty": 18, "record_dates": [-1550, -1530],
                                "candidate_fit": {"ahmose-18": True, "ahmose-26": False}}
    tie = kc.resolve_in_context(KINGS, "Amenemhat", record_dynasty=12, record_dates=(-1960, -1950), strict=True)
    assert tie["context"]["candidates_in_date"] == ["amenemhat-12a"]


def test_a_records_date_range_is_read_as_given() -> None:
    assert kc.record_range(-664, -525) == (-664, -525)
    assert kc.record_range(None, -525) == (-525, -525)
    assert kc.record_range(None, None) is None
    # A range that ends before it starts is the museum's error, read as no date.
    assert kc.record_range(-664, -712) is None


def test_record_contexts_read_the_single_dynasty_and_the_dates() -> None:
    rows = [{"id": "met-1", "dynasty": "Dynasty 18", "date_start": -1550, "date_end": -1525},
            {"id": "met-2", "dynasty": "Dynasty 19–20", "date_start": None, "date_end": -1100},
            {"id": "met-3"}]
    assert al.record_contexts(rows) == {
        "met-1": {"dynasty": 18, "dates": (-1550, -1525)},
        "met-2": {"dynasty": None, "dates": (-1100, -1100)},
        "met-3": {"dynasty": None, "dates": None}}


def test_the_graph_gives_a_kings_reign_as_the_span_of_its_sources() -> None:
    kings = al.load_authority().kings
    # Sankhkare Mentuhotep III: Beckerath 1995–1983, pharaoh.se 1958–1947, Leprohon undated.
    assert kings.reign("cluster-beckerath-11.06") == (-1995, -1947)
    assert kings.dynasties("cluster-beckerath-11.06") == (11,)
    assert kings.reign("cluster-leprohon-leprohon-13.33") == (-1701, -1661)
    assert kings.label("cluster-leprohon-leprohon-13.33") == "Aya"


def test_the_committed_measure_is_the_reported_effect() -> None:
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "docs/evaluations/king-context-2026-10-17"
    measure = json.loads((root / "results/measure.json").read_text())
    assert measure["changed_mentions"] == {"met": 13}
    assert measure["changes"]["met"] == {
        "met|link_added_from_ambiguous:record_context|Teti|Dynasty 6|cluster-beckerath-06.01": 3,
        "met|link_removed:record_context_conflict|Amenhotep II|Dynasty 19|None": 1,
        "met|link_removed:record_context_conflict|Aya|Dynasty 18|None": 7,
        "met|link_removed:record_context_conflict|Ramesses IV|Dynasty 19|None": 1,
        "met|link_removed:record_context_conflict|Takeloth II|Dynasty 23|None": 1,
    }
    assert measure["ambiguous_king_mentions_now"] == {"different_kings": 3, "same_label_entries": 56}
    readme = (root / "README.md").read_text()
    assert "13 Met mention changes; no other museum changes." in readme
