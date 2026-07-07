"""Tests for the claim-graph cross-source ruler matcher (ADR-018/020).

These encode the deterministic invariants that the module previously asserted only in
docstrings (Constitutional Rule 3 — a rule that lives only in prose is a suggestion):

  * normalize.py — the cross-convention collapse, including the German transcription
    (Beckerath) and the consonantal-skeleton path that makes the flagship Amasis example
    (``Chnem-ib-rê`` / ``khnum ib ra`` / ``ẖnm ib rꜥ``) actually resolve to one key.
  * matcher.py — homonym coverage (the reused prenomina that must escalate rather than
    merge), the Dynasty-0 early-Horus carve-out, the name-only→escalate basis, the
    cross-source-only rule, and uniqueness-clash order-independence.
  * reviewer.py — the verdict-JSON parser's salvage paths, and the Rule-14 guarantee that
    the reviewer prompt does NOT leak the deterministic stage-1 answer.
  * verdicts.py — unparseable output escalates the one candidate WITH its raw response
    persisted (Rule 13); an API error fails the whole run loud (Rule 2).
"""

from __future__ import annotations

import pytest

from pipeline.authority.claimgraph.matcher import (
    Candidate,
    _HOMONYM_KEYS,
    _is_homonym_key,
    generate_candidates,
    uniqueness_clashes,
)
from pipeline.authority.claimgraph.normalize import (
    NameForm,
    keys_for_form,
    key_set,
    phon_key,
    skeleton_key,
    translit_key,
)
from pipeline.authority.claimgraph.reviewer import (
    SYSTEM_PROMPT,
    VERDICT_APPROVED,
    VERDICT_ESCALATED,
    VERDICT_REJECTED,
    ReviewerParseError,
    _build_user_prompt,
    _parse_verdict_json,
)
from pipeline.authority.claimgraph.matcher import _HOMONYM_SPELLINGS
from pipeline.authority.claimgraph.sources import SOURCE_AUTHORITY, RulerRecord
from pipeline.authority.claimgraph import verdicts as verdicts_mod


# --- normalize.py ----------------------------------------------------------


def test_amasis_flagship_example_collapses():
    """The module docstring's headline claim, now enforced: the German, anglicised, and
    transliterated spellings of Khnemibre (Amasis) MUST share a normalized key."""
    german = keys_for_form(NameForm(surface="Chnem-ib-rê"), skeleton=True)
    anglic = keys_for_form(NameForm(surface="khnum ib ra"), skeleton=True)
    translit = keys_for_form(NameForm(surface="", translit="ẖnm ib rꜥ"), skeleton=True)
    assert german & anglic, "German vs anglicised must intersect"
    assert german & translit, "German vs transliteration must intersect"
    assert anglic & translit, "anglicised vs transliteration must intersect"
    # all three via the shared consonantal skeleton
    assert "khnmbr" in german & anglic & translit


def test_german_digraphs_fold_to_ascii_skeleton():
    assert translit_key("Chnem-ib-rê") == "khnemibre"  # ch -> kh
    assert translit_key("Schepseskare").startswith("shepses")  # sch -> sh
    assert translit_key("Dschedkare").startswith("djed")  # dsch -> dj (before sch/ch)


def test_phon_key_canonicalizes_re_and_neb_elements():
    # re/rê/ra collapse to 'ra'; the vowel-carrier neb collapses to 'nb'.
    assert phon_key("Neb-maat-re") == "nbmaatra"
    assert phon_key("Neb-maat-rê") == "nbmaatra"
    assert phon_key("neb maat ra") == "nbmaatra"


def test_skeleton_key_drops_vowels_and_guards_short_residue():
    assert skeleton_key("khnum ib ra") == "khnmbr"
    assert skeleton_key("ra") == ""  # too short to block on
    assert skeleton_key("re") == ""


def test_name_blocker_does_not_use_skeleton():
    """key_set without skeleton must not fold vowel-differing names together (guards the
    name_only explosion) — 'Amenhotep' and 'Amenhatep' differ, but a skeleton would not."""
    a = key_set([NameForm(surface="Amenhotep")])
    b = key_set([NameForm(surface="Amenhetep")])
    assert not (a & b)
    # with skeleton on, they would collapse — proving the flag is what gates it
    a_sk = key_set([NameForm(surface="Amenhotep")], skeleton=True)
    b_sk = key_set([NameForm(surface="Amenhetep")], skeleton=True)
    assert a_sk & b_sk


# --- matcher.py: homonym list ----------------------------------------------


@pytest.mark.parametrize(
    "spelling",
    [
        "Menkheperre",
        "Nebmaatre",
        "Usermaatre",
        "Neferkare",  # the most-reused throne name — regression guard
        "Kheperkare",
        "Sehetepibre",
        "Wahkare",
        "Sekhemkare",
        "Men-cheper-Rê",  # German spelling must ALSO be caught (digraph fold)
    ],
)
def test_reused_prenomina_are_homonym_trapped(spelling):
    keys = keys_for_form(NameForm(surface=spelling), skeleton=True)
    assert any(_is_homonym_key(k) for k in keys), f"{spelling!r} must be a homonym trap"


def test_sekhemre_prefix_trap():
    keys = keys_for_form(NameForm(surface="Sekhemre-Wadjkhau"), skeleton=True)
    assert any(_is_homonym_key(k) for k in keys)


def test_homonym_keys_nonempty():
    assert _HOMONYM_KEYS  # the committed list actually produced keys


# --- matcher.py: candidate generation --------------------------------------


def _rec(
    source_id,
    local_id,
    display_name,
    *,
    dynasty=None,
    prenomina=None,
    horus_names=None,
    nomina=None,
    alt_names=None,
    reign_start_bce=None,
):
    return RulerRecord(
        source_id=source_id,
        local_id=local_id,
        display_name=display_name,
        alt_names=alt_names or [],
        dynasty=dynasty,
        dynasty_label=None,
        prenomina=[NameForm(surface=p) for p in (prenomina or [])],
        horus_names=[NameForm(surface=h) for h in (horus_names or [])],
        nomina=[NameForm(surface=n) for n in (nomina or [])],
        reign_start_bce=reign_start_bce,
        reign_end_bce=None,
        intra_source_same_as=[],
        authority=SOURCE_AUTHORITY[source_id],
    )


def test_shared_prenomen_makes_prenomen_basis():
    recs = [
        _rec("leprohon", "leprohon-1", "Amasis", prenomina=["Khnemibre"]),
        _rec("beckerath", "beckerath-1", "Amasis", prenomina=["Chnem-ib-rê"]),
    ]
    cands = generate_candidates(recs)
    assert len(cands) == 1
    assert cands[0].basis == "prenomen"
    assert cands[0].homonym_trap is None  # Khnemibre is unique, not a homonym


def test_reused_prenomen_flags_homonym_trap():
    recs = [
        _rec("leprohon", "leprohon-2", "Pepi II", prenomina=["Neferkare"]),
        _rec("kitchen", "kitchen-2", "Neferkare Peftjauawybast", prenomina=["Neferkare"]),
    ]
    cands = generate_candidates(recs)
    assert len(cands) == 1
    assert cands[0].basis == "prenomen"
    assert cands[0].homonym_trap is not None  # must escalate, not merge


def test_dynasty_zero_qualifies_for_early_horus_basis():
    """Regression: `dynasty or 99` used to map Dynasty 0 to 'missing', excluding Narmer &
    co. from the exact Horus-name basis that exists for the earliest dynasties."""
    recs = [
        _rec("leprohon", "leprohon-3", "Narmer", dynasty=0, horus_names=["Narmer"]),
        _rec("pharaoh_se", "pharaoh_se-3", "Narmer", dynasty=0, horus_names=["Narmer"]),
    ]
    cands = generate_candidates(recs)
    assert len(cands) == 1
    assert cands[0].basis == "horus_early"


def test_name_only_basis_when_only_names_match():
    recs = [
        _rec("leprohon", "leprohon-4", "Sneferu", nomina=["Sneferu"]),
        _rec("beckerath", "beckerath-4", "Sneferu", nomina=["Sneferu"]),
    ]
    cands = generate_candidates(recs)
    assert len(cands) == 1
    assert cands[0].basis == "name_only"


def test_same_source_pairs_are_never_candidates():
    recs = [
        _rec("leprohon", "leprohon-5a", "Thutmose III", prenomina=["Menkheperre"]),
        _rec("leprohon", "leprohon-5b", "Necho I", prenomina=["Menkheperre"]),
    ]
    assert generate_candidates(recs) == []


# --- matcher.py: uniqueness clashes ----------------------------------------


def _cand(cid, a_id, b_id, a_source, b_source, keys=("khnmbr",)):
    return Candidate(
        id=cid,
        a_id=a_id,
        b_id=b_id,
        a_source=a_source,
        b_source=b_source,
        a_name=a_id,
        b_name=b_id,
        basis="prenomen",
        shared_prenomen_keys=list(keys),
        shared_name_keys=[],
        dynasty_match=None,
        reign_far_apart=False,
        homonym_trap=None,
    )


def test_uniqueness_clash_is_symmetric_and_order_independent():
    # leprohon-X is the corroborated match of TWO distinct beckerath records => clash.
    cands = [
        _cand("c1", "leprohon-X", "beckerath-1", "leprohon", "beckerath"),
        _cand("c2", "leprohon-X", "beckerath-2", "leprohon", "beckerath"),
        _cand("c3", "leprohon-Y", "beckerath-3", "leprohon", "beckerath"),  # clean
    ]
    forced = uniqueness_clashes(cands)
    assert forced == {"c1", "c2"}
    # order independence: reversing the input must not change the outcome
    assert uniqueness_clashes(list(reversed(cands))) == {"c1", "c2"}


# --- reviewer.py: verdict parsing ------------------------------------------


def test_parse_clean_json():
    assert _parse_verdict_json('{"outcome":"approved","reason":"ok"}') == (
        VERDICT_APPROVED,
        "ok",
    )


def test_parse_fenced_json():
    text = '```json\n{"outcome":"rejected","reason":"distinct kings"}\n```'
    assert _parse_verdict_json(text) == (VERDICT_REJECTED, "distinct kings")


def test_parse_salvages_truncated_reason():
    text = '{"outcome":"escalated","reason":"the reason ran long and got cut off mid-sen'
    outcome, reason = _parse_verdict_json(text)
    assert outcome == VERDICT_ESCALATED
    assert reason.startswith("the reason ran long")


def test_parse_unparseable_raises():
    with pytest.raises(ValueError):
        _parse_verdict_json("I think these two are probably the same person.")


# --- reviewer.py: Rule-14 no answer leakage --------------------------------


def test_system_prompt_does_not_name_committed_homonyms():
    """Rule 14: the standing policy prompt must not name the specific reused throne names
    on the committed homonym answer-key (matcher._HOMONYM_SPELLINGS) — doing so hands the
    model the escalate verdict for exactly the cases the eval tests."""
    sp = SYSTEM_PROMPT.lower()
    named = [s for s in _HOMONYM_SPELLINGS if " " not in s and "-" not in s and s[:1].isupper()]
    assert named, "expected joined anglicised homonym spellings to exist"
    for name in named:
        assert name.lower() not in sp, f"SYSTEM_PROMPT leaks committed homonym: {name!r}"
    assert "sekhemre" not in sp, "SYSTEM_PROMPT leaks the Sekhemre prefix trap"


def test_reviewer_prompt_does_not_leak_stage1_answer():
    a = _rec("leprohon", "leprohon-6", "Thutmose III", prenomina=["Menkheperre"])
    b = _rec("kitchen", "kitchen-6", "Necho I", prenomina=["Menkheperre"])
    cand = _cand("c", "leprohon-6", "kitchen-6", "leprohon", "kitchen", keys=("menkheperra",))
    cand.homonym_trap = "menkheperra"
    cand.basis = "prenomen"
    prompt = _build_user_prompt(cand, a, b).lower()
    # none of the stage-1 conclusion may appear: not the basis label, not the homonym
    # flag, not the shared-key set.
    for leak in ("basis", "homonym", "trap", "stage-1", "stage 1", "menkheperra"):
        assert leak not in prompt, f"prompt leaks stage-1 signal: {leak!r}"


# --- verdicts.py: fail-loud vs escalate-with-provenance --------------------


def test_unparseable_after_retries_escalates_with_raw_response():
    """A persistently-unparseable reviewer escalates THAT candidate (never silently, never
    aborting the run) AND persists the raw response that drove it (Rule 13)."""

    def boom(c, a, b):
        raise ReviewerParseError(
            "bad json",
            prompt="the exact prompt",
            raw_response={"content": [{"type": "text", "text": "garbled"}]},
            model_id="m",
            model_snapshot="claude-sonnet-5-snap",
        )

    cand = _cand("c", "a", "b", "leprohon", "kitchen")
    v = verdicts_mod._review_with_retry(boom, cand, None, None, retries=1)
    assert v.outcome == VERDICT_ESCALATED
    assert v.prompt == "the exact prompt"
    assert v.raw_response == {"content": [{"type": "text", "text": "garbled"}]}
    assert v.model_snapshot == "claude-sonnet-5-snap"


def test_homonym_trap_forces_escalation_even_if_llm_approves(monkeypatch):
    """The committed homonym list is a deterministic hard guard: even if the live reviewer
    returns 'approved', a homonym-trapped prenomen pair must be escalated, never emitted as
    an identity link (codex P1 — the LLM judges blind, the guard is enforced in finalize)."""
    from pipeline.authority.claimgraph.reviewer import Verdict

    def always_approve(client, c, a, b, model):
        return Verdict(candidate_id=c.id, outcome=VERDICT_APPROVED, reason="looks same", reviewer="llm")

    monkeypatch.setattr(verdicts_mod, "review_with_llm", always_approve)
    recs = [
        _rec("leprohon", "leprohon-9", "Pepi II", prenomina=["Neferkare"]),
        _rec("kitchen", "kitchen-9", "Neferkare Peftjauawybast", prenomina=["Neferkare"]),
    ]
    res = verdicts_mod.resolve_matches(recs, mode="llm", client=object(), model="m", cache_path=None)
    assert res.approved_edges == []
    assert len(res.escalations) == 1
    assert "homonym" in res.escalations[0].reason.lower()


def test_clean_prenomen_approval_survives_finalize(monkeypatch):
    """A non-homonym prenomen pair the reviewer approves must remain an approved edge —
    the hard guards only ever downgrade, never gratuitously escalate clean matches."""
    from pipeline.authority.claimgraph.reviewer import Verdict

    def always_approve(client, c, a, b, model):
        return Verdict(candidate_id=c.id, outcome=VERDICT_APPROVED, reason="same king", reviewer="llm")

    monkeypatch.setattr(verdicts_mod, "review_with_llm", always_approve)
    recs = [
        _rec("leprohon", "leprohon-10", "Amasis", prenomina=["Khnemibre"]),
        _rec("beckerath", "beckerath-10", "Amasis", prenomina=["Chnem-ib-rê"]),
    ]
    res = verdicts_mod.resolve_matches(recs, mode="llm", client=object(), model="m", cache_path=None)
    assert len(res.approved_edges) == 1
    assert res.escalations == []


def test_api_error_fails_loud():
    def boom(c, a, b):
        raise RuntimeError("credit balance too low")

    cand = _cand("c", "a", "b", "leprohon", "kitchen")
    with pytest.raises(RuntimeError, match="Live reviewer failed"):
        verdicts_mod._review_with_retry(boom, cand, None, None, retries=1)


def test_name_only_is_escalated_without_calling_the_reviewer(monkeypatch):
    """Name-only pairs never reach the paid reviewer — they escalate deterministically, and
    the reason states external documented evidence (not a model assertion) is required to
    confirm the identity (Rule 1)."""

    def must_not_be_called(client, c, a, b, model):
        raise AssertionError("reviewer was called for a name-only candidate")

    monkeypatch.setattr(verdicts_mod, "review_with_llm", must_not_be_called)
    recs = [
        _rec("beckerath", "beckerath-11", "Usaphais", nomina=["Usaphais"]),
        _rec("pharaoh_se", "pharaoh_se-11", "Den", nomina=["Den"], alt_names=["Usaphais"]),
    ]
    res = verdicts_mod.resolve_matches(recs, mode="llm", client=object(), model="m", cache_path=None)
    assert res.approved_edges == []
    assert len(res.escalations) == 1
    assert res.escalations[0].reviewer == "deterministic"
    assert "external documented evidence" in res.escalations[0].reason.lower()


def test_openrouter_mode_requires_api_key():
    recs = [_rec("leprohon", "leprohon-12", "X", prenomina=["Khnemibre"])]
    with pytest.raises(RuntimeError, match="without an api_key"):
        verdicts_mod.resolve_matches(recs, mode="llm", provider="openrouter", api_key=None)
