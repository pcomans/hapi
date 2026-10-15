"""The weak-sign key's hill-climb on the TLA 2018 names: a fixed split, two metrics.

Ground truth: `pipeline/pipeline/authority/sources/tla-2018-names/reconciled.jsonl` (CC BY-SA
4.0). Each lemma's transliteration and its German and English translations, glosses and
bracketed descriptions removed, are one name in several conventions: their keys should meet
(recall). Two lemmas whose transliterations differ in a strong consonant should not share a key
(strong merges). Nothing here reads museum records.

    cd pipeline && uv run python ../docs/evaluations/weak-sign-key-hillclimb/measure.py \\
        keys/iteration-2.py --split validation

The split is by a hash of the TLA id: train 60%, validation 20%, test 20%. Iterations were
accepted on train and checked on validation; the test split was scored once, at the end
(`results/test-final.json`), for the starting and the final key.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TLA = REPO / "pipeline" / "pipeline" / "authority" / "sources" / "tla-2018-names" / "reconciled.jsonl"
SPLITS = ("train", "validation", "test")


def split_of(tla_id: str) -> str:
    h = int(hashlib.sha256(f"weak-sign-hillclimb/{tla_id}".encode()).hexdigest(), 16) % 10
    return "train" if h < 6 else "validation" if h < 8 else "test"


GLOSS = re.compile(r"\s*[\(;,].*$")


def renderings(row: dict) -> list[str]:
    """The transliteration, then each translation value with its gloss removed; a bracketed
    value is a description, not a name."""
    out = [row["transliteration"]]
    for value in (t["value"] for t in row["translations"] if t.get("value")):
        if value.startswith("["):
            continue
        value = GLOSS.sub("", value).strip()
        if value and value not in out:
            out.append(value)
    return out


# The transliteration's own signs, every consonant distinct: two lemmas with one strict key
# are one name in two entries, not a merge.
STRICT_DROP = re.compile(r"[.\-=\s()\[\]⸗~ʾ]|i̯|u̯|̯")
# The weak signs and a final t, which the key is meant to drop, and the consonants English
# renderings never tell apart (ḥ/h, ẖ/ḫ, q/k). Fixed before iteration 1 was accepted and
# applied to every iteration (README).
WEAK = re.compile(r"[ꜣꜥjyw]|ꞽ|i")
ENGLISH_SAME = str.maketrans({"ḥ": "h", "ẖ": "ḫ", "q": "k", "ḳ": "k"})


def strict_key(transliteration: str) -> str:
    return unicodedata.normalize("NFC", STRICT_DROP.sub("", transliteration).casefold())


def strong_skeleton(strict: str) -> str:
    s = strict[:-1] if strict.endswith("t") else strict
    return WEAK.sub("", s.translate(ENGLISH_SAME))


def load_key(path: Path):
    namespace: dict = {}
    source = path.read_text(encoding="utf-8").replace(
        "from .claimgraph.normalize import", "from pipeline.authority.claimgraph.normalize import")
    exec(compile(source, str(path), "exec"), namespace)  # noqa: S102 (a committed key snapshot)
    return namespace["weak_sign_skeleton"]


def measure(key, rows: list[dict], split: str) -> dict:
    rows = [r for r in rows if split_of(r["tla_id"]) == split]
    pairs = met = 0
    keyed: dict[str, set[str]] = {}
    for row in rows:
        forms = renderings(row)
        keys = [key(f) for f in forms]
        for (_, ka), (_, kb) in itertools.combinations(zip(forms, keys), 2):
            if ka and kb:
                pairs += 1
                met += ka == kb
        k = key(row["transliteration"])
        if k:
            keyed.setdefault(k, set()).add(strict_key(row["transliteration"]))
    strong = {k: sorted(v) for k, v in sorted(keyed.items())
              if len(v) > 1 and len({strong_skeleton(x) for x in v}) > 1}
    names = sum(len(v) for v in keyed.values())
    return {"split": split, "lemmas": len(rows), "positive_pairs": pairs, "met": met,
            "recall": round(met / pairs, 4), "keyed_names": names,
            "names_in_strong_merges": sum(len(v) for v in strong.values()), "strong_merges": strong}


def tla_rows() -> list[dict]:
    return [json.loads(line) for line in TLA.read_text(encoding="utf-8").splitlines()][1:]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("key", help="a key snapshot under keys/")
    parser.add_argument("--split", choices=SPLITS, required=True)
    args = parser.parse_args()
    print(json.dumps(measure(load_key(HERE / args.key), tla_rows(), args.split), ensure_ascii=False, indent=1))
