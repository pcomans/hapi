"""Cut a chunk's pages from the Dodson & Hilton PDF into the sub-PDF its extraction agents read.

The book (158 MB) is over the Read tool's limit, so each chunk's agents read a small sub-PDF
under `raw/` (gitignored, like the book under `proprietary/`). The book and every sub-PDF are
pinned by SHA-256, so the agents' input is reproducible. From the dyn15-18 chunk on, the slice
is this script rather than an inline snippet (see `transcribe.md`).

    cd pipeline && uv run python pipeline/authority/sources/dodson-hilton-queens/slice_source.py dyn15-18 \\
        [--book <path to the book PDF, if not under this checkout's proprietary/books/>]
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pypdf

SOURCE_DIR = Path(__file__).parent
BOOK = SOURCE_DIR.parents[4] / "proprietary/books/Dodson & Hilton 2004 - Complete Royal Families.pdf"
BOOK_SHA256 = "e636c49f3d0b5b6c6ec072cc6e7af9d605caf52d438c55cd84da9de7b07008a0"

# chunk -> (physical PDF pages, 1-based, in order; sub-PDF SHA-256)
SLICES = {
    # Printed pp. 114 (box), 115 (Brief Lives), 116 (box), 120 (Brief Lives), 122 (box),
    # 128-129 (Brief Lives): physical = printed - 10 in this stretch of the book.
    "dyn15-18": ((104, 105, 106, 110, 112, 118, 119),
                 "7e92f81d1ea9ef0c45a115757095a00c11f3bab849ccc392183f5a87a80b796f"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def slice_chunk(chunk: str, book: Path = BOOK) -> Path:
    pages, expected = SLICES[chunk]
    if sha256(book) != BOOK_SHA256:
        raise ValueError(f"{book} is not the pinned edition scan")
    writer = pypdf.PdfWriter()
    reader = pypdf.PdfReader(book)
    for page in pages:
        writer.add_page(reader.pages[page - 1])
    out = SOURCE_DIR / "raw" / f"source-{chunk}.pdf"
    with out.open("wb") as handle:
        writer.write(handle)
    if sha256(out) != expected:
        raise ValueError(f"{out} has SHA-256 {sha256(out)}, not the pinned {expected}")
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("chunk", choices=sorted(SLICES))
    parser.add_argument("--book", type=Path, default=BOOK,
                        help="the book PDF (gitignored; default: proprietary/books/ in this checkout)")
    args = parser.parse_args()
    print(slice_chunk(args.chunk, args.book))
