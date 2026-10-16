"""Museum mentions of rulers, sites and other entities, read from the raw museum records.

Promoted for production (#338) from the #361 ruler re-registration's extractor
(`docs/evaluations/ruler-reregistration-2026-10-15/scripts/extract_mentions.py`), whose file
stays as it is because #361 pins it by hash; `pipeline/tests/test_enrich_mentions.py` holds the
source of each shared definition identical, so the first change here must also change that
test and this paragraph. Detection and span boundaries come from museum field structure and fixed syntax
rules; authority labels, aliases, identifiers and resolver results are not inputs. Each
museum's evidence fields are named in `extract_mentions` (the per-museum field inventory).

Cleveland and the Walters came after #361: their readers are `cleveland_mentions` and
`walters_mentions`, added beside #361's definitions rather than into them, and
`extract_all_mentions` joins them. A run calls that; without Cleveland or Walters records it gives
exactly what `extract_mentions` gives (tested).
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from collections.abc import Iterable

# #361: the royal-woman cues (`royal_women.ROYAL_WOMAN_CUE_BEFORE`) are cues too, longest first,
# so that "Queen Mother Tiye" and "King's Wife Ahhotep" are cued as wholes ("mother" and "wife"
# are stop words after a bare "queen" or "king").
ROYAL_CUE = re.compile(
    r"\b(queen\s+mother|great\s+royal\s+wife|king['\u2019]s\s+(?:great\s+wife|wife|mother|daughter)"
    r"|god['\u2019]s\s+wife(?:\s+of\s+amun)?|divine\s+adoratrice(?:\s+of\s+amun)?|princess"
    r"|reigns?\s+of|pontificate\s+of|pharaoh|king|queen|ruler)\b",
    re.I,
)
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
        # #361: the record's dynasty as its canonical record gives it, for the royal-women
        # resolver's dynasty check (`royal_women.single_dynasty` reads it).
        "record_dynasty": artifact.get("dynasty"),
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


JOINT_REIGN = re.compile(r"^\s*joint\s+reigns?\s+of\s+", re.I)


def cleveland_reign_components(entry: str) -> list[tuple[str, int]]:
    """The reign components of one Cleveland `culture` entry, with their offsets: the top-level
    components (`component_spans`) that open as a reign does ("reign of", "probably reign of",
    "late reign of", "joint reign of", ...). The mapper's `ruler_display_name` and
    `cleveland_mentions` both read these, so the two cannot disagree on what a reign is."""
    return [(component, start) for component, start, _ in component_spans(entry)
            if LEADING_REIGN.match(component) or LEADING_UNCERTAIN_REIGN.match(component) or JOINT_REIGN.match(component)]


def without_trailing_dates(component: str) -> str:
    """A reign without its trailing dates: the final parenthesis is cut only when it holds a
    digit ("(1390–1352 BCE)"), so a doubt mark ("Ramesses II(?)") stays and the expression
    classifies as uncertain. Only that last parenthesis is cut, so a range keeps both ends
    ("reign of X (dates)–reign of Y"). Cleveland's reign components and the Walters' `Reign`
    field are both read through it, by their mappers and by their mention readers."""
    if component.endswith(")"):
        cut = component.rfind("(")
        if re.search(r"\d", component[cut:]):
            return component[:cut].rstrip()
    return component


def cleveland_mentions(artifact: dict, raw: dict) -> list[dict]:
    """Cleveland's ruler mentions: the reign components of each `culture` entry
    (`cleveland_reign_components`), its catalogued reign, read as the Met's `reign` field is
    (`classify_reign_expression`) once their dates are cut (`without_trailing_dates`). Ranges and
    qualifiers ("or later", "probably", "(?)") classify as such and are not resolved to one ruler.
    Cleveland's other evidence (`find_spot`, places in `culture`, title cues) is not read yet
    (docs/museum-sources/cleveland.md)."""
    found = []
    for index, entry in enumerate(raw.get("culture") or []):
        for component, component_start in cleveland_reign_components(entry):
            text = without_trailing_dates(component)
            length = len(text)
            expression, candidate, span = classify_reign_expression(text)
            if expression == "single_identity" and candidate is not None and span is not None:
                start, end = component_start + span[0], component_start + span[1]
            else:
                start, end = component_start, component_start + length
            found.append(make_mention(
                artifact=artifact, entity_type="ruler", field_path=f"culture[{index}]", field_value=entry,
                start=start, end=end, extraction_method="typed_structured_reign_parser",
                evidence_role="catalogued_reign", expression_type=expression,
            ))
    return found


def walters_reign_expression(value: str) -> tuple[str, str | None, tuple[int, int] | None]:
    """The Walters' `Reign` field, which names its ruler with no leading "reign of" ("Ramesses II
    (1279-1213 BC)"), read with the Met reign parser's own tests once its dates are cut
    (`without_trailing_dates`): a doubt, a temporal phrase or a range or list is not one ruler.
    A field of more than one top-level component lists several rulers ("Shabako (715-700 BC),
    Psammetichus I") and is a list too. A hyphen without spaces is not a range, as in the parser:
    a hyphenated pair ("Psametik I-Necho II") classifies as `single_identity`, one name that no
    ruler matches in the authority mode, and that the literal mode links by its text."""
    text = without_trailing_dates(value.strip())
    offset = value.find(text)
    if not text:
        return "empty", None, None
    if UNCERTAIN.search(text):
        return "uncertain_identity", None, None
    if len(list(component_spans(text))) > 1:
        return "multi_or_range", None, None
    candidate = TRAILING_PHASE.sub("", text).strip()
    if TEMPORAL_CONTEXT.search(candidate):
        return "temporal_context", None, None
    if RANGE_OR_MULTI.search(candidate):
        return "multi_or_range", None, None
    if not candidate:
        return "unparsed_structured_value", None, None
    return "single_identity", candidate, (offset, offset + len(candidate))


def royal_cue_mentions(artifact: dict, field_path: str, value: str) -> tuple[list[dict], int]:
    """The royal-cue mentions of one text field, by `extract_mentions`' own grammar for the
    fields it reads (its loop, for one field), and the number of cues with no name after them. A
    test holds it to `extract_mentions` on the museums that reads."""
    found: list[dict] = []
    missed = 0
    seen: set[tuple[int, int]] = set()
    for cue in ROYAL_CUE.finditer(value):
        if value[cue.end():cue.end() + 2].startswith(("'", "\u2019")):
            continue
        candidate, start, end = candidate_after_royal_cue(value, cue)
        if candidate is None:
            missed += 1
            continue
        if (start, end) in seen:
            continue
        seen.add((start, end))
        context = value[max(0, cue.start() - 15):min(len(value), end + 24)]
        if UNCERTAIN.search(context):
            expression = "uncertain_identity"
        elif RANGE_OR_MULTI.search(context):
            expression = "multi_or_range"
        else:
            expression = "single_identity"
        found.append(make_mention(
            artifact=artifact, entity_type="ruler", field_path=field_path, field_value=value,
            start=start, end=end, extraction_method="explicit_royal_cue_grammar",
            evidence_role="explicit_royal_text_cue", expression_type=expression,
        ))
    return found, missed


WALTERS_REIGN_FIELD = "Reign"
# Read with the royal-cue grammar, as Brooklyn's title and date fields are: `DateText` names a
# reign on some records ("ca. 1250 BCE (New Kingdom, 19th dynasty, reign of Ramesses II)").
WALTERS_CUE_FIELDS = ("Title", "DateText")


def walters_mentions(artifact: dict, raw: dict) -> tuple[list[dict], Counter]:
    """The Walters' ruler mentions: its catalogued reign (`Reign`, read by
    `walters_reign_expression`), as the Met's `reign` is read, and royal cues in its title and
    date text, as Brooklyn's title and dates are read. Its description and inscriptions are not
    read. The Walters publishes no find place
    (docs/museum-sources/walters.md). Returns the mentions and the cues with no name after them,
    by field."""
    obj = raw["object"]
    found: list[dict] = []
    value = obj[WALTERS_REIGN_FIELD]
    if value.strip():
        expression, candidate, span = walters_reign_expression(value)
        if expression == "single_identity" and candidate is not None and span is not None:
            start, end = span
        else:
            stripped = value.strip()
            start, end = value.find(stripped), value.find(stripped) + len(stripped)
        found.append(make_mention(
            artifact=artifact, entity_type="ruler", field_path=f"object.{WALTERS_REIGN_FIELD}", field_value=value,
            start=start, end=end, extraction_method="typed_structured_reign_parser",
            evidence_role="catalogued_reign", expression_type=expression,
        ))
    missed: Counter = Counter()
    for field in WALTERS_CUE_FIELDS:
        if obj[field].strip():
            cued, misses = royal_cue_mentions(artifact, f"object.{field}", obj[field])
            found += cued
            if misses:
                missed[f"walters|object.{field}"] += misses
    return found, missed


def _cleveland_reader(artifact: dict, raw: dict) -> tuple[list[dict], Counter]:
    return cleveland_mentions(artifact, raw), Counter()


# The readers of the museums added after #361's extractor, each giving its mentions and its royal
# cues with no name after them, by field.
ADDED_READERS = {"cleveland": _cleveland_reader, "walters": walters_mentions}


def extract_all_mentions(canonical: list[dict], raw_indexes: dict[str, dict[str, dict]]) -> tuple[list[dict], dict]:
    """`extract_mentions` (#361's, verbatim) for the museums it reads, `cleveland_mentions` and
    `walters_mentions` for theirs, in one order and with one set of diagnostics. Without Cleveland
    or Walters records it gives exactly what `extract_mentions` gives."""
    others = [row for row in canonical if row["source_museum"] not in ADDED_READERS]
    found, diagnostics = extract_mentions(others, raw_indexes)
    added = [row for row in canonical if row["source_museum"] in ADDED_READERS]
    if not added:
        return found, diagnostics
    missed = Counter(diagnostics["royal_cues_without_syntactic_candidate"])
    for artifact in added:
        museum = artifact["source_museum"]
        rows, misses = ADDED_READERS[museum](artifact, raw_indexes[museum][artifact["source_id"]])
        found += rows
        missed.update(misses)
    found.sort(key=lambda row: (
        row["artifact_id"], row["entity_type"], row["field_path"], row["span_start"],
        row["span_end"], row["extraction_method"], row["mention_id"],
    ))
    ids = [row["mention_id"] for row in found]
    if len(ids) != len(set(ids)):
        raise ValueError("mention identifiers are not unique")
    return found, {
        **diagnostics,
        "records_scanned": len(canonical),
        "records_with_at_least_one_mention": len({row["artifact_id"] for row in found}),
        "mentions": len(found),
        "mentions_by_museum": dict(sorted(Counter(row["museum"] for row in found).items())),
        "mentions_by_entity_type": dict(sorted(Counter(row["entity_type"] for row in found).items())),
        "royal_cues_without_syntactic_candidate": dict(sorted(missed.items())),
    }
