"""Spelling links between D&H's women and the TLA's names (protocol v2): the deterministic
candidates and review units, the review runner's checks, and the resolver reading linked
spellings."""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import pytest

from pipeline.authority import royal_women as rw
from pipeline.authority import tla_link_review as review
from pipeline.authority import tla_links as tl

sys.path.insert(0, str(Path(__file__).parent))
from test_royal_women import KINGS  # noqa: E402


@pytest.fixture(scope="module")
def women() -> list[rw.RoyalWoman]:
    return rw.load_royal_women()


@pytest.fixture(scope="module")
def pairs(women) -> list[tl.Pair]:
    return tl.candidate_pairs(women, tl.tla_rows())


def by_id(pairs, pair_id):
    (pair,) = [p for p in pairs if p.pair_id == pair_id]
    return pair


def test_the_candidate_pairs_and_their_tiers(pairs) -> None:
    assert len(pairs) == 165
    assert collections.Counter(p.tier for p in pairs) == {
        "weak_sign_skeleton": 122, "raw_exact": 34, "committed_normalized": 9}
    assert len({p.pair_id for p in pairs}) == len(pairs)
    # Same spelling, linked by rule: D&H "Ahmes-Nefertiry" against TLA 600465 is a weak-sign
    # pair (the TLA writes Ahmes-Nefertari), while an identical spelling is exact.
    assert by_id(pairs, "Ahmes-Nefertiry|600465").tier == "weak_sign_skeleton"
    assert by_id(pairs, "Ahhotep|450271").dh_target_ids == ("dodson_hilton:Ahhotep I", "dodson_hilton:Ahhotep II")
    # Only personal-name lemmas: the queens' royal-name lemmas are the kings' stage.
    tla = {r["tla_id"]: r for r in tl.tla_rows()}
    assert {tla[p.tla_id]["subtype"] for p in pairs} == {"person_name"}


def test_keys_that_different_names_share_propose_nothing(pairs, women) -> None:
    from pipeline.authority.weak_sign_skeleton import weak_sign_skeleton
    # D&H spells these keys differently for different women: Henttawy / Henutwati, Nebetia /
    # Nebtit / Nebtu, Neferet / Neferu, Tentamun / Tintamun.
    assert tl.withheld_keys(women) == {"hntt", "nbt", "nfr", "tntmn"}
    weak = [p for p in pairs if p.tier == "weak_sign_skeleton"]
    assert len(weak) == 122
    assert not {weak_sign_skeleton(p.dh_name) for p in weak} & tl.withheld_keys(women)


def test_renderings_drop_glosses_and_descriptions() -> None:
    row = {"transliteration": "Jꜥḥ-ms.w-nfr.t-jr.j", "translations": [
        {"lang": "de", "value": "Ahmes-Nefertari (Frau des Ahmose)"}, {"lang": "en", "value": "[a queen]"},
        {"lang": "en"}, {"lang": "en", "value": "Ahmose-Nofretari; Nefertari"}]}
    assert tl.renderings(row) == ["Jꜥḥ-ms.w-nfr.t-jr.j", "Ahmes-Nefertari", "Ahmose-Nofretari"]


def test_strict_name_is_the_transliteration_without_separators_or_marks() -> None:
    assert tl.strict_name("Jꜥḥ-ms.w-nfr.t-jr.j") == "jꜥḥmswnfrtjrj"
    assert tl.strict_name("Jni̯-jtj=f") == "jnijtjf"
    assert tl.strict_name("Nfr.t-jr.j mr.yt-Mw.t") == "nfrtjrjmrytmwt"


@pytest.fixture(scope="module")
def units(women) -> dict[str, tl.Unit]:
    return {u.dh_name: u for u in tl.units(women, tl.tla_rows())}


def test_a_name_is_one_name_one_rule_name_decides_and_otherwise_it_is_reviewed(units) -> None:
    rule = [u for u in units.values() if u.by_rule]
    review_units = [u for u in units.values() if not u.by_rule]
    assert (len(units), len(rule), len(review_units)) == (97, 32, 65)
    assert sum(len(u.options) for u in review_units) == 108
    assert all(not u.options for u in rule) and all(u.options for u in review_units)
    # One TLA name on the exact or claim-graph keys decides; the weak-sign candidates of a
    # name so decided are not reviewed.
    assert units["Seneb"].by_rule == tl.Option("snb", ("450043",))
    assert units["Neferure"].by_rule == tl.Option("nfrwrꜥw", ("400800",))
    # Two TLA names on the exact keys are not a rule decision: the unit is reviewed.
    assert [o.name for o in units["Iaret"].options] == ["jꜣrt", "jꜥrt"]
    assert [o.name for o in units["Ti"].options] == ["tj", "ty"]
    assert len(units["Mereret"].options) == 8


def test_options_are_shown_under_seeded_opaque_labels(units) -> None:
    labels = review.labelled(units["Mereret"])
    assert {k: v.name for k, v in labels.items()} == {
        "C1": "mrry", "C2": "mrryt", "C3": "mrrw", "C4": "mrr", "C5": "mrrj", "C6": "mrrwy", "C7": "mrrꜥw",
        "C8": "mryrꜥw"}
    assert {k: v.name for k, v in review.labelled(units["Ti"]).items()} == {"C1": "ty", "C2": "tj"}


def test_a_composed_prompt_carries_the_name_the_candidates_and_the_choices_only(units) -> None:
    data = review.inputs()
    text = review.compose(data["reviewer"], units["Ti"], data["tla"])
    assert "Name: Ti\n" in text
    assert "Candidate C1: Ty\n  Lemma 1: German: " in text and "Candidate C2: Tj\n  Lemma 1: German: " in text
    assert '"choices": [<zero or more of "C1", "C2">]' in text
    assert review.RULES in text and "{" not in review.RULES
    # The D&H side is the name only: no target id, letter, dynasty or kin; no lemma id either.
    assert "dodson_hilton" not in text and "Dynasty" not in text
    assert not any(t in text for o in units["Ti"].options for t in o.tla_ids)
    assert "{" + "candidates}" not in text and "{" + "reviews}" not in text and "{" + "rules}" not in text


def test_a_lemma_is_shown_by_its_spellings_without_descriptions() -> None:
    tla = {r["tla_id"]: r for r in tl.tla_rows()}
    assert review.spellings(tla["400448"]) == "German: Iaret | English: Iaret"  # "(a wife of Tuthmosis IV)"
    assert review.spellings(tla["703463"]) == "German: Nefer-hetep | English: (none)"  # ", der Ältere"
    assert review.spellings(tla["702722"]) == "German: Ni-hep; Ni-Apis | English: (none)"
    assert review.spellings(tla["705752"]) == "German: Chnum-anchu | English: (none)"  # "Chnum(?)-anchu"
    assert review.spellings(tla["850227"]) == "German: Ti | English: Ti"  # "Ti (?)"


def _record(unit_id: str, answer: str, *, role: str = "A", model: str = "claude-sonnet-5-5", auth: str = "none",
            tools=(), extra_events=(), subtype: str = "success", is_error: bool = False, exit_code: int = 0,
            usage_models=None) -> dict:
    events = [{"type": "system", "subtype": "init", "model": model, "apiKeySource": auth, "tools": list(tools)},
              *extra_events,
              {"type": "result", "subtype": subtype, "is_error": is_error, "result": answer,
               "modelUsage": {m: {} for m in (usage_models or [model])}}]
    return {"unit_id": unit_id, "role": role, "labels": {"C1": "nfr", "C2": "nbt"}, "events": events,
            "exit_code": exit_code}


def _answer(unit_id="X", choices=("C1",), reasoning="nfr = nfr") -> str:
    return json.dumps({"unit_id": unit_id, "choices": list(choices), "reasoning": reasoning})


def test_the_runner_reads_a_clean_answer_and_names_each_malformed_one() -> None:
    assert review.validate(_record("X", "Some note.\n" + _answer())) == {"answer": json.loads(_answer())}
    assert review.validate(_record("X", _answer(choices=()))) == {"answer": json.loads(_answer(choices=()))}
    assert review.validate(_record("X", _answer(choices=("C2", "C1")))) == {
        "answer": json.loads(_answer(choices=("C2", "C1")))}
    silent_hook = {"type": "system", "subtype": "hook_response", "hook_name": "h", "stdout": "", "output": ""}
    assert review.validate(_record("X", _answer(), extra_events=[silent_hook])) == {"answer": json.loads(_answer())}
    assert review.validate(_record("X", "no json")) == {"failure": "answer is not a JSON object at the end of the message"}
    # v2.1: one closing ```json fence around the final object is read; anything after it is not.
    assert review.validate(_record("X", "```json\n" + _answer() + "\n```")) == {"answer": json.loads(_answer())}
    assert review.validate(_record("X", "Note.\n```\n" + _answer() + "\n```\n")) == {"answer": json.loads(_answer())}
    assert review.validate(_record("X", "```json\n" + _answer() + "\n```\nMore.")) == {
        "failure": "answer is not a JSON object at the end of the message"}
    assert review.validate(_record("X", _answer(unit_id="Y"))) == {"failure": "answer does not echo the unit id"}
    assert review.validate(_record("X", _answer(choices=("C3",)))) == {"failure": "choices ['C3'] are not distinct labels"}
    assert review.validate(_record("X", _answer(choices=("C1", "C1")))) == {
        "failure": "choices ['C1', 'C1'] are not distinct labels"}
    assert review.validate(_record("X", json.dumps({"unit_id": "X", "choices": "C1", "reasoning": "r"}))) == {
        "failure": "choices 'C1' are not distinct labels"}
    assert review.validate(_record("X", _answer(reasoning=" "))) == {"failure": "empty reasoning"}
    assert review.validate(_record("X", json.dumps({"unit_id": "X", "choices": ["C1"]}))) == {
        "failure": "answer keys ['choices', 'unit_id']"}
    assert review.validate(_record("X", _answer(), subtype="error_max_turns")) == {
        "failure": "call did not end in a successful result: 'result'/'error_max_turns'"}


@pytest.mark.parametrize(("kwargs", "message"), [
    ({"auth": "ANTHROPIC_API_KEY"}, "bill"),
    ({"model": "claude-haiku-5-5"}, "served models"),
    ({"role": "B"}, "served models"),  # B must be served by opus
    ({"usage_models": ["claude-sonnet-5-5", "claude-haiku-5-5"]}, "served models"),
    ({"extra_events": [{"type": "assistant", "message": {"model": "claude-haiku-5-5", "content": []}}]},
     "served models"),
    ({"tools": ["WebSearch"]}, "tools offered"),
    ({"extra_events": [{"type": "system", "subtype": "hook_response", "stdout": "x"}]}, "hook output"),
    ({"extra_events": [{"type": "assistant", "message": {"model": "claude-sonnet-5-5",
                                                          "content": [{"type": "tool_use"}]}}]}, "used a tool"),
    ({"is_error": True}, "ended in an error"),
])
def test_the_runner_stops_on_billing_another_model_a_tool_a_hook_or_an_error(kwargs, message) -> None:
    with pytest.raises(review.ProtocolFailure, match=message):
        review.validate(_record("X", _answer(), **kwargs))


def test_a_decision_is_read_from_the_event_log_not_the_stored_result() -> None:
    record = _record("X", _answer())
    record["result"] = review.validate(record)
    assert review.valid_answer([record]) == json.loads(_answer())
    record["result"] = {"answer": {**json.loads(_answer()), "choices": ["C2"]}}  # an edited copy
    with pytest.raises(ValueError, match="not what its event log says"):
        review.valid_answer([record])


def test_the_resolver_reads_one_linked_name_as_labels_of_her_name(tmp_path: Path) -> None:
    decisions = tmp_path / "decisions.jsonl"
    decisions.write_text("".join(json.dumps(d) + "\n" for d in [
        {"dh_name": "Ahmes-Nefertiry", "dh_target_ids": ["dodson_hilton:Ahmes-Nefertiry"], "basis": "rule",
         "tla_names": ["jꜥḥmswnfrtjrj"], "tla_ids": ["600465"]},
        {"dh_name": "Bakmut", "dh_target_ids": ["dodson_hilton:Bakmut"], "basis": "agreement", "tla_names": [],
         "tla_ids": []},
    ]), encoding="utf-8")
    linked = tl.linked_spellings(decisions)
    assert linked == {"dodson_hilton:Ahmes-Nefertiry": ("Jꜥḥ-ms.w-nfr.t-jr.j", "Ahmes-Nefertari", "Ahmose-Nofretari")}
    index = rw.build_index(rw.load_royal_women(), KINGS, linked_spellings=linked)
    found = rw.resolve_royal_woman(index, "Ahmose-Nofretari", record_king_ids=set(), record_dynasty=None)
    assert (found["status"], found["resolution_method"], found["target_ids"]) == (
        "resolved", "raw_exact", ["dodson_hilton:Ahmes-Nefertiry"])
    with pytest.raises(ValueError, match="not D&H women"):
        rw.build_index(rw.load_royal_women(), KINGS, linked_spellings={"dodson_hilton:Nobody": ("X",)})


def test_a_decisions_names_must_be_its_lemmas_names(tmp_path: Path) -> None:
    decisions = tmp_path / "decisions.jsonl"
    decisions.write_text(json.dumps({"dh_name": "Minemaes", "dh_target_ids": ["dodson_hilton:Minemaes"],
                                     "basis": "agreement", "tla_names": ["mnwmsw"], "tla_ids": ["550286", "600267"]}),
                         encoding="utf-8")
    with pytest.raises(ValueError, match="are not its lemmas' names"):
        tl.linked_spellings(decisions)


def test_every_rendered_candidate_spelling_is_a_name_without_description() -> None:
    """Prompt audit v2, round 2: no bearer, relation or doubt survives the render."""
    import re
    data = review.inputs()
    ids = {t for u in review.review_units(data) for o in u.options for t in o.tla_ids}
    assert len(ids) == 109
    stop = re.compile(r"\b(Tochter|Frau|Sohn|Mutter|Vater|König|Königin|wife|daughter|son|mother|king|queen|"
                      r"der|die|des|the|of)\b", re.I)
    for tla_id in ids:
        for part in review.spellings(data["tla"][tla_id]).split(" | "):
            for value in part.split(": ", 1)[1].split("; "):
                if value != "(none)":
                    assert not re.search(r"[()\[\]?]", value) and len(value.split()) <= 2 and not stop.search(value), (
                        tla_id, value)


def test_the_prompts_are_the_audited_ones() -> None:
    import hashlib
    audit = (tl.LINKS_DIR / "prompt-audit-v2.md").read_text(encoding="utf-8")
    for name in ("system-v2.txt", "rules-v2.txt", "reviewer-v2.txt", "reconciler-v2.txt"):
        digest = hashlib.sha256((review.PROMPTS / name).read_bytes()).hexdigest()
        assert f"`{name}`: `{digest}`" in audit, name
    assert sorted(p.name for p in review.PROMPTS.iterdir()) == [
        "reconciler-v2.txt", "reviewer-v2.txt", "rules-v2.txt", "system-v2.txt"]
