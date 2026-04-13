# ADR-012: Authoritative Sources for Egyptian Chronology, Rulers, and Sites

## Status
Accepted

## Context
Constitutional rule 6 requires that ruler names, dynasty labels, and site names come from authority files in `pipeline/pipeline/authority/`, with no string literals for domain values in mapper code. The rule itself is established, but the *sources* for those authority files were never specified — leaving open the path of populating them from LLM training data, ad-hoc Wikipedia scraping, or someone's recollection. None of those are auditable or defensible to an Egyptologist.

Egyptology has well-established academic and digital-humanities reference works for each domain we need to model. Picking from them deliberately, with citations committed to the repo, forecloses sloppy sourcing forever.

## Decision

Every authority file in `pipeline/pipeline/authority/` is built from a citable source committed to the repo. Four sources, one per domain:

| Authority | Primary source | License |
|---|---|---|
| Periods | Hornung, E., Krauss, R., & Warburton, D. A. (Eds.). (2006). *Ancient Egyptian Chronology*. Brill. | Copyrighted (fair use for chronological reference) |
| Dynasties | Same Hornung/Krauss/Warburton chronology table | Copyrighted (fair use) |
| Rulers | Wikidata SPARQL dump (entities of class "pharaoh of ancient Egypt"), cross-checked against Beckerath, J. von. (1999). *Handbuch der ägyptischen Königsnamen* (2nd ed.). Philipp von Zabern. | Wikidata: CC0; Beckerath: copyrighted (fair use for cross-check) |
| Sites | iDAI.gazetteer (German Archaeological Institute), REST API at `gazetteer.dainst.org` | CC BY 4.0 |

### Layout

```
pipeline/pipeline/authority/
  sources/                          # raw downloads, never edited
    hkw-chronology-2006.md          # transcribed table with page citations
    wikidata-rulers.json            # SPARQL query result
    idai-gazetteer/raw.json         # iDAI.gazetteer API responses
  periods.json                      # curated, alias-enriched
  dynasties.json
  rulers.json
  sites.json
```

### Mandatory `_source` block

Every curated authority file has an `_source` block at the top:

```json
{
  "_source": {
    "citation": "Hornung, E., Krauss, R., & Warburton, D. A. (Eds.). (2006). Ancient Egyptian Chronology. Brill.",
    "retrieved": "2026-04-12",
    "license": "Copyrighted — fair use for chronological reference",
    "raw_file": "sources/hkw-chronology-2006.md"
  },
  "entries": [...]
}
```

A structural test (to be added in `pipeline/tests/test_structure.py` as part of MVP task 3.2) will verify that every authority file has a non-empty `_source` block and that the referenced raw file exists.

## Consequences
- Authority data is auditable: every entry traces back to a citation
- Adding a new entry requires either an existing source or adding a new one with citation — there is no path for "the LLM said so"
- iDAI.gazetteer is the sole site authority, replacing the originally planned TM Places + Theban Mapping Project. TM Places was dropped because its papyrological bias (built from documentary attestations) means pharaonic sites are subsumed under coarse toponyms — e.g., Deir el-Bahari, Valley of the Kings, and Medinet Habu are all lumped into TM Geo 1341 ("Memnoneia"), making them unusable for resolving museum provenance strings. TMP was dropped because it is offline and has restrictive copyright. See `docs/site-authority-research.md` for the full evaluation of five candidate sources
- Beckerath is the citation backbone for ruler titulary. Wikidata provides Q-IDs and alternate spellings but is not trusted for canonical names — Wikidata blends Greek, Anglicized, and Egyptian transliterations (see ADR-016)
- Hornung/Krauss/Warburton (HKW) is copyrighted. We transcribe only the chronology table under fair use for academic reference. The full text is not redistributed
- Re-acquisition of any source must update the `retrieved` field and the raw file together
- Structural test enforcement means a missing or stale `_source` block is a CI failure
