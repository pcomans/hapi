# Walters Art Museum

Explored and ingested 2026-10-16. Added to give the ruler test more cases: its catalogued reigns spell rulers differently from the Met's ("Thutmosis IV", "Amenophis III", "Sesostris I", "Sety I").

The counts below are from `walters-profile/profile.json`, made by `walters-profile/profile.py` from the ingested `catalog.raw_walters` table. `raw_sha256` names the rows it read, and `code_sha256` names the code. A later edit to that code needs a re-run before the counts describe it. The checks of web pages and the rights page are from exploration calls, which are not committed.

## Access

- **No live API.** The museum's collections API (v1) closed in 2023. The museum now publishes its collection data as CSV files in the GitHub repository [WaltersArtMuseum/api-thewalters-org](https://github.com/WaltersArtMuseum/api-thewalters-org), with documentation in its [wiki](https://github.com/WaltersArtMuseum/api-thewalters-org/wiki).
- **Files read:**
  - `art.csv`: one row per object, 22,193 objects of every collection (`file_objects`).
  - `media.csv`: one row per image or file, with `ImageURL`, `IsPrimary` and `Rank`.
  - `collections.csv` (not ingested) names the collection codes. `EGY` is "Ancient Egypt and Nubia".
- **Version.** The ingest resolves the `main` branch to a commit through the GitHub API, then reads both files at that commit. Both files therefore come from one version. The commit and the files' SHA-256 are in the asset's materialization metadata.
  - The ingest of 2026-10-16 read commit `f7531ed751ac2c138eeb6f923a3b4fd325d78adf` ("Data update", 2026-09-11).
  - The profile downloads both files at that commit, checks their SHA-256 (`source`), and requires the raw table to be exactly what the ingest's `candidate_records` makes of them (`raw_table_equals_ingest_candidates`). So the stored records trace to the public files.
- **Re-ingesting** upserts and never deletes, as every ingest asset does (#374). An object that a later version of the files drops stays in the table until that is solved. Deleting raw rows alone would leave their canonical rows without a raw payload, which `authority_links` refuses.
- **Raw record.** The ingest stores one object's `art.csv` row (`object`) and its `media.csv` rows (`media`, in file order), as Python's CSV reader gives them: every value is a string. A row with more or fewer fields than the header raises, and so does a repeated `ObjectID`.
- **Record pages.** `ResourceURL` is a permanent link (`https://purl.thewalters.org/art/<accession>`) that redirects to `https://art.thewalters.org/object/<accession>/`.
  - The site is behind Cloudflare. A request without a browser's user agent gets HTTP 403; with one, the page loads.
  - That matters to reviewers who open record pages: they need a real browser.

## Pagination and rate limits

There is no pagination: each file is one download. GitHub's unauthenticated API allows 60 requests an hour, and the ingest makes one (the commit). The two file downloads are from `raw.githubusercontent.com`.

## License

- **Data and images: CC0.** From the rights page (https://thewalters.org/about/policies/rights-reproductions/): the museum "has adopted the Creative Commons Zero: No Rights Reserved or CC0 license to waive copyright and allow for unrestricted use of digital images and metadata by any person, for any purpose".
  - Its exceptions are works on loan and works under artists' copyright. No in-scope record has a credit line that names a loan (`in_scope_credit_lines_naming_a_loan`).
  - The files carry no per-object rights field, so `MUSEUM_LICENSE` is CC0 and the mapper uses it for every record with an image.
- **Modern objects.** Four in-scope records are dated after 1800 (`in_scope_dated_after_1800`), all modern pieces filed in the Egyptian collection, such as 24708, "Head of Hatshepsut (?)", which its description calls a forgery. All four pages (22.77, 42.1, 42.78, 42.90) show "Creative Commons Zero" for their images, like the rest.
- **No image → `none`.**

## Field inventory (canonical mapping)

| Walters field (`object.`) | Canonical | Notes |
|---|---|---|
| `ObjectID` | `id` (`walters-{id}`), `source_id` | |
| `ResourceURL` | `source_url` | The purl link |
| `Title` | `title` | |
| `Description` | `description` | Verbatim HTML, ending in a boilerplate pointer to the online collection |
| `ObjectName` | `object_type` | E.g. "scarabs; amulets" |
| `Medium` | `materials` | One string, not split |
| `Dimensions` | `dimensions` | |
| `Period` | `period` | Empty for every object in the file (`file_objects_with_period`), so always None |
| `Dynasty` | `dynasty` | E.g. "18th Dynasty", "25th-26th Dynasty" |
| `Reign` | `ruler_display_name` | Raw text without its trailing dates; see below |
| `DateBeginYear` / `DateEndYear` | `date_start` / `date_end` | Integer strings, negative for BCE |
| `DateText` | `date_display` | Often names the period and dynasty in its final parenthesis |
| `Provenance` | `provenance` | Ownership history |
| `AccessionNumber`, `CreditLine` | `accession_number`, `credit_line` | Surrounding whitespace removed |
| `media[]` | `image_url`, `thumbnail_url` | See below |

Every text field is stripped of surrounding whitespace, and an empty field is None.

Not mapped:
- `MuseumLocation`: a pointer to the website ("To learn whether this object is now on view … visit …"), not a location.
- `GeographyID`: empty for every in-scope record. The museum publishes no geography file and no find-place field, so `origin_site_raw` is always None. A find place appears only in prose, in `Provenance` ("said to be from Deir el-Bahri") or `Description`.
- `Inscriptions`, `Style`, `Classification`, `Keywords`, `Creators`, `Exhibitions`, `RelatedObjects`.

### `Reign`

99 in-scope records have a `Reign`. It names the ruler directly, with no "reign of", usually followed by dates: "Ramesses II (1279-1213 BC)".

- `ruler_display_name` is the field without its trailing dates. As for Cleveland, the final parenthesis is cut only when it holds a digit (`without_trailing_dates` in `pipeline/enrich/mentions.py`). So "Seti I (1290-1279/8) (?)" keeps its dates, because its final parenthesis is the doubt mark.
- The spellings differ from the Met's: "Thutmosis III", "Amenophis III", "Sesostris I", "Senostris I", "Sety I", "Psametik I", "Psammetichus I", "Ptolemy II Philadelphos", "King Shabaqo", "Tutankhamen".
- Lists and ranges are written several ways:
  - a hyphen with no spaces: "Psametik I-Necho II", "Tutankhamun-Horemheb";
  - a comma or semicolon: "Ptolemy II Philadelphos; Ptolemy IV Philopator";
  - "or": "Tutankhamen or Ay";
  - a slash: "Amenophis IV/Akhenaten".

### Images

An object's `media.csv` rows are its images (and, once, a PDF).
- The record's image is the one row marked `IsPrimary` (1,208 records).
- Six records have images but none marked primary. They take the image the museum ranks first (lowest `Rank`). A tie there would raise, and none occurs.
- 107 in-scope records have no image row.
- `ImageURL` is the only URL given (`https://art.thewalters.org/images/raw/...`), so the thumbnail is the same image.

## Inclusion (Egyptian scope)

- **What the ingest stores.** The ingest stores every candidate: an object whose `CollectionID` contains "EGY", or whose `Culture` contains "Egypt". That is 1,341 of 22,193 objects.
- **What the mapper keeps.** The mapper's `is_egyptian` decides, from the museum's own classification:

| Rule | Records (2026-10-16) | In scope |
|---|---|---|
| `CollectionID` includes `EGY` ("Ancient Egypt and Nubia"), alone or beside other codes ("EGY\|JWL", "GRC\|EGY") | 1,129 | yes |
| No collection, `Culture` exactly "Egyptian" | 192 | yes: all are ancient Egyptian objects the museum has not assigned to a collection |
| Only other collections (Islamic, Roman, Greek, Near Eastern), whatever the culture | 20 | **no**: the museum files them elsewhere. Eleven have culture "Egyptian": Greco-Roman figures (Harpokrates, Eros, a seated athlete), a Roman panel portrait whose `Reign` is "Marcus Aurelius", Near Eastern scarabs, Islamic-period fragments. Ids in `out_of_scope_ids` |
| **Total** | 1,341 (1,321 in scope) | |

- `CollectionID` is a "|"-separated list of codes. Two quirks:
  - one object, 24014, has its codes run together ("EGYJWL"), read as EGY and JWL;
  - "PRE" is used on 12 early objects (Paleolithic to Iron Age, six of them Egyptian Predynastic: `file_objects_using_code_pre`), but `collections.csv` does not list it.
- A code the museum does not use raises.
- An object in no collection whose culture is not "Egyptian" also raises, so a new case gets decided rather than guessed.
- In-scope cultures include Coptic, Roman, Greek, Nubian and Kushite, because the museum files those objects in its Egyptian collection (`in_scope_by_culture`).

## Enrichment (authority links)

The mention reader (`walters_mentions` in `pipeline/enrich/mentions.py`) reads:
- **`Reign`**, as the Met's `reign` field is read (`walters_reign_expression`). Its dates are cut first, then the Met parser's own tests apply:
  - a doubt, a temporal phrase, "or"/"and" or a spaced dash is not one ruler;
  - a field of more than one top-level component (comma or semicolon) is a list.

  A hyphen without spaces is not a range, as in the parser. "Psametik I-Necho II" stays one name. In the authority mode no ruler matches it, so it is a missed link, not a wrong one. In the literal mode it links by its text, to any record that writes the same pair.
- **Royal cues in `Title` and `DateText`.** These use #361's cue grammar (`royal_cue_mentions`), as Brooklyn's title and date fields are read. `DateText` names a reign on 11 in-scope records ("ca. 1250 BCE (New Kingdom, 19th dynasty, reign of Ramesses II)"), four of them without a `Reign` (`in_scope_date_text_naming_a_reign`).

From the 1,321 in-scope records it gives 141 ruler mentions (`in_scope_ruler_mentions`):
- 91 `Reign` values classified as one name. Twelve of them are hyphenated pairs ("Psametik I-Necho II", "Tutankhamun-Horemheb": `reign_single_identity_hyphenated_pairs`);
- 11 `DateText` cues;
- 31 title cues;
- the rest lists or doubts.

50 title cues have no name after them ("Head of a King").

It does not read:
- `Description` or `Inscriptions`;
- find places, of which there are none as fields.

So the Walters has no site links. Every Walters pair is unevaluated in `QUALIFIED_SCOPES`.

The resolver was not tuned on these spellings. They are left as they are, so the Walters can serve as a clean test of the ruler authority.

## Known quirks

- `DateText` and `Reign` can disagree on spelling within one record: 1605 has `Reign` "Psametik I-Necho II" and `DateText` "… reign of Psamtek I".
- One `Reign` misspells its ruler: "Kashtar (ca. 746 BC)" (Kashta). It is kept as given.
- One object (23) has a `media.csv` row for a PDF with an empty file name. It is not an image, so it is never the record's image.
- `CreditLine` values sometimes start with spaces, and one reads "Walters Art Musueum". They are stripped of spaces only.
