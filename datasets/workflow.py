"""Two user-facing stages: obtain inputs, then verify dataset readiness."""

import argparse
import json
from pathlib import Path

import cv2

from datasets import detection, jogging, tracker
from datasets.paths import DETECTION, MATCHER, ROOT, TRACKER, tracker_input
from datasets.storage import sha256, write_json
from motion_tracking.matching import TargetMatcher


def check_video(path: Path, expected_frames: int | None = None) -> dict:
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise ValueError(f"Cannot open {path}")
        expected = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        count = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            count += 1
        if not count or (expected_frames is not None and count != expected_frames):
            raise ValueError(
                f"Incomplete video {path}: decoded {count}, expected {expected_frames or expected}"
            )
        return dict(
            frames=count,
            header_frames=expected,
            width=frame.shape[1]
            if frame is not None
            else int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            fps=cap.get(cv2.CAP_PROP_FPS),
        )
    finally:
        cap.release()


def setup(
    *,
    offline: bool = False,
    raw: bool = False,
    detection_source: Path | None = None,
    purpose: str = "all",
) -> None:
    if purpose in ("all", "tracker"):
        tracker.prepare(offline=offline, raw=raw)
    if purpose in ("all", "matcher"):
        jogging.prepare(offline=offline)
    if purpose in ("all", "detection"):
        detection.prepare(offline=offline, source=detection_source)
    # Generated manifest describes actual prepared bytes, never replaces source provenance.
    for name in ("tracker", "matcher", "detection"):
        if purpose not in ("all", name):
            continue
        directory = ROOT / "data" / name
        inputs = sorted(p for p in (directory / "inputs").glob("*") if p.is_file())
        if name == "detection":
            inputs.append(DETECTION / "raw/town_centre.mp4")
        write_json(
            directory / "generated/prepared.json",
            [
                dict(
                    path=str(p.relative_to(ROOT)),
                    bytes=p.stat().st_size,
                    sha256=sha256(p),
                )
                for p in inputs
            ],
        )


def verify_data(*, purpose: str = "all") -> dict:
    setup(offline=True, purpose=purpose)
    report = {}
    if purpose in ("all", "tracker"):
        counts = {
            int(Path(r["local_file"]).stem): r["frames"]
            for r in tracker.records("lasiesta")
        }
        counts.update(
            {int(Path(r["file"]).stem): r["frames"] for r in tracker.records("overlap")}
        )
        counts[14] = 2715
        report["tracker"] = {
            f"{n:02d}": check_video(tracker_input(n), counts.get(n))
            for n in range(1, 20)
        }
        reference = TRACKER / "reference"
        events = json.loads((reference / "events.json").read_text())
        truth = json.loads((reference / "ground_truth.json").read_text())
        if len(events) != 30 or any(event["video"] not in truth for event in events):
            raise ValueError("Missing tracker event annotations")
        if all(
            (TRACKER / f"raw/lasiesta/{seq}-GT").is_dir()
            for seq in ("I_OC_01", "I_OC_02", "I_IL_01", "I_IL_02", "I_CA_01")
        ) and all(
            (TRACKER / "raw/caviar" / r["gt_file"]).exists()
            for r in tracker.records("overlap")
        ):
            from datasets.annotations import rebuild

            rebuilt = TRACKER / "generated/annotations"
            rebuild(rebuilt)
            if json.loads((rebuilt / "ground_truth.json").read_text()) != truth:
                raise ValueError(
                    "Reconstructed tracker annotations differ from preserved reference"
                )
    if purpose in ("all", "matcher"):
        report["matcher"] = check_video(MATCHER / "inputs/jogging.mp4", 307)
        TargetMatcher(cv2.imread(str(MATCHER / "inputs/target.png")))
    if purpose in ("all", "detection"):
        report["detection"] = check_video(DETECTION / "raw/town_centre.mp4", 7502)
        TargetMatcher(cv2.imread(str(DETECTION / "inputs/target.png")))
    for name, details in report.items():
        write_json(ROOT / "data" / name / "generated/readiness.json", details)
    return report


def main(stage: str) -> None:
    if stage not in {"setup", "verify"}:
        raise ValueError(f"Unknown workflow stage: {stage}")
    parser = argparse.ArgumentParser(
        description="Prepare pinned datasets"
        if stage == "setup"
        else "Verify all prepared data inputs"
    )
    parser.add_argument(
        "--purpose", choices=("all", "tracker", "matcher", "detection"), default="all"
    )
    if stage == "setup":
        parser.add_argument(
            "--offline", action="store_true", help="Use cached local sources only"
        )
        parser.add_argument(
            "--raw",
            action="store_true",
            help="Also download/extract tracker source archives and GT for full measurements",
        )
        parser.add_argument(
            "--detection-source",
            type=Path,
            help="Import the original Oxford MP4 from a local download",
        )
    args = vars(parser.parse_args())
    try:
        if stage == "setup":
            setup(**args)
            print("Data ready; run scripts/02_verify_data.py")
        else:
            print(json.dumps(verify_data(**args), indent=2))
    except (OSError, ValueError, cv2.error) as error:
        parser.exit(2, f"Error: {error}\n")
