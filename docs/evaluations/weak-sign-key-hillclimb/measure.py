"""The weak-sign key's hill-climb, protocol v2 (PROTOCOL.md): TLA names, split by name,
recall and coverage per split, strong merges over the whole set; and the held-out check on
the claim graph's king spellings.

    cd pipeline && uv run python ../docs/evaluations/weak-sign-key-hillclimb/measure.py keys/v2-0-baseline.py

Keys are measured with `normalize_frozen.py`, never the live normalizer.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import itertools
import json
import re
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TLA = REPO / "pipeline" / "pipeline" / "authority" / "sources" / "tla-2018-names" / "reconciled.jsonl"
GRAPH = REPO / "web-claimgraph" / "data" / "claim-graph.json"
KEY_IMPORT = "from .claimgraph.normalize import translit_key\n"


def frozen_translit_key():
    spec = importlib.util.spec_from_file_location("weak_sign_hillclimb_normalize", HERE / "normalize_frozen.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.translit_key


def load_key(path: Path):
    source = path.read_text(encoding="utf-8")
    if source.count(KEY_IMPORT) != 1:
        raise ValueError(f"{path} does not import translit_key as the committed key does")
    namespace = {"translit_key": frozen_translit_key(), "__name__": "weak_sign_hillclimb_key"}
    exec(compile(source.replace(KEY_IMPORT, ""), str(path), "exec"), namespace)  # noqa: S102 (a committed snapshot)
    return namespace["weak_sign_skeleton"]


# --- TLA ground truth -------------------------------------------------------------------------

GLOSS = re.compile(r"\s*[\(;,].*$")
STRICT_DROP = re.compile(r"[.\-=⸗~ʾ\s()\[\]]|̯|̮")
STRONG_DROP = re.compile(r"[ꜣjywiꞽ]")
FOLD_AWARE = str.maketrans({"ḥ": "h", "ẖ": "ḫ"})


def tla_rows() -> list[dict]:
    lines = TLA.read_text(encoding="utf-8").splitlines()
    if "_source" not in json.loads(lines[0]):
        raise ValueError(f"{TLA} does not start with its _source header")
    return [json.loads(line) for line in lines[1:]]


def name_of(row: dict) -> str:
    return unicodedata.normalize("NFC", STRICT_DROP.sub("", row["transliteration"]).casefold())


def strong_skeleton(name: str) -> str:
    return STRONG_DROP.sub("", name[:-1] if name.endswith("t") else name)


def split_of(name: str) -> str:
    h = int(hashlib.sha256(f"weak-sign-hillclimb-v2/{name}".encode()).hexdigest(), 16) % 10
    return "train" if h < 6 else "validation" if h < 8 else "test"


def renderings(row: dict) -> list[str]:
    out = [row["transliteration"]]
    for value in (t["value"] for t in row["translations"] if t.get("value")):
        if value.startswith("["):
            continue
        value = GLOSS.sub("", value).strip()
        if value and value not in out:
            out.append(value)
    return out


def measure(key, rows: list[dict]) -> dict:
    per_split = {s: {"pairs": 0, "met": 0, "renderings": 0, "keyed": 0} for s in ("train", "validation", "test")}
    by_key: dict[str, set[str]] = collections.defaultdict(set)
    for row in rows:
        name = name_of(row)
        stats = per_split[split_of(name)]
        forms = renderings(row)
        keys = [key(f) for f in forms]
        stats["renderings"] += len(forms)
        stats["keyed"] += sum(1 for k in keys if k)
        for ka, kb in itertools.combinations(keys, 2):
            if ka and kb:
                stats["pairs"] += 1
                stats["met"] += ka == kb
        for k in keys:
            if k:
                by_key[k].add(name)

    def merges(skeleton) -> dict[str, list[str]]:
        return {k: sorted(v) for k, v in sorted(by_key.items()) if len({skeleton(n) for n in v}) > 1}

    strict = merges(strong_skeleton)
    fold_aware = merges(lambda n: strong_skeleton(n.translate(FOLD_AWARE)))
    return {
        "splits": {s: {**v, "recall": round(v["met"] / v["pairs"], 4), "coverage": round(v["keyed"] / v["renderings"], 4)}
                   for s, v in per_split.items()},
        "strong_merges": {"names": sum(len(v) for v in strict.values()), "groups": strict},
        "fold_aware_merges": {"names": sum(len(v) for v in fold_aware.values())},
    }


def accepted(before: dict, after: dict) -> bool:
    b, a = before["splits"], after["splits"]
    return (a["train"]["recall"] > b["train"]["recall"]
            and a["validation"]["recall"] >= b["validation"]["recall"]
            and a["train"]["coverage"] >= b["train"]["coverage"]
            and a["validation"]["coverage"] >= b["validation"]["coverage"]
            and after["strong_merges"]["names"] <= before["strong_merges"]["names"])


# --- Held-out: the claim graph's king spellings ------------------------------------------------

NUMERAL = re.compile(r"\s+[IVX]+\b")
PAREN = re.compile(r"\s*\(.*$")


def king_clusters() -> list[list[str]]:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    node = {r["id"]: r for r in graph["rulers"]}
    out = []
    for cluster in graph["clusters"]:
        names = sorted({NUMERAL.sub("", PAREN.sub("", node[m]["display_name"])).strip()
                        for m in cluster["member_ids"]} - {""})
        out.append(names)
    return out


def held_out(key) -> dict:
    pairs = met = 0
    owners: dict[str, set[int]] = collections.defaultdict(set)
    for i, names in enumerate(king_clusters()):
        keys = [key(n) for n in names]
        for ka, kb in itertools.combinations(keys, 2):
            if ka and kb:
                pairs += 1
                met += ka == kb
        for k in keys:
            if k:
                owners[k].add(i)
    shared = sorted(k for k, v in owners.items() if len(v) > 1)
    return {"pairs": pairs, "met": met, "recall": round(met / pairs, 4), "keys_shared_by_clusters": shared}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("key")
    parser.add_argument("--held-out", action="store_true")
    args = parser.parse_args()
    key = load_key(HERE / args.key)
    result = held_out(key) if args.held_out else measure(key, tla_rows())
    print(json.dumps(result, ensure_ascii=False, indent=1))
