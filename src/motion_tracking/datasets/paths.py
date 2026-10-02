"""Repository paths, independent of the shell's working directory."""

import os
from pathlib import Path


def workspace_root() -> Path:
    """Keep editable checkout assets stable; wheels use an explicit workspace."""
    if root := os.environ.get("MOTION_TRACKING_ROOT"):
        return Path(root).expanduser().resolve()
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "data").is_dir():
            return parent
    return Path.cwd().resolve()


ROOT = workspace_root()
DATA = ROOT / "data"
RESULTS = ROOT / "results"
TRACKER = DATA / "tracker"
MATCHER = DATA / "matcher"
DETECTION = DATA / "detection"
TRACKER_REFERENCE = TRACKER / "reference"


def tracker_input(case: int | str) -> Path:
    number = int(case)
    if not 1 <= number <= 19:
        raise ValueError("Tracker case must be between 1 and 19")
    return TRACKER / "inputs" / f"{number:02d}{'.mpg' if number <= 3 else '.mp4'}"
