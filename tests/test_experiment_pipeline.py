"""Experiments must measure the app's output, including changes to its detector."""

import cv2
import numpy as np

from motion_tracking import runner
from motion_tracking.experiments import learning_rate, measurements
from motion_tracking.matching import MatchResult


class AppDetector:
    """Distinct app output makes a separate experiment detector observable."""

    def __init__(self, config):
        self.raw_mask = np.zeros((24, 32), np.uint8)
        self.raw_mask[:, :16] = 127

    def detect(self, frame):
        mask = np.zeros(frame.shape[:2], np.uint8)
        mask[:, :16] = 255
        self.binary_mask = mask
        self.opened_mask = mask
        return [(0, 0, 16, 24)], mask


def write_video(path, count):
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 25, (32, 24))
    assert writer.isOpened()
    try:
        for _ in range(count):
            writer.write(np.zeros((24, 32, 3), np.uint8))
    finally:
        writer.release()


def test_tracker_experiment_uses_app_detections(tmp_path, monkeypatch):
    source = tmp_path / "01.mp4"
    write_video(source, 3)
    monkeypatch.setattr(runner, "MotionDetector", AppDetector)
    [(name, variants)] = list(measurements.measure_tracks([source]))
    assert name == "01"
    for records in variants.values():
        assert records == [
            {"frame": index, "tracks": {"1": [0, 0, 16, 24]}} for index in range(3)
        ]


def test_matching_experiment_uses_app_matches(tmp_path, monkeypatch):
    write_video(tmp_path / "inputs/jogging.mp4", 307)
    assert cv2.imwrite(
        str(tmp_path / "inputs/target.png"), np.zeros((24, 32, 3), np.uint8)
    )

    class AppMatcher:
        def __init__(self, target):
            self.target_kp = [None] * 10

        def match(self, frame):
            return MatchResult(keypoints=41, matches=4, inliers=3)

    monkeypatch.setattr(measurements, "MATCHER", tmp_path)
    monkeypatch.setattr(runner, "TargetMatcher", AppMatcher)
    rows, images = measurements.measure_application_matcher()
    assert len(rows) == len(images) == 5
    for row in rows:
        assert row["keypoints"] == 41
        assert row["matches"] == 4
        assert row["inliers"] == 3
        assert row["rate"] == 40
        assert row["found"] is False


def test_learning_rate_uses_app_masks_and_raw_labels(tmp_path, monkeypatch):
    write_video(tmp_path / "inputs/17.mp4", 525)
    gt_dir = tmp_path / "raw/lasiesta/I_IL_02-GT"
    gt_dir.mkdir(parents=True)
    gt = np.zeros((24, 32, 3), np.uint8)
    gt[:, :16] = (0, 0, 255)
    for index in range(1, 526):
        assert cv2.imwrite(str(gt_dir / f"I_IL_02-GT_{index}.png"), gt)
    monkeypatch.setattr(learning_rate, "TRACKER", tmp_path)
    monkeypatch.setattr(runner, "MotionDetector", AppDetector)
    rows, images = learning_rate.run()
    assert len(rows) == 15 and len(images) == 3
    for row in rows:
        assert row["foreground_recall"] == 1
        assert row["background_fpr"] == 0
        assert row["person_raw_shadow_fraction"] == 1
        assert row["person_raw_background_fraction"] == 0
        assert row["person_raw_foreground_fraction"] == 0
