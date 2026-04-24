# ADR-012: Authoritative Sources for Egyptian Chronology, Rulers, and Sites

## Status
Accepted

## Context
Constitutional rule 7 requires that ruler names, dynasty labels, and site names come from authority files in `pipeline/pipeline/authority/`, with no string literals for domain values in mapper code. Constitutional rule 1 (work like a scholar) further requires that every fact in those authority files trace to a committed, reproducibly-acquired raw source on disk — not to training-data recall. Together, these rules foreclose the path of populating authority files from LLM training data, uncommitted or non-reproducible Wikipedia extraction, or someone's recollection — none of which are auditable or defensible to an Egyptologist. Wikipedia-derived material *is* acceptable in principle when it is acquired reproducibly, committed as a raw artifact (snapshot or scraped HTML), and cited like any other Phase 0 input, but the initial Wikipedia-Ptolemaic source failed this bar and was dropped 2026-04-23 (see Consequences).

Egyptology has well-established academic and digital-humanities reference works for each domain we need to model. Picking from them deliberately, with citations committed to the repo, forecloses sloppy sourcing forever.

## Decision

Every authority file in `pipeline/pipeline/authority/` is built from a citable source committed to the repo. Four sources, one per domain:

| Authority | Primary source | License |
|---|---|---|
| Periods | Hornung, E., Krauss, R., & Warburton, D. A. (Eds.). (2006). *Ancient Egyptian Chronology*. Brill. | Copyrighted (fair use for chronological reference) |
| Dynasties | Same Hornung/Krauss/Warburton chronology table | Copyrighted (fair use) |
| Rulers | [Pharaoh.se](https://pharaoh.se/) by Peter Lundstrom — expert-curated royal titulary database (381 rulers, full five-name titulary, multiple scholarly chronologies, Gardiner codes, source citations). Scraped via Firecrawl. | CC BY 4.0 |
| Sites | iDAI.gazetteer (German Archaeological Institute), REST API at `gazetteer.dainst.org` | CC BY 4.0 |

### Layout

```
pipeline/pipeline/authority/
  sources/                          # raw downloads, never edited
    hkw-chronology-2006/            # transcribed chronology table with page citations
    pharaoh-se/                     # Firecrawl markdown scrape of pharaoh.se (381 rulers)
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
- Pharaoh.se replaces Wikidata as the ruler authority source. Wikidata had persistent quality issues (fictional characters, non-pharaohs, 0% prenomen coverage). Pharaoh.se provides expert-curated data with full five-name titulary sourced from Beckerath and other standard references. Pharaoh.se covers all Ptolemaic rulers with full titulary.
- The `wikipedia-ptolemaic` source (24-row Ptolemaic supplement, PR #19) was dropped 2026-04-23. Its coverage was redundant with pharaoh.se + Leprohon 2013 chunk 14, and the directory committed no raw snapshots, revision IDs, retrieval dates, fetch script, or per-row URLs — a Rule-1 violation surfaced by the 2026-04-23 sweep audit. The 5 Ptolemaic queens unique to Wikipedia-Ptolemaic (Cleopatra III/V/VII, Berenice III/IV) are planned for D&H Ch 5 House-of-Ptolemy.
- Hornung/Krauss/Warburton (HKW) is copyrighted. We transcribe only the chronology table under fair use for academic reference. The full text is not redistributed
- Re-acquisition of any source must update the `retrieved` field and the raw file together
- Structural test enforcement means a missing or stale `_source` block is a CI failure
