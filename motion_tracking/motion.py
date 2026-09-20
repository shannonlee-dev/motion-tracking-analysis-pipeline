"""MOG2 foreground segmentation and contour bounding boxes."""

import cv2
import numpy as np

from motion_tracking import BBox
from motion_tracking.config import DEFAULT_CONFIG, Config
from motion_tracking.constants import MASK_MAX_VALUE

FOREGROUND_THRESHOLD = 200  # Discard shadows.


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
        self.open_kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (self.config.open_kernel_size, self.config.open_kernel_size),
        )
        self.frame_count = 0
        self.raw_mask: np.ndarray | None = None
        self.binary_mask: np.ndarray | None = None
        self.opened_mask: np.ndarray | None = None

    def detect(
        self, frame: np.ndarray
    ) -> tuple[list[BBox], np.ndarray]:  # boxes,binary mask
        raw = self.model.apply(
            frame, learningRate=self.config.learning_rate
        )  # one channel mask, 0=background, 127=shadow, 255=foreground
        self.raw_mask = raw
        mask = cv2.threshold(
            raw, FOREGROUND_THRESHOLD, MASK_MAX_VALUE, cv2.THRESH_BINARY
        )[1]  # binary mask
        self.binary_mask = mask
        mask = cv2.morphologyEx(
            mask, cv2.MORPH_OPEN, self.open_kernel
        )  # remove white noise, opening = erosion + dilation
        self.opened_mask = mask
        mask = cv2.morphologyEx(
            mask, cv2.MORPH_CLOSE, self.kernel
        )  # closing fills holes
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
