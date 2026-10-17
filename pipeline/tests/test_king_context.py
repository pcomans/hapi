"""A king mention in its record's context (`pipeline.authority.king_context`)."""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.authority import king_context as kc
from pipeline.enrich import authority_links as al


class Kings:
    """name → candidate ids; id → (dynasties, reign)."""

    NAMES = {"Aya": ["aya-13"], "Ahmose": ["ahmose-18", "ahmose-26"], "Teti": ["teti-6", "aha-1", "sekhemkhet-3"],
             "Takeloth II": ["takeloth-22"], "Djoser": ["djoser-3"], "Nobody": [],
             "Undated": ["undated-x", "ahmose-18"]}
    KINGS = {"aya-13": ((13,), (-1701, -1661)), "ahmose-18": ((18,), (-1550, -1525)),
             "ahmose-26": ((26,), (-570, -526)), "teti-6": ((6,), (-2305, -2279)), "aha-1": ((1,), None),
             "sekhemkhet-3": ((3,), (-2565, -2559)), "takeloth-22": ((22,), (-850, -825)),
             "djoser-3": ((3,), None), "undated-x": ((), None)}

    def resolve(self, name: str) -> dict:
        found = self.NAMES[name]
        status = "resolved" if len(found) == 1 else "ambiguous" if found else "unmatched"
        return {"status": status, "target_ids": list(found), "resolution_method": "raw_exact" if found else None}

    def dynasties(self, target_id: str) -> tuple[int, ...]:
        return self.KINGS[target_id][0]

    def reign(self, target_id: str) -> tuple[int, int] | None:
        return self.KINGS[target_id][1]


KINGS = Kings()


def resolve(name: str, *, dynasty=None, dates=None, reign_field: bool, refused=frozenset()) -> tuple:
    found = kc.resolve_in_context(KINGS, name, record_dynasty=dynasty, record_dates=dates,
                                  catalogued_reign=reign_field, refused_on_record=frozenset(refused))
    return found["status"], found["target_ids"], found["context_rule"]


def test_a_reign_field_whose_dynasty_and_date_both_clash_never_links_the_king() -> None:
    # The Met's Dynasty 18 "reign of Aya" records, c. 1327 BCE: the only "Aya" is the Dynasty 13 king.
    assert resolve("Aya", dynasty=18, dates=(-1327, -1327), reign_field=True) == (
        "unmatched", [], "record_context_conflict")
    assert resolve("Aya", dynasty=13, dates=(-1700, -1676), reign_field=True) == ("resolved", ["aya-13"], None)


def test_a_dynasty_number_alone_or_a_date_alone_is_no_clash() -> None:
    # The Met's Takeloth II in Aston's Dynasty 23, dated within his reign: kept.
    assert resolve("Takeloth II", dynasty=23, dates=(-837, -812), reign_field=True) == ("resolved", ["takeloth-22"], None)
    # A dynasty clash without dates to confirm it: kept.
    assert resolve("Aya", dynasty=18, reign_field=True) == ("resolved", ["aya-13"], None)
    # A date clash with the king's own dynasty (a placeholder date): kept.
    assert resolve("Aya", dynasty=13, dates=(-1295, -1295), reign_field=True) == ("resolved", ["aya-13"], None)


def test_a_title_cue_may_name_an_earlier_king_so_a_clash_never_drops_it() -> None:
    assert resolve("Aya", dynasty=26, dates=(-664, -525), reign_field=False) == ("resolved", ["aya-13"], None)


def test_a_title_on_a_record_whose_reign_field_refused_the_king_does_not_name_him_either() -> None:
    # Met 557077: "reign of Aya" refused for Dynasty 18; its title "… Aya (II)" names the same name.
    assert resolve("Aya", dynasty=18, dates=(-1327, -1323), reign_field=False, refused={"aya-13"}) == (
        "unmatched", [], "record_context_conflict")


def test_the_records_dynasty_chooses_among_kings_of_one_name() -> None:
    assert resolve("Teti", dynasty=6, reign_field=True) == ("resolved", ["teti-6"], "record_context")
    assert resolve("Ahmose", dynasty=26, reign_field=False) == ("resolved", ["ahmose-26"], "record_context")
    # A dynasty that fits none chooses none.
    assert resolve("Ahmose", dynasty=12, reign_field=False) == ("ambiguous", ["ahmose-18", "ahmose-26"], None)


def test_a_reign_field_that_drops_all_but_one_candidate_resolves_by_context() -> None:
    # Dynasty 26 c. 600 BCE: Ahmose I clashes on both and is dropped; Amasis remains, and fits.
    assert resolve("Ahmose", dynasty=26, dates=(-600, -590), reign_field=True) == ("resolved", ["ahmose-26"], "record_context")
    # The dropped one is recorded, and so is that the context decided, even with the survivor unknown.
    found = kc.resolve_in_context(KINGS, "Undated", record_dynasty=26, record_dates=(-600, -590),
                                  catalogued_reign=True, refused_on_record=frozenset())
    assert (found["status"], found["target_ids"], found["context_rule"], found["context"]["dropped"]) == (
        "resolved", ["undated-x"], "record_context", ["ahmose-18"])


def test_without_context_a_name_links_only_when_one_king_has_it() -> None:
    assert resolve("Djoser", reign_field=True) == ("resolved", ["djoser-3"], None)
    assert resolve("Ahmose", reign_field=True) == ("ambiguous", ["ahmose-18", "ahmose-26"], None)
    assert resolve("Nobody", dynasty=18, reign_field=True) == ("unmatched", [], None)


def test_a_candidate_the_king_lists_do_not_date_keeps_the_choice_open() -> None:
    assert resolve("Undated", dynasty=18, reign_field=True) == ("ambiguous", ["undated-x", "ahmose-18"], None)
    assert kc.dynasty_fit(KINGS, "undated-x", 18) is None


def test_the_slack_is_fifty_years_each_side() -> None:
    assert kc.DATE_SLACK_YEARS == 50
    # Aya's reign ends 1661 BCE: a record of 1611 BCE does not clash, one of 1610 does.
    assert kc.dates_clash(KINGS, "aya-13", (-1611, -1611)) is False
    assert kc.dates_clash(KINGS, "aya-13", (-1610, -1600)) is True
    assert kc.dates_clash(KINGS, "aya-13", (-1751, -1751)) is False
    assert kc.dates_clash(KINGS, "aya-13", (-1800, -1752)) is True
    assert kc.dates_clash(KINGS, "djoser-3", (-1000, -900)) is False  # no reign dates: no clash
    assert kc.clashes(KINGS, "aya-13", 18, (-1327, -1327)) is True
    assert kc.clashes(KINGS, "aya-13", 13, (-1327, -1327)) is False


def test_the_resolution_says_what_context_it_read() -> None:
    found = kc.resolve_in_context(KINGS, "Ahmose", record_dynasty=18, record_dates=(-1550, -1530),
                                  catalogued_reign=True, refused_on_record=frozenset())
    assert found["context"] == {"record_dynasty": 18, "record_dates": [-1550, -1530],
                                "candidate_fit": {"ahmose-18": True, "ahmose-26": False},
                                "candidate_clash": {"ahmose-18": False, "ahmose-26": True}, "dropped": ["ahmose-26"]}


def test_a_records_date_range_is_read_as_given() -> None:
    assert kc.record_range(-664, -525) == (-664, -525)
    assert kc.record_range(None, -525) == (-525, -525)
    assert kc.record_range(None, None) is None
    # A range that ends before it starts is the museum's error, read as no date.
    assert kc.record_range(-664, -712) is None


def test_record_dates_are_each_records_range() -> None:
    rows = [{"id": "met-1", "date_start": -1550, "date_end": -1525}, {"id": "met-2", "date_start": None, "date_end": -1100},
            {"id": "met-3"}]
    assert al.record_dates(rows) == {"met-1": (-1550, -1525), "met-2": (-1100, -1100), "met-3": None}


def test_the_graph_gives_a_kings_reign_as_the_span_of_its_sources() -> None:
    kings = al.load_authority().kings
    # Sankhkare Mentuhotep III: Beckerath 1995–1983, pharaoh.se 1958–1947, Leprohon undated.
    assert kings.reign("cluster-beckerath-11.06") == (-1995, -1947)
    assert kings.dynasties("cluster-beckerath-11.06") == (11,)
    assert kings.reign("cluster-leprohon-leprohon-13.33") == (-1701, -1661)


def test_a_title_mention_on_a_record_with_a_refused_reign_is_refused_end_to_end() -> None:
    authority = al.load_authority()
    field_reign, field_title = "reign of Aya", "Scarab of Pharaoh Aya"
    base = {"artifact_id": "met-1", "museum": "met", "entity_type": "ruler", "expression_type": "single_identity",
            "record_dynasty": "Dynasty 18", "mention_text": "Aya"}
    mentions = [
        {**base, "mention_id": "m-1", "field_path": "reign", "field_value": field_reign, "span_start": field_reign.index("Aya"),
         "span_end": field_reign.index("Aya") + 3,
         "evidence_role": "catalogued_reign"},
        {**base, "mention_id": "m-2", "field_path": "title", "field_value": field_title,
         "span_start": field_title.index("Aya"), "span_end": field_title.index("Aya") + 3, "evidence_role": "explicit_royal_text_cue"},
    ]
    rows = al.resolve_mentions(mentions, "authority", authority, {"met-1": (-1327, -1323)})
    assert [(r["status"], r["reason"]) for r in rows] == [
        ("unmatched", "record_context_conflict"), ("unmatched", "record_context_conflict")]
    # The same title on a record whose reign field gives no clash keeps its one king.
    rows = al.resolve_mentions([mentions[1]], "authority", authority, {"met-1": (-1327, -1323)})
    assert [(r["status"], r["target_ids"]) for r in rows] == [("resolved", ["cluster-leprohon-leprohon-13.33"])]


def test_the_committed_measure_is_the_reported_effect() -> None:
    root = Path(__file__).resolve().parents[2] / "docs/evaluations/king-context-2026-10-17"
    measure = json.loads((root / "results/measure.json").read_text())
    assert measure["schema_version"] == "hapi-king-context-measure/4"
    assert measure["exposure"] == {
        "dynasty_conflict_not_dropped:dates_within_slack": 2, "dynasty_conflict_not_dropped:king_has_no_reign_dates": 3,
        "title_dropped_king_the_reign_field_refused": 2, "title_keeps_clashing_king:record_later_than_king": 1}
    assert measure["changed_mentions"] == {"met": 13}
    assert measure["changes"]["met"] == {
        "met|ambiguous_to_ambiguous:3_to_2_candidates|Menkheperre|Dynasty 21|None": 1,
        "met|link_added_from_ambiguous:record_context|Teti|Dynasty 6|cluster-beckerath-06.01": 3,
        "met|link_removed:record_context_conflict|Amenhotep II|Dynasty 19|None": 1,
        "met|link_removed:record_context_conflict|Aya|Dynasty 18|None": 8,
    }
    aya = "cluster-leprohon-leprohon-13.33"
    assert measure["record_links_removed"] == sorted(
        [f"met-{n}|{aya}" for n in (550059, 550075, 557077, 557785, 557786, 557787, 567754)]
        + ["met-549239|cluster-beckerath-18.07"])
    assert measure["record_links_added"] == ["met-543897|cluster-beckerath-06.01", "met-543922|cluster-beckerath-06.01"]
    assert measure["ambiguous_king_mentions_now"] == {"candidates_all_labelled_apart": 3, "candidates_sharing_a_label": 56}
    readme = (root / "README.md").read_text()
    assert "13 Met mentions change; no other\nmuseum changes" in readme
    for record in ("met-550059", "-567754", "met-543897", "met-549239"):
        assert record in readme

