"""Two-model OCR runner for Ryholt 1997 (ADR-017).

Runs Claude Opus 4.6 vision and Gemini 3.1 Pro preview in parallel over a
specified PDF page range, writes per-page markdown from each model into
`raw/claude/page-NNN.md` and `raw/gemini/page-NNN.md`, and emits a per-page
character-level diff report into `raw/diff/page-NNN.diff`. The committed
canonical OCR in `raw/page-NNN.md` is produced by the transcriber from
these two sources, with disagreements adjudicated against the PDF.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/ryholt-1997-sip/fetch.py \\
        --pages 333-410          # inclusive printed-page range
    cd pipeline && uv run python pipeline/authority/sources/ryholt-1997-sip/fetch.py \\
        --pages 336 --only claude    # single page, one model

Environment (from repo-root .env):
    ANTHROPIC_API_KEY   required for Claude
    GEMINI_API_KEY      required for Gemini (must be on a billing-enabled project)
"""

from __future__ import annotations

import argparse
import base64
import difflib
import io
import os
import sys
import time
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
RAW_DIR = SOURCE_DIR / "raw"
PDF_PATH = Path(__file__).resolve().parents[5] / "proprietary" / "books" / (
    "Ryholt 1997 - Political Situation SIP.pdf"
)

# Printed-page → physical-page offset. The Ryholt PDF prints p. 336 on
# physical page 340 (verified during benchmarking); front matter adds 4.
PRINTED_TO_PHYSICAL_OFFSET = 4

PROMPT = (
    "Transcribe this page of Ryholt 1997 'The Political Situation in Egypt "
    "During the Second Intermediate Period' as faithful Markdown. Preserve "
    "Egyptological transliteration characters exactly: ꜣ ꜥ ḥ ḫ ẖ š ṯ ḏ. "
    "Do not substitute ASCII look-alikes (no '3' for ꜣ, no 'c' for ꜥ, no "
    "'h' for ḥ/ḫ). Preserve roman numerals and bibliographic references "
    "exactly. Preserve the two-column layout by emitting column 1 then "
    "column 2. Preserve underlined text using Markdown's HTML passthrough "
    "`<u>…</u>`. Output only the Markdown transcription — no preamble, no "
    "closing remarks."
)

CLAUDE_MODEL = "claude-opus-4-6"
GEMINI_MODEL = "gemini-3.1-pro-preview"


def _load_env() -> None:
    from dotenv import load_dotenv

    load_dotenv(SOURCE_DIR.parents[3] / ".env")  # pipeline/.env


def _extract_page_pdf(physical_page_index: int) -> bytes:
    """Return a single-page PDF (bytes) for the given 0-indexed physical page."""
    import pypdf

    reader = pypdf.PdfReader(str(PDF_PATH))
    writer = pypdf.PdfWriter()
    writer.add_page(reader.pages[physical_page_index])
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _claude_ocr(pdf_bytes: bytes) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=16000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": base64.b64encode(pdf_bytes).decode("ascii"),
                        },
                    },
                    {"type": "text", "text": PROMPT},
                ],
            },
        ],
    )
    return "".join(b.text for b in msg.content if b.type == "text")


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


def _write_diff(claude_md: str, gemini_md: str, out: Path) -> None:
    diff = difflib.unified_diff(
        claude_md.splitlines(keepends=True),
        gemini_md.splitlines(keepends=True),
        fromfile="claude.md",
        tofile="gemini.md",
        n=2,
    )
    out.write_text("".join(diff))


def _parse_page_range(spec: str) -> list[int]:
    """Parse '333-410' or '336' or '333,340,345' into a list of printed-page ints."""
    out: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            lo, hi = part.split("-", 1)
            out.extend(range(int(lo), int(hi) + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def run(printed_pages: list[int], only: str | None) -> None:
    (RAW_DIR / "claude").mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "gemini").mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "diff").mkdir(parents=True, exist_ok=True)

    for printed in printed_pages:
        physical = printed + PRINTED_TO_PHYSICAL_OFFSET - 1  # 0-indexed
        pdf_bytes = _extract_page_pdf(physical)

        label = f"page-{printed:03d}"
        claude_path = RAW_DIR / "claude" / f"{label}.md"
        gemini_path = RAW_DIR / "gemini" / f"{label}.md"
        diff_path = RAW_DIR / "diff" / f"{label}.diff"

        ran_any = False
        if only in (None, "claude") and not claude_path.exists():
            print(f"  {label}: Claude…", flush=True)
            claude_md = _claude_ocr(pdf_bytes)
            claude_path.write_text(claude_md)
            ran_any = True
        if only in (None, "gemini") and not gemini_path.exists():
            print(f"  {label}: Gemini…", flush=True)
            gemini_md = _gemini_ocr(pdf_bytes)
            gemini_path.write_text(gemini_md)
            ran_any = True

        if claude_path.exists() and gemini_path.exists():
            _write_diff(claude_path.read_text(), gemini_path.read_text(), diff_path)

        if not ran_any:
            print(f"  {label}: cached", flush=True)
        else:
            time.sleep(0.2)  # polite rate-limiter


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pages",
        required=True,
        help="Printed page(s) to OCR: e.g. '336' or '333-410' or '333,340,345'.",
    )
    parser.add_argument(
        "--only",
        choices=["claude", "gemini"],
        help="Run only one model (default: both).",
    )
    args = parser.parse_args()

    _load_env()
    if not PDF_PATH.exists():
        sys.exit(f"ERROR: source PDF not found at {PDF_PATH}")

    printed_pages = _parse_page_range(args.pages)
    print(f"OCR'ing {len(printed_pages)} page(s) from {PDF_PATH.name}")
    run(printed_pages, args.only)


if __name__ == "__main__":
    main()
