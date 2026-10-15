"""Model review of the spelling links that no rule decides (`tla_links.units`), protocol v2.

Each review unit is one D&H name with its candidate TLA names under opaque labels in a
seeded order. Two independent reviewers (A, B), on two different models, each list every
candidate that is the same name, or none. Their agreed list decides the unit. A disagreement goes to a reconciler,
whose list decides it. Every call is Claude Code, headless, on the subscription
(`claude -p`, no API key), with no tools: the records in the prompt are the whole evidence.
Every call is stored complete, as its stream-json event log with the exact command, system
prompt and user content (Constitutional Rule 13: the record is re-read, never re-run), and a
decision is re-derived from that stored log, never from a summary of it. The prompts are
`sources/tla-2018-names/links/prompts/`, leak-audited before use (Rule 14). Protocol v1,
which judged pairs by a consonant procedure and linked names that differ, is withdrawn
(`links/v1-withdrawn/`).

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
import re
import subprocess
import tempfile
from pathlib import Path

from . import royal_women as rw
from . import tla_links as tl

# Role -> (model alias requested, model the session must serve).
MODELS = {"A": ("sonnet", "claude-sonnet-5-5"), "B": ("opus", "claude-opus-5-5"),
          "reconciler": ("opus", "claude-opus-5-5")}
EFFORT = "high"
# Format retries only: a call whose answer cannot be read is stored and retried; the first valid
# answer counts.
MAX_ATTEMPTS = 3
FENCED_ANSWER = re.compile(r"```(?:json)?\s*(\{.*\})\s*```$", re.S)
PROMPTS = tl.LINKS_DIR / "prompts"
RUNS = tl.LINKS_DIR / "runs"
DECISIONS = tl.LINKS_DIR / "decisions.jsonl"
SHUFFLE_SALT = "tla-links-v2/"
RULES = (PROMPTS / "rules-v2.txt").read_text(encoding="utf-8").strip()


class ProtocolFailure(RuntimeError):
    """A call that must stop the run (billed auth, another model, a tool or hook, an error)."""


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_id(unit_id: str) -> str:
    return sha256(unit_id)[:16]


def labelled(unit: tl.Unit) -> dict[str, tl.Option]:
    """The unit's options under opaque labels C1, C2, … in an order seeded by the D&H name,
    so that neither label nor position carries the source order (Rule 14)."""
    options = list(unit.options)
    random.Random(sha256(SHUFFLE_SALT + unit.dh_name)).shuffle(options)
    return {f"C{i}": option for i, option in enumerate(options, 1)}


LANGUAGES = {"de": "German", "en": "English"}
def spellings(row: dict) -> str:
    """A lemma's modern spellings as the prompt shows them: German, then English, each value
    read by `tla_links.spellings_of`, and "(none)" for a language without one. No id: a lemma id
    says nothing of the name and could proxy its source (prompt audit v2, round 1)."""
    out = []
    for lang, language in LANGUAGES.items():
        values = [s for t in row["translations"] if t["lang"] == lang for s in tl.spellings_of(t.get("value"))]
        out.append(f"{language}: {'; '.join(values) if values else '(none)'}")
    return " | ".join(out)


def compose(template: str, unit: tl.Unit, tla: dict, reviews: str = "") -> str:
    labels = labelled(unit)
    candidates = "\n\n".join(
        f"Candidate {label}: {tla[option.tla_ids[0]]['transliteration']}\n"
        + "\n".join(f"  Lemma {i}: {spellings(tla[t])}" for i, t in enumerate(option.tla_ids, 1))
        for label, option in labels.items())
    return template.format(dh_record=f"Name: {unit.dh_name}", candidates=candidates, unit_id=unit.dh_name,
                           labels=", ".join(json.dumps(c) for c in labels), rules=RULES, reviews=reviews)


def command(role: str, system_prompt: str, user_content: str) -> list[str]:
    return ["claude", "-p", user_content, "--model", MODELS[role][0], "--effort", EFFORT,
            "--thinking-display", "summarized", "--system-prompt", system_prompt, "--tools", "",
            "--mcp-config", json.dumps({"mcpServers": {}}), "--strict-mcp-config", "--disable-slash-commands",
            "--output-format", "stream-json", "--verbose", "--no-session-persistence"]


def call(unit: tl.Unit, role: str, system_prompt: str, user_content: str) -> dict:
    argv = command(role, system_prompt, user_content)
    record = {"unit_id": unit.dh_name, "role": role, "requested_model": MODELS[role][0],
              "labels": {label: option.name for label, option in labelled(unit).items()},
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
    """The call's answer, read from its stored event log, or a `failure` (retried). Billed
    auth, another model anywhere in the call, a tool, hook output or a session that ends in an
    error (a usage limit among them) raises: the run stops."""
    events = record["events"]
    inits = [e for e in events if e.get("type") == "system" and e.get("subtype") == "init"]
    if len(inits) != 1:
        raise ProtocolFailure(f"{len(inits)} init events")
    init, served = inits[0], MODELS[record["role"]][1]
    if init.get("apiKeySource") != "none":
        raise ProtocolFailure(f"API-key auth would bill this call: {init.get('apiKeySource')!r}")
    models = {init.get("model")} | {e["message"].get("model") for e in events if e.get("type") == "assistant"}
    if events[-1].get("type") == "result":
        models |= set(events[-1].get("modelUsage", {}))
    if models != {served}:
        raise ProtocolFailure(f"served models {sorted(map(str, models))}, not only {served!r}")
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
    if final.get("type") == "result" and final.get("is_error"):
        raise ProtocolFailure(f"the session ended in an error: {final.get('result')!r}")
    if record["exit_code"] != 0 or final.get("type") != "result" or final.get("subtype") != "success":
        return {"failure": f"call did not end in a successful result: {final.get('type')!r}/{final.get('subtype')!r}"}
    text = final["result"].strip()
    # v2.1: the final object may sit in one closing ```json fence, as Opus writes it.
    if fenced := FENCED_ANSWER.search(text):
        text = fenced.group(1)
    start = text.rfind("\n{") + 1 if not text.startswith("{") else 0
    try:
        answer = json.loads(text[start:])
    except json.JSONDecodeError:
        return {"failure": "answer is not a JSON object at the end of the message"}
    if not isinstance(answer, dict) or set(answer) != {"unit_id", "choices", "reasoning"}:
        return {"failure": f"answer keys {sorted(answer) if isinstance(answer, dict) else type(answer).__name__}"}
    if answer["unit_id"] != record["unit_id"]:
        return {"failure": "answer does not echo the unit id"}
    choices = answer["choices"]
    if not isinstance(choices, list) or not all(isinstance(c, str) for c in choices) \
            or len(set(choices)) != len(choices) or not set(choices) <= set(record["labels"]):
        return {"failure": f"choices {choices!r} are not distinct labels"}
    if not isinstance(answer["reasoning"], str) or not answer["reasoning"].strip():
        return {"failure": "empty reasoning"}
    return {"answer": answer}


def inputs() -> dict:
    women = rw.load_royal_women()
    rows = tl.tla_rows()
    return {"units": tl.units(women, rows), "tla": {r["tla_id"]: r for r in rows},
            "system": (PROMPTS / "system-v2.txt").read_text(encoding="utf-8"),
            "reviewer": (PROMPTS / "reviewer-v2.txt").read_text(encoding="utf-8"),
            "reconciler": (PROMPTS / "reconciler-v2.txt").read_text(encoding="utf-8")}


def review_units(data: dict) -> list[tl.Unit]:
    return [u for u in data["units"] if u.by_rule is None]


def stored(role_dir: Path, unit: tl.Unit) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(role_dir.glob(f"{file_id(unit.dh_name)}.attempt-*.json"))]


def valid_answer(records: list[dict], expected: tuple[str, str] | None = None) -> dict | None:
    """The one valid answer among a unit's stored calls, re-derived from each call's event log
    (`validate`); the `result` stored beside the log must agree with it. With `expected`
    (system prompt, user content), the valid call must have been composed from exactly those
    (Rule 13/14: a decision stands only on the audited prompt it was asked)."""
    valid = []
    for record in records:
        checked = validate(record)
        if checked != record["result"]:
            raise ValueError(f"{record['unit_id']}: the stored result is not what its event log says")
        if "answer" in checked:
            valid.append((record, checked["answer"]))
    if expected is not None and any((r["system_prompt"], r["user_content"]) != expected for r, _ in valid):
        raise ValueError(f"{records[0]['unit_id']}: a stored call was not composed from the current prompts")
    if len(valid) > 1:
        raise ValueError(f"{records[0]['unit_id']}: more than one valid call")
    return valid[0][1] if valid else None


def run_role(data: dict, units: list[tl.Unit], role: str, compose_for) -> None:
    role_dir = RUNS / role
    role_dir.mkdir(parents=True, exist_ok=True)
    for unit in units:
        records = stored(role_dir, unit)
        while valid_answer(records) is None:
            if len(records) >= MAX_ATTEMPTS:
                raise ProtocolFailure(f"{unit.dh_name}: no valid answer in {MAX_ATTEMPTS} attempts")
            record = call(unit, role, data["system"], compose_for(unit))
            path = role_dir / f"{file_id(unit.dh_name)}.attempt-{len(records) + 1}.json"
            # Stored before it is judged: a call that stops the run is kept too (Rule 13).
            try:
                record["result"] = validate(record)
            except ProtocolFailure as stop:
                record["result"] = {"stopped": str(stop)}
                path.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
                raise
            path.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            records.append(record)
            answer = record["result"].get("answer")
            print(f"{role} {unit.dh_name}: {answer['choices'] if answer else record['result']['failure']}", flush=True)


def reviews_of(data: dict, unit: tl.Unit) -> tuple[dict, dict]:
    expected = (data["system"], compose(data["reviewer"], unit, data["tla"]))
    a, b = (valid_answer(stored(RUNS / label, unit), expected) for label in ("A", "B"))
    if a is None or b is None:
        raise ValueError(f"{unit.dh_name}: reviewers A and B must both have decided first")
    return a, b


def disputed(data: dict) -> list[tl.Unit]:
    out = []
    for unit in review_units(data):
        a, b = reviews_of(data, unit)
        if set(a["choices"]) != set(b["choices"]):
            out.append(unit)
    return out


def compose_reconciler(data: dict, unit: tl.Unit) -> str:
    reviews = list(reviews_of(data, unit))
    # Opaque labels in a seeded order, so the reconciler cannot tell which reviewer is which.
    random.Random(sha256(SHUFFLE_SALT + "reviews/" + unit.dh_name)).shuffle(reviews)
    text = "\n\n".join(f"Review {label}:\n{json.dumps({k: r[k] for k in ('choices', 'reasoning')}, ensure_ascii=False)}"
                       for label, r in zip(("X", "Y"), reviews))
    return compose(data["reconciler"], unit, data["tla"], text)


def decide(data: dict) -> list[dict]:
    """One decision per unit: by rule (one TLA name on the exact or claim-graph keys), by the
    reviewers' agreement, or by the reconciler."""
    out = []
    for unit in data["units"]:
        if unit.by_rule is not None:
            options, basis = [unit.by_rule], "rule"
        else:
            a, b = reviews_of(data, unit)
            if set(a["choices"]) == set(b["choices"]):
                choices, basis = a["choices"], "agreement"
            else:
                r = valid_answer(stored(RUNS / "reconciler", unit), (data["system"], compose_reconciler(data, unit)))
                if r is None:
                    raise ValueError(f"{unit.dh_name}: disputed and not reconciled")
                choices, basis = r["choices"], "reconciler"
            labels = labelled(unit)
            options = sorted((labels[c] for c in choices), key=lambda o: o.name)
        out.append({"dh_name": unit.dh_name, "dh_target_ids": list(unit.dh_target_ids), "basis": basis,
                    "tla_names": [o.name for o in options], "tla_ids": sorted(t for o in options for t in o.tla_ids)})
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="step", required=True)
    review = sub.add_parser("review")
    review.add_argument("--label", required=True, choices=("A", "B"))
    sub.add_parser("reconcile")
    sub.add_parser("decide")
    args = parser.parse_args()
    data = inputs()
    if args.step == "review":
        run_role(data, review_units(data), args.label, lambda u: compose(data["reviewer"], u, data["tla"]))
    elif args.step == "reconcile":
        run_role(data, disputed(data), "reconciler", lambda u: compose_reconciler(data, u))
    else:
        DECISIONS.write_text("".join(json.dumps(d, ensure_ascii=False, sort_keys=True) + "\n" for d in decide(data)),
                             encoding="utf-8")
        print(f"wrote {DECISIONS}")


if __name__ == "__main__":
    main()
