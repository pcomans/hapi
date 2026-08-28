#!/usr/bin/env python3
"""Materialize the frozen, provisional SILVER web review.

The judgments below were authored only after ``freeze_review_sample.py`` had
written and hashed the review sample.  They are evaluation evidence, never
gold truth or human validation, and are not consumed by the resolver.
"""

from __future__ import annotations

import collections
import csv
import hashlib
import json
import os
from pathlib import Path


OUT = Path(os.environ.get("HAPI_EVAL_OUT", "/tmp/hapi-linkability-mvp"))
LABEL = "PROVISIONAL SILVER WEB REVIEW — not gold truth and not human validation"


def cite(url: str, source_type: str, note: str, access: str = "direct_url") -> dict:
    return {
        "url": url,
        "source_type": source_type,
        "evidence_note": note,
        "access_note": access,
    }


PHARAOH = {
    "akhenaten": "https://pharaoh.se/ancient-egypt/pharaoh/amenhotep-iv/",
    "sobekhotep_iii": "https://pharaoh.se/ancient-egypt/pharaoh/sobekhotep-iii/",
    "osorkon_i": "https://pharaoh.se/ancient-egypt/pharaoh/osorkon-i/",
    "amenhotep_iii": "https://pharaoh.se/ancient-egypt/pharaoh/amenhotep-iii/",
    "xerxes_i": "https://pharaoh.se/ancient-egypt/pharaoh/xerxes-i/",
    "amenemhat_i": "https://pharaoh.se/ancient-egypt/pharaoh/amenemhat-i/",
    "khafra": "https://pharaoh.se/ancient-egypt/pharaoh/khafra/",
    "ahmose_i": "https://pharaoh.se/ancient-egypt/pharaoh/ahmose-i/",
    "ramesses_ii": "https://pharaoh.se/ancient-egypt/pharaoh/ramesses-ii/",
    "index": "https://pharaoh.se/ancient-egypt/pharaohs/",
}


def idai(identifier: str) -> str:
    return f"https://gazetteer.dainst.org/doc/{identifier}.html"


# resolution_judgment exhaustively partitions all frozen rows:
# supported / false_link / underresolved / correct_abstention / not_applicable.
J = {
    "review-001": dict(
        span_judgment="supported", entity_type_judgment="supported",
        artifact_relation_judgment="supported", resolution_judgment="underresolved",
        expected_identity="Akhenaten (Amenhotep IV)", accepted_target_ids=[],
        failure_categories=["incomplete_reconciliation"],
        evidence_note="The museum identifies the shabti as Akhenaten; the two current graph units denote one ruler and should not force an ambiguous result.",
        extra_citations=[cite(PHARAOH["akhenaten"], "source-referenced ruler authority", "Lists Akhenaten as an alternate name of Amenhotep IV; this is a current graph source, but is self-published and therefore corroborative rather than sole evidence.")],
    ),
    "review-002": dict(
        span_judgment="supported", entity_type_judgment="supported",
        artifact_relation_judgment="supported", resolution_judgment="underresolved",
        expected_identity="Sobekhotep III", accepted_target_ids=[],
        failure_categories=["incomplete_reconciliation"],
        evidence_note="The title names Sobekhotep III; two unreconciled current source units create artificial ambiguity.",
        extra_citations=[cite(PHARAOH["sobekhotep_iii"], "source-referenced ruler authority", "Independent current graph source page for Sobekhotep III, with cited titulary references.")],
    ),
    "review-003": dict(
        span_judgment="supported", entity_type_judgment="unsupported",
        artifact_relation_judgment="supported_person_but_wrong_authority_type", resolution_judgment="false_link",
        expected_identity="Queen/God's Wife Maatkare, daughter of Painedjem I (not Hatshepsut)", accepted_target_ids=[],
        failure_categories=["homonym", "entity_typing"],
        evidence_note="A title cue 'Queen' was treated as ruler evidence and the bare homonym Maatkare was linked to Hatshepsut. Institutional comparanda distinguish Dynasty-21 Maatkare from Hatshepsut's throne name.",
        extra_citations=[
            cite("https://www.metmuseum.org/art/collection/search/545948", "museum object page", "Met object page identifies the Dynasty-21 God's Wife Maatkare as daughter of Painedjem I."),
            cite("https://www.metmuseum.org/art/collection/search/544450", "museum object page", "Met page states that Hatshepsut used Maatkare as her throne name, documenting the homonym."),
        ],
    ),
    "review-004": dict(
        span_judgment="supported", entity_type_judgment="supported",
        artifact_relation_judgment="supported", resolution_judgment="supported",
        expected_identity="Osorkon I", accepted_target_ids=["cluster-beckerath-22.02"],
        failure_categories=[], evidence_note="Museum title and current source-referenced authority agree on Osorkon I.",
        extra_citations=[cite(PHARAOH["osorkon_i"], "source-referenced ruler authority", "Current graph source page identifies Osorkon I and cites Beckerath and Leprohon.")],
    ),
    "review-005": dict(
        span_judgment="minor_boundary_error", entity_type_judgment="supported",
        artifact_relation_judgment="uncertain", resolution_judgment="correct_abstention",
        expected_identity=None, accepted_target_ids=[], failure_categories=["boundary_punctuation"],
        evidence_note="The museum title itself marks Cleopatra VII as tentative; abstention is appropriate. The extracted span retains an opening parenthesis.", extra_citations=[],
    ),
    "review-006": dict(
        span_judgment="supported", entity_type_judgment="unsupported",
        artifact_relation_judgment="supported_person_but_wrong_authority_type", resolution_judgment="correct_abstention",
        expected_identity="Queen Henuttawy (royal person; not established here as a ruler)", accepted_target_ids=[],
        failure_categories=["entity_typing", "authority_scope"],
        evidence_note="The museum title supports the person mention, but a generic Queen cue is insufficient to type every queen as a ruler. No ruler link is accepted.", extra_citations=[],
    ),
    "review-007": dict(
        span_judgment="supported", entity_type_judgment="supported",
        artifact_relation_judgment="uncertain", resolution_judgment="underresolved",
        expected_identity="Amunhotep III as one explicit alternative, not a certain artifact identification", accepted_target_ids=[],
        failure_categories=["uncertainty_parser", "missing_alias"],
        evidence_note="Brooklyn explicitly gives an Amun-Re versus Amunhotep III alternative. The adapter missed both the 'or' hedge and the Amunhotep/Amenhotep spelling relation; it should preserve a candidate without asserting a link.",
        extra_citations=[cite(PHARAOH["amenhotep_iii"], "source-referenced ruler authority", "Current graph source page for Amenhotep III; museum spelling remains an uncommitted alias gap.")],
    ),
    "review-008": dict(
        span_judgment="supported", entity_type_judgment="supported",
        artifact_relation_judgment="supported", resolution_judgment="correct_abstention",
        expected_identity=None, accepted_target_ids=[], failure_categories=["place_granularity_homonym"],
        evidence_note="The string contains Fayum but does not by itself select the city versus oasis current targets; retaining both candidates is safer than guessing.",
        extra_citations=[cite(idai("2042846"), "institutional gazetteer", "iDAI city target carrying Fayum as an alias."), cite(idai("2751193"), "institutional gazetteer", "iDAI oasis target also carrying Fayum as an alias.")],
    ),
    "review-009": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="supported", expected_identity="Saqqara", accepted_target_ids=["idai:2042907"],
        failure_categories=[], evidence_note="The museum place and iDAI's Saqqara archaeological/populated-place record agree.",
        extra_citations=[cite(idai("2042907"), "institutional gazetteer", "DAI record gives Saqqara as an English alias of Saqqāra and types it as an archaeological place.")],
    ),
    "review-010": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="supported", expected_identity="Harageh (Haraga)", accepted_target_ids=["idai:2751316"],
        failure_categories=[], evidence_note="Haraga is a committed alias on the iDAI Harageh target.",
        extra_citations=[cite(idai("2751316"), "institutional gazetteer", "DAI record for Harageh/Haraga.")],
    ),
    "review-011": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="correct_abstention", expected_identity="Egypt", accepted_target_ids=[],
        failure_categories=["missing_current_target"],
        evidence_note="Egypt is valid structured museum evidence. The live iDAI Egypt root exists but is absent from the current committed 1,000-row representation, so it was correctly not imported at evaluation time.",
        extra_citations=[cite("https://gazetteer.dainst.org/place/2042786", "institutional gazetteer", "Live DAI Egypt root; cited only to document the committed-target omission, not injected into matching.")],
    ),
    "review-012": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="correct_abstention", expected_identity="Samayna", accepted_target_ids=[],
        failure_categories=["missing_current_target"],
        evidence_note="Samayna is a genuine museum place value but no current committed site target matched it.",
        extra_citations=[cite("https://www.metmuseum.org/art/collection/search/558188", "museum object page", "Independent Met object provenance names Samayna, corroborating that this is a place rather than noise.")],
    ),
    "review-013": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="correct_abstention", expected_identity="Local tomb D303 at Abydos", accepted_target_ids=[],
        failure_categories=["missing_current_target", "tomb_register_scope"],
        evidence_note="The structured Brooklyn location explicitly names Tomb D303 at Abydos. Current PM targets cover committed Theban/Memphite rows, not this local Abydos tomb code.", extra_citations=[],
    ),
    "review-014": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported_context",
        resolution_judgment="underresolved", expected_identity="Akhenaten (Amenhotep IV)", accepted_target_ids=[],
        failure_categories=["incomplete_reconciliation"],
        evidence_note="Harvard's label uses Akhenaten as historical context for this Amarna relief. Two current graph units denote one identity and should be reconciled.",
        extra_citations=[cite(PHARAOH["akhenaten"], "source-referenced ruler authority", "Lists Akhenaten as Amenhotep IV's alternate name.")],
    ),
    "review-015": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="unsupported_reference_only",
        resolution_judgment="false_link", expected_identity="Amasis is mentioned only in a footnote about MFA Boston 36.337", accepted_target_ids=[],
        failure_categories=["reference_only_false_link"],
        evidence_note="The span is real, but it describes a different museum object used as a comparison. Linking the Harvard artifact itself to Amasis is unsupported.",
        extra_citations=[],
    ),
    "review-016": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="supported", expected_identity="Arsinoe II", accepted_target_ids=["leprohon-leprohon-33.02a"],
        failure_categories=[], evidence_note="The museum title explicitly identifies Queen Arsinoe II and the current Leprohon source node has the same display identity.", extra_citations=[],
    ),
    "review-017": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="uncertain",
        resolution_judgment="correct_abstention", expected_identity=None, accepted_target_ids=[], failure_categories=[],
        evidence_note="Harvard qualifies the dating as 'probably reign of Pepi II'; abstention preserves the museum's uncertainty.",
        extra_citations=[cite(PHARAOH["index"], "source-referenced ruler authority", "Current source index includes Pepi II; used only as corroboration because the artifact relation remains uncertain.")],
    ),
    "review-018": dict(
        span_judgment="unsupported_overlapping_boundary", entity_type_judgment="supported",
        artifact_relation_judgment="unsupported_duplicate_mention", resolution_judgment="not_applicable",
        expected_identity="Ramesses II is captured by the separate maximal span in review-019", accepted_target_ids=[],
        failure_categories=["overlapping_extraction"],
        evidence_note="'King Rameses' is a truncated overlapping extraction from 'King Rameses II'; it must not form a separate artifact mention.", extra_citations=[],
    ),
    "review-019": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported_context",
        resolution_judgment="underresolved", expected_identity="Ramesses II", accepted_target_ids=[],
        failure_categories=["missing_alias", "incomplete_reconciliation"],
        evidence_note="Harvard's label explicitly says Rameses II. Current authority uses Ramesses II and still has unreconciled source units; the one-m spelling variant is missing.",
        extra_citations=[cite(PHARAOH["ramesses_ii"], "source-referenced ruler authority", "Current graph source page for Ramesses II; its dynasty index also lists Rameses II as an alternate spelling.")],
    ),
    "review-020": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="correct_abstention", expected_identity=None, accepted_target_ids=[],
        failure_categories=["place_granularity_homonym"],
        evidence_note="Harvard's place hierarchy supports a Fayum location but does not uniquely distinguish the current city and oasis records.",
        extra_citations=[cite(idai("2042846"), "institutional gazetteer", "iDAI city candidate."), cite(idai("2751193"), "institutional gazetteer", "iDAI oasis candidate.")],
    ),
    "review-021": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="supported", expected_identity="Fustat", accepted_target_ids=["idai:2379568"],
        failure_categories=[], evidence_note="Harvard's creation place and iDAI Fustat target agree.",
        extra_citations=[cite(idai("2379568"), "institutional gazetteer", "DAI archaeological-site record for Fustat.")],
    ),
    "review-022": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="supported", expected_identity="Asyut", accepted_target_ids=["idai:2042814"],
        failure_categories=[], evidence_note="Asyut is a committed alias of iDAI Asyūt.",
        extra_citations=[cite(idai("2042814"), "institutional gazetteer", "DAI record for Asyūt/Asyut.")],
    ),
    "review-023": dict(
        span_judgment="supported", entity_type_judgment="supported_geographic_container", artifact_relation_judgment="supported",
        resolution_judgment="correct_abstention", expected_identity="Africa (broad geographic container)", accepted_target_ids=[],
        failure_categories=["authority_geographic_scope"],
        evidence_note="Africa is genuinely present in Harvard's place hierarchy, but the current Egypt-focused site extract does not offer a suitable canonical target. No link is accepted.", extra_citations=[],
    ),
    "review-024": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="correct_abstention", expected_identity="Cerveteri in Etruria", accepted_target_ids=[],
        failure_categories=["authority_geographic_scope"],
        evidence_note="The Harvard place is explicit but outside the current Egypt-focused 1,000-row iDAI representation. This is an authority-scope gap, not absence of museum evidence.", extra_citations=[],
    ),
    "review-025": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="not_applicable", expected_identity="Metropolitan Museum of Art excavation activity", accepted_target_ids=[],
        failure_categories=["absent_canonical_entity_type"],
        evidence_note="The explicit excavation string is valid, but no current committed excavation authority target exists.", extra_citations=[],
    ),
    "review-026": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="not_applicable", expected_identity="Garstang excavation campaign, 1907", accepted_target_ids=[],
        failure_categories=["absent_canonical_entity_type"],
        evidence_note="The explicit excavation string is valid, but no current committed excavation authority target exists.", extra_citations=[],
    ),
    "review-027": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="underresolved", expected_identity="Amenhotep III", accepted_target_ids=[],
        failure_categories=["incomplete_reconciliation"],
        evidence_note="The structured Met reign is unambiguous; duplicate current authority units produce artificial ambiguity.",
        extra_citations=[cite(PHARAOH["amenhotep_iii"], "source-referenced ruler authority", "Current graph source page for Amenhotep III.")],
    ),
    "review-028": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="underresolved", expected_identity="Xerxes I", accepted_target_ids=[],
        failure_categories=["incomplete_reconciliation"],
        evidence_note="The structured Met reign is unambiguous; duplicate current authority units produce artificial ambiguity.",
        extra_citations=[cite(PHARAOH["xerxes_i"], "source-referenced ruler authority", "Current graph source page for Xerxes I.")],
    ),
    "review-029": dict(
        span_judgment="supported", entity_type_judgment="supported_multi_entity", artifact_relation_judgment="supported_range",
        resolution_judgment="correct_abstention", expected_identity="Reign range from Djedkare Isesi through Unis", accepted_target_ids=[],
        failure_categories=[], evidence_note="The Met value denotes a range across two rulers. Not collapsing it to one node is correct.",
        extra_citations=[cite(PHARAOH["index"], "source-referenced ruler authority", "Current source index lists Djedkare Isesi and Unis as separate rulers.")],
    ),
    "review-030": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="supported", expected_identity="Amenemhat I", accepted_target_ids=["pharaoh_se-Amenemhat-I"],
        failure_categories=[], evidence_note="The explicit Met reign and current source node agree.",
        extra_citations=[cite(PHARAOH["amenemhat_i"], "source-referenced ruler authority", "Current graph source page for Amenemhat I.")],
    ),
    "review-031": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="supported", expected_identity="Khafra (Chephren)", accepted_target_ids=["cluster-beckerath-04.04"],
        failure_categories=[], evidence_note="Chephren is a documented alias of Khafra and the Met reign refers to that ruler.",
        extra_citations=[cite(PHARAOH["khafra"], "source-referenced ruler authority", "Source page explicitly lists Chephren as an alternate name of Khafra and cites Beckerath/Leprohon.")],
    ),
    "review-032": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="uncertain_temporal_bound",
        resolution_judgment="correct_abstention", expected_identity=None, accepted_target_ids=[], failure_categories=[],
        evidence_note="'Late reign of Mentuhotep II or later' is an open temporal bound, not a unique ruler assertion. Abstention is correct.", extra_citations=[],
    ),
    "review-033": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="uncertain",
        resolution_judgment="correct_abstention", expected_identity=None, accepted_target_ids=[], failure_categories=[],
        evidence_note="The value explicitly says 'Possibly Senwosret I'; abstention is correct.", extra_citations=[],
    ),
    "review-034": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="underresolved", expected_identity="Ahmose I in Dynasty 18", accepted_target_ids=["cluster-beckerath-18.01"],
        failure_categories=["context_disambiguation", "missing_short_alias"],
        evidence_note="The bare reign value needs the record's Dynasty-18 context to select Ahmose I. The current adapter intentionally did not add this contextual inference.",
        extra_citations=[cite(PHARAOH["ahmose_i"], "source-referenced ruler authority", "Current graph source page identifies Ahmose I as the first Dynasty-18 pharaoh.")],
    ),
    "review-035": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="underresolved", expected_identity="Ramesses II", accepted_target_ids=[],
        failure_categories=["qualifier_parser", "incomplete_reconciliation"],
        evidence_note="A deterministic typed parser could separate the year-21 qualifier from Ramesses II. Current authority then still has two unreconciled source units.",
        extra_citations=[cite(PHARAOH["ramesses_ii"], "source-referenced ruler authority", "Current graph source page for Ramesses II.")],
    ),
    "review-036": dict(
        span_judgment="supported", entity_type_judgment="supported_multi_entity", artifact_relation_judgment="supported_joint_reign",
        resolution_judgment="correct_abstention", expected_identity="Hatshepsut and Thutmose III as two entities", accepted_target_ids=[],
        failure_categories=["multi_entity_parser"],
        evidence_note="The adapter safely declined to collapse a joint reign to one node, but classified the structured value as unparsed rather than emitting two typed mentions.",
        extra_citations=[cite("https://www.metmuseum.org/art/collection/search/559833", "museum object page", "Met institutional page describes the joint reign and Hatshepsut's Maatkare name.")],
    ),
    "review-037": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="correct_abstention", expected_identity=None, accepted_target_ids=[],
        failure_categories=["place_granularity_homonym"],
        evidence_note="The explicit region value is Fayum while the current target set contains a city and an oasis with the same alias. Field hierarchy suggests a future typed disambiguator, but this SILVER review abstains.",
        extra_citations=[cite(idai("2042846"), "institutional gazetteer", "iDAI city candidate."), cite(idai("2751193"), "institutional gazetteer", "iDAI oasis candidate.")],
    ),
    "review-038": dict(
        span_judgment="minor_boundary_error", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="underresolved", expected_identity="Ombos/Nubt at Naqada", accepted_target_ids=["idai:2751407"],
        failure_categories=["context_disambiguation", "boundary_punctuation"],
        evidence_note="The full field 'Naqada (Nubt, Ombos)' selects iDAI's Ombos/Nubt record rather than Kom Ombo. The isolated span retained a closing parenthesis and discarded disambiguating context.",
        extra_citations=[cite(idai("2751407"), "institutional gazetteer", "DAI Ombos target carries Nubt/Nbwt aliases."), cite(idai("2101017"), "institutional gazetteer", "DAI Kom Ombo target documents the competing Ombos alias.")],
    ),
    "review-039": dict(
        span_judgment="supported", entity_type_judgment="supported_broad_region", artifact_relation_judgment="supported",
        resolution_judgment="supported", expected_identity="Upper Egypt", accepted_target_ids=["idai:2379505"],
        failure_categories=[], evidence_note="Upper Egypt is an exact alias of iDAI Aegyptus Superior. This is valid but broad connectivity evidence.",
        extra_citations=[cite(idai("2379505"), "institutional gazetteer", "DAI administrative/archaeological-area record for Upper Egypt.")],
    ),
    "review-040": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="supported", expected_identity="Buhen", accepted_target_ids=["idai:2751172"],
        failure_categories=[], evidence_note="The Met subregion and iDAI Buhen archaeological-site target agree.",
        extra_citations=[cite(idai("2751172"), "institutional gazetteer", "DAI record for Buhen/Bouhen.")],
    ),
    "review-041": dict(
        span_judgment="supported", entity_type_judgment="supported_broad_country", artifact_relation_judgment="supported",
        resolution_judgment="correct_abstention", expected_identity="Egypt", accepted_target_ids=[],
        failure_categories=["missing_current_target"],
        evidence_note="Egypt is explicit in the museum field. The live DAI root was not in the committed evaluation target set, so no runtime target was invented.",
        extra_citations=[cite("https://gazetteer.dainst.org/place/2042786", "institutional gazetteer", "Live DAI Egypt root documenting the current committed-target gap.")],
    ),
    "review-042": dict(
        span_judgment="supported", entity_type_judgment="supported_local_locus", artifact_relation_judgment="supported",
        resolution_judgment="correct_abstention", expected_identity="Local findspot Pit 219", accepted_target_ids=[],
        failure_categories=["missing_target_granularity"],
        evidence_note="Pit 219 is valid local findspot evidence, but the current site authority representation has no artifact-local locus node at this granularity.", extra_citations=[],
    ),
    "review-043": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="supported", expected_identity="Theban Tomb 280, tomb of Meketre", accepted_target_ids=["pm_theban:TT280"],
        failure_categories=[], evidence_note="The museum page identifies Meketre's tomb as TT 280; whitespace normalization preserves the same PM code.",
        extra_citations=[cite("https://www.griffith.ox.ac.uk/topbib/pdf/pm1-1.pdf", "scholarly institutional catalogue", "Official Griffith Institute Porter–Moss volume I/1 used by the committed tomb register.")],
    ),
    "review-044": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="supported", expected_identity="Valley of the Queens tomb 55, Amenherkhepeshef", accepted_target_ids=["pm_theban:QV55"],
        failure_categories=[], evidence_note="The museum page explicitly identifies the Tomb of Amenherkhepeshef as QV 55; whitespace normalization preserves the PM code.",
        extra_citations=[cite("https://www.griffith.ox.ac.uk/topbib/pdf/pm1-2.pdf", "scholarly institutional catalogue", "Official Griffith Institute Porter–Moss volume I/2 used by the committed tomb register.")],
    ),
    "review-045": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="correct_abstention", expected_identity="Local Met excavation tomb MMA 60", accepted_target_ids=[],
        failure_categories=["missing_current_target", "tomb_register_scope"],
        evidence_note="The museum's local tomb identifier is valid, but it is not a TT/QV/KV-style row in the current committed PM representation.", extra_citations=[],
    ),
    "review-046": dict(
        span_judgment="supported", entity_type_judgment="supported", artifact_relation_judgment="supported",
        resolution_judgment="correct_abstention", expected_identity="Local cemetery tomb R99S", accepted_target_ids=[],
        failure_categories=["missing_current_target", "tomb_register_scope"],
        evidence_note="The museum's local tomb identifier is valid, but the current PM representation does not contain this cemetery-local code.", extra_citations=[],
    ),
}


SEARCH_LOG = {
    "label": LABEL,
    "review_date_utc": "2026-08-28",
    "method": "Searches were executed only after the sample was frozen. Direct museum pages, DAI records, Griffith Institute/Porter–Moss volumes, and source-referenced ruler pages were used. Wikipedia/Wikidata were not used as sole authority and no adjudication was fed back into resolver logic.",
    "limitations": [
        "Harvard object pages were blocked to the web-search client by robots.txt. Their direct institutional URLs and the verified raw Harvard API payload in the corpus remain cited; those cases are not represented as independently re-fetched pages.",
        "pharaoh.se is a source-referenced but self-published current graph input. It is used as corroboration and graph-source documentation, not as sole gold authority.",
        "The SILVER sample is stratified and deterministic, not a probability sample; fractions are descriptive only.",
    ],
    "query_groups": [
        {"purpose": "Brooklyn ruler/object checks", "queries": ["site:brooklynmuseum.org/opencollection/objects/3317 Akhenaten", "site:brooklynmuseum.org/opencollection/objects/3854 Amunhotep III", "site:brooklynmuseum.org/opencollection/objects/3635 Osorkon I"]},
        {"purpose": "Maatkare homonym check", "queries": ["site:metmuseum.org/art/collection/search/545948 Maatkare Painedjem", "site:metmuseum.org Maatkare Hatshepsut throne name"]},
        {"purpose": "Harvard object checks", "queries": ["site:harvardartmuseums.org/collections/object/291048 Charioteers Akhenaten", "site:harvardartmuseums.org/collections/object/289668 Arsinoe II", "site:harvardartmuseums.org/collections/object/354559 Amasis sistrum"], "result": "robots.txt blocked direct retrieval"},
        {"purpose": "DAI site target checks", "queries": ["site:gazetteer.dainst.org/doc/2042907 Saqqara", "site:gazetteer.dainst.org Egypt 2042786"]},
        {"purpose": "Porter–Moss tomb checks", "queries": ["site:griffith.ox.ac.uk Topographical Bibliography TT 280 Meketre", "site:griffith.ox.ac.uk Topographical Bibliography QV 55 Amenherkhepeshef"]},
        {"purpose": "Ruler identity/alias checks", "queries": ["site:pharaoh.se Amenhotep IV Akhenaten", "site:pharaoh.se Sobekhotep III", "site:pharaoh.se Khafra Chephren", "site:pharaoh.se Ramesses II Rameses II", "site:pharaoh.se Ahmose I", "site:pharaoh.se Xerxes I"]},
        {"purpose": "Met tomb pages", "queries": ["site:metmuseum.org/art/collection/search/544125 TT 280 Meketre", "site:metmuseum.org/art/collection/search/548357 QV 55 Amenherkhepeshef"]},
        {"purpose": "Missing-place corroboration", "queries": ["site:metmuseum.org Samayna Egypt"]},
    ],
    "representative_audited_urls": [
        "https://opencollection.brooklynmuseum.org/objects/3317",
        "https://www.brooklynmuseum.org/opencollection/objects/3854",
        "https://www.metmuseum.org/art/collection/search/545948",
        "https://gazetteer.dainst.org/doc/2042907.html",
        "https://gazetteer.dainst.org/place/2042786",
        "https://topbib.griffith.ox.ac.uk/",
        "https://www.griffith.ox.ac.uk/topbib/pdf/pm1-1.pdf",
        "https://www.metmuseum.org/art/collection/search/548357",
        "https://pharaoh.se/ancient-egypt/pharaoh/khafra/",
        "https://pharaoh.se/ancient-egypt/pharaoh/amenhotep-iii/",
    ],
}


def ratio(numerator: int, denominator: int) -> dict:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "fraction": numerator / denominator if denominator else None,
    }


def main() -> None:
    sample_path = OUT / "review_sample.json"
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    sample_ids = [row["sample_id"] for row in sample]
    if set(sample_ids) != set(J) or len(sample_ids) != len(J):
        raise SystemExit(f"judgment/sample mismatch: sample={len(sample_ids)} judgments={len(J)}")

    rows = []
    for source in sample:
        judgment = dict(J[source["sample_id"]])
        extra = judgment.pop("extra_citations")
        museum_citation = cite(
            source["source_url"],
            "museum object page",
            f"Direct institutional object record underlying {source['field_path']}={source['field_value']!r}.",
            "direct URL; value also verified in the unpacked museum raw payload",
        )
        rows.append({
            "label": LABEL,
            "sample_id": source["sample_id"],
            "museum": source["museum"],
            "artifact_id": source["artifact_id"],
            "artifact_title": source["artifact_title"],
            "entity_type": source["entity_type"],
            "system_status": source["status"],
            "field_path": source["field_path"],
            "field_value": source["field_value"],
            "mention_text": source["mention_text"],
            "target_ids": source["target_ids"],
            **judgment,
            "citations": [museum_citation, *extra],
        })

    # Every accepted identity/target must carry direct URL evidence.
    for row in rows:
        if row["expected_identity"] is not None or row["accepted_target_ids"]:
            if not row["citations"] or not all(c["url"].startswith("https://") for c in row["citations"]):
                raise SystemExit(f"accepted/expected identity lacks direct citations: {row['sample_id']}")

    (OUT / "review_adjudications.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUT / "web_search_log.json").write_text(
        json.dumps(SEARCH_LOG, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    fields = [
        "sample_id", "museum", "artifact_id", "entity_type", "system_status",
        "mention_text", "span_judgment", "entity_type_judgment",
        "artifact_relation_judgment", "resolution_judgment", "expected_identity",
        "accepted_target_ids", "failure_categories", "evidence_note", "citation_urls",
    ]
    with (OUT / "review_adjudications.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            printable = {key: row.get(key) for key in fields}
            printable["accepted_target_ids"] = "|".join(row["accepted_target_ids"])
            printable["failure_categories"] = "|".join(row["failure_categories"])
            printable["citation_urls"] = "|".join(c["url"] for c in row["citations"])
            writer.writerow(printable)

    resolution_counts = collections.Counter(row["resolution_judgment"] for row in rows)
    span_counts = collections.Counter(row["span_judgment"] for row in rows)
    relation_counts = collections.Counter(row["artifact_relation_judgment"] for row in rows)
    failure_counts = collections.Counter(cat for row in rows for cat in row["failure_categories"])
    resolved = [row for row in rows if row["system_status"] == "resolved"]
    supported_resolved = [row for row in resolved if row["resolution_judgment"] == "supported"]
    false_resolved = [row for row in resolved if row["resolution_judgment"] == "false_link"]

    by_museum = {}
    for museum in sorted({row["museum"] for row in rows}):
        group = [row for row in resolved if row["museum"] == museum]
        supported = sum(row["resolution_judgment"] == "supported" for row in group)
        by_museum[museum] = {"sampled_resolved": len(group), "supported": supported, "false_links": len(group) - supported, "support_fraction": ratio(supported, len(group))}
    by_entity = {}
    for entity in sorted({row["entity_type"] for row in rows}):
        group = [row for row in resolved if row["entity_type"] == entity]
        if group:
            supported = sum(row["resolution_judgment"] == "supported" for row in group)
            by_entity[entity] = {"sampled_resolved": len(group), "supported": supported, "false_links": len(group) - supported, "support_fraction": ratio(supported, len(group))}

    metrics = {
        "label": LABEL,
        "sample_sha256": hashlib.sha256(sample_path.read_bytes()).hexdigest(),
        "sample_size": len(rows),
        "design_warning": "Deterministic stratified review, deliberately over-sampling statuses/cells; descriptive review fractions are not population estimates.",
        "recall": {"reported": False, "reason": "The review frame contains extracted mentions only and has no defensible negative/no-mention denominator."},
        "resolution_judgment_counts": dict(sorted(resolution_counts.items())),
        "span_judgment_counts": dict(sorted(span_counts.items())),
        "artifact_relation_judgment_counts": dict(sorted(relation_counts.items())),
        "failure_category_counts": dict(sorted(failure_counts.items())),
        "sampled_resolved_support": {
            "sampled_resolved": len(resolved),
            "supported": len(supported_resolved),
            "false_links": len(false_resolved),
            "support_fraction": ratio(len(supported_resolved), len(resolved)),
            "false_link_fraction": ratio(len(false_resolved), len(resolved)),
            "not_an_estimated_precision": True,
        },
        "sampled_resolved_support_by_museum": by_museum,
        "sampled_resolved_support_by_entity_type": by_entity,
    }
    (OUT / "review_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
