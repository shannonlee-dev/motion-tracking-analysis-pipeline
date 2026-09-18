"""Foreground segmentation and geometric ORB target recognition."""

from dataclasses import dataclass

import cv2
import numpy as np

from motion_tracking.config import DEFAULT_CONFIG, Config
from motion_tracking.constants import MASK_MAX_VALUE
from motion_tracking.features import (
    FEATURE_COUNT,
    KNN_NEIGHBORS,
    MATCH_RATIO,
    RANSAC_REPROJECTION_THRESHOLD,
    unique_ratio_matches,
)
from motion_tracking.geometry import BBox

FOREGROUND_THRESHOLD = 200  # Discard the MOG2 shadow label (127).
MIN_TARGET_INLIERS = 8
MIN_TARGET_INLIER_RATIO = 0.5
MIN_TARGET_AREA = 100
MAX_TARGET_AREA_FRACTION = 0.95
TARGET_BOUNDARY_MARGIN = 1  # Permit one frame's width/height outside each edge.


class MotionDetector:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or DEFAULT_CONFIG
        self.model = cv2.createBackgroundSubtractorMOG2(
            history=self.config.history,
            varThreshold=self.config.var_threshold,
            detectShadows=True,
        )
        self.kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (self.config.kernel_size, self.config.kernel_size)
        )
        self.frame_count = 0

    def detect(self, frame: np.ndarray) -> tuple[list[BBox], np.ndarray]:
        raw = self.model.apply(
            frame, learningRate=self.config.learning_rate
        )  # one channel mask, 0=background, 127=shadow, 255=foreground
        mask = cv2.threshold(
            raw, FOREGROUND_THRESHOLD, MASK_MAX_VALUE, cv2.THRESH_BINARY
        )[1]  # binary mask
        mask = cv2.morphologyEx(
            mask, cv2.MORPH_OPEN, self.kernel
        )  # remove white noise, opening = erosion + dilation
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kernel)  # opening
        self.frame_count += 1

        if self.frame_count <= self.config.warmup_frames:
            return [], mask

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        max_area = frame.shape[0] * frame.shape[1] * self.config.max_area_fraction
        boxes = [
            cv2.boundingRect(c)
            for c in contours
            if self.config.min_area <= cv2.contourArea(c) <= max_area
        ]

        return sorted(boxes), mask


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
