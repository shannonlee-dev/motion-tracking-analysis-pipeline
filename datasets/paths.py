"""Repository paths, independent of the shell's working directory."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
