import numpy as np
import pytest

from motion_tracking.config import Config
from motion_tracking.matching import TargetMatcher
from motion_tracking.motion import MotionDetector
from motion_tracking.tracker import Tracker


def test_ids_follow_positions_not_detection_order():
    t = Tracker(max_distance=30, max_missing=2, trail_length=3)
    t.update([(0, 0, 10, 10), (100, 0, 10, 10)])
    tracks = t.update([(102, 0, 10, 10), (2, 0, 10, 10)])
    assert tracks[1].bbox == (2, 0, 10, 10)
    assert tracks[2].bbox == (102, 0, 10, 10)
    assert len(tracks[1].trail) == 2


def test_one_detection_cannot_update_two_tracks_and_ids_never_reuse():
    t = Tracker(max_distance=30, max_missing=1)
    t.update([(0, 0, 10, 10), (20, 0, 10, 10)])
    tracks = t.update([(10, 0, 10, 10)])
    assert sum(x.missing == 0 for x in tracks.values()) == 1
    t.update([])
    assert len(t.tracks) == 1
    t.update([])
    assert not t.tracks
    assert list(t.update([(0, 0, 10, 10)])) == [3]


def test_distance_gate_and_bounded_trail():
    t = Tracker(max_distance=5, trail_length=2)
    t.update([(0, 0, 10, 10)])
    t.update([(100, 0, 10, 10)])

    for x in range(101, 110):
        t.update([(x, 0, 10, 10)])

    assert list(t.tracks) == [1, 2]
    assert len(t.tracks[2].trail) == 2


def test_motion_after_background_warmup():
    detector = MotionDetector(Config(min_area=50, warmup_frames=5))
    background = np.zeros((120, 160, 3), np.uint8)

    for _ in range(10):
        boxes, _ = detector.detect(background)

    assert boxes == []
    frame = background.copy()
    frame[30:70, 40:80] = 255
    boxes, mask = detector.detect(frame)
    assert len(boxes) == 1
    assert boxes[0][0] <= 42 and boxes[0][2] >= 36
    assert mask[50, 50] == 255


def test_matcher_rejects_featureless_target():
    with pytest.raises(ValueError):
        TargetMatcher(np.zeros((100, 100, 3), np.uint8))


def test_matcher_accepts_real_texture_and_rejects_blank():
    rng = np.random.default_rng(7)
    target = rng.integers(0, 256, (180, 180, 3), dtype=np.uint8)
    matcher = TargetMatcher(target)
    scene = np.zeros((300, 400, 3), np.uint8)
    scene[50:230, 80:260] = target
    result = matcher.match(scene)
    assert result.found and result.inliers >= 8
    assert not matcher.match(np.zeros_like(scene)).found


def test_invalid_config_rejected():
    with pytest.raises(ValueError):
        Config(learning_rate=2)

    with pytest.raises(ValueError):
        Config(kernel_size=0)


def test_missing_frames_match_last_observed_position_without_extrapolation():
    tracker = Tracker(max_distance=11, max_missing=3)
    tracker.update([(0, 0, 10, 10)])
    tracker.update([(10, 0, 10, 10)])
    tracker.update([])
    tracker.update([])
    tracks = tracker.update([(40, 0, 10, 10)])
    assert list(tracks) == [1, 2]
    assert tracks[1].missing == 3
    assert list(tracks[1].trail) == [(5, 5), (15, 5)]
    assert tracks[2].bbox == (40, 0, 10, 10)
    tracks = tracker.update([(12, 0, 10, 10)])
    assert tracks[1].missing == 0
    assert list(tracks[1].trail) == [(5, 5), (15, 5), (17, 5)]
