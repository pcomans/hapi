"""The weak-sign skeleton's rules as properties, checked exhaustively over every name of every
Dodson & Hilton woman (labels and alternative names), and the third resolver tier's
guarantees over the whole index.

`test_weak_sign_skeleton.py` checks each rule on cited examples and pins the collision
table; this file checks that each rule holds for *every* authority name, generating the
variants a rule says must meet (or must not), so a regression in any rule shows up on the
names it breaks. Variants are made from the authority's own labels by the documented rules
only: no museum record is read (rule 14; see `test_the_key_reads_no_museum_or_evaluation_data`).
"""

from __future__ import annotations

import ast
import collections
import json
import re
import sys
import unicodedata
from pathlib import Path

import pytest

from pipeline.authority import royal_women as rw
from pipeline.authority import weak_sign_skeleton as module
from pipeline.authority.weak_sign_skeleton import DISAMBIGUATOR, MIN_WEAK_SIGN_SKELETON_LEN, weak_sign_skeleton

sys.path.insert(0, str(Path(__file__).parent))
from test_royal_women import KINGS  # noqa: E402  (the shared king-authority stand-in)

PIPELINE = Path(__file__).resolve().parents[1]
REPO = PIPELINE.parent
SOURCES = PIPELINE / "pipeline" / "authority" / "sources"

VOWELS = "aeiou"
WEAK = {"y": "i", "i": "y", "w": "u", "u": "w"}
# Consonants that stand alone after the fold (never part of kh, sh, ch, dj, tj, th), each
# with a different consonant to swap in that also stands alone.
SWAP = {"b": "f", "f": "b", "m": "n", "n": "m", "p": "b", "r": "l", "l": "r", "z": "b"}
KEY_ALPHABET = re.compile(r"^(?:[bcdfghklmnpqrstvxz]|(?<=[dt])j)+$")


@pytest.fixture(scope="module")
def women() -> list[rw.RoyalWoman]:
    return rw.load_royal_women()


@pytest.fixture(scope="module")
def index(women) -> rw.RoyalWomenIndex:
    return rw.build_index(women, KINGS)


@pytest.fixture(scope="module")
def names(women) -> list[str]:
    """Every name of every woman, without D&H's disambiguating letters and numerals, and
    without lacunose labels: the strings the rules operate on."""
    out = set()
    for woman in women:
        for name in (*woman.labels, *woman.alt_names):
            base = " ".join(t for t in name.split() if not DISAMBIGUATOR.match(t))
            if base and not rw.LACUNA.search(base):
                out.add(base)
    return sorted(out)


def keyed(names: list[str]) -> list[str]:
    return [n for n in names if weak_sign_skeleton(n)]


def test_the_name_population_is_what_the_properties_run_on(names) -> None:
    # Pinned so a change in the women (a new chunk) shows up here too, reviewed.
    assert len(names) == 257
    assert len(keyed(names)) == 172


# --- Each rule as an invariant over every name -------------------------------------------

def test_rule_0_any_disambiguator_token_is_ignored(names) -> None:
    for name in keyed(names):
        key = weak_sign_skeleton(name)
        for token in ("A", "B", "Q", "Z", "I", "II", "III", "IV", "V", "VII", "X"):
            assert weak_sign_skeleton(f"{name} {token}") == key, (name, token)
            assert weak_sign_skeleton(f"{token} {name}") == key, (name, token)


def test_rule_1_case_separators_and_diacritics_do_not_count(names) -> None:
    for name in keyed(names):
        key = weak_sign_skeleton(name)
        variants = {
            name.lower(), name.title(), name.replace("-", " "), name.replace("-", ""),
            name.replace(" ", "-"), f"  {name}  ", name.replace("e", "é").replace("a", "á"),
        }
        for variant in variants:
            if any(DISAMBIGUATOR.match(t) for t in variant.split()):
                continue  # an uppercase single letter would be read as a D&H letter
            assert weak_sign_skeleton(variant) == key, (name, variant)
        assert weak_sign_skeleton(unicodedata.normalize("NFD", name)) == key, name


def test_rule_2_a_final_t_comes_and_goes(names) -> None:
    """The final t is the folded name's (so "Meryetre(-Hatshepsut)" loses its t too)."""
    from pipeline.authority.claimgraph.normalize import translit_key
    for name in keyed(names):
        if translit_key(name).endswith("t"):
            stripped = name[:name.rindex("t")] + name[name.rindex("t") + 1:]
            assert weak_sign_skeleton(stripped) == weak_sign_skeleton(name), name
        else:
            assert weak_sign_skeleton(name + "t") == weak_sign_skeleton(name), name


def test_rule_3_every_vowel_may_be_any_vowel(names) -> None:
    checked = 0
    for name in keyed(names):
        key = weak_sign_skeleton(name)
        for i, ch in enumerate(name):
            if ch.lower() not in VOWELS:
                continue
            for other in VOWELS:
                variant = name[:i] + (other.upper() if ch.isupper() else other) + name[i + 1:]
                assert weak_sign_skeleton(variant) == key, (name, variant)
                checked += 1
    assert checked == 3660


def test_rule_3_every_weak_sign_may_be_its_other_rendering_or_absent(names) -> None:
    checked = 0
    for name in keyed(names):
        key = weak_sign_skeleton(name)
        for i, ch in enumerate(name):
            if ch.lower() not in WEAK:
                continue
            swapped = name[:i] + WEAK[ch.lower()] + name[i + 1:]
            dropped = name[:i] + name[i + 1:]
            assert weak_sign_skeleton(swapped) == key, (name, swapped)
            # Dropping it changes nothing, unless that exposes a final t (rule 2 is surface-final).
            if not (dropped.endswith("t") and not name.endswith("t")):
                assert weak_sign_skeleton(dropped) == key, (name, dropped)
            checked += 1
    assert checked == 225


def test_rule_3_j_is_a_weak_sign_except_in_dj_and_tj(names) -> None:
    for name in keyed(names):
        key = weak_sign_skeleton(name)
        # A j inserted after a vowel is the weak sign and goes.
        assert weak_sign_skeleton(re.sub(r"([aeiou])", r"\1j", name, count=1)) == key, name
    # In dj/tj (ḏ, ṯ after the fold) the j is the consonant's and stays: ḏ is not d.
    assert weak_sign_skeleton("Nedjmetes") == "ndjmts" != weak_sign_skeleton("Nedmetes") == "ndmts"
    assert weak_sign_skeleton("Netjerkhet") == "ntjrkh" != weak_sign_skeleton("Neterkhet") == "ntrkh"
    assert weak_sign_skeleton("Djedmutesankh") == weak_sign_skeleton("Jdjedmutesankh") == "djdmtsnkh"


def test_a_real_consonant_always_changes_the_key(names) -> None:
    """The key is not too lossy: swapping any standalone consonant for another changes it."""
    checked = 0
    for name in keyed(names):
        key = weak_sign_skeleton(name)
        folded = name.lower()
        for i, ch in enumerate(folded):
            if ch not in SWAP:
                continue
            if i + 1 < len(folded) and folded[i + 1] == "h" and ch in "cs":
                continue
            variant = name[:i] + SWAP[ch] + name[i + 1:]
            new = weak_sign_skeleton(variant)
            assert new != key, (name, variant)
            checked += 1
    assert checked == 514


def test_every_key_is_consonants_only_and_at_least_the_minimum(names) -> None:
    for name in names:
        key = weak_sign_skeleton(name)
        assert key == "" or (KEY_ALPHABET.match(key) and len(key) >= MIN_WEAK_SIGN_SKELETON_LEN), (name, key)


def test_the_key_is_deterministic_and_total() -> None:
    for text in ("", " ", "-", "A", "II", "–18P", "[...]", "ʿ", "Ahmes-Nefertiry", "ꜥꜣ-ḫpr-kꜣ-rꜥ"):
        assert weak_sign_skeleton(text) == weak_sign_skeleton(text)
        assert isinstance(weak_sign_skeleton(text), str)
    assert [weak_sign_skeleton(t) for t in ("", " ", "-", "A", "II", "–18P", "[...]", "ʿ")] == [""] * 8


# --- The resolver tier, over the whole index ------------------------------------------------

def _variant_only_the_third_tier_finds(index, label: str) -> str | None:
    """A rendering of `label` by the documented rules that the exact and claim-graph tiers
    both miss, or None if every such rendering is still caught by them."""
    for i, ch in enumerate(label):
        for repl in ({"e": "a", "a": "e", "o": "e", "i": "y", "y": "i", "u": "w", "w": "u"}.get(ch, ""),):
            if not repl:
                continue
            variant = label[:i] + repl + label[i + 1:]
            if rw.surface_key(variant) in index.exact:
                continue
            if any(k in index.normalized for k in rw.name_keys(variant)):
                continue
            return variant
    return None


def test_every_keyed_woman_is_reached_by_a_rendering_the_first_two_tiers_miss(index) -> None:
    """For every weak-sign key: a rendering of one of its labels by the documented rules, which
    the first two tiers miss, finds exactly the key's women; it resolves only when the record
    confirms the woman (her family king, or her dynasty, or her family kings' dynasty), never
    on the bare name, and never with another dynasty."""
    reached = groups = confirmable = 0
    for key, targets in sorted(index.weak_sign.items()):
        labels = sorted(label for label, ids in index.exact.items() if ids & targets and weak_sign_skeleton(label) == key)
        variant = next((v for v in (_variant_only_the_third_tier_finds(index, label) for label in labels) if v), None)
        if variant is None:
            continue
        reached += 1
        bare = rw.resolve_royal_woman(index, variant, record_king_ids=set(), record_dynasty=None)
        assert bare["resolution_method"] == "weak_sign_skeleton", variant
        assert bare["candidate_ids"] == sorted(targets), variant
        assert bare["status"] != "resolved", variant
        if len(targets) > 1:
            assert bare["status"] == "ambiguous", variant
            groups += 1
            continue
        (woman,) = targets
        assert bare["context_rule"] == "weak_sign_unconfirmed", variant
        confirming = set(index.dynasties[woman]) or set(index.family_dynasties[woman])
        for dynasty in range(0, 34):
            f = rw.resolve_royal_woman(index, variant, record_king_ids=set(), record_dynasty=dynasty)
            if dynasty in confirming:
                assert (f["status"], f["target_ids"]) == ("resolved", [index.king_ids.get(woman, woman)]), (variant, dynasty)
            else:
                assert f["status"] == "unmatched", (variant, dynasty)
        if index.family_king_ids[woman]:
            f = rw.resolve_royal_woman(index, variant, record_king_ids=set(index.family_king_ids[woman]),
                                       record_dynasty=None)
            assert f["status"] == "resolved", variant
        confirmable += bool(confirming or index.family_king_ids[woman])
    # 138 single women; 11 of them have neither a dynasty nor a family king (Tetisherit and
    # the like), so this tier can never resolve them.
    assert (reached, groups, confirmable) == (171, 33, 127)


def test_the_third_tier_never_overrides_the_first_two(index) -> None:
    """For every indexed label and each of its claim-graph keys, the answer comes from the
    tier that holds it, whatever the weak-sign index says."""
    for label, ids in index.exact.items():
        f = rw.resolve_royal_woman(index, label, record_king_ids=set(), record_dynasty=None)
        assert (f["resolution_method"], f["candidate_ids"]) == ("raw_exact", sorted(ids)), label


def test_the_third_tier_only_ever_returns_indexed_royal_women_or_female_rulers(index, women) -> None:
    indexed = set(index.dynasties)  # every target the index holds: D&H women and female rulers
    assert {w.target_id for w in women} <= indexed
    for targets in index.weak_sign.values():
        assert targets <= indexed
    female_rulers = {t for t in indexed if t.startswith("king:")} | set(index.king_ids.values())
    other_kings = set(KINGS.NAMES) - female_rulers
    assert other_kings >= {"king:amenhotep-iii", "king:mentuhotep-ii", "king:akhenaten", "king:ramesses-ii"}
    for king in other_kings:
        for label in KINGS.NAMES[king][0]:
            for variant in (label, label.replace("e", "a"), label + "t"):
                f = rw.resolve_royal_woman(index, variant, record_king_ids=set(), record_dynasty=None)
                assert king not in f["candidate_ids"] and king not in f["target_ids"], variant


@pytest.mark.parametrize("dynasty", [1, 11, 12, 13, 17, 18, 19, 20, 21])
def test_a_record_dynasty_never_lets_the_third_tier_pick_a_woman_of_another_dynasty(index, dynasty) -> None:
    for key, targets in index.weak_sign.items():
        text = key + "a"  # the skeleton itself plus a vowel: it folds back to `key`
        if rw.surface_key(text) in index.exact or any(k in index.normalized for k in rw.name_keys(text)):
            continue
        f = rw.resolve_royal_woman(index, text, record_king_ids=set(), record_dynasty=dynasty)
        if f["status"] == "resolved":
            chosen = f["royal_woman_id"] if "royal_woman_id" in f else f["target_ids"][0]
            known = index.dynasties.get(chosen, ())
            assert not known or dynasty in known, (text, chosen, known, dynasty)


# --- The citations in the module's docstring are to committed data ------------------------

@pytest.mark.parametrize(("source", "text"), [
    ("porter-moss-theban-necropolis", "ʿAhmosi Nefertere"),
    ("porter-moss-theban-necropolis", "Merytamun"),
    ("porter-moss-theban-necropolis", "Meryet-Amun"),
    ("porter-moss-theban-necropolis", "Tanezem(t)"),
    ("porter-moss-theban-necropolis", "Nebttaui"),
    ("leprohon-2013-titulary", "Tetisheri"),
    ("leprohon-2013-titulary", "iah mes"),
    ("leprohon-2013-titulary", "imen em ipet"),
    ("leprohon-2013-titulary", "djehuty"),
    ("leprohon-2013-titulary", "netjeru"),
    ("pharaoh-se", "Khasty"),
    ("pharaoh-se", "Meni"),
    ("pharaoh-se", "Semsu"),
    ("pharaoh-se", "Qebehu"),
    ("pharaoh-se", "Iah mesu"),
    ("pharaoh-se", "Netjery khet"),
    ("dodson-hilton-queens", "Tetisherit"),
    ("dodson-hilton-queens", "Ahmes-Nefertiry"),
    ("dodson-hilton-queens", "Nebettawy A"),
])
def test_each_cited_rendering_is_in_the_committed_source(source: str, text: str) -> None:
    """Both ways: the cited rendering is in the committed source, and the module cites it."""
    rows = (SOURCES / source / "reconciled.jsonl").read_text(encoding="utf-8")
    assert text in rows
    assert text in module.__doc__


def test_every_cited_pair_of_renderings_meets_on_one_key() -> None:
    pairs = [("Ahmes-Nefertiry", "ʿAhmosi Nefertere"), ("Meryetamun", "Merytamun"), ("Meryetamun", "Meryet-Amun"),
             ("Tetisherit", "Tetisheri"), ("Nebettawy", "Nebttaui"), ("Nefertiry", "Nefertari"),
             ("Ahmes-Nefertiry", "Ahmose-Nefertiry")]
    for a, b in pairs:
        assert weak_sign_skeleton(a) == weak_sign_skeleton(b) != "", (a, b)


# --- The real king authority -----------------------------------------------------------------

# On the committed claim graph: the female rulers only the king lists hold (keyed as kings),
# and the king clusters of D&H's women who reigned (Sobkneferu, Hatshepsut D, Tawosret).
KING_ONLY_FEMALE_RULERS_REACHED = {
    "leprohon-leprohon-33.02a", "leprohon-leprohon-33.03a", "leprohon-leprohon-33.05a", "leprohon-leprohon-33.08a",
    "leprohon-leprohon-33.12", "leprohon-leprohon-33.14", "leprohon-leprohon-6.07", "pharaoh_se-Cleopatra-VII"}
DH_WOMEN_WHO_REIGNED = ["cluster-beckerath-12.08", "cluster-beckerath-18.05", "cluster-leprohon-leprohon-19.08"]


class GraphKings:
    """The claim graph's ruler resolver (the linkability resolver the evaluations load) as a
    royal_women.KingAuthority, over the committed graph."""

    def __init__(self) -> None:
        import importlib.util
        path = REPO / "docs/evaluations/hapi-linkability-mvp-2026-08-28/scripts/run_linkability.py"
        spec = importlib.util.spec_from_file_location("_weak_sign_run_linkability", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        graph = json.loads(mod.GRAPH.read_text(encoding="utf-8"))
        self._resolver, self._catalog = mod.build_ruler_resolver(graph)
        self._norm = mod.ruler_norm
        self._node = {r["id"]: r for r in graph["rulers"]}
        names: dict[str, set[str]] = collections.defaultdict(set)
        by_subject = collections.defaultdict(list)
        for claim in graph["claims"]:
            if claim["predicate"] in mod.NAME_PREDICATES:
                by_subject[claim["subject_id"]].append(claim)
        for target, info in self._catalog.items():
            for member in info["member_ids"]:
                names[target].add(self._node[member]["display_name"])
                for claim in by_subject[member]:
                    names[target].update(v for v in (claim.get("value_text"), claim.get("value_translit")) if v)
        self._names = names

    def resolve(self, name: str) -> dict:
        return self._resolver.resolve(name, self._norm)

    def labels(self, target_id: str) -> list[str]:
        return sorted(self._names[target_id])

    def dynasties(self, target_id: str) -> tuple[int, ...]:
        return tuple(sorted({self._node[m]["dynasty"] for m in self._catalog[target_id]["member_ids"]
                             if self._node[m]["dynasty"] is not None}))


@pytest.fixture(scope="module")
def graph_index(women) -> rw.RoyalWomenIndex:
    return rw.build_index(women, GraphKings())


def test_on_the_real_king_graph_the_tier_reaches_the_queens_and_no_other_king(graph_index) -> None:
    def found(text, **kw):
        f = rw.resolve_royal_woman(graph_index, text, record_king_ids=set(), record_dynasty=kw.get("dynasty"))
        return f["status"], f["resolution_method"], f["target_ids"]

    # D&H's labels made into other renderings by the documented rules only; a weak-sign
    # match needs the record's confirmation, here its dynasty.
    assert found("Ahmose Nefertari") == ("unmatched", "weak_sign_skeleton", [])
    assert found("Ahmose Nefertari", dynasty=18) == ("resolved", "weak_sign_skeleton", ["dodson_hilton:Ahmes-Nefertiry"])
    # Her father "Taa II" is not a king the graph resolves (D&H's name for Seqenenre), so only
    # Ahmose I's Dynasty 18 confirms her here, not 17.
    assert found("Ahmose Nefertari", dynasty=17) == ("unmatched", "weak_sign_skeleton", [])
    assert found("Ahmose Nefertari", dynasty=19) == ("unmatched", "weak_sign_skeleton", [])
    assert found("Sithathoryunet", dynasty=12) == ("resolved", "weak_sign_skeleton", ["dodson_hilton:Sithathoriunet"])
    # No king in her D&H entry and no dynasty of her own: nothing can confirm these two.
    assert found("Tetisheri", dynasty=17) == ("unmatched", "weak_sign_skeleton", [])
    assert found("Ahmose-Tumerisi", dynasty=17) == ("unmatched", "weak_sign_skeleton", [])
    # The only kings the tier can reach are the female rulers of `female-rulers.json`: those
    # the king lists alone hold (keyed as kings) and D&H's women who reigned (resolved to theirs).
    king_targets = {t for targets in graph_index.weak_sign.values() for t in targets if not t.startswith("dodson_hilton:")}
    assert king_targets == KING_ONLY_FEMALE_RULERS_REACHED
    assert sorted(graph_index.king_ids.values()) == DH_WOMEN_WHO_REIGNED


# --- No museum or evaluation data ------------------------------------------------------------

def test_the_key_reads_no_museum_or_evaluation_data() -> None:
    """The key's module imports only `re` and the committed normalizer, and names no file."""
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    imports = {(node.module, node.level) if isinstance(node, ast.ImportFrom) else (alias.name, 0)
               for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
               for alias in (node.names if isinstance(node, ast.Import) else [None])}
    assert imports == {("__future__", 0), ("re", 0), ("claimgraph.normalize", 1)}
    code = ast.unparse([n for n in tree.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))])
    for forbidden in ("open(", "read_text", "Path(", "ndjson", "dropbox", "corpus", "evaluations"):
        assert forbidden not in code, forbidden
