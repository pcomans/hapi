"""Tests for the claim-graph cross-source ruler matcher (ADR-018/020).

These encode the deterministic invariants that the module previously asserted only in
docstrings (Constitutional Rule 3 — a rule that lives only in prose is a suggestion):

  * normalize.py — the cross-convention collapse, including the German transcription
    (Beckerath) and the consonantal-skeleton path that makes the flagship Amasis example
    (``Chnem-ib-rê`` / ``khnum ib ra`` / ``ẖnm ib rꜥ``) actually resolve to one key.
  * matcher.py — homonym coverage (the reused prenomina that must escalate rather than
    merge), the Dynasty-0 early-Horus carve-out, the name-only→escalate basis, the
    cross-source-only rule, and uniqueness-clash order-independence.
  * reviewer.py — the verdict-JSON parser's STRICT contract (a truncated or fenced or
    prose-wrapped response never becomes a verdict), the completeness of the persisted
    interaction record (Rule 13), and the Rule-14 guarantee that the reviewer prompt does
    NOT leak the deterministic stage-1 answer.
  * verdicts.py — unparseable output escalates the one candidate with EVERY attempt's full
    interaction persisted (Rule 13); an API error fails the whole run loud (Rule 2); a
    cached verdict is reusable only while the request that produced it is unchanged, and
    conflicting cache lines raise instead of resolving by file order (Rule 2/6).
"""

from __future__ import annotations

import json
from dataclasses import asdict, replace

import pytest

from pipeline.authority.claimgraph.matcher import (
    Candidate,
    _HOMONYM_KEYS,
    _is_homonym_key,
    generate_candidates,
    king_name_route_corroborated,
    lacks_titulary,
    regnal_number_of,
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
    ANTHROPIC_PARAMETERS,
    PROVIDER_ANTHROPIC,
    SYSTEM_PROMPT,
    VERDICT_APPROVED,
    VERDICT_ESCALATED,
    VERDICT_REJECTED,
    ReviewerHttpError,
    ReviewerInteraction,
    ReviewerParseError,
    Verdict,
    _build_user_prompt,
    _parse_verdict_json,
    request_digest,
    review_with_llm,
    review_with_openrouter,
)
from pipeline.authority.claimgraph.matcher import _HOMONYM_SPELLINGS
from pipeline.authority.claimgraph.sources import SOURCE_AUTHORITY, RulerRecord
from pipeline.authority.claimgraph import verdicts as verdicts_mod



# --- normalize.py ----------------------------------------------------------


def test_amasis_flagship_example_collapses():
    """The module docstring's headline claim, now enforced: the German, anglicised, and
    transliterated spellings of Khnemibre (Amasis) MUST share a normalized key. The exact
    key sets are asserted, not merely a non-empty intersection (Rule 5) — a widened
    normalizer that folded everything together would still pass a truthiness check."""
    german = keys_for_form(NameForm(surface="Chnem-ib-rê"), skeleton=True)
    anglic = keys_for_form(NameForm(surface="khnum ib ra"), skeleton=True)
    translit = keys_for_form(NameForm(surface="", translit="ẖnm ib rꜥ"), skeleton=True)
    assert german == {"khnemibra", "khnemibre", "khnmbr"}
    assert anglic == {"khnmbr", "khnumibra"}
    assert translit == {"hnmibr", "khnmbr", "khnmibra"}
    # they meet on exactly one key — the shared consonantal skeleton, nothing else
    assert german & anglic == {"khnmbr"}
    assert german & translit == {"khnmbr"}
    assert anglic & translit == {"khnmbr"}


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
    assert a == {"amenhotep"}
    assert b == {"amenhetep"}
    assert a & b == set()
    # with skeleton on, they collapse on exactly the vowel-less skeleton — proving the flag
    # is what gates it, and that nothing else is folding them together.
    a_sk = key_set([NameForm(surface="Amenhotep")], skeleton=True)
    b_sk = key_set([NameForm(surface="Amenhetep")], skeleton=True)
    assert a_sk == {"amenhotep", "mnhtp"}
    assert b_sk == {"amenhetep", "mnhtp"}
    assert a_sk & b_sk == {"mnhtp"}


# --- matcher.py: homonym list ----------------------------------------------


@pytest.mark.parametrize(
    ("spelling", "expected_keys"),
    [
        ("Menkheperre", {"menkheperre", "mnkhprr"}),
        ("Nebmaatre", {"nbmtr", "nebmaatre"}),
        ("Usermaatre", {"srmtr", "usermaatre"}),
        ("Neferkare", {"neferkare", "nfrkr"}),  # most-reused throne name — regression guard
        ("Kheperkare", {"kheperkare", "khprkr"}),
        ("Sehetepibre", {"sehetepibre", "shtpbr"}),
        ("Wahkare", {"wahkare", "whkr"}),
        ("Sekhemkare", {"sekhemkare", "skhmkr"}),
        # German spelling must ALSO be caught (digraph fold) — and it yields an extra
        # element-canonicalised key on top of the two the anglicised spelling produces.
        ("Men-cheper-Rê", {"menkheperra", "menkheperre", "mnkhprr"}),
    ],
)
def test_reused_prenomina_are_homonym_trapped(spelling, expected_keys):
    """Every key the spelling normalizes to is trapped — asserted as an exact set, so a
    normalizer change that dropped one of the two paths (leaving a spelling reachable by an
    untrapped key) fails here instead of passing an `any(...)` check."""
    keys = keys_for_form(NameForm(surface=spelling), skeleton=True)
    assert keys == expected_keys
    assert {k for k in keys if _is_homonym_key(k)} == expected_keys


def test_sekhemre_prefix_trap():
    """The Sekhemre-* prefix trap catches the SKELETON key of a compound; the vowelled
    full-name key is deliberately not on the committed list (it is the prefix that traps)."""
    keys = keys_for_form(NameForm(surface="Sekhemre-Wadjkhau"), skeleton=True)
    assert keys == {"sekhemrewadjkhau", "skhmrwdjkh"}
    assert {k for k in keys if _is_homonym_key(k)} == {"skhmrwdjkh"}


def test_homonym_key_set_is_exactly_the_committed_list():
    """The committed homonym answer-key, pinned key-for-key: a normalizer change that
    silently stopped producing one of these keys would reopen a known false-merge path."""
    assert _HOMONYM_KEYS == {
        "hprkr", "kheperkara", "kheperkare", "khprkara", "khprkr",
        "menkheperra", "menkheperre", "mnhprr", "mnkhprr", "mnkhprra",
        "nbmaatra", "nbmtr", "nebmaatra", "nebmaatre",
        "neferkara", "neferkare", "nfrkara", "nfrkr",
        "sehetepibra", "sehetepibre", "shtpbr", "shtpibra",
        "sekhemkara", "sekhemkare", "shmkr", "skhmkara", "skhmkr",
        "srmtr", "usermaatra", "usermaatre", "wsrmaatra", "wsrmtr",
        "wahkara", "wahkare", "whkr",
    }


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
    display_name_absence=None,
):
    return RulerRecord(
        source_id=source_id,
        local_id=local_id,
        display_name=display_name,
        display_name_absence=display_name_absence,
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


def test_dynasty_zero_qualifies_as_early_dynastic_horus():
    """Regression: `dynasty or 99` used to map Dynasty 0 to 'missing', excluding Narmer &
    co. from the earliest dynasties, where the deterministic policy accepts a Horus name."""
    recs = [
        _rec("leprohon", "leprohon-3", "Narmer", dynasty=0, horus_names=["Narmer"]),
        _rec("pharaoh_se", "pharaoh_se-3", "Narmer", dynasty=0, horus_names=["Narmer"]),
    ]
    cands = generate_candidates(recs)
    assert len(cands) == 1
    assert cands[0].basis == "horus"
    assert cands[0].early_dynastic is True


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
    assert _parse_verdict_json('  {"outcome":"rejected","reason":" distinct kings "}\n') == (
        VERDICT_REJECTED,
        "distinct kings",
    )
    assert _parse_verdict_json('{"reason":"unsure","outcome":"escalated"}') == (
        VERDICT_ESCALATED,
        "unsure",
    )


@pytest.mark.parametrize(
    ("label", "text"),
    [
        # THE codex P1: a truncated object must never mint an approval. A regex salvage
        # would read "approved" out of this and emit an identity edge on a response the
        # model never finished.
        ("truncated_approved", '{"outcome":"approved"'),
        ("truncated_reason", '{"outcome":"escalated","reason":"ran long and got cut off'),
        # A fence is not the response the system prompt mandates ("ONLY a single JSON
        # object and nothing else") — stripping it silently accepts an off-contract reply.
        ("fenced", '```json\n{"outcome":"rejected","reason":"distinct kings"}\n```'),
        ("prose_around_object", 'Sure! {"outcome":"approved","reason":"same king"} — hope that helps'),
        ("two_objects", '{"outcome":"approved","reason":"a"}{"outcome":"rejected","reason":"b"}'),
        ("prose_only", "I think these two are probably the same person."),
        ("empty", "   "),
        ("json_but_not_object", '["approved"]'),
        ("unknown_outcome", '{"outcome":"maybe","reason":"unsure"}'),
        ("wrong_case_outcome", '{"outcome":"Approved","reason":"same king"}'),
        ("outcome_not_a_string", '{"outcome":true,"reason":"same king"}'),
        ("missing_reason", '{"outcome":"approved"}'),
        ("empty_reason", '{"outcome":"approved","reason":"   "}'),
        ("reason_not_a_string", '{"outcome":"approved","reason":42}'),
        ("extra_key", '{"outcome":"approved","reason":"same king","confidence":0.9}'),
    ],
)
def test_parse_rejects_anything_but_one_clean_object(label, text):
    with pytest.raises(ValueError):
        _parse_verdict_json(text)


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


def _interaction(**over) -> ReviewerInteraction:
    """A complete interaction record, as the live reviewer builds one."""
    base = dict(
        attempt=1,
        provider=PROVIDER_ANTHROPIC,
        requested_model="claude-sonnet-5",
        model_snapshot="claude-sonnet-5-20260101",
        parameters=dict(ANTHROPIC_PARAMETERS),
        system_prompt=SYSTEM_PROMPT,
        user_prompt="the exact user prompt",
        raw_response={"content": [{"type": "text", "text": "garbled"}]},
    )
    base.update(over)
    return ReviewerInteraction(**base)


def _pair(n: int):
    """A real candidate + both real records — the retry wrapper builds the prompt of a
    failed attempt from them, so they must be genuine records, not None."""
    a = _rec("leprohon", f"leprohon-{n}", "Amasis", prenomina=["Khnemibre"])
    b = _rec("beckerath", f"beckerath-{n}", "Amasis", prenomina=["Chnem-ib-rê"])
    return generate_candidates([a, b])[0], a, b


def test_unparseable_after_retries_escalates_with_every_attempt_persisted():
    """A persistently-unparseable reviewer escalates THAT candidate (never silently, never
    aborting the run) AND persists EVERY attempt's complete interaction (Rule 13) — each
    one a real call that consumed a retry and shaped the escalation."""
    attempts = []

    def boom(c, a, b):
        n = len(attempts) + 1
        attempts.append(n)
        raise ReviewerParseError(
            f"bad json #{n}",
            interaction=_interaction(
                model_snapshot=f"claude-sonnet-5-snap-{n}",
                raw_response={"content": [{"type": "text", "text": f"garbled #{n}"}]},
                parse_error=f"bad json #{n}",
            ),
            request_digest="digest-abc",
        )

    cand, a, b = _pair(40)
    v = verdicts_mod._review_with_retry(
        boom, cand, a, b, retries=2, model="claude-sonnet-5", provider=PROVIDER_ANTHROPIC
    )
    assert attempts == [1, 2, 3]
    assert v.outcome == VERDICT_ESCALATED
    assert v.reviewer == "llm"
    assert v.request_digest == "digest-abc"
    assert [i.attempt for i in v.interactions] == [1, 2, 3]
    assert [i.model_snapshot for i in v.interactions] == [
        "claude-sonnet-5-snap-1",
        "claude-sonnet-5-snap-2",
        "claude-sonnet-5-snap-3",
    ]
    assert [i.raw_response["content"][0]["text"] for i in v.interactions] == [
        "garbled #1",
        "garbled #2",
        "garbled #3",
    ]
    assert [i.parse_error for i in v.interactions] == ["bad json #1", "bad json #2", "bad json #3"]
    for i in v.interactions:
        assert i.provider == PROVIDER_ANTHROPIC
        assert i.requested_model == "claude-sonnet-5"
        assert i.parameters == dict(ANTHROPIC_PARAMETERS)
        assert i.system_prompt == SYSTEM_PROMPT
        assert i.user_prompt == "the exact user prompt"


def test_retry_persists_the_superseded_attempts_alongside_the_successful_one():
    """Attempts 1-2 malformed, attempt 3 parses: all THREE interactions are persisted, in
    order, on the verdict that shipped — the two discarded responses are exactly the
    provenance a reader needs to see why the answer took three calls (Rule 13). Each
    attempt carries distinct metadata so an off-by-one or a last-write-wins bug shows up."""
    calls = []

    def flaky(c, a, b):
        n = len(calls) + 1
        calls.append(n)
        if n < 3:
            raise ReviewerParseError(
                f"bad json #{n}",
                interaction=_interaction(
                    model_snapshot=f"snap-{n}",
                    raw_response={"id": f"msg_{n}", "content": [{"type": "text", "text": f"junk {n}"}]},
                    parse_error=f"bad json #{n}",
                ),
                request_digest="digest-xyz",
            )
        return Verdict(
            candidate_id=c.id,
            outcome=VERDICT_APPROVED,
            reason="same king",
            reviewer="llm",
            request_digest="digest-xyz",
            interactions=[
                _interaction(
                    model_snapshot=f"snap-{n}",
                    raw_response={"id": f"msg_{n}", "content": [{"type": "text", "text": '{"outcome":"approved","reason":"same king"}'}]},
                )
            ],
        )

    cand, a, b = _pair(41)
    v = verdicts_mod._review_with_retry(
        flaky, cand, a, b, retries=2, model="claude-sonnet-5", provider=PROVIDER_ANTHROPIC
    )
    assert calls == [1, 2, 3]
    assert v.outcome == VERDICT_APPROVED
    assert v.reason == "same king"
    assert v.request_digest == "digest-xyz"
    assert [i.attempt for i in v.interactions] == [1, 2, 3]
    assert [i.model_snapshot for i in v.interactions] == ["snap-1", "snap-2", "snap-3"]
    assert [i.raw_response["id"] for i in v.interactions] == ["msg_1", "msg_2", "msg_3"]
    assert [i.parse_error for i in v.interactions] == ["bad json #1", "bad json #2", None]
    # the request is fully reconstructible from every stored attempt, not just the last
    for i in v.interactions:
        assert i.system_prompt == SYSTEM_PROMPT
        assert i.user_prompt == "the exact user prompt"
        assert i.parameters == dict(ANTHROPIC_PARAMETERS)
        assert i.provider == PROVIDER_ANTHROPIC
        assert i.requested_model == "claude-sonnet-5"


def test_retry_fills_in_the_requested_model_when_the_interaction_lacks_one():
    """Regression (codex P1): the escalation path used to read a bare `model` that was not
    a parameter of `_review_with_retry` — a NameError on every malformed-response run. The
    requested model is now passed in explicitly and backfills an interaction that reports
    none (a malformed body may carry no model at all)."""

    def boom(c, a, b):
        raise ReviewerParseError(
            "bad json",
            interaction=_interaction(requested_model=None, model_snapshot=None),
            request_digest="digest-1",
        )

    cand, a, b = _pair(42)
    v = verdicts_mod._review_with_retry(
        boom, cand, a, b, retries=1, model="z-ai/glm-5.2", provider=PROVIDER_ANTHROPIC
    )
    assert v.outcome == VERDICT_ESCALATED
    assert [i.requested_model for i in v.interactions] == ["z-ai/glm-5.2", "z-ai/glm-5.2"]
    assert [i.model_snapshot for i in v.interactions] == [None, None]


class _FakeBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _FakeResponse:
    def __init__(self, text, model="claude-sonnet-5-20260101"):
        self.content = [_FakeBlock(text)]
        self.model = model
        self._text = text

    def model_dump(self, mode="json"):
        return {"id": "msg_1", "model": self.model, "content": [{"type": "text", "text": self._text}]}


class _FakeAnthropic:
    """Captures the request kwargs so the test can assert the PERSISTED record describes
    the request that was actually sent."""

    def __init__(self, text):
        self.text = text
        self.seen = None
        self.messages = self

    def create(self, **kwargs):
        self.seen = kwargs
        return _FakeResponse(self.text)


def test_live_reviewer_persists_the_whole_request_and_response():
    """Rule 13: the stored interaction must reconstruct the request — system prompt,
    user prompt, every parameter, provider, requested model, served snapshot, raw body."""
    a = _rec("leprohon", "leprohon-20", "Amasis", prenomina=["Khnemibre"])
    b = _rec("beckerath", "beckerath-20", "Amasis", prenomina=["Chnem-ib-rê"])
    cand = generate_candidates([a, b])[0]
    client = _FakeAnthropic('{"outcome":"approved","reason":"shared throne name"}')

    v = review_with_llm(client, cand, a, b, model="claude-sonnet-5")

    assert v.outcome == VERDICT_APPROVED
    assert v.reason == "shared throne name"
    assert v.reviewer == "llm"
    assert len(v.interactions) == 1
    i = v.interactions[0]
    assert ANTHROPIC_PARAMETERS == {
        "max_tokens": 16000,
        "thinking": {"type": "adaptive", "display": "summarized"},
    }
    assert i.attempt == 1
    assert i.provider == PROVIDER_ANTHROPIC
    assert i.requested_model == "claude-sonnet-5"
    assert i.model_snapshot == "claude-sonnet-5-20260101"
    assert i.parameters == dict(ANTHROPIC_PARAMETERS)
    assert i.system_prompt == SYSTEM_PROMPT
    assert i.user_prompt == _build_user_prompt(cand, a, b)
    assert i.raw_response == {
        "id": "msg_1",
        "model": "claude-sonnet-5-20260101",
        "content": [{"type": "text", "text": '{"outcome":"approved","reason":"shared throne name"}'}],
    }
    assert i.parse_error is None
    # what was persisted IS what was sent
    assert client.seen == {
        "model": "claude-sonnet-5",
        "max_tokens": 16000,
        "thinking": {"type": "adaptive", "display": "summarized"},
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": i.user_prompt}],
    }
    assert v.request_digest == request_digest(
        cand, a, b, provider=PROVIDER_ANTHROPIC, model="claude-sonnet-5",
        parameters=dict(ANTHROPIC_PARAMETERS),
    )


def test_live_reviewer_malformed_output_raises_with_the_interaction_attached():
    """A truncated 'approved' must NOT become a verdict — it raises, carrying the full
    interaction so the escalation it drives is still on the record."""
    a = _rec("leprohon", "leprohon-21", "Amasis", prenomina=["Khnemibre"])
    b = _rec("beckerath", "beckerath-21", "Amasis", prenomina=["Chnem-ib-rê"])
    cand = generate_candidates([a, b])[0]
    client = _FakeAnthropic('{"outcome":"approved"')

    with pytest.raises(ReviewerParseError) as excinfo:
        review_with_llm(client, cand, a, b, model="claude-sonnet-5")

    err = excinfo.value
    assert err.interaction.raw_response["content"][0]["text"] == '{"outcome":"approved"'
    assert err.interaction.parse_error == str(err)
    assert err.interaction.system_prompt == SYSTEM_PROMPT
    assert err.interaction.user_prompt == _build_user_prompt(cand, a, b)
    assert err.request_digest == request_digest(
        cand, a, b, provider=PROVIDER_ANTHROPIC, model="claude-sonnet-5",
        parameters=dict(ANTHROPIC_PARAMETERS),
    )


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
    res = verdicts_mod.resolve_matches(recs, mode="llm", client=object(), model="m", cache_path=None, uncertain_readings=frozenset())
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
    res = verdicts_mod.resolve_matches(recs, mode="llm", client=object(), model="m", cache_path=None, uncertain_readings=frozenset())
    assert len(res.approved_edges) == 1
    assert res.escalations == []


def _always_reject(client, c, a, b, model):
    return Verdict(candidate_id=c.id, outcome=VERDICT_REJECTED, reason="different birth names", reviewer="llm")


def _senakhtenre_pair():
    return [
        _rec("leprohon", "leprohon-17.26", "Senakhtenre Ahmose", dynasty=17,
             prenomina=["Senakhtenre"], nomina=["Ahmose"]),
        _rec("ryholt", "ryholt-17.7", "Siamun (?)", dynasty=17,
             prenomina=["Senakhtenre"], nomina=["Siamun (?)"]),
    ]


def test_rejection_on_an_uncertain_reading_is_escalated(monkeypatch):
    """ADR-020 amendment 2026-10-12 item 5: a reading the source marks uncertain cannot
    ground a 'different king' verdict; the pair is escalated, never dropped."""
    monkeypatch.setattr(verdicts_mod, "review_with_llm", _always_reject)
    res = verdicts_mod.resolve_matches(
        _senakhtenre_pair(), mode="llm", client=object(), model="m", cache_path=None,
        uncertain_readings=frozenset({"ryholt-17.7"}),
    )
    assert res.approved_edges == []
    assert [(e.candidate_id, e.reason) for e in res.escalations] == [(
        "cand-leprohon-17.26|ryholt-17.7",
        "different birth names [overridden to escalate: a record carries a name its source "
        "marks as an uncertain reading]",
    )]
    assert [v.outcome for v in res.verdicts] == [VERDICT_ESCALATED]


def test_rejection_without_an_uncertain_reading_stands(monkeypatch):
    monkeypatch.setattr(verdicts_mod, "review_with_llm", _always_reject)
    res = verdicts_mod.resolve_matches(
        _senakhtenre_pair(), mode="llm", client=object(), model="m", cache_path=None,
        uncertain_readings=frozenset({"ryholt-13.17"}),
    )
    assert res.approved_edges == []
    assert res.escalations == []
    assert [v.outcome for v in res.verdicts] == [VERDICT_REJECTED]


def test_uncertain_readings_are_the_ryholt_rows_the_source_flags():
    from pipeline.authority.claimgraph.build_graph import AUTHORITY_ROOT
    from pipeline.authority.claimgraph.sources import load_all_sources

    assert load_all_sources(AUTHORITY_ROOT).uncertain_readings == frozenset({
        "ryholt-13.17", "ryholt-13.53", "ryholt-14.32", "ryholt-14.g",
        "ryholt-16.5", "ryholt-17.7", "ryholt-Abyd.15",
    })


def test_api_error_fails_loud():
    def boom(c, a, b):
        raise RuntimeError("credit balance too low")

    cand, a, b = _pair(43)
    with pytest.raises(RuntimeError, match="Live reviewer failed"):
        verdicts_mod._review_with_retry(
            boom, cand, a, b, retries=1, model="m", provider=PROVIDER_ANTHROPIC
        )


def test_non_parse_error_attempt_is_still_persisted_when_a_later_attempt_succeeds():
    """Rule 13: an attempt that raised something OTHER than a ReviewerParseError was still
    a real call that consumed a retry, so it must appear in the verdict's interactions —
    otherwise a run that failed once and then succeeded reports a clean single-shot call
    that never happened. The absence of a response body is recorded explicitly, not by
    omitting the attempt."""
    calls = []

    def flaky(c, x, y):
        n = len(calls) + 1
        calls.append(n)
        if n == 1:
            # e.g. the OpenRouter body-shape path: a response arrived, then extracting
            # `body["choices"][0]` blew up.
            raise KeyError("choices")
        return Verdict(
            candidate_id=c.id,
            outcome=VERDICT_APPROVED,
            reason="same king",
            reviewer="llm",
            request_digest="digest-xyz",
            interactions=[_interaction(model_snapshot="snap-2", raw_response={"id": "msg_2"})],
        )

    cand, a, b = _pair(44)
    v = verdicts_mod._review_with_retry(
        flaky, cand, a, b, retries=2, model="claude-sonnet-5", provider=PROVIDER_ANTHROPIC
    )
    assert calls == [1, 2]
    assert v.outcome == VERDICT_APPROVED
    assert [i.attempt for i in v.interactions] == [1, 2]
    failed, ok = v.interactions
    assert failed.call_error == "KeyError: 'choices'"
    assert failed.raw_response is None  # explicit marker: no body was obtained
    assert failed.parse_error is None
    assert failed.provider == PROVIDER_ANTHROPIC
    assert failed.requested_model == "claude-sonnet-5"
    assert failed.model_snapshot is None
    assert failed.parameters == dict(ANTHROPIC_PARAMETERS)
    assert failed.system_prompt == SYSTEM_PROMPT
    assert failed.user_prompt == _build_user_prompt(cand, a, b)
    assert ok.call_error is None
    assert ok.raw_response == {"id": "msg_2"}
    assert ok.model_snapshot == "snap-2"


class _FakeHttpResponse:
    def __init__(self, payload, *, text=None, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = text if text is not None else json.dumps(payload)

    def raise_for_status(self):
        # Mirrors httpx: an error status raises AFTER the body has been transferred, which
        # is exactly why the reviewer must capture the body before checking the status.
        if self.status_code >= 400:
            raise RuntimeError(f"Server error '{self.status_code}'")

    def json(self):
        if self._payload is _NOT_JSON:
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return self._payload


_NOT_JSON = object()


@pytest.mark.parametrize(
    ("label", "payload", "text", "expected"),
    [
        ("no_choices", {"model": "z-ai/glm-5.2"}, None, "unexpected structure"),
        ("empty_choices", {"model": "z-ai/glm-5.2", "choices": []}, None, "unexpected structure"),
        ("no_message", {"model": "z-ai/glm-5.2", "choices": [{}]}, None, "unexpected structure"),
        ("not_json", _NOT_JSON, "<html>502 Bad Gateway</html>", "was not JSON"),
    ],
)
def test_openrouter_malformed_body_escalates_with_the_response_attached(
    monkeypatch, label, payload, text, expected
):
    """A response that ARRIVED must never be lost. A body of unexpected shape used to raise
    a bare KeyError, discarding the provider's reply — now it raises ReviewerParseError
    carrying that reply verbatim, so the escalation it drives stays on the record (Rule 13)."""
    import httpx

    a = _rec("leprohon", "leprohon-45", "Amasis", prenomina=["Khnemibre"])
    b = _rec("beckerath", "beckerath-45", "Amasis", prenomina=["Chnem-ib-rê"])
    cand = generate_candidates([a, b])[0]
    monkeypatch.setattr(httpx, "post", lambda *args, **kw: _FakeHttpResponse(payload, text=text))

    with pytest.raises(ReviewerParseError) as excinfo:
        review_with_openrouter("key", cand, a, b, model="z-ai/glm-5.2")

    err = excinfo.value
    assert expected in str(err)
    assert err.interaction.raw_response == (text if payload is _NOT_JSON else payload)
    assert err.interaction.parse_error == str(err)
    assert err.interaction.provider == "openrouter"
    assert err.interaction.requested_model == "z-ai/glm-5.2"
    assert err.interaction.parameters == {"max_tokens": 3000, "temperature": 0}
    assert err.interaction.system_prompt == SYSTEM_PROMPT
    assert err.interaction.user_prompt == _build_user_prompt(cand, a, b)


@pytest.mark.parametrize(
    ("status", "payload", "text"),
    [
        (429, {"error": {"code": 429, "message": "Rate limit exceeded, retry in 12s"}}, None),
        (400, {"error": {"code": 400, "message": "context length exceeded"}}, None),
        (401, {"error": {"code": 401, "message": "No auth credentials found"}}, None),
        (500, _NOT_JSON, "<html>502 Bad Gateway</html>"),
    ],
)
def test_openrouter_error_status_persists_the_error_body(monkeypatch, status, payload, text):
    """An HTTP error is a real blocker, so it still fails the run loud — but the provider's
    error BODY (rate-limit window, context-length overflow, auth failure) is the most
    diagnostic payload in the exchange. `raise_for_status()` used to run before the body was
    read, so the attempt was recorded as `raw_response=None` with a marker asserting no body
    was received: a false provenance claim (Rule 13)."""
    import httpx

    a = _rec("leprohon", "leprohon-46", "Amasis", prenomina=["Khnemibre"])
    b = _rec("beckerath", "beckerath-46", "Amasis", prenomina=["Chnem-ib-rê"])
    cand = generate_candidates([a, b])[0]
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *args, **kw: _FakeHttpResponse(payload, text=text, status_code=status),
    )

    with pytest.raises(ReviewerHttpError) as excinfo:
        review_with_openrouter("key", cand, a, b, model="z-ai/glm-5.2")

    err = excinfo.value
    assert f"HTTP {status}" in str(err)
    assert err.interaction.raw_response == (text if payload is _NOT_JSON else payload)
    assert err.interaction.raw_response is not None
    assert err.interaction.call_error == (
        f"OpenRouter returned HTTP {status}; error body captured above."
    )
    assert err.interaction.parse_error is None
    assert err.interaction.parameters == {"max_tokens": 3000, "temperature": 0}
    assert err.interaction.user_prompt == _build_user_prompt(cand, a, b)


def test_http_error_attempt_is_persisted_with_its_body_when_a_later_attempt_succeeds():
    """Attempt 1 gets a 429 WITH a body, attempt 2 succeeds: the failed attempt is kept in
    order and carries the provider's error body verbatim — not None."""
    error_body = {"error": {"code": 429, "message": "Rate limit exceeded, retry in 12s"}}
    calls = []

    def flaky(c, x, y):
        n = len(calls) + 1
        calls.append(n)
        if n == 1:
            raise ReviewerHttpError(
                "OpenRouter returned HTTP 429",
                interaction=_interaction(
                    provider="openrouter",
                    requested_model="z-ai/glm-5.2",
                    model_snapshot=None,
                    parameters={"max_tokens": 3000, "temperature": 0},
                    raw_response=error_body,
                    call_error="OpenRouter returned HTTP 429; error body captured above.",
                ),
                request_digest="digest-http",
            )
        return Verdict(
            candidate_id=c.id,
            outcome=VERDICT_APPROVED,
            reason="same king",
            reviewer="llm",
            request_digest="digest-http",
            interactions=[_interaction(model_snapshot="snap-2", raw_response={"id": "msg_2"})],
        )

    cand, a, b = _pair(47)
    v = verdicts_mod._review_with_retry(
        flaky, cand, a, b, retries=2, model="z-ai/glm-5.2", provider="openrouter"
    )
    assert calls == [1, 2]
    assert v.outcome == VERDICT_APPROVED
    assert [i.attempt for i in v.interactions] == [1, 2]
    failed = v.interactions[0]
    assert failed.raw_response == error_body
    assert failed.call_error == "OpenRouter returned HTTP 429; error body captured above."
    assert failed.parse_error is None


def test_persistent_http_error_fails_loud_and_keeps_every_interaction():
    """An error status is a blocker (credits, auth, rate limit) — it must never quietly
    escalate the candidate the way an unparseable response does. But the calls that ENDED
    the run are the ones most needed for diagnosis, so the terminal exception carries every
    attempt, with the provider's error body intact (Rule 13)."""
    bodies = [
        {"error": {"code": 429, "message": "Rate limit exceeded, retry in 12s"}},
        {"error": {"code": 401, "message": "No auth credentials found"}},
    ]
    calls = []
    cand, a, b = _pair(48)
    real_prompt = _build_user_prompt(cand, a, b)

    def boom(c, x, y):
        n = len(calls)
        calls.append(n)
        raise ReviewerHttpError(
            f"OpenRouter returned HTTP {bodies[n]['error']['code']}",
            interaction=_interaction(
                provider="openrouter",
                requested_model="z-ai/glm-5.2",
                parameters={"max_tokens": 3000, "temperature": 0},
                user_prompt=real_prompt,
                raw_response=bodies[n],
                call_error=f"OpenRouter returned HTTP {bodies[n]['error']['code']};"
                " error body captured above.",
            ),
            request_digest="digest-http",
        )

    with pytest.raises(verdicts_mod.ReviewerRunAborted) as excinfo:
        verdicts_mod._review_with_retry(
            boom, cand, a, b, retries=1, model="z-ai/glm-5.2", provider="openrouter"
        )

    err = excinfo.value
    assert "Live reviewer failed" in str(err)
    assert err.candidate_id == cand.id
    assert err.request_digest == "digest-http"
    assert [i.attempt for i in err.interactions] == [1, 2]
    assert [i.raw_response for i in err.interactions] == bodies
    assert [i.call_error for i in err.interactions] == [
        "OpenRouter returned HTTP 429; error body captured above.",
        "OpenRouter returned HTTP 401; error body captured above.",
    ]
    for i in err.interactions:
        assert i.system_prompt == SYSTEM_PROMPT
        assert i.user_prompt == _build_user_prompt(cand, a, b)
        assert i.parameters == {"max_tokens": 3000, "temperature": 0}


def test_terminal_failure_writes_its_interactions_to_disk_before_the_run_dies(tmp_path):
    """A candidate that never completes writes no verdict, so without this the provider's
    final error body would die with the run. The failed attempts are appended to a file
    NEXT TO the verdict cache — separate, because they are failed attempts and must never
    be mistaken for a decision on resume."""
    error_body = {"error": {"code": 401, "message": "No auth credentials found"}}
    a = _rec("leprohon", "leprohon-50", "Amasis", prenomina=["Khnemibre"])
    b = _rec("beckerath", "beckerath-50", "Amasis", prenomina=["Chnem-ib-rê"])
    real_prompt = _build_user_prompt(generate_candidates([a, b])[0], a, b)

    def boom(c, x, y):
        raise ReviewerHttpError(
            "OpenRouter returned HTTP 401",
            interaction=_interaction(
                raw_response=error_body, call_error="HTTP 401", user_prompt=real_prompt
            ),
            request_digest="digest-http",
        )

    cache_path = str(tmp_path / "cache.jsonl")

    with pytest.raises(verdicts_mod.ReviewerRunAbortedGroup) as excinfo:
        verdicts_mod.resolve_matches(
            [a, b], mode="llm", reviewer_fn=boom, model="claude-sonnet-5",
            retries_per_candidate=1, cache_path=cache_path, uncertain_readings=frozenset()
        )

    # the same evidence is on the raised error, not only on disk
    assert [ab.candidate_id for ab in excinfo.value.aborts] == ["cand-beckerath-50|leprohon-50"]
    assert excinfo.value.as_records() == [ab.as_record() for ab in excinfo.value.aborts]
    assert cache_path + ".failed-attempts.jsonl" in str(excinfo.value)

    # no verdict was reached, so the verdict cache stays empty — a failed attempt is not a
    # decision and must never be resumed as one
    assert open(cache_path, encoding="utf-8").read() == ""
    records = [
        json.loads(line)
        for line in open(cache_path + ".failed-attempts.jsonl", encoding="utf-8")
        if line.strip()
    ]
    assert len(records) == 1
    rec = records[0]
    assert rec["candidate_id"] == "cand-beckerath-50|leprohon-50"
    assert rec["aborted"] is True
    assert "Live reviewer failed" in rec["error"]
    assert rec["request_digest"] == "digest-http"
    assert [i["attempt"] for i in rec["interactions"]] == [1, 2]
    assert [i["raw_response"] for i in rec["interactions"]] == [error_body, error_body]
    assert [i["call_error"] for i in rec["interactions"]] == ["HTTP 401", "HTTP 401"]
    assert rec["interactions"][0]["system_prompt"] == SYSTEM_PROMPT
    assert rec["interactions"][0]["user_prompt"] == real_prompt


def test_abort_without_a_cache_path_carries_its_evidence_on_the_raised_error():
    """The DEFAULT configuration has no cache_path, so nothing is written to disk and the
    raised error is the only copy of the evidence. It must therefore actually carry it."""
    error_body = {"error": {"code": 401, "message": "No auth credentials found"}}
    a = _rec("leprohon", "leprohon-51", "Amasis", prenomina=["Khnemibre"])
    b = _rec("beckerath", "beckerath-51", "Amasis", prenomina=["Chnem-ib-rê"])
    real_prompt = _build_user_prompt(generate_candidates([a, b])[0], a, b)

    def boom(c, x, y):
        raise ReviewerHttpError(
            "OpenRouter returned HTTP 401",
            interaction=_interaction(
                raw_response=error_body, call_error="HTTP 401", user_prompt=real_prompt
            ),
            request_digest="digest-401",
        )

    with pytest.raises(verdicts_mod.ReviewerRunAbortedGroup) as excinfo:
        verdicts_mod.resolve_matches(
            [a, b], mode="llm", reviewer_fn=boom, model="claude-sonnet-5",
            retries_per_candidate=1, uncertain_readings=frozenset()
        )

    err = excinfo.value
    assert "1 candidate(s) failed after retries" in str(err)
    assert "only copy" in str(err)
    assert len(err.aborts) == 1
    ab = err.aborts[0]
    assert ab.candidate_id == "cand-beckerath-51|leprohon-51"
    assert ab.request_digest == "digest-401"
    assert [i.attempt for i in ab.interactions] == [1, 2]
    assert [i.raw_response for i in ab.interactions] == [error_body, error_body]
    assert [i.user_prompt for i in ab.interactions] == [real_prompt, real_prompt]


def test_multiple_aborts_are_all_recoverable_from_the_raised_error():
    """Two candidates abort in the same (no-cache) run: the ids, digests and interactions
    of BOTH must be recoverable. Collapsing them into the first candidate's abort — as the
    aggregate message claimed not to do — would silently lose the second."""
    bodies = {
        "cand-beckerath-60|leprohon-60": {"error": {"code": 429, "message": "rate limited"}},
        "cand-beckerath-61|leprohon-61": {"error": {"code": 401, "message": "no credentials"}},
    }
    recs = [
        _rec("leprohon", "leprohon-60", "Amasis", prenomina=["Khnemibre"]),
        _rec("beckerath", "beckerath-60", "Amasis", prenomina=["Chnem-ib-rê"]),
        _rec("leprohon", "leprohon-61", "Amenhotep I", prenomina=["Djeserkare"]),
        _rec("beckerath", "beckerath-61", "Amenophis I", prenomina=["Djeser-ka-Re"]),
    ]
    assert {c.id for c in generate_candidates(recs)} == set(bodies)

    def boom(c, x, y):
        raise ReviewerHttpError(
            f"provider error for {c.id}",
            interaction=_interaction(raw_response=bodies[c.id], call_error=f"HTTP {c.id}"),
            request_digest=f"digest-{c.id}",
        )

    with pytest.raises(verdicts_mod.ReviewerRunAbortedGroup) as excinfo:
        verdicts_mod.resolve_matches(
            recs, mode="llm", reviewer_fn=boom, model="claude-sonnet-5",
            retries_per_candidate=1, uncertain_readings=frozenset()
        )

    err = excinfo.value
    assert "2 candidate(s) failed after retries" in str(err)
    by_id = {ab.candidate_id: ab for ab in err.aborts}
    assert set(by_id) == set(bodies)
    for cid, body in bodies.items():
        ab = by_id[cid]
        assert ab.request_digest == f"digest-{cid}"
        assert [i.attempt for i in ab.interactions] == [1, 2]
        assert [i.raw_response for i in ab.interactions] == [body, body]
        assert [i.call_error for i in ab.interactions] == [f"HTTP {cid}"] * 2
        assert cid in str(err)  # every aborted candidate is named in the message


def test_exception_carried_error_body_is_persisted():
    """The Anthropic SDK raises `APIStatusError` carrying the server's error payload on
    `.body` rather than handing back a response, so that payload is captured from the
    exception instead of being discarded."""

    class _FakeAPIStatusError(Exception):
        def __init__(self):
            super().__init__("Error code: 529 - overloaded_error")
            self.body = {"type": "error", "error": {"type": "overloaded_error"}}

    calls = []

    def flaky(c, x, y):
        calls.append(len(calls) + 1)
        if len(calls) == 1:
            raise _FakeAPIStatusError()
        return Verdict(
            candidate_id=c.id,
            outcome=VERDICT_APPROVED,
            reason="same king",
            reviewer="llm",
            interactions=[_interaction(raw_response={"id": "msg_2"})],
        )

    cand, a, b = _pair(49)
    v = verdicts_mod._review_with_retry(
        flaky, cand, a, b, retries=2, model="claude-sonnet-5", provider=PROVIDER_ANTHROPIC
    )
    failed = v.interactions[0]
    assert failed.raw_response == {"type": "error", "error": {"type": "overloaded_error"}}
    assert failed.call_error == "_FakeAPIStatusError: Error code: 529 - overloaded_error"


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
    res = verdicts_mod.resolve_matches(recs, mode="llm", client=object(), model="m", cache_path=None, uncertain_readings=frozenset())
    assert res.approved_edges == []
    assert len(res.escalations) == 1
    assert res.escalations[0].reviewer == "deterministic"
    assert "external documented evidence" in res.escalations[0].reason.lower()


def test_openrouter_mode_requires_api_key():
    recs = [_rec("leprohon", "leprohon-12", "X", prenomina=["Khnemibre"])]
    with pytest.raises(RuntimeError, match="without an api_key"):
        verdicts_mod.resolve_matches(recs, mode="llm", provider="openrouter", api_key=None, uncertain_readings=frozenset())


# --- verdicts.py: the resumable cache is request-pinned --------------------


def _cached_run(tmp_path, *, model, cache_name="cache.jsonl"):
    """One resolve_matches run over a single clean prenomen pair, with a verdict cache.
    Returns (result, cache_path, calls) where `calls` counts live reviewer invocations."""
    a = _rec("leprohon", "leprohon-30", "Amasis", prenomina=["Khnemibre"])
    b = _rec("beckerath", "beckerath-30", "Amasis", prenomina=["Chnem-ib-rê"])
    by_id = {r.local_id: r for r in (a, b)}
    calls: list[str] = []

    def reviewer_fn(c, x, y):
        calls.append(c.id)
        return Verdict(
            candidate_id=c.id,
            outcome=VERDICT_APPROVED,
            reason="same king",
            reviewer="llm",
            request_digest=request_digest(
                c, by_id[c.a_id], by_id[c.b_id],
                provider=PROVIDER_ANTHROPIC, model=model,
                parameters=dict(ANTHROPIC_PARAMETERS),
            ),
            interactions=[_interaction(requested_model=model)],
        )

    cache_path = str(tmp_path / cache_name)
    res = verdicts_mod.resolve_matches(
        [a, b], mode="llm", reviewer_fn=reviewer_fn, model=model, cache_path=cache_path, uncertain_readings=frozenset()
    )
    return res, cache_path, calls


def test_cached_verdict_is_reused_when_the_request_is_identical(tmp_path):
    res, cache_path, calls = _cached_run(tmp_path, model="claude-sonnet-5")
    assert len(res.approved_edges) == 1
    assert calls == ["cand-beckerath-30|leprohon-30"]
    # second run over an identical request: the cached verdict is reused, no new call
    res2, _, calls2 = _cached_run(tmp_path, model="claude-sonnet-5")
    assert calls2 == []
    assert len(res2.approved_edges) == 1
    assert res2.verdicts[0].interactions[0].requested_model == "claude-sonnet-5"


def test_cached_verdict_from_a_different_model_raises(tmp_path):
    _cached_run(tmp_path, model="claude-sonnet-5")
    # same candidate, different reviewer configuration → the cached verdict does NOT
    # describe this run and must not be reused (Rule 6/13).
    with pytest.raises(RuntimeError, match="produced under a DIFFERENT request"):
        _cached_run(tmp_path, model="z-ai/glm-5.2")


def test_conflicting_cache_lines_for_one_candidate_raise(tmp_path):
    _, cache_path, _ = _cached_run(tmp_path, model="claude-sonnet-5")
    original = open(cache_path, encoding="utf-8").read().strip()
    # an appended re-review that disagrees: last-write-wins would silently pick one by file
    # order — a verdict with no provenance.
    with open(cache_path, "a", encoding="utf-8") as fh:
        fh.write(original.replace("verdict_approved", "verdict_rejected") + "\n")
    with pytest.raises(RuntimeError, match="CONFLICTING entries"):
        verdicts_mod._load_cache(cache_path)


def test_identical_duplicate_cache_lines_are_idempotent(tmp_path):
    _, cache_path, _ = _cached_run(tmp_path, model="claude-sonnet-5")
    original = open(cache_path, encoding="utf-8").read().strip()
    with open(cache_path, "a", encoding="utf-8") as fh:
        fh.write(original + "\n")
    cached = verdicts_mod._load_cache(cache_path)
    assert set(cached) == {"cand-beckerath-30|leprohon-30"}
    assert cached["cand-beckerath-30|leprohon-30"].outcome == VERDICT_APPROVED


def test_cache_round_trip_preserves_every_interaction(tmp_path):
    _, cache_path, _ = _cached_run(tmp_path, model="claude-sonnet-5")
    cached = verdicts_mod._load_cache(cache_path)
    v = cached["cand-beckerath-30|leprohon-30"]
    assert [i.attempt for i in v.interactions] == [1]
    i = v.interactions[0]
    assert isinstance(i, ReviewerInteraction)
    assert i.provider == PROVIDER_ANTHROPIC
    assert i.requested_model == "claude-sonnet-5"
    assert i.parameters == dict(ANTHROPIC_PARAMETERS)
    assert i.system_prompt == SYSTEM_PROMPT
    assert i.raw_response == {"content": [{"type": "text", "text": "garbled"}]}


# --- escalation-queue rules (ADR-020 amendment 2026-10-12) ------------------


def _one(recs):
    cands = generate_candidates(recs)
    assert len(cands) == 1
    return cands[0]


def test_same_name_same_dynasty_without_titulary_goes_to_the_reviewer():
    """Kitchen's Psusennes I carries no throne name: before, name_only and never reviewed."""
    c = _one([
        _rec("kitchen", "kitchen-21.03", "Psusennes I", dynasty=21),
        _rec("pharaoh_se", "pharaoh_se-Psusennes-I", "Psusennes I", dynasty=21,
             prenomina=["Aa kheper Ra, setep en Amun"]),
    ])
    assert c.basis == "name_dynasty"
    assert c.shared_name_keys == ["psusennesi"]


@pytest.mark.parametrize(
    ("a", "b", "basis"),
    [
        # Different regnal numbers: different kings, stays name_only.
        (("Amenhotep I", 18), ("Amenhotep II", 18), "name_only"),
        # Different dynasty, or none known.
        (("Teti", 1), ("Teti", 6), "name_only"),
        (("Apries", None), ("Apries", 26), "name_only"),
        # Ryholt renumbered the Dyn 13 Sobekhoteps against Beckerath.
        (("Sobekhotep II", 13), ("Sobekhotep II", 13), "name_only"),
        # One number missing is not a conflict.
        (("Apries", 26), ("Apries II", 26), "name_dynasty"),
    ],
)
def test_name_dynasty_needs_one_dynasty_outside_13_17_and_no_conflicting_number(a, b, basis):
    c = _one([
        _rec("kitchen", "kitchen-x", a[0], dynasty=a[1], nomina=[a[0].split()[0]]),
        _rec("pharaoh_se", "pharaoh_se-x", b[0], dynasty=b[1], nomina=[b[0].split()[0]]),
    ])
    assert c.basis == basis


def test_a_later_horus_name_corroborates_only_with_a_shared_king_name():
    same_king = _one([
        _rec("leprohon", "leprohon-20.02", "Ramesses III", dynasty=20,
             horus_names=["ka nakht aa nesyt"], prenomina=["weser maat ra"]),
        _rec("pharaoh_se", "pharaoh_se-R3", "Ramesses III", dynasty=20,
             horus_names=["Ka nakht aa nesyt"], prenomina=["User Maat Ra, mery Amun"]),
    ])
    assert (same_king.basis, same_king.early_dynastic) == ("horus", False)
    # Kanakht-meryre is borne by Thutmose III, Sety I, Ramesses II and Sety II.
    reused = _one([
        _rec("leprohon", "leprohon-19.02", "Sety I", dynasty=19, horus_names=["ka nakht mery ra"]),
        _rec("pharaoh_se", "pharaoh_se-T3", "Thutmose III", dynasty=18, horus_names=["Ka nakht mery Ra"]),
    ])
    assert reused.basis == "name_only"


def test_a_listed_skeleton_collision_does_not_trap_a_pair_sharing_its_full_throne_name():
    """Thutmose IV's Menkheperure skeletons to Thutmose III's listed Menkheperre."""
    c = _one([
        _rec("leprohon", "leprohon-18.08", "Thutmose IV", dynasty=18, prenomina=["men kheperu ra"]),
        _rec("pharaoh_se", "pharaoh_se-T4", "Thutmose IV", dynasty=18, prenomina=["Men kheperu Ra"]),
    ])
    assert c.basis == "prenomen"
    assert "mnkhprr" in c.shared_prenomen_keys
    assert c.homonym_trap is None
    # Sharing only the listed name itself, as spelled, stays trapped.
    trapped = _one([
        _rec("leprohon", "leprohon-x", "Necho I", dynasty=26, prenomina=["men kheper ra"]),
        _rec("pharaoh_se", "pharaoh_se-x", "Menkheperre", dynasty=21, prenomina=["Men kheper Ra"]),
    ])
    assert trapped.homonym_trap is not None


def test_a_clash_resolves_to_the_target_matched_through_both_primary_throne_names():
    """pharaoh.se's Amenhotep II lists the variant Aakheperuenre, whose skeleton is Thutmose
    II's Aakheperenre: Beckerath's Amenophis II matches his primary name, Tuthmosis II only
    the variant."""
    recs = [
        _rec("beckerath", "beckerath-18.04", "Tuthmosis II.", dynasty=18, prenomina=["A-cheper-en-rê"]),
        _rec("beckerath", "beckerath-18.07", "Amenophis II.", dynasty=18, prenomina=["A-chepru-rê"]),
        _rec("pharaoh_se", "pharaoh_se-A2", "Amenhotep II", dynasty=18,
             prenomina=["Aa kheperu Ra", "Aa kheperu en Ra"]),
        _rec("pharaoh_se", "pharaoh_se-T2", "Thutmose II", dynasty=18, prenomina=["Aa kheper en Ra"]),
    ]
    cands = {c.id: c for c in generate_candidates(recs)}
    assert sorted(cands) == [
        "cand-beckerath-18.04|pharaoh_se-A2",
        "cand-beckerath-18.04|pharaoh_se-T2",
        "cand-beckerath-18.07|pharaoh_se-A2",
    ]
    assert {cid: c.primary_prenomen_match for cid, c in cands.items()} == {
        "cand-beckerath-18.04|pharaoh_se-A2": False,
        "cand-beckerath-18.04|pharaoh_se-T2": True,
        "cand-beckerath-18.07|pharaoh_se-A2": True,
    }
    assert uniqueness_clashes(list(cands.values())) == {"cand-beckerath-18.04|pharaoh_se-A2"}


def test_a_clash_with_a_rival_of_unknown_dynasty_stays_escalated():
    recs = [
        _rec("beckerath", "beckerath-18.04", "Tuthmosis II.", dynasty=None, prenomina=["A-cheper-en-rê"]),
        _rec("beckerath", "beckerath-18.07", "Amenophis II.", dynasty=18, prenomina=["A-chepru-rê"]),
        _rec("pharaoh_se", "pharaoh_se-A2", "Amenhotep II", dynasty=18,
             prenomina=["Aa kheperu Ra", "Aa kheperu en Ra"]),
    ]
    cands = generate_candidates(recs)
    assert uniqueness_clashes(cands) == {
        "cand-beckerath-18.04|pharaoh_se-A2", "cand-beckerath-18.07|pharaoh_se-A2",
    }


def test_a_listed_name_shared_in_full_stays_trapped_beside_an_unlisted_compound():
    """Shabaka's Neferkare is a listed reused name; sharing Neferkare-meryamun as well
    does not make it a skeleton collision (code review P1-2)."""
    c = _one([
        _rec("leprohon", "leprohon-25.04", "Shabaka", dynasty=25,
             prenomina=["nefer ka ra", "nefer ka ra mery amun"]),
        _rec("pharaoh_se", "pharaoh_se-Shabaka", "Shabaka", dynasty=25,
             prenomina=["Nefer ka Ra", "Nefer ka Ra mery Amun"]),
    ])
    assert c.basis == "prenomen"
    assert c.homonym_trap is not None


def test_a_later_horus_name_with_conflicting_regnal_numbers_is_name_only():
    c = _one([
        _rec("leprohon", "leprohon-19.02", "Sety I", dynasty=19, horus_names=["ka nakht mery ra"]),
        _rec("pharaoh_se", "pharaoh_se-S2", "Sety II", dynasty=19, horus_names=["Ka nakht mery Ra"]),
    ])
    assert c.basis == "name_only"


@pytest.mark.parametrize(("name", "number"), [
    ("Ramesses III", "III"), ("Amenophis II.", "II"), ("Userkare (I)", "I"),
    ("Thutmose III (a)", "III"), ("Mentuhotep II (b)", "II"), ("Khety (VI)", "VI"),
    ("Sheshonq IIa", None), ("Ity", None), ("Djedkare Isesi", None),
])
def test_regnal_number_reads_plain_parenthesised_and_stage_suffixed_numerals(name, number):
    assert regnal_number_of(name) == number


def _window(rec, start, end):
    return replace(rec, reign_start_bce=start, reign_end_bce=end)


@pytest.mark.parametrize(("a", "b", "ok"), [
    ((-589, -570), (-589, -570), True),
    ((-1047, -1001), (-1039, -991), True),     # 39 of the shorter 47 years
    ((-2461, -2456), (-2441, -2436), False),   # no overlap
    ((-2446, -2433), (-2440, -2439), True),    # all of the shorter window
    ((-2446, -2433), (-2434, -2420), False),   # 2 of 14 years
    ((-2446, -2433), (None, None), False),     # a window unknown
])
def test_king_name_route_needs_both_windows_overlapping_by_half(a, b, ok):
    x = _window(_rec("kitchen", "kitchen-1", "Apries", dynasty=26), *a)
    y = _window(_rec("beckerath", "beckerath-1", "Apries", dynasty=26), *b)
    assert king_name_route_corroborated(x, y) is ok


def test_a_fragmentary_throne_name_is_not_titulary():
    assert lacks_titulary(_rec("ryholt", "ryholt-13.x", "Djed /// Re", prenomina=["Djed /// Re"]))
    assert not lacks_titulary(_rec("ryholt", "ryholt-13.y", "Djedneferre", prenomina=["Djedneferre"]))


def test_king_name_route_needs_the_same_regnal_number():
    x = _window(_rec("kitchen", "kitchen-1", "Psusennes I", dynasty=21), -1047, -1001)
    assert king_name_route_corroborated(x, _window(_rec("beckerath", "b-1", "Psusennes I", dynasty=21), -1047, -1001))
    assert not king_name_route_corroborated(x, _window(_rec("beckerath", "b-1", "Psusennes", dynasty=21), -1047, -1001))


def test_a_blocked_king_name_pair_is_not_a_rival_in_a_uniqueness_clash():
    # Beckerath's Amasis matches one Kitchen record through a secondary throne-name variant
    # (so the primary-name rule cannot settle a clash) and another, without titulary and with
    # no reign window, by name and dynasty. finalize can never approve the second, so it
    # must not escalate the first as a clash (Codex review of #357).
    becke = _window(_rec("beckerath", "beckerath-26.05", "Amasis", dynasty=26, prenomina=["Khnemibre"]), -570, -526)
    by_throne = _window(_rec("kitchen", "kitchen-26.5", "Ahmose II", dynasty=26, prenomina=["Wahkare", "Khnemibre"]), -570, -526)
    by_name = _rec("kitchen", "kitchen-26.x", "Amasis", dynasty=26)
    cands = {(c.a_id, c.b_id): c for c in generate_candidates([becke, by_throne, by_name])}
    throne = cands[("beckerath-26.05", "kitchen-26.5")]
    name = cands[("beckerath-26.05", "kitchen-26.x")]
    assert (throne.basis, throne.king_name_route_blocked, throne.primary_prenomen_match) == ("prenomen", False, False)
    assert (name.basis, name.king_name_route_blocked) == ("name_dynasty", True)
    assert uniqueness_clashes([throne, name]) == set()
    # With a window the name pair is approvable, and the two targets clash.
    windowed = replace(name, king_name_route_blocked=False)
    assert uniqueness_clashes([throne, windowed]) == {throne.id, windowed.id}


def _always_approve(client, c, a, b, model):
    return Verdict(candidate_id=c.id, outcome=VERDICT_APPROVED, reason="same king", reviewer="llm")


def test_an_approved_king_name_pair_without_corroborating_windows_is_escalated(monkeypatch):
    monkeypatch.setattr(verdicts_mod, "review_with_llm", _always_approve)
    recs = [
        _window(_rec("beckerath", "beckerath-04.07", "Schepses-kaf", dynasty=4, nomina=["Shepseskaf"]),
                -2461, -2456),
        _window(_rec("pharaoh_se", "pharaoh_se-Shepseskaf", "Shepseskaf", dynasty=4,
                     prenomina=["Shepses ka f"], nomina=["Shepseskaf"]), -2441, -2436),
    ]
    res = verdicts_mod.resolve_matches(recs, mode="llm", client=object(), model="m", cache_path=None,
                                       uncertain_readings=frozenset())
    assert res.approved_edges == []
    assert [e.basis for e in res.escalations] == ["name_dynasty"]
    assert res.escalations[0].reason.endswith(
        "[overridden to escalate: king-name route needs both reign windows, overlapping by at "
        "least half the shorter, and the same regnal number]"
    )
    # Both records carrying titulary: the reviewer weighed throne names; the guard is silent.
    recs[0] = replace(recs[0], prenomina=[NameForm(surface="Nebka")])
    res = verdicts_mod.resolve_matches(recs, mode="llm", client=object(), model="m", cache_path=None,
                                       uncertain_readings=frozenset())
    assert [e.basis for e in res.approved_edges] == ["name_dynasty"]


def test_an_era_rejected_pair_on_an_uncertain_reading_stays_rejected(monkeypatch):
    monkeypatch.setattr(verdicts_mod, "review_with_llm", _always_approve)
    recs = [
        _window(_rec("leprohon", "leprohon-4.01", "Senakhtenre", dynasty=4, prenomina=["Senakhtenre"]),
                -2600, -2590),
        _window(_rec("ryholt", "ryholt-17.7", "Siamun (?)", dynasty=17, prenomina=["Senakhtenre"]),
                -1559, -1558),
    ]
    res = verdicts_mod.resolve_matches(recs, mode="llm", client=object(), model="m", cache_path=None,
                                       uncertain_readings=frozenset({"ryholt-17.7"}))
    assert res.verdicts[0].outcome == VERDICT_REJECTED
    assert res.escalations == []


def test_a_cached_verdict_never_outranks_a_name_only_basis(tmp_path):
    """A pair the current matcher calls name-only is escalated deterministically even when
    the cache holds a reviewer verdict from a matcher that gave it a basis."""
    recs = [
        _rec("kitchen", "kitchen-21.03", "Psusennes I", dynasty=21),
        _rec("pharaoh_se", "pharaoh_se-P1", "Psusennes I", dynasty=22),
    ]
    (c,) = generate_candidates(recs)
    assert c.basis == "name_only"
    digest = request_digest(c, recs[0], recs[1], provider=PROVIDER_ANTHROPIC, model="m",
                            parameters=dict(ANTHROPIC_PARAMETERS))
    cache = tmp_path / "cache.jsonl"
    cache.write_text(json.dumps(asdict(Verdict(
        candidate_id=c.id, outcome=VERDICT_APPROVED, reason="same king", reviewer="llm",
        request_digest=digest, interactions=[_interaction(requested_model="m")],
    ))) + "\n")
    res = verdicts_mod.resolve_matches(recs, mode="llm", client=object(), model="m",
                                       cache_path=str(cache), uncertain_readings=frozenset())
    assert res.approved_edges == []
    assert [(v.outcome, v.reviewer) for v in res.verdicts] == [(VERDICT_ESCALATED, "deterministic")]


def test_reviewer_policy_is_the_leak_audited_text():
    """The hash the last PASS round of the leak audit records (Rule 14)."""
    import hashlib
    import re
    from pathlib import Path

    audit = (Path(__file__).resolve().parents[2]
             / "docs/evaluations/ruler-escalation-queue/prompt-audit-2026-10-12.md").read_text()
    (audited,) = re.findall(r"Audited `SYSTEM_PROMPT` SHA-256 \(UTF-8\): `([0-9a-f]{64})`", audit)
    assert hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest() == audited
