# ADR-016: Royal Display Name Standard Is Anglicized Nomen

## Status
Accepted

## Context
Pharaonic royal names are a notorious database problem. A king has a five-part titulary:

1. **Horus name** — proclaimed in a *serekh* frame
2. **Nebty name** ("Two Ladies") — under the protection of Wadjet and Nekhbet
3. **Golden Horus name**
4. **Prenomen** ("He of the Sedge and the Bee" / throne name) — written in the first cartouche
5. **Nomen** ("Son of Re" / birth name) — written in the second cartouche

The Prenomen and Nomen are the two most commonly attested on artifacts. A single ruler has multiple transliterations of each name across English, German, French, and Greek scholarship:

- Amenhotep III's Prenomen is *Nebmaatre*; his Nomen renders as *Amenhotep* (English), *Amenophis* (Greek), or *Nimmuria* (Akkadian/Amarna letters)
- Khufu is also *Cheops* (Greek) and *Suphis* (Manetho)
- Thutmose III is also *Tuthmosis III*, *Djehutymes III*, and (Prenomen) *Menkheperre*

Beckerath catalogs all of these. General-purpose reference sources often blend them inconsistently — treating a single arbitrary label as canonical produces nonsense like "Cheops" sitting next to "Amenhotep III" in the same UI list.

For an Egyptological database to be usable, the display name must be predictable, consistent, and survive a cartouche reading from any of the museums.

## Decision

Each ruler entity in `pipeline/pipeline/authority/rulers.json` has exactly one canonical display name: **the Anglicized Nomen** — the birth name in its modern English form.

- Khufu, not Cheops
- Khafre, not Khafra, not Chephren
- Menkaure, not Menkaura, not Mycerinus
- Amenhotep III, not Amenophis III, not Nimmuria
- Thutmose III, not Tuthmosis III, not Djehutymes III
- Senwosret I, not Senusret I, not Sesostris I
- Shabataka, not Shebitko
- Tantamani, not Tenutamen

The display uses the spelling conventionally used in Anglophone scholarship and — crucially — the form the three source museums (Met, Brooklyn, Harvard) actually emit in their catalogue text. Empirical check: the Met's Egyptian collection returns ~1000 hits for "Senwosret" and 0 for "Senusret"; ~21 for "Khafre" and 0 for "Khafra." Picking continental/Beckerath transliterations as `display` would show one spelling in the UI while every ingested artifact text uses another — dissonant for users and for search snippets.

Continental transliterations (Senusret, Khafra, Menkaura) and Greek forms (Sesostris, Chephren, Mycerinus) live in `aliases` so enrichment resolves all variants to the same ruler.

Numbering uses Arabic numerals with no period (`III`, not `III.` or `the Third`). Hyphenation and apostrophes follow Beckerath.

### Schema

```json
{
  "id": "amenhotep_iii",
  "display": "Amenhotep III",
  "dynasty_id": "dynasty_18",
  "dates": {"start": -1390, "end": -1352},
  "beckerath_id": "...",
  "pharaoh_se_slug": "amenhotep-iii",
  "titulary": {
    "horus":         ["Kanakht Khaemmaat"],
    "nebty":         ["Semenhepusegerentawy"],
    "golden_horus":  ["Aakhepesh husetiu"],
    "prenomen":      ["Nebmaatre"],
    "nomen":         ["Amenhotep", "Amenophis"]
  },
  "aliases": [
    "Amenhotep III", "Amenophis III", "Nebmaatre",
    "Nimmuria", "Mimmuria",
    "Kanakht Khaemmaat", "Semenhepusegerentawy", "Aakhepesh husetiu"
  ]
}
```

The flat `aliases` list is the union of all titulary parts plus all known transliterations and Greek forms. The enrichment matcher (ADR-009) reads only `aliases` — it is dumb, fast, and case-insensitive. The structured `titulary` object is consumed only by the web app for display ("also known as Nebmaatre (Prenomen)").

Beckerath's *Handbuch der ägyptischen Königsnamen* is the citation backbone for both the canonical display name and the titulary contents. Pharaoh.se (which itself cites Beckerath) provides the structured five-name data; its URL slug is the stable external identifier.

## Consequences
- The web app can present a consistent ruler index without "Cheops" and "Khufu" appearing as separate entities
- A cartouche reading of *Nebmaatre* on a Brooklyn artifact and *Amenhotep III* on a Met artifact resolve to the same ruler entity, enabling cross-museum companion-piece grouping (ADR-008 Tier A)
- Adding a new transliteration variant means appending to the `aliases` array — no code change
- The structured `titulary` object preserves *which* name is which, so the UI can show "(Prenomen)" or "(Greek form)" alongside aliases
- Beckerath IDs in the entry are the long-term citation handle — pharaoh.se URL slugs are an additional stable handle, but Beckerath identifiers are authoritative
- The display name standard will be enforced by a structural test (to be added as part of MVP task 3.2) that rejects entries where `display` is not present in the `nomen` titulary list (the canonical Nomen must be the display name)
- Co-regencies (Hatshepsut + Thutmose III, Amenemhat I + Senusret I) are handled at the artifact level via the `ruler_ids: list[str]` field from enrichment, not by creating composite ruler entries
