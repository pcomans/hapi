"""Issue #342 — the rules that let the high-frequency ruler clusters (Amenhotep III,
Akhenaten, Ramesses II) reconcile instead of abstaining: the era gate, added-epithet
handling, Leprohon titulary-stage identity, the dynasty-scoped homonym and uniqueness
rules, intra-source cluster edges, and the pinned Vercel AI Gateway reviewer."""

from __future__ import annotations

import json

import pytest

from pipeline.authority.claimgraph import verdicts as verdicts_mod
from pipeline.authority.claimgraph.build_graph import AUTHORITY_ROOT
from pipeline.authority.claimgraph.clusters import INTRA_SOURCE_BASIS, compute_clusters
from pipeline.authority.claimgraph.graph_ir import build_documentary_graph
from pipeline.authority.claimgraph.matcher import (
    Candidate,
    era_conflict,
    generate_candidates,
    same_person_groups,
    uniqueness_clashes,
)
from pipeline.authority.claimgraph.normalize import NameForm
from pipeline.authority.claimgraph.reviewer import (
    SYSTEM_PROMPT,
    VERDICT_APPROVED,
    VERDICT_REJECTED,
    ReviewerProvenanceError,
    Verdict,
    _build_user_prompt,
    review_deterministic,
    review_with_vercel,
)
from pipeline.authority.claimgraph.sources import (
    SOURCE_AUTHORITY,
    RulerRecord,
    SourceRowError,
    _from_titulary_list,
    _link_titulary_stages,
    load_all_sources,
)


def _rec(
    source_id,
    local_id,
    display_name,
    *,
    dynasty=None,
    prenomina=(),
    nomina=(),
    reign_start_bce=None,
    same_as=(),
):
    def forms(values):
        return [v if isinstance(v, NameForm) else NameForm(surface=v) for v in values]

    return RulerRecord(
        source_id=source_id,
        local_id=local_id,
        display_name=display_name,
        display_name_absence=None,
        alt_names=[],
        dynasty=dynasty,
        dynasty_label=None,
        prenomina=forms(prenomina),
        horus_names=[],
        nomina=forms(nomina),
        reign_start_bce=reign_start_bce,
        reign_end_bce=None,
        intra_source_same_as=list(same_as),
        authority=SOURCE_AUTHORITY[source_id],
    )


def _epithet(surface, translit=None):
    return NameForm(surface=surface, translit=translit, is_added_epithet=True)


def _pair(cands, a_id, b_id):
    (match,) = [c for c in cands if {c.a_id, c.b_id} == {a_id, b_id}]
    return match


# --- era gate --------------------------------------------------------------


def test_reign_starts_200_years_apart_are_an_era_conflict():
    ramesses = _rec("beckerath", "beckerath-1", "Ramses II.", dynasty=19, reign_start_bce=-1279)
    osorkon = _rec("pharaoh_se", "pharaoh_se-1", "Osorkon II", dynasty=22, reign_start_bce=-872)
    # tolerance at 1279 BCE: 150 + 1279 // 20 = 213, so the limit is 214
    assert era_conflict(ramesses, osorkon) == (
        "Reign starts 407 years apart (-1279 vs -872); >= 214 is distinct kings."
    )


def test_reign_starts_199_years_apart_are_not_an_era_conflict():
    a = _rec("beckerath", "beckerath-1", "A", reign_start_bce=-900)
    b = _rec("pharaoh_se", "pharaoh_se-1", "B", reign_start_bce=-701)
    assert era_conflict(a, b) is None


def test_reign_gap_of_exactly_200_years_is_an_era_conflict_after_1000_bce():
    """At 900 BCE the cross-chronology tolerance is 150 + 45 = 195, so the 200-year floor
    governs and is inclusive."""
    a = _rec("beckerath", "beckerath-1", "A", reign_start_bce=-900)
    b = _rec("pharaoh_se", "pharaoh_se-1", "B", reign_start_bce=-700)
    assert era_conflict(a, b) == (
        "Reign starts 200 years apart (-900 vs -700); >= 200 is distinct kings."
    )


def test_a_clean_run_writes_no_failed_attempts_file(tmp_path):
    def reviewer_fn(c, a, b):
        return Verdict(candidate_id=c.id, outcome=VERDICT_APPROVED, reason="same", reviewer="llm",
                       request_digest=None)

    recs = [
        _rec("leprohon", "leprohon-1", "Amasis", prenomina=["Khnemibre"]),
        _rec("beckerath", "beckerath-1", "Amasis", prenomina=["Chnem-ib-rê"]),
    ]
    cache = tmp_path / "graph.json.verdict-cache.jsonl"
    verdicts_mod.resolve_matches(
        recs, mode="llm", reviewer_fn=reviewer_fn, model="m", cache_path=str(cache)
    )
    assert cache.exists()
    assert not (tmp_path / "graph.json.verdict-cache.jsonl.failed-attempts.jsonl").exists()


def test_reign_gap_threshold_scales_with_antiquity():
    """At 2000 BCE cross-framework dates may differ by 150 + 100 = 250 years: a 220-year
    gap is chronology divergence, not proof of two kings."""
    a = _rec("beckerath", "beckerath-1", "A", reign_start_bce=-2000)
    b = _rec("pharaoh_se", "pharaoh_se-1", "B", reign_start_bce=-1780)
    assert era_conflict(a, b) is None
    c = _rec("pharaoh_se", "pharaoh_se-2", "C", reign_start_bce=-1749)
    assert era_conflict(a, c) == (
        "Reign starts 251 years apart (-2000 vs -1749); >= 251 is distinct kings."
    )


def test_dynasties_two_apart_outside_the_contested_bands_are_an_era_conflict():
    amenhotep = _rec("beckerath", "beckerath-1", "Amenophis III.", dynasty=18)
    ramesses = _rec("leprohon", "leprohon-1", "Ramesses VI", dynasty=20)
    assert era_conflict(amenhotep, ramesses) == (
        "Dynasties 18 and 20 are 2 apart and not within one contested numbering band "
        "((6, 10), (13, 17), (21, 26))."
    )


@pytest.mark.parametrize(
    ("a_id", "b_id"),
    [
        # Leprohon "Dynasty 8a" = pharaoh.se Dyn 10: the same kings in the same order.
        ("leprohon-leprohon-8a.01", "pharaoh_se-Sekhemkara-I"),
        ("leprohon-leprohon-8a.02", "pharaoh_se-Wadjkara"),
        ("leprohon-leprohon-8a.04", "pharaoh_se-Imhotep"),
        ("leprohon-leprohon-8a.05", "pharaoh_se-Hotep"),
        ("leprohon-leprohon-8a.06", "pharaoh_se-Khui"),
        ("leprohon-leprohon-8a.07", "pharaoh_se-Isu"),
        ("leprohon-leprohon-8a.08", "pharaoh_se-Iytenu"),
        # Ryholt's disputed Netjerkare = Nitocris equation: review, never reject.
        ("leprohon-leprohon-6.07", "pharaoh_se-Netjerikara"),
    ],
)
def test_first_intermediate_period_renumbering_is_not_an_era_conflict(a_id, b_id):
    by_id = {r.local_id: r for r in load_all_sources(AUTHORITY_ROOT).records}
    assert era_conflict(by_id[a_id], by_id[b_id]) is None


def test_adjacent_dynasties_are_not_an_era_conflict():
    a = _rec("leprohon", "leprohon-1", "Nebmaatre", dynasty=17)
    b = _rec("beckerath", "beckerath-1", "Amenophis III.", dynasty=18)
    assert era_conflict(a, b) is None


def test_necho_i_in_dynasty_24_and_26_is_not_an_era_conflict():
    """Kitchen files Necho I under Dyn 24, Leprohon under Dyn 26: both inside the Third
    Intermediate / Late band where sources number parallel lines differently."""
    kitchen = _rec("kitchen", "kitchen-1", "Necho I", dynasty=24, reign_start_bce=-672)
    leprohon = _rec("leprohon", "leprohon-1", "Necho I", dynasty=26)
    assert era_conflict(kitchen, leprohon) is None


def test_bands_do_not_bridge_into_each_other():
    """Dyn 17 and Dyn 21 are both 'contested', but in different bands: still a conflict."""
    a = _rec("ryholt", "ryholt-1", "A", dynasty=17)
    b = _rec("kitchen", "kitchen-1", "B", dynasty=21)
    assert era_conflict(a, b) == (
        "Dynasties 17 and 21 are 4 apart and not within one contested numbering band "
        "((6, 10), (13, 17), (21, 26))."
    )


def test_missing_era_evidence_is_never_a_conflict():
    a = _rec("leprohon", "leprohon-1", "A")
    b = _rec("pharaoh_se", "pharaoh_se-1", "B", dynasty=8, reign_start_bce=-2100)
    assert era_conflict(a, b) is None


def test_era_conflict_is_rejected_deterministically():
    recs = [
        _rec("beckerath", "beckerath-19.03", "Ramses II.", dynasty=19,
             prenomina=["User-maat-rê sotep-en-rê"], reign_start_bce=-1279),
        _rec("pharaoh_se", "pharaoh_se-Osorkon-II", "Osorkon II", dynasty=22,
             prenomina=["User Maat Ra, setep en Ra"], reign_start_bce=-872),
    ]
    (cand,) = generate_candidates(recs)
    verdict = review_deterministic(cand, forced_escalate=False)
    assert verdict.outcome == VERDICT_REJECTED
    assert verdict.reviewer == "deterministic"
    assert verdict.reason == (
        "Era gate (ADR-020 amendment 2026-10-10): Reign starts 407 years apart "
        "(-1279 vs -872); >= 214 is distinct kings."
    )


def test_era_conflict_never_reaches_the_live_reviewer():
    def must_not_be_called(c, a, b):
        raise AssertionError(f"reviewer called for era-rejected {c.id}")

    recs = [
        _rec("beckerath", "beckerath-19.03", "Ramses II.", dynasty=19,
             prenomina=["User-maat-rê sotep-en-rê"], reign_start_bce=-1279),
        _rec("pharaoh_se", "pharaoh_se-Osorkon-II", "Osorkon II", dynasty=22,
             prenomina=["User Maat Ra, setep en Ra"], reign_start_bce=-872),
    ]
    res = verdicts_mod.resolve_matches(
        recs, mode="llm", reviewer_fn=must_not_be_called, model="m", cache_path=None
    )
    assert res.approved_edges == []
    assert res.escalations == []
    (verdict,) = res.verdicts
    assert verdict.outcome == VERDICT_REJECTED
    assert verdict.interactions == []


# --- added epithets --------------------------------------------------------


def test_added_epithet_alone_is_not_a_matching_key():
    """Leprohon's Amenhotep III lists mr.n rꜥ ('Whom Re has loved') as an epithet added to
    his throne name; on its own it spells the Dyn 6 throne name Merenre."""
    amenhotep = _rec("leprohon", "leprohon-18.09", "Amenhotep III", dynasty=18,
                     prenomina=[NameForm("neb maat ra", "nb mꜣꜥt rꜥ"),
                                _epithet("mer en ra", "mr.n rꜥ")])
    merenre = _rec("pharaoh_se", "pharaoh_se-Nemtiemsaf-I", "Nemtiemsaf I", dynasty=6,
                   prenomina=[NameForm("Mer en Ra", "mr-n-rꜥ")])
    assert generate_candidates([amenhotep, merenre]) == []


def test_name_plus_added_epithet_matches_the_compound_another_source_prints():
    """Leprohon gives Ramesses II's throne name as wsr mꜣꜥt rꜥ and stp.n rꜥ as an added
    epithet; Beckerath prints the compound User-maat-rê sotep-en-rê as one throne name."""
    leprohon = _rec("leprohon", "leprohon-19.03", "Ramesses II", dynasty=19,
                    prenomina=[NameForm("weser maat ra", "wsr mꜣꜥt rꜥ"),
                               _epithet("setep en ra", "stp.n rꜥ")])
    pharaoh = _rec("pharaoh_se", "pharaoh_se-Ramesses-II", "Ramesses II", dynasty=19,
                   prenomina=[NameForm("User Maat Ra, setep en Ra", "wsr-mꜢꜤt-rꜤ stp.n-rꜤ")])
    (cand,) = generate_candidates([leprohon, pharaoh])
    assert cand.basis == "prenomen"
    assert "wsrmtrstpnr" in cand.shared_prenomen_keys


def test_only_the_primary_throne_name_is_compounded_with_added_epithets():
    """Thutmose III's late epithet must not be grafted onto his early variant."""
    leprohon = _rec("leprohon", "leprohon-18.05", "Thutmose III", dynasty=18,
                    prenomina=[NameForm("men kheper ra", "mn ḫpr rꜥ"),
                               NameForm("men kheper ka ra", "mn ḫpr kꜣ rꜥ"),
                               _epithet("iwa ra", "iwꜥ rꜥ")])
    other = _rec("pharaoh_se", "pharaoh_se-X", "X", dynasty=18,
                 prenomina=[NameForm("Men kheper ka Ra iwa Ra", "mn-ḫpr-kꜣ-rꜥ iwꜥ-rꜥ")])
    assert generate_candidates([leprohon, other]) == []


def test_birth_names_are_not_compounded_with_added_epithets():
    """Amenhotep II + ḥqꜣ wꜣst spells Amenhotep III's nomen; it must not become a key."""
    amenhotep_ii = _rec("leprohon", "leprohon-18.07", "Amenhotep II", dynasty=18,
                        nomina=[NameForm("imen hetep", "imn ḥtp"),
                                _epithet("netjer heqa iunu", "nṯr ḥqꜣ iwnw")])
    other = _rec("pharaoh_se", "pharaoh_se-X", "Unrelated", dynasty=18,
                 nomina=[NameForm("imen hetep netjer heqa iunu", "imn-ḥtp nṯr-ḥqꜣ-iwnw")])
    assert generate_candidates([amenhotep_ii, other]) == []


@pytest.mark.parametrize(
    "fragment", ["Djed /// Re", "Senefer[...]re", "It...", "//-kꜣ-//", "[..]-ḏfꜣ-rꜥ"]
)
def test_fragmentary_throne_names_never_corroborate(fragment):
    a = _rec("leprohon", "leprohon-1", "A", prenomina=[fragment])
    b = _rec("ryholt", "ryholt-1", "B", prenomina=[fragment])
    cands = generate_candidates([a, b])
    assert all(c.basis == "name_only" for c in cands)


def test_alternative_readings_are_not_fragments():
    """A lone slash separates alternative readings (Beckerath `A-qen-en-rê/A-user-rê`)."""
    a = _rec("beckerath", "beckerath-1", "Apophis", prenomina=["A-qen-en-rê/A-user-rê"])
    b = _rec("ryholt", "ryholt-1", "Apepi", prenomina=["A-qen-en-rê/A-user-rê"])
    (cand,) = generate_candidates([a, b])
    assert cand.basis == "prenomen"


def test_loader_marks_added_epithets_from_the_transcription_convention():
    row = {"throne_names": [
        {"anglicised": "neb maat ra", "transliteration": "nb mꜣꜥt rꜥ", "is_variant": False,
         "source_note": None},
        {"anglicised": "mer en ra", "transliteration": "mr.n rꜥ", "is_variant": True,
         "source_note": "Epithet added to the Throne name."},
        {"anglicised": "tit ra", "transliteration": "tit rꜥ", "is_variant": True,
         "source_note": "Epithet added to the Throne name (from the Abydos Seven Chapels)."},
    ]}
    forms = _from_titulary_list(row, "throne_names", source="leprohon", row_id="r1")
    assert forms == [
        NameForm("neb maat ra", "nb mꜣꜥt rꜥ", is_added_epithet=False),
        NameForm("mer en ra", "mr.n rꜥ", is_added_epithet=True),
        NameForm("tit ra", "tit rꜥ", is_added_epithet=True),
    ]


def test_loader_rejects_an_epithet_note_on_a_primary_name():
    row = {"throne_names": [
        {"anglicised": "mer en ra", "transliteration": "mr.n rꜥ", "is_variant": False,
         "source_note": "Epithet added to the Throne name."},
    ]}
    with pytest.raises(SourceRowError, match="primary name of a slot cannot be an epithet"):
        _from_titulary_list(row, "throne_names", source="leprohon", row_id="r1")


def test_committed_leprohon_epithets_are_loaded_as_epithets():
    by_id = {r.local_id: r for r in load_all_sources(AUTHORITY_ROOT).records}
    amenhotep = by_id["leprohon-leprohon-18.09"]
    assert [(f.translit, f.is_added_epithet) for f in amenhotep.prenomina] == [
        ("nb mꜣꜥt rꜥ", False),
        ("tit rꜥ", True),
        ("tit imn", True),
        ("šsp.n itmw", True),
        ("stp.n rꜥ", True),
        ("iwꜥ rꜥ", True),
        ("ir.n rꜥ", True),
        ("mr.n rꜥ", True),
        ("sꜣ rꜥ", True),
    ]


# --- Leprohon titulary stages ----------------------------------------------


def test_stage_rows_without_a_sibling_raise():
    lone = _rec("leprohon", "leprohon-leprohon-18.10a", "Amenhotep IV")
    with pytest.raises(ValueError, match="has no sibling stage and no parent row"):
        _link_titulary_stages([lone], {"leprohon-18.10": ["leprohon-leprohon-18.10a"]})


def test_stage_rows_link_to_each_other_and_to_their_parent_row():
    parent = _rec("leprohon", "leprohon-leprohon-12.01", "Amenemhat I")
    a = _rec("leprohon", "leprohon-leprohon-12.01a", "Amenemhat I (a)")
    b = _rec("leprohon", "leprohon-leprohon-12.01b", "Amenemhat I (b)")
    _link_titulary_stages(
        [parent, a, b], {"leprohon-12.01": ["leprohon-leprohon-12.01a", "leprohon-leprohon-12.01b"]}
    )
    assert parent.intra_source_same_as == ["leprohon-leprohon-12.01a", "leprohon-leprohon-12.01b"]
    assert a.intra_source_same_as == ["leprohon-leprohon-12.01", "leprohon-leprohon-12.01b"]
    assert b.intra_source_same_as == ["leprohon-leprohon-12.01", "leprohon-leprohon-12.01a"]


def test_committed_akhenaten_stages_are_one_person_and_consorts_are_not():
    records = load_all_sources(AUTHORITY_ROOT).records
    by_id = {r.local_id: r for r in records}
    assert by_id["leprohon-leprohon-18.10a"].intra_source_same_as == ["leprohon-leprohon-18.10b"]
    assert by_id["leprohon-leprohon-18.10b"].intra_source_same_as == ["leprohon-leprohon-18.10a"]
    assert by_id["leprohon-leprohon-33.02a"].intra_source_same_as == []  # Arsinoe II
    person = same_person_groups(records)
    assert person["leprohon-leprohon-18.10b"] == "leprohon-leprohon-18.10a"
    assert person["leprohon-leprohon-33.02a"] == "leprohon-leprohon-33.02a"


# --- reused throne names, scoped by dynasty --------------------------------


def _nebmaatre_records(*extra):
    return [
        _rec("beckerath", "beckerath-18.09", "Amenophis III.", dynasty=18,
             prenomina=["Neb-maat-rê"], reign_start_bce=-1388),
        _rec("leprohon", "leprohon-18.09", "Amenhotep III", dynasty=18,
             prenomina=[NameForm("neb maat ra", "nb mꜣꜥt rꜥ")]),
        _rec("leprohon", "leprohon-17a.01", "Nebmaatre", dynasty=17,
             prenomina=[NameForm("neb maat ra", "nb mꜣꜥt rꜥ")]),
        *extra,
    ]


def test_reused_throne_name_is_cleared_for_the_sole_bearer_in_the_dynasty():
    cands = generate_candidates(_nebmaatre_records())
    assert _pair(cands, "beckerath-18.09", "leprohon-18.09").homonym_trap is None
    assert _pair(cands, "beckerath-18.09", "leprohon-17a.01").homonym_trap == "nbmaatra"


def test_reused_throne_name_stays_trapped_with_a_same_dynasty_bearer():
    other = _rec("leprohon", "leprohon-18.99", "Other Nebmaatre", dynasty=18,
                 prenomina=[NameForm("neb maat ra", "nb mꜣꜥt rꜥ")])
    cands = generate_candidates(_nebmaatre_records(other))
    assert _pair(cands, "beckerath-18.09", "leprohon-18.09").homonym_trap == "nbmaatra"


def test_an_undated_bearer_does_not_block_but_its_own_pair_stays_trapped():
    """pharaoh.se's unplaced Ini II (Menkheperre, no dynasty) must not stop Thutmose III
    reaching review; its own pairs with Thutmose III share no dynasty and stay trapped."""
    undated = _rec("leprohon", "leprohon-x", "Undated Nebmaatre",
                   prenomina=[NameForm("neb maat ra", "nb mꜣꜥt rꜥ")])
    cands = generate_candidates(_nebmaatre_records(undated))
    assert _pair(cands, "beckerath-18.09", "leprohon-18.09").homonym_trap is None
    assert _pair(cands, "beckerath-18.09", "leprohon-x").homonym_trap == "nbmaatra"


def test_a_skeleton_collision_does_not_veto_an_unambiguous_full_name():
    """Thutmose IV's Menkheperure and Thutmose III's Menkheperre share the vowel-less
    skeleton mnkhprr; the full Menkheperre is still borne by only one Dyn 18 king."""
    recs = [
        _rec("beckerath", "beckerath-18.06", "Tuthmosis III.", dynasty=18,
             prenomina=["Men-cheper-rê"]),
        _rec("pharaoh_se", "pharaoh_se-Thutmose-III", "Thutmose III", dynasty=18,
             prenomina=[NameForm("Men kheper Ra", "mn-ḫpr-rꜥ")]),
        _rec("pharaoh_se", "pharaoh_se-Thutmose-IV", "Thutmose IV", dynasty=18,
             prenomina=[NameForm("Men kheperu Ra", "mn-ḫprw-rꜥ")]),
    ]
    cands = generate_candidates(recs)
    assert _pair(cands, "beckerath-18.06", "pharaoh_se-Thutmose-III").homonym_trap is None


def test_a_pair_sharing_only_ambiguous_reused_names_stays_trapped():
    """Every shared reused name is ambiguous in the contested band: still trapped, even
    though the pair also shares a compound that is off the homonym list."""
    recs = [
        _rec("kitchen", "kitchen-23.03", "Osorkon III", dynasty=23,
             prenomina=["Usermaatre", "Usermaatre Setepenamun"]),
        _rec("pharaoh_se", "pharaoh_se-Takelot-III", "Takelot III", dynasty=23,
             prenomina=["User Maat Ra", "User Maat Ra setep en Amun"]),
    ]
    (cand,) = generate_candidates(recs)
    assert cand.homonym_trap is not None


def test_stage_rows_of_one_king_are_one_bearer_of_a_reused_name():
    recs = [
        _rec("beckerath", "beckerath-18.05", "Thutmosis III.", dynasty=18,
             prenomina=["Men-cheper-rê"]),
        _rec("leprohon", "leprohon-18.05a", "Thutmose III (a)", dynasty=18,
             prenomina=[NameForm("men kheper ra", "mn ḫpr rꜥ")],
             same_as=["leprohon-18.05b"]),
        _rec("leprohon", "leprohon-18.05b", "Thutmose III (b)", dynasty=18,
             prenomina=[NameForm("men kheper ra", "mn ḫpr rꜥ")],
             same_as=["leprohon-18.05a"]),
    ]
    cands = generate_candidates(recs)
    assert _pair(cands, "beckerath-18.05", "leprohon-18.05a").homonym_trap is None
    assert _pair(cands, "beckerath-18.05", "leprohon-18.05b").homonym_trap is None


def test_reused_throne_name_stays_trapped_in_a_contested_band():
    recs = [
        _rec("beckerath", "beckerath-22.06", "Schoschenq III.", dynasty=22,
             prenomina=["User-maat-rê"]),
        _rec("kitchen", "kitchen-22.06", "Shoshenq III", dynasty=22, prenomina=["Usermaatre"]),
    ]
    (cand,) = generate_candidates(recs)
    assert cand.homonym_trap == "srmtr"  # first shared homonym key in sorted order


# --- uniqueness clashes ----------------------------------------------------


def _cand(cid, a_id, b_id, a_source, b_source, *, dynasty_match, uncontested):
    return Candidate(
        id=cid, a_id=a_id, b_id=b_id, a_source=a_source, b_source=b_source,
        a_name=a_id, b_name=b_id, basis="prenomen", shared_prenomen_keys=["k"],
        shared_name_keys=[], dynasty_match=dynasty_match, reign_far_apart=False,
        homonym_trap=None, same_uncontested_dynasty=uncontested,
    )


def test_stage_siblings_are_one_target_not_a_clash():
    cands = [
        _cand("c1", "beckerath-18.10", "lep-18.10a", "beckerath", "leprohon",
              dynasty_match=True, uncontested=True),
        _cand("c2", "beckerath-18.10", "lep-18.10b", "beckerath", "leprohon",
              dynasty_match=True, uncontested=True),
    ]
    person = {"lep-18.10a": "lep-18.10a", "lep-18.10b": "lep-18.10a"}
    assert uniqueness_clashes(cands) == {"c1", "c2"}
    assert uniqueness_clashes(cands, person) == set()


def test_stage_siblings_matching_two_distinct_people_still_clash():
    cands = [
        _cand("c1", "beckerath-1", "lep-a", "beckerath", "leprohon",
              dynasty_match=None, uncontested=False),
        _cand("c2", "beckerath-2", "lep-b", "beckerath", "leprohon",
              dynasty_match=None, uncontested=False),
    ]
    person = {"lep-a": "lep-a", "lep-b": "lep-a"}
    assert uniqueness_clashes(cands, person) == {"c1", "c2"}


def test_clash_resolves_to_the_sole_same_dynasty_target():
    """pharaoh.se's Ramesses II (Dyn 19) shares a full throne name with Leprohon's
    Ramesses II (Dyn 19) and Ramesses IV (Dyn 20)."""
    cands = [
        _cand("c-r2", "lep-19.03", "ph-R2", "leprohon", "pharaoh_se",
              dynasty_match=True, uncontested=True),
        _cand("c-r4", "lep-20.03", "ph-R2", "leprohon", "pharaoh_se",
              dynasty_match=False, uncontested=False),
    ]
    assert uniqueness_clashes(cands) == {"c-r4"}


def test_clash_with_an_undated_alternative_stays_escalated():
    cands = [
        _cand("c1", "lep-19.03", "ph-R2", "leprohon", "pharaoh_se",
              dynasty_match=True, uncontested=True),
        _cand("c2", "lep-x", "ph-R2", "leprohon", "pharaoh_se",
              dynasty_match=None, uncontested=False),
    ]
    assert uniqueness_clashes(cands) == {"c1", "c2"}


def test_clash_with_two_same_dynasty_targets_stays_escalated():
    cands = [
        _cand("c1", "lep-1", "ph-R2", "leprohon", "pharaoh_se",
              dynasty_match=True, uncontested=True),
        _cand("c2", "lep-2", "ph-R2", "leprohon", "pharaoh_se",
              dynasty_match=True, uncontested=True),
    ]
    assert uniqueness_clashes(cands) == {"c1", "c2"}


# --- the three #342 kings on the committed sources -------------------------


def _committed_reviewable():
    records = load_all_sources(AUTHORITY_ROOT).records
    cands = generate_candidates(records)
    forced = uniqueness_clashes(cands, same_person_groups(records))
    return {
        frozenset((c.a_id, c.b_id))
        for c in cands
        if c.basis != "name_only" and not c.era_conflict and not c.homonym_trap
        and c.id not in forced
    }, {frozenset((c.a_id, c.b_id)): c for c in cands}


@pytest.mark.parametrize(
    ("a_id", "b_id"),
    [
        ("beckerath-18.09", "leprohon-leprohon-18.09"),
        ("beckerath-18.09", "pharaoh_se-Amenhotep-III"),
        ("leprohon-leprohon-18.09", "pharaoh_se-Amenhotep-III"),
        ("beckerath-18.10", "leprohon-leprohon-18.10a"),
        ("beckerath-18.10", "leprohon-leprohon-18.10b"),
        ("beckerath-18.10", "pharaoh_se-Amenhotep-IV"),
        ("leprohon-leprohon-18.10a", "pharaoh_se-Amenhotep-IV"),
        ("leprohon-leprohon-18.10b", "pharaoh_se-Amenhotep-IV"),
        ("beckerath-19.03", "pharaoh_se-Ramesses-II"),
        ("leprohon-leprohon-19.03", "pharaoh_se-Ramesses-II"),
        ("beckerath-18.06", "leprohon-leprohon-18.05a"),
        ("beckerath-18.06", "leprohon-leprohon-18.05b"),
        ("beckerath-18.06", "pharaoh_se-Thutmose-III"),
        ("leprohon-leprohon-18.05a", "pharaoh_se-Thutmose-III"),
        ("leprohon-leprohon-18.05b", "pharaoh_se-Thutmose-III"),
        ("beckerath-12.01", "pharaoh_se-Amenemhat-I"),
        ("leprohon-leprohon-12.01a", "pharaoh_se-Amenemhat-I"),
        # Pepi II's Neferkare is reused by Dyn 8 kings; a shared Dyn 6 still clears it.
        ("beckerath-06.05", "pharaoh_se-Pepi-II"),
        ("leprohon-leprohon-6.05", "pharaoh_se-Pepi-II"),
    ],
)
def test_committed_same_king_pairs_reach_the_reviewer(a_id, b_id):
    reviewable, _ = _committed_reviewable()
    assert frozenset((a_id, b_id)) in reviewable


def test_herakleopolitan_neferkare_stays_trapped():
    """Leprohon's Dyn 9 covers pharaoh.se's Dyn 9 AND 10, and pharaoh.se has a second
    Dyn 9 Neferkare (as a birth name): a shared "Dyn 9" cannot clear this reused name."""
    _, by_pair = _committed_reviewable()
    pair = by_pair[frozenset(("leprohon-leprohon-9-10a.03", "pharaoh_se-Neferkara-III"))]
    assert pair.homonym_trap is not None


@pytest.mark.parametrize(
    ("a_id", "b_id", "reason"),
    [
        ("beckerath-19.03", "pharaoh_se-Osorkon-II",
         "Reign starts 407 years apart (-1279 vs -872); >= 214 is distinct kings."),
        ("leprohon-leprohon-20.05", "pharaoh_se-Amenhotep-III",
         "Dynasties 20 and 18 are 2 apart and not within one contested numbering band "
         "((6, 10), (13, 17), (21, 26))."),
    ],
)
def test_committed_homonym_pairs_are_era_rejected(a_id, b_id, reason):
    _, by_pair = _committed_reviewable()
    assert by_pair[frozenset((a_id, b_id))].era_conflict == reason


# --- clusters --------------------------------------------------------------


def test_intra_source_identities_join_clusters_once():
    records = [
        _rec("leprohon", "leprohon-leprohon-18.10a", "Amenhotep IV",
             same_as=["leprohon-leprohon-18.10b"]),
        _rec("leprohon", "leprohon-leprohon-18.10b", "Akhenaten",
             same_as=["leprohon-leprohon-18.10a"]),
        _rec("beckerath", "beckerath-18.10", "Amenophis IV."),
    ]
    doc = build_documentary_graph(records)
    edge = verdicts_mod.MatchEdge(
        candidate_id="cand-x", a_id="beckerath-18.10", b_id="leprohon-leprohon-18.10b",
        a_source="beckerath", b_source="leprohon", a_name="Amenophis IV.",
        b_name="Akhenaten", basis="prenomen", shared_prenomen_keys=["k"],
        reason="same", reviewer="llm",
    )
    (cluster,) = compute_clusters(doc.rulers, [edge], doc.intra_source_identities)
    assert cluster.member_ids == [
        "beckerath-18.10", "leprohon-leprohon-18.10a", "leprohon-leprohon-18.10b"
    ]
    assert cluster.sources == ["beckerath", "leprohon"]
    assert cluster.edges == [
        {"a_id": "beckerath-18.10", "b_id": "leprohon-leprohon-18.10b", "basis": "prenomen"},
        {"a_id": "leprohon-leprohon-18.10a", "b_id": "leprohon-leprohon-18.10b",
         "basis": INTRA_SOURCE_BASIS},
    ]


def test_intra_source_identity_alone_forms_a_cluster():
    records = [
        _rec("leprohon", "leprohon-leprohon-18.05a", "Thutmose III (a)",
             same_as=["leprohon-leprohon-18.05b"]),
        _rec("leprohon", "leprohon-leprohon-18.05b", "Thutmose III (b)",
             same_as=["leprohon-leprohon-18.05a"]),
    ]
    doc = build_documentary_graph(records)
    (cluster,) = compute_clusters(doc.rulers, [], doc.intra_source_identities)
    assert cluster.member_ids == ["leprohon-leprohon-18.05a", "leprohon-leprohon-18.05b"]
    assert cluster.source_count == 1


# --- focus_records ---------------------------------------------------------


def test_focus_records_reviews_only_touching_candidates_with_full_set_clashes():
    calls = []

    def reviewer_fn(c, a, b):
        calls.append(c.id)
        return Verdict(candidate_id=c.id, outcome=VERDICT_APPROVED, reason="same", reviewer="llm")

    recs = [
        _rec("leprohon", "leprohon-1", "Amasis", prenomina=["Khnemibre"]),
        _rec("beckerath", "beckerath-1", "Amasis", prenomina=["Chnem-ib-rê"]),
        _rec("beckerath", "beckerath-2", "Amasis bis", prenomina=["Khnemibre"]),
        _rec("leprohon", "leprohon-9", "Khufu", prenomina=["Khufu"]),
        _rec("beckerath", "beckerath-9", "Cheops", prenomina=["Chufu"]),
    ]
    res = verdicts_mod.resolve_matches(
        recs, mode="llm", reviewer_fn=reviewer_fn, model="m",
        focus_records={"beckerath-1"}, cache_path=None,
    )
    assert calls == ["cand-beckerath-1|leprohon-1"]
    # leprohon-1 also matches beckerath-2 in the full set: the focused slice still escalates.
    assert [e.candidate_id for e in res.escalations] == ["cand-beckerath-1|leprohon-1"]
    assert res.approved_edges == []


def test_focus_records_naming_an_unloaded_record_raises():
    recs = [_rec("leprohon", "leprohon-1", "Amasis", prenomina=["Khnemibre"])]
    with pytest.raises(ValueError, match=r"unloaded record\(s\): \['nope'\]"):
        verdicts_mod.resolve_matches(
            recs, mode="deterministic", focus_records={"nope"}, cache_path=None
        )


# --- Vercel AI Gateway reviewer --------------------------------------------


class _FakeHttpResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def _gateway_body(
    final_provider, content='{"outcome":"approved","reason":"same king"}', build="aeb56401"
):
    metadata = {"gateway": {"routing": {"finalProvider": final_provider}}}
    if build is not None:
        metadata[final_provider] = {"systemFingerprint": build}
    return {
        "id": "gen_1",
        "model": "deepseek/deepseek-v4.1-flash",
        "system_fingerprint": "fp_test",
        "choices": [{
            "finish_reason": "stop",
            "message": {
                "role": "assistant",
                "content": content,
                "reasoning": "Both records give the same throne name and dynasty.",
                "provider_metadata": metadata,
            },
        }],
        "usage": {"prompt_tokens": 400, "completion_tokens": 90, "cost": 0.0001},
    }


def _amasis_pair():
    a = _rec("leprohon", "leprohon-45", "Amasis", prenomina=["Khnemibre"])
    b = _rec("beckerath", "beckerath-45", "Amasis", prenomina=["Chnem-ib-rê"])
    return generate_candidates([a, b])[0], a, b


def test_vercel_reviewer_sends_the_pinned_request_and_persists_the_response(monkeypatch):
    import httpx

    sent = {}

    def fake_post(url, headers, json, timeout):
        sent.update(url=url, json=json)
        return _FakeHttpResponse(_gateway_body("deepseek"))

    monkeypatch.setattr(httpx, "post", fake_post)
    cand, a, b = _amasis_pair()
    verdict = review_with_vercel("key", cand, a, b)

    assert sent["url"] == "https://ai-gateway.vercel.sh/v1/chat/completions"
    assert sent["json"] == {
        "model": "deepseek/deepseek-v4.1-flash",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(cand, a, b)},
        ],
        "max_tokens": 32000,
        "reasoning": {"effort": "max"},
        "providerOptions": {"gateway": {"only": ["deepseek"], "order": ["deepseek"]}},
    }
    assert verdict.outcome == VERDICT_APPROVED
    assert verdict.reason == "same king"
    (interaction,) = verdict.interactions
    assert interaction.provider == "vercel"
    assert interaction.requested_model == "deepseek/deepseek-v4.1-flash"
    assert interaction.model_snapshot == "deepseek/deepseek-v4.1-flash@aeb56401"
    assert interaction.raw_response == _gateway_body("deepseek")
    assert interaction.call_error is None


def test_vercel_response_served_by_another_provider_is_refused(monkeypatch):
    import httpx

    monkeypatch.setattr(
        httpx, "post", lambda *args, **kw: _FakeHttpResponse(_gateway_body("fireworks"))
    )
    cand, a, b = _amasis_pair()
    with pytest.raises(ReviewerProvenanceError) as excinfo:
        review_with_vercel("key", cand, a, b)
    err = excinfo.value
    assert err.interaction.call_error == (
        "Vercel AI Gateway served this response from 'fireworks', not the pinned 'deepseek'."
    )
    assert err.interaction.raw_response == _gateway_body("fireworks")


def test_vercel_response_without_the_serving_build_is_refused(monkeypatch):
    import httpx

    body = _gateway_body("deepseek", build=None)
    monkeypatch.setattr(httpx, "post", lambda *args, **kw: _FakeHttpResponse(body))
    cand, a, b = _amasis_pair()
    with pytest.raises(ReviewerProvenanceError) as excinfo:
        review_with_vercel("key", cand, a, b)
    assert excinfo.value.interaction.call_error == (
        "Vercel AI Gateway response does not report the 'deepseek' build "
        "(provider_metadata.deepseek.systemFingerprint)."
    )
    assert excinfo.value.interaction.raw_response == body


def test_reviewer_prompt_lists_added_epithets_apart_from_names():
    a = _rec("leprohon", "leprohon-19.03", "Ramesses II", dynasty=19,
             prenomina=[NameForm("weser maat ra", "wsr mꜣꜥt rꜥ"),
                        _epithet("setep en ra", "stp.n rꜥ")])
    b = _rec("pharaoh_se", "pharaoh_se-Ramesses-II", "Ramesses II", dynasty=19,
             prenomina=[NameForm("User Maat Ra, setep en Ra", "wsr-mꜢꜤt-rꜤ stp.n-rꜤ")])
    (cand,) = generate_candidates([a, b])
    prompt = _build_user_prompt(cand, a, b)
    assert "throne_names/prenomina: weser maat ra\n" in prompt
    assert "epithets added to the throne name: setep en ra\n" in prompt
    assert "throne_names/prenomina: User Maat Ra, setep en Ra\n" in prompt


def test_vercel_mode_requires_api_key():
    recs = [_rec("leprohon", "leprohon-12", "X", prenomina=["Khnemibre"])]
    with pytest.raises(RuntimeError, match="'llm'/vercel mode without an api_key"):
        verdicts_mod.resolve_matches(recs, mode="llm", provider="vercel", api_key=None)


# --- added-epithet convention: drift guard over the committed Leprohon rows -----------

# Leprohon notes that MENTION an epithet but are attached to a real name, not to an
# added-epithet entry (reviewed 2026-10-11; each is the entry's own name, with a note on
# how an epithet is written beside it, or on a different element).
_EPITHET_MENTION_NOT_AN_EPITHET_ENTRY = {
    ("leprohon-6.01", "birth_names", 1): "sꜣ rꜥ sometimes written inside Teti's cartouche",
    ("leprohon-6.03", "birth_names", 1): "sꜣ rꜥ sometimes written inside the cartouche",
    ("leprohon-6.05", "birth_names", 1): "sA ra sometimes precedes the name",
    ("leprohon-8.12", "later_cartouche_names", 1): "Turin adds Sri to the name",
    ("leprohon-11a.01", "birth_names", 1): "priestly title; epithets inside the cartouche",
    ("leprohon-11a.02", "birth_names", 1): "sꜣ rꜥ added within the cartouche at Tod",
    ("leprohon-11b.05a", "birth_names", 1): "the epithet is written within the cartouche",
    ("leprohon-11b.05c", "golden_horus_names", 1): "epithet on the Horus name elsewhere",
    ("leprohon-16.04", "birth_names", 1): "Leprohon prints it as the name; doubt noted",
    ("leprohon-20.06", "horus_names", 2): "an additional Horus NAME; epithet after serekh",
    ("leprohon-21.04", "golden_horus_names", 1): "reading of smA tAw; epithets in general",
    ("leprohon-21a.03", "throne_names", 1): "High Priest preamble title with epithets",
    ("leprohon-22.13", "birth_names", 1): "n(y)-sw-bity sometimes before the name",
    ("leprohon-22.13", "throne_names", 1): "n(y)-sw-bity sometimes before the name",
    ("leprohon-23.03", "birth_names", 1): "pr-aA sometimes written before the name",
    ("leprohon-23.04", "birth_names", 1): "pr-aA sometimes written before the name",
    ("leprohon-33.04", "golden_horus_names", 1): "'twice-great Thoth' is the god's epithet",
}


def test_every_leprohon_epithet_note_is_classified_or_reviewed():
    """Fails when a committed Leprohon note mentions an epithet without following the
    added-epithet convention and without a reviewed entry above — a new transcription
    pattern must be decided, not silently loaded as a name."""
    import re

    from pipeline.authority.claimgraph.sources import _ADDED_EPITHET_NOTE_PREFIXES

    path = AUTHORITY_ROOT / "leprohon-2013-titulary" / "reconciled.jsonl"
    unreviewed, stale = [], set(_EPITHET_MENTION_NOT_AN_EPITHET_ENTRY)
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        for slot, entries in row.items():
            if not (slot.endswith("_names") and isinstance(entries, list)):
                continue
            for entry in entries:
                note = entry.get("source_note") if isinstance(entry, dict) else None
                if not note or not re.search("epithet", note, re.IGNORECASE):
                    continue
                if note.startswith(_ADDED_EPITHET_NOTE_PREFIXES):
                    continue
                key = (row["leprohon_id"], slot, entry.get("variant_index"))
                if key in _EPITHET_MENTION_NOT_AN_EPITHET_ENTRY:
                    stale.discard(key)
                else:
                    unreviewed.append(key)
    assert unreviewed == []
    assert stale == set()


def test_committed_added_epithet_count():
    records = load_all_sources(AUTHORITY_ROOT).records
    counts = {
        slot: sum(f.is_added_epithet for r in records for f in getattr(r, slot))
        for slot in ("prenomina", "horus_names", "nomina")
    }
    assert counts == {"prenomina": 126, "horus_names": 1, "nomina": 130}


def test_stage_group_is_the_printed_under_entry_for_stages_and_consorts():
    by_id = {r.local_id: r for r in load_all_sources(AUTHORITY_ROOT).records}
    assert by_id["leprohon-leprohon-18.10a"].stage_group == "leprohon-18.10"
    assert by_id["leprohon-leprohon-18.10b"].stage_group == "leprohon-18.10"
    assert by_id["leprohon-leprohon-33.02a"].stage_group == "leprohon-33.02"
    assert by_id["leprohon-leprohon-18.09"].stage_group is None
