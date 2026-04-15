"""Gemini OCR runner for Ryholt 1997 (ADR-017).

Runs Gemini 3.1 Pro preview in page batches over a specified printed-page
range. Writes per-page markdown directly to `raw/page-NNN.md`.

Quality assurance is by human spot-check against the source PDF on a
sample of pages — not by cross-model diff (see ADR-017 for the decision
rationale).

Batching: every API call sends a multi-page PDF containing up to --batch
printed pages (default 5). The model is prompted to emit a
`=== PAGE NNN ===` header before each page's markdown; the runner splits
the response on that header to recover per-page files.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/ryholt-1997-sip/fetch.py \\
        --pages 333-411                  # full File 1 + Chronological Tables
    cd pipeline && uv run python pipeline/authority/sources/ryholt-1997-sip/fetch.py \\
        --pages 336 --batch 1            # single page

Environment (from pipeline/.env):
    GEMINI_API_KEY  required (billing-enabled Google AI project)
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
import time
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
RAW_DIR = SOURCE_DIR / "raw"
PDF_PATH = Path(__file__).resolve().parents[5] / "proprietary" / "books" / (
    "Ryholt 1997 - Political Situation SIP.pdf"
)

# Printed-page → physical-page offset. Ryholt prints p. 336 on physical
# page 340; front matter adds 4.
PRINTED_TO_PHYSICAL_OFFSET = 4

PAGE_HEADER_RE = re.compile(r"^===\s*PAGE\s+(\d+)\s*===\s*$", re.MULTILINE)

PROMPT_TEMPLATE = (
    "Transcribe the following pages from Ryholt 1997 'The Political "
    "Situation in Egypt During the Second Intermediate Period' as faithful "
    "Markdown.\n\n"
    "Rules:\n"
    "- Preserve Egyptological transliteration characters exactly: "
    "ꜣ ꜥ ḥ ḫ ẖ š ṯ ḏ. Do NOT substitute ASCII look-alikes — no '3' for ꜣ, "
    "no 'c' for ꜥ, no 'h' for ḥ or ḫ.\n"
    "- Preserve roman numerals and bibliographic references exactly as "
    "printed. If you see what looks like Greek Π or VH, it is the OCR "
    "mangling of II or VII — use the correct roman numeral.\n"
    "- Preserve the two-column layout by emitting column 1 then column 2 "
    "in reading order.\n"
    "- Preserve underlined text with Markdown's HTML passthrough "
    "`<u>…</u>`.\n"
    "- BEFORE each page's transcription, emit a header line of exactly "
    "`=== PAGE NNN ===` where NNN is the printed page number (no leading "
    "zeros). The printed page numbers for this batch are: {page_list}.\n"
    "- Emit nothing else: no preamble, no closing remarks, no commentary "
    "between pages."
)

GEMINI_MODEL = "gemini-3.1-pro-preview"


def _load_env() -> None:
    from dotenv import load_dotenv

    load_dotenv(SOURCE_DIR.parents[3] / ".env")


def _build_batch_pdf(physical_indices: list[int]) -> bytes:
    import pypdf

    reader = pypdf.PdfReader(str(PDF_PATH))
    writer = pypdf.PdfWriter()
    for idx in physical_indices:
        writer.add_page(reader.pages[idx])
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _prompt_for(printed_pages: list[int]) -> str:
    return PROMPT_TEMPLATE.format(page_list=", ".join(str(p) for p in printed_pages))


def _gemini_ocr(pdf_bytes: bytes, prompt: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            prompt,
        ],
    )
    return resp.text or ""


def _split_by_page_header(response: str, expected_pages: list[int]) -> dict[int, str]:
    matches = list(PAGE_HEADER_RE.finditer(response))
    if not matches:
        raise RuntimeError(
            f"Batch response contained no `=== PAGE NNN ===` headers; "
            f"expected pages {expected_pages}. Response starts: "
            f"{response[:200]!r}"
        )
    found_pages = [int(m.group(1)) for m in matches]
    if found_pages != expected_pages:
        raise RuntimeError(
            f"Batch response page headers {found_pages} do not match "
            f"expected {expected_pages}."
        )
    out: dict[int, str] = {}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(response)
        out[found_pages[i]] = response[start:end].strip("\n")
    return out


def _parse_page_range(spec: str) -> list[int]:
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


def _path(printed: int) -> Path:
    return RAW_DIR / f"page-{printed:03d}.md"


def run(printed_pages: list[int], batch_size: int) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for batch in _chunk(printed_pages, batch_size):
        needed = [p for p in batch if not _path(p).exists()]
        if not needed:
            print(f"  batch {batch[0]}-{batch[-1]}: cached", flush=True)
            continue
        print(f"  batch {batch[0]}-{batch[-1]}: {len(needed)} page(s)", flush=True)

        physical = [p + PRINTED_TO_PHYSICAL_OFFSET - 1 for p in needed]
        pdf_bytes = _build_batch_pdf(physical)
        prompt = _prompt_for(needed)

        resp = _gemini_ocr(pdf_bytes, prompt)
        for page, md in _split_by_page_header(resp, needed).items():
            _path(page).write_text(md + "\n")
        time.sleep(0.2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pages",
        required=True,
        help="Printed page(s) to OCR: '336' or '333-411' or '333,340,345'.",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=5,
        help="Pages per API call (default: 5).",
    )
    args = parser.parse_args()

    _load_env()
    if not PDF_PATH.exists():
        sys.exit(f"ERROR: source PDF not found at {PDF_PATH}")

    printed_pages = _parse_page_range(args.pages)
    print(
        f"OCR'ing {len(printed_pages)} page(s) from {PDF_PATH.name} "
        f"in batches of {args.batch}"
    )
    run(printed_pages, args.batch)


if __name__ == "__main__":
    main()
