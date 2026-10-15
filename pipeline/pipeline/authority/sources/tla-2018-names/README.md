# Thesaurus Linguae Aegyptiae, lemma list of January 2018 — personal and royal names

The personal and royal names of the TLA's hieroglyphic/hieratic lemma list: each with its
Egyptological transliteration and the TLA's German and English renderings, verbatim.

## Citation

Teilauszug der Datenbank des Vorhabens „Strukturen und Transformationen des Wortschatzes der
ägyptischen Sprache" vom Januar 2018, 2018, hrsg. von Tonio Sebastian Richter & Ingelore
Hafemann im Auftrag der Berlin-Brandenburgischen Akademie der Wissenschaften und Hans-Werner
Fischer-Elfert & Peter Dils im Auftrag der Sächsischen Akademie der Wissenschaften zu Leipzig,
urn:nbn:de:kobv:b4-opus4-29190 (<https://edoc.bbaw.de/frontdoor/index/index/docId/2919>).

- **Licence:** CC BY-SA 4.0 International. `reconciled.jsonl` is an adapted extract of that
  database and is shared under the same licence, with this attribution.
- **Archive:** `vocabulary.zip`, SHA-256
  `886bfd30d81e73bdd0158caa4eb94f9c047eca02ffac4c1a930e170e7265ce5a` (11,268,762 bytes),
  member `aaew_wlist.json` (38,775 lemmas). Retrieved 2026-10-15.

## Method

`fetch.py` downloads the archive to `raw/` (gitignored), checks its SHA-256, and keeps every
lemma of type `entity_name` with subtype `person_name` (2,944) or `kings_name` (418): 3,362
rows, sorted by subtype and TLA id. No model is involved; re-running gives the same bytes.

## Schema (`reconciled.jsonl`)

| Field | Meaning |
|---|---|
| `tla_id` | The TLA lemma id (`https://thesaurus-linguae-aegyptiae.de/lemma/<id>`). |
| `subtype` | `person_name` or `kings_name`, as the TLA classes it. |
| `transliteration` | The lemma in the TLA's transliteration (e.g. `Jꜥḥ-ms.w-nfr.t-jr.j`). |
| `de`, `en` | The TLA's German and English renderings, verbatim, glosses included (`"Ahmes-Nefertari (Frau des Ahmose)"`). 1,504 rows have no English. A bracketed rendering (`"[Thronname Mentuhoteps IV.]"`) is a description, not a name. |
| `revision_state` | `published` (3,280) or `published-obsolete` (82). |
| `source_citation` | The URN, archive member and SHA-256, and the licence. |

## Role

A lemma is a **name, not a person**: one lemma covers everyone who bore it (`Ḥn.wt-tꜣ.wj`
"Henut-tawi" is one lemma for several queens), and one name can be two lemmas (`Mnṯ.w-ḥtp.w`
is the king's name Mentuhotep and the private name Month-hetepu). The extract is therefore
used for name spellings only, never for identity:
1. as a ground-truth test set for the royal-women weak-sign skeleton key (each lemma's
   transliteration and renderings are one name in several conventions);
2. as a source of Egyptological transliterations for Dodson & Hilton's women (planned).
