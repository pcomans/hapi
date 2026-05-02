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
- **2026-04-21:** Leprohon 2013 *The Great Name* (`sources/leprohon-2013-titulary/`) is promoted to **primary titulary authority** (395 rows across Dyn 0 → Ptolemaic). Pharaoh.se is **demoted to secondary cross-validator**. Where Leprohon's canonical prenomen disagrees with pharaoh.se's primary, Leprohon wins. Pharaoh.se variants are retained as aliases when Leprohon attests them, flagged for review otherwise.
- **2026-04-25 (post-Beckerath landing):** Pharaoh.se's role is **further narrowed to gap-fill secondary**. Beckerath 1997 (`sources/beckerath-1997-chronologie/`, 172 rows Dyn 0–31) supersedes pharaoh.se's `chronologies` dict. Phase-A `build_rulers.py` consumer guidance:
  - **Titulary** → Leprohon first; pharaoh.se only when Leprohon is silent.
  - **Chronology** → plural-named-chronologies map driven by Beckerath 1997 (lead) / HKW 2006 (fallback) / Kitchen 1996 (Dyn 21–26 finer grain). Drop pharaoh.se's `chronologies` from the merge **for rulers covered by these primary sources (Dyn 0–31, ending 332 BCE)** — pharaoh.se is second-hand to the primary sources it cites (Beckerath, Shaw, etc.), and the project now uses more direct scholarly authorities. **Argead, Ptolemaic, Roman-emperor, and unplaced-king rows retain their chronology from pharaoh.se** — Beckerath stops at 332 BCE and no other Phase-0 source covers the post-Alexander periods or ephemeral kings until a Roman-period source (Kienast + Beckerath 1999, deferred post-v0 per issue #166; B&R 2004 evaluated 2026-05-02 and rejected as wrong source-shape) and an Argead/Ptolemaic chronology source land.
  - **Roman emperors (30 rows)** → entirely from pharaoh.se. The only on-disk source for the imperial period; this is the dealbreaker that prevents an outright drop.
  - **Argead / Ptolemaic (19 rows)** → Leprohon Ch X chunk 14 wins; pharaoh.se as cross-validator + `alt_labels` source.
  - **Unplaced kings / Abydos Dyn / Dyn-13–14 long-tail (~11+ rows)** → pharaoh.se where no other source attests the king at all, until Leprohon's Abydos-Dynasty / problematic-king sections cover them or the project accepts an MVP gap.
  - **`alt_labels`** → pharaoh.se where Leprohon doesn't carry the variant (Greek/Latin variant graph).
  - **Predecessor/successor chains** → derive from `sequence_in_dynasty` ordering across Beckerath/Leprohon/Ryholt/Kitchen; pharaoh.se chains as cross-validation only.

  The committed 381-row pharaoh.se `reconciled.jsonl` does NOT shrink — Phase-A consumers simply read fewer of its fields. **End state target:** drop pharaoh.se entirely once a Roman-emperor authority lands (Kienast + Beckerath 1999 once we pick this up post-v0 per issue #166; B&R 2004 evaluated 2026-05-02 and rejected as wrong source-shape) AND the unplaced-king long-tail is curated into Leprohon or accepted as a documented MVP gap. Decision audit trail in issue #112 (closed 2026-04-25); post-v0 Roman-period plan in issue #166.
- The `wikipedia-ptolemaic` source (24-row Ptolemaic supplement, PR #19) was dropped 2026-04-23. Its coverage was redundant with pharaoh.se + Leprohon 2013 chunk 14, and the directory committed no raw snapshots, revision IDs, retrieval dates, fetch script, or per-row URLs — a Rule-1 violation surfaced by the 2026-04-23 sweep audit. The 3 Ptolemaic queens unique to Wikipedia-Ptolemaic (Cleopatra III, Cleopatra V, Berenice IV) are planned for D&H Ch 5 House-of-Ptolemy; Cleopatra VII and Berenice III are already covered by Leprohon chunk 14 at `leprohon-33.14` / `leprohon-33.12`.
- Hornung/Krauss/Warburton (HKW) is copyrighted. We transcribe only the chronology table under fair use for academic reference. The full text is not redistributed
- Re-acquisition of any source must update the `retrieved` field and the raw file together
- Structural test enforcement means a missing or stale `_source` block is a CI failure
