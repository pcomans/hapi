#!/usr/bin/env python3
"""Compose exact LLM inputs and wrap exact raw responses with trace metadata."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path


ROLES = {
    "prompt_auditor",
    "stage_1_reviewer",
    "stage_1_reconciler",
    "stage_2_reviewer",
    "stage_2_reconciler",
}


def load_protocol():
    path = Path(__file__).with_name("review_protocol.py")
    spec = importlib.util.spec_from_file_location("_authority_control_review_protocol_wrap", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load review protocol")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def publish_validated(path: Path, value: dict, validator) -> None:
    """Validate a complete same-directory temp file, then publish without clobbering."""
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)
    try:
        write_json(temporary_path, value)
        validator(temporary_path)
        try:
            os.link(temporary_path, path)
        except FileExistsError as error:
            raise FileExistsError(f"refusing to replace existing artifact: {path}") from error
    finally:
        temporary_path.unlink(missing_ok=True)


def bound(path: Path, protocol) -> dict:
    return {"path": str(path), "sha256": protocol.sha256_path(path)}


def components(args, protocol) -> list[tuple[str, Path]]:
    system_prompt = protocol.launcher_system_prompt_path(args.role)
    raw_contract = protocol.raw_response_contract_path(args.role)
    if args.role == "prompt_auditor":
        if args.auditor_prompt is None or args.subject_composed_input is None:
            raise ValueError(
                "prompt_auditor requires --auditor-prompt and --subject-composed-input"
            )
        return [
            ("launcher_system_prompt", system_prompt),
            ("auditor_prompt", args.auditor_prompt),
            ("raw_response_contract", raw_contract),
            ("subject_composed_input", args.subject_composed_input),
        ]
    if args.prompt is None or args.queue is None:
        raise ValueError("reviewer/reconciler requires --prompt and --queue")
    if args.role.endswith("reviewer"):
        return [
            ("launcher_system_prompt", system_prompt),
            ("review_prompt", args.prompt),
            ("raw_response_contract", raw_contract),
            ("review_queue", args.queue),
        ]
    if len(args.source_review) != 2:
        raise ValueError("a reconciler requires exactly two --source-review artifacts")
    ordered = sorted(args.source_review, key=protocol.sha256_path)
    return [
        ("launcher_system_prompt", system_prompt),
        ("reconciler_prompt", args.prompt),
        ("raw_response_contract", raw_contract),
        ("review_queue", args.queue),
        ("source_review_1", ordered[0]),
        ("source_review_2", ordered[1]),
    ]


def raw_response(path: Path, protocol) -> tuple[str, dict]:
    raw_bytes = path.read_bytes()
    raw = raw_bytes.decode("utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("raw response must be one JSON object")
    return raw, parsed


def wrap(args, protocol, run: dict) -> dict:
    raw, parsed = raw_response(args.raw_response, protocol)
    protocol.validate_raw_response(args.role, parsed)
    transcript = args.launcher_transcript.read_bytes().decode("utf-8")
    composed_sha = protocol.composed_input_sha256(
        args.role, run["launcher_envelope"], components(args, protocol)
    )
    protocol.validate_launcher_transcript(
        args.transcript_format, transcript, raw, run, args.role, composed_sha,
        "launcher transcript", require_web=(
            args.role.endswith("reviewer")
            or any(
                resolution.get("method") == "explicit_cited_override"
                for decision in parsed.get("decisions", [])
                for resolution in decision.get("field_resolutions", {}).values()
            )
        ),
    )
    if args.role == "prompt_auditor":
        if set(parsed) != {"outcome", "findings"}:
            raise ValueError("prompt-auditor raw response fields differ")
        artifact = {
            "schema_version": protocol.PROMPT_AUDIT_SCHEMA_VERSION,
            "auditor_run": run,
            "auditor_prompt": bound(args.auditor_prompt, protocol),
            "raw_response_contract": bound(
                protocol.raw_response_contract_path(args.role), protocol
            ),
            "subject_role": protocol.read_json(args.subject_composed_input)["role"],
            "subject_composed_input": bound(args.subject_composed_input, protocol),
            "composed_input_sha256": composed_sha,
            "launcher_transcript_format": args.transcript_format,
            "launcher_transcript": transcript,
            "launcher_transcript_sha256": protocol.sha256_text(transcript),
            "full_raw_response": raw,
            "full_raw_response_sha256": protocol.sha256_text(raw),
            "outcome": parsed["outcome"],
            "findings": parsed["findings"],
        }
        publish_validated(
            args.out,
            artifact,
            lambda candidate: protocol.validate_prompt_audit(
                candidate, args.auditor_prompt, args.subject_composed_input,
                artifact["subject_role"],
            ),
        )
        return artifact

    if set(parsed) != {"decisions"}:
        raise ValueError("review raw response must contain exactly one decisions field")
    stage = args.role.split("_")[1]
    if args.auditor_prompt is None:
        raise ValueError("review wrapping requires --auditor-prompt")
    if args.role.endswith("reconciler") and (
        args.reviewer_prompt is None or args.reviewer_prompt_audit is None
    ):
        raise ValueError(
            "reconciler wrapping requires --reviewer-prompt and "
            "--reviewer-prompt-audit"
        )
    artifact = {
        "schema_version": (
            protocol.CONSENSUS_SCHEMA_VERSION
            if args.role.endswith("reconciler")
            else protocol.REVIEW_SCHEMA_VERSION
        ),
        "role": args.role,
        "run": run,
        "prompt": bound(args.prompt, protocol),
        "queue": bound(args.queue, protocol),
        "prompt_audit": bound(args.prompt_audit, protocol),
        "raw_response_contract": bound(
            protocol.raw_response_contract_path(args.role), protocol
        ),
        "composed_input_sha256": composed_sha,
        "launcher_transcript_format": args.transcript_format,
        "launcher_transcript": transcript,
        "launcher_transcript_sha256": protocol.sha256_text(transcript),
        "full_raw_response": raw,
        "full_raw_response_sha256": protocol.sha256_text(raw),
        "decisions": parsed["decisions"],
    }
    if args.role.endswith("reconciler"):
        artifact["source_reviews"] = sorted(
            (bound(path, protocol) for path in args.source_review),
            key=lambda item: item["sha256"],
        )
    if args.role.endswith("reviewer"):
        validator = lambda candidate: protocol.validate_review_package(
            candidate, args.queue, args.prompt, args.prompt_audit, args.auditor_prompt, stage,
        )
    else:
        validator = lambda candidate: protocol.validate_consensus_package(
            candidate, args.queue, args.reviewer_prompt, args.reviewer_prompt_audit,
            args.source_review, args.prompt, args.prompt_audit, args.auditor_prompt,
            stage,
        )
    publish_validated(args.out, artifact, validator)
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("compose", "wrap"):
        child = subparsers.add_parser(command)
        child.add_argument("--role", choices=sorted(ROLES), required=True)
        child.add_argument("--run-metadata", type=Path, required=True)
        child.add_argument("--prompt", type=Path)
        child.add_argument("--queue", type=Path)
        child.add_argument("--auditor-prompt", type=Path)
        child.add_argument("--reviewer-prompt", type=Path)
        child.add_argument("--reviewer-prompt-audit", type=Path)
        child.add_argument("--subject-composed-input", type=Path)
        child.add_argument("--source-review", type=Path, action="append", default=[])
        child.add_argument("--out", type=Path, required=True)
        if command == "wrap":
            child.add_argument("--prompt-audit", type=Path)
            child.add_argument("--raw-response", type=Path, required=True)
            child.add_argument("--launcher-transcript", type=Path, required=True)
            child.add_argument(
                "--transcript-format",
                choices=sorted(set(load_protocol().TRANSCRIPT_FORMAT_BY_TRANSPORT.values())),
                required=True,
            )
    args = parser.parse_args()
    protocol = load_protocol()
    run = read_json(args.run_metadata)
    protocol.validate_model_run(run, "run metadata", args.role)
    payload = protocol.composed_input_bytes(
        args.role, run["launcher_envelope"], components(args, protocol)
    )
    if args.command == "compose":
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(payload)
        print(json.dumps({"composed_input_sha256": protocol.sha256_path(args.out)}, indent=2))
        return
    if args.role != "prompt_auditor" and args.prompt_audit is None:
        raise ValueError("review and reconciliation wrapping requires --prompt-audit")
    artifact = wrap(args, protocol, run)
    print(json.dumps({"artifact_sha256": protocol.sha256_path(args.out), "role": artifact.get(
        "role", "prompt_auditor"
    )}, indent=2))


if __name__ == "__main__":
    main()
