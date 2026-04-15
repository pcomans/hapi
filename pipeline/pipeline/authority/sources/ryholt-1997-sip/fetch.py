"""Gemini OCR runner for Ryholt 1997 (ADR-017).

Chunks the source PDF by physical-page index and sends each chunk to
Gemini 3.1 Pro preview. Writes one markdown file per chunk into
`raw/chunk-pNNN-pMMM.md` where NNN-MMM is the 1-indexed physical page
range. Citations in `reconciled.jsonl` cite that physical-page range.

We do not try to resolve the PDF's printed page numbers on the agent
side; any shift introduced by blank / frontispiece / Part-heading
pages is handled by whoever verifies against the PDF.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/ryholt-1997-sip/fetch.py \\
        --physical 337-415              # inclusive physical-page range (1-indexed)
    cd pipeline && uv run python pipeline/authority/sources/ryholt-1997-sip/fetch.py \\
        --physical 337-415 --chunk-size 5

Environment (from pipeline/.env):
    GEMINI_API_KEY  required (billing-enabled Google AI project)
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
RAW_DIR = SOURCE_DIR / "raw"
PDF_PATH = Path(__file__).resolve().parents[5] / "proprietary" / "books" / (
    "Ryholt 1997 - Political Situation SIP.pdf"
)

PROMPT = (
    "Transcribe every page of this PDF as faithful Markdown. The PDF is a "
    "multi-page extract from Ryholt 1997 'The Political Situation in Egypt "
    "During the Second Intermediate Period'.\n\n"
    "Rules:\n"
    "- Preserve Egyptological transliteration characters exactly: "
    "ꜣ ꜥ ḥ ḫ ẖ š ṯ ḏ. Do NOT substitute ASCII look-alikes — no '3' for ꜣ, "
    "no 'c' for ꜥ, no 'h' for ḥ or ḫ.\n"
    "- Preserve roman numerals and bibliographic references exactly. If a "
    "glyph looks like Greek Π or VH in the OCR layer, it is II or VII; "
    "render the correct roman numeral.\n"
    "- Preserve the book's running headers (page-number banners at the "
    "top/bottom of each page, e.g. '336 Catalogue of Attestations' or "
    "'Chronological Tables 409'), inline where they appear. These are how "
    "a reader cross-references to the printed page.\n"
    "- Preserve the two-column layout by emitting column 1 then column 2 "
    "in reading order.\n"
    "- Preserve underlined text with Markdown's HTML passthrough "
    "`<u>…</u>`.\n"
    "- Output only the transcription — no preamble, no closing remarks."
)

GEMINI_MODEL = "gemini-3.1-pro-preview"


def _load_env() -> None:
    from dotenv import load_dotenv

    load_dotenv(SOURCE_DIR.parents[3] / ".env")


def _build_chunk_pdf(physical_one_indexed: list[int]) -> bytes:
    import pypdf

    reader = pypdf.PdfReader(str(PDF_PATH))
    writer = pypdf.PdfWriter()
    for p in physical_one_indexed:
        writer.add_page(reader.pages[p - 1])
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _gemini_ocr(pdf_bytes: bytes) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            PROMPT,
        ],
    )
    return resp.text or ""


def _parse_range(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            lo, hi = part.split("-", 1)
            out.extend(range(int(lo), int(hi) + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def _chunk(seq: list[int], size: int) -> list[list[int]]:
    return [seq[i : i + size] for i in range(0, len(seq), size)]


def _chunk_path(first: int, last: int) -> Path:
    return RAW_DIR / f"chunk-p{first:03d}-p{last:03d}.md"


def _process_chunk(batch: list[int]) -> str:
    """OCR one chunk and write its file. Returns a short log line."""
    first, last = batch[0], batch[-1]
    out = _chunk_path(first, last)
    if out.exists():
        return f"  chunk p{first:03d}-p{last:03d}: cached"

    pdf_bytes = _build_chunk_pdf(batch)
    text = _gemini_ocr(pdf_bytes)
    header = (
        f"<!-- Ryholt 1997 — physical pages {first}-{last} "
        f"(1-indexed PDF page numbers). Citations in reconciled.jsonl "
        f"reference this range. -->\n\n"
    )
    out.write_text(header + text.rstrip() + "\n")
    return f"  chunk p{first:03d}-p{last:03d}: {len(batch)} page(s) OK"


def run(physical_pages: list[int], chunk_size: int, workers: int) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    batches = _chunk(physical_pages, chunk_size)

    if workers <= 1:
        for batch in batches:
            print(_process_chunk(batch), flush=True)
        return

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_process_chunk, batch): batch for batch in batches}
        for fut in as_completed(futures):
            # Raise on failure so the caller sees a traceback, but keep the
            # other in-flight chunks going.
            print(fut.result(), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--physical",
        required=True,
        help="Physical (1-indexed PDF) page range, e.g. '337-415'.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=5,
        help="Pages per chunk / per API call (default: 5).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Concurrent OCR workers (default: 5; set to 1 for serial).",
    )
    args = parser.parse_args()

    _load_env()
    if not PDF_PATH.exists():
        sys.exit(f"ERROR: source PDF not found at {PDF_PATH}")

    physical_pages = _parse_range(args.physical)
    print(
        f"OCR'ing physical pages {physical_pages[0]}-{physical_pages[-1]} "
        f"({len(physical_pages)} pp.) in chunks of {args.chunk_size}, "
        f"{args.workers} worker(s)"
    )
    run(physical_pages, args.chunk_size, args.workers)


if __name__ == "__main__":
    main()
