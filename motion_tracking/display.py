"""Frame overlays and keyboard controls."""

import time
from collections.abc import Mapping
from pathlib import Path

import cv2
import numpy as np

from motion_tracking.tracker import Track
from motion_tracking.vision import MatchResult

KEY_QUIT = ord("q")
KEY_PAUSE = ord("p")
KEY_SNAPSHOT = ord("s")
FONT = cv2.FONT_HERSHEY_SIMPLEX
TEXT_SCALE = 0.45
TARGET_TEXT_SCALE = 0.75
LINE_THICKNESS = 2
TEXT_THICKNESS = 1
TARGET_BOX_THICKNESS = 5
TARGET_TEXT_THICKNESS = 2
TARGET_LABEL_PADDING = 4
CENTER_RADIUS = 3
TRACK_COLOR_BASE = 60
TRACK_COLOR_RANGE = 190
TRACK_COLOR_FACTORS = (73, 37, 109)
STATUS_SIZE = (400, 24)
STATUS_BACKGROUND = (25, 25, 25)
STATUS_TEXT_COLOR = (255, 255, 255)
TARGET_COLOR = (0, 0, 255)
STATUS_TEXT_ORIGIN = (7, 17)
LABEL_OFFSET = 5
LABEL_MIN_Y = 15


class Controls:
    def __init__(self) -> None:
        self.paused = False

    def handle(
        self,
        key: int,
        frame: np.ndarray | None,
        snapshot_dir: str | Path,
        frame_number: int,
    ) -> bool:
        if key == KEY_QUIT:
            return False

        if key == KEY_PAUSE:
            self.paused = not self.paused

        if key == KEY_SNAPSHOT and frame is not None:
            directory = Path(snapshot_dir)
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / f"frame_{frame_number:06d}_{time.time_ns()}.png"

            if not cv2.imwrite(str(path), frame):
                raise OSError(f"Cannot save snapshot: {path}")

        return True


def draw_overlay(
    frame: np.ndarray,
    tracks: Mapping[int, Track],
    fps: float,
    frame_number: int,
    match: MatchResult | None = None,
) -> np.ndarray:
    image = frame.copy()

    for tid, track in tracks.items():
        if track.missing:
            continue  # Retained state is not an observed detection.

        color = tuple(
            TRACK_COLOR_BASE + (tid * factor) % TRACK_COLOR_RANGE
            for factor in TRACK_COLOR_FACTORS
        )
        x, y, w, h = track.bbox
        cv2.rectangle(image, (x, y), (x + w, y + h), color, LINE_THICKNESS)
        cv2.putText(
            image,
            f"ID:{tid}",
            (x, max(y - LABEL_OFFSET, LABEL_MIN_Y)),
            FONT,
            TEXT_SCALE,
            color,
            TEXT_THICKNESS,
        )
        cv2.circle(image, tuple(map(int, track.center)), CENTER_RADIUS, color, -1)

        if len(track.trail) > 1:
            cv2.polylines(
                image, [np.array(track.trail, np.int32)], False, color, LINE_THICKNESS
            )

    cv2.rectangle(
        image,
        (0, 0),
        (min(image.shape[1], STATUS_SIZE[0]), STATUS_SIZE[1]),
        STATUS_BACKGROUND,
        -1,
    )
    cv2.putText(
        image,
        f"FPS: {fps:.1f} | frame {frame_number}",
        STATUS_TEXT_ORIGIN,
        FONT,
        TEXT_SCALE,
        STATUS_TEXT_COLOR,
        TEXT_THICKNESS,
    )

    if match is not None and match.found and match.polygon is not None:
        x, y, w, h = cv2.boundingRect(match.polygon)
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(image.shape[1] - 1, x + w)
        y2 = min(image.shape[0] - 1, y + h)

        if x2 <= x1 or y2 <= y1:
            return image

        cv2.rectangle(image, (x1, y1), (x2, y2), TARGET_COLOR, TARGET_BOX_THICKNESS)
        label = "TARGET DETECTED"
        (label_width, label_height), baseline = cv2.getTextSize(
            label, FONT, TARGET_TEXT_SCALE, TARGET_TEXT_THICKNESS
        )
        label_x = min(x1, max(0, image.shape[1] - label_width - TARGET_LABEL_PADDING))
        label_y = y1 - TARGET_LABEL_PADDING

        if label_y - label_height - baseline < 0:
            label_y = min(image.shape[0] - TARGET_LABEL_PADDING, y1 + label_height + TARGET_LABEL_PADDING)

        cv2.rectangle(
            image,
            (label_x, max(0, label_y - label_height - baseline - TARGET_LABEL_PADDING)),
            (
                min(image.shape[1] - 1, label_x + label_width + TARGET_LABEL_PADDING * 2),
                min(image.shape[0] - 1, label_y + baseline + TARGET_LABEL_PADDING),
            ),
            TARGET_COLOR,
            -1,
        )
        cv2.putText(
            image,
            label,
            (label_x + TARGET_LABEL_PADDING, label_y),
            FONT,
            TARGET_TEXT_SCALE,
            STATUS_TEXT_COLOR,
            TARGET_TEXT_THICKNESS,
        )

    return image
