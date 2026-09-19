"""Geometric ORB target recognition on complete application frames."""

from dataclasses import dataclass

import cv2
import numpy as np

from motion_tracking.features import (
    FEATURE_COUNT,
    KNN_NEIGHBORS,
    MATCH_RATIO,
    RANSAC_REPROJECTION_THRESHOLD,
    unique_ratio_matches,
)

MIN_TARGET_INLIERS = 8
MIN_TARGET_INLIER_RATIO = 0.5
MIN_TARGET_AREA = 100
MAX_TARGET_AREA_FRACTION = 0.95
TARGET_BOUNDARY_MARGIN = 1  # Permit one frame's width/height outside each edge.


@dataclass
class MatchResult:
    found: bool = False
    keypoints: int = 0
    matches: int = 0
    inliers: int = 0
    polygon: np.ndarray | None = None


class TargetMatcher:
    def __init__(
        self,
        target: np.ndarray | None,
        nfeatures: int = FEATURE_COUNT,
        ratio: float = MATCH_RATIO,
        min_inliers: int = MIN_TARGET_INLIERS,
    ) -> None:
        if target is None or target.size == 0:
            raise ValueError("Cannot read target image")

        self.orb = cv2.ORB_create(nfeatures=nfeatures)
        self.target_kp, self.target_desc = self.orb.detectAndCompute(target, None)

        if self.target_desc is None or len(self.target_kp) < min_inliers:
            raise ValueError(
                "Target needs more texture: fewer than required ORB features"
            )

        self.height, self.width = target.shape[:2]
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
        self.ratio, self.min_inliers = ratio, min_inliers

    def match(self, frame: np.ndarray) -> MatchResult:
        kp, desc = self.orb.detectAndCompute(frame, None)
        result = MatchResult(keypoints=len(kp))

        if desc is None or len(desc) < KNN_NEIGHBORS:
            return result

        good = unique_ratio_matches(self.matcher, self.target_desc, desc, self.ratio)
        result.matches = len(good)

        if len(good) < self.min_inliers:
            return result

        src = np.float32([self.target_kp[m.queryIdx].pt for m in good]).reshape(
            -1, 1, 2
        )
        dst = np.float32([kp[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        h, inlier_mask = cv2.findHomography(
            src, dst, cv2.RANSAC, RANSAC_REPROJECTION_THRESHOLD
        )

        if h is None or inlier_mask is None:
            return result

        result.inliers = int(inlier_mask.sum())
        corners = np.float32(
            [
                [0, 0],
                [self.width - 1, 0],
                [self.width - 1, self.height - 1],
                [0, self.height - 1],
            ]
        ).reshape(-1, 1, 2)
        polygon = cv2.perspectiveTransform(corners, h)

        if not np.isfinite(polygon).all():
            return result

        area = abs(cv2.contourArea(polygon))
        height, width = frame.shape[:2]
        inside = (
            (polygon[:, :, 0] >= -TARGET_BOUNDARY_MARGIN * width)
            & (polygon[:, :, 0] <= (1 + TARGET_BOUNDARY_MARGIN) * width)
            & (polygon[:, :, 1] >= -TARGET_BOUNDARY_MARGIN * height)
            & (polygon[:, :, 1] <= (1 + TARGET_BOUNDARY_MARGIN) * height)
        ).all()
        result.found = bool(
            result.inliers >= self.min_inliers
            and result.inliers / len(good) >= MIN_TARGET_INLIER_RATIO
            and MIN_TARGET_AREA <= area <= width * height * MAX_TARGET_AREA_FRACTION
            and inside
            and cv2.isContourConvex(polygon)
        )

        if result.found:
            result.polygon = polygon.astype(np.int32)

        return result
