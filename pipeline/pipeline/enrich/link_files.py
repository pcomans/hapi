"""The authority links of a corpus, written as versioned files (#338 step 2).

One run reads the canonical records and their raw payloads, extracts the mentions, resolves
them in both modes (`authority_links.MODES`) and writes, under `<root>/<run_id>/`:

* `mentions.ndjson.gz`;
* `resolutions-<mode>.ndjson.gz` and `links-<mode>.ndjson.gz` for each mode;
* `manifest.json`: the inputs' digest, each mode's snapshot, every file's SHA-256 and row
  count, the resolution outcomes by entity type, status and reason, and the inventory of what is
  not resolved (`unsupported`: the entity types with no authority, with their reason and
  count; `unevaluated_scopes`: the resolved types' museum pairs no evaluation qualified);
The manifest hashes each file's content (a gzip file's decompressed NDJSON). The run id is
the SHA-256 over the inputs' digest, both modes' resolver versions and this
module's own SHA-256 (it types the rows and writes the files), so the
same inputs and code give the same id and the same content (rows sorted). A run whose
directory exists is checked against it, never overwritten.

`<root>/CURRENT` names the run in force. When a run replaces another there, it writes
`<root>/diffs/<previous>-to-<run>.json`: for each mode, every link added, removed (with why) or
changed (its mentions changed, with how each lost one now resolves). Replacing `CURRENT` is the
commit: a diff is published only once its run is current, and one left pending by a run that
died is published or removed by the next run, as the commit happened or not. A run is written beside
its place and renamed into it, and `CURRENT` is replaced in one step, so a crashed process
leaves no half-written run (there is no fsync: a power loss can). Runs under one root hold a lock (`.lock`); a second one at the same time fails
loud.

A link is removed when its source decision is withdrawn: re-running on the new inputs or
authority makes no such link, and the diff says whether the record is gone, its mentions are
gone, or a mention that made it now resolves otherwise (with its new status and reason). Files
are the store for now (owner, 2026-10-16); a database table comes later.
"""

from __future__ import annotations

import collections
import contextlib
import fcntl
import gzip
import hashlib
import io
import json
import os
import re
import shutil
from collections.abc import Callable
from pathlib import Path

from pipeline.authority import royal_women
from pipeline.enrich import authority_links, mentions
from pipeline.enrich.inputs import check_inputs

# A link is the same link across runs by its key; every other field it carries is compared but
# these: the version that made it (it changes with any code or authority change, and the run
# id records it), the mode (the same on both sides of a diff) and the museum (the record's own).
LINK_KEY = ("artifact_id", "entity_type", "target_id")
NOT_DIFFED = ("resolver_version", "mode", "museum")
CURRENT = "CURRENT"
LOCK = ".lock"
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


def content_sha256(name: str, data: bytes) -> str:
    return hashlib.sha256(gzip.decompress(data) if name.endswith(".gz") else data).hexdigest()


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
    # A royal-woman target is a D&H woman's; a female ruler resolves to her king's cluster.
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
    """The links added, removed and changed against a previous run. A removed link says why; a
    kept link whose mentions, evidence roles or kind changed is `changed`, with the old and new
    values and the mentions it lost and how each now resolves (or that it is gone), so a
    withdrawal inside a link backed by several mentions is seen too."""
    def key(link: dict) -> tuple:
        return tuple(link[f] for f in LINK_KEY)
    old, new = {key(l): l for l in previous}, {key(l): l for l in links}
    by_mention = {r["mention_id"]: r for r in resolutions}

    def now(mention_ids: list[str]) -> list[dict]:
        return [{"mention_id": m, "status": by_mention[m]["status"], "reason": by_mention[m]["reason"],
                 "target_ids": by_mention[m]["target_ids"]} if m in by_mention else {"mention_id": m, "status": "gone"}
                for m in mention_ids]

    fields = ("artifact_id", "museum", "entity_type", "target_id", "mention_ids")
    removed = []
    for k in sorted(set(old) - set(new)):
        link = old[k]
        if link["artifact_id"] not in artifact_ids:
            why = {"why": "record_gone"}
        elif not any(m in by_mention for m in link["mention_ids"]):
            why = {"why": "mentions_gone"}
        else:
            why = {"why": "resolves_otherwise", "now": now(link["mention_ids"])}
        removed.append({**{f: link[f] for f in fields}, **why})
    changed = []
    for k in sorted(set(old) & set(new)):
        moved = [f for f in sorted(set(old[k]) | set(new[k])) if f not in LINK_KEY + NOT_DIFFED
                 and old[k].get(f) != new[k].get(f)]
        if moved:
            lost = sorted(set(old[k]["mention_ids"]) - set(new[k]["mention_ids"]))
            changed.append({**{f: new[k][f] for f in fields if f != "mention_ids"},
                            **{f"previous_{f}": old[k][f] for f in moved}, **{f: new[k][f] for f in moved},
                            "lost": now(lost)})
    added = [{f: new[k][f] for f in fields} for k in sorted(set(new) - set(old))]
    return {"added": added, "removed": removed, "changed": changed,
            "kept": len(set(old) & set(new)) - len(changed)}


def write_run(root: Path, read_inputs: Callable[[], tuple[list[dict], dict[str, dict[str, dict]]]],
              authority: authority_links.Authority | None = None) -> dict:
    """Write one run under `root` and point `root/CURRENT` at it; return its manifest.
    `read_inputs` gives the canonical records and the raw payloads by museum and source id; it
    is called with the run lock held, so no run can read older inputs than a run that became
    current before it. The inputs must be one pipeline generation (`inputs.check_inputs`)."""
    with run_lock(root):
        canonical, raw_indexes = read_inputs()
        check_inputs(canonical, raw_indexes)
        return _run(root, canonical, raw_indexes, authority)


def _run(root: Path, canonical: list[dict], raw_indexes: dict[str, dict[str, dict]],
         authority: authority_links.Authority | None) -> dict:
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
        # The SHA-256 of each file's content: a gzip file's decompressed NDJSON, which does not
        # depend on the zlib build that compressed it.
        "files": {name: {"content_sha256": content_sha256(name, data), "rows": counts[name]}
                  for name, data in sorted(files.items())},
        "outcomes": {mode: outcomes(by_mode[mode][0]) for mode in authority_links.MODES},
        "inventory": inventory(by_mode["authority"][0]),
    }
    files["manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")

    return _write(root, run_id, files, manifest, canonical, by_mode)


@contextlib.contextmanager
def run_lock(root: Path):
    """One run at a time under a root: a second one fails loud instead of racing for CURRENT
    (two runs diffing against the same CURRENT would leave a withdrawal between them
    unrecorded). The operating system releases the lock if the process dies."""
    root.mkdir(parents=True, exist_ok=True)
    with open(root / LOCK, "a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"another run holds {root / LOCK}; runs under one root must not overlap") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _write(root: Path, run_id: str, files: dict[str, bytes], manifest: dict, canonical: list[dict],
           by_mode: dict) -> dict:
    previous_id = (root / CURRENT).read_text(encoding="utf-8").strip() if (root / CURRENT).exists() else None
    # The diff against the run in force first: if that run's files are not what it wrote, nothing
    # is written.
    if previous_id is not None and (not previous_id or not (root / previous_id).is_dir()):
        raise ValueError(f"{root / CURRENT} names {previous_id!r}, which is not a run under {root}")
    diff = None
    if previous_id is not None and previous_id != run_id:
        artifact_ids = {row["id"] for row in canonical}
        diff = {"previous_run": previous_id, "run": run_id}
        # The previous run as it wrote it, every file, or the diff would report false changes and
        # the store would keep a damaged run as history.
        verify_run(root / previous_id)
        for mode in authority_links.MODES:
            diff[mode] = diff_links(read_rows(root / previous_id / f"links-{mode}.ndjson.gz"),
                                    by_mode[mode][1], by_mode[mode][0], artifact_ids)

    run_dir = root / run_id
    if run_dir.exists():
        # A run directory appears whole (renamed into place), so one that lacks a file or holds
        # other content was changed after it was written.
        for name, data in files.items():
            if not (run_dir / name).exists():
                raise ValueError(f"{run_dir} lacks {name}: it was changed after it was written")
            if content_sha256(name, (run_dir / name).read_bytes()) != content_sha256(name, data):
                raise ValueError(f"{run_dir / name} differs from what this run writes (changed on disk, or "
                                 f"the step is not deterministic)")
        if sorted(p.name for p in run_dir.iterdir()) != sorted(files):
            raise ValueError(f"{run_dir} holds files a run does not write")
    # Only after CURRENT, the previous run and this run's own directory are found sound: a run
    # that fails its checks leaves the root as it was, a pending diff included.
    settle_diffs(root, previous_id)
    if not run_dir.exists():
        # Written beside it and renamed into place, so a crashed process leaves only a scratch
        # directory, which the next run removes.
        # Under the lock no other run is writing, so every scratch directory is a dead run's.
        for dead in root.glob(".*.partial"):
            shutil.rmtree(dead) if dead.is_dir() else dead.unlink()
        scratch = root / f".{run_id}.partial"
        scratch.mkdir(parents=True)
        for name, data in files.items():
            (scratch / name).write_bytes(data)
        os.rename(scratch, run_dir)

    # Replacing CURRENT is the commit: the diff is written beside its name first and takes it only
    # after, so a diff of a transition that never happened is never published (`settle_diffs`).
    pending = None
    if diff is not None:
        (root / "diffs").mkdir(exist_ok=True)
        pending = root / "diffs" / f".{previous_id}-to-{run_id}.json.partial"
        # Written whole, then named: a process killed while writing leaves only a `.writing` file,
        # which `settle_diffs` discards.
        writing = pending.with_name(pending.name + ".writing")
        writing.write_text(json.dumps(diff, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.rename(writing, pending)
    pointer = root / f".{CURRENT}.partial"
    pointer.write_text(run_id + "\n", encoding="utf-8")
    os.replace(pointer, root / CURRENT)
    if pending is not None:
        os.rename(pending, root / "diffs" / f"{previous_id}-to-{run_id}.json")
    return manifest


PENDING_DIFF = re.compile(
    r"^\.(?P<previous>[0-9a-f]{64})-to-(?P<run>[0-9a-f]{64})\.json\.partial(?P<writing>\.writing)?$")


def verify_run(run_dir: Path) -> None:
    """A run directory holds exactly the files its manifest names, each with its recorded
    content."""
    if not (run_dir / "manifest.json").is_file():
        raise ValueError(f"{run_dir} has no manifest.json")
    recorded = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))["files"]
    present = sorted(p.name for p in run_dir.iterdir())
    if present != sorted([*recorded, "manifest.json"]):
        raise ValueError(f"{run_dir} holds {present}, not the files its manifest names")
    for name, entry in recorded.items():
        if content_sha256(name, (run_dir / name).read_bytes()) != entry["content_sha256"]:
            raise ValueError(f"{run_dir / name} is not what that run wrote (its manifest disagrees)")


def settle_diffs(root: Path, current: str | None) -> None:
    """A diff left pending by a run that died: published if its run became current (the run died
    after the commit), else removed unread (it died before, so that transition never happened,
    whatever the file holds; a `.writing` file is always such). Only this module writes pending
    diffs, so a name it does not write, or a diff to publish whose content names other runs
    than its name, fails loud, and before any pending diff is touched."""
    if not (root / "diffs").is_dir():
        return
    found = []
    for pending in sorted(p for p in (root / "diffs").iterdir() if p.name.startswith(".")):
        m = PENDING_DIFF.match(pending.name)
        if m is None:
            raise ValueError(f"{pending} is not a pending diff this module writes")
        publish = m["run"] == current and not m["writing"]
        if publish:
            content = json.loads(pending.read_text(encoding="utf-8"))
            if (content["previous_run"], content["run"]) != (m["previous"], m["run"]):
                raise ValueError(f"{pending} holds the diff of {content['previous_run']} to {content['run']}")
        found.append((pending, m, publish))
    for pending, m, publish in found:
        if publish:
            os.rename(pending, root / "diffs" / f"{m['previous']}-to-{m['run']}.json")
        else:
            pending.unlink()
