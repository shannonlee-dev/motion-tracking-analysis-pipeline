"""Reproduce tracker and application matcher measurements with the unmodified application classes."""

import json
from pathlib import Path

import cv2

from datasets.jogging import SELECTIONS, write_image
from datasets.paths import MATCHER, TRACKER
from experiments.storage import initialize_reproducibility, write_csv
from motion_tracking.matching import TargetMatcher
from motion_tracking.motion import MotionDetector
from motion_tracking.tracker import Tracker


def measure_application_matcher(details: Path | None = None):
    initialize_reproducibility()
    matcher = TargetMatcher(cv2.imread(str(MATCHER / "inputs/target.png")))
    selected = {s[2] - 1: s for s in SELECTIONS}
    cap = cv2.VideoCapture(str(MATCHER / "inputs/jogging.mp4"))
    rows, images = [], {}
    index = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if index in selected:
                slug, label, source, _ = selected[index]
                label = label.replace("° 방향 변화", "도 회전")
                result = matcher.match(frame)
                rows.append(
                    dict(
                        condition=label,
                        video="data/matcher/inputs/jogging.mp4",
                        frame=index,
                        source_jpg_frame=source,
                        keypoints=result.keypoints,
                        matches=result.matches,
                        target_keypoints=len(matcher.target_kp),
                        rate=100 * result.matches / len(matcher.target_kp),
                        inliers=result.inliers,
                        found=result.found,
                    )
                )
                images[f"feature_{slug}"] = frame
                if details is not None:
                    write_image(details / f"application__feature_{slug}.png", frame)
            index += 1
    finally:
        cap.release()
    if index != 307 or len(rows) != len(selected):
        raise ValueError(
            f"Incomplete Jogging input: {index} frames, {len(rows)} conditions"
        )
    rows.sort(key=lambda r: list(selected).index(r["frame"]))
    if details is not None:
        write_csv(details / "application__features.csv", rows)
    return rows, images


def measure_tracks(details: Path | None = None):
    """Yield one video's traces at a time; retain no decoded video frames."""
    initialize_reproducibility()
    for path in sorted((TRACKER / "inputs").glob("*")):
        if path.stem in ("12", "13"):
            continue
        cap = cv2.VideoCapture(str(path))
        detector = MotionDetector()
        variants = {
            "default": Tracker(),
            "distance_80": Tracker(max_distance=80),
            "missing_30": Tracker(max_missing=30),
            "velocity": Tracker(predict_velocity=True),
        }
        records = {key: [] for key in variants}
        index = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                boxes, _ = detector.detect(frame)
                for key, tracker in variants.items():
                    tracks = tracker.update(boxes)
                    records[key].append(
                        dict(
                            frame=index,
                            tracks={
                                str(tid): list(t.bbox)
                                for tid, t in tracks.items()
                                if t.missing == 0
                            },
                        )
                    )
                index += 1
        finally:
            cap.release()
        if details is not None:
            for key, record in records.items():
                (details / f"tracks_{path.stem}_{key}.json").write_text(
                    json.dumps(record, separators=(",", ":")) + "\n"
                )
        print(path, index, flush=True)
        yield path.stem, records
