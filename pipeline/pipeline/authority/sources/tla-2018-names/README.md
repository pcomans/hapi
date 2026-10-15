# Thesaurus Linguae Aegyptiae, lemma list of January 2018 — personal and royal names

The personal and royal names of the TLA's hieroglyphic/hieratic lemma list: each lemma's
transliteration, translations and relations, copied verbatim.

## Citation and licence

Teilauszug der Datenbank des Vorhabens „Strukturen und Transformationen des Wortschatzes der
ägyptischen Sprache" vom Januar 2018, 2018, hrsg. von Tonio Sebastian Richter & Ingelore
Hafemann im Auftrag der Berlin-Brandenburgischen Akademie der Wissenschaften und Hans-Werner
Fischer-Elfert & Peter Dils im Auftrag der Sächsischen Akademie der Wissenschaften zu Leipzig,
urn:nbn:de:kobv:b4-opus4-29190 (<https://edoc.bbaw.de/frontdoor/index/index/docId/2919>).

- **Licence:** [CC BY-SA 4.0 International](https://creativecommons.org/licenses/by-sa/4.0/).
  `vocabulary.zip` is the publisher's archive, unchanged. `reconciled.jsonl` is an extract of
  it (Adapted Material) and is shared under the same licence, with this attribution; it is
  not covered by the repository's Apache-2.0 licence (see `NOTICE`).
- **ShareAlike for later use.** Anything built from these rows, such as the planned
  transliteration labels for Dodson & Hilton's women, is Adapted Material too. It must carry
  this attribution per row and be shared under CC BY-SA 4.0, kept in its own data file rather
  than mixed into Apache-licensed code or data.
- **Archive:** `vocabulary.zip` (committed; 11,268,762 bytes, SHA-256
  `886bfd30d81e73bdd0158caa4eb94f9c047eca02ffac4c1a930e170e7265ce5a`), member
  `aaew_wlist.json` (38,775 lemmas). Retrieved 2026-10-15.

## Method

`fetch.py` reads the committed archive (or downloads it, if absent, and checks the SHA-256
before writing it), then keeps every lemma of type `entity_name` with subtype `person_name`
(2,944) or `kings_name` (418): 3,362 rows, sorted by subtype and TLA id, after one `_source`
header line. The lemma list's other `entity_name` subtypes are left out: gods_name 3,319,
place_name 1,747, artifact_name 650, org_name 489, animal_name 19, and 8 without a subtype.
Two lemmas have no type at all (867767 "py", 873713 "ḫꜣw"); the script names them and fails on
any other. No model is involved. A test rebuilds `reconciled.jsonl` from the committed archive
and checks it byte for byte.

## Schema (`reconciled.jsonl`)

| Field | Meaning |
|---|---|
| `tla_id` | The TLA lemma id. |
| `subtype` | `person_name` or `kings_name`, as the TLA classes it. |
| `transliteration` | The lemma in the TLA's transliteration (e.g. `Jꜥḥ-ms.w-nfr.t-jr.j`). |
| `translations` | The lemma's translations as the source holds them: `lang` and, where present, `value`. Per lemma: 2,212 have one German and one English entry, 1,148 one German only; two are exceptions, 863237 (Smendes) with only an English entry and 704366 (Hen-iati) with two German ones ("Hen-iati", "PN/?"). Of the English entries, 1,858 have a value, 322 an empty value and 33 no value key. A value is the TLA's rendering, often with a gloss (`"Ahmes-Nefertari (Frau des Ahmose)"`); a bracketed value (`"[Thronname Mentuhoteps IV.]"`) is a description, not a name. |
| `relations` | The lemma's relations to other lemmas (`type`, `objectId`) as the source holds them: successor 93, referencedBy 91, referencing 85, contains 5, partOf 5, and one with neither key. |
| `revision_state` | `published` (3,280) or `published-obsolete` (82). Every obsolete lemma has a `referencing` relation to the lemma that replaces it. Its spellings are kept: they are the TLA's renderings all the same. |

## Role and caution

The rows are used for **name spellings only, never for identity**:
1. as a test set for the royal-women weak-sign key (a lemma's transliteration and its
   renderings, glosses and bracketed descriptions removed by tested code, are one name in
   several conventions);
2. later, as Egyptological transliterations for Dodson & Hilton's women (ShareAlike above).

A lemma does not map one-to-one to a name or a person: `Tjy` is three `person_name` lemmas
(600348, 708792, 708799), `Nfr.t-jr.j` two, `Mnṯ.w-ḥtp.w` both a royal (400020 "Mentuhotep") and a
private (400025 "Month-hetepu") name, and some lemmas are glossed with a person ("Frau des
Ahmose"). The data has the inconsistencies of a working database (851822 "Henut-Ba" is
`Ḫn.wt-Bꜣ`, with Ḫ where its sibling names have Ḥ), so it is a test set, not an oracle.
