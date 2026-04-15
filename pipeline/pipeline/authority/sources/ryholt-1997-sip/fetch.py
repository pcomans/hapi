"""Two-model OCR runner for Ryholt 1997 (ADR-017).

Runs Claude Opus 4.6 vision and Gemini 3.1 Pro preview in batches over a
specified printed-page range, writes per-page markdown from each model into
`raw/claude/page-NNN.md` and `raw/gemini/page-NNN.md`, and emits a per-page
character-level diff into `raw/diff/page-NNN.diff`. The committed canonical
OCR in `raw/page-NNN.md` is produced by the transcriber from these two
sources, with disagreements adjudicated against the PDF.

Batching: every API call sends a multi-page PDF containing up to --batch
printed pages (default 5). The models are prompted to emit a
`=== PAGE NNN ===` header before each page's markdown; the runner splits
the response on that header to recover per-page files.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/ryholt-1997-sip/fetch.py \\
        --pages 333-411                  # full File 1 + Chronological Tables
    cd pipeline && uv run python pipeline/authority/sources/ryholt-1997-sip/fetch.py \\
        --pages 333-411 --batch 8        # larger batches (fewer API calls)
    cd pipeline && uv run python pipeline/authority/sources/ryholt-1997-sip/fetch.py \\
        --pages 336 --only claude        # single page, one model

Environment (from pipeline/.env):
    ANTHROPIC_API_KEY   required for Claude
    GEMINI_API_KEY      required for Gemini (billing-enabled project)
"""

from __future__ import annotations

import argparse
import base64
import difflib
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

# Printed-page → physical-page offset. The Ryholt PDF prints p. 336 on
# physical page 340 (verified during benchmarking); front matter adds 4.
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

CLAUDE_MODEL = "claude-opus-4-6"
GEMINI_MODEL = "gemini-3.1-pro-preview"


def _load_env() -> None:
    from dotenv import load_dotenv

    load_dotenv(SOURCE_DIR.parents[3] / ".env")


def _build_batch_pdf(physical_indices: list[int]) -> bytes:
    """Combine several physical pages into a single PDF."""
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


def _claude_ocr(pdf_bytes: bytes, prompt: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    # Use streaming: large max_tokens + long PDF input can exceed the SDK's
    # 10-minute non-streaming ceiling.
    with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=32000,
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
                    {"type": "text", "text": prompt},
                ],
            },
        ],
    ) as stream:
        return "".join(stream.text_stream)


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
    """Split a batch response on `=== PAGE NNN ===` headers.

    Returns {printed_page: markdown}. Raises if the set of page headers found
    does not match `expected_pages`.
    """
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
    """Parse '333-410', '336', or '333,340,345' into a sorted list of ints."""
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


def run(printed_pages: list[int], only: str | None, batch_size: int) -> None:
    (RAW_DIR / "claude").mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "gemini").mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "diff").mkdir(parents=True, exist_ok=True)

    def path(model: str, printed: int) -> Path:
        return RAW_DIR / model / f"page-{printed:03d}.md"

    for batch in _chunk(printed_pages, batch_size):
        # Skip pages already on disk per model, independently: a batch where
        # Claude is fully cached but Gemini is not still runs Gemini.
        needs_claude = [p for p in batch if not path("claude", p).exists()]
        needs_gemini = [p for p in batch if not path("gemini", p).exists()]
        if only == "claude":
            needs_gemini = []
        elif only == "gemini":
            needs_claude = []

        if not needs_claude and not needs_gemini:
            print(f"  batch {batch[0]}-{batch[-1]}: cached", flush=True)
            _refresh_diffs(batch)
            continue

        print(
            f"  batch {batch[0]}-{batch[-1]}: "
            f"Claude={len(needs_claude)} Gemini={len(needs_gemini)}",
            flush=True,
        )

        # Same prompt + PDF for both models — so the batch PDF is built once
        # from the union of pages needed by either model.
        union = sorted(set(needs_claude) | set(needs_gemini))
        physical = [p + PRINTED_TO_PHYSICAL_OFFSET - 1 for p in union]
        pdf_bytes = _build_batch_pdf(physical)
        prompt = _prompt_for(union)

        if needs_claude:
            claude_resp = _claude_ocr(pdf_bytes, prompt)
            for page, md in _split_by_page_header(claude_resp, union).items():
                if page in needs_claude:
                    path("claude", page).write_text(md + "\n")
            time.sleep(0.2)

        if needs_gemini:
            gemini_resp = _gemini_ocr(pdf_bytes, prompt)
            for page, md in _split_by_page_header(gemini_resp, union).items():
                if page in needs_gemini:
                    path("gemini", page).write_text(md + "\n")
            time.sleep(0.2)

        _refresh_diffs(batch)


def _refresh_diffs(batch: list[int]) -> None:
    for printed in batch:
        c = RAW_DIR / "claude" / f"page-{printed:03d}.md"
        g = RAW_DIR / "gemini" / f"page-{printed:03d}.md"
        d = RAW_DIR / "diff" / f"page-{printed:03d}.diff"
        if c.exists() and g.exists():
            _write_diff(c.read_text(), g.read_text(), d)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pages",
        required=True,
        help="Printed page(s) to OCR: '336' or '333-411' or '333,340,345'.",
    )
    parser.add_argument(
        "--only",
        choices=["claude", "gemini"],
        help="Run only one model (default: both).",
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
    run(printed_pages, args.only, args.batch)


if __name__ == "__main__":
    main()
