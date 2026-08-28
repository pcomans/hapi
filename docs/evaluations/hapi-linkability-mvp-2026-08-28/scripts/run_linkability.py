#!/usr/bin/env python3
"""Disposable, deterministic full-corpus linkability adapter.

This evaluates only the authority representations committed in the repository.  It is
not production enrichment and it contains no web-adjudicated aliases or identities.
"""

from __future__ import annotations

import collections
import gzip
import hashlib
import io
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(os.environ.get("HAPI_ROOT", "/workspaces/content"))
CORPUS = Path(os.environ.get("HAPI_CORPUS", "/tmp/hapi-corpus-2026-08-27"))
OUT = Path(os.environ.get("HAPI_EVAL_OUT", "/tmp/hapi-linkability-mvp"))
AUTH = ROOT / "pipeline" / "pipeline" / "authority"
GRAPH = ROOT / "web-claimgraph" / "data" / "claim-graph.json"
IDAI = AUTH / "sources" / "idai-gazetteer" / "reconciled.jsonl"
PM_THEBAN = AUTH / "sources" / "porter-moss-theban-necropolis" / "reconciled.jsonl"
PM_MEMPHIS = AUTH / "sources" / "porter-moss-memphis" / "reconciled.jsonl"

sys.path.insert(0, str(ROOT / "pipeline"))
from pipeline.authority.claimgraph.normalize import NameForm, keys_for_form  # noqa: E402


NAME_PREDICATES = {"hapi:display_name", "hapi:prenomen", "hapi:horus_name", "hapi:nomen"}
WS = re.compile(r"\s+")
PART_SPLIT = re.compile(r"\s*(?:,|;)\s*")
ROYAL_CUE = re.compile(r"\b(reigns?\s+of|pontificate\s+of|pharaoh|king|queen|ruler)\b", re.I)
TOMB_CODE = re.compile(r"\b(?:KV|QV|TT)\s*\d+[A-Za-z]?\b|\bTomb\s+[A-Z]{1,4}[ .-]?\d+[A-Za-z]?\b", re.I)
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
TEXT_STOP = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of", "on", "or", "the", "to",
    "with", "wearing", "possibly", "probably", "perhaps", "mother", "wife", "daughter", "son", "statue",
    "head", "god", "goddess", "priest", "scribe", "servant", "sky", "upper", "lower", "new", "old",
}


def load_ndjson_gz(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl_gz(path: Path, rows: Iterable[dict]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", compresslevel=9, mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def surface_key(text: str) -> str:
    return WS.sub(" ", unicodedata.normalize("NFC", text).strip()).casefold()


def place_norm(text: str) -> str:
    s = unicodedata.normalize("NFKD", text.casefold())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.translate(str.maketrans({"ꜣ": "a", "ꜥ": "a", "ʿ": "a", "‘": "'", "’": "'"}))
    # Parenthetical ancient/modern qualifiers are not discarded: they can distinguish
    # labels. Punctuation and spacing alone are normalized.
    return re.sub(r"[^a-z0-9]+", "", s)


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Target:
    target_id: str
    label: str
    entity_type: str
    representation: str


class Resolver:
    def __init__(self) -> None:
        self.targets: dict[str, Target] = {}
        self.exact: dict[str, set[str]] = collections.defaultdict(set)
        self.normalized: dict[str, set[str]] = collections.defaultdict(set)

    def add(self, target: Target, labels: Iterable[str], norm_fn) -> None:
        self.targets[target.target_id] = target
        for label in labels:
            if not label or not label.strip():
                continue
            self.exact[surface_key(label)].add(target.target_id)
            for key in norm_fn(label):
                if key:
                    self.normalized[key].add(target.target_id)

    def resolve(self, text: str, norm_fn) -> dict:
        exact = sorted(self.exact.get(surface_key(text), ()))
        norm_keys = sorted(set(norm_fn(text)))
        normalized = sorted({target for key in norm_keys for target in self.normalized.get(key, ())})
        exact_status = "unique" if len(exact) == 1 else "ambiguous" if exact else "unmatched"
        if exact:
            final = exact
            method = "raw_exact"
        else:
            final = normalized
            method = "committed_normalized" if normalized else None
        status = "resolved" if len(final) == 1 else "ambiguous" if len(final) > 1 else "unmatched"
        return {
            "raw_exact_status": exact_status,
            "raw_exact_target_ids": exact,
            "normalized_keys": norm_keys,
            "resolution_method": method,
            "status": status,
            "target_ids": final,
        }


def ruler_norm(text: str) -> set[str]:
    # The committed normalizer's phonetic/transliteration paths, but never its lossy
    # skeleton path, are permitted for artifact-to-authority resolution.
    return keys_for_form(NameForm(surface=text), skeleton=False)


def place_norm_set(text: str) -> set[str]:
    key = place_norm(text)
    return {key} if key else set()


def build_ruler_resolver(graph: dict) -> tuple[Resolver, dict]:
    resolver = Resolver()
    node_by_id = {r["id"]: r for r in graph["rulers"]}
    member_unit: dict[str, str] = {}
    unit_members: dict[str, list[str]] = {}
    for cluster in graph["clusters"]:
        unit_members[cluster["id"]] = sorted(cluster["member_ids"])
        for member in cluster["member_ids"]:
            if member in member_unit:
                raise RuntimeError(f"overlapping graph cluster for {member}")
            member_unit[member] = cluster["id"]
    for node_id in node_by_id:
        if node_id not in member_unit:
            unit_members[node_id] = [node_id]
            member_unit[node_id] = node_id

    claims_by_node: dict[str, list[dict]] = collections.defaultdict(list)
    for claim in graph["claims"]:
        if claim["predicate"] in NAME_PREDICATES:
            claims_by_node[claim["subject_id"]].append(claim)
    cluster_by_id = {c["id"]: c for c in graph["clusters"]}
    catalog = {}
    for unit_id in sorted(unit_members):
        members = unit_members[unit_id]
        label = cluster_by_id[unit_id]["label"] if unit_id in cluster_by_id else node_by_id[unit_id]["display_name"]
        representation = "approved_claim_graph_cluster" if unit_id in cluster_by_id else "claim_graph_singleton_source_node"
        target = Target(unit_id, label, "ruler", representation)
        labels = []
        source_ids = []
        claim_ids = []
        for member in members:
            labels.append(node_by_id[member]["display_name"])
            source_ids.append(node_by_id[member]["source_id"])
            for claim in claims_by_node[member]:
                claim_ids.append(claim["id"])
                labels.extend(v for v in (claim.get("value_text"), claim.get("value_translit")) if v)
        resolver.add(target, labels, ruler_norm)
        catalog[unit_id] = {
            "label": label,
            "entity_type": "ruler",
            "representation": representation,
            "member_ids": members,
            "source_ids": sorted(set(source_ids)),
            "name_claim_ids": sorted(set(claim_ids)),
            "label_count_including_duplicates": len(labels),
        }
    return resolver, catalog


def build_site_resolver(rows: list[dict]) -> tuple[Resolver, dict]:
    resolver = Resolver()
    catalog = {}
    for row in sorted((r for r in rows if r.get("kind") == "site"), key=lambda r: r["id"]):
        target = Target(row["id"], row["display"], "site", "idai_reconciled_source_row")
        labels = [row["display"], *(row.get("alt_labels") or [])]
        resolver.add(target, labels, place_norm_set)
        catalog[row["id"]] = {
            "label": row["display"],
            "entity_type": "site",
            "representation": "idai_reconciled_source_row",
            "types": row.get("types") or [],
            "parent_id": row.get("parent_id"),
            "parent_in_file": row.get("parent_in_file"),
            "cross_refs": row.get("cross_refs") or {},
        }
    return resolver, catalog


def build_pm_resolver() -> tuple[Resolver, dict]:
    resolver = Resolver()
    catalog = {}
    for source, path in (("pm_theban", PM_THEBAN), ("pm_memphis", PM_MEMPHIS)):
        for row in sorted(load_jsonl(path), key=lambda r: r["tomb_id"]):
            target_id = f"{source}:{row['tomb_id']}"
            target = Target(target_id, row["tomb_id"], "tomb_monument", f"{source}_reconciled_source_row")
            labels = [row["tomb_id"], *(row.get("tomb_aliases") or [])]
            # Do not treat occupants, areas, or free notes as aliases of a tomb.
            resolver.add(target, labels, place_norm_set)
            catalog[target_id] = {
                "label": row["tomb_id"],
                "entity_type": "tomb_monument",
                "representation": f"{source}_reconciled_source_row",
                "aliases": row.get("tomb_aliases") or [],
                "occupant_name": row.get("occupant_name"),
                "area": row.get("theban_area") or row.get("memphite_area"),
                "source_citation": row.get("source_citation"),
            }
    return resolver, catalog


def string_spans(text: str, field_path: str) -> Iterable[tuple[str, int, int, str]]:
    """Yield comma/semicolon components with exact offsets in the source field."""
    last = 0
    for match in PART_SPLIT.finditer(text):
        raw = text[last:match.start()]
        leading = len(raw) - len(raw.lstrip())
        trailing = len(raw.rstrip())
        if raw.strip():
            yield raw.strip(), last + leading, last + trailing, field_path
        last = match.end()
    raw = text[last:]
    leading = len(raw) - len(raw.lstrip())
    trailing = len(raw.rstrip())
    if raw.strip():
        yield raw.strip(), last + leading, last + trailing, field_path


def strip_parenthetical_container(text: str) -> list[tuple[str, int, int]]:
    """Return original component plus a deterministic pre-parenthesis child label.

    Both are kept so the adapter does not erase potentially distinguishing context. The
    derived child is explicitly labelled and never masquerades as raw exact evidence.
    """
    out = [(text, 0, len(text))]
    pos = text.find("(")
    if pos > 0 and text.endswith(")"):
        child = text[:pos].rstrip()
        if child and child != text:
            out.append((child, 0, len(child)))
    return out


def classify_reign_expression(value: str) -> tuple[str, str | None, tuple[int, int] | None]:
    text = value.strip()
    offset = value.find(text)
    if not text:
        return "empty", None, None
    uncertain_prefix = bool(LEADING_UNCERTAIN_REIGN.match(text))
    if uncertain_prefix or UNCERTAIN.search(text):
        return "uncertain_identity", None, None
    m = LEADING_REIGN.match(text)
    if not m:
        # Structured field values are retained, but non-reign context is not coerced.
        return "unparsed_structured_value", None, None
    candidate = text[m.end():].strip()
    start = offset + m.end() + (len(text[m.end():]) - len(text[m.end():].lstrip()))
    candidate = TRAILING_PHASE.sub("", candidate).strip()
    if TEMPORAL_CONTEXT.search(candidate):
        return "temporal_context", None, None
    if RANGE_OR_MULTI.search(candidate):
        return "multi_or_range", None, None
    if not candidate:
        return "unparsed_structured_value", None, None
    return "single_identity", candidate, (start, start + len(candidate))


def candidate_after_cue(text: str, cue: re.Match, resolver: Resolver) -> tuple[str | None, int, int, str]:
    """Extract an explicit proper-name phrase after a royal cue, conservatively."""
    tail = text[cue.end():]
    leading = len(tail) - len(tail.lstrip(" :-,\t"))
    start = cue.end() + leading
    if start >= len(text):
        return None, start, start, "no_name_after_cue"
    # Capture words with letters, apostrophes, hyphens, or a Roman/Arabic ordinal.
    tokens = list(re.finditer(r"[^\W_\d][\w\u00c0-\u024f\u1e00-\u1eff'\u2019-]*|\d+", text[start:], re.UNICODE))
    contiguous = []
    prior_end = 0
    for token in tokens:
        gap = text[start + prior_end:start + token.start()]
        if contiguous and (re.search(r"[,;:()\[\]?!]", gap) or len(gap.split()) > 1):
            break
        word = token.group(0)
        if word.casefold() in TEXT_STOP:
            break
        if not contiguous and not (word[0].isupper() or word.isdigit()):
            break
        contiguous.append(token)
        prior_end = token.end()
        if len(contiguous) >= 5:
            break
    if not contiguous:
        return None, start, start, "generic_royal_cue"
    # Try longest authority-resolvable prefix first. This does not add aliases or facts;
    # it only bounds the span of an explicitly cued proper-name phrase.
    for count in range(len(contiguous), 0, -1):
        end = start + contiguous[count - 1].end()
        candidate = text[start:end].strip()
        result = resolver.resolve(candidate, ruler_norm)
        if result["status"] != "unmatched":
            return candidate, start, end, "authority_bounded_explicit_cue"
    # An unmatched candidate remains observable, limited to two tokens to avoid swallowing
    # a sentence. It can be reviewed as a missing alias/authority gap.
    count = min(2, len(contiguous))
    end = start + contiguous[count - 1].end()
    return text[start:end].strip(), start, end, "explicit_cue_unmatched_candidate"


def make_mention(
    *, artifact: dict, entity_type: str, field_path: str, field_value: str,
    text: str, start: int, end: int, extraction_method: str, evidence_role: str,
    expression_type: str, resolution: dict, sequence: int, source_layer: str = "raw",
) -> dict:
    stable = "\x1f".join([
        artifact["id"], entity_type, field_path, str(start), str(end), text,
        extraction_method, expression_type, str(sequence),
    ])
    mention_id = "mention-" + sha_text(stable)[:20]
    row = {
        "mention_id": mention_id,
        "artifact_id": artifact["id"],
        "museum": artifact["source_museum"],
        "source_id": artifact["source_id"],
        "source_url": artifact["source_url"],
        "artifact_title": artifact.get("title"),
        "entity_type": entity_type,
        "source_layer": source_layer,
        "field_path": field_path,
        "field_value": field_value,
        "span_start": start,
        "span_end": end,
        "mention_text": text,
        "extraction_method": extraction_method,
        "evidence_role": evidence_role,
        "expression_type": expression_type,
        **resolution,
    }
    row["eligible_for_connectivity"] = row["status"] == "resolved" and expression_type == "single_identity"
    return row


def unavailable_resolution(reason: str) -> dict:
    return {
        "raw_exact_status": "not_applicable",
        "raw_exact_target_ids": [],
        "normalized_keys": [],
        "resolution_method": None,
        "status": "authority_unavailable",
        "target_ids": [],
        "authority_unavailable_reason": reason,
    }


def nonresolving_expression(status: str) -> dict:
    return {
        "raw_exact_status": "not_attempted",
        "raw_exact_target_ids": [],
        "normalized_keys": [],
        "resolution_method": None,
        "status": status,
        "target_ids": [],
    }


def extract_mentions(
    canonical: list[dict], raw_indexes: dict[str, dict], ruler: Resolver, site: Resolver, pm: Resolver,
) -> list[dict]:
    mentions: list[dict] = []
    for artifact in sorted(canonical, key=lambda r: r["id"]):
        museum = artifact["source_museum"]
        raw = raw_indexes[museum][artifact["source_id"]]
        sequence = 0

        # Explicit structured ruler field (Met only). Every non-empty value is retained,
        # including deterministic abstentions for uncertainty/ranges.
        if museum == "met" and isinstance(raw.get("reign"), str) and raw["reign"].strip():
            field_value = raw["reign"]
            expr, candidate, span = classify_reign_expression(field_value)
            if expr == "single_identity" and candidate and span:
                resolution = ruler.resolve(candidate, ruler_norm)
                text, start, end = candidate, span[0], span[1]
            else:
                resolution = nonresolving_expression(expr)
                text, start, end = field_value.strip(), field_value.find(field_value.strip()), field_value.find(field_value.strip()) + len(field_value.strip())
            mentions.append(make_mention(
                artifact=artifact, entity_type="ruler", field_path="reign", field_value=field_value,
                text=text, start=start, end=end, extraction_method="typed_structured_reign_parser",
                evidence_role="catalogued_reign", expression_type=expr, resolution=resolution, sequence=sequence,
            ))
            sequence += 1

        # Explicit royal cues in textual fields. Met title is included only as an
        # independent raw cue (its structured reign field remains preferred downstream).
        ruler_text_fields = {
            "met": ("title",),
            "brooklyn": ("title", "inscribed", "dates", "objectDate", "provenance"),
            "harvard": ("title", "description", "labeltext", "commentary", "dated", "contextualtext"),
        }[museum]
        seen_spans = set()
        for field in ruler_text_fields:
            value = raw.get(field)
            if not isinstance(value, str) or not value.strip():
                continue
            for cue in ROYAL_CUE.finditer(value):
                # possessive/common-noun constructions are not identity cues
                after = value[cue.end():cue.end() + 2]
                if after.startswith(("'", "\u2019")):
                    continue
                candidate, start, end, extraction = candidate_after_cue(value, cue, ruler)
                if not candidate or (field, start, end) in seen_spans:
                    continue
                seen_spans.add((field, start, end))
                context = value[max(0, cue.start() - 15):min(len(value), end + 20)]
                expr = "uncertain_identity" if UNCERTAIN.search(context) else "multi_or_range" if RANGE_OR_MULTI.search(candidate) else "single_identity"
                resolution = ruler.resolve(candidate, ruler_norm) if expr == "single_identity" else nonresolving_expression(expr)
                mentions.append(make_mention(
                    artifact=artifact, entity_type="ruler", field_path=field, field_value=value,
                    text=candidate, start=start, end=end, extraction_method=extraction,
                    evidence_role="explicit_royal_text_cue", expression_type=expr,
                    resolution=resolution, sequence=sequence,
                ))
                sequence += 1

        # Structured site evidence. Locations are decomposed into catalogued hierarchy
        # components, preserving the precise raw field and span.
        site_values: list[tuple[str, str, str]] = []
        if museum == "met":
            role = raw.get("geographyType") or "unspecified"
            for field in ("country", "region", "subregion", "locale", "locus"):
                if isinstance(raw.get(field), str) and raw[field].strip():
                    site_values.append((field, raw[field], f"{role}:{field}"))
            if isinstance(raw.get("excavation"), str) and raw["excavation"].strip():
                value = raw["excavation"]
                mentions.append(make_mention(
                    artifact=artifact, entity_type="excavation", field_path="excavation", field_value=value,
                    text=value.strip(), start=value.find(value.strip()), end=value.find(value.strip()) + len(value.strip()),
                    extraction_method="explicit_structured_value", evidence_role="excavation_credit",
                    expression_type="single_identity",
                    resolution=unavailable_resolution("no committed canonical excavation authority"), sequence=sequence,
                ))
                sequence += 1
        elif museum == "brooklyn":
            for i, place in enumerate(raw.get("geographicalLocations") or []):
                if not isinstance(place, dict):
                    continue
                role = place.get("type") or "unspecified"
                # The catalogued name is the primary field; its comma components include
                # city/country with offsets. City/country leaves are audited as corroborating
                # structure but are not emitted again as duplicate mentions.
                value = place.get("name")
                if isinstance(value, str) and value.strip():
                    site_values.append((f"geographicalLocations[{i}].name", value, role))
                else:
                    for leaf in ("city", "country"):
                        value = place.get(leaf)
                        if isinstance(value, str) and value.strip():
                            site_values.append((f"geographicalLocations[{i}].{leaf}", value, role))
        else:
            for i, place in enumerate(raw.get("places") or []):
                if not isinstance(place, dict):
                    continue
                value = place.get("displayname")
                if isinstance(value, str) and value.strip():
                    site_values.append((f"places[{i}].displayname", value, place.get("type") or "unspecified"))

        for field_path, field_value, role in site_values:
            for component, start, end, _ in string_spans(field_value, field_path):
                variants = strip_parenthetical_container(component)
                for variant_index, (text, rel_start, rel_end) in enumerate(variants):
                    resolution = site.resolve(text, place_norm_set)
                    extraction_method = "structured_location_component" if variant_index == 0 else "structured_pre_parenthesis_component"
                    if variant_index > 0 and resolution["resolution_method"] == "raw_exact":
                        # Derived child text cannot honestly be reported as raw exact.
                        resolution["resolution_method"] = "deterministic_component_exact"
                    mentions.append(make_mention(
                        artifact=artifact, entity_type="site", field_path=field_path, field_value=field_value,
                        text=text, start=start + rel_start, end=start + rel_end,
                        extraction_method=extraction_method, evidence_role=role,
                        expression_type="single_identity", resolution=resolution, sequence=sequence,
                    ))
                    sequence += 1

                # Exact PM codes/registered monument aliases inside structured location
                # components. Codes get their own precise spans; free text is only tried as
                # a whole exact alias, never fuzzy matched.
                pm_hits = list(TOMB_CODE.finditer(component))
                if pm_hits:
                    for hit in pm_hits:
                        text = hit.group(0)
                        resolution = pm.resolve(text, place_norm_set)
                        mentions.append(make_mention(
                            artifact=artifact, entity_type="tomb_monument", field_path=field_path, field_value=field_value,
                            text=text, start=start + hit.start(), end=start + hit.end(),
                            extraction_method="explicit_tomb_code", evidence_role=role,
                            expression_type="single_identity", resolution=resolution, sequence=sequence,
                        ))
                        sequence += 1
                else:
                    pm_result = pm.resolve(component, place_norm_set)
                    if pm_result["status"] != "unmatched":
                        mentions.append(make_mention(
                            artifact=artifact, entity_type="tomb_monument", field_path=field_path, field_value=field_value,
                            text=component, start=start, end=end,
                            extraction_method="exact_registered_monument_alias", evidence_role=role,
                            expression_type="single_identity", resolution=pm_result, sequence=sequence,
                        ))
                        sequence += 1
    mentions.sort(key=lambda r: r["mention_id"])
    if len({m["mention_id"] for m in mentions}) != len(mentions):
        raise RuntimeError("non-unique mention ids")
    return mentions


def metrics_and_links(canonical: list[dict], mentions: list[dict], catalogs: dict[str, dict]) -> tuple[dict, list[dict], dict, list[dict]]:
    record_counts = collections.Counter(row["source_museum"] for row in canonical)
    museums = ("met", "brooklyn", "harvard")
    entity_types = ("ruler", "site", "tomb_monument", "excavation")
    cell_metrics = {}
    for museum in museums:
        for entity in entity_types:
            rows = [m for m in mentions if m["museum"] == museum and m["entity_type"] == entity]
            evidence_artifacts = {m["artifact_id"] for m in rows}
            status_counts = collections.Counter(m["status"] for m in rows)
            artifact_status = collections.defaultdict(set)
            for m in rows:
                artifact_status[m["artifact_id"]].add(m["status"])
            resolved_mentions = status_counts["resolved"]
            attempted = sum(status_counts[s] for s in ("resolved", "ambiguous", "unmatched"))
            cell_metrics[f"{museum}|{entity}"] = {
                "museum": museum,
                "entity_type": entity,
                "records_denominator": record_counts[museum],
                "records_with_extracted_evidence": len(evidence_artifacts),
                "record_evidence_rate": len(evidence_artifacts) / record_counts[museum] if record_counts[museum] else None,
                "mentions": len(rows),
                "mention_status_counts": dict(sorted(status_counts.items())),
                "mentions_with_resolution_attempt_denominator": attempted,
                "unique_resolved_mentions": resolved_mentions,
                "mention_resolution_rate_among_attempted": resolved_mentions / attempted if attempted else None,
                "artifacts_with_at_least_one_unique_resolution": sum("resolved" in states for states in artifact_status.values()),
                "artifacts_with_ambiguous_mentions": sum("ambiguous" in states for states in artifact_status.values()),
                "artifacts_with_unmatched_mentions": sum("unmatched" in states for states in artifact_status.values()),
            }

    # Artifact-node links are deduplicated across mentions. This is the only input to
    # connectivity, preventing duplicate field evidence from inflating artifact counts.
    grouped: dict[tuple[str, str, str, str], list[str]] = collections.defaultdict(list)
    for mention in mentions:
        if not mention["eligible_for_connectivity"] or len(mention["target_ids"]) != 1:
            continue
        target_id = mention["target_ids"][0]
        grouped[(mention["artifact_id"], mention["museum"], mention["entity_type"], target_id)].append(mention["mention_id"])
    links = [
        {"artifact_id": key[0], "museum": key[1], "entity_type": key[2], "target_id": key[3], "mention_ids": sorted(ids)}
        for key, ids in sorted(grouped.items())
    ]

    node_groups: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for link in links:
        node_groups[(link["entity_type"], link["target_id"])].append(link)
    node_rows = []
    for (entity, target_id), node_links in sorted(node_groups.items()):
        counts = collections.Counter(link["museum"] for link in node_links)
        cat = catalogs[entity].get(target_id, {})
        node_rows.append({
            "entity_type": entity,
            "target_id": target_id,
            "target_label": cat.get("label"),
            "representation": cat.get("representation"),
            "museum_count": len(counts),
            "artifact_count": len(node_links),
            "artifact_counts_by_museum": dict(sorted(counts.items())),
            "shared_across_museums": len(counts) >= 2,
        })
    shared = [row for row in node_rows if row["shared_across_museums"]]
    shared_keys = {(row["entity_type"], row["target_id"]) for row in shared}
    discoverable_artifacts = {(l["artifact_id"], l["museum"]) for l in links if (l["entity_type"], l["target_id"]) in shared_keys}
    connectivity = {
        "model": "shared authority-node incidence; no artifact all-pairs materialized",
        "artifact_node_links": len(links),
        "linked_artifacts": len({l["artifact_id"] for l in links}),
        "linked_nodes": len(node_rows),
        "nodes_linked_from_at_least_two_museums": len(shared),
        "shared_nodes_by_entity_type": dict(collections.Counter(r["entity_type"] for r in shared)),
        "artifacts_on_shared_nodes_newly_cross_museum_discoverable": len(discoverable_artifacts),
        "discoverable_artifacts_by_museum": dict(collections.Counter(m for _, m in discoverable_artifacts)),
        "discoverable_artifacts_by_entity_type": {
            entity: len({l["artifact_id"] for l in links if l["entity_type"] == entity and (entity, l["target_id"]) in shared_keys})
            for entity in ("ruler", "site", "tomb_monument")
        },
        "note": "An artifact is counted once overall if any of its resolved nodes also has artifacts from another museum; per-entity counts can overlap.",
    }

    # Weighted unresolved signatures. Count distinct artifacts, not duplicate mentions.
    signatures: dict[tuple, set[str]] = collections.defaultdict(set)
    signature_rows = {}
    for m in mentions:
        if m["status"] == "resolved":
            continue
        key = (m["museum"], m["entity_type"], surface_key(m["mention_text"]), m["status"], m["expression_type"])
        signatures[key].add(m["artifact_id"])
        signature_rows.setdefault(key, m)
    gaps = []
    for key, artifacts in signatures.items():
        sample = signature_rows[key]
        gaps.append({
            "museum": key[0], "entity_type": key[1], "normalized_mention": key[2],
            "example_mention": sample["mention_text"], "status": key[3], "expression_type": key[4],
            "artifact_frequency": len(artifacts), "example_artifact_id": sample["artifact_id"],
            "example_source_url": sample["source_url"], "example_field_path": sample["field_path"],
        })
    gaps.sort(key=lambda r: (-r["artifact_frequency"], r["museum"], r["entity_type"], r["normalized_mention"]))

    # Minimal exact-vs-current-normalization ablation over resolution-attempt mentions.
    ablation = {}
    for entity in ("ruler", "site", "tomb_monument"):
        rows = [m for m in mentions if m["entity_type"] == entity and m["status"] in {"resolved", "ambiguous", "unmatched"}]
        raw_unique = sum(m["raw_exact_status"] == "unique" for m in rows)
        current_unique = sum(m["status"] == "resolved" for m in rows)
        raw_artifacts = {m["artifact_id"] for m in rows if m["raw_exact_status"] == "unique"}
        current_artifacts = {m["artifact_id"] for m in rows if m["status"] == "resolved"}
        ablation[entity] = {
            "attempted_mentions_denominator": len(rows),
            "raw_exact_unique_mentions": raw_unique,
            "current_exact_plus_committed_normalization_unique_mentions": current_unique,
            "incremental_unique_mentions": current_unique - raw_unique,
            "raw_exact_artifacts_with_unique_match": len(raw_artifacts),
            "current_artifacts_with_unique_match": len(current_artifacts),
            "incremental_artifacts": len(current_artifacts - raw_artifacts),
        }

    metrics = {
        "scope": {"canonical_records": len(canonical), "records_by_museum": dict(sorted(record_counts.items()))},
        "cells": cell_metrics,
        "ablation": ablation,
    }
    return metrics, links, connectivity, node_rows, gaps


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    canonical = load_ndjson_gz(CORPUS / "data" / "artifacts.ndjson.gz")
    raw_indexes = {}
    for museum in ("met", "brooklyn", "harvard"):
        wrappers = load_ndjson_gz(CORPUS / "data" / f"raw_{museum}.ndjson.gz")
        raw_indexes[museum] = {row["object_id"]: row["data"] for row in wrappers}
    for artifact in canonical:
        if artifact["source_id"] not in raw_indexes[artifact["source_museum"]]:
            raise RuntimeError(f"missing linked raw {artifact['id']}")

    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    ruler_resolver, ruler_catalog = build_ruler_resolver(graph)
    site_resolver, site_catalog = build_site_resolver(load_jsonl(IDAI))
    pm_resolver, pm_catalog = build_pm_resolver()
    catalogs = {"ruler": ruler_catalog, "site": site_catalog, "tomb_monument": pm_catalog}

    mentions = extract_mentions(canonical, raw_indexes, ruler_resolver, site_resolver, pm_resolver)
    metrics, links, connectivity, node_rows, gaps = metrics_and_links(canonical, mentions, catalogs)

    write_jsonl_gz(OUT / "mentions.ndjson.gz", mentions)
    write_jsonl_gz(OUT / "artifact_authority_links.ndjson.gz", links)
    write_json(OUT / "linkability_metrics.json", metrics)
    write_json(OUT / "connectivity_metrics.json", connectivity)
    write_json(OUT / "authority_node_connectivity.json", node_rows)
    write_json(OUT / "top_gaps.json", gaps[:500])
    write_json(OUT / "adapter_catalog_summary.json", {
        "ruler_targets": len(ruler_catalog), "site_targets": len(site_catalog),
        "tomb_monument_targets": len(pm_catalog),
        "ruler_exact_keys": len(ruler_resolver.exact), "ruler_normalized_keys": len(ruler_resolver.normalized),
        "site_exact_keys": len(site_resolver.exact), "site_normalized_keys": len(site_resolver.normalized),
        "pm_exact_keys": len(pm_resolver.exact), "pm_normalized_keys": len(pm_resolver.normalized),
        "target_label_collision_counts": {
            "ruler_exact": sum(len(v) > 1 for v in ruler_resolver.exact.values()),
            "ruler_normalized": sum(len(v) > 1 for v in ruler_resolver.normalized.values()),
            "site_exact": sum(len(v) > 1 for v in site_resolver.exact.values()),
            "site_normalized": sum(len(v) > 1 for v in site_resolver.normalized.values()),
            "tomb_exact": sum(len(v) > 1 for v in pm_resolver.exact.values()),
            "tomb_normalized": sum(len(v) > 1 for v in pm_resolver.normalized.values()),
        },
    })
    print(json.dumps({
        "mentions": len(mentions), "links": len(links),
        "linked_artifacts": connectivity["linked_artifacts"],
        "shared_nodes": connectivity["nodes_linked_from_at_least_two_museums"],
        "discoverable_artifacts": connectivity["artifacts_on_shared_nodes_newly_cross_museum_discoverable"],
    }, indent=2))


if __name__ == "__main__":
    main()
