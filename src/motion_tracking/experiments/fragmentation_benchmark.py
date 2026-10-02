"""Alternate real app runs to measure composition cost without observers."""

import argparse
import json
from pathlib import Path

from motion_tracking.config import Config
from motion_tracking.datasets.paths import tracker_input
from motion_tracking.experiments.storage import (
    environment,
    initialize_reproducibility,
    write_csv,
)
from motion_tracking.runner import run


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--videos", nargs="+", default=["03", "11", "17", "19"])
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    args.output.mkdir(parents=True, exist_ok=False)
    initialize_reproducibility()
    inputs = [tracker_input(name) for name in args.videos]
    metadata = environment(inputs)
    metadata.update(
        repeats=args.repeats,
        order="alternating AB/BA; no observer, matcher, or encoder",
    )
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    rows = []
    for name, source in zip(args.videos, inputs):
        for repeat in range(args.repeats):
            for enabled in (0, 1) if repeat % 2 == 0 else (1, 0):
                result = run(source, Config(compose_fragments=enabled), headless=True)
                rows.append(
                    dict(video=name, repeat=repeat, compose_fragments=enabled, **result)
                )
        print(name, "measured", flush=True)
    write_csv(args.output / "timings.csv", rows)


if __name__ == "__main__":
    main()
