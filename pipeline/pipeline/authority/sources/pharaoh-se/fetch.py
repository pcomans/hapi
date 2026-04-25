"""Fetch and reconcile pharaoh data from pharaoh.se into authority source JSONL.

Scrapes the pharaoh.se index page and all individual pharaoh pages using
Firecrawl, then parses the markdown into structured authority records with
full five-name royal titulary.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/pharaoh-se/fetch.py

Output:
    raw/index.md               — markdown of the pharaohs index page
    raw/{slug}.md              — markdown of each individual pharaoh page
    reconciled.jsonl           — one JSON object per line in authority source schema
"""

import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from firecrawl import FirecrawlApp

load_dotenv()

SOURCE_DIR = Path(__file__).parent
RAW_DIR = SOURCE_DIR / "raw"

PHARAOHS_INDEX_URL = "https://pharaoh.se/ancient-egypt/pharaohs"
PHARAOH_BASE_URL = "https://pharaoh.se/ancient-egypt/pharaoh"

# Section headers that introduce name categories in the markdown.
# Maps the markdown heading text to the field name in the output schema.
NAME_SECTIONS = {
    "Horus names": "horus_names",
    "Horus name": "horus_names",
    "Nebty names": "nebty_names",
    "Nebty name": "nebty_names",
    "Golden Horus names": "golden_horus_names",
    "Golden Horus name": "golden_horus_names",
    "Throne names": "throne_names",
    "Throne name": "throne_names",
    "Birth names": "birth_names",
    "Birth name": "birth_names",
}


def _init_firecrawl() -> FirecrawlApp:
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        print("ERROR: FIRECRAWL_API_KEY not set in environment", file=sys.stderr)
        sys.exit(1)
    return FirecrawlApp(api_key=api_key)


# ---------------------------------------------------------------------------
# Index page parsing
# ---------------------------------------------------------------------------

def _parse_dynasty_header(line: str) -> dict | None:
    """Parse a dynasty/period heading like '## Eighteenth Dynasty' or '## Predynastic kings'."""
    m = re.match(r"^##\s+(.+)$", line.strip())
    if not m:
        return None
    label = m.group(1).strip()

    # Try to extract a dynasty number
    num_match = re.search(r"(?:^|\s)(\d+)(?:st|nd|rd|th)\s", label)
    if num_match:
        return {"label": label, "number": int(num_match.group(1))}

    # Word-based dynasty names (e.g., "First Dynasty")
    ordinals = {
        "First": 1, "Second": 2, "Third": 3, "Fourth": 4, "Fifth": 5,
        "Sixth": 6, "Seventh": 7, "Eighth": 8, "Ninth": 9, "Tenth": 10,
        "Eleventh": 11, "Twelfth": 12, "Thirteenth": 13, "Fourteenth": 14,
        "Fifteenth": 15, "Sixteenth": 16, "Seventeenth": 17, "Eighteenth": 18,
        "Nineteenth": 19, "Twentieth": 20, "Twenty-first": 21, "Twenty-second": 22,
        "Twenty-third": 23, "Twenty-fourth": 24, "Twenty-fifth": 25,
        "Twenty-sixth": 26, "Twenty-seventh": 27, "Twenty-eighth": 28,
        "Twenty-ninth": 29, "Thirtieth": 30, "Thirty-first": 31,
    }
    # Check longest names first so "Twenty-first" matches before "First"
    for word, num in sorted(ordinals.items(), key=lambda x: -len(x[0])):
        if word.lower() in label.lower():
            return {"label": label, "number": num}

    # Non-numbered dynasty groups
    return {"label": label, "number": None}


def _parse_reign_dates(
    date_str: str, is_roman: bool = False
) -> tuple[int | None, int | None]:
    """Parse reign date string like '1479–1425' into (start_year, end_year).

    BCE dates are stored as negative integers. AD dates (Roman emperors)
    are stored as positive integers. Pharaoh.se uses bare numbers without
    BC/AD markers. BCE ranges descend (1479→1425), AD ranges ascend (14→37).

    For ambiguous single-year reigns (e.g. Otho "69"), the dynasty context is
    needed to disambiguate. ``is_roman=True`` flags that the reign is from a
    Roman-emperor entry, in which case unmarked values are positive (CE).
    """
    if not date_str or not date_str.strip():
        return None, None

    date_str = date_str.strip()

    # Handle ranges: "1479–1425", "2900–", "?–2870", "27 BC–14 CE"
    # Use en-dash or hyphen as separator
    parts = re.split(r"[–\-]", date_str, maxsplit=1)

    def _parse_part(part: str) -> int | None:
        """Parse a single date part, respecting explicit BC/BCE/CE/AD markers."""
        part = part.strip()
        m = re.search(r"(\d+)", part)
        if not m:
            return None
        val = int(m.group(1))
        # Explicit era markers
        if re.search(r"\b(CE|AD)\b", part, re.IGNORECASE):
            return val
        if re.search(r"\b(BC|BCE)\b", part, re.IGNORECASE):
            return -val
        # No marker — return raw value, sign determined by range context
        return val

    raw_start = _parse_part(parts[0]) if len(parts) >= 1 else None
    raw_end = _parse_part(parts[1]) if len(parts) >= 2 else None

    # If explicit markers resolved the signs, we're done
    if raw_start is not None and raw_start > 0 and raw_end is not None and raw_end < 0:
        # e.g., "14 CE" (positive) and something BC (negative) — shouldn't happen
        return raw_start, raw_end
    if raw_start is not None and raw_start < 0:
        # Explicit BC marker was present
        return raw_start, raw_end if raw_end is not None else None
    if raw_end is not None and raw_end > 0 and raw_start is not None and raw_start < 0:
        # Mixed: "27 BC–14 CE"
        return raw_start, raw_end

    # No explicit markers — infer from range direction.
    # BCE ranges descend (1479→1425): negate both.
    # AD ranges ascend (14→37): keep positive.
    if raw_start is not None and raw_end is not None:
        if raw_start == raw_end:
            # Equal endpoints (e.g., a single-year span "218–218"): direction
            # is ambiguous, so fall back to dynasty context.
            return (raw_start, raw_end) if is_roman else (-raw_start, -raw_end)
        if raw_start > raw_end:
            return -raw_start, -raw_end
        return raw_start, raw_end

    # Single date without marker: dynasty context decides the sign.
    if raw_start is not None:
        return (raw_start if is_roman else -raw_start), None
    if raw_end is not None:
        return None, (raw_end if is_roman else -raw_end)
    return None, None


def parse_index(markdown: str) -> list[dict]:
    """Parse the pharaohs index page markdown into a list of basic pharaoh records."""
    records = []
    current_dynasty = None

    for line in markdown.split("\n"):
        # Check for dynasty headers
        dynasty = _parse_dynasty_header(line)
        if dynasty is not None:
            current_dynasty = dynasty
            continue

        # Check for pharaoh table rows: | 1 | [Name](url) | alt names | reign |
        # Some pharaohs have "?" instead of a number for uncertain ordering.
        m = re.match(
            r"\|\s*(\d+|\?)\s*\|\s*\[([^\]]+)\]\(https://pharaoh\.se/ancient-egypt/pharaoh/([^)]+)\)\s*\|([^|]*)\|([^|]*)\|",
            line,
        )
        if not m:
            continue

        ordinal = int(m.group(1)) if m.group(1) != "?" else None
        display = m.group(2).strip()
        slug = m.group(3).strip().rstrip("/")
        alt_raw = m.group(4).strip()
        reign_raw = m.group(5).strip()

        # Parse alt names: "_Tuthmosis III, Thutmosis III_" → ["Tuthmosis III", "Thutmosis III"]
        alt_labels = None
        if alt_raw:
            cleaned = alt_raw.strip("_ \t")
            if cleaned:
                alt_labels = [a.strip() for a in cleaned.split(",") if a.strip()]

        is_roman = _is_roman_dynasty(
            current_dynasty["label"] if current_dynasty else None
        )
        start_year, end_year = _parse_reign_dates(reign_raw, is_roman=is_roman)

        url = f"{PHARAOH_BASE_URL}/{slug}/"

        records.append({
            "slug": slug,
            "display": display,
            "url": url,
            "alt_labels": alt_labels,
            "ordinal": ordinal,
            "dynasty_label": current_dynasty["label"] if current_dynasty else None,
            "dynasty_number": current_dynasty["number"] if current_dynasty else None,
            "start_year": start_year,
            "end_year": end_year,
        })

    return records


# ---------------------------------------------------------------------------
# Individual pharaoh page parsing
# ---------------------------------------------------------------------------

def _parse_intro(lines: list[str]) -> dict:
    """Parse the intro paragraph for dynasty link and alt names."""
    info: dict = {"predecessor": None, "successor": None, "alt_labels_from_page": None}

    for line in lines[:10]:
        # a.k.a. line: _a.k.a. Name1, Name2_
        aka_match = re.search(r"_a\.k\.a\.\s*(.+?)_", line)
        if aka_match:
            raw = aka_match.group(1)
            info["alt_labels_from_page"] = [a.strip() for a in raw.split(",") if a.strip()]

        # Predecessor/successor from the info table
        # Pharaoh.se has a typo: "Precedessor" instead of "Predecessor".
        # The regex accommodates both spellings.
        pred_match = re.search(
            r"Prec?edec?e?ssor.*?\[([^\]]+)\]",
            line,
        )
        if pred_match:
            info["predecessor"] = pred_match.group(1)

        succ_match = re.search(r"Successor.*?\[([^\]]+)\]", line)
        if succ_match:
            info["successor"] = succ_match.group(1)

    return info


_DATE_VALUE_RE = re.compile(
    r"^\s*"
    r"(?:\?|\d{2,})\s*(?:BC|BCE|CE|AD)?\s*"
    r"(?:[–\-]\s*(?:\?|\d{0,})\s*(?:BC|BCE|CE|AD)?)?\s*"
    r"$",
    re.IGNORECASE,
)


def _looks_like_date(value: str) -> bool:
    """Reject prose like '4th millenium BCE', durations like '2y 1m 1d',
    and labels like 'Year 54' that show up in 'Reign of' rows for sparse
    rulers. Only digit-and-separator forms (with optional era markers) pass.

    The leading number requires >= 2 digits so a stray single digit (e.g.
    a footnote marker, the leading digit of '4th millennium', or a
    1-digit ordinal that survives an upstream regex) cannot pass as a
    legitimate year. Pharaoh.se's earliest single-year Roman reign is
    Galba/Otho/Vitellius at 68/69 — all 2 digits — so this floor is safe.
    """
    return bool(value) and bool(_DATE_VALUE_RE.match(value))


def _is_roman_dynasty(dynasty_label: str | None) -> bool:
    """Return True for pharaoh.se's 'Roman Emperors' dynasty group.

    This matches the source's own header text, not a canonical authority
    value — the function lives in the pharaoh.se mapper specifically to
    parse pharaoh.se's vocabulary, not to assert a project-wide name.
    """
    return bool(dynasty_label) and "Roman" in dynasty_label


def _extract_page_reign(chronology_lines: list[str]) -> str | None:
    """Extract the ruler's reign-date string from the page header table.

    Two pharaoh.se layouts produce a usable reign date:

    * BCE rulers carry an explicit ``| AE Chronology | YYYY–YYYY |`` row in
      the chronology table.
    * Roman emperors omit the chronology table entirely — the reign appears
      as a 2-cell row immediately following the ``| Reign of **NAME** |``
      header (e.g. ``|  | 69 |``).

    Returns the raw date string (caller parses with the right era context)
    or ``None`` if no reign row is present.
    """
    # Prefer the AE-Chronology row when present (BCE rulers)
    for line in chronology_lines:
        m = re.match(r"\|\s*AE Chronology\s*\|\s*(.+?)\s*\|", line)
        if m:
            value = m.group(1).strip()
            if _looks_like_date(value):
                return value

    # Fall back to the unlabeled row after '| Reign of **NAME** |'. Roman
    # emperor pages render the reign as a 2-cell row with an empty first
    # cell ('|  | 69 |'). Other rulers without an AE Chronology row may
    # have labelled scholar rows there (e.g., 'Turin King List | 2y 1m 1d')
    # which encode a reign DURATION, not a date range — skip those.
    for i, line in enumerate(chronology_lines):
        if not re.search(r"\|\s*Reign of\s+\*\*", line):
            continue
        for next_line in chronology_lines[i + 1 : i + 5]:
            m = re.match(r"\|\s*(.*?)\s*\|\s*(.+?)\s*\|", next_line)
            if not m:
                continue
            label = m.group(1).strip()
            value = m.group(2).strip()
            if label:
                # Labelled row → not the empty-cell Roman-emperor reign row
                continue
            if _looks_like_date(value):
                return value
        break

    return None


def _parse_chronology_table(lines: list[str]) -> dict[str, str]:
    """Parse the chronology table rows like '| AE Chronology | 1479–1425 |'."""
    chronologies = {}
    skip_labels = {"Highest attestation"}

    for line in lines:
        m = re.match(r"\|\s*(.+?)\s*\|\s*(.+?)\s*\|", line)
        if not m:
            continue
        label = m.group(1).strip()
        value = m.group(2).strip()

        # Skip non-chronology rows
        if label.startswith("---") or label.startswith("Reign of") or label.startswith("Predec"):
            continue
        if label in skip_labels:
            continue
        if not value or value == "---":
            continue

        if label:
            chronologies[label] = value

    return chronologies


def _parse_name_cards(section_lines: list[str]) -> list[dict]:
    """Parse name cards from a titulary section.

    Each card in the markdown follows this pattern:
        {Type} name [variant]     ← label line
        ![...](svg_url)           ← hieroglyph image
        {readable name}           ← name in modern transcription
        {transliteration}         ← scholarly transliteration with Unicode
        {translation}             ← English translation
        {gardiner codes}          ← Gardiner sign codes
        {source lines...}         ← bibliographic sources
    """
    cards = []
    # Find card boundaries by looking for label lines
    card_starts = []
    for i, line in enumerate(section_lines):
        stripped = line.strip()
        if re.match(
            r"^(Horus|Nebty|Golden Horus|Throne|Birth) name( variant)?( [A-Z])?$",
            stripped,
        ):
            card_starts.append(i)

    for idx, start in enumerate(card_starts):
        end = card_starts[idx + 1] if idx + 1 < len(card_starts) else len(section_lines)
        card_lines = section_lines[start:end]

        label = card_lines[0].strip()
        is_variant = "variant" in label

        # Skip image lines and extract content lines
        content = []
        for cl in card_lines[1:]:
            stripped = cl.strip()
            if not stripped:
                continue
            if stripped.startswith("!["):
                continue
            content.append(stripped)

        if len(content) < 3:
            continue

        # The pattern is: name, transliteration, translation, gardiner, sources...
        # Transliteration contains special Unicode chars like Ꜣ, ḫ, ꞽ, ḥ, etc.
        name = content[0]

        # Skip placeholder entries ("Name missing" with en-dash transliteration)
        if name == "Name missing":
            continue
        # Convert literal string "null" to actual None
        if name == "null":
            name = None
        transliteration = content[1] if len(content) > 1 else None
        translation = content[2] if len(content) > 2 else None

        # Gardiner codes are typically uppercase letter + number patterns
        gardiner = None
        sources = []
        # Footer phrases that indicate we've left the name card area
        footer_markers = {"**PLEASE NOTE**", "Ex nihilo nihil fit", "Back to top",
                          "There _might_ be errors", "Original text from"}
        for ci in range(3, len(content)):
            line = content[ci]
            # Stop if we hit pharaoh.se's page footer
            if any(marker in line for marker in footer_markers):
                break
            if line.startswith("[![Pharaoh.SE]"):
                break
            # Gardiner codes: sequences like "E1:D40-xa:m-R19-t:O49".
            # Must contain at least one uppercase-letter-followed-by-digit pattern
            # (e.g. E1, D40, N17) to distinguish from plain English words.
            stripped_line = line.replace(" ", "")
            if (gardiner is None
                    and re.match(r"^[A-Za-z0-9:*\-\\&/_.#]+$", stripped_line)
                    and re.search(r"[A-Z]\d", stripped_line)):
                gardiner = line
            else:
                sources.append(line)

        # If translation is "–" (dash), it means no translation available
        if translation == "–":
            translation = None

        # Strip escaped asterisks from pharaoh.se's retroactive-attribution markers
        # (e.g. "Meni\*" → "Meni", "Khufu\*" → "Khufu")
        # Strip markdown italic underscores from epithets
        # (e.g. "User Maat Ra, _setep en Ra_" → "User Maat Ra, setep en Ra")
        if name:
            name = name.rstrip("*").rstrip("\\").strip()
            name = re.sub(r"_([^_]+)_", r"\1", name)
        if transliteration:
            transliteration = transliteration.rstrip("*").rstrip("\\").strip()
            transliteration = re.sub(r"_([^_]+)_", r"\1", transliteration)

        cards.append({
            "name": name,
            "transliteration": transliteration,
            "translation": translation,
            "gardiner": gardiner,
            "is_variant": is_variant,
            "sources": sources if sources else None,
        })

    return cards


def _parse_ancient_sources(lines: list[str]) -> list[dict] | None:
    """Parse the 'sources of antiquity' table."""
    sources = []
    for line in lines:
        # | Author info | Greek | Transcription | Reign |
        m = re.match(r"\|\s*(.+?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|", line)
        if not m:
            continue
        author = m.group(1).strip()
        if author.startswith("---") or author.lower() == "author":
            continue

        sources.append({
            "author": author,
            "greek": m.group(2).strip() or None,
            "transcription": m.group(3).strip() or None,
            "reign": m.group(4).strip() or None,
        })

    return sources if sources else None


def parse_pharaoh_page(markdown: str, slug: str) -> dict:
    """Parse a single pharaoh page markdown into structured data."""
    lines = markdown.split("\n")

    # Extract intro info
    intro = _parse_intro(lines)

    # Parse chronology table (lines with | pattern before first ## subsection)
    chronology_lines = []
    name_section_lines: dict[str, list[str]] = {}
    ancient_source_lines = []
    current_section = "header"

    for line in lines:
        stripped = line.strip()

        # Detect section changes
        if stripped.startswith("## "):
            heading = stripped[3:].strip()
            if heading in NAME_SECTIONS:
                current_section = NAME_SECTIONS[heading]
                if current_section not in name_section_lines:
                    name_section_lines[current_section] = []
            elif "sources of antiquity" in heading.lower():
                current_section = "ancient_sources"
            elif heading == "The Royal Titulary":
                current_section = "titulary_intro"
            elif heading == "Bibliography":
                current_section = "bibliography"
            else:
                current_section = "other"
            continue

        if current_section == "header":
            chronology_lines.append(line)
        elif current_section in name_section_lines:
            name_section_lines[current_section].append(line)
        elif current_section == "ancient_sources":
            ancient_source_lines.append(line)

    chronologies = _parse_chronology_table(chronology_lines)
    page_reign = _extract_page_reign(chronology_lines)

    # Parse name sections
    titulary = {}
    for field_name, section_lines in name_section_lines.items():
        cards = _parse_name_cards(section_lines)
        if cards:
            titulary[field_name] = cards

    ancient_sources = _parse_ancient_sources(ancient_source_lines)

    return {
        "slug": slug,
        "predecessor": intro["predecessor"],
        "successor": intro["successor"],
        "alt_labels_from_page": intro["alt_labels_from_page"],
        "chronologies": chronologies if chronologies else None,
        "page_reign": page_reign,
        **titulary,
        "ancient_sources": ancient_sources,
    }


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------

def reconcile(index_records: list[dict], page_data: dict[str, dict]) -> list[dict]:
    """Merge index and page data into final authority records."""
    reconciled = []

    for rec in index_records:
        slug = rec["slug"]
        page = page_data.get(slug, {})

        # Reign dates: the ruler's own page wins when it disagrees with the
        # index column. The pharaoh.se index has row-shift bugs in the late
        # Roman section (e.g., Macrinus indexed as 244–249 vs page 217–218),
        # and it also drops the era marker, so a single-year Roman reign in
        # the index can't be sign-disambiguated without dynasty context. The
        # per-page header (AE Chronology / 'Reign of' row) is authoritative.
        # Merge per-field: page value wins where present, otherwise fall
        # back to the index so a sparse page (e.g. Tutankhamun "?–1324")
        # doesn't drop a known endpoint that the index supplies.
        is_roman = _is_roman_dynasty(rec.get("dynasty_label"))
        page_reign_str = page.get("page_reign")
        page_start, page_end = _parse_reign_dates(page_reign_str, is_roman=is_roman)
        start_year = page_start if page_start is not None else rec["start_year"]
        end_year = page_end if page_end is not None else rec["end_year"]

        # Merge alt labels from index and page (dedup, preserve order)
        alt_labels = []
        seen = set()
        for label in (rec.get("alt_labels") or []) + (page.get("alt_labels_from_page") or []):
            # Filter dash placeholders where pharaoh.se uses "-" for "no alternate name"
            if label in ("-", "–", "—") or not label.strip():
                continue
            if label not in seen and label != rec["display"]:
                alt_labels.append(label)
                seen.add(label)

        # Extract primary prenomen (first throne name, non-variant)
        prenomen = None
        throne_names = page.get("throne_names", [])
        if throne_names:
            prenomen = throne_names[0].get("name")

        # Extract primary nomen (first birth name, non-variant)
        nomen = None
        birth_names = page.get("birth_names", [])
        if birth_names:
            nomen = birth_names[0].get("name")

        # Add compact (spaceless) prenomen form for museum catalog matching.
        # Pharaoh.se writes "Men kheper Ra"; museums use "Menkheperre".
        # Standard Anglophone convention uses terminal -re not -ra.
        if prenomen and " " in prenomen:
            compact = prenomen.replace(" ", "").replace(",", "").lower()
            # Normalize terminal "ra" to "re" per museum convention
            if compact.endswith("ra"):
                compact = compact[:-2] + "re"
            # Capitalize first letter
            compact = compact[0].upper() + compact[1:] if compact else compact
            if compact not in seen and compact.lower() != rec["display"].lower():
                alt_labels.append(compact)
                seen.add(compact)

        # Propagate Greek/Manetho transcriptions from ancient_sources to alt_labels.
        # These are names like "Suphis" (Khufu), "Menes" (Narmer), "Sesostris" (Senusret).
        for src in page.get("ancient_sources") or []:
            transcription = src.get("transcription")
            if not transcription:
                continue
            # Strip gender symbols and other Unicode noise
            transcription = re.sub(r"[\u2640\u2642\u2600-\u26FF]", "", transcription).strip()
            # Strip parenthetical annotations like "(female symbol)"
            transcription = re.sub(r"\s*\([^)]*symbol[^)]*\)", "", transcription).strip()
            if transcription and transcription not in seen and transcription != rec["display"]:
                alt_labels.append(transcription)
                seen.add(transcription)

        reconciled.append({
            "kind": "ruler",
            "slug": slug,
            "url": rec["url"],
            "display": rec["display"],
            "alt_labels": alt_labels if alt_labels else None,
            "prenomen": prenomen,
            "nomen": nomen,
            "start_year": start_year,
            "end_year": end_year,
            "dynasty_label": rec["dynasty_label"],
            "dynasty_number": rec["dynasty_number"],
            "ordinal": rec["ordinal"],
            "predecessor": page.get("predecessor"),
            "successor": page.get("successor"),
            "chronologies": page.get("chronologies"),
            "horus_names": page.get("horus_names"),
            "nebty_names": page.get("nebty_names"),
            "golden_horus_names": page.get("golden_horus_names"),
            "throne_names": throne_names if throne_names else None,
            "birth_names": birth_names if birth_names else None,
            "ancient_sources": page.get("ancient_sources"),
        })

    return reconciled


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch_index(app: FirecrawlApp) -> str:
    """Scrape the pharaohs index page and return markdown."""
    print("Fetching pharaohs index page...")
    result = app.scrape(PHARAOHS_INDEX_URL, formats=["markdown"], only_main_content=True)
    md = result.markdown or ""
    print(f"  Index page: {len(md)} chars")
    return md


def fetch_pharaoh_pages(app: FirecrawlApp, slugs: list[str]) -> dict[str, str]:
    """Batch-scrape all individual pharaoh pages, return slug → markdown mapping."""
    urls = [f"{PHARAOH_BASE_URL}/{slug}/" for slug in slugs]
    print(f"Batch-scraping {len(urls)} pharaoh pages...")

    batch = app.batch_scrape(
        urls,
        formats=["markdown"],
        only_main_content=True,
        poll_interval=5,
    )

    results = {}
    for doc in batch.data:
        url = doc.metadata.source_url if doc.metadata and doc.metadata.source_url else ""
        # Extract slug from URL
        m = re.search(r"/pharaoh/([^/]+)/?$", url)
        if m:
            slug = m.group(1)
            results[slug] = doc.markdown or ""
        else:
            print(f"  WARNING: could not extract slug from URL: {url}", file=sys.stderr)

    print(f"  Received {len(results)} pages")
    return results


def _save_raw(index_md: str, page_markdowns: dict[str, str]) -> None:
    """Save raw markdown files for auditability."""
    RAW_DIR.mkdir(exist_ok=True)
    (RAW_DIR / "index.md").write_text(index_md, encoding="utf-8")
    for slug, md in page_markdowns.items():
        (RAW_DIR / f"{slug}.md").write_text(md, encoding="utf-8")
    print(f"  Saved raw markdown to {RAW_DIR}/")


def _load_raw() -> tuple[str, dict[str, str]] | None:
    """Load previously saved raw markdown files if they exist."""
    index_path = RAW_DIR / "index.md"
    if not index_path.exists():
        return None

    index_md = index_path.read_text(encoding="utf-8")
    page_markdowns = {}
    for p in RAW_DIR.glob("*.md"):
        if p.name == "index.md":
            continue
        page_markdowns[p.stem] = p.read_text(encoding="utf-8")

    return index_md, page_markdowns


def main():
    # Check for --parse-only flag to skip re-fetching
    parse_only = "--parse-only" in sys.argv

    if parse_only:
        print("Running in parse-only mode (using saved raw markdown)...")
        raw = _load_raw()
        if raw is None:
            print("ERROR: No raw data found. Run without --parse-only first.", file=sys.stderr)
            sys.exit(1)
        index_md, page_markdowns = raw
    else:
        app = _init_firecrawl()

        # Step 1: Fetch and parse index
        index_md = fetch_index(app)

        # Step 2: Parse index to get slugs
        index_records = parse_index(index_md)
        print(f"  Parsed {len(index_records)} pharaohs from index")
        slugs = [r["slug"] for r in index_records]

        # Step 3: Batch-fetch all individual pages
        page_markdowns = fetch_pharaoh_pages(app, slugs)

        # Step 4: Save raw data
        _save_raw(index_md, page_markdowns)

    index_records = parse_index(index_md)
    print(f"  Parsed {len(index_records)} pharaohs from index")
    slugs = [r["slug"] for r in index_records]

    # Parse individual pages
    print("Parsing individual pharaoh pages...")
    page_data = {}
    for slug, md in page_markdowns.items():
        page_data[slug] = parse_pharaoh_page(md, slug)

    missing = [s for s in slugs if s not in page_data]
    if missing:
        # Constitutional rule 2: loud-fail on missing source pages. Partial
        # reconciliation produces index-only rows with null titulary, which
        # silently degrades the authority data. Raise so the caller fixes
        # the scrape (or removes the slug from the index) before reconcile.
        raise RuntimeError(
            f"{len(missing)} pages missing from raw/: {missing}. "
            "Re-run fetch without --parse-only or restore the missing files."
        )

    # Step 5: Reconcile
    reconciled = reconcile(index_records, page_data)
    print(f"  Reconciled {len(reconciled)} rulers")

    # Step 6: Save reconciled JSONL
    jsonl_path = SOURCE_DIR / "reconciled.jsonl"
    with open(jsonl_path, "w", encoding="utf-8", newline="\n") as f:
        for row in reconciled:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"  Saved → {jsonl_path}")

    # Stats
    has_prenomen = sum(1 for r in reconciled if r["prenomen"] is not None)
    has_nomen = sum(1 for r in reconciled if r["nomen"] is not None)
    has_dates = sum(1 for r in reconciled if r["start_year"] is not None or r["end_year"] is not None)
    has_horus = sum(1 for r in reconciled if r["horus_names"] is not None)
    has_alts = sum(1 for r in reconciled if r["alt_labels"] is not None)

    print(f"\nStats ({len(reconciled)} rulers):")
    print(f"  With dates:       {has_dates} ({100*has_dates//len(reconciled)}%)")
    print(f"  With prenomen:    {has_prenomen} ({100*has_prenomen//len(reconciled)}%)")
    print(f"  With nomen:       {has_nomen} ({100*has_nomen//len(reconciled)}%)")
    print(f"  With Horus names: {has_horus} ({100*has_horus//len(reconciled)}%)")
    print(f"  With alt labels:  {has_alts} ({100*has_alts//len(reconciled)}%)")


if __name__ == "__main__":
    main()
