"""Foreground segmentation and geometric ORB target recognition."""
from dataclasses import dataclass
import cv2
import numpy as np
from motion_tracking.config import Config


class MotionDetector:
    def __init__(self, config=None):
        self.config = config or Config()
        self.model = cv2.createBackgroundSubtractorMOG2(
            history=self.config.history, varThreshold=self.config.var_threshold, detectShadows=True)
        self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                               (self.config.kernel_size, self.config.kernel_size))
        self.frame_count = 0

    def detect(self, frame):
        raw = self.model.apply(frame, learningRate=self.config.learning_rate)
        # MOG2 labels shadows 127; only definite foreground survives.
        mask = cv2.threshold(raw, 200, 255, cv2.THRESH_BINARY)[1]
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kernel)
        self.frame_count += 1
        if self.frame_count <= self.config.warmup_frames:
            return [], mask
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        max_area = frame.shape[0]*frame.shape[1]*self.config.max_area_fraction
        boxes = [cv2.boundingRect(c) for c in contours
                 if self.config.min_area <= cv2.contourArea(c) <= max_area]
        return sorted(boxes), mask


@dataclass
class MatchResult:
    found: bool = False
    keypoints: int = 0
    matches: int = 0
    inliers: int = 0
    polygon: object = None


class TargetMatcher:
    def __init__(self, target, nfeatures=1500, ratio=0.75, min_inliers=8):
        if target is None or target.size == 0:
            raise ValueError('Cannot read target image')
        self.orb = cv2.ORB_create(nfeatures=nfeatures)
        self.target_kp, self.target_desc = self.orb.detectAndCompute(target, None)
        if self.target_desc is None or len(self.target_kp) < min_inliers:
            raise ValueError('Target needs more texture: fewer than required ORB features')
        self.height, self.width = target.shape[:2]
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
        self.ratio, self.min_inliers = ratio, min_inliers

    def match(self, frame):
        kp, desc = self.orb.detectAndCompute(frame, None)
        result = MatchResult(keypoints=len(kp))
        if desc is None or len(desc) < 2:
            return result
        pairs = self.matcher.knnMatch(self.target_desc, desc, k=2)
        good = [pair[0] for pair in pairs if len(pair) == 2 and pair[0].distance < self.ratio*pair[1].distance]
        # Each scene feature can support at most one target correspondence.
        unique = {}
        for match in sorted(good, key=lambda m: m.distance):
            unique.setdefault(match.trainIdx, match)
        good = list(unique.values())
        result.matches = len(good)
        if len(good) < self.min_inliers:
            return result
        src = np.float32([self.target_kp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst = np.float32([kp[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        h, inlier_mask = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
        if h is None or inlier_mask is None:
            return result
        result.inliers = int(inlier_mask.sum())
        corners = np.float32([[0, 0], [self.width-1, 0], [self.width-1, self.height-1], [0, self.height-1]]).reshape(-1, 1, 2)
        polygon = cv2.perspectiveTransform(corners, h)
        if not np.isfinite(polygon).all():
            return result
        area = abs(cv2.contourArea(polygon))
        height, width = frame.shape[:2]
        inside = ((polygon[:, :, 0] >= -width) & (polygon[:, :, 0] <= 2*width) &
                  (polygon[:, :, 1] >= -height) & (polygon[:, :, 1] <= 2*height)).all()
        result.found = bool(result.inliers >= self.min_inliers and result.inliers/len(good) >= .5
                            and 100 <= area <= width*height*.95 and inside and cv2.isContourConvex(polygon))
        if result.found:
            result.polygon = polygon.astype(np.int32)
        return result
