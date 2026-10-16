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
from pathlib import Path

import pytest

from pipeline.authority import royal_women as rw
from pipeline.authority.graph_kings import GraphKings
from pipeline.authority import weak_sign_skeleton as module
from pipeline.authority.claimgraph.normalize import translit_key
from pipeline.authority.royal_women import DISAMBIGUATOR
from pipeline.authority.weak_sign_skeleton import MIN_WEAK_SIGN_CONSONANTS, consonant_count, weak_sign_skeleton

sys.path.insert(0, str(Path(__file__).parent))
from test_royal_women import KINGS  # noqa: E402  (the shared king-authority stand-in)

PIPELINE = Path(__file__).resolve().parents[1]
REPO = PIPELINE.parent

VOWELS = "aeiou"
WEAK = {"y": "i", "i": "y", "w": "u", "u": "w"}
# Consonants that stand alone after the fold (never part of kh, sh, ch, dj, tj, th), each
# with a different consonant to swap in that also stands alone.
SWAP = {"b": "f", "f": "b", "m": "n", "n": "m", "p": "b", "r": "l", "l": "r", "z": "b"}
# After the fold: no c or q (both k); the digraph units written ḫ š ḏ ṯ; no j outside them.
KEY_ALPHABET = re.compile(r"^[bcdfghklmnpqrstvxzḫšḏṯ]+$")


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
    assert len(keyed(names)) == 199


# --- Each rule as an invariant over every name -------------------------------------------

def test_rule_0_the_authority_side_strips_the_disambiguator_and_keeps_the_numeral(names) -> None:
    """The key itself strips nothing: a letter that is a consonant changes it and a roman
    numeral, all weak i/v/x, mostly vanishes — which is why the resolver strips both before
    keying a label and remembers the numeral (`weak_sign_entry`)."""
    for name in keyed(names):
        key = weak_sign_skeleton(name)
        for token in ("A", "B", "Q", "Z", "I", "II", "III", "IV", "V", "VII", "X"):
            numerals = frozenset({token}) if rw.NUMERAL.match(token) else frozenset()
            assert rw.weak_sign_entry(f"{name} {token}") == (key, numerals), (name, token)
            assert rw.weak_sign_entry(f"{token} {name}") == (key, numerals), (name, token)
        for token in ("B", "Q", "Z", "V", "X"):
            assert weak_sign_skeleton(f"{name} {token}") != key, (name, token)
        if not translit_key(name).endswith("t"):  # else the trailing token shields the final t
            for token in ("A", "I", "II", "III"):
                assert weak_sign_skeleton(f"{name} {token}") == key, (name, token)


def test_rule_1_case_and_separators_do_not_count(names) -> None:
    boundary_pair = re.compile(r"[sk][\s\-]h|[dt][\s\-]j", re.I)
    for name in keyed(names):
        key = weak_sign_skeleton(name)
        for variant in {name.lower(), name.title(), name.replace("-", " "), name.replace("-", ""),
                        name.replace(" ", "-"), name.replace(" ", ""), f"  {name}  "}:
            if any(DISAMBIGUATOR.match(t) for t in variant.split()):
                continue  # an uppercase single letter would be read as a D&H letter by the resolver
            if boundary_pair.search(name) and variant in (name.replace("-", ""), name.replace(" ", "")):
                # A digraph is a unit within a token (rule 1), so the separator between the
                # s and h of "Ahmes-Henutemipet" is kept information: written solid it reads š.
                continue
            assert weak_sign_skeleton(variant) == key, (name, variant)


def test_rule_2_c_and_q_are_letters_of_their_own(names) -> None:
    """The former c/q → k rule is dropped: putting c or q for a k changes the key."""
    checked = 0
    for name in keyed(names):
        key = weak_sign_skeleton(name)
        for i, ch in enumerate(name):
            if ch.lower() != "k" or name[i + 1:i + 2].lower() == "h":
                continue  # kh is ḫ, not k
            for other in "cq":
                assert weak_sign_skeleton(name[:i] + other + name[i + 1:]) != key, (name, i, other)
                checked += 1
    assert checked == 38


def test_rule_3_a_final_t_comes_and_goes(names) -> None:
    """The final t is the folded name's (so "Meryetre(-Hatshepsut)" loses its t too)."""
    for name in keyed(names):
        if translit_key(name).endswith("t"):
            stripped = name[:name.rindex("t")] + name[name.rindex("t") + 1:]
            assert weak_sign_skeleton(stripped) == weak_sign_skeleton(name), name
        else:
            assert weak_sign_skeleton(name + "t") == weak_sign_skeleton(name), name


def test_rule_4_every_vowel_may_be_any_vowel(names) -> None:
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
    assert checked == 4020


def test_rule_4_every_weak_sign_may_be_its_other_rendering_or_absent(names) -> None:
    checked = 0
    for name in keyed(names):
        key = weak_sign_skeleton(name)
        for i, ch in enumerate(name):
            if ch.lower() not in WEAK:
                continue
            swapped = name[:i] + WEAK[ch.lower()] + name[i + 1:]
            dropped = name[:i] + name[i + 1:]
            assert weak_sign_skeleton(swapped) == key, (name, swapped)
            # Dropping it changes nothing, unless that exposes a final t (rule 3 is surface-final)
            # or joins the letters of a digraph pair ("Syhefernerer" without its y reads š: a
            # digraph is a unit of the written letters, rule 1).
            before, after = name[i - 1:i].lower(), name[i + 1:i + 2].lower()
            joins_pair = (before in ("s", "k") and after == "h") or (before in ("d", "t") and after == "j")
            if not (dropped.endswith("t") and not name.endswith("t")) and not joins_pair:
                assert weak_sign_skeleton(dropped) == key, (name, dropped)
            checked += 1
    assert checked == 258


def test_rule_4_j_is_a_weak_sign_except_in_dj_and_tj(names) -> None:
    for name in keyed(names):
        key = weak_sign_skeleton(name)
        # A j inserted after a vowel is the weak sign and goes; so is one opening a token.
        assert weak_sign_skeleton(re.sub(r"([aeiou])", r"\1j", name, count=1)) == key, name
        assert weak_sign_skeleton("J" + name.lower()) == key, name
        assert weak_sign_skeleton(name.replace(" ", "-J").replace("-", "-J")) == key, name
    # In dj/tj (ḏ, ṯ after the fold) the j is the consonant's and stays: ḏ is not d.
    assert weak_sign_skeleton("Nedjmetes") == "nḏmts" != weak_sign_skeleton("Nedmetes") == "ndmts"
    assert weak_sign_skeleton("Netjerkhet") == "nṯrḫ" != weak_sign_skeleton("Neterkhet") == "ntrḫ"
    assert weak_sign_skeleton("Djedmutesankh") == weak_sign_skeleton("Jdjedmutesankh") == "ḏdmtsnḫ"


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
    assert checked == 560


def test_every_key_is_consonants_only_and_at_least_the_minimum(names) -> None:
    for name in names:
        key = weak_sign_skeleton(name)
        assert key == "" or (KEY_ALPHABET.match(key) and consonant_count(key) >= MIN_WEAK_SIGN_CONSONANTS), (name, key)


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


def _resolve(index, text, kings=frozenset(), dynasty=None):
    return rw.resolve_royal_woman(index, text, record_king_ids=set(kings), record_dynasty=dynasty)


def _labels_under(index, key: str, targets: set[str]) -> list[str]:
    """The indexed labels of `targets` that the authority side keys under `key`, without
    their letters and numerals (the exact index holds them casefolded, so a regnal numeral
    is put back in capitals first to be recognised)."""
    labels = set()
    for label, ids in index.exact.items():
        restored = re.sub(r"\b([ivx]+)\b", lambda m: m.group(1).upper(), label)
        if ids & targets and rw.weak_sign_entry(restored)[0] == key:
            labels.add(" ".join(t for t in restored.split() if not DISAMBIGUATOR.match(t)))
    return sorted(labels)


def _family_only(key: str) -> bool:
    return consonant_count(key) == MIN_WEAK_SIGN_CONSONANTS


def _confirming(index, woman: str) -> set[int]:
    return set(index.dynasties[woman]) | set(index.family_dynasties[woman])


def test_every_key_is_reached_by_a_rendering_the_first_two_tiers_miss(index) -> None:
    """For every weak-sign key of the index: a rendering of one of its labels by the
    documented rules, which the first two tiers miss, finds exactly the key's targets. A
    single target resolves only when the record confirms it (a family king named, or a
    dynasty among hers and her family kings' — unless the key is three consonants, when
    only the king does; a key the authority spells in several forms for different targets is
    never a single target), never on the bare name, and never against
    her own dynasty without a named king."""
    reached, skipped = 0, {}
    groups = singles = by_king = by_dynasty_only = never = 0
    for key, targets in sorted(index.weak_sign.items()):
        labels = _labels_under(index, key, targets)
        variant = next((v for v in (_variant_only_the_third_tier_finds(index, label) for label in labels) if v), None)
        if variant is None:
            skipped[key] = labels
            continue
        reached += 1
        bare = _resolve(index, variant)
        assert bare["resolution_method"] == "weak_sign_skeleton", variant
        assert bare["candidate_ids"] == sorted(targets), variant
        assert bare["status"] != "resolved", variant
        if len(targets) > 1:
            groups += 1
            assert bare["status"] == "ambiguous", variant
            continue
        singles += 1
        (woman,) = targets
        assert bare["context_rule"] == "weak_sign_unconfirmed", variant
        own, confirming, kings = set(index.dynasties[woman]), _confirming(index, woman), index.family_king_ids[woman]
        target = index.king_ids.get(woman, woman)
        for dynasty in range(0, 34):
            f = _resolve(index, variant, dynasty=dynasty)
            if own and dynasty not in own:
                assert (f["status"], f["context_rule"]) == ("unmatched", "record_dynasty_contradicts"), (variant, dynasty)
            elif dynasty in confirming and not _family_only(key):
                assert (f["status"], f["target_ids"]) == ("resolved", [target]), (variant, dynasty)
            else:
                assert (f["status"], f["context_rule"]) == ("unmatched", "weak_sign_unconfirmed"), (variant, dynasty)
        if kings:
            assert _resolve(index, variant, kings=kings)["target_ids"] == [target], variant
            # ... and the named king overrides a dynasty that is not hers.
            other = next(d for d in range(0, 34) if d not in own)
            assert _resolve(index, variant, kings=kings, dynasty=other)["target_ids"] == [target], variant
            by_king += 1
        elif confirming and not _family_only(key):
            by_dynasty_only += 1
        else:
            never += 1
    # Every key is reached: for each, some single-letter rendering of one of its labels is
    # neither an indexed label nor a claim-graph key of one.
    assert skipped == {}
    assert reached == len(index.weak_sign) == 197
    # Single targets: confirmable by a named family king (with or without a dynasty), by a
    # dynasty alone (female rulers, and women none of whose kin the stand-in king authority
    # resolves, on a key of four consonants or more), or by nothing (Tetisherit and the
    # like, and three-consonant keys without a resolvable king).
    # (The stand-in resolves Amenemhat I and Sety II, which moves two Dynasty 12 women from
    # dynasty-only to by-king and Tawosret, a three-consonant key, from never to by-king.)
    assert (groups, singles, by_king, by_dynasty_only, never) == (37, 160, 56, 76, 28)


def test_the_narrowing_rules_pick_within_a_group_and_the_confirmation_still_applies(index) -> None:
    """For every shared key: each member a named family king singles out resolves (rule
    "family", overriding any dynasty); each dynasty that singles a member out resolves her
    only when the key is not family-only and the dynasty confirms her (rule "dynasty"); a
    key the authority spells differently for different targets (`different_spellings`) stays
    ambiguous whatever the record says."""
    by_family = by_dynasty = dynasty_refused = withheld = 0
    withheld_keys = rw.different_spellings(index)
    for key, targets in sorted(index.weak_sign.items()):
        if len(targets) < 2:
            continue
        labels = _labels_under(index, key, targets)
        variant = next((v for v in (_variant_only_the_third_tier_finds(index, label) for label in labels) if v), None)
        if variant is None:
            continue
        if key in withheld_keys:
            # Different spellings on one key: no king and no dynasty may pick (a family king
            # would pick the woman linked to him whatever her name). Egyptologist review, P1.
            for member in sorted(targets):
                for kwargs in ({"kings": index.family_king_ids[member]}, {"dynasty": 99}, {}):
                    f = _resolve(index, variant, **kwargs)
                    assert (f["status"], f["context_rule"], f["target_ids"]) == (
                        "ambiguous", "weak_sign_different_spellings", sorted(targets)), (variant, kwargs)
                    withheld += 1
            continue
        for member in sorted(targets):
            kings = index.family_king_ids[member]
            if kings and sum(1 for t in targets if index.family_king_ids[t] & kings) == 1:
                f = _resolve(index, variant, kings=kings, dynasty=99)
                assert (f["status"], f["target_ids"], f["context_rule"]) == (
                    "resolved", [index.king_ids.get(member, member)], "family"), (variant, member)
                by_family += 1
        for dynasty in range(0, 34):
            fitting = [t for t in targets if not index.dynasties[t] or dynasty in index.dynasties[t]]
            if len(fitting) != 1:
                continue
            (member,) = fitting
            f = _resolve(index, variant, dynasty=dynasty)
            if not _family_only(key) and dynasty in _confirming(index, member):
                assert (f["status"], f["target_ids"], f["context_rule"]) == (
                    "resolved", [index.king_ids.get(member, member)], "dynasty"), (variant, dynasty)
                by_dynasty += 1
            else:
                assert (f["status"], f["context_rule"]) == ("unmatched", "weak_sign_unconfirmed"), (variant, dynasty)
                dynasty_refused += 1
    # Withheld: hntt, nbt, nfr, nfrsbk and tntmn, 25 members x 3 records; tntmn's Tintamun,
    # once picked by Thutmose IV (family) and by Dynasty 18, is among them.
    assert (by_family, by_dynasty, dynasty_refused, withheld) == (17, 17, 66, 75)


def test_the_third_tier_only_ever_returns_indexed_royal_women_or_female_rulers(index, women) -> None:
    indexed = set(index.dynasties)  # every target the index holds: D&H women and female rulers
    assert {w.target_id for w in women} <= indexed
    for targets in index.weak_sign.values():
        assert targets <= indexed
    female_rulers = {t for t in indexed if t.startswith("king:")}
    assert {t for targets in index.weak_sign.values() for t in targets if t.startswith("king:")} == female_rulers
    assert female_rulers == {"king:arsinoe-ii", "king:berenike", "king:berenike-ii", "king:cleopatra-i", "king:cleopatra-ii",
                             "king:cleopatra-vii-l", "king:cleopatra-vii-p", "king:neith-iqeret"}


def test_a_record_dynasty_alone_resolves_only_a_confirmable_woman_of_that_dynasty(index) -> None:
    """The skeleton itself plus a vowel folds back to the key. Under each dynasty, a bare
    key resolves only a woman the dynasty confirms (hers or her family kings'), never on a
    family-only key, never against her own dynasty; otherwise it is refused or ambiguous."""
    outcomes = collections.Counter()
    withheld_keys = rw.different_spellings(index)
    for key, targets in sorted(index.weak_sign.items()):
        # The key plus a vowel folds back to the key; a hyphen keeps two units that are
        # written as a digraph's letters (s-h in "hmshntmp") from reading as one.
        text = re.sub(r"(?<=[sk])(?=h)|(?<=[dt])(?=j)", "-", key) + "a"
        assert weak_sign_skeleton(text) == key, (key, text)
        if rw.surface_key(text) in index.exact or any(k in index.normalized for k in rw.name_keys(text)):
            outcomes["caught by an earlier tier"] += 1
            continue
        for dynasty in range(0, 34):
            f = _resolve(index, text, dynasty=dynasty)
            assert f["resolution_method"] == "weak_sign_skeleton", text
            if key in withheld_keys:
                assert (f["status"], f["context_rule"]) == ("ambiguous", "weak_sign_different_spellings"), (text, dynasty)
                outcomes["ambiguous", "weak_sign_different_spellings"] += 1
            elif f["status"] == "resolved":
                woman = f["royal_woman_id"]
                assert woman in targets
                assert not _family_only(key), (text, dynasty)
                assert dynasty in _confirming(index, woman), (text, dynasty)
                assert not index.dynasties[woman] or dynasty in index.dynasties[woman], (text, dynasty)
                outcomes["resolved"] += 1
            else:
                if f["status"] == "ambiguous" and f["context_rule"] is None:
                    # The women reported are those the record's dynasty leaves (#369).
                    assert f["target_ids"] and all(not index.dynasties[t] or dynasty in index.dynasties[t]
                                                   for t in f["target_ids"]), (text, dynasty)
                outcomes[f["status"], f["context_rule"]] += 1
    # 197 keys x 34 dynasties: no bare key is an indexed label or claim-graph key. The five
    # withheld keys (hntt, nbt, nfr, nfrsbk, tntmn) give 170 = 5 x 34; tntmn's two dynasty
    # picks (Tintamun under 18, Tentamun B under 21) are among them.
    assert outcomes == {
        "resolved": 145,
        # 911 were ambiguous before #369 although every candidate was of another dynasty.
        ("unmatched", "record_dynasty_contradicts"): 5760,
        ("unmatched", "weak_sign_unconfirmed"): 529,
        ("ambiguous", None): 94,
        ("ambiguous", "weak_sign_different_spellings"): 170,
    }


def test_every_cited_pair_of_renderings_meets_on_one_key() -> None:
    pairs = [("Ahmes-Nefertiry", "ʿAhmosi Nefertere"), ("Meryetamun", "Merytamun"), ("Meryetamun", "Meryet-Amun"),
             ("Tetisherit", "Tetisheri"), ("Nebettawy", "Nebttaui"), ("Nefertiry", "Nefertari"),
             ("Ahmes-Nefertiry", "Ahmose-Nefertiry"), ("Ahmes-Nefertiry", "Jꜥḥ-ms-nfrt-jrj"), ("Ahmes", "Iah mesu")]
    for a, b in pairs:
        assert weak_sign_skeleton(a) == weak_sign_skeleton(b) != "", (a, b)


# --- The real king authority -----------------------------------------------------------------

# On the committed claim graph: the female rulers only the king lists hold (keyed as kings),
# and the king clusters of D&H's women who reigned (Sobkneferu, Hatshepsut D, Tawosret).
KING_ONLY_FEMALE_RULERS_REACHED = {
    "leprohon-leprohon-33.02a", "leprohon-leprohon-33.03a", "leprohon-leprohon-33.05a", "leprohon-leprohon-33.08a",
    "leprohon-leprohon-33.12", "leprohon-leprohon-33.14", "leprohon-leprohon-6.07", "pharaoh_se-Cleopatra-VII"}
DH_WOMEN_WHO_REIGNED = ["cluster-beckerath-12.08", "cluster-beckerath-18.05", "cluster-leprohon-leprohon-19.08"]


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
    # The Ptolemaic female rulers, by their king_name only, numeral matched. Their Greek and
    # Latin spellings (Kleopatra, Berenice) do not meet on this tier since c/q → k was dropped.
    assert found("Cleopatra II", dynasty=33) == ("resolved", "raw_exact", ["leprohon-leprohon-33.08a"])
    assert found("Kleopatra II", dynasty=33) == ("unmatched", None, [])
    assert found("Cleopatra III", dynasty=33) == ("unmatched", None, [])
    assert found("Berenike II", dynasty=33) == ("resolved", "raw_exact", ["leprohon-leprohon-33.03a"])
    assert found("Berenice II", dynasty=33) == ("unmatched", None, [])
    # The only kings the tier can reach are the female rulers of `female-rulers.json`: those
    # the king lists alone hold (keyed as kings) and D&H's women who reigned (resolved to theirs).
    king_targets = {t for targets in graph_index.weak_sign.values() for t in targets if not t.startswith("dodson_hilton:")}
    assert king_targets == KING_ONLY_FEMALE_RULERS_REACHED
    assert sorted(graph_index.king_ids.values()) == DH_WOMEN_WHO_REIGNED
    assert len(graph_index.weak_sign) == 197


def test_on_the_real_king_graph_the_new_collisions_are_the_pinned_ones(graph_index) -> None:
    """The collisions the tier introduces over the real graph: the four D&H keys whose women
    D&H spell differently (hntt, nbt, nfr, tntmn), the Ptolemaic female rulers who share a name
    (Berenike II / Berenike III; Cleopatra I / II / VII), and female-rulers.json's
    "Neferusobek" for the king Sobkneferu meeting D&H's princess Neferusobk."""
    new = rw.new_weak_sign_collisions(graph_index)
    assert new == {
        "brnk": ("leprohon-leprohon-33.03a", "leprohon-leprohon-33.12"),
        "hntt": ("dodson_hilton:Henttawy A", "dodson_hilton:Henttawy B", "dodson_hilton:Henttawy C",
                 "dodson_hilton:Henttawy D", "dodson_hilton:Henttawy Q", "dodson_hilton:Henutwati"),
        "clptr": ("leprohon-leprohon-33.05a", "leprohon-leprohon-33.08a", "pharaoh_se-Cleopatra-VII"),
        "nbt": ("dodson_hilton:Nebetia", "dodson_hilton:Nebtit", "dodson_hilton:Nebtu"),
        "nfr": ("dodson_hilton:Neferet B", "dodson_hilton:Neferet I", "dodson_hilton:Neferet II", "dodson_hilton:Neferet Q",
                "dodson_hilton:Neferet R", "dodson_hilton:Neferu A", "dodson_hilton:Neferu B", "dodson_hilton:Neferu I",
                "dodson_hilton:Neferu II", "dodson_hilton:Neferu III", "dodson_hilton:Neferu Q"),
        "nfrsbk": ("dodson_hilton:Neferusobk", "dodson_hilton:Sobkneferu"),
        "tntmn": ("dodson_hilton:Tentamun A", "dodson_hilton:Tentamun B", "dodson_hilton:Tintamun"),
    }
    assert graph_index.weak_sign_numerals["clptr"] == {
        "leprohon-leprohon-33.05a": {"I"}, "leprohon-leprohon-33.08a": {"II"}, "pharaoh_se-Cleopatra-VII": {"VII"}}


def test_on_the_real_king_graph_the_differently_spelt_keys_are_the_pinned_ones(graph_index) -> None:
    """The keys the resolver withholds, derived from the authority's spellings alone: four
    D&H groups and female-rulers.json's "Neferusobek" beside D&H's "Neferusobk". A single
    target's own spellings (Tawosret / Tausret; "Meryetre(-Hatshepsut)" and its alt name) do
    not count; the Ptolemaic clptr and brnk are one spelling each."""
    assert rw.different_spellings(graph_index) == DIFFERENT_SPELLINGS
    assert graph_index.weak_sign_spellings["tsr"] == {"dodson_hilton:Tawosret": {"tawosret", "tausret"}}
    assert not rw.spelled_differently(graph_index, "tsr") and not rw.spelled_differently(graph_index, "clptr")


DIFFERENT_SPELLINGS = {
    "hntt": ("henttawy", "henutwati"),
    "nbt": ("nebetia", "nebtit", "nebtu"),
    "nfr": ("neferet", "neferu"),
    "nfrsbk": ("neferusobek", "neferusobk"),
    "tntmn": ("tentamun", "tintamun"),
}


# --- No museum or evaluation data ------------------------------------------------------------

def test_the_key_reads_no_museum_or_evaluation_data() -> None:
    """The key's module imports only `re` and the committed normalizer, and names no file."""
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    imports = {(node.module, node.level) if isinstance(node, ast.ImportFrom) else (alias.name, 0)
               for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
               for alias in (node.names if isinstance(node, ast.Import) else [None])}
    assert imports == {("__future__", 0), ("re", 0), ("unicodedata", 0), ("claimgraph.normalize", 1)}
    code = ast.unparse([n for n in tree.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))])
    for forbidden in ("open(", "read_text", "Path(", "ndjson", "dropbox", "corpus", "evaluations"):
        assert forbidden not in code, forbidden


def test_a_wrapped_numeral_resolves_as_the_bare_one_on_the_real_graph(graph_index) -> None:
    """Every indexed label with a regnal numeral: written "[II]", "(II)" or "II." it resolves as
    written bare, on every tier (Codex review: "Berenike [II]" had met the bare Berenike)."""
    checked = 0
    for key in graph_index.exact:  # case-folded labels; the numeral is written back in capitals
        tokens = key.split()
        if len(tokens) < 2 or not rw.NUMERAL.match(tokens[-1].upper()):
            continue
        tokens[-1] = tokens[-1].upper()
        bare = rw.resolve_royal_woman(graph_index, " ".join(tokens), record_king_ids=set(), record_dynasty=None)
        for wrapped in (f"[{tokens[-1]}]", f"({tokens[-1]})", f"{tokens[-1]}."):
            text = " ".join([*tokens[:-1], wrapped])
            found = rw.resolve_royal_woman(graph_index, text, record_king_ids=set(), record_dynasty=None)
            assert (found["status"], found["target_ids"]) == (bare["status"], bare["target_ids"]), text
            checked += 1
    assert checked == 36  # 12 numbered labels, three wrappings each
    found = rw.resolve_royal_woman(graph_index, "Berenike [II]", record_king_ids=set(), record_dynasty=33)
    assert (found["status"], found["target_ids"]) == ("resolved", ["leprohon-leprohon-33.03a"])


@pytest.mark.parametrize("text", ["Berenike II ?", "Berenike II (?)", "Berenike II [?]", "Cleopatre ? II",
                                  "Berenike (?)", "Ahhotep?"])
def test_a_doubt_mark_anywhere_refuses_the_mention(graph_index, text) -> None:
    """A detached doubt mark questions the reading as an attached one does (Codex review)."""
    found = rw.resolve_royal_woman(graph_index, text, record_king_ids=set(), record_dynasty=33)
    assert (found["status"], found["context_rule"], found["target_ids"]) == ("unmatched", "doubted_mention", [])


@pytest.mark.parametrize(("text", "expected"), [
    ("Mer[i]taten", ("unmatched", "weak_sign_skeleton", [], "weak_sign_unconfirmed")),
    # Read as letters, a restored name is the name: Meryetaten and Isetneferet on the exact tier.
    ("Meryet[a]ten", ("resolved", "raw_exact", ["dodson_hilton:Meryetaten"], None)),
    ("[I]setneferet", ("ambiguous", "raw_exact", ["dodson_hilton:Isetneferet A", "dodson_hilton:Isetneferet B",
                                                  "dodson_hilton:Isetneferet C", "dodson_hilton:Isetneferet D"], None))])
def test_a_restoration_inside_a_word_is_not_a_numeral(graph_index, text, expected) -> None:
    """A bracket followed by a letter restores letters of the name (Codex review), read as
    letters on every tier."""
    found = rw.resolve_royal_woman(graph_index, text, record_king_ids=set(), record_dynasty=None)
    assert (found["status"], found["resolution_method"], found["target_ids"], found["context_rule"]) == expected


@pytest.mark.parametrize("text", [
    "Berenike [II?]", "Berenike [ii]", "Berenike[ii]", "Berenike [II?],", "Cleopatre(ii)", "Cleopatre (ii)",
    "Cleopatre(iii)", "Cleopatre(II?)", "Cleopatre (II?)", "Cleopatra (II?)", "CleopatreII.", "CleopatreIII",
    "Cleopatre (II]", "Cleopatre [II)", "Cleopatre(II]", "Cleopatre ( II ]", "Berenike[II)",
    "Cleopatre (II", "Cleopatre II]", "Berenike [II", "Berenike II)", "Cleopatre ( II", "Berenike II ].",
    "Cleopatre(II", "Berenike[II", "CleopatreII)", "BerenikeII]", "Cleopatre(ii", "Berenike[II?", "CleopatreIII).",
    "CLEOPATREII", "BERENIKEII.", "AHHOTPII", "TETI", "TETISHERI",  # all-caps: TETI is the deliberate loud miss
    "Nefertit[i]", "Neferu I II", "Neferu I I", "Cleopatre II (III)",
    "Berenike II?", "Berenike II?.", "Cleopatre ?II", "Cleopatre II!", "Cleopatre ii?",
    "Ahhotp 2", "Ahhotp 11", "Cleopatre (2)", "Berenike2", "Cleopatre ２",
    "Berenike Ⅱ", "Cleopatre ⅲ", "BerenikeⅡ", "Cleopatre Ⅻ", "Ahhotp ½"])
def test_a_bracketed_numeral_that_cannot_be_read_refuses_rather_than_drops(graph_index, text) -> None:
    """The fold deletes any bracketed text, so an unread bracketed numeral would leave the bare
    name to match another ruler (scope review of the Codex fix): it is refused."""
    found = rw.resolve_royal_woman(graph_index, text, record_king_ids=set(), record_dynasty=33)
    assert (found["status"], found["context_rule"], found["target_ids"]) == ("unmatched", "unreadable_numeral", [])


def test_trailing_punctuation_wraps_a_numeral(graph_index) -> None:
    # and an attached wrapped numeral is split off (Codex review): "Berenike[II]", "Berenike(II)".
    for text in ("Berenike [II],", "Berenike II;", "Berenike (II):", "Berenike[II]", "Berenike(II)", "Berenike [ II ]"):
        found = rw.resolve_royal_woman(graph_index, text, record_king_ids=set(), record_dynasty=33)
        assert (found["status"], found["target_ids"]) == ("resolved", ["leprohon-leprohon-33.03a"]), text


def test_a_numbered_labels_keys_meet_no_other_targets_unnumbered_label(graph_index) -> None:
    """"Neferu I" keys as "neferui": no unnumbered label of another target may share a
    claim-graph key with a numbered one (scope review)."""
    numbered, unnumbered = collections.defaultdict(set), collections.defaultdict(set)
    for key, targets in graph_index.exact.items():
        tokens = key.split()
        bucket = numbered if len(tokens) > 1 and rw.NUMERAL.match(tokens[-1].upper()) else unnumbered
        for name_key in rw.name_keys(key):
            bucket[name_key] |= targets
    clashes = {k: (numbered[k], unnumbered[k]) for k in numbered if k in unnumbered and unnumbered[k] - numbered[k]}
    assert clashes == {}


def test_an_attached_numeral_selects_or_refuses_on_the_weak_sign_tier(graph_index) -> None:
    def found(text):
        f = rw.resolve_royal_woman(graph_index, text, record_king_ids=set(), record_dynasty=33)
        return f["status"], f["target_ids"]
    assert found("Cleopatre(II)") == ("resolved", ["leprohon-leprohon-33.08a"])
    assert found("Cleopatre(III)") == ("unmatched", [])


def test_the_mention_reader_refuses_no_authority_label(graph_index, women) -> None:
    """The allow-list (`read_mention`) must read every real name the authority holds: D&H's
    labels and alternative names, the female rulers' king names, and every label the real king
    graph gives them (titulary and transliterations included) — all but D&H's two placeholder
    ids, which carry no name."""
    labels = [label for w in women for label in (*w.labels, *w.alt_names)]
    rulers = json.loads(rw.FEMALE_RULERS.read_text(encoding="utf-8"))["entries"]
    labels += [entry["king_name"] for entry in rulers]
    kings = GraphKings()
    for entry in rulers:  # every female ruler, with or without a D&H row, as build_index reads her
        (king_id,) = kings.resolve(entry["king_name"])["target_ids"]
        labels += [rw.LEADING_QUEEN.sub("", label) for label in kings.labels(king_id)]
    assert "Cleopatra VII Philopator" in labels
    refused = sorted({label for label in labels if rw.read_mention(label)[1]})
    assert refused == ["–18P", "–18Q"]


def test_graph_kings_built_from_a_given_module_and_graph_is_the_default_one() -> None:
    """The injection point the #361 evaluation uses (a frozen tree's linkability module and
    graph) gives the same kings as the default construction."""
    from pipeline.authority.graph_kings import load_linkability
    default = GraphKings()
    module = load_linkability()
    given = GraphKings(module, json.loads(module.GRAPH.read_text(encoding="utf-8")))
    assert given.catalog.keys() == default.catalog.keys() and len(given.catalog) > 800
    for target in ("cluster-beckerath-18.05", "cluster-beckerath-18.15", "cluster-leprohon-leprohon-19.08"):
        assert (given.labels(target), given.dynasties(target)) == (default.labels(target), default.dynasties(target))
    assert default.dynasties("cluster-beckerath-18.05") == (18,)


def test_on_the_real_king_graph_both_queen_ahmose_records_reach_ahmes_b_through_hatshepsut() -> None:
    """#369, as #361 resolves (the real graph, the TLA-linked spellings): the field of Brooklyn
    3634 and of Met 566763 names Hatshepsut as her kin, Hatshepsut is one cluster, and that
    cluster is a family king of Ahmes B. Without the stated kin, the three-consonant key stays
    unconfirmed."""
    from pipeline.authority import tla_links

    kings = GraphKings()
    index = rw.build_index(rw.load_royal_women(), kings, linked_spellings=tla_links.linked_spellings())
    assert kings.resolve("Hatshepsut")["target_ids"] == ["cluster-beckerath-18.05"]
    assert "cluster-beckerath-18.05" in index.family_king_ids["dodson_hilton:Ahmes B"]
    assert not rw.spelled_differently(index, weak_sign_skeleton("Ahmose"))
    for field in ("Queen Ahmose, Mother of Hatshepsut", "Hatshepsut's Mother, Queen Ahmose"):
        start = field.index("Ahmose")
        f = rw.resolve_ruler_mention(index, kings, field, start, start + len("Ahmose"), record_king_ids=set(),
                                     record_dynasty=18)
        assert (f["status"], f["target_ids"], f["resolution_method"], f["context_rule"], f["stated_kin_king_ids"]) == (
            "resolved", ["dodson_hilton:Ahmes B"], "weak_sign_skeleton", "family", ["cluster-beckerath-18.05"]), field
    f = rw.resolve_ruler_mention(index, kings, "Queen Ahmose", 6, 12, record_king_ids=set(), record_dynasty=18)
    assert (f["status"], f["context_rule"]) == ("unmatched", "weak_sign_unconfirmed")
