"""Boundary cases for geometry and descriptor matching shared across callers."""
import cv2
import numpy as np
import pytest

from motion_tracking.features import unique_ratio_matches
from motion_tracking.geometry import intersection_area, iou


@pytest.mark.parametrize('box, area, score', [
    ((5, 0, 10, 10), 50, 1/3),
    ((10, 0, 10, 10), 0, 0),
    ((2, 2, 2, 2), 4, .04),
    ((0, 0, 0, 0), 0, 0),
])
def test_box_intersection_and_union(box, area, score):
    reference = (0, 0, 10, 10)
    assert intersection_area(reference, box) == intersection_area(box, reference) == area
    assert iou(reference, box) == pytest.approx(score)
    assert iou(box, reference) == pytest.approx(score)


@pytest.mark.parametrize('norm, dtype', [(cv2.NORM_HAMMING, np.uint8), (cv2.NORM_L2, np.float32)])
def test_matching_deduplicates_scene_features_for_orb_and_sift(norm, dtype):
    reference = np.array([[0, 0], [0, 0], [255, 255]], dtype=dtype)
    scene = np.array([[0, 0], [255, 255]], dtype=dtype)
    matcher = cv2.BFMatcher(norm)
    matches = unique_ratio_matches(matcher, reference, scene)
    assert [(m.queryIdx, m.trainIdx) for m in matches] == [(0, 0), (2, 1)]
    assert unique_ratio_matches(matcher, reference, None) == []
    assert unique_ratio_matches(matcher, reference, scene[:1]) == []
    # Equal nearest-neighbor distances fail the strict ratio test.
    assert unique_ratio_matches(matcher, reference[:1], np.zeros((2, 2), dtype=dtype)) == []
