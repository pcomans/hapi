"""Spelling links between D&H's women and the TLA's names: the deterministic candidate
pairs, the review runner's checks, and the resolver reading linked spellings."""

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


def _record(pair_id: str, answer: str, *, model: str = "claude-sonnet-5-5", auth: str = "none",
            tools=(), extra_events=(), subtype: str = "success", exit_code: int = 0) -> dict:
    events = [{"type": "system", "subtype": "init", "model": model, "apiKeySource": auth, "tools": list(tools)},
              *extra_events,
              {"type": "result", "subtype": subtype, "is_error": False, "result": answer}]
    return {"pair_id": pair_id, "events": events, "exit_code": exit_code}


def test_the_runner_accepts_a_clean_answer_and_retries_a_malformed_one() -> None:
    good = json.dumps({"pair_id": "X|1", "verdict": "same_name", "reasoning": "nfr = nfr"})
    assert review.validate(_record("X|1", "Some note.\n" + good)) == {"answer": json.loads(good)}
    assert "failure" in review.validate(_record("X|1", "no json"))
    assert "failure" in review.validate(_record("X|1", json.dumps({"pair_id": "Y|2", "verdict": "same_name",
                                                                     "reasoning": "r"})))
    silent_hook = {"type": "system", "subtype": "hook_response", "hook_name": "h", "stdout": "", "output": ""}
    assert review.validate(_record("X|1", good, extra_events=[silent_hook])) == {"answer": json.loads(good)}
    assert "failure" in review.validate(_record("X|1", json.dumps({"pair_id": "X|1", "verdict": "probably",
                                                                     "reasoning": "r"})))


@pytest.mark.parametrize(("kwargs", "message"), [
    ({"auth": "ANTHROPIC_API_KEY"}, "bill"),
    ({"model": "claude-haiku-5-5"}, "served model"),
    ({"tools": ["WebSearch"]}, "tools offered"),
    ({"extra_events": [{"type": "system", "subtype": "hook_response", "stdout": "x"}]}, "hook output"),
    ({"extra_events": [{"type": "assistant", "message": {"content": [{"type": "tool_use"}]}}]}, "used a tool"),
])
def test_the_runner_stops_on_billing_another_model_a_tool_or_a_hook(kwargs, message) -> None:
    good = json.dumps({"pair_id": "X|1", "verdict": "same_name", "reasoning": "r"})
    with pytest.raises(review.ProtocolFailure, match=message):
        review.validate(_record("X|1", good, **kwargs))


def test_the_resolver_reads_linked_spellings_as_labels_of_her_name(tmp_path: Path) -> None:
    decisions = tmp_path / "decisions.jsonl"
    decisions.write_text("".join(json.dumps(d) + "\n" for d in [
        {"pair_id": "Ahmes-Nefertiry|600465", "tla_id": "600465", "dh_target_ids": ["dodson_hilton:Ahmes-Nefertiry"],
         "verdict": "same_name"},
        {"pair_id": "Bakmut|710920", "tla_id": "710920", "dh_target_ids": ["dodson_hilton:Bakmut"],
         "verdict": "different_name"},
    ]), encoding="utf-8")
    linked = tl.linked_spellings(decisions)
    assert linked == {"dodson_hilton:Ahmes-Nefertiry": ("Jꜥḥ-ms.w-nfr.t-jr.j", "Ahmes-Nefertari", "Ahmose-Nofretari")}
    index = rw.build_index(rw.load_royal_women(), KINGS, linked_spellings=linked)
    found = rw.resolve_royal_woman(index, "Ahmose-Nofretari", record_king_ids=set(), record_dynasty=None)
    assert (found["status"], found["resolution_method"], found["target_ids"]) == (
        "resolved", "raw_exact", ["dodson_hilton:Ahmes-Nefertiry"])
    with pytest.raises(ValueError, match="not D&H women"):
        rw.build_index(rw.load_royal_women(), KINGS, linked_spellings={"dodson_hilton:Nobody": ("X",)})


def test_the_prompts_are_the_audited_ones() -> None:
    import hashlib
    audit = (tl.LINKS_DIR / "prompt-audit.md").read_text(encoding="utf-8")
    for name in ("system-v1.txt", "reviewer-v1.txt", "reconciler-v1.txt"):
        digest = hashlib.sha256((review.PROMPTS / name).read_bytes()).hexdigest()
        assert f"`{name}`: `{digest}`" in audit, name


# --- The committed run: its calls and its decisions -----------------------------------------

def _stored_calls() -> dict[str, list[dict]]:
    return {role: [json.loads(p.read_text(encoding="utf-8")) for p in sorted((review.RUNS / role).glob("*.json"))]
            for role in ("A", "B", "reconciler")}


def test_every_stored_call_passes_the_protocol_and_states_its_reasoning() -> None:
    calls = _stored_calls()
    assert {role: len(records) for role, records in calls.items()} == {"A": 124, "B": 124, "reconciler": 2}
    for role, records in calls.items():
        for record in records:
            checked = review.validate(record)  # raises on billed auth, another model, a tool or a hook
            assert "answer" in checked, (role, record["pair_id"], checked)
            assert checked["answer"]["reasoning"].strip()
            assert record["requested_model"] == review.MODEL_ALIAS and record["role"] == (
                "reconciler" if role == "reconciler" else "reviewer")


def test_the_committed_decisions_are_rebuilt_from_the_stored_calls() -> None:
    data = review.inputs()
    committed = [json.loads(line) for line in review.DECISIONS.read_text(encoding="utf-8").splitlines()]
    assert committed == [json.loads(json.dumps(d, sort_keys=True)) for d in review.decide(data)]
    assert collections.Counter((d["tier"], d["verdict"], d["basis"]) for d in committed) == {
        ("raw_exact", "same_name", "rule:raw_exact"): 34,
        ("committed_normalized", "same_name", "rule:committed_normalized"): 9,
        ("weak_sign_skeleton", "same_name", "agreement"): 70,
        ("weak_sign_skeleton", "different_name", "agreement"): 50,
        ("weak_sign_skeleton", "different_name", "reconciler"): 2}
    assert [p.pair_id for p in review.disputed(data)] == [d["pair_id"] for d in committed if d["basis"] == "reconciler"]


def test_calls_stored_for_pairs_that_are_no_longer_candidates_are_the_withheld_tntmn_pairs() -> None:
    # The run's candidates withheld hntt, nbt and nfr; the resolver's rule (`withheld_keys`)
    # later withheld tntmn too. The two pairs' calls stay on disk (Rule 13) and decide nothing.
    data = review.inputs()
    current = {review.file_id(p.pair_id) for p in review.review_pairs(data)}
    for role in ("A", "B"):
        orphans = sorted({json.loads(p.read_text(encoding="utf-8"))["pair_id"]
                          for p in (review.RUNS / role).glob("*.json") if p.name.split(".")[0] not in current})
        assert orphans == ["Tentamun|708230", "Tintamun|708230"], role


def test_the_links_add_spellings_without_new_collisions_or_unwithheld_keys(women) -> None:
    linked = tl.linked_spellings()
    assert (len(linked), sum(map(len, linked.values()))) == (110, 304)
    before = rw.build_index(women, KINGS)
    after = rw.build_index(women, KINGS, linked_spellings=linked)
    assert rw.different_spellings(after).keys() == rw.different_spellings(before).keys() == {
        "hntt", "nbt", "nfr", "nfrsbk", "tntmn"}
    assert rw.new_weak_sign_collisions(after) == rw.new_weak_sign_collisions(before)
