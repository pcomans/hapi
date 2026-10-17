#!/usr/bin/env python3
"""Per-museum ruler test: score the frozen consensus and apply the decision rule (`decision-rule.md`).

Reads the two frozen consensus files (link and miss), each rebuilt here from the stored calls
(`review_protocol.verify_consensus`), and the private answer key, and writes:
- a public score (counts only): per museum, the links confirmed, wrong and unconfirmed (units and
  records), the decoys caught and missed, the miss counts, and each museum's outcome;
- a private fix list (it names museum texts): every miss unit with its outcome and the rulers
  the deciding calls named.

    runtime/.venv/bin/python docs/evaluations/ruler-per-museum-2026-10-17/scripts/score.py \\
        --repo-root . --review <private review dir> --records <private records dir> \\
        --public-out docs/evaluations/ruler-per-museum-2026-10-17/results/score.json \\
        --private-out <private records dir>/fix-list.json
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

EVALUATION_ROOT = Path("docs/evaluations/ruler-per-museum-2026-10-17")
DIGEST = EVALUATION_ROOT / "results/review-population-digest.json"
SCHEMA_VERSION = "hapi-ruler-per-museum-score/1"
# Calibration (decision-rule.md): the review must reject the decoys. More than this share of
# decoys not judged different_identity makes the result INCONCLUSIVE.
MAX_MISSED_DECOY_SHARE = (1, 5)
# ... and fewer than this many counted decoys (those whose twin was confirmed) makes it
# INCONCLUSIVE too (owner, 2026-10-17).
MIN_COUNTED_DECOYS = 15


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    if path.exists():
        raise ValueError(f"{path} exists; frozen files are never overwritten")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def load_protocol(repo_root: Path):
    path = repo_root / EVALUATION_ROOT / "scripts/review_protocol.py"
    spec = importlib.util.spec_from_file_location("_ruler_per_museum_score_protocol", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def at_most(count: int, total: int, share: tuple[int, int]) -> bool:
    """count / total <= share, in integers."""
    return count * share[1] <= share[0] * total


def museum_outcomes(rows: dict[str, dict], calibration_passed: bool) -> dict[str, str]:
    """Each museum's outcome (decision-rule.md): `no_decision` everywhere when the calibration
    failed; otherwise `fails` when any of its links is wrong, else `passes`. Unconfirmed links
    are reported and decide nothing (owner, 2026-10-17)."""
    out = {}
    for museum, row in sorted(rows.items()):
        if not calibration_passed:
            out[museum] = "no_decision"
        else:
            out[museum] = "fails" if row["wrong"]["units"] else "passes"
    return out


LINK_CATEGORY = {"exact_identity": "confirmed", "different_identity": "wrong", "insufficient_evidence": "unconfirmed"}
MISS_CATEGORY = {"one_ruler": "names_one_ruler", "not_one_ruler": "names_no_single_ruler",
                 "insufficient_evidence": "unconfirmed"}


def tally(key: list[dict], link_outcomes: dict[str, str], miss_outcomes: dict[str, str]) -> dict:
    """The rule's counts from the answer key and each case's consensus outcome."""
    museums: dict[str, dict] = {}
    decoys = {"caught": 0, "missed": 0, "by_outcome": collections.Counter(), "twin_not_confirmed": 0}
    # A decoy is surely wrong only if its real twin (the same unit with its own target) is right,
    # so only decoys whose twin was confirmed calibrate the review (decision-rule.md).
    twin = {case["unit_id"]: link_outcomes[case["case_id"]] for case in key if case["unit_kind"] == "link"}
    for case in key:
        side = museums.setdefault(case["museum"], {
            **{c: {"units": 0, "records": set()} for c in ("confirmed", "wrong", "unconfirmed")},
            "link_records": set(),
            "miss": {c: {"units": 0, "records": set()} for c in MISS_CATEGORY.values()},
        })
        if case["unit_kind"] == "decoy":
            if twin[case["unit_id"]] != "exact_identity":
                decoys["twin_not_confirmed"] += 1
                continue
            outcome = link_outcomes[case["case_id"]]
            decoys["by_outcome"][outcome] += 1
            decoys["caught" if outcome == "different_identity" else "missed"] += 1
        elif case["unit_kind"] == "link":
            category = LINK_CATEGORY[link_outcomes[case["case_id"]]]
            side[category]["units"] += 1
            side[category]["records"].update(case["artifact_ids"])
            side["link_records"].update(case["artifact_ids"])
        else:
            category = MISS_CATEGORY[miss_outcomes[case["case_id"]]]
            side["miss"][category]["units"] += 1
            side["miss"][category]["records"].update(case["artifact_ids"])

    def counted(cell: dict) -> dict:
        return {"units": cell["units"], "records": len(cell["records"])}

    rows = {
        museum: {
            **{c: counted(side[c]) for c in ("confirmed", "wrong", "unconfirmed")},
            "link_records": len(side["link_records"]),
            "miss": {c: counted(cell) for c, cell in side["miss"].items()},
        }
        for museum, side in sorted(museums.items())
    }
    total = decoys["caught"] + decoys["missed"]
    calibration = {"decoys": total, "caught": decoys["caught"], "missed": decoys["missed"],
                   "set_aside_twin_not_confirmed": decoys["twin_not_confirmed"],
                   "by_outcome": dict(sorted(decoys["by_outcome"].items())),
                   "max_missed_share": list(MAX_MISSED_DECOY_SHARE), "min_counted_decoys": MIN_COUNTED_DECOYS,
                   "passed": total >= MIN_COUNTED_DECOYS and at_most(decoys["missed"], total, MAX_MISSED_DECOY_SHARE)}
    return {"calibration": calibration, "museums": rows,
            "museum_outcomes": museum_outcomes(rows, calibration["passed"])}


def score(repo_root: Path, review: Path, records: Path, public_out: Path, private_out: Path) -> dict:
    protocol = load_protocol(repo_root)
    digest = read_json(repo_root / DIGEST)
    for name, sha in digest["output_sha256"].items():
        if sha256_path(review / name) != sha:
            raise ValueError(f"{name} is not the committed population's")
    for name, binding in [*digest["review_protocol"]["prompts"].items(), *digest["review_protocol"]["schemas"].items(),
                          *((k, v) for k, v in digest["review_protocol"].items() if "path" in v)]:
        if sha256_path(repo_root / binding["path"]) != binding["sha256"]:
            raise ValueError(f"the review protocol changed since the population was built: {binding['path']}")
    consensus = {
        stage: protocol.verify_consensus(stage, records / stage / "consensus.json", review / f"{stage}-queue.json",
                                         records / stage)
        for stage in protocol.STAGE_FIELDS
    }
    outcomes = {stage: {d["case_id"]: d[protocol.STAGE_FIELDS[stage][0]] for d in c["decisions"]}
                for stage, c in consensus.items()}
    key = read_json(review / "private-answer-key.json")["cases"]
    result = tally(key, outcomes["link"], outcomes["miss"])
    result["page_opens"] = {stage: page_opens(protocol, stage, review, records / stage, key) for stage in consensus}
    unanswered = {stage: dict(sorted(collections.Counter(
        r["method"] for d in c["decisions"] for r in d["field_resolutions"].values()
        if r["method"] in ("no_valid_review", "no_valid_reconciliation")).items())) for stage, c in consensus.items()}
    public = {
        "schema_version": SCHEMA_VERSION,
        "cases_without_an_answer": unanswered,
        # Every stored call, attempt and consensus by hash, and the set-aside ledger: the records
        # this score was made from (2026-10-16's `real-review-records.json`).
        "records_sha256": {path.relative_to(records).as_posix(): sha256_path(path)
                           for path in sorted(records.rglob("*.json")) if path.parent != records},
        "set_asides_sha256": sha256_path(protocol.SET_ASIDES_PATH),
        "scorer_sha256": sha256_path(Path(__file__).resolve()),
        "population_digest_sha256": sha256_path(repo_root / DIGEST),
        "consensus_sha256": {stage: sha256_path(records / stage / "consensus.json") for stage in consensus},
        **result,
    }
    fix_list = []
    by_case = {d["case_id"]: d for d in consensus["miss"]["decisions"]}
    queue = {c["case_id"]: c for c in read_json(review / "miss-queue.json")["cases"]}
    reconcile = {c["case_id"]: c for c in protocol.reconciliation_queue(
        "miss", read_json(review / "miss-queue.json"), records / "miss")["cases"]}
    for case in sorted((c for c in key if c["unit_kind"] == "miss"), key=lambda c: (c["museum"], c["mention_text"])):
        decision = by_case[case["case_id"]]
        fix_list.append({
            "museum": case["museum"], "mention_text": case["mention_text"], "case_id": case["case_id"],
            "records": len(case["artifact_ids"]), "outcome": decision["names_one_ruler"],
            "rulers_named": rulers_named(protocol, records / "miss", queue[case["case_id"]],
                                         reconcile.get(case["case_id"]), decision),
        })
    write_json(public_out, public)
    write_json(private_out, {"schema_version": SCHEMA_VERSION, "warning": "private: museum text", "misses": fix_list})
    return public


def page_opens(protocol, stage: str, review: Path, records: Path, key: list[dict]) -> dict:
    """What the deciding calls (both reviews of every case, and each reconciler call that settled
    one) could read: pages opened and loaded, by museum and unit kind, and the calls that loaded no
    page. Reported, not gated: a decoy shows the same records as its link, so a page that will not
    load hampers both alike."""
    kind = {c["case_id"]: (c["museum"], c["unit_kind"]) for c in key}
    queue = read_json(review / f"{stage}-queue.json")
    calls = [(case_id, review[1]) for case_id, by_label in protocol.reviewer_decisions(stage, queue, records).items()
             for review in by_label.values() if review is not None]
    role = protocol.ROLES[f"{stage}_reconciler"]
    inputs = protocol.role_inputs(role)
    for case in protocol.reconciliation_queue(stage, queue, records)["cases"]:
        decided = protocol.decided_record(records / "reconciler", case, role, inputs)
        if decided is not None:
            calls.append((case["case_id"], decided[1]))
    out: dict[str, dict] = {}
    without = 0
    for case_id, record in calls:
        museum, unit_kind = kind[case_id]
        cell = out.setdefault(f"{museum}/{unit_kind}", {"calls": 0, "opened": 0, "loaded": 0})
        opens = record["page_opens"]
        cell["calls"] += 1
        cell["opened"] += len(opens)
        cell["loaded"] += sum(o["loaded"] for o in opens)
        without += not any(o["loaded"] for o in opens)
    return {"deciding_calls": len(calls), "calls_without_a_loaded_page": without, "by_museum_and_kind": dict(sorted(out.items()))}


def rulers_named(protocol, records: Path, case: dict, reconcile_case: dict | None, decision: dict) -> list[str]:
    """The rulers the deciding calls named (`review_protocol.decided_record`): both reviewers'
    when they agreed, the reconciler's when it settled the question, none when no call gave an
    answer."""
    method = decision["field_resolutions"]["names_one_ruler"]["method"]
    if method in ("no_valid_review", "no_valid_reconciliation"):
        return []
    if method == "agreement":
        role = protocol.ROLES["miss_reviewer"]
        inputs = protocol.role_inputs(role)
        return [protocol.decided_record(records / f"reviewer-{label}", case, role, inputs)[1]["decision"]["ruler"]
                for label in protocol.REVIEWERS]
    role = protocol.ROLES["miss_reconciler"]
    _, stored = protocol.decided_record(records / "reconciler", reconcile_case, role, protocol.role_inputs(role))
    return [stored["decision"]["resolutions"]["names_one_ruler"]["ruler"]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True, help="private dir holding the queues and answer key")
    parser.add_argument("--records", type=Path, required=True, help="private dir holding link/ and miss/")
    parser.add_argument("--public-out", type=Path, required=True)
    parser.add_argument("--private-out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(score(args.repo_root.resolve(), args.review, args.records, args.public_out, args.private_out),
                     indent=1))


if __name__ == "__main__":
    main()
