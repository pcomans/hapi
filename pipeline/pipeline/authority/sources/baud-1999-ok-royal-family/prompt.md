# Baud 1999 — structured extraction prompt (chunk 1: vol.2 pp. 19–40, entries `[1]`–`[~25]`)

You are extracting structured prosopographical rows from the *Corpus*
of Michel Baud, *Famille royale et pouvoir sous l'Ancien Empire
égyptien*, vol. 2 (BdE 126/2, IFAO 1999). The PDF is at
`proprietary/books/Baud 1999 - Famille royale AE vol 2.pdf` and
pinned by SHA-256
`8768536a13fb5428d8ec7fbd96263d028aabb557a5411e7f796cad99ed6881cb`.

**Fair-use framing.** This is a facts-only scholarly extraction for a
private research repository under contract with a credentialed
Egyptologist user. The extraction is not redistributed; prose is not
reproduced; only identity-bearing facts (numeric IDs, names,
monuments, PM references, dynasties, titles, kinship) and short
non-copyrightable snippets for identity disambiguation survive into
the output.

## Your task

1. Read vol.2 physical pages **19–40** via the Claude Code `Read` tool,
   in 5–10-page sweeps:
   `Read(file_path="/Users/philipp/code/hapi/proprietary/books/Baud 1999 - Famille royale AE vol 2.pdf", pages:"19-24")`
   then `pages:"25-30"` etc. Confirm the first page you look at opens
   with Baud's `Corpus` header (printed p. 395) or `[1]` (printed p. 399).
2. For every numbered entry `[N]` in that page range, emit exactly one
   JSONL line following the schema below. Do not merge entries; do
   not split one entry across two rows.
3. Write your output to
   `pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/raw/agent-{YOUR_TAG}-chunk1.jsonl`
   where `{YOUR_TAG}` is `a`, `b`, or `c` as directed in your
   launch prompt.

## Schema (every row is ONE JSON object; keys sorted in output)

See README.md for the authoritative schema with field semantics.
Reproducing the concise version here:

```json
{
  "baud_id":         "003",
  "name":            "Jḥtj-ḥtp",
  "head_note":       null,
  "asterisk":        false,
  "redirect_to":     null,
  "monuments":       ["Mastaba G 7650 dans la nécropole orientale de Gîza"],
  "pm_refs":         ["PM 200-201"],
  "publications":    ["Publication très partielle (fouilles de Reisner).", "Baer n° 7", "Schmitz, p. 121-122 (356)", "Harpur n° 10"],
  "king":            "Rêkhaef au plus tard",
  "datation_raw":    null,
  "dynasty_min":     null,
  "dynasty_max":     null,
  "titles":          ["/// n jmꜣt (?)", "ꜥd-mr wḥꜥw", "ḥm [bꜣw] Nḫn", "ḥm-nṯr Ḫwfw", "ḥrp ꜥḥ", "smr", "smr wꜥtj"],
  "father_name":     null,
  "mother_name":     null,
  "king_father":     null,
  "spouse_names":    ["Mrt-jt.s [86]"],
  "children_names":  [],
  "sex":             "male",
  "notes":           "Husband of the royal daughter Mrt-jt.s [86]. Baer n°7; Schmitz pp.121-122.",
  "sub_period":      "Old Kingdom (Dynasties 3-6)",
  "source_citation": {"edition": "IFAO BdE 126/2 1999", "pdf_pages": "20-20"}
}
```

### Field-by-field rules

- **`baud_id`** — the bracketed corpus number at the head of the
  entry, zero-padded to **three** digits. `[1]` → `"001"`, `[17]` →
  `"017"`, `[282]` → `"282"`. Do NOT zero-pad to two or four digits.
- **`name`** — Baud's own Egyptological transliteration at the head
  of the entry, verbatim. Preserve:
  - Egyptological special characters: `ꜣ ꜥ ḥ ḫ ẖ š ṯ ḏ ḳ`.
  - Dots and parentheses as Baud prints them: `Jj-ḫt-nfr`,
    `Kꜣ(.j)-wꜥb(.w)`, `Jj-mrjj`.
  - Superscript ordinals: `"Jpwt Ire"` keep the `re` attached.
  - Lacuna markers: `[ḥr?]`, `[...]`, `///` — preserve verbatim.
  - Do NOT anglicise (no "Khufu", no "Cheops"; use `Ḫwfw`).
  - Do NOT strip the trailing `*` asterisk — that belongs in the
    `asterisk` field below AND stays out of `name`.
- **`head_note`** — when Baud prints an italic descriptor on the
  same line as the headword (e.g. *"graffito de la pyramide de
  Néferirkaré"* for `[1]`, *"Nom perdu, fils de Pépi II, ..."* for
  `[282]`), copy the italic descriptor verbatim as the `head_note`
  value (without the surrounding italics markup). If the headword
  has no italic descriptor (the typical case — just a transliterated
  name), set to `null`.
- **`asterisk`** — `true` if Baud prints `*` after the headword
  (marks *rattaché à la famille royale*). Examples in chunk 1:
  `[4] Jḥtj-ḥtp*`, `[5] Jḥtj-špss*`, `[7] Jj-mrjj*`, `[10] Jꜥn*`,
  `[11] Jww*`. Else `false`.
- **`redirect_to`** — for stubs that send you to another entry
  (e.g. `[9] Jj-[ḥr?]-nfr. Voir à Nfrt-kꜣw II [132]`), set
  `redirect_to` to the bracketed target number zero-padded
  (`"132"`). Then set `monuments`, `pm_refs`, `publications`,
  `king`, `datation_raw`, `dynasty_min`, `dynasty_max`, `titles`,
  `father_name`, `mother_name`, `king_father`, `spouse_names`,
  `children_names`, `sex`, `notes` all to `null` / `[]` /
  `false` as appropriate (`list`-typed fields → `[]`; `bool`
  → `false`; other → `null`). Non-redirect rows leave
  `redirect_to` as `null`.
- **`monuments`** — the monument / document list Baud prints in the
  entry header (one per monument). "Mastaba G 7650 dans la
  nécropole orientale de Gîza", "Tombe rupestre n° 4 au nord du
  Sphinx, Gîza", "Complexe funéraire de Néferirkaré, Abousir".
  Verbatim French. When Baud lists several documents under
  lettered sub-markers (`1:`, `2:`, `a:`, `b:`), treat each
  sub-document as one entry in the list. `[]` if none.
- **`pm_refs`** — Porter-Moss references verbatim. `"PM 214"`,
  `"PM 200-201"`, `"PM V, p. 72"`, `"PM 339"`. Keep volume roman
  numerals. List-typed.
- **`publications`** — all other publication / bibliographic
  citations printed in the header block (Borchardt,
  Hassan, Jéquier, Schmitz, Harpur, Baer, …). Verbatim; one string
  per printed line. `[]` if Baud prints none beyond PM.
- **`king`** — the short reign line in the header block (e.g.
  `Néferirkaré`, `Khoufou environ`, `Rêkhaef au plus tard`,
  `Snéfrou`, `Fin IVe – début Ve dynastie?`, `Pépi Ier`). This is
  the line Baud prints between the publication list and the TITRES
  section. Verbatim French including hedges (`environ`, `au plus
  tard`, `(ou plus)`, `?`). `null` if absent.
- **`datation_raw`** — a SEPARATE French date-phrase line if Baud
  prints both a king-name line AND a dynasty line in the header
  (common when he wants to qualify the reign — e.g. `"Pépi Ier"`
  on one line and `"Ve dynastie"` or `"Début Ve dynastie"` on the
  next, or `"Khoufou"` and `"IVe dynastie"`). If only one line is
  printed, prefer placing an explicit king-name in `king` and a
  pure dynasty-phrase in `datation_raw`. Hedges stay verbatim.
  `null` if the other field already captures everything.
- **`dynasty_min` / `dynasty_max`** — **Leave as `null`.** Derived
  deterministically by `fix_rows.py`; DO NOT attempt to infer the
  integer.
- **`titles`** — the TITRES line(s), split on Baud's comma
  separators. Each element is one transliterated title verbatim
  (`"zꜣt nswt"`, `"ḥmt nswt"`, `"rḫ nswt"`, `"ḥm-nṯr Ḫwfw"`,
  `"zꜣ nswt nj ẖt.f smsw"`). Parenthetical disambiguators stay
  attached (`"shd zwnw (aîné, Jr-n-Jḥtj)"`). Commas *inside*
  parentheses are NOT split points. When Baud prints multiple
  monument-keyed TITRES blocks (`(1a)`, `(1b)`, `(2)`, …) the
  outer monument-tag stays with the title string (e.g.
  `"wrt ḥts (1a-b)"`). **Bold-italic weight** Baud applies to
  names like *mwt nswt* is irrelevant for extraction; capture the
  text only. `[]` if no TITRES section is printed.
- **`father_name` / `mother_name`** — from the PARENTÉ section's
  prose. Verbatim transliteration. If Baud hedges
  (`"peut-être fils de Snéfrou"`, `"probable"`, `"d'après Kanawati"`)
  append the hedge in parentheses: `"Snéfrou (peut-être)"`,
  `"Amenemhat I (probable)"`. If Baud writes `"Inconnue"` /
  `"Inconnu"` / explicit absence, emit `null` (not the literal
  string `"Inconnue"`). For anonymous parents attested by royal
  wife-title alone (`mère fut une hmt nswt de X`) without a
  personal name, emit `null`.
- **`king_father`** — **Leave as `null`.** Derived in
  `fix_rows.py` from `father_name` against a known-king list.
- **`spouse_names`** / **`children_names`** — from PARENTÉ,
  transliteration, hedges in parens, `[]` if none. Each spouse or
  child is one string; Baud's bracketed back-reference number
  stays attached: `"Mrt-jt.s [86]"`. If Baud only refers to a
  spouse by a kinship title without naming them (`"son épouse, une
  hmt nswt"`), emit `[]` (not a bogus name).
- **`sex`** — inferred from the dominant title in `titles`:
  - Female if any of: `mwt nswt`, `ḥmt nswt`, `zꜣt nswt`,
    `ḥkrt nswt`, `wrt ḥts`, `wrt ḥzt`, `mrrt ḥwt-Ḥr`.
  - Male if any of: `zꜣ nswt`, `smr wꜥtj`, `jrj-pꜥt`, `ḥrj-tp`,
    `jmj-rꜣ …`, `ḥm-nṯr …`, `ḥrj-sštꜣ …`, and no female-marked
    title is present.
  - If the TITRES list contains both a clearly-female title and a
    male function-title (unusual), default to the kinship title
    (so zꜣt nswt with a secondary profession → female).
  - `null` only when the entry is a redirect stub OR when neither
    a female nor a male title appears (e.g. an anonymous
    appendix-pointer).
- **`notes`** — at most 2 English sentences distilling the
  DATATION / DIVERS sections, *only when they add identity-
  disambiguating context not captured elsewhere*. Examples:
  - Kinship chain not otherwise visible from the structured fields
    (e.g. "Husband of the royal daughter Mrt-jt.s [86].").
  - A king-anchor that the structured field missed
    ("Probably dates to Rêkhaef based on fausse-porte type.").
  - Nothing → emit `null`.
  Do NOT restate the titles, monument, or PM refs. Do NOT
  reproduce Baud's argumentative discussion. No long quotations;
  short identity-disambiguating paraphrase only.
- **`sub_period`** — ALWAYS literal string
  `"Old Kingdom (Dynasties 3-6)"`. This is the schema-parity field
  with Dodson-Hilton.
- **`source_citation`** — ALWAYS
  `{"edition": "IFAO BdE 126/2 1999", "pdf_pages": "<s>-<e>"}`
  where `<s>` and `<e>` are the vol.2 physical page numbers (not
  printed-page) spanning THIS entry. A single-page entry uses
  `"20-20"`, a multi-page entry uses the full span (e.g. `[17]
  Jpwt Ire` spans physical pp. 24–26 → `"24-26"`). Keep the
  range even when start equals end.

## Output format

Write JSONL to the exact path
`pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/raw/agent-{YOUR_TAG}-chunk1.jsonl`
where `{YOUR_TAG}` is the agent letter (`a`, `b`, or `c`) directed
by your launch prompt. One JSON object per line. Keys sorted
(use `json.dumps(..., sort_keys=True, ensure_ascii=False)`).
Encode all Egyptological characters as real Unicode (NFC); do NOT
escape them as `\uXXXX`.

## Edge cases you will encounter in chunk 1

- `[1] ///-Ḥr (?)` — the headword itself begins with a lacuna
  `///`; preserve the literal `///-Ḥr (?)` as `name`. Baud's
  entry-header italic line is `"graffito de la pyramide de
  Néferirkaré"` → that goes in `head_note`. TITRES is just
  `zꜣt nswt`; sex female.
- `[2] Jḥ-Rꜥ` — rare name, date range printed as `"Fin IVe – début
  Ve dynastie?"` — goes verbatim in `datation_raw` with the `?`.
  TITRES line includes an `mrjj.f` suffix — keep the suffix in the
  title string.
- `[3] Jḥtj-ḥtp` — the flagship. Spouse `Mrt-jt.s [86]` — keep the
  bracketed number in the spouse string.
- `[4] Jḥtj-ḥtp*` — asterisk is `true`.
- `[7] Jj-mrjj*` — multiple monument sub-documents listed under
  lettered sub-markers `1:`, `2:`, `3:`; each becomes one
  `monuments`/`publications` list entry. TITRES line has
  monument-tagged variants (`jmj-r wḥrt (2), rḫ nswt (1), wꜥb
  mwt nswt (1), shd wꜥbw (3)`).
- `[8] Jj-nfr` — the headword has a lacuna-tagged title list
  (`/// dd-Snfrw, /// nb pr-ḫnd, ///`). Preserve the `///`
  literally inside each title.
- `[9] Jj-[ḥr?]-nfr` — redirect stub pointing to `[132]`. This is
  your canonical `redirect_to` example: set `redirect_to="132"`,
  all other factual fields `null`/`[]`/`false`.
- `[15] Jwn-kꜣ(.j)` — extremely short entry; `king: "Milieu de la
  IVe dynastie"`, one TITRE `zꜣ nswt`, PARENTÉ points to
  `Ḫwfw-ḫꜥ.f I [179]` as grandfather.
- `[17] Jpwt Ire` — BIG entry spanning physical pp. 24–26, with
  the longest TITRES list of the chunk (many monument-keyed
  variants `(1a)`, `(1a-b)`, `(1a, 3, 4, 5)`, etc.). `head_note`
  is `null` (no italic descriptor). PARENTÉ: épouse de Téti et
  mère de Pépi Ier. Both those facts map to structured fields.
  Expect `spouse_names: ["Téti"]` and `children_names: ["Pépi
  Ier"]` after you follow the rule that kings get their French
  Arabic-numeral-plus-ordinal spelling.
- A *non*-exhaustive footnote scan: Baud's numbered footnotes
  (`^10`, `^11`, etc.) are NOT extracted. They live at the foot
  of the page in small type; the entry-body text never needs
  them to produce a valid row.

## Sanity bounds

Chunk 1 is entries `[1]`–`[~25]` over vol.2 physical pp. 19–40.
Expect between **20 and 30** rows. If your JSONL has fewer than
20 or more than 30, re-read the PDF for missed/duplicated entries.
One redirect stub (`[9]`) is expected. At least 5 asterisk-true
entries are expected.

## Report back (one sentence, ≤ 80 words)

Row count + lowest/highest `baud_id` + anomalies (missing
entries, ambiguous asterisk, multi-page sprawl other than `[17]`).
