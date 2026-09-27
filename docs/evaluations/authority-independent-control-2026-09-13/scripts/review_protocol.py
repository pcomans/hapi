#!/usr/bin/env python3
"""Validate prompt audits and fully traceable two-reviewer consensus artifacts."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shlex
import urllib.parse
from pathlib import Path


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
HOST_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)
STAGE_OUTCOMES = {
    "1": {
        "same_entity": {"same_entity", "different_entity", "insufficient_evidence"},
        "useful_granularity": {"useful", "too_broad", "too_narrow", "insufficient_evidence"},
    },
    "2": {
        "canonical_identity": {"exact_identity", "different_identity", "insufficient_evidence"},
    },
}
PROMPT_ROLES = {
    ("1", "reviewer"): "stage_1_reviewer",
    ("1", "reconciler"): "stage_1_reconciler",
    ("2", "reviewer"): "stage_2_reviewer",
    ("2", "reconciler"): "stage_2_reconciler",
}
PROMPT_FORBIDDEN_SNIPPETS = (
    "authority_only_transition",
    "literal_only_transition",
    "retained_control",
    "source_target_id",
    "case_binding_sha256",
    "idai:",
)
QUEUE_FORBIDDEN_KEYS = {
    "arm_native", "artifact_id", "artifact_ids", "artifact_ids_by_side",
    "case_binding_sha256", "mention_id", "mention_ids", "mention_ids_by_side",
    "source_target_id", "transition_class",
}
EVIDENCE_BLOCK_KEYS = {
    "evidence_group", "representative_exact_mention", "exact_mention_variants",
    "mention_count", "distinct_record_count", "field_paths", "evidence_roles",
}
PROTOCOL_VERSION = "hapi-authority-control-traceable-review/2"
MODEL_INPUT_SCHEMA_VERSION = "hapi-authority-control-model-input/2"
PROMPT_AUDIT_SCHEMA_VERSION = "hapi-authority-control-prompt-audit/2"
REVIEW_SCHEMA_VERSION = "hapi-authority-control-traceable-review/2"
CONSENSUS_SCHEMA_VERSION = "hapi-authority-control-traceable-consensus/2"
EVALUATION_ROOT = Path(__file__).resolve().parent.parent
RAW_RESPONSE_CONTRACT_PATHS = {
    "prompt_auditor": EVALUATION_ROOT / "raw-response-contracts/prompt-auditor-v1.schema.json",
    "stage_1_reviewer": EVALUATION_ROOT / "raw-response-contracts/stage-1-reviewer-v1.schema.json",
    "stage_1_reconciler": EVALUATION_ROOT / "raw-response-contracts/stage-1-reconciler-v1.schema.json",
    "stage_2_reviewer": EVALUATION_ROOT / "raw-response-contracts/stage-2-reviewer-v1.schema.json",
    "stage_2_reconciler": EVALUATION_ROOT / "raw-response-contracts/stage-2-reconciler-v1.schema.json",
}
LAUNCHER_SYSTEM_PROMPT_PATHS = {
    "prompt_auditor": EVALUATION_ROOT / "launcher-instructions/prompt-auditor-system-v1.txt",
    "stage_1_reviewer": EVALUATION_ROOT / "launcher-instructions/review-system-v1.txt",
    "stage_1_reconciler": EVALUATION_ROOT / "launcher-instructions/review-system-v1.txt",
    "stage_2_reviewer": EVALUATION_ROOT / "launcher-instructions/review-system-v1.txt",
    "stage_2_reconciler": EVALUATION_ROOT / "launcher-instructions/review-system-v1.txt",
}
TRANSCRIPT_FORMAT_BY_TRANSPORT = {
    "anthropic_cli_bare_stream_json": "claude_stream_json",
    "openai_responses_api_jsonl": "responses_api_jsonl",
}
PROVIDER_BY_TRANSPORT = {
    "anthropic_cli_bare_stream_json": "anthropic",
    "openai_responses_api_jsonl": "openai",
}
UNPINNED_MODEL_IDS = {"gpt-5.6-sol"}
REASONING_SUMMARY_LEVELS = {"auto", "concise", "detailed"}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def is_valid_https_url(value: object) -> bool:
    if not isinstance(value, str) or not value or any(char.isspace() for char in value):
        return False
    try:
        parsed = urllib.parse.urlsplit(value)
        hostname = parsed.hostname
        parsed.port
    except (UnicodeError, ValueError):
        return False
    if (
        parsed.scheme.lower() != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        return False
    try:
        ascii_hostname = hostname.encode("idna").decode("ascii").rstrip(".")
    except UnicodeError:
        return False
    return (
        0 < len(ascii_hostname) <= 253
        and all(HOST_LABEL_RE.fullmatch(label) for label in ascii_hostname.split("."))
    )


def raw_response_contract_path(role: str) -> Path:
    try:
        return RAW_RESPONSE_CONTRACT_PATHS[role]
    except KeyError as error:
        raise ValueError(f"unknown review role: {role}") from error


def launcher_system_prompt_path(role: str) -> Path:
    try:
        return LAUNCHER_SYSTEM_PROMPT_PATHS[role]
    except KeyError as error:
        raise ValueError(f"unknown review role: {role}") from error


def composed_input_bytes(
    role: str, launcher_envelope: str, components: list[tuple[str, Path]]
) -> bytes:
    """Return the exact versioned UTF-8 payload that an external launcher must send."""
    value = {
        "schema_version": MODEL_INPUT_SCHEMA_VERSION,
        "role": role,
        "launcher_envelope": launcher_envelope,
        "components": [
            {
                "label": label,
                "path": str(path),
                "sha256": sha256_path(path),
                "utf8": path.read_text(encoding="utf-8"),
            }
            for label, path in components
        ],
    }
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def composed_input_sha256(
    role: str, launcher_envelope: str, components: list[tuple[str, Path]]
) -> str:
    return hashlib.sha256(composed_input_bytes(role, launcher_envelope, components)).hexdigest()


def validate_composed_input_file(path: Path, expected_role: str) -> dict:
    value = read_json(path)
    require_keys(
        value, {"schema_version", "role", "launcher_envelope", "components"},
        "composed input",
    )
    if value["schema_version"] != MODEL_INPUT_SCHEMA_VERSION:
        raise ValueError("composed input schema version mismatch")
    if value["role"] != expected_role:
        raise ValueError("composed input role mismatch")
    require_nonempty_string(value["launcher_envelope"], "composed input launcher_envelope")
    components = value["components"]
    if not isinstance(components, list) or not components:
        raise ValueError("composed input components must be nonempty")
    labels = []
    for index, component in enumerate(components):
        require_keys(component, {"label", "path", "sha256", "utf8"}, f"component {index}")
        labels.append(require_nonempty_string(component["label"], f"component {index}.label"))
        component_path = Path(require_nonempty_string(
            component["path"], f"component {index}.path"
        ))
        if component["sha256"] != sha256_path(component_path):
            raise ValueError(f"composed input component SHA-256 mismatch: {component['label']}")
        if component["utf8"] != component_path.read_text(encoding="utf-8"):
            raise ValueError(f"composed input component bytes mismatch: {component['label']}")
    if len(labels) != len(set(labels)):
        raise ValueError("composed input component labels are duplicated")
    expected_labels = {
        "prompt_auditor": [
            "launcher_system_prompt", "auditor_prompt", "raw_response_contract",
            "subject_composed_input",
        ],
        "stage_1_reviewer": [
            "launcher_system_prompt", "review_prompt", "raw_response_contract",
            "review_queue",
        ],
        "stage_2_reviewer": [
            "launcher_system_prompt", "review_prompt", "raw_response_contract",
            "review_queue",
        ],
        "stage_1_reconciler": [
            "launcher_system_prompt", "reconciler_prompt", "raw_response_contract",
            "review_queue", "source_review_1", "source_review_2",
        ],
        "stage_2_reconciler": [
            "launcher_system_prompt", "reconciler_prompt", "raw_response_contract",
            "review_queue", "source_review_1", "source_review_2",
        ],
    }[expected_role]
    if labels != expected_labels:
        raise ValueError(
            f"composed input component labels differ: {labels} != {expected_labels}"
        )
    component_by_label = {component["label"]: component for component in components}
    if Path(component_by_label["raw_response_contract"]["path"]).resolve() != (
        raw_response_contract_path(expected_role).resolve()
    ):
        raise ValueError("composed input uses the wrong raw-response contract")
    if Path(component_by_label["launcher_system_prompt"]["path"]).resolve() != (
        launcher_system_prompt_path(expected_role).resolve()
    ):
        raise ValueError("composed input uses the wrong launcher system prompt")
    validate_raw_response_contract(expected_role)
    expected_bytes = composed_input_bytes(
        expected_role,
        value["launcher_envelope"],
        [(component["label"], Path(component["path"])) for component in components],
    )
    if path.read_bytes() != expected_bytes:
        raise ValueError("composed input bytes are not canonical or changed")
    return value


def canonical_sha256(value) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_text(encoded)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require_keys(value: dict, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise ValueError(f"{label} fields differ: {actual} != {sorted(expected)}")


def require_nonempty_string(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _resolve_local_ref(root: dict, reference: str, label: str) -> dict:
    if not reference.startswith("#/"):
        raise ValueError(f"{label} uses a non-local JSON Schema reference")
    value = root
    for part in reference[2:].split("/"):
        if not isinstance(value, dict) or part not in value:
            raise ValueError(f"{label} has an unresolved JSON Schema reference")
        value = value[part]
    if not isinstance(value, dict):
        raise ValueError(f"{label} JSON Schema reference is not an object")
    return value


def _validate_json_schema(value, schema: dict, root: dict, label: str) -> None:
    if "$ref" in schema:
        _validate_json_schema(value, _resolve_local_ref(root, schema["$ref"], label), root, label)
        return
    if "const" in schema and value != schema["const"]:
        raise ValueError(f"{label} differs from the raw-response contract const")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{label} is outside the raw-response contract enum")
    expected_type = schema.get("type")
    type_checks = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "boolean": lambda item: isinstance(item, bool),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
    }
    if expected_type is not None:
        if expected_type not in type_checks or not type_checks[expected_type](value):
            raise ValueError(f"{label} must be JSON type {expected_type}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise ValueError(f"{label} is shorter than the raw-response contract")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise ValueError(f"{label} does not match the raw-response contract pattern")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise ValueError(f"{label} has too few items for the raw-response contract")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise ValueError(f"{label} has too many items for the raw-response contract")
        if "items" in schema:
            for index, item in enumerate(value):
                _validate_json_schema(item, schema["items"], root, f"{label}[{index}]")
    if isinstance(value, dict):
        required = schema.get("required", [])
        missing = [key for key in required if key not in value]
        if missing:
            raise ValueError(f"{label} is missing raw-response contract fields: {missing}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extras = sorted(set(value) - set(properties))
            if extras:
                raise ValueError(f"{label} has extra raw-response contract fields: {extras}")
        for key, child_schema in properties.items():
            if key in value:
                _validate_json_schema(value[key], child_schema, root, f"{label}.{key}")
    if "anyOf" in schema:
        failures = []
        for branch in schema["anyOf"]:
            try:
                _validate_json_schema(value, branch, root, label)
            except ValueError as error:
                failures.append(str(error))
            else:
                break
        else:
            raise ValueError(
                f"{label} matches no raw-response contract anyOf branch: {failures}"
            )


def validate_raw_response_contract(role: str) -> dict:
    path = raw_response_contract_path(role)
    contract = read_json(path)
    if contract.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ValueError("raw-response contract JSON Schema version mismatch")
    if contract.get("x-hapi-role") != role:
        raise ValueError("raw-response contract role mismatch")
    expected_id = f"hapi-authority-control-raw-response/{role.replace('_', '-')}/1"
    if contract.get("$id") != expected_id:
        raise ValueError("raw-response contract ID mismatch")
    return contract


def validate_raw_response(role: str, value: dict) -> None:
    contract = validate_raw_response_contract(role)
    _validate_json_schema(value, contract, contract, "raw response")


def validate_provider_snapshot_evidence(
    binding: dict, model_id: str, model_snapshot: str, transport: str, label: str,
) -> None:
    require_keys(binding, {"path", "sha256"}, f"{label}.provider_snapshot_evidence")
    path = Path(require_nonempty_string(
        binding["path"], f"{label}.provider_snapshot_evidence.path"
    ))
    if binding["sha256"] != sha256_path(path):
        raise ValueError(f"{label}.provider_snapshot_evidence SHA-256 mismatch")
    evidence = read_json(path)
    require_keys(evidence, {
        "schema_version", "provider", "requested_model_id", "resolved_snapshot_id",
        "source_url", "retrieved_at", "raw_provider_response",
    }, f"{label}.provider_snapshot_evidence content")
    if evidence["schema_version"] != "hapi-provider-model-snapshot-evidence/1":
        raise ValueError(f"{label}.provider_snapshot_evidence schema version mismatch")
    if transport not in PROVIDER_BY_TRANSPORT:
        raise ValueError(f"{label}.launcher_transport is unsupported")
    expected_provider = PROVIDER_BY_TRANSPORT[transport]
    if evidence["provider"] != expected_provider:
        raise ValueError(f"{label}.provider does not match the launcher transport")
    if evidence["requested_model_id"] != model_id:
        raise ValueError(f"{label}.provider snapshot requested model mismatch")
    if evidence["resolved_snapshot_id"] != model_snapshot:
        raise ValueError(f"{label}.provider resolved snapshot mismatch")
    if model_id in UNPINNED_MODEL_IDS:
        raise ValueError(f"{label}.model_id has no provider-pinned immutable snapshot")
    if model_snapshot == model_id or re.search(
        r"(?:\d{4}-\d{2}-\d{2}|\d{8})", model_snapshot
    ) is None:
        raise ValueError(f"{label}.model_snapshot is not a distinct dated provider snapshot")
    parsed_url = urllib.parse.urlsplit(evidence["source_url"])
    expected_hosts = {"openai": "api.openai.com", "anthropic": "api.anthropic.com"}
    expected_path = f"/v1/models/{urllib.parse.quote(model_snapshot, safe='')}"
    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname != expected_hosts[expected_provider]
        or parsed_url.port is not None
        or parsed_url.username is not None
        or parsed_url.password is not None
        or parsed_url.path != expected_path
        or parsed_url.query
        or parsed_url.fragment
    ):
        raise ValueError(f"{label}.provider snapshot URL is not an allowlisted official model endpoint")
    try:
        retrieved_at = dt.datetime.fromisoformat(
            evidence["retrieved_at"].replace("Z", "+00:00")
        )
    except (AttributeError, ValueError) as error:
        raise ValueError(f"{label}.provider snapshot retrieved_at must be ISO-8601") from error
    if retrieved_at.tzinfo is None:
        raise ValueError(f"{label}.provider snapshot retrieved_at must include a timezone")
    if not isinstance(evidence["raw_provider_response"], dict):
        raise ValueError(f"{label}.raw_provider_response must be an object")
    raw = evidence["raw_provider_response"]
    if raw.get("id") != model_snapshot or raw.get("type", raw.get("object")) != "model":
        raise ValueError(f"{label}.raw provider model response does not identify the snapshot")
    if expected_provider == "openai":
        if (
            not isinstance(raw.get("created"), int)
            or isinstance(raw.get("created"), bool)
            or raw["created"] <= 0
            or not isinstance(raw.get("owned_by"), str)
            or not raw["owned_by"].strip()
        ):
            raise ValueError(f"{label}.raw OpenAI model response lacks authoritative fields")
    elif (
        not isinstance(raw.get("created_at"), str)
        or not raw["created_at"].strip()
        or not isinstance(raw.get("display_name"), str)
        or not raw["display_name"].strip()
    ):
        raise ValueError(f"{label}.raw Anthropic model response lacks authoritative fields")


def validate_reasoning_capture_parameters(parameters: dict, transport: str, label: str) -> None:
    """Require the request to have actually asked the provider to surface its reasoning.

    A pinned snapshot and a byte-verified transcript prove *which* model answered and
    *that* the transcript is unaltered; neither proves the model's stated reasoning was
    requested at all. Provider APIs only emit reasoning content when the caller asks
    for it, so that request must be present before the transcript is trusted to carry it.
    """
    if transport == "openai_responses_api_jsonl":
        reasoning = parameters.get("reasoning")
        if not isinstance(reasoning, dict) or reasoning.get("summary") not in REASONING_SUMMARY_LEVELS:
            raise ValueError(
                f"{label}.parameters.reasoning.summary must request a captured reasoning summary"
            )
    elif transport == "anthropic_cli_bare_stream_json":
        thinking = parameters.get("thinking")
        if (
            not isinstance(thinking, dict)
            or thinking.get("type") != "enabled"
            or not isinstance(thinking.get("budget_tokens"), int)
            or isinstance(thinking.get("budget_tokens"), bool)
            or thinking["budget_tokens"] <= 0
        ):
            raise ValueError(
                f"{label}.parameters.thinking must enable extended thinking with a positive budget"
            )
    else:
        raise ValueError(f"{label}.launcher_transport has no reasoning-capture contract")


def validate_model_run(value: dict, label: str, role: str) -> None:
    require_keys(value, {
        "request_id", "transport_session_id", "run_date", "model_id",
        "model_snapshot", "reasoning_effort", "parameters", "launcher_transport",
        "launcher_system_prompt",
        "provider_snapshot_evidence", "launcher_envelope", "launcher_envelope_sha256",
    }, label)
    try:
        dt.date.fromisoformat(require_nonempty_string(value["run_date"], f"{label}.run_date"))
    except ValueError as error:
        raise ValueError(f"{label}.run_date must be ISO YYYY-MM-DD") from error
    for key in (
        "request_id", "transport_session_id", "model_id", "model_snapshot",
        "reasoning_effort", "launcher_envelope",
    ):
        require_nonempty_string(value[key], f"{label}.{key}")
    transport = value["launcher_transport"]
    if transport not in TRANSCRIPT_FORMAT_BY_TRANSPORT:
        raise ValueError(f"{label}.launcher_transport is unsupported")
    validate_provider_snapshot_evidence(
        value["provider_snapshot_evidence"], value["model_id"],
        value["model_snapshot"], transport, label,
    )
    validate_bound_input(
        value["launcher_system_prompt"], launcher_system_prompt_path(role),
        f"{label}.launcher_system_prompt",
    )
    if value["launcher_envelope_sha256"] != sha256_text(value["launcher_envelope"]):
        raise ValueError(f"{label}.launcher_envelope SHA-256 mismatch")
    if not isinstance(value["parameters"], dict) or not value["parameters"]:
        raise ValueError(f"{label}.parameters must be a nonempty object")
    validate_reasoning_capture_parameters(value["parameters"], transport, label)
    try:
        envelope = json.loads(value["launcher_envelope"])
    except json.JSONDecodeError as error:
        raise ValueError(f"{label}.launcher_envelope must be canonical JSON") from error
    require_keys(envelope, {
        "schema_version", "transport", "model_snapshot", "system_prompt_sha256",
        "input_delivery", "parameters", "agent_profile", "transcript_format",
        "invocation", "credential_mode",
    }, f"{label}.launcher_envelope content")
    if value["launcher_envelope"] != json.dumps(
        envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ):
        raise ValueError(f"{label}.launcher_envelope is not canonical JSON")
    if envelope["schema_version"] != "hapi-authority-control-launcher-envelope/2":
        raise ValueError(f"{label}.launcher_envelope schema version mismatch")
    if envelope["transport"] != transport:
        raise ValueError(f"{label}.launcher_envelope transport mismatch")
    if envelope["model_snapshot"] != value["model_snapshot"]:
        raise ValueError(f"{label}.launcher_envelope model snapshot mismatch")
    if envelope["system_prompt_sha256"] != value["launcher_system_prompt"]["sha256"]:
        raise ValueError(f"{label}.launcher_envelope system prompt mismatch")
    if envelope["input_delivery"] != "stdin_exact_composed_input_bytes":
        raise ValueError(f"{label}.launcher_envelope input delivery is not exact")
    if envelope["parameters"] != value["parameters"]:
        raise ValueError(f"{label}.launcher_envelope parameters mismatch")
    if envelope["agent_profile"] is not None:
        raise ValueError(f"{label}.launcher_envelope must not select an agent profile")
    if envelope["transcript_format"] != TRANSCRIPT_FORMAT_BY_TRANSPORT[transport]:
        raise ValueError(f"{label}.launcher_envelope transcript format mismatch")
    invocation = require_nonempty_string(
        envelope["invocation"], f"{label}.launcher_envelope invocation"
    )
    if "--agent" in invocation:
        raise ValueError(f"{label}.launcher_envelope must not use --agent")
    if transport == "anthropic_cli_bare_stream_json":
        if envelope["credential_mode"] not in {"anthropic_api_key", "api_key_helper"}:
            raise ValueError(f"{label}.Claude bare invocation requires API-key credentials")
        try:
            tokens = shlex.split(invocation)
        except ValueError as error:
            raise ValueError(f"{label}.Claude invocation is not valid shell syntax") from error

        def flag_value(flag: str) -> str | None:
            positions = [index for index, token in enumerate(tokens) if token == flag]
            if len(positions) != 1 or positions[0] + 1 >= len(tokens):
                return None
            return tokens[positions[0] + 1]

        expected_system_prompt = launcher_system_prompt_path(role).read_text(
            encoding="utf-8"
        )
        if (
            not tokens
            or tokens[0] != "claude"
            or "--bare" not in tokens
            or "--print" not in tokens
            or "--verbose" not in tokens
            or "--agent" in tokens
            or "--append-system-prompt" in tokens
            or flag_value("--output-format") != "stream-json"
            or flag_value("--model") != value["model_snapshot"]
            or flag_value("--system-prompt") != expected_system_prompt
            or flag_value("--tools") != ""
        ):
            raise ValueError(
                f"{label}.Claude invocation is not exact bare stream-json with the bound system prompt"
            )
    elif transport == "openai_responses_api_jsonl":
        if envelope["credential_mode"] != "openai_api_key":
            raise ValueError(f"{label}.OpenAI Responses invocation requires API-key credentials")
        if invocation != "POST https://api.openai.com/v1/responses":
            raise ValueError(f"{label}.OpenAI invocation is not the explicit Responses API path")


def validate_bound_input(value: dict, actual_path: Path, label: str) -> None:
    require_keys(value, {"path", "sha256"}, label)
    if require_nonempty_string(value["path"], f"{label}.path") != str(actual_path):
        raise ValueError(f"{label} path mismatch")
    if value["sha256"] != sha256_path(actual_path):
        raise ValueError(f"{label} SHA-256 mismatch")


def _jsonl_events(transcript: str, label: str) -> list[dict]:
    lines = transcript.splitlines()
    if not lines:
        raise ValueError(f"{label} is empty")
    events = []
    for index, line in enumerate(lines):
        if not line.strip():
            raise ValueError(f"{label} contains a blank JSONL record")
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{label} record {index} is not JSON") from error
        if not isinstance(event, dict):
            raise ValueError(f"{label} record {index} is not an object")
        events.append(event)
    return events


def _validate_usage(value, label: str) -> None:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{label} usage must be a nonempty object")
    for key in ("input_tokens", "output_tokens"):
        count = value.get(key)
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
            raise ValueError(f"{label} usage.{key} must be a positive integer")


def _validate_request_capture(
    event: dict, run: dict, role: str, input_sha256: str, label: str,
) -> None:
    require_keys(event, {
        "type", "transport", "request_id", "transport_session_id", "run_date",
        "model_id", "model_snapshot", "reasoning_effort", "parameters",
        "input_sha256", "system_prompt", "system_prompt_sha256",
    }, f"{label} request capture")
    expected_system = launcher_system_prompt_path(role).read_text(encoding="utf-8")
    expected = {
        "type": "hapi.transport.request",
        "transport": run["launcher_transport"],
        "request_id": run["request_id"],
        "transport_session_id": run["transport_session_id"],
        "run_date": run["run_date"],
        "model_id": run["model_id"],
        "model_snapshot": run["model_snapshot"],
        "reasoning_effort": run["reasoning_effort"],
        "parameters": run["parameters"],
        "input_sha256": input_sha256,
        "system_prompt": expected_system,
        "system_prompt_sha256": sha256_text(expected_system),
    }
    if event != expected:
        raise ValueError(f"{label} request capture does not bind the exact model run and input")


def _https_sources(value, label: str) -> None:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} web result must contain sources")
    for source in value:
        if (
            not isinstance(source, dict)
            or not is_valid_https_url(source.get("url"))
        ):
            raise ValueError(f"{label} web result contains an invalid source")


def _validate_responses_web_pairs(
    events: list[dict], completed_output: list[dict], label: str,
) -> None:
    starts = {}
    finishes = {}
    for event in events:
        if event.get("type") not in {"response.output_item.added", "response.output_item.done"}:
            continue
        if not isinstance(event.get("output_index"), int) or not isinstance(
            event.get("item"), dict
        ):
            raise ValueError(f"{label} web-search event output binding mismatch")
        item = event["item"]
        if item.get("type") != "web_search_call":
            continue
        item_id = require_nonempty_string(item.get("id"), f"{label} web-search item ID")
        target = starts if event["type"].endswith("added") else finishes
        if item_id in target:
            raise ValueError(f"{label} duplicates a web-search event")
        target[item_id] = (event["output_index"], item)
    if not starts or set(starts) != set(finishes):
        raise ValueError(f"{label} lacks paired Responses web-search call/results")
    completed_by_id = {
        item.get("id"): item for item in completed_output
        if isinstance(item, dict) and item.get("type") == "web_search_call"
    }
    if set(completed_by_id) != set(finishes):
        raise ValueError(f"{label} completed response web-search items differ")
    for item_id, (output_index, item) in finishes.items():
        if starts[item_id][0] != output_index or item.get("status") != "completed":
            raise ValueError(f"{label} web-search result is not complete")
        action = item.get("action")
        completed_item = completed_by_id[item_id]
        if not isinstance(action, dict) or action != completed_item.get("action"):
            raise ValueError(f"{label} web-search action differs from completed response")
        require_nonempty_string(action.get("query"), f"{label} web-search query")
        _https_sources(action.get("sources"), f"{label} web-search {item_id}")


def _validate_claude_web_pairs(events: list[dict], label: str) -> None:
    starts = {}
    finishes = {}
    for event in events:
        message = event.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), list):
            continue
        for block in message["content"]:
            if not isinstance(block, dict):
                continue
            if (
                event.get("type") == "assistant"
                and block.get("type") == "tool_use"
                and block.get("name") == "WebSearch"
            ):
                item_id = require_nonempty_string(block.get("id"), f"{label} WebSearch ID")
                if item_id in starts or not isinstance(block.get("input"), dict):
                    raise ValueError(f"{label} duplicates or malforms a WebSearch call")
                require_nonempty_string(block["input"].get("query"), f"{label} WebSearch query")
                starts[item_id] = block
            elif event.get("type") == "user" and block.get("type") == "tool_result":
                item_id = require_nonempty_string(
                    block.get("tool_use_id"), f"{label} WebSearch result ID"
                )
                if item_id in finishes:
                    raise ValueError(f"{label} duplicates a WebSearch result")
                finishes[item_id] = block
    if not starts or set(starts) != set(finishes):
        raise ValueError(f"{label} lacks paired Claude WebSearch call/results")
    for item_id, block in finishes.items():
        _https_sources(block.get("sources"), f"{label} WebSearch {item_id}")


def validate_launcher_transcript(
    transcript_format: str, transcript: str, expected_raw_response: str,
    run: dict, role: str, expected_composed_input_sha256: str, label: str,
    require_web: bool = False,
) -> None:
    expected_format = TRANSCRIPT_FORMAT_BY_TRANSPORT[run["launcher_transport"]]
    if transcript_format != expected_format:
        raise ValueError(f"{label} format does not match the launcher transport")
    events = _jsonl_events(transcript, label)
    _validate_request_capture(
        events[0], run, role, expected_composed_input_sha256, label
    )
    if transcript_format == "claude_stream_json":
        provider_events = events[1:]
        init_events = [
            event for event in provider_events
            if event.get("type") == "system" and event.get("subtype") == "init"
        ]
        if (
            len(init_events) != 1
            or not provider_events
            or provider_events[0] is not init_events[0]
        ):
            raise ValueError(f"{label} lacks the Claude system/init record")
        init = init_events[0]
        if (
            init.get("session_id") != run["transport_session_id"]
            or init.get("model") != run["model_snapshot"]
        ):
            raise ValueError(f"{label} Claude init does not bind session/model metadata")
        terminal = provider_events[-1]
        if (
            terminal.get("type") != "result"
            or terminal.get("subtype") != "success"
            or terminal.get("is_error") is not False
        ):
            raise ValueError(f"{label} lacks a successful terminal Claude result")
        model_usage = terminal.get("modelUsage")
        if terminal.get("session_id") != run["transport_session_id"]:
            raise ValueError(f"{label} terminal Claude session mismatch")
        if (
            not isinstance(model_usage, dict)
            or set(model_usage) != {run["model_snapshot"]}
            or not isinstance(model_usage[run["model_snapshot"]], dict)
            or not model_usage[run["model_snapshot"]]
        ):
            raise ValueError(f"{label} terminal Claude modelUsage snapshot mismatch")
        _validate_usage(terminal.get("usage"), f"{label} terminal Claude result")
        assistant_events = [
            event for event in provider_events[1:-1]
            if event.get("type") == "assistant"
        ]
        num_turns = terminal.get("num_turns")
        if (
            not assistant_events
            or not isinstance(num_turns, int)
            or isinstance(num_turns, bool)
            or num_turns <= 0
            or num_turns != len(assistant_events)
        ):
            raise ValueError(f"{label} Claude turn count does not bind assistant events")
        session_id = run["transport_session_id"]
        if any(event.get("session_id") != session_id for event in provider_events):
            raise ValueError(f"{label} Claude event session mismatch")
        for event in assistant_events:
            message = event.get("message")
            if (
                not isinstance(message, dict)
                or message.get("type") != "message"
                or message.get("role") != "assistant"
                or message.get("model") != run["model_snapshot"]
                or not isinstance(message.get("content"), list)
                or not isinstance(message.get("stop_reason"), str)
                or not message["stop_reason"]
            ):
                raise ValueError(f"{label} Claude assistant event is incomplete")
        thinking_blocks = [
            block
            for event in assistant_events
            for block in event["message"]["content"]
            if isinstance(block, dict) and block.get("type") == "thinking"
        ]
        if not any(
            isinstance(block.get("thinking"), str) and block["thinking"].strip()
            for block in thinking_blocks
        ):
            raise ValueError(f"{label} lacks captured extended-thinking content")
        final_assistant_message = assistant_events[-1]["message"]
        assistant_text = "".join(
            block["text"]
            for block in final_assistant_message["content"]
            if isinstance(block, dict)
            and block.get("type") == "text"
            and isinstance(block.get("text"), str)
        )
        if assistant_text != expected_raw_response:
            raise ValueError(f"{label} final Claude assistant message differs from raw response")
        final_message = terminal.get("result")
        if require_web:
            _validate_claude_web_pairs(provider_events[1:-1], label)
    else:
        provider_events = events[1:]
        sequence_numbers = [event.get("sequence_number") for event in provider_events]
        if (
            not all(isinstance(number, int) and not isinstance(number, bool) for number in sequence_numbers)
            or sequence_numbers != list(range(len(provider_events)))
            or not all(
                isinstance(event.get("type"), str)
                and event["type"].startswith("response.")
                for event in provider_events
            )
        ):
            raise ValueError(f"{label} Responses events are not a contiguous native sequence")
        if provider_events[0].get("type") != "response.created" or not isinstance(
            provider_events[0].get("response"), dict
        ):
            raise ValueError(f"{label} lacks one provider-native response.created event")
        response_id = run["transport_session_id"]
        created = provider_events[0]["response"]
        expected_metadata = {
            "hapi_request_id": run["request_id"],
            "hapi_composed_input_sha256": expected_composed_input_sha256,
        }
        # Assumes the Responses API echoes the requested summary level verbatim in
        # response.reasoning.summary rather than resolving it to a different value.
        expected_reasoning_summary = run["parameters"]["reasoning"]["summary"]
        if (
            created.get("id") != response_id
            or created.get("object") != "response"
            or created.get("status") != "in_progress"
            or not isinstance(created.get("created_at"), int)
            or created.get("model") != run["model_snapshot"]
            or created.get("metadata") != expected_metadata
            or created.get("output") != []
            or created.get("usage") is not None
            or not isinstance(created.get("reasoning"), dict)
            or created["reasoning"].get("summary") != expected_reasoning_summary
            or not isinstance(created.get("tools"), list)
            or created.get("instructions") != launcher_system_prompt_path(role).read_text(
                encoding="utf-8"
            )
        ):
            raise ValueError(f"{label} response.created metadata mismatch")
        terminal = events[-1]
        if terminal.get("type") != "response.completed" or not isinstance(
            terminal.get("response"), dict
        ):
            raise ValueError(f"{label} is truncated before response.completed")
        completed = terminal["response"]
        required_response_fields = {
            "id", "object", "created_at", "status", "completed_at", "error",
            "incomplete_details", "instructions", "model", "output", "reasoning",
            "tools", "usage", "metadata",
        }
        if (
            not required_response_fields.issubset(completed)
            or completed.get("id") != response_id
            or completed.get("object") != "response"
            or completed.get("created_at") != created["created_at"]
            or not isinstance(completed.get("completed_at"), int)
            or completed.get("error") is not None
            or completed.get("incomplete_details") is not None
            or completed.get("model") != run["model_snapshot"]
            or completed.get("metadata") != expected_metadata
            or completed.get("status") != "completed"
            or completed.get("instructions") != created["instructions"]
            or not isinstance(completed.get("reasoning"), dict)
            or completed["reasoning"].get("summary") != expected_reasoning_summary
            or not isinstance(completed.get("tools"), list)
        ):
            raise ValueError(f"{label} response.completed metadata mismatch")
        _validate_usage(completed.get("usage"), f"{label} terminal Responses event")
        text_events = [
            event for event in events[1:-1]
            if event.get("type") == "response.output_text.done"
        ]
        if len(text_events) != 1 or not all(
            isinstance(text_events[0].get(key), int)
            for key in ("output_index", "content_index")
        ) or not isinstance(text_events[0].get("item_id"), str):
            raise ValueError(f"{label} lacks one terminal response.output_text.done event")
        final_message = text_events[0].get("text")
        output = completed.get("output")
        if not isinstance(output, list):
            raise ValueError(f"{label} completed response lacks output items")
        added_items = {}
        done_items = {}
        for event in events[1:-1]:
            if event.get("type") not in {
                "response.output_item.added", "response.output_item.done",
            }:
                continue
            item = event.get("item")
            output_index = event.get("output_index")
            if (
                not isinstance(item, dict)
                or not isinstance(output_index, int)
                or not isinstance(item.get("id"), str)
            ):
                raise ValueError(f"{label} output-item event is malformed")
            target = added_items if event["type"].endswith("added") else done_items
            if item["id"] in target:
                raise ValueError(f"{label} duplicates an output-item event")
            target[item["id"]] = (output_index, item)
        terminal_items = {
            item.get("id"): (index, item)
            for index, item in enumerate(output)
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        if (
            len(terminal_items) != len(output)
            or set(added_items) != set(done_items)
            or set(done_items) != set(terminal_items)
        ):
            raise ValueError(f"{label} streamed and completed output-item sets differ")
        for item_id, (output_index, done_item) in done_items.items():
            if (
                added_items[item_id][0] != output_index
                or terminal_items[item_id][0] != output_index
                or added_items[item_id][1].get("type") != done_item.get("type")
                or done_item != terminal_items[item_id][1]
            ):
                raise ValueError(f"{label} output item {item_id} differs across the stream")
        message_items = [
            item for item in output
            if isinstance(item, dict) and item.get("id") == text_events[0]["item_id"]
            and item.get("type") == "message" and item.get("status") == "completed"
        ]
        expected_text_blocks = [
            block for item in message_items for block in item.get("content", [])
            if isinstance(block, dict) and block.get("type") == "output_text"
            and block.get("text") == final_message
        ]
        if len(message_items) != 1 or len(expected_text_blocks) != 1:
            raise ValueError(f"{label} final text differs from the completed response output")
        if require_web:
            if not any(
                isinstance(tool, dict)
                and tool.get("type") in {"web_search", "web_search_preview"}
                for tool in completed["tools"]
            ):
                raise ValueError(f"{label} completed response lacks a web-search tool declaration")
            _validate_responses_web_pairs(events[1:-1], output, label)
        reasoning_items = [
            item for item in output
            if isinstance(item, dict) and item.get("type") == "reasoning"
        ]
        if not any(
            isinstance(item.get("summary"), list)
            and any(
                isinstance(part, dict)
                and part.get("type") == "summary_text"
                and isinstance(part.get("text"), str)
                and part["text"].strip()
                for part in item["summary"]
            )
            for item in reasoning_items
        ):
            raise ValueError(f"{label} completed response lacks captured reasoning summary content")
    if not isinstance(final_message, str) or final_message.encode("utf-8") != (
        expected_raw_response.encode("utf-8")
    ):
        raise ValueError(f"{label} final agent message differs byte-for-byte from raw response")


def recursive_forbidden_keys(value, path: str = "$") -> list[str]:
    findings = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in QUEUE_FORBIDDEN_KEYS:
                findings.append(child_path)
            findings.extend(recursive_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(recursive_forbidden_keys(child, f"{path}[{index}]"))
    return findings


def audit_prompt_bytes(prompt_path: Path) -> dict:
    text = prompt_path.read_text(encoding="utf-8")
    snippets = [snippet for snippet in PROMPT_FORBIDDEN_SNIPPETS if snippet in text]
    return {
        "prompt_sha256": sha256_path(prompt_path),
        "forbidden_snippets": snippets,
        "passed": not snippets,
    }


def validate_queue(queue_path: Path, stage: str, prompt_path: Path) -> dict[str, dict]:
    queue = read_json(queue_path)
    cases = queue.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("queue cases must be a nonempty list")
    case_ids = [case.get("case_id") for case in cases]
    if None in case_ids or len(case_ids) != len(set(case_ids)):
        raise ValueError("queue case IDs are missing or duplicated")
    prompt_contract = queue.get("review_protocol", {})
    expected_role = PROMPT_ROLES[(stage, "reviewer")]
    if prompt_contract.get("role") != expected_role:
        raise ValueError("queue review role mismatch")
    if prompt_contract.get("prompt_sha256") != sha256_path(prompt_path):
        raise ValueError("queue does not bind the exact reviewer prompt")
    if prompt_contract.get("raw_response_contract_sha256") != sha256_path(
        raw_response_contract_path(expected_role)
    ):
        raise ValueError("queue does not bind the role-specific raw-response contract")
    forbidden = recursive_forbidden_keys(queue)
    if forbidden:
        raise ValueError(f"queue leaks private/class fields: {forbidden}")
    if stage == "1":
        if any("proposed_target" in case for case in cases):
            raise ValueError("Stage 1 queue contains a proposed target")
        for case in cases:
            evidence = {
                "museum_pair": case["museum_pair"],
                "entity_type": case["entity_type"],
                "sides": case["sides"],
            }
            if canonical_sha256(evidence) != case.get("evidence_sha256"):
                raise ValueError(f"Stage 1 evidence hash mismatch: {case['case_id']}")
            pair = case["museum_pair"]
            if any(len(case["sides"][museum]) != 1 for museum in pair):
                raise ValueError(
                    f"Stage 1 evidence exposes a sub-group cardinality proxy: {case['case_id']}"
                )
            if any(
                set(group) != EVIDENCE_BLOCK_KEYS
                for museum in pair for group in case["sides"][museum]
            ):
                raise ValueError(f"Stage 1 evidence block schema differs: {case['case_id']}")
            group_sets = [
                {group["evidence_group"] for group in case["sides"][museum]}
                for museum in pair
            ]
            if group_sets[0] & group_sets[1]:
                raise ValueError(f"cross-side evidence-group proxy leak: {case['case_id']}")
    else:
        for case in cases:
            evidence = {
                "museum_pair": case["museum_pair"],
                "entity_type": case["entity_type"],
                "sides": case["sides"],
            }
            if canonical_sha256(evidence) != case.get("evidence_sha256"):
                raise ValueError(f"Stage 2 evidence hash mismatch: {case['case_id']}")
            if not isinstance(case.get("proposed_target"), dict):
                raise ValueError(f"Stage 2 proposed target missing: {case['case_id']}")
    return {case["case_id"]: case for case in cases}


def validate_prompt_audit(
    audit_path: Path, auditor_prompt_path: Path, subject_composed_input_path: Path,
    subject_role: str,
) -> dict:
    subject_input = validate_composed_input_file(subject_composed_input_path, subject_role)
    prompt_components = [
        Path(component["path"])
        for component in subject_input["components"]
        if component["label"] in {"review_prompt", "reconciler_prompt"}
    ]
    if len(prompt_components) != 1:
        raise ValueError("subject composed input must contain exactly one subject prompt")
    static = audit_prompt_bytes(prompt_components[0])
    if not static["passed"]:
        raise ValueError(
            f"prompt contains deterministic leakage tokens: {static['forbidden_snippets']}"
        )
    value = read_json(audit_path)
    require_keys(value, {
        "schema_version", "auditor_run", "auditor_prompt", "subject_role",
        "subject_composed_input", "raw_response_contract", "composed_input_sha256",
        "launcher_transcript_format", "launcher_transcript",
        "launcher_transcript_sha256", "full_raw_response",
        "full_raw_response_sha256", "outcome", "findings",
    }, "prompt audit")
    if value["schema_version"] != PROMPT_AUDIT_SCHEMA_VERSION:
        raise ValueError("prompt audit schema version mismatch")
    validate_model_run(value["auditor_run"], "prompt audit auditor_run", "prompt_auditor")
    validate_bound_input(
        value["auditor_prompt"], auditor_prompt_path, "prompt audit auditor_prompt"
    )
    validate_bound_input(
        value["raw_response_contract"], raw_response_contract_path("prompt_auditor"),
        "prompt audit raw_response_contract",
    )
    if value["subject_role"] != subject_role:
        raise ValueError("prompt audit subject role mismatch")
    validate_bound_input(
        value["subject_composed_input"], subject_composed_input_path,
        "prompt audit subject_composed_input",
    )
    expected_composed = composed_input_sha256(
        "prompt_auditor",
        value["auditor_run"]["launcher_envelope"],
        [
            ("launcher_system_prompt", launcher_system_prompt_path("prompt_auditor")),
            ("auditor_prompt", auditor_prompt_path),
            ("raw_response_contract", raw_response_contract_path("prompt_auditor")),
            ("subject_composed_input", subject_composed_input_path),
        ],
    )
    if value["composed_input_sha256"] != expected_composed:
        raise ValueError("prompt audit composed-input SHA-256 mismatch")
    raw = require_nonempty_string(value["full_raw_response"], "prompt audit full_raw_response")
    if value["full_raw_response_sha256"] != sha256_text(raw):
        raise ValueError("prompt audit raw response hash mismatch")
    try:
        raw_value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("prompt audit full raw response must be JSON") from error
    validate_raw_response("prompt_auditor", raw_value)
    if raw_value.get("outcome") != value["outcome"] or raw_value.get("findings") != value["findings"]:
        raise ValueError("prompt audit parsed result does not match full raw response")
    if value["outcome"] != "PASS":
        raise ValueError("prompt audit did not pass")
    if not isinstance(value["findings"], list) or not all(
        isinstance(finding, dict) for finding in value["findings"]
    ):
        raise ValueError("prompt audit findings must be a list")
    for finding in value["findings"]:
        if finding.get("severity") not in {"P0", "P1", "P2", "P3"}:
            raise ValueError("prompt audit finding severity is invalid")
        require_nonempty_string(finding.get("evidence"), "prompt audit finding evidence")
    blockers = [
        finding for finding in value["findings"]
        if finding.get("severity") in {"P0", "P1", "P2"}
    ]
    if blockers:
        raise ValueError("prompt audit contains blocking findings")
    transcript = require_nonempty_string(
        value["launcher_transcript"], "prompt audit launcher_transcript"
    )
    if value["launcher_transcript_sha256"] != sha256_text(transcript):
        raise ValueError("prompt audit launcher transcript hash mismatch")
    validate_launcher_transcript(
        value["launcher_transcript_format"], transcript, raw, value["auditor_run"],
        "prompt_auditor", expected_composed, "prompt audit launcher transcript",
    )
    return value


def validate_citations(decision: dict, label: str) -> None:
    citations = decision.get("citations")
    exceptions = decision.get("artifact_exceptions")
    if not isinstance(citations, list) or not all(
        is_valid_https_url(url) for url in citations
    ):
        raise ValueError(f"{label}.citations must contain only HTTPS URLs")
    if not isinstance(exceptions, list) or not all(
        isinstance(item, str) and item.strip() for item in exceptions
    ):
        raise ValueError(f"{label}.artifact_exceptions must contain nonempty strings")
    if not citations and not exceptions:
        raise ValueError(f"{label} requires a citation or explicit artifact exception")


def validate_stage_1_outcome_pair(decision: dict, label: str) -> None:
    if (
        decision.get("same_entity") == "different_entity"
        and decision.get("useful_granularity") == "useful"
    ):
        raise ValueError(
            f"{label} cannot call a different-entity connection useful"
        )


def validate_review_package(
    package_path: Path, queue_path: Path, prompt_path: Path, prompt_audit_path: Path,
    auditor_prompt_path: Path, stage: str,
) -> dict:
    audit_preview = read_json(prompt_audit_path)
    subject_input_path = Path(audit_preview.get("subject_composed_input", {}).get("path", ""))
    audit_value = validate_prompt_audit(
        prompt_audit_path, auditor_prompt_path, subject_input_path,
        PROMPT_ROLES[(stage, "reviewer")],
    )
    cases = validate_queue(queue_path, stage, prompt_path)
    value = read_json(package_path)
    require_keys(value, {
        "schema_version", "role", "run", "prompt", "queue", "prompt_audit",
        "raw_response_contract", "composed_input_sha256", "launcher_transcript_format",
        "launcher_transcript", "launcher_transcript_sha256", "full_raw_response",
        "full_raw_response_sha256", "decisions",
    }, "review package")
    if value["schema_version"] != REVIEW_SCHEMA_VERSION:
        raise ValueError("review package schema version mismatch")
    if value["role"] != PROMPT_ROLES[(stage, "reviewer")]:
        raise ValueError("review package role mismatch")
    validate_model_run(value["run"], "review run", value["role"])
    validate_bound_input(value["prompt"], prompt_path, "review prompt")
    validate_bound_input(value["queue"], queue_path, "review queue")
    validate_bound_input(value["prompt_audit"], prompt_audit_path, "review prompt_audit")
    validate_bound_input(
        value["raw_response_contract"], raw_response_contract_path(value["role"]),
        "review raw_response_contract",
    )
    expected_composed = composed_input_sha256(
        value["role"],
        value["run"]["launcher_envelope"],
        [
            ("launcher_system_prompt", launcher_system_prompt_path(value["role"])),
            ("review_prompt", prompt_path),
            ("raw_response_contract", raw_response_contract_path(value["role"])),
            ("review_queue", queue_path),
        ],
    )
    if value["composed_input_sha256"] != expected_composed:
        raise ValueError("review composed-input SHA-256 mismatch")
    if audit_value["subject_composed_input"]["sha256"] != expected_composed:
        raise ValueError("review prompt audit does not bind the exact subject input")
    decisions = value["decisions"]
    ids = [decision.get("case_id") for decision in decisions]
    if len(ids) != len(set(ids)) or set(ids) != set(cases):
        raise ValueError("review decisions must cover the queue exactly once")
    outcome_fields = STAGE_OUTCOMES[stage]
    required = {
        "case_id", "evidence_sha256", *outcome_fields, "reasoning", "citations",
        "artifact_exceptions",
    }
    for decision in decisions:
        label = f"review decision {decision.get('case_id')}"
        require_keys(decision, required, label)
        case = cases[decision["case_id"]]
        if decision["evidence_sha256"] != case["evidence_sha256"]:
            raise ValueError(f"{label} evidence hash mismatch")
        for field, allowed in outcome_fields.items():
            if decision[field] not in allowed:
                raise ValueError(f"{label} invalid {field}")
        if stage == "1":
            validate_stage_1_outcome_pair(decision, label)
        require_nonempty_string(decision["reasoning"], f"{label}.reasoning")
        validate_citations(decision, label)
    raw = require_nonempty_string(value["full_raw_response"], "review full_raw_response")
    if value["full_raw_response_sha256"] != sha256_text(raw):
        raise ValueError("review raw response hash mismatch")
    try:
        raw_value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("review full raw response must be JSON") from error
    validate_raw_response(value["role"], raw_value)
    if raw_value.get("decisions") != decisions:
        raise ValueError("review decisions do not equal the full raw response decisions")
    transcript = require_nonempty_string(
        value["launcher_transcript"], "review launcher_transcript"
    )
    if value["launcher_transcript_sha256"] != sha256_text(transcript):
        raise ValueError("review launcher transcript hash mismatch")
    validate_launcher_transcript(
        value["launcher_transcript_format"], transcript, raw, value["run"], value["role"],
        expected_composed, "review launcher transcript", require_web=True,
    )
    return value


def _source_outcomes(review_hashes: list[str], review_maps: list[dict], case_id: str, field: str) -> list[dict]:
    return sorted([
        {"review_sha256": review_hash, "outcome": decisions[case_id][field]}
        for review_hash, decisions in zip(review_hashes, review_maps, strict=True)
    ], key=lambda item: item["review_sha256"])


def validate_consensus_package(
    consensus_path: Path, queue_path: Path, reviewer_prompt_path: Path,
    reviewer_prompt_audit_path: Path, reviewer_paths: list[Path],
    reconciler_prompt_path: Path, reconciler_prompt_audit_path: Path,
    auditor_prompt_path: Path, stage: str,
) -> dict:
    if len(reviewer_paths) != 2 or reviewer_paths[0] == reviewer_paths[1]:
        raise ValueError("exactly two distinct source reviewer artifacts are required")
    reviews = [
        validate_review_package(
            path, queue_path, reviewer_prompt_path, reviewer_prompt_audit_path,
            auditor_prompt_path, stage,
        )
        for path in reviewer_paths
    ]
    review_hashes = [sha256_path(path) for path in reviewer_paths]
    request_ids = [review["run"]["request_id"] for review in reviews]
    if len(set(review_hashes)) != 2 or len(set(request_ids)) != 2:
        raise ValueError("source reviews must be independent artifacts with distinct request IDs")
    reconciler_audit_preview = read_json(reconciler_prompt_audit_path)
    reconciler_subject_input_path = Path(
        reconciler_audit_preview.get("subject_composed_input", {}).get("path", "")
    )
    reconciler_audit = validate_prompt_audit(
        reconciler_prompt_audit_path, auditor_prompt_path,
        reconciler_subject_input_path, PROMPT_ROLES[(stage, "reconciler")],
    )
    cases = validate_queue(queue_path, stage, reviewer_prompt_path)
    value = read_json(consensus_path)
    require_keys(value, {
        "schema_version", "role", "run", "prompt", "queue", "prompt_audit",
        "source_reviews", "raw_response_contract", "composed_input_sha256",
        "launcher_transcript_format", "launcher_transcript",
        "launcher_transcript_sha256", "full_raw_response", "full_raw_response_sha256",
        "decisions",
    }, "consensus package")
    if value["schema_version"] != CONSENSUS_SCHEMA_VERSION:
        raise ValueError("consensus package schema version mismatch")
    if value["role"] != PROMPT_ROLES[(stage, "reconciler")]:
        raise ValueError("consensus role mismatch")
    validate_model_run(value["run"], "consensus run", value["role"])
    if value["run"]["request_id"] in request_ids:
        raise ValueError("consensus request ID must differ from both source reviews")
    validate_bound_input(value["prompt"], reconciler_prompt_path, "consensus prompt")
    validate_bound_input(value["queue"], queue_path, "consensus queue")
    validate_bound_input(value["prompt_audit"], reconciler_prompt_audit_path, "consensus prompt_audit")
    validate_bound_input(
        value["raw_response_contract"], raw_response_contract_path(value["role"]),
        "consensus raw_response_contract",
    )
    expected_sources = sorted(
        ({"path": str(path), "sha256": sha256_path(path)} for path in reviewer_paths),
        key=lambda item: item["sha256"],
    )
    if sorted(value["source_reviews"], key=lambda item: item.get("sha256", "")) != expected_sources:
        raise ValueError("consensus source reviewer bindings mismatch")
    ordered_reviewer_paths = sorted(reviewer_paths, key=sha256_path)
    expected_composed = composed_input_sha256(
        value["role"],
        value["run"]["launcher_envelope"],
        [
            ("launcher_system_prompt", launcher_system_prompt_path(value["role"])),
            ("reconciler_prompt", reconciler_prompt_path),
            ("raw_response_contract", raw_response_contract_path(value["role"])),
            ("review_queue", queue_path),
            ("source_review_1", ordered_reviewer_paths[0]),
            ("source_review_2", ordered_reviewer_paths[1]),
        ],
    )
    if value["composed_input_sha256"] != expected_composed:
        raise ValueError("consensus composed-input SHA-256 mismatch")
    if reconciler_audit["subject_composed_input"]["sha256"] != expected_composed:
        raise ValueError("reconciler prompt audit does not bind the exact subject input")
    decisions = value["decisions"]
    ids = [decision.get("case_id") for decision in decisions]
    if len(ids) != len(set(ids)) or set(ids) != set(cases):
        raise ValueError("consensus decisions must cover the queue exactly once")
    outcome_fields = STAGE_OUTCOMES[stage]
    review_maps = [{row["case_id"]: row for row in review["decisions"]} for review in reviews]
    required = {
        "case_id", "evidence_sha256", *outcome_fields, "field_resolutions", "reasoning",
        "citations", "artifact_exceptions",
    }
    for decision in decisions:
        case_id = decision.get("case_id")
        label = f"consensus decision {case_id}"
        require_keys(decision, required, label)
        if decision["evidence_sha256"] != cases[case_id]["evidence_sha256"]:
            raise ValueError(f"{label} evidence hash mismatch")
        require_nonempty_string(decision["reasoning"], f"{label}.reasoning")
        validate_citations(decision, label)
        resolutions = decision["field_resolutions"]
        if not isinstance(resolutions, dict) or set(resolutions) != set(outcome_fields):
            raise ValueError(f"{label} field resolutions are incomplete")
        for field, allowed in outcome_fields.items():
            if decision[field] not in allowed:
                raise ValueError(f"{label} invalid {field}")
            source_outcomes = _source_outcomes(review_hashes, review_maps, case_id, field)
            resolution = resolutions[field]
            require_keys(resolution, {"method", "source_outcomes", "rationale", "citations"}, f"{label}.{field}")
            if resolution["source_outcomes"] != source_outcomes:
                raise ValueError(f"{label}.{field} source outcomes mismatch")
            source_values = {item["outcome"] for item in source_outcomes}
            require_nonempty_string(resolution["rationale"], f"{label}.{field}.rationale")
            if not isinstance(resolution["citations"], list) or not all(
                is_valid_https_url(url) for url in resolution["citations"]
            ):
                raise ValueError(f"{label}.{field}.citations must contain only HTTPS URLs")
            if len(source_values) == 1:
                if resolution["method"] != "agreement" or decision[field] != next(iter(source_values)):
                    raise ValueError(f"{label}.{field} must preserve exact reviewer agreement")
            else:
                if resolution["method"] != "explicit_cited_override":
                    raise ValueError(f"{label}.{field} disagreement requires explicit cited override")
                if not isinstance(resolution["citations"], list) or not resolution["citations"] or not all(
                    is_valid_https_url(url) for url in resolution["citations"]
                ):
                    raise ValueError(f"{label}.{field} override requires HTTPS citations")
        if stage == "1":
            validate_stage_1_outcome_pair(decision, label)
    raw = require_nonempty_string(value["full_raw_response"], "consensus full_raw_response")
    if value["full_raw_response_sha256"] != sha256_text(raw):
        raise ValueError("consensus raw response hash mismatch")
    try:
        raw_value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("consensus full raw response must be JSON") from error
    validate_raw_response(value["role"], raw_value)
    if raw_value.get("decisions") != decisions:
        raise ValueError("consensus decisions do not equal the full raw response decisions")
    transcript = require_nonempty_string(
        value["launcher_transcript"], "consensus launcher_transcript"
    )
    if value["launcher_transcript_sha256"] != sha256_text(transcript):
        raise ValueError("consensus launcher transcript hash mismatch")
    validate_launcher_transcript(
        value["launcher_transcript_format"], transcript, raw, value["run"], value["role"],
        expected_composed, "consensus launcher transcript", require_web=any(
            resolution["method"] == "explicit_cited_override"
            for decision in decisions
            for resolution in decision["field_resolutions"].values()
        ),
    )
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("validate-prompt-audit")
    audit.add_argument("--subject-composed-input", type=Path, required=True)
    audit.add_argument(
        "--subject-role",
        choices=sorted(set(PROMPT_ROLES.values())),
        required=True,
    )
    audit.add_argument("--auditor-prompt", type=Path, required=True)
    audit.add_argument("--audit", type=Path, required=True)
    reviewer = subparsers.add_parser("validate-reviewer")
    reviewer.add_argument("--stage", choices=("1", "2"), required=True)
    reviewer.add_argument("--queue", type=Path, required=True)
    reviewer.add_argument("--prompt", type=Path, required=True)
    reviewer.add_argument("--prompt-audit", type=Path, required=True)
    reviewer.add_argument("--auditor-prompt", type=Path, required=True)
    reviewer.add_argument("--review", type=Path, required=True)
    consensus = subparsers.add_parser("validate-consensus")
    consensus.add_argument("--stage", choices=("1", "2"), required=True)
    consensus.add_argument("--queue", type=Path, required=True)
    consensus.add_argument("--reviewer-prompt", type=Path, required=True)
    consensus.add_argument("--reviewer-prompt-audit", type=Path, required=True)
    consensus.add_argument("--review", type=Path, action="append", required=True)
    consensus.add_argument("--reconciler-prompt", type=Path, required=True)
    consensus.add_argument("--reconciler-prompt-audit", type=Path, required=True)
    consensus.add_argument("--auditor-prompt", type=Path, required=True)
    consensus.add_argument("--consensus", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "validate-prompt-audit":
        result = validate_prompt_audit(
            args.audit, args.auditor_prompt, args.subject_composed_input,
            args.subject_role,
        )
    elif args.command == "validate-reviewer":
        result = validate_review_package(
            args.review, args.queue, args.prompt, args.prompt_audit,
            args.auditor_prompt, args.stage,
        )
    else:
        result = validate_consensus_package(
            args.consensus, args.queue, args.reviewer_prompt,
            args.reviewer_prompt_audit, args.review, args.reconciler_prompt,
            args.reconciler_prompt_audit, args.auditor_prompt, args.stage,
        )
    print(json.dumps({"status": "VALID", "artifact_sha256": sha256_path(
        args.audit if args.command == "validate-prompt-audit" else (
            args.review if args.command == "validate-reviewer" else args.consensus
        )
    )}, indent=2))


if __name__ == "__main__":
    main()
