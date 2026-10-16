"""The authority links of a corpus, written as versioned files (#338 step 2).

One run reads the canonical records and their raw payloads, extracts the mentions, resolves
them in both modes (`authority_links.MODES`) and writes, under `<root>/<run_id>/`:

* `mentions.ndjson.gz`;
* `resolutions-<mode>.ndjson.gz` and `links-<mode>.ndjson.gz` for each mode;
* `manifest.json`: the inputs' digest, each mode's snapshot, every file's SHA-256 and row
  count, the resolution outcomes by entity type, status and reason, and the inventory of what is
  not resolved (`unsupported`: the entity types with no authority, with their reason and
  count; `unevaluated_scopes`: the resolved types' museum pairs no evaluation qualified);
The run id is the SHA-256 over the inputs' digest, both modes' resolver versions and this
module's own SHA-256 (it types the rows and writes the files), so the
same inputs and code give the same id and the same bytes (rows sorted, gzip without a
timestamp). A run whose directory exists is checked byte for byte, never overwritten.

`<root>/CURRENT` names the run in force. When a run replaces another there, it writes
`<root>/diffs/<previous>-to-<run>.json`: for each mode, every link added, and every link removed
with why.

A link is removed when its source decision is withdrawn: re-running on the new inputs or
authority makes no such link, and the diff says whether the record is gone, its mentions are
gone, or a mention that made it now resolves otherwise (with its new status and reason). Files
are the store for now (owner, 2026-10-16); a database table comes later.
"""

from __future__ import annotations

import collections
import gzip
import hashlib
import io
import json
from pathlib import Path

from pipeline.authority import royal_women
from pipeline.enrich import authority_links, mentions

CURRENT = "CURRENT"
# What a target is, by the authority that resolved it. A royal woman who reigned resolves to
# her king's cluster, which is a king.
TARGET_KINDS = {"kings": "king", "royal_women": "royal_woman", "idai": "site", "porter_moss": "tomb",
                "literal": "literal"}


def canonical_line(row: dict) -> bytes:
    return (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def gzip_rows(rows: list[dict]) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", fileobj=buffer, mode="wb", compresslevel=9, mtime=0) as handle:
        for row in rows:
            handle.write(canonical_line(row))
    return buffer.getvalue()


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in gzip.decompress(path.read_bytes()).splitlines()]


def input_digest(canonical: list[dict], raw_indexes: dict[str, dict[str, dict]]) -> str:
    """The SHA-256 over the canonical records and raw payloads, in a fixed order."""
    digest = hashlib.sha256()
    for row in sorted(canonical, key=lambda r: r["id"]):
        digest.update(canonical_line(row))
    for museum in sorted(raw_indexes):
        for source_id in sorted(raw_indexes[museum]):
            digest.update(canonical_line({"museum": museum, "source_id": source_id, "data": raw_indexes[museum][source_id]}))
    return digest.hexdigest()


def target_kind(row: dict) -> str | None:
    if row["status"] != "resolved":
        return None
    if row["authority"] == "royal_women" and not row["target_ids"][0].startswith(royal_women.TARGET_PREFIX):
        return "king"
    return TARGET_KINDS[row["authority"]]


def typed(resolutions: list[dict]) -> list[dict]:
    return [{**row, "target_kind": target_kind(row)} for row in resolutions]


def typed_links(links: list[dict], resolutions: list[dict]) -> list[dict]:
    kind = {row["mention_id"]: row["target_kind"] for row in resolutions}
    out = []
    for link in links:
        (k,) = {kind[m] for m in link["mention_ids"]}
        out.append({**link, "target_kind": k})
    return out


def outcomes(resolutions: list[dict]) -> dict:
    counts = collections.Counter((r["entity_type"], r["status"], r["reason"] or "") for r in resolutions)
    return {f"{t}|{s}|{reason}": n for (t, s, reason), n in sorted(counts.items())}


def inventory(resolutions: list[dict]) -> dict:
    unsupported = collections.Counter(r["entity_type"] for r in resolutions if (r["reason"] or "").startswith("unsupported:"))
    return {
        "unsupported": {t: {"reason": authority_links.UNSUPPORTED[t], "mentions": unsupported[t]}
                        for t in sorted(authority_links.UNSUPPORTED)},
        "unevaluated_scopes": {t: [list(pair) for pair in authority_links.MUSEUM_PAIRS
                                   if pair not in authority_links.QUALIFIED_SCOPES[t]]
                               for t in authority_links.RESOLVED_TYPES},
    }


def diff_links(previous: list[dict], links: list[dict], resolutions: list[dict], artifact_ids: set[str]) -> dict:
    """The links added and removed against a previous run, each removal with why."""
    def key(link: dict) -> tuple:
        return link["artifact_id"], link["entity_type"], link["target_id"]
    old, new = {key(l): l for l in previous}, {key(l): l for l in links}
    by_mention = {r["mention_id"]: r for r in resolutions}
    removed = []
    for k in sorted(set(old) - set(new)):
        link = old[k]
        if link["artifact_id"] not in artifact_ids:
            why = {"why": "record_gone"}
        else:
            present = [by_mention[m] for m in link["mention_ids"] if m in by_mention]
            if not present:
                why = {"why": "mentions_gone"}
            else:
                why = {"why": "resolves_otherwise",
                       "now": [{"mention_id": r["mention_id"], "status": r["status"], "reason": r["reason"],
                                "target_ids": r["target_ids"]} for r in present]}
        removed.append({**{f: link[f] for f in ("artifact_id", "museum", "entity_type", "target_id", "mention_ids")}, **why})
    added = [{f: new[k][f] for f in ("artifact_id", "museum", "entity_type", "target_id", "mention_ids")}
             for k in sorted(set(new) - set(old))]
    return {"added": added, "removed": removed, "kept": len(set(old) & set(new))}


def write_run(canonical: list[dict], raw_indexes: dict[str, dict[str, dict]], root: Path,
              authority: authority_links.Authority | None = None) -> dict:
    """Write one run under `root` and point `root/CURRENT` at it; return its manifest."""
    authority = authority or authority_links.load_authority()
    found, extraction = mentions.extract_mentions(canonical, raw_indexes)
    snapshots = {"authority": authority.snapshot, "literal": authority_links.snapshot("literal")}
    inputs = input_digest(canonical, raw_indexes)
    writer = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    run_id = hashlib.sha256(json.dumps({"inputs": inputs, "writer": writer,
                                        "versions": {m: s["resolver_version"] for m, s in snapshots.items()}},
                                       sort_keys=True).encode("utf-8")).hexdigest()
    files: dict[str, bytes] = {"mentions.ndjson.gz": gzip_rows(found)}
    counts: dict[str, int] = {"mentions.ndjson.gz": len(found)}
    by_mode = {}
    for mode in authority_links.MODES:
        resolutions = typed(authority_links.resolve_mentions(found, mode, authority if mode == "authority" else None))
        links = typed_links(authority_links.build_links(resolutions), resolutions)
        by_mode[mode] = (resolutions, links)
        files[f"resolutions-{mode}.ndjson.gz"] = gzip_rows(resolutions)
        files[f"links-{mode}.ndjson.gz"] = gzip_rows(links)
        counts[f"resolutions-{mode}.ndjson.gz"], counts[f"links-{mode}.ndjson.gz"] = len(resolutions), len(links)

    manifest = {
        "schema_version": "hapi-authority-links/1",
        "run_id": run_id,
        "inputs_sha256": inputs,
        # This module types the rows and writes the files; its SHA-256 is in the run id too.
        "writer_sha256": writer,
        "records": len(canonical),
        "snapshots": snapshots,
        "extraction": extraction,
        "files": {name: {"sha256": hashlib.sha256(data).hexdigest(), "rows": counts.get(name)}
                  for name, data in sorted(files.items())},
        "outcomes": {mode: outcomes(by_mode[mode][0]) for mode in authority_links.MODES},
        "inventory": inventory(by_mode["authority"][0]),
    }
    files["manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")

    run_dir = root / run_id
    if run_dir.exists():
        for name, data in files.items():
            if (run_dir / name).read_bytes() != data:
                raise ValueError(f"{run_dir / name} differs from a re-run on the same inputs and code")
    else:
        run_dir.mkdir(parents=True)
        for name, data in files.items():
            (run_dir / name).write_bytes(data)

    previous_id = (root / CURRENT).read_text(encoding="utf-8").strip() if (root / CURRENT).exists() else None
    if previous_id is not None and previous_id != run_id:
        artifact_ids = {row["id"] for row in canonical}
        diff = {"previous_run": previous_id, "run": run_id}
        for mode in authority_links.MODES:
            diff[mode] = diff_links(read_rows(root / previous_id / f"links-{mode}.ndjson.gz"), by_mode[mode][1],
                                    by_mode[mode][0], artifact_ids)
        (root / "diffs").mkdir(exist_ok=True)
        (root / "diffs" / f"{previous_id}-to-{run_id}.json").write_text(
            json.dumps(diff, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / CURRENT).write_text(run_id + "\n", encoding="utf-8")
    return manifest
