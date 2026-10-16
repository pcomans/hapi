"""Museum mentions resolved to authority targets, and the links they make (#338).

The production form of what the #337 and #361 evaluations measured. Every mention gets one
resolution row; a row that is not resolved says why. Two modes, the matcher's switch:

* `authority`: sites among the reconciled iDAI rows (`resolver.build_site_resolver`), rulers
  among the claim graph's identity clusters and, after a royal-woman cue, among Dodson &
  Hilton's royal women (`royal_women.resolve_ruler_mention`, the record's other kings and its
  single dynasty as context, the TLA-linked spellings in the index). These are the entity
  types the evaluations found to beat plain text: sites in all three museum pairs (#337 v10),
  rulers for Met–Brooklyn (#361).
* `literal`: the plain-text baseline both evaluations compared against; a mention's target is
  its NFC, whitespace-collapsed, casefolded text, typed by entity.

Nothing is forced. A mention that is not a single identity, of an entity type without a
qualifying authority, ambiguous or unmatched gets no target, and its row keeps the
alternatives or the reason. A link joins a record to a target only on a resolved mention, and
says only identity: the resolvers resolve a name to the entity it names, never to a broader,
narrower or overlapping one.

Every resolution and link carries `resolver_version`, the SHA-256 of the code and authority
files it was made from (`authority_snapshot`), so a link traces to its mention, the rule and
the data that made it, and a change to any of them changes the version.
"""

from __future__ import annotations

import collections
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pipeline.authority import graph_kings, resolver, royal_women, tla_links

ENRICH = Path(__file__).resolve().parent
AUTHORITY = ENRICH.parent / "authority"
REPO = ENRICH.parents[2]
SUPPORTED = ("ruler", "site")
# Entity types the extractor finds that this step does not resolve, and why.
UNSUPPORTED = {
    "tomb_monument": "an authority exists (Porter & Moss) but did not beat plain text in #337",
    "temple": "no committed canonical temple authority",
    "excavation": "no committed canonical excavation authority",
}
MODES = ("authority", "literal")
LITERAL_METHOD = "typed_nfc_whitespace_casefold_literal_equality"
# The code and data a resolution depends on, hashed into `resolver_version`.
SNAPSHOT_FILES = (
    ENRICH / "mentions.py",
    ENRICH / "authority_links.py",
    AUTHORITY / "resolver.py",
    AUTHORITY / "graph_kings.py",
    AUTHORITY / "royal_women.py",
    AUTHORITY / "tla_links.py",
    AUTHORITY / "weak_sign_skeleton.py",
    AUTHORITY / "claimgraph" / "normalize.py",
    resolver.GRAPH,
    resolver.IDAI,
    royal_women.DODSON_HILTON,
    royal_women.SAME_WOMAN,
    royal_women.FEMALE_RULERS,
    tla_links.TLA,
    tla_links.LINKS_DIR / "decisions.jsonl",
)


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def authority_snapshot() -> dict:
    """The files a resolution depends on, by repository path, with their SHA-256, and the
    version they make together."""
    files = {str(path.relative_to(REPO)): sha256_path(path) for path in SNAPSHOT_FILES}
    version = hashlib.sha256(json.dumps(files, sort_keys=True).encode("utf-8")).hexdigest()
    return {"files": files, "resolver_version": version}


@dataclass(frozen=True)
class Authority:
    sites: resolver.Resolver
    kings: graph_kings.GraphKings
    women: royal_women.RoyalWomenIndex
    snapshot: dict


def load_authority() -> Authority:
    kings = graph_kings.GraphKings()
    sites, _ = resolver.build_site_resolver(resolver.load_jsonl(resolver.IDAI))
    women = royal_women.build_index(royal_women.load_royal_women(), kings,
                                    linked_spellings=tla_links.linked_spellings())
    return Authority(sites=sites, kings=kings, women=women, snapshot=authority_snapshot())


def literal_target(entity_type: str, text: str) -> str:
    key = f"{entity_type}\x1f{resolver.surface_key(text)}"
    return "literal:" + hashlib.sha256(key.encode("utf-8")).hexdigest()


def resolve_mentions(mentions: list[dict], mode: str, authority: Authority | None) -> list[dict]:
    """One resolution row per mention, in the mentions' order."""
    if mode not in MODES:
        raise ValueError(f"unknown mode: {mode}")
    if mode == "authority" and authority is None:
        raise ValueError("the authority mode needs the authority")
    version = authority.snapshot["resolver_version"] if authority else None
    # A record's own kings: the kings its uncued single-identity ruler mentions resolve to.
    record_kings: dict[str, set[str]] = collections.defaultdict(set)
    if mode == "authority":
        for m in mentions:
            if (m["entity_type"] == "ruler" and m["expression_type"] == "single_identity"
                    and not royal_women.royal_woman_cued(m["field_value"], m["span_start"])):
                found = authority.kings.resolve(m["mention_text"])
                if found["status"] == "resolved":
                    record_kings[m["artifact_id"]].update(found["target_ids"])
    rows = []
    for m in mentions:
        row = {
            "mention_id": m["mention_id"], "artifact_id": m["artifact_id"], "museum": m["museum"],
            "entity_type": m["entity_type"], "field_path": m["field_path"], "evidence_role": m["evidence_role"],
            "mention_text": m["mention_text"], "mode": mode, "resolver_version": version,
            "authority": None, "resolution_method": None, "target_ids": [], "candidate_ids": [],
            "context_rule": None, "stated_kin_king_ids": [],
        }
        if m["expression_type"] != "single_identity":
            rows.append({**row, "status": "abstained", "reason": f"expression:{m['expression_type']}"})
        elif m["entity_type"] in UNSUPPORTED:
            rows.append({**row, "status": "abstained", "reason": f"unsupported:{m['entity_type']}"})
        elif m["entity_type"] not in SUPPORTED:
            raise ValueError(f"unclassified entity type: {m['entity_type']}")
        elif mode == "literal":
            rows.append({**row, "status": "resolved", "reason": None, "resolution_method": LITERAL_METHOD,
                         "target_ids": [literal_target(m["entity_type"], m["mention_text"])]})
        else:
            rows.append({**row, **_resolve_one(authority, m, record_kings[m["artifact_id"]])})
    return rows


def _resolve_one(authority: Authority, m: dict, record_kings: set[str]) -> dict:
    if m["entity_type"] == "site":
        found = {**authority.sites.resolve(m["mention_text"], resolver.place_norm_set),
                 "authority": "idai", "context_rule": None}
    else:
        found = royal_women.resolve_ruler_mention(
            authority.women, authority.kings, m["field_value"], m["span_start"], m["span_end"],
            record_king_ids=record_kings, record_dynasty=royal_women.single_dynasty(m["record_dynasty"]))
    status = found["status"]
    return {
        "status": status,
        "reason": None if status == "resolved" else (found["context_rule"] or f"authority_{status}"),
        "authority": found["authority"],
        "resolution_method": found["resolution_method"],
        "target_ids": found["target_ids"] if status == "resolved" else [],
        # Not resolved: the targets still in play when ambiguous (the royal women's are those
        # the record's family and dynasty leave), else every target the name met (a royal
        # woman's weak-sign match the record did not confirm, say).
        "candidate_ids": [] if status == "resolved" else
        found["target_ids"] if status == "ambiguous" else found.get("candidate_ids", []),
        "context_rule": found["context_rule"],
        "stated_kin_king_ids": found.get("stated_kin_king_ids", []),
    }


def build_links(resolutions: list[dict]) -> list[dict]:
    """One link per record, entity type and target, on its resolved mentions."""
    grouped: dict[tuple[str, str, str, str], list[dict]] = collections.defaultdict(list)
    for row in resolutions:
        if row["status"] == "resolved":
            (target,) = row["target_ids"]
            grouped[(row["artifact_id"], row["museum"], row["entity_type"], target)].append(row)
    links = []
    for (artifact_id, museum, entity_type, target), rows in sorted(grouped.items()):
        (mode,) = {r["mode"] for r in rows}
        (version,) = {r["resolver_version"] for r in rows}
        links.append({
            "artifact_id": artifact_id, "museum": museum, "entity_type": entity_type, "target_id": target,
            "relation": "identity", "mode": mode, "resolver_version": version,
            "mention_ids": sorted(r["mention_id"] for r in rows),
            "evidence_roles": sorted({r["evidence_role"] for r in rows}),
        })
    return links
