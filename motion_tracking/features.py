"""Descriptor matching for ORB target recognition."""

import cv2
import numpy as np

FEATURE_COUNT = 1500
MATCH_RATIO = 0.75
KNN_NEIGHBORS = 2
RANSAC_REPROJECTION_THRESHOLD = 3.0


def unique_ratio_matches(
    matcher: cv2.DescriptorMatcher,
    reference: np.ndarray,
    scene: np.ndarray | None,
    ratio: float = MATCH_RATIO,
) -> list[cv2.DMatch]:
    """Apply Lowe's ratio test, keeping the best match per scene feature."""

    if scene is None or len(scene) < KNN_NEIGHBORS:
        return []

    pairs = matcher.knnMatch(reference, scene, k=KNN_NEIGHBORS)
    candidates = [
        pair[0]
        for pair in pairs
        if len(pair) == KNN_NEIGHBORS and pair[0].distance < ratio * pair[1].distance
    ]
    unique = {}

    for match in sorted(candidates, key=lambda match: match.distance):
        unique.setdefault(match.trainIdx, match)

    return list(unique.values())
