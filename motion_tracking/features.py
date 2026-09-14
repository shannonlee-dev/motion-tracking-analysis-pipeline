"""Descriptor matching shared by ORB recognition and SIFT evaluation."""

FEATURE_COUNT = 1500
MATCH_RATIO = 0.75
KNN_NEIGHBORS = 2
HOMOGRAPHY_MIN_MATCHES = 4
RANSAC_REPROJECTION_THRESHOLD = 3.0


def unique_ratio_matches(matcher, reference, scene, ratio=MATCH_RATIO):
    """Apply Lowe's ratio test, keeping the best match per scene feature."""
    if scene is None or len(scene) < KNN_NEIGHBORS:
        return []
    pairs = matcher.knnMatch(reference, scene, k=KNN_NEIGHBORS)
    candidates = [pair[0] for pair in pairs
                  if len(pair) == KNN_NEIGHBORS and pair[0].distance < ratio*pair[1].distance]
    unique = {}
    for match in sorted(candidates, key=lambda match: match.distance):
        unique.setdefault(match.trainIdx, match)
    return list(unique.values())
