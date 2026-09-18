"""Prepare official public benchmarks; verify pinned source checksums."""

import hashlib
import json
import urllib.request
from collections.abc import Mapping
from pathlib import Path

from scripts.constants import (
    LASIESTA_MANIFEST,
    LASIESTA_RAW_DIR,
    ROOT,
)

DOWNLOAD_TIMEOUT_SECONDS = 120


def verify(content: bytes, record: Mapping[str, object]) -> None:
    if (
        len(content) != record["bytes"]
        or hashlib.sha256(content).hexdigest() != record["sha256"]
    ):
        raise ValueError(f"Source checksum mismatch: {record['file']}")


def download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        return response.read()


def safe_path(root: Path, name: str) -> Path:
    path = Path(name)

    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Unsafe archive path")

    return root / path


def main() -> None:
    import libarchive  # optional preparation dependency; also needs OS libarchive

    destination = ROOT / LASIESTA_RAW_DIR
    destination.mkdir(parents=True, exist_ok=True)

    for rec in json.loads((ROOT / LASIESTA_MANIFEST).read_text()):
        path = destination / rec["file"]

        if not path.exists():
            content = download(rec["url"])
            verify(content, rec)
            path.write_bytes(content)

        verify(path.read_bytes(), rec)

        with libarchive.file_reader(str(path)) as archive:
            for entry in archive:
                out = safe_path(destination, entry.pathname)

                if entry.isdir:
                    out.mkdir(parents=True, exist_ok=True)
                elif entry.isfile:
                    out.parent.mkdir(parents=True, exist_ok=True)

                    with out.open("wb") as handle:
                        for block in entry.get_blocks():
                            handle.write(block)
                else:
                    raise ValueError("Unexpected archive entry type")


if __name__ == "__main__":
    main()
