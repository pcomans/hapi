#!/usr/bin/env python3
"""Freeze museum mentions without reading an authority vocabulary.

This module intentionally imports only the Python standard library.  Detection and
span boundaries come from museum field structure and fixed syntax rules.  Authority
labels, aliases, identifiers, and resolver results are not inputs to this phase.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import tarfile
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Iterable


ARCHIVE_PREFIX = "hapi-museum-corpus-2026-08-27"
EVALUATION_DATE = "2026-09-13"
CORPUS_SNAPSHOT_DATE = "2026-08-27"
EXPECTED_ARCHIVE_SHA256 = "f4aabc2fc03b3ee0b5965bb9b27129e0ac482dae086c6124dd0d73d70276cc5b"
EXPECTED_MEMBER_SHA256 = {
    "data/artifacts.ndjson.gz": "b69fb207b5775f3fca3e3fe6c1dad13df91b0d90afdf196c17d869721be4ca24",
    "data/raw_brooklyn.ndjson.gz": "b68ee05e1f86a664730933ee38b8178c3bcf789a32c017135877f17abf306b31",
    "data/raw_harvard.ndjson.gz": "1ac4e06ce7b3859fefdd43039c8ddbee42c6e3a80311d916db7751be79b8178f",
    "data/raw_met.ndjson.gz": "cc81d0f676e63137fbe8575982fbb20b2b997686536d6f2a6a634d924da3394e",
}
EXPECTED_CANONICAL_COUNTS = {"met": 27_969, "brooklyn": 7_554, "harvard": 722}
EXPECTED_RAW_COUNTS = {"met": 27_969, "brooklyn": 8_832, "harvard": 722}

WS = re.compile(r"\s+")
ROYAL_CUE = re.compile(r"\b(reigns?\s+of|pontificate\s+of|pharaoh|king|queen|ruler)\b", re.I)
TOMB_CODE = re.compile(
    r"\b(?:KV|QV|TT)\s*\d+[A-Za-z]?\b|\bTomb\s+[A-Z]{1,4}[ .-]?\d+[A-Za-z]?\b",
    re.I,
)
TEMPLE_CUE = re.compile(r"\btemple\b", re.I)
UNCERTAIN = re.compile(r"\b(?:possibly|probably|perhaps|uncertain(?:ly)?|maybe|attributed)\b|\?", re.I)
RANGE_OR_MULTI = re.compile(r"\s(?:-|\u2013|\u2014)\s|[\u2013\u2014]|\b(?:or|and|to|through)\b", re.I)
TEMPORAL_CONTEXT = re.compile(r"\b(?:before|after|earliest|latest|later|earlier|death\s+of)\b", re.I)
LEADING_REIGN = re.compile(
    r"^\s*(?:(?:early|late|middle|mid|end\s+of|beginning\s+of|latter\s+part\s+of)\s+)?"
    r"(?:reigns?\s+of|pontificate\s+of)\s+",
    re.I,
)
LEADING_UNCERTAIN_REIGN = re.compile(
    r"^\s*(?:possibly|probably|perhaps)\s+(?:the\s+)?(?:reigns?\s+of|pontificate\s+of)\s+",
    re.I,
)
TRAILING_PHASE = re.compile(
    r"\s*,?\s+(?:early|late|middle|mid|first\s+half|second\s+half|approximately|ca\.?|c\.?)$",
    re.I,
)
NAME_TOKEN = re.compile(r"[^\W_\d][\w\u00c0-\u024f\u1e00-\u1eff'\u2019-]*|\d+", re.UNICODE)
TEXT_STOP = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of", "on", "or", "the", "to",
    "with", "wearing", "possibly", "probably", "perhaps", "mother", "wife", "daughter", "son", "statue",
    "head", "god", "goddess", "priest", "scribe", "servant", "sky", "upper", "lower", "new", "old",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def read_exact_archive_members(archive: Path) -> dict[str, bytes]:
    actual_archive_sha = sha256_path(archive)
    if actual_archive_sha != EXPECTED_ARCHIVE_SHA256:
        raise ValueError(f"archive SHA-256 mismatch: {actual_archive_sha}")
    wanted = {f"{ARCHIVE_PREFIX}/{name}": name for name in EXPECTED_MEMBER_SHA256}
    found: dict[str, bytes] = {}
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.getmembers():
            relative = wanted.get(member.name)
            if relative is None:
                continue
            if relative in found:
                raise ValueError(f"duplicate archive member: {relative}")
            if not member.isfile():
                raise ValueError(f"required archive member is not a regular file: {relative}")
            extracted = bundle.extractfile(member)
            if extracted is None:
                raise ValueError(f"cannot read archive member: {relative}")
            found[relative] = extracted.read()
    missing = sorted(set(EXPECTED_MEMBER_SHA256) - set(found))
    if missing:
        raise ValueError(f"missing archive members: {missing}")
    for name, expected in EXPECTED_MEMBER_SHA256.items():
        actual = sha256_bytes(found[name])
        if actual != expected:
            raise ValueError(f"archive member SHA-256 mismatch for {name}: {actual}")
    return found


def load_gzip_ndjson(data: bytes, label: str) -> list[dict]:
    with gzip.GzipFile(fileobj=io.BytesIO(data), mode="rb") as compressed:
        raw = compressed.read()
    rows = []
    for line_number, line in enumerate(raw.splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON in {label} line {line_number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"non-object row in {label} line {line_number}")
        rows.append(row)
    return rows


def classify_reign_expression(value: str) -> tuple[str, str | None, tuple[int, int] | None]:
    text = value.strip()
    offset = value.find(text)
    if not text:
        return "empty", None, None
    if LEADING_UNCERTAIN_REIGN.match(text) or UNCERTAIN.search(text):
        return "uncertain_identity", None, None
    match = LEADING_REIGN.match(text)
    if not match:
        return "unparsed_structured_value", None, None
    remainder = text[match.end():]
    leading = len(remainder) - len(remainder.lstrip())
    candidate = TRAILING_PHASE.sub("", remainder.strip()).strip()
    start = offset + match.end() + leading
    if TEMPORAL_CONTEXT.search(candidate):
        return "temporal_context", None, None
    if RANGE_OR_MULTI.search(candidate):
        return "multi_or_range", None, None
    if not candidate:
        return "unparsed_structured_value", None, None
    return "single_identity", candidate, (start, start + len(candidate))


def candidate_after_royal_cue(text: str, cue: re.Match[str]) -> tuple[str | None, int, int]:
    """Bound a cued name with syntax alone: at most three title-cased/name tokens."""
    tail = text[cue.end():]
    leading = len(tail) - len(tail.lstrip(" :-,\t"))
    start = cue.end() + leading
    tokens = list(NAME_TOKEN.finditer(text[start:]))
    selected: list[re.Match[str]] = []
    previous_end = 0
    for token in tokens:
        gap = text[start + previous_end:start + token.start()]
        if selected and (re.search(r"[,;:()\[\]?!]", gap) or len(gap.split()) > 1):
            break
        word = token.group(0)
        if word.casefold() in TEXT_STOP:
            break
        if not (word[0].isupper() or word.isdigit()):
            break
        selected.append(token)
        previous_end = token.end()
        if len(selected) == 3:
            break
    if not selected:
        return None, start, start
    end = start + selected[-1].end()
    return text[start:end], start, end


def component_spans(text: str) -> Iterable[tuple[str, int, int]]:
    """Split top-level comma/semicolon components without cutting parentheses."""
    last = 0
    depth = 0
    for index, character in enumerate(text):
        if character == "(":
            depth += 1
        elif character == ")" and depth:
            depth -= 1
        elif character in ",;" and depth == 0:
            raw = text[last:index]
            leading = len(raw) - len(raw.lstrip())
            trailing = len(raw.rstrip())
            if raw.strip():
                yield raw.strip(), last + leading, last + trailing
            last = index + 1
    raw = text[last:]
    leading = len(raw) - len(raw.lstrip())
    trailing = len(raw.rstrip())
    if raw.strip():
        yield raw.strip(), last + leading, last + trailing


def component_variants(text: str) -> list[tuple[str, int, int, str]]:
    variants = [(text, 0, len(text), "structured_location_component")]
    position = text.find("(")
    if position > 0 and text.endswith(")"):
        child = text[:position].rstrip()
        if child and child != text:
            variants.append((child, 0, len(child), "structured_pre_parenthesis_component"))
    return variants


def make_mention(
    *, artifact: dict, entity_type: str, field_path: str, field_value: str,
    start: int, end: int, extraction_method: str, evidence_role: str,
    expression_type: str,
) -> dict:
    if not (0 <= start < end <= len(field_value)):
        raise ValueError(f"invalid span {start}:{end} for {artifact['id']} {field_path}")
    text = field_value[start:end]
    stable = "\x1f".join(
        (artifact["id"], entity_type, field_path, str(start), str(end), text, extraction_method, expression_type)
    )
    return {
        "mention_id": "mention-" + hashlib.sha256(stable.encode("utf-8")).hexdigest()[:20],
        "artifact_id": artifact["id"],
        "museum": artifact["source_museum"],
        "source_id": artifact["source_id"],
        "entity_type": entity_type,
        "field_path": field_path,
        "field_value": field_value,
        "span_start": start,
        "span_end": end,
        "mention_text": text,
        "extraction_method": extraction_method,
        "evidence_role": evidence_role,
        "expression_type": expression_type,
    }


def extract_mentions(canonical: list[dict], raw_indexes: dict[str, dict[str, dict]]) -> tuple[list[dict], dict]:
    mentions: list[dict] = []
    cue_without_candidate = Counter()
    records_with_mentions: set[str] = set()
    for artifact in sorted(canonical, key=lambda row: row["id"]):
        museum = artifact["source_museum"]
        raw = raw_indexes[museum][artifact["source_id"]]
        before = len(mentions)

        if museum == "met" and isinstance(raw.get("reign"), str) and raw["reign"].strip():
            field_value = raw["reign"]
            expression, candidate, span = classify_reign_expression(field_value)
            if expression == "single_identity" and candidate is not None and span is not None:
                start, end = span
            else:
                stripped = field_value.strip()
                start, end = field_value.find(stripped), field_value.find(stripped) + len(stripped)
            mentions.append(make_mention(
                artifact=artifact, entity_type="ruler", field_path="reign", field_value=field_value,
                start=start, end=end, extraction_method="typed_structured_reign_parser",
                evidence_role="catalogued_reign", expression_type=expression,
            ))

        ruler_text_fields = {
            "met": ("title",),
            "brooklyn": ("title", "inscribed", "dates", "objectDate", "provenance"),
            "harvard": ("title", "description", "labeltext", "commentary", "dated", "contextualtext"),
        }[museum]
        seen_ruler_spans: set[tuple[str, int, int]] = set()
        for field in ruler_text_fields:
            value = raw.get(field)
            if not isinstance(value, str) or not value.strip():
                continue
            for cue in ROYAL_CUE.finditer(value):
                if value[cue.end():cue.end() + 2].startswith(("'", "\u2019")):
                    continue
                candidate, start, end = candidate_after_royal_cue(value, cue)
                if candidate is None:
                    cue_without_candidate[f"{museum}|{field}"] += 1
                    continue
                if (field, start, end) in seen_ruler_spans:
                    continue
                seen_ruler_spans.add((field, start, end))
                context = value[max(0, cue.start() - 15):min(len(value), end + 24)]
                if UNCERTAIN.search(context):
                    expression = "uncertain_identity"
                elif RANGE_OR_MULTI.search(context):
                    expression = "multi_or_range"
                else:
                    expression = "single_identity"
                mentions.append(make_mention(
                    artifact=artifact, entity_type="ruler", field_path=field, field_value=value,
                    start=start, end=end, extraction_method="explicit_royal_cue_grammar",
                    evidence_role="explicit_royal_text_cue", expression_type=expression,
                ))

        site_values: list[tuple[str, str, str]] = []
        if museum == "met":
            role = raw.get("geographyType") or "unspecified"
            for field in ("country", "region", "subregion", "locale", "locus"):
                value = raw.get(field)
                if isinstance(value, str) and value.strip():
                    site_values.append((field, value, f"{role}:{field}"))
            excavation = raw.get("excavation")
            if isinstance(excavation, str) and excavation.strip():
                stripped = excavation.strip()
                start = excavation.find(stripped)
                mentions.append(make_mention(
                    artifact=artifact, entity_type="excavation", field_path="excavation",
                    field_value=excavation, start=start, end=start + len(stripped),
                    extraction_method="explicit_structured_value", evidence_role="excavation_credit",
                    expression_type="single_identity",
                ))
        elif museum == "brooklyn":
            for index, place in enumerate(raw.get("geographicalLocations") or []):
                if not isinstance(place, dict):
                    continue
                role = place.get("type") or "unspecified"
                value = place.get("name")
                if isinstance(value, str) and value.strip():
                    site_values.append((f"geographicalLocations[{index}].name", value, role))
                else:
                    for leaf in ("city", "country"):
                        value = place.get(leaf)
                        if isinstance(value, str) and value.strip():
                            site_values.append((f"geographicalLocations[{index}].{leaf}", value, role))
        else:
            for index, place in enumerate(raw.get("places") or []):
                if not isinstance(place, dict):
                    continue
                value = place.get("displayname")
                if isinstance(value, str) and value.strip():
                    site_values.append((
                        f"places[{index}].displayname", value, place.get("type") or "unspecified"
                    ))

        for field_path, field_value, role in site_values:
            for component, component_start, component_end in component_spans(field_value):
                emitted_tomb_spans: set[tuple[int, int]] = set()
                for text, relative_start, relative_end, method in component_variants(component):
                    start, end = component_start + relative_start, component_start + relative_end
                    if TEMPLE_CUE.search(text):
                        entity_type = "temple"
                    elif TOMB_CODE.fullmatch(text):
                        entity_type = "tomb_monument"
                    else:
                        entity_type = "site"
                    if entity_type == "tomb_monument":
                        emitted_tomb_spans.add((start, end))
                    mentions.append(make_mention(
                        artifact=artifact, entity_type=entity_type, field_path=field_path,
                        field_value=field_value, start=start, end=end, extraction_method=method,
                        evidence_role=role, expression_type="single_identity",
                    ))
                for hit in TOMB_CODE.finditer(component):
                    hit_span = (component_start + hit.start(), component_start + hit.end())
                    if hit_span in emitted_tomb_spans:
                        continue
                    mentions.append(make_mention(
                        artifact=artifact, entity_type="tomb_monument", field_path=field_path,
                        field_value=field_value, start=hit_span[0], end=hit_span[1],
                        extraction_method="explicit_tomb_code",
                        evidence_role=role, expression_type="single_identity",
                    ))

        if len(mentions) > before:
            records_with_mentions.add(artifact["id"])

    mentions.sort(key=lambda row: (
        row["artifact_id"], row["entity_type"], row["field_path"], row["span_start"],
        row["span_end"], row["extraction_method"], row["mention_id"],
    ))
    ids = [row["mention_id"] for row in mentions]
    if len(ids) != len(set(ids)):
        raise ValueError("mention identifiers are not unique")
    for row in mentions:
        if row["field_value"][row["span_start"]:row["span_end"]] != row["mention_text"]:
            raise ValueError(f"span/text mismatch for {row['mention_id']}")
    diagnostics = {
        "records_scanned": len(canonical),
        "records_with_at_least_one_mention": len(records_with_mentions),
        "mentions": len(mentions),
        "mentions_by_museum": dict(sorted(Counter(row["museum"] for row in mentions).items())),
        "mentions_by_entity_type": dict(sorted(Counter(row["entity_type"] for row in mentions).items())),
        "royal_cues_without_syntactic_candidate": dict(sorted(cue_without_candidate.items())),
    }
    return mentions, diagnostics


def write_ledger(path: Path, rows: list[dict]) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    uncompressed_digest = hashlib.sha256()
    mention_id_digest = hashlib.sha256()
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", compresslevel=9, mtime=0) as compressed:
            for row in rows:
                encoded = canonical_json_bytes(row)
                compressed.write(encoded)
                uncompressed_digest.update(encoded)
                mention_id_digest.update((row["mention_id"] + "\n").encode("utf-8"))
    return {
        "path_basename": path.name,
        "rows": len(rows),
        "gzip_sha256": sha256_path(path),
        "canonical_uncompressed_sha256": uncompressed_digest.hexdigest(),
        "ordered_mention_ids_sha256": mention_id_digest.hexdigest(),
    }


def build_from_archive(archive: Path, ledger_path: Path, manifest_path: Path) -> dict:
    members = read_exact_archive_members(archive)
    canonical = load_gzip_ndjson(members["data/artifacts.ndjson.gz"], "canonical")
    canonical_counts = Counter(row.get("source_museum") for row in canonical)
    if dict(canonical_counts) != EXPECTED_CANONICAL_COUNTS:
        raise ValueError(f"canonical museum counts mismatch: {dict(canonical_counts)}")
    canonical_ids = [row.get("id") for row in canonical]
    if None in canonical_ids or len(canonical_ids) != len(set(canonical_ids)):
        raise ValueError("canonical record identifiers are missing or duplicated")

    raw_indexes: dict[str, dict[str, dict]] = {}
    for museum in ("met", "brooklyn", "harvard"):
        rows = load_gzip_ndjson(members[f"data/raw_{museum}.ndjson.gz"], f"raw_{museum}")
        if len(rows) != EXPECTED_RAW_COUNTS[museum]:
            raise ValueError(f"raw {museum} count mismatch: {len(rows)}")
        index: dict[str, dict] = {}
        for row in rows:
            source_id = str(row.get("object_id"))
            if source_id in index:
                raise ValueError(f"duplicate raw {museum} object_id: {source_id}")
            if not isinstance(row.get("data"), dict):
                raise ValueError(f"raw {museum} payload is not an object: {source_id}")
            index[source_id] = row["data"]
        raw_indexes[museum] = index
    for artifact in canonical:
        museum = artifact["source_museum"]
        if artifact["source_id"] not in raw_indexes[museum]:
            raise ValueError(f"missing raw payload for canonical record {artifact['id']}")

    mentions, diagnostics = extract_mentions(canonical, raw_indexes)
    ledger = write_ledger(ledger_path, mentions)
    manifest = {
        "schema_version": "hapi-authority-independent-mention-ledger/1",
        "evaluation_date": EVALUATION_DATE,
        "archive": {
            "snapshot_date": CORPUS_SNAPSHOT_DATE,
            "sha256": EXPECTED_ARCHIVE_SHA256,
            "member_sha256": dict(sorted(EXPECTED_MEMBER_SHA256.items())),
            "canonical_counts": EXPECTED_CANONICAL_COUNTS,
            "raw_counts": EXPECTED_RAW_COUNTS,
        },
        "independence_contract": {
            "inputs": ["canonical rows", "raw museum payloads", "fixed field map", "fixed syntax rules"],
            "authority_labels_aliases_ids_consulted": False,
            "span_invariant": "mention_text == field_value[span_start:span_end]",
        },
        "diagnostics": diagnostics,
        "ledger": ledger,
        "extractor_sha256": sha256_path(Path(__file__)),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_from_archive(args.archive, args.ledger, args.manifest)
    print(json.dumps({"ledger": manifest["ledger"], "diagnostics": manifest["diagnostics"]}, indent=2))


if __name__ == "__main__":
    main()
