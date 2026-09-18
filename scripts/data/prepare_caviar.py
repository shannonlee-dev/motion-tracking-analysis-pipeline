"""Download public source media to the ignored data/raw tree."""

import hashlib
import json
import urllib.request

from scripts.constants import (
    CAVIAR_MANIFEST,
    CAVIAR_RAW_DIR,
    LIGHTING_MANIFEST,
    LIGHTING_RAW_DIR,
    ROOT,
)

DOWNLOAD_TIMEOUT_SECONDS = 90
BASE = "https://homepages.inf.ed.ac.uk/rbf/"
SOURCES = {
    "Meet_WalkSplit.mpg": "CAVIARDATA1/Meet_WalkSplit/Meet_WalkSplit.mpg",
    "Walk1.mpg": "CAVIARDATA1/Walk1/Walk1.mpg",
    "OneStopNoEnter1cor.mpg": "CAVIARDATA2/OneStopNoEnter1cor/OneStopNoEnter1cor.mpg",
}


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        return response.read()


def store(path, url: str) -> bytes:
    if not path.exists():
        print("Downloading", path.name, flush=True)
        content = fetch(url)
        temp = path.with_suffix(path.suffix + ".part")
        temp.write_bytes(content)
        temp.replace(path)

    return path.read_bytes()


def download_caviar() -> None:
    destination = ROOT / CAVIAR_RAW_DIR
    destination.mkdir(parents=True, exist_ok=True)
    manifest = ROOT / CAVIAR_MANIFEST
    records = (
        {r["file"]: r for r in json.loads(manifest.read_text())}
        if manifest.exists()
        else {}
    )

    for name, suffix in SOURCES.items():
        path = destination / name
        url = BASE + suffix
        content = store(path, url)

        records[name] = dict(
            file=name,
            url=url,
            bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )

    manifest.write_text(json.dumps(list(records.values()), indent=2) + "\n")


def download_lighting() -> None:
    destination = ROOT / LIGHTING_RAW_DIR
    destination.mkdir(parents=True, exist_ok=True)
    records = json.loads((ROOT / LIGHTING_MANIFEST).read_text())

    for record in records:
        path = destination / record["raw_file"]
        content = store(path, record["source_url"])
        expected_size = record.get("source_bytes", record.get("bytes"))
        expected_hash = record.get("source_sha256", record.get("sha256"))

        if len(content) != expected_size or hashlib.sha256(content).hexdigest() != expected_hash:
            raise ValueError(f"Source checksum mismatch: {record['raw_file']}")


def main() -> None:
    download_caviar()
    download_lighting()


if __name__ == "__main__":
    main()
