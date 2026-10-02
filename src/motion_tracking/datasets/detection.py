"""Create local-only directories for manually supplied Oxford inputs."""

import json

from motion_tracking.datasets.paths import DETECTION
from motion_tracking.datasets.storage import verify


def prepare() -> None:
    for name in ("raw", "inputs"):
        directory = DETECTION / name
        directory.mkdir(parents=True, exist_ok=True)
        (directory / ".gitkeep").touch(exist_ok=True)


def verify_inputs() -> None:
    record = json.loads((DETECTION / "reference/source.json").read_text())
    verify(DETECTION / "raw/town_centre.mp4", record)
    verify(DETECTION / "inputs/target.png", record["target"])
