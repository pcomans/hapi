"""Authoritative JSON Schema validation for every versioned contract document."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


class SchemaValidationError(ValueError):
    pass


def validate_schema(instance: object, schema_path: Path, label: str) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.absolute_path))
    if errors:
        rendered = []
        for error in errors:
            location = "$" + "".join(
                f"[{part}]" if isinstance(part, int) else f".{part}"
                for part in error.absolute_path
            )
            rendered.append(f"{location}: {error.message}")
        raise SchemaValidationError(f"{label} schema validation failed: {'; '.join(rendered)}")


def meta_validate_schema_directory(schema_directory: Path) -> list[str]:
    """Meta-validate every schema, without claiming any instance was executed."""
    paths = sorted(schema_directory.glob("*.schema.json"))
    if not paths:
        raise SchemaValidationError("schema directory contains no contract schemas")
    for path in paths:
        Draft202012Validator.check_schema(
            json.loads(path.read_text(encoding="utf-8"))
        )
    return [path.name for path in paths]


def execute_schema_contract_tests(schema_directory: Path, cases_path: Path) -> dict:
    """Execute one valid and one-or-more adversarial invalid cases per schema."""
    document = json.loads(cases_path.read_text(encoding="utf-8"))
    if document.get("schema_version") != "site-graph-v0-schema-test-cases/1":
        raise SchemaValidationError("unsupported schema-test-cases schema_version")
    cases = document.get("cases")
    if not isinstance(cases, dict):
        raise SchemaValidationError("schema-test-cases cases must be an object")
    schema_names = meta_validate_schema_directory(schema_directory)
    if set(cases) != set(schema_names):
        raise SchemaValidationError(
            "schema-test-cases inventory mismatch: "
            f"missing={sorted(set(schema_names) - set(cases))}, "
            f"extra={sorted(set(cases) - set(schema_names))}"
        )
    invalid_count = 0
    for name in schema_names:
        case = cases[name]
        if not isinstance(case, dict) or set(case) != {"valid", "invalid"}:
            raise SchemaValidationError(f"invalid schema-test-cases entry: {name}")
        invalid = case["invalid"]
        if not isinstance(invalid, list) or not invalid:
            raise SchemaValidationError(f"schema lacks adversarial invalid cases: {name}")
        schema_path = schema_directory / name
        validate_schema(case["valid"], schema_path, f"{name} representative valid")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for index, instance in enumerate(invalid):
            if not list(validator.iter_errors(instance)):
                raise SchemaValidationError(
                    f"{name} adversarial invalid case {index} unexpectedly passed"
                )
            invalid_count += 1
    return {
        "meta_valid_schema_count": len(schema_names),
        "representative_valid_instance_count": len(schema_names),
        "adversarial_invalid_instance_count": invalid_count,
        "schemas": schema_names,
    }
