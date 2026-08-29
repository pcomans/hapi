#!/usr/bin/env python3
"""Read-only release authentication and real-private-corpus semantic validation."""

from __future__ import annotations

import argparse
import ast
import collections
import hashlib
import importlib
import inspect
import json
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

PUBLIC_BASELINE_OUTPUTS = (
    "baseline-metrics.json",
    "baseline-node-scope.json",
    "planned-opportunity-summary.json",
    "private-ledger-digests.json",
    "top-unmatched-components.json",
)

EVALUATION_RELATIVE = Path("docs/evaluations/site-graph-v0")
MANIFEST_RELATIVE = EVALUATION_RELATIVE / "release-manifest.json"
RELEASE_CONTRACT_RELATIVE = EVALUATION_RELATIVE / "scripts/release_contract.py"
BOOTSTRAP_MANIFEST_VERSION = "site-graph-v0-release-manifest/2"
BOOTSTRAP_CONTRACT_VERSION = "site-graph-v0-release/4"
BOOTSTRAP_PYCACHE_EXCLUSION = (
    "Python cache directories (__pycache__, .pytest_cache) and bytecode suffixes "
    "(.pyc, .pyo) are runtime by-products, are never required release files, and are "
    "ignored during exact-inventory discovery. No other file or directory is ignored."
)
BOOTSTRAP_INVENTORY_RULE = (
    "Exactly REQUIRED_RELEASE_FILES in scripts/release_contract.py. Any addition, "
    "removal, or cache-exclusion change requires a separately reviewed "
    "contract-version migration."
)
BOOTSTRAP_REQUIRED_PATHS = frozenset(
    {
        RELEASE_CONTRACT_RELATIVE.as_posix(),
        (EVALUATION_RELATIVE / "scripts/integrity.py").as_posix(),
        (EVALUATION_RELATIVE / "scripts/validate_contract.py").as_posix(),
    }
)
IGNORED_PARTS = frozenset({"__pycache__", ".pytest_cache"})
IGNORED_SUFFIXES = frozenset({".pyc", ".pyo"})

FORBIDDEN_BOUNDARY_BASENAMES = frozenset(
    {
        "frozen-record-evidence.ndjson.gz",
        "frozen-opportunity-source.ndjson.gz",
        "planned-opportunity-queue.json",
        "private-record-evidence.ndjson.gz",
        "private-opportunity-source.ndjson.gz",
        "private-opportunity-ledger.json",
    }
)
FORBIDDEN_BULK_SUFFIXES = (
    ".ndjson",
    ".ndjson.gz",
    ".jsonl",
    ".jsonl.gz",
    ".csv",
    ".csv.gz",
    ".tsv",
    ".tsv.gz",
    ".parquet",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".tar",
    ".tar.gz",
    ".tgz",
    ".zip",
)
FORBIDDEN_DUMP_NAME = re.compile(
    r"(?:^|[-_.])(?:"
    r"artifact[-_.]?ids?(?:[-_.](?:dump|export|expansion|membership|rows?))?"
    r"|mentions?(?:[-_.](?:dump|export|rows?|source|evidence|texts?))?"
    r")(?:[-_.]|$)",
    re.IGNORECASE,
)


class ReleaseIntegrityPreflightError(RuntimeError):
    """The target release could not be authenticated without executing its code."""


def _bootstrap_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _manifest_entry_is_valid(relative: object, expected: object) -> bool:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        return False
    path = Path(relative)
    return (
        not path.is_absolute()
        and relative == path.as_posix()
        and ".." not in path.parts
        and isinstance(expected, dict)
        and set(expected) == {"bytes", "sha256"}
        and type(expected["bytes"]) is int
        and expected["bytes"] >= 0
        and isinstance(expected["sha256"], str)
        and bool(re.fullmatch(r"[0-9a-f]{64}", expected["sha256"]))
    )


def _contract_literal(node: ast.AST, values: dict[str, object]) -> object:
    """Evaluate the tiny declarative subset used by release_contract.py."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and node.id in values:
        return values[node.id]
    if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        items: list[object] = []
        for child in node.elts:
            if isinstance(child, ast.Starred):
                expanded = _contract_literal(child.value, values)
                if not isinstance(expanded, (set, frozenset, list, tuple)):
                    raise ReleaseIntegrityPreflightError(
                        "release contract contains a non-collection starred value"
                    )
                items.extend(expanded)
            else:
                items.append(_contract_literal(child, values))
        if isinstance(node, ast.Set):
            return set(items)
        if isinstance(node, ast.Tuple):
            return tuple(items)
        return items
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "frozenset"
        and len(node.args) == 1
        and not node.keywords
    ):
        value = _contract_literal(node.args[0], values)
        if not isinstance(value, (set, frozenset, list, tuple)):
            raise ReleaseIntegrityPreflightError(
                "release contract frozenset input is not declarative"
            )
        return frozenset(value)
    raise ReleaseIntegrityPreflightError(
        f"release contract uses unsupported executable syntax: {type(node).__name__}"
    )


def _static_release_contract(path: Path) -> dict[str, object]:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as error:
        raise ReleaseIntegrityPreflightError(
            f"cannot statically read release inventory contract: {error}"
        ) from error
    wanted = {
        "CONTRACT_VERSION",
        "PYCACHE_EXCLUSION",
        "CI_RELEASE_FILES",
        "REQUIRED_RELEASE_FILES",
    }
    values: dict[str, object] = {}
    for statement in tree.body:
        if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
            continue
        if isinstance(statement, ast.Assign):
            if len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
                continue
            name = statement.targets[0].id
            value_node = statement.value
        else:
            if not isinstance(statement.target, ast.Name) or statement.value is None:
                continue
            name = statement.target.id
            value_node = statement.value
        if name in wanted:
            values[name] = _contract_literal(value_node, values)
    if set(values) != wanted:
        raise ReleaseIntegrityPreflightError(
            "release inventory contract lacks required declarative constants: "
            f"{sorted(wanted - set(values))}"
        )
    for name in ("CI_RELEASE_FILES", "REQUIRED_RELEASE_FILES"):
        value = values[name]
        if not isinstance(value, (set, frozenset)) or not value or not all(
            isinstance(item, str) and item for item in value
        ):
            raise ReleaseIntegrityPreflightError(
                f"release inventory contract has invalid {name}"
            )
    return values


def _is_main_guard(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Compare)
        and isinstance(node.left, ast.Name)
        and node.left.id == "__name__"
        and len(node.ops) == 1
        and isinstance(node.ops[0], ast.Eq)
        and len(node.comparators) == 1
        and isinstance(node.comparators[0], ast.Constant)
        and node.comparators[0].value == "__main__"
    )


SAFE_DECORATORS = {"contextlib.contextmanager", "dataclasses.dataclass"}
ALLOWED_RELEASE_IMPORT_MODULES = frozenset(
    {
        "argparse", "ast", "base64", "collections", "contextlib", "copy",
        "datetime", "gzip", "hashlib", "importlib", "inspect", "io", "json",
        "os", "platform", "re", "secrets", "shutil", "subprocess", "sys",
        "tarfile", "tempfile", "unicodedata", "uuid",
    }
)
ALLOWED_RELEASE_FROM_IMPORTS = {
    "__future__": {"annotations"},
    "build_baseline": {
        "build_metrics", "build_opportunity_queue", "canonical_json_sha256",
        "canonical_list_sha256", "gzip_ledger_digest", "read_gzip_jsonl",
        "read_json", "resolution_state", "sha256", "validate_site_mention",
        "write_gzip_jsonl", "write_json",
    },
    "candidate_git": {
        "CandidateGitError", "blob_oid", "ed25519_key_id", "is_ancestor",
        "normalize_relative_path", "read_authenticated_bytes",
        "read_authenticated_json", "read_bytes", "resolve_commit",
        "verify_ed25519_signature",
    },
    "collections": {"Counter", "defaultdict"},
    "compare_baseline_runs": {"atomic_write_json", "compare"},
    "contract_constants": {
        "CONCENTRATION_MAXIMUM_INCREASE", "MAXIMUM_NEWLY_BLOCKING_FRACTION",
        "MINIMUM_AFFECTED_FRACTION", "MINIMUM_GAINED_IDENTITIES", "MUSEUMS",
        "OPPORTUNITY_MUSEUM_PROTECTION", "OPPORTUNITY_TOTAL_SIGNATURES", "PAIRS",
        "REVIEWS_PER_CREDITED_DECISION",
    },
    "corpus_archive": {"authenticated_corpus", "validate_archive_attestation"},
    "cryptography.exceptions": {"InvalidSignature"},
    "cryptography.hazmat.primitives.asymmetric.ed25519": {"Ed25519PublicKey"},
    "dataclasses": {"dataclass", "field"},
    "datetime": {"datetime"},
    "fractions": {"Fraction"},
    "integrity": {
        "EVALUATION_RELATIVE", "MANIFEST_NAME", "discovered_release_files",
        "sha256", "verify_release",
    },
    "itertools": {"combinations"},
    "jsonschema": {"Draft202012Validator", "FormatChecker"},
    "metrics_core": {"TOP_K", "concentration", "partition_scopes", "ratio"},
    "pathlib": {"Path", "PurePosixPath"},
    "private_ledgers": {"verify_private_ledgers"},
    "release_contract": {
        "CI_RELEASE_FILES", "CONTRACT_VERSION", "PYCACHE_EXCLUSION",
        "REQUIRED_RELEASE_FILES", "validation_input_bindings",
    },
    "review_auth": {
        "ArtifactUsageTracker", "ReviewAuthenticationError",
        "authenticate_prompt_audit", "authenticate_review_artifact",
        "authenticate_semantic_prompt_audit", "canonical_forbidden_values",
        "canonical_json_bytes", "canonical_sha256", "load_reviewer_registry",
        "require_distinct_registered_reviewers", "strict_json_object",
        "validate_reviewer_registry",
    },
    "run_baseline": {"DETERMINISTIC_OUTPUTS", "FINAL_OUTPUTS", "run", "sha256"},
    "runtime_attestation": {"build_runtime_attestation", "validate_runtime_attestation"},
    "schema_validation": {
        "SchemaValidationError", "execute_schema_contract_tests", "validate_schema",
    },
    "source_exports": {
        "TRUSTED_SOURCE_EXPORTERS_RELATIVE", "authenticate_source_export",
        "load_source_exporter_policy", "validate_source_exporter_registry",
    },
    "trusted_completion": {"verify_trusted_completion"},
    "typing": {"Callable", "Iterable", "Iterator", "Sequence"},
    "validate_contract": {"semantic_report_for_release_generation"},
}


def _module_bindings(tree: ast.Module) -> tuple[dict[str, str], set[str]]:
    imports: dict[str, str] = {}
    assigned: set[str] = set()
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                bound = alias.asname or alias.name.split(".", 1)[0]
                imports[bound] = alias.name if alias.asname else bound
        elif isinstance(statement, ast.ImportFrom) and statement.module:
            for alias in statement.names:
                if alias.name != "*":
                    imports[alias.asname or alias.name] = (
                        f"{statement.module}.{alias.name}"
                    )
        elif isinstance(statement, ast.Assign):
            assigned.update(
                target.id for target in statement.targets if isinstance(target, ast.Name)
            )
        elif isinstance(statement, ast.AnnAssign) and isinstance(
            statement.target, ast.Name
        ):
            assigned.add(statement.target.id)
        elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            assigned.add(statement.name)
    return imports, assigned


def _qualified_reference(
    node: ast.AST, imports: dict[str, str], assigned: set[str]
) -> str | None:
    if isinstance(node, ast.Name):
        if node.id in assigned:
            return None
        if node.id in imports:
            return imports[node.id]
        if node.id in {"frozenset", "list"}:
            return f"builtins.{node.id}"
        return None
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        root = node.value.id
        if root in assigned or root not in imports:
            return None
        return f"{imports[root]}.{node.attr}"
    return None


def _initializer_expression_kind(
    node: ast.AST,
    imports: dict[str, str],
    assigned: set[str],
    value_kinds: dict[str, str],
) -> str | None:
    """Infer an inert built-in value only for exact release-needed expressions.

    A recognized callee name is deliberately insufficient: several otherwise
    ordinary constructors and serializers invoke protocols or callbacks supplied
    through their arguments.  Every allowed call below therefore validates its
    complete positional and keyword shape before it receives a kind.
    """
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return "string"
        if isinstance(node.value, bool):
            return "json_boolean"
        if node.value is None:
            return "json_null"
        if isinstance(node.value, (int, float)):
            return "json_number"
        if isinstance(node.value, bytes):
            return "bytes"
        return None
    if isinstance(node, ast.Name):
        if node.id in value_kinds:
            return value_kinds[node.id]
        if node.id == "__file__" and node.id not in imports and node.id not in assigned:
            return "string"
        return None
    if isinstance(node, ast.Starred):
        kind = _initializer_expression_kind(
            node.value, imports, assigned, value_kinds
        )
        return kind if kind in {"tuple", "list", "set", "frozenset"} else None
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        element_kinds = [
            _initializer_expression_kind(item, imports, assigned, value_kinds)
            for item in node.elts
        ]
        if any(kind is None for kind in element_kinds):
            return None
        if isinstance(node, ast.Tuple):
            return (
                "json_tuple"
                if all(kind in _JSON_VALUE_KINDS for kind in element_kinds)
                else "tuple"
            )
        if isinstance(node, ast.List):
            return (
                "json_list"
                if all(kind in _JSON_VALUE_KINDS for kind in element_kinds)
                else "list"
            )
        return (
            "set"
            if all(
                kind
                in {
                    "string",
                    "bytes",
                    "json_boolean",
                    "json_null",
                    "json_number",
                    "json_tuple",
                    "set",
                    "frozenset",
                }
                for kind in element_kinds
            )
            else None
        )
    if isinstance(node, ast.Dict):
        key_kinds = [
            _initializer_expression_kind(key, imports, assigned, value_kinds)
            if key is not None
            else None
            for key in node.keys
        ]
        value_kinds_found = [
            _initializer_expression_kind(value, imports, assigned, value_kinds)
            for value in node.values
        ]
        if all(kind == "string" for kind in key_kinds) and all(
            kind in _JSON_VALUE_KINDS for kind in value_kinds_found
        ):
            return "json_dict"
        return (
            "dict"
            if all(kind == "string" for kind in key_kinds)
            and all(kind is not None for kind in value_kinds_found)
            else None
        )
    if isinstance(node, ast.Call):
        direct = _qualified_reference(node.func, imports, assigned)
        if direct in {"builtins.frozenset", "builtins.list"}:
            if len(node.args) != 1 or node.keywords:
                return None
            iterable_kind = _initializer_expression_kind(
                node.args[0], imports, assigned, value_kinds
            )
            if iterable_kind not in {
                "tuple", "json_tuple", "list", "json_list", "set", "frozenset"
            }:
                return None
            if direct == "builtins.frozenset":
                return (
                    "frozenset"
                    if iterable_kind in {"set", "frozenset"}
                    else None
                )
            return (
                "json_list"
                if iterable_kind in {"json_tuple", "json_list"}
                else "list"
            )
        if direct == "dataclasses.field":
            return (
                "field"
                if not node.args
                and len(node.keywords) == 1
                and node.keywords[0].arg == "default_factory"
                and isinstance(node.keywords[0].value, ast.Name)
                and node.keywords[0].value.id == "dict"
                and "dict" not in imports
                and "dict" not in assigned
                else None
            )
        if direct == "fractions.Fraction":
            return (
                "fraction"
                if len(node.args) == 2
                and not node.keywords
                and all(_is_static_integer(argument) for argument in node.args)
                else None
            )
        if direct == "hashlib.sha256":
            return (
                "hash"
                if len(node.args) == 1
                and not node.keywords
                and _initializer_expression_kind(
                    node.args[0], imports, assigned, value_kinds
                )
                == "bytes"
                else None
            )
        if direct == "json.dumps":
            keyword_values = {
                keyword.arg: keyword.value
                for keyword in node.keywords
                if keyword.arg is not None
            }
            expected_options = {
                "ensure_ascii": False,
                "sort_keys": True,
                "allow_nan": False,
            }
            static_options = all(
                isinstance(keyword_values.get(name), ast.Constant)
                and keyword_values[name].value is expected
                for name, expected in expected_options.items()
            )
            separators = keyword_values.get("separators")
            static_separators = (
                isinstance(separators, ast.Tuple)
                and len(separators.elts) == 2
                and all(isinstance(item, ast.Constant) for item in separators.elts)
                and tuple(item.value for item in separators.elts) == (",", ":")
            )
            return (
                "string"
                if len(node.args) == 1
                and set(keyword_values) == {*expected_options, "separators"}
                and len(node.keywords) == len(keyword_values)
                and static_options
                and static_separators
                and _initializer_expression_kind(
                    node.args[0], imports, assigned, value_kinds
                )
                in _JSON_VALUE_KINDS
                else None
            )
        if direct == "pathlib.Path":
            return (
                "path"
                if len(node.args) == 1
                and not node.keywords
                and _initializer_expression_kind(
                    node.args[0], imports, assigned, value_kinds
                )
                == "string"
                else None
            )
        if direct == "re.compile":
            flags_are_static = len(node.args) == 1 or (
                len(node.args) == 2 and _is_static_regex_flag(node.args[1], imports, assigned)
            )
            return (
                "regex"
                if len(node.args) in {1, 2}
                and not node.keywords
                and flags_are_static
                and _initializer_expression_kind(
                    node.args[0], imports, assigned, value_kinds
                )
                == "string"
                else None
            )
        if isinstance(node.func, ast.Attribute):
            receiver_kind = _initializer_expression_kind(
                node.func.value, imports, assigned, value_kinds
            )
            if (
                receiver_kind == "hash"
                and node.func.attr == "hexdigest"
                and not node.args
                and not node.keywords
            ):
                return "string"
            if (
                receiver_kind == "path"
                and node.func.attr in {"as_posix", "resolve"}
                and not node.args
                and not node.keywords
            ):
                return "string" if node.func.attr == "as_posix" else "path"
            if (
                receiver_kind == "string"
                and node.func.attr == "encode"
                and len(node.args) == 1
                and not node.keywords
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "utf-8"
            ):
                return "bytes"
        return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left_kind = _initializer_expression_kind(
            node.left, imports, assigned, value_kinds
        )
        right_kind = _initializer_expression_kind(
            node.right, imports, assigned, value_kinds
        )
        return "path" if left_kind == "path" and right_kind == "string" else None
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.BitOr, ast.Sub)):
        left_kind = _initializer_expression_kind(
            node.left, imports, assigned, value_kinds
        )
        right_kind = _initializer_expression_kind(
            node.right, imports, assigned, value_kinds
        )
        if left_kind in {"set", "frozenset"} and right_kind in {
            "set", "frozenset"
        }:
            return left_kind
        return None
    if isinstance(node, ast.Subscript):
        receiver_kind = _initializer_expression_kind(
            node.value, imports, assigned, value_kinds
        )
        if receiver_kind == "path_parents" and _is_static_integer(node.slice):
            return "path"
        direct = _qualified_reference(node.value, imports, assigned)
        if (
            direct == "typing.Callable"
            and isinstance(node.slice, ast.Tuple)
            and len(node.slice.elts) == 2
            and isinstance(node.slice.elts[0], ast.List)
            and all(
                isinstance(item, ast.Name)
                and item.id in {"bytes", "dict", "str"}
                and item.id not in imports
                and item.id not in assigned
                for item in node.slice.elts[0].elts
            )
            and isinstance(node.slice.elts[1], ast.Name)
            and node.slice.elts[1].id in {"bytes", "dict", "str"}
            and node.slice.elts[1].id not in imports
            and node.slice.elts[1].id not in assigned
        ):
            return "type_expression"
        return None
    if isinstance(node, ast.Attribute) and node.attr == "parent":
        receiver_kind = _initializer_expression_kind(
            node.value, imports, assigned, value_kinds
        )
        return "path" if receiver_kind == "path" else None
    if isinstance(node, ast.Attribute) and node.attr == "parents":
        receiver_kind = _initializer_expression_kind(
            node.value, imports, assigned, value_kinds
        )
        return "path_parents" if receiver_kind == "path" else None
    return None


_JSON_VALUE_KINDS = {
    "string", "json_boolean", "json_null", "json_number", "json_tuple",
    "json_list", "json_dict",
}


def _is_static_integer(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return isinstance(node.value, int) and not isinstance(node.value, bool)
    return (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, (ast.UAdd, ast.USub))
        and isinstance(node.operand, ast.Constant)
        and isinstance(node.operand.value, int)
        and not isinstance(node.operand.value, bool)
    )


def _is_static_regex_flag(
    node: ast.AST, imports: dict[str, str], assigned: set[str]
) -> bool:
    return _is_static_integer(node) or _qualified_reference(
        node, imports, assigned
    ) in {"re.ASCII", "re.IGNORECASE", "re.MULTILINE", "re.DOTALL", "re.VERBOSE"}


def _annotation_is_declarative(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return True
    if isinstance(node, ast.Attribute):
        return _annotation_is_declarative(node.value)
    if isinstance(node, ast.Subscript):
        return _annotation_is_declarative(node.value) and _annotation_is_declarative(
            node.slice
        )
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _annotation_is_declarative(node.left) and _annotation_is_declarative(
            node.right
        )
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return all(_annotation_is_declarative(item) for item in node.elts)
    if isinstance(node, ast.Dict):
        return all(
            (key is None or _annotation_is_declarative(key))
            and _annotation_is_declarative(value)
            for key, value in zip(node.keys, node.values)
        )
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        return isinstance(node.operand, ast.Constant) and isinstance(
            node.operand.value, (int, float, complex)
        )
    return isinstance(node, ast.Constant) and isinstance(
        node.value, (str, int, float, complex, bool, type(None), type(Ellipsis))
    )


def _release_import_is_allowed(statement: ast.Import | ast.ImportFrom) -> bool:
    if isinstance(statement, ast.Import):
        return all(
            alias.name in ALLOWED_RELEASE_IMPORT_MODULES
            for alias in statement.names
        )
    if statement.level != 0 or statement.module not in ALLOWED_RELEASE_FROM_IMPORTS:
        return False
    allowed_names = ALLOWED_RELEASE_FROM_IMPORTS[statement.module]
    return all(alias.name in allowed_names for alias in statement.names)


def _preflight_release_python_sources(
    repo_root: Path, required: set[str]
) -> dict:
    """Parse release Python and reject forbidden import-time executable statements.

    Definitions and declarative constant construction remain permitted. Standalone
    calls, arbitrary control flow, and mutating calls in constant initializers do not.
    """
    python_paths = sorted(
        relative
        for relative in required
        if relative.startswith((EVALUATION_RELATIVE / "scripts").as_posix() + "/")
        and relative.endswith(".py")
    )
    violations: dict[str, list[str]] = {}
    for relative in python_paths:
        path = repo_root / relative
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as error:
            raise ReleaseIntegrityPreflightError(
                f"authenticated release Python syntax is invalid in {relative}: {error}"
            ) from error
        path_violations: list[str] = []
        imports, assigned_names = _module_bindings(tree)
        value_kinds: dict[str, str] = {}
        passive_local_classes: set[str] = set()
        postponed_annotations = any(
            isinstance(statement, ast.ImportFrom)
            and statement.module == "__future__"
            and any(alias.name == "annotations" for alias in statement.names)
            for statement in tree.body
        )
        for import_statement in (
            statement
            for statement in tree.body
            if isinstance(statement, (ast.Import, ast.ImportFrom))
        ):
            if not _release_import_is_allowed(import_statement):
                path_violations.append(
                    f"line {import_statement.lineno}: import is outside the exact "
                    f"release allowlist: {ast.unparse(import_statement)}"
                )

        def check_annotation(annotation: ast.AST | None) -> None:
            if annotation is not None and not postponed_annotations:
                path_violations.append(
                    f"line {annotation.lineno}: annotations require "
                    "from __future__ import annotations to prevent import-time evaluation"
                )
            elif annotation is not None and not _annotation_is_declarative(annotation):
                path_violations.append(
                    f"line {annotation.lineno}: executable or non-declarative annotation "
                    f"{ast.unparse(annotation)}"
                )

        def check_initializer(
            value: ast.AST | None,
            scope_value_kinds: dict[str, str] | None = None,
            scope_assigned_names: set[str] | None = None,
        ) -> None:
            if value is None:
                return
            kinds = value_kinds if scope_value_kinds is None else scope_value_kinds
            assigned_for_scope = (
                assigned_names
                if scope_assigned_names is None
                else scope_assigned_names
            )
            if (
                _initializer_expression_kind(
                    value, imports, assigned_for_scope, kinds
                )
                is None
            ):
                path_violations.append(
                    f"line {value.lineno}: non-declarative initializer expression "
                    f"{ast.unparse(value)}"
                )

        def check_definition(
            definition: ast.FunctionDef | ast.AsyncFunctionDef,
            scope_value_kinds: dict[str, str] | None = None,
            scope_assigned_names: set[str] | None = None,
        ) -> None:
            assigned_for_scope = (
                assigned_names
                if scope_assigned_names is None
                else scope_assigned_names
            )
            for decorator in definition.decorator_list:
                decorator_function = (
                    decorator.func if isinstance(decorator, ast.Call) else decorator
                )
                qualified = _qualified_reference(
                    decorator_function, imports, assigned_for_scope
                )
                if isinstance(decorator, ast.Call) or qualified not in SAFE_DECORATORS:
                    path_violations.append(
                        f"line {decorator.lineno}: executable decorator "
                        f"{ast.unparse(decorator_function)}"
                    )
            for value in [
                *definition.args.defaults,
                *(item for item in definition.args.kw_defaults if item is not None),
            ]:
                check_initializer(
                    value, scope_value_kinds, assigned_for_scope
                )
            for argument in [
                *definition.args.posonlyargs,
                *definition.args.args,
                *definition.args.kwonlyargs,
            ]:
                check_annotation(argument.annotation)
            if definition.args.vararg is not None:
                check_annotation(definition.args.vararg.annotation)
            if definition.args.kwarg is not None:
                check_annotation(definition.args.kwarg.annotation)
            check_annotation(definition.returns)

        def check_assignment_targets(
            statement: ast.Assign | ast.AnnAssign,
            *,
            allow_sys_assignment: bool = True,
        ) -> None:
            targets = (
                statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            )
            for target in targets:
                safe_target = isinstance(target, ast.Name) or (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and allow_sys_assignment
                    and target.value.id == "sys"
                    and target.attr == "dont_write_bytecode"
                )
                if not safe_target:
                    path_violations.append(
                        f"line {target.lineno}: mutating top-level assignment target"
                    )

        for statement in tree.body:
            if isinstance(statement, ast.Expr):
                if not (
                    isinstance(statement.value, ast.Constant)
                    and isinstance(statement.value.value, str)
                ):
                    path_violations.append(
                        f"line {statement.lineno}: executable top-level expression"
                    )
                continue
            if isinstance(statement, ast.If):
                if not _is_main_guard(statement.test) or statement.orelse:
                    path_violations.append(
                        f"line {statement.lineno}: non-main top-level control flow"
                    )
                continue
            if isinstance(statement, (ast.Assign, ast.AnnAssign)):
                check_assignment_targets(statement)
                if isinstance(statement, ast.AnnAssign):
                    check_annotation(statement.annotation)
                check_initializer(statement.value)
                if isinstance(statement.value, ast.AST):
                    value_kind = _initializer_expression_kind(
                        statement.value, imports, assigned_names, value_kinds
                    )
                    targets = (
                        statement.targets
                        if isinstance(statement, ast.Assign)
                        else [statement.target]
                    )
                    for target in targets:
                        if not isinstance(target, ast.Name):
                            continue
                        # Assignment evaluates its RHS before rebinding the target.
                        # Never retain an inferred inert kind after an unrecognized
                        # reassignment: a later method call could otherwise execute
                        # an arbitrary replacement object under the stale kind.
                        if value_kind is None:
                            value_kinds.pop(target.id, None)
                        else:
                            value_kinds[target.id] = value_kind
                        passive_local_classes.discard(target.id)
                continue
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                check_definition(statement)
                value_kinds[statement.name] = "function"
                passive_local_classes.discard(statement.name)
                continue
            if isinstance(statement, ast.ClassDef):
                safe_bases = True
                for base in statement.bases:
                    safe_base = (
                        isinstance(base, ast.Name)
                        and (
                            base.id in passive_local_classes
                            or (
                                base.id in {"RuntimeError", "ValueError"}
                                and base.id not in imports
                                and base.id not in assigned_names
                            )
                        )
                    )
                    if not safe_base:
                        safe_bases = False
                        path_violations.append(
                            f"line {base.lineno}: class base is not a passive local "
                            f"exception or allowed builtin exception: {ast.unparse(base)}"
                        )
                if statement.keywords:
                    path_violations.append(
                        f"line {statement.lineno}: class keywords/metaclass are forbidden"
                    )
                for decorator in statement.decorator_list:
                    decorator_function = (
                        decorator.func if isinstance(decorator, ast.Call) else decorator
                    )
                    qualified = _qualified_reference(
                        decorator_function, imports, assigned_names
                    )
                    if (
                        isinstance(decorator, ast.Call)
                        or qualified not in SAFE_DECORATORS
                    ):
                        path_violations.append(
                            f"line {decorator.lineno}: executable decorator "
                            f"{ast.unparse(decorator_function)}"
                        )
                class_value_kinds: dict[str, str] = {}
                class_shadowed_names: set[str] = set()

                def class_scope_value_kinds() -> dict[str, str]:
                    # Class bodies execute immediately.  Earlier class-local
                    # bindings shadow globals even when their value kind is not
                    # recognized, so an unknown local must never resurrect a
                    # same-named global's previously inferred inert kind.
                    scope = {
                        name: kind
                        for name, kind in value_kinds.items()
                        if name not in class_shadowed_names
                    }
                    scope.update(class_value_kinds)
                    return scope

                for class_statement in statement.body:
                    class_assigned_names = assigned_names | class_shadowed_names
                    if isinstance(class_statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        check_definition(
                            class_statement,
                            class_scope_value_kinds(),
                            class_assigned_names,
                        )
                        class_shadowed_names.add(class_statement.name)
                        class_value_kinds.pop(class_statement.name, None)
                    elif isinstance(class_statement, (ast.Assign, ast.AnnAssign)):
                        check_assignment_targets(
                            class_statement, allow_sys_assignment=False
                        )
                        if isinstance(class_statement, ast.AnnAssign):
                            check_annotation(class_statement.annotation)
                        scope_kinds = class_scope_value_kinds()
                        check_initializer(
                            class_statement.value,
                            scope_kinds,
                            class_assigned_names,
                        )
                        if isinstance(class_statement.value, ast.AST):
                            class_value_kind = _initializer_expression_kind(
                                class_statement.value,
                                imports,
                                class_assigned_names,
                                scope_kinds,
                            )
                            class_targets = (
                                class_statement.targets
                                if isinstance(class_statement, ast.Assign)
                                else [class_statement.target]
                            )
                            for target in class_targets:
                                if not isinstance(target, ast.Name):
                                    continue
                                class_shadowed_names.add(target.id)
                                if class_value_kind is None:
                                    class_value_kinds.pop(target.id, None)
                                else:
                                    class_value_kinds[target.id] = class_value_kind
                    elif isinstance(class_statement, ast.Expr) and not (
                        isinstance(class_statement.value, ast.Constant)
                        and isinstance(class_statement.value.value, str)
                    ):
                        path_violations.append(
                            f"line {class_statement.lineno}: executable class expression"
                        )
                    elif not isinstance(class_statement, (ast.Expr, ast.Pass)):
                        path_violations.append(
                            f"line {class_statement.lineno}: executable class "
                            f"{type(class_statement).__name__}"
                        )
                passive_body = all(
                    isinstance(class_statement, ast.Pass)
                    or (
                        isinstance(class_statement, ast.Expr)
                        and isinstance(class_statement.value, ast.Constant)
                        and isinstance(class_statement.value.value, str)
                    )
                    for class_statement in statement.body
                )
                if safe_bases and not statement.keywords and passive_body:
                    passive_local_classes.add(statement.name)
                else:
                    passive_local_classes.discard(statement.name)
                value_kinds[statement.name] = "class"
                continue
            if isinstance(statement, (ast.Import, ast.ImportFrom)):
                bound_names = (
                    [alias.asname or alias.name.split(".", 1)[0] for alias in statement.names]
                    if isinstance(statement, ast.Import)
                    else [alias.asname or alias.name for alias in statement.names]
                )
                for name in bound_names:
                    value_kinds.pop(name, None)
                    passive_local_classes.discard(name)
                continue
            if not isinstance(statement, (ast.Import, ast.ImportFrom)):
                path_violations.append(
                    f"line {statement.lineno}: executable top-level "
                    f"{type(statement).__name__}"
                )
        if path_violations:
            violations[relative] = path_violations
    if violations:
        raise ReleaseIntegrityPreflightError(
            "authenticated release Python has import-time side effects: "
            + json.dumps(violations, sort_keys=True)
        )
    return {
        "parsed_python_file_count": len(python_paths),
        "forbidden_import_time_side_effects_absent": True,
    }


def _tracked_release_file(path: Path) -> bool:
    return (
        path.is_file()
        and not path.is_symlink()
        and not any(part in IGNORED_PARTS for part in path.parts)
        and path.suffix not in IGNORED_SUFFIXES
    )


def _release_surface_entry(path: Path) -> bool:
    return (
        (path.is_file() or path.is_symlink())
        and not any(part in IGNORED_PARTS for part in path.parts)
        and path.suffix not in IGNORED_SUFFIXES
    )


def authenticate_release_preimport(repo_root: Path) -> dict:
    """Authenticate inventory and bytes without importing target-release Python."""
    repo_root = repo_root.resolve()
    manifest_path = repo_root / MANIFEST_RELATIVE
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ReleaseIntegrityPreflightError(
            f"missing regular immutable release manifest: {manifest_path}"
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReleaseIntegrityPreflightError(
            f"cannot read release manifest: {error}"
        ) from error
    if not isinstance(manifest, dict):
        raise ReleaseIntegrityPreflightError("release manifest must be an object")
    if set(manifest) != {
        "schema_version",
        "contract_version",
        "hash_algorithm",
        "pycache_exclusion",
        "inventory_rule",
        "files",
    }:
        raise ReleaseIntegrityPreflightError("release manifest field inventory mismatch")
    if manifest.get("schema_version") != BOOTSTRAP_MANIFEST_VERSION:
        raise ReleaseIntegrityPreflightError("unsupported release manifest schema_version")
    if manifest.get("contract_version") != BOOTSTRAP_CONTRACT_VERSION:
        raise ReleaseIntegrityPreflightError("release manifest contract_version mismatch")
    if manifest.get("hash_algorithm") != "sha256":
        raise ReleaseIntegrityPreflightError("release manifest must use sha256")
    if manifest.get("pycache_exclusion") != BOOTSTRAP_PYCACHE_EXCLUSION:
        raise ReleaseIntegrityPreflightError("release manifest cache exclusion mismatch")
    if manifest.get("inventory_rule") != BOOTSTRAP_INVENTORY_RULE:
        raise ReleaseIntegrityPreflightError("release manifest inventory rule mismatch")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ReleaseIntegrityPreflightError(
            "release manifest files must be a non-empty object"
        )
    invalid_entries = sorted(
        repr(relative)
        for relative, expected in files.items()
        if not _manifest_entry_is_valid(relative, expected)
    )
    if invalid_entries:
        raise ReleaseIntegrityPreflightError(
            f"invalid release manifest entries: {invalid_entries}"
        )
    if not BOOTSTRAP_REQUIRED_PATHS <= set(files):
        raise ReleaseIntegrityPreflightError(
            "release manifest omits bootstrap-required paths: "
            f"{sorted(BOOTSTRAP_REQUIRED_PATHS - set(files))}"
        )

    missing: list[str] = []
    mismatches: dict[str, dict] = {}
    for relative in sorted(files):
        path = repo_root / relative
        if not _tracked_release_file(path):
            missing.append(relative)
            continue
        try:
            path.resolve().relative_to(repo_root)
        except ValueError:
            mismatches[relative] = {"error": "path resolves outside repo-root"}
            continue
        expected = files[relative]
        actual = {"bytes": path.stat().st_size, "sha256": _bootstrap_sha256(path)}
        if actual != expected:
            mismatches[relative] = {"expected": expected, "actual": actual}
    if missing or mismatches:
        raise ReleaseIntegrityPreflightError(
            json.dumps(
                {"missing": missing, "extra": [], "mismatches": mismatches},
                sort_keys=True,
            )
        )

    contract = _static_release_contract(repo_root / RELEASE_CONTRACT_RELATIVE)
    required = set(contract["REQUIRED_RELEASE_FILES"])
    ci_files = set(contract["CI_RELEASE_FILES"])
    if contract["CONTRACT_VERSION"] != BOOTSTRAP_CONTRACT_VERSION:
        raise ReleaseIntegrityPreflightError(
            "static release contract version differs from bootstrap version"
        )
    if contract["PYCACHE_EXCLUSION"] != BOOTSTRAP_PYCACHE_EXCLUSION:
        raise ReleaseIntegrityPreflightError(
            "static release contract cache exclusion differs from bootstrap rule"
        )
    if set(files) != required:
        raise ReleaseIntegrityPreflightError(
            "release manifest inventory differs from static contract: "
            + json.dumps(
                {
                    "missing": sorted(required - set(files)),
                    "extra": sorted(set(files) - required),
                },
                sort_keys=True,
            )
        )

    evaluation_root = repo_root / EVALUATION_RELATIVE
    actual_names = {
        path.relative_to(repo_root).as_posix()
        for path in evaluation_root.rglob("*")
        if _release_surface_entry(path) and path.name != MANIFEST_RELATIVE.name
    }
    for relative in ci_files:
        path = repo_root / relative
        if _release_surface_entry(path):
            actual_names.add(relative)
    inventory_missing = sorted(required - actual_names)
    inventory_extra = sorted(actual_names - required)
    if inventory_missing or inventory_extra:
        raise ReleaseIntegrityPreflightError(
            json.dumps(
                {
                    "missing": inventory_missing,
                    "extra": inventory_extra,
                    "mismatches": {},
                },
                sort_keys=True,
            )
        )
    python_preflight = _preflight_release_python_sources(repo_root, required)
    return {
        "manifest_sha256": _bootstrap_sha256(manifest_path),
        "verified_file_count": len(required),
        "preimport_authentication": True,
        "static_inventory_contract_parsed_without_execution": True,
        "python_source_preflight": python_preflight,
    }


def _candidate_release_preimport(repo_root: Path) -> dict:
    """Snapshot a dirty release candidate for the sole report-generation entry."""
    repo_root = repo_root.resolve()
    contract_path = repo_root / RELEASE_CONTRACT_RELATIVE
    if not _tracked_release_file(contract_path):
        raise ReleaseIntegrityPreflightError(
            f"release inventory contract is not a regular file: {contract_path}"
        )
    contract = _static_release_contract(contract_path)
    if contract["CONTRACT_VERSION"] != BOOTSTRAP_CONTRACT_VERSION:
        raise ReleaseIntegrityPreflightError(
            "candidate static release contract version mismatch"
        )
    if contract["PYCACHE_EXCLUSION"] != BOOTSTRAP_PYCACHE_EXCLUSION:
        raise ReleaseIntegrityPreflightError(
            "candidate static release contract cache exclusion mismatch"
        )
    required = set(contract["REQUIRED_RELEASE_FILES"])
    ci_files = set(contract["CI_RELEASE_FILES"])
    actual_names = {
        path.relative_to(repo_root).as_posix()
        for path in (repo_root / EVALUATION_RELATIVE).rglob("*")
        if _release_surface_entry(path) and path.name != MANIFEST_RELATIVE.name
    }
    for relative in ci_files:
        if _release_surface_entry(repo_root / relative):
            actual_names.add(relative)
    missing = sorted(required - actual_names)
    extra = sorted(actual_names - required)
    if missing or extra:
        raise ReleaseIntegrityPreflightError(
            "dirty release candidate inventory mismatch: "
            + json.dumps({"missing": missing, "extra": extra}, sort_keys=True)
        )
    files: dict[str, dict[str, int | str]] = {}
    for relative in sorted(required):
        path = repo_root / relative
        if not _tracked_release_file(path):
            raise ReleaseIntegrityPreflightError(
                f"candidate release path is not a regular file: {relative}"
            )
        try:
            path.resolve().relative_to(repo_root)
        except ValueError as error:
            raise ReleaseIntegrityPreflightError(
                f"candidate release path resolves outside repo-root: {relative}"
            ) from error
        files[relative] = {
            "bytes": path.stat().st_size,
            "sha256": _bootstrap_sha256(path),
        }
    python_preflight = _preflight_release_python_sources(repo_root, required)
    activation_sha256 = hashlib.sha256(
        json.dumps(
            files,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "activation_sha256": activation_sha256,
        "candidate_files": files,
        "candidate_file_count": len(files),
        "candidate_inventory_snapshotted_before_import": True,
        "static_inventory_contract_parsed_without_execution": True,
        "python_source_preflight": python_preflight,
    }


_ACTIVE_RELEASE_ROOT: Path | None = None
_ACTIVE_RELEASE_MANIFEST_SHA256: str | None = None


def _activate_release_modules(repo_root: Path, evidence: dict) -> dict:
    """Load target-root semantic modules after a caller completed its preflight."""
    global _ACTIVE_RELEASE_ROOT, _ACTIVE_RELEASE_MANIFEST_SHA256
    repo_root = repo_root.resolve()
    activation_sha256 = evidence["activation_sha256"]
    if (
        _ACTIVE_RELEASE_ROOT == repo_root
        and _ACTIVE_RELEASE_MANIFEST_SHA256 == activation_sha256
    ):
        return evidence

    scripts_root = (repo_root / EVALUATION_RELATIVE / "scripts").resolve()
    local_names = {
        path.stem
        for path in scripts_root.glob("*.py")
        if path.is_file() and not path.is_symlink()
    }
    for name in sorted(local_names - {"validate_contract"}):
        sys.modules.pop(name, None)
    original_path = list(sys.path)
    sys.path.insert(0, str(scripts_root))
    importlib.invalidate_caches()
    try:
        modules = {
            name: importlib.import_module(name)
            for name in (
                "integrity",
                "build_baseline",
                "compare_candidate",
                "contract_constants",
                "corpus_archive",
                "private_ledgers",
                "release_contract",
                "runtime_attestation",
                "schema_validation",
                "compare_baseline_runs",
            )
        }
        wrong_roots = {}
        for name in sorted(local_names):
            module = sys.modules.get(name)
            module_file = getattr(module, "__file__", None) if module else None
            if module_file is None:
                continue
            path = Path(module_file).resolve()
            if path.parent != scripts_root:
                wrong_roots[name] = str(path)
        if wrong_roots:
            raise ReleaseIntegrityPreflightError(
                "semantic release modules resolved outside --repo-root: "
                + json.dumps(wrong_roots, sort_keys=True)
            )
    except BaseException as error:
        if isinstance(error, KeyboardInterrupt):
            raise
        if isinstance(error, ReleaseIntegrityPreflightError):
            raise
        raise ReleaseIntegrityPreflightError(
            "authenticated semantic release module import failed: "
            f"{type(error).__name__}: {error}"
        ) from error
    finally:
        sys.path[:] = original_path

    build = modules["build_baseline"]
    candidate = modules["compare_candidate"]
    constants = modules["contract_constants"]
    archive = modules["corpus_archive"]
    integrity = modules["integrity"]
    ledgers = modules["private_ledgers"]
    release_contract = modules["release_contract"]
    runtime = modules["runtime_attestation"]
    schemas = modules["schema_validation"]
    baseline_runs = modules["compare_baseline_runs"]
    globals().update(
        {
            "build_metrics": build.build_metrics,
            "build_opportunity_queue": build.build_opportunity_queue,
            "canonical_json_sha256": build.canonical_json_sha256,
            "classify_current_nodes": build.classify_current_nodes,
            "read_gzip_jsonl": build.read_gzip_jsonl,
            "read_jsonl": build.read_jsonl,
            "MAXIMUM_NEWLY_BLOCKING_FRACTION": candidate.MAXIMUM_NEWLY_BLOCKING_FRACTION,
            "CONCENTRATION_MAXIMUM_INCREASE": candidate.CONCENTRATION_MAXIMUM_INCREASE,
            "MINIMUM_AFFECTED_FRACTION": candidate.MINIMUM_AFFECTED_FRACTION,
            "MINIMUM_GAINED_IDENTITIES": candidate.MINIMUM_GAINED_IDENTITIES,
            "REVIEWS_PER_CREDITED_DECISION": candidate.REVIEWS_PER_CREDITED_DECISION,
            "OPPORTUNITY_MUSEUM_PROTECTION": constants.OPPORTUNITY_MUSEUM_PROTECTION,
            "OPPORTUNITY_TOTAL_SIGNATURES": constants.OPPORTUNITY_TOTAL_SIGNATURES,
            "CorpusArchiveBlocked": archive.CorpusArchiveBlocked,
            "CorpusArchiveInvalid": archive.CorpusArchiveInvalid,
            "authenticated_corpus": archive.authenticated_corpus,
            "IntegrityError": integrity.IntegrityError,
            "sha256": integrity.sha256,
            "verify_release": integrity.verify_release,
            "FORBIDDEN_PUBLIC_FILES": ledgers.FORBIDDEN_PUBLIC_FILES,
            "PUBLIC_AGGREGATE_FILES": ledgers.PUBLIC_AGGREGATE_FILES,
            "verify_private_ledgers": ledgers.verify_private_ledgers,
            "verify_public_boundary": ledgers.verify_public_boundary,
            "validation_input_bindings": release_contract.validation_input_bindings,
            "validate_runtime_attestation": runtime.validate_runtime_attestation,
            "execute_schema_contract_tests": schemas.execute_schema_contract_tests,
            "validate_schema": schemas.validate_schema,
            "validate_baseline_run": baseline_runs.validate_run,
        }
    )
    _ACTIVE_RELEASE_ROOT = repo_root
    _ACTIVE_RELEASE_MANIFEST_SHA256 = activation_sha256
    return evidence


def _activate_authenticated_release(repo_root: Path) -> dict:
    """Authenticate the frozen release, then load only its target-root modules."""
    evidence = authenticate_release_preimport(repo_root)
    evidence["activation_sha256"] = evidence["manifest_sha256"]
    return _activate_release_modules(repo_root, evidence)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_file(path: Path, expected: dict) -> dict:
    actual = {
        "exists": path.is_file(),
        "bytes": path.stat().st_size if path.is_file() else None,
        "sha256": _bootstrap_sha256(path) if path.is_file() else None,
    }
    actual["passed"] = (
        actual["exists"]
        and actual["bytes"] == expected["bytes"]
        and actual["sha256"] == expected["sha256"]
    )
    return actual


def _public_boundary_evidence_passed(
    evidence: object,
    public_files: set[str] | frozenset[str],
    forbidden_files: set[str] | frozenset[str],
) -> bool:
    return (
        isinstance(evidence, dict)
        and set(evidence) == {
            "public_aggregate_files",
            "forbidden_public_files_absent",
        }
        and isinstance(evidence["public_aggregate_files"], list)
        and isinstance(evidence["forbidden_public_files_absent"], list)
        and evidence["public_aggregate_files"] == sorted(public_files)
        and evidence["forbidden_public_files_absent"] == sorted(forbidden_files)
    )


def _schema_execution_evidence_passed(
    evidence: object, schema_directory: Path, cases_path: Path
) -> bool:
    try:
        schema_names = sorted(
            path.name for path in schema_directory.glob("*.schema.json")
        )
        cases_document = read_json(cases_path)
        cases = cases_document["cases"]
        if (
            cases_document.get("schema_version")
            != "site-graph-v0-schema-test-cases/1"
            or not schema_names
            or not isinstance(cases, dict)
            or set(cases) != set(schema_names)
            or any(
                not isinstance(cases[name], dict)
                or set(cases[name]) != {"valid", "invalid"}
                or not isinstance(cases[name]["invalid"], list)
                or not cases[name]["invalid"]
                for name in schema_names
            )
        ):
            return False
        invalid_count = sum(len(cases[name]["invalid"]) for name in schema_names)
    except (KeyError, OSError, TypeError, UnicodeError, json.JSONDecodeError):
        return False
    return (
        isinstance(evidence, dict)
        and set(evidence)
        == {
            "meta_valid_schema_count",
            "representative_valid_instance_count",
            "adversarial_invalid_instance_count",
            "schemas",
        }
        and all(
            type(evidence[name]) is int
            for name in (
                "meta_valid_schema_count",
                "representative_valid_instance_count",
                "adversarial_invalid_instance_count",
            )
        )
        and isinstance(evidence["schemas"], list)
        and evidence["meta_valid_schema_count"] == len(schema_names)
        and evidence["representative_valid_instance_count"] == len(schema_names)
        and evidence["adversarial_invalid_instance_count"] == invalid_count
        and evidence["schemas"] == schema_names
    )


def _boundary_path_violation(relative: str) -> str | None:
    path = Path(relative)
    basename = path.name.casefold()
    components = {part.casefold().replace("_", "-") for part in path.parts}
    in_evaluation_release = (
        relative == EVALUATION_RELATIVE.as_posix()
        or relative.startswith(EVALUATION_RELATIVE.as_posix() + "/")
    )
    if basename in FORBIDDEN_BOUNDARY_BASENAMES:
        return "known_private_bulk_filename"
    if components & {"private", "private-data", "private-bulk", "bulk-data"}:
        return "private_or_bulk_directory"
    if in_evaluation_release and any(
        basename.endswith(suffix) for suffix in FORBIDDEN_BULK_SUFFIXES
    ):
        return "bulk_data_extension"
    if FORBIDDEN_DUMP_NAME.search(basename):
        return "artifact_id_or_mention_dump_name"
    return None


def _run_git(repo_root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )


def scan_public_repository_boundary(repo_root: Path) -> dict:
    """Scan current release paths and every tree reachable from the current HEAD.

    This deliberately narrow check covers path names across the repository. It does
    not claim that aggregate ranks/counts are unlinkable, inspect file contents, or
    cover unreachable/pruned Git objects.
    """
    repo_root = repo_root.resolve()
    current_paths = sorted(
        path.relative_to(repo_root).as_posix()
        for path in repo_root.rglob("*")
        if (path.is_file() or path.is_symlink())
        and ".git" not in path.relative_to(repo_root).parts
        and not any(part in IGNORED_PARTS for part in path.parts)
    )
    current_violations = [
        {"path": relative, "reason": reason}
        for relative in current_paths
        if (reason := _boundary_path_violation(relative)) is not None
    ]
    claim_scope = (
        "Recursive repository-wide path-name scan in the current checkout and every "
        "commit tree reachable from HEAD. It detects known private bulk paths and "
        "artifact-ID/mention-dump filenames everywhere, plus bulk-data extensions "
        "inside docs/evaluations/site-graph-v0; it does not assert rank/count "
        "unlinkability, inspect blob contents, or cover unreachable/pruned Git objects."
    )
    if not (repo_root / ".git").exists():
        return {
            "passed": False,
            "status": "UNABLE_GIT_METADATA_ABSENT",
            "claim_scope": claim_scope,
            "git_metadata_available": False,
            "current_tree": {
                "recursive_scan_completed": True,
                "violations": current_violations,
            },
            "git_history": {
                "all_trees_reachable_from_head_scanned": False,
                "violations": [],
            },
            "inability_reason": (
                "repo-root has no .git file or directory, so reachable history cannot "
                "be scanned and the historical public-boundary claim cannot be made"
            ),
        }

    inside = _run_git(repo_root, "rev-parse", "--is-inside-work-tree")
    head_result = _run_git(repo_root, "rev-parse", "--verify", "HEAD^{commit}")
    commits_result = _run_git(repo_root, "rev-list", "HEAD")
    roots_result = _run_git(repo_root, "rev-list", "--max-parents=0", "HEAD")
    commands = (inside, head_result, commits_result, roots_result)
    if any(command.returncode != 0 for command in commands):
        errors = [
            command.stderr.strip() or command.stdout.strip()
            for command in commands
            if command.returncode != 0
        ]
        return {
            "passed": False,
            "status": "UNABLE_GIT_HISTORY_QUERY_FAILED",
            "claim_scope": claim_scope,
            "git_metadata_available": True,
            "current_tree": {
                "recursive_scan_completed": True,
                "violations": current_violations,
            },
            "git_history": {
                "all_trees_reachable_from_head_scanned": False,
                "violations": [],
            },
            "inability_reason": "; ".join(errors),
        }
    if inside.stdout.strip() != "true":
        return {
            "passed": False,
            "status": "UNABLE_NOT_GIT_WORK_TREE",
            "claim_scope": claim_scope,
            "git_metadata_available": True,
            "current_tree": {
                "recursive_scan_completed": True,
                "violations": current_violations,
            },
            "git_history": {
                "all_trees_reachable_from_head_scanned": False,
                "violations": [],
            },
            "inability_reason": "repo-root is not inside a Git work tree",
        }

    commits = [line for line in commits_result.stdout.splitlines() if line]
    history_violations: set[tuple[str, str, str]] = set()
    for commit in commits:
        tree = subprocess.run(
            [
                "git",
                "ls-tree",
                "-r",
                "-z",
                commit,
            ],
            cwd=repo_root,
            check=False,
            capture_output=True,
        )
        if tree.returncode != 0:
            return {
                "passed": False,
                "status": "UNABLE_GIT_HISTORY_QUERY_FAILED",
                "claim_scope": claim_scope,
                "git_metadata_available": True,
                "current_tree": {
                    "recursive_scan_completed": True,
                    "violations": current_violations,
                },
                "git_history": {
                    "all_trees_reachable_from_head_scanned": False,
                    "violations": [],
                },
                "inability_reason": tree.stderr.decode("utf-8", errors="replace").strip(),
            }
        for raw_entry in tree.stdout.split(b"\0"):
            if not raw_entry:
                continue
            try:
                metadata, raw_path = raw_entry.split(b"\t", 1)
                _mode, object_type, object_id = metadata.decode("ascii").split(" ")
                relative = raw_path.decode("utf-8")
            except (UnicodeError, ValueError):
                return {
                    "passed": False,
                    "status": "UNABLE_GIT_TREE_DECODE_FAILED",
                    "claim_scope": claim_scope,
                    "git_metadata_available": True,
                    "current_tree": {
                        "recursive_scan_completed": True,
                        "violations": current_violations,
                    },
                    "git_history": {
                        "all_trees_reachable_from_head_scanned": False,
                        "violations": [],
                    },
                    "inability_reason": "Git tree contains a non-UTF-8 or malformed name",
                }
            if object_type != "blob":
                continue
            reason = _boundary_path_violation(relative)
            if reason is not None:
                history_violations.add((object_id, relative, reason))

    history_rows = [
        {"object_id": object_id, "path": relative, "reason": reason}
        for object_id, relative, reason in sorted(history_violations)
    ]
    passed = not current_violations and not history_rows
    return {
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "claim_scope": claim_scope,
        "git_metadata_available": True,
        "current_tree": {
            "recursive_scan_completed": True,
            "violations": current_violations,
        },
        "git_history": {
            "all_trees_reachable_from_head_scanned": True,
            "violations": history_rows,
        },
        "inability_reason": None,
    }


def _validate_private_run_runtime(
    repo_root: Path,
    private_run: Path,
    snapshot: dict,
    reruns: dict,
    *,
    _release_activated: bool = False,
) -> dict:
    """Verify a fresh run against deterministic bytes, separately from history.

    The committed rerun identities authenticate the historical release exercise.
    A later reproduction is accepted by deterministic equivalence and release/input
    bindings; its directory, UUID, and provenance hash are intentionally irrelevant.
    """
    if not _release_activated:
        _activate_authenticated_release(repo_root)
    runtime_path = private_run / "runtime-attestation.json"
    manifest_path = private_run / "run-output-manifest.json"
    provenance_path = private_run / "run-provenance.json"
    paths = {
        "runtime_attestation": runtime_path,
        "run_output_manifest": manifest_path,
        "run_provenance": provenance_path,
    }
    missing = sorted(label for label, path in paths.items() if not path.is_file())
    if missing:
        return {
            "passed": False,
            "missing": missing,
            "checks": {},
            "matching_rerun": None,
        }

    try:
        runtime = read_json(runtime_path)
        manifest = read_json(manifest_path)
        provenance = read_json(provenance_path)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return {
            "passed": False,
            "missing": [],
            "checks": {},
            "matching_rerun": None,
            "error": f"private-run runtime provenance is unreadable: {error}",
        }

    errors: list[str] = []
    exact_full_run_validation = False
    try:
        validate_baseline_run(private_run)
        exact_full_run_validation = True
    except (KeyError, OSError, TypeError, ValueError, RuntimeError) as error:
        errors.append(str(error))

    runtime_matches_release = False
    try:
        validated_runtime = validate_runtime_attestation(
            repo_root, snapshot, runtime
        )
        runtime_matches_release = True
    except (KeyError, TypeError, ValueError, RuntimeError) as error:
        validated_runtime = None
        errors.append(str(error))

    runtime_reference = None
    if validated_runtime is not None:
        runtime_reference = {
            "path": "runtime-attestation.json",
            "sha256": sha256(runtime_path),
            "python": validated_runtime["python"],
            "dependency_lock": validated_runtime["dependency_lock"],
        }

    manifest_hashes = (
        manifest.get("deterministic_output_hashes", {})
        if isinstance(manifest, dict)
        else {}
    )
    rerun_hashes = (
        reruns.get("deterministic_output_hashes", {})
        if isinstance(reruns, dict)
        else {}
    )
    requested_output = (
        provenance.get("requested_output") if isinstance(provenance, dict) else None
    )
    requested_output_matches = (
        isinstance(requested_output, str)
        and Path(requested_output).resolve() == private_run.resolve()
    )
    historical_rows = [reruns.get(label) for label in ("run_a", "run_b")]
    historical_identity_authenticated = (
        reruns.get("schema_version") == "site-graph-v0-baseline-rerun-evidence/3"
        and all(
            isinstance(row, dict)
            and set(row)
            == {
                "resolved_directory",
                "run_id",
                "manifest_sha256",
                "provenance_sha256",
            }
            and all(isinstance(row[field], str) and row[field] for field in row)
            for row in historical_rows
        )
        and historical_rows[0]["resolved_directory"]
        != historical_rows[1]["resolved_directory"]
        and historical_rows[0]["run_id"] != historical_rows[1]["run_id"]
        and historical_rows[0]["manifest_sha256"]
        == historical_rows[1]["manifest_sha256"]
    )
    checks = {
        "exact_full_run_output_validation": exact_full_run_validation,
        "runtime_attestation_matches_release_environment": runtime_matches_release,
        "manifest_schema_version": (
            isinstance(manifest, dict)
            and manifest.get("schema_version")
            == "site-graph-v0-baseline-run-manifest/3"
        ),
        "manifest_runtime_binding": (
            runtime_reference is not None
            and isinstance(manifest, dict)
            and manifest.get("runtime_attestation") == runtime_reference
        ),
        "manifest_runtime_output_hash": (
            runtime_reference is not None
            and isinstance(manifest_hashes, dict)
            and manifest_hashes.get("runtime-attestation.json")
            == runtime_reference["sha256"]
        ),
        "provenance_schema_version": (
            isinstance(provenance, dict)
            and provenance.get("schema_version")
            == "site-graph-v0-baseline-run-provenance/3"
        ),
        "provenance_runtime_binding": (
            runtime_reference is not None
            and isinstance(provenance, dict)
            and provenance.get("runtime_attestation") == runtime_reference
        ),
        "provenance_requested_output_binding": requested_output_matches,
        "historical_release_identity_record_authenticated": historical_identity_authenticated,
        "fresh_manifest_deterministic_outputs_equal_committed_release": (
            isinstance(manifest_hashes, dict)
            and manifest_hashes == rerun_hashes
            and len(manifest_hashes) == reruns.get("deterministic_output_count")
            and historical_identity_authenticated
            and sha256(manifest_path) == historical_rows[0]["manifest_sha256"]
        ),
        "fresh_manifest_input_and_tool_bindings_equal_committed_release": (
            isinstance(manifest, dict)
            and manifest.get("input_snapshot_sha256")
            == reruns.get("input_snapshot_sha256")
            and manifest.get("runner_sha256") == reruns.get("runner_sha256")
            and manifest.get("builder_sha256") == reruns.get("builder_sha256")
            and manifest.get("corpus_archive_sha256")
            == reruns.get("corpus_archive_sha256")
        ),
        "committed_rerun_evidence_runtime_binding": (
            runtime_reference is not None
            and reruns.get("runtime_attestation") == runtime_reference
        ),
        "committed_rerun_evidence_runtime_output_hash": (
            runtime_reference is not None
            and isinstance(rerun_hashes, dict)
            and rerun_hashes.get("runtime-attestation.json")
            == runtime_reference["sha256"]
        ),
    }
    return {
        "passed": all(checks.values()),
        "missing": [],
        "checks": checks,
        "runtime_attestation": runtime_reference,
        "historical_release_run_identities": {
            label: reruns.get(label) for label in ("run_a", "run_b")
        },
        "fresh_reproduction_equivalence": {
            "deterministic_output_count": len(manifest_hashes),
            "deterministic_output_hashes": manifest_hashes,
            "manifest_sha256": sha256(manifest_path),
            "path_uuid_and_provenance_hash_are_not_equivalence_inputs": True,
        },
        "errors": errors,
    }


def _semantic_report(
    repo_root: Path,
    corpus: Path,
    private_run: Path,
    archive_attestation: dict,
    *,
    _release_activated: bool = False,
) -> dict:
    if not _release_activated:
        _activate_authenticated_release(repo_root)
    root = repo_root / "docs/evaluations/site-graph-v0"
    snapshot = read_json(root / "input-snapshot.json")
    prereg = read_json(root / "preregistration.json")
    metrics = read_json(root / "baseline-metrics.json")
    node_scope = read_json(root / "baseline-node-scope.json")
    opportunity_summary = read_json(root / "planned-opportunity-summary.json")
    top_components = read_json(root / "top-unmatched-components.json")
    private_digests = read_json(root / "private-ledger-digests.json")
    reruns = read_json(root / "baseline-rerun-evidence.json")
    crosswalk = read_json(root / "type-crosswalk.json")
    checks: list[dict] = []

    def check(check_id: str, passed: bool, evidence: object) -> None:
        checks.append({"check_id": check_id, "passed": bool(passed), "evidence": evidence})

    private_runtime_validation = _validate_private_run_runtime(
        repo_root,
        private_run,
        snapshot,
        reruns,
        _release_activated=True,
    )
    check(
        "private_run_runtime_attestation_and_rerun_binding",
        private_runtime_validation["passed"],
        private_runtime_validation,
    )

    runtime_attestation_path = private_run / "corpus-archive-attestation.json"
    runtime_attestation = (
        read_json(runtime_attestation_path) if runtime_attestation_path.is_file() else None
    )
    check(
        "authenticated_archive_attestation_bound_to_private_run",
        runtime_attestation == archive_attestation,
        {
            "archive_sha256": archive_attestation["archive"]["sha256"],
            "runtime_attestation_sha256": (
                sha256(runtime_attestation_path)
                if runtime_attestation_path.is_file()
                else None
            ),
            "exact_attestation_match": runtime_attestation == archive_attestation,
        },
    )

    frozen_inputs = {}
    for relative, expected in snapshot["corpus"]["files"].items():
        frozen_inputs[f"external-private/{relative}"] = verify_file(corpus / relative, expected)
    for group in ("extractor_and_matcher", "current_authority"):
        for relative, expected in snapshot[group]["files"].items():
            frozen_inputs[relative] = verify_file(repo_root / relative, expected)
    check(
        "frozen_input_bytes",
        all(item["passed"] for item in frozen_inputs.values()),
        frozen_inputs,
    )

    private_authentication = verify_private_ledgers(private_run, root)
    external_private_input = private_digests["external_private_input"]
    check(
        "authenticated_private_snapshot_input",
        external_private_input["snapshot_acquisition_integrity"] == "PASS"
        and external_private_input["upstream_production_lineage"]
        == "UNAVAILABLE_DISCLOSED"
        and external_private_input["archive_sha256"]
        == archive_attestation["archive"]["sha256"]
        and private_authentication["private_record_count"]
        == snapshot["corpus"]["canonical_record_count"],
        {
            **private_authentication,
            "canonical_transport_sha256": external_private_input[
                "canonical_artifact_transport_gzip_sha256"
            ],
            "archive_sha256": archive_attestation["archive"]["sha256"],
            "snapshot_acquisition_integrity": external_private_input[
                "snapshot_acquisition_integrity"
            ],
            "upstream_production_lineage": external_private_input[
                "upstream_production_lineage"
            ],
            "historical_export_reproducibility": external_private_input[
                "historical_export_reproducibility"
            ],
            "unavailable_lineage_effect": external_private_input[
                "unavailable_lineage_effect"
            ],
        },
    )
    frozen = prereg["frozen_artifacts"]
    record_digest = private_digests["ledgers"]["private_record_evidence"]
    source_digest = private_digests["ledgers"]["private_opportunity_source"]
    opportunity_digest = private_digests["ledgers"][
        "private_opportunity_membership"
    ]
    preregistered_digest_bindings = {
        "private_record_evidence": {
            "runtime_path": "private-record-evidence.ndjson.gz",
            "record_count": record_digest["row_count"],
            "gzip_transport_sha256": record_digest["transport_gzip_sha256"],
            "canonical_uncompressed_ndjson_sha256": record_digest[
                "canonical_uncompressed_ndjson_sha256"
            ],
            "canonical_row_merkle_sha256": record_digest[
                "canonical_row_merkle_sha256"
            ],
            "publicly_redistributed": False,
        },
        "private_opportunity_source": {
            "runtime_path": "private-opportunity-source.ndjson.gz",
            "record_count": source_digest["row_count"],
            "gzip_transport_sha256": source_digest["transport_gzip_sha256"],
            "canonical_uncompressed_ndjson_sha256": source_digest[
                "canonical_uncompressed_ndjson_sha256"
            ],
            "canonical_row_merkle_sha256": source_digest[
                "canonical_row_merkle_sha256"
            ],
            "publicly_redistributed": False,
        },
        "private_opportunity_ledger": {
            "runtime_path": "private-opportunity-ledger.json",
            "canonical_json_sha256": opportunity_digest["canonical_json_sha256"],
            "transport_json_sha256": opportunity_digest["transport_json_sha256"],
            "publicly_redistributed": False,
        },
    }
    check(
        "preregistered_private_and_public_digest_bindings",
        all(
            frozen[name] == value
            for name, value in preregistered_digest_bindings.items()
        )
        and frozen["public_opportunity_summary"]["sha256"]
        == sha256(root / frozen["public_opportunity_summary"]["path"])
        and frozen["private_ledger_digests"]["sha256"]
        == sha256(root / frozen["private_ledger_digests"]["path"])
        and frozen["type_crosswalk"]["sha256"]
        == sha256(root / frozen["type_crosswalk"]["path"]),
        {
            "private": preregistered_digest_bindings,
            "public_opportunity_summary_sha256": sha256(
                root / frozen["public_opportunity_summary"]["path"]
            ),
            "private_ledger_digests_sha256": sha256(
                root / frozen["private_ledger_digests"]["path"]
            ),
            "type_crosswalk_sha256": sha256(
                root / frozen["type_crosswalk"]["path"]
            ),
        },
    )
    public_boundary = verify_public_boundary(root)
    check(
        "public_data_boundary",
        _public_boundary_evidence_passed(
            public_boundary, PUBLIC_AGGREGATE_FILES, FORBIDDEN_PUBLIC_FILES
        ),
        public_boundary,
    )
    repository_boundary = scan_public_repository_boundary(repo_root)
    check(
        "public_repository_current_and_reachable_history_boundary",
        repository_boundary["passed"],
        repository_boundary,
    )

    canonical = read_gzip_jsonl(corpus / "data/artifacts.ndjson.gz")
    canonical_by_id = {row["id"]: row for row in canonical}
    records = read_gzip_jsonl(private_run / "private-record-evidence.ndjson.gz")
    record_by_id = {row["artifact_id"]: row for row in records}
    canonical_counts = dict(
        sorted(collections.Counter(row["source_museum"] for row in canonical).items())
    )
    record_counts = dict(sorted(collections.Counter(row["museum"] for row in records).items()))
    aligned = (
        len(canonical_by_id) == len(canonical)
        and len(record_by_id) == len(records)
        and set(canonical_by_id) == set(record_by_id)
        and all(
            canonical_by_id[artifact_id]["source_museum"] == record_by_id[artifact_id]["museum"]
            for artifact_id in record_by_id
        )
    )
    check(
        "canonical_population_and_private_record_alignment",
        len(records) == snapshot["corpus"]["canonical_record_count"]
        and canonical_counts == snapshot["corpus"]["records_by_museum"]
        and record_counts == snapshot["corpus"]["records_by_museum"]
        and aligned,
        {
            "canonical_records": len(canonical),
            "private_records": len(records),
            "records_by_museum": record_counts,
            "artifact_and_museum_alignment": aligned,
        },
    )

    idai_rows = read_jsonl(
        repo_root / "pipeline/pipeline/authority/sources/idai-gazetteer/reconciled.jsonl"
    )
    raw_hierarchy = read_json(
        repo_root / "pipeline/pipeline/authority/sources/idai-gazetteer/raw.json"
    )
    expected_targets = snapshot["current_authority"]["site_snapshot"]["site_target_count"]
    recomputed_nodes, scope_by_target, hierarchy_summary = classify_current_nodes(
        idai_rows, raw_hierarchy, crosswalk, expected_targets
    )
    expected_node_scope = {
        "schema_version": "site-graph-v0-baseline-node-scope/2",
        "hierarchy_context": hierarchy_summary,
        "nodes": recomputed_nodes,
    }
    filtered_parent_missing = sum(
        row.get("kind") == "site" and row.get("parent_id") and not row.get("parent_in_file")
        for row in idai_rows
    )
    check(
        "node_scope_recomputed_from_crosswalk_and_complete_available_hierarchy",
        node_scope == expected_node_scope,
        {
            "scope_counts": dict(
                sorted(collections.Counter(row["scope_class"] for row in recomputed_nodes).items())
            ),
            "filtered_1000_parent_outside_filtered_set": filtered_parent_missing,
            "raw_2075_parent_reference_outside_raw_set": hierarchy_summary[
                "raw_records_with_parent_outside_available_hierarchy"
            ],
            "measure_explanation": (
                "566 counts filtered targets whose parent is absent from the filtered 1,000; "
                "699 counts raw records whose parent reference is absent from all 2,075 available raw records."
            ),
        },
    )

    site_links = [
        {"artifact_id": row["artifact_id"], "museum": row["museum"], "target_id": target}
        for row in records
        for target in row["baseline_site_target_ids"]
    ]
    source_rows = read_gzip_jsonl(private_run / "private-opportunity-source.ndjson.gz")
    actual_private_opportunity = read_json(private_run / "private-opportunity-ledger.json")
    evidence_counts = collections.Counter(
        row["museum"] for row in records if row["extracted_site_text_evidence"]
    )
    regenerated_summary, regenerated_private, regenerated_top = build_opportunity_queue(
        source_rows,
        records,
        site_links,
        scope_by_target,
        dict(collections.Counter(row["museum"] for row in records)),
        dict(evidence_counts),
    )
    regenerated_summary["private_ledger_authentication"] = opportunity_summary[
        "private_ledger_authentication"
    ]
    recomputed_metrics = build_metrics(records, site_links, scope_by_target)
    recomputed_metrics["planned_slice_maximum_measurable_effect"] = {
        "source": "planned-opportunity-summary.json",
        "per_museum": regenerated_summary["per_museum"],
        "pair_side_ceilings": regenerated_summary["pair_side_ceilings"],
        "interpretation": (
            "Numeric intent-to-treat upper bounds, not expected effects or accuracy claims. "
            "Unsupported, broad/administrative, abstained, failed, and disputed research "
            "remains in denominators and earns zero credit."
        ),
    }
    headline_evidence = {
        "per_museum": recomputed_metrics["per_museum"],
        "pair_shared_node_counts": {
            key: value["shared_node_count"]
            for key, value in recomputed_metrics["connectivity"]["pairs"].items()
        },
        "all_three_shared_node_count": recomputed_metrics["connectivity"]["all_three"][
            "shared_node_count"
        ],
        "any_two_or_more_shared_node_count": recomputed_metrics["connectivity"][
            "any_two_or_more"
        ]["shared_node_count"],
    }
    check("headline_metrics_recomputed", metrics == recomputed_metrics, headline_evidence)
    check(
        "intent_to_treat_aggregates_and_private_membership_recomputed",
        opportunity_summary == regenerated_summary
        and top_components == regenerated_top
        and actual_private_opportunity == regenerated_private,
        {
            "selected_signatures": regenerated_summary["selected_signature_count"],
            "per_museum": regenerated_summary["per_museum"],
            "pair_side_ceilings": regenerated_summary["pair_side_ceilings"],
            "private_opportunity_ledger_canonical_sha256": canonical_json_sha256(
                regenerated_private
            ),
        },
    )

    formula_expected = {
        "extracted_site_text_availability": "|X_m| / |A_m|",
        "overall_linkability": "|L_m| / |A_m|",
        "extracted_site_text_conditional_linkability": "|L_m| / |X_m|",
        "blocking_ambiguity": "|{r in X_m: direct targets empty and any site mention ambiguous}| / |X_m|",
        "planned_maximum_overall_effect": "(|new-link-eligible records in O_m| + |broad-only strict-refinement-eligible records in O_m|) / |A_m|",
        "planned_maximum_extracted_site_text_conditional_effect": "(|new-link-eligible records in O_m| + |broad-only strict-refinement-eligible records in O_m|) / |X_m|",
        "pair_side_coverage_overall": "D_(m->n) / |A_m|",
        "pair_side_coverage_extracted_site_text_conditional": "D_(m->n) / |X_m|",
        "top_k_concentration": "|union of museum-side records incident on its top-k shared identity classes| / |union of museum-side records incident on all its shared identity classes|",
        "hhi": "sum_j(I_j^2) / (sum_j I_j)^2",
    }
    actual_formulas = {
        key: prereg["metric_formulas"][key]["expression"] for key in formula_expected
    }
    check("machine_readable_formulas", actual_formulas == formula_expected, actual_formulas)

    machine_expected = {
        "maximum_newly_blocking_fraction": {
            "numerator": MAXIMUM_NEWLY_BLOCKING_FRACTION.numerator,
            "denominator": MAXIMUM_NEWLY_BLOCKING_FRACTION.denominator,
        },
        "concentration_maximum_increase": {
            "numerator": CONCENTRATION_MAXIMUM_INCREASE.numerator,
            "denominator": CONCENTRATION_MAXIMUM_INCREASE.denominator,
        },
        "minimum_gained_distinct_specific_identity_classes": MINIMUM_GAINED_IDENTITIES,
        "minimum_affected_opportunity_fraction": {
            "numerator": MINIMUM_AFFECTED_FRACTION.numerator,
            "denominator": MINIMUM_AFFECTED_FRACTION.denominator,
        },
        "minimum_reviews_per_credited_decision": REVIEWS_PER_CREDITED_DECISION,
        "opportunity_museum_protection_signatures": OPPORTUNITY_MUSEUM_PROTECTION,
        "opportunity_total_signatures": OPPORTUNITY_TOTAL_SIGNATURES,
    }
    check(
        "machine_readable_decision_thresholds",
        prereg["machine_thresholds"] == machine_expected
        and opportunity_summary["minimum_affected_opportunity_fraction"]
        == machine_expected["minimum_affected_opportunity_fraction"],
        {"preregistered": prereg["machine_thresholds"], "executable": machine_expected},
    )

    concentration_shape_ok = True
    side_values = {}
    for pair_key, pair in recomputed_metrics["connectivity"]["pairs"].items():
        expected_sides = set(pair_key.split("__"))
        concentration_shape_ok &= set(pair["concentration_by_museum_side"]) == expected_sides
        for museum in expected_sides:
            value = pair["concentration_by_museum_side"][museum]
            concentration_shape_ok &= set(value["top_k_unique_record_concentration"]) == {
                "1",
                "5",
                "10",
            }
        side_values[pair_key] = pair["concentration_by_museum_side"]
    check("per_side_top_k_and_hhi_concentration", concentration_shape_ok, side_values)

    actual_idai_types = sorted(
        {type_name for row in raw_hierarchy for type_name in row.get("types", [])}
    )
    crosswalk_types = sorted(crosswalk["idai_gazetteer_actual_hyphenated_types"])
    unclassified_with_mapped_types = [
        row["target_id"]
        for row in recomputed_nodes
        if row["scope_class"] == "unclassified" and row["source_types"]
    ]
    check(
        "single_source_type_crosswalk",
        actual_idai_types == crosswalk_types
        and unclassified_with_mapped_types == []
        and crosswalk["credit_policy"][
            "broad_or_administrative_new_link_improvement_credit"
        ]
        == 0,
        {
            "actual_idai_types": actual_idai_types,
            "crosswalk_types": crosswalk_types,
            "unclassified_targets_with_mapped_source_types": unclassified_with_mapped_types,
        },
    )

    schema_execution = execute_schema_contract_tests(
        root / "schemas", root / "schema-test-cases.json"
    )
    validate_schema(
        opportunity_summary,
        root / "schemas/opportunity-summary.schema.json",
        "committed opportunity summary",
    )
    validate_schema(
        actual_private_opportunity,
        root / "schemas/private-opportunity-ledger.schema.json",
        "regenerated private opportunity ledger",
    )
    check(
        "all_json_schemas_meta_valid_and_instance_executed",
        _schema_execution_evidence_passed(
            schema_execution, root / "schemas", root / "schema-test-cases.json"
        ),
        schema_execution,
    )

    trusted_attestors = read_json(root / "trusted-run-attestors.json")
    trusted_source_exporters = read_json(root / "trusted-source-exporters.json")
    trusted_reviewers = read_json(root / "trusted-reviewers.json")
    validate_schema(
        trusted_attestors,
        root / "schemas/trusted-run-attestors.schema.json",
        "release-pinned trusted run attestors",
    )
    validate_schema(
        trusted_source_exporters,
        root / "schemas/trusted-source-exporters.schema.json",
        "release-pinned trusted source exporters",
    )
    validate_schema(
        trusted_reviewers,
        root / "schemas/trusted-reviewers.schema.json",
        "release-pinned trusted reviewers and auditors",
    )
    check(
        "production_candidate_trust_gates_fail_closed",
        trusted_attestors["status"] == "NOT_CONFIGURED"
        and trusted_attestors["attestors"] == []
        and trusted_source_exporters["status"] == "NOT_CONFIGURED"
        and trusted_source_exporters["registry_scope"] == "production_release"
        and trusted_source_exporters["exporters"] == []
        and trusted_reviewers["status"] == "NOT_CONFIGURED"
        and trusted_reviewers["trust_tier"] == "PRODUCTION"
        and trusted_reviewers["identities"] == [],
        {
            "trusted_run_attestor_status": trusted_attestors["status"],
            "trusted_source_exporter_status": trusted_source_exporters["status"],
            "trusted_reviewer_status": trusted_reviewers["status"],
            "downstream_product_verdict": "NOT_RUN",
            "effects": {
                "run_completion": trusted_attestors["current_effect"],
                "source_export": trusted_source_exporters["current_effect"],
                "review_evidence": trusted_reviewers["current_effect"],
            },
        },
    )

    correction_policy = read_json(root / "correction-policy.json")
    correction_trust = correction_policy.get("chain_trust", {})
    correction_prior_head = correction_trust.get("prior_head", {})
    check(
        "immutable_primary_and_private_correction_policy",
        correction_policy.get("schema_version")
        == "site-graph-v0-correction-policy/4"
        and type(correction_policy.get("current_primary_corrections_applied")) is int
        and correction_policy["current_primary_corrections_applied"] == 0
        and correction_policy["allowed_operations"] == ["set_site_mention_resolution"]
        and correction_policy["sensitivity_estimands"][
            "fixed_frozen_intent_to_treat"
        ]
        and correction_policy["sensitivity_estimands"][
            "corrected_source_counterfactual_reselection"
        ]
        and correction_trust.get("status") == "NOT_CONFIGURED"
        and correction_trust.get("chain_id")
        == "hapi-site-graph-v0-private-corrections"
        and correction_trust.get("ledger_path")
        == "private/corrections/ledger.json"
        and correction_trust.get("review_artifact_directory")
        == "private/corrections/reviews"
        and correction_trust.get("genesis_commit") is None
        and correction_trust.get("registration") is None
        and correction_prior_head
        == {
            "sequence": 0,
            "record_sha256": None,
            "ledger_commit": None,
            "ledger_sha256": None,
            "ledger_git_blob_oid": None,
        },
        {
            "schema_version": correction_policy.get("schema_version"),
            "current_primary_corrections_applied": correction_policy.get(
                "current_primary_corrections_applied"
            ),
            "allowed_operations": correction_policy.get("allowed_operations"),
            "sensitivity_estimands": correction_policy.get("sensitivity_estimands"),
            "chain_trust": correction_trust,
            "production_sensitivity_status": "BLOCKED_UNTIL_GENUINE_ROOTS_REGISTERED",
        },
    )

    rerun_hashes = reruns.get("deterministic_output_hashes", {})
    public_match = all(
        rerun_hashes.get(name) == sha256(root / name) for name in PUBLIC_BASELINE_OUTPUTS
    )
    check(
        "authenticated_deterministic_baseline_reproduction",
        reruns.get("schema_version") == "site-graph-v0-baseline-rerun-evidence/3"
        and reruns.get("status")
        == {
            "snapshot_acquisition_integrity": "PASS",
            "derived_baseline_reproducibility": "PASS",
            "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
            "overall_contract_status": "READY_SNAPSHOT_CONDITIONAL",
            "downstream_product_verdict": "NOT_RUN",
        }
        and reruns.get("terminology") == "deterministic_reproduction_not_statistical_independence"
        and reruns.get("run_a", {}).get("run_id") != reruns.get("run_b", {}).get("run_id")
        and reruns.get("output_mismatches") == {}
        and reruns.get("metadata_mismatches") == {}
        and reruns.get("input_snapshot_sha256") == sha256(root / "input-snapshot.json")
        and reruns.get("runner_sha256") == sha256(root / "scripts/run_baseline.py")
        and reruns.get("builder_sha256") == sha256(root / "scripts/build_baseline.py")
        and reruns.get("corpus_archive_sha256")
        == snapshot["corpus"]["archive_acquisition"]["archive_sha256"]
        and private_runtime_validation["passed"]
        and public_match,
        {
            "run_a": reruns.get("run_a"),
            "run_b": reruns.get("run_b"),
            "deterministic_output_count": reruns.get("deterministic_output_count"),
            "private_run_runtime_binding": private_runtime_validation,
            "committed_public_outputs_match": public_match,
        },
    )

    rule = prereg["ordered_decision_rule"]
    review_rules = prereg["review_census"]
    check(
        "ordered_decision_and_review_census",
        rule["precedence"] == ["INVALID", "REDESIGN", "CONTINUE", "STOP"]
        and rule["raw_link_rate_growth_can_satisfy_continue"] is False
        and rule["museum_equality_required"] is False
        and review_rules["reviews_per_decision"] == 2
        and review_rules["held_out_sample_is_pass_gate"] is False
        and review_rules["population_precision_claim_permitted"] is False,
        {"decision_rule": rule, "review_census": review_rules},
    )

    provenance = snapshot["corpus"]["provenance"]
    provenance_bytes_authenticated = (
        sha256(root / "corpus-provenance/bundle-README.md")
        == provenance["verified_bundle_readme_sha256"]
        and sha256(root / "corpus-provenance/manifest.json")
        == provenance["verified_bundle_manifest_sha256"]
        and sha256(root / "corpus-provenance/validation/verify_bundle.sh")
        == provenance["verified_bundle_verifier_sha256"]
        and sha256(root / "corpus-provenance/validation/results.json")
        == provenance["verified_bundle_results_sha256"]
    )
    check(
        "snapshot_handoff_metadata_bytes_authenticated",
        provenance_bytes_authenticated
        and "cannot be regenerated bit-for-bit" in provenance["known_reproduction_limit"],
        {
            "snapshot_acquisition_integrity": "PASS",
            "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
            "historical_export_reproducible": False,
            "known_reproduction_limit": provenance["known_reproduction_limit"],
        },
    )

    round_1 = read_json(root / "reviews/round-1/metadata.json")
    round_2 = read_json(root / "reviews/round-2/metadata.json")
    review_ok = (
        sha256(root / "reviews/round-1/prompt.md")
        == round_1["raw_artifacts"]["prompt"]["sha256"]
        and sha256(root / "reviews/round-1/raw-output.txt")
        == round_1["raw_artifacts"]["output"]["sha256"]
        and sha256(root / "reviews/round-2/prompt.md")
        == round_2["artifacts"]["prompt.md"]["sha256"]
        and sha256(root / "reviews/round-2/raw-output.txt")
        == round_2["artifacts"]["raw-output.txt"]["sha256"]
        and round_2["reviewed_commit"] == "0ea47dad1e9e415d0fe76ac1fc0157ce218fbdad"
        and round_2["reviewer_cli"]["version"] == "2.1.247"
        and round_2["reviewer_cli"]["model_selector"] == "opus"
        and round_2["reviewer_cli"]["backend_model_id"] == "not_exposed_by_claude_cli"
    )
    check(
        "historical_review_provenance_authenticated_not_approval",
        review_ok,
        {
            "round_1_reviewed_commit": round_1["reviewed_commit_sha"],
            "round_2_reviewed_commit": round_2["reviewed_commit"],
            "historical_review_outcome": "REQUEST_CHANGES",
            "exact_current_head_external_review_gate": "PENDING_OUTSIDE_COMMIT",
            "implementer_dispositions_are_reviewer_approval": False,
        },
    )

    derived_status = "PASS" if all(item["passed"] for item in checks) else "INVALID"
    overall_status = (
        "READY_SNAPSHOT_CONDITIONAL" if derived_status == "PASS" else "INVALID"
    )
    return {
        "schema_version": "site-graph-v0-validation-report/4",
        "status": {
            "snapshot_acquisition_integrity": "PASS",
            "derived_baseline_reproducibility": derived_status,
            "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
            "overall_contract_status": overall_status,
            "downstream_product_verdict": "NOT_RUN",
            "external_exact_head_review_gate": "PENDING_OUTSIDE_COMMIT",
            "pre_pr_ci_status": "PENDING_OUTSIDE_COMMIT",
        },
        "scope": (
            f"snapshot-conditional evaluation over the authenticated real "
            f"{snapshot['corpus']['canonical_record_count']:,}-record private archive; "
            "fixtures/proxies support no corpus claim and historical export reproducibility "
            "is not asserted"
        ),
        "archive_sha256": archive_attestation["archive"]["sha256"],
        "production_lineage": snapshot["corpus"]["production_lineage"],
        "prohibited_claims": snapshot["corpus"]["production_lineage"][
            "prohibited_inferences"
        ],
        "release_candidate_binding": {
            "hash_algorithm": "sha256",
            "rule": (
                "Every static required release file except validation-report.json is "
                "hashed after semantic recomputation and before release-manifest generation."
            ),
            "files": validation_input_bindings(repo_root),
        },
        "checks": checks,
        "limitations": [
            {
                "id": "upstream_production_lineage_unavailable_disclosed",
                "status": "UNAVAILABLE_DISCLOSED",
                "effect": (
                    "The authorized handoff bytes are verified, but the historical export "
                    "cannot be regenerated from repository history because its export command, "
                    "code revision, and pipeline run identifiers were not supplied."
                ),
            }
        ],
        "summary": {
            "checks": len(checks),
            "passed": sum(item["passed"] for item in checks),
            "failed": sum(not item["passed"] for item in checks),
            "canonical_records": len(records),
            "private_record_evidence_gzip_sha256": record_digest["transport_gzip_sha256"],
            "private_record_evidence_uncompressed_sha256": record_digest[
                "canonical_uncompressed_ndjson_sha256"
            ],
            "archive_sha256": archive_attestation["archive"]["sha256"],
            "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
            "overall_contract_status": overall_status,
            "downstream_product_verdict": "NOT_RUN",
        },
    }


def semantic_report(
    repo_root: Path,
    corpus_archive: Path,
    corpus_archive_sidecar: Path,
    private_run: Path,
) -> dict:
    """Authenticate release code and the external archive, then recompute."""
    _activate_authenticated_release(repo_root)
    with authenticated_corpus(
        repo_root, corpus_archive, corpus_archive_sidecar
    ) as (corpus, archive_attestation):
        return _semantic_report(
            repo_root,
            corpus,
            private_run,
            archive_attestation,
            _release_activated=True,
        )


def semantic_report_for_release_generation(
    repo_root: Path,
    corpus_archive: Path,
    corpus_archive_sidecar: Path,
    private_run: Path,
) -> dict:
    """Recompute a report from an exact dirty-candidate snapshot.

    This is deliberately unavailable to the public validation CLI. Its immediate
    caller must be the target release's generation script; the resulting report still
    requires a subsequent freeze and ordinary fail-closed validator pass.
    """
    repo_root = repo_root.resolve()
    expected_caller = (
        repo_root / EVALUATION_RELATIVE / "scripts/generate_validation_report.py"
    ).resolve()
    frame = inspect.currentframe()
    caller = frame.f_back if frame is not None else None
    caller_file = (
        Path(caller.f_code.co_filename).resolve() if caller is not None else None
    )
    del frame
    if caller_file != expected_caller:
        raise ReleaseIntegrityPreflightError(
            "dirty-candidate report generation is callable only from "
            f"{expected_caller}"
        )
    if Path(__file__).resolve() != (
        repo_root / EVALUATION_RELATIVE / "scripts/validate_contract.py"
    ).resolve():
        raise ReleaseIntegrityPreflightError(
            "release generation must import validate_contract.py from --repo-root"
        )

    candidate = _candidate_release_preimport(repo_root)
    expected_files = candidate["candidate_files"]
    _activate_release_modules(repo_root, candidate)
    with authenticated_corpus(
        repo_root, corpus_archive, corpus_archive_sidecar
    ) as (corpus, archive_attestation):
        report = _semantic_report(
            repo_root,
            corpus,
            private_run,
            archive_attestation,
            _release_activated=True,
        )
    actual_files = {
        relative: {
            "bytes": (repo_root / relative).stat().st_size,
            "sha256": _bootstrap_sha256(repo_root / relative),
        }
        for relative in expected_files
    }
    if actual_files != expected_files:
        raise ReleaseIntegrityPreflightError(
            "release candidate bytes changed during semantic report recomputation"
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--corpus-archive", type=Path, required=True)
    parser.add_argument("--corpus-archive-sidecar", type=Path, required=True)
    parser.add_argument("--private-run", type=Path, required=True)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    try:
        integrity = _activate_authenticated_release(repo_root)
    except ReleaseIntegrityPreflightError as error:
        print(
            json.dumps(
                {
                    "snapshot_acquisition_integrity": "BLOCKED",
                    "derived_baseline_reproducibility": "INVALID",
                    "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
                    "overall_contract_status": "INVALID",
                    "downstream_product_verdict": "NOT_RUN",
                    "phase": "release_integrity",
                    "semantic_release_modules_activated": False,
                    "error": str(error),
                },
                sort_keys=True,
            )
        )
        raise SystemExit(1) from error
    try:
        report = semantic_report(
            repo_root,
            args.corpus_archive.resolve(),
            args.corpus_archive_sidecar.resolve(),
            args.private_run.resolve(),
        )
    except CorpusArchiveBlocked as error:
        print(
            json.dumps(
                {
                    "snapshot_acquisition_integrity": "BLOCKED",
                    "derived_baseline_reproducibility": "BLOCKED",
                    "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
                    "overall_contract_status": "BLOCKED",
                    "downstream_product_verdict": "NOT_RUN",
                    "error": str(error),
                },
                sort_keys=True,
            )
        )
        raise SystemExit(1) from error
    except CorpusArchiveInvalid as error:
        print(
            json.dumps(
                {
                    "snapshot_acquisition_integrity": "INVALID",
                    "derived_baseline_reproducibility": "BLOCKED",
                    "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
                    "overall_contract_status": "INVALID",
                    "downstream_product_verdict": "NOT_RUN",
                    "error": str(error),
                },
                sort_keys=True,
            )
        )
        raise SystemExit(1) from error
    committed = read_json(
        repo_root / "docs/evaluations/site-graph-v0/validation-report.json"
    )
    report_matches = report == committed
    output = {
        "status": (
            report["status"]
            if report_matches
            else {
                **report["status"],
                "overall_contract_status": "INVALID",
                "derived_baseline_reproducibility": "INVALID",
            }
        ),
        "release_integrity": integrity,
        "committed_validation_report_matches_recomputation": report_matches,
        **report["summary"],
    }
    print(json.dumps(output, sort_keys=True))
    if (
        report["status"]["overall_contract_status"]
        != "READY_SNAPSHOT_CONDITIONAL"
        or not report_matches
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
