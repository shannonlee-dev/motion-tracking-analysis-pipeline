"""Reproduce submission measurements with the unmodified application classes."""

import json
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np

from datasets.jogging import SELECTIONS
from datasets.paths import MATCHER, TRACKER
from evaluation.storage import environment, write_csv
from motion_tracking.config import DEFAULT_CONFIG
from motion_tracking.matching import TargetMatcher
from motion_tracking.motion import MotionDetector
from motion_tracking.tracker import Tracker


def measure_application_matcher(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    cv2.setNumThreads(1)
    cv2.setRNGSeed(0)
    matcher = TargetMatcher(cv2.imread(str(MATCHER / "inputs/target.png")))
    selected = {s[2] - 1: s for s in SELECTIONS}
    cap = cv2.VideoCapture(str(MATCHER / "inputs/jogging.mp4"))
    rows = []
    index = 0
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
            cv2.imwrite(str(output / f"feature_{slug}.png"), frame)
        index += 1
    cap.release()
    if index != 307 or len(rows) != len(selected):
        raise ValueError(
            f"Incomplete Jogging input: {index} frames, {len(rows)} conditions"
        )
    rows.sort(key=lambda r: list(selected).index(r["frame"]))
    write_csv(output / "features.csv", rows)
    environment(output, [MATCHER / "inputs/jogging.mp4", MATCHER / "inputs/target.png"])


def measure_learning_rates(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    cv2.setNumThreads(1)
    for rate in (0.001, 0.01, 0.1):
        detector = MotionDetector(replace(DEFAULT_CONFIG, learning_rate=rate))
        cap = cv2.VideoCapture(str(TRACKER / "inputs/17.mp4"))
        rows = []
        tiles = []
        index = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            boxes, mask = detector.detect(frame)
            rows.append(
                dict(
                    frame=index,
                    foreground_pixels=int(np.count_nonzero(mask)),
                    foreground_fraction=float(np.mean(mask > 0)),
                    boxes=len(boxes),
                    mean_gray=float(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean()),
                )
            )
            if index in (100, 170, 190, 210, 240, 270, 300, 350, 420):
                im = frame.copy()
                for x, y, w, h in boxes:
                    cv2.rectangle(im, (x, y), (x + w, y + h), (0, 255, 0), 2)
                a = cv2.resize(im, (320, 240))
                b = cv2.resize(cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR), (320, 240))
                cv2.putText(a, f"LR {rate} f{index}", (5, 20), 0, 0.6, (0, 255, 255), 1)
                tiles.append(np.hstack([a, b]))
            index += 1
        cap.release()
        write_csv(output / f"learning_rate_{rate}.csv", rows)
        cv2.imwrite(str(output / f"learning_rate_{rate}.jpg"), np.vstack(tiles))
        print("learning rate", rate, "frames", index, flush=True)
    environment(output, [TRACKER / "inputs/17.mp4"])


def measure_tracks(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    cv2.setNumThreads(1)
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
                            tid: list(t.bbox)
                            for tid, t in tracks.items()
                            if t.missing == 0
                        },
                    )
                )
            index += 1
        cap.release()
        for key, record in records.items():
            (output / f"tracks_{path.stem}_{key}.json").write_text(
                json.dumps(record, separators=(",", ":")) + "\n"
            )
        print(path, index, flush=True)

    environment(output, sorted((TRACKER / "inputs").glob("*")))
