#!/usr/bin/env python3
"""Write the added-museums archive (`hapi-added-museums-2026-10-16.tar.gz`) from a database.

Reads `catalog.raw_cleveland` and `catalog.raw_walters` and writes each table as NDJSON, one row
per line: `{"object_id", "data"}`, where `data` is the stored text verbatim. Before writing, it
requires each table to reproduce the `raw_sha256` of its committed profile
(`docs/museum-sources/<museum>-profile/profile.json`), so the archive holds the table the
profile measured. The tar and gzip headers carry no time, owner or file name, so the same tables
give the same bytes on the same zlib build, whose SHA-256 `make_run.py` pins
(`ADDED_ARCHIVE_SHA256`). Another zlib build may compress differently and miss that pin; the
tables inside are still checked against the profiles (`make_run.load_added`).

The archive used was written on 2026-10-16 from Neon (the Vercel project
web-claim-graph-hapi) to the project's private store,
`dropbox/hapi-added-museums-2026-10-16/`. Both museums' data is CC0.

    DATABASE_URL=<postgres url> uv run python \\
        docs/evaluations/ruler-reregistration-2026-10-16/scripts/dump_added_museums.py --out <tar.gz>
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import sys
import tarfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "pipeline"))
import sqlalchemy as sa  # noqa: E402
from pipeline.types.models import raw_cleveland_table, raw_walters_table  # noqa: E402

PREFIX = "hapi-added-museums-2026-10-16/"
TABLES = {"cleveland": raw_cleveland_table, "walters": raw_walters_table}


def dump(url: str, out: Path) -> str:
    members = {}
    with sa.create_engine(url).connect() as conn:
        for museum, table in TABLES.items():
            rows = sorted((r["object_id"], r["data"]) for r in conn.execute(sa.select(table)).mappings())
            digest = hashlib.sha256("".join(f"{i}\x1f{d}\x1e" for i, d in rows).encode("utf-8")).hexdigest()
            profile = REPO / f"docs/museum-sources/{museum}-profile/profile.json"
            if digest != json.loads(profile.read_text(encoding="utf-8"))["raw_sha256"]:
                raise ValueError(f"catalog.raw_{museum} is not the table its profile measured")
            members[f"raw_{museum}.ndjson"] = "".join(
                json.dumps({"object_id": i, "data": d}, ensure_ascii=False) + "\n" for i, d in rows).encode("utf-8")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for name, body in sorted(members.items()):
            info = tarfile.TarInfo(PREFIX + name)
            info.size, info.mtime, info.mode = len(body), 0, 0o644
            tar.addfile(info, io.BytesIO(body))
    # No file name or time in the gzip header, so the bytes do not depend on where it is written.
    with out.open("wb") as handle, gzip.GzipFile(filename="", fileobj=handle, mode="wb", mtime=0) as archive:
        archive.write(buffer.getvalue())
    return hashlib.sha256(out.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(dump(os.environ["DATABASE_URL"], args.out))


if __name__ == "__main__":
    main()
