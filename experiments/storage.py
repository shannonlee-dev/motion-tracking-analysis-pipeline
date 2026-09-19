"""Experiment exports and reproducibility metadata."""

import argparse
import csv
import json
import platform
import subprocess
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import cv2
import numpy as np

from datasets.paths import RESULTS, ROOT
from datasets.storage import sha256
from motion_tracking.config import DEFAULT_CONFIG


def initialize_reproducibility() -> None:
    cv2.setNumThreads(1)
    cv2.setRNGSeed(0)


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"No measurements to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def environment(inputs: list[Path]) -> dict:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True
    )

    return dict(
        python=platform.python_version(),
        opencv=cv2.__version__,
        numpy=np.__version__,
        platform=platform.platform(),
        commit=revision.stdout.strip(),
        config=asdict(DEFAULT_CONFIG),
        seed=0,
        threads=1,
        input_sha256={str(p.relative_to(ROOT)): sha256(p) for p in inputs},
        code_sha256={
            str(p.relative_to(ROOT)): sha256(p)
            for directory in ("motion_tracking", "experiments", "datasets")
            for p in sorted((ROOT / directory).glob("*.py"))
        },
    )


def result_arguments(experiment: str, argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description=f"Reproduce {experiment} results")
    parser.add_argument("--output", type=Path, default=RESULTS / experiment)
    parser.add_argument(
        "--details", action="store_true", help="Keep individual traces and images"
    )
    return parser.parse_args(argv)


def comparison_image(images: dict[str, np.ndarray], output: Path) -> None:
    """Make a labeled, aspect-preserving overview of the selected evidence."""
    tiles = []
    for label, frame in sorted(images.items()):
        scale = 480 / frame.shape[1]
        frame = cv2.resize(
            frame,
            (
                max(1, round(frame.shape[1] * scale)),
                max(1, round(frame.shape[0] * scale)),
            ),
        )
        tile = np.full((frame.shape[0] + 40, 480, 3), 245, dtype=np.uint8)
        tile[40 : 40 + frame.shape[0], : frame.shape[1]] = frame
        cv2.putText(
            tile, label, (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 20), 1
        )
        tiles.append(tile)
    if not tiles:
        raise ValueError("No comparison images")
    height = max(tile.shape[0] for tile in tiles)
    tiles = [
        cv2.copyMakeBorder(
            tile,
            0,
            height - tile.shape[0],
            0,
            0,
            cv2.BORDER_CONSTANT,
            value=(245, 245, 245),
        )
        for tile in tiles
    ]
    columns = min(3, len(tiles))
    while len(tiles) % columns:
        tiles.append(np.full_like(tiles[0], 245))
    sheet = np.vstack(
        [np.hstack(tiles[i : i + columns]) for i in range(0, len(tiles), columns)]
    )
    if not cv2.imwrite(str(output), sheet):
        raise OSError(f"Cannot write comparison image: {output}")


@contextmanager
def result_directory(output: Path, experiment: str):
    """Stage final files; preserve previous results if calculation or export fails."""
    if output.is_symlink():
        raise ValueError(f"Refusing symlink output: {output}")
    if output.exists() and any(output.iterdir()):
        marker = output / "metadata.json"
        if (
            not marker.is_file()
            or json.loads(marker.read_text()).get("experiment") != experiment
        ):
            raise ValueError(f"Refusing unrelated output directory: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=f".{experiment}-", dir=output.parent) as temporary:
        staging = Path(temporary) / "ready"
        staging.mkdir()
        yield staging
        previous = Path(temporary) / "previous"
        if output.exists():
            output.rename(previous)
        try:
            staging.rename(output)
        except OSError:
            if previous.exists():
                previous.rename(output)
            raise
    print(f"Results: {output}")


def publish_results(
    output: Path,
    experiment: str,
    summary: list[dict],
    images: dict[str, np.ndarray],
    metadata: dict,
    *,
    details: bool = False,
    extra_summaries: dict[str, list[dict]] | None = None,
) -> None:
    """Write final artifacts directly from computed values, without intermediate files."""
    write_csv(output / "summary.csv", summary)
    for name, rows in (extra_summaries or {}).items():
        write_csv(output / name, rows)
    comparison_image(images, output / "comparison.jpg")
    (output / "metadata.json").write_text(
        json.dumps(
            dict(
                metadata,
                experiment=experiment,
                exported_at=datetime.now(timezone.utc).isoformat(),
                details=details,
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
