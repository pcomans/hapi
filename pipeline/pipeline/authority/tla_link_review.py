"""Model review of the weak-sign-only spelling links (`tla_links.candidate_pairs`).

Each pair meeting only on the weak-sign key goes to two independent reviewers (A, B). Their
agreed verdict decides it; a disagreement goes to a reconciler, whose verdict decides it.
Every call is Claude Code, headless, on the subscription (`claude -p`, no API key), with no
tools: the two records in the prompt are the whole evidence. Every call is stored, complete,
as its stream-json event log with the exact command, system prompt and user content
(Constitutional Rule 13: the record is re-read, never re-run). The prompts are
`sources/tla-2018-names/links/prompts/`, leak-audited before use (Rule 14).

    cd pipeline && uv run python -m pipeline.authority.tla_link_review review --label A
    cd pipeline && uv run python -m pipeline.authority.tla_link_review review --label B
    cd pipeline && uv run python -m pipeline.authority.tla_link_review reconcile
    cd pipeline && uv run python -m pipeline.authority.tla_link_review decide
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import tempfile
from pathlib import Path

from . import royal_women as rw
from . import tla_links as tl

MODEL_ALIAS = "sonnet"
SERVED_MODEL = "claude-sonnet-5-5"
EFFORT = "high"
MAX_ATTEMPTS = 3
VERDICTS = ("same_name", "different_name", "insufficient_evidence")
PROMPTS = tl.LINKS_DIR / "prompts"
RUNS = tl.LINKS_DIR / "runs"
DECISIONS = tl.LINKS_DIR / "decisions.jsonl"

class ProtocolFailure(RuntimeError):
    """A call that must stop the run (billed auth, another model, a tool or hook)."""


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_id(pair_id: str) -> str:
    return sha256(pair_id)[:16]


def dh_record(pair: tl.Pair) -> str:
    """Only the D&H name: who bore it, D&H's letters and alternative names are no evidence
    about its spelling (prompt audit, Rule 14)."""
    return f"Name: {pair.dh_name}"


def tla_record(row: dict) -> str:
    translations = "; ".join(f"{t['lang']}: {json.dumps(t.get('value', ''), ensure_ascii=False)}"
                             for t in row["translations"])
    return (f"Lemma: {row['tla_id']} ({row['subtype']})\nTransliteration: {row['transliteration']}\n"
            f"Translations: {translations}")


def compose(template: str, pair: tl.Pair, inputs: dict, reviews: str = "") -> str:
    return template.format(dh_record=dh_record(pair),
                           tla_record=tla_record(inputs["tla"][pair.tla_id]), pair_id=pair.pair_id, reviews=reviews)


def command(system_prompt: str, user_content: str) -> list[str]:
    return ["claude", "-p", user_content, "--model", MODEL_ALIAS, "--effort", EFFORT,
            "--thinking-display", "summarized", "--system-prompt", system_prompt, "--tools", "",
            "--mcp-config", json.dumps({"mcpServers": {}}), "--strict-mcp-config",
            "--output-format", "stream-json", "--verbose", "--no-session-persistence"]


def call(pair: tl.Pair, role: str, system_prompt: str, user_content: str) -> dict:
    argv = command(system_prompt, user_content)
    record = {"pair_id": pair.pair_id, "role": role, "requested_model": MODEL_ALIAS,
              "parameters": {"effort": EFFORT, "thinking_display": "summarized", "tools": []},
              "command": argv[:2] + ["<user_content>"] + argv[3:], "system_prompt": system_prompt,
              "user_content": user_content, "user_content_sha256": sha256(user_content)}
    env = {key: value for key, value in os.environ.items() if key != "ANTHROPIC_API_KEY"}
    with tempfile.TemporaryDirectory(prefix="hapi-tla-link-") as cwd:
        proc = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True, cwd=cwd, env=env)
    record["exit_code"] = proc.returncode
    record["stderr"] = proc.stderr
    record["events"] = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    return record


def validate(record: dict) -> dict:
    """The call's verdict, or a `failure` (retried). Billed auth, another model, a tool or
    hook output raises: the run stops."""
    events = record["events"]
    init = next(e for e in events if e.get("type") == "system" and e.get("subtype") == "init")
    if init.get("apiKeySource") != "none":
        raise ProtocolFailure(f"API-key auth would bill this call: {init.get('apiKeySource')!r}")
    if init.get("model") != SERVED_MODEL:
        raise ProtocolFailure(f"served model {init.get('model')!r}, not {SERVED_MODEL!r}")
    if init.get("tools"):
        raise ProtocolFailure(f"tools offered: {init.get('tools')}")
    # User-level hooks still run in a `claude -p` session; only one with output reaches the model.
    hooks = [e.get("hook_name") for e in events if e.get("type") == "system" and e.get("subtype") == "hook_response"
             and (e.get("output") or e.get("stdout") or e.get("stderr"))]
    if hooks:
        raise ProtocolFailure(f"hook output reached the session: {hooks}")
    if any(c.get("type") == "tool_use" for e in events if e.get("type") == "assistant"
           for c in e["message"]["content"]):
        raise ProtocolFailure("the model used a tool")
    final = events[-1]
    if record["exit_code"] != 0 or final.get("type") != "result" or final.get("subtype") != "success" \
            or final.get("is_error"):
        if "limit" in json.dumps(final).lower():
            raise ProtocolFailure(f"Claude Code session limit: {final.get('result')!r}")
        return {"failure": f"call did not end in a successful result: {final.get('subtype')!r}"}
    text = final["result"].strip()
    start = text.rfind("\n{") + 1 if not text.startswith("{") else 0
    try:
        answer = json.loads(text[start:])
    except json.JSONDecodeError:
        return {"failure": "answer is not a JSON object at the end of the message"}
    if set(answer) != {"pair_id", "verdict", "reasoning"}:
        return {"failure": f"answer keys {sorted(answer)}"}
    if answer["pair_id"] != record["pair_id"]:
        return {"failure": "answer does not echo the pair id"}
    if answer["verdict"] not in VERDICTS or not answer["reasoning"].strip():
        return {"failure": f"invalid verdict {answer['verdict']!r} or empty reasoning"}
    return {"answer": answer}


def inputs() -> dict:
    women = {w.target_id: w for w in rw.load_royal_women()}
    rows = [json.loads(line) for line in rw.DODSON_HILTON.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {"women": women, "dh_rows": {(r["dh_id"], r["sub_period"]): r for r in rows},
            "tla": {r["tla_id"]: r for r in tl.tla_rows()},
            "system": (PROMPTS / "system-v1.txt").read_text(encoding="utf-8"),
            "reviewer": (PROMPTS / "reviewer-v1.txt").read_text(encoding="utf-8"),
            "reconciler": (PROMPTS / "reconciler-v1.txt").read_text(encoding="utf-8")}


def review_pairs(data: dict) -> list[tl.Pair]:
    pairs = tl.candidate_pairs(list(data["women"].values()), list(data["tla"].values()))
    return [p for p in pairs if p.tier == tl.BY_REVIEW]


def stored(role_dir: Path, pair: tl.Pair) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(role_dir.glob(f"{file_id(pair.pair_id)}.attempt-*.json"))]


def valid_answer(records: list[dict], expected: tuple[str, str] | None = None) -> dict | None:
    """The one valid answer among a pair's stored calls. With `expected` (system prompt, user
    content), the valid call must have been composed from exactly those (Rule 13/14: a
    decision stands only on the audited prompt it was asked)."""
    valid = [r for r in records if "answer" in r["result"]]
    if expected is not None and any((r["system_prompt"], r["user_content"]) != expected for r in valid):
        raise ValueError(f"{records[0]['pair_id']}: a stored call was not composed from the current prompts")
    answers = [r["result"]["answer"] for r in valid]
    if len(answers) > 1:
        raise ValueError(f"{records[0]['pair_id']}: more than one valid call")
    return answers[0] if answers else None


def run_role(data: dict, pairs: list[tl.Pair], role: str, role_dir: Path, compose_for) -> None:
    role_dir.mkdir(parents=True, exist_ok=True)
    for pair in pairs:
        records = stored(role_dir, pair)
        while valid_answer(records) is None:
            if len(records) >= MAX_ATTEMPTS:
                raise ProtocolFailure(f"{pair.pair_id}: no valid answer in {MAX_ATTEMPTS} attempts")
            user = compose_for(pair)
            record = call(pair, role, data["system"], user)
            path = role_dir / f"{file_id(pair.pair_id)}.attempt-{len(records) + 1}.json"
            # Stored before it is judged: a call that stops the run is kept too (Rule 13).
            try:
                record["result"] = validate(record)
            except ProtocolFailure as stop:
                record["result"] = {"stopped": str(stop)}
                path.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
                raise
            path.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            records.append(record)
            print(f"{role} {pair.pair_id}: {record['result'].get('answer', {}).get('verdict') or record['result']['failure']}",
                  flush=True)


def disputed(data: dict) -> list[tl.Pair]:
    out = []
    for pair in review_pairs(data):
        a, b = (valid_answer(stored(RUNS / label, pair)) for label in ("A", "B"))
        if a is None or b is None:
            raise ValueError(f"{pair.pair_id}: reviewers A and B must both have decided first")
        if a["verdict"] != b["verdict"]:
            out.append(pair)
    return out


def compose_reconciler(data: dict, pair: tl.Pair) -> str:
    reviews = [valid_answer(stored(RUNS / label, pair)) for label in ("A", "B")]
    # Opaque labels in a seeded order, so the reconciler cannot tell which reviewer is which.
    random.Random(sha256(pair.pair_id)).shuffle(reviews)
    text = "\n\n".join(f"Review {label}:\n{json.dumps({k: r[k] for k in ('verdict', 'reasoning')}, ensure_ascii=False)}"
                       for label, r in zip(("X", "Y"), reviews))
    return compose(data["reconciler"], pair, data, text)


def decide(data: dict) -> list[dict]:
    """One decision per pair: by rule (exact or claim-graph keys), by agreement, or by the
    reconciler."""
    out = []
    for pair in tl.candidate_pairs(list(data["women"].values()), list(data["tla"].values())):
        if pair.tier in tl.BY_RULE:
            verdict, basis = "same_name", f"rule:{pair.tier}"
        else:
            expected = (data["system"], compose(data["reviewer"], pair, data))
            a, b = (valid_answer(stored(RUNS / label, pair), expected) for label in ("A", "B"))
            if a["verdict"] == b["verdict"]:
                verdict, basis = a["verdict"], "agreement"
            else:
                r = valid_answer(stored(RUNS / "reconciler", pair),
                                 (data["system"], compose_reconciler(data, pair)))
                if r is None:
                    raise ValueError(f"{pair.pair_id}: disputed and not reconciled")
                verdict, basis = r["verdict"], "reconciler"
        out.append({"pair_id": pair.pair_id, "dh_name": pair.dh_name, "tla_id": pair.tla_id, "tier": pair.tier,
                    "dh_target_ids": list(pair.dh_target_ids), "verdict": verdict, "basis": basis})
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="step", required=True)
    review = sub.add_parser("review")
    review.add_argument("--label", required=True, choices=("A", "B"))
    review.add_argument("--limit", type=int, help="only the first N pairs (a pilot)")
    sub.add_parser("reconcile")
    sub.add_parser("decide")
    args = parser.parse_args()
    data = inputs()
    if args.step == "review":
        pairs = review_pairs(data)[: args.limit]
        run_role(data, pairs, "reviewer", RUNS / args.label, lambda p: compose(data["reviewer"], p, data))
    elif args.step == "reconcile":
        run_role(data, disputed(data), "reconciler", RUNS / "reconciler", lambda p: compose_reconciler(data, p))
    else:
        DECISIONS.write_text("".join(json.dumps(d, ensure_ascii=False, sort_keys=True) + "\n" for d in decide(data)),
                             encoding="utf-8")
        print(f"wrote {DECISIONS}")


if __name__ == "__main__":
    main()
