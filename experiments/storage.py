"""Experiment exports and reproducibility metadata."""

import csv
import platform
import subprocess
from dataclasses import asdict
from pathlib import Path

import cv2
import numpy as np

from datasets.paths import ROOT
from datasets.storage import sha256, write_json
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


def environment(output: Path, inputs: list[Path]) -> None:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True
    )
    write_json(
        output / "environment.json",
        dict(
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
        ),
    )
