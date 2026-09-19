"""One command for Tracker, Matcher and Target Detection tests."""

import argparse
import json
from pathlib import Path

import cv2

from datasets.paths import DETECTION, RESULTS, TRACKER, tracker_input
from datasets.storage import write_json
from motion_tracking.runner import run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="purpose", required=True)
    tracker = subparsers.add_parser(
        "tracker", help="MOG2, ID and trajectory test on cases 01–19"
    )
    tracker.add_argument("--case", type=int, choices=range(1, 20), default=1)
    tracker.add_argument("--suite", action="store_true", help="Run all 19 cases")
    tracker.add_argument(
        "--measure",
        action="store_true",
        help="Reproduce annotated submission and learning-rate measurements",
    )
    tracker.add_argument(
        "--max-frames",
        type=int,
        help="Limit app smoke run; incompatible with --measure",
    )
    matcher = subparsers.add_parser(
        "matcher", help="Jogging ORB/SIFT ROI conditions and full-frame app comparison"
    )
    detection = subparsers.add_parser(
        "detection", help="Oxford full-frame production TargetMatcher demonstration"
    )
    detection.add_argument(
        "--max-frames",
        type=int,
        help="Defaults to all 7,502 frames; target registration is frame 5,800",
    )
    for command in (tracker, matcher, detection):
        command.add_argument(
            "--output-dir", type=Path, help="Default: results/<purpose>/runs/latest"
        )
    args = parser.parse_args()
    output = args.output_dir or RESULTS / args.purpose / "runs/latest"
    output = output.resolve()
    if (
        output.is_relative_to(RESULTS)
        and "baseline" in output.relative_to(RESULTS).parts
    ):
        parser.error("Baseline evidence is immutable; select a run output directory")
    cv2.setNumThreads(1)
    cv2.setRNGSeed(0)
    try:
        output.mkdir(parents=True, exist_ok=True)
        if args.purpose == "tracker":
            if args.measure:
                if args.max_frames is not None:
                    parser.error("--measure requires complete input videos")
                from datasets.workflow import prepare_evaluation
                from evaluation import background, measurements, review
                from evaluation import tracker as metrics

                gt = TRACKER / "raw/lasiesta/I_IL_02-GT"
                if len(list(gt.glob("*.png"))) != 525:
                    raise FileNotFoundError(
                        "Learning-rate GT missing. Run: python scripts/01_setup_data.py --purpose tracker --raw"
                    )
                prepare_evaluation(purpose="tracker")
                measurements.measure_tracks(output / "submission")
                metrics.run(output / "submission")
                review.run(output / "submission")
                measurements.measure_learning_rates(output / "learning_rate")
                background.run(output / "learning_rate")
                result = dict(
                    submission=str(output / "submission"),
                    learning_rate=str(output / "learning_rate"),
                )
            else:
                result = {}
                for number in range(1, 20) if args.suite else [args.case]:
                    destination = output / f"case_{number:02d}"
                    result[f"{number:02d}"] = run(
                        tracker_input(number),
                        headless=True,
                        max_frames=args.max_frames,
                        output=destination / "video.mp4",
                        csv_path=destination / "tracks.csv",
                        snapshot_dir=destination / "snapshots",
                    )
        elif args.purpose == "matcher":
            from evaluation import matcher, measurements

            rows = matcher.run(output / "roi")
            measurements.measure_application_matcher(output / "application")
            result = dict(conditions=len(rows), algorithms=["ORB", "SIFT"])
        else:
            result = run(
                DETECTION / "raw/town_centre.mp4",
                target=DETECTION / "inputs/target.png",
                headless=True,
                max_frames=args.max_frames,
                output=output / "video.mp4",
                csv_path=output / "tracks.csv",
                snapshot_dir=output / "snapshots",
            )
            if not result["target_frames"]:
                raise ValueError(
                    "No TARGET DETECTED frames; short prefixes may end before the registered person appears"
                )
        write_json(output / "summary.json", result)
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, cv2.error) as error:
        parser.exit(2, f"Error: {error}\n")
