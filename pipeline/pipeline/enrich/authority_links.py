"""Museum mentions resolved to authority targets, and the links they make (#338).

The production form of what the #337 and #361 evaluations measured. Every mention gets one
resolution row; a row that is not resolved says why. Two modes, the matcher's switch:

* `authority`: sites among the reconciled iDAI rows, tombs among Porter & Moss's tomb rows
  (`resolver`), rulers among the claim graph's identity clusters and, after a royal-woman cue,
  among Dodson & Hilton's royal women (`royal_women.resolve_ruler_mention`: the record's other
  kings and its single dynasty as context, the TLA-linked spellings in the index).
* `literal`: the plain-text baseline both evaluations compared against; a mention's target is
  its NFC, whitespace-collapsed, casefolded text, typed by entity.

Every entity type with an authority is resolved; temples and excavations have none and
abstain. Which (entity type, museum pair) scopes the evaluations found the authority to beat
plain text in is `QUALIFIED_SCOPES`; a consumer reports the others as unevaluated, never as
proven.

Nothing is forced. A mention that is not a single identity, ambiguous or unmatched gets no
target. A row keeps the resolver's own answer whole (`resolution`: its candidates, the keys it
tried, the context rule that chose or refused), so the alternatives and the evidence for a
decision stay with it. A link joins a record to a target only on a resolved mention, and says
only identity: the resolvers resolve a name to the entity it names, never to a broader,
narrower or overlapping one.

Every row and link carries `resolver_version`: the SHA-256 over the code and data files its
mode reads and the Unicode version Python's normalization uses (`snapshot`). A change to any
of them changes the version.
"""

from __future__ import annotations

import collections
import hashlib
import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from pipeline.authority import graph_kings, resolver, royal_women, tla_links

ENRICH = Path(__file__).resolve().parent
AUTHORITY = ENRICH.parent / "authority"
REPO = ENRICH.parents[2]
MODES = ("authority", "literal")
RESOLVED_TYPES = ("ruler", "site", "tomb_monument")
# Entity types the extractor finds that have no authority, and why.
UNSUPPORTED = {
    "temple": "no committed canonical temple authority",
    "excavation": "no committed canonical excavation authority",
}
MUSEUM_PAIRS = (("met", "brooklyn"), ("met", "harvard"), ("brooklyn", "harvard"),
                ("met", "cleveland"), ("brooklyn", "cleveland"), ("harvard", "cleveland"),
                ("met", "walters"), ("brooklyn", "walters"), ("harvard", "walters"), ("cleveland", "walters"))
# Where the authority beat plain text under review (`docs/evaluations/`):
# * site, all three pairs: #337 v10 (`authority-independent-control-2026-10-11/README.md`);
# * ruler, Met–Brooklyn: #361 (`ruler-reregistration-2026-10-15/README.md`). The Harvard pairs
#   had no changed ruler case to review, so they are unevaluated, not failed.
# Tombs are unevaluated: in #337 no tomb mention reached a node shared across museums in
# either arm, so no tomb case was reviewed.
# Every Cleveland and Walters pair is unevaluated: both museums were added after both reviews
# (docs/museum-sources/cleveland.md, walters.md).
QUALIFIED_SCOPES = {
    "site": frozenset({("met", "brooklyn"), ("met", "harvard"), ("brooklyn", "harvard")}),
    "ruler": frozenset({("met", "brooklyn")}),
    "tomb_monument": frozenset(),
}
LITERAL_METHOD = "typed_nfc_whitespace_casefold_literal_equality"
LITERAL_FILES = (ENRICH / "mentions.py", ENRICH / "authority_links.py", AUTHORITY / "resolver.py")
# The code and data a resolution in the authority mode reads, hashed into its version.
AUTHORITY_FILES = LITERAL_FILES + (
    AUTHORITY / "graph_kings.py",
    AUTHORITY / "royal_women.py",
    AUTHORITY / "tla_links.py",
    AUTHORITY / "weak_sign_skeleton.py",
    AUTHORITY / "claimgraph" / "__init__.py",
    AUTHORITY / "claimgraph" / "normalize.py",
    AUTHORITY / "__init__.py",
    ENRICH / "__init__.py",
    resolver.GRAPH,
    resolver.IDAI,
    resolver.PM_THEBAN,
    resolver.PM_MEMPHIS,
    royal_women.DODSON_HILTON,
    royal_women.SAME_WOMAN,
    royal_women.FEMALE_RULERS,
    tla_links.TLA,
    tla_links.LINKS_DIR / "decisions.jsonl",
)


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(mode: str) -> dict:
    """The files a resolution in `mode` reads, by repository path, with their SHA-256; the
    Unicode version; and the version they make together."""
    if mode not in MODES:
        raise ValueError(f"unknown mode: {mode}")
    files = {str(p.relative_to(REPO)): sha256_path(p) for p in (AUTHORITY_FILES if mode == "authority" else LITERAL_FILES)}
    body = {"mode": mode, "files": files, "unicode": unicodedata.unidata_version}
    return {**body, "resolver_version": hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()}


@dataclass(frozen=True)
class Authority:
    sites: resolver.Resolver
    tombs: resolver.Resolver
    kings: graph_kings.GraphKings
    women: royal_women.RoyalWomenIndex
    snapshot: dict


def load_authority() -> Authority:
    kings = graph_kings.GraphKings()
    sites, _ = resolver.build_site_resolver(resolver.load_jsonl(resolver.IDAI))
    tombs, _ = resolver.build_pm_resolver()
    women = royal_women.build_index(royal_women.load_royal_women(), kings,
                                    linked_spellings=tla_links.linked_spellings())
    return Authority(sites=sites, tombs=tombs, kings=kings, women=women, snapshot=snapshot("authority"))


def literal_target(entity_type: str, text: str) -> str:
    key = f"{entity_type}\x1f{resolver.surface_key(text)}"
    return "literal:" + hashlib.sha256(key.encode("utf-8")).hexdigest()


def resolve_mentions(mentions: list[dict], mode: str, authority: Authority | None) -> list[dict]:
    """One resolution row per mention, in the mentions' order."""
    if mode not in MODES:
        raise ValueError(f"unknown mode: {mode}")
    if mode == "authority" and authority is None:
        raise ValueError("the authority mode needs the authority")
    version = (authority.snapshot if mode == "authority" else snapshot("literal"))["resolver_version"]
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
            "authority": None, "target_ids": [], "resolution": None,
        }
        if m["expression_type"] != "single_identity":
            rows.append({**row, "status": "abstained", "reason": f"expression:{m['expression_type']}"})
        elif m["entity_type"] in UNSUPPORTED:
            rows.append({**row, "status": "abstained", "reason": f"unsupported:{m['entity_type']}"})
        elif m["entity_type"] not in RESOLVED_TYPES:
            raise ValueError(f"unclassified entity type: {m['entity_type']}")
        elif mode == "literal":
            rows.append({**row, "status": "resolved", "reason": None, "authority": "literal",
                         "target_ids": [literal_target(m["entity_type"], m["mention_text"])]})
        else:
            rows.append({**row, **_resolve_one(authority, m, record_kings[m["artifact_id"]])})
    return rows


def _resolve_one(authority: Authority, m: dict, record_kings: set[str]) -> dict:
    if m["entity_type"] == "site":
        found = {**authority.sites.resolve(m["mention_text"], resolver.place_norm_set), "authority": "idai"}
    elif m["entity_type"] == "tomb_monument":
        found = {**authority.tombs.resolve(m["mention_text"], resolver.place_norm_set), "authority": "porter_moss"}
    else:
        found = royal_women.resolve_ruler_mention(
            authority.women, authority.kings, m["field_value"], m["span_start"], m["span_end"],
            record_king_ids=record_kings, record_dynasty=royal_women.single_dynasty(m["record_dynasty"]))
    status = found["status"]
    return {
        "status": status,
        "reason": None if status == "resolved" else (found.get("context_rule") or f"authority_{status}"),
        "authority": found["authority"],
        "target_ids": found["target_ids"] if status == "resolved" else [],
        "resolution": found,
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
