import cv2
import numpy as np

from motion_tracking.config import Config
from motion_tracking.runner import run


def test_app_exposes_segmentation_stages(tmp_path):
    path = tmp_path / "scene.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 20, (160, 120))
    for f in range(15):
        frame = np.zeros((120, 160, 3), np.uint8)
        if f > 9:
            frame[20:90, 60:80] = 255
        writer.write(frame)
    writer.release()
    observed = []

    def observe(result):
        assert hasattr(result, "binary_mask")
        assert hasattr(result, "opened_mask")
        assert hasattr(result, "boxes")
        observed.append(len(result.boxes))

    run(path, Config(warmup_frames=5), headless=True, on_frame=observe)
    assert max(observed) == 1


def test_quality_rejects_a_leg_and_counts_leftovers_and_merges():
    from motion_tracking.experiments.fragmentation import quality

    gt = {"a": (0, 0, 20, 100), "b": (25, 0, 20, 100)}
    leg = quality(gt, {1: (0, 70, 20, 30)})
    assert leg["complete"] == 0
    assert leg["misses"] == 1
    pieces = quality({"a": gt["a"]}, {1: (0, 0, 20, 60), 2: (0, 70, 20, 30)})
    assert pieces["duplicates"] == 1
    assert pieces["fragmented"] == 1
    assert quality(gt, {1: (0, 0, 45, 100)})["merges"] == 1
    assert quality(gt, {1: gt["a"], 2: gt["b"]})["complete"] == 2


def test_independent_open_control_preserves_thin_body_connection():
    from motion_tracking.motion import MotionDetector

    detector = MotionDetector(
        Config(warmup_frames=2, learning_rate=0, open_kernel_size=1)
    )
    frame = np.zeros((288, 384, 3), np.uint8)
    for _ in range(3):
        detector.detect(frame)
    frame[40:55, 90:110] = 255
    frame[55:65, 99:100] = 255
    frame[65:130, 85:115] = 255
    boxes, mask = detector.detect(frame)
    assert len(boxes) == 1
    assert boxes[0][1] == 40
    assert mask[60, 99] == 255


def test_temporal_composition_retains_person_and_separates_neighbor():
    from motion_tracking.tracker import Tracker

    tracker = Tracker()
    tracker.update([(20, 20, 30, 100), (60, 20, 30, 100)])
    fragments = [(22, 20, 26, 20), (20, 45, 30, 75), (60, 20, 30, 100)]
    assert hasattr(tracker, "compose")
    boxes = tracker.compose(fragments)
    assert sorted(boxes) == [(20, 20, 30, 100), (60, 20, 30, 100)]
    assert len(tracker.update(boxes)) == 2


def test_ambiguous_fragments_are_not_merged_or_discarded():
    from motion_tracking.tracker import Tracker

    tracker = Tracker()
    tracker.update([(20, 20, 30, 100), (30, 20, 30, 100)])
    fragments = [(32, 20, 10, 20), (32, 60, 10, 40)]
    assert hasattr(tracker, "compose")
    assert tracker.compose(fragments) == fragments


def test_app_reassembles_observed_body_without_dropping_nearby_person(tmp_path):
    path = tmp_path / "split.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"FFV1"), 20, (320, 240))
    assert writer.isOpened()
    for f in range(15):
        frame = np.zeros((240, 320, 3), np.uint8)
        if f >= 5:
            frame[30:130, 30:60] = 255
            frame[30:130, 85:115] = 255
        if f >= 8:
            frame[50:65, 30:60] = 0
        writer.write(frame)
    writer.release()
    outputs = []
    for enabled in (0, 1):
        observed = []

        def observe(r):
            observed.append(
                (
                    len(r.component_boxes),
                    len(r.boxes),
                    {i: t.bbox for i, t in r.tracks.items() if not t.missing},
                )
            )

        run(
            path,
            Config(warmup_frames=2, learning_rate=0, compose_fragments=enabled),
            headless=True,
            on_frame=observe,
        )
        outputs.append(observed[-1])
    assert outputs[0][0:2] == (3, 3)
    assert outputs[1][0:2] == (3, 2)
    assert len(outputs[0][2]) == 3
    assert set(outputs[1][2]) == {1, 2}
    assert sorted(outputs[1][2].values()) == [(30, 30, 30, 100), (85, 30, 30, 100)]


def test_composition_is_scale_relative_and_does_not_join_unseen_or_expired_people():
    from motion_tracking.tracker import Tracker

    for scale in (1, 2, 4):

        def scaled(box):
            return tuple(v * scale for v in box)

        full = scaled((20, 20, 30, 100))
        parts = [scaled((20, 20, 30, 20)), scaled((20, 50, 30, 70))]
        t = Tracker()
        assert t.compose(parts) == parts
        t.update([full])
        assert t.compose(parts) == [full]
        for _ in range(3):
            t.update([])
        assert t.compose(parts) == parts
