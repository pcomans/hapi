#!/usr/bin/env python3
"""A check of the one Met-Brooklyn ruler connection no review has seen (#338 step 3).

#376 found the pipeline's Met-Brooklyn ruler population to be #361's reviewed one plus one shared
target, D&H's Ahmes B (#369's fix), which joins brooklyn-3634, met-566763 and met-547683. Those
three records come from #361's case-016 (its deciding e: the plain-text "Ahmose" node). Owner,
2026-10-16: re-review it now, as a check only. Its outcome says whether this link is right; it
is not evidence for the scope's qualification, because #369's fix was found on this very case.

This builds the review case with #361's own protocol and code (`ruler-reregistration-2026-10-15/
scripts/build_review_queue.py`), run by #361's runner and prompts unchanged:

* `stage-1`: one Stage 1 unit, the museum-side evidence of the Ahmes B node (the pipeline's
  authority links on the frozen corpus), no target shown;
* `stage-2`: once Stage 1's consensus is frozen, the released Stage 2 case: Ahmes B as the
  proposed target, with the metadata #361 released for a royal woman.

    uv run python docs/evaluations/ahmes-b-recheck-2026-10-16/scripts/build_queues.py stage-1 \\
        --archive <corpus archive> --out <private dir>/stage-1/queue.json
    uv run python .../build_queues.py stage-2 --stage-1-queue <...> --consensus <...> --template <...> --out <...>
    uv run python .../build_queues.py verify --private <private dir>
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import re
import sys
import tarfile
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "pipeline"))
from pipeline.authority import royal_women  # noqa: E402
from pipeline.enrich import link_files  # noqa: E402

EVAL_361 = REPO / "docs/evaluations/ruler-reregistration-2026-10-15"
ARCHIVE_SHA256 = "f4aabc2fc03b3ee0b5965bb9b27129e0ac482dae086c6124dd0d73d70276cc5b"
TARGET = "dodson_hilton:Ahmes B"
PAIR = ("met", "brooklyn")
# Opaque, as #361's are: the case id reaches the model.
CASE_ID = "review-unit-001"
# #361's Stage 1 queue header and Stage 2 question, as its builder writes them.
STAGE_1_HEADER = {
    "schema_version": "hapi-authority-independent-control-stage-1-review/5",
    "task": "Judge each independently shuffled museum-side census unit without consulting a proposed canonical target.",
}


def builder():
    spec = importlib.util.spec_from_file_location("_361_build_review_queue", EVAL_361 / "scripts/build_review_queue.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_corpus(archive: Path) -> tuple[list[dict], dict]:
    if sha256_path(archive) != ARCHIVE_SHA256:
        raise ValueError(f"{archive} is not the frozen corpus archive")
    with tarfile.open(archive, "r:gz") as bundle:
        def rows(name: str) -> list[dict]:
            data = bundle.extractfile(f"hapi-museum-corpus-2026-08-27/data/{name}").read()
            return [json.loads(line) for line in gzip.GzipFile(fileobj=io.BytesIO(data)).read().splitlines()]
        canonical = rows("artifacts.ndjson.gz")
        raw = {m: {str(r["object_id"]): r["data"] for r in rows(f"raw_{m}.ndjson.gz")} for m in ("met", "brooklyn", "harvard")}
    return canonical, raw


def stage_1(archive: Path, template: dict) -> tuple[dict, dict]:
    """The Stage 1 unit of the Ahmes B node, built as #361 builds one from its arm runs."""
    b = builder()
    canonical, raw = load_corpus(archive)
    with tempfile.TemporaryDirectory() as root:
        manifest = link_files.write_run(Path(root), lambda: (canonical, raw))
        run = Path(root) / manifest["run_id"]
        mentions = {m["mention_id"]: m for m in link_files.read_rows(run / "mentions.ndjson.gz")}
        literal_rows = {r["mention_id"]: r for r in link_files.read_rows(run / "resolutions-literal.ndjson.gz")}
        links = [l for l in link_files.read_rows(run / "links-authority.ndjson.gz")
                 if l["entity_type"] == "ruler" and l["target_id"] == TARGET]
    sides = {museum: sorted({m for l in links if l["museum"] == museum for m in l["mention_ids"]}) for museum in PAIR}
    if not all(sides.values()):
        raise ValueError(f"{TARGET} is not shared by {PAIR} in this run")
    node = b.arm_node(TARGET, sides, mentions)
    binding = b.review_unit_binding(list(PAIR), "ruler", node)
    source_urls = {row["id"]: row["source_url"] for row in canonical}
    evidence = b.review_unit_evidence(binding, mentions, literal_rows, source_urls)
    case = {
        "case_id": CASE_ID,
        "evidence_sha256": b.canonical_sha256(evidence),
        **evidence,
        "questions": template["cases"][0]["questions"],
    }
    queue = {**STAGE_1_HEADER, "instructions": template["instructions"], "review_protocol": template["review_protocol"],
             "cases": [case]}
    # Stage 1 is target-blind (Rule 14): an opaque case id, and nothing naming the target.
    if not re.fullmatch(r"review-unit-\d{3}", case["case_id"]):
        raise ValueError(f"case id {case['case_id']!r} is not opaque")
    text = json.dumps(queue, ensure_ascii=False)
    for token in (TARGET, "Ahmes B", "Ahmes", "dodson_hilton"):
        if token in text:
            raise ValueError(f"the Stage 1 queue names the target ({token!r})")
    private = {"case_id": CASE_ID, "target_id": TARGET, "run_id": manifest["run_id"],
               "artifact_ids_by_side": node["artifact_ids_by_side"], "mention_ids_by_side": node["mention_ids_by_side"]}
    return queue, private


def protocol():
    spec = importlib.util.spec_from_file_location("_361_review_protocol", EVAL_361 / "scripts/review_protocol.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def stage_2(stage_1_queue: Path, consensus: Path, template: dict) -> dict:
    """The released Stage 2 case: Ahmes B as the proposed target, with the metadata #361 released
    for a royal woman (label, dynasties, family names, representation, source). Released only
    when the Stage 1 consensus is the one the stored Stage 1 calls make (#361's
    `verify_consensus`), so the target cannot be shown before Stage 1 is frozen."""
    protocol().verify_consensus("1", consensus, stage_1_queue, stage_1_queue.parent)
    b = builder()
    queue_1 = json.loads(stage_1_queue.read_text(encoding="utf-8"))
    (case_1,) = queue_1["cases"]
    woman = {w.target_id: w for w in royal_women.load_royal_women()}[TARGET]
    custodian_case = {
        "case_id": CASE_ID,
        "evidence_sha256": case_1["evidence_sha256"],
        "proposed_target": {
            "target_id": TARGET, "target_label": woman.label,
            "target_metadata": {"label": woman.label, "entity_type": "ruler",
                                "representation": "dodson_hilton_royal_woman",
                                "source": "Dodson & Hilton, The Complete Royal Families of Ancient Egypt (2004)",
                                "dynasties": list(woman.dynasties), "family_names": list(woman.family_names)},
        },
        "question": template["cases"][0]["question"],
        "allowed_outcomes": template["cases"][0]["allowed_outcomes"],
    }
    return {
        "schema_version": template["schema_version"],
        "task": template["task"],
        "review_protocol": template["review_protocol"],
        "stage_1_queue_sha256": sha256_path(stage_1_queue),
        "frozen_stage_1_consensus_sha256": sha256_path(consensus),
        "stage_2_custodian_sha256": None,
        "cases": [b.released_stage_2_case(custodian_case, case_1)],
    }


def verify(private: Path, check_path: Path) -> None:
    """With the private records: both consensus files are what the stored calls make (#361's
    `verify_consensus`), every stored call and file has the SHA-256 `check.json` records, and
    `check.json`'s outcomes are the consensus decisions."""
    rp = protocol()
    check = json.loads(check_path.read_text(encoding="utf-8"))
    for stage, recorded in check["stages"].items():
        d = private / f"stage-{stage}"
        consensus = rp.verify_consensus(stage, d / "consensus.json", d / "queue.json", d)
        if (sha256_path(d / "queue.json"), sha256_path(d / "consensus.json")) != (recorded["queue_sha256"], recorded["consensus_sha256"]):
            raise ValueError(f"stage {stage}: queue or consensus is not the one check.json records")
        calls = {str(p.relative_to(d)): sha256_path(p) for p in sorted(d.rglob("*.attempt-*.json"))}
        if calls != recorded["stored_calls_sha256"]:
            raise ValueError(f"stage {stage}: stored calls differ from check.json")
        (decision,) = consensus["decisions"]
        outcome = {k: v for k, v in decision.items() if k not in ("case_id", "evidence_sha256", "field_resolutions")}
        if outcome != recorded["outcome"]:
            raise ValueError(f"stage {stage}: check.json's outcome is not the consensus")
    print("verified: consensus rebuilt from the stored calls, hashes and outcomes match check.json")


def write_new(path: Path, value: dict) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    one = commands.add_parser("stage-1")
    one.add_argument("--archive", type=Path, required=True)
    one.add_argument("--template", type=Path, required=True, help="#361's private Stage 1 queue (header and questions)")
    one.add_argument("--out", type=Path, required=True)
    two = commands.add_parser("stage-2")
    two.add_argument("--stage-1-queue", type=Path, required=True)
    two.add_argument("--consensus", type=Path, required=True)
    two.add_argument("--template", type=Path, required=True, help="#361's private released Stage 2 queue")
    two.add_argument("--out", type=Path, required=True)
    check = commands.add_parser("verify")
    check.add_argument("--private", type=Path, required=True, help="the private records directory")
    check.add_argument("--check", type=Path, default=Path(__file__).resolve().parents[1] / "results/check.json")
    args = parser.parse_args()
    if args.command == "verify":
        verify(args.private, args.check)
        return
    template = json.loads(args.template.read_text(encoding="utf-8"))
    if args.command == "stage-1":
        queue, private = stage_1(args.archive, template)
        write_new(args.out, queue)
        write_new(args.out.with_name("private-binding.json"), private)
    else:
        write_new(args.out, stage_2(args.stage_1_queue, args.consensus, template))


if __name__ == "__main__":
    main()
